# SPDX-License-Identifier: GPL-3.0-or-later
"""O tipo de cada linha do PDF pela fonte, e as medidas do livro que o decidem (ADR-0004).

Título é fonte de 1,2 vez o corpo ou mais, ou linha toda em negrito do tamanho do corpo para cima
(subtítulo do Competente), menos no livro em que o negrito é prosa (o Kafka à beira-mar), onde só
a linha em negrito toda em maiúsculas é título (ADR-0004, "Prosa em negrito do tamanho do
corpo"); código é linha toda monoespaçada; nota é fonte menor que 0,85 do corpo. Saiu de
`blocos.py` para ele caber nas 400 linhas do ADR-0001.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from itertools import pairwise
from statistics import median

from earbook.dominio.pagina import (
    RAZAO_DO_TITULO,
    Linha,
    Pagina,
    corpo_em_negrito,
    so_maiusculas,
    tamanho_do_corpo,
)

RAZAO_DA_NOTA = 0.85
# O subtítulo em negrito vai do corpo para cima, com esta folga: o cabeçalho de tabela do Hard
# Parts tem 10 pt, com corpo de 10,5; o cabeçalho de tabela menor e o rodapé de seção, 9 pt
# (ADR-0004).
FOLGA_DO_SUBTITULO = 0.5
# A prosa em negrito do tamanho do corpo (ADR-0004, "Prosa em negrito do tamanho do corpo"): no
# livro em que a linha em negrito tem a medida da linha comum, o negrito é ênfase de trechos
# inteiros, e não subtítulo. Medido, a mediana de letras da linha em negrito contra a da linha
# comum: Kafka à beira-mar 1,06 (a voz do Corvo, o interrogador, a segunda pessoa); Hard Parts
# 0,15 (subtítulo, cabeçalho de tabela).
RAZAO_DA_PROSA_EM_NEGRITO = 0.8
# A manchete e o rótulo do relatório não fecham frase; a fala gritada ("— NÃO!") e a última linha
# curta de um trecho em negrito ("EUA."), sim (code-review).
_FECHA_FRASE = re.compile(r"[.!?\u2026][\u201d\u2019\"')]*$")


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
    """O corpo não é negrito, nem a prosa: só então a linha toda em negrito é subtítulo."""
    maiusculas_destacam: bool
    """O corpo não é negrito: a linha toda em negrito e em maiúsculas é título mesmo no livro de
    prosa em negrito (a manchete do Kafka; ADR-0004, "Prosa em negrito do tamanho do corpo")."""


def tipo_da_linha(linha: Linha, medidas: Medidas) -> TipoDeBloco:
    corpo = medidas.corpo
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
    if linha.negrito and linha.tamanho >= corpo - FOLGA_DO_SUBTITULO and _destaca(linha, medidas):
        return TipoDeBloco.TITULO
    return TipoDeBloco.PARAGRAFO


def medir(paginas: Sequence[Pagina]) -> Medidas:
    """O corpo, a entrelinha mais comum entre linhas de corpo seguidas da mesma página e o que o
    negrito do tamanho do corpo destaca: o corpo em negrito não destaca nada, e a prosa em negrito,
    só a linha em maiúsculas (ADR-0004)."""
    corpo = tamanho_do_corpo(paginas)
    maiusculas = not corpo_em_negrito(paginas, corpo)
    destaca = maiusculas and not negrito_em_prosa(paginas, corpo)
    sem_entrelinha = Medidas(corpo, 0.0, negrito_destaca=destaca, maiusculas_destacam=maiusculas)
    distancias: Counter[float] = Counter()
    for pagina in paginas:
        corpo_da_pagina = sorted(
            (
                linha
                for linha in pagina.linhas
                if tipo_da_linha(linha, sem_entrelinha) is TipoDeBloco.PARAGRAFO
            ),
            key=lambda linha: linha.topo,
        )
        for de_cima, de_baixo in pairwise(corpo_da_pagina):
            distancia = round(de_baixo.topo - de_cima.topo, 3)
            if distancia > 0:
                distancias[distancia] += 1
    entrelinha = distancias.most_common(1)[0][0] if distancias else 0.0
    return replace(sem_entrelinha, entrelinha=entrelinha)


def _destaca(linha: Linha, medidas: Medidas) -> bool:
    """A linha toda em negrito é título: em todo livro de corpo regular e de negrito curto, e, no
    de prosa em negrito, só a em maiúsculas que não fecha frase."""
    texto = linha.texto
    em_maiusculas = so_maiusculas(texto) and any(letra.isalpha() for letra in texto)
    manchete = em_maiusculas and _FECHA_FRASE.search(texto) is None
    return medidas.negrito_destaca or (medidas.maiusculas_destacam and manchete)


def negrito_em_prosa(paginas: Sequence[Pagina], corpo: float) -> bool:
    """Se a linha toda em negrito da faixa do subtítulo tem, na mediana, a medida da linha comum
    do corpo: aí o negrito é prosa, e não destaca subtítulo nenhum, como no livro de corpo em
    negrito (ADR-0004, "Prosa em negrito do tamanho do corpo")."""
    negrito: list[int] = []
    comum: list[int] = []
    for pagina in paginas:
        for linha in pagina.linhas:
            if _na_faixa_do_subtitulo(linha, corpo):
                negrito.append(len(linha.texto))
            elif round(linha.tamanho, 1) == corpo and not linha.negrito:
                comum.append(len(linha.texto))
    if not negrito or not comum:
        return False
    return median(negrito) >= median(comum) * RAZAO_DA_PROSA_EM_NEGRITO


def _na_faixa_do_subtitulo(linha: Linha, corpo: float) -> bool:
    """A linha que o `tipo_da_linha` faria título só por ser toda negrito."""
    return (
        linha.negrito
        and not linha.monoespacada
        and not linha.versalete
        and corpo - FOLGA_DO_SUBTITULO <= linha.tamanho < corpo * RAZAO_DO_TITULO
    )
