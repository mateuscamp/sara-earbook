# SPDX-License-Identifier: GPL-3.0-or-later
"""Extrai o EPUB (um zip) e lê do OPF os metadados e a ordem de leitura."""

from __future__ import annotations

import posixpath
import zipfile
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from lxml import etree

from earbook.adaptadores.xml_seguro import PARSER_SEGURO, Elemento
from earbook.dominio.trabalho import ItemIgnorado
from earbook.dominio.traducao import TrocaDeIdioma

CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
OPF = "http://www.idpf.org/2007/opf"
DC = "http://purl.org/dc/elements/1.1/"
# text/x-oeb1-document: XHTML do OEB 1, o formato antes do EPUB, ainda visto em livro antigo.
TIPOS_XHTML = frozenset({"application/xhtml+xml", "text/html", "text/x-oeb1-document"})
# Um EPUB de texto passa pouco de dezenas de MB; acima disso, é provável bomba de zip.
LIMITE_DESCOMPACTADO = 2 * 1024**3
TIPO_DO_NCX = "application/x-dtbncx+xml"


class EpubInvalidoError(ValueError):
    pass


@dataclass(frozen=True)
class PacoteEpub:
    titulo: str
    autor: str
    idioma: str
    spine: tuple[str, ...]
    """Caminhos dos XHTML na ordem de leitura, relativos à raiz do EPUB, sem repetição."""
    ignorados: tuple[ItemIgnorado, ...]


def extrair_epub(epub: Path, destino: Path) -> PacoteEpub:
    """Extrai `epub` em `destino` e devolve metadados e spine."""
    try:
        with zipfile.ZipFile(epub) as zip_:
            _extrair_com_seguranca(zip_, destino)
    except zipfile.BadZipFile as erro:
        mensagem = f"{epub}: não é um zip válido ({erro})"
        raise EpubInvalidoError(mensagem) from erro
    caminho_opf = _caminho_do_opf(destino)
    return _ler_opf(destino, caminho_opf)


def _extrair_com_seguranca(zip_: zipfile.ZipFile, destino: Path) -> None:
    membros = zip_.infolist()
    total = sum(membro.file_size for membro in membros)
    if total > LIMITE_DESCOMPACTADO:
        mensagem = f"descompactado teria {total} bytes (limite {LIMITE_DESCOMPACTADO})"
        raise EpubInvalidoError(mensagem)
    raiz = destino.resolve()
    for membro in membros:
        alvo = (raiz / membro.filename).resolve()
        if not alvo.is_relative_to(raiz):
            mensagem = f"membro {membro.filename!r} escapa da pasta de extração"
            raise EpubInvalidoError(mensagem)
    zip_.extractall(raiz)


def _xml(caminho: Path) -> Elemento:
    try:
        return etree.parse(str(caminho), PARSER_SEGURO).getroot()
    except (OSError, etree.XMLSyntaxError) as erro:
        mensagem = f"{caminho.name}: não foi possível ler ({erro})"
        raise EpubInvalidoError(mensagem) from erro


def _caminho_do_opf(raiz: Path) -> str:
    container = _xml(raiz / "META-INF" / "container.xml")
    rootfile = container.find(f".//{{{CONTAINER}}}rootfile")
    if rootfile is None or not rootfile.get("full-path"):
        mensagem = "META-INF/container.xml sem <rootfile full-path=...>"
        raise EpubInvalidoError(mensagem)
    # A2 da auditoria: sem a checagem, o título vinha de um OPF plantado fora da pasta.
    return _caminho_dentro_do_epub("", rootfile.get("full-path", ""), "o container.xml")


def _ler_opf(raiz: Path, caminho_opf: str) -> PacoteEpub:
    opf = _xml(raiz / caminho_opf)
    spine, ignorados = _spine(opf, posixpath.dirname(caminho_opf))
    return PacoteEpub(
        titulo=_metadado(opf, "title"),
        autor=_metadado(opf, "creator"),
        idioma=_metadado(opf, "language"),
        spine=spine,
        ignorados=ignorados,
    )


def _metadado(opf: Elemento, nome: str) -> str:
    elemento = opf.find(f"{{{OPF}}}metadata/{{{DC}}}{nome}")
    return "" if elemento is None else " ".join("".join(elemento.itertext()).split())


