# SPDX-License-Identifier: GPL-3.0-or-later
"""A nota de rodapé na letra das referências, logo antes do título da lista, fica (ADR-0004,
"Camada do OCR sobre as figuras e chamada colada").

No Bonica, a nota do autor vem no fim do capítulo, na letra das referências (Times New Roman de
11,2 pt, com o corpo de 15), seguida do título "References" em negrito e da lista. A regra da
bibliografia pela letra levava a nota com a lista: 7 notas, 746 palavras de prosa.
"""

from __future__ import annotations

from dataclasses import replace

from earbook.dominio.bibliografia_do_pdf import tirar_bibliografia
from earbook.dominio.pagina import Linha, Pagina

CORPO = "TimesNewRomanPSMT"
NEGRITO = "TimesNewRomanPS"


def _linha(texto: str, topo: float, *, fonte: str = CORPO, tamanho: float = 15.0) -> Linha:
    return Linha(texto, x=72.0, fim=540.0, topo=topo, tamanho=tamanho, fonte=fonte)


def _corpo(topo: float, n: int = 12) -> list[Linha]:
    texto = (
        "Texto corrido da linha {k} do livro, longo o bastante para a letra dele ser a do corpo."
    )
    return [_linha(texto.format(k=k), topo + 0.013 * k) for k in range(n)]


def _pequena(texto: str, topo: float) -> Linha:
    return _linha(texto, topo, tamanho=11.2)


NOTA = [
    _pequena("*Convém lembrar que as teorias da dor como sentido próprio", 0.30),
    _pequena("nasceram do estudo da pele, e não das vísceras.", 0.32),
]
TITULO = replace(_linha("Referências", 0.36, fonte=NEGRITO), negrito=True)


def _lista(topo: float, n: int = 12) -> list[Linha]:
    return [
        _pequena(
            f"{k}. Autor AB, Outro CD. Título do artigo. Rev Sint 1999;{k}:10-{k + 20}.",
            topo + 0.02 * k,
        )
        for k in range(1, n + 1)
    ]


def _sairam(*linhas: Linha) -> list[str]:
    limpas = tirar_bibliografia([Pagina(1, tuple(linhas))])
    return [r.texto for r in limpas.remocoes]


def test_nota_antes_do_titulo_da_lista_fica_e_a_lista_sai() -> None:
    lista = _lista(0.38)
    assert _sairam(*_corpo(0.1), *NOTA, TITULO, *lista) == [
        TITULO.texto,
        *[linha.texto for linha in lista],
    ]


def test_primeira_referencia_em_duas_linhas_sai_inteira() -> None:
    # A linha sem citação que abre a primeira referência é da lista: não há título entre elas.
    abre = _pequena("1. Autor AB. Um livro sobre a dor, com o título em duas linhas:", 0.38)
    lista = _lista(0.40)
    assert _sairam(*_corpo(0.1), TITULO, abre, *lista)[1] == abre.texto


def test_cabecalho_em_negrito_no_meio_da_lista_nao_a_parte() -> None:
    # O cabeçalho da página de bibliografia online (Miller): vem depois da primeira citação.
    cabecalho = replace(
        _linha("Capítulo 2: A dor", 0.60, fonte=NEGRITO, tamanho=11.0), negrito=True
    )
    lista = _lista(0.38)
    saem = _sairam(*_corpo(0.1), TITULO, *lista[:6], cabecalho, *lista[6:])
    esperado = [TITULO, *lista[:6], cabecalho, *lista[6:]]
    assert saem == [linha.texto for linha in esperado]


def test_referencias_antes_de_um_subtitulo_saem_com_a_lista() -> None:
    # As "Leituras sugeridas" com citação, antes do subtítulo: são da lista, e não nota.
    leituras = [
        _pequena(f"Autor EF. Leitura sugerida número {k}. Rev Sint 2001;{k}:1-9.", 0.30 + 0.02 * k)
        for k in range(1, 3)
    ]
    lista = _lista(0.40)
    saem = _sairam(*_corpo(0.1), *leituras, TITULO, *lista)
    assert saem[:2] == [linha.texto for linha in leituras]
