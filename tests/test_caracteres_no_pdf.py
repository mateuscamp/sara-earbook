# SPDX-License-Identifier: GPL-3.0-or-later
"""O adaptador lê os caracteres do PDF e entrega a linha sem a chamada sobrescrita, sem o espaço
inventado na letra espaçada e com a família da letra (ADR-0004, "Número de referência e espaço
falso" e "Tabela e figura pela letra")."""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.adaptadores.pdf import ler_paginas
from earbook.comandos.cli import principal
from earbook.comandos.importar_pdf import MOTIVO_DA_CHAMADA, importar_pdf
from earbook.dominio.paginacao import LinhaRemovida
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf


def _linhas(pdf: Path) -> list[tuple[str, tuple[str, ...]]]:
    return [(linha.texto, linha.chamadas) for p in ler_paginas(pdf) for linha in p.linhas]


def test_chamada_sobrescrita_sai_da_linha_e_fica_registrada(tmp_path: Path) -> None:
    linha = LinhaDeTeste("of the wages.^1^ (to", 72, 700, tamanho=10, sobrescrito=True)
    pdf = montar_pdf(tmp_path / "livro.pdf", [[linha]])
    assert _linhas(pdf) == [("of the wages. (to", ("wages.[1]",))]


def test_nome_com_letra_espacada_sai_sem_o_espaco_inventado(tmp_path: Path) -> None:
    # O par "AT" do Gotham-Bold vem apertado (vão de 0,1 pt contra 1 pt), e o "ATA" parecia
    # palavra para a regra da letra espaçada.
    texto = "NA|TA|LIE MORYL, CH|ARLES INTURRISI"
    linha = LinhaDeTeste(texto, 72, 700, tamanho=10, espacamento=1.0)
    pdf = montar_pdf(tmp_path / "livro.pdf", [[linha]])
    assert _linhas(pdf) == [("NATALIE MORYL, CHARLES INTURRISI", ())]


def test_a_linha_traz_a_familia_da_letra(tmp_path: Path) -> None:
    linhas = [
        LinhaDeTeste("Texto em Helvetica.", 72, 700),
        LinhaDeTeste("Texto em Times.", 72, 680, serifa=True),
        LinhaDeTeste("Texto em negrito.", 72, 660, negrito=True),
    ]
    pdf = montar_pdf(tmp_path / "livro.pdf", [linhas])
    familias = [linha.fonte for p in ler_paginas(pdf) for linha in p.linhas]
    assert familias == ["Helvetica", "Times", "Helvetica"]


def test_importar_pdf_registra_a_chamada_e_o_resumo_a_conta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpo = [
        LinhaDeTeste(f"Linha {n} do texto corrido do livro.", 72, 700 - 14 * n, tamanho=10)
        for n in range(8)
    ]
    chamada = LinhaDeTeste("of the wages.^1^ (to", 72, 560, tamanho=10, sobrescrito=True)
    pdf = montar_pdf(tmp_path / "livro.pdf", [[*corpo, chamada]])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub")
    assert importacao.chamadas == (LinhaRemovida(1, MOTIVO_DA_CHAMADA, "wages.[1]"),)
    assert principal(["importar-pdf", str(pdf), "--epub", str(tmp_path / "outro.epub")]) == 0
    saida = capsys.readouterr().out
    assert "1 número de referência sobrescrito tirado." in saida
