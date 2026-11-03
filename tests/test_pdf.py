# SPDX-License-Identifier: GPL-3.0-or-later
"""Contrato do adaptador de PDF: o que o pdfminer.six entrega vira `Pagina` e `Linha`."""

from __future__ import annotations

import re
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from earbook.adaptadores.pdf import MetadadosDoPdf, PdfInvalidoError, ler_metadados, ler_paginas
from earbook.dominio.pagina import Linha, Pagina
from tests.pdf_de_teste import (
    LinhaDeTeste,
    montar_pdf,
    montar_pdf_com_arvore_funda,
    montar_pdf_com_nome_de_fonte,
    montar_pdf_com_senha,
    montar_pdf_com_titulo_circular,
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


def test_fim_da_linha_vem_do_pdf(tmp_path: Path) -> None:
    # "na pasta" em Helvetica 10,5: 3.836 milésimos de em, 40,3 pt a partir de x = 72.
    paginas = _ler(tmp_path, [LinhaDeTeste("na pasta", 72, 700)])
    assert [round(linha.fim, 1) for linha in _linhas(paginas)] == [112.3]


def test_fonte_monoespacada_e_marcada(tmp_path: Path) -> None:
    paginas = _ler(
        tmp_path,
        [LinhaDeTeste("Texto.", 72, 700), LinhaDeTeste("def f(): pass", 72, 660, mono=True)],
    )
    assert [linha.monoespacada for linha in _linhas(paginas)] == [False, True]


def test_codigo_no_meio_da_prosa_nao_faz_a_linha_monoespacada(tmp_path: Path) -> None:
    # Hard Parts: 183 linhas de prosa com um nome em fonte de código ("ss.survey") viravam
    # bloco de código e partiam o parágrafo; as 584 linhas de código são 100% monoespaçadas.
    # "na pasta " em Helvetica 10,5 mede 43,2 pt: o Courier começa colado, na mesma linha.
    paginas = _ler(
        tmp_path,
        [LinhaDeTeste("na pasta ", 72, 700), LinhaDeTeste("ss.order", 115.2, 700, mono=True)],
    )
    linhas = [(linha.texto, linha.monoespacada) for linha in _linhas(paginas)]
    assert linhas == [("na pasta ss.order", False)]


def test_fonte_negrito_e_marcada(tmp_path: Path) -> None:
    paginas = _ler(
        tmp_path,
        [
            LinhaDeTeste("Texto.", 72, 700),
            LinhaDeTeste("Pedaços de palavra", 72, 660, negrito=True),
        ],
    )
    assert [linha.negrito for linha in _linhas(paginas)] == [False, True]


@pytest.mark.parametrize(
    ("nome_da_fonte", "negrito"),
    [
        (b"/ABCDEF+SourceSans3-SemiboldIt", True),
        (b"/Arial,Bold", True),
        (b"/Blackadder", False),
        (b"/Helvetica", False),
    ],
    ids=["subconjunto", "virgula", "familia-black", "comum"],
)
def test_negrito_vem_do_estilo_depois_do_separador_do_nome(
    tmp_path: Path, nome_da_fonte: bytes, *, negrito: bool
) -> None:
    pdf = montar_pdf_com_nome_de_fonte(tmp_path / "fonte.pdf", nome_da_fonte)
    assert [linha.negrito for linha in _linhas(ler_paginas(pdf))] == [negrito]


def test_espaco_em_fonte_comum_entre_palavras_em_negrito_nao_desfaz_o_negrito(
    tmp_path: Path,
) -> None:
    # Auditoria: o negrito olha só as letras visíveis; o espaço entre palavras pode vir na
    # fonte comum. "Pedaços" em Helvetica-Bold 10,5 mede 43,19 pt; o espaço em Helvetica, 2,92.
    paginas = _ler(
        tmp_path,
        [
            LinhaDeTeste("Pedaços", 72, 700, negrito=True),
            LinhaDeTeste(" ", 115.19, 700),
            LinhaDeTeste("de palavra", 118.11, 700, negrito=True),
        ],
    )
    linhas = [(linha.texto, linha.negrito) for linha in _linhas(paginas)]
    assert linhas == [("Pedaços de palavra", True)]


def test_enfase_em_negrito_no_meio_da_prosa_nao_faz_a_linha_negrito(tmp_path: Path) -> None:
    # Competente: 619 linhas de prosa têm ênfase em negrito no meio; virariam título e
    # partiriam o parágrafo. "na pasta " em Helvetica 10,5 mede 43,2 pt.
    paginas = _ler(
        tmp_path,
        [LinhaDeTeste("na pasta ", 72, 700), LinhaDeTeste("certa", 115.2, 700, negrito=True)],
    )
    linhas = [(linha.texto, linha.negrito) for linha in _linhas(paginas)]
    assert linhas == [("na pasta certa", False)]


def test_tamanho_da_linha_e_o_da_maioria_das_letras(tmp_path: Path) -> None:
    # A1 da auditoria: no Hard Parts, a saga vem em 9 pt (corpo 10,5) e o nome de código em
    # 8,5 pt; a média caía abaixo de 0,85 do corpo, e a linha de prosa virava nota de rodapé
    # ("Addi-" + "removed" no parágrafo, "son created" na nota). "ss.survey " em Courier
    # 8,5 mede 51 pt: o Helvetica começa colado, na mesma linha.
    paginas = _ler(
        tmp_path,
        [
            LinhaDeTeste("ss.survey ", 72, 700, tamanho=8.5, mono=True),
            LinhaDeTeste("son created. Notice that", 123, 700, tamanho=9),
        ],
    )
    linhas = [(linha.texto, linha.tamanho) for linha in _linhas(paginas)]
    assert linhas == [("ss.survey son created. Notice that", 9.0)]


def test_empate_de_tamanho_fica_com_o_maior(tmp_path: Path) -> None:
    # Pós-revisão: com tantas letras de código (8,5 pt) quanto de prosa (9 pt), a moda
    # ficava com o tamanho que vinha primeiro, e a linha voltava a virar nota.
    paginas = _ler(
        tmp_path,
        [
            LinhaDeTeste("ss.survey ", 72, 700, tamanho=8.5, mono=True),
            LinhaDeTeste("son create", 123, 700, tamanho=9),
        ],
    )
    assert [linha.tamanho for linha in _linhas(paginas)] == [9.0]


def test_letra_espacada_sai_do_pdf_como_palavra(tmp_path: Path) -> None:
    # Escuta de 2026-11-01: o ElevenReader colou "P A R T E I" em "PARTEI" e leu "partei".
    # Larguras do Helvetica 8,5 pt (P 5,67, A 5,67, R 6,14, T 5,19, E 5,67), 1,4 pt entre
    # letras e 4,5 pt antes do "I", como no Competente p. 20. No livro, o fim da palavra
    # espaçada traz um glifo de espaço de verdade ("E "), que não é letra.
    letras = [("P", 100.0), ("A", 107.07), ("R", 114.14), ("T", 121.68), ("E ", 128.27)]
    linhas = [LinhaDeTeste(letra, x, 700, tamanho=8.5) for letra, x in letras]
    paginas = _ler(tmp_path, [*linhas, LinhaDeTeste("I", 138.44, 700, tamanho=8.5)])
    assert [linha.texto for linha in _linhas(paginas)] == ["PARTE I"]


def test_codigo_com_caracteres_soltos_nao_e_juntado(tmp_path: Path) -> None:
    # Em fonte monoespaçada o espaço tem a largura de uma letra: "1 2 3 4 5" passaria
    # por letra espaçada e viraria "12345".
    paginas = _ler(tmp_path, [LinhaDeTeste("a = 1 2 3 4 5", 72, 700, mono=True)])
    assert [linha.texto for linha in _linhas(paginas)] == ["a = 1 2 3 4 5"]


def test_prosa_com_numeros_soltos_sai_do_pdf_como_esta(tmp_path: Path) -> None:
    # F1 da auditoria: saía "Siga os passos 1234e5 da lista."
    paginas = _ler(tmp_path, [LinhaDeTeste("Siga os passos 1 2 3 4 e 5 da lista.", 72, 700)])
    assert [linha.texto for linha in _linhas(paginas)] == ["Siga os passos 1 2 3 4 e 5 da lista."]


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
    # Pelo padrão, e não pelo número do objeto: a fonte negrito empurrou a página de 6 para 7,
    # e a troca literal deixava de acontecer sem falhar.
    dados, trocas = re.subn(rb"/Kids \[\d+ 0 R\]", b"/Kids [foo]", pdf.read_bytes())
    assert trocas == 1
    _ = pdf.write_bytes(dados)
    with pytest.raises(PdfInvalidoError, match=r"filho\.pdf"):
        _ = ler_paginas(pdf)


def test_erro_da_propria_conversao_nao_vira_pdf_invalido(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Revisão nº 1: o except em volta de tudo mostrava bug do adaptador como PDF ruim.
    def moda_quebrada(_: object) -> float:
        mensagem = "bug plantado"
        raise TypeError(mensagem)

    monkeypatch.setattr("earbook.adaptadores.pdf.multimode", moda_quebrada)
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
    # TypeError, sem o nome do arquivo. Nome que não é texto não é monoespaçado nem negrito.
    pdf = montar_pdf_com_nome_de_fonte(tmp_path / "fonte.pdf", nome_da_fonte)
    linhas = _linhas(ler_paginas(pdf))
    resultado = [(linha.texto, linha.monoespacada, linha.negrito) for linha in linhas]
    assert resultado == [("Texto.", False, False)]


def test_xref_com_deslocamento_negativo_e_recusado_com_o_nome(tmp_path: Path) -> None:
    # F2 da pós-auditoria: o seek negativo dava OSError, que passava como "arquivo
    # inacessível" ("[Errno 22] Invalid argument"), sem o nome do arquivo.
    pdf = montar_pdf_com_xref_negativo(tmp_path / "xref.pdf")
    with pytest.raises(PdfInvalidoError, match=r"xref\.pdf"):
        _ = ler_paginas(pdf)


def test_metadado_de_titulo_e_autor_vem_do_pdf(tmp_path: Path) -> None:
    # "Ação" em UTF-16 com BOM, como o PDF guarda texto fora do Latin-1.
    info = {"Title": b"<FEFF004100E700E3006F>", "Author": b"(Fulana de Tal)"}
    pdf = montar_pdf(tmp_path / "livro.pdf", [[LinhaDeTeste("Texto.", 72, 700)]], info)
    assert ler_metadados(pdf) == MetadadosDoPdf("Ação", "Fulana de Tal")


def test_pdf_sem_metadado_devolve_vazio(tmp_path: Path) -> None:
    pdf = montar_pdf(tmp_path / "livro.pdf", [[LinhaDeTeste("Texto.", 72, 700)]])
    assert ler_metadados(pdf) == MetadadosDoPdf("", "")


def test_metadado_de_arquivo_que_nao_e_pdf_e_recusado_com_o_nome(tmp_path: Path) -> None:
    falso = tmp_path / "falso.pdf"
    _ = falso.write_bytes(b"isto nao e um pdf")
    with pytest.raises(PdfInvalidoError, match=r"falso\.pdf"):
        _ = ler_metadados(falso)


def test_metadado_em_utf8_com_bom_vem_certo(tmp_path: Path) -> None:
    # Revisão: o PDF 2.0 aceita UTF-8 com BOM, e o decode_text do pdfminer só conhece o
    # UTF-16; saía "ï»¿AÃ§Ã£o".
    info = {"Title": b"<EFBBBF41C3A7C3A36F>"}
    pdf = montar_pdf(tmp_path / "livro.pdf", [[LinhaDeTeste("Texto.", 72, 700)]], info)
    assert ler_metadados(pdf).titulo == "Ação"


def test_metadado_em_utf16_little_endian_com_bom_vem_certo(tmp_path: Path) -> None:
    # A3 da auditoria: fora da especificação, mas visto; saía "ÿþAção".
    info = {"Title": b"<FFFE4100E700E3006F00>"}
    pdf = montar_pdf(tmp_path / "livro.pdf", [[LinhaDeTeste("Texto.", 72, 700)]], info)
    assert ler_metadados(pdf).titulo == "Ação"


def test_metadado_que_nao_e_texto_vira_vazio(tmp_path: Path) -> None:
    info = {"Title": b"42", "Author": b"/Fulana"}
    pdf = montar_pdf(tmp_path / "livro.pdf", [[LinhaDeTeste("Texto.", 72, 700)]], info)
    assert ler_metadados(pdf) == MetadadosDoPdf("", "")


def test_titulo_que_aponta_para_si_mesmo_vira_vazio_sem_travar(tmp_path: Path) -> None:
    # N1 da pós-auditoria: o `resolve1` do pdfminer seguia a referência sem limite, e o
    # importar-pdf girava para sempre depois de ler todas as páginas.
    pdf = montar_pdf_com_titulo_circular(tmp_path / "circular.pdf")
    resultado: list[MetadadosDoPdf] = []
    leitura = threading.Thread(target=lambda: resultado.append(ler_metadados(pdf)), daemon=True)
    leitura.start()
    leitura.join(5)
    assert resultado == [MetadadosDoPdf("", "")]


def test_erro_da_nossa_decodificacao_nao_vira_pdf_invalido(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # N2 da pós-auditoria: o `try` do pdfminer cobria também a nossa decodificação.
    def decodificacao_quebrada(_: object) -> str:
        mensagem = "bug plantado"
        raise TypeError(mensagem)

    monkeypatch.setattr("earbook.adaptadores.pdf._decodificar", decodificacao_quebrada)
    pdf = montar_pdf(tmp_path / "livro.pdf", [[LinhaDeTeste("T.", 72, 700)]], {"Title": b"(T)"})
    with pytest.raises(TypeError, match="bug plantado"):
        _ = ler_metadados(pdf)


def test_utf16_little_endian_quebrado_nao_derruba_a_importacao(tmp_path: Path) -> None:
    pdf = montar_pdf(
        tmp_path / "livro.pdf", [[LinhaDeTeste("T.", 72, 700)]], {"Title": b"<FFFE4100E7>"}
    )
    assert ler_metadados(pdf).titulo.startswith("A")
