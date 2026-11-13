# SPDX-License-Identifier: GPL-3.0-or-later
"""A seção de questões de múltipla escolha sai do áudio (ADR-0008, "Tratado em português e em
espanhol"): o enunciado e as alternativas de letra, do título da seção em diante. Nunca pelo
título, que o ADR-0008 proíbe como critério e que o OCR estraga ("Qu esõ e d Provae do tsA").

Medido no Manica: 62 capítulos terminam numa seção assim, cada questão aberta pelo enunciado de
prova ("34.1 (TSA/2012) …"). A lista de letras da prosa fica: o PCDT tem 13 grupos "a), b), c)"
(questionário, notas do GRADE), o Miller 4, o Practical 1 e o Bonica 1, e nenhum deles sai.
"""

from __future__ import annotations

import re
from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import accumulate

from earbook.dominio.segmento import Papel, Segmento

MOTIVO_DAS_QUESTOES = "seção de questões: enunciados e alternativas de múltipla escolha"
# "A. Propofol.", "b) Etomidato.", "(c) Midazolam.": a letra de A a E, em qualquer caixa (o
# versalete do Manica a troca), com ponto ou parêntese.
_ALTERNATIVA = re.compile(r"\(?(?P<letra>[A-Ea-e])[.)]\s")
# "34.1 (TSA/2012) As variáveis…": o número da questão e a prova, sigla e ano, entre parênteses.
_ENUNCIADO_DE_PROVA = re.compile(
    r"\d{1,3}(?:\.\d{1,3})?\.?\s*\([^\W\d_]{2,10}\s?[/-]\s?(?:19|20)\d\d\)"
)
ALTERNATIVAS_DO_GRUPO = 3
# O título e, no máximo, 3 parágrafos de enunciado antes da primeira alternativa. Medido: o
# enunciado do Manica tem 1 parágrafo, e 2 quando a página o parte.
SEGMENTOS_ATE_O_TITULO = 4
# Medido no Manica: do título ao fim do capítulo, 1.250 de 1.322 segmentos são alternativa ou
# enunciado de prova (95%); o resto é enunciado partido e resto de figura.
FRACAO_DE_QUESTOES = 0.5
SINAIS_DA_SECAO = 2
"""O enunciado de prova que abre a seção e mais um sinal: outro enunciado ou um grupo de
alternativas. Um enunciado sozinho é o item de uma norma ("12.3 (RDC/2010) Dispõe…"). E sem
enunciado de prova nada sai, por mais grupos que haja: a enumeração da prosa ("Critérios maiores:
a) … b) … c) …") tem a mesma forma da questão (A1 da code-audit)."""


@dataclass(frozen=True)
class _Sinais:
    """O que o capítulo tem de questão, com as contas acumuladas: o EPUB é entrada não confiável,
    e contar de novo a cada enunciado custava o quadrado do capítulo (A2 da code-audit)."""

    grupos: tuple[int, ...]
    """Onde começa cada grupo de alternativas em ordem."""
    enunciados: tuple[int, ...]
    paragrafos_ate: tuple[int, ...]
    """Quantos parágrafos há antes de cada posição; a última é o capítulo inteiro."""
    questoes_ate: tuple[int, ...]
    """Quantos deles são alternativa ou enunciado de prova."""
    ultima_questao_ate: tuple[int, ...]
    """A posição da última questão antes de cada posição; -1 se não há."""

    def serve(self, inicio: int, fim: int) -> bool:
        """Do título `inicio` até `fim`, metade dos parágrafos ou mais é questão, e há sinal."""
        paragrafos = self.paragrafos_ate[fim] - self.paragrafos_ate[inicio + 1]
        questoes = self.questoes_ate[fim] - self.questoes_ate[inicio + 1]
        sinais = _entre(self.grupos, inicio, fim) + _entre(self.enunciados, inicio, fim)
        return sinais >= SINAIS_DA_SECAO and questoes >= FRACAO_DE_QUESTOES * paragrafos

    def depois_da_ultima_questao(self, inicio: int, limite: int) -> int:
        """Onde a seção acaba: depois da última alternativa ou enunciado de prova antes de
        `limite`. O que vem depois não é questão: a seção curta que fecha o capítulo, o começo
        do capítulo seguinte que a página trouxe para cá (R1 da code-review)."""
        return max(self.ultima_questao_ate[limite], inicio) + 1


