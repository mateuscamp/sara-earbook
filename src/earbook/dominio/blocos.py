# SPDX-License-Identifier: GPL-3.0-or-later
"""Das linhas do PDF aos blocos do livro: título, parágrafo, código e nota (ADR-0004).

As regras vêm da medição no Competente (pt-BR) e no Hard Parts (en):
- parágrafo novo quando a linha recua em relação ao parágrafo (Competente: recuo de 13 pt) ou
  quando o espaço acima dela passa de 1,35 entrelinha (Hard Parts: 0,028 contra 0,019);
- título é fonte de 1,2 vez o corpo ou mais, ou linha toda em negrito do tamanho do corpo para
  cima (subtítulo do Competente); código é linha toda monoespaçada; nota é fonte menor que
  0,85 do corpo;
- o verbete (linha toda em negrito menor que o corpo) abre parágrafo depois de frase fechada, e
  a linha comum seguinte abre outro: o termo do glossário sai fora da definição (Competente);
- a palavra partida no fim da linha volta inteira, a não ser que o livro escreva a mesma
  palavra com hífen em outro lugar (`non-productive`, `anti-pattern`).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from itertools import pairwise
from typing import final

from earbook.dominio.pagina import Linha, Pagina, corpo_em_negrito, tamanho_do_corpo

RAZAO_DO_TITULO = 1.2
RAZAO_DA_NOTA = 0.85
RAZAO_DO_ESPACO = 1.35
RECUO_MINIMO = 3.0
"""Em pontos. Medido: parágrafo recua 13 (Competente) e 18 (Hard Parts); item de lista, 4 e 5;
nenhuma linha de corpo entre 1 e 3."""
DIFERENCA_DE_TAMANHO = 0.5
# O subtítulo em negrito vai do corpo para cima, com esta folga: o cabeçalho de tabela do Hard
# Parts tem 10 pt, com corpo de 10,5; o cabeçalho de tabela menor e o rodapé de seção, 9 pt
# (ADR-0004).
FOLGA_DO_SUBTITULO = 0.5
# Linhas a menos disso de topo estão na mesma altura (células de tabela no Hard Parts: 0,001).
MESMA_ALTURA = 0.004
# Com 3 pedaços ou mais na mesma altura, é linha de tabela; com 2, linha justificada partida.
CELULAS_DA_TABELA = 3
_PONTUACAO_DA_PONTA = ".,;:!?\"'()[]\u201c\u201d\u2018\u2019"
_FIM_DE_FRASE = tuple('.!?:\u201d"')
_HIFEN_NO_FIM = re.compile(r"\w[-\u2010]$")
_PRIMEIRA_LETRA = re.compile(r"[^\W\d_]")
# Norma brasileira: o hífen do composto se repete no começo da linha de baixo.
_HIFEN_REPETIDO = re.compile(r"[-\u2010][^\W\d_]")
# Fecha a frase para a regra do recuo. A aspa de fechamento não: "uma “transformação”"
# seguia na linha de baixo no Competente.
_FECHA_PARA_O_RECUO = tuple(".!?:;")
# Item de lista: travessão, meia-risca, bolinha, hífen ou "3.", seguido de espaço. Até dois
# algarismos, para "2020. Depois…" no começo da linha não contar como item.
_ITEM_DE_LISTA = re.compile(r"(?:[\u2013\u2014\u2022\-]|\d{1,2}\.)\s")
HIFEN_SUAVE = "\u00ad"
# O Hard Parts quebra a linha com o U+2010 (1.058 vezes) e nunca o usa no meio da linha;
# para o dicionário do livro, ele vale o mesmo que o "-".
HIFEN_TIPOGRAFICO = "\u2010"


class TipoDeBloco(StrEnum):
    TITULO = "titulo"
    PARAGRAFO = "paragrafo"
    CODIGO = "codigo"
    NOTA = "nota"


@dataclass(frozen=True)
class Bloco:
    tipo: TipoDeBloco
    texto: str
    pagina: int
    """Página do PDF onde o bloco começa."""
    tamanho: float
    """Tamanho da fonte da primeira linha, em pontos: decide o nível do título."""
    nivel: int = 0
    """Nível do título (1 = capítulo); 0 nos outros blocos."""


@dataclass(frozen=True)
class LivroMontado:
    blocos: tuple[Bloco, ...]
    hifens_tirados: int
    hifens_mantidos: int


@dataclass(frozen=True)
class _Dicionario:
    """O que o próprio livro diz sobre as palavras: decide o hífen da quebra de linha."""

    com_hifen: frozenset[str]
    """Escritas com hífen no meio da linha (`non-productive`)."""
    palavras: frozenset[str]
    """Escritas inteiras, sem hífen (`oriented`, `perguntou`)."""


@dataclass(frozen=True)
class _Medidas:
    corpo: float
    entrelinha: float
    negrito_destaca: bool
    """O corpo não é negrito: só então a linha toda em negrito é subtítulo."""


@dataclass
class _Aberto:
    """O bloco em montagem: o texto ainda cresce a cada linha."""

    tipo: TipoDeBloco
    pagina: int
    tamanho: float
    partes: list[str]
    x_da_primeira: float
    x_do_corpo: float | None = None
    tabela: bool = False
    """Recebeu célula na mesma altura: é linha de tabela, e a próxima altura abre outra."""
    negrito: bool = False
    """Parágrafo aberto por linha toda em negrito: é verbete, e a 1ª linha comum abre outro."""


def montar_blocos(paginas: Sequence[Pagina]) -> LivroMontado:
    """Junta as linhas, página por página e de cima para baixo, em blocos do livro."""
    montador = _Montador(_medir(paginas), _dicionario(paginas))
    for pagina in paginas:
        anterior: Linha | None = None
        for linha, pedacos in _linhas_visuais(pagina.linhas):
            montador.acrescentar(pagina.numero, linha, anterior, pedacos)
            anterior = linha
    return montador.livro()


def _comeca_em_minuscula(texto: str) -> bool:
    letra = _PRIMEIRA_LETRA.search(texto)
    return letra is not None and letra.group().islower()


def _linhas_visuais(linhas: Sequence[Linha]) -> list[tuple[Linha, int]]:
    """Junta os pedaços na mesma altura numa linha só, de cima para baixo e da esquerda.

    O pdfminer parte linha justificada ("…communication patterns" e "in", Hard Parts p. 60)
    e devolve cada célula de tabela como linha própria. O número de pedaços vai junto: com
    3 ou mais, é linha de tabela.
    """
    alturas: list[list[Linha]] = []
    for linha in sorted(linhas, key=lambda linha: linha.topo):
        if alturas and abs(linha.topo - alturas[-1][0].topo) < MESMA_ALTURA:
            alturas[-1].append(linha)
        else:
            alturas.append([linha])
    visuais: list[tuple[Linha, int]] = []
    # Revisão nº 2: ordenar por (topo, x) punha primeiro o pedaço da direita que ficasse um
    # pouco mais alto (618 vezes no Hard Parts). A ordem dentro da altura é só a do x.
    for altura in alturas:
        pedacos = sorted(altura, key=lambda linha: linha.x)
        juntas = replace(
            pedacos[0],
            texto=" ".join(pedaco.texto for pedaco in pedacos),
            monoespacada=all(pedaco.monoespacada for pedaco in pedacos),
            negrito=all(pedaco.negrito for pedaco in pedacos),
        )
        visuais.append((juntas, len(pedacos)))
    return visuais


def _tipo(linha: Linha, corpo: float, *, negrito_destaca: bool) -> TipoDeBloco:
    if linha.monoespacada:
        return TipoDeBloco.CODIGO
    if linha.tamanho >= corpo * RAZAO_DO_TITULO:
        return TipoDeBloco.TITULO
    if linha.tamanho < corpo * RAZAO_DA_NOTA:
        return TipoDeBloco.NOTA
    # O subtítulo em negrito tem o tamanho do corpo ou mais (Competente: 10,5 e 12 pt, com
    # corpo de 10,5). O negrito menor fica parágrafo: é verbete do glossário (Competente: 9,5
    # pt), que o `_quebra` separa da definição, ou cabeçalho de tabela e rodapé de seção (Hard
    # Parts: 9 pt). ADR-0004, "Subtítulo em negrito do tamanho do corpo", com os limites.
    if negrito_destaca and linha.negrito and linha.tamanho >= corpo - FOLGA_DO_SUBTITULO:
        return TipoDeBloco.TITULO
    return TipoDeBloco.PARAGRAFO


def _medir(paginas: Sequence[Pagina]) -> _Medidas:
    """O corpo e a entrelinha mais comum entre linhas de corpo seguidas da mesma página."""
    corpo = tamanho_do_corpo(paginas)
    destaca = not corpo_em_negrito(paginas, corpo)
    distancias: Counter[float] = Counter()
    for pagina in paginas:
        corpo_da_pagina = sorted(
            (
                linha
                for linha in pagina.linhas
                if _tipo(linha, corpo, negrito_destaca=destaca) is TipoDeBloco.PARAGRAFO
            ),
            key=lambda linha: linha.topo,
        )
        for de_cima, de_baixo in pairwise(corpo_da_pagina):
            distancia = round(de_baixo.topo - de_cima.topo, 3)
            if distancia > 0:
                distancias[distancia] += 1
    entrelinha = distancias.most_common(1)[0][0] if distancias else 0.0
    return _Medidas(corpo, entrelinha, destaca)


def _dicionario(paginas: Sequence[Pagina]) -> _Dicionario:
    """As palavras do livro, com e sem hífen no meio: o dicionário do hífen da quebra."""
    com_hifen: set[str] = set()
    inteiras: set[str] = set()
    for pagina in paginas:
        for linha in pagina.linhas:
            for palavra in linha.texto.split():
                limpa = _no_dicionario(palavra)
                if "-" in limpa.strip("-"):
                    com_hifen.add(limpa)
                elif limpa.isalpha():
                    inteiras.add(limpa)
    return _Dicionario(frozenset(com_hifen), frozenset(inteiras))


def _no_dicionario(palavra: str) -> str:
    """A forma que o dicionário do hífen guarda: sem pontuação na ponta, com "-", minúscula."""
    return palavra.strip(_PONTUACAO_DA_PONTA).replace(HIFEN_TIPOGRAFICO, "-").casefold()


@final
class _Montador:
    def __init__(self, medidas: _Medidas, dicionario: _Dicionario) -> None:
        self._medidas = medidas
        self._dicionario = dicionario
        self._prontos: list[Bloco] = []
        self._aberto: _Aberto | None = None
        self._hifens_tirados = 0
        self._hifens_mantidos = 0
        # Parágrafo fechado sem terminar a frase, seguido só de nota ou código: a linha
        # minúscula que vier depois o retoma (legenda no meio do parágrafo, Competente p. 33).
        self._interrompido: tuple[_Aberto, int] | None = None
        self._posicao_do_aberto: int | None = None

    def acrescentar(self, pagina: int, linha: Linha, anterior: Linha | None, pedacos: int) -> None:
        medidas = self._medidas
        tipo = _tipo(linha, medidas.corpo, negrito_destaca=medidas.negrito_destaca)
        de_tabela = tipo is TipoDeBloco.PARAGRAFO and pedacos >= CELULAS_DA_TABELA
        aberto = self._aberto
        if tipo is TipoDeBloco.PARAGRAFO and not de_tabela and self._retomar(linha):
            return
        if (
            de_tabela
            or aberto is None
            or aberto.tipo is not tipo
            or self._quebra(aberto, linha, anterior)
        ):
            self._fechar()
            negrito = tipo is TipoDeBloco.PARAGRAFO and self._verbete(linha)
            self._aberto = _Aberto(
                tipo,
                pagina,
                linha.tamanho,
                [linha.texto],
                linha.x,
                tabela=de_tabela,
                negrito=negrito,
            )
        else:
            self._continuar(aberto, linha)

    def livro(self) -> LivroMontado:
        self._fechar()
        return LivroMontado(tuple(self._prontos), self._hifens_tirados, self._hifens_mantidos)

    def _quebra(self, aberto: _Aberto, linha: Linha, anterior: Linha | None) -> bool:
        """A linha começa bloco novo, embora seja do mesmo tipo do bloco aberto?"""
        if aberto.tipo is TipoDeBloco.TITULO:
            return self._quebra_o_titulo(aberto, linha, anterior)
        if aberto.tipo is not TipoDeBloco.PARAGRAFO:
            return anterior is None and aberto.tipo is TipoDeBloco.NOTA
        # O termo do glossário acaba onde a letra deixa de ser negrito (Competente p. 479:
        # "Tokenizador A parte do modelo…"). ADR-0004, "Verbete em negrito abaixo do corpo".
        fim_do_verbete = aberto.negrito and not self._verbete(linha)
        if aberto.tabela or fim_do_verbete or self._mudou_o_recuo(aberto, linha):
            return True
        # Hard Parts p. 45: itens a 1,32 entrelinha um do outro passavam abaixo do limiar.
        if _ITEM_DE_LISTA.match(linha.texto):
            return True
        if anterior is None:
            return self._comeca_frase_na_pagina_nova(aberto, linha)
        return linha.topo - anterior.topo >= self._medidas.entrelinha * RAZAO_DO_ESPACO

    def _quebra_o_titulo(self, aberto: _Aberto, linha: Linha, anterior: Linha | None) -> bool:
        """Título novo no tamanho que muda e na página nova.

        O título da faixa do subtítulo, abaixo de 1,2 vez o corpo, quebra também como o
        parágrafo: no item de lista (revisão nº 2) e no vão (A1 da auditoria: "A.", "B.", "C."
        e "Index" do sumário do Hard Parts saíam num título só). O título grande não: "CAPÍTULO
        1", linha em branco, "O começo" é um título e um capítulo (N1 da pós-auditoria).
        """
        if anterior is None or abs(linha.tamanho - aberto.tamanho) > DIFERENCA_DE_TAMANHO:
            return True
        if aberto.tamanho >= self._medidas.corpo * RAZAO_DO_TITULO:
            return False
        if _ITEM_DE_LISTA.match(linha.texto):
            return True
        # Sem entrelinha medida, o vão não tem régua, e o subtítulo segue junto.
        entrelinha = self._medidas.entrelinha
        return bool(entrelinha) and linha.topo - anterior.topo >= entrelinha * RAZAO_DO_ESPACO

    def _mudou_o_recuo(self, aberto: _Aberto, linha: Linha) -> bool:
        # Recuo só separa parágrafo se a linha de cima fechou a frase. Senão é item de lista
        # com recuo deslocado (x 58 e depois 70) ou texto que contorna figura (x 114 e
        # depois 72, Hard Parts p. 60), e a frase continua.
        if not aberto.partes[-1].rstrip().endswith(_FECHA_PARA_O_RECUO):
            return False
        if aberto.x_do_corpo is None:
            # Voltar à margem é a 2ª linha do parágrafo de 1ª linha recuada; o verbete depois de
            # linha comum, não (Competente p. 475: "Prompt" tem definição de uma linha só).
            verbete_novo = self._verbete(linha) and not aberto.negrito
            return verbete_novo or linha.x >= aberto.x_da_primeira + RECUO_MINIMO
        # Na margem do parágrafo, até o verbete segue: é o título da obra em negrito no meio
        # da referência ("(EMNLP 2024)." e "Proceedings of…", Competente p. 493).
        return abs(linha.x - aberto.x_do_corpo) >= RECUO_MINIMO

    @staticmethod
    def _comeca_frase_na_pagina_nova(aberto: _Aberto, linha: Linha) -> bool:
        """Sem recuo, só o fim de frase seguido de maiúscula separa parágrafo na virada."""
        return aberto.partes[-1].endswith(_FIM_DE_FRASE) and linha.texto[:1].isupper()

    def _verbete(self, linha: Linha) -> bool:
        """A linha de parágrafo toda em negrito, num livro de corpo regular: é verbete."""
        return self._medidas.negrito_destaca and linha.negrito

    def _continuar(self, aberto: _Aberto, linha: Linha) -> None:
        if aberto.x_do_corpo is None:
            aberto.x_do_corpo = linha.x
        if aberto.tipo is TipoDeBloco.CODIGO:
            aberto.partes.append("\n" + linha.texto)
        elif aberto.partes[-1].endswith(HIFEN_SUAVE):
            # O hífen suave (U+00AD) é sempre de quebra de linha: sai sem consultar o livro.
            aberto.partes[-1] = aberto.partes[-1][:-1]
            aberto.partes.append(linha.texto)
            self._hifens_tirados += 1
        elif _HIFEN_NO_FIM.search(aberto.partes[-1]) and _HIFEN_REPETIDO.match(linha.texto):
            aberto.partes.append(linha.texto[1:])
            self._hifens_mantidos += 1
        elif _HIFEN_NO_FIM.search(aberto.partes[-1]) and linha.texto[:1].islower():
            aberto.partes.append(self._depois_do_hifen(aberto, linha.texto))
        else:
            aberto.partes.append(" " + linha.texto)

    def _depois_do_hifen(self, aberto: _Aberto, texto: str) -> str:
        """Tira o hífen da quebra, a não ser que o livro use a palavra com hífen."""
        antes = aberto.partes[-1].rsplit(maxsplit=1)[-1]
        depois = texto.split(maxsplit=1)[0]
        if self._mantem_o_hifen(_no_dicionario(antes[:-1]), _no_dicionario(depois)):
            self._hifens_mantidos += 1
            return texto
        self._hifens_tirados += 1
        aberto.partes[-1] = aberto.partes[-1][:-1]
        return texto

    def _mantem_o_hifen(self, antes: str, depois: str) -> bool:
        """`antes` e `depois` são as metades da palavra partida, já sem o hífen da quebra."""
        if "-" not in antes and "-" not in depois:
            return f"{antes}-{depois}" in self._dicionario.com_hifen
        # A2 da auditoria: palavra que já tem outro hífen ("--no-agent-state", "proof-of-
        # concepts") é composta, e a quebra caiu num hífen dela. A não ser que as metades
        # vizinhas à quebra formem palavra do livro: então caiu numa sílaba ("ser-" +
        # "vice-based", "pergun-" + "tou-me"; B2 da pós-auditoria).
        silaba = antes.rsplit("-", 1)[-1] + depois.split("-", 1)[0]
        return silaba not in self._dicionario.palavras

    def _retomar(self, linha: Linha) -> bool:
        """Retoma o parágrafo interrompido por nota ou código, se a linha o continua."""
        if self._interrompido is None or self._aberto is None:
            return False
        # Revisão nº 1: só nota e código interrompem. Com título aberto, a linha colava no
        # parágrafo de antes dele, e o título ia parar depois do texto.
        interrompe = self._aberto.tipo in {TipoDeBloco.NOTA, TipoDeBloco.CODIGO}
        if not interrompe or not _comeca_em_minuscula(linha.texto):
            return False
        interrompido, posicao = self._interrompido
        self._fechar()
        _ = self._prontos.pop(posicao)
        self._aberto, self._posicao_do_aberto = interrompido, posicao
        self._continuar(interrompido, linha)
        return True

    def _fechar(self) -> None:
        aberto = self._aberto
        self._aberto = None
        if aberto is None:
            return
        bloco = Bloco(aberto.tipo, "".join(aberto.partes), aberto.pagina, aberto.tamanho)
        posicao = len(self._prontos) if self._posicao_do_aberto is None else self._posicao_do_aberto
        self._prontos.insert(posicao, bloco)
        self._posicao_do_aberto = None
        if aberto.tipo is TipoDeBloco.PARAGRAFO and not aberto.tabela and not aberto.negrito:
            terminou = bloco.texto.rstrip().endswith(_FECHA_PARA_O_RECUO)
            self._interrompido = None if terminou else (aberto, posicao)
        elif aberto.tipo in {TipoDeBloco.PARAGRAFO, TipoDeBloco.TITULO}:
            # Tabela e verbete fecham a retomada, como o título: o verbete não fecha frase, e
            # a definição não cola nele nem no parágrafo de antes dele.
            self._interrompido = None