def _spine(opf: Elemento, pasta_do_opf: str) -> tuple[tuple[str, ...], tuple[ItemIgnorado, ...]]:
    manifesto = {item.get("id"): item for item in opf.iterfind(f"{{{OPF}}}manifest/{{{OPF}}}item")}
    caminhos: list[str] = []
    ignorados: list[ItemIgnorado] = []
    for itemref in opf.iterfind(f"{{{OPF}}}spine/{{{OPF}}}itemref"):
        idref = itemref.get("idref", "")
        item = manifesto.get(idref)
        # A4 da auditoria: item que não se lê era pulado sem aviso, levando o capítulo junto.
        motivo = _motivo_para_nao_ler(item)
        if item is None or motivo:
            ignorados.append(ItemIgnorado(idref, motivo))
            continue
        href = unquote(item.get("href", "").partition("#")[0])
        caminho = _caminho_dentro_do_epub(pasta_do_opf, href, "o spine")
        # A3 da auditoria: ler duas vezes duplicava o texto no áudio e deixava ID órfão.
        if caminho in caminhos:
            ignorados.append(ItemIgnorado(idref, f"repete {caminho}"))
            continue
        caminhos.append(caminho)
    return tuple(caminhos), tuple(ignorados)


def _motivo_para_nao_ler(item: Elemento | None) -> str:
    """'' quando o item é XHTML legível; senão, o motivo para o relato."""
    if item is None:
        return "idref sem item no manifesto"
    tipo = item.get("media-type", "")
    # "application/xhtml+xml; charset=utf-8" continua sendo XHTML.
    if tipo.partition(";")[0].strip().lower() not in TIPOS_XHTML:
        return f"tipo {tipo} não é XHTML"
    return ""


def _caminho_dentro_do_epub(base: str, href: str, quem_aponta: str) -> str:
    """Recusa href absoluto ou com `..` que sai da raiz: o `preparar` lê e regrava o alvo."""
    caminho = posixpath.normpath(posixpath.join(base, href))
    if caminho.startswith(("/", "../")) or caminho == "..":
        mensagem = f"{quem_aponta} aponta para fora do EPUB: {href!r}"
        raise EpubInvalidoError(mensagem)
    return caminho


def opf_em_outro_idioma(pasta: Path, troca: TrocaDeIdioma) -> tuple[str, bytes]:
    """O caminho do OPF dentro de `pasta` (o EPUB extraído) e o OPF com o idioma trocado.

    Muda o `dc:language` e o `dcterms:language` do idioma do original: com "en", o leitor
    pode escolher a voz inglesa para ler o português (ADR-0006).
    """
    caminho = _caminho_do_opf(pasta)
    opf = _xml(pasta / caminho)
    for elemento in opf.iter(f"{{{DC}}}language", f"{{{OPF}}}meta"):
        do_idioma = elemento.tag == f"{{{DC}}}language"
        if (do_idioma or elemento.get("property") == "dcterms:language") and elemento.text:
            elemento.text = troca.trocar(elemento.text.strip())
    return caminho, etree.tostring(opf.getroottree(), xml_declaration=True, encoding="utf-8")


@dataclass(frozen=True)
class ArquivosDoSumario:
    """Onde o pacote guarda a ordem de leitura e o sumário, a partir da raiz do EPUB."""

    opf: str
    nav: str | None
    """O sumário do EPUB 3: o item do manifesto com a propriedade `nav`."""
    ncx: str | None
    """O sumário do EPUB 2: o item do manifesto com o tipo do `toc.ncx`."""


def arquivos_do_sumario(pasta: Path) -> ArquivosDoSumario:
    """O OPF, o `nav` e o `toc.ncx` do EPUB extraído em `pasta` (ADR-0005, "Capítulo sem texto
    fora do EPUB montado")."""
    caminho = _caminho_do_opf(pasta)
    base = posixpath.dirname(caminho)
    nav = ncx = None
    for item in _xml(pasta / caminho).iterfind(f"{{{OPF}}}manifest/{{{OPF}}}item"):
        href = unquote(item.get("href", "").partition("#")[0])
        if "nav" in item.get("properties", "").split():
            nav = nav or _caminho_dentro_do_epub(base, href, "o manifesto")
        elif item.get("media-type", "").partition(";")[0].strip().lower() == TIPO_DO_NCX:
            ncx = ncx or _caminho_dentro_do_epub(base, href, "o manifesto")
    return ArquivosDoSumario(caminho, nav, ncx)


def caminho_do_alvo(de: str, href: str) -> str:
    """O caminho, a partir da raiz do EPUB, do arquivo a que `href` leva quando escrito no arquivo
    `de`: sem a âncora e sem o escape da URL. O link para fora do livro dá um caminho que nenhum
    arquivo tem."""
    alvo = unquote(href.partition("#")[0])
    return posixpath.normpath(posixpath.join(posixpath.dirname(de), alvo))


