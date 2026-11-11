# SPDX-License-Identifier: GPL-3.0-or-later
"""As páginas de lista do PDF saem inteiras do áudio (ADR-0004, "Páginas de lista").

Duas listas que o pdfminer embaralha, por virem em duas colunas, e que não se leem:
- **a página de remissões**, o índice remissivo e o sumário: muitas linhas terminam em vírgula e
  número de página ("pelvic pain in, 617", "Interdisciplinary Pain Management, 39"). No
  Practical, o índice é página escaneada com OCR, lida intercalada entre nota e parágrafo, e a
  regra do ADR-0008 ("Índice pelo conteúdo"), de 10 parágrafos seguidos, não dispara;
- **a página de colaboradores**: o nome com o título acadêmico ("Honorio T. Benzon, MD") e a
  afiliação, linha a linha.

A decisão é por página, onde o PDF ainda as separa; no texto montado, a lista vira um bloco com
o texto vizinho.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from itertools import pairwise

from earbook.dominio.pagina import PALAVRAS_DO_ROTULO, Linha, Pagina
from earbook.dominio.paginacao import LinhaRemovida, PaginasLimpas

MOTIVO_DAS_REMISSOES = "página de remissões: índice remissivo ou sumário"
MOTIVO_DOS_COLABORADORES = "página de colaboradores: nome, título e afiliação"
MOTIVO_DO_SUMARIO = "sumário sem número de página: rótulos de capítulo em páginas sem frase"
REMISSOES_MINIMAS = 5
FRACAO_DAS_REMISSOES = 0.25
"""A página curta do fim do sumário do Practical (p. 22) tem 5 remissões em 18 linhas."""
PALAVRAS_DA_PROSA = 8
FRASES_DA_LISTA = 0
"""A página de lista não tem frase: nenhuma palavra de 3 minúsculas ou mais seguida de ponto. As
do sumário do Bonica, com o título que termina em "?", têm 0; a prosa tem dezenas."""
NOMES_DA_VIZINHA = 2
ROTULOS_DO_SUMARIO = 3
COLABORADORES_MINIMOS = 5
FRACAO_DOS_COLABORADORES = 0.1
"""Conta o nome seguido da afiliação: o prefácio do Practical (p. 18) assina com 7 linhas "Nome,
MD" coladas, e fica."""
# A linha termina em vírgula, espaço e página, com a letra da figura ou da tabela ("621 t", "99f")
# e a faixa ("977- 978"). O ano ("Philadelphia, 2004") e a vírgula decimal ("17,6", a tabela do
# Dalgalarrondo p. 302) não contam.
_REMISSAO = re.compile(
    r",\s+(?!(?:1[5-9]|20)\d\d\b)\d{1,4}\s?[a-z]?(?:\s*[-\u2013]\s*\d{1,4}\s?[a-z]?)?\s*$"
)
# O fim de frase: palavra de 3 minúsculas ou mais e o ponto, com aspas ou parêntese depois, e
# então espaço, fim da linha ou a chamada que o adaptador não tirou ("pain.12 The", "pain.[3]",
# "pain.¹"). A abreviação curta ("Jr.", "St. Louis") e o título em maiúsculas não contam.
_FIM_DE_FRASE = re.compile(
    r"[a-zà-ÿ]{3,}\.[\"\u201d\u2019)]?(?=[\s\d\[\u00b9\u00b2\u00b3\u2070-\u2079]|$)"
)
# O rótulo no começo da linha, sozinho ("CHAPTER 4"), com o título ("CHAPTER 6: Supraspinal") ou
# depois do nome da subparte em maiúsculas.
_ROTULO_DO_SUMARIO = re.compile(
    rf"(?:[A-ZÀ-Ý][A-ZÀ-Ý ]*\s)?(?:{PALAVRAS_DO_ROTULO})\s+\d+(?=[\s:]|$)"
)
# O nome, com minúscula (o autor do capítulo vem em maiúsculas), e o título acadêmico.
_TITULOS = (
    "MD|DO|PhD|PharmD|PsyD|DDS|DMD|DNP|RN|MBBS|MB|BS|BSc|MS|MSc|MA|BA|MPH|MSN|PT|DPT|DC|"
    "FRCA|FRCPC|FRCP"
)
_NOME_COM_TITULO = re.compile(
    rf"[A-ZÀ-Ý][a-zà-ÿ'\u2019.-]+(?:\s+[A-ZÀ-Ýa-zà-ÿ][\w.'\u2019-]*){{0,5}},\s*(?:{_TITULOS})\b"
)


