# SPDX-License-Identifier: GPL-3.0-or-later
"""Das linhas do PDF aos blocos do livro: título, parágrafo, código e nota (ADR-0004).

As regras vêm da medição no Competente (pt-BR) e no Hard Parts (en):
- parágrafo novo quando a linha recua em relação ao parágrafo (Competente: recuo de 13 pt) ou
  quando o espaço acima dela passa de 1,35 entrelinha (Hard Parts: 0,028 contra 0,019);
- o tipo da linha (título, parágrafo, código ou nota) vem da fonte, em `tipo_da_linha.py`;
- o verbete (linha toda em negrito menor que o corpo) abre parágrafo depois de frase fechada, e
  a linha comum seguinte abre outro: o termo do glossário sai fora da definição (Competente);
- a palavra partida no fim da linha volta inteira, a não ser que o livro escreva a mesma
  palavra com hífen em outro lugar (`non-productive`, `anti-pattern`);
- o quadro abre no rótulo ("Quadro 5.1") e entra na leitura depois da frase que ele interrompe
  (Dalgalarrondo; ADR-0004, "Quadro no lugar").
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import final

from earbook.dominio.colunas import linhas_visuais
from earbook.dominio.hifen_da_quebra import Dicionario, dicionario_do_livro, no_dicionario
from earbook.dominio.pagina import (
    DIFERENCA_DE_TAMANHO,
    HIFEN_SUAVE,
    RAZAO_DO_TITULO,
    Linha,
    Pagina,
    comeca_em_minuscula,
    so_maiusculas,
)
from earbook.dominio.quadro import abre_o_quadro, letra_de_quadro, solta_o_quadro
from earbook.dominio.tipo_da_linha import Medidas, TipoDeBloco, medir, tipo_da_linha

RAZAO_DO_ESPACO = 1.35
RECUO_MINIMO = 3.0
"""Em pontos. Medido: parágrafo recua 13 (Competente) e 18 (Hard Parts); item de lista, 4 e 5;
nenhuma linha de corpo entre 1 e 3."""
# Com 3 pedaços ou mais na mesma altura, é linha de tabela; com 2, linha justificada partida.
CELULAS_DA_TABELA = 3
_FIM_DE_FRASE = tuple('.!?:\u201d"')
_HIFEN_NO_FIM = re.compile(r"\w[-\u2010]$")
_NUMERO_NO_HIFEN = re.compile(r"\d[-\u2010]$")
# Norma brasileira: o hífen do composto se repete no começo da linha de baixo.
_HIFEN_REPETIDO = re.compile(r"[-\u2010][^\W\d_]")
# Fecha a frase para a regra do recuo. A aspa de fechamento não: "uma “transformação”"
# seguia na linha de baixo no Competente.
_FECHA_PARA_O_RECUO = tuple(".!?:;")
# Item de lista: travessão, meia-risca, bolinha, hífen ou "3.", seguido de espaço. Até dois
# algarismos, para "2020. Depois…" no começo da linha não contar como item.
_ITEM_DE_LISTA = re.compile(r"(?:[\u2013\u2014\u2022\-]|\d{1,2}\.)\s")


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
    capitulo: str = ""
    """No primeiro bloco do capítulo, o nome que o sumário interno do PDF dá a ele (ADR-0004,
    "Capítulos pelo sumário interno do PDF"); vazio nos outros e no livro sem sumário interno."""


@dataclass(frozen=True)
class LivroMontado:
    blocos: tuple[Bloco, ...]
    hifens_tirados: int
    hifens_mantidos: int


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
    versalete: bool = False
    """Título em versalete: a linha seguinte só em maiúsculas, do mesmo tamanho, o continua."""
    quadro: bool = False
    """Bloco de quadro: espera em `_Montador._quadro` e não mexe na retomada do texto."""


def montar_blocos(
    paginas: Sequence[Pagina], prova_do_hifen: Sequence[Pagina] | None = None
) -> LivroMontado:
    """Junta as linhas, página por página e de cima para baixo, em blocos do livro.

    O dicionário do hífen vem de `prova_do_hifen`, se dada: o índice e a tabela que não se leem
    ainda provam que o livro escreve "east-west" (ADR-0004, "Tratado médico").
    """
    medidas = medir(paginas)
    montador = _Montador(medidas, dicionario_do_livro(prova_do_hifen or paginas))
    for pagina in paginas:
        anterior: Linha | None = None
        for linha, pedacos in linhas_visuais(pagina.linhas, medidas.corpo):
            montador.acrescentar(pagina.numero, linha, anterior, pedacos)
            anterior = linha
    return montador.livro()


def _virou_a_coluna(linha: Linha, anterior: Linha | None) -> bool:
    """A linha sobe na página: é a primeira da coluna seguinte (ADR-0004, "Duas colunas")."""
    return anterior is not None and linha.topo < anterior.topo


@final
class _Montador:
    def __init__(self, medidas: Medidas, dicionario: Dicionario) -> None:
        self._medidas = medidas
        self._dicionario = dicionario
        self._prontos: list[Bloco] = []
        self._aberto: _Aberto | None = None
        self._hifens_tirados = 0
        self._hifens_mantidos = 0
        # Parágrafo fechado sem terminar a frase, seguido só de nota, código ou quadro: a linha
        # minúscula que vier depois o retoma (legenda no meio do parágrafo, Competente p. 33).
        self._interrompido: tuple[_Aberto, int] | None = None
        self._posicao_do_aberto: int | None = None
        # Os blocos do quadro esperam a frase que ele interrompe acabar (ADR-0004, "Quadro no
        # lugar"): entram antes do próximo título ou parágrafo do corpo que abre frase.
        self._no_quadro = False
        self._quadro: list[Bloco] = []

    def acrescentar(self, pagina: int, linha: Linha, anterior: Linha | None, pedacos: int) -> None:
        tipo, saiu_do_quadro = self._tipo(linha)
        de_tabela = tipo is TipoDeBloco.PARAGRAFO and pedacos >= CELULAS_DA_TABELA
        aberto = self._aberto
        retoma = tipo is TipoDeBloco.PARAGRAFO and not de_tabela and not self._no_quadro
        if retoma and self._retomar(linha, saiu_do_quadro=saiu_do_quadro):
            return
        if (
            de_tabela
            or aberto is None
            or aberto.tipo is not tipo
            or aberto.quadro is not self._no_quadro
            or self._quebra(aberto, linha, anterior)
        ):
            self._abrir(pagina, linha, tipo, tabela=de_tabela)
        else:
            if _virou_a_coluna(linha, anterior):
                aberto.x_do_corpo = linha.x
            self._continuar(aberto, linha)

    def _abrir(self, pagina: int, linha: Linha, tipo: TipoDeBloco, *, tabela: bool) -> None:
        """Fecha o bloco aberto, solta o quadro que espera, se for a hora, e abre outro."""
        self._fechar()
        self._soltar_o_quadro(linha, tipo)
        negrito = tipo is TipoDeBloco.PARAGRAFO and self._verbete(linha)
        self._aberto = _Aberto(
            tipo,
            pagina,
            linha.tamanho,
            [linha.texto],
            linha.x,
            tabela=tabela,
            negrito=negrito,
            versalete=linha.versalete,
            quadro=self._no_quadro,
        )

    def livro(self) -> LivroMontado:
        self._fechar()
        self._prontos.extend(self._quadro)
        return LivroMontado(tuple(self._prontos), self._hifens_tirados, self._hifens_mantidos)

    def _tipo(self, linha: Linha) -> tuple[TipoDeBloco, bool]:
        """O tipo da linha, com o versalete que continua e o quadro, e se ela fecha o quadro."""
        medidas = self._medidas
        tipo = tipo_da_linha(linha, medidas.corpo, negrito_destaca=medidas.negrito_destaca)
        return self._no_quadro_ou_fora(linha, self._continua_o_versalete(linha, tipo))

    def _continua_o_versalete(self, linha: Linha, tipo: TipoDeBloco) -> TipoDeBloco:
        """A segunda linha do versalete não tem letra maior ("PERSONALIDADE PARANÓIDE",
        Dalgalarrondo p. 270): a linha de nota só em maiúsculas, do tamanho do título em
        versalete aberto, o continua."""
        aberto = self._aberto
        continua = (
            tipo is TipoDeBloco.NOTA
            and aberto is not None
            and aberto.versalete
            and so_maiusculas(linha.texto)
            and abs(linha.tamanho - aberto.tamanho) <= DIFERENCA_DE_TAMANHO
        )
        return TipoDeBloco.TITULO if continua else tipo

    def _no_quadro_ou_fora(self, linha: Linha, tipo: TipoDeBloco) -> tuple[TipoDeBloco, bool]:
        """O tipo da linha e se ela fecha o quadro (`dominio/quadro.py`). A letra menor do quadro
        é o conteúdo dele, e não nota, que iria para "Notas" (ADR-0005)."""
        rotulo = abre_o_quadro(linha, titulo=tipo is TipoDeBloco.TITULO)
        segue = rotulo or (self._no_quadro and letra_de_quadro(linha, self._medidas.corpo))
        saiu, self._no_quadro = self._no_quadro and not segue, segue
        return (TipoDeBloco.PARAGRAFO if segue and tipo is TipoDeBloco.NOTA else tipo), saiu

    def _soltar_o_quadro(self, linha: Linha, tipo: TipoDeBloco) -> None:
        """Os blocos do quadro entram na leitura quando a frase que ele interrompe acaba."""
        titulo, paragrafo = tipo is TipoDeBloco.TITULO, tipo is TipoDeBloco.PARAGRAFO
        solta = solta_o_quadro(linha, self._medidas.corpo, titulo=titulo, paragrafo=paragrafo)
        if solta and not self._no_quadro:
            self._prontos.extend(self._quadro)
            self._quadro.clear()

    def _quebra(self, aberto: _Aberto, linha: Linha, anterior: Linha | None) -> bool:
        """A linha começa bloco novo, embora seja do mesmo tipo do bloco aberto?"""
        if aberto.tipo is TipoDeBloco.TITULO:
            return self._quebra_o_titulo(aberto, linha, anterior)
        if aberto.tipo is not TipoDeBloco.PARAGRAFO:
            return anterior is None and aberto.tipo is TipoDeBloco.NOTA
        return self._quebra_o_paragrafo(aberto, linha, anterior)

    def _quebra_o_paragrafo(self, aberto: _Aberto, linha: Linha, anterior: Linha | None) -> bool:
        # O termo do glossário acaba onde a letra deixa de ser negrito (Competente p. 479:
        # "Tokenizador A parte do modelo…"). ADR-0004, "Verbete em negrito abaixo do corpo".
        fim_do_verbete = aberto.negrito and not self._verbete(linha)
        if aberto.tabela or fim_do_verbete:
            return True
        if _virou_a_coluna(linha, anterior):
            return self._quebra_na_virada(aberto, linha)
        if self._mudou_o_recuo(aberto, linha):
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
    def _quebra_na_virada(aberto: _Aberto, linha: Linha) -> bool:
        """A margem da coluna nova não se compara com a do parágrafo na coluna de antes: o item
        que vira de coluna se partia no ponto. A virada é como a de página (ADR-0004, "Duas
        colunas"), a não ser que a letra mude: o destaque de margem de 9 pt, ao lado do texto de
        10 pt, colava na frase dele (ADR-0004, "Destaque de margem na virada de coluna").
        """
        if abs(linha.tamanho - aberto.tamanho) > DIFERENCA_DE_TAMANHO:
            return True
        item = _ITEM_DE_LISTA.match(linha.texto) is not None
        return item or _Montador._comeca_frase_na_pagina_nova(aberto, linha)

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
        elif _NUMERO_NO_HIFEN.search(aberto.partes[-1]) and linha.texto[:1].isdigit():
            # O número partido na quebra ("tabla 6-" | "1", "684-" | "696", Miller) volta inteiro.
            aberto.partes.append(linha.texto)
            self._hifens_mantidos += 1
        else:
            aberto.partes.append(" " + linha.texto)

    def _depois_do_hifen(self, aberto: _Aberto, texto: str) -> str:
        """Tira o hífen da quebra, a não ser que o livro use a palavra com hífen."""
        antes = aberto.partes[-1].rsplit(maxsplit=1)[-1]
        depois = texto.split(maxsplit=1)[0]
        if self._dicionario.mantem_o_hifen(no_dicionario(antes[:-1]), no_dicionario(depois)):
            self._hifens_mantidos += 1
            return texto
        self._hifens_tirados += 1
        aberto.partes[-1] = aberto.partes[-1][:-1]
        return texto

    def _retomar(self, linha: Linha, *, saiu_do_quadro: bool) -> bool:
        """Retoma o parágrafo interrompido por nota, código ou quadro, se a linha o continua."""
        if self._interrompido is None or self._aberto is None:
            return False
        # Revisão nº 1: só nota, código e quadro interrompem. Com título aberto, a linha colava no
        # parágrafo de antes dele, e o título ia parar depois do texto.
        nota_ou_codigo = self._aberto.tipo in {TipoDeBloco.NOTA, TipoDeBloco.CODIGO}
        interrompe = saiu_do_quadro or nota_ou_codigo
        if not interrompe or not comeca_em_minuscula(linha.texto):
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
        if aberto.quadro:
            self._quadro.append(bloco)
            return
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
