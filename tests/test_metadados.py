# SPDX-License-Identifier: GPL-3.0-or-later
"""Título e autor do livro que vem do PDF (ADR-0004)."""

from __future__ import annotations

import pytest

from earbook.dominio.metadados import autor_do_livro, titulo_do_livro


def test_titulo_do_metadado_vale_quando_parece_titulo() -> None:
    # Os dois PDFs medidos trazem o título certo no metadado: "Competente o Suficiente".
    assert titulo_do_livro("  Competente o  Suficiente ", "Competente-o-Suficiente-ebook") == (
        "Competente o Suficiente"
    )


@pytest.mark.parametrize(
    "metadado",
    ["", "   ", "Microsoft Word - cap1.doc", "livro.pdf", "Untitled", "Sem título", "Documento1"],
)
def test_titulo_que_parece_nome_de_arquivo_cede_ao_nome_do_pdf(metadado: str) -> None:
    assert (
        titulo_do_livro(metadado, "Competente-o-Suficiente-ebook")
        == "Competente-o-Suficiente-ebook"
    )


def test_autores_separados_por_ponto_e_virgula_saem_arrumados() -> None:
    # Hard Parts: "Ford, Neal;Richards, Mark;Sadalage, Pramod;Dehghani, Zhamak;"
    metadado = "Ford, Neal;Richards, Mark;Sadalage, Pramod;Dehghani, Zhamak;"
    assert autor_do_livro(metadado) == (
        "Ford, Neal; Richards, Mark; Sadalage, Pramod; Dehghani, Zhamak"
    )


@pytest.mark.parametrize("metadado", ["", "Administrator", "user", "Usuário"])
def test_autor_que_e_nome_de_maquina_fica_vazio(metadado: str) -> None:
    assert autor_do_livro(metadado) == ""


def test_titulo_que_comeca_com_untitled_vale() -> None:
    assert titulo_do_livro("Untitled: Notes on Art", "arquivo") == "Untitled: Notes on Art"


def test_titulo_so_com_caractere_de_controle_cede_ao_nome_do_pdf() -> None:
    # A3 da auditoria: "\\x00\\x00" passava por título e virava `dc:title` vazio.
    assert titulo_do_livro("\x00\x00", "arquivo") == "arquivo"
    assert autor_do_livro("\x00") == ""


def test_titulo_sobre_produto_microsoft_vale() -> None:
    # A4 da auditoria: só o padrão do editor ("Microsoft Word - ...") é nome de arquivo.
    assert titulo_do_livro("Microsoft Excel 2019 Bible", "arquivo") == "Microsoft Excel 2019 Bible"
    assert titulo_do_livro("Microsoft Word - Documento sem nome", "arquivo") == "arquivo"


def test_titulo_sem_letra_nem_algarismo_cede_ao_nome_do_pdf() -> None:
    # H1 da pós-auditoria: só caractere invisível (U+200B, U+FEFF) ou U+FFFD passava.
    assert titulo_do_livro("\u200b\ufeff", "arquivo") == "arquivo"
    assert titulo_do_livro("\ufffd\ufffd", "arquivo") == "arquivo"
    assert autor_do_livro("\u200b") == ""


def test_padrao_do_powerpoint_e_nome_de_arquivo() -> None:
    assert titulo_do_livro("Microsoft PowerPoint - apresentacao", "arquivo") == "arquivo"
