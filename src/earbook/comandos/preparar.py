# SPDX-License-Identifier: GPL-3.0-or-later
"""Comando `preparar`: EPUB → pasta de trabalho com segmentos prontos para traduzir."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.adaptadores.pacote_epub import PacoteEpub, extrair_epub
from earbook.adaptadores.xhtml import segmentar_xhtml
from earbook.dominio.limpeza import LivroLimpo, limpar_para_o_ouvido
from earbook.dominio.segmento import Segmento, id_do_capitulo
from earbook.dominio.trabalho import CapituloPreparado, LivroPreparado, TextoForaDeSegmento


@dataclass(frozen=True)
class Preparo:
    livro: LivroPreparado
    limpeza: LivroLimpo


def pasta_padrao(epub: Path) -> Path:
    """`pasta_padrao(Path("Duna.epub"))` → `Path("Duna.earbook")`."""
    return epub.with_suffix(".earbook")


def preparar(epub: Path, pasta: Path) -> Preparo:
    """Extrai, segmenta, limpa e grava o livro em `pasta`, que não pode existir ainda.

    Se algo falhar no meio, apaga a pasta que acabou de criar: pasta pela metade
    faria o próximo `preparar` recusar sem motivo.
    """
    trabalho.criar_pasta_de_trabalho(pasta)
    try:
        pacote = extrair_epub(epub, trabalho.pasta_do_epub(pasta))
        livro, segmentados = _segmentar_livro(epub, pasta, pacote)
        limpeza = limpar_para_o_ouvido(segmentados, pacote.titulo, pacote.autor)
        for capitulo in limpeza.capitulos:
            trabalho.gravar_limpos(pasta, capitulo)
        trabalho.gravar_limpeza(pasta, limpeza)
        trabalho.gravar_livro(pasta, livro)
    except BaseException:
        shutil.rmtree(pasta)
        raise
    return Preparo(livro, limpeza)


def _segmentar_livro(
    epub: Path, pasta: Path, pacote: PacoteEpub
) -> tuple[LivroPreparado, list[tuple[str, list[Segmento]]]]:
    capitulos: list[CapituloPreparado] = []
    segmentados: list[tuple[str, list[Segmento]]] = []
    fora: list[TextoForaDeSegmento] = []
    for posicao, arquivo in enumerate(pacote.spine, start=1):
        capitulo = id_do_capitulo(posicao)
        resultado = segmentar_xhtml(trabalho.ler_xhtml(pasta, arquivo), capitulo, arquivo)
        trabalho.gravar_xhtml(pasta, arquivo, resultado.xhtml_marcado)
        trabalho.gravar_segmentos(pasta, capitulo, resultado.segmentos)
        capitulos.append(CapituloPreparado(capitulo, arquivo, len(resultado.segmentos)))
        segmentados.append((capitulo, resultado.segmentos))
        fora.extend(TextoForaDeSegmento(capitulo, t) for t in resultado.texto_fora_de_segmento)
    return _livro(epub, pacote, capitulos, fora), segmentados


def _livro(
    epub: Path,
    pacote: PacoteEpub,
    capitulos: list[CapituloPreparado],
    fora: list[TextoForaDeSegmento],
) -> LivroPreparado:
    return LivroPreparado(
        origem=epub.name,
        titulo=pacote.titulo,
        autor=pacote.autor,
        idioma=pacote.idioma,
        capitulos=tuple(capitulos),
        texto_fora_de_segmento=tuple(fora),
        itens_do_spine_ignorados=pacote.ignorados,
    )
