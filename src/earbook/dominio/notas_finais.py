# SPDX-License-Identifier: GPL-3.0-or-later
"""A seção de notas finais do capítulo sai pela letra, pelo recuo e pela forma da entrada (ADR-0004,
"Notas finais do capítulo").

No Being You, o fim de cada capítulo traz a seção de notas na letra delas (12,5 pt, com o corpo de
15): o título numa linha, e cada nota abrindo na margem com a frase do texto que ela comenta,
seguida de dois-pontos ("global workspace theory: Baars (1988); …"), com recuo pendente nas linhas
de baixo. São 13 mil palavras de citação autor-ano, sem marcador no corpo que as chame. Depois
delas vêm as notas de rodapé com símbolo ("* This paper…", "† Each hemisphere…"), na mesma letra e
mais recuadas, que o corpo chama ("to be a bat.*") e que ficam.

A seção sai antes dos blocos, porque é aqui que ela se separa das notas de rodapé: no bloco de
nota, as duas viram um texto só por página, e o `limpar` só as separaria trocando texto.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from earbook.dominio.pagina import DIFERENCA_DE_TAMANHO, Linha, Pagina
from earbook.dominio.paginacao import PaginasLimpas
from earbook.dominio.tabelas_e_figuras import (
    Posicao,
    corridas_fora_do_corpo,
    letra_do_corpo,
    sem_as_linhas,
)

MOTIVO_DAS_NOTAS_FINAIS = "notas finais do capítulo: chave em frase e citação autor-ano"
CHAVES_MINIMAS = 10
CITACOES_MINIMAS = 10
"""Medido no Being You: a seção provada tem de 13 a 41 chaves e de 19 a 73 citações; as 3 curtas
(1, 2 e 3 chaves) saem pelo título que as provadas repetem."""
PARTE_DAS_CHAVES = 0.75
"""Das linhas na margem da seção, quantas abrem com chave. Na seção de notas do Being You, 31 de
31 a 36 de 37; na bibliografia, que tem a mesma letra e o mesmo recuo pendente, 49 de 444."""
SECOES_DO_TITULO = 2
"""O título que o livro prova: o de 2 seções provadas ou mais ("Notes", 12 no Being You)."""
TOLERANCIA_DA_MARGEM = 0.5
"""Em pontos: o título e a primeira chave na mesma margem."""
# A frase do texto que a nota comenta, sem pontuação de fim de frase, e o dois-pontos com espaço
# ("A computer that plays Go: Silver…"). O "https://" não tem espaço, e "Fulano, A. (1988)."
# tem ponto antes.
_CHAVE = re.compile(r"[^.!?:]{1,80}?: \S")
# O ano entre parênteses, com o autor ou não: "(1988)", "(Searle, 1980)", "(Chalmers, 1995a)".
_CITACAO_AUTOR_ANO = re.compile(r"\(\D{0,80}?(?:1[5-9]|20)\d\d[a-z]?[),;]")
# A nota de rodapé com símbolo abre a linha com ele: "*", "†", "‡", "§", "¶", "||", "#".
_SIMBOLO_DO_RODAPE = re.compile(r"[*†‡§¶#|]")


@dataclass(frozen=True)
class _Secao:
    titulo: str
    posicoes: tuple[Posicao, ...]
    """Do título até a linha antes da primeira nota de rodapé com símbolo, ou do fim da corrida."""
    chaves: int
    na_margem: int
    """As linhas na margem do título, fora ele: as que abrem nota."""
    citacoes: int

    @property
    def provada(self) -> bool:
        return (
            self.chaves >= CHAVES_MINIMAS
            and self.citacoes >= CITACOES_MINIMAS
            and self.so_de_chaves
        )

    @property
    def so_de_chaves(self) -> bool:
        return self.chaves >= self.na_margem * PARTE_DAS_CHAVES


def tirar_notas_finais(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """As páginas sem as seções de notas finais, e uma remoção registrada por linha.

    Sai a seção provada (10 chaves e 10 citações autor-ano, e 3 de cada 4 linhas da margem com
    chave) e a seção curta que abre com o título de 2 seções provadas ou mais: o livro prova o
    próprio título, que a regra não conhece ("Notes", "Notas").
    """
    corpo = letra_do_corpo(paginas)
    if corpo is None:
        return PaginasLimpas(tuple(paginas), ())
    secoes = [
        secao
        for corrida in corridas_fora_do_corpo(paginas, corpo)
        for secao in _secoes(paginas, corrida, corpo[1])
    ]
    provadas = Counter(secao.titulo for secao in secoes if secao.provada)
    titulos = {titulo for titulo, vezes in provadas.items() if vezes >= SECOES_DO_TITULO}
    saem = {
        posicao: MOTIVO_DAS_NOTAS_FINAIS
        for secao in secoes
        if secao.provada or (secao.titulo in titulos and secao.so_de_chaves)
        for posicao in secao.posicoes
    }
    return sem_as_linhas(paginas, saem)


def _secoes(paginas: Sequence[Pagina], corrida: list[Posicao], corpo: float) -> list[_Secao]:
    """As seções candidatas da corrida: cada uma abre na linha seguida de uma chave na mesma margem
    e na mesma letra, e a busca segue depois do fim dela."""
    linhas = [paginas[p].linhas[n] for p, n in corrida]
    secoes: list[_Secao] = []
    inicio = 0
    while inicio < len(linhas) - 1:
        if not _abre(linhas[inicio], linhas[inicio + 1]):
            inicio += 1
            continue
        fim = _fim(linhas, inicio, corpo)
        secoes.append(_secao(linhas[inicio:fim], tuple(corrida[inicio:fim])))
        inicio = fim
    return secoes


def _abre(titulo: Linha, primeira: Linha) -> bool:
    """O título, que não é chave, e logo abaixo dele a primeira chave, na mesma margem e letra."""
    return (
        not _eh_chave(titulo)
        and _eh_chave(primeira)
        and abs(titulo.x - primeira.x) <= TOLERANCIA_DA_MARGEM
        and abs(titulo.tamanho - primeira.tamanho) <= DIFERENCA_DE_TAMANHO
    )


def _fim(linhas: list[Linha], inicio: int, corpo: float) -> int:
    """Onde a seção acaba: na nota de rodapé com símbolo, na linha do tamanho do corpo (de outra
    família, que não fecha a corrida: Arial e ArialMT no Being You) ou no fim da corrida. A fórmula
    em outra letra e a explicação dela, mais recuada, ficam dentro ("The rule itself: …")."""
    for fim in range(inicio + 1, len(linhas)):
        linha = linhas[fim]
        if _SIMBOLO_DO_RODAPE.match(linha.texto) or linha.tamanho >= corpo - DIFERENCA_DE_TAMANHO:
            return fim
    return len(linhas)


def _secao(linhas: list[Linha], posicoes: tuple[Posicao, ...]) -> _Secao:
    titulo = linhas[0]
    na_margem = [linha for linha in linhas[1:] if abs(linha.x - titulo.x) <= TOLERANCIA_DA_MARGEM]
    chaves = sum(1 for linha in na_margem if _eh_chave(linha))
    citacoes = sum(len(_CITACAO_AUTOR_ANO.findall(linha.texto)) for linha in linhas)
    return _Secao(titulo.texto, posicoes, chaves, len(na_margem), citacoes)


def _eh_chave(linha: Linha) -> bool:
    return _CHAVE.match(linha.texto) is not None
