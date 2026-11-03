# SPDX-License-Identifier: GPL-3.0-or-later
"""Lê o PDF com o pdfminer.six e devolve páginas do domínio (ADR-0004).

É o único módulo que importa a biblioteca de PDF.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from statistics import multimode

from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTChar, LTPage, LTTextBox, LTTextLine
from pdfminer.pdfdocument import PDFDocument, PDFEncryptionError
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import PDFObjRef
from pdfminer.utils import decode_text

from earbook.dominio.pagina import Letra, Linha, Pagina, juntar_letras_espacadas
from earbook.dominio.segmento import normalizar_espacos

# Medido no spike: o código do "Hard Parts" vem em UbuntuMono.
_FONTE_MONOESPACADA = re.compile(r"mono|courier|code|consol", re.IGNORECASE)
# O estilo vem depois do traço ou da vírgula do nome: "SourceSans3-SemiboldIt" (Competente),
# "MyriadPro-SemiboldCond" (Hard Parts), "Arial,Bold". Sem o separador, "Blackadder" seria
# negrito. ADR-0004, "Subtítulo em negrito do tamanho do corpo".
_FONTE_NEGRITO = re.compile(r"[-,]\w*(?:bold|black|heavy|demi)", re.IGNORECASE)


_BOM_UTF8 = b"\xef\xbb\xbf"
_BOM_UTF16LE = b"\xff\xfe"


class PdfInvalidoError(ValueError):
    pass


@dataclass(frozen=True)
class MetadadosDoPdf:
    titulo: str
    autor: str


def ler_metadados(pdf: Path) -> MetadadosDoPdf:
    """Título e autor do dicionário `/Info` do PDF, vazios quando ele não os tem.

    O valor vem cru do PDF (texto em PDFDocEncoding, UTF-16 ou UTF-8, ou referência a outro
    objeto): só texto passa, e o resto vira vazio.
    """
    with pdf.open("rb") as arquivo:
        info = _pelo_pdfminer(pdf, lambda: _info(PDFDocument(PDFParser(arquivo))))
        titulo = _pelo_pdfminer(pdf, lambda: _bytes_do_info(info, "Title"))
        autor = _pelo_pdfminer(pdf, lambda: _bytes_do_info(info, "Author"))
    # Fora do `try`: a decodificação é nossa, e bug nosso não é PDF inválido (N2 da
    # pós-auditoria).
    return MetadadosDoPdf(_decodificar(titulo), _decodificar(autor))


def _info(documento: PDFDocument) -> list[dict[str, object]]:
    return documento.info  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]  # motivo: o pdfminer não tipa o `info`; cada valor é validado em `_texto_do_info`


def _bytes_do_info(info: list[dict[str, object]], chave: str) -> bytes:
    """O valor cru de `chave`, seguindo uma referência só: o `resolve1` do pdfminer segue
    sem limite, e um objeto que aponta para si mesmo travava o importar-pdf (N1 da
    pós-auditoria). Referência de referência, ou o que não é texto, vira vazio."""
    for dicionario in info:
        valor = dicionario.get(chave)
        if isinstance(valor, PDFObjRef):
            valor = valor.resolve()  # pyright: ignore[reportAny]  # motivo: o pdfminer devolve Any; o isinstance a seguir valida
        if isinstance(valor, bytes):
            return valor
    return b""


def _decodificar(valor: bytes) -> str:
    """O texto do `/Info`: PDFDocEncoding ou UTF-16BE com BOM, pelo pdfminer; UTF-8 com BOM,
    que o PDF 2.0 aceita (revisão); e UTF-16LE com BOM, fora da especificação mas visto
    (A3 da auditoria). O `decode_text` do pdfminer só conhece o UTF-16BE."""
    for bom, codificacao in ((_BOM_UTF8, "utf-8"), (_BOM_UTF16LE, "utf-16-le")):
        if valor.startswith(bom):
            return valor[len(bom) :].decode(codificacao, errors="replace")
    return decode_text(valor)


def ler_paginas(pdf: Path) -> tuple[Pagina, ...]:
    """Uma `Pagina` por página do PDF, com as linhas de texto na ordem do pdfminer.

    Converte uma página por vez: guardar todos os layouts do pdfminer levava o
    Competente (503 páginas) a 720 MB de memória (A3 da auditoria).
    """
    # O arquivo abre fora do `try`: arquivo inexistente é OSError da máquina, enquanto o
    # OSError de dentro da leitura vem do conteúdo (F2: xref com deslocamento negativo).
    with pdf.open("rb") as arquivo:
        layouts = extract_pages(arquivo, laparams=LAParams())
        paginas: list[Pagina] = []
        while (layout := _proximo_layout(pdf, layouts)) is not None:
            paginas.append(_pagina(pdf, len(paginas) + 1, layout))
    return tuple(paginas)


def _proximo_layout(pdf: Path, layouts: Iterator[LTPage]) -> LTPage | None:
    return _pelo_pdfminer(pdf, lambda: next(layouts, None))


def _pelo_pdfminer[T](pdf: Path, chamada: Callable[[], T]) -> T:
    """`chamada()`, com toda falha do pdfminer virando `PdfInvalidoError`.

    O `try` cobre só a biblioteca, não a nossa conversão: bug do adaptador continua
    aparecendo como bug, não como "PDF inválido" (revisão nº 1). Falta de memória é da
    máquina, não do PDF, e passa como veio.
    """
    try:
        return chamada()
    except MemoryError:
        raise
    except PDFEncryptionError as erro:
        mensagem = f"{pdf}: PDF protegido por senha ({type(erro).__name__})"
        raise PdfInvalidoError(mensagem) from erro
    # PDF é entrada hostil, e o pdfminer deixa escapar qualquer exceção (A2 e P1:
    # RecursionError, AttributeError, TypeError...). O `from` guarda a causa.
    except Exception as erro:
        mensagem = f"{pdf}: não é um PDF válido ({type(erro).__name__}: {erro})"
        raise PdfInvalidoError(mensagem) from erro


def _pagina(pdf: Path, numero: int, layout: LTPage) -> Pagina:
    if layout.height <= 0:
        mensagem = f"{pdf}: a página {numero} tem altura {layout.height}"
        raise PdfInvalidoError(mensagem)
    linhas = [
        _linha(linha, layout.height)
        for caixa in layout
        # LTTextBox é tipado como contêiner de LTTextLine; o LTTextContainer genérico não.
        if isinstance(caixa, LTTextBox)
        for linha in caixa
    ]
    return Pagina(numero, tuple(linha for linha in linhas if linha is not None))


def _linha(linha: LTTextLine, altura: float) -> Linha | None:
    caracteres = [c for c in linha if isinstance(c, LTChar)]
    texto = normalizar_espacos(linha.get_text())
    if not caracteres or not texto:
        return None
    # A moda, não a média: nome de código em 8,5 pt numa linha de 9 pt puxava a média
    # para baixo de 0,85 do corpo, e a prosa virava nota (A1 da auditoria, Hard Parts).
    # No empate, o maior: a letra menor é a do código ou da nota (pós-revisão).
    tamanho = max(multimode(round(c.size, 1) for c in caracteres))
    # Toda letra, não alguma: no Hard Parts, as 584 linhas de código são 100% monoespaçadas
    # e as 183 de prosa com um nome de código no meio ("ss.survey") ficam entre 0 e 90%.
    monoespacada = all(_fonte_casa(_FONTE_MONOESPACADA, c.fontname) for c in caracteres)
    visiveis = [c for c in caracteres if c.get_text().strip()]
    if not monoespacada:
        letras = [Letra(c.get_text(), c.x0, c.x1) for c in visiveis]
        texto = juntar_letras_espacadas(letras, tamanho) or texto
    # Toda letra visível, como na monoespaçada: a ênfase no meio da prosa (619 linhas no
    # Competente) não faz a linha negrito.
    negrito = all(_fonte_casa(_FONTE_NEGRITO, c.fontname) for c in visiveis)
    return Linha(
        texto,
        x=linha.x0,
        topo=1 - linha.y1 / altura,
        tamanho=tamanho,
        monoespacada=monoespacada,
        negrito=negrito,
        fim=linha.x1,
    )


def _fonte_casa(padrao: re.Pattern[str], nome_da_fonte: object) -> bool:
    """O pdfminer entrega o nome cru quando ele não é nome PDF: bytes ou número (F1)."""
    return isinstance(nome_da_fonte, str) and padrao.search(nome_da_fonte) is not None
