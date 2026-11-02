# SPDX-License-Identifier: GPL-3.0-or-later
"""Capitular devolvida (ADR-0007): o `limpar` põe a letra deslocada de volta no começo do
capítulo quando o próprio livro prova a palavra, e registra cada correção.

Casos medidos no Tides of Darkness: a letra no mesmo parágrafo ("stirred, D unable"), a letra
abrindo o parágrafo seguinte ("G demanded.", "A Lothar nodded") e o falso amigo ("From his
vantage A point"). O "I" e o "A" sem prova ficam como suspeita, como antes.
"""

from __future__ import annotations

from collections.abc import Sequence

from earbook.dominio.capitular import CapitularDevolvida
from earbook.dominio.limpeza import Juncao, LivroLimpo, limpar_para_o_ouvido
from earbook.dominio.segmento import Papel, Segmento


def _livro(*capitulos: Sequence[str]) -> LivroLimpo:
    """Cada capítulo começa com um título; o resto vira parágrafo, com ID na ordem."""
    entrada = [
        (
            f"c{c:03d}",
            [
                Segmento(f"c{c:03d}-s{s:04d}", Papel.TITULO if s == 1 else Papel.PARAGRAFO, texto)
                for s, texto in enumerate(["ONE", *textos], 1)
            ],
        )
        for c, textos in enumerate(capitulos, 1)
    ]
    return limpar_para_o_ouvido(entrada, "Tides of Darkness", "Aaron Rosenberg")


def _textos(livro: LivroLimpo, capitulo: int = 0) -> list[str]:
    return [s.texto for s in livro.capitulos[capitulo].segmentos[1:]]


def test_letra_no_mesmo_paragrafo_volta_para_o_comeco_da_palavra() -> None:
    texto = "awn, and fog. In Southshore, people stirred, D unable to see the dawn light."
    livro = _livro([texto])
    assert _textos(livro) == [
        "Dawn, and fog. In Southshore, people stirred, unable to see the dawn light."
    ]
    posicao = texto.index(" D ") + 1
    assert livro.capitulares == (CapitularDevolvida("c001-s0002", "c001-s0002", posicao, "D"),)
    assert livro.suspeitas == ()


def test_letra_que_abre_o_paragrafo_seguinte_sai_de_la() -> None:
    livro = _livro(["re we ready?”", "“Ready, sir.”", "A Lothar nodded. They are ready."])
    assert _textos(livro) == ["Are we ready?”", "“Ready, sir.”", "Lothar nodded. They are ready."]
    assert livro.capitulares == (CapitularDevolvida("c001-s0002", "c001-s0004", 0, "A"),)


def test_apostrofo_reto_e_tipografico_sao_o_mesmo_na_prova() -> None:
    livro = _livro(["ul'dan was furious.", "Gul\u2019dan sat. G He stood."])
    assert _textos(livro) == ["Gul'dan was furious.", "Gul\u2019dan sat. He stood."]


def test_sem_a_letra_a_frase_partida_se_junta_de_novo() -> None:
    # Tides, c004-s0487/s0488: "he" + "G demanded." era uma fala só, partida pela página.
    livro = _livro(["ul'dan was furious. Gul'dan sat.", "“Why?” he", "G demanded."])
    assert _textos(livro) == ["Gul'dan was furious. Gul'dan sat.", "“Why?” he demanded."]
    assert Juncao("c001-s0004", "c001-s0003") in livro.juncoes


def test_letra_que_e_palavra_volta_separada_quando_o_livro_prova_a_conversao() -> None:
    # "Adark" não existe; "a dark" existe. Os outros dois capítulos provam que esta
    # conversão desloca a capitular.
    livro = _livro(
        ["dark figure stood. From his vantage A point he saw a dark city."],
        ["re we ready? A They are here."],
        ["hey are not coming. T They left."],
    )
    assert _textos(livro) == ["A dark figure stood. From his vantage point he saw a dark city."]
    assert len(livro.capitulares) == 3


