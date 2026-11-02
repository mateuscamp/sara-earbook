# SPDX-License-Identifier: GPL-3.0-or-later
"""A tradução por lote (ADR-0006): o que o Python pede e o que o agente responde.

O Python nunca chama o LLM (ADR-0001). Ele exporta pedidos, cada um com até N palavras de
um capítulo, e o Claude Code grava a resposta de cada lote com o mesmo nome.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from earbook.dominio.segmento import Segmento

IDIOMA_DE_SAIDA = "pt-BR"
PALAVRAS_POR_LOTE = 2000
"""~2.700 tokens de entrada e ~3.500 de saída: a falha no meio custa no máximo isso."""

LOTE = re.compile(r"(c[0-9]{3,})-l([0-9]{3,})")
# O OPF pode trazer o código de três letras (ISO 639-2): "por" é "pt" (A2 e A3 da auditoria).
# O nome por extenso ("Portuguese") é fora do padrão, mas aparece em OPF feito à mão.
_DUAS_LETRAS = {
    "por": "pt", "eng": "en", "fra": "fr", "fre": "fr", "spa": "es", "deu": "de", "ger": "de",
    "ita": "it", "lat": "la",
    "portuguese": "pt", "português": "pt", "portugues": "pt", "english": "en", "inglês": "en",
    "ingles": "en", "french": "fr", "français": "fr", "spanish": "es", "español": "es",
    "german": "de", "deutsch": "de",
}  # fmt: skip
_INDEFINIDOS = frozenset({"", "und"})


class Modo(StrEnum):
    TRADUCAO = "traducao"
    """O texto final é a tradução, e ela cobre o livro inteiro."""
    AMOSTRA = "amostra"
    """Só o traduzido entra; o resto sai, nunca fica no original."""
    ORIGINAL = "original"
    """O texto limpo, no idioma do original (para ouvir a limpeza antes de traduzir)."""


@dataclass(frozen=True)
class Pedido:
    lote: str
    segmentos: tuple[Segmento, ...]


@dataclass(frozen=True)
class Traduzido:
    id: str
    texto: str


@dataclass(frozen=True)
class Resposta:
    """O que o agente gravou para o lote de mesmo nome."""

    lote: str
    traduzidos: tuple[Traduzido, ...]


@dataclass(frozen=True)
class TrocaDeIdioma:
    de: str
    para: str

    def trocar(self, valor: str) -> str:
        """`TrocaDeIdioma("en", "pt-BR").trocar("en-US")` → `"pt-BR"`; outra língua fica.

        Trecho marcado com outra língua (`xml:lang="fr"`) é escolha do autor (ADR-0006).
        """
        return self.para if mesmo_idioma(valor, self.de) else valor


def mesmo_idioma(um: str, outro: str) -> bool:
    """Compara a língua sem a região: `en-US` e `en` são a mesma."""
    return _lingua(um) == _lingua(outro)


def _lingua(idioma: str) -> str:
    """`pt_BR`, `pt-BR` e `por` são `pt`."""
    lingua = idioma.strip().replace("_", "-").split("-", maxsplit=1)[0].casefold()
    return _DUAS_LETRAS.get(lingua, lingua)


def idioma_indefinido(idioma: str) -> bool:
    """`und` ou vazio: o PDF importado sem `--idioma`, ou o EPUB sem `dc:language`."""
    return _lingua(idioma) in _INDEFINIDOS


def precisa_traduzir(idioma: str) -> bool:
    """O livro que não está em português é traduzido para pt-BR (ADR-0003).

    O de idioma indefinido monta o texto limpo, como antes do ADR-0006, e o `traduzir` pede
    o idioma (decisão do Mateus, 2026-11-01).
    """
    return not idioma_indefinido(idioma) and not mesmo_idioma(idioma, IDIOMA_DE_SAIDA)


def id_do_lote(capitulo: str, posicao: int) -> str:
    """`id_do_lote("c005", 3)` → `"c005-l003"`. A posição começa em 1."""
    return f"{capitulo}-l{posicao:03d}"


def capitulo_do_lote(lote: str) -> str:
    """`capitulo_do_lote("c005-l003")` → `"c005"`."""
    achado = LOTE.fullmatch(lote)
    return achado.group(1) if achado else ""


def novos_pedidos(
    capitulo: str,
    limpos: Sequence[Segmento],
    pedidos: Sequence[Pedido],
    palavras: int,
    respondidos: Sequence[str] = (),
) -> tuple[Pedido, ...]:
    """Os lotes do que ainda não está em `pedidos`, com até `palavras` palavras cada. A
    numeração continua depois do último lote com pedido ou com resposta (`respondidos`):
    reusar o nome casaria o pedido novo com a resposta velha (achado da code-review)."""
    ja_pedidos = {segmento.id for pedido in pedidos for segmento in pedido.segmentos}
    faltam = [segmento for segmento in limpos if segmento.id not in ja_pedidos]
    ultimo = _ultimo_lote(capitulo, [*(pedido.lote for pedido in pedidos), *respondidos])
    return tuple(
        Pedido(id_do_lote(capitulo, ultimo + posicao), lote)
        for posicao, lote in enumerate(_em_lotes(faltam, palavras), start=1)
    )


def _ultimo_lote(capitulo: str, lotes: Sequence[str]) -> int:
    numeros = (_numero_do_lote(lote) for lote in lotes if capitulo_do_lote(lote) == capitulo)
    return max(numeros, default=0)


def _numero_do_lote(lote: str) -> int:
    achado = LOTE.fullmatch(lote)
    return int(achado.group(2)) if achado else 0


def _em_lotes(segmentos: Sequence[Segmento], palavras: int) -> list[tuple[Segmento, ...]]:
    """Sem partir segmento: o maior que o limite vai sozinho, e o tradutor o recebe inteiro."""
    lotes: list[tuple[Segmento, ...]] = []
    atual: list[Segmento] = []
    contadas = 0
    for segmento in segmentos:
        tamanho = len(segmento.texto.split())
        if atual and contadas + tamanho > palavras:
            lotes.append(tuple(atual))
            atual, contadas = [], 0
        atual.append(segmento)
        contadas += tamanho
    if atual:
        lotes.append(tuple(atual))
    return lotes
