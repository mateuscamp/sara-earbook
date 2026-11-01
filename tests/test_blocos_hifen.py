# SPDX-License-Identifier: GPL-3.0-or-later
"""Montagem de blocos: a palavra partida no fim da linha (ADR-0004)."""

from __future__ import annotations

from tests.linhas_de_teste import ENTRELINHA, RECUO, linha, montar, resumo, texto_corrido


def test_palavra_partida_no_fim_da_linha_volta_inteira() -> None:
    pagina = [
        *texto_corrido(0.1),
        linha("Os archi-", 0.3, RECUO),
        linha("tects decidem.", 0.3 + ENTRELINHA),
    ]
    livro = montar(pagina)
    assert resumo(livro)[-1:] == [("paragrafo", "Os architects decidem.")]
    assert (livro.hifens_tirados, livro.hifens_mantidos) == (1, 0)


def test_hifen_tipografico_no_fim_da_linha_tambem_sai() -> None:
    # Hard Parts: 1.058 quebras com o hífen U+2010, que o livro nunca usa no meio da linha.
    pagina = [
        *texto_corrido(0.1),
        linha("Os architec\u2010", 0.3, RECUO),
        linha("tures decidem.", 0.3 + ENTRELINHA),
    ]
    livro = montar(pagina)
    assert resumo(livro)[-1:] == [("paragrafo", "Os architectures decidem.")]
    assert (livro.hifens_tirados, livro.hifens_mantidos) == (1, 0)


def test_composto_partido_no_hifen_tipografico_mantem_o_hifen() -> None:
    # O dicionário do livro é escrito com "-"; a quebra com U+2010 o consulta do mesmo jeito.
    pagina = [
        *texto_corrido(0.1),
        linha("Um trabalho non-productive aqui.", 0.3, RECUO),
        linha("Outro trabalho non\u2010", 0.3 + 2 * ENTRELINHA, RECUO),
        linha("productive ali.", 0.3 + 3 * ENTRELINHA),
    ]
    livro = montar(pagina)
    assert resumo(livro)[-1:] == [("paragrafo", "Outro trabalho non\u2010productive ali.")]
    assert (livro.hifens_tirados, livro.hifens_mantidos) == (0, 1)


def test_composto_que_o_livro_escreve_com_hifen_tipografico_mantem_o_hifen() -> None:
    pagina = [
        *texto_corrido(0.1),
        linha("Um trabalho non\u2010productive aqui.", 0.3, RECUO),
        linha("Outro trabalho non-", 0.3 + 2 * ENTRELINHA, RECUO),
        linha("productive ali.", 0.3 + 3 * ENTRELINHA),
    ]
    livro = montar(pagina)
    assert resumo(livro)[-1:] == [("paragrafo", "Outro trabalho non-productive ali.")]
    assert (livro.hifens_tirados, livro.hifens_mantidos) == (0, 1)


def test_pontuacao_em_volta_nao_esconde_o_composto_do_dicionario() -> None:
    pagina = [
        *texto_corrido(0.1),
        linha("Um trabalho (non-productive) aqui.", 0.3, RECUO),
        linha("Outro trabalho \u201cnon-", 0.3 + 2 * ENTRELINHA, RECUO),
        linha("productive,\u201d ali.", 0.3 + 3 * ENTRELINHA),
    ]
    livro = montar(pagina)
    texto = "Outro trabalho \u201cnon-productive,\u201d ali."
    assert resumo(livro)[-1:] == [("paragrafo", texto)]
    assert (livro.hifens_tirados, livro.hifens_mantidos) == (0, 1)


