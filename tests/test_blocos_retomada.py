# SPDX-License-Identifier: GPL-3.0-or-later
"""Retomada do parágrafo interrompido por nota ou código, e o que a encerra (ADR-0004)."""

from __future__ import annotations

from tests.linhas_de_teste import ENTRELINHA, RECUO, linha, montar, resumo, texto_corrido


def test_linha_de_tabela_encerra_o_paragrafo_interrompido_mesmo_com_nota_depois() -> None:
    # Como o título: sem isso, a linha minúscula depois da nota colava no parágrafo de antes
    # da tabela, e a tabela ia parar depois dele (mutante M11 do verbete, ADR-0004).
    pagina = [
        *texto_corrido(0.1),
        linha("A tabela abaixo mostra", 0.3, RECUO),
        linha("Epic", 0.3 + ENTRELINHA),
        linha("sync", 0.3 + ENTRELINHA, 200),
        linha("atomic", 0.3 + ENTRELINHA, 350),
        linha("Fonte: os autores.", 0.3 + ENTRELINHA * 2, tamanho=8.5),
        linha("continua em minúscula.", 0.3 + ENTRELINHA * 3),
    ]
    assert resumo(montar(pagina))[-4:] == [
        ("paragrafo", "A tabela abaixo mostra"),
        ("paragrafo", "Epic sync atomic"),
        ("nota", "Fonte: os autores."),
        ("paragrafo", "continua em minúscula."),
    ]


def test_paragrafo_interrompido_por_legenda_e_codigo_e_retomado() -> None:
    # Nota e código interrompem sem fechar a retomada: a linha minúscula depois dos dois
    # continua o parágrafo (M18 da auditoria do verbete, ADR-0004).
    pagina = [
        *texto_corrido(0.1),
        linha("O parágrafo segue", 0.3, RECUO),
        linha("Figura 2. A saída do comando.", 0.3 + ENTRELINHA, tamanho=8.5),
        linha("make check", 0.3 + ENTRELINHA * 2, mono=True),
        linha("e continua em minúscula.", 0.3 + ENTRELINHA * 3),
    ]
    assert resumo(montar(pagina))[-3:] == [
        ("paragrafo", "O parágrafo segue e continua em minúscula."),
        ("nota", "Figura 2. A saída do comando."),
        ("codigo", "make check"),
    ]


def test_paragrafo_interrompido_por_codigo_e_legenda_e_retomado() -> None:
    # A ordem inversa da de cima: o código também não fecha a retomada (A1 da pós-auditoria
    # do verbete, ADR-0004).
    pagina = [
        *texto_corrido(0.1),
        linha("O parágrafo segue", 0.3, RECUO),
        linha("make check", 0.3 + ENTRELINHA, mono=True),
        linha("Figura 2. A saída do comando.", 0.3 + ENTRELINHA * 2, tamanho=8.5),
        linha("e continua em minúscula.", 0.3 + ENTRELINHA * 3),
    ]
    assert resumo(montar(pagina))[-3:] == [
        ("paragrafo", "O parágrafo segue e continua em minúscula."),
        ("codigo", "make check"),
        ("nota", "Figura 2. A saída do comando."),
    ]


def test_linha_em_maiuscula_depois_da_nota_nao_retoma_o_paragrafo() -> None:
    # A retomada é da continuação da frase, que começa em minúscula: a linha em maiúscula depois
    # da legenda abre parágrafo novo (P3 da pós-auditoria do quadro, ADR-0004, "Quadro no lugar").
    pagina = [
        *texto_corrido(0.1),
        linha("O parágrafo segue", 0.3, RECUO),
        linha("Figura 2. A saída do comando.", 0.3 + ENTRELINHA, tamanho=8.5),
        linha("Outro parágrafo começa aqui.", 0.3 + ENTRELINHA * 2),
    ]
    assert resumo(montar(pagina))[-3:] == [
        ("paragrafo", "O parágrafo segue"),
        ("nota", "Figura 2. A saída do comando."),
        ("paragrafo", "Outro parágrafo começa aqui."),
    ]
