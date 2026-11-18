# SPDX-License-Identifier: GPL-3.0-or-later
"""A letra da fonte de símbolo vira o que a fonte desenha (ADR-0004, "Letra grega da fonte de
símbolo").

No Miller, a MathematicalPi-One desenha mi, alfa, beta e gama no lugar de "m", "a", "b" e "g", e
o PDF diz a letra latina: "20 mg/kg" de atropina era, na página, 20 microgramas por quilo, e a voz
lia a dose mil vezes maior (p. 1183). Só entra na tabela o que se viu na página renderizada.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.adaptadores.pdf import ler_paginas
from earbook.comandos.cli import principal
from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.nome_da_fonte import letra_desenhada
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf_com_nome_de_fonte

PI = "ULYLLH+MathematicalPi-One"
MI = "\u03bc"


@pytest.mark.parametrize(
    ("letra", "desenho"),
    [
        ("m", MI),
        ("a", "\u03b1"),
        ("b", "\u03b2"),
        ("g", "\u03b3"),
        ("d", "\u03b4"),
        ("l", "\u03bb"),
        ("u", "\u03b8"),
        ("9", "\u2032"),
        ("\ue024", "\u2265"),
    ],
    ids=["mi", "alfa", "beta", "gama", "delta", "lambda", "teta", "linha", "maior-ou-igual"],
)
def test_letra_da_mathematical_pi_vira_o_que_ela_desenha(letra: str, desenho: str) -> None:
    # Visto no Miller: a dose (p. 1183), "theta" (p. 346), "donde lambda" (p. 348), "desde delta"
    # (p. 350), a linha de "T3 linha" (p. 238), "carótida maior ou igual a 70%" (p. 2472).
    assert letra_desenhada(letra, PI) == desenho


@pytest.mark.parametrize(
    ("letra", "fonte", "desenho"),
    [
        ("m", "MathPiOneItalic", MI),
        ("b", "MathPiOneBoldItalic", "\u03b2"),
        ("a", "ABCDEF+MathPiOneBold", "\u03b1"),
        ("a", "MathematicalPi-One-SC700", "\u03b1"),
        ("m", "MathematicalPi-Four", MI),
        ("g", "MathematicalPi-Four-SC700", "\u03b3"),
        ("k", "Symbol", "\u03ba"),
        ("w", "Symbol", "\u03c9"),
        ("k", "Symbol-Italic", "\u03ba"),
    ],
)
def test_o_estilo_da_fonte_de_simbolo_desenha_a_mesma_letra(
    letra: str, fonte: str, desenho: str
) -> None:
    # Visto no Miller: a viscosidade (p. 1556), os betabloqueantes (p. 1409 e 422), os receptores
    # alfa-adrenérgicos no título (p. 428), a dose por minuto (p. 1132), o NF-kappa-B (p. 673 e
    # 851) e a impedância em ômega (p. 830).
    assert letra_desenhada(letra, fonte) == desenho


@pytest.mark.parametrize(
    ("letra", "fonte"),
    [
        ("u", "MathematicalPi-Four"),
        ("\ue03f", PI),
        ("a", "Symbol"),
        ("k", "SymbolSans"),
        ("m", "ULYLLH+StoneSerif"),
        ("m", "MathematicalPi"),
        ("m", b"MathematicalPi-One"),
    ],
    ids=[
        "four-sem-teta",
        "ponto-do-v",
        "symbol-sem-alfa",
        "outra-familia",
        "outra-fonte",
        "sem-o-numero",
        "nome-que-nao-e-texto",
    ],
)
def test_letra_que_nao_se_viu_desenhada_fica(letra: str, fonte: object) -> None:
    assert letra_desenhada(letra, fonte) == letra


def _linha_com_mi(tmp_path: Path) -> Path:
    """A dose com o "m" na fonte de símbolo. A Times de 10,5 pt mede 56 pt em "atropina 20 ", e a
    fonte trocada, 6,3 pt em toda letra."""
    linhas = [
        LinhaDeTeste("Linha do texto corrido do livro, com a dose.", 72, 740, serifa=True),
        LinhaDeTeste("atropina 20 ", 72, 700, serifa=True),
        LinhaDeTeste("m", 128.0, 700),
        LinhaDeTeste("g/kg.", 134.3, 700, serifa=True),
    ]
    return montar_pdf_com_nome_de_fonte(tmp_path / "dose.pdf", f"/{PI}".encode(), linhas)


def test_adaptador_le_a_letra_grega_e_conta_a_troca(tmp_path: Path) -> None:
    linhas = [linha for pagina in ler_paginas(_linha_com_mi(tmp_path)) for linha in pagina.linhas]
    assert [(linha.texto, linha.letras_gregas) for linha in linhas] == [
        ("Linha do texto corrido do livro, com a dose.", 0),
        (f"atropina 20 {MI}g/kg.", 1),
    ]


def test_resumo_do_importar_pdf_conta_as_letras_gregas(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf = _linha_com_mi(tmp_path)
    assert importar_pdf(pdf, tmp_path / "livro.epub").letras_gregas == 1
    assert principal(["importar-pdf", str(pdf), "--epub", str(tmp_path / "outro.epub")]) == 0
    assert "1 letra de fonte de símbolo lida pelo desenho, e não pela letra latina." in (
        capsys.readouterr().out
    )


def test_letra_grega_da_linha_que_sai_da_pagina_nao_conta(tmp_path: Path) -> None:
    # Miller: a MathPiOneItalic do texto das fórmulas gravado além da borda do papel (x < 0).
    linhas = [
        LinhaDeTeste("Linha do texto corrido do livro, com a dose.", 72, 740, serifa=True),
        LinhaDeTeste("Outra linha do texto corrido do livro aqui.", 72, 720, serifa=True),
        LinhaDeTeste("m", 700.0, 700),
    ]
    pdf = montar_pdf_com_nome_de_fonte(tmp_path / "fora.pdf", f"/{PI}".encode(), linhas)
    assert importar_pdf(pdf, tmp_path / "livro.epub").letras_gregas == 0
