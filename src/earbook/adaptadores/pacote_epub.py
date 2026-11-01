# SPDX-License-Identifier: GPL-3.0-or-later
"""Extrai o EPUB (um zip) e lê do OPF os metadados e a ordem de leitura."""

from __future__ import annotations

import posixpath
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from lxml import etree

from earbook.adaptadores.xml_seguro import PARSER_SEGURO, Elemento
from earbook.dominio.trabalho import ItemIgnorado

CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
OPF = "http://www.idpf.org/2007/opf"
DC = "http://purl.org/dc/elements/1.1/"
# text/x-oeb1-document: XHTML do OEB 1, o formato antes do EPUB, ainda visto em livro antigo.
TIPOS_XHTML = frozenset({"application/xhtml+xml", "text/html", "text/x-oeb1-document"})
# Um EPUB de texto passa pouco de dezenas de MB; acima disso, é provável bomba de zip.
LIMITE_DESCOMPACTADO = 2 * 1024**3


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


def empacotar_pasta(pasta: Path, destino: Path, substituicoes: Mapping[str, bytes]) -> None:
    """Empacota o EPUB extraído em `pasta`, com `substituicoes` (caminho → conteúdo) no lugar."""

    def escrever(zip_: zipfile.ZipFile) -> None:
        for arquivo in sorted(pasta.rglob("*")):
            nome = arquivo.relative_to(pasta).as_posix()
            # A pasta é editada pelo agente e pela tradução: um link para fora levaria um
            # arquivo qualquer do computador para dentro do EPUB (revisão).
            if arquivo.is_symlink():
                mensagem = f"{nome}: link simbólico na pasta do EPUB ({pasta}); não empacoto"
                raise EpubInvalidoError(mensagem)
            if arquivo.is_file() and nome != "mimetype":
                conteudo = substituicoes[nome] if nome in substituicoes else arquivo.read_bytes()
                zip_.writestr(nome, conteudo)
        # A troca que não achou o arquivo deixaria o capítulo cru, sem aviso (A5 da auditoria).
        if sobrando := sorted(set(substituicoes) - set(zip_.namelist())):
            mensagem = f"{pasta}: sem arquivo para trocar: {', '.join(sobrando)}"
            raise EpubInvalidoError(mensagem)

    gravar_pacote(destino, escrever)
