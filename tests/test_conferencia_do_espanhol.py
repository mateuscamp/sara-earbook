# SPDX-License-Identifier: GPL-3.0-or-later
"""O `conferir` do livro traduzido do espanhol (ADR-0013): o que ficou em espanhol é acusado, e o
português do Manica não. As frases são montadas no teste, nas formas medidas nos dois livros."""

from __future__ import annotations

import pytest

from earbook.dominio.conferencia import Problema
from earbook.dominio.conferencia_da_traducao import ReguaDaTraducao, conferir_traducao
from earbook.dominio.lingua_do_original import (
    ESPANHOL,
    INGLES,
    LinguaDoOriginal,
    LinguaSemListaError,
    exigir_lingua_do_original,
    lingua_do_original,
)
from earbook.dominio.livro_limpo import CapituloLimpo
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.traducao import Pedido, Resposta, Traduzido

PORTUGUES = (
    "O fentanil é um opioide sintético usado na anestesia geral e na analgesia dos pacientes."
    " A dose de indução varia conforme a idade, o peso e o estado clínico de cada paciente."
    " Na criança e no idoso, a depuração é menor, e o efeito pode durar mais do que o esperado"
)
ESPANHOL_ESQUECIDO = "El ajuste de dosis depende según el peso y del estado del paciente."


def _conferir(papel: Papel, original: str, traducao: str) -> tuple[Problema, ...]:
    segmento = Segmento("c001-s0001", papel, original)
    capitulos = (CapituloLimpo("c001", (segmento,)),)
    pedidos = (Pedido("c001-l001", (segmento,)),)
    respostas = [Resposta("c001-l001", (Traduzido(segmento.id, traducao),))]
    return conferir_traducao(
        capitulos, pedidos, respostas, ReguaDaTraducao((), ESPANHOL), amostra=False
    )


def test_frase_que_ficou_em_espanhol_dentro_do_paragrafo_e_acusada() -> None:
    texto = f"{PORTUGUES}. {ESPANHOL_ESQUECIDO}"
    assert _conferir(Papel.PARAGRAFO, ESPANHOL_ESQUECIDO, texto) == (
        Problema(
            "c001-s0001",
            (
                "parece espanhol: 5 de 13 palavras são como 'el', 'los', 'y', na frase"
                " “El ajuste de dosis depende…”"
            ),
        ),
    )


def test_paragrafo_copiado_do_original_e_igual_ao_original_em_espanhol() -> None:
    assert _conferir(Papel.PARAGRAFO, ESPANHOL_ESQUECIDO, ESPANHOL_ESQUECIDO) == (
        Problema("c001-s0001", "igual ao original, em espanhol"),
    )


def test_titulo_em_caixa_alta_copiado_do_original_e_acusado() -> None:
    # 169 títulos do Miller vêm em maiúsculas: na linha toda em maiúsculas, "LOS" conta.
    titulo = "TRATAMIENTO DE LOS PACIENTES TOLERANTES A LOS OPIOIDES"
    assert _conferir(Papel.TITULO, titulo, titulo) == (
        Problema("c001-s0001", "igual ao original, em espanhol"),
    )


@pytest.mark.parametrize(
    "portugues",
    [
        # Medidos no Manica: o pronome colado ao verbo, a sigla e o eixo em maiúsculas, o nome.
        "É essencial conhecê-las para preveni-las e remediá-las, nunca as esquecendo.",
        # O mesmo, com o hífen não separável (U+2011) e o hífen tipográfico (U+2010).
        "É preciso conhecê\u2011las, preveni\u2011las e remediá\u2010las, nunca as esquecendo.",
        "Sempre que possível, instilar AL e vasoconstritor pelo conector em Y.",
        "Tipos de fraturas segundo a classificação de Le Fort, adaptada de Al Shetawi.",
        # O "et al." que a tradução mantém: 999 segmentos do Miller o têm.
        "Os estudos de Hodges et al. e de Sulecki et al. mostram isso.",
    ],
)
def test_portugues_do_manica_nao_parece_espanhol(portugues: str) -> None:
    assert _conferir(Papel.PARAGRAFO, ESPANHOL_ESQUECIDO, portugues) == ()


def test_terceira_lingua_copiada_do_original_nao_e_acusada() -> None:
    # A afiliação em inglês no Miller fica como está (`tradutor-es.md`, "Terceira língua").
    afiliacao = "Professor and Chair, Department of Anesthesiology and Critical Care"
    assert _conferir(Papel.PARAGRAFO, afiliacao, afiliacao) == ()


@pytest.mark.parametrize(
    ("idioma", "lingua"),
    [("es", ESPANHOL), ("es-AR", ESPANHOL), ("spa", ESPANHOL), ("en-US", INGLES), ("fr", None)],
)
def test_lingua_do_original_pelo_codigo_do_livro(
    idioma: str, lingua: LinguaDoOriginal | None
) -> None:
    assert lingua_do_original(idioma) == lingua


def test_lingua_sem_lista_e_recusada_com_o_idioma_e_as_linguas_que_tem() -> None:
    with pytest.raises(LinguaSemListaError, match=r"livro\.earbook: .*'de-DE'.*inglês e espanhol"):
        _ = exigir_lingua_do_original("de-DE", "livro.earbook")


def test_dez_por_cento_de_palavras_espanholas_ja_e_problema() -> None:
    # O limiar do espanhol (ADR-0013, "Calibragem"): 1 em 10 é acusado, 1 em 11 não.
    dez = "O paciente recebeu a dose correta con muito cuidado hoje."
    onze = "O paciente recebeu ontem a dose correta con muito cuidado hoje."
    assert _conferir(Papel.PARAGRAFO, ESPANHOL_ESQUECIDO, dez) == (
        Problema("c001-s0001", "parece espanhol: 1 de 10 palavras são como 'el', 'los', 'y'"),
    )
    assert _conferir(Papel.PARAGRAFO, ESPANHOL_ESQUECIDO, onze) == ()
