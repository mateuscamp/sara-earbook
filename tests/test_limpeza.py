# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import pytest

from ai_book.dominio.limpeza import LivroLimpo, Remocao, Suspeita, tirar_cabecalhos_de_pagina
from ai_book.dominio.segmento import Papel, Segmento

# Os metadados reais do OPF do Tides of Darkness: o cabeçalho é um pedaço do título.
TITULO = "World of WarCraft - Tides of Darkness"
AUTOR = "Aaron Rosenberg"


def _livro(
    *capitulos: list[str], papel: Papel = Papel.PARAGRAFO, titulo: str = TITULO
) -> LivroLimpo:
    """Cada capítulo é uma lista de textos; o ID é cNNN-sNNNN na ordem."""
    entrada = [
        (
            f"c{c:03d}",
            [Segmento(f"c{c:03d}-s{s:04d}", papel, texto) for s, texto in enumerate(textos, 1)],
        )
        for c, textos in enumerate(capitulos, 1)
    ]
    return tirar_cabecalhos_de_pagina(entrada, titulo, AUTOR)


def _textos(livro: LivroLimpo) -> list[list[str]]:
    return [[s.texto for s in capitulo.segmentos] for capitulo in livro.capitulos]


def test_titulo_com_numero_de_pagina_repetido_sai_do_texto() -> None:
    # Medido no Tides of Darkness: 203 linhas assim, lidas em voz alta a cada duas páginas.
    livro = _livro(
        ["Dawn came.", "Tides of Darkness 2", "Fog rose.", "Tides of Darkness 4"],
        ["Night fell.", "Tides of Darkness 6"],
    )
    assert _textos(livro) == [["Dawn came.", "Fog rose."], ["Night fell."]]


def test_numero_antes_do_nome_tambem_e_cabecalho() -> None:
    # Medido no Tides of Darkness: 55 linhas assim, nas páginas ímpares.
    livro = _livro(["12 Aaron Rosenberg", "A.", "14 Aaron Rosenberg", "B.", "16 Aaron Rosenberg"])
    assert _textos(livro) == [["A.", "B."]]


def test_frase_com_numero_que_se_repete_pouco_fica() -> None:
    # Duas ocorrências ainda podem ser texto do livro ("Room 101" no diálogo).
    livro = _livro(["Room 101", "They took him.", "Room 101"])
    assert _textos(livro) == [["Room 101", "They took him.", "Room 101"]]


def test_mesmo_numero_repetido_nao_e_numeracao_de_pagina() -> None:
    livro = _livro(["Room 101", "Room 101", "Room 101"])
    assert _textos(livro) == [["Room 101", "Room 101", "Room 101"]]


def test_dois_numeros_diferentes_nao_bastam() -> None:
    # A3 da auditoria: o limiar de três números não tinha teste.
    capitulo = ["Tides of Darkness 2", "A.", "Tides of Darkness 4"]
    livro = _livro(capitulo)
    assert _textos(livro) == [capitulo]
    assert livro.suspeitas == ()


@pytest.mark.parametrize(
    "rotulo", ["Chapter", "Capítulo", "Cap.", "Part", "Parte", "Book", "Livro", "Section", "Seção"]
)
def test_rotulo_de_capitulo_numerado_fica(rotulo: str) -> None:
    # "Chapter N" muda de número como página, mas é título que o ouvinte quer escutar.
    # A1 da auditoria: "Cap." nunca casava, e saía do áudio como cabeçalho.
    # O título do livro é o próprio rótulo, então só a regra do rótulo segura essas linhas.
    capitulos = [[f"{rotulo} 1"], [f"{rotulo} 2"], [f"{rotulo} 3"]]
    livro = _livro(*capitulos, titulo=rotulo)
    assert _textos(livro) == capitulos
    assert livro.suspeitas == ()


def test_titulo_do_livro_que_comeca_com_rotulo_sai() -> None:
    # A1 da auditoria: a comparação por prefixo isentava "Book of Dust 12" por começar com "Book".
    livro = _livro(
        ["Book of Dust 12", "A.", "Book of Dust 14", "Book of Dust 16"], titulo="Book of Dust"
    )
    assert _textos(livro) == [["A."]]


def test_frase_que_nao_esta_no_titulo_nem_no_autor_fica_como_suspeita() -> None:
    # H1 da auditoria: "Dia 1, Dia 2, Dia 3" de um diário é título, não cabeçalho. Fica no
    # texto e vai para a lista de suspeitas, que o Claude Code decide (ADR-0003).
    livro = _livro(["Dia 1", "A."], ["Dia 2", "B."], ["Dia 3", "C."])
    assert _textos(livro) == [["Dia 1", "A."], ["Dia 2", "B."], ["Dia 3", "C."]]
    motivo = "possível cabeçalho de página 'Dia': não está no título nem no autor"
    assert livro.suspeitas == (
        Suspeita("c001-s0001", motivo, "Dia 1"),
        Suspeita("c002-s0001", motivo, "Dia 2"),
        Suspeita("c003-s0001", motivo, "Dia 3"),
    )
    assert livro.remocoes == ()


def test_pedaco_de_palavra_do_titulo_nao_conta_como_titulo() -> None:
    # "Dark" está dentro de "Darkness", mas não é uma palavra do título.
    livro = _livro(["Dark 2", "Dark 4", "Dark 6"])
    assert _textos(livro) == [["Dark 2", "Dark 4", "Dark 6"]]
    assert len(livro.suspeitas) == 3


def test_titulo_e_nota_nunca_saem_pela_regra_de_cabecalho() -> None:
    capitulo = ["Tides of Darkness 2", "Tides of Darkness 4", "Tides of Darkness 6"]
    assert _textos(_livro(capitulo, papel=Papel.TITULO)) == [capitulo]
    assert _textos(_livro(capitulo, papel=Papel.NOTA)) == [capitulo]


def test_remocao_registra_id_motivo_e_texto() -> None:
    livro = _livro(["Tides of Darkness 2", "A.", "Tides of Darkness 4", "Tides of Darkness 6"])
    motivo = "cabeçalho de página 'Tides of Darkness'"
    assert livro.remocoes == (
        Remocao("c001-s0001", motivo, "Tides of Darkness 2"),
        Remocao("c001-s0003", motivo, "Tides of Darkness 4"),
        Remocao("c001-s0004", motivo, "Tides of Darkness 6"),
    )


def test_todo_segmento_de_origem_fica_ou_e_registrado() -> None:
    # O invariante que o `conferir` vai cobrar (ADR-0003): nada some em silêncio. A suspeita
    # é só um aviso: o segmento continua no texto.
    livro = _livro(
        ["Tides of Darkness 2", "A.", "Tides of Darkness 4", "Dia 1"],
        ["B.", "Tides of Darkness 6", "Dia 2", "Dia 3"],
    )
    mantidos = {s.id for capitulo in livro.capitulos for s in capitulo.segmentos}
    removidos = {r.id for r in livro.remocoes}
    assert mantidos | removidos == {
        "c001-s0001", "c001-s0002", "c001-s0003", "c001-s0004",
        "c002-s0001", "c002-s0002", "c002-s0003", "c002-s0004",
    }  # fmt: skip
    assert not mantidos & removidos
    assert removidos == {"c001-s0001", "c001-s0003", "c002-s0002"}
    assert {s.id for s in livro.suspeitas} <= mantidos
