# SPDX-License-Identifier: GPL-3.0-or-later
"""O destaque de margem que repete o texto (ADR-0004 e ADR-0008, "Destaque de margem").

No Dalgalarrondo, o destaque tem 9 pt, numa coluna estreita ao lado do texto de 10 pt, e repete
uma frase dele. O `importar-pdf` o separa do texto na virada de coluna, e o `limpar` o tira,
registrado; as metades da frase que ele partia se juntam pela junção de sempre (ADR-0003).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from earbook.comandos.importar_pdf import importar_pdf
from earbook.comandos.preparar import preparar
from earbook.dominio.blocos import montar_blocos
from earbook.dominio.limpeza import LivroLimpo, limpar_para_o_ouvido
from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.segmento import Papel, Segmento
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf

MOTIVO = "destaque de margem: repete o texto vizinho"
ENTRELINHA = 0.017


def _linhas(
    coluna: tuple[float, float],
    tamanho: float,
    topo: float,
    *textos: str,
    passo: float = ENTRELINHA,
) -> list[Linha]:
    x, fim = coluna
    return [
        Linha(texto, x=x, fim=fim, topo=topo + n * passo, tamanho=tamanho)
        for n, texto in enumerate(textos)
    ]


def _corpo() -> list[Linha]:
    """Um parágrafo de 10 pt no alto da página: firma o corpo e a entrelinha do livro."""
    meio = ["segue com as medidas do livro"] * 7
    return _linhas((66.0, 247.5), 10.0, 0.1, "Um parágrafo de corpo que", *meio, "e acaba aqui.")


def _blocos(*linhas: Linha) -> list[str]:
    livro = montar_blocos([Pagina(1, (*_corpo(), *linhas))])
    return [bloco.texto for bloco in livro.blocos][1:]


def test_destaque_de_letra_menor_na_virada_de_coluna_nao_cola_na_continuacao() -> None:
    # Dalgalarrondo p. 250: o texto vira para a coluna estreita ao lado do destaque, que o
    # `colunas` lê antes dela. O destaque fecha a frase, a continuação começa em minúscula, e o
    # `blocos` os emendava: "…palcos de nossas vidas. de nossas vidas. Lugar…".
    largo = Linha("O corpo é um dos principais palcos", x=88.7, fim=247.5, topo=0.517, tamanho=10.0)
    texto = _linhas(
        (162.4, 247.5),
        10.0,
        0.534,
        "de nossas vidas.",
        "Lugar de dor e",
        "de prazer. Assim",
        "fala:",
    )
    destaque = _linhas(
        (66.0, 142.6),
        9.0,
        0.561,
        "O corpo é um dos",
        "principais palcos",
        "de nossas vidas.",
        passo=0.015,
    )
    assert _blocos(largo, *texto, *destaque) == [
        "O corpo é um dos principais palcos",
        "O corpo é um dos principais palcos de nossas vidas.",
        "de nossas vidas. Lugar de dor e de prazer. Assim fala:",
    ]


def test_texto_que_vira_para_o_destaque_de_letra_menor_nao_o_engole() -> None:
    # Dalgalarrondo p. 111: o texto estreito vem antes do destaque ao lado dele, a frase do texto
    # ainda não fechou, e o destaque colava no fim dela: "…Só após o agravamento Geralmente a…".
    texto = _linhas(
        (66.0, 142.6), 10.0, 0.4, "A desorientação", "vem no tempo e", "só depois do", "agravamento"
    )
    destaque = _linhas(
        (162.4, 247.5),
        9.0,
        0.41,
        "A desorientação vem",
        "no tempo e só depois",
        "no espaço.",
        passo=0.015,
    )
    depois = Linha("atinge o espaço e a pessoa.", x=66.0, fim=247.5, topo=0.48, tamanho=10.0)
    assert _blocos(*texto, *destaque, depois) == [
        "A desorientação vem no tempo e só depois do agravamento",
        "A desorientação vem no tempo e só depois no espaço.",
        "atinge o espaço e a pessoa.",
    ]


def test_virada_de_coluna_com_meio_ponto_de_diferenca_segue_no_paragrafo() -> None:
    # A folga é a do título, `DIFERENCA_DE_TAMANHO`: o arredondamento do tamanho não parte frase.
    esquerda = _linhas((66.0, 247.5), 10.0, 0.4, "O parágrafo começa na", "coluna e vira", "para a")
    direita = _linhas(
        (287.0, 446.0), 9.5, 0.4, "coluna da direita", "com a letra um pouco", "menor."
    )
    assert _blocos(*esquerda, *direita) == [
        "O parágrafo começa na coluna e vira para a coluna da direita com a letra um pouco menor."
    ]


def test_linha_de_letra_menor_sem_virada_de_coluna_segue_no_paragrafo() -> None:
    # Só a virada de coluna separa: em toda linha que muda de tamanho, o Competente ganhava 177
    # parágrafos, e o Hard Parts, 21 (ADR-0004, "Destaque de margem na virada de coluna").
    maior = _linhas((66.0, 247.5), 10.0, 0.4, "O parágrafo de corpo segue", "pela linha de baixo e")
    menor = _linhas((66.0, 247.5), 9.0, 0.434, "termina numa linha menor.")
    assert _blocos(*maior, *menor) == [
        "O parágrafo de corpo segue pela linha de baixo e termina numa linha menor."
    ]


def _limpar(*capitulos: Sequence[str | tuple[Papel, str]]) -> LivroLimpo:
    """Texto vira parágrafo; (papel, texto) entra com o papel dado. IDs cNNN-sNNNN na ordem."""
    entrada = [
        (
            f"c{c:03d}",
            [
                Segmento(
                    f"c{c:03d}-s{s:04d}", *(i if isinstance(i, tuple) else (Papel.PARAGRAFO, i))
                )
                for s, i in enumerate(itens, 1)
            ],
        )
        for c, itens in enumerate(capitulos, 1)
    ]
    return limpar_para_o_ouvido(entrada, "Psicopatologia", "Paulo Dalgalarrondo")


def _textos(livro: LivroLimpo) -> list[list[str]]:
    return [[segmento.texto for segmento in capitulo.segmentos] for capitulo in livro.capitulos]


def _destaques(livro: LivroLimpo) -> list[str]:
    return [remocao.id for remocao in livro.remocoes if remocao.motivo == MOTIVO]


CONTROVERSIA = (
    "O conceito de saúde e de normalidade em psicopatologia é questão de grande controvérsia"
)
TEXTO = (
    f"{CONTROVERSIA} (Almeida Filho, 2000). Obviamente, quando se trata de casos extremos, o "
    "delineamento das fronteiras entre o normal e o patológico não é tão problemático."
)


def test_destaque_que_repete_a_frase_do_paragrafo_vizinho_sai_registrado() -> None:
    # Dalgalarrondo c005-s0008, o da escuta: o destaque repete a frase do texto sem a citação.
    livro = _limpar([f"{CONTROVERSIA}.", TEXTO])
    assert _textos(livro) == [[TEXTO]]
    assert [(r.id, r.motivo, r.texto) for r in livro.remocoes] == [
        ("c001-s0001", MOTIVO, f"{CONTROVERSIA}.")
    ]


def test_destaque_no_meio_da_frase_sai_e_a_frase_se_emenda() -> None:
    # Dalgalarrondo p. 250: "…principais palcos" | destaque | "de nossas vidas…".
    livro = _limpar(
        [
            "O corpo é um dos principais palcos",
            "O corpo é um dos principais palcos de nossas vidas. Lugar de dor e de desejo.",
            "de nossas vidas. Lugar de dor e de desejo. Assim Drummond fala:",
        ]
    )
    frase = "O corpo é um dos principais palcos de nossas vidas. Lugar de dor e de desejo."
    assert _textos(livro) == [[f"{frase} Assim Drummond fala:"]]
    assert _destaques(livro) == ["c001-s0002"]


def test_destaque_no_meio_da_palavra_partida_sai_e_as_metades_se_juntam() -> None:
    # Dalgalarrondo c011: "os pri-" | destaque | "meiros três minutos…": o hífen da quebra não
    # impede a comparação.
    livro = _limpar(
        [
            "Esses pesquisadores verificaram que os pri-",
            "Os primeiros três minutos da entrevista são extremamente significativos.",
            "meiros três minutos da entrevista são extremamente significativos para o diagnóstico.",
        ]
    )
    assert _destaques(livro) == ["c001-s0002"]
    assert len(_textos(livro)[0]) == 1


def test_palavra_partida_pelo_destaque_volta_sem_o_hifen_da_quebra() -> None:
    # Dalgalarrondo c004: "identifi-" | destaque | "car". A junção emendava "identifi-car"; o
    # hífen sai porque o livro escreve "identificar" em outro lugar (ADR-0003).
    livro = _limpar(
        [
            "O psicopatólogo busca apenas observar, identifi-",
            "O psicopatólogo busca apenas observar, identificar e compreender a doença.",
            "car e compreender a doença. Além disso, rejeita o dogma.",
        ]
    )
    texto = "O psicopatólogo busca apenas observar, identificar e compreender a doença."
    assert _textos(livro) == [[f"{texto} Além disso, rejeita o dogma."]]


def test_hifen_no_meio_da_palavra_nao_esconde_o_destaque() -> None:
    # Dalgalarrondo c021: o texto ficou com "divi-dem-se", e o destaque, com "dividem-se".
    texto = (
        "Desde Aristóteles, os elementos do pensamento divi-dem-se em três operações básicas: "
        "os conceitos, os juízos e o raciocínio. Os conceitos vêm primeiro."
    )
    destaque = "Desde Aristóteles, os elementos do pensamento dividem-se em três operações básicas."
    assert _textos(_limpar([texto, destaque])) == [[texto]]


def test_destaque_que_abre_no_meio_da_frase_do_texto_sai() -> None:
    # Dalgalarrondo c038: o texto diz "Para Sonenreich (1971), o alcoolismo…", e o destaque
    # começa a frase em maiúscula, sem o autor.
    texto = (
        "Para Sonenreich (1971), o alcoolismo deve ser definido como a perda da liberdade de "
        "escolher entre beber e não beber. Há certa concordância nisso."
    )
    destaque = "O alcoolismo deve ser definido como a perda da liberdade de escolher."
    assert _textos(_limpar([texto, destaque])) == [[texto]]


ILUSAO = "Ilusão é a percepção deformada de um objeto real e presente."


def test_gemeo_no_meio_da_frase_sai_e_o_outro_fica() -> None:
    # Dalgalarrondo c017: o texto define a ilusão num parágrafo de uma frase só, e o destaque,
    # igual a ele, cai no meio da frase seguinte: "As ilusões ocor-" | destaque | "rem…".
    livro = _limpar([ILUSAO, "As ilusões ocorrem basicamente", ILUSAO, "em três condições:"])
    assert _textos(livro) == [[ILUSAO, "As ilusões ocorrem basicamente em três condições:"]]
    assert _destaques(livro) == ["c001-s0003"]


def test_gemeos_fora_do_meio_da_frase_ficam() -> None:
    # Learning DDD c095: duas notas seguidas citam a mesma obra. No Dalgalarrondo, 8 pares de
    # destaque igual a um parágrafo inteiro do texto ficam assim, lidos duas vezes (ADR-0008).
    fowler = "Fowler, M. (2002). Patterns of Enterprise Application Architecture. Boston: Wesley."
    livro = _limpar(["Can you spot it?", fowler, fowler, "Visit the site."])
    assert _destaques(livro) == []


@pytest.mark.parametrize(
    "paragrafos",
    [
        # O título que veio como parágrafo não fecha frase (c008).
        [
            "Relações da psicopatologia com a psicologia geral",
            "Segundo Sonenreich, as relações da psicopatologia com a psicologia geral são muitas.",
        ],
        # A continuação em minúscula é o texto; o destaque está colado no vizinho (c015).
        [
            (
                "Geralmente a desorientação ocorre no tempo. Só após o agravamento do transtorno, "
                "o indivíduo se desorienta quanto ao espaço."
            ),
            "do transtorno, o indivíduo se desorienta quanto ao espaço.",
        ],
        # A questão de revisão que termina em dois-pontos (c022).
        [
            "Como estabelecer um diagnóstico diferencial entre idéias prevalentes e delirantes?",
            "Como estabelecer um diagnóstico diferencial entre:",
        ],
        # O pedaço de bibliografia que abre em algarismo (Competente c023).
        [
            "Acesso em: 13 out. 2026. STANFORD INSTITUTE FOR HUMAN CENTERED AI. Report.",
            "2026. STANFORD INSTITUTE FOR HUMAN CENTERED AI.",
        ],
        # O número conta: com outro número, a frase diz outra coisa.
        [
            "O orgasmo dura de 3 a 25 segundos e está associado a leve obnubilação (Sadock).",
            "O orgasmo dura de 5 a 30 segundos e está associado a leve obnubilação.",
        ],
        # Com uma palavra a menos, é outra obra (Learning DDD c284).
        [
            "Vernon, V. (2021). Implementing Strategic Monoliths and Microservices. Wesley.",
            "Vernon, V. (2021). Strategic Monoliths and Microservices. Wesley.",
        ],
    ],
)
def test_paragrafo_que_nao_e_destaque_fica(paragrafos: list[str]) -> None:
    assert _destaques(_limpar(paragrafos)) == []


@pytest.mark.parametrize(
    ("frase", "saem"),
    [("A emoção cega o homem.", []), ("A emoção cega o homem sempre.", ["c001-s0001"])],
)
def test_destaque_tem_seis_palavras_ou_mais(frase: str, saem: list[str]) -> None:
    texto = f"Na tradição ocidental, {frase[0].lower()}{frase[1:-1]} e o impede de pensar."
    assert _destaques(_limpar([frase, texto])) == saem


@pytest.mark.parametrize(("entre", "saem"), [(2, ["c001-s0001"]), (3, [])])
def test_texto_a_mais_de_tres_segmentos_do_destaque_nao_conta(entre: int, saem: list[str]) -> None:
    outros = [f"Um parágrafo de número {n}, sem relação com o destaque." for n in range(entre)]
    livro = _limpar([f"{CONTROVERSIA}.", *outros, TEXTO])
    assert _destaques(livro) == saem


def test_texto_em_outro_capitulo_nao_conta() -> None:
    assert _destaques(_limpar([f"{CONTROVERSIA}."], [TEXTO])) == []


@pytest.mark.parametrize(
    ("papel_do_destaque", "papel_do_texto"),
    [(Papel.CITACAO, Papel.PARAGRAFO), (Papel.PARAGRAFO, Papel.NOTA)],
)
def test_so_o_paragrafo_e_destaque_e_so_o_paragrafo_e_texto(
    papel_do_destaque: Papel, papel_do_texto: Papel
) -> None:
    # A epígrafe que repete o texto é citação, e o Quadro que repete uma frase é nota.
    livro = _limpar([(papel_do_destaque, f"{CONTROVERSIA}."), (papel_do_texto, TEXTO)])
    assert _destaques(livro) == []


ENTRELINHA_DO_PDF = 13.5  # pontos: 0,017 de uma página de 792 pt, como no Dalgalarrondo


def test_destaque_colado_do_pdf_sai_e_a_frase_volta_inteira(tmp_path: Path) -> None:
    # De ponta a ponta, a p. 250 do Dalgalarrondo: o `importar-pdf` separa o destaque de 9 pt na
    # virada de coluna, e o `limpar` o tira e emenda "…palcos" com "de nossas vidas…".
    corpo = [
        LinhaDeTeste(texto, 66, 700 - n * ENTRELINHA_DO_PDF, tamanho=10)
        for n, texto in enumerate(
            ["Um parágrafo de corpo que", *["segue em linhas"] * 6, "e acaba."]
        )
    ]
    largo = [LinhaDeTeste("O corpo é um dos principais palcos", 88.7, 400, tamanho=10)]
    texto = [
        LinhaDeTeste(t, 162.4, 387 - n * ENTRELINHA_DO_PDF, tamanho=10)
        for n, t in enumerate(["de nossas vidas.", "Lugar de dor e", "de prazer. Assim", "fala:"])
    ]
    destaque = [
        LinhaDeTeste(t, 66, 366 - n * 12, tamanho=9)
        for n, t in enumerate(["O corpo é um dos", "principais palcos", "de nossas vidas."])
    ]
    pdf = montar_pdf(tmp_path / "livro.pdf", [[*corpo, *largo, *texto, *destaque]])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub", idioma="pt-BR")
    limpeza = preparar(importacao.epub, tmp_path / "trabalho").limpeza
    assert _textos(limpeza)[0][1:] == [
        "O corpo é um dos principais palcos de nossas vidas. Lugar de dor e de prazer. Assim fala:"
    ]
    assert [(r.motivo, r.texto) for r in limpeza.remocoes] == [
        (MOTIVO, "O corpo é um dos principais palcos de nossas vidas.")
    ]
