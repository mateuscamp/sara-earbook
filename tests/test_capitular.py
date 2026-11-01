# SPDX-License-Identifier: GPL-3.0-or-later
"""Capitular perdida (ADR-0003): o primeiro parágrafo do capítulo começa sem a primeira letra.

No Tides of Darkness, a letra capitular sumiu na conversão do PDF em todos os 25 começos
de capítulo ("re we ready?”", "hadgar watched"). O Python não sabe que letra era: marca a
suspeita e o Claude Code corrige.
"""

from __future__ import annotations

from collections.abc import Sequence

from earbook.dominio.limpeza import (
    MOTIVO_DA_CAPITULAR,
    MOTIVO_DA_LINHA_CURTA,
    LivroLimpo,
    Pista,
    Suspeita,
    limpar_para_o_ouvido,
)
from earbook.dominio.segmento import Papel, Segmento


def _livro(*capitulos: Sequence[str | Segmento]) -> LivroLimpo:
    """Texto vira parágrafo com ID cNNN-sNNNN na ordem; Segmento entra como está."""
    entrada = [
        (
            f"c{c:03d}",
            [
                item
                if isinstance(item, Segmento)
                else Segmento(f"c{c:03d}-s{s:04d}", Papel.PARAGRAFO, item)
                for s, item in enumerate(itens, 1)
            ],
        )
        for c, itens in enumerate(capitulos, 1)
    ]
    return limpar_para_o_ouvido(entrada, "Tides of Darkness", "Aaron Rosenberg")


def _titulo(texto: str) -> Segmento:
    return Segmento("c001-s0001", Papel.TITULO, texto)


def test_paragrafo_em_minuscula_depois_de_titulo_e_capitular_perdida() -> None:
    livro = _livro([_titulo("EIGHT"), "re we ready?”"])
    assert livro.suspeitas == (Suspeita("c001-s0002", MOTIVO_DA_CAPITULAR, "re we ready?”"),)


def test_marcar_nao_muda_o_texto() -> None:
    # Só o agente sabe que a letra era "A": o texto segue como veio, até ele corrigir.
    livro = _livro([_titulo("EIGHT"), "re we ready?”"])
    assert [s.texto for s in livro.capitulos[0].segmentos] == ["EIGHT", "re we ready?”"]


def test_primeiro_paragrafo_do_capitulo_sem_titulo_nao_e_marcado() -> None:
    # A3 da auditoria: no Tides os 25 casos vieram depois de título ou de linha curta, e o
    # começo de capítulo sem título não teve nenhum. Marcar ali só abria falso positivo.
    livro = _livro(["hadgar watched quietly from one side of the throne room."])
    assert livro.suspeitas == ()


def test_fala_que_abre_aspas_depois_de_titulo_tambem_e_capitular() -> None:
    livro = _livro([_titulo("TWENTY-TWO"), "“o!” the word burst from Turalyon."])
    assert [s.motivo for s in livro.suspeitas] == [MOTIVO_DA_CAPITULAR]


def test_paragrafo_em_maiuscula_depois_de_titulo_nao_e_marcado() -> None:
    livro = _livro([_titulo("ONE"), "Despite himself, Lothar was impressed."])
    assert livro.suspeitas == ()


def test_minuscula_no_meio_do_capitulo_nao_e_capitular() -> None:
    # Travessão de propósito e fala interrompida: medidos no Tides, não são capitular.
    livro = _livro(
        [
            "Night fell over the whole camp.",
            "—and found herself staring at the troll.",
            "“—don\u2019t know how far we can trust him,” he said.",
        ]
    )
    assert livro.suspeitas == ()


def test_titulo_em_minuscula_depois_de_paragrafo_continua_suspeita_de_titulo() -> None:
    # "acknowledgments" é o título; ele não perdeu letra nenhuma.
    livro = _livro(["“What could they possibly do to earn statues?”", "acknowledgments"])
    assert livro.suspeitas == (Suspeita("c001-s0002", MOTIVO_DA_LINHA_CURTA, "acknowledgments"),)


def test_cada_segmento_aparece_uma_vez_so_nas_suspeitas() -> None:
    # "awn" é suspeito pela linha curta antes e pela capitular: entra uma vez, como capitular.
    titulo = Segmento("c002-s0001", Papel.TITULO, "ONE")
    livro = _livro(
        ["first prologue", "awn, and fog still shrouded the world."],
        [titulo, "espite himself, he was impressed."],
    )
    assert [(s.id, s.motivo) for s in livro.suspeitas] == [
        ("c001-s0002", MOTIVO_DA_CAPITULAR),
        ("c002-s0002", MOTIVO_DA_CAPITULAR),
    ]


def _pista(livro: LivroLimpo) -> Pista | None:
    [suspeita] = livro.suspeitas
    return suspeita.pista


def test_letra_solta_no_mesmo_paragrafo_vira_pista() -> None:
    # A1 da auditoria: a capitular não sumiu, foi parar no meio do texto ("stirred, D unable").
    texto = "awn came slowly as the camp stirred, D unable to sleep."
    livro = _livro([_titulo("SEVEN"), texto])
    assert _pista(livro) == Pista("c001-s0002", texto.index(" D ") + 1, "D")


def test_letra_solta_dois_paragrafos_adiante_vira_pista() -> None:
    livro = _livro([_titulo("SIX"), "ul'dan was furious.", "He threw the cup away.", "G demanded."])
    assert _pista(livro) == Pista("c001-s0004", 0, "G")


def test_letra_alem_de_dois_paragrafos_nao_vira_pista() -> None:
    livro = _livro([_titulo("SIX"), "ul'dan was furious.", "He sat.", "He stood.", "G demanded."])
    assert _pista(livro) is None


def test_pronome_e_inicial_de_nome_nao_viram_pista() -> None:
    # "I" se confunde com o pronome; "J." e "R." são iniciais, não letra solta.
    livro = _livro([_titulo("ONE"), "t was done, I said, and J. R. R. Tolkien agreed."])
    assert _pista(livro) is None


def test_segmento_suspeito_de_cabecalho_nao_vira_capitular_tambem() -> None:
    # A4 da auditoria: cabeçalho em minúscula, logo depois de título, saía duas vezes.
    capitulos = [
        [Segmento(f"c00{c}-s0001", Papel.TITULO, "ONE"), f"the long voyage {n}"]
        for c, n in ((1, 12), (2, 14), (3, 16))
    ]
    livro = _livro(*capitulos)
    ids = [s.id for s in livro.suspeitas]
    assert ids == ["c001-s0002", "c002-s0002", "c003-s0002"]
    assert {s.motivo for s in livro.suspeitas} != {MOTIVO_DA_CAPITULAR}
