# SPDX-License-Identifier: GPL-3.0-or-later
"""O `conferir` no modo tradução (ADR-0006)."""

from __future__ import annotations

import pytest

from earbook.dominio.conferencia import Problema
from earbook.dominio.conferencia_da_traducao import conferir_traducao
from earbook.dominio.glossario import EntradaDoGlossario
from earbook.dominio.livro_limpo import CapituloLimpo
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.traducao import Pedido, Resposta, Traduzido

TITULO = Segmento("c001-s0001", Papel.TITULO, "The Doors of Perception")
PARAGRAFO = Segmento(
    "c001-s0002", Papel.PARAGRAFO, "It was in 1886 that the German pharmacologist published it."
)
NOTA = Segmento("c001-s0003", Papel.NOTA, "See the following papers by Humphry Osmond.")
CAPITULOS = (CapituloLimpo("c001", (TITULO, PARAGRAFO, NOTA)),)
PEDIDOS = (Pedido("c001-l001", (TITULO, PARAGRAFO)), Pedido("c001-l002", (NOTA,)))
TRADUCAO = {
    TITULO.id: "As Portas da Percepção",
    PARAGRAFO.id: "Foi em 1886 que o farmacologista alemão o publicou.",
    NOTA.id: "Ver os artigos a seguir, de Humphry Osmond.",
}


def _respostas(traducao: dict[str, str] = TRADUCAO) -> list[Resposta]:
    return [
        Resposta(
            p.lote, tuple(Traduzido(s.id, traducao[s.id]) for s in p.segmentos if s.id in traducao)
        )
        for p in PEDIDOS
    ]


def _conferir(
    respostas: list[Resposta],
    glossario: tuple[EntradaDoGlossario, ...] = (),
    *,
    amostra: bool = False,
) -> tuple[Problema, ...]:
    return conferir_traducao(CAPITULOS, PEDIDOS, respostas, glossario, amostra=amostra)


def _com(id_: str, texto: str) -> list[Resposta]:
    return _respostas({**TRADUCAO, id_: texto})


def test_livro_todo_traduzido_nao_tem_problema() -> None:
    assert _conferir(_respostas()) == ()


def test_segmentos_sem_traducao_sao_uma_linha_por_capitulo() -> None:
    # Um livro recém-exportado tem centenas: uma linha por segmento esconderia o resto.
    assert _conferir(_respostas({NOTA.id: TRADUCAO[NOTA.id]})) == (
        Problema("c001", "2 segmentos sem tradução (o primeiro é c001-s0001)"),
    )


def test_amostra_nao_cobra_o_segmento_sem_traducao() -> None:
    assert _conferir(_respostas({NOTA.id: TRADUCAO[NOTA.id]}), amostra=True) == ()


def test_resposta_sem_pedido_e_problema() -> None:
    respostas = [*_respostas(), Resposta("c001-l009", ())]
    assert _conferir(respostas) == (Problema("c001-l009", "resposta sem pedido"),)


def test_id_respondido_num_lote_que_nao_o_pediu_e_problema() -> None:
    um, dois = _respostas()
    respostas = [Resposta(um.lote, (*um.traduzidos, *dois.traduzidos)), Resposta(dois.lote, ())]
    assert _conferir(respostas) == (
        Problema("c001-s0003", "respondido no lote c001-l001, que não o pediu"),
    )


def test_id_traduzido_duas_vezes_e_problema() -> None:
    um, dois = _respostas()
    respostas = [um, Resposta(dois.lote, (*dois.traduzidos, *dois.traduzidos))]
    assert _conferir(respostas) == (Problema("c001-s0003", "traduzido 2 vezes"),)


def test_texto_que_mudou_em_limpos_depois_do_pedido_e_problema() -> None:
    # O agente corrigiu a capitular depois de exportar: a tradução é do texto velho.
    corrigido = Segmento(PARAGRAFO.id, Papel.PARAGRAFO, "It was in 1887 that the German...")
    capitulos = (CapituloLimpo("c001", (TITULO, corrigido, NOTA)),)
    assert conferir_traducao(capitulos, PEDIDOS, _respostas(), (), amostra=False) == (
        Problema(
            "c001-s0002",
            (
                "o texto em limpos/ mudou depois do pedido c001-l001: apague o pedido e a"
                " resposta e rode o traduzir"
            ),
        ),
    )


