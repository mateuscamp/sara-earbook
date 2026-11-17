# SPDX-License-Identifier: GPL-3.0-or-later
"""O texto fora da página sai do áudio (ADR-0004, "A ordem das colunas no Miller").

O PDF do Miller grava, além da borda do papel, o texto de cada fórmula ("V˙A/Q˙", "A c l a r a m
i e n t o d e c r e a t i n i-"): o leitor de PDF não o mostra, e a voz o lia no meio da frase.
Ele também entrava num lado da calha e escondia as colunas da página.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.adaptadores.pdf import ler_paginas
from earbook.comandos.cli import principal
from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.fora_da_pagina import (
    MOTIVO_DO_TEXTO_FORA_DA_PAGINA,
    tirar_texto_fora_da_pagina,
)
from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginacao import LinhaRemovida
from tests.pdf_de_teste import LARGURA, LinhaDeTeste, montar_pdf


def _linha(texto: str, topo: float, *, fora: bool = False) -> Linha:
    return Linha(texto, x=60.0, fim=308.0, topo=topo, tamanho=9.0, fora_da_pagina=fora)


def test_linha_fora_da_pagina_sai_registrada_com_a_pagina() -> None:
    dentro = _linha("La embolia pulmonar causa alteración del", 0.2)
    formula = _linha("V˙A/Q˙", 0.2, fora=True)
    limpas = tirar_texto_fora_da_pagina([Pagina(7, (dentro, formula))])
    assert [linha.texto for linha in limpas.paginas[0].linhas] == [dentro.texto]
    assert limpas.remocoes == (LinhaRemovida(7, MOTIVO_DO_TEXTO_FORA_DA_PAGINA, "V˙A/Q˙"),)


def _pagina_com_formula_fora() -> list[LinhaDeTeste]:
    corpo = [
        LinhaDeTeste(f"Texto corrido da linha {k} do livro de teste, dentro da página.", 72, y)
        for k, y in enumerate(range(700, 560, -14))
    ]
    fora = [
        LinhaDeTeste("Aclaramiento de creatinina", LARGURA + 140, 500),
        LinhaDeTeste("V/Q", -200, 450),
    ]
    na_borda = LinhaDeTeste("1990", LARGURA - 15, 400)
    return [*corpo, *fora, na_borda]


def test_adaptador_diz_qual_linha_esta_inteira_fora_da_pagina(tmp_path: Path) -> None:
    linhas = ler_paginas(montar_pdf(tmp_path / "livro.pdf", [_pagina_com_formula_fora()]))[0].linhas
    # Na ordem do pdfminer, a linha da esquerda vem antes.
    assert [linha.texto for linha in linhas if linha.fora_da_pagina] == [
        "V/Q",
        "Aclaramiento de creatinina",
    ]
    # A célula de tabela que passa da borda só em parte (Miller p. 748) continua na página.
    assert [linha.fora_da_pagina for linha in linhas if linha.texto == "1990"] == [False]


def test_importar_pdf_tira_o_texto_fora_da_pagina_e_o_resumo_o_conta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf = montar_pdf(tmp_path / "livro.pdf", [_pagina_com_formula_fora()])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub")
    assert [(r.motivo, r.texto) for r in importacao.remocoes] == [
        (MOTIVO_DO_TEXTO_FORA_DA_PAGINA, "V/Q"),
        (MOTIVO_DO_TEXTO_FORA_DA_PAGINA, "Aclaramiento de creatinina"),
    ]
    assert "Aclaramiento" not in " ".join(bloco.texto for bloco in importacao.livro.blocos)
    assert principal(["importar-pdf", str(pdf), "--epub", str(tmp_path / "outro.epub")]) == 0
    assert f"  {MOTIVO_DO_TEXTO_FORA_DA_PAGINA}: 2" in capsys.readouterr().out


def test_chamada_da_linha_fora_da_pagina_nao_prova_as_duvidosas(tmp_path: Path) -> None:
    # A página prova a chamada duvidosa ("6 h¹⁴⁸") com 3 chamadas certas. A da linha fora da
    # página não conta: ela sai do áudio, e a página só tem 2 (code-review).
    frases = [
        LinhaDeTeste(f"La frase número {k} del libro termina aquí.^{k + 10}^ Y sigue.", 72, y)
        for k, y in enumerate((700, 686))
    ]
    fora = LinhaDeTeste("La fórmula termina.^30^ Y sigue.", LARGURA + 140, 500)
    duvidosa = LinhaDeTeste("La vida media es de 6 h^148^. Y nada más.", 72, 100)
    linhas = [
        LinhaDeTeste(linha.texto, linha.x, linha.y, sobrescrito=True)
        for linha in (*frases, fora, duvidosa)
    ]
    pagina = ler_paginas(montar_pdf(tmp_path / "livro.pdf", [linhas]))[0]
    assert [linha.texto for linha in pagina.linhas if "vida media" in linha.texto] == [
        "La vida media es de 6 h148. Y nada más."
    ]
