# SPDX-License-Identifier: GPL-3.0-or-later
"""Onde cada segmento cai na escuta (ADR-0007): a conta do roteiro de escuta."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from earbook.dominio.segmento import Segmento

PALAVRAS_POR_MINUTO = 160


class SegmentoDesconhecidoError(ValueError):
    pass


@dataclass(frozen=True)
class Posicao:
    id: str
    capitulo: str
    minuto_no_livro: int
    minuto_no_capitulo: int


def posicoes(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]], ids: Iterable[str]
) -> tuple[Posicao, ...]:
    """Pelas palavras lidas antes do segmento, a `PALAVRAS_POR_MINUTO`. No Tides, o roteiro
    de escuta fazia esta conta à mão. A nota, que o `montar` leva para o fim do capítulo,
    conta onde está: a diferença é de segundos."""
    antes: dict[str, tuple[str, int, int]] = {}
    no_livro = 0
    for capitulo, segmentos in capitulos:
        no_capitulo = 0
        for segmento in segmentos:
            antes[segmento.id] = (capitulo, no_livro, no_capitulo)
            palavras = len(segmento.texto.split())
            no_livro += palavras
            no_capitulo += palavras
    return tuple(_posicao(id_, antes) for id_ in ids)


def _posicao(id_: str, antes: dict[str, tuple[str, int, int]]) -> Posicao:
    if (achado := antes.get(id_)) is None:
        mensagem = f"{id_}: segmento que o livro não tem"
        raise SegmentoDesconhecidoError(mensagem)
    capitulo, no_livro, no_capitulo = achado
    return Posicao(
        id_, capitulo, no_livro // PALAVRAS_POR_MINUTO, no_capitulo // PALAVRAS_POR_MINUTO
    )
