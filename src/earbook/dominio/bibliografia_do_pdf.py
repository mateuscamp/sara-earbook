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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise

from earbook.dominio.pagina import DIFERENCA_DE_TAMANHO, RAZAO_DO_TITULO, Linha, Pagina
from earbook.dominio.paginacao import PaginasLimpas
from earbook.dominio.referencias_vancouver import CITACAO_DE_PERIODICO, CITACOES_MINIMAS
from earbook.dominio.tabelas_e_figuras import (
    Posicao,
    corridas_fora_do_corpo,
    letra_do_corpo,
    na_letra_do_corpo,
    sem_as_linhas,
)

MOTIVO_DA_BIBLIOGRAFIA_DO_PDF = (
    "bibliografia: letra menor que a do corpo, com citações de periódico"
)
MOTIVO_DA_LISTA_DE_LEITURA = (
    "bibliografia: lista de leitura logo antes das referências, na letra delas"
)
LINHAS_DA_PONTE = 3
"""As linhas seguidas de outra letra entre duas da lista que saem com ela: o cabeçalho e o número
da página de bibliografia online do Miller ("Capítulo 2: …", "47.e1"). Com 4 ou mais é outra
coisa: a caixa de recursos entre duas listas."""
LINHAS_DO_TITULO = 2
"""O título logo antes da lista, em negrito, versalete ou letra de título ("BiBliografía",
"referências"). Medido: 1 linha no Manica e no Miller, 2 num capítulo do Miller."""
LINHAS_DO_CORPO_NO_CAMINHO = 40
"""As linhas na letra do corpo entre o título da lista de leitura e a bibliografia provada, que
ficam e não param a regra: a caixa da coluna ao lado, que o PDF grava no meio da lista. Medido no
Practical: de 5 a 32. Com mais, é o texto do capítulo (ADR-0004, "Lista de leitura logo antes da
bibliografia")."""

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
            # Antes de marcar o trecho: a lista de leitura para na linha que já sai.
            inicio, letra = (*trecho[:1], *titulo)[-1], _letra(_linha_em(paginas, trecho[0]))
            leitura = _lista_de_leitura(paginas, inicio, letra, corpo, saem)
            saem |= dict.fromkeys(leitura, MOTIVO_DA_LISTA_DE_LEITURA)
            saem |= dict.fromkeys((*titulo, *trecho), MOTIVO_DA_BIBLIOGRAFIA_DO_PDF)
    return sem_as_linhas(paginas, saem)


def _lista_de_leitura(
    paginas: Sequence[Pagina],
    inicio: Posicao,
    letra: _Letra,
    corpo: tuple[str, float],
    saem: Mapping[Posicao, str],
) -> list[Posicao]:
    """A lista de leitura logo antes da bibliografia provada, que começa em `inicio` (o título
    dela, ou a primeira referência) e vem na `letra`: o título em letra de título e, dele até a
    última linha nessa letra, o que não está na letra do corpo (ADR-0004, "Lista de leitura logo
    antes da bibliografia").

    No Practical, as "Suggested Readings" vêm na letra da lista numerada, numa corrida só delas,
    que o título "References" fecha: com menos de 10 linhas de citação, ficavam. Sai quando o
    título encabeça a lista (a linha depois dele não é do corpo) e ela tem alguma citação de
    periódico: a nota de rodapé depois da prosa e a lista só de sites ficam. A frase em outra
    letra depois da última referência fica, para a marca d'água do `limpar`.

    Sem título, entre dois trechos provados, é a metade da lista longa que a caixa do corpo
    partiu: sai da primeira à última linha na letra das citações.
    """
    caminho = _para_tras(paginas, inicio, letra, corpo, saem)
    if caminho is None or not caminho.visitadas:
        return []
    linhas = [_linha_em(paginas, posicao) for posicao in caminho.visitadas]
    da_lista = [n for n, linha in enumerate(linhas) if _letra(linha) == letra]
    encabeca = caminho.titulo is None or not na_letra_do_corpo(linhas[-1], corpo)
    if not encabeca or not any(_cita(linhas[n], corpo[1]) for n in da_lista):
        return []
    # Com título, o subtítulo logo abaixo dele sai; entre dois trechos, só as pontas da lista.
    ultima = len(linhas) if caminho.titulo is not None else da_lista[-1] + 1
    fora_do_corpo = [
        caminho.visitadas[n]
        for n in range(da_lista[0], ultima)
        if not na_letra_do_corpo(linhas[n], corpo)
    ]
    # Só a linha de título logo acima da lista: a de cima dela, mesmo na mesma letra, pode ser o
    # título de outra seção, que o PDF em colunas grava logo antes (A1 da code-audit).
    titulo = [caminho.titulo] if caminho.titulo is not None else []
    return [*titulo, *reversed(fora_do_corpo)]


