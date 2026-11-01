# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

import pytest

from ai_book.adaptadores.xhtml import CapituloSegmentado, XhtmlInvalidoError, segmentar_xhtml
from ai_book.dominio.segmento import Papel
from tests.livro_de_teste import DOCTYPE_XHTML11, xhtml

CAMINHO = "OEBPS/cap1.xhtml"


def _segmentar(corpo: str, doctype: str = "") -> CapituloSegmentado:
    return segmentar_xhtml(xhtml(corpo, doctype), "c001", CAMINHO)


def _textos(corpo: str, doctype: str = "") -> list[str]:
    return [s.texto for s in _segmentar(corpo, doctype).segmentos]


def test_entidade_html_com_doctype_xhtml11_vira_caractere() -> None:
    # A1 da auditoria: saía "Mr.Smith dont caf", sem nenhum aviso.
    corpo = "<p>Mr.&nbsp;Smith don&rsquo;t caf&eacute;</p>"
    assert _textos(corpo, DOCTYPE_XHTML11) == ["Mr. Smith don\N{RIGHT SINGLE QUOTATION MARK}t café"]


def test_entidade_html_sem_doctype_vira_caractere() -> None:
    # Sem DOCTYPE, o &eacute; derrubava o livro inteiro com "Entity not defined".
    assert _textos("<p>caf&eacute; &amp; cr&egrave;me</p>") == ["café & crème"]


def test_entidade_interna_do_doctype_e_resolvida() -> None:
    doctype = '<!DOCTYPE html [<!ENTITY autor "Asimov">]>'
    assert _textos("<p>By &autor;.</p>", doctype) == ["By Asimov."]


def test_entidade_externa_nao_le_arquivo_local(tmp_path: Path) -> None:
    # A5 da auditoria: a proteção contra XXE existia, mas nenhum teste a cobria.
    segredo = tmp_path / "segredo.txt"
    _ = segredo.write_text("SEGREDO")
    doctype = f'<!DOCTYPE html [<!ENTITY xxe SYSTEM "file://{segredo}">]>'
    with pytest.raises(XhtmlInvalidoError, match="xxe"):
        _ = _segmentar("<p>Leak: &xxe;</p>", doctype)


def test_entidade_desconhecida_recusa_o_capitulo_com_o_nome() -> None:
    # Sem valor conhecido, a entidade sumiria do áudio: melhor parar e dizer qual é.
    with pytest.raises(XhtmlInvalidoError, match="naoexiste"):
        _ = _segmentar("<p>Odd &naoexiste; here.</p>", DOCTYPE_XHTML11)


def test_paragrafo_dentro_de_citacao_vira_um_segmento_so() -> None:
    # A referência extraía <blockquote> e o <p> de dentro: o TTS lia duas vezes.
    assert _textos("<blockquote><p>A quoted line.</p></blockquote>") == ["A quoted line."]


def test_paragrafo_dentro_de_item_de_lista_vira_um_segmento_so() -> None:
    assert _textos("<ul><li><p>One item.</p></li></ul>") == ["One item."]


def test_texto_solto_em_div_vira_segmento() -> None:
    assert _textos("<div>Loose text in a div.</div>") == ["Loose text in a div."]


def test_chamada_de_nota_com_epub_type_sai_do_texto() -> None:
    corpo = '<p>He said it.<sup><a epub:type="noteref" href="#fn1">1</a></sup> Then left.</p>'
    assert _textos(corpo) == ["He said it. Then left."]


def test_chamada_de_nota_so_com_link_e_sup_sai_do_texto() -> None:
    corpo = '<p>Twice<a href="notes.xhtml#n2"><sup>[2]</sup></a> over.</p>'
    assert _textos(corpo) == ["Twice over."]


def test_numero_sobrescrito_sem_link_fica_no_texto() -> None:
    # Sem link, não dá para distinguir nota de expoente ("10<sup>6</sup>").
    assert _textos("<p>About 10<sup>6</sup> stars.</p>") == ["About 106 stars."]


def test_chamada_de_nota_fica_registrada_com_caminho_resolvido() -> None:
    corpo = (
        '<p>A<a epub:type="noteref" href="#fn1">1</a> and'
        ' B<a href="notes.xhtml#n2"><sup>2</sup></a>.</p>'
    )
    notas = [s.notas for s in _segmentar(corpo).segmentos]
    assert notas == [("OEBPS/cap1.xhtml#fn1", "OEBPS/notes.xhtml#n2")]


def test_corpo_da_nota_marcada_vira_segmento_de_papel_nota() -> None:
    corpo = '<p>Text.</p><aside epub:type="footnote" id="fn1"><p>The note body.</p></aside>'
    papeis = [(s.texto, s.papel) for s in _segmentar(corpo).segmentos]
    assert papeis == [("Text.", Papel.PARAGRAFO), ("The note body.", Papel.NOTA)]


def test_alvo_de_chamada_no_mesmo_arquivo_vira_segmento_de_papel_nota() -> None:
    corpo = '<p>Text<a href="#n9"><sup>9</sup></a>.</p><div id="n9"><p>Plain note.</p></div>'
    papeis = [s.papel for s in _segmentar(corpo).segmentos]
    assert papeis == [Papel.PARAGRAFO, Papel.NOTA]


def test_titulo_tem_papel_titulo() -> None:
    assert [s.papel for s in _segmentar("<h2>Chapter One</h2>").segmentos] == [Papel.TITULO]


def test_quebra_de_linha_vira_espaco() -> None:
    assert _textos("<p>Line one<br/>line two</p>") == ["Line one line two"]


def test_italico_no_meio_da_frase_nao_perde_espaco() -> None:
    assert _textos("<p>A <em>very</em> long\n   night.</p>") == ["A very long night."]


def test_bloco_vazio_nao_vira_segmento() -> None:
    assert _textos("<p>   </p><p>Real.</p><div><img src='x.png'/></div>") == ["Real."]


def test_ids_seguem_a_ordem_do_documento() -> None:
    ids = [s.id for s in _segmentar("<h1>T</h1><p>A</p><p>B</p>").segmentos]
    assert ids == ["c001-s0001", "c001-s0002", "c001-s0003"]


def test_xhtml_marcado_traz_o_id_no_elemento_do_segmento() -> None:
    marcado = _segmentar("<blockquote><p>Quoted.</p></blockquote>").xhtml_marcado
    assert b'<p data-ai-book="c001-s0001">Quoted.</p>' in marcado
    assert b"<blockquote>" in marcado


def test_todo_texto_do_corpo_cabe_em_algum_segmento() -> None:
    corpo = "<h1>T</h1><blockquote><p>Q</p></blockquote><div>D</div><p>P<br/>Q</p>"
    resultado = _segmentar(corpo)
    assert [s.texto for s in resultado.segmentos] == ["T", "Q", "D", "P Q"]
    assert resultado.texto_fora_de_segmento == []


def test_texto_misturado_com_paragrafos_e_relatado_em_vez_de_perdido() -> None:
    resultado = _segmentar("<div>Stray words<p>Inside.</p>more stray</div>")
    assert resultado.texto_fora_de_segmento == ["Stray words", "more stray"]
