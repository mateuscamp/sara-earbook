# SPDX-License-Identifier: GPL-3.0-or-later
"""Ponto de entrada do `ai-book`. A saída é texto para humano; os dados ficam na pasta."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ai_book.comandos.preparar import pasta_padrao, preparar
from ai_book.dominio.trabalho import LivroPreparado

EXEMPLOS_DE_TEXTO_FORA = 5


class _Opcoes(argparse.Namespace):
    """Tipa o resultado do argparse, que de outro modo devolve atributos `Any`.

    Os valores aqui são só o ponto de partida; o argparse sobrescreve os dois.
    """

    epub: Path = Path()
    pasta: Path | None = None


def principal(argumentos: list[str] | None = None) -> int:
    """`principal(["preparar", "Duna.epub"])` cria `Duna.ai-book/` e devolve 0."""
    opcoes = _analisador().parse_args(argumentos, namespace=_Opcoes())
    pasta = opcoes.pasta or pasta_padrao(opcoes.epub)
    try:
        livro = preparar(opcoes.epub, pasta)
    except (OSError, ValueError) as erro:
        print(f"ai-book: {erro}", file=sys.stderr)
        return 1
    print(_resumo(livro, pasta))
    return 0


def _analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(prog="ai-book")
    comandos = analisador.add_subparsers(dest="comando", required=True)
    preparo = comandos.add_parser("preparar", help="EPUB → pasta de trabalho com segmentos")
    _ = preparo.add_argument("epub", type=Path)
    _ = preparo.add_argument("--pasta", type=Path, help="padrão: ao lado do EPUB, com .ai-book")
    return analisador


def _resumo(livro: LivroPreparado, pasta: Path) -> str:
    segmentos = sum(c.segmentos for c in livro.capitulos)
    fora = livro.texto_fora_de_segmento
    linhas = [
        f"Preparado em {pasta}: {len(livro.capitulos)} capítulos, {segmentos} segmentos.",
        f"{len(fora)} {'trecho' if len(fora) == 1 else 'trechos'} fora de segmento.",
    ]
    linhas += [f"  {t.capitulo}: {t.texto}" for t in fora[:EXEMPLOS_DE_TEXTO_FORA]]
    if len(fora) > EXEMPLOS_DE_TEXTO_FORA:
        linhas.append(f"  ... a lista completa está em {pasta / 'livro.json'}")
    return "\n".join(linhas + _linhas_dos_ignorados(livro))


def _linhas_dos_ignorados(livro: LivroPreparado) -> list[str]:
    """Todos, sem corte: cada um pode ser um capítulo inteiro fora do áudio."""
    ignorados = livro.itens_do_spine_ignorados
    if not ignorados:
        return []
    plural = "item do spine ignorado" if len(ignorados) == 1 else "itens do spine ignorados"
    return [f"{len(ignorados)} {plural}:"] + [f"  {i.idref}: {i.motivo}" for i in ignorados]
