# SPDX-License-Identifier: GPL-3.0-or-later
"""Quebra um XHTML de capítulo em segmentos e marca cada um no próprio XHTML.

Segmento é o bloco-folha: elemento de bloco sem outro bloco dentro. A regra
existe porque a referência (ebook-GPT-translator) extraía `<blockquote>` e o
`<p>` de dentro, e o TTS lia o trecho duas vezes (ADR-0001).
"""

from __future__ import annotations

import html.entities
import posixpath
import re
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import unquote

from lxml import etree

from ai_book.adaptadores.xml_seguro import PARSER_SEGURO, Elemento
from ai_book.dominio.segmento import Papel, Segmento, id_do_segmento, normalizar_espacos

XHTML = "http://www.w3.org/1999/xhtml"
OPS = "http://www.idpf.org/2007/ops"
ATRIBUTO_DO_ID = "data-ai-book"

TITULOS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
BLOCOS = TITULOS | frozenset(
    {
        "p", "div", "li", "blockquote", "section", "article", "aside", "header",
        "footer", "nav", "main", "figure", "figcaption", "dt", "dd", "td", "th",
        "caption", "pre", "address", "table", "tr", "thead", "tbody", "tfoot",
        "ul", "ol", "dl", "hr",
    }
)  # fmt: skip
TIPOS_DE_NOTA = frozenset({"footnote", "endnote", "rearnote", "note"})
PAPEIS_ARIA_DE_NOTA = frozenset({"doc-footnote", "doc-endnote"})
# Texto de chamada de nota sem epub:type: "1", "[2]", "(3)", "*", "†", "a".
_CHAMADA_CURTA = re.compile(r"^[\[(]?(\d{1,3}|[*†‡§¶]+|[a-z])[\])]?$")
_ENTIDADE = re.compile(rb"&([A-Za-z][A-Za-z0-9]{1,31});")
_ENTIDADES_DO_XML = frozenset({b"amp", b"lt", b"gt", b"quot", b"apos"})


@dataclass(frozen=True)
class CapituloSegmentado:
    xhtml_marcado: bytes
    segmentos: list[Segmento]
    texto_fora_de_segmento: list[str]


class XhtmlInvalidoError(ValueError):
    pass


def segmentar_xhtml(conteudo: bytes, capitulo: str, caminho: str) -> CapituloSegmentado:
    """Segmenta o XHTML `caminho` (relativo à raiz do EPUB) do capítulo `capitulo`.

    `segmentar_xhtml(dados, "c003", "OEBPS/cap3.xhtml")` devolve os segmentos
    `c003-s0001`, `c003-s0002`... e o XHTML com `data-ai-book` em cada um.
    """
    corpo = _corpo(conteudo, caminho)
    chamadas = {a for a in corpo.iter(f"{{{XHTML}}}a") if _eh_chamada_de_nota(a)}
    alvos = _alvos_locais(chamadas, caminho)
    segmentos: list[Segmento] = []
    for folha in _folhas(corpo):
        texto, notas = _texto_e_notas(folha, chamadas, caminho)
        if not texto:
            continue
        segmento = Segmento(
            id=id_do_segmento(capitulo, len(segmentos) + 1),
            papel=_papel(folha, alvos),
            texto=texto,
            notas=tuple(notas),
        )
        folha.set(ATRIBUTO_DO_ID, segmento.id)
        segmentos.append(segmento)
    marcado = etree.tostring(corpo.getroottree(), xml_declaration=True, encoding="utf-8")
    return CapituloSegmentado(marcado, segmentos, list(_texto_fora(corpo, chamadas)))


def _corpo(conteudo: bytes, caminho: str) -> Elemento:
    try:
        raiz = etree.fromstring(_entidades_html_em_numericas(conteudo), PARSER_SEGURO)
    except etree.XMLSyntaxError as erro:
        mensagem = f"{caminho}: XHTML malformado ({erro})"
        raise XhtmlInvalidoError(mensagem) from erro
    corpo = raiz.find(f"{{{XHTML}}}body")
    if corpo is None:
        mensagem = f"{caminho}: sem <body> no namespace {XHTML}"
        raise XhtmlInvalidoError(mensagem)
    _recusar_entidade_sem_valor(corpo, caminho)
    return corpo


def _entidades_html_em_numericas(conteudo: bytes) -> bytes:
    """`&nbsp;` → `&#160;`. O EPUB2 confia no DTD do XHTML, que o parser seguro não carrega."""

    def trocar(achado: re.Match[bytes]) -> bytes:
        nome = achado.group(1)
        texto = html.entities.html5.get(nome.decode("ascii") + ";")
        if nome in _ENTIDADES_DO_XML or texto is None:
            return achado.group(0)
        return "".join(f"&#{ord(letra)};" for letra in texto).encode("ascii")

    return _ENTIDADE.sub(trocar, conteudo)


