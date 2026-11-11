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

from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginacao import LinhaRemovida, PaginasLimpas

MOTIVO_DAS_REMISSOES = "página de remissões: índice remissivo ou sumário"
MOTIVO_DOS_COLABORADORES = "página de colaboradores: nome, título e afiliação"
REMISSOES_MINIMAS = 5
FRACAO_DAS_REMISSOES = 0.25
"""A página curta do fim do sumário do Practical (p. 22) tem 5 remissões em 18 linhas."""
PALAVRAS_DA_PROSA = 8
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
# O nome, com minúscula (o autor do capítulo vem em maiúsculas), e o título acadêmico.
_TITULOS = (
    "MD|DO|PhD|PharmD|PsyD|DDS|DMD|DNP|RN|MBBS|MB|BS|BSc|MS|MSc|MA|BA|MPH|MSN|PT|DPT|DC|"
    "FRCA|FRCPC|FRCP"
)
_NOME_COM_TITULO = re.compile(
    rf"[A-ZÀ-Ý][a-zà-ÿ'\u2019.-]+(?:\s+[A-ZÀ-Ýa-zà-ÿ][\w.'\u2019-]*){{0,5}},\s*(?:{_TITULOS})\b"
)


def tirar_paginas_de_lista(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """As páginas sem as de remissões e de colaboradores, e uma remoção registrada por linha."""
    limpas: list[Pagina] = []
    remocoes: list[LinhaRemovida] = []
    for pagina in paginas:
        motivo = _motivo(pagina.linhas)
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
    nome = [_NOME_COM_TITULO.match(linha.texto) is not None for linha in linhas]
    nomes = sum(e_nome and not seguinte for e_nome, seguinte in pairwise(nome))
    if nomes >= max(COLABORADORES_MINIMOS, FRACAO_DOS_COLABORADORES * len(linhas)):
        return MOTIVO_DOS_COLABORADORES
    return None
