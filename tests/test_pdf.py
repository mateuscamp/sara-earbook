# SPDX-License-Identifier: GPL-3.0-or-later
"""Contrato do adaptador de PDF: o que o pdfminer.six entrega vira `Pagina` e `Linha`."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from earbook.adaptadores.pdf import PdfInvalidoError, ler_paginas
from earbook.dominio.pagina import Linha, Pagina
from tests.pdf_de_teste import (
    LinhaDeTeste,
    montar_pdf,
    montar_pdf_com_arvore_funda,
    montar_pdf_com_nome_de_fonte,
    montar_pdf_com_senha,
    montar_pdf_com_xref_negativo,
)


def _ler(tmp_path: Path, *paginas: list[LinhaDeTeste]) -> tuple[Pagina, ...]:
    return ler_paginas(montar_pdf(tmp_path / "livro.pdf", list(paginas)))


def test_le_uma_pagina_por_pagina_com_o_texto_de_cada_linha(tmp_path: Path) -> None:
    paginas = _ler(
        tmp_path,
        [LinhaDeTeste("Primeira linha.", 72, 700), LinhaDeTeste("Segunda linha.", 72, 680)],
        [LinhaDeTeste("Outra página.", 72, 700)],
    )
    assert [(p.numero, [linha.texto for linha in p.linhas]) for p in paginas] == [
        (1, ["Primeira linha.", "Segunda linha."]),
        (2, ["Outra página."]),
    ]


def _linhas(paginas: tuple[Pagina, ...]) -> list[Linha]:
    return [linha for pagina in paginas for linha in pagina.linhas]


def test_topo_vai_de_zero_no_alto_a_um_no_pe(tmp_path: Path) -> None:
    paginas = _ler(tmp_path, [LinhaDeTeste("12", 300, 770), LinhaDeTeste("Pé.", 72, 30)])
    faixas = [
        "alto" if linha.topo < 0.04 else "pé" if linha.topo > 0.94 else "meio"
        for linha in _linhas(paginas)
    ]
    assert faixas == ["alto", "pé"]


def test_x_e_tamanho_da_fonte_vem_do_pdf(tmp_path: Path) -> None:
    paginas = _ler(tmp_path, [LinhaDeTeste("Título", 90, 700, tamanho=19)])
    assert [(round(linha.x), round(linha.tamanho, 1)) for linha in _linhas(paginas)] == [(90, 19.0)]


def test_fonte_monoespacada_e_marcada(tmp_path: Path) -> None:
    paginas = _ler(
        tmp_path,
        [LinhaDeTeste("Texto.", 72, 700), LinhaDeTeste("def f(): pass", 72, 660, mono=True)],
    )
    assert [linha.monoespacada for linha in _linhas(paginas)] == [False, True]


def test_acento_do_portugues_chega_inteiro(tmp_path: Path) -> None:
    paginas = _ler(tmp_path, [LinhaDeTeste("Coração, ação e não.", 72, 700)])
    assert [linha.texto for linha in _linhas(paginas)] == ["Coração, ação e não."]


def test_arquivo_que_nao_e_pdf_e_recusado_com_o_nome(tmp_path: Path) -> None:
    falso = tmp_path / "falso.pdf"
    _ = falso.write_bytes(b"isto nao e um pdf")
    with pytest.raises(PdfInvalidoError, match=r"falso\.pdf"):
        _ = ler_paginas(falso)


def test_topo_e_o_alto_da_letra_nao_a_linha_de_base(tmp_path: Path) -> None:
    # Fonte de 40 pt com base em y=700: o alto da letra fica perto de 0,08, a base em 0,116.
    paginas = _ler(tmp_path, [LinhaDeTeste("Título", 72, 700, tamanho=40)])
    assert [linha.topo < 0.1 for linha in _linhas(paginas)] == [True]


def test_pagina_com_altura_zero_e_recusada(tmp_path: Path) -> None:
    # A2 da auditoria: dividia por zero no adaptador.
    pdf = montar_pdf(tmp_path / "achatado.pdf", [[LinhaDeTeste("Texto.", 72, 0)]])
    _ = pdf.write_bytes(pdf.read_bytes().replace(b"[0 0 612 792]", b"[0 0 612 000]"))
    with pytest.raises(PdfInvalidoError, match="altura"):
        _ = ler_paginas(pdf)


def test_arvore_de_paginas_funda_demais_e_recusada_com_o_nome(tmp_path: Path) -> None:
    # A2 da auditoria: o RecursionError do pdfminer escapava do erro do projeto.
    pdf = montar_pdf_com_arvore_funda(tmp_path / "fundo.pdf", 3000)
    with pytest.raises(PdfInvalidoError, match=r"fundo\.pdf"):
        _ = ler_paginas(pdf)


def test_pdf_com_senha_e_recusado_dizendo_que_tem_senha(tmp_path: Path) -> None:
    pdf = montar_pdf_com_senha(tmp_path / "trancado.pdf")
    # A frase exata: "senha" sozinha casaria com o caminho do tmp_path, que leva o nome do teste.
    with pytest.raises(PdfInvalidoError, match="protegido por senha"):
        _ = ler_paginas(pdf)


def test_arvore_com_filho_que_nao_e_objeto_e_recusada_com_o_nome(tmp_path: Path) -> None:
    # P1 da pós-auditoria: o AttributeError do pdfminer escapava do erro do projeto.
    pdf = montar_pdf(tmp_path / "filho.pdf", [[LinhaDeTeste("Texto.", 72, 700)]])
    _ = pdf.write_bytes(pdf.read_bytes().replace(b"/Kids [6 0 R]", b"/Kids [foo]"))
    with pytest.raises(PdfInvalidoError, match=r"filho\.pdf"):
        _ = ler_paginas(pdf)


def test_erro_da_propria_conversao_nao_vira_pdf_invalido(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Revisão nº 1: o except em volta de tudo mostrava bug do adaptador como PDF ruim.
    def media_quebrada(_: object) -> float:
        mensagem = "bug plantado"
        raise TypeError(mensagem)

    monkeypatch.setattr("earbook.adaptadores.pdf.mean", media_quebrada)
    pdf = montar_pdf(tmp_path / "bom.pdf", [[LinhaDeTeste("Texto.", 72, 700)]])
    with pytest.raises(TypeError, match="bug plantado"):
        _ = ler_paginas(pdf)


def test_falta_de_memoria_nao_vira_pdf_invalido(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Revisão nº 7: sem memória, o problema é da máquina, não do arquivo.
    # O pdfminer só lê ao pedir a próxima página: o falso estoura no next, não na chamada.
    def estoura(_: object) -> object:
        raise MemoryError

    def paginas_sem_memoria(*_args: object, **_opcoes: object) -> Iterator[object]:
        return map(estoura, [None])

    monkeypatch.setattr("earbook.adaptadores.pdf.extract_pages", paginas_sem_memoria)
    pdf = montar_pdf(tmp_path / "grande.pdf", [[LinhaDeTeste("Texto.", 72, 700)]])
    with pytest.raises(MemoryError):
        _ = ler_paginas(pdf)


def test_arquivo_que_nao_existe_continua_erro_de_arquivo(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _ = ler_paginas(tmp_path / "sumiu.pdf")


@pytest.mark.parametrize("nome_da_fonte", [b"(Courier)", b"5"], ids=["texto", "numero"])
def test_nome_de_fonte_malformado_nao_derruba_a_leitura(
    tmp_path: Path, nome_da_fonte: bytes
) -> None:
    # F1 da pós-auditoria: o pdfminer entrega bytes ou int no nome, e a regex quebrava com
    # TypeError, sem o nome do arquivo. Nome que não é texto não é monoespaçado.
    pdf = montar_pdf_com_nome_de_fonte(tmp_path / "fonte.pdf", nome_da_fonte)
    linhas = _linhas(ler_paginas(pdf))
    assert [(linha.texto, linha.monoespacada) for linha in linhas] == [("Texto.", False)]


def test_xref_com_deslocamento_negativo_e_recusado_com_o_nome(tmp_path: Path) -> None:
    # F2 da pós-auditoria: o seek negativo dava OSError, que passava como "arquivo
    # inacessível" ("[Errno 22] Invalid argument"), sem o nome do arquivo.
    pdf = montar_pdf_com_xref_negativo(tmp_path / "xref.pdf")
    with pytest.raises(PdfInvalidoError, match=r"xref\.pdf"):
        _ = ler_paginas(pdf)
