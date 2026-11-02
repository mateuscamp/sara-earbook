# SPDX-License-Identifier: GPL-3.0-or-later
"""Comando `minuto`: em que minuto da escuta cai cada segmento, para o roteiro (ADR-0007)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.dominio.escuta import Posicao, posicoes
from earbook.dominio.segmento import Segmento


def minutos(pasta: Path, ids: Sequence[str]) -> tuple[Posicao, ...]:
    """Conta pelo texto que se ouve: a tradução, quando o segmento tem, ou o texto limpo."""
    traducao = {t.id: t.texto for r in trabalho.ler_respostas(pasta) for t in r.traduzidos}
    capitulos: list[tuple[str, Sequence[Segmento]]] = [
        (
            capitulo.id,
            [
                replace(s, texto=traducao.get(s.id, s.texto))
                for s in trabalho.ler_limpos(pasta, capitulo.id)
            ],
        )
        for capitulo in trabalho.ler_capitulos(pasta)
    ]
    return posicoes(capitulos, ids)
