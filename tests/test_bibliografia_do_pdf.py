# SPDX-License-Identifier: GPL-3.0-or-later
"""A bibliografia do PDF sai pela letra, antes da ordem de leitura (ADR-0004, "Bibliografia pela
letra e rótulo com a caixa trocada").

No Miller, o corpo é StoneSerif de 9 pt e a bibliografia vem na mesma família, em 7,5 pt, uma
referência por linha, na coluna ao lado do fim da prosa: lida por altura, a página intercalava as
duas. No Manica, o corpo é Times New Roman de 9,3 pt e as referências, MyriadPro de 6 pt, depois
do título "referências" em MyriadPro negrito de 15 pt.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from earbook.comandos.cli import principal
from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.bibliografia_do_pdf import MOTIVO_DA_BIBLIOGRAFIA_DO_PDF, tirar_bibliografia
from earbook.dominio.pagina import Linha, Pagina
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf

CORPO = "StoneSerif"
SEM_SERIFA = "StoneSans"


def _linha(
    texto: str,
    topo: float,
    *,
    fonte: str = CORPO,
    tamanho: float = 9.0,
    x: float = 42.0,
) -> Linha:
    return Linha(texto, x=x, fim=x + 248, topo=topo, tamanho=tamanho, fonte=fonte)


def _negrito(linha: Linha) -> Linha:
    return replace(linha, negrito=True)


def _corpo(topo: float, n: int = 12) -> list[Linha]:
    # Linhas longas: a letra do corpo é a que tem mais caracteres no livro.
    texto = (
        "Texto corrido da linha {k} do livro, longo o bastante para a letra dele ser a do corpo."
    )
    return [_linha(texto.format(k=k), topo + 0.013 * k) for k in range(n)]


def _referencia(
    n: int, topo: float, texto: str = "{n}. Autor AB, et al: Rev Sint {n}:{p}, 1999."
) -> Linha:
    return _linha(texto.format(n=n, p=100 + n), topo, tamanho=7.5, x=306.0)


def _lista(de: int, ate: int, topo: float = 0.3, **opcoes: str) -> list[Linha]:
    return [_referencia(n, topo + 0.011 * (n - de), **opcoes) for n in range(de, ate + 1)]


TITULO = _negrito(_linha("BiBliografía", 0.28, fonte=SEM_SERIFA, tamanho=7.7, x=306.0))


def _motivos(*paginas: list[Linha]) -> list[tuple[int, str, str]]:
    limpas = tirar_bibliografia([Pagina(n, tuple(linhas)) for n, linhas in enumerate(paginas, 1)])
    return [(r.pagina, r.motivo, r.texto) for r in limpas.remocoes]


def _sairam(*paginas: list[Linha]) -> list[str]:
    return [texto for _, _, texto in _motivos(*paginas)]


def _textos(linhas: list[Linha]) -> list[str]:
    return [linha.texto for linha in linhas]


def test_dez_referencias_em_letra_menor_e_o_titulo_em_negrito_saem_registrados() -> None:
    lista = _lista(1, 10)
    pagina = [*_corpo(0.1), TITULO, *lista]
    limpas = tirar_bibliografia([Pagina(7, tuple(pagina))])
    assert [linha.texto for linha in limpas.paginas[0].linhas] == _textos(_corpo(0.1))
    assert [(r.pagina, r.motivo, r.texto) for r in limpas.remocoes] == [
        (7, MOTIVO_DA_BIBLIOGRAFIA_DO_PDF, texto) for texto in _textos([TITULO, *lista])
    ]


def test_nove_linhas_de_citacao_ficam() -> None:
    assert _motivos([*_corpo(0.1), TITULO, *_lista(1, 9)]) == []


def test_a_citacao_com_ano_ponto_e_virgula_volume_e_pagina_conta() -> None:
    vancouver = _lista(1, 10, texto="{n}. Autor AB. Título. Rev Sint. 2004;{n}:{p}-9.")
    assert _sairam([*_corpo(0.1), *vancouver]) == _textos(vancouver)


def test_a_linha_sem_citacao_no_meio_da_lista_sai_com_ela() -> None:
    # A referência de livro e a continuação da referência longa não têm volume nem página.
    continuacao = _referencia(0, 0.355, "portal and healthcare information systems.")
    lista = [*_lista(1, 5), continuacao, *_lista(6, 10, topo=0.37)]
    assert _sairam([*_corpo(0.1), *lista]) == _textos(lista)


def test_o_titulo_em_letra_de_titulo_logo_acima_sai_junto() -> None:
    # Manica: "referências" em negrito de 15 pt fecha a corrida, e ficaria lido sozinho.
    titulo = _negrito(_linha("referências", 0.27, fonte="MyriadPro", tamanho=15.0, x=306.0))
    lista = _lista(1, 10)
    assert _sairam([*_corpo(0.1), titulo, *lista]) == _textos([titulo, *lista])


def test_a_linha_em_negrito_de_outra_letra_acima_do_titulo_fica() -> None:
    # R2 da code-review: o subtítulo em negrito da prosa, logo acima do título da lista, não é
    # a segunda linha do título dela.
    subtitulo = _negrito(_linha("Agradecimientos", 0.26, tamanho=9.0, x=306.0))
    lista = _lista(1, 10)
    assert _sairam([*_corpo(0.1), subtitulo, TITULO, *lista]) == _textos([TITULO, *lista])


def test_o_titulo_em_duas_linhas_da_mesma_letra_sai_inteiro() -> None:
    segunda = _negrito(_linha("y lecturas", 0.29, fonte=SEM_SERIFA, tamanho=7.7, x=306.0))
    lista = _lista(1, 10)
    assert _sairam([*_corpo(0.1), TITULO, segunda, *lista]) == _textos([TITULO, segunda, *lista])


def test_o_titulo_que_fica_abaixo_da_lista_na_pagina_nao_e_dela() -> None:
    # O título do pé da coluna da esquerda vem antes, na ordem do PDF, da lista que abre o alto
    # da coluna da direita: é o título de outra seção ("Questão de prova").
    titulo = _negrito(_linha("Questão de prova", 0.9, fonte="MyriadPro", tamanho=15.0))
    lista = _lista(1, 10)
    assert _sairam([*_corpo(0.1), titulo, *lista]) == _textos(lista)


def test_a_linha_do_corpo_logo_antes_da_lista_fica() -> None:
    aviso = _linha("Bibliografía completa disponible online.", 0.27, x=306.0)
    lista = _lista(1, 10)
    assert _sairam([*_corpo(0.1), aviso, *lista]) == _textos(lista)


def test_a_caixa_em_outra_letra_antes_da_lista_fica() -> None:
    # Miller: os objetivos e as listas de recursos, em StoneSans de 8 pt, na mesma corrida.
    caixa = [
        _linha(f"Objetivo {k} del capítulo.", 0.2 + 0.012 * k, fonte=SEM_SERIFA, tamanho=8.0)
        for k in range(5)
    ]
    lista = _lista(1, 10)
    assert _sairam([*_corpo(0.02), *caixa, TITULO, *lista]) == _textos([TITULO, *lista])


def test_o_cabecalho_da_pagina_online_entre_as_referencias_sai_com_elas() -> None:
    cabecalho = [
        _linha("Capítulo 2: Ámbito de la anestesia", 0.04, fonte=SEM_SERIFA),
        _negrito(_linha("47.e1", 0.04, fonte=SEM_SERIFA, tamanho=10.0, x=540.0)),
    ]
    primeira, segunda = _lista(1, 10), _lista(11, 14, topo=0.08)
    assert _sairam([*_corpo(0.1), *primeira], [*cabecalho, *segunda]) == _textos(
        [*primeira, *cabecalho, *segunda]
    )


def test_quatro_linhas_de_outra_letra_partem_o_trecho() -> None:
    caixa = [
        _linha(f"Recurso {k} en la red.", 0.5 + 0.012 * k, fonte=SEM_SERIFA, tamanho=8.0)
        for k in range(4)
    ]
    primeira, resto = _lista(1, 10), _lista(11, 14, topo=0.6)
    assert _sairam([*_corpo(0.1), *primeira, *caixa, *resto]) == _textos(primeira)


def test_dois_trechos_de_nove_citacoes_na_mesma_corrida_ficam() -> None:
    # As 10 citações contam por trecho, e não pela corrida inteira.
    caixa = [
        _linha(f"Recurso {k} en la red.", 0.5 + 0.012 * k, fonte=SEM_SERIFA, tamanho=8.0)
        for k in range(4)
    ]
    assert _motivos([*_corpo(0.1), *_lista(1, 9), *caixa, *_lista(10, 18, topo=0.6)]) == []


def test_a_lista_continua_na_pagina_seguinte() -> None:
    primeira, segunda = _lista(1, 6), _lista(7, 12, topo=0.05)
    depois = _corpo(0.5, 3)
    assert _sairam([*_corpo(0.1), *primeira], [*segunda, *depois]) == _textos([*primeira, *segunda])


def test_as_citacoes_na_letra_do_corpo_ficam() -> None:
    lista = [
        _linha(f"{n}. Autor AB, et al: Rev Sint {n}:{100 + n}, 1999.", 0.3 + 0.013 * n)
        for n in range(12)
    ]
    assert _motivos([*_corpo(0.1), *lista]) == []


def test_as_citacoes_em_outra_familia_do_tamanho_do_corpo_ficam() -> None:
    lista = [
        _linha(
            f"{n}. Autor AB, et al: Rev Sint {n}:{100 + n}, 1999.",
            0.3 + 0.013 * n,
            fonte=SEM_SERIFA,
        )
        for n in range(12)
    ]
    assert _motivos([*_corpo(0.1), *lista]) == []


def test_o_pdf_que_nao_diz_a_familia_da_letra_nao_muda() -> None:
    corpo = [_linha(f"Texto corrido {k}.", 0.1 + 0.013 * k, fonte="") for k in range(12)]
    lista = [
        _linha(
            f"{n}. Autor AB: Rev Sint {n}:{100 + n}, 1999.", 0.5 + 0.011 * n, fonte="", tamanho=7.5
        )
        for n in range(12)
    ]
    assert _motivos([*corpo, *lista]) == []


def test_importar_pdf_tira_a_bibliografia_e_o_resumo_a_conta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpo = [
        LinhaDeTeste(
            f"Linha {n} do texto corrido do livro, longa o bastante para ser o corpo.",
            72,
            700 - 14 * n,
            serifa=True,
        )
        for n in range(12)
    ]
    lista = [
        LinhaDeTeste(
            f"{n}. Autor AB, et al: Rev Sint {n}:{100 + n}, 1999.",
            72,
            500 - 9 * n,
            tamanho=7.5,
            serifa=True,
        )
        for n in range(1, 11)
    ]
    pdf = montar_pdf(tmp_path / "livro.pdf", [[*corpo, *lista]])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub")
    assert [(r.motivo, r.texto) for r in importacao.remocoes] == [
        (MOTIVO_DA_BIBLIOGRAFIA_DO_PDF, linha.texto) for linha in lista
    ]
    assert principal(["importar-pdf", str(pdf), "--epub", str(tmp_path / "outro.epub")]) == 0
    saida = capsys.readouterr().out
    assert "0 linhas tiradas da página: a borda, o texto escondido e o texto repetido." in saida
    assert (
        "10 linhas de bibliografia tiradas: letra menor que a do corpo, com citações de periódico."
        in saida
    )
