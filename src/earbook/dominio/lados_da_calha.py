# SPDX-License-Identifier: GPL-3.0-or-later
"""O que cada lado da calha é: coluna de texto ou célula de tabela (ADR-0004, "Duas colunas").

A calha separa a página em dois lados; a faixa só é lida coluna a coluna quando os dois lados são
colunas de texto. A tabela também tem calha, e lida coluna a coluna ela perde o par de cada linha
("Communication Consistency… Synchronous Atomic…", Hard Parts p. 347). Separado de
`dominio/colunas.py`, que acha a calha e corta as faixas, quando a prosa ao lado de uma lista
entrou (ADR-0004, "A ordem das colunas no Miller").
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from statistics import median

from earbook.dominio.pagina import (
    DIFERENCA_DE_TAMANHO,
    HIFENS_DA_QUEBRA,
    Linha,
    comeca_em_minuscula,
)

# Linhas a menos disso de topo estão na mesma altura (células de tabela no Hard Parts: 0,001).
MESMA_ALTURA = 0.004
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
VAO_DA_FAIXA = 2.5
"""Em entrelinhas. Medido no Dalgalarrondo com a entrelinha da página inteira: o parágrafo novo
abre 2 entrelinhas; o quadro e a epígrafe, de 4,5 a 5,6 (p. 30 e 31). Medida dentro da coluna
(`colunas._entrelinha`), a entrelinha do Dalgalarrondo é 13% maior (mediana de 0,0169 contra
0,0149), e as mesmas medidas ficam perto de 1,8 e de 4 a 5. O subtítulo das duas colunas do
Miller abre 2,3; o título do Quadro 29.2 do Dalgalarrondo (p. 325), 2,5, no limiar (ADR-0004, "A
ordem das colunas no Miller")."""
CONTINUIDADE_DO_JUSTIFICADO = 0.3
LINHAS_CHEIAS = 0.4
"""O lado de verbetes, que abrem em maiúscula, é texto corrido quando continua em 30% ou mais
dos pares e 40% ou mais das linhas chegam à margem direita dele: é justificado. Medido no
Dalgalarrondo: o glossário tem de 0,40 a 0,55 de linhas cheias, e a bibliografia, de 0,62 a
0,77; as tabelas do Competente e do Hard Parts que passam de 0,3 de continuidade têm no máximo
0,25 (a p. 144 do Competente, 0,11). As tabelas com a coluna da direita alinhada (Hard Parts
p. 143) têm linhas cheias, mas continuidade zero (ADR-0004, "O que ficou da Fase 1")."""
LINHAS_DA_COLUNA_CURTA = 2
"""O resto do parágrafo no pé da página, ao lado de uma lista (`_curta_do_corpo`)."""
FOLGA_DA_MARGEM = 1.0
"""Em pontos: a linha cheia termina a menos disso da margem direita do lado."""
LINHAS_DA_PROSA = 6
CARACTERES_DA_PROSA = 35
"""A prosa ao lado de uma lista (`_prosa_ao_lado`): 6 linhas ou mais, com 35 caracteres ou mais
na mediana. Medido no Miller: a linha de prosa da coluna tem de 50 a 62 caracteres; a célula de
tabela que quebra linha e chega à margem dela ("Porcentaje del / tiempo de", p. 2965), menos de
20."""
FOLGA_DA_PROSA = 3.0
LINHAS_CHEIAS_DA_PROSA = 0.6
"""Em pontos, da margem mais comum do lado, e a fração das linhas nela. A margem pelo fim mais
alto (`FOLGA_DA_MARGEM`) se perdia com uma só linha 1 pt além dela (o "®" do Miller p. 2884)."""
LARGURA_AO_LADO = (0.8, 1.05)
"""A largura do outro lado, em frações da largura da prosa: a coluna da página tem a largura da
vizinha. A coluna de chave de uma tabela fica bem mais estreita que a de valor."""


@dataclass(frozen=True)
class Regua:
    """O que mede o vão entre as faixas da página: a entrelinha dela e o corpo do livro."""

    entrelinha: float
    corpo: float

    @property
    def vao(self) -> float:
        return VAO_DA_FAIXA * self.entrelinha

    def do_corpo(self, linha: Linha) -> bool:
        return abs(linha.tamanho - self.corpo) <= DIFERENCA_DE_TAMANHO

    def menor_que_o_corpo(self, linha: Linha) -> bool:
        return linha.tamanho < self.corpo - DIFERENCA_DE_TAMANHO


def duas_colunas(esquerda: list[Linha], direita: list[Linha], regua: Regua) -> bool:
    """Os dois lados da faixa são colunas de texto, ou um é prosa e o outro tem a largura dela."""
    if not esquerda or not direita:
        return False
    # As alturas de cada lado uma vez só: a regra roda em cada faixa de cada calha candidata.
    lados = ((esquerda, por_altura(esquerda)), (direita, por_altura(direita)))
    largura_da_faixa = _largura(esquerda + direita)
    if all(_coluna(lado, alturas, largura_da_faixa, regua) for lado, alturas in lados):
        return True
    return _prosa_ao_lado(*lados[0], *lados[1]) or _prosa_ao_lado(*lados[1], *lados[0])


def _coluna(
    lado: list[Linha], alturas: list[list[Linha]], largura_da_faixa: float, regua: Regua
) -> bool:
    """Um lado da calha é coluna de texto: 3 linhas ou mais, ou a coluna curta do corpo; largo e
    corrido."""
    if len(alturas) < LINHAS_POR_COLUNA and not _curta_do_corpo(alturas, regua):
        return False
    return _largura(lado) >= LARGURA_DA_COLUNA * largura_da_faixa and _corrido(alturas)


def _prosa_ao_lado(
    prosa: list[Linha],
    alturas_da_prosa: list[list[Linha]],
    outro: list[Linha],
    alturas_do_outro: list[list[Linha]],
) -> bool:
    """Um lado é prosa de livro, e o outro, de 3 linhas ou mais, tem a largura dela: a lista, a
    tabela na letra do corpo ou o quadro na coluna ao lado da prosa (Miller p. 1377 e 2884). A
    regra dos dois lados corridos a recusava, e a página era lida por altura, com a prosa
    intercalada: "Torácica 30 que estos pacientes suelen…" (ADR-0004, "A ordem das colunas no
    Miller")."""
    if len(alturas_do_outro) < LINHAS_POR_COLUNA or not _prosa(alturas_da_prosa):
        return False
    minima, maxima = LARGURA_AO_LADO
    return minima * _largura(prosa) <= _largura(outro) <= maxima * _largura(prosa)


def _prosa(alturas: list[list[Linha]]) -> bool:
    """Linha longa, texto corrido e margem direita comum: a coluna de um livro justificado."""
    if len(alturas) < LINHAS_DA_PROSA:
        return False
    if median(len(texto_da_altura(altura)) for altura in alturas) < CARACTERES_DA_PROSA:
        return False
    fins = _fins(alturas)
    margem = Counter(round(fim) for fim in fins).most_common(1)[0][0]
    return _corrido(alturas) and _na_margem(fins, margem, FOLGA_DA_PROSA) >= LINHAS_CHEIAS_DA_PROSA


def _curta_do_corpo(alturas: list[list[Linha]], regua: Regua) -> bool:
    """Duas linhas do corpo, a de cima partida no hífen da quebra e a de baixo em minúscula: o
    resto do parágrafo no pé da página, ao lado de uma lista (Dalgalarrondo p. 384, "…é classi-"
    / "camente definida pela tríade:"). A célula de duas linhas de uma tabela não se parte em
    sílaba (Hard Parts p. 257), e com qualquer continuação ela virava coluna (ADR-0004, "O que
    ficou da Fase 1")."""
    if len(alturas) != LINHAS_DA_COLUNA_CURTA or not all(
        regua.do_corpo(linha) for altura in alturas for linha in altura
    ):
        return False
    de_cima, de_baixo = (texto_da_altura(altura) for altura in alturas)
    return de_cima.endswith(HIFENS_DA_QUEBRA) and comeca_em_minuscula(de_baixo)


def _largura(linhas: list[Linha]) -> float:
    return max(linha.fim for linha in linhas) - min(linha.x for linha in linhas)


def _corrido(alturas: list[list[Linha]]) -> bool:
    """Texto corrido, e não célula de tabela: a linha de baixo costuma continuar a de cima."""
    textos = [texto_da_altura(altura) for altura in alturas]
    pares = list(pairwise(textos))
    continuam = sum(_continua(de_cima, de_baixo) for de_cima, de_baixo in pares)
    if continuam >= CONTINUIDADE * len(pares):
        return True
    return continuam >= CONTINUIDADE_DO_JUSTIFICADO * len(pares) and _justificado(alturas)


def _justificado(alturas: list[list[Linha]]) -> bool:
    """40% ou mais das linhas terminam na margem direita do lado: o glossário e a bibliografia do
    Dalgalarrondo, cujos verbetes abrem em maiúscula e continuam pouco (`LINHAS_CHEIAS`)."""
    fins = _fins(alturas)
    return _na_margem(fins, max(fins), FOLGA_DA_MARGEM) >= LINHAS_CHEIAS


def _fins(alturas: list[list[Linha]]) -> list[float]:
    return [max(linha.fim for linha in altura) for altura in alturas]


def _na_margem(fins: list[float], margem: float, folga: float) -> float:
    """A fração das linhas que terminam a menos de `folga` pontos da `margem`."""
    return sum(abs(margem - fim) <= folga for fim in fins) / len(fins)


def _continua(de_cima: str, de_baixo: str) -> bool:
    return de_cima.endswith(HIFENS_DA_QUEBRA) or comeca_em_minuscula(de_baixo)


def por_altura(linhas: Sequence[Linha]) -> list[list[Linha]]:
    """Agrupa as linhas na mesma altura, de cima para baixo."""
    alturas: list[list[Linha]] = []
    for linha in sorted(linhas, key=lambda linha: linha.topo):
        if alturas and abs(linha.topo - alturas[-1][0].topo) < MESMA_ALTURA:
            alturas[-1].append(linha)
        else:
            alturas.append([linha])
    return alturas


def texto_da_altura(altura: list[Linha]) -> str:
    return " ".join(pedaco.texto for pedaco in sorted(altura, key=lambda linha: linha.x))
