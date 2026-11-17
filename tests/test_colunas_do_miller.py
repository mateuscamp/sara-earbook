# SPDX-License-Identifier: GPL-3.0-or-later
"""As colunas que a regra "Duas colunas" não via no Miller (ADR-0004, "A ordem das colunas no
Miller"): as colunas desalinhadas em meia linha e a prosa ao lado de uma lista.

As medidas imitam o Miller: corpo de 9 pt, coluna da esquerda de x = 60 a 308,6 e da direita de
324 a 572,6, entrelinha de 0,0134 da altura da página.
"""

from __future__ import annotations

from earbook.dominio.colunas import linhas_visuais
from earbook.dominio.pagina import Linha

CORPO = 9.0
ENTRELINHA = 0.0134
ESQUERDA = (60.0, 308.6)
DIREITA = (324.0, 572.6)
TITULO = 11.0


def _linha(texto: str, coluna: tuple[float, float], topo: float, tamanho: float = CORPO) -> Linha:
    x, fim = coluna
    return Linha(texto, x=x, fim=fim, topo=topo, tamanho=tamanho)


def _lidas(linhas: list[Linha]) -> list[str]:
    return [linha.texto for linha, _ in linhas_visuais(linhas, CORPO)]


def _secao(coluna: tuple[float, float], nome: str, topo: float) -> list[Linha]:
    """Quatro linhas de texto corrido, um vão de 2,3 entrelinhas, o subtítulo e mais quatro."""
    corridas = [f"{nome} começa aqui e", "segue na linha de baixo", "até o fim do", "parágrafo."]
    antes = [_linha(t, coluna, topo + n * ENTRELINHA) for n, t in enumerate(corridas)]
    titulo_no = topo + 3 * ENTRELINHA + 2.3 * ENTRELINHA
    titulo = _linha(f"SUBTÍTULO DA {nome.upper()}", coluna, titulo_no, TITULO)
    depois = [
        _linha(t, coluna, titulo_no + 1.7 * ENTRELINHA + n * ENTRELINHA)
        for n, t in enumerate(
            [f"{nome} continua aqui e", "segue na linha de baixo", "até o fim da", "coluna."]
        )
    ]
    return [*antes, titulo, *depois]


def test_colunas_desalinhadas_em_meia_linha_sao_lidas_inteiras() -> None:
    # Miller p. 2931: a coluna da direita começa meia linha acima da da esquerda. Medida pela
    # distância entre alturas seguidas da página, a entrelinha caía à metade, o vão do subtítulo
    # fechava as colunas, e a página saía em quatro pedaços, com os dois subtítulos colados numa
    # linha só ("SUPRAGLOTITIS AGUDA ABSCESO RETROFARÍNGEO").
    esquerda = _secao(ESQUERDA, "A esquerda", 0.072)
    direita = _secao(DIREITA, "A direita", 0.072 - ENTRELINHA / 2)
    assert _lidas(esquerda + direita) == [linha.texto for linha in esquerda + direita]


_LISTA = [
    "Tipo de cirugía",
    "General",
    "Edad > 40 años 10 < 1 0,1",
    "Torácica 30",
    "Vascular",
    "Reparación aórtica 26 y periférica 12 en los ancianos",
    "Urológica",
    "Prostatectomía abierta 40",
]
_PROSA = [
    "supervivientes a una parada cardíaca extrahospitalaria. Aun-",
    "que estos pacientes suelen recibir tratamiento antiarrítmico,",
    "el tratamiento posoperatorio debe centrarse en su trastorno",
    "de base. El tratamiento antiarrítmico crónico se comenta en",
    "la última sección del capítulo. Las torsade de pointes con-",
    "sisten en una taquicardia ventricular caracterizada por epi-",
    "sodios de polaridad eléctrica alternante, de forma que el",
    "vector del complejo QRS parece girar.",
]


def _lista(fins: list[float], textos: list[str] = _LISTA) -> list[Linha]:
    x, _ = ESQUERDA
    return [
        Linha(t, x=x, fim=fim, topo=0.1 + n * ENTRELINHA, tamanho=CORPO)
        for n, (t, fim) in enumerate(zip(textos, fins, strict=True))
    ]


_DESVIOS_DA_MARGEM = [0.0, 0.0, -2.5, 0.0, -2.5, 2.0, 0.0]
"""A linha cheia do Miller termina na margem ou até 2,6 pt antes dela (a do hífen); uma passa
2 pt além (o "®" da p. 2884). A margem pela linha mais longa, com 1 pt de folga, só via uma."""


