# SPDX-License-Identifier: GPL-3.0-or-later
"""Comando `preparar`: EPUB → pasta de trabalho com segmentos prontos para traduzir."""

from __future__ import annotations

import shutil
from pathlib import Path

from ai_book.adaptadores import pasta_de_trabalho as trabalho
from ai_book.adaptadores.pacote_epub import PacoteEpub, extrair_epub
from ai_book.adaptadores.xhtml import segmentar_xhtml
from ai_book.dominio.segmento import id_do_capitulo
from ai_book.dominio.trabalho import CapituloPreparado, LivroPreparado, TextoForaDeSegmento


def pasta_padrao(epub: Path) -> Path:
    """`pasta_padrao(Path("Duna.epub"))` → `Path("Duna.ai-book")`."""
    return epub.with_suffix(".ai-book")


def preparar(epub: Path, pasta: Path) -> LivroPreparado:
    """Extrai, segmenta e grava o livro em `pasta`, que não pode existir ainda.

    Se algo falhar no meio, apaga a pasta que acabou de criar: pasta pela metade
    faria o próximo `preparar` recusar sem motivo.
    """
    trabalho.criar_pasta_de_trabalho(pasta)
    try:
        pacote = extrair_epub(epub, trabalho.pasta_do_epub(pasta))
        livro = _segmentar_livro(epub, pasta, pacote)
        trabalho.gravar_livro(pasta, livro)
    except BaseException:
        shutil.rmtree(pasta)
        raise
    return livro


def _segmentar_livro(epub: Path, pasta: Path, pacote: PacoteEpub) -> LivroPreparado:
    capitulos: list[CapituloPreparado] = []
    fora: list[TextoForaDeSegmento] = []
    for posicao, arquivo in enumerate(pacote.spine, start=1):
        capitulo = id_do_capitulo(posicao)
        resultado = segmentar_xhtml(trabalho.ler_xhtml(pasta, arquivo), capitulo, arquivo)
        trabalho.gravar_xhtml(pasta, arquivo, resultado.xhtml_marcado)
        trabalho.gravar_segmentos(pasta, capitulo, resultado.segmentos)
        capitulos.append(CapituloPreparado(capitulo, arquivo, len(resultado.segmentos)))
        fora.extend(TextoForaDeSegmento(capitulo, t) for t in resultado.texto_fora_de_segmento)
    return LivroPreparado(
        origem=epub.name,
        titulo=pacote.titulo,
        autor=pacote.autor,
        idioma=pacote.idioma,
        capitulos=tuple(capitulos),
        texto_fora_de_segmento=tuple(fora),
        itens_do_spine_ignorados=pacote.ignorados,
    )
