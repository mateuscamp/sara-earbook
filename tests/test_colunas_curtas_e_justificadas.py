# SPDX-License-Identifier: GPL-3.0-or-later
"""As colunas que a continuidade não via: o verbete justificado, a letra do quadro que acaba e a
coluna curta do corpo (ADR-0004, "Duas colunas", "O que ficou da Fase 1").

As medidas imitam o Dalgalarrondo: corpo de 10 pt, coluna da esquerda de x = 66 a 247 e da
direita de 287 a 446, entrelinha de 0,017 da altura da página.
"""

from __future__ import annotations

from earbook.dominio.colunas import linhas_visuais
from earbook.dominio.pagina import Linha

CORPO = 10.0
ENTRELINHA = 0.017
ESQUERDA = (66.0, 247.0)
DIREITA = (287.0, 446.0)


def _linha(texto: str, x: float, fim: float, topo: float, tamanho: float = CORPO) -> Linha:
    return Linha(texto, x=x, fim=fim, topo=topo, tamanho=tamanho)


def _lidas(linhas: list[Linha]) -> list[str]:
    return [linha.texto for linha, _ in linhas_visuais(linhas, CORPO)]


def _verbetes(coluna: tuple[float, float], nome: str) -> list[Linha]:
    """Glossário do Dalgalarrondo (p. 397): cada verbete abre em maiúscula, e a continuação é de
    2 em 6 pares (0,33). Das 7 linhas, 3 chegam à margem direita da coluna: é texto justificado."""
    x, cheia = coluna
    linhas = [
        (f"{nome}: pasta de coca fumada.", x + 70),
        ("Bem na fita: entre usuários de substân-", cheia),
        ("cias psicoativas, sair-se bem.", x + 120),
        ("Biba, bi: termos para homem homossexual.", cheia),
        ("Bichinho: entre usuários de substâncias,", cheia),
        ("denominação do vírus da AIDS.", x + 100),
        ("Binga: membro viril.", x + 60),
    ]
    return [_linha(t, x, fim, 0.1 + n * ENTRELINHA) for n, (t, fim) in enumerate(linhas)]


def test_verbetes_justificados_sao_lidos_coluna_a_coluna() -> None:
    # A continuidade (0,33) fica abaixo dos 40% de "Duas colunas", e as colunas saíam
    # intercaladas: "Bichinho: … Prová- Lambuzão: desleixado…" (p. 405).
    lidas = _lidas(_verbetes(ESQUERDA, "Bazuco") + _verbetes(DIREITA, "Zabaneira"))
    assert lidas[:2] == ["Bazuco: pasta de coca fumada.", "Bem na fita: entre usuários de substân-"]
    assert lidas[7] == "Zabaneira: pasta de coca fumada."


def test_celula_de_tabela_com_alguma_continuacao_e_sem_margem_comum_segue_linha_a_linha() -> None:
    # Competente p. 144: continuidade de 0,38, mas só 11% das linhas na margem direita. Lida
    # coluna a coluna, a tabela perde o par de cada linha.
    def lado(coluna: tuple[float, float], textos: list[str]) -> list[Linha]:
        x, fim = coluna
        return [_linha(t, x, fim - 15 * n, 0.1 + n * ENTRELINHA) for n, t in enumerate(textos)]

    medido = lado(ESQUERDA, ["O que foi medido", "a taxa de acerto", "Tempo de resposta", "Custo"])
    numero = lado(DIREITA, ["Número", "em segundos", "Que tipo de número", "Reais"])
    assert _lidas(medido + numero)[:2] == [
        "O que foi medido Número",
        "a taxa de acerto em segundos",
    ]


def _lado(
    coluna: tuple[float, float], textos: list[str], topos: list[float], tamanho: float
) -> list[Linha]:
    x, fim = coluna
    return [_linha(t, x, fim, topo, tamanho) for t, topo in zip(textos, topos, strict=True)]


# Dalgalarrondo p. 324: a tabela do Quadro 29.1, em 8 pt, com linhas a 0,0135 e um vão de linha
# da tabela; o corpo, em 10 pt, a 2,1 entrelinhas dela, abaixo do vão das faixas (2,5).
TOPOS_DA_TABELA = [0.1, 0.1135, 0.127, 0.154, 0.1675, 0.181]
TOPOS_DO_CORPO = [0.217, 0.234, 0.251, 0.268, 0.285]


def _tabela_e_corpo() -> list[Linha]:
    histerica = [
        "Mais comum em",
        "mulheres, com",
        "conflitos.",
        "Fase tônica",
        "precedendo a",
        "clônica.",
    ]
    epileptica = [
        "Distribuição",
        "equilibrada entre",
        "os sexos.",
        "A fase tônica",
        "precede a",
        "clônica.",
    ]
    esquerda = [
        "Já a somatização é",
        "um termo amplo,",
        "referente ao",
        "processo pelo",
        "qual o indivíduo",
    ]
    direita = [
        "usa o corpo para",
        "fins psicológicos",
        "ou para obter",
        "ganhos pessoais",
        "e afetivos.",
    ]
    return [
        *_lado(ESQUERDA, histerica, TOPOS_DA_TABELA, 8.0),
        *_lado(DIREITA, epileptica, TOPOS_DA_TABELA, 8.0),
        *_lado(ESQUERDA, esquerda, TOPOS_DO_CORPO, CORPO),
        *_lado(DIREITA, direita, TOPOS_DO_CORPO, CORPO),
    ]


