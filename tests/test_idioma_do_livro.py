# SPDX-License-Identifier: GPL-3.0-or-later
"""O livro traduzido declara pt-BR no OPF e nos XHTML (ADR-0006)."""

from __future__ import annotations

from pathlib import Path

from earbook.adaptadores.pacote_epub import opf_em_outro_idioma
from earbook.adaptadores.xhtml import montar_xhtml
from earbook.dominio.traducao import TrocaDeIdioma

TROCA = TrocaDeIdioma("en", "pt-BR")
CONTAINER = (
    '<?xml version="1.0"?><container version="1.0"'
    ' xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
    '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
    "</rootfiles></container>"
)
OPF = (
    '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
    '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
    "<dc:language>en</dc:language><dc:language>fr</dc:language>"
    '<meta property="dcterms:language">en-US</meta>'
    '<meta property="dcterms:title">en</meta>'
    "</metadata><manifest/><spine/></package>"
)


def test_opf_troca_dc_language_e_dcterms_language_do_original(tmp_path: Path) -> None:
    (tmp_path / "META-INF").mkdir()
    (tmp_path / "OEBPS").mkdir()
    _ = (tmp_path / "META-INF" / "container.xml").write_text(CONTAINER)
    _ = (tmp_path / "OEBPS" / "content.opf").write_text(OPF)
    caminho, conteudo = opf_em_outro_idioma(tmp_path, TROCA)
    assert caminho == "OEBPS/content.opf"
    texto = conteudo.decode()
    assert "<dc:language>pt-BR</dc:language><dc:language>fr</dc:language>" in texto
    assert '<meta property="dcterms:language">pt-BR</meta>' in texto
    # Só o meta de idioma: outro meta com o texto "en" não é idioma.
    assert '<meta property="dcterms:title">en</meta>' in texto


def test_xhtml_troca_lang_e_xml_lang_inclusive_na_raiz() -> None:
    # A raiz `<html>` é onde o EPUB real declara a língua (X4 da auditoria).
    conteudo = (
        b'<?xml version="1.0" encoding="utf-8"?>\n'
        b'<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">'
        b'<head><title>t</title></head><body><p data-earbook="c001-s0001" lang="en-GB">x</p>'
        b"</body></html>"
    )
    saida = montar_xhtml(conteudo, {"c001-s0001": "Texto."}, set(), "a.xhtml", TROCA).decode()
    assert '<html xmlns="http://www.w3.org/1999/xhtml" lang="pt-BR" xml:lang="pt-BR">' in saida
    assert '<p lang="pt-BR">Texto.</p>' in saida
