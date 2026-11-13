# SPDX-License-Identifier: GPL-3.0-or-later
"""O título sem letra nem algarismo sai do texto lido, registrado (ADR-0008, "Tratado em
português e em espanhol", decisão 3).

No Manica, o texto que o OCR leu dentro das figuras vira título: "•", "• •", "-", "~". São 375.
O Mateus decidiu tirar o título sem nenhuma palavra; o de algarismo ("2012") e o de letra solta
("A", "V") ficam, porque também são título de verdade.
"""

from __future__ import annotations

import pytest

from earbook.dominio.fora_do_audio import MOTIVO_DO_TITULO_SEM_LETRA
from earbook.dominio.limpeza import limpar_para_o_ouvido
from earbook.dominio.livro_limpo import LivroLimpo
from earbook.dominio.segmento import Papel, Segmento

ANTES = (Papel.PARAGRAFO, "A pressão do fluido cresce com o raio do vaso.")
DEPOIS = (Papel.PARAGRAFO, "O fluxo dos gases também pode ser medido.")


def _limpar(segmentos: list[tuple[Papel, str]]) -> LivroLimpo:
    capitulo = [
        Segmento(f"c001-s{n:04d}", papel, texto) for n, (papel, texto) in enumerate(segmentos, 1)
    ]
    return limpar_para_o_ouvido([("c001", capitulo)], "Livro", "Autor")


def _sobrou(livro: LivroLimpo) -> list[str]:
    return [s.texto for capitulo in livro.capitulos for s in capitulo.segmentos]


@pytest.mark.parametrize("resto", ["•", "• •", "---", "~", "}", "□", "- . , -"])
def test_titulo_sem_letra_nem_algarismo_sai_registrado(resto: str) -> None:
    livro = _limpar([ANTES, (Papel.TITULO, resto), DEPOIS])
    assert _sobrou(livro) == [ANTES[1], DEPOIS[1]]
    assert [(r.id, r.motivo, r.texto) for r in livro.remocoes] == [
        ("c001-s0002", MOTIVO_DO_TITULO_SEM_LETRA, resto)
    ]


@pytest.mark.parametrize("titulo", ["2012", "1.", "A", "l", "A B", "V", "Técnica", "§ 3"])
def test_titulo_com_letra_ou_algarismo_fica(titulo: str) -> None:
    assert _sobrou(_limpar([ANTES, (Papel.TITULO, titulo), DEPOIS])) == [
        ANTES[1],
        titulo,
        DEPOIS[1],
    ]


@pytest.mark.parametrize("papel", [Papel.PARAGRAFO, Papel.NOTA, Papel.CITACAO, Papel.ITEM])
def test_a_pausa_de_cena_que_nao_e_titulo_fica(papel: Papel) -> None:
    assert _sobrou(_limpar([ANTES, (papel, "* * *"), DEPOIS])) == [ANTES[1], "* * *", DEPOIS[1]]


def test_o_paragrafo_que_o_resto_de_figura_partia_se_emenda() -> None:
    # O título sem letra é resto de página, como o cabeçalho: sai antes da junção (ADR-0003).
    livro = _limpar(
        [
            (Papel.PARAGRAFO, "Em um vaso cilíndrico, a relação entre a pressão e a tensão da"),
            (Papel.TITULO, "• •"),
            (Papel.PARAGRAFO, "parede segue a lei."),
        ]
    )
    inteiro = "Em um vaso cilíndrico, a relação entre a pressão e a tensão da parede segue a lei."
    assert _sobrou(livro) == [inteiro]
    assert [(j.id, j.em) for j in livro.juncoes] == [("c001-s0003", "c001-s0001")]
