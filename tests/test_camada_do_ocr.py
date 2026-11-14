# SPDX-License-Identifier: GPL-3.0-or-later
"""O texto que a página não pinta sai do áudio (ADR-0004, "Camada do OCR sobre as figuras e
chamada colada").

O PDF do Manica é digital, mas um OCR leu o que havia dentro das figuras e gravou o resultado no
modo de pintura 3, que ninguém vê na página. A voz lia "1", "l", "o o o" e "~ ~" como título.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.adaptadores.pdf import ler_paginas
from earbook.comandos.cli import principal
from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.camada_do_ocr import MOTIVO_DA_CAMADA_DO_OCR, tirar_camada_do_ocr
from earbook.dominio.pagina import Linha, Pagina
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf


def _linha(texto: str, topo: float, *, nao_pintada: bool = False) -> Linha:
    return Linha(texto, x=42.0, fim=296.0, topo=topo, tamanho=10.0, nao_pintada=nao_pintada)


def _corpo(topo: float, n: int = 6) -> list[Linha]:
    return [_linha(f"Texto corrido da linha {k} do livro.", topo + 0.014 * k) for k in range(n)]


def _textos(paginas: tuple[Pagina, ...]) -> list[list[str]]:
    return [[linha.texto for linha in pagina.linhas] for pagina in paginas]


def test_linha_nao_pintada_sai_registrada_com_a_pagina() -> None:
    figura = [_linha("o o o", 0.5, nao_pintada=True), _linha("~ ~", 0.6, nao_pintada=True)]
    paginas = [Pagina(1, tuple(_corpo(0.1))), Pagina(2, (*_corpo(0.1), *figura))]
    limpas = tirar_camada_do_ocr(paginas)
    assert _textos(limpas.paginas) == _textos((paginas[0], Pagina(2, tuple(_corpo(0.1)))))
    assert [(r.pagina, r.motivo, r.texto) for r in limpas.remocoes] == [
        (2, MOTIVO_DA_CAMADA_DO_OCR, "o o o"),
        (2, MOTIVO_DA_CAMADA_DO_OCR, "~ ~"),
    ]


def test_pagina_escaneada_cujo_texto_so_existe_na_camada_fica() -> None:
    # O texto da página escaneada só existe na camada do OCR: tirá-la seria perder a página.
    escaneada = [
        _linha(f"Texto da página escaneada, linha {k}.", 0.1 + 0.014 * k, nao_pintada=True)
        for k in range(6)
    ]
    paginas = [Pagina(1, tuple(_corpo(0.1))), Pagina(2, tuple(escaneada))]
    limpas = tirar_camada_do_ocr(paginas)
    assert (_textos(limpas.paginas), limpas.remocoes) == (_textos(tuple(paginas)), ())


def test_pagina_em_que_o_texto_nao_pintado_e_a_maior_parte_fica() -> None:
    # A página escaneada com o carimbo pintado por cima ("Baixado por Fulano"): o carimbo não
    # prova que o resto é figura.
    escaneada = [
        _linha(f"Texto da página escaneada, linha {k}.", 0.1 + 0.014 * k, nao_pintada=True)
        for k in range(6)
    ]
    paginas = [Pagina(1, (*escaneada, _linha("Baixado por Fulano.", 0.95)))]
    assert tirar_camada_do_ocr(paginas).remocoes == ()


def test_no_empate_entre_pintado_e_nao_pintado_nada_sai() -> None:
    paginas = [Pagina(1, (_linha("abcde", 0.1), _linha("vwxyz", 0.2, nao_pintada=True)))]
    assert tirar_camada_do_ocr(paginas).remocoes == ()


def test_cada_pagina_decide_por_si() -> None:
    # A figura da página 1 sai; a página 2, escaneada, fica.
    figura = _linha("l 1 T", 0.5, nao_pintada=True)
    escaneada = _linha("Texto da página escaneada.", 0.1, nao_pintada=True)
    paginas = [Pagina(1, (*_corpo(0.1), figura)), Pagina(2, (escaneada,))]
    limpas = tirar_camada_do_ocr(paginas)
    assert [(r.pagina, r.texto) for r in limpas.remocoes] == [(1, "l 1 T")]
    assert _textos(limpas.paginas)[1] == ["Texto da página escaneada."]


def _pagina_com_figura() -> list[LinhaDeTeste]:
    corpo = [
        LinhaDeTeste(f"Texto corrido da linha {k} do livro de teste, que a página pinta.", 72, y)
        for k, y in enumerate(range(700, 560, -14))
    ]
    figura = [
        LinhaDeTeste("o o o", 120, 400, tamanho=31.2, sem_tinta=True),
        LinhaDeTeste("l", 300, 360, tamanho=82.4, serifa=True, sem_tinta=True),
    ]
    return [*corpo, *figura, LinhaDeTeste("O texto continua depois da figura.", 72, 200)]


def test_adaptador_diz_qual_linha_a_pagina_nao_pinta(tmp_path: Path) -> None:
    pdf = montar_pdf(tmp_path / "livro.pdf", [_pagina_com_figura()])
    linhas = ler_paginas(pdf)[0].linhas
    assert [linha.texto for linha in linhas if linha.nao_pintada] == ["o o o", "l"]
    # O modo de pintura volta ao normal depois da figura.
    assert [
        linha.nao_pintada for linha in linhas if linha.texto.startswith("O texto continua")
    ] == [False]


def test_linha_que_mistura_letra_pintada_e_nao_pintada_nao_conta(tmp_path: Path) -> None:
    mista = [
        LinhaDeTeste("Legenda da", 72, 400),
        LinhaDeTeste("figura", 131, 400, sem_tinta=True),
    ]
    linhas = ler_paginas(montar_pdf(tmp_path / "livro.pdf", [mista]))[0].linhas
    assert [(linha.texto, linha.nao_pintada) for linha in linhas] == [("Legenda da figura", False)]


def test_importar_pdf_tira_a_camada_do_ocr_e_o_resumo_a_conta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf = montar_pdf(tmp_path / "livro.pdf", [_pagina_com_figura()])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub")
    assert [(r.motivo, r.texto) for r in importacao.remocoes] == [
        (MOTIVO_DA_CAMADA_DO_OCR, "o o o"),
        (MOTIVO_DA_CAMADA_DO_OCR, "l"),
    ]
    assert "o o o" not in " ".join(bloco.texto for bloco in importacao.livro.blocos)
    assert principal(["importar-pdf", str(pdf), "--epub", str(tmp_path / "outro.epub")]) == 0
    assert f"  {MOTIVO_DA_CAMADA_DO_OCR}: 2" in capsys.readouterr().out


def test_pdf_escaneado_com_ocr_embutido_continua_entrando(tmp_path: Path) -> None:
    escaneado = [
        LinhaDeTeste(f"Texto da página escaneada, na linha {k} do livro.", 72, y, sem_tinta=True)
        for k, y in enumerate(range(700, 560, -14))
    ]
    importacao = importar_pdf(montar_pdf(tmp_path / "livro.pdf", [escaneado]), tmp_path / "l.epub")
    assert importacao.remocoes == ()
    assert "Texto da página escaneada, na linha 0 do livro." in " ".join(
        bloco.texto for bloco in importacao.livro.blocos
    )
