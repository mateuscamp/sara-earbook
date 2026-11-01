# SPDX-License-Identifier: GPL-3.0-or-later
"""Cabeçalho e rodapé de página no PDF, reconhecidos pela posição (ADR-0004).

No EPUB convertido, o cabeçalho é só mais um parágrafo, e a regra de texto do `limpar` só
o reconhece quando ele repete o título ou o autor do livro. No PDF ele mora numa faixa
fixa da página, e é isso que esta regra usa. Ela pega também o cabeçalho com o título do
capítulo e com letras espaçadas, medidos no spike.

A faixa sozinha não basta (A1 da auditoria): título de capítulo e número de capítulo
também caem nela. Por isso, só sai da faixa o que tem fonte de rodapé (não maior que a do
corpo) e, além disso, ou é número que segue a paginação ou se repete no mesmo topo.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from earbook.dominio.pagina import Linha, Pagina, tamanho_do_corpo

# Medido no spike: o cabeçalho ficou acima de 90% da altura, e o rodapé abaixo de 8%.
FAIXA_DA_BORDA = 0.08
# Duas páginas ainda podem ser texto do livro; três já é cabeçalho corrente.
PAGINAS_MINIMAS = 3
# Medido nos dois livros: cada cabeçalho tirado tinha um topo só (0,05 e 0,9252).
TOLERANCIA_DO_TOPO = 0.01
# Cabeçalho e número de página vêm no tamanho do corpo ou menores (7,5 e 9 pt contra 10,5).
FOLGA_DA_FONTE = 0.5
# Sem o ponto: "1.2" virava 12 e passava por número de página (revisão nº 5).
_SEPARADORES = re.compile(r"[\s|\u00b7\u2022\-\u2013\u2014]")
_ARABICO = re.compile(r"[0-9]{1,5}")
_ROMANO = re.compile(r"M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})")
_LETRA = re.compile(r"[^\W\d_]")
_VALOR_ROMANO = {"M": 1000, "D": 500, "C": 100, "L": 50, "X": 10, "V": 5, "I": 1}

type _Ocorrencia = tuple[int, int, Linha]
"""(número da página, posição da linha na página, linha)."""


@dataclass(frozen=True)
class LinhaRemovida:
    pagina: int
    motivo: str
    texto: str


@dataclass(frozen=True)
class PaginasLimpas:
    paginas: tuple[Pagina, ...]
    remocoes: tuple[LinhaRemovida, ...]


def tirar_cabecalhos_e_rodapes(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """Tira da borda o número de página que segue a paginação e a linha que se repete.

    `tirar_cabecalhos_e_rodapes(paginas)` devolve as páginas sem essas linhas e uma
    remoção registrada por linha tirada.
    """
    candidatas = _candidatas(paginas)
    numeros = _numeros_de_pagina(candidatas)
    repetidas = _repetidas(o for o in candidatas if (o[0], o[1]) not in numeros)
    motivos = dict.fromkeys(numeros, "número de página") | repetidas
    limpas: list[Pagina] = []
    remocoes: list[LinhaRemovida] = []
    for pagina in paginas:
        mantidas: list[Linha] = []
        for posicao, linha in enumerate(pagina.linhas):
            motivo = motivos.get((pagina.numero, posicao))
            if motivo is None:
                mantidas.append(linha)
            else:
                remocoes.append(LinhaRemovida(pagina.numero, motivo, linha.texto))
        limpas.append(Pagina(pagina.numero, tuple(mantidas)))
    return PaginasLimpas(tuple(limpas), tuple(remocoes))


def _candidatas(paginas: Sequence[Pagina]) -> list[_Ocorrencia]:
    """Linhas na faixa da borda com fonte de rodapé: no máximo o tamanho do corpo."""
    limite = tamanho_do_corpo(paginas) + FOLGA_DA_FONTE
    return [
        (pagina.numero, posicao, linha)
        for pagina in paginas
        for posicao, linha in enumerate(pagina.linhas)
        if _na_borda(linha) and linha.tamanho <= limite
    ]


def _na_borda(linha: Linha) -> bool:
    return linha.topo < FAIXA_DA_BORDA or linha.topo > 1 - FAIXA_DA_BORDA


def _numeros_de_pagina(candidatas: Sequence[_Ocorrencia]) -> set[tuple[int, int]]:
    """Os números cujo deslocamento em relação à página se repete em 3 páginas ou mais.

    No Competente, o número impresso é a página - 7 em 398 de 398; no Hard Parts, - 18 em
    429 de 433. Um número sozinho ("2020.", "1.", "mix") não prova sequência e fica.
    """
    impressos: list[tuple[int, int, str, int]] = []
    for pagina, posicao, linha in candidatas:
        lido = _numero_impresso(linha.texto)
        if lido is not None:
            impressos.append((pagina, posicao, lido[0], lido[1] - pagina))
    # Conta páginas, não ocorrências: o número no alto e no pé da mesma página vale uma vez.
    paginas_por_sequencia: defaultdict[tuple[str, int], set[int]] = defaultdict(set)
    for pagina, _, sistema, deslocamento in impressos:
        paginas_por_sequencia[sistema, deslocamento].add(pagina)
    coerentes = {
        chave for chave, paginas in paginas_por_sequencia.items() if len(paginas) >= PAGINAS_MINIMAS
    }
    return {(p, posicao) for p, posicao, sistema, desl in impressos if (sistema, desl) in coerentes}


def _numero_impresso(texto: str) -> tuple[str, int] | None:
    """("arabico", 23) para "| 23"; ("romano", 12) para "xii"; None para o resto."""
    nucleo = _SEPARADORES.sub("", texto)
    if _ARABICO.fullmatch(nucleo):
        return "arabico", int(nucleo)
    if nucleo and _ROMANO.fullmatch(nucleo.upper()):
        return "romano", _valor_romano(nucleo.upper())
    return None


def _valor_romano(romano: str) -> int:
    valores = [_VALOR_ROMANO[letra] for letra in romano]
    seguintes = [*valores[1:], 0]
    return sum(-v if v < seguinte else v for v, seguinte in zip(valores, seguintes, strict=True))


def _chave(texto: str) -> str:
    """Sem espaço e com o número trocado por "#": "C O M P E T E N T E 12" = "competente#"."""
    return re.sub(r"\d+", "#", "".join(texto.split()).casefold())


def _repetidas(candidatas: Iterable[_Ocorrencia]) -> dict[tuple[int, int], str]:
    """A linha que se repete no mesmo topo em 3 páginas ou mais, com o motivo de cada uma."""
    # Alto e pé em grupos separados: com o título no alto das pares e no pé das ímpares, a
    # mediana do grupo inteiro caía no meio da página e nada saía (revisão nº 3).
    grupos: defaultdict[tuple[str, bool], list[_Ocorrencia]] = defaultdict(list)
    for ocorrencia in candidatas:
        chave = _chave(ocorrencia[2].texto)
        # O1: sem letra, o "#" juntaria números diferentes ("2020.", "1999.", "1984.") num
        # rodapé falso. A chave vira o texto literal: só o mesmo rodapé em toda página sai
        # ("2021", "© 2020", uma data; A3 da auditoria).
        if not _LETRA.search(chave):
            chave = "".join(ocorrencia[2].texto.split())
        grupos[chave, ocorrencia[2].topo < FAIXA_DA_BORDA].append(ocorrencia)
    motivos: dict[tuple[int, int], str] = {}
    for ocorrencias in grupos.values():
        for mesma_altura in _por_altura(ocorrencias):
            if len({pagina for pagina, _, _ in mesma_altura}) < PAGINAS_MINIMAS:
                continue
            for pagina, posicao, linha in mesma_altura:
                lugar = "cabeçalho" if linha.topo < FAIXA_DA_BORDA else "rodapé"
                motivos[pagina, posicao] = f"{lugar} de página repetido"
    return motivos


def _por_altura(ocorrencias: Sequence[_Ocorrencia]) -> list[list[_Ocorrencia]]:
    """Agrupa as ocorrências seguidas, em ordem de topo, a menos da tolerância uma da outra.

    O2: a mediana do grupo inteiro empatava entre duas alturas e não tirava nenhuma.
    """
    ordenadas = sorted(ocorrencias, key=lambda o: o[2].topo)
    grupos: list[list[_Ocorrencia]] = [[ordenadas[0]]]
    for ocorrencia in ordenadas[1:]:
        if ocorrencia[2].topo - grupos[-1][-1][2].topo <= TOLERANCIA_DO_TOPO:
            grupos[-1].append(ocorrencia)
        else:
            grupos.append([ocorrencia])
    return grupos