@dataclass(frozen=True)
class _Caminho:
    """O que há, para trás, entre a bibliografia provada e o que encabeça a lista de leitura."""

    titulo: Posicao | None
    """A linha em letra de título que encabeça a lista; None se o caminho acabou num trecho
    provado, que já sai."""
    visitadas: list[Posicao]
    """As linhas do caminho, da última para a primeira."""


def _para_tras(
    paginas: Sequence[Pagina],
    inicio: Posicao,
    letra: _Letra,
    corpo: tuple[str, float],
    saem: Mapping[Posicao, str],
) -> _Caminho | None:
    """Para trás, na ordem do PDF, de antes de `inicio` até a primeira linha em letra de título
    ou a primeira que já sai (o trecho provado anterior). None se o livro acaba antes, se o
    caminho passa por mais de `LINHAS_DA_PONTE` linhas de outra letra sem uma da lista entre elas
    (a caixa, o anexo), por mais de `LINHAS_DO_CORPO_NO_CAMINHO` linhas do corpo (o texto do
    capítulo) ou por uma linha do corpo antes de chegar à lista: ela termina encostada na
    bibliografia, e a prosa entre as duas diz que o bloco lá atrás é de outra seção (R2 da
    code-review)."""
    visitadas: list[Posicao] = []
    do_corpo = ponte = 0
    viu_a_lista = False
    posicao = _anterior(paginas, inicio)
    while posicao is not None:
        linha = _linha_em(paginas, posicao)
        if posicao in saem or linha.tamanho >= corpo[1] * RAZAO_DO_TITULO:
            return _Caminho(None if posicao in saem else posicao, visitadas)
        if na_letra_do_corpo(linha, corpo):
            # A lista termina encostada na bibliografia: o corpo só passa no meio dela.
            do_corpo = do_corpo + 1 if viu_a_lista else LINHAS_DO_CORPO_NO_CAMINHO + 1
        else:
            ponte = 0 if _letra(linha) == letra else ponte + 1
            viu_a_lista = viu_a_lista or _letra(linha) == letra
        if do_corpo > LINHAS_DO_CORPO_NO_CAMINHO or ponte > LINHAS_DA_PONTE:
            return None
        visitadas.append(posicao)
        posicao = _anterior(paginas, posicao)
    return None


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
    grupos = [
        _depois_do_titulo(linhas, citam, grupo, tamanho_do_corpo)
        for grupo in _com_ponte(na_letra)
        if sum(citam[n] for n in grupo) >= CITACOES_MINIMAS
    ]
    return [corrida[grupo[0] : grupo[-1] + 1] for grupo in grupos]


def _depois_do_titulo(
    linhas: list[Linha], citam: list[bool], grupo: list[int], tamanho_do_corpo: float
) -> list[int]:
    """O grupo sem o que vem antes do título da lista, quando ali não há citação nenhuma: a nota
    de rodapé do autor, na letra das referências, logo acima de "References" (Bonica: 7 notas,
    746 palavras; ADR-0004, "Camada do OCR sobre as figuras e chamada colada"). O título é a
    linha de outra letra, em negrito, versalete ou letra de título, antes da primeira citação; o
    cabeçalho da página de bibliografia, no meio da lista, vem depois dela e não a parte."""
    primeira_citacao = next(n for n in grupo if citam[n])
    comeco = grupo[0]
    for antes, depois in pairwise(grupo):
        if depois > primeira_citacao:
            break
        if any(_de_titulo(linhas[n], tamanho_do_corpo) for n in range(antes + 1, depois)):
            comeco = depois
    return [n for n in grupo if n >= comeco]


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
        outra = bool(titulo) and _de_outro_titulo(
            _linha_em(paginas, titulo[0]), linha, tamanho_do_corpo
        )
        if abaixo or outra or not _de_titulo(linha, tamanho_do_corpo):
            break
        titulo.append(posicao)
        posicao = _anterior(paginas, posicao)
    return titulo


def _de_outro_titulo(primeira: Linha, linha: Linha, tamanho_do_corpo: float) -> bool:
    """A segunda linha, acima da primeira do título, é de outro título quando não tem a letra
    dela: o subtítulo em negrito da prosa logo acima (R2 da code-review). Menos quando ela vem na
    família da primeira, em letra de título, e a primeira não: o título da lista dividida em
    partes, acima do subtítulo da primeira ("References" | "Section I", os dois em MyriadPro;
    ADR-0004, "Lista de leitura logo antes da bibliografia"). O título grande de outra família,
    acima do título pequeno da lista, é o do capítulo, e fica."""
    if _letra(linha) == _letra(primeira):
        return False
    grande = tamanho_do_corpo * RAZAO_DO_TITULO
    do_subtitulo = linha.fonte == primeira.fonte and linha.tamanho >= grande > primeira.tamanho
    return not do_subtitulo


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
