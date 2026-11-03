# SPDX-License-Identifier: GPL-3.0-or-later
"""O tipo de cada linha do PDF pela fonte, e as medidas do livro que o decidem (ADR-0004).

Título é fonte de 1,2 vez o corpo ou mais, ou linha toda em negrito do tamanho do corpo para cima
(subtítulo do Competente); código é linha toda monoespaçada; nota é fonte menor que 0,85 do
corpo. Saiu de `blocos.py` para ele caber nas 400 linhas do ADR-0001.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise

from earbook.dominio.pagina import (
    RAZAO_DO_TITULO,
    Linha,
    Pagina,
    corpo_em_negrito,
    tamanho_do_corpo,
)

RAZAO_DA_NOTA = 0.85
# O subtítulo em negrito vai do corpo para cima, com esta folga: o cabeçalho de tabela do Hard
# Parts tem 10 pt, com corpo de 10,5; o cabeçalho de tabela menor e o rodapé de seção, 9 pt
# (ADR-0004).
FOLGA_DO_SUBTITULO = 0.5


class TipoDeBloco(StrEnum):
    TITULO = "titulo"
    PARAGRAFO = "paragrafo"
    CODIGO = "codigo"
    NOTA = "nota"


@dataclass(frozen=True)
class Medidas:
    corpo: float
    entrelinha: float
    negrito_destaca: bool
    """O corpo não é negrito: só então a linha toda em negrito é subtítulo."""


def tipo_da_linha(linha: Linha, corpo: float, *, negrito_destaca: bool) -> TipoDeBloco:
    if linha.monoespacada:
        return TipoDeBloco.CODIGO
    # O versalete é subtítulo, mesmo com a maioria das letras em tamanho de nota (ADR-0004,
    # "O que ficou da Fase 1").
    if linha.tamanho >= corpo * RAZAO_DO_TITULO or linha.versalete:
        return TipoDeBloco.TITULO
    if linha.tamanho < corpo * RAZAO_DA_NOTA:
        return TipoDeBloco.NOTA
    # O subtítulo em negrito tem o tamanho do corpo ou mais (Competente: 10,5 e 12 pt, com
    # corpo de 10,5). O negrito menor fica parágrafo: é verbete do glossário (Competente: 9,5
    # pt), que o `_quebra` separa da definição, ou cabeçalho de tabela e rodapé de seção (Hard
    # Parts: 9 pt). ADR-0004, "Subtítulo em negrito do tamanho do corpo", com os limites.
    if negrito_destaca and linha.negrito and linha.tamanho >= corpo - FOLGA_DO_SUBTITULO:
        return TipoDeBloco.TITULO
    return TipoDeBloco.PARAGRAFO


def medir(paginas: Sequence[Pagina]) -> Medidas:
    """O corpo e a entrelinha mais comum entre linhas de corpo seguidas da mesma página."""
    corpo = tamanho_do_corpo(paginas)
    destaca = not corpo_em_negrito(paginas, corpo)
    distancias: Counter[float] = Counter()
    for pagina in paginas:
        corpo_da_pagina = sorted(
            (
                linha
                for linha in pagina.linhas
                if tipo_da_linha(linha, corpo, negrito_destaca=destaca) is TipoDeBloco.PARAGRAFO
            ),
            key=lambda linha: linha.topo,
        )
        for de_cima, de_baixo in pairwise(corpo_da_pagina):
            distancia = round(de_baixo.topo - de_cima.topo, 3)
            if distancia > 0:
                distancias[distancia] += 1
    entrelinha = distancias.most_common(1)[0][0] if distancias else 0.0
    return Medidas(corpo, entrelinha, destaca)
