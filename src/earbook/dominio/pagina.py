# SPDX-License-Identifier: GPL-3.0-or-later
"""A página de um PDF como o domínio a vê: linhas com posição e fonte (ADR-0004).

É o que o PDF sabe e o EPUB convertido já esqueceu: onde a linha está na página e de que
tamanho é a letra. O adaptador de PDF traduz a biblioteca para estes tipos.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from statistics import median, quantiles

# Letra espaçada (Competente: "P A R T E   I", "F A B I O   A K I T A"). Medido: o vão entre
# letras vai de 0,14 a 0,22 do tamanho da fonte; no texto comum, perto de zero dentro da
# palavra. O vão entre palavras passa do dobro do vão entre letras (4,4 contra 1,4 pt).
FOLGA_DO_ESPACADO = 0.08
VAO_DA_PALAVRA = 2.0
VIZINHAS_MINIMAS = 3
# O vão entre letras espaçadas fica bem abaixo do espaço comum da mesma linha; caracteres
# soltos separados pelo espaço comum ("passos 1 2 3 4 e 5") não são letra espaçada (F1).
FRACAO_DO_ESPACO = 0.75
HIFEN_SUAVE = "\u00ad"
# O Hard Parts quebra a linha com o U+2010 (1.058 vezes) e nunca o usa no meio da linha;
# para o dicionário do livro, ele vale o mesmo que o "-".
HIFEN_TIPOGRAFICO = "\u2010"
HIFENS_DA_QUEBRA = ("-", HIFEN_TIPOGRAFICO, HIFEN_SUAVE)
"""O hífen da quebra de linha: o "-", o U+2010 do Hard Parts e o hífen suave do Competente."""
_PRIMEIRA_LETRA = re.compile(r"[^\W\d_]")
# A letra de título e a folga do tamanho, pelas quais o `blocos`, o `capitulos` e o `quadro`
# comparam a letra da linha com a do corpo (ADR-0004). Moram aqui para o `quadro` não importar o
# `blocos`, que o importa.
RAZAO_DO_TITULO = 1.2
DIFERENCA_DE_TAMANHO = 0.5


@dataclass(frozen=True)
class Linha:
    texto: str
    x: float
    """Distância da borda esquerda da página até o começo da linha, em pontos. Na linha visual
    de uma coluna, conta da margem da coluna (ADR-0004, "Duas colunas")."""
    fim: float
    """Até o fim da linha, medido como o `x`: com ele, diz se a linha atravessa a calha entre
    duas colunas (ADR-0004, "Duas colunas")."""
    topo: float
    """Posição do alto da linha: 0 no topo da página, 1 no pé."""
    tamanho: float
    """Tamanho médio da fonte da linha, em pontos."""
    monoespacada: bool = False
    negrito: bool = False
    """Toda letra visível em fonte negrito: o subtítulo do tamanho do corpo (Competente)."""
    versalete: bool = False
    """Só maiúsculas, e alguma letra maior que a da linha: o subtítulo em versalete feito à mão
    (Dalgalarrondo), que pelo tamanho viraria nota."""
    fonte: str = ""
    """A família da letra da maioria dos caracteres visíveis, sem o prefixo do subconjunto e sem o
    estilo ("AGaramondPro", "HelveticaNeueLTStd"): a tabela e a figura vêm noutra família que a do
    corpo (ADR-0004, "Tabela e figura pela letra")."""
    chamadas: tuple[str, ...] = ()
    """As chamadas de referência sobrescritas tiradas da linha, com a palavra antes: "wages.[1]"
    (ADR-0004, "Número de referência e espaço falso")."""


@dataclass(frozen=True)
class Letra:
    """Um caractere visível da linha, com onde ele começa e termina na horizontal."""

    texto: str
    x0: float
    x1: float


@dataclass(frozen=True)
class Pagina:
    numero: int
    """Começa em 1, como no leitor de PDF."""
    linhas: tuple[Linha, ...]


def tamanho_do_corpo(paginas: Sequence[Pagina]) -> float:
    """O tamanho de fonte com mais caracteres no livro: o do texto corrido."""
    caracteres: Counter[float] = Counter()
    for pagina in paginas:
        for linha in pagina.linhas:
            caracteres[round(linha.tamanho, 1)] += len(linha.texto)
    return caracteres.most_common(1)[0][0] if caracteres else 0.0


def corpo_em_negrito(paginas: Sequence[Pagina], corpo: float) -> bool:
    """Se a maior parte do texto do tamanho `corpo` está em linha toda negrito.

    Aí o negrito é o corpo do livro e não destaca subtítulo nenhum (revisão nº 1).
    """
    caracteres: Counter[bool] = Counter()
    for pagina in paginas:
        for linha in pagina.linhas:
            if round(linha.tamanho, 1) == corpo:
                caracteres[linha.negrito] += len(linha.texto)
    return caracteres[True] > caracteres[False]


def em_versalete(letras: Sequence[tuple[str, float]], tamanho: float) -> bool:
    """Maiúsculas de dois tamanhos: nenhuma letra minúscula, e alguma letra maior que o tamanho
    da linha (a moda). É o versalete feito à mão do Dalgalarrondo, com a inicial da palavra em
    10,5 pt e o resto em 7,4 (ADR-0004, "O que ficou da Fase 1"). Os rótulos do Competente
    ("PREFÁCIO", "APÊNDICE A") têm um tamanho só, e o somatório maior numa fórmula ("ML = 100 *
    ∑", Hard Parts) não é letra.
    """
    maior = any(letra.isalpha() and t > tamanho + DIFERENCA_DE_TAMANHO for letra, t in letras)
    return so_maiusculas("".join(letra for letra, _ in letras)) and maior


def so_maiusculas(texto: str) -> bool:
    """Nenhuma letra minúscula: o versalete e a linha que continua o título em versalete."""
    return not any(letra.islower() for letra in texto)


def comeca_em_minuscula(texto: str) -> bool:
    """A primeira letra do texto, passando por algarismo e pontuação, é minúscula."""
    letra = _PRIMEIRA_LETRA.search(texto)
    return letra is not None and letra.group().islower()


def juntar_letras_espacadas(letras: Sequence[Letra], tamanho: float) -> str | None:
    """`"PARTE I"` para as letras de `"P A R T E   I"`; None se a linha não tem trecho espaçado.

    O ElevenReader cola as letras soltas, e "P A R T E I" virava "PARTEI", lido como o
    verbo "partei" (escuta de 2026-11-01). A palavra termina onde o vão real passa do
    dobro do vão típico entre as letras do trecho, e não onde o pdfminer pôs espaço: em
    "B O M 15", ele pôs um espaço só antes de um vão de 10,5 pt. A decisão é por trecho:
    na linha mista, a palavra comum fica como está (revisão); caracteres soltos separados
    pelo espaço comum não são letra espaçada (F1 da auditoria).
    """
    palavras = _palavras(letras, tamanho * FOLGA_DO_ESPACADO)
    espaco = _espaco_comum(palavras)
    trechos = _trechos(palavras)
    if not any(_espacado(trecho, espaco) for trecho in trechos):
        return None
    return " ".join(_texto_do_trecho(trecho, espaco) for trecho in trechos)


def _espaco_comum(palavras: list[list[Letra]]) -> float | None:
    """O vão em volta das palavras de mais de uma letra: a régua do espaço comum da linha."""
    vaos = [
        depois[0].x0 - antes[-1].x1
        for antes, depois in pairwise(palavras)
        if len(antes) > 1 or len(depois) > 1
    ]
    return median(vaos) if vaos else None


def _vao_entre_letras(letras: list[Letra]) -> float:
    """O primeiro quartil dos vãos: o de letra, mesmo com muita palavra de uma letra ("É O FIM")."""
    return quantiles([depois.x0 - antes.x1 for antes, depois in pairwise(letras)], n=4)[0]


def _palavras(letras: Sequence[Letra], vao_aberto: float) -> list[list[Letra]]:
    """Corta nos vãos abertos: no texto comum, só entre palavras; no espaçado, entre letras."""
    palavras: list[list[Letra]] = []
    for anterior, letra in zip([None, *letras], letras, strict=False):
        if anterior is None or letra.x0 - anterior.x1 > vao_aberto:
            palavras.append([letra])
        else:
            palavras[-1].append(letra)
    return palavras


def _trechos(palavras: list[list[Letra]]) -> list[list[list[Letra]]]:
    """Junta as palavras de uma letra só que vêm seguidas: o candidato a trecho espaçado."""
    trechos: list[list[list[Letra]]] = []
    for palavra in palavras:
        if len(palavra) == 1 and trechos and all(len(p) == 1 for p in trechos[-1]):
            trechos[-1].append(palavra)
        else:
            trechos.append([palavra])
    return trechos


def _espacado(trecho: list[list[Letra]], espaco: float | None) -> bool:
    """Letras soltas seguidas, com 3 pares de letras vizinhas ou mais, e vão bem menor que o
    espaço comum da linha, quando ela tem palavra comum.

    Pares, e não só letras: os pontinhos do sumário não têm letra, e a fórmula
    "D = A + I - 1" (Hard Parts p. 87) tem sempre um operador entre duas letras. Um trecho
    é uma palavra de várias letras ou só palavras de uma letra; no primeiro caso, 0 pares.
    """
    soltas = [palavra[0] for palavra in trecho]
    vizinhas = sum(a.texto.isalnum() and b.texto.isalnum() for a, b in pairwise(soltas))
    if vizinhas < VIZINHAS_MINIMAS:
        return False
    return espaco is None or _vao_entre_letras(soltas) < espaco * FRACAO_DO_ESPACO


def _texto_do_trecho(trecho: list[list[Letra]], espaco: float | None) -> str:
    if not _espacado(trecho, espaco):
        return " ".join("".join(letra.texto for letra in palavra) for palavra in trecho)
    letras = [palavra[0] for palavra in trecho]
    vaos = [depois.x0 - antes.x1 for antes, depois in pairwise(letras)]
    limite = _vao_entre_letras(letras) * VAO_DA_PALAVRA
    partes = [letras[0].texto]
    for vao, letra in zip(vaos, letras[1:], strict=True):
        partes.append((" " if vao > limite else "") + letra.texto)
    return "".join(partes)
