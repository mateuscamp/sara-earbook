# SPDX-License-Identifier: GPL-3.0-or-later
"""Comandos `conferir` e `montar`: da pasta de trabalho ao EPUB para ouvir (ADR-0005)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.adaptadores.pacote_epub import empacotar_pasta
from earbook.adaptadores.xhtml import ids_marcados, montar_xhtml
from earbook.dominio.conferencia import (
    CapituloParaConferir,
    Problema,
    conferir,
    conferir_textos,
)
from earbook.dominio.segmento import Segmento, notas_para_o_fim
from earbook.dominio.trabalho import CapituloPreparado

PROBLEMAS_NA_MENSAGEM = 5


class MontagemRecusadaError(ValueError):
    pass


@dataclass(frozen=True)
class Montagem:
    epub: Path
    capitulos: int
    segmentos: int
    notas: int
    """Notas de rodapé levadas para o fim do capítulo."""


def epub_padrao(pasta: Path) -> Path:
    """`epub_padrao(Path("Duna.earbook"))` → `Path("Duna.pronto.epub")`."""
    return pasta.with_suffix(".pronto.epub")


def conferir_pasta(pasta: Path) -> tuple[Problema, ...]:
    """Os problemas que impedem o `montar`; vazio quando nada some, sobra ou se repete."""
    capitulos = trabalho.ler_capitulos(pasta)
    limpeza = trabalho.ler_limpeza(pasta)
    ids = conferir(
        [_para_conferir(pasta, capitulo) for capitulo in capitulos],
        limpeza.removidos,
        limpeza.juntados,
    )
    limpos = [s for capitulo in capitulos for s in trabalho.ler_limpos(pasta, capitulo.id)]
    return tuple(sorted([*ids, *conferir_textos(limpos)], key=lambda problema: problema.id))


def montar(pasta: Path, destino: Path) -> Montagem:
    """Grava em `destino` o EPUB original com o texto final de cada segmento.

    Recusa antes de gravar qualquer coisa se o `conferir` acha problema, para que o livro
    montado nunca perca texto em silêncio.
    """
    if destino.exists():
        mensagem = f"{destino} já existe"
        raise FileExistsError(mensagem)
    problemas = conferir_pasta(pasta)
    if problemas:
        raise MontagemRecusadaError(_recusa(pasta, problemas))
    capitulos = trabalho.ler_capitulos(pasta)
    limpos = {capitulo.id: trabalho.ler_limpos(pasta, capitulo.id) for capitulo in capitulos}
    substituicoes = {
        capitulo.arquivo: _montar_capitulo(pasta, capitulo, limpos[capitulo.id])
        for capitulo in capitulos
    }
    empacotar_pasta(trabalho.pasta_do_epub(pasta), destino, substituicoes)
    segmentos = sum(len(lista) for lista in limpos.values())
    notas = sum(len(notas_para_o_fim(lista)) for lista in limpos.values())
    return Montagem(destino, len(capitulos), segmentos, notas)


def _para_conferir(pasta: Path, capitulo: CapituloPreparado) -> CapituloParaConferir:
    return CapituloParaConferir(
        capitulo.id,
        tuple(s.id for s in trabalho.ler_segmentos(pasta, capitulo.id)),
        tuple(s.id for s in trabalho.ler_limpos(pasta, capitulo.id)),
        ids_marcados(trabalho.ler_xhtml(pasta, capitulo.arquivo), capitulo.arquivo),
    )


def _montar_capitulo(
    pasta: Path, capitulo: CapituloPreparado, limpos: tuple[Segmento, ...]
) -> bytes:
    textos = {segmento.id: segmento.texto for segmento in limpos}
    notas = notas_para_o_fim(limpos)
    return montar_xhtml(
        trabalho.ler_xhtml(pasta, capitulo.arquivo), textos, notas, capitulo.arquivo
    )


def _recusa(pasta: Path, problemas: tuple[Problema, ...]) -> str:
    primeiros = "; ".join(f"{p.id}: {p.motivo}" for p in problemas[:PROBLEMAS_NA_MENSAGEM])
    resto = len(problemas) - PROBLEMAS_NA_MENSAGEM
    mais = f"; e mais {resto} (earbook conferir {pasta})" if resto > 0 else ""
    return f"{pasta}: o conferir achou {len(problemas)} problemas: {primeiros}{mais}"