def tirar_paginas_de_lista(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """As páginas sem as de remissões, de colaboradores e de sumário sem número, e uma remoção
    registrada por linha."""
    motivos = [_motivo(pagina.linhas) for pagina in paginas]
    sem_frase = [_frases(pagina.linhas) <= FRASES_DA_LISTA for pagina in paginas]
    _colaboradores_vizinhos(paginas, motivos, sem_frase)
    _sumario_sem_numero(paginas, motivos, sem_frase)
    limpas: list[Pagina] = []
    remocoes: list[LinhaRemovida] = []
    for pagina, motivo in zip(paginas, motivos, strict=True):
        if motivo is None:
            limpas.append(pagina)
            continue
        limpas.append(Pagina(pagina.numero, ()))
        remocoes += [LinhaRemovida(pagina.numero, motivo, linha.texto) for linha in pagina.linhas]
    return PaginasLimpas(tuple(limpas), tuple(remocoes))


def _motivo(linhas: Sequence[Linha]) -> str | None:
    remissao = [_REMISSAO.search(linha.texto) is not None for linha in linhas]
    remissoes = sum(remissao)
    # A página com mais prosa que remissão é texto com uma tabela de doses ou de páginas: ela não
    # sai inteira (R1 da code-review). A linha do índice e a do sumário são curtas.
    prosa = sum(
        not e_remissao and len(linha.texto.split()) >= PALAVRAS_DA_PROSA
        for linha, e_remissao in zip(linhas, remissao, strict=True)
    )
    densa = remissoes >= max(REMISSOES_MINIMAS, FRACAO_DAS_REMISSOES * len(linhas))
    if densa and prosa <= remissoes:
        return MOTIVO_DAS_REMISSOES
    if _nomes(linhas) >= max(COLABORADORES_MINIMOS, FRACAO_DOS_COLABORADORES * len(linhas)):
        return MOTIVO_DOS_COLABORADORES
    return None


def _nomes(linhas: Sequence[Linha]) -> int:
    """Os nomes com título acadêmico seguidos de uma linha que não é nome: a afiliação."""
    nome = [_NOME_COM_TITULO.match(linha.texto) is not None for linha in linhas]
    return sum(e_nome and not seguinte for e_nome, seguinte in pairwise(nome))


def _frases(linhas: Sequence[Linha]) -> int:
    return sum(len(_FIM_DE_FRASE.findall(linha.texto)) for linha in linhas)


def _colaboradores_vizinhos(
    paginas: Sequence[Pagina], motivos: list[str | None], sem_frase: Sequence[bool]
) -> None:
    """A lista de colaboradores continua na página vizinha sem frase que tem 2 nomes com afiliação
    ou mais, para os dois lados, e acaba na página seguinte sem frase, mesmo sem nome, na letra da
    lista: as últimas linhas da afiliação (Bonica p. 54). Antes da lista, a página sem nome fica:
    a dedicatória."""
    candidata = [
        motivo is None and livre and _nomes(pagina.linhas) >= NOMES_DA_VIZINHA
        for pagina, motivo, livre in zip(paginas, motivos, sem_frase, strict=True)
    ]
    for i in range(1, len(paginas)):  # a corrente para a frente
        if candidata[i] and motivos[i - 1] == MOTIVO_DOS_COLABORADORES:
            motivos[i] = MOTIVO_DOS_COLABORADORES
    for i in reversed(range(len(paginas) - 1)):  # e para trás
        if candidata[i] and motivos[i + 1] == MOTIVO_DOS_COLABORADORES:
            motivos[i] = MOTIVO_DOS_COLABORADORES
    fins = [i for i in range(1, len(paginas)) if _fim_da_lista(paginas, motivos, sem_frase, i)]
    for i in fins:
        motivos[i] = MOTIVO_DOS_COLABORADORES


def _fim_da_lista(
    paginas: Sequence[Pagina], motivos: Sequence[str | None], sem_frase: Sequence[bool], i: int
) -> bool:
    """A página `i` fecha a lista da anterior: sem frase e só nas letras da lista."""
    if motivos[i - 1] != MOTIVO_DOS_COLABORADORES or motivos[i] is not None or not sem_frase[i]:
        return False
    letras_da_lista = {round(linha.tamanho, 1) for linha in paginas[i - 1].linhas}
    return all(round(linha.tamanho, 1) in letras_da_lista for linha in paginas[i].linhas)


def _sumario_sem_numero(
    paginas: Sequence[Pagina], motivos: list[str | None], sem_frase: Sequence[bool]
) -> None:
    """Sai a sequência de páginas seguidas sem frase com 3 rótulos de capítulo ou mais: o sumário
    sem número de página (Bonica p. 67 a 194) ou com o número sem vírgula (p. 5899 a 6053), do
    primeiro rótulo ao último. A abertura de capítulo sem frase é uma página só, com um rótulo."""
    sequencia: list[int] = []
    for i in [*range(len(paginas)), len(paginas)]:
        if i < len(paginas) and motivos[i] is None and sem_frase[i]:
            sequencia.append(i)
            continue
        rotulos = [_rotulos(paginas[j].linhas) for j in sequencia]
        if sum(rotulos) >= ROTULOS_DO_SUMARIO:
            # Do primeiro rótulo ao último: a dedicatória antes e a página da parte depois também
            # não têm frase, e ficam.
            com_rotulo = [j for j, n in zip(sequencia, rotulos, strict=True) if n]
            for j in range(com_rotulo[0], com_rotulo[-1] + 1):
                motivos[j] = MOTIVO_DO_SUMARIO
        sequencia = []


def _rotulos(linhas: Sequence[Linha]) -> int:
    return sum(_ROTULO_DO_SUMARIO.match(linha.texto) is not None for linha in linhas)
