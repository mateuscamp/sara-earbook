# SPDX-License-Identifier: GPL-3.0-or-later
"""O texto escondido debaixo de outro, que sai antes dos blocos (ADR-0004, "O que ficou da
Fase 1").

No Dalgalarrondo p. 275, debaixo do Quadro 22.4, ficou o resto de uma abertura de capítulo
antiga: o "24" em 60 pt e "A inteligência e" / "suas alterações" em 22 pt. Na mesma altura de
uma linha do quadro, ele se juntava a ela, o "24" virava título do tamanho do capítulo e abria
um capítulo falso (`c026`); o quadro fechava, e três pedaços dele iam para "Notas".
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from earbook.dominio.colunas import MESMA_ALTURA
from earbook.dominio.pagina import (
    DIFERENCA_DE_TAMANHO,
    RAZAO_DO_TITULO,
    Linha,
    Pagina,
    tamanho_do_corpo,
)
from earbook.dominio.paginacao import LinhaRemovida, PaginasLimpas

MOTIVO_DO_ESCONDIDO = "texto escondido debaixo de outro"
SOBREPOSICAO_MINIMA = 1.0
"""Em pontos, na horizontal. Duas linhas na mesma altura que dividem mais que isso não cabem na
mesma linha da página: uma está desenhada por cima da outra."""


def tirar_texto_escondido(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """Tira a linha em letra de título que, na mesma altura, se sobrepõe na horizontal a uma linha
    de outro tamanho, com uma remoção registrada por linha.

    Medido nos três PDFs: só os 3 da p. 275 do Dalgalarrondo. O texto repetido por cima, do mesmo
    tamanho, fica: é negrito feito à mão ("Conheça também", Dalgalarrondo p. 2; "Beijing", Hard
    Parts p. 5). A letra miúda sobreposta (Hard Parts p. 462, de 0,7 a 3,6 pt) também fica.
    """
    titulo = tamanho_do_corpo(paginas) * RAZAO_DO_TITULO
    limpas: list[Pagina] = []
    remocoes: list[LinhaRemovida] = []
    for pagina in paginas:
        escondidas = _escondidas(pagina.linhas, titulo)
        limpas.append(Pagina(pagina.numero, tuple(_sem(pagina.linhas, escondidas))))
        remocoes += [
            LinhaRemovida(pagina.numero, MOTIVO_DO_ESCONDIDO, linha.texto) for linha in escondidas
        ]
    return PaginasLimpas(tuple(limpas), tuple(remocoes))


def _sem(linhas: Sequence[Linha], escondidas: list[Linha]) -> list[Linha]:
    tiradas = {id(linha) for linha in escondidas}
    return [linha for linha in linhas if id(linha) not in tiradas]


def _escondidas(linhas: Sequence[Linha], titulo: float) -> list[Linha]:
    """As linhas em letra de título (`titulo` pontos ou mais) por cima de outra de outro tamanho,
    na ordem da página.

    Só se comparam as linhas da mesma altura, na ordem do topo: o PDF é entrada não confiável, e
    comparar todos os pares custava 50 milhões de comparações numa página de 10 mil linhas (R1
    da code-review); agora são 0,1 s. Fica quadrático só o que está numa altura só: 2 mil linhas
    na mesma altura levam 0,6 s, e o pdfminer leva mais que isso para montar a página.
    """
    ordenadas = sorted(linhas, key=lambda linha: linha.topo)
    escondidas: set[int] = set()
    for posicao, uma in enumerate(ordenadas):
        for outra in _na_mesma_altura(ordenadas, posicao):
            maior = max(uma, outra, key=lambda linha: linha.tamanho)
            if _sobrepostas(uma, outra) and maior.tamanho >= titulo:
                escondidas.add(id(maior))
    return [linha for linha in linhas if id(linha) in escondidas]


def _na_mesma_altura(ordenadas: Sequence[Linha], posicao: int) -> Iterator[Linha]:
    """As linhas depois de `posicao`, em ordem de topo, enquanto estão na mesma altura dela."""
    topo = ordenadas[posicao].topo
    seguinte = posicao + 1
    while seguinte < len(ordenadas) and ordenadas[seguinte].topo - topo < MESMA_ALTURA:
        yield ordenadas[seguinte]
        seguinte += 1


def _sobrepostas(uma: Linha, outra: Linha) -> bool:
    mesma_altura = abs(uma.topo - outra.topo) < MESMA_ALTURA
    outro_tamanho = abs(uma.tamanho - outra.tamanho) > DIFERENCA_DE_TAMANHO
    em_comum = min(uma.fim, outra.fim) - max(uma.x, outra.x)
    return mesma_altura and outro_tamanho and em_comum > SOBREPOSICAO_MINIMA
