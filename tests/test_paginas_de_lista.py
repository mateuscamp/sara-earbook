# SPDX-License-Identifier: GPL-3.0-or-later
"""As páginas de lista saem do áudio inteiras (ADR-0004, "Páginas de lista").

No Practical, o índice remissivo (p. 1467 a 1503) é página escaneada com OCR, em Times de 8,3 pt:
o pdfminer o lê intercalado ("clinical use of, Z!! AAHPM…"), e a regra do ADR-0008, de 10
parágrafos de "termo, página" seguidos, não dispara. O sumário (p. 19 a 22) tem duas colunas, e os
títulos dos capítulos se misturam com os autores. A lista de colaboradores (p. 6 a 13) traz
"Nome, MD" e a afiliação, em duas colunas.
"""

from __future__ import annotations

from pathlib import Path

from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginas_de_lista import (
    MOTIVO_DAS_REMISSOES,
    MOTIVO_DOS_COLABORADORES,
    tirar_paginas_de_lista,
)
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf


def _pagina(numero: int, textos: list[str]) -> Pagina:
    linhas = [
        Linha(texto, x=42.0, fim=296.0, topo=0.05 + 0.014 * n, tamanho=10.0)
        for n, texto in enumerate(textos)
    ]
    return Pagina(numero, tuple(linhas))


def _corpo(numero: int) -> Pagina:
    return _pagina(
        numero, [f"Texto corrido da linha {k} do capítulo, sem nada." for k in range(40)]
    )


INDICE = [
    "Adolescents",
    "juvenile primary fibromyalgia syndrome, 629",
    "pain assessment in, 621 t",
    "pelvic pain in, 617",
    "Adrenal  insufficiency (AJ), 889",
    "<X-Adrenergic agonists",
    "for burn pain, 1049",
    "intrathecal delivery, 977- 978",
    "prevention of chronic pose-surgical pain",
    "syndromes, ill",
    "Adrenocorticotropic hormone (ACTH),",
    "201- 202,878",
    "Adulr(s)",
    "musculoskeletal pain in, 1027",
    "monitoring of, 82, 836",
    "plans for response co, 84",
    "Aerobic exercise, for fibromyalgia,  526",
    "Afferent fibers",
    "large, sprouting of, .!l!_",
    "zones, 2.8.,. 99f",
]
SUMARIO = [
    "Contents",
    "Part 1:  General Considerations",
    "1",
    "2",
    "History Is a Distillation of Rumor, 3",
    "Natalie Moryl, Charles Inturrisi",
    "Classification of Acute Pain and Chronic Pain",
    "Syndromes, 11",
    "Juan C. Mora, Rene Przkora, Matthew Meroney",
    "Interdisciplinary Pain Management, 39",
    "Steven P. Stanos",
    "The Healthcare Policy of Pain Management, 57",
    "Thomas R. Vetter",
    "Safety in Pain Management, 67",
    "Debra B. Gordon, James P. Rathmell",
    "Medicine, 87",
    "Neurochemistry of Nociception, 110",
    "Tony L. Yaksh, Gilson Gonçalves dos Santos, Lauriane Delay,",
    "10  Neuroimaging Techniques, 125",
    "Treatment of Pain: Race, Ethnicity, and Sex, 138",
]
COLABORADORES = [
    "Fabrizio Benedetti, MD",
    "Professor",
    "Department of Neuroscience",
    "University of Turin Medical School",
    "John C. Benson, MD",
    "Assistant Professor",
    "Mayo Clinic",
    "Rochester, Minnesota",
    "Honorio T. Benzon, MD",
    "Professor",
    "Chicago, Illinois",
    "Hubert A. Benzon, MD",
    "Attending Anesthesiologist",
    "Anuj Bhatia, MBBS, MD, PhD, FRCPC, FRCA, FFPMRCA",
    "Associate Professor",
    "University of Toronto",
    "Staja Q. Booker, PhD, RN",
    "Assistant Professor",
    "Nicholas E. Burjek, MD",
    "Northwestern University",
]


def _textos(paginas: tuple[Pagina, ...]) -> list[str]:
    return [linha.texto for pagina in paginas for linha in pagina.linhas]


def test_pagina_de_indice_remissivo_sai_inteira_e_registrada() -> None:
    limpas = tirar_paginas_de_lista([_corpo(1), _pagina(2, INDICE)])
    assert _textos(limpas.paginas) == _textos((_corpo(1),))
    assert [(r.pagina, r.motivo, r.texto) for r in limpas.remocoes] == [
        (2, MOTIVO_DAS_REMISSOES, texto) for texto in INDICE
    ]


def test_pagina_de_sumario_com_virgula_e_pagina_sai() -> None:
    limpas = tirar_paginas_de_lista([_pagina(1, SUMARIO), _corpo(2)])
    assert _textos(limpas.paginas) == _textos((_corpo(2),))


def test_pagina_de_colaboradores_sai() -> None:
    limpas = tirar_paginas_de_lista([_pagina(1, COLABORADORES), _corpo(2)])
    assert {r.motivo for r in limpas.remocoes} == {MOTIVO_DOS_COLABORADORES}
    assert _textos(limpas.paginas) == _textos((_corpo(2),))


