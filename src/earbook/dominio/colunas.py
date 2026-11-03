# SPDX-License-Identifier: GPL-3.0-or-later
"""A ordem de leitura da página do PDF: coluna por coluna, não linha a linha (ADR-0004).

O pdfminer entrega soltas as linhas da página. Juntar tudo o que está na mesma altura serve à
linha justificada partida em pedaços e à linha de tabela, mas, na página em duas colunas
(Dalgalarrondo), intercalava as colunas: "o problema essas experiências são basicamenda
classificação…". A coluna é achada pela calha: um x que nenhuma linha atravessa, com texto dos
dois lados (ADR-0004, "Duas colunas").
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum
from itertools import pairwise
from statistics import median

from earbook.dominio.pagina import HIFENS_DA_QUEBRA, Linha, comeca_em_minuscula

# Linhas a menos disso de topo estão na mesma altura (células de tabela no Hard Parts: 0,001).
MESMA_ALTURA = 0.004
CALHA_MINIMA = 10.0
"""Em pontos, do fim da linha da esquerda ao começo da da direita. Medido: o vão das colunas vai
de 16 a 40 pt; o da linha justificada partida fica abaixo de 10."""
LINHAS_POR_COLUNA = 3
LARGURA_DA_COLUNA = 0.3
"""Fração da largura da faixa que cada coluna ocupa, no mínimo. Medido: na linha do tempo do
Competente (p. 377 a 380), o lado estreito (data ou capítulo) fica entre 6% e 27%, e é célula de
tabela; as colunas de texto do Dalgalarrondo e do índice do Hard Parts, perto de 45%."""
CONTINUIDADE = 0.4
"""Fração das linhas seguidas de um lado em que a de baixo continua a de cima. Medido: das 758
faixas aceitas no Dalgalarrondo, 58 ficam entre 0,4 e 0,6 (glossário, listas, quadros), e no
Hard Parts, 3 de 21 (p. 412, 455 e 459); a tabela de célula curta fica em 0, e a bibliografia,
entre 0,33 e 0,4. Com 0,3, a tabela da p. 144 do Competente seria lida coluna a coluna."""
INICIOS_MAXIMOS = 200
"""Começos de linha diferentes acima dos quais a página não é de texto em colunas e vai como
antes, por altura. A busca da calha custa um passe pela página por começo, e o PDF é entrada não
confiável: 1.600 linhas em x distintos levavam 2,4 s (code-review). Medido: a página com mais
começos tem 97 (Dalgalarrondo p. 302, uma tabela); o índice do Hard Parts, 75. Juntar os
começos por ponto inteiro baixava a conta para 44, mas tirava as colunas de 9 páginas do
Dalgalarrondo (glossário e bibliografia), onde a calha meio ponto à direita parte a faixa."""
VAO_DA_FAIXA = 2.5
"""Em entrelinhas. Medido no Dalgalarrondo: o parágrafo novo abre 2 entrelinhas; o quadro e a
epígrafe, de 4,5 a 5,6 (p. 30 e 31)."""


class _Lado(Enum):
    ESQUERDA = "esquerda"
    DIREITA = "direita"
    ATRAVESSA = "atravessa"


@dataclass(frozen=True)
class _Faixa:
    """Linhas seguidas da página, de cima para baixo, separadas pela calha."""

    esquerda: tuple[Linha, ...] = ()
    direita: tuple[Linha, ...] = ()
    atravessa: tuple[Linha, ...] = ()
    """A linha que atravessa a calha (título, quadro de largura cheia) fica numa faixa só dela."""
    colunas: bool = False
    """Os dois lados são colunas de texto: a da esquerda é lida inteira antes da da direita."""


def linhas_visuais(linhas: Sequence[Linha]) -> list[tuple[Linha, int]]:
    """As linhas na ordem de leitura, com os pedaços da mesma altura juntos numa linha só.

    O pdfminer parte linha justificada ("…communication patterns" e "in", Hard Parts p. 60)
    e devolve cada célula de tabela como linha própria. O número de pedaços vai junto: com
    3 ou mais, é linha de tabela. Na página em colunas, cada coluna vem inteira, uma depois
    da outra.
    """
    return [_juntar(altura) for altura in _em_ordem(linhas)]


def _em_ordem(linhas: Sequence[Linha]) -> list[list[Linha]]:
    """As alturas da página na ordem de leitura; a coluna da esquerda antes da da direita."""
    ordenadas = sorted(linhas, key=lambda linha: linha.topo)
    faixas = _melhor_divisao(ordenadas)
    if faixas is None:
        return _por_altura(linhas)
    ordem: list[list[Linha]] = []
    soltas: list[Linha] = []
    for faixa in faixas:
        if faixa.colunas:
            colunas = _em_ordem(_na_margem(faixa.esquerda)) + _em_ordem(_na_margem(faixa.direita))
            ordem += _por_altura(soltas) + colunas
            soltas = []
        else:
            soltas += [*faixa.esquerda, *faixa.direita, *faixa.atravessa]
    return ordem + _por_altura(soltas)


def _melhor_divisao(ordenadas: list[Linha]) -> list[_Faixa] | None:
    """As faixas da calha que põe mais linhas em colunas; None se nenhuma põe."""
    inicios = sorted({linha.x for linha in ordenadas})
    if len(inicios) > INICIOS_MAXIMOS:
        return None
    limite = VAO_DA_FAIXA * _entrelinha(ordenadas)
    melhor: tuple[int, list[_Faixa]] | None = None
    for calha in inicios:
        faixas = _faixas(ordenadas, calha, limite)
        em_colunas = sum(len(f.esquerda) + len(f.direita) for f in faixas if f.colunas)
        if em_colunas and (melhor is None or em_colunas > melhor[0]):
            melhor = (em_colunas, faixas)
    return None if melhor is None else melhor[1]


def _entrelinha(ordenadas: list[Linha]) -> float:
    """A distância típica entre alturas seguidas; infinita quando há uma altura só."""
    distancias = [
        de_baixo.topo - de_cima.topo
        for de_cima, de_baixo in pairwise(ordenadas)
        if de_baixo.topo - de_cima.topo >= MESMA_ALTURA
    ]
    return median(distancias) if distancias else math.inf


def _faixas(ordenadas: list[Linha], calha: float, limite: float) -> list[_Faixa]:
    """Corta a página, de cima para baixo, na linha que atravessa a calha e no vão que fecha
    as colunas."""
    lados = _lados(ordenadas, calha)
    faixas: list[_Faixa] = []
    esquerda: list[Linha] = []
    direita: list[Linha] = []
    for posicao, (linha, lado) in enumerate(zip(ordenadas, lados, strict=True)):
        corta = lado is _Lado.ATRAVESSA or _fecha_as_colunas(ordenadas, lados, posicao, limite)
        if corta and (esquerda or direita):
            faixas.append(_faixa(esquerda, direita))
            esquerda, direita = [], []
        if lado is _Lado.ATRAVESSA:
            faixas.append(_Faixa(atravessa=(linha,)))
        else:
            (esquerda if lado is _Lado.ESQUERDA else direita).append(linha)
    return [*faixas, _faixa(esquerda, direita)] if esquerda or direita else faixas


def _faixa(esquerda: list[Linha], direita: list[Linha]) -> _Faixa:
    return _Faixa(tuple(esquerda), tuple(direita), colunas=_duas_colunas(esquerda, direita))


def _lados(ordenadas: list[Linha], calha: float) -> list[_Lado]:
    """O lado da calha de cada linha, altura por altura."""
    lados: list[_Lado] = []
    for altura in _por_altura(ordenadas):
        lados += _lados_da_altura(altura, calha)
    return lados


def _lados_da_altura(altura: list[Linha], calha: float) -> list[_Lado]:
    """O pedaço colado a uma linha que atravessa a calha atravessa com ela: é a mesma linha,
    partida pelo pdfminer (code-review). Colado é a menos de uma calha: o título da coluna da
    direita que cobre a calha dos itens não leva a linha da coluna da esquerda na mesma altura,
    17 pt antes dele (Dalgalarrondo p. 308)."""
    lados = [_lado(linha, calha) for linha in altura]
    pela_esquerda = sorted(range(len(altura)), key=lambda posicao: altura[posicao].x)
    for passe in (pela_esquerda, pela_esquerda[::-1]):
        for de, para in pairwise(passe):
            if lados[de] is _Lado.ATRAVESSA and _colados(altura[de], altura[para]):
                lados[para] = _Lado.ATRAVESSA
    return lados


def _colados(uma: Linha, outra: Linha) -> bool:
    antes, depois = sorted((uma, outra), key=lambda linha: linha.x)
    return depois.x - antes.fim < CALHA_MINIMA


def _lado(linha: Linha, calha: float) -> _Lado:
    if linha.fim <= calha - CALHA_MINIMA:
        return _Lado.ESQUERDA
    return _Lado.DIREITA if linha.x >= calha else _Lado.ATRAVESSA


def _fecha_as_colunas(
    ordenadas: list[Linha], lados: list[_Lado], posicao: int, limite: float
) -> bool:
    """O vão de mais de 2,5 entrelinhas antes da linha `posicao` fecha as colunas: "Questões de
    revisão" vem depois delas (Dalgalarrondo p. 30 e 343), e a epígrafe, antes (p. 31).

    A não ser que uma coluna só passe por ele: a outra já acabou mais acima, e a mesma coluna
    continua embaixo com texto, 3 linhas ou mais. Aí o vão é subtítulo ou quadro dela, e o
    resto da coluna segue nela, antes da outra (code-review).
    """
    if posicao == 0:
        return False
    de_cima, de_baixo = ordenadas[posicao - 1].topo, ordenadas[posicao].topo
    if de_baixo - de_cima <= limite:
        return False
    acima = _lados_entre(ordenadas, lados, de_cima - limite, de_cima)
    return len(acima) != 1 or not _continua_so(lados[posicao:], acima.pop())


def _continua_so(lados_abaixo: list[_Lado], lado: _Lado) -> bool:
    """As primeiras linhas abaixo do vão são 3 ou mais do mesmo `lado`, sem nada da outra
    coluna nem linha que atravessa."""
    seguidas = 0
    for outro in lados_abaixo:
        if outro is not lado:
            break
        seguidas += 1
    return seguidas >= LINHAS_POR_COLUNA


def _lados_entre(ordenadas: list[Linha], lados: list[_Lado], alto: float, pe: float) -> set[_Lado]:
    """Os lados da calha que têm linha com o topo entre `alto` e `pe`."""
    return {lado for linha, lado in zip(ordenadas, lados, strict=True) if alto <= linha.topo <= pe}


def _duas_colunas(esquerda: list[Linha], direita: list[Linha]) -> bool:
    if not esquerda or not direita:
        return False
    largura_da_faixa = _largura(esquerda + direita)
    return all(_coluna(lado, largura_da_faixa) for lado in (esquerda, direita))


def _coluna(lado: list[Linha], largura_da_faixa: float) -> bool:
    """Um lado da calha é coluna de texto: 3 linhas ou mais, largo e corrido."""
    alturas = _por_altura(lado)
    if len(alturas) < LINHAS_POR_COLUNA:
        return False
    return _largura(lado) >= LARGURA_DA_COLUNA * largura_da_faixa and _corrido(alturas)


def _largura(linhas: list[Linha]) -> float:
    return max(linha.fim for linha in linhas) - min(linha.x for linha in linhas)


def _corrido(alturas: list[list[Linha]]) -> bool:
    """Texto corrido, e não célula de tabela: a linha de baixo costuma continuar a de cima."""
    textos = [_texto(altura) for altura in alturas]
    pares = list(pairwise(textos))
    continuam = sum(_continua(de_cima, de_baixo) for de_cima, de_baixo in pares)
    return continuam >= CONTINUIDADE * len(pares)


def _continua(de_cima: str, de_baixo: str) -> bool:
    return de_cima.endswith(HIFENS_DA_QUEBRA) or comeca_em_minuscula(de_baixo)


def _na_margem(coluna: tuple[Linha, ...]) -> tuple[Linha, ...]:
    """A coluna com o x contado da margem dela, o x mais comum das suas linhas.

    O `blocos` compara o recuo com a margem do parágrafo, e a página par e a ímpar têm margens
    diferentes (Dalgalarrondo: 66 e 301, 46 e 245). Contado da borda da página, o parágrafo que
    vira da coluna da direita de uma para a da esquerda da seguinte se partia a cada fim de
    frase. Dentro da página, a virada de coluna é do `blocos` (`_virou_a_coluna`).
    """
    contagem = Counter(round(linha.x) for linha in coluna)
    mais_comum = max(contagem.values())
    margem = min(x for x, vezes in contagem.items() if vezes == mais_comum)
    return tuple(replace(linha, x=linha.x - margem, fim=linha.fim - margem) for linha in coluna)


def _por_altura(linhas: Sequence[Linha]) -> list[list[Linha]]:
    """Agrupa as linhas na mesma altura, de cima para baixo."""
    alturas: list[list[Linha]] = []
    for linha in sorted(linhas, key=lambda linha: linha.topo):
        if alturas and abs(linha.topo - alturas[-1][0].topo) < MESMA_ALTURA:
            alturas[-1].append(linha)
        else:
            alturas.append([linha])
    return alturas


def _texto(altura: list[Linha]) -> str:
    return " ".join(pedaco.texto for pedaco in sorted(altura, key=lambda linha: linha.x))


def _juntar(altura: list[Linha]) -> tuple[Linha, int]:
    # Revisão nº 2: ordenar por (topo, x) punha primeiro o pedaço da direita que ficasse um
    # pouco mais alto (618 vezes no Hard Parts). A ordem dentro da altura é só a do x.
    pedacos = sorted(altura, key=lambda linha: linha.x)
    juntas = replace(
        pedacos[0],
        texto=_texto(pedacos),
        monoespacada=all(pedaco.monoespacada for pedaco in pedacos),
        negrito=all(pedaco.negrito for pedaco in pedacos),
        fim=max(pedaco.fim for pedaco in pedacos),
    )
    return juntas, len(pedacos)
