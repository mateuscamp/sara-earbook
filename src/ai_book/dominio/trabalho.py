# SPDX-License-Identifier: GPL-3.0-or-later
"""O que o `preparar` registra sobre o livro na pasta de trabalho."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapituloPreparado:
    id: str
    arquivo: str
    segmentos: int


@dataclass(frozen=True)
class TextoForaDeSegmento:
    """Texto que não coube em nenhum segmento e, sem conferência, sumiria do áudio."""

    capitulo: str
    texto: str


@dataclass(frozen=True)
class ItemIgnorado:
    """Item do spine que o `preparar` não leu, com o motivo, para não sumir em silêncio."""

    idref: str
    motivo: str


@dataclass(frozen=True)
class LivroPreparado:
    origem: str
    titulo: str
    autor: str
    idioma: str
    capitulos: tuple[CapituloPreparado, ...]
    texto_fora_de_segmento: tuple[TextoForaDeSegmento, ...]
    itens_do_spine_ignorados: tuple[ItemIgnorado, ...] = ()
