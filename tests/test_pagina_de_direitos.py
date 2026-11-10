# SPDX-License-Identifier: GPL-3.0-or-later
"""A página de direitos autorais sai do áudio, registrada (ADR-0003).

Os textos imitam a página do Tides of Darkness (EPUB) e a do Competente o Suficiente (PDF).
"""

from __future__ import annotations

import pytest

from earbook.dominio.direitos import MOTIVO_DA_PAGINA_DE_DIREITOS, MOTIVO_DA_VIZINHA_DE_DIREITOS
from earbook.dominio.limpeza import limpar_para_o_ouvido
from earbook.dominio.livro_limpo import LivroLimpo
from earbook.dominio.segmento import Papel, Segmento

T, P = Papel.TITULO, Papel.PARAGRAFO


def _limpar(*segmentos: tuple[Papel, str]) -> LivroLimpo:
    capitulo = [
        Segmento(f"c001-s{n:04d}", papel, texto) for n, (papel, texto) in enumerate(segmentos, 1)
    ]
    return limpar_para_o_ouvido([("c001", capitulo)], "Um Livro", "Fulana")


def _ficam(livro: LivroLimpo) -> list[str]:
    return [s.texto for s in livro.capitulos[0].segmentos]


def _saem(livro: LivroLimpo) -> list[tuple[str, str]]:
    return [(r.texto, r.motivo) for r in livro.remocoes]


def test_pagina_de_direitos_sai_e_a_dedicatoria_fica() -> None:
    # Tides of Darkness: o bloco do © até a URL era lido em voz alta antes da dedicatória.
    livro = _limpar(
        (T, "POCKET STAR BOOKS"),
        (P, "A Division of Simon & Schuster, Inc. 1230 Avenue of the Americas"),
        (P, "© 2007 Blizzard Entertainment, Inc. All rights reserved."),
        (P, "ISBN-13: 978-1-4165-3990-2"),
        (P, "POCKET STAR BOOKS and colophon are registered trademarks of Simon & Schuster."),
        (P, "Visit us on the World Wide Web:"),
        (P, "http://www.SimonSays.com"),
        (P, "To my family and friends."),
    )
    assert _ficam(livro) == [
        "POCKET STAR BOOKS",
        "A Division of Simon & Schuster, Inc. 1230 Avenue of the Americas",
        "To my family and friends.",
    ]
    assert _saem(livro) == [
        ("© 2007 Blizzard Entertainment, Inc. All rights reserved.", MOTIVO_DA_PAGINA_DE_DIREITOS),
        ("ISBN-13: 978-1-4165-3990-2", MOTIVO_DA_PAGINA_DE_DIREITOS),
        (
            "POCKET STAR BOOKS and colophon are registered trademarks of Simon & Schuster.",
            MOTIVO_DA_VIZINHA_DE_DIREITOS,
        ),
        ("Visit us on the World Wide Web:", MOTIVO_DA_VIZINHA_DE_DIREITOS),
        ("http://www.SimonSays.com", MOTIVO_DA_VIZINHA_DE_DIREITOS),
    ]


def test_direitos_em_portugues_saem() -> None:
    # Competente: o segmento traz título, subtítulo e o aviso de direitos.
    livro = _limpar(
        (P, "FABIO AKITA"),
        (P, "Competente o Suficiente © 2026 Fabio Akita. Todos os direitos reservados."),
        (T, "Sumário"),
    )
    assert _ficam(livro) == ["FABIO AKITA", "Sumário"]


def test_corrente_nao_atravessa_titulo() -> None:
    # Um capítulo que começa logo depois da página de direitos, com um link no primeiro
    # parágrafo, não pode sair junto.
    livro = _limpar(
        (P, "Copyright © 2020 Editora Exemplo"),
        (T, "Capítulo 1"),
        (P, "Veja www.exemplo.com antes de começar."),
    )
    assert _ficam(livro) == ["Capítulo 1", "Veja www.exemplo.com antes de começar."]


def test_texto_comum_com_palavra_de_editora_fica() -> None:
    # Sem marca forte (©, direitos reservados, ISBN), nada sai: "edição" e um link são texto.
    livro = _limpar(
        (P, "A segunda edição saiu em 2020."),
        (P, "O site é www.exemplo.com."),
    )
    assert _saem(livro) == []


