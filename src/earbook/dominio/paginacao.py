# SPDX-License-Identifier: GPL-3.0-or-later
"""Cabeçalho e rodapé de página no PDF, reconhecidos pela posição (ADR-0004).

No EPUB convertido, o cabeçalho é só mais um parágrafo, e a regra de texto do `limpar` só
o reconhece quando ele repete o título ou o autor do livro. No PDF ele mora numa faixa
fixa da página, e é isso que esta regra usa. Ela pega também o cabeçalho com o título do
capítulo e com letras espaçadas, medidos no spike.

A faixa sozinha não basta (A1 da auditoria): título de capítulo e número de capítulo
também caem nela. Por isso, só sai da faixa o número que segue a paginação ou a linha com
fonte de rodapé (não maior que a do corpo) que se repete no mesmo topo. O número maior que
o corpo forma a sua própria sequência, com os do mesmo tamanho (ADR-0004, "Número de página
maior que o corpo").
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from statistics import median

from earbook.dominio.pagina import Linha, Pagina, tamanho_do_corpo

# Medido no spike: o cabeçalho ficou acima de 90% da altura, e o rodapé abaixo de 8%.
FAIXA_DA_BORDA = 0.08
# Duas páginas ainda podem ser texto do livro; três já é cabeçalho corrente.
PAGINAS_MINIMAS = 3
# A não ser que as duas sejam vizinhas, as duas de uma abertura: "Prefácio da 1a edição" e
# "Sumário", no Dalgalarrondo (p. 14 e 15, 18 e 19). O par com uma página entre elas (o
# Competente e o Hard Parts, que alternam o cabeçalho) fica: a forma geral foi recusada, porque
# no Hard Parts o rodapé tirado deixava a virada de página colar um item de lista no parágrafo
# seguinte (ADR-0004, "O que ficou da Fase 1").
PAGINAS_VIZINHAS = 2
# Fora da faixa, a borda é o que fica fora da mancha, a área do corpo no livro inteiro. No
# Maudlin (396 x 612 pt), o cabeçalho fica a 13,6% do alto, acima do corpo, que começa a 17%, e o
# número de página fica na margem de fora, a 81% da altura (ADR-0004, "Cabeçalho fora da
# faixa"). O percentil 1, e não o extremo: uma linha do corpo fora do lugar não desloca a mancha.
# A faixa fica junto da mancha, e não no lugar dela, para não mudar os livros já medidos: nos
# outros PDFs o cabeçalho cai na faixa, e a mancha sozinha mediria outra borda (C3 da auditoria).
PERCENTIL_DA_MANCHA = 0.01
# A mancha se mede pelas linhas largas, de pelo menos metade da largura mediana do corpo: o
# cabeçalho e o número do tamanho do corpo, um por página, entrariam nela (R1 da auditoria).
FRACAO_DA_LARGURA = 0.5
# Acima da mancha é acima dela por mais que isto: o cabeçalho de tabela que abre a página, na
# altura do corpo (Hard Parts, "Advantage Disadvantage"), fica.
FOLGA_DA_MANCHA = 0.005
# A linha de fora da faixa é cabeçalho na metade de cima e rodapé na de baixo.
METADE_DA_PAGINA = 0.5
# Medido nos dois livros: cada cabeçalho tirado tinha um topo só (0,05 e 0,9252).
TOLERANCIA_DO_TOPO = 0.01
# Cabeçalho e número de página vêm no tamanho do corpo ou menores (7,5 e 9 pt contra 10,5).
FOLGA_DA_FONTE = 0.5
# A linha do corpo, na mancha, é a que fica a menos disto do tamanho do corpo.
TOLERANCIA_DO_CORPO = 0.5
# Sem o ponto: "1.2" virava 12 e passava por número de página (revisão nº 5).
_SEPARADORES = re.compile(r"[\s|\u00b7\u2022\-\u2013\u2014]")
_ARABICO = re.compile(r"[0-9]{1,5}")
_ROMANO = re.compile(r"M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})")
_LETRA = re.compile(r"[^\W\d_]")
# Data com hora, já sem os espaços: "27/09/2017 20:12:36", com ou sem os segundos.
_CARIMBO = re.compile(r"\d{1,2}/\d{1,2}/\d{4}\d{1,2}:\d{2}(?::\d{2})?")
_VALOR_ROMANO = {"M": 1000, "D": 500, "C": 100, "L": 50, "X": 10, "V": 5, "I": 1}

type _Ocorrencia = tuple[int, int, Linha]
"""(número da página, posição da linha na página, linha)."""
type _Sequencia = tuple[str, int, float | None]
"""(sistema, deslocamento entre o número impresso e a página, tamanho do número grande)."""


@dataclass(frozen=True)
class LinhaRemovida:
    pagina: int
    motivo: str
    texto: str


@dataclass(frozen=True)
class _Mancha:
    """Onde o corpo mora no livro: o alto dele e as duas margens, em fração e em pontos."""

    topo: float
    esquerda: float
    direita: float


@dataclass(frozen=True)
class PaginasLimpas:
    paginas: tuple[Pagina, ...]
    remocoes: tuple[LinhaRemovida, ...]


def tirar_cabecalhos_e_rodapes(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """Tira da borda o número de página que segue a paginação e a linha que se repete.

    `tirar_cabecalhos_e_rodapes(paginas)` devolve as páginas sem essas linhas e uma
    remoção registrada por linha tirada.
    """
    corpo = tamanho_do_corpo(paginas)
    limite = corpo + FOLGA_DA_FONTE
    na_borda, ao_lado = _candidatas(paginas, _mancha(paginas, corpo))
    numeros = _numeros_de_pagina([*na_borda, *ao_lado], limite)
    repetidas = _repetidas(
        o for o in na_borda if o[2].tamanho <= limite and (o[0], o[1]) not in numeros
    )
    na_altura = _na_altura_do_numero(na_borda, numeros, limite)
    motivos = dict.fromkeys(numeros, "número de página") | repetidas | na_altura
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


def _candidatas(
    paginas: Sequence[Pagina], mancha: _Mancha | None
) -> tuple[list[_Ocorrencia], list[_Ocorrencia]]:
    """(na borda, ao lado): as linhas na faixa da borda ou acima da mancha, que vão às duas
    regras, e as ao lado da mancha, que vão só à do número de página (R2 da auditoria).

    De qualquer tamanho: quem filtra a fonte é cada regra. Ao lado da coluna, a linha que se
    repete é do livro: a nota de margem, o "x" do eixo de uma figura.
    """
    na_borda: list[_Ocorrencia] = []
    ao_lado: list[_Ocorrencia] = []
    for pagina in paginas:
        for posicao, linha in enumerate(pagina.linhas):
            if _na_borda(linha) or _acima_da_mancha(linha, mancha):
                na_borda.append((pagina.numero, posicao, linha))
            elif _ao_lado_da_mancha(linha, mancha):
                ao_lado.append((pagina.numero, posicao, linha))
    return na_borda, ao_lado


def _na_altura_do_numero(
    na_borda: Sequence[_Ocorrencia], numeros: set[tuple[int, int]], limite: float
) -> dict[tuple[int, int], str]:
    """O cabeçalho maior que o corpo, que a regra da repetição não olha: a linha com letra na
    altura do número de página da mesma página, na letra dele, em 3 páginas ou mais (ADR-0004,
    "Cabeçalho na altura do número").

    No Manica, o título do livro e o do capítulo vêm em negrito de 10 pt, com o corpo de 9,3, na
    linha do número; o título do capítulo de 3 páginas aparece uma vez só. O número ao lado da
    coluna não serve de régua: na altura dele mora o corpo.
    """
    numeros_da_pagina: defaultdict[int, list[Linha]] = defaultdict(list)
    for pagina, posicao, linha in na_borda:
        if (pagina, posicao) in numeros:
            numeros_da_pagina[pagina].append(linha)
    achadas = [
        (pagina, posicao, linha)
        for pagina, posicao, linha in na_borda
        if (pagina, posicao) not in numeros
        and linha.tamanho > limite
        and _LETRA.search(linha.texto)
        and any(_na_linha_do_numero(linha, numero) for numero in numeros_da_pagina[pagina])
    ]
    if len({pagina for pagina, _, _ in achadas}) < PAGINAS_MINIMAS:
        return {}
    return {
        (pagina, posicao): f"{_lugar(linha)} de página na altura do número"
        for pagina, posicao, linha in achadas
    }


def _na_linha_do_numero(linha: Linha, numero: Linha) -> bool:
    mesma_altura = abs(linha.topo - numero.topo) <= TOLERANCIA_DO_TOPO
    return mesma_altura and abs(linha.tamanho - numero.tamanho) <= FOLGA_DA_FONTE


def _lugar(linha: Linha) -> str:
    return "cabeçalho" if linha.topo < METADE_DA_PAGINA else "rodapé"


def _mancha(paginas: Sequence[Pagina], corpo: float) -> _Mancha | None:
    """A área do corpo no livro, pelo percentil das linhas largas do tamanho do corpo."""
    do_corpo = [
        linha
        for pagina in paginas
        for linha in pagina.linhas
        if abs(linha.tamanho - corpo) < TOLERANCIA_DO_CORPO
    ]
    if not do_corpo:
        return None
    minima = median(linha.fim - linha.x for linha in do_corpo) * FRACAO_DA_LARGURA
    largas = [linha for linha in do_corpo if linha.fim - linha.x >= minima]
    k = int(len(largas) * PERCENTIL_DA_MANCHA)
    topos = sorted(linha.topo for linha in largas)
    esquerdas = sorted(linha.x for linha in largas)
    direitas = sorted(linha.fim for linha in largas)
    return _Mancha(topos[k], esquerdas[k], direitas[-1 - k])


def _acima_da_mancha(linha: Linha, mancha: _Mancha | None) -> bool:
    return mancha is not None and linha.topo < mancha.topo - FOLGA_DA_MANCHA


def _ao_lado_da_mancha(linha: Linha, mancha: _Mancha | None) -> bool:
    return mancha is not None and (linha.fim < mancha.esquerda or linha.x > mancha.direita)


def _na_borda(linha: Linha) -> bool:
    return linha.topo < FAIXA_DA_BORDA or linha.topo > 1 - FAIXA_DA_BORDA


def _numeros_de_pagina(candidatas: Sequence[_Ocorrencia], limite: float) -> set[tuple[int, int]]:
    """Os números cujo deslocamento em relação à página se repete em 3 páginas ou mais.

    No Competente, o número impresso é a página - 7 em 398 de 398; no Hard Parts, - 18 em
    429 de 433. Um número sozinho ("2020.", "1.", "mix") não prova sequência e fica.
    """
    impressos: list[tuple[int, int, _Sequencia]] = []
    for pagina, posicao, linha in candidatas:
        lido = _numero_impresso(linha.texto)
        if lido is not None:
            sequencia = (lido[0], lido[1] - pagina, _tamanho_da_sequencia(linha, limite))
            impressos.append((pagina, posicao, sequencia))
    # Conta páginas, não ocorrências: o número no alto e no pé da mesma página vale uma vez.
    paginas_por_sequencia: defaultdict[_Sequencia, set[int]] = defaultdict(set)
    for pagina, _, sequencia in impressos:
        paginas_por_sequencia[sequencia].add(pagina)
    coerentes = {
        chave for chave, paginas in paginas_por_sequencia.items() if len(paginas) >= PAGINAS_MINIMAS
    }
    return {(p, posicao) for p, posicao, sequencia in impressos if sequencia in coerentes}


def _tamanho_da_sequencia(linha: Linha, limite: float) -> float | None:
    """None para o número com fonte de rodapé, que se conta junto, de qualquer tamanho.

    O maior que o corpo se conta só com os do mesmo tamanho (ADR-0004, "Número de página
    maior que o corpo"): no Dalgalarrondo, os 412 números de página têm 12 pt, com o corpo de
    10; o "3" de 48 pt de uma abertura de capítulo, sozinho no tamanho dele, não faz sequência
    e fica (A1 da auditoria).
    """
    return None if linha.tamanho <= limite else round(linha.tamanho, 1)


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
    """A linha que se repete no mesmo topo em 3 páginas ou mais, ou nas 2 de uma abertura, com o
    motivo de cada uma."""
    motivos: dict[tuple[int, int], str] = {}
    for (chave, _), ocorrencias in _grupos(candidatas).items():
        com_letra = _LETRA.search(chave) is not None
        for mesma_altura in _por_altura(ocorrencias):
            paginas = {pagina for pagina, _, _ in mesma_altura}
            if not _cabecalho_corrente(paginas, com_letra=com_letra):
                continue
            for pagina, posicao, linha in mesma_altura:
                motivos[pagina, posicao] = f"{_lugar(linha)} de página repetido"
    return motivos


def _grupos(candidatas: Iterable[_Ocorrencia]) -> dict[tuple[str, bool], list[_Ocorrencia]]:
    """As ocorrências pela chave do texto e pela faixa, alto ou pé."""
    # Alto e pé em grupos separados: com o título no alto das pares e no pé das ímpares, a
    # mediana do grupo inteiro caía no meio da página e nada saía (revisão nº 3).
    grupos: defaultdict[tuple[str, bool], list[_Ocorrencia]] = defaultdict(list)
    for ocorrencia in candidatas:
        chave = _chave(ocorrencia[2].texto)
        # O1: sem letra, o "#" juntaria números diferentes ("2020.", "1999.", "1984.") num
        # rodapé falso. A chave vira o texto literal: só o mesmo rodapé em toda página sai
        # ("2021", "© 2020", uma data; A3 da auditoria).
        # O carimbo da gráfica, que muda a cada página, se agrupa pela forma (ADR-0004, "Cabeçalho
        # na altura do número"): "27/09/2017 20:12:36" no pé das páginas do Manica.
        literal = "".join(ocorrencia[2].texto.split())
        if not _LETRA.search(chave) and not _CARIMBO.fullmatch(literal):
            chave = literal
        grupos[chave, ocorrencia[2].topo < METADE_DA_PAGINA].append(ocorrencia)
    return grupos


def _cabecalho_corrente(paginas: set[int], *, com_letra: bool) -> bool:
    """3 páginas ou mais, ou 2 vizinhas, se a linha tem letra: a pausa de cena ("* * *") no alto
    de duas páginas seguidas é texto do livro (R2 da code-review)."""
    vizinhas = len(paginas) == PAGINAS_VIZINHAS and max(paginas) - min(paginas) == 1
    return len(paginas) >= PAGINAS_MINIMAS or (vizinhas and com_letra)


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
