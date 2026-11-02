# SPDX-License-Identifier: GPL-3.0-or-later
"""Comando `traduzir`: exporta o que falta traduzir e diz onde gravar a resposta (ADR-0006).

O Python nunca chama o LLM (ADR-0001). Quem traduz é o Claude Code, um subagente por
capítulo, com as instruções de `.claude/agents/tradutor.md`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.dominio.glossario import candidatos_a_nome
from earbook.dominio.segmento import Segmento
from earbook.dominio.traducao import (
    PALAVRAS_POR_LOTE,
    Pedido,
    Resposta,
    capitulo_do_lote,
    idioma_indefinido,
    novos_pedidos,
    precisa_traduzir,
)

# ADR-0007: o que a amostra decidiu mora aqui, e não no brief de cada tradutor.
MODELO_DAS_DECISOES = """# Decisões do livro

A sessão escreve, depois da escuta da amostra; todo tradutor lê antes do primeiro lote
(ADR-0007). Seção vazia: vale a regra do `tradutor.md`.

## Nome fora do glossário

## Tom e registro

## Dialeto

## Títulos e caixa

## Tratamento

## Escolhas da amostra
"""


class TraducaoDesnecessariaError(ValueError):
    pass


class IdiomaIndefinidoError(ValueError):
    pass


@dataclass(frozen=True)
class CapituloNaTraducao:
    capitulo: str
    segmentos: int
    traduzidos: int
    pendentes: tuple[str, ...]
    """Os lotes pedidos que ainda não têm resposta."""


@dataclass(frozen=True)
class Exportacao:
    novos: int
    """Lotes pedidos agora; rodar de novo não refaz os que já existem."""
    capitulos: tuple[CapituloNaTraducao, ...]
    candidatos: int
    pedidos: Path
    """A pasta dos pedidos."""
    resposta: Path
    """O modelo do caminho da resposta, com `<lote>` no lugar do nome do lote."""
    glossario: Path
    nomes: Path
    decisoes: Path
    """O arquivo das decisões do livro, que todo tradutor lê (ADR-0007)."""
    palavras_pendentes: Mapping[str, int]
    """Por capítulo, as palavras ainda sem tradução: a conta da divisão e do custo."""


def traduzir(pasta: Path, palavras: int = PALAVRAS_POR_LOTE) -> Exportacao:
    """Grava os pedidos do que ainda não foi pedido e os candidatos a nome próprio. Recusa
    o livro em português, que só é preparado para o ouvido (ADR-0003)."""
    _recusar_idioma(pasta, trabalho.ler_idioma(pasta))
    trabalho.criar_pastas_da_traducao(pasta)
    limpos = {c.id: trabalho.ler_limpos(pasta, c.id) for c in trabalho.ler_capitulos(pasta)}
    pedidos = list(trabalho.ler_pedidos(pasta))
    respostas = trabalho.ler_respostas(pasta)
    novos = _pedir(pasta, limpos, pedidos, [r.lote for r in respostas], palavras)
    candidatos = _gravar_candidatos(pasta, limpos)
    estado = _estado(limpos, [*pedidos, *novos], respostas)
    trabalho.gravar_decisoes_se_faltar(pasta, MODELO_DAS_DECISOES)
    return Exportacao(
        len(novos),
        estado,
        candidatos,
        trabalho.pasta_dos_pedidos(pasta),
        trabalho.caminho_da_resposta(pasta, "<lote>"),
        trabalho.caminho_do_glossario(pasta),
        trabalho.caminho_dos_candidatos(pasta),
        trabalho.caminho_das_decisoes(pasta),
        _palavras_pendentes(limpos, respostas),
    )


def _palavras_pendentes(
    limpos: Mapping[str, Sequence[Segmento]], respostas: Sequence[Resposta]
) -> dict[str, int]:
    traduzidos = {t.id for resposta in respostas for t in resposta.traduzidos}
    return {
        capitulo: sum(len(s.texto.split()) for s in segmentos if s.id not in traduzidos)
        for capitulo, segmentos in limpos.items()
    }


def _gravar_candidatos(pasta: Path, limpos: Mapping[str, Sequence[Segmento]]) -> int:
    glossario = trabalho.ler_glossario(pasta)
    candidatos = candidatos_a_nome((s for lista in limpos.values() for s in lista), glossario)
    trabalho.gravar_candidatos(pasta, candidatos)
    return len(candidatos)


def _recusar_idioma(pasta: Path, idioma: str) -> None:
    if idioma_indefinido(idioma):
        mensagem = (
            f"{pasta}: o idioma do livro é indefinido ({idioma!r}); prepare de novo com o"
            " idioma no EPUB, ou importe o PDF com --idioma"
        )
        raise IdiomaIndefinidoError(mensagem)
    if not precisa_traduzir(idioma):
        mensagem = f"{pasta}: o livro já está em {idioma}; não há o que traduzir"
        raise TraducaoDesnecessariaError(mensagem)


def _pedir(
    pasta: Path,
    limpos: Mapping[str, Sequence[Segmento]],
    pedidos: Sequence[Pedido],
    respondidos: Sequence[str],
    palavras: int,
) -> list[Pedido]:
    novos = [
        pedido
        for capitulo, segmentos in limpos.items()
        for pedido in novos_pedidos(
            capitulo, segmentos, _do_capitulo(pedidos, capitulo), palavras, respondidos
        )
    ]
    for pedido in novos:
        trabalho.gravar_pedido(pasta, pedido)
    return novos


def _do_capitulo(pedidos: Sequence[Pedido], capitulo: str) -> list[Pedido]:
    return [pedido for pedido in pedidos if capitulo_do_lote(pedido.lote) == capitulo]


def _estado(
    limpos: Mapping[str, Sequence[Segmento]],
    pedidos: Sequence[Pedido],
    respostas: Sequence[Resposta],
) -> tuple[CapituloNaTraducao, ...]:
    """Só os capítulos com texto: a capa sem segmento não tem o que traduzir."""
    respondidos = {resposta.lote for resposta in respostas}
    traduzidos = {t.id for resposta in respostas for t in resposta.traduzidos}
    return tuple(
        CapituloNaTraducao(
            capitulo,
            len(segmentos),
            sum(segmento.id in traduzidos for segmento in segmentos),
            tuple(p.lote for p in _do_capitulo(pedidos, capitulo) if p.lote not in respondidos),
        )
        for capitulo, segmentos in limpos.items()
        if segmentos
    )
