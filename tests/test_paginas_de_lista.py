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

import pytest

from earbook.comandos.cli import principal
from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginas_de_lista import (
    MOTIVO_DAS_REMISSOES,
    MOTIVO_DO_SUMARIO,
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


# Bonica p. 67 a 194: o sumário da frente não traz número de página; cada capítulo é o rótulo, o
# título, os autores em maiúsculas e as seções, uma por linha, sem frase nenhuma.
SUMARIO_SEM_NUMERO = [
    "Contents",
    "PART ONE",
    "Basic Considerations",
    "CHAPTER 1",
    "Intellectual Milestones in Our Understanding and Treatment of Pain",
    "G.F. GEBHART",
    "Pain Understood as Part of a Larger Philosophy or Worldview",
    "Mechanistic Views of Pain",
    "19TH CENTURY\u2014PAIN AS A SPECIFIC SENSE",
    "CHAPTER 2",
    "Definition of Commonly Used Pain Terms",
    "DENNIS C. TURK AND AKIKO OKIFUJI",
    "Is Chronic Pain a Disease?",
]
SECOES_DO_SUMARIO = [
    "CLASSIFICATION BASED ON BODY SYSTEM",
    "CLASSIFICATION BASED ON SEVERITY",
    "Multiaxial Classifications",
    "Empirically Based Classification of the Psychological Components of Pain",
]
# Bonica p. 5899 a 6053: o sumário do fim, com o número de página sem vírgula, solto ou no fim.
SUMARIO_DO_FIM = [
    "CHAPTER 6: Supraspinal Mechanisms of Pain and",
    "Nociception",
    "377",
    "Functional Imaging of Pain in Humans",
    "Tumor Infiltration of Abdominal Hollow Organs 2058",
    "CHAPTER 7: Psychological Aspects of Pain",
    "449",
]


def test_sumario_sem_numero_de_pagina_sai_inteiro_e_registrado() -> None:
    paginas = [
        _corpo(1),
        _pagina(2, SUMARIO_SEM_NUMERO),
        _pagina(3, SECOES_DO_SUMARIO),
        _pagina(4, ["CHAPTER 3", "Nociceptors", *SECOES_DO_SUMARIO]),
        _corpo(5),
    ]
    limpas = tirar_paginas_de_lista(paginas)
    assert _textos(limpas.paginas) == _textos((_corpo(1), _corpo(5)))
    assert {(r.pagina, r.motivo) for r in limpas.remocoes} == {
        (2, MOTIVO_DO_SUMARIO),
        (3, MOTIVO_DO_SUMARIO),
        (4, MOTIVO_DO_SUMARIO),
    }


def test_sumario_do_fim_com_numero_sem_virgula_sai() -> None:
    paginas = [_corpo(1), _pagina(2, SUMARIO_DO_FIM), _pagina(3, SUMARIO_DO_FIM)]
    limpas = tirar_paginas_de_lista(paginas)
    assert _textos(limpas.paginas) == _textos((_corpo(1),))


def test_abertura_de_capitulo_sem_frase_fica() -> None:
    # A página que abre o capítulo com o rótulo, o título, os autores e uma figura não tem frase,
    # mas é uma só, com um rótulo: não é sumário.
    abertura = ["CHAPTER 3", "Nociceptors", "MICHAEL S. GOLD", "FIGURE 3.1 Nociceptor"]
    paginas = [_corpo(1), _pagina(2, abertura), _corpo(3), _pagina(4, abertura), _corpo(5)]
    assert tirar_paginas_de_lista(paginas).remocoes == ()


def test_pagina_com_frase_depois_do_sumario_fica() -> None:
    # Bonica p. 195: o capítulo 1 abre logo depois do sumário, com o rótulo e a prosa.
    primeira = ["CHAPTER 1", "Intellectual Milestones", "G.F. GEBHART"]
    primeira += [f"Texto corrido da linha {k} do capítulo, sem nada." for k in range(3)]
    paginas = [_pagina(1, SUMARIO_SEM_NUMERO), _pagina(2, SUMARIO_SEM_NUMERO), _pagina(3, primeira)]
    limpas = tirar_paginas_de_lista(paginas)
    assert _textos(limpas.paginas) == primeira


def test_colaboradores_da_pagina_vizinha_saem_com_a_lista() -> None:
    # Bonica p. 9 a 54: as páginas com 3 ou 4 colaboradores, entre as de 5 ou mais, ficavam.
    poucos = COLABORADORES[:12]
    paginas = [_corpo(1), _pagina(2, poucos), _pagina(3, COLABORADORES), _pagina(4, poucos)]
    paginas.append(_corpo(5))
    limpas = tirar_paginas_de_lista(paginas)
    assert _textos(limpas.paginas) == _textos((_corpo(1), _corpo(5)))
    assert {r.motivo for r in limpas.remocoes} == {MOTIVO_DOS_COLABORADORES}


def test_fim_da_lista_de_colaboradores_sem_nome_sai() -> None:
    # Bonica p. 54: só as últimas linhas da afiliação de quem começou na página anterior.
    fim = ["David Geffen School of Medicine at UCLA", "Pediatrics", "Los Angeles, California"]
    paginas = [_pagina(1, COLABORADORES), _pagina(2, fim), _corpo(3)]
    assert _textos(tirar_paginas_de_lista(paginas).paginas) == _textos((_corpo(3),))


def test_dedicatoria_antes_dos_colaboradores_fica() -> None:
    # Bonica p. 7 e 8: a dedicatória e a legenda da foto, sem frase e sem nome com título.
    dedicatoria = ["TO THE LASTING MEMORY OF JOHN", "BONICA AND HIS ENDURING QUEST"]
    paginas = [_pagina(1, dedicatoria), _pagina(2, COLABORADORES)]
    assert _textos(tirar_paginas_de_lista(paginas).paginas) == dedicatoria


def test_prefacio_depois_dos_colaboradores_fica() -> None:
    prefacio = [f"Texto corrido da linha {k} do prefácio, sem nada." for k in range(30)]
    prefacio += ["Honorio T. Benzon, MD", "Professor", "James P. Rathmell, MD", "Boston"]
    paginas = [_pagina(1, COLABORADORES), _pagina(2, prefacio)]
    assert _textos(tirar_paginas_de_lista(paginas).paginas) == prefacio


def test_prosa_com_chamada_colada_ao_ponto_nao_vira_sumario() -> None:
    # A chamada no tamanho do corpo, que o adaptador não tira ("pain.12 The"), não apaga a frase:
    # sem isso, as páginas de prosa de três aberturas seguidas sairiam como sumário.
    prosa = [f"Linha {k} do texto, que acaba em chamada pain.{k} The" for k in range(30)]
    paginas = [_pagina(n, [f"CHAPTER {n}", "Title", *prosa]) for n in (1, 2, 3)]
    assert tirar_paginas_de_lista(paginas).remocoes == ()


def test_pagina_sem_frase_e_sem_rotulo_na_borda_do_sumario_fica() -> None:
    # A dedicatória antes do sumário e a página da parte depois dele não têm frase, mas não são
    # sumário: a sequência vai do primeiro rótulo ao último.
    dedicatoria = ["TO THE LASTING MEMORY OF JOHN BONICA"]
    parte = ["PART ONE", "Basic Considerations"]
    paginas = [_pagina(1, dedicatoria), _pagina(2, SUMARIO_SEM_NUMERO)]
    paginas += [_pagina(3, SUMARIO_SEM_NUMERO), _pagina(4, parte), _corpo(5)]
    limpas = tirar_paginas_de_lista(paginas)
    assert {r.pagina for r in limpas.remocoes} == {2, 3}


def test_pagina_de_titulo_depois_dos_colaboradores_fica() -> None:
    # O fim da lista é só afiliação, na letra da lista; o título maior não é fim de lista.
    titulo = Linha("Contents", x=42.0, fim=296.0, topo=0.05, tamanho=18.0)
    paginas = [_pagina(1, COLABORADORES), Pagina(2, (titulo,)), _corpo(3)]
    assert {r.pagina for r in tirar_paginas_de_lista(paginas).remocoes} == {1}


def test_resumo_conta_o_sumario_sem_numero_com_as_paginas_de_lista(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Bonica: o resumo contava as 12.678 linhas do sumário junto com a borda da página.
    corpo = [
        LinhaDeTeste(f"Linha {n} do texto corrido do livro, sem nada.", 72, 700 - 14 * n)
        for n in range(10)
    ]
    sumario = [
        [LinhaDeTeste(f"CHAPTER {n}", 72, 700), LinhaDeTeste("Pain Mechanisms", 72, 686)]
        for n in (1, 2, 3)
    ]
    pdf = montar_pdf(tmp_path / "livro.pdf", [*sumario, corpo])
    assert principal(["importar-pdf", str(pdf), "--epub", str(tmp_path / "livro.epub")]) == 0
    saida = capsys.readouterr().out
    assert "0 linhas tiradas da página: a borda, o texto escondido e o texto repetido." in saida
    assert "6 linhas de tabela, figura e página de lista tiradas." in saida
