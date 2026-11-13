# SPDX-License-Identifier: GPL-3.0-or-later
"""A palavra de rótulo com a caixa trocada volta à caixa normal nas menções (ADR-0004,
"Bibliografia pela letra e rótulo com a caixa trocada").

O versalete do Manica mapeia parte das letras pequenas para a maiúscula: "No QuAdro 13.1", "ver
FigurA 12.3", "(tAb. 4.2)". São 802 menções fora de título. O Mateus decidiu acertar só as
palavras de rótulo, só nas menções; os títulos e as outras palavras ficam como estão.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.comandos.cli import principal
from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.blocos import Bloco
from earbook.dominio.caixa_do_rotulo import acertar_rotulos
from earbook.dominio.tipo_da_linha import TipoDeBloco
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf


def _bloco(texto: str, tipo: TipoDeBloco = TipoDeBloco.PARAGRAFO) -> Bloco:
    return Bloco(tipo, texto, pagina=1, tamanho=9.3)


def _acertado(texto: str, tipo: TipoDeBloco = TipoDeBloco.PARAGRAFO) -> str:
    blocos, _ = acertar_rotulos([_bloco(texto, tipo)])
    return blocos[0].texto


@pytest.mark.parametrize(
    ("antes", "depois"),
    [
        ("Os tipos estão na FigurA 12.3, ao lado.", "Os tipos estão na Figura 12.3, ao lado."),
        ("No QuAdro 13.1, encontram-se os fatores.", "No Quadro 13.1, encontram-se os fatores."),
        (
            "Ver doses (tAb. 4.2) e efeitos (fIg. 4.1).",
            "Ver doses (tab. 4.2) e efeitos (fig. 4.1).",
        ),
        ("A tAbelA 8.1 e os QuADros 8.2 e 8.3.", "A tabela 8.1 e os Quadros 8.2 e 8.3."),
        ("Véanse la tAblA 6-1 y el cuAdro 4-1.", "Véanse la tabla 6-1 y el cuadro 4-1."),
        ("Compare as FigurAs 2 e 3.", "Compare as Figuras 2 e 3."),
    ],
)
def test_a_palavra_de_rotulo_antes_de_numero_volta_a_caixa_normal(antes: str, depois: str) -> None:
    assert _acertado(antes) == depois


@pytest.mark.parametrize(
    "texto",
    [
        "A Figura 12.3 e o Quadro 13.1 ficam.",
        "A figura 12.3 e a tabela 8.1 ficam.",
        "FIGURA 12.3 e QUADRO 13.1, em maiúsculas, ficam.",
        "A FigurA mostra o plexo, e o QuAdro resume.",
        "Na AnestesiA 12.3 nada muda, nem em históriA 4.",
        "A configurA 3 vezes e o esQuAdro 4 ficam.",
    ],
)
def test_o_que_nao_e_rotulo_com_a_caixa_trocada_antes_de_numero_nao_muda(texto: str) -> None:
    assert _acertado(texto) == texto


def test_o_titulo_fica_como_esta() -> None:
    assert _acertado("QuAdro 13.1 FAtores de risco", TipoDeBloco.TITULO) == (
        "QuAdro 13.1 FAtores de risco"
    )


def test_o_bloco_de_codigo_fica_como_esta() -> None:
    # R4 da code-review: a decisão cobre as menções da prosa, e não o que o código escreve.
    assert _acertado("print(tAb. 4, FigurA 2)", TipoDeBloco.CODIGO) == "print(tAb. 4, FigurA 2)"


def test_a_nota_tambem_e_mencao() -> None:
    assert _acertado("Fonte: adaptado da FigurA 2.4.", TipoDeBloco.NOTA) == (
        "Fonte: adaptado da Figura 2.4."
    )


def test_conta_cada_rotulo_acertado() -> None:
    blocos = [_bloco("A FigurA 1.1 e o QuAdro 1.2."), _bloco("Sem rótulo."), _bloco("A tAb. 2.1.")]
    _, acertados = acertar_rotulos(blocos)
    assert acertados == 3


def test_importar_pdf_acerta_a_mencao_e_o_resumo_a_conta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    linhas = [
        LinhaDeTeste("O bloqueio aparece na FigurA 12.3 deste livro,", 72, 700, serifa=True),
        LinhaDeTeste("e as doses, no QuAdro 13.1 do capítulo seguinte.", 72, 686, serifa=True),
    ]
    pdf = montar_pdf(tmp_path / "livro.pdf", [linhas])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub")
    esperado = (
        "O bloqueio aparece na Figura 12.3 deste livro, e as doses, no Quadro 13.1 do capítulo"
        " seguinte."
    )
    assert [bloco.texto for bloco in importacao.livro.blocos] == [esperado]
    assert principal(["importar-pdf", str(pdf), "--epub", str(tmp_path / "outro.epub")]) == 0
    assert "2 palavras de rótulo com a caixa acertada (Figura, Quadro, Tabela)." in (
        capsys.readouterr().out
    )