def test_quebra_em_palavra_que_ja_tem_hifen_mantem_o_hifen() -> None:
    # A2 da auditoria: "--no-" + "agent-state." virava "--noagent-state." (Competente p. 396)
    # e "proof-of-" + "concepts" virava "proof-ofconcepts" (Hard Parts). Palavra com outro
    # hífen é composta: a quebra caiu num hífen dela.
    pagina = [
        *texto_corrido(0.1),
        linha("Rode com --no-", 0.3, RECUO),
        linha("agent-state, um proof-", 0.3 + ENTRELINHA),
        linha("of-concepts e um proof-of-", 0.3 + 2 * ENTRELINHA),
        linha("concepts no fim.", 0.3 + 3 * ENTRELINHA),
    ]
    livro = montar(pagina)
    texto = "Rode com --no-agent-state, um proof-of-concepts e um proof-of-concepts no fim."
    assert resumo(livro)[-1:] == [("paragrafo", texto)]
    assert (livro.hifens_tirados, livro.hifens_mantidos) == (0, 3)


def test_hifen_repetido_na_linha_de_baixo_fica_um_so() -> None:
    # Revisão xhigh: a norma brasileira repete o hífen do composto na linha de baixo
    # ("human-" / "-friendliness", Competente); saía "human- -friendliness".
    pagina = [
        *texto_corrido(0.1),
        linha("Um texto sobre human-", 0.3, RECUO),
        linha("-friendliness e mais.", 0.3 + ENTRELINHA),
    ]
    livro = montar(pagina)
    assert resumo(livro)[-1:] == [("paragrafo", "Um texto sobre human-friendliness e mais.")]
    assert (livro.hifens_tirados, livro.hifens_mantidos) == (0, 1)


def test_composto_com_hifen_que_o_livro_usa_inteiro_mantem_o_hifen() -> None:
    # 42 dos 267 hífens do Hard Parts eram compostos que o livro escreve com hífen.
    pagina = [
        *texto_corrido(0.1),
        linha("Um trabalho non-productive aqui.", 0.3, RECUO),
        linha("Outro trabalho non-", 0.3 + 2 * ENTRELINHA, RECUO),
        linha("productive ali.", 0.3 + 3 * ENTRELINHA),
    ]
    livro = montar(pagina)
    assert resumo(livro)[-1:] == [("paragrafo", "Outro trabalho non-productive ali.")]
    assert (livro.hifens_tirados, livro.hifens_mantidos) == (0, 1)


def test_hifen_suave_no_fim_da_linha_sempre_sai() -> None:
    # Competente: "carreira er­" + "rada." vem com o hífen suave (U+00AD), que é só de quebra.
    pagina = [
        *texto_corrido(0.1),
        linha("Escolheu a carreira er­", 0.3, RECUO),
        linha("rada, pensou.", 0.3 + ENTRELINHA),
    ]
    livro = montar(pagina)
    assert resumo(livro)[-1:] == [("paragrafo", "Escolheu a carreira errada, pensou.")]
    assert livro.hifens_tirados == 1


def test_composto_partido_numa_silaba_perde_o_hifen_da_quebra() -> None:
    # B2 da pós-auditoria: com outro hífen por perto, o hífen da quebra ficava sempre
    # ("pergun-tou-me", "ser-vice-based"). Se as metades vizinhas à quebra formam palavra
    # que o livro usa inteira, a quebra caiu numa sílaba e o hífen sai.
    pagina = [
        *texto_corrido(0.1),
        linha("Ele perguntou sobre o service oriented. Ele pergun-", 0.3, RECUO),
        linha("tou-me depois, num time ser-", 0.3 + ENTRELINHA),
        linha("vice-based e service-ori\u2010", 0.3 + 2 * ENTRELINHA),
        linha("ented aqui.", 0.3 + 3 * ENTRELINHA),
    ]
    livro = montar(pagina)
    texto = (
        "Ele perguntou sobre o service oriented. Ele perguntou-me depois, num time "
        "service-based e service-oriented aqui."
    )
    assert resumo(livro)[-1:] == [("paragrafo", texto)]
    assert (livro.hifens_tirados, livro.hifens_mantidos) == (3, 0)
