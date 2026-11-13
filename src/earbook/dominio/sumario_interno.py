# SPDX-License-Identifier: GPL-3.0-or-later
"""O sumário interno do PDF (os marcadores) como fonte dos capítulos (ADR-0004, "Capítulos pelo
sumário interno do PDF").

O adaptador de PDF lê os itens; aqui se decide se eles servem e onde cada capítulo abre.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

ROTULOS_MINIMOS = 3
"""O nível do capítulo tem o rótulo em 3 páginas ou mais, como o rótulo no título (`capitulos`)."""
# "Capítulo 1. …", "Capitulo 1_ …", "capitulo 4_ …" (Miller, sem acento e sem maiúscula), "CHAPTER
# 1: …": a palavra e o número, sem olhar a caixa. "Capítulos 1 a 3" não é rótulo.
_ROTULO = re.compile(r"\W*(?:cap[ií]tulo|chapter)\s*\d+(?!\w)", re.IGNORECASE)


@dataclass(frozen=True)
class ItemDoSumario:
    nivel: int
    """1 para o item de fora; os filhos dele têm 2, e assim por diante."""
    titulo: str
    pagina: int
    """A página do PDF para onde o item leva, a partir de 1."""


@dataclass(frozen=True)
class Abertura:
    """Onde um capítulo abre, e o nome que o sumário interno dá a ele."""

    pagina: int
    nome: str


def aberturas_de_capitulo(itens: Sequence[ItemDoSumario]) -> tuple[Abertura, ...]:
    """As aberturas de capítulo que o sumário interno dá, em ordem de página; vazio se ele não
    serve.

    Todo item do nível do capítulo e dos níveis acima dele abre capítulo: o prefácio, a parte e o
    anexo são irmãos do capítulo. Com mais de um item na mesma página (Miller: "Capitulo 1_ …" no
    nível 1 e "Capítulo 1 - …" no 2), o nome é o do último.
    """
    nivel = _nivel_do_capitulo(itens)
    if nivel is None:
        return ()
    nomes: dict[int, str] = {}
    for item in itens:
        if item.nivel <= nivel:
            nomes[item.pagina] = item.titulo
    return tuple(Abertura(pagina, nomes[pagina]) for pagina in sorted(nomes))


def _nivel_do_capitulo(itens: Sequence[ItemDoSumario]) -> int | None:
    """O nível mais fundo em que a maioria dos itens começa pelo rótulo de capítulo, em 3 páginas
    ou mais; None se nenhum.

    O sumário sem rótulo (Practical: "1 History…") e o plano, com capítulo e seção no mesmo nível
    (Bonica), não dizem qual item é capítulo, e não servem.
    """
    por_nivel: defaultdict[int, list[ItemDoSumario]] = defaultdict(list)
    for item in itens:
        por_nivel[item.nivel].append(item)
    for nivel in sorted(por_nivel, reverse=True):
        do_nivel = por_nivel[nivel]
        com_rotulo = [item for item in do_nivel if _ROTULO.match(item.titulo)]
        paginas = {item.pagina for item in com_rotulo}
        if len(paginas) >= ROTULOS_MINIMOS and len(com_rotulo) * 2 > len(do_nivel):
            return nivel
    return None