def test_pagina_de_texto_com_poucas_remissoes_fica() -> None:
    textos = [f"Texto corrido da linha {k} do capítulo, sem nada." for k in range(36)]
    textos += ["as in Chapter 12, 34", "see Table 3, 2", "the dose, 5", "and later, 7"]
    assert tirar_paginas_de_lista([_pagina(1, textos)]).remocoes == ()


def test_lista_de_anos_nao_e_remissao() -> None:
    textos = [f"Smith J, Jones K. The study of pain, {1990 + k}" for k in range(20)]
    assert tirar_paginas_de_lista([_pagina(1, textos)]).remocoes == ()


def test_assinaturas_do_prefacio_ficam() -> None:
    textos = [f"Texto corrido da linha {k} do prefácio, sem nada." for k in range(30)]
    textos += ["Honorio T. Benzon, MD", "James P. Rathmell, MD", "Christopher L. Wu, MD"]
    assert tirar_paginas_de_lista([_pagina(1, textos)]).remocoes == ()


def test_autores_do_capitulo_em_maiusculas_nao_sao_colaboradores() -> None:
    textos = ["NATALIE MORYL, MD", "CHARLES INTURRISI, PHD"] * 6
    textos += [f"Texto corrido da linha {k} do capítulo, sem nada." for k in range(20)]
    assert tirar_paginas_de_lista([_pagina(1, textos)]).remocoes == ()


def test_tabela_com_virgula_decimal_nao_e_remissao() -> None:
    # Dalgalarrondo p. 302: a Tabela 25.1 tem 70 células "17,6", "0,3", uma por linha.
    textos = [f"Texto corrido da linha {k} do capítulo, sem nada." for k in range(30)]
    textos += [f"{k},{k % 10}" for k in range(1, 71)]
    assert tirar_paginas_de_lista([_pagina(1, textos)]).remocoes == ()


def test_prefacio_assinado_por_sete_editores_fica() -> None:
    # Practical p. 18: o prefácio termina com 7 linhas "Nome, MD", uma embaixo da outra.
    textos = [f"Texto corrido da linha {k} do prefácio, sem nada." for k in range(30)]
    textos += [f"Editor Number{k} Smith, MD" for k in range(7)]
    assert tirar_paginas_de_lista([_pagina(1, textos)]).remocoes == ()


def test_ultima_pagina_curta_do_sumario_sai() -> None:
    # Practical p. 22: 18 linhas, 5 delas com a página.
    textos = [
        "xxiv",
        "Part 8: Research, Ethics, Healthcare Policy,",
        "and Future Directions in Pain Management",
        "85 Ethical Issues in Pain Research, 1123",
        "Katherine Gentry, Gary A. Walco",
        "83 Clinical Trial Design Methodology and",
        "Data Analytic Strategies for Pain Outcome",
        "Studies, 1095",
        "Steven P. Cohen, Nebojsa Nick Knezevic",
        "Index, 1139",
        "Thomas R. Vetter",
        "84 Outcome Domains and Measures in Acute and",
        "Chronic Pain Clinical Trials, 1111",
        "Honorio T. Benzon, Hubert A. Benzon",
        "86 Treatment Development: Directions and",
        "Areas in Need of Investigation, 1131",
        "David A. Williams",
        "Christopher L. Wu",
    ]
    assert len(tirar_paginas_de_lista([_pagina(1, textos)]).remocoes) == len(textos)


def test_pagina_de_texto_com_tabela_de_doses_fica() -> None:
    # R1 da code-review: a página com prosa não sai inteira por causa de uma tabela.
    textos = [f"Texto corrido da linha {k} do capítulo, longo como a prosa." for k in range(30)]
    textos += [f"Medication number {k}, {k + 5}" for k in range(12)]
    assert tirar_paginas_de_lista([_pagina(1, textos)]).remocoes == ()


def test_o_indice_que_sai_ainda_prova_o_hifen_do_livro(tmp_path: Path) -> None:
    # Hard Parts: "east-|west" na quebra de linha só ficava com hífen porque o índice escreve
    # "east-west"; com o índice tirado antes dos blocos, virava "eastwest".
    corpo = [
        LinhaDeTeste(f"Linha {n} do texto corrido do livro, longa.", 72, 700 - 14 * n)
        for n in range(10)
    ]
    corpo += [
        LinhaDeTeste("Services talk to one another, the east-", 72, 540),
        LinhaDeTeste("west communication of the system.", 72, 526),
    ]
    indice = [LinhaDeTeste(f"termo {n}, {n + 10}", 72, 700 - 14 * n) for n in range(8)]
    indice.append(LinhaDeTeste("east-west communication, 42", 72, 580))
    pdf = montar_pdf(tmp_path / "livro.pdf", [corpo, indice])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub")
    textos = " ".join(bloco.texto for bloco in importacao.livro.blocos)
    assert "east-west communication of the system." in textos
    assert "termo 1, 11" not in textos