def _recusar_entidade_sem_valor(corpo: Elemento, caminho: str) -> None:
    """Entidade que sobrou sem valor sumiria do áudio em silêncio (A1 da auditoria)."""
    # O .text de um nó de entidade é a própria referência: "&nome;".
    nomes = sorted({entidade.text or "" for entidade in corpo.iter(etree.Entity)})
    if nomes:
        mensagem = f"{caminho}: entidade sem valor conhecido: {', '.join(nomes)}"
        raise XhtmlInvalidoError(mensagem)


def _nome(elemento: Elemento) -> str:
    """Nome local do elemento; comentário e instrução de processamento viram ''."""
    if not isinstance(elemento.tag, str):
        return ""
    return etree.QName(elemento).localname


def _eh_chamada_de_nota(link: Elemento) -> bool:
    if "#" not in link.get("href", ""):
        return False
    if "noteref" in link.get(f"{{{OPS}}}type", "").split():
        return True
    if link.get("role") == "doc-noteref":
        return True
    if not _CHAMADA_CURTA.match(normalizar_espacos("".join(link.itertext()))):
        return False
    pai = link.getparent()
    dentro_de_sup = pai is not None and _nome(pai) == "sup"
    return dentro_de_sup or any(_nome(filho) == "sup" for filho in link)


def _destino(href: str, caminho: str) -> str:
    """Resolve `notes.xhtml#n2` a partir de `OEBPS/cap1.xhtml` → `OEBPS/notes.xhtml#n2`."""
    arquivo, _, fragmento = href.partition("#")
    if not arquivo:
        return f"{caminho}#{fragmento}"
    resolvido = posixpath.normpath(posixpath.join(posixpath.dirname(caminho), unquote(arquivo)))
    return f"{resolvido}#{fragmento}"


def _alvos_locais(chamadas: set[Elemento], caminho: str) -> set[str]:
    prefixo = f"{caminho}#"
    destinos = (_destino(a.get("href", ""), caminho) for a in chamadas)
    return {d.removeprefix(prefixo) for d in destinos if d.startswith(prefixo)}


def _folhas(corpo: Elemento) -> Iterator[Elemento]:
    for elemento in corpo.iterdescendants():
        if _nome(elemento) in BLOCOS and not _tem_bloco_dentro(elemento):
            yield elemento


def _tem_bloco_dentro(elemento: Elemento) -> bool:
    return any(_nome(d) in BLOCOS for d in elemento.iterdescendants())


def _texto_e_notas(folha: Elemento, chamadas: set[Elemento], caminho: str) -> tuple[str, list[str]]:
    notas: list[str] = []
    pedacos = _pedacos_de_texto(folha, chamadas, caminho, notas)
    return normalizar_espacos("".join(pedacos)), notas


def _pedacos_de_texto(
    elemento: Elemento, chamadas: set[Elemento], caminho: str, notas: list[str]
) -> Iterator[str]:
    """Texto do elemento sem as chamadas de nota; `<br/>` vira espaço."""
    if elemento.text and _nome(elemento):
        yield elemento.text
    for filho in elemento:
        if filho in chamadas:
            notas.append(_destino(filho.get("href", ""), caminho))
        elif _nome(filho) == "br":
            yield " "
        elif _nome(filho):
            yield from _pedacos_de_texto(filho, chamadas, caminho, notas)
        if filho.tail:
            yield filho.tail


def _papel(folha: Elemento, alvos_locais: set[str]) -> Papel:
    for elemento in (folha, *folha.iterancestors()):
        if _eh_corpo_de_nota(elemento, alvos_locais):
            return Papel.NOTA
    return Papel.TITULO if _nome(folha) in TITULOS else Papel.PARAGRAFO


def _eh_corpo_de_nota(elemento: Elemento, alvos_locais: set[str]) -> bool:
    tipos = set(elemento.get(f"{{{OPS}}}type", "").split())
    return (
        bool(tipos & TIPOS_DE_NOTA)
        or elemento.get("role") in PAPEIS_ARIA_DE_NOTA
        or elemento.get("id") in alvos_locais
    )


def _texto_fora(elemento: Elemento, chamadas: set[Elemento]) -> Iterator[str]:
    """Texto que não caiu em nenhuma folha, como em `<div>solto<p>x</p></div>`."""
    if _nome(elemento) in BLOCOS and not _tem_bloco_dentro(elemento):
        return
    if elemento.text and elemento.text.strip():
        yield normalizar_espacos(elemento.text)
    for filho in elemento:
        if _nome(filho) and filho not in chamadas:
            yield from _texto_fora(filho, chamadas)
        if filho.tail and filho.tail.strip():
            yield normalizar_espacos(filho.tail)
