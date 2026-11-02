# SPDX-License-Identifier: GPL-3.0-or-later
"""Verbete do glossário em negrito abaixo do corpo: parágrafo, fora da definição (ADR-0004)."""

from __future__ import annotations

from earbook.dominio.pagina import Linha
from tests.linhas_de_teste import (
    ENTRELINHA,
    MARGEM,
    em_negrito,
    linha,
    montar,
    resumo,
    texto_corrido,
)

# Competente, p. 466 a 480: o verbete vem em negrito de 9,5 pt na margem, e a definição, em
# 9,5 pt comum, recuada para x = 66,6.
GLOSSARIO = 9.5
DEFINICAO = 66.6


def verbete(texto: str, topo: float) -> list[Linha]:
    return [em_negrito(linha(texto, topo, MARGEM, tamanho=GLOSSARIO))]


def definicao(topo: float, *linhas: str) -> list[Linha]:
    return [
        linha(texto, topo + ENTRELINHA * n, DEFINICAO, tamanho=GLOSSARIO)
        for n, texto in enumerate(linhas)
    ]


def test_verbete_em_negrito_menor_que_o_corpo_sai_separado_da_definicao() -> None:
    # Competente p. 479: "Tokenizador A parte do modelo que quebra o texto…" saía num
    # parágrafo só, e o ouvinte não ouvia onde o termo acabava.
    pagina = [
        *texto_corrido(0.1),
        *verbete("Tokenizador", 0.3),
        *definicao(
            0.3 + ENTRELINHA, "A parte do modelo que quebra o texto em tokens", "e de volta."
        ),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "Tokenizador"),
        ("paragrafo", "A parte do modelo que quebra o texto em tokens e de volta."),
    ]


def test_verbete_depois_de_definicao_de_uma_linha_abre_paragrafo() -> None:
    # Competente p. 475: a definição de "Prompt" tem uma linha só, e voltar à margem depois de
    # uma linha recuada é, no parágrafo comum, a segunda linha dele. O verbete não é.
    pagina = [
        *texto_corrido(0.1),
        *verbete("Prompt", 0.3),
        *definicao(0.3 + ENTRELINHA, "O texto que você escreve pedindo algo ao modelo."),
        *verbete("Prompt caching", 0.3 + ENTRELINHA * 2.2),
        *definicao(0.3 + ENTRELINHA * 3.2, "O servidor guarda o trecho inicial da conversa."),
    ]
    assert resumo(montar(pagina))[-3:] == [
        ("paragrafo", "O texto que você escreve pedindo algo ao modelo."),
        ("paragrafo", "Prompt caching"),
        ("paragrafo", "O servidor guarda o trecho inicial da conversa."),
    ]


# Referências do Competente: a primeira linha na margem, as outras recuadas para x = 67,5, em
# 9 pt; o título da obra vem em negrito, às vezes numa linha inteira.
REFERENCIA = 9.0
CONTINUACAO = 67.5


def referencia(texto: str, linha_da_referencia: int, x: float = CONTINUACAO) -> Linha:
    return linha(texto, 0.3 + ENTRELINHA * linha_da_referencia, x, tamanho=REFERENCIA)


def test_negrito_na_margem_da_referencia_depois_de_frase_fechada_segue_nela() -> None:
    # Competente p. 493: depois de "(EMNLP 2024).", o título em negrito na mesma margem da
    # referência saía como parágrafo, e o "Lan-" do fim dele, partido de "guage".
    pagina = [
        *texto_corrido(0.1),
        referencia("LI, Zhuowan et al. Retrieval Augmented Generation", 0, MARGEM),
        referencia("or Long-Context LLMs? (EMNLP 2024).", 1),
        em_negrito(referencia("Proceedings of the Conference on Natural Lan-", 2)),
        referencia("guage Processing. Miami, nov. 2024.", 3),
    ]
    inteira = (
        "LI, Zhuowan et al. Retrieval Augmented Generation or Long-Context LLMs? (EMNLP 2024)."
        " Proceedings of the Conference on Natural Language Processing. Miami, nov. 2024."
    )
    assert resumo(montar(pagina))[-1:] == [("paragrafo", inteira)]


def test_linha_comum_depois_de_nota_nao_retoma_o_verbete() -> None:
    # O verbete não fecha frase, e a retomada do parágrafo interrompido por nota colava nele a
    # linha em minúscula: "Tokenizador a parte do modelo…". Nenhum caso nos dois livros.
    pagina = [
        *texto_corrido(0.1),
        *verbete("Tokenizador", 0.3),
        linha("Figura 3. O vocabulário do modelo.", 0.3 + ENTRELINHA, tamanho=7.7),
        *definicao(0.3 + ENTRELINHA * 2, "a parte do modelo que quebra o texto em tokens."),
    ]
    assert resumo(montar(pagina))[-3:] == [
        ("paragrafo", "Tokenizador"),
        ("nota", "Figura 3. O vocabulário do modelo."),
        ("paragrafo", "a parte do modelo que quebra o texto em tokens."),
    ]


def test_livro_de_corpo_em_negrito_nao_tem_verbete() -> None:
    # Com o corpo em negrito (revisão nº 1 do subtítulo), a linha comum é que destoa, e a
    # linha em negrito antes dela é só o parágrafo: a frase segue.
    pagina = [
        *[em_negrito(corpo) for corpo in texto_corrido(0.1)],
        em_negrito(linha("O corpo do livro em negrito continua", 0.3)),
        linha("numa linha comum, no mesmo parágrafo.", 0.3 + ENTRELINHA),
    ]
    paragrafo = "O corpo do livro em negrito continua numa linha comum, no mesmo parágrafo."
    assert resumo(montar(pagina))[-1:] == [("paragrafo", paragrafo)]


