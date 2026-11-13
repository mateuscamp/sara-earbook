# SPDX-License-Identifier: GPL-3.0-or-later
"""O hífen gravado como U+00AD volta a ser hífen (ADR-0004, "Tratado em português e em espanhol").

No Manica e no Miller o hífen de verdade vem como U+00AD no meio da linha, e a voz colava as duas
metades. No Competente ele só aparece no fim da linha, onde é o hífen da quebra.
"""

from __future__ import annotations

from earbook.dominio.hifen_da_quebra import mostrar_hifen_invisivel
from earbook.dominio.pagina import Pagina
from tests.linhas_de_teste import ENTRELINHA, linha, montar, resumo, texto_corrido

INVISIVEL = "\u00ad"


def _pagina(*textos: str) -> Pagina:
    return Pagina(1, tuple(linha(texto, 0.1 + ENTRELINHA * n) for n, texto in enumerate(textos)))


def _textos(paginas: tuple[Pagina, ...]) -> list[str]:
    return [linha.texto for pagina in paginas for linha in pagina.linhas]


def test_hifen_invisivel_no_meio_da_linha_vira_hifen() -> None:
    pagina = _pagina(f"A meia{INVISIVEL}vida no pós{INVISIVEL}operatório (tabela 6{INVISIVEL}1).")
    assert _textos(mostrar_hifen_invisivel([pagina])) == [
        "A meia-vida no pós-operatório (tabela 6-1)."
    ]


def test_hifen_invisivel_antes_de_espaco_no_meio_da_linha_vira_hifen() -> None:
    pagina = _pagina(f"No pré{INVISIVEL} e no pós-operatório.")
    assert _textos(mostrar_hifen_invisivel([pagina])) == ["No pré- e no pós-operatório."]


def test_hifen_invisivel_do_fim_da_linha_vira_hifen_no_livro_que_o_usa_no_meio() -> None:
    pagina = _pagina(
        f"A meia{INVISIVEL}vida curta.",
        f"O pós{INVISIVEL}operatório longo.",
        f"O bloqueio β{INVISIVEL}adrenérgico.",
        f"A recupe{INVISIVEL}",
        "ração é lenta.",
    )
    assert _textos(mostrar_hifen_invisivel([pagina]))[3:] == ["A recupe-", "ração é lenta."]


def test_hifen_invisivel_so_no_fim_da_linha_continua_como_veio() -> None:
    # Competente: o U+00AD só aparece no fim da linha, e o `blocos` o tira sem consultar o livro.
    pagina = _pagina(f"A recupe{INVISIVEL}", "ração é lenta.", f"A anes{INVISIVEL}", "tesia geral.")
    assert _textos(mostrar_hifen_invisivel([pagina])) == [linha.texto for linha in pagina.linhas]


def test_duas_linhas_com_hifen_invisivel_no_meio_nao_mudam_o_do_fim() -> None:
    pagina = _pagina(
        f"A meia{INVISIVEL}vida curta.", f"O pós{INVISIVEL}operatório.", f"A recupe{INVISIVEL}"
    )
    assert _textos(mostrar_hifen_invisivel([pagina])) == [
        "A meia-vida curta.",
        "O pós-operatório.",
        f"A recupe{INVISIVEL}",
    ]


def test_numero_partido_no_hifen_do_fim_da_linha_volta_inteiro() -> None:
    # Miller: "tabla 6-" | "1" e a faixa de páginas "684-" | "696".
    topo = 0.4
    livro = montar(
        [
            *texto_corrido(0.1),
            linha("Os resultados estão na tabela 6-", topo),
            linha("1 e nas páginas 684-", topo + ENTRELINHA),
            linha("696 do livro.", topo + 2 * ENTRELINHA),
        ]
    )
    assert resumo(livro)[-1] == (
        "paragrafo",
        "Os resultados estão na tabela 6-1 e nas páginas 684-696 do livro.",
    )


def test_letra_e_hifen_no_fim_da_linha_antes_de_numero_segue_com_espaco() -> None:
    # Só o algarismo dos dois lados prova o número partido: "pré-" | "2010" não é faixa.
    topo = 0.4
    livro = montar(
        [
            *texto_corrido(0.1),
            linha("Os estudos da fase pré-", topo),
            linha("2010 eram menores.", topo + ENTRELINHA),
        ]
    )
    assert resumo(livro)[-1] == ("paragrafo", "Os estudos da fase pré- 2010 eram menores.")
