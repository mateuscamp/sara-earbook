# SPDX-License-Identifier: GPL-3.0-or-later
"""Cabeçalho de página: frase do título ou do autor com número de página, repetida no livro
(ADR-0003). Saiu de `limpeza.py`, que passava das 390 linhas (lote B do ADR-0008).
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence

from earbook.dominio.segmento import Papel, Segmento

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


def frases_do_cabecalho(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]], titulo: str, autor: str
) -> set[str]:
    """As frases de cabeçalho do livro: repetidas com três números de página ou mais e no título
    ou no autor. O cabeçalho colado no fim do parágrafo é procurado só com elas."""
    repetidas = frases_de_cabecalho([s for _, segmentos in capitulos for s in segmentos])
    return frases_do_livro(repetidas, titulo, autor)


def frases_do_livro(repetidas: set[str], titulo: str, autor: str) -> set[str]:
    """As frases repetidas que estão no título ou no autor: essas saem do áudio (H1)."""
    return {f for f in repetidas if _esta_no_titulo_ou_no_autor(f, titulo, autor)}


def _esta_no_titulo_ou_no_autor(frase: str, titulo: str, autor: str) -> bool:
    """`frase` em casefold, como palavras inteiras: "Dark" não está em "Tides of Darkness"."""
    if len(frase) < TAMANHO_MINIMO_DA_FRASE:
        return False
    palavras = re.compile(rf"(?<!\w){re.escape(frase)}(?!\w)")
    return any(palavras.search(texto.casefold()) for texto in (titulo, autor))


def frase_repetida(segmento: Segmento, repetidas: set[str]) -> str | None:
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


def frases_de_cabecalho(segmentos: Sequence[Segmento]) -> set[str]:
    """Frases, em casefold, que aparecem com pelo menos três números de página diferentes."""
    numeros: defaultdict[str, set[str]] = defaultdict(set)
    for segmento in segmentos:
        cabecalho = _cabecalho(segmento)
        if cabecalho is not None:
            numeros[cabecalho[0].casefold()].add(cabecalho[1])
    return {f for f, nums in numeros.items() if len(nums) >= NUMEROS_DIFERENTES_MINIMOS}