def test_titulo_com_palavra_de_editora_logo_depois_fica() -> None:
    livro = _limpar(
        (P, "© 2020 Fulana. Todos os direitos reservados."),
        (T, "Prefácio à segunda edição"),
        (P, "Esta edição traz dois capítulos novos."),
    )
    assert _ficam(livro) == ["Prefácio à segunda edição", "Esta edição traz dois capítulos novos."]


def test_marca_forte_no_meio_do_livro_nao_tira_nada() -> None:
    # Revisão: "© Oracle" ou um ISBN citado num capítulo puxava os vizinhos com link.
    corpo = [(P, f"Parágrafo {n}.") for n in range(60)]
    corpo[30] = (P, "O Java é © Oracle, e a documentação está em https://docs.oracle.com.")
    corpo[31] = (P, "Veja também https://openjdk.org.")
    assert _saem(_limpar(*corpo)) == []


def test_dedicatoria_entre_o_aviso_e_a_edicao_fica() -> None:
    # Revisão: a travessia levava a linha sem marca entre duas marcadas, e a dedicatória
    # pode estar justamente ali, conforme a editora.
    livro = _limpar(
        (P, "© 2020 Editora Exemplo. Todos os direitos reservados."),
        (P, "Para minha mãe."),
        (P, "Primeira edição: março de 2020."),
    )
    assert "Para minha mãe." in _ficam(livro)


def test_pagina_de_direitos_no_fim_do_livro_sai() -> None:
    # Hard Parts: a contracapa, no último capítulo, traz o aviso da O'Reilly.
    corpo = [(P, f"Parágrafo {n}.") for n in range(60)]
    corpo[59] = (P, "© 2022 O'Reilly Media, Inc. All rights reserved.")
    assert _saem(_limpar(*corpo)) == [
        ("© 2022 O'Reilly Media, Inc. All rights reserved.", MOTIVO_DA_PAGINA_DE_DIREITOS)
    ]


def test_posicao_conta_no_livro_inteiro_e_nao_no_capitulo() -> None:
    # O © no começo do capítulo do meio está no meio do livro.
    def capitulo(numero: int, textos: list[str]) -> tuple[str, list[Segmento]]:
        ids = (f"c{numero:03d}-s{n:04d}" for n in range(1, len(textos) + 1))
        return (f"c{numero:03d}", [Segmento(i, P, t) for i, t in zip(ids, textos, strict=True)])

    meio = ["Uma citação: © 2001 Fulano, usada com permissão.", *(f"Texto {n}." for n in range(40))]
    capitulos = [
        capitulo(1, [f"Antes {n}." for n in range(40)]),
        capitulo(2, meio),
        capitulo(3, [f"Depois {n}." for n in range(40)]),
    ]
    assert limpar_para_o_ouvido(capitulos, "Um Livro", "Fulana").remocoes == ()


def test_corrente_nao_sai_das_pontas_do_livro() -> None:
    # A1 da auditoria: a âncora ficava na ponta, mas a corrente andava pelo livro adentro
    # enquanto houvesse link (um ISBN numa referência levou 60 entradas da bibliografia).
    corpo = [(P, f"Parágrafo {n}.") for n in range(60)]
    corpo[18] = (P, "© 2020 Fulana.")
    for n in range(19, 31):
        corpo[n] = (P, f"Veja https://exemplo.com/{n}.")
    assert [texto for texto, _ in _saem(_limpar(*corpo))] == [
        "© 2020 Fulana.",
        "Veja https://exemplo.com/19.",
    ]


def test_corrente_leva_no_maximo_cinco_linhas_fracas_de_cada_lado() -> None:
    # Colofão depois de uma lista de links, já na ponta do fim do livro.
    corpo = [(P, f"Parágrafo {n}.") for n in range(60)]
    for n in range(45, 59):
        corpo[n] = (P, f"Referência {n}. Disponível em: https://exemplo.com/{n}.")
    corpo[59] = (P, "© 2026 Fulana. Todos os direitos reservados.")
    saem = [texto for texto, _ in _saem(_limpar(*corpo))]
    assert len(saem) == 6
    assert saem[0] == "Referência 54. Disponível em: https://exemplo.com/54."


