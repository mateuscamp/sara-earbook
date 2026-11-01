# SPDX-License-Identifier: GPL-3.0-or-later
"""Comando `importar-pdf`: PDF → EPUB simples, pronto para o `preparar` (ADR-0004)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from earbook.adaptadores.epub_simples import gravar_epub
from earbook.adaptadores.pdf import ler_paginas
from earbook.dominio.blocos import LivroMontado, dividir_em_capitulos, montar_blocos
from earbook.dominio.paginacao import LinhaRemovida, tirar_cabecalhos_e_rodapes


class PdfSemTextoError(ValueError):
    pass


@dataclass(frozen=True)
class Importacao:
    epub: Path
    paginas: int
    remocoes: tuple[LinhaRemovida, ...]
    livro: LivroMontado
    capitulos: int


def epub_padrao(pdf: Path) -> Path:
    """`epub_padrao(Path("Duna.pdf"))` → `Path("Duna.epub")`."""
    return pdf.with_suffix(".epub")


def importar_pdf(pdf: Path, epub: Path, idioma: str = "und") -> Importacao:
    """Lê o PDF, tira cabeçalho e rodapé, monta parágrafos e grava o EPUB em `epub`.

    O título do livro é o nome do arquivo: o metadado de título do PDF costuma ser
    o nome do arquivo do editor ("Microsoft Word - cap1.doc"), e o ouvido o ouviria.
    """
    if epub.exists():
        # A gravação também recusa; checar antes poupa os minutos de leitura do PDF.
        mensagem = f"{epub} já existe"
        raise FileExistsError(mensagem)
    paginas = ler_paginas(pdf)
    limpas = tirar_cabecalhos_e_rodapes(paginas)
    livro = montar_blocos(limpas.paginas)
    if not livro.blocos:
        mensagem = f"{pdf}: nenhum texto nas {len(paginas)} páginas (escaneado? não há OCR)"
        raise PdfSemTextoError(mensagem)
    capitulos = dividir_em_capitulos(livro.blocos)
    gravar_epub(epub, pdf.stem, idioma, capitulos)
    return Importacao(epub, len(paginas), limpas.remocoes, livro, len(capitulos))
