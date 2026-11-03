# SPDX-License-Identifier: GPL-3.0-or-later
"""Comando `importar-pdf`: PDF → EPUB simples, pronto para o `preparar` (ADR-0004)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from earbook.adaptadores.epub_simples import gravar_epub
from earbook.adaptadores.pdf import ler_metadados, ler_paginas
from earbook.dominio.blocos import LivroMontado, montar_blocos
from earbook.dominio.capitulos import dividir_em_capitulos
from earbook.dominio.metadados import autor_do_livro, titulo_do_livro
from earbook.dominio.paginacao import LinhaRemovida, tirar_cabecalhos_e_rodapes
from earbook.dominio.texto_escondido import tirar_texto_escondido


class PdfSemTextoError(ValueError):
    pass


@dataclass(frozen=True)
class Importacao:
    epub: Path
    paginas: int
    remocoes: tuple[LinhaRemovida, ...]
    livro: LivroMontado
    capitulos: int
    titulo: str
    autor: str


def epub_padrao(pdf: Path) -> Path:
    """`epub_padrao(Path("Duna.pdf"))` → `Path("Duna.epub")`."""
    return pdf.with_suffix(".epub")


def importar_pdf(
    pdf: Path,
    epub: Path,
    idioma: str = "und",
    titulo: str | None = None,
    autor: str | None = None,
) -> Importacao:
    """Lê o PDF, tira cabeçalho e rodapé, monta parágrafos e grava o EPUB em `epub`.

    Título e autor vêm de `titulo` e `autor`, se dados; senão, do metadado do PDF, que os
    dois livros medidos trazem certos; o título que parece nome de arquivo ("Microsoft
    Word - cap1.doc") cede ao nome do PDF (`dominio/metadados.py`).
    """
    if epub.exists():
        # A gravação também recusa; checar antes poupa os minutos de leitura do PDF.
        mensagem = f"{epub} já existe"
        raise FileExistsError(mensagem)
    paginas = ler_paginas(pdf)
    # O texto escondido sai antes da borda: em letra de título, ele contaria no corpo e na
    # paginação (ADR-0004, "O que ficou da Fase 1").
    visiveis = tirar_texto_escondido(paginas)
    limpas = tirar_cabecalhos_e_rodapes(visiveis.paginas)
    livro = montar_blocos(limpas.paginas)
    if not livro.blocos:
        mensagem = f"{pdf}: nenhum texto nas {len(paginas)} páginas (escaneado? não há OCR)"
        raise PdfSemTextoError(mensagem)
    capitulos = dividir_em_capitulos(livro.blocos)
    metadados = ler_metadados(pdf)
    titulo = titulo or titulo_do_livro(metadados.titulo, pdf.stem)
    autor = autor or autor_do_livro(metadados.autor)
    gravar_epub(epub, titulo, idioma, capitulos, autor=autor)
    remocoes = (*visiveis.remocoes, *limpas.remocoes)
    return Importacao(epub, len(paginas), remocoes, livro, len(capitulos), titulo, autor)
