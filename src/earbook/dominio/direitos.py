# SPDX-License-Identifier: GPL-3.0-or-later
"""A página de direitos autorais, que a limpeza tira do áudio (ADR-0003)."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from earbook.dominio.segmento import Papel, Segmento

# Página de direitos autorais (2026-11-01). A marca forte só apareceu, nos quatro livros
# medidos, em página de direitos e boilerplate de editora; a fraca vem em volta dela
# (editora, marca registrada, edição, site) e, sozinha, é texto comum ("a segunda edição").
# O aviso de direitos; com o ISBN, forma a marca forte. Só o aviso abre a corrente de
# vizinhas: o ISBN aparece também em referência bibliográfica, cercada de outras com link (N6).
_AVISO_DE_DIREITOS = r"©|\(c\)\s*(?:19|20)\d\d|all rights reserved|direitos reservados"
_MARCA_FORTE_DE_DIREITOS = re.compile(rf"{_AVISO_DE_DIREITOS}|\bISBN\b", re.IGNORECASE)
_AVISO = re.compile(_AVISO_DE_DIREITOS, re.IGNORECASE)
_MARCAS_FRACAS_DE_DIREITOS = (
    "copyright",
    "direitos autorais",
    "trademarks?",
    "marcas? registradas?",
    "published by",
    "publicad[oa] por",
    r"\beditora\b",
    r"\bpublisher\b",
    "printed in",
    "impresso (?:no|em)",
    "cataloga[çc][ãa]o",
    "cataloging",
    "library of congress",
    "https?://",
    r"www\.",
    r"\bedi[çc][ãa]o\b",
    r"\bedition\b",
)
_MARCA_FRACA_DE_DIREITOS = re.compile("|".join(_MARCAS_FRACAS_DE_DIREITOS), re.IGNORECASE)
# A página de direitos fica nas pontas do livro: nos quatro livros, a marca forte apareceu a
# até 5% do começo ou na contracapa. No meio do livro, "© Oracle" é texto (revisão).
PONTA_DO_LIVRO = 0.10
PONTA_MINIMA = 20
# A página de direitos real tem até 3 linhas sem marca forte de cada lado da âncora (Tides);
# o limite segura a corrente que entraria numa lista de links (A1 da auditoria).
VIZINHAS_MAXIMAS = 5
# A corrente não leva a dedicatória, que pode vir ao lado do aviso ou da linha da edição.
_ABERTURAS_DE_DEDICATORIA = (
    "para",
    "to",
    "for",
    "ao",
    "aos",
    "à",
    "às",
    "a minha",
    r"dedic\w*",
    "this (?:book|one) is (?:dedicated|for)",
    r"em (?:\w+ )?memória",
    "in (?:loving )?memory",
)
_DEDICATORIA = re.compile(rf"^(?:{'|'.join(_ABERTURAS_DE_DEDICATORIA)})\b", re.IGNORECASE)
MOTIVO_DA_PAGINA_DE_DIREITOS = "página de direitos autorais"
MOTIVO_DA_VIZINHA_DE_DIREITOS = "página de direitos autorais: linha vizinha"


def nas_pontas(total: int) -> Callable[[int], bool]:
    """Se a posição `i` (no livro inteiro, de `total` segmentos) está numa das pontas."""
    ponta = max(PONTA_MINIMA, int(total * PONTA_DO_LIVRO))
    return lambda i: i < ponta or i >= total - ponta


def pagina_de_direitos(
    segmentos: Sequence[Segmento], na_ponta: Callable[[int], bool]
) -> dict[int, str]:
    """Posição → motivo dos segmentos da página de direitos do capítulo.

    `na_ponta(i)` diz se a posição `i` do capítulo está numa das pontas do livro: só ali a
    marca forte abre página de direitos, e só ali a corrente de vizinhas anda (A1 da
    auditoria).
    """
    fortes = [i for i, s in enumerate(segmentos) if na_ponta(i) and _forte(s.texto)]
    saem = dict.fromkeys(fortes, MOTIVO_DA_PAGINA_DE_DIREITOS)
    for i in (i for i in fortes if _AVISO.search(segmentos[i].texto)):
        for passo in (-1, 1):
            for j in _vizinhas_de_direitos(segmentos, i, passo, na_ponta):
                _ = saem.setdefault(j, MOTIVO_DA_VIZINHA_DE_DIREITOS)
    return saem


def _vizinhas_de_direitos(
    segmentos: Sequence[Segmento], inicio: int, passo: int, na_ponta: Callable[[int], bool]
) -> list[int]:
    """As linhas seguidas com marca, a partir de `inicio`, no sentido de `passo`, até
    `VIZINHAS_MAXIMAS` linhas sem marca forte.

    Atravessa uma linha sem marca quando a seguinte tem ("Visit us on the World Wide Web:",
    antes da URL). Nunca leva título nem dedicatória.
    """

    def pode_sair(j: int) -> bool:
        if not 0 <= j < len(segmentos) or not na_ponta(j):
            return False
        segmento = segmentos[j]
        return segmento.papel is not Papel.TITULO and not _DEDICATORIA.match(segmento.texto)

    def marcada(j: int) -> bool:
        texto = segmentos[j].texto if pode_sair(j) else ""
        return _forte(texto) or bool(_MARCA_FRACA_DE_DIREITOS.search(texto))

    vizinhas: list[int] = []
    j = inicio + passo
    while True:
        passos = (
            [j] if marcada(j) else [j, j + passo] if pode_sair(j) and marcada(j + passo) else []
        )
        # O limite conta o passo inteiro: a travessia leva duas linhas de uma vez (N3).
        fracas = sum(not _forte(segmentos[k].texto) for k in [*vizinhas, *passos])
        if not passos or fracas > VIZINHAS_MAXIMAS:
            return vizinhas
        vizinhas += passos
        j = passos[-1] + passo


def _forte(texto: str) -> bool:
    return bool(_MARCA_FORTE_DE_DIREITOS.search(texto))