def test_id_pedido_que_saiu_de_limpos_e_problema() -> None:
    capitulos = (CapituloLimpo("c001", (TITULO, PARAGRAFO)),)
    assert conferir_traducao(capitulos, PEDIDOS, _respostas(), (), amostra=False) == (
        Problema("c001-s0003", "traduzido, mas não está em limpos/"),
    )


def test_traducao_vazia_e_problema() -> None:
    assert _conferir(_com(NOTA.id, "  ")) == (Problema("c001-s0003", "tradução vazia"),)


def test_texto_igual_ao_original_com_palavra_inglesa_e_problema() -> None:
    assert _conferir(_com(TITULO.id, TITULO.texto)) == (
        Problema("c001-s0001", "igual ao original, em inglês"),
    )


def test_nome_igual_ao_original_nao_e_problema() -> None:
    autor = Segmento("c002-s0001", Papel.TITULO, "Aldous Huxley")
    capitulos = (*CAPITULOS, CapituloLimpo("c002", (autor,)))
    pedidos = (*PEDIDOS, Pedido("c002-l001", (autor,)))
    respostas = [*_respostas(), Resposta("c002-l001", (Traduzido(autor.id, "Aldous Huxley"),))]
    assert conferir_traducao(capitulos, pedidos, respostas, (), amostra=False) == ()


def test_paragrafo_que_ficou_meio_em_ingles_e_problema() -> None:
    meio = "Foi em 1886 que the German pharmacologist published it and the rest."
    assert _conferir(_com(PARAGRAFO.id, meio)) == (
        Problema("c001-s0002", "parece inglês: 4 de 11 palavras são como 'the', 'of', 'and'"),
    )


def test_referencia_com_titulo_em_ingles_nao_parece_ingles() -> None:
    # A nota bibliográfica mantém o título da obra no original (ADR-0006).
    referencia = "Schizophrenia: A New Approach. De Humphry Osmond e John Smythies, abril de 1952."
    assert _conferir(_com(NOTA.id, referencia)) == ()


def test_url_nao_conta_como_ingles() -> None:
    texto = "Disponível em https://the-book.of/the-and-of-the-was-which-that, abril de 1952."
    assert _conferir(_com(NOTA.id, texto)) == ()


def test_nome_fora_do_glossario_e_problema_com_o_id() -> None:
    glossario = (EntradaDoGlossario("Humphry Osmond", "Humphry Osmond"),)
    assert _conferir(_com(NOTA.id, "Ver os artigos a seguir, do psiquiatra."), glossario) == (
        Problema("c001-s0003", "sem 'Humphry Osmond', que o glossário dá para 'Humphry Osmond'"),
    )


def test_nome_repetido_no_glossario_e_problema() -> None:
    glossario = (EntradaDoGlossario("Lewin", "Lewin"), EntradaDoGlossario("Lewin", "Levin"))
    assert _conferir(_respostas(), glossario) == (
        Problema("glossário", "'Lewin' aparece mais de uma vez"),
    )


def test_frase_inteira_em_ingles_dentro_de_paragrafo_traduzido_e_problema() -> None:
    # A1 da auditoria: medida no segmento, a frase inglesa se diluía no português.
    portugues = (
        "Foi em 1886 que o farmacologista alemão Ludwig Lewin publicou o primeiro estudo"
        " sistemático do cacto, que mais tarde receberia o seu nome. Para a religião primitiva"
        " e para os índios do México, era um amigo de longa data. Na verdade, era muito mais"
        " do que um amigo."
    )
    texto = f"{portugues} It was new to science and to the world of the doctors."
    assert _conferir(_com(PARAGRAFO.id, texto)) == (
        Problema(
            "c001-s0002",
            (
                "parece inglês: 8 de 12 palavras são como 'the', 'of', 'and', na frase"
                " \u201cIt was new to science\u2026\u201d"
            ),
        ),
    )


