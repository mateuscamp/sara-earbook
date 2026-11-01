# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_book.adaptadores import pacote_epub
from ai_book.comandos.preparar import pasta_padrao, preparar
from ai_book.dominio.trabalho import ItemIgnorado
from tests.livro_de_teste import Adulteracao, montar_epub, opf, xhtml


def _ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def _json(conteudo: object) -> str:
    """O texto exato que a pasta de trabalho grava; comparar texto evita o `Any` do json.loads."""
    return json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n"


@pytest.fixture
def epub(tmp_path: Path) -> Path:
    # O spine inverte a ordem do manifesto: a ordem de leitura é a do spine.
    return montar_epub(
        tmp_path / "livro.epub",
        {"a.xhtml": "<p>A</p>", "b.xhtml": "<h1>B</h1><div>Stray<p>In.</p></div>"},
        ordem_no_spine=["b.xhtml", "a.xhtml"],
    )


def test_preparar_grava_um_arquivo_de_segmentos_por_capitulo_na_ordem_do_spine(
    epub: Path, tmp_path: Path
) -> None:
    pasta = tmp_path / "trabalho"
    _ = preparar(epub, pasta)
    c001: list[dict[str, object]] = [
        {"id": "c001-s0001", "papel": "titulo", "texto": "B", "notas": []},
        {"id": "c001-s0002", "papel": "paragrafo", "texto": "In.", "notas": []},
    ]
    c002: list[dict[str, object]] = [
        {"id": "c002-s0001", "papel": "paragrafo", "texto": "A", "notas": []},
    ]
    assert _ler(pasta / "segmentos" / "c001.json") == _json(c001)
    assert _ler(pasta / "segmentos" / "c002.json") == _json(c002)


def test_preparar_grava_metadados_capitulos_e_texto_fora_no_livro_json(
    epub: Path, tmp_path: Path
) -> None:
    pasta = tmp_path / "trabalho"
    _ = preparar(epub, pasta)
    assert _ler(pasta / "livro.json") == _json(
        {
            "origem": "livro.epub",
            "titulo": "Livro de Teste",
            "autor": "Fulano",
            "idioma": "en",
            "capitulos": [
                {"id": "c001", "arquivo": "OEBPS/b.xhtml", "segmentos": 2},
                {"id": "c002", "arquivo": "OEBPS/a.xhtml", "segmentos": 1},
            ],
            "texto_fora_de_segmento": [{"capitulo": "c001", "texto": "Stray"}],
            "itens_do_spine_ignorados": [],
        }
    )


def test_preparar_le_xhtml_repetido_no_spine_uma_vez_so_e_relata(tmp_path: Path) -> None:
    # A3 da auditoria: o texto saía duas vezes, e o primeiro ID ficava sem elemento no XHTML.
    # O itemref "a.xhtml" se repete, e o item "b.xhtml" do manifesto é um apelido de a.xhtml.
    epub = montar_epub(
        tmp_path / "livro.epub",
        {"a.xhtml": "<p>Only once.</p>", "b.xhtml": "<p>B</p>"},
        ordem_no_spine=["a.xhtml", "a.xhtml", "b.xhtml"],
        adulteracao=Adulteracao(hrefs={"b.xhtml": "x/../a.xhtml"}),
    )
    livro = preparar(epub, tmp_path / "trabalho")
    assert [c.arquivo for c in livro.capitulos] == ["OEBPS/a.xhtml"]
    assert livro.itens_do_spine_ignorados == (
        ItemIgnorado("a.xhtml", "repete OEBPS/a.xhtml"),
        ItemIgnorado("b.xhtml", "repete OEBPS/a.xhtml"),
    )


@pytest.mark.parametrize("tipo", ["application/xhtml+xml; charset=utf-8", "text/x-oeb1-document"])
def test_preparar_le_capitulo_com_variante_de_tipo_xhtml(tmp_path: Path, tipo: str) -> None:
    # A4 da auditoria: esses capítulos sumiam do livro sem aviso.
    epub = montar_epub(
        tmp_path / "livro.epub",
        {"a.xhtml": "<p>A</p>"},
        adulteracao=Adulteracao(tipos={"a.xhtml": tipo}),
    )
    livro = preparar(epub, tmp_path / "trabalho")
    assert [c.arquivo for c in livro.capitulos] == ["OEBPS/a.xhtml"]


def test_preparar_relata_item_do_spine_que_nao_le(tmp_path: Path) -> None:
    # A4 da auditoria: o livro saía com 1 capítulo de 4, e nada dizia que faltavam 3.
    epub = montar_epub(
        tmp_path / "livro.epub",
        {"a.xhtml": "<p>A</p>", "img.svg": "<p>x</p>"},
        ordem_no_spine=["a.xhtml", "img.svg", "fantasma"],
        adulteracao=Adulteracao(tipos={"img.svg": "image/svg+xml"}),
    )
    livro = preparar(epub, tmp_path / "trabalho")
    assert livro.itens_do_spine_ignorados == (
        ItemIgnorado("img.svg", "tipo image/svg+xml não é XHTML"),
        ItemIgnorado("fantasma", "idref sem item no manifesto"),
    )


def test_preparar_grava_copia_do_epub_com_o_xhtml_marcado(epub: Path, tmp_path: Path) -> None:
    pasta = tmp_path / "trabalho"
    _ = preparar(epub, pasta)
    assert (pasta / "epub" / "mimetype").read_text() == "application/epub+zip"
    marcado = (pasta / "epub" / "OEBPS" / "a.xhtml").read_text(encoding="utf-8")
    assert '<p data-ai-book="c002-s0001">A</p>' in marcado


