# SPDX-License-Identifier: GPL-3.0-or-later
"""O título da coluna da esquerda que abre uma faixa da largura da página (ADR-0004, "Duas
colunas" e "Título que atravessa as colunas").

Practical p. 203: "Summary" e "Key Points" ficam na coluna da esquerda, mas abrem uma faixa nova
da largura da página. A coluna da direita para logo acima deles, e o texto da esquerda logo acima
do título continua no alto da direita ("…redirect care" | "temporarily to another…"). Lida coluna
a coluna, a página intercalava os pontos-chave com a prosa.
"""

from __future__ import annotations

from dataclasses import replace

from earbook.dominio.colunas import linhas_visuais
from earbook.dominio.pagina import Linha

ENTRELINHA = 0.014
ESQUERDA = (42.0, 296.0)
DIREITA = (312.0, 566.0)


def _coluna(
    coluna: tuple[float, float], topo: float, *textos: str, tamanho: float = 10.0
) -> list[Linha]:
    x, fim = coluna
    return [
        Linha(texto, x=x, fim=fim, topo=topo + n * ENTRELINHA, tamanho=tamanho)
        for n, texto in enumerate(textos)
    ]


def _lidas(linhas: list[Linha]) -> list[str]:
    return [linha.texto for linha, _ in linhas_visuais(linhas, 10.0)]


def _pagina(*, titulo_topo: float = 0.641) -> tuple[list[Linha], list[str]]:
    """A p. 203: a prosa nas duas colunas até 0,618, "Key Points" à esquerda e os pontos-chave."""
    prosa_e = _coluna(
        ESQUERDA, 0.506, "Ideally, a clinician\u2019s practice setting", *["is set up"] * 7
    )
    prosa_e += _coluna(ESQUERDA, 0.618, "and instead to redirect care")
    prosa_d = _coluna(DIREITA, 0.506, "temporarily to another member", *["of the team"] * 7)
    prosa_d += _coluna(DIREITA, 0.618, "nothing is better than that.")
    titulo = _coluna(ESQUERDA, titulo_topo, "Key Points", tamanho=13.0)
    pontos_e = _coluna(ESQUERDA, 0.668, "• Management of chronic pain", *["includes more"] * 4)
    pontos_d = _coluna(DIREITA, 0.668, "• Motivational interviewing", *["challenges it"] * 4)
    linhas = [*prosa_e, *titulo, *pontos_e, *prosa_d, *pontos_d]
    ordem = [*prosa_e, *prosa_d, *titulo, *pontos_e, *pontos_d]
    return linhas, [linha.texto for linha in ordem]


def test_titulo_da_esquerda_no_vao_da_direita_abre_faixa_nova() -> None:
    linhas, ordem = _pagina()
    assert _lidas(linhas) == ordem


def _uma_coluna_depois_da_outra(linhas: list[Linha]) -> list[str]:
    esquerda = sorted((linha for linha in linhas if linha.x == ESQUERDA[0]), key=_topo)
    direita = sorted((linha for linha in linhas if linha.x == DIREITA[0]), key=_topo)
    return [linha.texto for linha in (*esquerda, *direita)]


def _topo(linha: Linha) -> float:
    return linha.topo


def test_subtitulo_da_esquerda_com_a_direita_correndo_ao_lado_fica_na_coluna() -> None:
    esquerda = [
        *_coluna(ESQUERDA, 0.1, "Texto da esquerda que segue", *["e continua"] * 6),
        *_coluna(ESQUERDA, 0.219, "Subtítulo", tamanho=13.0),
        *_coluna(ESQUERDA, 0.24, "Texto do subtítulo", *["e continua"] * 5),
    ]
    # Só o vão segura o subtítulo na coluna: a direita fecha frase em toda linha e continua a da
    # esquerda, mas corre ao lado dele (0,212 e 0,226).
    direita = _coluna(DIREITA, 0.1, *["e segue a frase."] * 15)
    linhas = [*esquerda, *direita]
    assert _lidas(linhas) == _uma_coluna_depois_da_outra(linhas)


def test_titulo_depois_de_frase_acabada_fica_na_coluna() -> None:
    linhas, _ = _pagina()
    acabada = [
        replace(linha, texto="and instead redirect care.")
        if linha.texto == "and instead to redirect care"
        else linha
        for linha in linhas
    ]
    assert _lidas(acabada).index("Key Points") < _lidas(acabada).index(
        "temporarily to another member"
    )


def test_titulo_de_duas_linhas_nao_se_parte() -> None:
    # Miller p. 2004: a coluna da direita acaba ao lado da 1ª linha do título e volta depois da
    # 2ª. Julgadas uma a uma, a 2ª atravessava sozinha, e o texto da direita entrava entre as duas.
    esquerda = [
        *_coluna(ESQUERDA, 0.1, "Texto da esquerda que segue", *["e continua"] * 7),
        *_coluna(ESQUERDA, 0.218, "BLOQUEOS ILIOINGUINAL", "E ILIOHIPOGÁSTRICO", tamanho=13.0),
        *_coluna(ESQUERDA, 0.26, "Texto do título", *["e continua"] * 5),
    ]
    direita = [
        *_coluna(DIREITA, 0.107, "a direita continua a frase", *["e segue"] * 6, "e acaba aqui."),
        *_coluna(DIREITA, 0.26, "Outro parágrafo da direita", *["e segue"] * 5),
    ]
    lidas = _lidas([*esquerda, *direita])
    assert lidas.index("E ILIOHIPOGÁSTRICO") == lidas.index("BLOQUEOS ILIOINGUINAL") + 1
