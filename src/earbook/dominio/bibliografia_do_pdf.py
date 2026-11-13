# SPDX-License-Identifier: GPL-3.0-or-later
"""A bibliografia do PDF sai pela letra, antes da ordem de leitura (ADR-0004, "Bibliografia pela
letra e rótulo com a caixa trocada").

No Miller, a lista do fim do capítulo vem na família do corpo, em 7,5 pt contra 9, uma referência
por linha, na coluna ao lado do fim da prosa. A coluna de linhas curtas não é texto corrido para
a regra das colunas, a página era lida por altura, e 432 parágrafos saíam com a prosa intercalada
com as referências: o `limpar` não desfaz a mistura. Aqui as linhas ainda vêm na ordem do PDF,
seguidas. O sinal é a letra e o conteúdo, juntos: 37.706 das 94.811 linhas de 7,5 pt do Miller
trazem citação de periódico, contra 2 das 263.328 do corpo.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from earbook.dominio.pagina import DIFERENCA_DE_TAMANHO, RAZAO_DO_TITULO, Linha, Pagina
from earbook.dominio.paginacao import PaginasLimpas
from earbook.dominio.referencias_vancouver import CITACAO_DE_PERIODICO, CITACOES_MINIMAS
from earbook.dominio.tabelas_e_figuras import (
    Posicao,
    corridas_fora_do_corpo,
    letra_do_corpo,
    sem_as_linhas,
)

MOTIVO_DA_BIBLIOGRAFIA_DO_PDF = (
    "bibliografia: letra menor que a do corpo, com citações de periódico"
)
LINHAS_DA_PONTE = 3
"""As linhas seguidas de outra letra entre duas da lista que saem com ela: o cabeçalho e o número
da página de bibliografia online do Miller ("Capítulo 2: …", "47.e1"). Com 4 ou mais é outra
coisa: a caixa de recursos entre duas listas."""
LINHAS_DO_TITULO = 2
"""O título logo antes da lista, em negrito, versalete ou letra de título ("BiBliografía",
"referências"). Medido: 1 linha no Manica e no Miller, 2 num capítulo do Miller."""

type _Letra = tuple[str, float]


def tirar_bibliografia(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """As páginas sem os trechos de bibliografia, e uma remoção registrada por linha."""
    corpo = letra_do_corpo(paginas)
    if corpo is None:
        return PaginasLimpas(tuple(paginas), ())
    saem: dict[Posicao, str] = {}
    for corrida in corridas_fora_do_corpo(paginas, corpo):
        for trecho in _trechos(paginas, corrida, corpo[1]):
            titulo = _titulo_antes(paginas, trecho[0], corpo[1])
            saem |= dict.fromkeys((*titulo, *trecho), MOTIVO_DA_BIBLIOGRAFIA_DO_PDF)
    return sem_as_linhas(paginas, saem)


def _trechos(
    paginas: Sequence[Pagina], corrida: list[Posicao], tamanho_do_corpo: float
) -> list[list[Posicao]]:
    """Os trechos da corrida na letra das citações, cada um com 10 linhas de citação ou mais."""
    linhas = [_linha_em(paginas, posicao) for posicao in corrida]
    citam = [_cita(linha, tamanho_do_corpo) for linha in linhas]
    if sum(citam) < CITACOES_MINIMAS:
        return []
    das_citacoes = Counter(_letra(linha) for linha, cita in zip(linhas, citam, strict=True) if cita)
    letra = das_citacoes.most_common(1)[0][0]
    na_letra = [n for n, linha in enumerate(linhas) if _letra(linha) == letra]
    return [
        corrida[grupo[0] : grupo[-1] + 1]
        for grupo in _com_ponte(na_letra)
        if sum(citam[n] for n in grupo) >= CITACOES_MINIMAS
    ]


def _com_ponte(posicoes: list[int]) -> list[list[int]]:
    """As posições agrupadas: até `LINHAS_DA_PONTE` linhas de outra letra não separam duas."""
    grupos: list[list[int]] = []
    for posicao in posicoes:
        if grupos and posicao - grupos[-1][-1] - 1 <= LINHAS_DA_PONTE:
            grupos[-1].append(posicao)
        else:
            grupos.append([posicao])
    return grupos


def _cita(linha: Linha, tamanho_do_corpo: float) -> bool:
    """Linha em letra menor que a do corpo com citação de periódico, a mesma do `limpar`."""
    menor = linha.tamanho < tamanho_do_corpo - DIFERENCA_DE_TAMANHO
    return menor and CITACAO_DE_PERIODICO.search(linha.texto) is not None


def _letra(linha: Linha) -> _Letra:
    return linha.fonte, round(linha.tamanho, 1)


def _titulo_antes(
    paginas: Sequence[Pagina], primeira: Posicao, tamanho_do_corpo: float
) -> list[Posicao]:
    """Até `LINHAS_DO_TITULO` linhas de título logo antes da lista, na ordem do PDF. Na mesma
    página, o título fica acima dela: o do pé da coluna da esquerda, antes da lista que abre o
    alto da direita, é de outra seção."""
    topo = _linha_em(paginas, primeira).topo
    titulo: list[Posicao] = []
    posicao = _anterior(paginas, primeira)
    while posicao is not None and len(titulo) < LINHAS_DO_TITULO:
        linha = _linha_em(paginas, posicao)
        abaixo = posicao[0] == primeira[0] and linha.topo >= topo
        # A segunda linha é do título quando tem a letra da primeira: o subtítulo em negrito da
        # prosa logo acima não é (R2 da code-review).
        outra_letra = bool(titulo) and _letra(linha) != _letra(_linha_em(paginas, titulo[0]))
        if abaixo or outra_letra or not _de_titulo(linha, tamanho_do_corpo):
            break
        titulo.append(posicao)
        posicao = _anterior(paginas, posicao)
    return titulo


def _linha_em(paginas: Sequence[Pagina], posicao: Posicao) -> Linha:
    return paginas[posicao[0]].linhas[posicao[1]]


def _de_titulo(linha: Linha, tamanho_do_corpo: float) -> bool:
    grande = linha.tamanho >= tamanho_do_corpo * RAZAO_DO_TITULO
    return linha.negrito or linha.versalete or grande


def _anterior(paginas: Sequence[Pagina], posicao: Posicao) -> Posicao | None:
    """A linha de antes na ordem do PDF: a de cima na página, ou a última da página anterior
    que tem linha."""
    pagina, linha = posicao
    if linha > 0:
        return pagina, linha - 1
    for anterior in range(pagina - 1, -1, -1):
        if paginas[anterior].linhas:
            return anterior, len(paginas[anterior].linhas) - 1
    return None
