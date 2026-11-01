# SPDX-License-Identifier: GPL-3.0-or-later
"""O `montar` troca o texto de cada elemento marcado pelo texto final (ADR-0005)."""

from __future__ import annotations

from lxml import etree

from earbook.adaptadores.xhtml import XHTML, ids_marcados, montar_xhtml
from earbook.adaptadores.xml_seguro import PARSER_SEGURO
from tests.livro_de_teste import xhtml


def _blocos(saida: bytes) -> list[tuple[str, str]]:
    corpo = etree.fromstring(saida, PARSER_SEGURO).find(f"{{{XHTML}}}body")
    assert corpo is not None
    return [
        (etree.QName(elemento).localname, "".join(elemento.itertext()))
        for elemento in corpo.iter()
        if elemento is not corpo
    ]


def test_mantido_ganha_o_texto_final_e_removido_ou_juntado_sai() -> None:
    corpo = (
        '<h1 data-earbook="c001-s0001">Um</h1>'
        '<p data-earbook="c001-s0002">Texto <em>com</em> nota<a href="#n1">1</a>.</p>'
        '<p data-earbook="c001-s0003">Tides of Darkness 2</p>'
        '<p data-earbook="c001-s0004">partido.</p>'
    )
    textos = {"c001-s0001": "Um", "c001-s0002": "Texto com nota. partido."}
    saida = montar_xhtml(xhtml(corpo), textos, set(), "OEBPS/a.xhtml")
    assert _blocos(saida) == [("h1", "Um"), ("p", "Texto com nota. partido.")]
    assert b"data-earbook" not in saida


def test_nota_vai_para_o_fim_do_capitulo_sob_notas() -> None:
    corpo = (
        '<p data-earbook="c001-s0001">Texto.</p>'
        '<aside epub:type="footnote"><p data-earbook="c001-s0002">1 A nota.</p></aside>'
        '<p data-earbook="c001-s0003">Mais texto.</p>'
    )
    textos = {"c001-s0001": "Texto.", "c001-s0002": "1 A nota.", "c001-s0003": "Mais texto."}
    saida = montar_xhtml(xhtml(corpo), textos, {"c001-s0002"}, "OEBPS/a.xhtml")
    assert _blocos(saida) == [
        ("p", "Texto."),
        ("p", "Mais texto."),
        ("h2", "Notas"),
        ("p", "1 A nota."),
    ]


def test_texto_solto_depois_do_elemento_tirado_fica() -> None:
    corpo = '<div>Antes<p data-earbook="c001-s0001">tirado</p> depois</div>'
    saida = montar_xhtml(xhtml(corpo), {}, set(), "OEBPS/a.xhtml")
    assert _blocos(saida) == [("div", "Antes depois")]


def test_doctype_do_original_fica() -> None:
    entrada = xhtml('<p data-earbook="c001-s0001">Texto.</p>', doctype="<!DOCTYPE html>")
    saida = montar_xhtml(entrada, {"c001-s0001": "Texto."}, set(), "OEBPS/a.xhtml")
    assert saida.startswith(b"<?xml")
    assert b"<!DOCTYPE html>" in saida


def _ids(saida: bytes) -> list[str]:
    raiz = etree.fromstring(saida, PARSER_SEGURO)
    return [i for e in raiz.iter() if (i := e.get("id")) is not None]


def test_ancoras_de_dentro_do_mantido_e_do_tirado_continuam_no_capitulo() -> None:
    # Revisão: o sumário do Calibre aponta para `cap.xhtml#calibre_toc_3`, dentro do título;
    # trocar o texto ou tirar o elemento levava a âncora, e o ElevenReader perdia o destino.
    corpo = (
        '<h1 data-earbook="c001-s0001"><a id="calibre_toc_3"></a>Um</h1>'
        '<p data-earbook="c001-s0002" id="p2">Texto<em><a id="ftn.1" href="#n1">1</a></em>.</p>'
        '<p data-earbook="c001-s0003"><a id="pagina_12"></a>Livro 12</p>'
        '<aside id="n1" epub:type="footnote"><p data-earbook="c001-s0004">1 Nota.</p></aside>'
    )
    textos = {"c001-s0001": "Um", "c001-s0002": "Texto.", "c001-s0004": "1 Nota."}
    saida = montar_xhtml(xhtml(corpo), textos, {"c001-s0004"}, "OEBPS/a.xhtml")
    assert sorted(_ids(saida)) == ["calibre_toc_3", "ftn.1", "n1", "p2", "pagina_12"]
    assert _blocos(saida)[:2] == [("h1", "Um"), ("a", "")]  # a âncora vem antes do texto
    assert "".join(etree.fromstring(saida, PARSER_SEGURO).itertext()).count("Um") == 1


def _pais_das_ancoras(saida: bytes) -> list[str]:
    raiz = etree.fromstring(saida, PARSER_SEGURO)
    return [
        etree.QName(pai).localname
        for ancora in raiz.iter(f"{{{XHTML}}}a")
        if (pai := ancora.getparent()) is not None and ancora.get("href") is None
    ]


def test_ancora_do_tirado_vai_para_o_proximo_bloco_mantido() -> None:
    # A4 da auditoria: `<a id>` direto no `<ul>` (ou no `<body>` do EPUB2) é XHTML inválido.
    corpo = (
        '<ul><li id="i1" data-earbook="c001-s0001">Livro 12</li>'
        '<li data-earbook="c001-s0002">Item.</li></ul>'
    )
    saida = montar_xhtml(xhtml(corpo), {"c001-s0002": "Item."}, set(), "OEBPS/a.xhtml")
    assert _ids(saida) == ["i1"]
    assert _pais_das_ancoras(saida) == ["li"]
    assert _blocos(saida) == [("ul", "Item."), ("li", "Item."), ("a", "")]


