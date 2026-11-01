# SPDX-License-Identifier: GPL-3.0-or-later
"""Cabeçalho e rodapé pela posição na página (ADR-0004).

Os exemplos vêm do spike: no "Competente o Suficiente", número de página e título do livro e
do capítulo com letras espaçadas no alto; no "Hard Parts", "Chapter N: <título>" e o número
no rodapé.
"""

from __future__ import annotations

import pytest

from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginacao import LinhaRemovida, PaginasLimpas, tirar_cabecalhos_e_rodapes

ALTO = 0.03
PE = 0.96
MEIO = 0.5
ESPACADO = "C O M P E T E N T E   O   S U F I C I E N T E"


def _linha(texto: str, topo: float = MEIO, tamanho: float = 10.5) -> Linha:
    return Linha(texto, x=54, topo=topo, tamanho=tamanho)


def _corpo(numero: int) -> Linha:
    """Uma linha comprida de texto, que firma o tamanho do corpo (10,5 pt)."""
    return _linha(f"Texto corrido da página {numero}, longo como uma linha de livro.")


def _limpar(*paginas: list[Linha]) -> PaginasLimpas:
    return tirar_cabecalhos_e_rodapes(
        [Pagina(n, tuple(linhas)) for n, linhas in enumerate(paginas, 1)]
    )


def _textos(limpas: PaginasLimpas) -> list[list[str]]:
    return [[linha.texto for linha in pagina.linhas] for pagina in limpas.paginas]


def test_numero_de_pagina_no_alto_sai_quando_segue_a_paginacao() -> None:
    # A1 da auditoria: o número sozinho não prova nada; a sequência com o mesmo
    # deslocamento em três páginas, sim (no Competente, número impresso = página - 7).
    limpas = _limpar(*[[_linha(str(146 + n), ALTO), _corpo(n)] for n in (1, 2, 3)])
    assert [len(p.linhas) for p in limpas.paginas] == [1, 1, 1]
    assert [r.motivo for r in limpas.remocoes] == ["número de página"] * 3


def test_numeral_romano_no_pe_sai_quando_segue_a_paginacao() -> None:
    limpas = _limpar(
        *[[_corpo(n), _linha(romano, PE)] for n, romano in ((1, "xii"), (2, "xiii"), (3, "xiv"))]
    )
    assert [len(p.linhas) for p in limpas.paginas] == [1, 1, 1]


def test_titulo_corrente_espacado_no_alto_sai_quando_se_repete() -> None:
    limpas = _limpar(*[[_linha(ESPACADO, ALTO), _linha(f"Texto {n}.")] for n in (1, 2, 3)])
    assert _textos(limpas) == [["Texto 1."], ["Texto 2."], ["Texto 3."]]


def test_rodape_com_titulo_do_capitulo_e_numero_sai() -> None:
    paginas = [
        [_linha(f"Texto {n}."), _linha(f"Chapter 1: What Happens When | {n}", PE)]
        for n in (23, 24, 25)
    ]
    assert _textos(_limpar(*paginas)) == [["Texto 23."], ["Texto 24."], ["Texto 25."]]


def test_espaco_diferente_nao_separa_a_repeticao() -> None:
    variantes = [ESPACADO, "COMPETENTE O SUFICIENTE", "C O M P E T E N T E O S U F I C I E N T E"]
    limpas = _limpar(*[[_linha(v, ALTO), _linha("Texto.")] for v in variantes])
    assert _textos(limpas) == [["Texto."]] * 3


def test_linha_no_alto_em_duas_paginas_so_fica() -> None:
    # Duas vezes ainda pode ser texto do livro; três é numeração de página.
    paginas = [[_linha("Um aviso no alto", ALTO), _linha("Texto.")] for _ in range(2)]
    assert _textos(_limpar(*paginas)) == [["Um aviso no alto", "Texto."]] * 2


def test_linha_repetida_no_meio_da_pagina_fica() -> None:
    paginas = [[_linha("Texto."), _linha("* * *")] for _ in range(3)]
    assert _textos(_limpar(*paginas)) == [["Texto.", "* * *"]] * 3


