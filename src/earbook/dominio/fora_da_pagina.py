# SPDX-License-Identifier: GPL-3.0-or-later
"""O texto fora da página do PDF: além da borda do papel (ADR-0004, "A ordem das colunas no
Miller").

O PDF do Miller grava o texto de cada fórmula além da borda da página, à direita (x de 754 a 895,
numa página de 612 pt) ou à esquerda (x negativo): "V˙A/Q˙", "A c l a r a m i e n t o d e c r e a
t i n i-". O leitor de PDF não o mostra, e a voz o lia no meio da frase. Ele também entrava num
lado da calha e escondia as colunas da página: 1.217 linhas no livro. Só o adaptador sabe
onde a página acaba; ele marca a linha, e a regra a tira com registro, como a camada do OCR.
"""

from __future__ import annotations

from collections.abc import Sequence

from earbook.dominio.pagina import Pagina
from earbook.dominio.paginacao import PaginasLimpas
from earbook.dominio.tabelas_e_figuras import sem_as_linhas

MOTIVO_DO_TEXTO_FORA_DA_PAGINA = "texto fora da página: além da borda do papel"


def tirar_texto_fora_da_pagina(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """As páginas sem as linhas inteiras fora da página, e uma remoção registrada por linha."""
    saem = {
        (p, n): MOTIVO_DO_TEXTO_FORA_DA_PAGINA
        for p, pagina in enumerate(paginas)
        for n, linha in enumerate(pagina.linhas)
        if linha.fora_da_pagina
    }
    return sem_as_linhas(paginas, saem)
