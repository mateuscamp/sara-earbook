# SPDX-License-Identifier: GPL-3.0-or-later
"""Grava os blocos montados do PDF num EPUB 3 simples, que segue para o `preparar` (ADR-0004).

Só o que o ouvido usa: título, parágrafo, código e nota, um XHTML por capítulo. Nada de
CSS nem de imagem, porque o EPUB não é para ler na tela.
"""

from __future__ import annotations

import re
import uuid
import zipfile
from collections.abc import Sequence
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import assert_never

from earbook.adaptadores.pacote_epub import CONTAINER, DC, OPF
from earbook.adaptadores.xhtml import OPS, XHTML
from earbook.dominio.blocos import Bloco, TipoDeBloco

# O XML 1.0 não aceita controle fora de tab e quebra de linha, nem surrogate solto. O texto
# vem de PDF, que carrega de tudo; sem a limpeza, o `preparar` recusaria o EPUB inteiro.
_FORA_DO_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")

_CONTAINER = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="{container}">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

_OPF = """<?xml version="1.0" encoding="utf-8"?>
<package version="3.0" unique-identifier="id" xmlns="{opf}">
  <metadata xmlns:dc="{dc}">
    <dc:identifier id="id">urn:uuid:{identificador}</dc:identifier>
    <dc:title>{titulo}</dc:title>
    <dc:language>{idioma}</dc:language>
    <meta property="dcterms:modified">{modificado}</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
{itens}
  </manifest>
  <spine>
{referencias}
  </spine>
</package>
"""

_XHTML = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="{xhtml}" xmlns:epub="{ops}" \
xml:lang="{idioma}" lang="{idioma}">
<head><title>{titulo}</title></head>
<body>
{corpo}
</body>
</html>
"""


def gravar_epub(
    destino: Path, titulo: str, idioma: str, capitulos: Sequence[Sequence[Bloco]]
) -> None:
    """Grava `capitulos` em `destino`, que não pode existir ainda.

    Se algo falhar no meio, apaga o arquivo que acabou de criar: EPUB pela metade
    pareceria um livro e faria o próximo `importar-pdf` recusar sem motivo.
    """
    arquivo = destino.open("xb")
    # O `close` fica dentro do `try`: o último flush é onde o disco cheio aparece (revisão nº 3).
    try:
        with arquivo, zipfile.ZipFile(arquivo, "w", zipfile.ZIP_DEFLATED) as zip_:
            _gravar(zip_, _limpo(titulo), _limpo(idioma), capitulos)
    except BaseException:
        destino.unlink()
        raise


def _gravar(
    zip_: zipfile.ZipFile, titulo: str, idioma: str, capitulos: Sequence[Sequence[Bloco]]
) -> None:
    # O mimetype vem primeiro e sem compressão: é assim que o leitor reconhece o EPUB.
    zip_.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
    zip_.writestr("META-INF/container.xml", _CONTAINER.format(container=CONTAINER))
    nomes = [f"c{posicao:03d}" for posicao in range(1, len(capitulos) + 1)]
    for nome, blocos in zip(nomes, capitulos, strict=True):
        corpo = "\n".join(_elemento(bloco) for bloco in blocos)
        zip_.writestr(f"OEBPS/{nome}.xhtml", _documento(titulo, idioma, corpo))
    zip_.writestr("OEBPS/nav.xhtml", _sumario(titulo, idioma, nomes, capitulos))
    zip_.writestr("OEBPS/content.opf", _pacote(titulo, idioma, nomes))


def _elemento(bloco: Bloco) -> str:
    texto = escape(_limpo(bloco.texto))
    match bloco.tipo:
        case TipoDeBloco.TITULO:
            # Título acima do capítulo (nível 1) também vira h1; o XHTML só tem seis níveis.
            nivel = min(max(bloco.nivel, 1), 6)
            return f"<h{nivel}>{texto}</h{nivel}>"
        case TipoDeBloco.PARAGRAFO:
            return f"<p>{texto}</p>"
        case TipoDeBloco.CODIGO:
            return f"<pre>{texto}</pre>"
        case TipoDeBloco.NOTA:
            return f'<aside epub:type="footnote"><p>{texto}</p></aside>'
        case _:
            assert_never(bloco.tipo)


def _documento(titulo: str, idioma: str, corpo: str) -> str:
    return _XHTML.format(
        xhtml=XHTML, ops=OPS, titulo=escape(titulo), idioma=escape(idioma), corpo=corpo
    )


def _sumario(
    titulo: str, idioma: str, nomes: Sequence[str], capitulos: Sequence[Sequence[Bloco]]
) -> str:
    entradas = "\n".join(
        f'<li><a href="{nome}.xhtml">{escape(_rotulo(posicao, blocos))}</a></li>'
        for posicao, (nome, blocos) in enumerate(zip(nomes, capitulos, strict=True), start=1)
    )
    corpo = f'<nav epub:type="toc"><ol>\n{entradas}\n</ol></nav>'
    return _documento(titulo, idioma, corpo)


def _rotulo(posicao: int, blocos: Sequence[Bloco]) -> str:
    """O primeiro título do capítulo; sem título, a posição dele no livro."""
    titulos = (b.texto for b in blocos if b.tipo is TipoDeBloco.TITULO)
    return _limpo(next(titulos, str(posicao)))


def _pacote(titulo: str, idioma: str, nomes: Sequence[str]) -> str:
    itens = "\n".join(
        f'    <item id="{nome}" href="{nome}.xhtml" media-type="application/xhtml+xml"/>'
        for nome in nomes
    )
    referencias = "\n".join(f'    <itemref idref="{nome}"/>' for nome in nomes)
    return _OPF.format(
        opf=OPF,
        dc=DC,
        identificador=uuid.uuid4(),
        titulo=escape(titulo),
        idioma=escape(idioma),
        modificado=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        itens=itens,
        referencias=referencias,
    )


def _limpo(texto: str) -> str:
    return _FORA_DO_XML.sub("", texto)
