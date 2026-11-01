# SPDX-License-Identifier: GPL-3.0-or-later
"""Segmento: a menor unidade que o tradutor recebe e devolve.

O ID é o contrato entre `preparar`, tradução e `montar` (ADR-0001): todo ID que
entra na tradução tem de sair dela, sem faltar, sobrar ou repetir.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Papel(StrEnum):
    TITULO = "titulo"
    PARAGRAFO = "paragrafo"
    NOTA = "nota"


@dataclass(frozen=True)
class Segmento:
    """Um bloco de texto do livro, já limpo para o ouvido.

    `notas` guarda o destino de cada chamada de nota tirada do texto, como
    `OEBPS/cap1.xhtml#fn1`, para que o `montar` leve a nota para o fim do capítulo.
    """

    id: str
    papel: Papel
    texto: str
    notas: tuple[str, ...] = ()


def id_do_capitulo(posicao_no_spine: int) -> str:
    """`id_do_capitulo(3)` → `"c003"`. A posição começa em 1."""
    return f"c{posicao_no_spine:03d}"


def id_do_segmento(capitulo: str, posicao: int) -> str:
    """`id_do_segmento("c003", 42)` → `"c003-s0042"`. A posição começa em 1."""
    return f"{capitulo}-s{posicao:04d}"


def normalizar_espacos(texto: str) -> str:
    """Junta qualquer sequência de espaço Unicode (inclusive NBSP) num espaço só."""
    return " ".join(texto.split())