def test_letra_que_e_palavra_fica_suspeita_sem_prova_da_conversao() -> None:
    # Software Architecture: "saga A long story of heroic achievement." é verbete; o "A" é
    # artigo de verdade, e nenhuma outra capitular do livro prova o deslocamento.
    texto = "saga A long story of heroic achievement. A saga is long."
    livro = _livro([texto])
    assert _textos(livro) == [texto]
    assert livro.capitulares == ()
    assert [s.id for s in livro.suspeitas] == ["c001-s0002"]


def test_palavra_que_o_livro_nao_tem_fica_suspeita() -> None:
    texto = "awn came slowly as the camp stirred, D unable to sleep."
    livro = _livro([texto])
    assert _textos(livro) == [texto]
    assert livro.capitulares == ()


def test_as_duas_leituras_possiveis_ficam_suspeitas() -> None:
    # "Around" e "a round" existem no livro: não há como saber.
    texto = "round the fire. Then A they went around and drank a round."
    livro = _livro([texto], ["re we ready? A They are here."], ["hey left. T They did."])
    assert _textos(livro) == [texto]


def test_pronome_i_sem_pista_continua_suspeito() -> None:
    # Tides, c007-s0381: o "I" em "near the I cliff's edge" é igual ao pronome.
    texto = "t will be fine. It is near the I cliff."
    livro = _livro([texto])
    assert _textos(livro) == [texto]
    assert [s.id for s in livro.suspeitas] == ["c001-s0002"]


def test_letra_sozinha_no_paragrafo_nao_e_tirada() -> None:
    # Tirar a letra deixaria o segmento vazio, e a limpeza não apaga em silêncio.
    livro = _livro(["awn came at dawn.", "D"])
    assert _textos(livro) == ["awn came at dawn.", "D"]
    assert livro.capitulares == ()


def test_colada_que_nao_foi_devolvida_nao_prova_a_conversao() -> None:
    # Lote B da revisão: as duas coladas não se aplicam (a letra está sozinha no parágrafo) e
    # mesmo assim contavam para a maioria, que liberava o artigo de verdade do verbete.
    verbete = "saga A long story. A saga is long."
    livro = _livro(["awn came at dawn.", "D"], ["hey said they would.", "T"], [verbete])
    assert _textos(livro, 2) == [verbete]
    assert livro.capitulares == ()


def test_o_par_que_a_propria_letra_solta_forma_nao_prova_a_leitura() -> None:
    # Lote C da revisão: o "O" deslocado caiu antes de "rei", e o par "o rei" só existia por
    # causa dele. Os outros capítulos provam a conversão, mas não esta leitura.
    texto = "rei chegou cedo. Quando O rei sorriu, todos riram."
    livro = _livro([texto], ["oi assim. Foi F bom."], ["ra uma vez. Era E bom."])
    assert _textos(livro) == [texto]
    assert [s.id for s in livro.suspeitas] == ["c001-s0002"]


def test_a_letra_entra_depois_do_mesmo_prefixo_que_a_marcacao_pula() -> None:
    # Lote D da revisão: a marcação pulava qualquer espaço antes da primeira letra, e a
    # devolução só o espaço comum; com espaço inseparável, a letra entrava antes dele.
    texto = "\u00a0awn, and fog. People stirred, D unable to see the dawn light."
    livro = _livro([texto])
    assert _textos(livro) == ["\u00a0Dawn, and fog. People stirred, unable to see the dawn light."]


def test_segmento_suspeito_de_cabecalho_e_linha_curta_entra_uma_vez() -> None:
    # Lote D da revisão: a junção roda duas vezes (ADR-0007) e não repete a suspeita; na
    # primeira passada, o cabeçalho "dia 2" também já era suspeito pelo outro motivo.
    livro = _livro(["They walked on and", "dia 2", "x.", "dia 3", "y.", "dia 4"])
    ids = [s.id for s in livro.suspeitas]
    assert ids.count("c001-s0003") == 1
