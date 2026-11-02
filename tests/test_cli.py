# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

import pytest

from earbook.comandos.cli import principal
from tests.livro_de_teste import montar_epub


def test_preparar_cria_a_pasta_ao_lado_do_epub_e_resume(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    epub = montar_epub(
        tmp_path / "livro.epub",
        {"a.xhtml": "<p>A</p><p>B</p>", "b.xhtml": "<div>Stray<p>C</p></div>"},
    )
    assert principal(["preparar", str(epub)]) == 0
    assert (tmp_path / "livro.earbook" / "livro.json").is_file()
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


def test_preparar_resume_a_limpeza_agrupada_por_motivo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # No Tides of Darkness são 258 remoções: o resumo agrupa, e o detalhe fica no registro.
    corpo = "".join(f"<p>Livro de Teste {n}</p><p>A</p><p>Dia {n}</p>" for n in (2, 4, 6))
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": corpo})
    assert principal(["preparar", str(epub)]) == 0
    saida = capsys.readouterr().out
    assert "3 segmentos removidos na limpeza" in saida
    assert "  cabeçalho de página 'Livro de Teste': 3" in saida
    assert "limpeza.json" in saida
    assert "3 segmentos suspeitos ficaram no texto" in saida
    # Agrupadas por motivo: no Tides são 25 capitulares e 1 título, e o número diz o que fazer.
    assert "  possível cabeçalho de página 'Dia': não está no título nem no autor: 3" in saida


def test_preparar_conta_as_capitulares_devolvidas(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpo = "<h1>EIGHT</h1><p>re we ready?</p><p>A Lothar nodded. They are ready.</p>"
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": corpo})
    assert principal(["preparar", str(epub)]) == 0
    assert "1 capitular deslocada devolvida ao começo do capítulo." in capsys.readouterr().out


def test_preparar_conta_aparos_e_juncoes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    soltos = "".join(f"<p>Livro de Teste {n}</p>" for n in (2, 4, 6))
    corpo = f"<p>They peered, trying Livro de Teste 8</p><p>to pierce the fog.</p>{soltos}"
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": corpo})
    assert principal(["preparar", str(epub)]) == 0
    saida = capsys.readouterr().out
    assert "1 cabeçalho colado aparado do fim de parágrafo." in saida
    assert "1 parágrafo partido na quebra de página juntado." in saida


def test_preparar_aceita_outra_pasta(tmp_path: Path) -> None:
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": "<p>A</p>"})
    assert principal(["preparar", str(epub), "--pasta", str(tmp_path / "outra")]) == 0
    assert (tmp_path / "outra" / "livro.json").is_file()


def test_preparar_com_erro_mostra_a_causa_e_sai_com_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert principal(["preparar", str(tmp_path / "nao-existe.epub")]) == 1
    assert "nao-existe.epub" in capsys.readouterr().err
