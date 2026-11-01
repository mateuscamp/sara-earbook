# SPDX-License-Identifier: GPL-3.0-or-later
"""Monta PDFs mínimos para os testes, em vez de guardar binário no repositório.

Usa as fontes padrão do PDF (Helvetica e Courier, sem embutir) com WinAnsiEncoding,
que cobre os acentos do português. A página tem 612 x 792 pontos (carta).
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


def _conteudo(linhas: list[LinhaDeTeste]) -> bytes:
    comandos = [
        (
            f"BT /{'F2' if linha.mono else 'F1'} {linha.tamanho} Tf {linha.x} {linha.y} Td "
            f"({_cadeia_pdf(linha.texto)}) Tj ET"
        )
        for linha in linhas
    ]
    return "\n".join(comandos).encode("latin-1")


def montar_pdf(destino: Path, paginas: list[list[LinhaDeTeste]]) -> Path:
    """Grava em `destino` um PDF com uma página por lista de linhas."""
    fonte = "<< /Type /Font /Subtype /Type1 /BaseFont /{} /Encoding /WinAnsiEncoding >>"
    objetos: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # a árvore de páginas entra depois, quando os números das páginas existem
        fonte.format("Helvetica").encode(),
        fonte.format("Courier").encode(),
    ]
    filhos: list[str] = []
    for linhas in paginas:
        conteudo = _conteudo(linhas)
        objetos.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(conteudo), conteudo))
        recursos = "<< /Font << /F1 3 0 R /F2 4 0 R >> >>"
        objetos.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {LARGURA} {ALTURA}] "
                f"/Resources {recursos} /Contents {len(objetos)} 0 R >>"
            ).encode()
        )
        filhos.append(f"{len(objetos)} 0 R")
    objetos[1] = f"<< /Type /Pages /Kids [{' '.join(filhos)}] /Count {len(filhos)} >>".encode()
    _ = destino.write_bytes(_arquivo(objetos))
    return destino


def _arquivo(objetos: list[bytes]) -> bytes:
    corpo = bytearray(b"%PDF-1.4\n")
    posicoes: list[int] = []
    for numero, objeto in enumerate(objetos, 1):
        posicoes.append(len(corpo))
        corpo += b"%d 0 obj\n%s\nendobj\n" % (numero, objeto)
    inicio_da_tabela = len(corpo)
    corpo += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    corpo += b"".join(b"%010d 00000 n \n" % posicao for posicao in posicoes)
    corpo += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objetos) + 1)
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