def test_preparar_devolve_o_mesmo_resultado_em_duas_execucoes(epub: Path, tmp_path: Path) -> None:
    _ = preparar(epub, tmp_path / "um")
    _ = preparar(epub, tmp_path / "dois")
    for relativo in ("livro.json", "segmentos/c001.json", "epub/OEBPS/b.xhtml"):
        assert (tmp_path / "um" / relativo).read_bytes() == (
            tmp_path / "dois" / relativo
        ).read_bytes()


def test_preparar_recusa_pasta_de_trabalho_que_ja_existe(epub: Path, tmp_path: Path) -> None:
    # Refazer o preparo apagaria a tradução já feita (driver de retomabilidade).
    pasta = tmp_path / "trabalho"
    pasta.mkdir()
    _ = (pasta / "traducao.json").write_text("{}")
    with pytest.raises(FileExistsError, match="trabalho"):
        _ = preparar(epub, pasta)
    assert (pasta / "traducao.json").read_text() == "{}"


def test_preparar_recusa_epub_com_membro_que_escapa_da_pasta(tmp_path: Path) -> None:
    epub = montar_epub(
        tmp_path / "mau.epub",
        {"a.xhtml": "<p>A</p>"},
        adulteracao=Adulteracao(membros_extras={"../../fora.txt": b"x"}),
    )
    pasta = tmp_path / "sub" / "trabalho"
    with pytest.raises(ValueError, match=r"fora\.txt"):
        _ = preparar(epub, pasta)
    assert not (tmp_path / "fora.txt").exists()
    assert not pasta.exists()


@pytest.mark.parametrize("forma", ["relativo", "absoluto"])
def test_preparar_recusa_spine_que_aponta_para_fora_do_epub(tmp_path: Path, forma: str) -> None:
    # Sem a recusa, o preparar lia e REGRAVAVA (marcado) um XHTML fora da pasta.
    alvo = tmp_path / "alvo.xhtml"
    original = xhtml("<p>Fora.</p>")
    _ = alvo.write_bytes(original)
    # OEBPS/../../../alvo.xhtml, visto de trabalho/epub/, cai em tmp_path/alvo.xhtml.
    href = str(alvo) if forma == "absoluto" else "../../../alvo.xhtml"
    adulteracao = Adulteracao(hrefs={"a.xhtml": href})
    epub = montar_epub(tmp_path / "mau.epub", {"a.xhtml": "<p>A</p>"}, adulteracao=adulteracao)
    with pytest.raises(ValueError, match=r"alvo\.xhtml"):
        _ = preparar(epub, tmp_path / "trabalho")
    assert alvo.read_bytes() == original


@pytest.mark.parametrize("forma", ["relativo", "absoluto"])
def test_preparar_recusa_opf_que_esta_fora_do_epub(tmp_path: Path, forma: str) -> None:
    # A2 da auditoria: o título do livro vinha de um OPF plantado fora da pasta.
    fora = tmp_path / "fora.opf"
    _ = fora.write_bytes(opf(titulo="CANARIO"))
    # ../../fora.opf, visto de trabalho/epub/, cai em tmp_path/fora.opf.
    caminho = str(fora) if forma == "absoluto" else "../../fora.opf"
    adulteracao = Adulteracao(caminho_do_opf=caminho)
    epub = montar_epub(tmp_path / "mau.epub", {"a.xhtml": "<p>A</p>"}, adulteracao=adulteracao)
    with pytest.raises(ValueError, match=r"fora\.opf"):
        _ = preparar(epub, tmp_path / "trabalho")


def test_preparar_nao_le_arquivo_local_por_entidade_externa_no_opf(tmp_path: Path) -> None:
    # A5 da auditoria: a proteção contra XXE existia, mas nenhum teste a cobria.
    segredo = tmp_path / "segredo.txt"
    _ = segredo.write_text("SEGREDO")
    doctype = f'<!DOCTYPE package [<!ENTITY xxe SYSTEM "file://{segredo}">]>\n'
    opf_mau = opf(titulo="Livro &xxe;").replace(b"?>\n", b"?>\n" + doctype.encode(), 1)
    adulteracao = Adulteracao(
        caminho_do_opf="OEBPS/mau.opf", membros_extras={"OEBPS/mau.opf": opf_mau}
    )
    epub = montar_epub(tmp_path / "mau.epub", {"a.xhtml": "<p>A</p>"}, adulteracao=adulteracao)
    with pytest.raises(ValueError, match="xxe") as recusa:
        _ = preparar(epub, tmp_path / "trabalho")
    assert "SEGREDO" not in str(recusa.value)


def test_preparar_recusa_zip_que_descompacta_alem_do_limite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A5 da auditoria: a checagem existia sem teste. O limite real (2 GiB) cai para 1 KB aqui.
    monkeypatch.setattr(pacote_epub, "LIMITE_DESCOMPACTADO", 1024)
    epub = montar_epub(tmp_path / "grande.epub", {"a.xhtml": f"<p>{'A' * 4096}</p>"})
    pasta = tmp_path / "trabalho"
    with pytest.raises(ValueError, match="limite 1024"):
        _ = preparar(epub, pasta)
    assert not pasta.exists()


def test_pasta_padrao_fica_ao_lado_do_epub() -> None:
    assert pasta_padrao(Path("/livros/Duna.epub")) == Path("/livros/Duna.ai-book")