def test_ancora_sem_bloco_mantido_no_capitulo_fica_num_div() -> None:
    saida = montar_xhtml(xhtml('<p id="x" data-earbook="c001-s0001">T 2</p>'), {}, set(), "a.xhtml")
    assert (_ids(saida), _pais_das_ancoras(saida)) == (["x"], ["div"])


def test_sumario_nav_fica_com_os_links() -> None:
    # A1 da auditoria: o item do sumário EPUB3 é segmento, e trocar o texto tirava o `<a>`;
    # o epubcheck acusava `li` sem link, e o leitor perdia o sumário.
    corpo = (
        '<nav epub:type="toc"><ol>'
        '<li data-earbook="c001-s0001"><a href="a.xhtml">Um</a></li>'
        '<li data-earbook="c001-s0002"><a href="b.xhtml">Dois</a></li>'
        "</ol></nav>"
    )
    textos = {"c001-s0001": "Um", "c001-s0002": "Dois"}
    saida = montar_xhtml(xhtml(corpo), textos, set(), "OEBPS/nav.xhtml")
    raiz = etree.fromstring(saida, PARSER_SEGURO)
    links = [(a.get("href"), a.text) for a in raiz.iter(f"{{{XHTML}}}a")]
    assert links == [("a.xhtml", "Um"), ("b.xhtml", "Dois")]


def test_marca_repetida_aparece_duas_vezes() -> None:
    # Sem a repetição, o conferir não veria a marca duplicada.
    corpo = '<p data-earbook="c001-s0001">A</p><p data-earbook="c001-s0001">B</p>'
    assert ids_marcados(xhtml(corpo), "a.xhtml") == ("c001-s0001", "c001-s0001")


def test_ancora_do_tirado_depois_do_ultimo_bloco_vai_para_o_fim_dele() -> None:
    corpo = '<p data-earbook="c001-s0001">A</p><p id="x" data-earbook="c001-s0002">T 2</p>'
    saida = montar_xhtml(xhtml(corpo), {"c001-s0001": "A"}, set(), "a.xhtml")
    assert (_blocos(saida), _pais_das_ancoras(saida)) == ([("p", "A"), ("a", "")], ["p"])


def _links(saida: bytes) -> list[tuple[str | None, str | None]]:
    raiz = etree.fromstring(saida, PARSER_SEGURO)
    return [(a.get("href"), a.text) for a in raiz.iter(f"{{{XHTML}}}a") if a.get("href")]


SUMARIO = (
    '<nav epub:type="toc"><ol>'
    '<li data-earbook="c001-s0002"><a href="a.xhtml">Epigraph</a></li>'
    '<li data-earbook="c001-s0003"><a href="b.xhtml">The Doors</a></li>'
    "</ol></nav>"
)


def test_item_do_sumario_recebe_o_texto_final_no_link() -> None:
    # N1 da pós-auditoria: o item ficava com o texto original; no livro traduzido, o
    # sumário sairia em inglês, a leitura bilíngue que o projeto proíbe.
    textos = {"c001-s0002": "Epígrafe", "c001-s0003": "As Portas"}
    saida = montar_xhtml(xhtml(SUMARIO), textos, set(), "OEBPS/toc.xhtml")
    assert _links(saida) == [("a.xhtml", "Epígrafe"), ("b.xhtml", "As Portas")]


def test_item_do_sumario_tirado_pela_limpeza_continua_no_sumario() -> None:
    # N2 da pós-auditoria: tirar os itens esvaziava o `<nav>`, que saía inteiro, e o livro
    # perdia a navegação no leitor.
    saida = montar_xhtml(xhtml(SUMARIO), {}, set(), "OEBPS/toc.xhtml")
    assert _links(saida) == [("a.xhtml", "Epigraph"), ("b.xhtml", "The Doors")]


def test_ancora_tirada_antes_do_sumario_nao_entra_no_item() -> None:
    # N3 da pós-auditoria: `<a id>` dentro do `<li>` do sumário é XHTML inválido, e o
    # epubcheck acusa âncora sem texto no `<nav>`.
    corpo = (
        '<p id="t" data-earbook="c001-s0001">Sumário</p>'
        + SUMARIO
        + '<p data-earbook="c001-s0004">Texto.</p>'
    )
    textos = {"c001-s0002": "Epigraph", "c001-s0003": "The Doors", "c001-s0004": "Texto."}
    saida = montar_xhtml(xhtml(corpo), textos, set(), "OEBPS/toc.xhtml")
    assert (_ids(saida), _pais_das_ancoras(saida)) == (["t"], ["p"])


def test_ancora_do_tirado_vem_antes_do_texto_do_proximo_bloco() -> None:
    # N4 da pós-auditoria: no fim do bloco, o salto do sumário pularia o parágrafo inteiro.
    corpo = '<p id="x" data-earbook="c001-s0001">T 2</p><p data-earbook="c001-s0002">Texto.</p>'
    saida = montar_xhtml(xhtml(corpo), {"c001-s0002": "Texto."}, set(), "a.xhtml")
    paragrafo = etree.fromstring(saida, PARSER_SEGURO).find(f".//{{{XHTML}}}p")
    assert paragrafo is not None
    assert (paragrafo.text, paragrafo[0].get("id"), paragrafo[0].tail) == (None, "x", "Texto.")
