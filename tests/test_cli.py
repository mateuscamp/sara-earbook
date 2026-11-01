# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

import pytest

from ai_book.comandos.cli import principal
from tests.livro_de_teste import montar_epub


def test_preparar_cria_a_pasta_ao_lado_do_epub_e_resume(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    epub = montar_epub(
        tmp_path / "livro.epub",
        {"a.xhtml": "<p>A</p><p>B</p>", "b.xhtml": "<div>Stray<p>C</p></div>"},
    )
    assert principal(["preparar", str(epub)]) == 0
    assert (tmp_path / "livro.ai-book" / "livro.json").is_file()
    saida = capsys.readouterr().out
    assert "2 capítulos, 3 segmentos" in saida
    assert "1 trecho fora de segmento" in saida
    assert "c002: Stray" in saida


def test_preparar_mostra_os_itens_do_spine_ignorados(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # A4 da auditoria: capítulo que o preparar não lê tem de aparecer para quem vai ouvir.
    epub = montar_epub(
        tmp_path / "livro.epub", {"a.xhtml": "<p>A</p>"}, ordem_no_spine=["a.xhtml", "fantasma"]
    )
    assert principal(["preparar", str(epub)]) == 0
    saida = capsys.readouterr().out
    assert "1 item do spine ignorado" in saida
    assert "  fantasma: idref sem item no manifesto" in saida


def test_preparar_aceita_outra_pasta(tmp_path: Path) -> None:
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": "<p>A</p>"})
    assert principal(["preparar", str(epub), "--pasta", str(tmp_path / "outra")]) == 0
    assert (tmp_path / "outra" / "livro.json").is_file()


def test_preparar_com_erro_mostra_a_causa_e_sai_com_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert principal(["preparar", str(tmp_path / "nao-existe.epub")]) == 1
    assert "nao-existe.epub" in capsys.readouterr().err
