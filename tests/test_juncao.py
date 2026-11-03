# SPDX-License-Identifier: GPL-3.0-or-later
"""Cabeçalho colado e parágrafo partido na quebra de página (ADR-0003).

Os exemplos vêm do Tides of Darkness, convertido de PDF: 165 cabeçalhos colados no fim de
parágrafo e 290 junções de parágrafo que continua, em minúscula, depois da quebra.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from earbook.dominio.limpeza import Aparo, Juncao, LivroLimpo, Suspeita, limpar_para_o_ouvido
from earbook.dominio.segmento import Papel, Segmento

TITULO = "World of WarCraft - Tides of Darkness"
AUTOR = "Aaron Rosenberg"
# Três cabeçalhos soltos firmam a frase como cabeçalho do livro.
CABECALHOS = ["Tides of Darkness 90", "Tides of Darkness 92", "Tides of Darkness 94"]


def _livro(*capitulos: Sequence[str | Segmento]) -> LivroLimpo:
    """Texto vira parágrafo com ID cNNN-sNNNN na ordem; Segmento entra como está."""
    entrada = [
        (
            f"c{c:03d}",
            [
                item
                if isinstance(item, Segmento)
                else Segmento(f"c{c:03d}-s{s:04d}", Papel.PARAGRAFO, item)
                for s, item in enumerate(itens, 1)
            ],
        )
        for c, itens in enumerate(capitulos, 1)
    ]
    return limpar_para_o_ouvido(entrada, TITULO, AUTOR)


def _textos(livro: LivroLimpo) -> list[list[str]]:
    return [[s.texto for s in capitulo.segmentos] for capitulo in livro.capitulos]


def test_cabecalho_colado_no_fim_do_paragrafo_sai_e_fica_registrado() -> None:
    # A frase só sai colada se o livro já a firmou como cabeçalho em linhas soltas.
    soltos = ["13 Aaron Rosenberg", "15 Aaron Rosenberg", "17 Aaron Rosenberg"]
    livro = _livro(["Lothar spoke at last. 3 Aaron Rosenberg", "Night fell.", *soltos])
    assert _textos(livro) == [["Lothar spoke at last.", "Night fell."]]
    motivo = "cabeçalho de página 'Aaron Rosenberg' colado no fim"
    assert livro.aparos == (Aparo("c001-s0001", motivo, "3 Aaron Rosenberg"),)


def test_frase_do_titulo_no_fim_sem_numero_fica() -> None:
    livro = _livro(["They sailed on the Tides of Darkness", *CABECALHOS])
    assert _textos(livro) == [["They sailed on the Tides of Darkness"]]
    assert livro.aparos == ()


def test_paragrafo_partido_na_quebra_de_pagina_vira_um_so() -> None:
    livro = _livro(["They peered into the fog, trying", "to pierce its gloom."])
    assert _textos(livro) == [["They peered into the fog, trying to pierce its gloom."]]
    assert livro.juncoes == (Juncao("c001-s0002", "c001-s0001"),)


def test_cabecalho_colado_sai_antes_da_juncao() -> None:
    livro = _livro(
        ["into the fog, trying Tides of Darkness 2", "to pierce its gloom.", *CABECALHOS]
    )
    assert _textos(livro) == [["into the fog, trying to pierce its gloom."]]


def test_hifen_da_quebra_sai_quando_o_livro_escreve_a_palavra_inteira() -> None:
    # Dalgalarrondo c004: o destaque partia "identifi-" | destaque | "car"; sem ele, a junção
    # emendava "identifi-car", e o livro escreve "identificar" em outro lugar (ADR-0003).
    livro = _livro(
        ["O psicopatólogo busca observar, identifi-", "car e compreender.", "Cabe identificar."]
    )
    assert _textos(livro) == [
        ["O psicopatólogo busca observar, identificar e compreender.", "Cabe identificar."]
    ]


@pytest.mark.parametrize(
    ("partido", "inteiro"),
    [
        # O composto que o livro só escreve com hífen.
        (
            ["A cor do dia relaciona-", "se ao humor.", "O humor relaciona-se à cor."],
            "relaciona-se",
        ),
        # O hífen de quebra que o livro não prova fica: melhor um hífen a mais que uma palavra
        # inventada (Dalgalarrondo: "embrioná-ria").
        (["Isso vem desde a fase embrioná-", "ria do cérebro."], "embrioná-ria"),
    ],
)
def test_hifen_fica_quando_o_livro_nao_escreve_a_palavra_inteira(
    partido: list[str], inteiro: str
) -> None:
    assert inteiro in _textos(_livro(partido))[0][0]


def test_fala_que_continua_depois_das_aspas_vira_um_so() -> None:
    livro = _livro(["“You are correct, of course,”", "he answered."])
    assert _textos(livro) == [["“You are correct, of course,” he answered."]]


def test_apostrofo_no_fim_continua_no_paragrafo_seguinte() -> None:
    apostrofo = "\N{RIGHT SINGLE QUOTATION MARK}"
    livro = _livro([f"out of the warriors{apostrofo}", "reach. “While you were away.”"])
    assert _textos(livro) == [[f"out of the warriors{apostrofo} reach. “While you were away.”"]]


def test_continuacao_que_abre_aspas_em_minuscula_tambem_junta() -> None:
    livro = _livro(["“And will it,” he agreed,", "“but will it give them power?”"])
    assert _textos(livro) == [["“And will it,” he agreed, “but will it give them power?”"]]


def test_paragrafo_fechado_com_ponto_nao_junta() -> None:
    # O seguinte é longo e com pontuação: só a regra do ponto final segura os dois separados.
    capitulo = ["Teach Heaven to rock, amigo.", "visit us on the web, where the story goes on."]
    livro = _livro(capitulo)
    assert _textos(livro) == [capitulo]
    assert livro.juncoes == ()


def test_proximo_em_maiuscula_nao_junta() -> None:
    # Verso do Huxley: linha que termina em vírgula, seguida de linha em maiúscula.
    livro = _livro(["The flowers are easy to paint,", "The leaves difficult."])
    assert _textos(livro) == [["The flowers are easy to paint,", "The leaves difficult."]]


def test_linha_curta_antes_de_minuscula_fica_como_suspeita() -> None:
    # "first prologue" é título de capítulo como <p>; "awn" perdeu a capitular ("Dawn").
    # A suspeita é uma só, com o motivo mais útil para quem corrige: a capitular.
    livro = _livro(["first prologue", "awn, and fog still shrouded the world."])
    assert _textos(livro) == [["first prologue", "awn, and fog still shrouded the world."]]
    motivo = (
        "capitular perdida? começa em minúscula logo depois de título: corrigir a primeira letra"
    )
    assert livro.suspeitas == (
        Suspeita("c001-s0002", motivo, "awn, and fog still shrouded the world."),
    )


def test_seguinte_curto_sem_pontuacao_fica_como_suspeita() -> None:
    # "acknowledgments" é título que veio em minúscula depois do fim do último capítulo.
    livro = _livro(["“What could they possibly do to earn statues?”", "acknowledgments"])
    assert _textos(livro) == [["“What could they possibly do to earn statues?”", "acknowledgments"]]
    assert [s.id for s in livro.suspeitas] == ["c001-s0002"]


def test_tres_pedacos_do_mesmo_paragrafo_viram_um_so() -> None:
    livro = _livro(["He walked along the", "shore and kept on walking", "until night came."])
    assert _textos(livro) == [["He walked along the shore and kept on walking until night came."]]
    assert livro.juncoes == (
        Juncao("c001-s0002", "c001-s0001"),
        Juncao("c001-s0003", "c001-s0001"),
    )


def test_juncao_soma_as_notas() -> None:
    a = Segmento("c001-s0001", Papel.PARAGRAFO, "He said it and", ("OEBPS/a.xhtml#n1",))
    b = Segmento("c001-s0002", Papel.PARAGRAFO, "then left.", ("OEBPS/a.xhtml#n2",))
    notas = [s.notas for c in _livro([a, b]).capitulos for s in c.segmentos]
    assert notas == [("OEBPS/a.xhtml#n1", "OEBPS/a.xhtml#n2")]


def test_juncao_nao_atravessa_capitulo() -> None:
    livro = _livro(["The last line of a chapter, and"], ["the first of the next."])
    assert _textos(livro) == [["The last line of a chapter, and"], ["the first of the next."]]


def test_travessao_que_fecha_e_abre_paragrafo_nao_junta() -> None:
    # A1 da auditoria: é a ação interrompida entre dois parágrafos, não quebra de página.
    capitulo = [
        "She ran between two clusters of trees\u2014",
        "\u2014and found herself staring at a troll.",
    ]
    livro = _livro(capitulo)
    assert _textos(livro) == [capitulo]
    assert livro.juncoes == ()


def test_cabecalho_colado_depois_de_hifen_sai_e_a_palavra_se_junta_sem_espaco() -> None:
    # A2 da auditoria: "sub-429 Aaron Rosenberg" + "commander" ficava no áudio.
    soltos = ["13 Aaron Rosenberg", "15 Aaron Rosenberg", "17 Aaron Rosenberg"]
    livro = _livro(
        ["He was named lieutenant and sub-429 Aaron Rosenberg", "commander of the fleet.", *soltos]
    )
    assert _textos(livro) == [["He was named lieutenant and sub-commander of the fleet."]]
    motivo = "cabeçalho de página 'Aaron Rosenberg' colado no fim"
    assert livro.aparos == (Aparo("c001-s0001", motivo, "429 Aaron Rosenberg"),)


@pytest.mark.parametrize("fim", [".", "!", "?", "\u2026", ":", ";"])
def test_paragrafo_que_termina_frase_nao_junta(fim: str) -> None:
    # A4 da auditoria: só o ponto final tinha teste.
    capitulo = [f"It was over at last{fim}", "and nobody slept that night, not even the guards."]
    assert _textos(_livro(capitulo)) == [capitulo]


def test_continuacao_que_abre_aspas_retas_em_minuscula_junta() -> None:
    livro = _livro(['"And will it," he agreed,', '"but will it give them power?"'])
    assert _textos(livro) == [['"And will it," he agreed, "but will it give them power?"']]


def test_titulo_longo_antes_de_minuscula_nao_junta() -> None:
    # A4 da auditoria: título de 4 palavras ou mais, seguido de capitular perdida.
    titulo = Segmento("c001-s0001", Papel.TITULO, "The Battle of Grim Batol")
    livro = _livro([titulo, "re we ready for the fight?\u201d"])
    assert _textos(livro) == [["The Battle of Grim Batol", "re we ready for the fight?\u201d"]]


def test_linha_de_tres_palavras_sem_pontuacao_conta_como_curta() -> None:
    livro = _livro(["about the author", "was born in a small town and lives there still."])
    assert _textos(livro) == [
        ["about the author", "was born in a small town and lives there still."]
    ]
    assert [s.id for s in livro.suspeitas] == ["c001-s0002"]


@pytest.mark.parametrize("papel", [Papel.ITEM, Papel.CELULA, Papel.CITACAO])
def test_item_celula_e_citacao_nao_entram_na_juncao(papel: Papel) -> None:
    # A3 da auditoria: o <p> sem ponto engolia a lista, a tabela e a citação seguintes.
    anterior = "the list goes on like this and"
    seguinte = Segmento("c001-s0002", papel, "first item of the list goes here")
    livro = _livro([anterior, seguinte])
    assert _textos(livro) == [[anterior, "first item of the list goes here"]]


def test_titulo_e_nota_nao_entram_na_juncao() -> None:
    titulo = Segmento("c001-s0001", Papel.TITULO, "The beginning of")
    nota = Segmento("c001-s0003", Papel.NOTA, "see the appendix.")
    livro = _livro([titulo, "the end of it, and", nota])
    assert _textos(livro) == [["The beginning of", "the end of it, and", "see the appendix."]]


def test_todo_segmento_de_origem_fica_e_removido_ou_juntado() -> None:
    # O invariante do `conferir` (ADR-0003): origem = mantidos + removidos + juntados.
    livro = _livro(
        ["They peered, trying Tides of Darkness 2", "to pierce it.", *CABECALHOS],
        ["first prologue", "awn came."],
    )
    mantidos = {s.id for c in livro.capitulos for s in c.segmentos}
    removidos = {r.id for r in livro.remocoes}
    juntados = {j.id for j in livro.juncoes}
    origem = {f"c001-s{n:04d}" for n in range(1, 6)} | {"c002-s0001", "c002-s0002"}
    assert mantidos | removidos | juntados == origem
    assert not mantidos & removidos
    assert not mantidos & juntados
    assert not removidos & juntados
