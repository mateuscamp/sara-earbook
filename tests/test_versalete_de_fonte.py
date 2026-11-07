# SPDX-License-Identifier: GPL-3.0-or-later
"""O versalete de fonte própria é versalete (ADR-0004, "Versalete de fonte própria").

No Maudlin (*Philosophy of Physics: Quantum Theory*), os títulos dos 8 experimentos e das
seções vêm em `Archer-Medium-SC700`, uma fonte só de versaletes, num tamanho só e menor que o
corpo. Sem a marca, a linha virava nota e ia para o fim do capítulo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.adaptadores.pdf import ler_paginas
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf_com_nome_de_fonte


def _versaletes(pdf: Path) -> list[tuple[str, bool]]:
    return [(linha.texto, linha.versalete) for p in ler_paginas(pdf) for linha in p.linhas]


@pytest.mark.parametrize(
    ("nome_da_fonte", "versalete"),
    [
        (b"/ZBKYXD+Archer-Medium-SC700", True),
        (b"/Archer-SC", True),
        (b"/Archer-sc", True),
        (b"/MinionPro-Regular", False),
        (b"/ABCDEF+DiscoSC", False),
    ],
    ids=["subconjunto-com-peso", "so-SC", "sc-minusculo", "comum", "SC-sem-separador"],
)
def test_linha_toda_em_fonte_de_versalete_e_versalete(
    tmp_path: Path, nome_da_fonte: bytes, *, versalete: bool
) -> None:
    pdf = montar_pdf_com_nome_de_fonte(tmp_path / "fonte.pdf", nome_da_fonte)
    assert _versaletes(pdf) == [("Texto.", versalete)]


def test_abertura_com_as_primeiras_palavras_em_versalete_nao_e_versalete(tmp_path: Path) -> None:
    # Maudlin p. 18: "Physics has TradiTionally been" abre o capítulo em versalete e segue no
    # corpo. "na pasta " em Helvetica 10,5 mede 43,2 pt.
    linhas = [LinhaDeTeste("na pasta ", 72, 700), LinhaDeTeste("certa", 115.2, 700, negrito=True)]
    pdf = montar_pdf_com_nome_de_fonte(tmp_path / "fonte.pdf", b"/Archer-Medium-SC700", linhas)
    assert _versaletes(pdf) == [("na pasta certa", False)]
