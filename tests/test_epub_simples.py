# SPDX-License-Identifier: GPL-3.0-or-later
"""Contrato do gravador de EPUB: o `preparar` é quem diz se o EPUB gravado serve."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import override

import pytest
from lxml import etree

from earbook.adaptadores.epub_simples import gravar_epub
from earbook.adaptadores.xml_seguro import PARSER_SEGURO
from earbook.comandos.preparar import Preparo, preparar
from earbook.dominio.blocos import Bloco, TipoDeBloco


def _bloco(tipo: TipoDeBloco, texto: str, nivel: int = 0) -> Bloco:
    return Bloco(tipo, texto, pagina=1, tamanho=10.5, nivel=nivel)


def _papeis_e_textos(preparo: Preparo) -> list[list[tuple[str, str]]]:
    return [[(str(s.papel), s.texto) for s in c.segmentos] for c in preparo.limpeza.capitulos]


def test_epub_gravado_passa_pelo_preparar_com_papel_e_texto(tmp_path: Path) -> None:
    capitulos = [
        [
            _bloco(TipoDeBloco.TITULO, "Prefácio", nivel=2),
            _bloco(TipoDeBloco.PARAGRAFO, "Abertura."),
        ],
        [
            _bloco(TipoDeBloco.TITULO, "1", nivel=1),
            _bloco(TipoDeBloco.PARAGRAFO, "Texto do capítulo."),
            _bloco(TipoDeBloco.CODIGO, "def f():\n    return 1"),
            _bloco(TipoDeBloco.NOTA, "1 Uma nota."),
        ],
    ]
    epub = tmp_path / "livro.epub"
    gravar_epub(epub, "Livro de Teste", "pt-BR", capitulos)
    preparo = preparar(epub, tmp_path / "trabalho")
    livro = preparo.livro
    assert (livro.titulo, livro.idioma, len(livro.capitulos)) == ("Livro de Teste", "pt-BR", 2)
    assert _papeis_e_textos(preparo) == [
        [("titulo", "Prefácio"), ("paragrafo", "Abertura.")],
        [
            ("titulo", "1"),
            ("paragrafo", "Texto do capítulo."),
            ("paragrafo", "def f(): return 1"),
            ("nota", "1 Uma nota."),
        ],
    ]


def test_texto_com_sinais_do_xml_e_controle_chega_inteiro(tmp_path: Path) -> None:
    # O texto do PDF é livre: "<", "&" e caractere de controle não podem quebrar o XHTML.
    capitulos = [[_bloco(TipoDeBloco.PARAGRAFO, "Se a < b & c > d,\x0c então\x00 ok.")]]
    epub = tmp_path / "livro.epub"
    gravar_epub(epub, "T & U", "en", capitulos)
    preparo = preparar(epub, tmp_path / "trabalho")
    assert _papeis_e_textos(preparo) == [[("paragrafo", "Se a < b & c > d, então ok.")]]


def test_nao_sobrescreve_epub_que_ja_existe(tmp_path: Path) -> None:
    epub = tmp_path / "livro.epub"
    _ = epub.write_bytes(b"antigo")
    with pytest.raises(FileExistsError, match=r"livro\.epub"):
        gravar_epub(epub, "T", "en", [[_bloco(TipoDeBloco.PARAGRAFO, "Novo.")]])
    assert epub.read_bytes() == b"antigo"


def test_falha_no_meio_apaga_o_epub_parcial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def disco_cheio(*_args: object, **_opcoes: object) -> None:
        raise OSError(28, "disco cheio")

    monkeypatch.setattr(zipfile.ZipFile, "writestr", disco_cheio)
    epub = tmp_path / "livro.epub"
    with pytest.raises(OSError, match="disco cheio"):
        gravar_epub(epub, "T", "en", [[_bloco(TipoDeBloco.PARAGRAFO, "Texto.")]])
    assert not epub.exists()


def test_mimetype_vem_primeiro_e_sem_compressao(tmp_path: Path) -> None:
    # Leitor de EPUB reconhece o formato pelos primeiros bytes do zip (OCF 3, seção 4.3).
    epub = tmp_path / "livro.epub"
    gravar_epub(epub, "T", "en", [[_bloco(TipoDeBloco.PARAGRAFO, "Texto.")]])
    with zipfile.ZipFile(epub) as zip_:
        primeiro = zip_.infolist()[0]
        conteudo = zip_.read(primeiro)
    assert (primeiro.filename, primeiro.compress_type) == ("mimetype", zipfile.ZIP_STORED)
    assert conteudo == b"application/epub+zip"


def test_nivel_do_titulo_vira_o_numero_do_h(tmp_path: Path) -> None:
    capitulos = [
        [
            _bloco(TipoDeBloco.TITULO, "Parte", nivel=1),
            _bloco(TipoDeBloco.TITULO, "Seção", nivel=3),
            _bloco(TipoDeBloco.TITULO, "Sem nível"),
        ]
    ]
    epub = tmp_path / "livro.epub"
    gravar_epub(epub, "T", "en", capitulos)
    with zipfile.ZipFile(epub) as zip_:
        xhtml = zip_.read("OEBPS/c001.xhtml").decode()
    assert "<h1>Parte</h1>\n<h3>Seção</h3>\n<h1>Sem nível</h1>" in xhtml


class _FechaSemEspaco(io.FileIO):
    """O último flush, no `close`, é onde o disco cheio aparece quando o buffer guarda o fim."""

    @override
    def close(self) -> None:
        super().close()
        raise OSError(28, "disco cheio no close")


def test_falha_ao_fechar_o_arquivo_apaga_o_epub_parcial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Revisão nº 3: o `close` do arquivo ficava fora do `try`, e o EPUB truncado ficava.
    def abrir(caminho: Path, *_args: object, **_opcoes: object) -> io.FileIO:
        return _FechaSemEspaco(caminho, "x")

    monkeypatch.setattr(Path, "open", abrir)
    epub = tmp_path / "livro.epub"
    with pytest.raises(OSError, match="disco cheio no close"):
        gravar_epub(epub, "T", "en", [[_bloco(TipoDeBloco.PARAGRAFO, "Texto.")]])
    assert not epub.exists()


def test_sumario_tem_o_primeiro_titulo_ou_a_posicao_e_aponta_cada_capitulo(
    tmp_path: Path,
) -> None:
    # A4 da auditoria (M10c-e): o `preparar` não lê o nav, então o contrato não o cobria.
    capitulos = [
        [_bloco(TipoDeBloco.TITULO, "A & <B>\x0c", nivel=1)],
        [_bloco(TipoDeBloco.PARAGRAFO, "Sem título.")],
    ]
    epub = tmp_path / "livro.epub"
    gravar_epub(epub, "T", 'en"x', capitulos)
    with zipfile.ZipFile(epub) as zip_:
        nav = etree.fromstring(zip_.read("OEBPS/nav.xhtml"), PARSER_SEGURO)
    links = [(a.get("href"), "".join(a.itertext())) for a in nav.iter("{*}a")]
    assert links == [("c001.xhtml", "A & <B>"), ("c002.xhtml", "2")]
    assert nav.get("lang") == 'en"x'


def test_autor_entra_no_epub_e_o_preparar_le(tmp_path: Path) -> None:
    epub = tmp_path / "livro.epub"
    gravar_epub(
        epub, "T", "pt-BR", [[_bloco(TipoDeBloco.PARAGRAFO, "Texto.")]], autor="Fulana & Cia"
    )
    livro = preparar(epub, tmp_path / "trabalho").livro
    assert (livro.titulo, livro.autor) == ("T", "Fulana & Cia")


def test_sem_autor_o_epub_sai_sem_creator(tmp_path: Path) -> None:
    epub = tmp_path / "livro.epub"
    gravar_epub(epub, "T", "pt-BR", [[_bloco(TipoDeBloco.PARAGRAFO, "Texto.")]])
    with zipfile.ZipFile(epub) as zip_:
        assert b"dc:creator" not in zip_.read("OEBPS/content.opf")
