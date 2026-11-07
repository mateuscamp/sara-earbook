# SPDX-License-Identifier: GPL-3.0-or-later
"""Cabeçalho e número de página fora da faixa de 8% (ADR-0004, "Cabeçalho fora da faixa").

No Maudlin (*Philosophy of Physics: Quantum Theory*, 396 x 612 pt), o cabeçalho corrente fica a
13,6% do alto, acima de onde o corpo começa (17%), e o número de página fica na margem de fora,
a 81% da altura, ao lado da coluna do corpo. Os dois caíam no meio das frases: "what 5 Chapter 1
we want".
"""

from __future__ import annotations

from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginacao import PaginasLimpas, tirar_cabecalhos_e_rodapes

ESQUERDA = 99.0
DIREITA = 359.0
PRIMEIRA_DO_CORPO = 0.17
ACIMA_DA_MANCHA = 0.136
AO_LADO = 392.0
ALTURA_DO_NUMERO = 0.808


def _corpo(topo: float) -> Linha:
    return Linha(
        "texto corrido do livro, longo como uma linha de prosa",
        x=ESQUERDA,
        fim=DIREITA,
        topo=topo,
        tamanho=10,
    )


def _pagina(numero: int, *extras: Linha) -> Pagina:
    corpo = [_corpo(PRIMEIRA_DO_CORPO + i * 0.018) for i in range(30)]
    return Pagina(numero, (*extras, *corpo))


def _extra(texto: str, topo: float, x: float = ESQUERDA, tamanho: float = 9) -> Linha:
    return Linha(texto, x=x, fim=x + 8 * len(texto), topo=topo, tamanho=tamanho)


def _sobras(limpas: PaginasLimpas) -> list[list[str]]:
    return [
        [linha.texto for linha in pagina.linhas if not linha.texto.startswith("texto corrido")]
        for pagina in limpas.paginas
    ]


def test_cabecalho_acima_da_mancha_sai_quando_se_repete() -> None:
    paginas = [_pagina(n, _extra("Chapter 2", ACIMA_DA_MANCHA)) for n in (1, 2, 3)]
    limpas = tirar_cabecalhos_e_rodapes(paginas)
    assert _sobras(limpas) == [[], [], []]
    assert [r.motivo for r in limpas.remocoes] == ["cabeçalho de página repetido"] * 3


def test_numero_ao_lado_da_coluna_sai_quando_segue_a_paginacao() -> None:
    paginas = [_pagina(n, _extra(str(n + 17), ALTURA_DO_NUMERO, x=AO_LADO)) for n in (1, 2, 3)]
    limpas = tirar_cabecalhos_e_rodapes(paginas)
    assert _sobras(limpas) == [[], [], []]
    assert [r.motivo for r in limpas.remocoes] == ["número de página"] * 3


def test_numero_na_margem_de_dentro_tambem_sai() -> None:
    # Nas páginas pares do Maudlin, o número fica à esquerda da coluna (x 62).
    paginas = [_pagina(n, _extra(str(n + 17), ALTURA_DO_NUMERO, x=62)) for n in (1, 2, 3)]
    assert _sobras(tirar_cabecalhos_e_rodapes(paginas)) == [[], [], []]


def test_numero_dentro_da_coluna_fica_mesmo_seguindo_a_paginacao() -> None:
    # Na coluna, à mesma altura, o número é do texto: um ano, um item, um pedaço de fórmula.
    paginas = [_pagina(n, _extra(str(n + 17), ALTURA_DO_NUMERO)) for n in (1, 2, 3)]
    assert _sobras(tirar_cabecalhos_e_rodapes(paginas)) == [["18"], ["19"], ["20"]]


def test_linha_repetida_no_alto_da_mancha_fica() -> None:
    # Hard Parts: o cabeçalho de tabela "Advantage Disadvantage" abre três páginas, na altura
    # em que o corpo começa. Não está acima da mancha, e é texto do livro.
    tabela = _extra("Advantage Disadvantage", PRIMEIRA_DO_CORPO, tamanho=10)
    paginas = [_pagina(n, tabela) for n in (1, 2, 3)]
    assert _sobras(tirar_cabecalhos_e_rodapes(paginas)) == [["Advantage Disadvantage"]] * 3


