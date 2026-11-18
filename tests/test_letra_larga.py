# SPDX-License-Identifier: GPL-3.0-or-later
"""O espaço que o pdfminer inventa depois da letra que o PDF desenha mais larga do que declara
(ADR-0004, "Romance convertido pelo Calibre").

No Kafka à beira-mar (PDF do Calibre), o Q do negrito avança 1,33 pt além da largura que a fonte
declara, e o y do regular, 0,75 pt, em toda ocorrência: o pdfminer põe espaço onde o PDF não tem
("Q uando", "SQ -118", "Toy ama", "Ky oto"). Na linha, o vão do Q passa às vezes do espaço de
verdade mais estreito; no livro inteiro, ele é sempre o mesmo, e isso o prova.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from earbook.adaptadores.pdf import ler_paginas
from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.letra_larga import tirar_espacos_da_letra_larga
from earbook.dominio.pagina import EspacoInventado, Linha, Pagina
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf

NEGRITO = "TimesNewRomanPS-BoldMT"


def _linha(texto: str, *espacos: tuple[str, float], tamanho: float = 6.0) -> Linha:
    """A linha com um espaço inventado depois de cada letra dada, na ordem em que aparecem; o
    Kafka tem o corpo em 6 pt."""
    inventados: list[EspacoInventado] = []
    inicio = 0
    for letra, vao in espacos:
        posicao = texto.index(letra + " ", inicio) + len(letra)
        inventados.append(EspacoInventado(posicao, letra, NEGRITO, vao))
        inicio = posicao
    return Linha(
        texto, x=25, fim=227, topo=0.5, tamanho=tamanho, espacos_inventados=tuple(inventados)
    )


def _textos(paginas: tuple[Pagina, ...]) -> list[str]:
    return [linha.texto for pagina in paginas for linha in pagina.linhas]


def test_espaco_depois_da_letra_larga_sai_em_todo_o_livro() -> None:
    linhas = [
        _linha("— Q uantos alunos estavam sob seus cuidados?", ("Q", 1.33)),
        _linha("— Q uer dizer então que, depois disso, as crianças", ("Q", 1.33)),
        _linha("são de número PTYX-722-SQ -118 a 122.", ("Q", 1.33)),
        _linha("no Q uartel- General do Comando Superior", ("Q", 1.33)),
        _linha("— Q ue aconteceu depois? E a série B da escola?", ("Q", 1.33)),
    ]
    feitas = tirar_espacos_da_letra_larga([Pagina(1, tuple(linhas))])
    assert _textos(feitas.paginas) == [
        "— Quantos alunos estavam sob seus cuidados?",
        "— Quer dizer então que, depois disso, as crianças",
        "são de número PTYX-722-SQ-118 a 122.",
        "no Quartel- General do Comando Superior",
        "— Que aconteceu depois? E a série B da escola?",
    ]
    assert feitas.tirados == 5


def test_letra_com_poucas_ocorrencias_nao_prova_nada() -> None:
    linhas = (_linha("— Q uantos alunos?", ("Q", 1.33)), _linha("— Q uer?", ("Q", 1.33)))
    feitas = tirar_espacos_da_letra_larga([Pagina(1, linhas)])
    assert _textos(feitas.paginas) == ["— Q uantos alunos?", "— Q uer?"]


def test_vao_que_muda_e_espaco_de_palavra_que_o_pdf_nao_gravou() -> None:
    # O vão de palavra sem o caractere de espaço muda com a linha justificada; o da letra larga,
    # não.
    vaos = (0.8, 1.6, 2.4, 1.1, 2.9)
    linhas = tuple(_linha(f"palavras s eguidas {n}", ("s", vao)) for n, vao in enumerate(vaos))
    feitas = tirar_espacos_da_letra_larga([Pagina(1, linhas)])
    assert feitas.tirados == 0


def test_adaptador_grava_o_espaco_inventado_so_na_linha_com_espaco_de_verdade(
    tmp_path: Path,
) -> None:
    pdf = montar_pdf(
        tmp_path / "l.pdf",
        [
            [
                LinhaDeTeste("Quando ele voltou, a Q estava ali.", 72, 700, letra_larga="Q"),
                LinhaDeTeste("Quanto", 72, 650, letra_larga="Q"),
            ]
        ],
    )
    com_espaco, sem_espaco = ler_paginas(pdf)[0].linhas
    assert com_espaco.texto == "Q uando ele voltou, a Q estava ali."
    assert [(e.posicao, e.letra) for e in com_espaco.espacos_inventados] == [(1, "Q")]
    assert sem_espaco.espacos_inventados == ()


def test_importar_pdf_junta_a_letra_larga_a_palavra(tmp_path: Path) -> None:
    frases = [
        "Quando ele voltou.",
        "Quer dizer então.",
        "Quantos alunos.",
        "Quartel General.",
        "Que mais.",
    ]
    linhas = [LinhaDeTeste(f, 72, 700 - 30 * n, letra_larga="Q") for n, f in enumerate(frases)]
    linhas.append(LinhaDeTeste("A série B da escola.", 72, 500))
    epub = tmp_path / "livro.epub"
    _ = importar_pdf(montar_pdf(tmp_path / "l.pdf", [linhas]), epub, "pt-BR")
    with zipfile.ZipFile(epub) as zip_:
        texto = zip_.read("OEBPS/c001.xhtml").decode()
    assert "Q u" not in texto
    assert "Quando ele voltou." in texto
    assert "A série B da escola." in texto


def test_algarismo_com_vao_constante_nao_e_letra_larga() -> None:
    # Revisão: a coluna de tabela alinhada, sem caractere de espaço entre as colunas, tem o mesmo
    # vão depois do algarismo em toda linha.
    linhas = tuple(_linha(f"Dose {n}2 34 mg", ("2", 1.33)) for n in range(5))
    assert tirar_espacos_da_letra_larga([Pagina(1, linhas)]).tirados == 0


def test_um_vao_fora_da_faixa_nao_derruba_a_letra() -> None:
    # Revisão: um espaço de palavra que o PDF não gravou, depois de y, derrubava a prova toda.
    linhas = [_linha(f"o major Toy ama {n}", ("y", 0.75)) for n in range(5)]
    linhas.append(_linha("Shibuy a outra", ("y", 2.9)))
    feitas = tirar_espacos_da_letra_larga([Pagina(1, tuple(linhas))])
    assert _textos(feitas.paginas)[:5] == [f"o major Toyama {n}" for n in range(5)]
    assert _textos(feitas.paginas)[5] == "Shibuy a outra"


def test_posicao_fora_do_texto_nao_derruba_a_importacao() -> None:
    # Auditoria: o PDF é entrada não confiável, e a posição vem da conta do adaptador; fora do
    # texto (um caractere com espaço dentro, que a junção dos espaços encurta), a linha fica.
    linhas = [_linha(f"Q uando {n}", ("Q", 1.33)) for n in range(3)]
    quebrada = Linha(
        "Q",
        x=25,
        fim=227,
        topo=0.5,
        tamanho=6.0,
        espacos_inventados=(EspacoInventado(5, "Q", NEGRITO, 1.33),),
    )
    feitas = tirar_espacos_da_letra_larga([Pagina(1, (*linhas, quebrada))])
    assert _textos(feitas.paginas)[-1] == "Q"


def test_vao_constante_do_tamanho_de_um_espaco_e_espaco_de_verdade() -> None:
    # Regressão: no Miller, o número de página do cabeçalho fica a 11,36 pt da última letra, em
    # 9 pt, em toda página; no Practical, "to \u201317.4" deixa 1,85 pt em 6,5 pt, em toda linha da
    # tabela. O vão é constante, mas é o de um espaço ou mais: a letra não é larga.
    cabecalhos = [
        _linha(f"Evaluación preoperatoria {n}", ("a", 11.36), tamanho=9.0) for n in range(5)
    ]
    tabela = [_linha(f"4.{n} (2.0 to \u201317.4)", ("o", 1.85), tamanho=6.5) for n in range(5)]
    feitas = tirar_espacos_da_letra_larga([Pagina(1, (*cabecalhos, *tabela))])
    assert _textos(feitas.paginas) == [linha.texto for linha in (*cabecalhos, *tabela)]
