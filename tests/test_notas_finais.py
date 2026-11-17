# SPDX-License-Identifier: GPL-3.0-or-later
"""A seção de notas finais do capítulo sai pela letra, pelo recuo e pela forma da entrada (ADR-0004,
"Notas finais do capítulo").

No fim de cada capítulo do Being You vem a seção "Notes", na letra das notas (12,5 pt, com o corpo
de 15): cada nota abre na margem com a frase do texto que ela comenta, seguida de dois-pontos
("global workspace theory: Baars (1988)…"), e continua com recuo pendente. Depois dela vêm as notas
de rodapé com símbolo ("* This paper…"), na mesma letra e mais recuadas, que ficam. O texto aqui é
sintético.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from earbook.comandos.cli import principal
from earbook.dominio.notas_finais import MOTIVO_DAS_NOTAS_FINAIS, tirar_notas_finais
from earbook.dominio.pagina import Linha, Pagina
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf

FAMILIA = "ArialMT"
MARGEM = 84.5
PENDENTE = 100.7
SIMBOLO = 106.3
DO_RODAPE = 125.7
PASSO = 0.004


def _linha(texto: str, *, x: float = MARGEM, tamanho: float = 15.0, fonte: str = FAMILIA) -> Linha:
    return Linha(texto, x=x, fim=500.0, topo=0.0, tamanho=tamanho, fonte=fonte)


def _nota(texto: str, x: float = MARGEM) -> Linha:
    return _linha(texto, x=x, tamanho=12.5)


def _corpo(n: int = 30, marca: str = "do texto") -> list[Linha]:
    # Linhas longas: a letra do corpo é a que tem mais caracteres no livro.
    texto = "Linha {k} {marca} corrido do livro, longa o bastante para a letra dela ser a do corpo."
    return [_linha(texto.format(k=k, marca=marca)) for k in range(n)]


def _entrada(n: int) -> list[Linha]:
    """Uma nota final em duas linhas: a chave, a citação autor-ano e a continuação pendente."""
    return [
        _nota(f"a frase número {n} do capítulo: Fulano ({1980 + n}); Beltrano & Sicrano"),
        _nota(f"({1990 + n}). Um comentário curto que continua na linha de baixo.", PENDENTE),
    ]


def _entradas(quantas: int, primeira: int = 1) -> list[Linha]:
    return [linha for n in range(primeira, primeira + quantas) for linha in _entrada(n)]


TITULO = _nota("Notas")
SECAO = [TITULO, *_entradas(10)]
RODAPE = [
    _nota("*", 108.4),
    _nota("Este artigo é um dos mais lidos da área, e o autor o comenta aqui.", DO_RODAPE),
    _nota("† Cada hemisfério tem quatro lobos, e alguns contam um quinto.", SIMBOLO),
    _nota("na continuação do rodapé, mais recuada que a nota final.", DO_RODAPE),
]
CAPITULO = _linha("Capítulo seguinte", tamanho=19.4)


def _paginas(*paginas: list[Linha]) -> list[Pagina]:
    """As páginas, com as linhas de cima para baixo na ordem em que foram dadas."""
    return [
        Pagina(
            numero,
            tuple(replace(linha, topo=0.05 + PASSO * k) for k, linha in enumerate(linhas)),
        )
        for numero, linhas in enumerate(paginas, 1)
    ]


def _sairam(*paginas: list[Linha]) -> list[str]:
    limpas = tirar_notas_finais(_paginas(*paginas))
    return [r.texto for r in limpas.remocoes]


def _ficam(*paginas: list[Linha]) -> list[str]:
    limpas = tirar_notas_finais(_paginas(*paginas))
    return [linha.texto for pagina in limpas.paginas for linha in pagina.linhas]


def _textos(linhas: list[Linha]) -> list[str]:
    return [linha.texto for linha in linhas]


def test_secao_de_notas_finais_sai_com_o_titulo() -> None:
    assert _sairam([*_corpo(), *SECAO]) == _textos(SECAO)


def test_secao_fica_registrada_com_a_pagina_e_o_motivo() -> None:
    limpas = tirar_notas_finais(_paginas(_corpo(), SECAO))
    assert {(r.pagina, r.motivo) for r in limpas.remocoes} == {(2, MOTIVO_DAS_NOTAS_FINAIS)}


def test_corpo_e_notas_de_rodape_com_simbolo_ficam() -> None:
    corpo = _corpo()
    assert _ficam([*corpo, *SECAO, *RODAPE]) == _textos([*corpo, *RODAPE])


def test_secao_que_atravessa_a_pagina_sai_inteira() -> None:
    assert _sairam([*_corpo(), TITULO, *_entradas(6)], _entradas(6, 7)) == _textos(
        [TITULO, *_entradas(12)]
    )


def test_formula_em_outra_letra_e_recuo_no_meio_da_nota_sai_com_ela() -> None:
    # "The rule itself: Here's how Bayes' rule is normally written:", a fórmula em MathJax de
    # 10,4 pt e a explicação dela com o recuo do rodapé, sem símbolo.
    formula = [
        _linha("p (H|D) = p(D|H)·p(H)", x=97.0, tamanho=10.4, fonte="MathJax_Main"),
        _nota("p(H|D) é a probabilidade da hipótese depois dos dados.", DO_RODAPE),
    ]
    secao = [TITULO, *_entradas(5), *formula, *_entradas(5, 6)]
    assert _sairam([*_corpo(), *secao, *RODAPE]) == _textos(secao)


def test_legenda_antes_do_titulo_fica() -> None:
    legenda = _nota("Fig. 7: A imagem de referência da figura 6.", 174.3)
    assert _ficam([*_corpo(), legenda, *SECAO])[-1] == legenda.texto


def test_secao_para_na_linha_do_tamanho_do_corpo() -> None:
    # A família do corpo muda em parte das linhas do Being You (Arial e ArialMT): a linha do
    # tamanho do corpo em outra família não fecha a corrida, e a seção para nela.
    outra = _linha("O capítulo seguinte começa aqui, numa família parecida.", fonte="Arial")
    assert _sairam([*_corpo(), *SECAO, outra, *_entradas(2, 20)]) == _textos(SECAO)


def test_nove_notas_com_chave_e_a_secao_fica() -> None:
    assert _sairam([*_corpo(), TITULO, *_entradas(9)]) == []


def test_chaves_sem_citacao_autor_ano_e_a_secao_fica() -> None:
    # O glossário em letra menor tem a mesma forma ("termo: definição"), sem citação.
    glossario = [
        _nota(f"termo número {n}: a definição dele, sem citar ninguém.") for n in range(12)
    ]
    assert _sairam([*_corpo(), _nota("Glossário"), *glossario]) == []


def test_bibliografia_com_poucas_chaves_na_margem_fica() -> None:
    # A lista de referências tem a mesma letra e o mesmo recuo pendente, mas a entrada abre pelo
    # autor ("Fulano, A. (1988). Título…"): o dois-pontos da editora não faz dela uma chave.
    referencias = [
        linha
        for n in range(30)
        for linha in (
            _nota(f"Fulano, A. B. ({1980 + n}). Um livro inventado número {n}."),
            _nota("Cidade: Editora Inventada.", PENDENTE),
        )
    ]
    pagina = [*_corpo(), _nota("Referências"), *_entradas(1), *referencias]
    assert _sairam(pagina) == []


def test_secao_curta_com_o_titulo_de_duas_secoes_provadas_sai() -> None:
    curta = [TITULO, *_entradas(1, 50)]
    paginas = ([*_corpo(), *curta, CAPITULO], [*_corpo(), *SECAO], [*_corpo(), *SECAO])
    assert _sairam(*paginas) == _textos([*curta, *SECAO, *SECAO])


def test_secao_curta_com_o_titulo_de_uma_secao_provada_so_fica() -> None:
    curta = [TITULO, *_entradas(1, 50)]
    assert _sairam([*_corpo(), *curta, CAPITULO], [*_corpo(), *SECAO]) == _textos(SECAO)


def test_secao_curta_com_outro_titulo_fica() -> None:
    curta = [_nota("Observações"), *_entradas(1, 50)]
    paginas = ([*_corpo(), *curta, CAPITULO], [*_corpo(), *SECAO], [*_corpo(), *SECAO])
    assert _sairam(*paginas) == _textos([*SECAO, *SECAO])


def test_livro_sem_familia_de_letra_fica() -> None:
    sem_familia = [replace(linha, fonte="") for linha in [*_corpo(), *SECAO]]
    assert _sairam(sem_familia) == []


def test_resumo_do_importar_pdf_conta_as_notas_finais(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpo = [
        LinhaDeTeste(
            f"Linha {n} do texto corrido do livro, longa o bastante para ser o corpo.",
            72,
            740 - 14 * n,
        )
        for n in range(12)
    ]
    titulo = LinhaDeTeste("Notas", 72, 560, tamanho=8)
    notas = [
        LinhaDeTeste(f"a frase {n} do capítulo: Fulano ({1980 + n}).", 72, 548 - 10 * n, tamanho=8)
        for n in range(1, 11)
    ]
    rodape = LinhaDeTeste("* Um comentário do autor, que o texto chama.", 90, 430, tamanho=8)
    pdf = montar_pdf(tmp_path / "livro.pdf", [[*corpo, titulo, *notas, rodape]])
    assert principal(["importar-pdf", str(pdf), "--epub", str(tmp_path / "livro.epub")]) == 0
    saida = capsys.readouterr().out
    assert (
        "11 linhas de notas finais do capítulo tiradas: chave em frase e citação autor-ano."
        in saida
    )


def test_linha_em_outra_margem_antes_das_chaves_nao_e_titulo() -> None:
    # Sem título na margem delas, a seção não abre: a legenda não sai como se fosse o título.
    legenda = _nota("Fig. 8: Outra imagem de referência.", 174.3)
    assert _sairam([*_corpo(), legenda, *_entradas(10)]) == []


def test_linha_em_outra_letra_na_margem_antes_das_chaves_nao_e_titulo() -> None:
    formula = _linha("x = y + z", tamanho=10.4, fonte="MathJax_Main")
    assert _sairam([*_corpo(), formula, *_entradas(10)]) == []


def test_secao_curta_com_o_titulo_provado_e_poucas_chaves_na_margem_fica() -> None:
    # O título que o livro provou, sobre um trecho que não é de notas com chave.
    trecho = [_nota(f"Fulano, A. ({1980 + n}). Um livro inventado.") for n in range(4)]
    curta = [TITULO, *_entradas(1, 50), *trecho]
    paginas = ([*_corpo(), *curta, CAPITULO], [*_corpo(), *SECAO], [*_corpo(), *SECAO])
    assert _sairam(*paginas) == _textos([*SECAO, *SECAO])


def test_secao_depois_de_legenda_seguida_de_nota_solta_sai() -> None:
    # A legenda em outra margem, com uma chave logo abaixo, não abre a seção: senão ela iria até o
    # fim da corrida, sem margem nenhuma, e engoliria a seção de verdade que vem depois.
    legenda = _nota("Fig. 8: Outra imagem de referência.", 174.3)
    assert _sairam([*_corpo(), legenda, *_entrada(0), *SECAO]) == _textos(SECAO)


def test_notas_de_uma_linha_sem_titulo_na_letra_delas_ficam() -> None:
    # O título é a linha que não é chave: a seção sem título na letra das notas não abre (o
    # limite declarado no ADR).
    uma_linha = [_nota(f"a frase {n} do capítulo: Fulano ({1980 + n}).") for n in range(12)]
    assert _sairam([*_corpo(), *uma_linha]) == []
