# SPDX-License-Identifier: GPL-3.0-or-later
"""O texto que a página do PDF não pinta: a camada do OCR sobre as imagens (ADR-0004, "Camada do
OCR sobre as figuras e chamada colada").

O PDF digital que passou por um OCR ganha, por cima de cada figura, o texto que o OCR leu dentro
dela, no modo de pintura 3: existe para a busca, e ninguém o vê. A voz lia "1", "l", "o o o" como
título e parágrafo (Manica: 2.735 linhas em 328 páginas). Pelo texto não se separam do título de
verdade; pela página, sim.
"""

from __future__ import annotations

from collections.abc import Sequence

from earbook.dominio.pagina import Pagina
from earbook.dominio.paginacao import PaginasLimpas
from earbook.dominio.tabelas_e_figuras import Posicao, sem_as_linhas

MOTIVO_DA_CAMADA_DO_OCR = "texto que a página não pinta: camada do OCR sobre a imagem"


def tirar_camada_do_ocr(paginas: Sequence[Pagina]) -> PaginasLimpas:
    """As páginas sem as linhas não pintadas, e uma remoção registrada por linha.

    Só na página em que o texto pintado é a maior parte: a página escaneada, cujo texto só existe
    na camada do OCR, fica como está, mesmo com um carimbo pintado por cima.
    """
    saem: dict[Posicao, str] = {}
    for p, pagina in enumerate(paginas):
        if _a_maior_parte_e_pintada(pagina):
            saem |= {
                (p, n): MOTIVO_DA_CAMADA_DO_OCR
                for n, linha in enumerate(pagina.linhas)
                if linha.nao_pintada
            }
    return sem_as_linhas(paginas, saem)


def _a_maior_parte_e_pintada(pagina: Pagina) -> bool:
    """Mais caracteres pintados que não pintados; no empate, a página fica como está."""
    pintados = sum(len(linha.texto) for linha in pagina.linhas if not linha.nao_pintada)
    nao_pintados = sum(len(linha.texto) for linha in pagina.linhas if linha.nao_pintada)
    return pintados > nao_pintados
