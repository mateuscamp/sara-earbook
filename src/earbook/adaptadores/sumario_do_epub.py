# SPDX-License-Identifier: GPL-3.0-or-later
"""Tira do sumário do EPUB os itens que apontam para um arquivo que não vai no livro montado
(ADR-0005, "Capítulo sem texto fora do EPUB montado").

O sumário do EPUB 3 é o arquivo `nav` (todo `<nav>` dele: sumário, `landmarks`, lista de páginas);
o do EPUB 2, o `toc.ncx`. O item que sai e tem filhos de outro arquivo dá o lugar a eles; a lista
que fica vazia sai, e o sumário que ficaria sem nenhum item é recusado.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from pathlib import Path

from lxml import etree

from earbook.adaptadores.pacote_epub import (
    EpubInvalidoError,
    arquivos_do_sumario,
    caminho_do_alvo,
    opf_sem_arquivos,
    tirar_elemento,
)
from earbook.adaptadores.papel_do_bloco import OPS
from earbook.adaptadores.xhtml import XHTML, entidades_html_em_numericas
from earbook.adaptadores.xml_seguro import PARSER_SEGURO, Elemento

NCX = "http://www.daisy.org/z3986/2005/ncx/"
_SUMARIO = "toc"


def tirar_do_pacote(
    pasta: Path, fora: Collection[str], substituicoes: Mapping[str, bytes]
) -> dict[str, bytes]:
    """As `substituicoes` do `montar` mais o OPF, o `nav` e o `toc.ncx` sem os arquivos de `fora`
    (caminhos a partir da raiz do EPUB extraído em `pasta`). Parte do conteúdo já trocado, se
    houver: o OPF no idioma da tradução, o `nav` que é capítulo e já foi montado."""
    arquivos = arquivos_do_sumario(pasta)

    def atual(caminho: str) -> bytes:
        return (
            substituicoes[caminho] if caminho in substituicoes else (pasta / caminho).read_bytes()
        )

    novas = dict(substituicoes)
    novas[arquivos.opf] = opf_sem_arquivos(atual(arquivos.opf), arquivos.opf, fora)
    if arquivos.nav is not None:
        novas[arquivos.nav] = nav_sem_arquivos(atual(arquivos.nav), arquivos.nav, fora)
    if arquivos.ncx is not None:
        novas[arquivos.ncx] = ncx_sem_arquivos(atual(arquivos.ncx), arquivos.ncx, fora)
    return novas


def nav_sem_arquivos(conteudo: bytes, caminho: str, fora: Collection[str]) -> bytes:
    """O arquivo `nav` sem os `<li>` cujo link aponta para um arquivo de `fora`."""
    raiz = _raiz(entidades_html_em_numericas(conteudo), caminho)
    for nav in list(raiz.iter(f"{{{XHTML}}}nav")):
        itens = [li for li in nav.iter(f"{{{XHTML}}}li") if _li_aponta_para(li, caminho, fora)]
        for li in itens:
            _dar_o_lugar_aos_filhos(li, f"{{{XHTML}}}ol/{{{XHTML}}}li")
        if not itens:
            continue
        _tirar_listas_vazias(nav)
        if next(nav.iter(f"{{{XHTML}}}li"), None) is None:
            _tirar_nav_vazio(nav, caminho)
    return etree.tostring(raiz.getroottree(), xml_declaration=True, encoding="utf-8")


def ncx_sem_arquivos(conteudo: bytes, caminho: str, fora: Collection[str]) -> bytes:
    """O `toc.ncx` sem os `<navPoint>`, `<pageTarget>` e `<navTarget>` que apontam para um
    arquivo de `fora`."""
    raiz = _raiz(conteudo, caminho)
    for nome in ("navPoint", "pageTarget", "navTarget"):
        for alvo in [
            e for e in raiz.iter(f"{{{NCX}}}{nome}") if _ncx_aponta_para(e, caminho, fora)
        ]:
            _dar_o_lugar_aos_filhos(alvo, f"{{{NCX}}}{nome}")
    for nome in ("pageList", "navList"):
        for lista in list(raiz.iter(f"{{{NCX}}}{nome}")):
            if next(lista.iter(f"{{{NCX}}}pageTarget", f"{{{NCX}}}navTarget"), None) is None:
                tirar_elemento(lista)
    if next(raiz.iter(f"{{{NCX}}}navPoint"), None) is None:
        mensagem = f"{caminho}: o sumário ficaria sem nenhum item, e o EPUB, inválido"
        raise EpubInvalidoError(mensagem)
    _fechar_a_ordem_de_leitura(raiz)
    return etree.tostring(raiz.getroottree(), xml_declaration=True, encoding="utf-8")


def _fechar_a_ordem_de_leitura(raiz: Elemento) -> None:
    """O `playOrder` sem salto, na mesma ordem: o epubcheck recusa a sequência com falha. Os
    itens que dividiam um número continuam dividindo."""
    com_ordem = [e for e in raiz.iter() if (e.get("playOrder") or "").isdecimal()]
    ordens = sorted({int(e.get("playOrder", "0")) for e in com_ordem})
    nova = {ordem: posicao for posicao, ordem in enumerate(ordens, start=1)}
    for elemento in com_ordem:
        elemento.set("playOrder", str(nova[int(elemento.get("playOrder", "0"))]))


def _raiz(conteudo: bytes, caminho: str) -> Elemento:
    try:
        return etree.fromstring(conteudo, PARSER_SEGURO)
    except etree.XMLSyntaxError as erro:
        mensagem = f"{caminho}: sumário malformado ({erro})"
        raise EpubInvalidoError(mensagem) from erro


def _li_aponta_para(li: Elemento, caminho: str, fora: Collection[str]) -> bool:
    """O link do próprio item: o `<a>` filho direto, e não o de um item de dentro."""
    link = li.find(f"{{{XHTML}}}a")
    return link is not None and caminho_do_alvo(caminho, link.get("href", "")) in fora


def _ncx_aponta_para(alvo: Elemento, caminho: str, fora: Collection[str]) -> bool:
    conteudo = alvo.find(f"{{{NCX}}}content")
    return conteudo is not None and caminho_do_alvo(caminho, conteudo.get("src", "")) in fora


def _dar_o_lugar_aos_filhos(item: Elemento, filhos: str) -> None:
    """Tira `item` e põe no lugar dele os itens de dentro (`filhos`, um caminho a partir dele):
    o que aponta para outro arquivo sobe um nível; o que aponta para o mesmo sai na vez dele."""
    pai = item.getparent()
    if pai is None:
        return
    posicao = pai.index(item)
    for deslocamento, filho in enumerate(item.findall(filhos)):
        pai.insert(posicao + deslocamento, filho)
    tirar_elemento(item)


def _tirar_listas_vazias(nav: Elemento) -> None:
    """A lista de dentro que ficou sem item: `<li><a/><ol/></li>` é inválido."""
    for lista in list(nav.iter(f"{{{XHTML}}}ol")):
        pai = lista.getparent()
        if len(lista) == 0 and pai is not None and pai.tag == f"{{{XHTML}}}li":
            tirar_elemento(lista)


def _tirar_nav_vazio(nav: Elemento, caminho: str) -> None:
    """O `landmarks` e a lista de páginas são opcionais; o sumário não."""
    if _SUMARIO in (nav.get(f"{{{OPS}}}type") or "").split():
        mensagem = f"{caminho}: o sumário ficaria sem nenhum item, e o EPUB, inválido"
        raise EpubInvalidoError(mensagem)
    tirar_elemento(nav)
