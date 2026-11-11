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
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from earbook.dominio.pagina import DIFERENCA_DE_TAMANHO, RAZAO_DO_TITULO, Linha, Pagina
from earbook.dominio.paginacao import LinhaRemovida, PaginasLimpas

MOTIVO_DA_TABELA = "tabela: rótulo e letra fora do corpo"
MOTIVO_DA_FIGURA = "figura e legenda: rótulo e letra fora do corpo"
# Só o rótulo em inglês: o "Quadro" e a "Tabela" do Dalgalarrondo ficam no lugar (ADR-0004,
# "Quadro no lugar"), e o "Figura" do Competente não pôde ser medido.
# "TABLE" sozinho na linha (o número vem na de baixo, no Practical), ou o rótulo com o número
# seguido de ponto, maiúscula ou fim de linha: "Table 2.1 Pain Axes", "Table 5-7. Components",
# "• Figure 2.1  International…". A menção que a linha quebrou ("Table 5-7 shows…", "Figure 5-2),
# Addison…", Hard Parts) e "Table of Contents" não são rótulo.
_NUMERO_E_LEGENDA = r"\s+\d+(?:[.\-\u2013]\d+)*[A-Z]?(?:\.?\s+[A-Z]|\.?\s*$)"
_ROTULO_DA_TABELA = re.compile(rf"TABLE\s*$|(?:TABLE|Table){_NUMERO_E_LEGENDA}")
_ROTULO_DA_FIGURA = re.compile(rf"(?:•\s*)?(?:FIGURE|Figure|Fig\.){_NUMERO_E_LEGENDA}")

FOLGA_DO_DIAGRAMA = 0.25
"""Pontos: o rótulo do diagrama pode ter a letra da legenda, mas não maior."""
# A frase da linha de cima acabou: ponto, interrogação, exclamação ou dois-pontos, com aspa ou
# parêntese depois ("…National Library of Medicine.)").
_FECHA_FRASE = re.compile(r"[.!?:][\u201d\u2019\"')]*$")

type _Posicao = tuple[int, int]
"""(índice da página, índice da linha)."""


def tirar_tabelas_e_figuras(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """As páginas sem as corridas de tabela e de figura, e uma remoção registrada por linha."""
    corpo = _letra_do_corpo(paginas)
    if corpo is None:
        return PaginasLimpas(tuple(paginas), ())
    saem: dict[_Posicao, str] = {}
    for corrida in _corridas(paginas, corpo):
        saem |= _da_corrida(paginas, corrida)
    return _sem(paginas, saem)


def _da_corrida(paginas: Sequence[Pagina], corrida: list[_Posicao]) -> dict[_Posicao, str]:
    """O que sai da corrida: a tabela, do rótulo em diante; a figura, em volta da legenda."""
    saem: dict[_Posicao, str] = {}
    for i, (p, n) in enumerate(corrida):
        anterior = paginas[p].linhas[n - 1] if n > 0 else None
        motivo = _rotulo(paginas[p].linhas[n], anterior)
        if motivo == MOTIVO_DA_TABELA:
            return saem | dict.fromkeys(_tabela(paginas, corrida[i:]), motivo)
        if motivo == MOTIVO_DA_FIGURA:
            saem |= dict.fromkeys(_figura(paginas, corrida, i), motivo)
    return saem


def _tabela(paginas: Sequence[Pagina], corrida: list[_Posicao]) -> list[_Posicao]:
    """Do rótulo em diante. Na página seguinte, a tabela continua só na letra que ela já usou: o
    crédito do autor em Gotham, no alto da página, não é célula (R2 da code-review)."""
    letras: set[tuple[str, float]] = set()
    pagina_do_rotulo = corrida[0][0]
    saem: list[_Posicao] = []
    for p, n in corrida:
        linha = paginas[p].linhas[n]
        letra = (linha.fonte, round(linha.tamanho, 1))
        if p != pagina_do_rotulo and letra not in letras:
            break
        letras.add(letra)
        saem.append((p, n))
    return saem


def _figura(paginas: Sequence[Pagina], corrida: list[_Posicao], legenda: int) -> list[_Posicao]:
    """A legenda e o que vem depois dela na página; antes dela, o diagrama, que vem em letra não
    maior que a da legenda (Practical: 7 pt contra 8). A caixa de 9 pt logo antes fica (R3 da
    code-review)."""
    p, n = corrida[legenda]
    tamanho = paginas[p].linhas[n].tamanho
    saem = [pos for pos in corrida[legenda:] if pos[0] == p]
    for pos in reversed(corrida[:legenda]):
        linha = paginas[pos[0]].linhas[pos[1]]
        if pos[0] != p or linha.tamanho > tamanho + FOLGA_DO_DIAGRAMA:
            break
        saem.append(pos)
    return saem


def _letra_do_corpo(paginas: Sequence[Pagina]) -> tuple[str, float] | None:
    """A família e o tamanho com mais caracteres no livro; None se o PDF não diz a família."""
    letras: Counter[tuple[str, float]] = Counter()
    for pagina in paginas:
        for linha in pagina.linhas:
            letras[linha.fonte, round(linha.tamanho, 1)] += len(linha.texto)
    if not letras:
        return None
    familia, tamanho = letras.most_common(1)[0][0]
    return (familia, tamanho) if familia else None


def _corridas(paginas: Sequence[Pagina], corpo: tuple[str, float]) -> list[list[_Posicao]]:
    """As corridas de linhas seguidas fora da letra do corpo e da de título, no livro todo."""
    corridas: list[list[_Posicao]] = [[]]
    for p, pagina in enumerate(paginas):
        for n, linha in enumerate(pagina.linhas):
            if _fecha(linha, corpo):
                corridas.append([])
            else:
                corridas[-1].append((p, n))
    return [corrida for corrida in corridas if corrida]


def _fecha(linha: Linha, corpo: tuple[str, float]) -> bool:
    """A letra do corpo, ou a de título que não é rótulo, fecha a corrida."""
    familia, tamanho = corpo
    do_corpo = linha.fonte == familia and abs(linha.tamanho - tamanho) <= DIFERENCA_DE_TAMANHO
    titulo = linha.tamanho >= tamanho * RAZAO_DO_TITULO and _rotulo(linha) is None
    return do_corpo or titulo


def _rotulo(linha: Linha, anterior: Linha | None = None) -> str | None:
    """O motivo, se a linha abre com rótulo de tabela ou de figura. A linha que continua a frase
    da de cima, na mesma letra, é menção quebrada, e não rótulo ("…components in" | "Figure
    5-11.", na prosa em MyriadPro de 9 pt do Hard Parts)."""
    if anterior is not None and _continua_a_frase(anterior, linha):
        return None
    if _ROTULO_DA_TABELA.match(linha.texto):
        return MOTIVO_DA_TABELA
    if _ROTULO_DA_FIGURA.match(linha.texto):
        return MOTIVO_DA_FIGURA
    return None


def _continua_a_frase(anterior: Linha, linha: Linha) -> bool:
    mesma_letra = anterior.fonte == linha.fonte and abs(anterior.tamanho - linha.tamanho) <= (
        DIFERENCA_DE_TAMANHO
    )
    return mesma_letra and _FECHA_FRASE.search(anterior.texto) is None


def _sem(paginas: Sequence[Pagina], saem: dict[_Posicao, str]) -> PaginasLimpas:
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
