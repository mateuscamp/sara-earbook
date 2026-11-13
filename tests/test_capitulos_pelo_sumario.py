# SPDX-License-Identifier: GPL-3.0-or-later
"""Os capítulos pelas aberturas do sumário interno do PDF (ADR-0004, "Capítulos pelo sumário
interno do PDF").

No Manica, o maior título em 3 páginas ou mais é resto de figura (82 pt), a parte vem em 55 pt e
o capítulo abre no número ("84.", 30 pt); o gabarito do fim do livro repete "Capítulo N".
"""

from __future__ import annotations

from earbook.dominio.blocos import Bloco
from earbook.dominio.capitulos import dividir_pelo_sumario
from earbook.dominio.sumario_interno import Abertura
from earbook.dominio.tipo_da_linha import TipoDeBloco


def _titulo(texto: str, pagina: int, tamanho: float = 30.0) -> Bloco:
    return Bloco(TipoDeBloco.TITULO, texto, pagina, tamanho)


def _paragrafo(texto: str, pagina: int) -> Bloco:
    return Bloco(TipoDeBloco.PARAGRAFO, texto, pagina, 9.3)


def _textos(capitulos: tuple[tuple[Bloco, ...], ...]) -> list[list[str]]:
    return [[bloco.texto for bloco in capitulo] for capitulo in capitulos]


def test_capitulo_abre_no_primeiro_titulo_da_pagina_que_o_sumario_diz() -> None:
    blocos = [
        _paragrafo("Prefácio.", 2),
        _paragrafo("Fim do prefácio, no alto da página.", 10),
        _titulo("1.", 10),
        _titulo("A história", 10, 23),
        _paragrafo("Texto do primeiro.", 10),
        _titulo("•", 12, 82.4),
        _paragrafo("Mais texto do primeiro.", 15),
        _titulo("2.", 20),
        _paragrafo("Texto do segundo.", 20),
    ]
    aberturas = (Abertura(10, "Capítulo 1. A história"), Abertura(20, "Capítulo 2. O ensino"))
    divisao = dividir_pelo_sumario(blocos, aberturas)
    assert _textos(divisao.capitulos) == [
        ["Prefácio.", "Fim do prefácio, no alto da página."],
        ["1.", "A história", "Texto do primeiro.", "•", "Mais texto do primeiro."],
        ["2.", "Texto do segundo."],
    ]
    assert divisao.nomes == (None, "Capítulo 1. A história", "Capítulo 2. O ensino")


def test_pagina_sem_titulo_abre_no_primeiro_bloco_dela() -> None:
    blocos = [
        _paragrafo("Dedicatória.", 3),
        _paragrafo("Agradeço a todos.", 5),
        _paragrafo("Prefácio sem título.", 7),
    ]
    aberturas = (Abertura(5, "Reconhecimento"), Abertura(7, "Prefácio"))
    divisao = dividir_pelo_sumario(blocos, aberturas)
    assert _textos(divisao.capitulos) == [
        ["Dedicatória."],
        ["Agradeço a todos."],
        ["Prefácio sem título."],
    ]
    assert divisao.nomes == (None, "Reconhecimento", "Prefácio")


def test_pagina_da_parte_fica_com_o_primeiro_capitulo_dela_e_o_nome_e_o_do_capitulo() -> None:
    blocos = [
        _paragrafo("Texto do capítulo anterior.", 8),
        _titulo("Parte II", 9, 55),
        _titulo("Gestão", 9, 48),
        _titulo("4.", 10),
        _paragrafo("Texto do quarto.", 10),
    ]
    aberturas = (Abertura(9, "Parte II - Gestão"), Abertura(10, "Capítulo 4. A gestão"))
    divisao = dividir_pelo_sumario(blocos, aberturas)
    assert _textos(divisao.capitulos) == [
        ["Texto do capítulo anterior."],
        ["Parte II", "Gestão", "4.", "Texto do quarto."],
    ]
    assert divisao.nomes == (None, "Capítulo 4. A gestão")


def test_rotulo_de_capitulo_dentro_do_anexo_nao_abre_capitulo() -> None:
    gabarito = [
        bloco
        for n in (1, 2, 3)
        for bloco in (_titulo(f"Capítulo {n}", 50 + n, 15), _paragrafo("Resposta: A.", 50 + n))
    ]
    blocos = [
        _titulo("1.", 10),
        _paragrafo("Texto do primeiro.", 10),
        _titulo("Anexo 1", 50),
        _paragrafo("Respostas das questões.", 50),
        *gabarito,
    ]
    aberturas = (Abertura(10, "Capítulo 1. A história"), Abertura(50, "Anexo 1. Respostas"))
    divisao = dividir_pelo_sumario(blocos, aberturas)
    assert [len(capitulo) for capitulo in divisao.capitulos] == [2, 8]
    assert divisao.nomes == ("Capítulo 1. A história", "Anexo 1. Respostas")


def test_abertura_em_pagina_que_saiu_inteira_abre_no_bloco_seguinte() -> None:
    # O sumário de papel (p. 19 a 22) sai como página de lista; o capítulo seguinte abre certo.
    blocos = [
        _paragrafo("Prefácio.", 18),
        _paragrafo("Uma linha que sobrou do sumário.", 22),
        _titulo("Parte I", 23, 55),
        _titulo("1.", 24),
        _paragrafo("Texto do primeiro.", 24),
    ]
    aberturas = (Abertura(19, "Sumário"), Abertura(23, "Parte I"), Abertura(24, "Capítulo 1"))
    divisao = dividir_pelo_sumario(blocos, aberturas)
    assert _textos(divisao.capitulos) == [
        ["Prefácio."],
        ["Uma linha que sobrou do sumário."],
        ["Parte I", "1.", "Texto do primeiro."],
    ]
    assert divisao.nomes == (None, "Sumário", "Capítulo 1")


def test_nivel_do_titulo_conta_do_tamanho_que_mais_abre_capitulo() -> None:
    blocos = [
        _titulo("Parte I", 9, 55),
        *[
            bloco
            for n in (1, 2, 3)
            for bloco in (
                _titulo(f"{n}.", 10 * n),
                _titulo("Título do capítulo", 10 * n, 23),
                _titulo("•", 10 * n + 1, 82.4),
                _titulo("Seção", 10 * n + 2, 15),
                _paragrafo("Texto.", 10 * n + 2),
            )
        ],
    ]
    aberturas = (Abertura(9, "Parte I"), *[Abertura(10 * n, f"Capítulo {n}") for n in (1, 2, 3)])
    divisao = dividir_pelo_sumario(blocos, aberturas)
    niveis = {bloco.texto: bloco.nivel for capitulo in divisao.capitulos for bloco in capitulo}
    assert niveis == {
        "Parte I": 1,
        "1.": 1,
        "2.": 1,
        "3.": 1,
        "•": 1,
        "Título do capítulo": 2,
        "Seção": 3,
        "Texto.": 0,
    }


def test_livro_que_comeca_na_primeira_abertura_nao_ganha_capitulo_vazio() -> None:
    blocos = [_titulo("Capa", 1, 64), _titulo("1.", 2), _paragrafo("Texto.", 2)]
    divisao = dividir_pelo_sumario(blocos, (Abertura(1, "Capa"), Abertura(2, "Capítulo 1")))
    assert _textos(divisao.capitulos) == [["Capa", "1.", "Texto."]]
    assert divisao.nomes == ("Capítulo 1",)