def test_titulo_de_capitulo_unico_no_alto_fica() -> None:
    limpas = _limpar([_linha("Um gerador de texto muito bom", ALTO), _linha("Texto.")])
    assert _textos(limpas) == [["Um gerador de texto muito bom", "Texto."]]


def test_remocao_registra_pagina_motivo_e_texto() -> None:
    limpas = _limpar(
        *[
            [_linha(str(11 + n), ALTO), _linha("Texto."), _linha("Rodapé fixo", PE)]
            for n in (1, 2, 3)
        ]
    )
    assert limpas.remocoes == (
        LinhaRemovida(1, "número de página", "12"),
        LinhaRemovida(1, "rodapé de página repetido", "Rodapé fixo"),
        LinhaRemovida(2, "número de página", "13"),
        LinhaRemovida(2, "rodapé de página repetido", "Rodapé fixo"),
        LinhaRemovida(3, "número de página", "14"),
        LinhaRemovida(3, "rodapé de página repetido", "Rodapé fixo"),
    )


def test_numero_sozinho_no_meio_da_pagina_fica() -> None:
    # Um ano ou o item de uma lista no meio do texto não é número de página.
    limpas = _limpar([_linha("Texto."), _linha("1945"), _linha("Mais texto.")])
    assert _textos(limpas) == [["Texto.", "1945", "Mais texto."]]


def _paginas_numeradas(*extras: tuple[int, Linha]) -> list[list[Linha]]:
    """Cinco páginas com número impresso = página + 7 no pé, como no Competente (-7)."""
    paginas = [[_corpo(n), _linha(str(n + 7), PE)] for n in range(1, 6)]
    for numero, linha in extras:
        paginas[numero - 1].append(linha)
    return paginas


def test_numero_de_capitulo_grande_no_alto_fica() -> None:
    # A1 da auditoria: "3" em 48 pt na abertura do capítulo saía como número de página.
    limpas = _limpar(*_paginas_numeradas((2, _linha("3", ALTO, tamanho=48))))
    assert [linha.texto for linha in limpas.paginas[1].linhas] == [
        limpas.paginas[1].linhas[0].texto,
        "3",
    ]


def test_romano_grande_no_alto_fica() -> None:
    limpas = _limpar(*_paginas_numeradas((2, _linha("IV", ALTO, tamanho=24))))
    assert "IV" in [linha.texto for linha in limpas.paginas[1].linhas]


def test_numero_que_nao_segue_a_paginacao_fica() -> None:
    # A1 da auditoria: "2020." e "1." no pé saíam como número de página.
    limpas = _limpar(*_paginas_numeradas((3, _linha("2020.", PE)), (4, _linha("1.", PE))))
    sobra_no_pe = [linha.texto for p in limpas.paginas for linha in p.linhas if linha.topo == PE]
    assert sobra_no_pe == ["2020.", "1."]


def test_palavra_de_letras_romanas_fica() -> None:
    limpas = _limpar(*_paginas_numeradas((2, _linha("mix", ALTO)), (3, _linha("civil", ALTO))))
    sobra_no_alto = [
        linha.texto for p in limpas.paginas for linha in p.linhas if linha.topo == ALTO
    ]
    assert sobra_no_alto == ["mix", "civil"]


def test_titulo_repetido_em_fonte_grande_no_alto_fica() -> None:
    # A1 da auditoria: "Capítulo N" em 20 pt no alto de três aberturas saía como cabeçalho.
    paginas = [[_linha(f"Capítulo {n}", ALTO, tamanho=20), _corpo(n)] for n in (1, 2, 3)]
    assert [len(p.linhas) for p in _limpar(*paginas).paginas] == [2, 2, 2]


def test_linha_repetida_em_alturas_diferentes_fica() -> None:
    # Título de seção que cai no alto de três páginas, mas cada vez numa altura.
    paginas = [
        [_linha("Consequences", topo), _corpo(n)] for n, topo in ((1, 0.01), (2, 0.04), (3, 0.07))
    ]
    assert [len(p.linhas) for p in _limpar(*paginas).paginas] == [2, 2, 2]


def test_separador_sozinho_repetido_no_pe_sai_como_rodape() -> None:
    # No Hard Parts, 416 "|" sozinhos no rodapé.
    limpas = _limpar(*[[_corpo(n), _linha("|", PE)] for n in (1, 2, 3)])
    assert [r.motivo for r in limpas.remocoes] == ["rodapé de página repetido"] * 3