def test_trecho_de_oito_palavras_ja_e_julgado_e_de_sete_nao() -> None:
    assert _conferir(_com(NOTA.id, "The man and the dog went to sleep.")) == (
        Problema("c001-s0003", "parece inglês: 4 de 8 palavras são como 'the', 'of', 'and'"),
    )
    assert _conferir(_com(NOTA.id, "The man and the dog went home.")) == ()


def test_vinte_por_cento_de_palavras_inglesas_ja_e_problema() -> None:
    assert _conferir(_com(NOTA.id, "O gato e o cão dormiram the noite and dia.")) == (
        Problema("c001-s0003", "parece inglês: 2 de 10 palavras são como 'the', 'of', 'and'"),
    )
    assert _conferir(_com(NOTA.id, "O gato e o cão dormiram the noite and o dia.")) == ()


def test_texto_igual_ao_original_da_um_motivo_so() -> None:
    assert _conferir(_com(PARAGRAFO.id, PARAGRAFO.texto)) == (
        Problema("c001-s0002", "igual ao original, em inglês"),
    )


PORTUGUES = (
    "Foi em 1886 que o farmacologista alemão Ludwig Lewin publicou o primeiro estudo"
    " sistemático do cacto, que mais tarde receberia o seu nome. Para a religião primitiva"
    " e para os índios do México, era um amigo de longa data. Na verdade, era muito mais"
    " do que um amigo"
)
INGLES = "It was new to science and to the world of the doctors."
NA_FRASE = (
    "parece inglês: 8 de 12 palavras são como 'the', 'of', 'and', na frase"
    " \u201cIt was new to science\u2026\u201d"
)


@pytest.mark.parametrize("fim", [".", ".\u201d", "\u2026", "?", "!", "?)"])
def test_frase_inglesa_depois_de_qualquer_fim_de_frase_e_acusada(fim: str) -> None:
    texto = f"{PORTUGUES}{fim} {INGLES}"
    assert _conferir(_com(PARAGRAFO.id, texto)) == (Problema("c001-s0002", NA_FRASE),)


def test_frases_curtas_em_ingles_seguidas_sao_julgadas_juntas() -> None:
    # F3 da pós-auditoria: cada uma tinha menos de 8 palavras e escapava.
    texto = f"{PORTUGUES}. He is gone. They were all at the gate. Depois, voltou o silêncio."
    assert _conferir(_com(PARAGRAFO.id, texto)) == (
        Problema(
            "c001-s0002",
            (
                "parece inglês: 7 de 9 palavras são como 'the', 'of', 'and', na frase"
                " \u201cHe is gone. They were\u2026\u201d"
            ),
        ),
    )


@pytest.mark.parametrize("quem", ["J. R. Smythies", "Dr. Smythies"])
def test_inicial_e_titulo_abreviado_nao_cortam_a_frase(quem: str) -> None:
    # F2 da pós-auditoria: o corte depois de "R." deixava "Smythies cita o verso the dark
    # of the night…" sozinho, com 23% de palavras inglesas; a frase inteira tem 14%.
    traducao = (
        f"O ensaio publicado em 1953 por um certo {quem} cita o verso the dark of the night,"
        " de um poeta."
    )
    assert _conferir(_com(NOTA.id, traducao)) == ()


def _nota_traduzida(original: str, traducao: str) -> tuple[Problema, ...]:
    nota = Segmento(NOTA.id, Papel.NOTA, original)
    capitulos = (CapituloLimpo("c001", (TITULO, PARAGRAFO, nota)),)
    pedidos = (PEDIDOS[0], Pedido("c001-l002", (nota,)))
    respostas = [*_respostas()[:1], Resposta("c001-l002", (Traduzido(NOTA.id, traducao),))]
    return conferir_traducao(capitulos, pedidos, respostas, (), amostra=False)


def test_titulo_de_obra_copiado_do_original_nao_conta_como_ingles() -> None:
    # F1 da pós-auditoria: o tradutor mantém o título da obra no original, como mandam as
    # instruções, e o "the" e o "of" do título faziam a nota parecer inglês.
    original = (
        "The Mescalin Phenomena. By John Smythies. The British Journal for the Philosophy"
        " of Science. Vol. iii. February 1953."
    )
    traducao = (
        "The Mescalin Phenomena. De John Smythies. The British Journal for the Philosophy"
        " of Science. Vol. iii. Fevereiro de 1953."
    )
    assert _nota_traduzida(original, traducao) == ()