def _prosa(textos: list[str], margem: float = DIREITA[1]) -> list[Linha]:
    x, _ = DIREITA
    # A última fecha o parágrafo.
    fins = [margem + desvio for desvio in _DESVIOS_DA_MARGEM[: len(textos) - 1]] + [x + 150]
    return [
        Linha(t, x=x, fim=fim, topo=0.1 + n * ENTRELINHA, tamanho=CORPO)
        for n, (t, fim) in enumerate(zip(textos, fins, strict=True))
    ]


_FINS_DA_LISTA = [150.0, 110.0, 230.0, 140.0, 120.0, 306.0, 130.0, 200.0]


def test_prosa_ao_lado_de_uma_lista_da_mesma_largura_e_lida_coluna_a_coluna() -> None:
    # Miller p. 1377: a tabela na letra do corpo, na coluna da esquerda, não continua de uma linha
    # para a outra, e a página era lida por altura: "Torácica 30 que estos pacientes suelen…".
    lista, prosa = _lista(_FINS_DA_LISTA), _prosa(_PROSA)
    assert _lidas(lista + prosa) == [linha.texto for linha in lista + prosa]


def test_lista_ao_lado_de_celula_curta_segue_linha_a_linha() -> None:
    # A célula de tabela que quebra linha também continua e chega à margem dela, mas tem linha
    # curta (Miller p. 2965, "Porcentaje del / tiempo de / control preciso"): não é prosa.
    celulas = [texto[:28] for texto in _PROSA]
    lidas = _lidas(_lista(_FINS_DA_LISTA) + _prosa(celulas))
    assert lidas[1] == f"General {celulas[1]}"


def test_lista_bem_mais_estreita_que_a_prosa_segue_linha_a_linha() -> None:
    # A coluna de chave ao lado da coluna de valor que é texto corrido: a chave ocupa metade da
    # largura do valor, e a tabela perderia o par de cada linha.
    estreita = _lista([60.0 + 120.0] * len(_LISTA))
    lidas = _lidas(estreita + _prosa(_PROSA))
    assert lidas[1] == f"General {_PROSA[1]}"


def test_prosa_de_cinco_linhas_ao_lado_de_uma_lista_segue_linha_a_linha() -> None:
    # Com poucas linhas, a célula longa de uma tabela também parece prosa: a regra pede 6.
    lista = _lista([150.0, 110.0, 306.0, 140.0, 120.0], _LISTA[:5])
    lidas = _lidas(lista + _prosa(_PROSA[:5]))
    assert lidas[1] == f"General {_PROSA[1]}"


def test_lista_bem_mais_larga_que_a_prosa_segue_linha_a_linha() -> None:
    # A coluna de valor mais estreita que a de chave não é a coluna vizinha da página.
    lidas = _lidas(_lista(_FINS_DA_LISTA) + _prosa(_PROSA, margem=DIREITA[0] + 176.0))
    assert lidas[1] == f"General {_PROSA[1]}"


def test_celula_longa_sem_margem_comum_segue_linha_a_linha() -> None:
    # A célula de tabela de texto longo, que continua de uma linha para a outra mas não é
    # justificada: cada linha termina num ponto (Competente p. 144).
    x, margem = DIREITA
    fins = [margem - 9 * n for n in range(len(_PROSA))]
    celulas = [
        Linha(t, x=x, fim=fim, topo=0.1 + n * ENTRELINHA, tamanho=CORPO)
        for n, (t, fim) in enumerate(zip(_PROSA, fins, strict=True))
    ]
    lidas = _lidas(_lista(_FINS_DA_LISTA) + celulas)
    assert lidas[1] == f"General {_PROSA[1]}"


def test_prosa_ao_lado_de_duas_linhas_segue_linha_a_linha() -> None:
    # Duas linhas ao lado da prosa não fazem coluna (`LINHAS_POR_COLUNA`), como na regra dos dois
    # lados corridos.
    lidas = _lidas(_lista([150.0, 306.0], _LISTA[:2]) + _prosa(_PROSA))
    assert lidas[1] == f"General {_PROSA[1]}"


def test_linhas_longas_que_nao_continuam_ao_lado_de_uma_lista_seguem_linha_a_linha() -> None:
    # A tabela de frase por linha, justificada, mas sem continuação: cada linha é uma célula.
    frases = [f"Frase {n} da célula de tabela, que termina nesta linha." for n in range(8)]
    lidas = _lidas(_lista(_FINS_DA_LISTA) + _prosa(frases))
    assert lidas[1] == f"General {frases[1]}"
