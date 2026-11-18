# SPDX-License-Identifier: GPL-3.0-or-later
"""O título da coluna da esquerda que abre uma faixa da largura da página (ADR-0004, "Título que
atravessa as colunas").

Practical p. 203: "Summary" e "Key Points" ficam só na coluna da esquerda, mas abrem uma faixa
nova, da largura da página. Lida coluna a coluna, a página punha os pontos-chave da esquerda no
meio da prosa ("…redirect care" | "• Management of chronic pain…" | … | "temporarily to another
member…"). Três sinais juntos dizem que o título atravessa: a coluna da direita tem um vão na
altura dele, com texto acima e abaixo; a frase da esquerda logo acima dele não acabou, e a da
direita logo acima do vão acabou; e o bloco da direita que termina no vão começa continuando a
frase da esquerda. Saiu de `colunas.py` para ele caber nas 400 linhas do ADR-0001.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from itertools import pairwise
from statistics import median

from earbook.dominio.pagina import (
    HIFENS_DA_QUEBRA,
    RAZAO_DO_TITULO,
    Linha,
    comeca_em_minuscula,
)

VAO_DO_TITULO = 1.5
"""Em entrelinhas da coluna: a linha da direita mais perto que isto do título o põe dentro da
coluna dele. E a linha de título a até isto da de cima é a mesma: o título de duas linhas ("The
Impact of Pharmacogenomic Research" | "on Clinical Medicine") atravessa inteiro ou fica inteiro.
No Miller, julgada linha a linha, a regra partia "BLOQUEOS ILIOINGUINAL" | "E ILIOHIPOGÁSTRICO"."""
VAO_DO_BLOCO = 2.5
"""Em entrelinhas: o vão que separa o bloco da direita que termina no vão do título do bloco de
cima (o `VAO_DA_FAIXA` do `colunas`)."""
MESMA_ALTURA = 0.004
_FECHA_A_FRASE = re.compile(r"[.!?:][\u201d\u2019\"')]*$")


def titulos_que_atravessam(
    ordenadas: Sequence[Linha], esquerda: Sequence[int], direita: Sequence[int], corpo: float
) -> set[int]:
    """As posições, em `ordenadas` (de cima para baixo), dos títulos da coluna da esquerda que
    atravessam a página. `esquerda` e `direita` são as posições de cada coluna, em ordem."""
    entrelinha = _entrelinha_das_colunas(ordenadas, esquerda, direita)
    if entrelinha is None:
        return set()
    atravessam: set[int] = set()
    for titulo in _titulos(ordenadas, esquerda, corpo, entrelinha):
        if _atravessa(ordenadas, titulo, esquerda, direita, entrelinha):
            atravessam |= set(titulo)
    return atravessam


def _entrelinha_das_colunas(
    ordenadas: Sequence[Linha], esquerda: Sequence[int], direita: Sequence[int]
) -> float | None:
    """A distância típica entre linhas seguidas da mesma coluna. A da página, com as duas colunas
    misturadas, dá a metade dela (`colunas._entrelinha`)."""
    distancias: list[float] = []
    for coluna in (esquerda, direita):
        topos = sorted({ordenadas[k].topo for k in coluna})
        distancias += [b - a for a, b in pairwise(topos) if b - a >= MESMA_ALTURA]
    return median(distancias) if distancias else None


def _titulos(
    ordenadas: Sequence[Linha], esquerda: Sequence[int], corpo: float, entrelinha: float
) -> list[list[int]]:
    """As linhas de título da coluna da esquerda, juntas quando seguidas."""
    titulos: list[list[int]] = []
    anterior: int | None = None
    for k in esquerda:
        if ordenadas[k].tamanho < corpo * RAZAO_DO_TITULO:
            anterior = None
            continue
        vao = None if anterior is None else ordenadas[k].topo - ordenadas[anterior].topo
        if vao is not None and vao <= VAO_DO_TITULO * entrelinha:
            titulos[-1].append(k)
        else:
            titulos.append([k])
        anterior = k
    return titulos


def _atravessa(
    ordenadas: Sequence[Linha],
    titulo: list[int],
    esquerda: Sequence[int],
    direita: Sequence[int],
    entrelinha: float,
) -> bool:
    alto, pe = ordenadas[titulo[0]].topo, ordenadas[titulo[-1]].topo
    folga = VAO_DO_TITULO * entrelinha
    da_direita = [ordenadas[k] for k in direita]
    if any(alto - folga <= linha.topo <= pe + folga for linha in da_direita):
        return False
    acima = [linha for linha in da_direita if linha.topo < alto]
    abaixo = [linha for linha in da_direita if linha.topo > pe]
    da_esquerda = [ordenadas[k] for k in esquerda if k < titulo[0]]
    if not acima or not abaixo or not da_esquerda:
        return False
    if _fecha(da_esquerda[-1]) or not _fecha(acima[-1]):
        return False
    return _continua(da_esquerda[-1], _inicio_do_bloco(acima, entrelinha))


def _inicio_do_bloco(acima: list[Linha], entrelinha: float) -> Linha:
    """A primeira linha do bloco da direita que termina logo acima do vão."""
    inicio = acima[-1]
    for linha in reversed(acima[:-1]):
        if inicio.topo - linha.topo > VAO_DO_BLOCO * entrelinha:
            break
        inicio = linha
    return inicio


def _fecha(linha: Linha) -> bool:
    return _FECHA_A_FRASE.search(linha.texto.rstrip()) is not None


def _continua(de_cima: Linha, de_baixo: Linha) -> bool:
    return de_cima.texto.endswith(HIFENS_DA_QUEBRA) or comeca_em_minuscula(de_baixo.texto)
