# SPDX-License-Identifier: GPL-3.0-or-later
"""A corrida continua sendo examinada depois do fim da tabela (ADR-0004, "Camada do OCR sobre as
figuras e chamada colada").

No Manica, a letra grande da camada do OCR fechava a corrida de linhas fora da letra do corpo. Sem
ela a corrida ficou mais longa, e a regra parava no primeiro rótulo de tabela: a figura da página
seguinte, na mesma corrida, deixava de ser vista, e a legenda dela voltava a ser lida.
"""

from __future__ import annotations

from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.tabelas_e_figuras import (
    MOTIVO_DA_FIGURA,
    MOTIVO_DA_TABELA,
    tirar_tabelas_e_figuras,
)

CORPO = "AGaramondPro"


def _linha(texto: str, topo: float, *, fonte: str = CORPO, tamanho: float = 10.0) -> Linha:
    return Linha(texto, x=42.0, fim=296.0, topo=topo, tamanho=tamanho, fonte=fonte)


def _corpo(topo: float, n: int = 12) -> list[Linha]:
    return [_linha(f"Texto corrido da linha {k} do livro.", topo + 0.014 * k) for k in range(n)]


def _tabela(topo: float) -> list[Linha]:
    return [
        _linha("Tabela 2.1 Eixos da dor", topo, fonte="MyriadPro", tamanho=9.0),
        _linha("Eixo I", topo + 0.02, fonte="MyriadPro", tamanho=8.0),
        _linha("Regiões", topo + 0.04, fonte="MyriadPro", tamanho=8.0),
    ]


def _figura(topo: float) -> list[Linha]:
    """Na página seguinte, noutra letra: a tabela acaba aqui, e a corrida segue."""
    return [
        _linha("Dor crônica", topo, fonte="Helvetica", tamanho=6.5),
        _linha(
            "Figura 2.2 Classificação da dor crônica.", topo + 0.03, fonte="Helvetica", tamanho=7.5
        ),
        _linha("Fonte: adaptada de Fulano.", topo + 0.05, fonte="Helvetica", tamanho=7.5),
    ]


def test_figura_depois_da_tabela_na_mesma_corrida_sai() -> None:
    paginas = [Pagina(1, (*_corpo(0.1), *_tabela(0.8))), Pagina(2, (*_figura(0.1), *_corpo(0.3)))]
    limpas = tirar_tabelas_e_figuras(paginas)
    assert [linha.texto for pagina in limpas.paginas for linha in pagina.linhas] == [
        linha.texto for linha in (*_corpo(0.1), *_corpo(0.3))
    ]
    assert [(r.pagina, r.motivo) for r in limpas.remocoes] == [
        *[(1, MOTIVO_DA_TABELA)] * 3,
        *[(2, MOTIVO_DA_FIGURA)] * 3,
    ]


def test_segunda_tabela_depois_do_fim_da_primeira_sai() -> None:
    outra = [
        _linha("Quadro 2.3 Sinais de alerta", 0.1, fonte="Helvetica", tamanho=7.5),
        _linha("Febre", 0.12, fonte="Helvetica", tamanho=7.5),
    ]
    paginas = [Pagina(1, (*_corpo(0.1), *_tabela(0.8))), Pagina(2, (*outra, *_corpo(0.3)))]
    limpas = tirar_tabelas_e_figuras(paginas)
    assert [(r.pagina, r.motivo, r.texto) for r in limpas.remocoes][3:] == [
        (2, MOTIVO_DA_TABELA, "Quadro 2.3 Sinais de alerta"),
        (2, MOTIVO_DA_TABELA, "Febre"),
    ]


def test_caixa_sem_rotulo_depois_do_fim_da_tabela_fica() -> None:
    caixa = [
        _linha("Pontos-chave", 0.1, fonte="Helvetica", tamanho=7.5),
        _linha("A dor crônica dura mais de três meses.", 0.12, fonte="Helvetica", tamanho=7.5),
    ]
    paginas = [Pagina(1, (*_corpo(0.1), *_tabela(0.8))), Pagina(2, (*caixa, *_corpo(0.3)))]
    limpas = tirar_tabelas_e_figuras(paginas)
    assert [linha.texto for linha in limpas.paginas[1].linhas][:2] == [
        "Pontos-chave",
        "A dor crônica dura mais de três meses.",
    ]