def _entre(posicoes: Sequence[int], inicio: int, fim: int) -> int:
    """Quantas das `posicoes`, em ordem, ficam depois de `inicio` e antes de `fim`."""
    return max(bisect_left(posicoes, fim) - bisect_right(posicoes, inicio), 0)


def secoes_de_questoes(capitulos: Sequence[tuple[str, Sequence[Segmento]]]) -> dict[str, str]:
    """ID → motivo de cada segmento das seções de questões de cada capítulo, com o título."""
    saem: dict[str, str] = {}
    for _, segmentos in capitulos:
        for inicio, fim in _secoes(segmentos):
            saem |= dict.fromkeys((s.id for s in segmentos[inicio:fim]), MOTIVO_DAS_QUESTOES)
    return saem


def _secoes(segmentos: Sequence[Segmento]) -> list[tuple[int, int]]:
    """(início, fim) de cada seção de questões do capítulo.

    Cada enunciado de prova, na ordem, pode abrir uma: ela começa no título logo antes dele. O
    que não serve (o item solto de uma norma) não esconde a seção que vem depois.
    """
    sinais = _sinais(segmentos)
    secoes: list[tuple[int, int]] = []
    fim = 0
    for enunciado in sinais.enunciados:
        titulo = None if enunciado < fim else _titulo_antes(segmentos, enunciado)
        if titulo is not None and titulo >= fim:
            secao = _da_secao(segmentos, sinais, titulo)
            secoes += [secao] if secao else []
            fim = secao[1] if secao else fim
    return secoes


def _da_secao(
    segmentos: Sequence[Segmento], sinais: _Sinais, titulo: int
) -> tuple[int, int] | None:
    """Do título até a última questão do capítulo; se há prosa demais no meio, até a última
    questão antes do próximo título."""
    for limite in (len(segmentos), _proximo_titulo(segmentos, titulo)):
        fim = sinais.depois_da_ultima_questao(titulo, limite)
        if sinais.serve(titulo, fim):
            return titulo, fim
    return None


def _sinais(segmentos: Sequence[Segmento]) -> _Sinais:
    letras = [_letra(segmento) for segmento in segmentos]
    enunciados = tuple(
        n
        for n, segmento in enumerate(segmentos)
        if segmento.papel is Papel.PARAGRAFO and _ENUNCIADO_DE_PROVA.match(segmento.texto)
    )
    questoes = [bool(letra) for letra in letras]
    for n in enunciados:
        questoes[n] = True
    paragrafos = [segmento.papel is Papel.PARAGRAFO for segmento in segmentos]
    ultima, ultimas = -1, [-1]
    for n, questao in enumerate(questoes):
        ultima = n if questao else ultima
        ultimas.append(ultima)
    paragrafos_ate = tuple(accumulate(paragrafos, initial=0))
    questoes_ate = tuple(accumulate(questoes, initial=0))
    return _Sinais(_grupos(letras), enunciados, paragrafos_ate, questoes_ate, tuple(ultimas))


def _letra(segmento: Segmento) -> str:
    achado = _ALTERNATIVA.match(segmento.texto) if segmento.papel is Papel.PARAGRAFO else None
    return achado["letra"].lower() if achado else ""


def _grupos(letras: Sequence[str]) -> tuple[int, ...]:
    """Onde começa cada grupo: 3 alternativas seguidas ou mais, em ordem, a partir do A."""
    grupos: list[int] = []
    posicao = 0
    while posicao < len(letras):
        fim = posicao + 1
        if letras[posicao] == "a":
            while fim < len(letras) and letras[fim] == chr(ord(letras[fim - 1]) + 1):
                fim += 1
            if fim - posicao >= ALTERNATIVAS_DO_GRUPO:
                grupos.append(posicao)
        posicao = fim
    return tuple(grupos)


def _titulo_antes(segmentos: Sequence[Segmento], primeiro: int) -> int | None:
    """O título mais perto, até `SEGMENTOS_ATE_O_TITULO` segmentos antes do enunciado."""
    for n in range(primeiro - 1, max(primeiro - 1 - SEGMENTOS_ATE_O_TITULO, -1), -1):
        if segmentos[n].papel is Papel.TITULO:
            return n
    return None


def _proximo_titulo(segmentos: Sequence[Segmento], inicio: int) -> int:
    for n in range(inicio + 1, len(segmentos)):
        if segmentos[n].papel is Papel.TITULO:
            return n
    return len(segmentos)
