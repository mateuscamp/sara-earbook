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

from earbook.dominio.lados_da_calha import (
    LINHAS_POR_COLUNA,
    MESMA_ALTURA,
    Regua,
    duas_colunas,
    por_altura,
    texto_da_altura,
)
from earbook.dominio.pagina import Linha
from earbook.dominio.titulo_que_atravessa import titulos_que_atravessam

CALHA_MINIMA = 10.0
"""Em pontos, do fim da linha da esquerda ao começo da da direita. Medido: o vão das colunas vai
de 16 a 40 pt; o da linha justificada partida fica abaixo de 10."""
INICIOS_MAXIMOS = 200
"""Começos de linha diferentes acima dos quais a página não é de texto em colunas e vai como
antes, por altura. A busca da calha custa um passe pela página por começo, e o PDF é entrada não
confiável: 1.600 linhas em x distintos levavam 2,4 s (code-review). Medido: a página com mais
começos tem 97 (Dalgalarrondo p. 302, uma tabela); o índice do Hard Parts, 75. Juntar os
começos por ponto inteiro baixava a conta para 44, mas tirava as colunas de 9 páginas do
Dalgalarrondo (glossário e bibliografia), onde a calha meio ponto à direita parte a faixa."""
LINHAS_ADIANTE = 40
"""Quantas linhas, na ordem da altura, a entrelinha procura a de baixo da mesma coluna. Medido no
Miller: em 99,996% das linhas ela está até 40 adiante (91% a 2, nas colunas desalinhadas). Sem
o limite, a página de 200 começos e 6.400 linhas, toda de células que não se sobrepõem, custava
0,4 s a mais."""
VAO_DA_TABELA = 1.35
"""Em entrelinhas: o vão do parágrafo (o `RAZAO_DO_ESPACO` do `blocos`). Antes da primeira linha
do corpo, depois da tabela de letra menor dos dois lados, ele já fecha as colunas (p. 324)."""


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


def linhas_visuais(linhas: Sequence[Linha], corpo: float) -> list[tuple[Linha, int]]:
    """As linhas na ordem de leitura, com os pedaços da mesma altura juntos numa linha só.

    O pdfminer parte linha justificada ("…communication patterns" e "in", Hard Parts p. 60)
    e devolve cada célula de tabela como linha própria. O número de pedaços vai junto: com
    3 ou mais, é linha de tabela. Na página em colunas, cada coluna vem inteira, uma depois
    da outra.
    """
    return [_juntar(altura) for altura in _em_ordem(linhas, corpo)]


def _em_ordem(linhas: Sequence[Linha], corpo: float) -> list[list[Linha]]:
    """As alturas da página na ordem de leitura; a coluna da esquerda antes da da direita."""
    ordenadas = sorted(linhas, key=lambda linha: linha.topo)
    faixas = _melhor_divisao(ordenadas, corpo)
    if faixas is None:
        return por_altura(linhas)
    ordem: list[list[Linha]] = []
    soltas: list[Linha] = []
    for faixa in faixas:
        if faixa.colunas:
            esquerda, direita = _na_margem(faixa.esquerda), _na_margem(faixa.direita)
            colunas = _em_ordem(esquerda, corpo) + _em_ordem(direita, corpo)
            ordem += por_altura(soltas) + colunas
            soltas = []
        else:
            soltas += [*faixa.esquerda, *faixa.direita, *faixa.atravessa]
    return ordem + por_altura(soltas)


def _melhor_divisao(ordenadas: list[Linha], corpo: float) -> list[_Faixa] | None:
    """As faixas da calha que põe mais linhas em colunas; None se nenhuma põe."""
    inicios = sorted({linha.x for linha in ordenadas})
    if len(inicios) > INICIOS_MAXIMOS:
        return None
    regua = Regua(_entrelinha(ordenadas), corpo)
    melhor: tuple[int, list[_Faixa]] | None = None
    for calha in inicios:
        faixas = _faixas(ordenadas, calha, regua)
        em_colunas = sum(len(f.esquerda) + len(f.direita) for f in faixas if f.colunas)
        if em_colunas and (melhor is None or em_colunas > melhor[0]):
            melhor = (em_colunas, faixas)
    return None if melhor is None else melhor[1]


def _entrelinha(ordenadas: list[Linha]) -> float:
    """A distância típica entre uma linha e a de baixo na mesma coluna; infinita quando não há.

    A de baixo é a primeira que a sobrepõe na horizontal. Medida entre alturas seguidas da página
    inteira, a entrelinha caía à metade quando as colunas estão desalinhadas em meia linha (Miller
    p. 2931): o vão do subtítulo passava de 2,5 entrelinhas, fechava as colunas, e a página saía em
    quatro pedaços, com os subtítulos das duas colunas colados numa linha só (ADR-0004, "A ordem
    das colunas no Miller").
    """
    distancias = [
        distancia
        for posicao in range(len(ordenadas))
        if (distancia := _ate_a_de_baixo(ordenadas, posicao)) is not None
    ]
    return median(distancias) if distancias else math.inf


def _ate_a_de_baixo(ordenadas: list[Linha], posicao: int) -> float | None:
    de_cima = ordenadas[posicao]
    for seguinte in range(posicao + 1, min(posicao + 1 + LINHAS_ADIANTE, len(ordenadas))):
        de_baixo = ordenadas[seguinte]
        distancia = de_baixo.topo - de_cima.topo
        if distancia >= MESMA_ALTURA and de_baixo.x < de_cima.fim and de_cima.x < de_baixo.fim:
            return distancia
    return None


