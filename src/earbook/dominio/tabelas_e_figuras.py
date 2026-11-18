# SPDX-License-Identifier: GPL-3.0-or-later
"""A tabela e a figura do PDF saem do áudio pela letra (ADR-0004, "Tabela e figura pela letra").

A voz lia as células coluna a coluna ("Axis I Axis II … Regions Systems …") e os rótulos de
diagrama soltos ("Ca2+ Arginine p38 MAPK NOS…"). O sinal é a letra: no Practical o corpo é
AGaramondPro de 10 pt, e a tabela e a figura vêm noutras famílias (Gotham, MyriadPro,
HelveticaNeue, Helvetica); no Bonica, na letra do corpo, mas menor. Sai a corrida de linhas fora da
letra do corpo que tem um rótulo em inglês ("TABLE", "Table 3.1", "• Figure 2.1", "FIGURE 1.1",
"Fig. 4"): o rótulo, o número, o título, as células, a fonte, os rótulos do diagrama e a legenda.
A corrida atravessa a página (a tabela continua na seguinte) e para na primeira linha da letra do
corpo ou de título. A caixa em outra letra sem rótulo ("Key Points") fica.

O rótulo em português e em espanhol ("Figura 1.2", "Quadro 1.1", "Tabela 8.1", "TABLA 2-1",
"CUADRO 4-1") vale também, fora da letra de título (ADR-0004, "Tratado em português e em
espanhol"): em letra de título ele abre o Quadro que fica no lugar (`dominio/quadro.py`).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from earbook.dominio.pagina import (
    DIFERENCA_DE_TAMANHO,
    RAZAO_DO_TITULO,
    Linha,
    Pagina,
    corpo_em_negrito,
)
from earbook.dominio.paginacao import LinhaRemovida, PaginasLimpas
from earbook.dominio.rotulos import (
    FIGURA_LOCAL,
    ROTULO_DA_CAIXA,
    ROTULO_DA_FIGURA,
    ROTULO_DA_TABELA,
    TABELA_LOCAL,
)

MOTIVO_DA_TABELA = "tabela: rótulo e letra fora do corpo"
MOTIVO_DA_FIGURA = "figura e legenda: rótulo e letra fora do corpo"
MOTIVO_DO_TEXTO_GIRADO = "texto girado: tabela deitada e rótulo de lado"
_LETRA_DO_PAINEL = r"(?:[A-Z]|[a-h]|[IVX]{1,4})"
_LETRAS_DO_PAINEL = re.compile(rf"{_LETRA_DO_PAINEL}(?:\s+{_LETRA_DO_PAINEL})*")
LINHAS_DO_TITULO_DO_ROTULO = 6
"""O título em negrito do quadro, na letra do corpo, tem até 6 linhas (medido no Miller: de 1 a 5
nos 308 "CUADRO")."""
FOLGA_DO_DIAGRAMA = 0.25
"""Pontos: o rótulo do diagrama pode ter a letra da legenda, mas não maior."""
# A frase da linha de cima acabou: ponto, interrogação, exclamação ou dois-pontos, com aspa ou
# parêntese depois ("…National Library of Medicine.)").
_FECHA_FRASE = re.compile(r"[.!?:][\u201d\u2019\"')]*$")

type Posicao = tuple[int, int]
"""(índice da página, índice da linha)."""


def tirar_texto_girado(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """As páginas sem as linhas giradas, e uma remoção registrada por linha (ADR-0004, "Texto
    girado"). O pdfminer monta a linha na horizontal: a tabela deitada vira uma letra de cada
    coluna, e não há o que ler. O livro com metade das letras giradas ou mais é o próprio livro de
    lado, e não muda."""
    caracteres: Counter[bool] = Counter()
    for pagina in paginas:
        for linha in pagina.linhas:
            caracteres[linha.girada] += len(linha.texto)
    if caracteres[True] * 2 >= caracteres.total():
        return PaginasLimpas(tuple(paginas), ())
    saem = {
        (p, n): MOTIVO_DO_TEXTO_GIRADO
        for p, pagina in enumerate(paginas)
        for n, linha in enumerate(pagina.linhas)
        if linha.girada
    }
    return sem_as_linhas(paginas, saem)


def tirar_tabelas_e_figuras(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """As páginas sem as corridas de tabela e de figura, e uma remoção registrada por linha."""
    corpo = letra_do_corpo(paginas)
    if corpo is None:
        return PaginasLimpas(tuple(paginas), ())
    saem: dict[Posicao, str] = {}
    for corrida in corridas_fora_do_corpo(paginas, corpo):
        saem |= _da_corrida(paginas, corrida, corpo[1])
    return sem_as_linhas(paginas, saem)


def _da_corrida(
    paginas: Sequence[Pagina], corrida: list[Posicao], tamanho_do_corpo: float
) -> dict[Posicao, str]:
    """O que sai da corrida: a tabela, do rótulo em diante; a figura, em volta da legenda.

    A tabela acaba na página seguinte, onde a letra muda, e a corrida continua sendo examinada
    dali: a figura e a outra tabela que vêm depois, na mesma corrida, saem também (ADR-0004,
    "Camada do OCR sobre as figuras e chamada colada").
    """
    saem: dict[Posicao, str] = {}
    i = 0
    while i < len(corrida):
        p, n = corrida[i]
        anterior = paginas[p].linhas[n - 1] if n > 0 else None
        motivo = _rotulo(paginas[p].linhas[n], tamanho_do_corpo, anterior)
        if motivo == MOTIVO_DA_TABELA:
            tabela = _tabela(paginas, corrida[i:])
            saem |= dict.fromkeys(tabela, motivo)
            i += len(tabela)
            continue
        if motivo == MOTIVO_DA_FIGURA:
            saem |= dict.fromkeys(_figura(paginas, corrida, i), motivo)
        i += 1
    return saem


def _tabela(paginas: Sequence[Pagina], corrida: list[Posicao]) -> list[Posicao]:
    """Do rótulo em diante. Na página seguinte, a tabela continua só na letra que ela já usou: o
    crédito do autor em Gotham, no alto da página, não é célula (R2 da code-review). O rótulo de
    um quadro fecha a tabela: o "• Box 49.4" do Practical vem na letra das células (ADR-0004,
    "Figura pelo diagrama e quadro depois da tabela")."""
    letras: set[tuple[str, float]] = set()
    pagina_do_rotulo = corrida[0][0]
    saem: list[Posicao] = []
    for p, n in corrida:
        linha = paginas[p].linhas[n]
        letra = (linha.fonte, round(linha.tamanho, 1))
        if p != pagina_do_rotulo and letra not in letras:
            break
        if saem and ROTULO_DA_CAIXA.match(linha.texto):
            break
        letras.add(letra)
        saem.append((p, n))
    return saem


def _figura(paginas: Sequence[Pagina], corrida: list[Posicao], legenda: int) -> list[Posicao]:
    """A legenda e o que vem depois dela na página; antes dela, o diagrama."""
    p, n = corrida[legenda]
    saem: list[Posicao] = []
    for pos in corrida[legenda:]:
        # O quadro depois da legenda fica (ADR-0004, "Figura pelo diagrama e quadro depois da
        # tabela").
        if saem and ROTULO_DA_CAIXA.match(paginas[pos[0]].linhas[pos[1]].texto):
            break
        if pos[0] == p:
            saem.append(pos)
    antes = [pos for pos in corrida[:legenda] if pos[0] == p]
    return saem + _diagrama(paginas, antes, paginas[p].linhas[n])


def _diagrama(paginas: Sequence[Pagina], antes: list[Posicao], legenda: Linha) -> list[Posicao]:
    """O que vem antes da legenda, na página dela (`antes`), em letra não maior que a dela
    (Practical: 7 pt contra 8). A caixa de 9 pt logo antes fica (R3 da code-review). A letra do
    painel ("A B", 10 pt) é do diagrama em qualquer tamanho, e a letra maior na família de uma
    linha do diagrama já tirada também (o eixo de 8,3 pt e o título de 10 pt em Helvetica, com
    os rótulos de 7,6 pt), se não fecha frase. O rótulo do quadro fecha o diagrama (ADR-0004,
    "Figura pelo diagrama e quadro depois da tabela")."""
    saem: list[Posicao] = []
    familias: set[str] = set()
    for pos in reversed(antes):
        linha = paginas[pos[0]].linhas[pos[1]]
        maior = linha.tamanho > legenda.tamanho + FOLGA_DO_DIAGRAMA
        # O título e o eixo não fecham frase; a caixa de 9 pt na mesma família, sim (code-review).
        da_familia = linha.fonte in familias and _FECHA_FRASE.search(linha.texto) is None
        do_diagrama = _painel(linha) or da_familia
        if ROTULO_DA_CAIXA.match(linha.texto) or (maior and not do_diagrama):
            break
        if linha.fonte != legenda.fonte:
            familias.add(linha.fonte)
        saem.append(pos)
    return saem


def _painel(linha: Linha) -> bool:
    """Só letras de painel soltas, maiúsculas, minúsculas de "a" a "h" ou algarismos romanos: "A B
    C", "c d c d", "I I II II"."""
    return _LETRAS_DO_PAINEL.fullmatch(linha.texto.strip()) is not None


def letra_do_corpo(paginas: Sequence[Pagina]) -> tuple[str, float] | None:
    """A família e o tamanho com mais caracteres no livro; None se o PDF não diz a família."""
    letras: Counter[tuple[str, float]] = Counter()
    for pagina in paginas:
        for linha in pagina.linhas:
            letras[linha.fonte, round(linha.tamanho, 1)] += len(linha.texto)
    if not letras:
        return None
    familia, tamanho = letras.most_common(1)[0][0]
    return (familia, tamanho) if familia else None


def corridas_fora_do_corpo(
    paginas: Sequence[Pagina], corpo: tuple[str, float]
) -> list[list[Posicao]]:
    """As corridas de linhas seguidas fora da letra do corpo e da de título, no livro todo."""
    # No livro de corpo em negrito, a linha em negrito é a prosa, e não título de quadro.
    com_titulo_em_negrito = not corpo_em_negrito(paginas, corpo[1])
    corridas: list[list[Posicao]] = [[]]
    for p, pagina in enumerate(paginas):
        restam = 0  # o título do rótulo não passa de página
        for n, linha in enumerate(pagina.linhas):
            restam = _linhas_do_titulo(linha, corpo, restam) if com_titulo_em_negrito else 0
            if _fecha(linha, corpo) and not restam:
                corridas.append([])
            else:
                corridas[-1].append((p, n))
    return [corrida for corrida in corridas if corrida]


def _linhas_do_titulo(linha: Linha, corpo: tuple[str, float], restam: int) -> int:
    """Quantas linhas o título do rótulo ainda pode ter, contando esta; 0 se ela não é dele.

    A linha toda em negrito, na letra do corpo, que abre com o rótulo em português ou em espanhol,
    e as linhas em negrito da mesma letra logo abaixo, não fecham a corrida: o título do quadro
    do Miller ("CUADRO 4-1 …", StoneSerif negrito de 9,5 pt, de 1 a 5 linhas). O limite é para o
    parágrafo de destaque em negrito que começa por uma menção não sair inteiro.
    """
    if not linha.negrito or not na_letra_do_corpo(linha, corpo):
        return 0
    if _rotulo_local(linha, corpo[1]) is not None:
        return LINHAS_DO_TITULO_DO_ROTULO
    return max(restam - 1, 0)


def na_letra_do_corpo(linha: Linha, corpo: tuple[str, float]) -> bool:
    """A família do corpo, no tamanho dele, com a folga de meio ponto."""
    familia, tamanho = corpo
    return linha.fonte == familia and abs(linha.tamanho - tamanho) <= DIFERENCA_DE_TAMANHO


def _fecha(linha: Linha, corpo: tuple[str, float]) -> bool:
    """A letra do corpo, ou a de título que não é rótulo, fecha a corrida."""
    tamanho = corpo[1]
    titulo = linha.tamanho >= tamanho * RAZAO_DO_TITULO and _rotulo(linha, tamanho) is None
    return na_letra_do_corpo(linha, corpo) or titulo


def _rotulo(linha: Linha, tamanho_do_corpo: float, anterior: Linha | None = None) -> str | None:
    """O motivo, se a linha abre com rótulo de tabela ou de figura. A linha que continua a frase
    da de cima, na mesma letra, é menção quebrada, e não rótulo ("…components in" | "Figure
    5-11.", na prosa em MyriadPro de 9 pt do Hard Parts)."""
    if anterior is not None and _continua_a_frase(anterior, linha):
        return None
    if ROTULO_DA_TABELA.match(linha.texto):
        return MOTIVO_DA_TABELA
    if ROTULO_DA_FIGURA.match(linha.texto):
        return MOTIVO_DA_FIGURA
    return _rotulo_local(linha, tamanho_do_corpo)


def _rotulo_local(linha: Linha, tamanho_do_corpo: float) -> str | None:
    """O rótulo em português ou em espanhol, fora da letra de título: nela, "Quadro 5.1" abre o
    quadro que fica no lugar (Dalgalarrondo, 12 pt com o corpo de 10; ADR-0004, "Quadro no
    lugar")."""
    if linha.tamanho >= tamanho_do_corpo * RAZAO_DO_TITULO:
        return None
    if TABELA_LOCAL.match(linha.texto):
        return MOTIVO_DA_TABELA
    if FIGURA_LOCAL.match(linha.texto):
        return MOTIVO_DA_FIGURA
    return None


def _continua_a_frase(anterior: Linha, linha: Linha) -> bool:
    """Na mesma letra, também no negrito: o rótulo em negrito embaixo de uma linha comum não a
    continua ("Glicogênio" | "FigurA 1.9", Manica)."""
    mesma_letra = (
        anterior.fonte == linha.fonte
        and anterior.negrito == linha.negrito
        and abs(anterior.tamanho - linha.tamanho) <= DIFERENCA_DE_TAMANHO
    )
    return mesma_letra and _FECHA_FRASE.search(anterior.texto) is None


def sem_as_linhas(paginas: Sequence[Pagina], saem: dict[Posicao, str]) -> PaginasLimpas:
    limpas: list[Pagina] = []
    remocoes: list[LinhaRemovida] = []
    for p, pagina in enumerate(paginas):
        ficam: list[Linha] = []
        for n, linha in enumerate(pagina.linhas):
            motivo = saem.get((p, n))
            if motivo is None:
                ficam.append(linha)
            else:
                remocoes.append(LinhaRemovida(pagina.numero, motivo, linha.texto))
        limpas.append(Pagina(pagina.numero, tuple(ficam)))
    return PaginasLimpas(tuple(limpas), tuple(remocoes))
