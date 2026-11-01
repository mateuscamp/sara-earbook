# SPDX-License-Identifier: GPL-3.0-or-later
"""Limpeza para o ouvido (ADR-0003): tira do texto o que o TTS leria e não é do livro."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from ai_book.dominio.segmento import Papel, Segmento

# "Tides of Darkness 4" ou "12 Aaron Rosenberg": frase e número de página, sozinhos na linha.
_FRASE_E_NUMERO = re.compile(r"^(?P<frase>\D.*?)\s+(?P<numero>\d{1,4})$")
_NUMERO_E_FRASE = re.compile(r"^(?P<numero>\d{1,4})\s+(?P<frase>\D.*?)$")
# "Chapter 2" também muda de número, mas é título que o ouvinte quer escutar. Compara a frase
# inteira: por prefixo, "Cap." nunca casava e "Book of Dust" ficava isento (A1 da auditoria).
_ROTULO_DE_CAPITULO = re.compile(
    r"chapter|cap[ií]tulo|cap\.|part|parte|book|livro|section|se[cç][aã]o", re.IGNORECASE
)
# Abaixo disso, a frase casaria com pedaço solto do título ("of", "a").
TAMANHO_MINIMO_DA_FRASE = 3
# Com dois números diferentes ainda pode ser texto do livro; com três, é numeração de página.
NUMEROS_DIFERENTES_MINIMOS = 3


@dataclass(frozen=True)
class Remocao:
    """Um segmento que saiu do áudio, com o motivo, para o `conferir` e para revisão."""

    id: str
    motivo: str
    texto: str


@dataclass(frozen=True)
class Suspeita:
    """Um segmento que parece lixo de página, mas ficou no texto: quem decide é o agente."""

    id: str
    motivo: str
    texto: str


@dataclass(frozen=True)
class CapituloLimpo:
    capitulo: str
    segmentos: tuple[Segmento, ...]


@dataclass(frozen=True)
class LivroLimpo:
    capitulos: tuple[CapituloLimpo, ...]
    remocoes: tuple[Remocao, ...]
    suspeitas: tuple[Suspeita, ...] = ()


def tirar_cabecalhos_de_pagina(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]],
    titulo: str,
    autor: str,
) -> LivroLimpo:
    """Tira os parágrafos que são cabeçalho corrente com número de página.

    A repetição se conta no livro inteiro, porque o cabeçalho atravessa capítulos. Só sai a
    frase que está no título ou no autor do OPF; a que se repete sem estar lá ("Dia 1",
    "Dia 2", "Dia 3" num diário) fica no texto como suspeita, para o agente decidir (H1 da
    auditoria). `tirar_cabecalhos_de_pagina([("c001", segmentos)], titulo, autor)`.
    """
    repetidas = _frases_de_cabecalho([s for _, segmentos in capitulos for s in segmentos])
    do_livro = {f for f in repetidas if _esta_no_titulo_ou_no_autor(f, titulo, autor)}
    limpos: list[CapituloLimpo] = []
    remocoes: list[Remocao] = []
    suspeitas: list[Suspeita] = []
    for capitulo, segmentos in capitulos:
        mantidos: list[Segmento] = []
        for segmento in segmentos:
            frase = _frase_repetida(segmento, repetidas)
            if frase is not None and frase.casefold() in do_livro:
                motivo = f"cabeçalho de página {frase!r}"
                remocoes.append(Remocao(segmento.id, motivo, segmento.texto))
                continue
            if frase is not None:
                motivo = f"possível cabeçalho de página {frase!r}: não está no título nem no autor"
                suspeitas.append(Suspeita(segmento.id, motivo, segmento.texto))
            mantidos.append(segmento)
        limpos.append(CapituloLimpo(capitulo, tuple(mantidos)))
    return LivroLimpo(tuple(limpos), tuple(remocoes), tuple(suspeitas))


def _esta_no_titulo_ou_no_autor(frase: str, titulo: str, autor: str) -> bool:
    """`frase` em casefold, como palavras inteiras: "Dark" não está em "Tides of Darkness"."""
    if len(frase) < TAMANHO_MINIMO_DA_FRASE:
        return False
    palavras = re.compile(rf"(?<!\w){re.escape(frase)}(?!\w)")
    return any(palavras.search(texto.casefold()) for texto in (titulo, autor))


def _frase_repetida(segmento: Segmento, repetidas: set[str]) -> str | None:
    cabecalho = _cabecalho(segmento)
    if cabecalho is None or cabecalho[0].casefold() not in repetidas:
        return None
    return cabecalho[0]


def _cabecalho(segmento: Segmento) -> tuple[str, str] | None:
    """(frase, número) de um parágrafo com cara de cabeçalho; None para o resto."""
    if segmento.papel is not Papel.PARAGRAFO:
        return None
    achado = _FRASE_E_NUMERO.match(segmento.texto) or _NUMERO_E_FRASE.match(segmento.texto)
    if achado is None or _ROTULO_DE_CAPITULO.fullmatch(achado["frase"]):
        return None
    return achado["frase"], achado["numero"]


def _frases_de_cabecalho(segmentos: Sequence[Segmento]) -> set[str]:
    """Frases, em casefold, que aparecem com pelo menos três números de página diferentes."""
    numeros: defaultdict[str, set[str]] = defaultdict(set)
    for segmento in segmentos:
        cabecalho = _cabecalho(segmento)
        if cabecalho is not None:
            numeros[cabecalho[0].casefold()].add(cabecalho[1])
    return {f for f, nums in numeros.items() if len(nums) >= NUMEROS_DIFERENTES_MINIMOS}