def test_cabecalho_repetido_no_alto_tem_o_motivo_de_cabecalho() -> None:
    limpas = _limpar(*[[_linha(ESPACADO, ALTO), _corpo(n)] for n in (1, 2, 3)])
    assert [r.motivo for r in limpas.remocoes] == ["cabeçalho de página repetido"] * 3


def test_caixa_diferente_nao_separa_a_repeticao() -> None:
    variantes = ["Competente o Suficiente", "COMPETENTE O SUFICIENTE", "competente o suficiente"]
    limpas = _limpar(*[[_linha(v, ALTO), _corpo(n)] for n, v in enumerate(variantes, 1)])
    assert len(limpas.remocoes) == 3


def test_numero_repetido_na_mesma_pagina_nao_conta_como_sequencia() -> None:
    # Revisão nº 2: duas páginas com o número no alto e no pé davam 4 ocorrências.
    paginas = [[_linha(str(n + 7), ALTO), _corpo(n), _linha(str(n + 7), PE)] for n in (1, 2)]
    assert [len(p.linhas) for p in _limpar(*paginas).paginas] == [3, 3]


def test_frase_que_alterna_entre_alto_e_pe_sai_dos_dois() -> None:
    # Revisão nº 3: com metade no alto e metade no pé, a mediana caía no meio da página.
    paginas = [[_linha("Competente", ALTO if n % 2 else PE), _corpo(n)] for n in range(1, 7)]
    assert [len(p.linhas) for p in _limpar(*paginas).paginas] == [1] * 6


def test_numero_decimal_no_pe_nao_vira_numero_de_pagina() -> None:
    # Revisão nº 5: o ponto como separador lia "1.2" como 12, coerente com a página 2.
    paginas = [[_corpo(n), _linha(f"1.{n}", topo)] for n, topo in ((1, 0.93), (2, 0.96), (3, 0.99))]
    assert [len(p.linhas) for p in _limpar(*paginas).paginas] == [2, 2, 2]


def test_linha_so_de_numero_que_nao_segue_a_paginacao_fica_mesmo_repetida() -> None:
    # O1 da pós-auditoria: "2020." no mesmo topo em 3 páginas virava "#." e saía como
    # rodapé repetido, mesmo reprovado na coerência da numeração.
    paginas = [[_corpo(n), _linha(f"{ano}.", PE)] for n, ano in ((1, 2020), (2, 1999), (3, 1984))]
    assert [len(p.linhas) for p in _limpar(*paginas).paginas] == [2, 2, 2]


@pytest.mark.parametrize("rodape", ["2021", "\u00a9 2020", "01/11/2026"])
def test_rodape_sem_letra_identico_em_toda_pagina_sai(rodape: str) -> None:
    # A3 da auditoria e revisão xhigh: o O1 pulava toda linha sem letra, e o rodapé fixo
    # ("2021", "\u00a9 2020", uma data) deixou de sair. O que o O1 separa são números
    # DIFERENTES que o "#" juntava; o mesmo texto em toda página é rodapé.
    paginas = [[_corpo(n), _linha(rodape, PE)] for n in range(1, 4)]
    assert [len(p.linhas) for p in _limpar(*paginas).paginas] == [1, 1, 1]


def test_mesma_frase_em_duas_alturas_da_mesma_faixa_sai_das_duas() -> None:
    # O2 da pós-auditoria: 3 páginas a 0,02 e 3 a 0,05 empatavam, a mediana caía entre as
    # duas alturas, e nada saía.
    paginas = [[_linha("Competente", 0.02 if n <= 3 else 0.05), _corpo(n)] for n in range(1, 7)]
    assert [len(p.linhas) for p in _limpar(*paginas).paginas] == [1] * 6


def test_frase_repetida_em_altura_minoritaria_tambem_sai() -> None:
    # O2: com 4 páginas numa altura e 3 noutra, só a maioria saía.
    paginas = [[_linha("Competente", 0.02 if n <= 4 else 0.05), _corpo(n)] for n in range(1, 8)]
    assert [len(p.linhas) for p in _limpar(*paginas).paginas] == [1] * 7
