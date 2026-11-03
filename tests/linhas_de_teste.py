# SPDX-License-Identifier: GPL-3.0-or-later
"""Linhas de PDF montadas em código para os testes de `dominio/blocos.py` (ADR-0004).

As medidas imitam o Competente: corpo de 10,5 pt, margem em x = 54, recuo de parágrafo de
13 pt, entrelinha de 0,021 da altura da página e 0,035 entre parágrafos.
"""

from __future__ import annotations

from dataclasses import replace

from earbook.dominio.blocos import LivroMontado, montar_blocos
from earbook.dominio.pagina import Linha, Pagina

MARGEM = 54.0
RECUO = 67.0
ENTRELINHA = 0.021
FIM_DA_LINHA = 378.0
"""A margem direita do Competente: toda linha vai até ela, atravessa qualquer calha e não faz
coluna (ADR-0004, "Duas colunas")."""


def linha(
    texto: str, topo: float, x: float = MARGEM, tamanho: float = 10.5, *, mono: bool = False
) -> Linha:
    return Linha(texto, x=x, fim=FIM_DA_LINHA, topo=topo, tamanho=tamanho, monoespacada=mono)


def em_negrito(linha: Linha) -> Linha:
    return replace(linha, negrito=True)


def texto_corrido(topo: float, linhas: int = 6) -> list[Linha]:
    """Um parágrafo de enchimento, para que corpo, margem e entrelinha sejam os do livro."""
    primeira = linha("Texto corrido para firmar as medidas do livro inteiro aqui.", topo, RECUO)
    resto = [
        linha("mais texto corrido para firmar as medidas do livro inteiro.", topo + ENTRELINHA * n)
        for n in range(1, linhas)
    ]
    return [primeira, *resto]


def montar(*paginas: list[Linha]) -> LivroMontado:
    return montar_blocos([Pagina(n, tuple(linhas)) for n, linhas in enumerate(paginas, 1)])


def resumo(livro: LivroMontado) -> list[tuple[str, str]]:
    return [(bloco.tipo.value, bloco.texto) for bloco in livro.blocos]