def opf_sem_arquivos(conteudo: bytes, caminho: str, fora: Collection[str]) -> bytes:
    """O OPF sem os arquivos de `fora`: saem o `<item>` do manifesto, o `<itemref>` do spine e a
    `<reference>` do `<guide>` de cada um; o `<guide>` que fica vazio sai junto."""
    try:
        opf = etree.fromstring(conteudo, PARSER_SEGURO)
    except etree.XMLSyntaxError as erro:
        mensagem = f"{caminho}: não foi possível ler ({erro})"
        raise EpubInvalidoError(mensagem) from erro
    ids = _tirar_os_que_apontam(opf, f"{{{OPF}}}manifest/{{{OPF}}}item", caminho, fora)
    for itemref in list(opf.iterfind(f"{{{OPF}}}spine/{{{OPF}}}itemref")):
        if itemref.get("idref") in ids:
            tirar_elemento(itemref)
    _ = _tirar_os_que_apontam(opf, f"{{{OPF}}}guide/{{{OPF}}}reference", caminho, fora)
    guia = opf.find(f"{{{OPF}}}guide")
    if guia is not None and len(guia) == 0:
        tirar_elemento(guia)
    if opf.find(f"{{{OPF}}}spine/{{{OPF}}}itemref") is None:
        mensagem = f"{caminho}: o spine ficaria sem nenhum arquivo, e o EPUB, inválido"
        raise EpubInvalidoError(mensagem)
    return etree.tostring(opf.getroottree(), xml_declaration=True, encoding="utf-8")


def _tirar_os_que_apontam(
    opf: Elemento, onde: str, caminho: str, fora: Collection[str]
) -> set[str | None]:
    """Tira os elementos de `onde` cujo `href` leva a um arquivo de `fora`; devolve o `id` deles."""
    ids: set[str | None] = set()
    for elemento in list(opf.iterfind(onde)):
        if caminho_do_alvo(caminho, elemento.get("href", "")) in fora:
            ids.add(elemento.get("id"))
            tirar_elemento(elemento)
    return ids


def tirar_elemento(elemento: Elemento) -> None:
    """Tira o elemento e guarda o texto que vinha depois dele, que o lxml levaria junto."""
    pai = elemento.getparent()
    if pai is None:
        return
    resto = elemento.tail or ""
    anterior = elemento.getprevious()
    if anterior is not None:
        anterior.tail = (anterior.tail or "") + resto
    else:
        pai.text = (pai.text or "") + resto
    pai.remove(elemento)


def gravar_pacote(destino: Path, escrever: Callable[[zipfile.ZipFile], None]) -> None:
    """Grava um EPUB em `destino`, que não pode existir ainda: o `mimetype` primeiro e sem
    compressão (é assim que o leitor reconhece o EPUB), depois o que `escrever` puser.

    Se algo falhar no meio, apaga o arquivo que acabou de criar: EPUB pela metade pareceria
    um livro, e a próxima gravação recusaria o destino sem motivo.
    """
    arquivo = destino.open("xb")
    # O `close` fica dentro do `try`: o último flush é onde o disco cheio aparece (revisão nº 3).
    try:
        with arquivo, zipfile.ZipFile(arquivo, "w", zipfile.ZIP_DEFLATED) as zip_:
            zip_.writestr("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
            escrever(zip_)
    except BaseException:
        destino.unlink()
        raise


def empacotar_pasta(
    pasta: Path, destino: Path, substituicoes: Mapping[str, bytes], fora: Collection[str] = ()
) -> None:
    """Empacota o EPUB extraído em `pasta`, com `substituicoes` (caminho → conteúdo) no lugar e
    sem os arquivos de `fora` (ADR-0005, "Capítulo sem texto fora do EPUB montado")."""

    def escrever(zip_: zipfile.ZipFile) -> None:
        for arquivo in sorted(pasta.rglob("*")):
            nome = arquivo.relative_to(pasta).as_posix()
            # A pasta é editada pelo agente e pela tradução: um link para fora levaria um
            # arquivo qualquer do computador para dentro do EPUB (revisão).
            if arquivo.is_symlink():
                mensagem = f"{nome}: link simbólico na pasta do EPUB ({pasta}); não empacoto"
                raise EpubInvalidoError(mensagem)
            if arquivo.is_file() and nome != "mimetype" and nome not in fora:
                conteudo = substituicoes[nome] if nome in substituicoes else arquivo.read_bytes()
                zip_.writestr(nome, conteudo)
        # A troca que não achou o arquivo deixaria o capítulo cru, sem aviso (A5 da auditoria).
        if sobrando := sorted(set(substituicoes) - set(zip_.namelist())):
            mensagem = f"{pasta}: sem arquivo para trocar: {', '.join(sobrando)}"
            raise EpubInvalidoError(mensagem)

    gravar_pacote(destino, escrever)