def test_texto_repetido_ao_lado_da_coluna_fica() -> None:
    # Ao lado da coluna, só o número de página sai: a nota de margem que se repete é do livro.
    paginas = [_pagina(n, _extra("Veja o quadro", ALTURA_DO_NUMERO, x=AO_LADO)) for n in (1, 2, 3)]
    assert _sobras(tirar_cabecalhos_e_rodapes(paginas)) == [["Veja o quadro"]] * 3


def test_titulo_unico_acima_da_mancha_fica() -> None:
    paginas = [_pagina(1, _extra("Eight Experiments", ACIMA_DA_MANCHA)), _pagina(2), _pagina(3)]
    assert _sobras(tirar_cabecalhos_e_rodapes(paginas)) == [["Eight Experiments"], [], []]


def test_cabecalho_e_numero_do_tamanho_do_corpo_tambem_saem() -> None:
    # R1 da auditoria: do tamanho do corpo, uma linha curta por página entrava na mancha e a
    # alargava até ela. A mancha se mede pelas linhas largas.
    paginas = [
        _pagina(
            n,
            _extra("Chapter 2", ACIMA_DA_MANCHA, tamanho=10),
            _extra(str(n + 17), ALTURA_DO_NUMERO, x=AO_LADO, tamanho=10),
        )
        for n in (1, 2, 3)
    ]
    assert _sobras(tirar_cabecalhos_e_rodapes(paginas)) == [[], [], []]


def test_numero_repetido_ao_lado_da_coluna_que_nao_segue_a_paginacao_fica() -> None:
    # R2 da auditoria: ao lado da coluna, só a regra do número de página vale. O "x" do eixo de
    # uma figura, na mesma altura em três páginas, não é rodapé.
    paginas = [_pagina(n, _extra("x", 0.5, x=AO_LADO)) for n in (1, 2, 3)]
    assert _sobras(tirar_cabecalhos_e_rodapes(paginas)) == [["x"]] * 3


def test_epigrafe_do_tamanho_do_corpo_no_alto_nao_desloca_a_mancha() -> None:
    # T1 da auditoria: o percentil 1, e não o extremo. Com 120 linhas do corpo, a epígrafe acima
    # do cabeçalho é a primeira da lista, e o cabeçalho continua acima da mancha.
    epigrafe = Linha(
        "uma epígrafe longa, do tamanho do corpo, no alto",
        x=ESQUERDA,
        fim=DIREITA,
        topo=0.10,
        tamanho=10,
    )
    paginas = [_pagina(n, _extra("Chapter 2", ACIMA_DA_MANCHA)) for n in (1, 2, 3, 4)]
    paginas[0] = _pagina(1, epigrafe, _extra("Chapter 2", ACIMA_DA_MANCHA))
    assert _sobras(tirar_cabecalhos_e_rodapes(paginas)) == [[epigrafe.texto], [], [], []]


def test_linha_do_corpo_que_passa_da_margem_nao_desloca_a_mancha() -> None:
    # T1 da auditoria: a margem direita também pelo percentil. A linha que avança sobre a margem
    # (uma equação larga) não leva a mancha até o número de página.
    larga = Linha(
        "uma equação larga que avança sobre a margem", x=ESQUERDA, fim=400, topo=0.5, tamanho=10
    )
    paginas = [_pagina(n, _extra(str(n + 17), ALTURA_DO_NUMERO, x=AO_LADO)) for n in (1, 2, 3, 4)]
    paginas[1] = _pagina(2, larga, _extra("19", ALTURA_DO_NUMERO, x=AO_LADO))
    assert _sobras(tirar_cabecalhos_e_rodapes(paginas)) == [[], [larga.texto], [], []]


def test_cabecalho_largo_em_letra_menor_que_o_corpo_sai() -> None:
    # Só a linha do tamanho do corpo mede a mancha: o cabeçalho que atravessa a coluna, em 9 pt,
    # é largo, e entraria nela se a tolerância de tamanho fosse frouxa.
    largo = Linha(
        "Chapter 2 · Eight Experiments", x=ESQUERDA, fim=DIREITA, topo=ACIMA_DA_MANCHA, tamanho=9
    )
    paginas = [_pagina(n, largo) for n in (1, 2, 3)]
    assert _sobras(tirar_cabecalhos_e_rodapes(paginas)) == [[], [], []]
