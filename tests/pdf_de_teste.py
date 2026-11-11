# SPDX-License-Identifier: GPL-3.0-or-later
"""Monta PDFs mínimos para os testes, em vez de guardar binário no repositório.

Usa as fontes padrão do PDF (Helvetica, Helvetica-Bold, Courier e Times-Roman, sem embutir) com
WinAnsiEncoding, que cobre os acentos do português. A página tem 612 x 792 pontos (carta).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

LARGURA = 612
ALTURA = 792


@dataclass(frozen=True)
class LinhaDeTeste:
    """Uma linha de texto na página. `y` é a linha de base, contada de baixo, em pontos."""

    texto: str
    x: float
    y: float
    tamanho: float = 10.5
    mono: bool = False
    negrito: bool = False
    versalete: bool = False
    """A inicial de cada palavra maior, como o versalete feito à mão do Dalgalarrondo (10,5 pt
    sobre 7,4)."""
    sobrescrito: bool = False
    """O trecho entre "^" sai sobrescrito e o entre "~", subscrito: a 0,58 do tamanho, com a linha
    de base 0,33 do tamanho acima ou abaixo, como o número de referência do Practical."""
    espacamento: float = 0.0
    """Pontos a mais depois de cada letra (o `Tc`), como o nome do autor do Practical. Com ele, o
    "|" no texto aperta o par de letras em 0,9 pt (o kerning de "AT" no Gotham-Bold)."""
    serifa: bool = False
    """Times-Roman, em vez da Helvetica: a outra família de letra da página."""
    inclinada: bool = False
    """A itálica feita pela matriz (`1 0 0.2 1`): inclina, mas não gira."""
    girada: bool = False
    """O texto de lado, subindo a página (a matriz `0 1 -1 0`), como a tabela deitada do Practical
    p. 73, que o pdfminer lê letra por letra."""


def _cadeia_pdf(texto: str) -> str:
    """Texto → literal de string do PDF, com os bytes fora do ASCII em octal."""
    partes: list[str] = []
    for byte in texto.encode("cp1252"):
        if byte in b"()\\":
            partes.append("\\" + chr(byte))
        elif 32 <= byte < 127:  # faixa do ASCII imprimível
            partes.append(chr(byte))
        else:
            partes.append(f"\\{byte:03o}")
    return "".join(partes)


def _fonte(linha: LinhaDeTeste) -> str:
    return "F2" if linha.mono else "F3" if linha.negrito else "F4" if linha.serifa else "F1"


_APERTO_DO_PAR = 90
_RAZAO_DO_SOBRESCRITO = 0.58
_SUBIDA_DO_SOBRESCRITO = 0.33


def _com_sobrescrito(linha: LinhaDeTeste) -> str:
    """Os trechos entre "^" sobem e os entre "~" descem, em letra menor."""
    fonte, tamanho = _fonte(linha), linha.tamanho
    menor = round(tamanho * _RAZAO_DO_SOBRESCRITO, 2)
    subida = round(tamanho * _SUBIDA_DO_SOBRESCRITO, 2)
    comandos: list[str] = []
    trecho, deslocamento = "", 0.0
    for caractere in linha.texto + "\0":
        if caractere in "^~\0":
            if trecho:
                letra = menor if deslocamento else tamanho
                comandos.append(f"/{fonte} {letra} Tf {deslocamento} Ts ({_cadeia_pdf(trecho)}) Tj")
            trecho = ""
            if caractere != "\0":
                alvo = subida if caractere == "^" else -subida
                deslocamento = 0.0 if deslocamento else alvo
        else:
            trecho += caractere
    return " ".join([*comandos, "0 Ts"])


def _texto(linha: LinhaDeTeste) -> str:
    """Os comandos que escrevem o texto: um só, ou um por trecho de tamanho no versalete."""
    espacamento = f"{linha.espacamento} Tc " if linha.espacamento else ""
    if linha.sobrescrito:
        return espacamento + _com_sobrescrito(linha)
    if linha.espacamento and "|" in linha.texto:
        pares = f" {_APERTO_DO_PAR} ".join(f"({_cadeia_pdf(p)})" for p in linha.texto.split("|"))
        return f"{espacamento}/{_fonte(linha)} {linha.tamanho} Tf [{pares}] TJ"
    if not linha.versalete:
        texto = f"/{_fonte(linha)} {linha.tamanho} Tf ({_cadeia_pdf(linha.texto)}) Tj"
        return espacamento + texto
    maior = round(linha.tamanho * 10.5 / 7.4, 1)
    trechos: list[str] = []
    for i, palavra in enumerate(linha.texto.split(" ")):
        inicial = (" " if i else "") + palavra[:1]
        trechos.append(f"/{_fonte(linha)} {maior} Tf ({_cadeia_pdf(inicial)}) Tj")
        trechos.append(f"/{_fonte(linha)} {linha.tamanho} Tf ({_cadeia_pdf(palavra[1:])}) Tj")
    return " ".join(trechos)


def _posicao(linha: LinhaDeTeste) -> str:
    if linha.girada:
        return f"0 1 -1 0 {linha.x} {linha.y} Tm"
    if linha.inclinada:
        return f"1 0 0.2 1 {linha.x} {linha.y} Tm"
    return f"{linha.x} {linha.y} Td"


def _conteudo(linhas: list[LinhaDeTeste]) -> bytes:
    comandos = [f"BT {_posicao(linha)} {_texto(linha)} ET" for linha in linhas]
    return "\n".join(comandos).encode("latin-1")


def montar_pdf(
    destino: Path, paginas: list[list[LinhaDeTeste]], info: dict[str, bytes] | None = None
) -> Path:
    """Grava em `destino` um PDF com uma página por lista de linhas.

    `info` é o dicionário de metadados, com cada valor já como string PDF: `b"(Título)"`
    ou, com acento, `b"<FEFF...>"` em UTF-16.
    """
    fonte = "<< /Type /Font /Subtype /Type1 /BaseFont /{} /Encoding /WinAnsiEncoding >>"
    objetos: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # a árvore de páginas entra depois, quando os números das páginas existem
        fonte.format("Helvetica").encode(),
        fonte.format("Courier").encode(),
        fonte.format("Helvetica-Bold").encode(),
        fonte.format("Times-Roman").encode(),
    ]
    filhos: list[str] = []
    for linhas in paginas:
        conteudo = _conteudo(linhas)
        objetos.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(conteudo), conteudo))
        recursos = "<< /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R /F4 6 0 R >> >>"
        objetos.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {LARGURA} {ALTURA}] "
                f"/Resources {recursos} /Contents {len(objetos)} 0 R >>"
            ).encode()
        )
        filhos.append(f"{len(objetos)} 0 R")
    objetos[1] = f"<< /Type /Pages /Kids [{' '.join(filhos)}] /Count {len(filhos)} >>".encode()
    if info is not None:
        objetos.append(
            b"<< " + b" ".join(b"/%s %s" % (k.encode(), v) for k, v in info.items()) + b" >>"
        )
    _ = destino.write_bytes(_arquivo(objetos, info_no=len(objetos) if info is not None else None))
    return destino


def _arquivo(objetos: list[bytes], info_no: int | None = None) -> bytes:
    corpo = bytearray(b"%PDF-1.4\n")
    posicoes: list[int] = []
    for numero, objeto in enumerate(objetos, 1):
        posicoes.append(len(corpo))
        corpo += b"%d 0 obj\n%s\nendobj\n" % (numero, objeto)
    inicio_da_tabela = len(corpo)
    corpo += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    corpo += b"".join(b"%010d 00000 n \n" % posicao for posicao in posicoes)
    info = b" /Info %d 0 R" % info_no if info_no is not None else b""
    corpo += b"trailer\n<< /Size %d /Root 1 0 R%s >>\n" % (len(objetos) + 1, info)
    corpo += b"startxref\n%d\n%%%%EOF\n" % inicio_da_tabela
    return bytes(corpo)


def montar_pdf_com_arvore_funda(destino: Path, niveis: int) -> Path:
    """Uma página só, embaixo de `niveis` nós de páginas aninhados (o pdfminer desce recursivo)."""
    fonte = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    conteudo = _conteudo([LinhaDeTeste("Fundo.", 72, 700)])
    objetos: list[bytes] = [
        b"<< /Type /Catalog /Pages 3 0 R >>",
        fonte.encode(),
        *(f"<< /Type /Pages /Kids [{n + 4} 0 R] /Count 1 >>".encode() for n in range(niveis)),
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(conteudo), conteudo),
    ]
    pagina = (
        f"<< /Type /Page /MediaBox [0 0 {LARGURA} {ALTURA}] "
        f"/Resources << /Font << /F1 2 0 R >> >> /Contents {len(objetos)} 0 R >>"
    )
    objetos.append(pagina.encode())
    _ = destino.write_bytes(_arquivo(objetos))
    return destino


def montar_pdf_com_senha(destino: Path) -> Path:
    """PDF com criptografia padrão cuja senha não é a vazia: o pdfminer recusa."""
    _ = montar_pdf(destino, [[LinhaDeTeste("Segredo.", 72, 700)]])
    dados = destino.read_bytes()
    cifra = (
        b"<< /Filter /Standard /V 1 /R 2 /O <" + b"ab" * 32 + b"> /U <" + b"cd" * 32 + b"> /P -4 >>"
    )
    trailer = b"/Root 1 0 R"
    novo = trailer + b" /Encrypt " + cifra + b" /ID [<" + b"01" * 16 + b"> <" + b"01" * 16 + b">]"
    _ = destino.write_bytes(dados.replace(trailer, novo, 1))
    return destino


_HELVETICA = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"


def montar_pdf_com_nome_de_fonte(
    destino: Path, nome_da_fonte: bytes, linhas: list[LinhaDeTeste] | None = None
) -> Path:
    """Fonte fora das 14 padrão, cujo /FontName no descritor é `nome_da_fonte` cru.

    Nome PDF é `/Courier`; `(Courier)` (texto) e `5` (número) são malformados, e o
    pdfminer os entrega sem converter em `str`. A fonte troca a Helvetica: as `linhas` em
    negrito (Helvetica-Bold) continuam na fonte padrão.
    """
    _ = montar_pdf(destino, [linhas or [LinhaDeTeste("Texto.", 72, 700)]])
    larguras = b"/FirstChar 32 /LastChar 126 /Widths [" + b" ".join([b"600"] * 95) + b"]"
    descritor = (
        b"<< /Type /FontDescriptor /FontName " + nome_da_fonte
        + b" /Flags 32 /FontBBox [0 -200 600 800] /Ascent 800 /Descent -200 >>"
    )  # fmt: skip
    fonte = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Estranha /Encoding /WinAnsiEncoding "
        + larguras + b" /FontDescriptor " + descritor + b" >>"
    )  # fmt: skip
    _ = destino.write_bytes(destino.read_bytes().replace(_HELVETICA, fonte, 1))
    return destino


def montar_pdf_com_xref_negativo(destino: Path) -> Path:
    """O primeiro objeto da tabela xref aponta para um deslocamento negativo."""
    dados = montar_pdf(destino, [[LinhaDeTeste("Texto.", 72, 700)]]).read_bytes()
    inicio = dados.index(b"0000000000 65535 f \n") + len(b"0000000000 65535 f \n")
    _ = destino.write_bytes(dados[:inicio] + b"-000000005" + dados[inicio + 10 :])
    return destino


def montar_pdf_com_titulo_circular(destino: Path) -> Path:
    """Uma página e o `/Title` apontando para um objeto que aponta para si mesmo."""
    fonte = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    conteudo = _conteudo([LinhaDeTeste("Texto.", 72, 700)])
    objetos: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [5 0 R] /Count 1 >>",
        fonte.encode(),
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(conteudo), conteudo),
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {LARGURA} {ALTURA}] "
            "/Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>"
        ).encode(),
        b"6 0 R",
        b"<< /Title 6 0 R >>",
    ]
    _ = destino.write_bytes(_arquivo(objetos, info_no=7))
    return destino
