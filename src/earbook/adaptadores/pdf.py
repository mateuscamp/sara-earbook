# SPDX-License-Identifier: GPL-3.0-or-later
"""Lê o PDF com o pdfminer.six e devolve páginas do domínio (ADR-0004).

É o único módulo que importa a biblioteca de PDF.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from statistics import mean

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTChar, LTPage, LTTextBox, LTTextLine
from pdfminer.pdfdocument import PDFEncryptionError

from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.segmento import normalizar_espacos

# Medido no spike: o código do "Hard Parts" vem em UbuntuMono.
_FONTE_MONOESPACADA = re.compile(r"mono|courier|code|consol", re.IGNORECASE)


class PdfInvalidoError(ValueError):
    pass


def ler_paginas(pdf: Path) -> tuple[Pagina, ...]:
    """Uma `Pagina` por página do PDF, com as linhas de texto na ordem do pdfminer.

    Converte uma página por vez: guardar todos os layouts do pdfminer levava o
    Competente (503 páginas) a 720 MB de memória (A3 da auditoria).
    """
    # O arquivo abre fora do `try`: arquivo inexistente é OSError da máquina, enquanto o
    # OSError de dentro da leitura vem do conteúdo (F2: xref com deslocamento negativo).
    with pdf.open("rb") as arquivo:
        layouts = extract_pages(arquivo, laparams=LAParams())
        paginas: list[Pagina] = []
        while (layout := _proximo_layout(pdf, layouts)) is not None:
            paginas.append(_pagina(pdf, len(paginas) + 1, layout))
    return tuple(paginas)


def _proximo_layout(pdf: Path, layouts: Iterator[LTPage]) -> LTPage | None:
    """A próxima página do pdfminer, com toda falha dele virando `PdfInvalidoError`.

    O `try` cobre só a biblioteca, não a nossa conversão: bug do adaptador continua
    aparecendo como bug, não como "PDF inválido" (revisão nº 1). Falta de memória é da
    máquina, não do PDF, e passa como veio.
    """
    try:
        return next(layouts, None)
    except MemoryError:
        raise
    except PDFEncryptionError as erro:
        mensagem = f"{pdf}: PDF protegido por senha ({type(erro).__name__})"
        raise PdfInvalidoError(mensagem) from erro
    # PDF é entrada hostil, e o pdfminer deixa escapar qualquer exceção (A2 e P1:
    # RecursionError, AttributeError, TypeError...). O `from` guarda a causa.
    except Exception as erro:
        mensagem = f"{pdf}: não é um PDF válido ({type(erro).__name__}: {erro})"
        raise PdfInvalidoError(mensagem) from erro


def _pagina(pdf: Path, numero: int, layout: LTPage) -> Pagina:
    if layout.height <= 0:
        mensagem = f"{pdf}: a página {numero} tem altura {layout.height}"
        raise PdfInvalidoError(mensagem)
    linhas = [
        _linha(linha, layout.height)
        for caixa in layout
        # LTTextBox é tipado como contêiner de LTTextLine; o LTTextContainer genérico não.
        if isinstance(caixa, LTTextBox)
        for linha in caixa
    ]
    return Pagina(numero, tuple(linha for linha in linhas if linha is not None))


def _linha(linha: LTTextLine, altura: float) -> Linha | None:
    caracteres = [c for c in linha if isinstance(c, LTChar)]
    texto = normalizar_espacos(linha.get_text())
    if not caracteres or not texto:
        return None
    return Linha(
        texto=texto,
        x=linha.x0,
        topo=1 - linha.y1 / altura,
        tamanho=mean(c.size for c in caracteres),
        monoespacada=any(_eh_monoespacada(c.fontname) for c in caracteres),
    )


def _eh_monoespacada(nome_da_fonte: object) -> bool:
    """O pdfminer entrega o nome cru quando ele não é nome PDF: bytes ou número (F1)."""
    return isinstance(nome_da_fonte, str) and _FONTE_MONOESPACADA.search(nome_da_fonte) is not None
