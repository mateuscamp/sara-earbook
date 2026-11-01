# SPDX-License-Identifier: GPL-3.0-or-later
"""Layout da pasta de trabalho de um livro. Só este módulo sabe onde cada arquivo fica.

livro.json            metadados, capítulos e texto fora de segmento
segmentos/cNNN.json   segmentos de cada capítulo, em inglês
epub/                 EPUB extraído, com o XHTML marcado por `data-ai-book`
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ai_book.dominio.segmento import Segmento
from ai_book.dominio.trabalho import LivroPreparado


def criar_pasta_de_trabalho(pasta: Path) -> None:
    """Cria a pasta; recusa se ela já existe, para não apagar tradução já feita."""
    if pasta.exists():
        mensagem = f"a pasta de trabalho {pasta} já existe; apague-a ou use outra"
        raise FileExistsError(mensagem)
    (pasta / "segmentos").mkdir(parents=True)


def pasta_do_epub(pasta: Path) -> Path:
    return pasta / "epub"


def ler_xhtml(pasta: Path, arquivo: str) -> bytes:
    return (pasta_do_epub(pasta) / arquivo).read_bytes()


def gravar_xhtml(pasta: Path, arquivo: str, conteudo: bytes) -> None:
    _ = (pasta_do_epub(pasta) / arquivo).write_bytes(conteudo)


def gravar_segmentos(pasta: Path, capitulo: str, segmentos: list[Segmento]) -> None:
    _gravar_json(pasta / "segmentos" / f"{capitulo}.json", [asdict(s) for s in segmentos])


def gravar_livro(pasta: Path, livro: LivroPreparado) -> None:
    _gravar_json(pasta / "livro.json", asdict(livro))


def _gravar_json(caminho: Path, conteudo: object) -> None:
    texto = json.dumps(conteudo, ensure_ascii=False, indent=2)
    _ = caminho.write_text(texto + "\n", encoding="utf-8")
