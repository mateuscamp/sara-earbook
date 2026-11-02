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
from collections.abc import Collection, Iterator, Mapping
from dataclasses import dataclass
from urllib.parse import unquote

from lxml import etree

from earbook.adaptadores.xml_seguro import PARSER_SEGURO, Elemento
from earbook.dominio.segmento import Papel, Segmento, id_do_segmento, normalizar_espacos
from earbook.dominio.traducao import TrocaDeIdioma

XHTML = "http://www.w3.org/1999/xhtml"
OPS = "http://www.idpf.org/2007/ops"
ATRIBUTO_DO_ID = "data-earbook"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
# O livro montado é sempre em pt-BR: em português de origem ou traduzido (ADR-0003).
TITULO_DAS_NOTAS = "Notas"

TITULOS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
ITENS = frozenset({"li", "dt", "dd"})
CELULAS = frozenset({"td", "th"})
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
    `c003-s0001`, `c003-s0002`... e o XHTML com `data-earbook` em cada um.
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


def ids_marcados(conteudo: bytes, caminho: str) -> tuple[str, ...]:
    """Os IDs marcados com `data-earbook` no XHTML, na ordem do documento."""
    corpo = _corpo(conteudo, caminho)
    return tuple(marca for e in corpo.iter() if (marca := e.get(ATRIBUTO_DO_ID)) is not None)


def ids_no_sumario(conteudo: bytes, caminho: str) -> frozenset[str]:
    """Os IDs marcados dentro do `<nav>`: na amostra, o sem tradução fica no original."""
    corpo = _corpo(conteudo, caminho)
    return frozenset(
        marca
        for e in corpo.iter()
        if (marca := e.get(ATRIBUTO_DO_ID)) is not None and _no_sumario(e)
    )


def montar_xhtml(
    conteudo: bytes,
    textos: Mapping[str, str],
    notas: Collection[str],
    caminho: str,
    idioma: TrocaDeIdioma | None = None,
) -> bytes:
    """O XHTML marcado com o texto final no lugar de cada segmento (ADR-0005).

    `textos` tem o texto final de cada ID mantido; o elemento de ID fora dele (removido ou
    juntado) sai. O ID em `notas` sai do lugar e entra no fim do capítulo, sob "Notas",
    como parágrafo comum. A marca `data-earbook` sai de todos. Todo `id` do capítulo
    continua nele (ver `_ancoras_no_comeco`). Com `idioma`, o `lang` e o `xml:lang` do
    idioma do original passam a ser o da tradução (ADR-0006).
    """
    corpo = _corpo(conteudo, caminho)
    no_fim: list[str] = []
    pendentes: list[str] = []
    ultimo: Elemento | None = None
    for elemento in [e for e in corpo.iter() if e.get(ATRIBUTO_DO_ID) is not None]:
        id_ = elemento.attrib.pop(ATRIBUTO_DO_ID)
        if _no_sumario(elemento):
            _trocar_texto_do_link(elemento, textos.get(id_))
            continue
        if id_ in textos and id_ not in notas:
            _trocar_texto(elemento, textos[id_], pendentes)
            pendentes, ultimo = [], elemento
            continue
        if id_ in textos:
            no_fim.append(textos[id_])
        pendentes += _tirar(elemento, corpo)
    _guardar_ancoras(corpo, ultimo, pendentes)
    if no_fim:
        _acrescentar_notas(corpo, no_fim)
    if idioma is not None:
        _trocar_idioma(corpo.getroottree().getroot(), idioma)
    return etree.tostring(corpo.getroottree(), xml_declaration=True, encoding="utf-8")


def _trocar_idioma(raiz: Elemento, troca: TrocaDeIdioma) -> None:
    """O trecho marcado com outra língua (`xml:lang="fr"`) fica: é escolha do autor."""
    for elemento in raiz.iter():
        for atributo in ("lang", XML_LANG):
            if _nome(elemento) and (valor := elemento.get(atributo)) is not None:
                elemento.set(atributo, troca.trocar(valor))


def _no_sumario(elemento: Elemento) -> bool:
    return any(_nome(ancestral) == "nav" for ancestral in elemento.iterancestors())