def test_corrente_anda_para_tras() -> None:
    livro = _limpar(
        (P, "Texto da folha de rosto."),
        (P, "Publicado por Editora Exemplo."),
        (P, "© 2020 Fulana."),
    )
    assert _ficam(livro) == ["Texto da folha de rosto."]


def test_dedicatoria_com_palavra_de_editora_ao_lado_do_aviso_fica() -> None:
    # A2 da auditoria: a dedicatória só era protegida quando era a linha atravessada.
    livro = _limpar(
        (P, "© 2020 Fulana. Todos os direitos reservados."),
        (P, "Para minha editora, Beltrana, sem a qual nada."),
    )
    assert _ficam(livro) == ["Para minha editora, Beltrana, sem a qual nada."]


@pytest.mark.parametrize(
    "aviso",
    [
        "Direitos reservados.",
        "All rights reserved.",
        "(c) 2020 Fulana",
        "© Fulana",
        "ISBN 978-0-00-000000-0",
    ],
)
def test_cada_marca_forte_abre_a_pagina_de_direitos(aviso: str) -> None:
    assert _saem(_limpar((P, aviso), (P, "Texto."))) == [(aviso, MOTIVO_DA_PAGINA_DE_DIREITOS)]


@pytest.mark.parametrize(("posicao", "removidas"), [(19, 1), (20, 0), (21, 1)])
def test_ponta_minima_de_vinte_segmentos(posicao: int, removidas: int) -> None:
    # Num livro de 41 segmentos, só a posição 20 fica no meio: 0 a 19 e 21 a 40 são pontas.
    corpo = [(P, f"Parágrafo {n}.") for n in range(41)]
    corpo[posicao] = (P, "© 2020 Fulana.")
    assert len(_saem(_limpar(*corpo))) == removidas


def test_travessia_nao_passa_do_limite_de_cinco() -> None:
    # N3 da pós-auditoria: o limite era conferido antes do passo, e a travessia levava duas
    # linhas de uma vez: saíam 6.
    livro = _limpar(
        (P, "© 2020 Fulana. Todos os direitos reservados."),
        (P, "Publicado por Editora Exemplo."),
        (P, "Primeira edição."),
        (P, "Impresso no Brasil."),
        (P, "www.exemplo.com"),
        (P, "Linha sem marca nenhuma."),
        (P, "Veja https://exemplo.com/6."),
        (P, "Texto 8."),
    )
    assert len(_saem(livro)) == 5


@pytest.mark.parametrize(
    "dedicatoria",
    [
        "This book is dedicated to my mother.",
        "Dedico este livro à minha mãe.",
        "In loving memory of my father.",
        "Dedicatória: à minha mãe.",
    ],
)
def test_dedicatoria_que_nao_comeca_com_para_tambem_fica(dedicatoria: str) -> None:
    # N5 da pós-auditoria: só "Para…", "To…", "For…" eram reconhecidas.
    livro = _limpar(
        (P, "© 2020 Fulana. Todos os direitos reservados."),
        (P, dedicatoria),
        (P, "Primeira edição: março de 2020."),
    )
    assert dedicatoria in _ficam(livro)


def test_isbn_numa_referencia_sai_sozinho() -> None:
    # N6 da pós-auditoria: uma referência com ISBN, no fim do livro, abria a corrente e
    # levava as referências vizinhas, com link.
    corpo = [(P, f"Parágrafo {n}.") for n in range(60)]
    for n in range(45, 60):
        corpo[n] = (
            P,
            f"Autor {n}. Livro. Editora X, 2020. Disponível em: https://exemplo.com/{n}.",
        )
    corpo[52] = (P, "Autor 52. Livro. Editora X, 2020. ISBN 978-85-0000-000-0.")
    assert [t for t, _ in _saem(_limpar(*corpo))] == [corpo[52][1]]


@pytest.mark.parametrize(("posicao", "removidas"), [(29, 1), (30, 0)])
def test_ponta_de_dez_por_cento_num_livro_grande(posicao: int, removidas: int) -> None:
    # Com 300 segmentos, a ponta é de 30: os 10% valem mais que o mínimo de 20.
    corpo = [(P, f"Parágrafo {n}.") for n in range(300)]
    corpo[posicao] = (P, "© 2020 Fulana.")
    assert len(_saem(_limpar(*corpo))) == removidas
