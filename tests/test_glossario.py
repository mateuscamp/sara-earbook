# SPDX-License-Identifier: GPL-3.0-or-later
"""Glossário de nomes próprios: candidatos para o agente e a cobrança no `conferir` (ADR-0006)."""

from __future__ import annotations

from earbook.dominio.glossario import (
    CandidatoANome,
    ConferenciaDeNomes,
    EntradaDoGlossario,
    candidatos_a_nome,
)
from earbook.dominio.segmento import Papel, Segmento


def _segmentos(*textos: str) -> list[Segmento]:
    return [
        Segmento(f"c004-s{posicao:04d}", Papel.PARAGRAFO, texto)
        for posicao, texto in enumerate(textos, start=1)
    ]


def _nomes(segmentos: list[Segmento], glossario: tuple[EntradaDoGlossario, ...] = ()) -> list[str]:
    return [candidato.nome for candidato in candidatos_a_nome(segmentos, glossario)]


def test_candidato_e_palavra_com_maiuscula_fora_do_comeco_da_frase() -> None:
    segmentos = _segmentos(
        "The orcs marched on Stormwind. Then they burned it.",
        "Nobody in Stormwind slept. Then the night came.",
    )
    # "The" e "Then" abrem frase duas vezes cada e não são nome.
    assert _nomes(segmentos) == ["Stormwind"]


def test_maiusculas_vizinhas_viram_um_nome_so() -> None:
    segmentos = _segmentos("He saw Anduin Lothar.", "They followed Anduin Lothar north.")
    assert _nomes(segmentos) == ["Anduin Lothar"]


def test_nome_que_aparece_uma_vez_so_fica_de_fora() -> None:
    assert _nomes(_segmentos("He saw Khadgar.", "He saw Medivh.", "Where is Medivh?")) == ["Medivh"]


def test_nome_depois_de_aspas_ou_travessao_no_comeco_da_frase_nao_e_candidato() -> None:
    segmentos = _segmentos("“Where are they?” he asked.", "“Where now?” — Where indeed.")
    assert _nomes(segmentos) == []


def test_pronome_e_letra_solta_da_capitular_nao_sao_candidatos() -> None:
    # A capitular deslocada do Tides deixa uma maiúscula sozinha no meio da frase (ADR-0003).
    segmentos = _segmentos("so I said D unable", "and I\u2019m sure I knew D there")
    assert _nomes(segmentos) == []


def test_nome_que_ja_esta_no_glossario_nao_e_candidato() -> None:
    segmentos = _segmentos("on Stormwind and Ironforge", "to Stormwind and Ironforge")
    glossario = (EntradaDoGlossario("Stormwind", "Ventobravo"),)
    assert _nomes(segmentos, glossario) == ["Ironforge"]


def test_candidatos_vem_do_mais_frequente_com_a_contagem_e_um_exemplo() -> None:
    segmentos = _segmentos(
        "to Lordaeron and Dalaran", "to Dalaran", "from Dalaran", "from Lordaeron"
    )
    assert candidatos_a_nome(segmentos, ()) == (
        CandidatoANome("Dalaran", 3, "c004-s0001"),
        CandidatoANome("Lordaeron", 2, "c004-s0001"),
    )


GLOSSARIO = (
    EntradaDoGlossario("Stormwind", "Ventobravo"),
    EntradaDoGlossario("Lothar", "Lorde Lothar"),
    EntradaDoGlossario("Khadgar", "Khadgar"),
)


def test_traducao_com_a_forma_do_glossario_nao_tem_motivo() -> None:
    conferencia = ConferenciaDeNomes(GLOSSARIO)
    assert conferencia.motivos("Khadgar saw Stormwind.", "Khadgar viu Ventobravo.") == []


def test_traducao_sem_a_forma_do_glossario_e_motivo() -> None:
    conferencia = ConferenciaDeNomes(GLOSSARIO)
    assert conferencia.motivos("Khadgar left.", "O mago partiu.") == [
        "sem 'Khadgar', que o glossário dá para 'Khadgar'"
    ]


def test_nome_que_ficou_no_original_e_motivo_mesmo_com_a_forma_do_glossario() -> None:
    conferencia = ConferenciaDeNomes(GLOSSARIO)
    assert conferencia.motivos("Stormwind fell.", "Ventobravo, a Stormwind, caiu.") == [
        "'Stormwind' ficou no original; o glossário diz 'Ventobravo'"
    ]


def test_forma_do_glossario_que_contem_o_original_nao_e_o_original_que_ficou() -> None:
    conferencia = ConferenciaDeNomes(GLOSSARIO)
    assert conferencia.motivos("Lothar rode.", "Lorde Lothar cavalgou.") == []


def test_nome_so_conta_como_palavra_inteira() -> None:
    # "Stormwinds" não é "Stormwind", e "Khadgars" na tradução não é "Khadgar".
    conferencia = ConferenciaDeNomes(GLOSSARIO)
    assert conferencia.motivos("The Stormwinds rose.", "Os ventos subiram.") == []
    assert conferencia.motivos("Khadgar left.", "Os Khadgars partiram.") == [
        "sem 'Khadgar', que o glossário dá para 'Khadgar'"
    ]


def test_nome_repetido_no_glossario_e_acusado() -> None:
    glossario = (*GLOSSARIO, EntradaDoGlossario("Stormwind", "Vento Bravo"))
    assert ConferenciaDeNomes(glossario).repetidos() == ["Stormwind"]


def test_possessivo_conta_como_o_proprio_nome() -> None:
    # No Tides, o possessivo (com apóstrofo tipográfico) aparecia 21 vezes à parte de "Lothar".
    segmentos = _segmentos("by Lothar\u2019s sword", "to Lothar", "to Medivh's tower and Medivh")
    assert _nomes(segmentos) == ["Lothar", "Medivh"]


def test_pronome_com_apostrofo_reto_nao_e_candidato() -> None:
    assert (
        _nomes(_segmentos("and I'm sure", "so I'm here", "but I\u2019ll go", "as I\u2019ll")) == []
    )


def test_nome_dentro_de_outra_palavra_nao_conta() -> None:
    conferencia = ConferenciaDeNomes(GLOSSARIO)
    assert conferencia.motivos("MacLothar rode.", "MacLothar cavalgou.") == []


def test_nome_depois_de_titulo_abreviado_e_candidato_e_o_titulo_nao() -> None:
    # Achado da code-review: o ponto de "Dr." fechava a frase, e o nome logo depois não
    # contava; o "Dr" virava candidato no lugar dele.
    segmentos = _segmentos("He met Dr. Slotkin there.", "Later, Mr. Slotkin left.")
    assert _nomes(segmentos) == ["Slotkin"]


def test_titulo_abreviado_repetido_nao_vira_candidato() -> None:
    segmentos = _segmentos("He met Dr. Slotkin.", "Then Dr. Slotkin left.", "and Dr. Smith")
    assert _nomes(segmentos) == ["Slotkin"]