def test_titulo_que_nao_esta_no_original_conta_como_ingles() -> None:
    original = "See the papers by John Smythies."
    traducao = "Ver The Effects of the Drug on the Mind of the Man, de John Smythies."
    # 13 palavras, não 15: "John Smythies" também está no original e sai da conta.
    assert _nota_traduzida(original, traducao) == (
        Problema("c001-s0003", "parece inglês: 6 de 13 palavras são como 'the', 'of', 'and'"),
    )


def test_frase_em_ingles_copiada_do_original_continua_acusada() -> None:
    # A frase esquecida não é título: só uma palavra com maiúscula.
    original = f"The note begins here. {INGLES}"
    traducao = f"A nota começa aqui, na primeira linha da página. {INGLES}"
    assert _nota_traduzida(original, traducao) == (
        Problema("c001-s0003", "parece inglês: 8 de 21 palavras são como 'the', 'of', 'and'"),
    )


def _paragrafo_traduzido(original: str, traducao: str) -> tuple[Problema, ...]:
    paragrafo = Segmento(PARAGRAFO.id, Papel.PARAGRAFO, original)
    capitulos = (CapituloLimpo("c001", (TITULO, paragrafo, NOTA)),)
    pedidos = (Pedido("c001-l001", (TITULO, paragrafo)), PEDIDOS[1])
    um, dois = _respostas()
    traduzidos = (um.traduzidos[0], Traduzido(PARAGRAFO.id, traducao))
    respostas = [Resposta(um.lote, traduzidos), dois]
    return conferir_traducao(capitulos, pedidos, respostas, (), amostra=False)


def test_frase_curta_em_portugues_nao_dilui_a_frase_inglesa_seguinte() -> None:
    # A1 da pós-auditoria curta (Tides, c007-s0317): colada na frase curta, a frase
    # inglesa caía abaixo dos 20%; 187 frases do Tides escapavam assim.
    texto = (
        f"{PORTUGUES}. — Não, ainda não — respondeu ele, cansado. He tapped the hard red"
        " stone before him and frowned."
    )
    assert _conferir(_com(PARAGRAFO.id, texto)) == (
        Problema(
            "c001-s0002",
            (
                "parece inglês: 3 de 10 palavras são como 'the', 'of', 'and', na frase"
                " \u201cHe tapped the hard red\u2026\u201d"
            ),
        ),
    )


def test_fala_em_ingles_copiada_do_original_no_corpo_continua_acusada() -> None:
    # A2 da pós-auditoria curta: a isenção do título só vale na nota; no corpo, "And I" de
    # uma fala esquecida saía da conta como se fosse título.
    fala = "\u201cAnd I will see them suffer for it.\u201d"
    original = f"Hatred. They brought this destruction upon us, she spat. {fala}"
    assert _paragrafo_traduzido(original, f"{PORTUGUES}. {fala}") == (
        Problema(
            "c001-s0002",
            (
                "parece inglês: 4 de 8 palavras são como 'the', 'of', 'and', na frase"
                " \u201c\u201cAnd I will see them\u2026\u201d"
            ),
        ),
    )


def test_titulo_depois_de_palavra_portuguesa_com_maiuscula_e_isento_na_nota() -> None:
    # A4 da pós-auditoria curta: "Ver The Varieties…" inteiro não está no original.
    original = "See The Varieties of Religious Experience, by William James, Lecture XVI."
    traducao = "Ver The Varieties of Religious Experience, de William James, conferência 16."
    assert _nota_traduzida(original, traducao) == ()


def test_referencia_com_titulo_em_minusculas_nao_e_acusada_por_frases_juntas() -> None:
    # A3 da pós-auditoria curta: na nota, as frases curtas não se juntam.
    original = (
        "Anthropic. Detecting and countering misuse of AI: September 2026. San Francisco:"
        " Anthropic, September 10, 2026."
    )
    traducao = (
        "Anthropic. Detecting and countering misuse of AI: September 2026. São Francisco:"
        " Anthropic, 10 de setembro de 2026."
    )
    assert _nota_traduzida(original, traducao) == ()
