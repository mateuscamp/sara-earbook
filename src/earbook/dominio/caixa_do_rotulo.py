# SPDX-License-Identifier: GPL-3.0-or-later
"""A palavra de rótulo com a caixa trocada volta à caixa normal nas menções (ADR-0004,
"Bibliografia pela letra e rótulo com a caixa trocada").

O versalete do Manica mapeia parte das letras pequenas para a maiúscula, e a menção no corpo sai
"No QuAdro 13.1", "ver FigurA 12.3", "(tAb. 4.2)": 802 vezes, em 30 formas. A caixa certa das
outras palavras ("AnestesiA", "históriA") não está no PDF; a destas está, porque a maiúscula no
meio da palavra de rótulo nunca é de propósito. O Mateus decidiu (2026-11-13): só estas palavras,
só nas menções; o título fica como está.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace

from earbook.dominio.blocos import Bloco
from earbook.dominio.tipo_da_linha import TipoDeBloco

# A palavra de rótulo em português e em espanhol, inteira, seguida de número: "Figura 12.3",
# "fig. 4.1", "Quadros 8.2", "tab. 4.2", "tabla 6-1", "cuadro 4-1". "configurA 3" não é rótulo.
_ROTULO_ANTES_DE_NUMERO = re.compile(
    r"(?<![^\W\d_])(?:figuras?|figs?\.|quadros?|tabelas?|tabs?\.|tablas?|cuadros?)(?=\s+\d)",
    re.IGNORECASE,
)
# A menção mora na prosa: o título fica como está, por decisão, e o código também.
_COM_MENCAO = frozenset({TipoDeBloco.PARAGRAFO, TipoDeBloco.NOTA})


def acertar_rotulos(blocos: Sequence[Bloco]) -> tuple[tuple[Bloco, ...], int]:
    """Os blocos com a palavra de rótulo acertada nos parágrafos e nas notas, e quantas foram.

    A primeira letra fica como veio e o resto vai para a minúscula: "QuAdro 13.1" vira "Quadro
    13.1", e "tAb. 4.2", "tab. 4.2". A palavra toda em maiúsculas ("QUADRO 2.1") não muda.
    """
    acertados = 0
    novos: list[Bloco] = []
    for bloco in blocos:
        trocadas = _trocadas(bloco.texto) if bloco.tipo in _COM_MENCAO else 0
        acertados += trocadas
        texto = _ROTULO_ANTES_DE_NUMERO.sub(_na_caixa_normal, bloco.texto)
        novos.append(replace(bloco, texto=texto) if trocadas else bloco)
    return tuple(novos), acertados


def _na_caixa_normal(achado: re.Match[str]) -> str:
    palavra = achado.group()
    return palavra[0] + palavra[1:].lower() if _trocada(palavra) else palavra


def _trocada(palavra: str) -> bool:
    """Maiúscula depois da primeira letra, sem a palavra estar toda em maiúsculas."""
    return palavra != palavra.upper() and palavra[1:] != palavra[1:].lower()


def _trocadas(texto: str) -> int:
    return sum(_trocada(achado.group()) for achado in _ROTULO_ANTES_DE_NUMERO.finditer(texto))