def _trocar_texto_do_link(elemento: Elemento, texto: str | None) -> None:
    """No sumário (`<nav>`), nada sai e o item não recebe âncora de fora: sem o `<a href>`,
    ou sem o `<nav>`, o leitor perde a navegação, e `<a id>` no `<li>` é inválido (A1 da
    auditoria; N1 a N3 da pós-auditoria). O texto final entra no link, que mantém o `href`:
    no livro traduzido, o sumário também sai em português.
    """
    if texto is None:
        return
    links = [d for d in elemento.iterdescendants() if _nome(d) in {"a", "span"}]
    alvo = links[0] if links else elemento
    for filho in list(alvo):
        alvo.remove(filho)
    alvo.text = texto


def _trocar_texto(elemento: Elemento, texto: str, ancoras_de_antes: list[str]) -> None:
    """O texto final entra sem a marcação interna: itálico e link não mudam o áudio."""
    de_dentro = _ids_de_dentro(elemento)
    for filho in list(elemento):
        elemento.remove(filho)
    elemento.text = texto
    _ancoras_no_comeco(elemento, [*ancoras_de_antes, *de_dentro])


def _ancoras_no_comeco(elemento: Elemento, ids: list[str]) -> None:
    """Todo `id` do capítulo continua nele, como `<a id>` vazio no começo de um bloco de
    texto, que sempre aceita `<a>`: o sumário e as notas apontam para ele
    (`cap.xhtml#calibre_toc_3`). Solto no `<ul>` ou no `<body>` do EPUB2, o `<a>` seria
    XHTML inválido (A4 da auditoria)."""
    if not ids:
        return
    texto, elemento.text = elemento.text, None
    ancoras = [_ancora(id_) for id_ in ids]
    for posicao, ancora in enumerate(ancoras):
        elemento.insert(posicao, ancora)
    ancoras[-1].tail = texto


def _guardar_ancoras(corpo: Elemento, ultimo: Elemento | None, ids: list[str]) -> None:
    """As âncoras tiradas depois do último bloco mantido vão para o fim dele; sem bloco
    mantido no capítulo, para um `<div>`, que aceita `<a>`."""
    if not ids:
        return
    destino = ultimo if ultimo is not None else etree.SubElement(corpo, f"{{{XHTML}}}div")
    for id_ in ids:
        destino.append(_ancora(id_))


def _tirar(elemento: Elemento, corpo: Elemento) -> list[str]:
    """Tira o elemento sem levar o texto solto que vem depois dele, e o contêiner que
    esvaziou. Devolve os `id` que saíram, para virarem âncora num bloco mantido."""
    pai = elemento.getparent()
    if pai is None:
        return []
    ids = [id_ for id_ in [elemento.get("id")] if id_] + _ids_de_dentro(elemento)
    if elemento.tail and elemento.tail.strip():
        anterior = elemento.getprevious()
        if anterior is not None:
            anterior.tail = (anterior.tail or "") + elemento.tail
        else:
            pai.text = (pai.text or "") + elemento.tail
    pai.remove(elemento)
    if pai is not corpo and len(pai) == 0 and not (pai.text or "").strip():
        ids += _tirar(pai, corpo)
    return ids


def _ids_de_dentro(elemento: Elemento) -> list[str]:
    return [id_ for filho in elemento.iterdescendants() if (id_ := filho.get("id"))]


def _ancora(id_: str) -> Elemento:
    ancora = etree.Element(f"{{{XHTML}}}a")
    ancora.set("id", id_)
    return ancora


def _acrescentar_notas(corpo: Elemento, textos: list[str]) -> None:
    titulo = etree.SubElement(corpo, f"{{{XHTML}}}h2")
    titulo.text = TITULO_DAS_NOTAS
    for texto in textos:
        paragrafo = etree.SubElement(corpo, f"{{{XHTML}}}p")
        paragrafo.text = texto


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
    """Nota vence tudo; depois título; depois o contêiner (A3 da auditoria: só parágrafo
    com parágrafo se junta na limpeza, então item, célula e citação precisam de papel próprio).
    """
    ancestrais = (folha, *folha.iterancestors())
    if any(_eh_corpo_de_nota(elemento, alvos_locais) for elemento in ancestrais):
        return Papel.NOTA
    nome = _nome(folha)
    if nome in TITULOS:
        return Papel.TITULO
    if nome in ITENS:
        return Papel.ITEM
    if nome in CELULAS:
        return Papel.CELULA
    if any(_nome(elemento) == "blockquote" for elemento in ancestrais):
        return Papel.CITACAO
    return Papel.PARAGRAFO


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
