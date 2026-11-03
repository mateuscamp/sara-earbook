# SPDX-License-Identifier: GPL-3.0-or-later
"""O texto escondido debaixo de outro e o texto repetido por cima, que saem antes dos blocos
(ADR-0004, "O que ficou da Fase 1" e "Negrito feito à mão").

No Dalgalarrondo p. 275, debaixo do Quadro 22.4, ficou o resto de uma abertura de capítulo
antiga: o "24" em 60 pt e "A inteligência e" / "suas alterações" em 22 pt. Na mesma altura de
uma linha do quadro, ele se juntava a ela, o "24" virava título do tamanho do capítulo e abria
um capítulo falso (`c026`); o quadro fechava, e três pedaços dele iam para "Notas".

Na p. 2, "Conheça também" (24 pt) está desenhado cinco vezes, deslocado de 0,5 a 1 pt, para
engrossar a letra, e a voz lia "Conheça Conheça Conheça também…".
"""

from __future__ import annotations

import re
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
MOTIVO_DO_REPETIDO = "texto repetido por cima: negrito feito à mão"
SOBREPOSICAO_MINIMA = 1.0
"""Em pontos, na horizontal. Duas linhas na mesma altura que dividem mais que isso não cabem na
mesma linha da página: uma está desenhada por cima da outra."""
COBERTURA_DA_COPIA = 0.9
"""A fração da largura da cópia que a outra linha cobre. Medido: as cópias do Dalgalarrondo (p. 2)
e do Hard Parts (p. 5) estão deslocadas no máximo 1 pt, e a outra cobre mais de 90% delas."""
LETRAS_DA_COPIA = 2
"""O texto vertical do Hard Parts (p. 462) vem uma letra por linha, e o "ll" de "Reilly" são duas
linhas iguais na mesma altura: a cópia de uma letra só fica."""
_LETRA = re.compile(r"[^\W\d_]")


def tirar_texto_escondido(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """Tira a linha em letra de título que, na mesma altura, se sobrepõe na horizontal a uma linha
    de outro tamanho, e a cópia de outra linha do mesmo tamanho, com uma remoção registrada por
    linha.

    Medido nos três PDFs: o texto escondido são só os 3 da p. 275 do Dalgalarrondo; as cópias, as
    8 da p. 2 do Dalgalarrondo ("Conheça também") e as 4 da p. 5 do Hard Parts ("Beijing Boston
    Farnham Sebastopol Tokyo"). A letra miúda sobreposta (Hard Parts p. 462, de 0,7 a 3,6 pt) fica.
    """
    titulo = tamanho_do_corpo(paginas) * RAZAO_DO_TITULO
    limpas: list[Pagina] = []
    remocoes: list[LinhaRemovida] = []
    for pagina in paginas:
        escondidas = _escondidas(pagina.linhas, titulo)
        # A cópia se procura entre as que ficam: a linha escondida desenhada duas vezes sai uma
        # vez só no registro, como escondida (R1 da code-review).
        copias = _copias(_sem(pagina.linhas, escondidas))
        limpas.append(Pagina(pagina.numero, tuple(_sem(pagina.linhas, escondidas + copias))))
        remocoes += _removidas(pagina.numero, MOTIVO_DO_ESCONDIDO, escondidas)
        remocoes += _removidas(pagina.numero, MOTIVO_DO_REPETIDO, copias)
    return PaginasLimpas(tuple(limpas), tuple(remocoes))


def _removidas(numero: int, motivo: str, linhas: list[Linha]) -> list[LinhaRemovida]:
    return [LinhaRemovida(numero, motivo, linha.texto) for linha in linhas]


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


def _copias(linhas: Sequence[Linha]) -> list[Linha]:
    """As linhas desenhadas por cima de outra do mesmo tamanho, que repetem o texto dela ou parte
    dele, na ordem da página. Entre duas iguais, fica a primeira; a que contém as outras ("Conheça
    também", contra "Conheça" e "também") sempre fica.

    Só se comparam as linhas da mesma altura, como em `_escondidas`.
    """
    ordem = {id(linha): posicao for posicao, linha in enumerate(linhas)}
    ordenadas = sorted(linhas, key=lambda linha: linha.topo)
    copias: set[int] = set()
    for posicao, uma in enumerate(ordenadas):
        for outra in _na_mesma_altura(ordenadas, posicao):
            for copia, original in ((uma, outra), (outra, uma)):
                if _copia_de(copia, original, depois=ordem[id(copia)] > ordem[id(original)]):
                    copias.add(id(copia))
    return [linha for linha in linhas if id(linha) in copias]


def _copia_de(copia: Linha, original: Linha, *, depois: bool) -> bool:
    """`copia` repete, no mesmo tamanho, o texto de `original`, que a cobre quase toda. Com o
    mesmo texto, só a que vem `depois` na página é cópia."""
    if abs(copia.tamanho - original.tamanho) > DIFERENCA_DE_TAMANHO:
        return False
    if len(_LETRA.findall(copia.texto)) < LETRAS_DA_COPIA or copia.texto not in original.texto:
        return False
    if copia.texto == original.texto and not depois:
        return False
    largura = copia.fim - copia.x
    em_comum = min(copia.fim, original.fim) - max(copia.x, original.x)
    return largura > 0 and em_comum >= COBERTURA_DA_COPIA * largura
