# SPDX-License-Identifier: GPL-3.0-or-later
"""O `montar` empacota a pasta `epub/` com os XHTML trocados (ADR-0005)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from earbook.adaptadores.pacote_epub import EpubInvalidoError, empacotar_pasta


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    pasta = tmp_path / "epub"
    (pasta / "META-INF").mkdir(parents=True)
    (pasta / "OEBPS").mkdir()
    _ = (pasta / "mimetype").write_bytes(b"application/epub+zip")
    _ = (pasta / "META-INF" / "container.xml").write_bytes(b"<container/>")
    _ = (pasta / "OEBPS" / "a.xhtml").write_bytes(b"marcado")
    _ = (pasta / "OEBPS" / "capa.png").write_bytes(b"\x89PNG")
    return pasta


def test_pasta_vira_epub_com_o_xhtml_trocado_e_o_resto_igual(pasta: Path, tmp_path: Path) -> None:
    destino = tmp_path / "livro.pronto.epub"
    empacotar_pasta(pasta, destino, {"OEBPS/a.xhtml": b"montado"})
    with zipfile.ZipFile(destino) as zip_:
        primeiro = zip_.infolist()[0]
        conteudo = {nome: zip_.read(nome) for nome in zip_.namelist()}
    assert (primeiro.filename, primeiro.compress_type) == ("mimetype", zipfile.ZIP_STORED)
    assert conteudo == {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": b"<container/>",
        "OEBPS/a.xhtml": b"montado",
        "OEBPS/capa.png": b"\x89PNG",
    }


def test_nao_sobrescreve_o_destino(pasta: Path, tmp_path: Path) -> None:
    destino = tmp_path / "livro.pronto.epub"
    _ = destino.write_bytes(b"antigo")
    with pytest.raises(FileExistsError, match=r"livro\.pronto\.epub"):
        empacotar_pasta(pasta, destino, {})
    assert destino.read_bytes() == b"antigo"


def test_falha_no_meio_apaga_o_parcial(pasta: Path, tmp_path: Path) -> None:
    (pasta / "OEBPS" / "capa.png").chmod(0)
    destino = tmp_path / "livro.pronto.epub"
    try:
        with pytest.raises(PermissionError):
            empacotar_pasta(pasta, destino, {})
    finally:
        (pasta / "OEBPS" / "capa.png").chmod(0o644)
    assert not destino.exists()


def test_link_simbolico_na_pasta_e_recusado(pasta: Path, tmp_path: Path) -> None:
    # Revisão: a pasta de trabalho é editada pelo agente e pela tradução; um link para fora
    # (`~/.ssh/id_rsa`) iria para dentro do EPUB que sobe para o ElevenReader.
    segredo = tmp_path / "segredo.txt"
    _ = segredo.write_text("senha")
    (pasta / "OEBPS" / "x.xhtml").symlink_to(segredo)
    destino = tmp_path / "livro.pronto.epub"
    with pytest.raises(EpubInvalidoError, match=r"OEBPS/x\.xhtml"):
        empacotar_pasta(pasta, destino, {})
    assert not destino.exists()


def test_troca_sem_arquivo_correspondente_e_recusada(pasta: Path, tmp_path: Path) -> None:
    # A5 da auditoria: o capítulo de caminho diferente do da pasta saía cru, sem a troca,
    # e o montar dizia que tinha montado.
    destino = tmp_path / "livro.pronto.epub"
    with pytest.raises(EpubInvalidoError, match=r"OEBPS/nao-existe\.xhtml"):
        empacotar_pasta(pasta, destino, {"OEBPS/nao-existe.xhtml": b"montado"})
    assert not destino.exists()
