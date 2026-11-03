# SPDX-License-Identifier: GPL-3.0-or-later
"""Dos blocos do livro aos capítulos, e o nível de cada título (ADR-0004).

Saiu de `blocos.py` para ele caber no limite de 400 linhas do ADR-0001.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from earbook.dominio.blocos import Bloco, TipoDeBloco
from earbook.dominio.pagina import DIFERENCA_DE_TAMANHO

PAGINAS_DO_CAPITULO = 3


def dividir_em_capitulos(blocos: Sequence[Bloco]) -> tuple[tuple[Bloco, ...], ...]:
    """Corta o livro no maior tamanho de título que aparece em 3 páginas ou mais.

    No Competente é o número do capítulo (30 pt); no Hard Parts, o título do capítulo
    (25,2 pt). O que vem antes do primeiro capítulo fica num capítulo de abertura.
    """
    capitulo = _tamanho_do_capitulo(blocos)
    niveis = _niveis(blocos, capitulo)
    capitulos: list[list[Bloco]] = [[]]
    for bloco in blocos:
        if bloco.tipo is TipoDeBloco.TITULO:
            bloco = replace(bloco, nivel=niveis[round(bloco.tamanho, 1)])  # noqa: PLW2901  # motivo: o mesmo bloco, agora com o nível
            if (
                capitulo is not None
                and abs(bloco.tamanho - capitulo) <= DIFERENCA_DE_TAMANHO
                and capitulos[-1]
            ):
                capitulos.append([])
        capitulos[-1].append(bloco)
    return tuple(tuple(capitulo) for capitulo in capitulos if capitulo)


def _tamanho_do_capitulo(blocos: Sequence[Bloco]) -> float | None:
    paginas_por_tamanho: dict[float, set[int]] = {}
    for bloco in blocos:
        if bloco.tipo is TipoDeBloco.TITULO:
            paginas_por_tamanho.setdefault(round(bloco.tamanho, 1), set()).add(bloco.pagina)
    frequentes = [
        t for t, paginas in paginas_por_tamanho.items() if len(paginas) >= PAGINAS_DO_CAPITULO
    ]
    return max(frequentes) if frequentes else None


def _niveis(blocos: Sequence[Bloco], capitulo: float | None) -> dict[float, int]:
    """Nível 1 para o capítulo e o que for maior que ele; os menores descem, até o 6."""
    tamanhos = sorted(
        {round(b.tamanho, 1) for b in blocos if b.tipo is TipoDeBloco.TITULO}, reverse=True
    )
    topo = capitulo if capitulo is not None else (tamanhos[0] if tamanhos else 0.0)
    menores = [t for t in tamanhos if t < topo - DIFERENCA_DE_TAMANHO]
    niveis = {t: 1 for t in tamanhos if t not in menores}
    niveis.update({t: min(n, 6) for n, t in enumerate(menores, 2)})
    return niveis
