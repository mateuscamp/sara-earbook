# SPDX-License-Identifier: GPL-3.0-or-later
"""O comando `importar-pdf` de ponta a ponta: PDF montado à mão → EPUB → `preparar`."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import override

import pytest

from earbook.comandos.cli import principal
from earbook.comandos.importar_pdf import PdfSemTextoError, epub_padrao, importar_pdf
from earbook.comandos.preparar import preparar
from earbook.dominio.blocos import TipoDeBloco
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf

ENTRELINHA = 16.6  # pontos: 0,021 de uma página de 792 pt, como no Competente


def _pagina(numero: int, *, titulo: str | None = None) -> list[LinhaDeTeste]:
    """Uma página com número no pé, título opcional e um parágrafo de quatro linhas."""
    linhas = [LinhaDeTeste(str(numero + 10), 300, 30, tamanho=7.5)]
    topo = 700.0
    if titulo is not None:
        linhas.append(LinhaDeTeste(titulo, 54, 720, tamanho=19))
        topo = 660.0
    linhas.append(LinhaDeTeste(f"Era uma vez a página {numero}, que", 67, topo))
    for n, texto in enumerate(
        ("seguia em várias linhas de corpo", "até o fim do seu", "parágrafo."), 1
    ):
        linhas.append(LinhaDeTeste(texto, 54, topo - n * ENTRELINHA))
    return linhas


TITULOS = {1: "Abertura", 2: "Capítulo 1", 4: "Capítulo 2", 6: "Capítulo 3"}


@pytest.fixture
def pdf(tmp_path: Path) -> Path:
    paginas = [_pagina(n, titulo=TITULOS.get(n)) for n in range(1, 8)]
    return montar_pdf(tmp_path / "livro.pdf", paginas)


def test_importar_pdf_grava_epub_que_o_preparar_le(pdf: Path, tmp_path: Path) -> None:
    importacao = importar_pdf(pdf, tmp_path / "livro.epub", idioma="pt-BR")
    assert importacao.paginas == 7
    assert [r.motivo for r in importacao.remocoes] == ["número de página"] * 7
    tipos = [b.tipo for b in importacao.livro.blocos]
    assert (tipos.count(TipoDeBloco.TITULO), tipos.count(TipoDeBloco.PARAGRAFO)) == (4, 7)
    # Os quatro títulos de 19 pt, em 3 páginas ou mais, abrem capítulo.
    assert importacao.capitulos == 4
    livro = preparar(importacao.epub, tmp_path / "trabalho").livro
    assert (len(livro.capitulos), livro.idioma) == (4, "pt-BR")


def test_paragrafo_do_pdf_chega_inteiro_ao_preparar(pdf: Path, tmp_path: Path) -> None:
    importacao = importar_pdf(pdf, tmp_path / "livro.epub")
    pasta = tmp_path / "trabalho"
    _ = preparar(importacao.epub, pasta)
    segmentos = (pasta / "segmentos" / "c001.json").read_text("utf-8")
    assert (
        "Era uma vez a página 1, que seguia em várias linhas de corpo até o fim do seu parágrafo."
        in segmentos
    )


def test_importar_pdf_recusa_epub_que_ja_existe_antes_de_ler_o_pdf(tmp_path: Path) -> None:
    # Um PDF de 500 páginas leva minutos: a recusa vem antes. Se o PDF fosse lido
    # primeiro, o erro seria de PDF inválido, não de arquivo existente.
    falso = tmp_path / "falso.pdf"
    _ = falso.write_bytes(b"isto nao e um pdf")
    epub = tmp_path / "livro.epub"
    _ = epub.write_bytes(b"antigo")
    with pytest.raises(FileExistsError, match=r"livro\.epub"):
        _ = importar_pdf(falso, epub)
    assert epub.read_bytes() == b"antigo"


def test_pdf_sem_texto_e_recusado_sem_gravar_epub(tmp_path: Path) -> None:
    # PDF escaneado não tem camada de texto, e o earbook não faz OCR (ADR-0004).
    vazio = montar_pdf(tmp_path / "escaneado.pdf", [[], []])
    epub = tmp_path / "escaneado.epub"
    with pytest.raises(PdfSemTextoError, match=r"escaneado\.pdf.*OCR"):
        _ = importar_pdf(vazio, epub)
    assert not epub.exists()


def test_epub_padrao_fica_ao_lado_do_pdf() -> None:
    assert epub_padrao(Path("/livros/Competente.pdf")) == Path("/livros/Competente.epub")


def test_cli_importar_pdf_grava_ao_lado_e_resume(
    pdf: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert principal(["importar-pdf", str(pdf), "--idioma", "pt-BR"]) == 0
    assert (tmp_path / "livro.epub").is_file()
    saida = capsys.readouterr().out
    assert "7 páginas, 4 capítulos" in saida
    assert "earbook preparar" in saida


def test_cli_importar_pdf_grava_onde_o_epub_pede(pdf: Path, tmp_path: Path) -> None:
    destino = tmp_path / "outro" / "nome.epub"
    destino.parent.mkdir()
    assert principal(["importar-pdf", str(pdf), "--epub", str(destino)]) == 0
    assert destino.is_file()
    assert not (tmp_path / "livro.epub").exists()


def test_cli_importar_pdf_invalido_mostra_a_causa_e_sai_com_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    falso = tmp_path / "falso.pdf"
    _ = falso.write_bytes(b"isto nao e um pdf")
    assert principal(["importar-pdf", str(falso)]) == 1
    assert "falso.pdf" in capsys.readouterr().err


class _SaidaFechada(io.StringIO):
    """O `| head` que fechou a ponta: escrever dá EPIPE."""

    @override
    def write(self, s: str, /) -> int:
        raise BrokenPipeError(32, "Broken pipe")


def test_cli_saida_fechada_nao_vira_falha_do_trabalho(
    pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Revisão xhigh: o print do resumo ficava dentro do try, e o EPUB gravado saía como
    # "earbook: [Errno 32] Broken pipe" com código 1, igual a uma importação que falhou. A
    # pós-revisão tirou também o traceback: quem fechou a ponta (`| head`) já leu o que quis.
    monkeypatch.setattr(sys, "stdout", _SaidaFechada())
    assert principal(["importar-pdf", str(pdf)]) == 0
    assert (tmp_path / "livro.epub").is_file()
    assert "earbook:" not in capsys.readouterr().err


def test_cli_cano_real_fechado_antes_do_resumo_sai_quieto(
    pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # B1 da pós-auditoria: num cano de verdade o print só enchia o buffer, e o EPIPE vinha
    # no flush do fim do processo, fora do try (`| true` dava código 120 e "Exception
    # ignored"). O StringIO do teste anterior não reproduz o buffer de bloco.
    leitura, escrita = os.pipe()
    os.close(leitura)
    saida = io.TextIOWrapper(io.BufferedWriter(io.FileIO(escrita, "w")))
    monkeypatch.setattr(sys, "stdout", saida)
    assert principal(["importar-pdf", str(pdf)]) == 0
    assert (tmp_path / "livro.epub").is_file()
    saida.flush()
    saida.close()
