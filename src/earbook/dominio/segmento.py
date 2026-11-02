# SPDX-License-Identifier: GPL-3.0-or-later
"""Segmento: a menor unidade que o tradutor recebe e devolve.

O ID é o contrato entre `preparar`, tradução e `montar` (ADR-0001): todo ID que
entra na tradução tem de sair dela, sem faltar, sobrar ou repetir.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

# O XML 1.0 não aceita controle fora de tab e quebra de linha, nem surrogate solto. O texto
# vem de PDF e, depois, da tradução; sem a checagem, o lxml recusa sem dizer o segmento.
FORA_DO_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
# Uma palavra, com o apóstrofo de dentro, reto ou tipográfico ("Gul'dan"): a conta da
# conferência da tradução e a prova da capitular (ADR-0006, ADR-0007).
PALAVRA = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*")
# O que pode abrir o parágrafo antes da primeira letra: aspas, travessões e espaço. A marcação
# e a devolução da capitular usam o mesmo, ou discordam de onde a palavra começa (ADR-0007).
ABRE_PARAGRAFO = r"[\u201c\u2018\"'\u2014\u2013\-\s]*"


class Papel(StrEnum):
    TITULO = "titulo"
    PARAGRAFO = "paragrafo"
    NOTA = "nota"
    ITEM = "item"
    CELULA = "celula"
    CITACAO = "citacao"
    # ADR-0008: estes dois existem em segmentos/ e nunca em limpos/; o limpar os tira.
    CODIGO = "codigo"
    INDICE = "indice"


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


def notas_para_o_fim(segmentos: Sequence[Segmento]) -> frozenset[str]:
    """As notas que o `montar` leva para o fim do capítulo (ADR-0005).

    Nenhuma quando o capítulo só tem notas e títulos: é a nota de fim de livro, que fica
    sob o subtítulo do capítulo dela (A3 da auditoria).
    """
    if all(segmento.papel in {Papel.NOTA, Papel.TITULO} for segmento in segmentos):
        return frozenset()
    return frozenset(segmento.id for segmento in segmentos if segmento.papel is Papel.NOTA)