def _faixas(ordenadas: list[Linha], calha: float, regua: Regua) -> list[_Faixa]:
    """Corta a página, de cima para baixo, na linha que atravessa a calha e no vão que fecha
    as colunas."""
    lados = _lados(ordenadas, calha)
    # O título da esquerda que abre faixa da largura da página (ADR-0004, "Título que atravessa
    # as colunas").
    de = {lado: [k for k, dela in enumerate(lados) if dela is lado] for lado in _Lado}
    titulos = titulos_que_atravessam(ordenadas, de[_Lado.ESQUERDA], de[_Lado.DIREITA], regua.corpo)
    lados = [_Lado.ATRAVESSA if k in titulos else lado for k, lado in enumerate(lados)]
    faixas: list[_Faixa] = []
    esquerda: list[Linha] = []
    direita: list[Linha] = []
    for posicao, (linha, lado) in enumerate(zip(ordenadas, lados, strict=True)):
        corta = lado is _Lado.ATRAVESSA or _fecha_as_colunas(ordenadas, lados, posicao, regua)
        if corta and (esquerda or direita):
            faixas.append(_faixa(esquerda, direita, regua))
            esquerda, direita = [], []
        if lado is _Lado.ATRAVESSA:
            faixas.append(_Faixa(atravessa=(linha,)))
        else:
            (esquerda if lado is _Lado.ESQUERDA else direita).append(linha)
    return [*faixas, _faixa(esquerda, direita, regua)] if esquerda or direita else faixas


def _faixa(esquerda: list[Linha], direita: list[Linha], regua: Regua) -> _Faixa:
    colunas = duas_colunas(esquerda, direita, regua)
    return _Faixa(tuple(esquerda), tuple(direita), colunas=colunas)


def _lados(ordenadas: list[Linha], calha: float) -> list[_Lado]:
    """O lado da calha de cada linha, altura por altura."""
    lados: list[_Lado] = []
    for altura in por_altura(ordenadas):
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
    ordenadas: list[Linha], lados: list[_Lado], posicao: int, regua: Regua
) -> bool:
    """O vão de mais de 2,5 entrelinhas antes da linha `posicao` fecha as colunas: "Questões de
    revisão" vem depois delas (Dalgalarrondo p. 30 e 343), e a epígrafe, antes (p. 31).

    A não ser que uma coluna só passe por ele: a outra já acabou mais acima, e a mesma coluna
    continua embaixo com texto, 3 linhas ou mais. Aí o vão é subtítulo ou quadro dela, e o
    resto da coluna segue nela, antes da outra (code-review).

    O vão menor, de parágrafo, fecha as colunas quando a tabela de letra menor acaba e o corpo
    começa (`_acaba_a_tabela`).
    """
    if posicao == 0:
        return False
    de_cima, de_baixo = ordenadas[posicao - 1].topo, ordenadas[posicao].topo
    if de_baixo - de_cima <= regua.vao:
        vao_de_paragrafo = de_baixo - de_cima > VAO_DA_TABELA * regua.entrelinha
        return vao_de_paragrafo and _acaba_a_tabela(ordenadas, lados, posicao, regua)
    acima = _lados_entre(ordenadas, lados, de_cima - regua.vao, de_cima)
    return len(acima) != 1 or not _continua_so(lados[posicao:], acima.pop())


def _acaba_a_tabela(ordenadas: list[Linha], lados: list[_Lado], posicao: int, regua: Regua) -> bool:
    """A linha `posicao` é do corpo, e os dois lados da calha acabam, logo acima dela, em 3 linhas
    ou mais de letra menor que o corpo: é a tabela de um quadro. Dalgalarrondo p. 324: o corpo
    vinha nas colunas da tabela do Quadro 29.1, e a coluna da direita da tabela caía depois
    dele, fora do quadro. Um destaque de um lado só não basta (p. 219), nem o subtítulo maior
    (p. 193 e 332). ADR-0004, "O que ficou da Fase 1"."""
    if not regua.do_corpo(ordenadas[posicao]):
        return False
    acima = list(zip(ordenadas[:posicao], lados[:posicao], strict=True))
    return all(
        _menores_no_fim(acima, lado, regua) >= LINHAS_POR_COLUNA
        for lado in (_Lado.ESQUERDA, _Lado.DIREITA)
    )


def _menores_no_fim(acima: list[tuple[Linha, _Lado]], lado: _Lado, regua: Regua) -> int:
    """Quantas linhas seguidas do `lado`, de baixo para cima, têm letra menor que o corpo."""
    menores = 0
    for linha, dela in reversed(acima):
        if dela is not lado:
            continue
        if not regua.menor_que_o_corpo(linha):
            break
        menores += 1
    return menores


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


def _juntar(altura: list[Linha]) -> tuple[Linha, int]:
    # Revisão nº 2: ordenar por (topo, x) punha primeiro o pedaço da direita que ficasse um
    # pouco mais alto (618 vezes no Hard Parts). A ordem dentro da altura é só a do x.
    pedacos = sorted(altura, key=lambda linha: linha.x)
    juntas = replace(
        pedacos[0],
        texto=texto_da_altura(pedacos),
        monoespacada=all(pedaco.monoespacada for pedaco in pedacos),
        negrito=all(pedaco.negrito for pedaco in pedacos),
        versalete=all(pedaco.versalete for pedaco in pedacos),
        fim=max(pedaco.fim for pedaco in pedacos),
    )
    return juntas, len(pedacos)