def test_corpo_depois_da_tabela_de_letra_menor_e_outra_faixa() -> None:
    # O corpo vinha nas mesmas colunas da tabela, e a coluna da direita da tabela caía depois
    # dele, fora do quadro: 1 nota em "Notas".
    lidas = _lidas(_tabela_e_corpo())
    assert lidas[5:8] == ["clônica.", "Distribuição", "equilibrada entre"]
    assert lidas[11:13] == ["clônica.", "Já a somatização é"]


def test_letra_menor_de_um_lado_so_nao_fecha_as_colunas() -> None:
    # Um destaque de 9 pt numa coluna, ao lado do texto de 10 da outra, não é tabela: o vão
    # depois dele não corta a faixa (p. 219: "DELÍRIO DE RELAÇÃO" ia para a coluna errada).
    acima, abaixo = [0.1, 0.117, 0.134], [0.17, 0.187, 0.204]
    destaque = ["O conceito de", "saúde é questão", "de controvérsia."]
    ao_lado = ["Freud supôs que", "o delirante também", "deforma o conteúdo"]
    linhas = [
        *_lado(ESQUERDA, destaque, acima, 9.0),
        *_lado(DIREITA, ao_lado, acima, CORPO),
        *_lado(ESQUERDA, ["Já a somatização é", "um termo amplo,", "referente ao"], abaixo, CORPO),
        *_lado(
            DIREITA, ["inaceitável, inver-", "tendo o tipo de", "afeto associado."], abaixo, CORPO
        ),
    ]
    assert _lidas(linhas)[3:5] == ["Já a somatização é", "um termo amplo,"]


def test_letra_menor_dos_dois_lados_sem_vao_de_paragrafo_nao_fecha_as_colunas() -> None:
    # A tabela só acaba no vão de parágrafo (1,35 entrelinha). Sem ele, o corpo que vem logo
    # abaixo de 3 linhas de letra menor em cada coluna (uma citação, um subtítulo) cortava as
    # colunas: mudava a ordem de 4 páginas do Dalgalarrondo (p. 91, "O inconsciente"; mutante M15
    # da auditoria).
    topos = [0.1 + n * ENTRELINHA for n in range(6)]
    esquerda = [
        "como diz o poeta,",
        "em verso de outra",
        "letra, e assim",
        "segue o texto da",
        "coluna da",
        "esquerda.",
    ]
    direita = [
        "e a coluna da",
        "direita também",
        "começa em letra",
        "menor e depois",
        "segue no corpo",
        "até o fim.",
    ]
    tamanhos = [9.0, 9.0, 9.0, CORPO, CORPO, CORPO]
    linhas = [
        _linha(t, *ESQUERDA, topo, tamanho)
        for t, topo, tamanho in zip(esquerda, topos, tamanhos, strict=True)
    ] + [
        _linha(t, *DIREITA, topo, tamanho)
        for t, topo, tamanho in zip(direita, topos, tamanhos, strict=True)
    ]
    assert _lidas(linhas)[3:7] == ["segue o texto da", "coluna da", "esquerda.", "e a coluna da"]


def _pe_da_pagina(esquerda: list[str]) -> list[Linha]:
    """Dalgalarrondo p. 384: o quadro de largura cheia e, embaixo, 2 linhas de corpo à esquerda e
    a lista de 3 itens à direita."""
    quadro = _linha(
        "e da sofisticação cognitiva do paciente ao longo de sua vida.", 80, 431, 0.76, 8.0
    )
    lista = [
        "1. perda da memória de fixação",
        "2. desorientação temporoespacial",
        "3. confabulações",
    ]
    return [
        quadro,
        *_lado(ESQUERDA, esquerda, [0.845, 0.862], CORPO),
        *_lado(DIREITA, lista, [0.845, 0.862, 0.879], CORPO),
    ]


def test_coluna_de_duas_linhas_ligadas_pelo_hifen_vem_antes_da_outra() -> None:
    lidas = _lidas(_pe_da_pagina(["seqüelar, da SWK, é classi-", "camente definida pela tríade:"]))
    assert lidas[1:4] == [
        "seqüelar, da SWK, é classi-",
        "camente definida pela tríade:",
        "1. perda da memória de fixação",
    ]


def test_duas_linhas_sem_o_hifen_da_quebra_seguem_linha_a_linha() -> None:
    # Hard Parts p. 257: na tabela de vantagens, a célula de duas linhas ("Ownership per team,
    # or some" / "combination") também continua em minúscula, mas não se parte em sílaba.
    lidas = _lidas(_pe_da_pagina(["Ownership per team, or some", "combination"]))
    assert lidas[1] == "Ownership per team, or some 1. perda da memória de fixação"