def test_verbete_na_margem_da_definicao_de_uma_linha_abre_paragrafo() -> None:
    # Glossário sem recuo: a definição de uma linha fica na margem do verbete seguinte.
    pagina = [
        *texto_corrido(0.1),
        *verbete("Prompt", 0.3),
        linha("O pedido ao modelo.", 0.3 + ENTRELINHA, tamanho=GLOSSARIO),
        *verbete("Prompt caching", 0.3 + ENTRELINHA * 2),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "O pedido ao modelo."),
        ("paragrafo", "Prompt caching"),
    ]


def test_linha_comum_depois_de_nota_nao_retoma_o_paragrafo_de_antes_do_verbete() -> None:
    # Como o título (revisão nº 1): a linha em minúscula colaria no parágrafo aberto antes do
    # verbete, e o verbete iria parar depois da definição.
    pagina = [
        *texto_corrido(0.1),
        linha("Um parágrafo que termina sem fechar a frase", 0.25, tamanho=GLOSSARIO),
        *verbete("Tokenizador", 0.3),
        linha("Figura 3. O vocabulário do modelo.", 0.3 + ENTRELINHA, tamanho=7.7),
        *definicao(0.3 + ENTRELINHA * 2, "a parte do modelo que quebra o texto em tokens."),
    ]
    assert resumo(montar(pagina))[-4:] == [
        ("paragrafo", "Um parágrafo que termina sem fechar a frase"),
        ("paragrafo", "Tokenizador"),
        ("nota", "Figura 3. O vocabulário do modelo."),
        ("paragrafo", "a parte do modelo que quebra o texto em tokens."),
    ]


def test_verbete_de_duas_linhas_sai_num_paragrafo_so() -> None:
    pagina = [
        *texto_corrido(0.1),
        *verbete("RLHF (Reinforcement Learning", 0.3),
        *verbete("from Human Feedback)", 0.3 + ENTRELINHA),
        *definicao(0.3 + ENTRELINHA * 2, "Aprendizado por reforço com nota humana."),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "RLHF (Reinforcement Learning from Human Feedback)"),
        ("paragrafo", "Aprendizado por reforço com nota humana."),
    ]


def test_verbete_no_pe_da_pagina_sai_separado_da_definicao_na_pagina_seguinte() -> None:
    # Na virada, o verbete não fecha frase e a definição começa em maiúscula; é também o que
    # separa 42 rodapés de seção do Hard Parts do texto da página seguinte (pós-auditoria).
    paginas = (
        [*texto_corrido(0.1), *verbete("Tokenizador", 0.85)],
        definicao(0.1, "A parte do modelo que quebra o texto em tokens", "e de volta."),
    )
    assert resumo(montar(*paginas))[-2:] == [
        ("paragrafo", "Tokenizador"),
        ("paragrafo", "A parte do modelo que quebra o texto em tokens e de volta."),
    ]


def test_negrito_depois_de_frase_aberta_segue_no_paragrafo() -> None:
    # Competente p. 486: o título da obra em negrito continua a palavra partida da linha de
    # cima ("Procee-" + "dings") e termina partido também ("Lin-" + "guistics").
    pagina = [
        *texto_corrido(0.1),
        referencia("BENDER, Emily M. Climbing towards NLU. In: ACL", 0, MARGEM),
        referencia("2020. Procee-", 1),
        em_negrito(referencia("dings of the Association for Computational Lin-", 2)),
        referencia("guistics. Online, jul. 2020.", 3),
    ]
    inteira = (
        "BENDER, Emily M. Climbing towards NLU. In: ACL 2020. Proceedings of the Association"
        " for Computational Linguistics. Online, jul. 2020."
    )
    assert resumo(montar(pagina))[-1:] == [("paragrafo", inteira)]


def test_quadro_todo_em_negrito_pequeno_segue_um_paragrafo_por_cima_do_fim_de_frase() -> None:
    # Code-review: a linha em negrito depois de frase fechada abria parágrafo também quando o
    # parágrafo de uma linha só era ele mesmo negrito, e o quadro se partia a cada frase.
    pagina = [
        *texto_corrido(0.1),
        *verbete("Cuidado com o agente.", 0.3),
        *verbete("Ele apaga arquivos sem pedir.", 0.3 + ENTRELINHA),
    ]
    quadro = "Cuidado com o agente. Ele apaga arquivos sem pedir."
    assert resumo(montar(pagina))[-1:] == [("paragrafo", quadro)]


def test_verbete_de_duas_linhas_com_dois_pontos_no_fim_da_primeira_segue_junto() -> None:
    # Code-audit (A1): "RAG:" / "Retrieval Augmented Generation" saía em dois parágrafos.
    pagina = [
        *texto_corrido(0.1),
        *verbete("RAG:", 0.3),
        *verbete("Retrieval Augmented Generation", 0.3 + ENTRELINHA),
        *definicao(0.3 + ENTRELINHA * 2, "Busca antes de gerar."),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "RAG: Retrieval Augmented Generation"),
        ("paragrafo", "Busca antes de gerar."),
    ]
