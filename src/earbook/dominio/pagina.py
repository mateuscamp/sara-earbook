# SPDX-License-Identifier: GPL-3.0-or-later
"""A página de um PDF como o domínio a vê: linhas com posição e fonte (ADR-0004).

É o que o PDF sabe e o EPUB convertido já esqueceu: onde a linha está na página e de que
tamanho é a letra. O adaptador de PDF traduz a biblioteca para estes tipos.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Linha:
    texto: str
    x: float
    """Distância da borda esquerda da página até o começo da linha, em pontos."""
    topo: float
    """Posição do alto da linha: 0 no topo da página, 1 no pé."""
    tamanho: float
    """Tamanho médio da fonte da linha, em pontos."""
    monoespacada: bool = False


@dataclass(frozen=True)
class Pagina:
    numero: int
    """Começa em 1, como no leitor de PDF."""
    linhas: tuple[Linha, ...]
