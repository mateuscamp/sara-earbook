# SPDX-License-Identifier: GPL-3.0-or-later
"""O que cada bloco do XHTML é, pela marcação: nota, título, item, célula, citação, código ou
índice remissivo. Saiu de `xhtml.py`, que passaria das 400 linhas com o código e o índice
(ADR-0008).
"""

from __future__ import annotations

from lxml import etree

from earbook.adaptadores.xml_seguro import Elemento
from earbook.dominio.segmento import Papel

OPS = "http://www.idpf.org/2007/ops"
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
_PAPEL_DO_NOME = {
    **dict.fromkeys(TITULOS, Papel.TITULO),
    **dict.fromkeys(ITENS, Papel.ITEM),
    **dict.fromkeys(CELULAS, Papel.CELULA),
}
# ADR-0008: o Gherkin é prosa estruturada ("Given… When… Then…"), feita para o especialista do
# domínio ler. Fica parágrafo e é traduzido; o resto do código sai do áudio.
LINGUAGENS_DE_PROSA = frozenset({"gherkin"})


def nome_local(elemento: Elemento) -> str:
    """Nome local do elemento; comentário e instrução de processamento viram ''."""
    if not isinstance(elemento.tag, str):
        return ""
    return etree.QName(elemento).localname


def papel_do_bloco(folha: Elemento, alvos_locais: set[str]) -> Papel:
    """O índice vence tudo, porque leva o bloco inteiro; depois a nota; depois o código, o
    título e o contêiner (A3 da auditoria: só parágrafo com parágrafo se junta na limpeza, então
    item, célula e citação precisam de papel próprio).
    """
    if raiz_do_indice(folha):
        return Papel.INDICE
    ancestrais = (folha, *folha.iterancestors())
    if any(_eh_corpo_de_nota(elemento, alvos_locais) for elemento in ancestrais):
        return Papel.NOTA
    if _eh_codigo(folha):
        return Papel.CODIGO
    if (papel := _PAPEL_DO_NOME.get(nome_local(folha))) is not None:
        return papel
    if any(nome_local(elemento) == "blockquote" for elemento in ancestrais):
        return Papel.CITACAO
    return Papel.PARAGRAFO


def raiz_do_indice(elemento: Elemento) -> bool:
    """O bloco que é o índice inteiro, um segmento só (ADR-0008): o bloco mais externo dentro da
    marca. Com a marca num bloco, é ele; com a marca no `<body>`, cada bloco dele que não está
    dentro de outro, mesmo sob um `<span>` (A2 da code-audit). O link do `landmarks`
    (`<a epub:type="index">`) não tem bloco dentro e não conta.
    """
    if nome_local(elemento) not in BLOCOS or not _na_marca_de_indice(elemento):
        return False
    acima = next((a for a in elemento.iterancestors() if nome_local(a) in BLOCOS), None)
    return acima is None or not _na_marca_de_indice(acima)


def _na_marca_de_indice(elemento: Elemento) -> bool:
    return any(_marcado_como_indice(e) for e in (elemento, *elemento.iterancestors()))


def _marcado_como_indice(elemento: Elemento) -> bool:
    """Pela marcação, nunca pelo título nem pelo nome do arquivo: o Huxley tem `index.xhtml` como
    folha de rosto, e "Índice", em português, é muitas vezes o sumário (ADR-0008). Vale o EPUB 3
    (`epub:type`), o DPUB-ARIA (`role`) e o HTMLBook da O'Reilly (`data-type`).
    """
    return (
        "index" in elemento.get(f"{{{OPS}}}type", "").split()
        or "doc-index" in elemento.get("role", "").split()
        or elemento.get("data-type") == "index"
    )


def _eh_codigo(folha: Elemento) -> bool:
    """O `<pre>` que se declara código (ADR-0008). O sem marca fica parágrafo: é o do
    `importar-pdf`, em que a fonte monoespaçada marca também prosa ("Wednesday, November 3,
    13:00" no Hard Parts), e é onde um EPUB mal feito põe verso.
    """
    if nome_local(folha) != "pre" or _linguagens(folha) & LINGUAGENS_DE_PROSA:
        return False
    return (
        folha.get("data-code-language") is not None
        or "programlisting" in folha.get("data-type", "").split()
        or any(nome_local(dentro) == "code" for dentro in folha.iterdescendants())
    )


def _linguagens(folha: Elemento) -> set[str]:
    """A linguagem que o bloco declara: `data-code-language` (HTMLBook), `language-x` na classe
    do `<pre>` ou do `<code>` (a recomendação do HTML) ou o nome solto na classe (o pandoc:
    `sourceCode gherkin`). A3 da code-audit: o Gherkin marcado pela classe saía como código.
    """
    nomes = {folha.get("data-code-language", "")}
    for elemento in (folha, *folha.iterdescendants()):
        if nome_local(elemento) in {"pre", "code"}:
            nomes |= {t.removeprefix("language-") for t in elemento.get("class", "").split()}
    return {nome.casefold() for nome in nomes if nome}


def _eh_corpo_de_nota(elemento: Elemento, alvos_locais: set[str]) -> bool:
    tipos = set(elemento.get(f"{{{OPS}}}type", "").split())
    return (
        bool(tipos & TIPOS_DE_NOTA)
        or elemento.get("role") in PAPEIS_ARIA_DE_NOTA
        or elemento.get("id") in alvos_locais
    )
