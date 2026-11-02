# SPDX-License-Identifier: GPL-3.0-or-later
"""Monta EPUBs mínimos para os testes, em vez de guardar binário no repositório."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Adulteracao:
    """O que o EPUB de teste traz de estranho, para simular arquivo malicioso ou malformado.

    `hrefs` troca o href que o OPF declara para um arquivo; `caminho_do_opf` troca o
    `full-path` do container.xml (o OPF continua gravado em OEBPS/content.opf); `tipos`
    troca o media-type declarado no manifesto.
    """

    membros_extras: dict[str, bytes] = field(default_factory=dict[str, bytes])
    hrefs: dict[str, str] = field(default_factory=dict[str, str])
    caminho_do_opf: str = "OEBPS/content.opf"
    tipos: dict[str, str] = field(default_factory=dict[str, str])


def _container(caminho_do_opf: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        f'<rootfiles><rootfile full-path="{caminho_do_opf}"'
        ' media-type="application/oebps-package+xml"/></rootfiles></container>'
    ).encode()


DOCTYPE_XHTML11 = (
    '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"'
    ' "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">'
)


def xhtml(corpo: str, doctype: str = "") -> bytes:
    return (
        f'<?xml version="1.0" encoding="utf-8"?>\n{doctype}\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
        f"<head><title>t</title></head><body>{corpo}</body></html>"
    ).encode()


def opf(
    manifesto: str = "", spine: str = "", titulo: str = "Livro de Teste", idioma: str = "en"
) -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f'<dc:identifier id="id">teste</dc:identifier><dc:title>{titulo}</dc:title>'
        f"<dc:creator>Fulano</dc:creator><dc:language>{idioma}</dc:language></metadata>"
        f"<manifest>{manifesto}</manifest><spine>{spine}</spine></package>"
    ).encode()


def _opf_dos_capitulos(
    arquivos: list[str], ordem_no_spine: list[str], estranho: Adulteracao, idioma: str
) -> bytes:
    manifesto = "".join(
        (
            f'<item id="{nome}" href="{estranho.hrefs.get(nome, nome)}"'
            f' media-type="{estranho.tipos.get(nome, "application/xhtml+xml")}"/>'
        )
        for nome in arquivos
    )
    spine = "".join(f'<itemref idref="{nome}"/>' for nome in ordem_no_spine)
    return opf(manifesto, spine, idioma=idioma)


def montar_epub(
    destino: Path,
    capitulos: dict[str, str],
    ordem_no_spine: list[str] | None = None,
    adulteracao: Adulteracao | None = None,
    idioma: str = "en",
) -> Path:
    """`capitulos` mapeia nome do arquivo → corpo XHTML, na ordem do manifesto."""
    estranho = adulteracao or Adulteracao()
    arquivos = list(capitulos)
    with zipfile.ZipFile(destino, "w") as zip_:
        zip_.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zip_.writestr("META-INF/container.xml", _container(estranho.caminho_do_opf))
        zip_.writestr(
            "OEBPS/content.opf",
            _opf_dos_capitulos(arquivos, ordem_no_spine or arquivos, estranho, idioma),
        )
        for nome, corpo in capitulos.items():
            zip_.writestr(f"OEBPS/{nome}", xhtml(corpo))
        for nome, conteudo in estranho.membros_extras.items():
            zip_.writestr(nome, conteudo)
    return destino
