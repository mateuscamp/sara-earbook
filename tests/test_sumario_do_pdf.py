# SPDX-License-Identifier: GPL-3.0-or-later
"""O adaptador lê o sumário interno do PDF, e o `importar-pdf` corta os capítulos por ele
(ADR-0004, "Capítulos pelo sumário interno do PDF").

O sumário é entrada não confiável: o que não se deixa ler vira sumário vazio, e a importação
segue pela regra do tamanho e do rótulo.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

import pytest

from earbook.adaptadores.pdf import ler_sumario
from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.sumario_interno import ItemDoSumario
from tests.pdf_de_teste import ItemDeTeste, LinhaDeTeste, montar_pdf, montar_pdf_com_sumario

PAGINAS = 4


def _paginas(n: int = PAGINAS) -> list[list[LinhaDeTeste]]:
    return [[LinhaDeTeste(f"Texto da página {k}.", 72, 700)] for k in range(1, n + 1)]


def test_sumario_interno_vem_com_nivel_titulo_e_pagina(tmp_path: Path) -> None:
    itens = [
        ItemDeTeste(1, "Parte I - História", 1),
        ItemDeTeste(2, "Capítulo 1. A história", 2),
        ItemDeTeste(2, "Capítulo 2. O ensino", 3, por_acao=True),
        ItemDeTeste(1, "Anexo 1", 4),
    ]
    pdf = montar_pdf_com_sumario(tmp_path / "livro.pdf", _paginas(), itens)
    assert ler_sumario(pdf) == (
        ItemDoSumario(1, "Parte I - História", 1),
        ItemDoSumario(2, "Capítulo 1. A história", 2),
        ItemDoSumario(2, "Capítulo 2. O ensino", 3),
        ItemDoSumario(1, "Anexo 1", 4),
    )


def test_destino_com_nome_e_resolvido_e_o_que_nao_existe_fica_de_fora(tmp_path: Path) -> None:
    itens = [
        ItemDeTeste(1, "Capítulo 1", destino=b"(cap1)", por_acao=True),
        ItemDeTeste(1, "Capítulo 2", destino=b"(nao-existe)"),
        ItemDeTeste(1, "Capítulo 3", destino=b"(cap3)"),
    ]
    pdf = montar_pdf_com_sumario(
        tmp_path / "livro.pdf", _paginas(), itens, nomes={"cap1": 2, "cap3": 4}
    )
    assert ler_sumario(pdf) == (
        ItemDoSumario(1, "Capítulo 1", 2),
        ItemDoSumario(1, "Capítulo 3", 4),
    )


def test_pdf_sem_sumario_interno_devolve_vazio_sem_aviso(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    pdf = montar_pdf(tmp_path / "livro.pdf", _paginas())
    with caplog.at_level(logging.WARNING):
        assert ler_sumario(pdf) == ()
    assert caplog.records == []


def test_sumario_em_circulo_acaba_onde_o_circulo_fecha(tmp_path: Path) -> None:
    itens = [ItemDeTeste(1, f"Capítulo {n}", n, em_circulo=n == PAGINAS - 1) for n in (1, 2, 3)]
    pdf = montar_pdf_com_sumario(tmp_path / "livro.pdf", _paginas(), itens)
    assert ler_sumario(pdf) == tuple(ItemDoSumario(1, f"Capítulo {n}", n) for n in (1, 2, 3))


def test_sumario_plano_com_mais_de_mil_itens_e_lido_inteiro(tmp_path: Path) -> None:
    # Bonica: 991 itens irmãos estouravam a recursão do `get_outlines` do pdfminer, que desce um
    # nível por irmão.
    itens = [ItemDeTeste(1, f"Seção {n}", 1 + n % PAGINAS) for n in range(1200)]
    pdf = montar_pdf_com_sumario(tmp_path / "livro.pdf", _paginas(), itens)
    lidos = ler_sumario(pdf)
    assert len(lidos) == 1200
    assert lidos[-1] == ItemDoSumario(1, "Seção 1199", 4)


def test_sumario_que_aponta_para_si_mesmo_nao_trava(tmp_path: Path) -> None:
    # Achado da code-audit: `/Outlines 15 0 R`, e o objeto 15 é "15 0 R". As páginas desse PDF
    # se leem; o `get_outlines` do pdfminer, que segue referência sem limite, não voltava.
    pdf = montar_pdf_com_sumario(tmp_path / "livro.pdf", _paginas(), [], objeto_a_mais=b"15 0 R")
    assert ler_sumario(pdf) == ()


def test_arvore_de_nomes_que_aponta_para_si_mesma_nao_trava(tmp_path: Path) -> None:
    # Os itens são os objetos 16 e 17, e o objeto a mais é o 18: um nó da árvore de nomes cujo
    # filho é ele mesmo.
    itens = [ItemDeTeste(1, "Capítulo 1", destino=b"(cap1)"), ItemDeTeste(1, "Capítulo 2", 2)]
    pdf = montar_pdf_com_sumario(
        tmp_path / "livro.pdf",
        _paginas(),
        itens,
        nomes=b"18 0 R",
        objeto_a_mais=b"<< /Kids [18 0 R] >>",
    )
    assert ler_sumario(pdf) == (ItemDoSumario(1, "Capítulo 2", 2),)


def test_arquivo_que_nao_e_pdf_devolve_sumario_vazio_com_aviso(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    pdf = tmp_path / "livro.pdf"
    _ = pdf.write_bytes(b"isto nao e um PDF")
    with caplog.at_level(logging.WARNING):
        assert ler_sumario(pdf) == ()
    assert "livro.pdf" in caplog.text
    assert "sumário interno" in caplog.text


def test_destino_que_nao_leva_a_uma_pagina_fica_de_fora(tmp_path: Path) -> None:
    # Com 4 páginas, a raiz do sumário é o objeto 15, os itens são o 16, o 17, o 18 e o 19, e o
    # objeto a mais é o 20, uma referência a si mesmo: seguir sem limite não acabaria nunca.
    itens = [
        ItemDeTeste(1, "Capítulo 1", 1),
        ItemDeTeste(1, "Capítulo 2", destino=b"20 0 R"),
        ItemDeTeste(1, "Capítulo 3", destino=b"99 0 R"),
        ItemDeTeste(1, "Capítulo 4", 4),
    ]
    pdf = montar_pdf_com_sumario(tmp_path / "livro.pdf", _paginas(), itens, objeto_a_mais=b"20 0 R")
    assert ler_sumario(pdf) == (
        ItemDoSumario(1, "Capítulo 1", 1),
        ItemDoSumario(1, "Capítulo 4", 4),
    )


def _livro(itens: list[ItemDeTeste], tmp_path: Path) -> Path:
    """Três capítulos que abrem no número (30 pt), com um resto de figura de 80 pt em 3 páginas e
    um gabarito que repete "Capítulo N" em 3 páginas: pelo tamanho e pelo rótulo, sairia errado."""
    paginas: list[list[LinhaDeTeste]] = [[LinhaDeTeste("Prefácio do livro de teste.", 72, 600)]]
    for n in (1, 2, 3):
        paginas.append(
            [
                LinhaDeTeste(f"{n}.", 72, 720, tamanho=30),
                LinhaDeTeste(f"O texto do capítulo {n} começa aqui.", 72, 600),
            ]
        )
        paginas.append(
            [
                LinhaDeTeste("o", 300, 700, tamanho=80),
                LinhaDeTeste(f"O texto do capítulo {n} continua.", 72, 600),
            ]
        )
    paginas.append([LinhaDeTeste("Anexo", 72, 720, tamanho=30)])
    paginas += [
        [
            LinhaDeTeste(f"Capítulo {n}", 72, 720, tamanho=16),
            LinhaDeTeste(f"A resposta da questão {n} é a primeira.", 72, 600),
        ]
        for n in (1, 2, 3)
    ]
    return montar_pdf_com_sumario(tmp_path / "livro.pdf", paginas, itens)


def _sumario_do_epub(epub: Path) -> list[str]:
    with zipfile.ZipFile(epub) as zip_:
        nav = zip_.read("OEBPS/nav.xhtml").decode()
    return [parte.split("</a>")[0] for parte in nav.split('.xhtml">')[1:]]


def test_importar_pdf_corta_os_capitulos_pelo_sumario_interno(tmp_path: Path) -> None:
    itens = [
        ItemDeTeste(1, "Prefácio", 1),
        ItemDeTeste(1, "Parte I - Fundamentos", 2),
        *[ItemDeTeste(2, f"Capítulo {n}. Tema {n}", 2 * n) for n in (1, 2, 3)],
        ItemDeTeste(1, "Anexo 1. Respostas", 8),
    ]
    epub = tmp_path / "livro.epub"
    importacao = importar_pdf(_livro(itens, tmp_path), epub, idioma="pt-BR")
    assert importacao.capitulos == 5
    assert _sumario_do_epub(epub) == [
        "Prefácio",
        "Capítulo 1. Tema 1",
        "Capítulo 2. Tema 2",
        "Capítulo 3. Tema 3",
        "Anexo 1. Respostas",
    ]


def test_importar_pdf_com_sumario_que_nao_serve_corta_como_antes(tmp_path: Path) -> None:
    sem_rotulo = [ItemDeTeste(1, f"{n} Tema {n}", 2 * n) for n in (1, 2, 3)]
    com_sumario = importar_pdf(_livro(sem_rotulo, tmp_path), tmp_path / "a.epub", idioma="pt-BR")
    pdf = montar_pdf(tmp_path / "sem.pdf", _paginas())
    assert com_sumario.capitulos != 5
    assert importar_pdf(pdf, tmp_path / "b.epub", idioma="pt-BR").capitulos == 1
