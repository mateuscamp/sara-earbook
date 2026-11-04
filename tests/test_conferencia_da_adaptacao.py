# SPDX-License-Identifier: GPL-3.0-or-later
"""O `conferir` no modo adaptação: cada ID num grupo, e cada grupo fiel às fontes (ADR-0009)."""

from __future__ import annotations

from dataclasses import replace

from earbook.dominio.adaptacao import Grupo, Omitido, RespostaDaAdaptacao, TipoDoGrupo
from earbook.dominio.conferencia_da_adaptacao import (
    avisos_da_adaptacao,
    conferir_adaptacao,
    conferir_sumario,
)
from earbook.dominio.glossario import EntradaDoGlossario
from earbook.dominio.limpeza import CapituloLimpo
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.traducao import Pedido

LIMPOS = (
    Segmento("c001-s0001", Papel.TITULO, "Quadro 27.1"),
    Segmento("c001-s0002", Papel.PARAGRAFO, "• Humor deprimido por 2 semanas"),
    Segmento("c001-s0003", Papel.PARAGRAFO, "• Anedonia"),
    Segmento("c001-s0004", Papel.PARAGRAFO, "A anedonia é a perda do prazer."),
    Segmento("c001-s0005", Papel.PARAGRAFO, "O SRAA regula a vigília."),
)
PEDIDO = Pedido("c001-l001", LIMPOS)
FIEL = (
    Grupo(("c001-s0001",), TipoDoGrupo.DESCARTE, descarte="rotulo"),
    Grupo(
        ("c001-s0002", "c001-s0003"),
        TipoDoGrupo.TEXTO,
        texto=("Os critérios são humor deprimido por 2 semanas e anedonia.",),
    ),
    Grupo(("c001-s0004",), TipoDoGrupo.IGUAL),
    Grupo(("c001-s0005",), TipoDoGrupo.TEXTO, texto=("O sistema ativador regula a vigília.",)),
)
GLOSSARIO = (EntradaDoGlossario("SRAA", "sistema ativador"),)


def _conferir(
    grupos: tuple[Grupo, ...],
    *,
    pedido: Pedido = PEDIDO,
    lote: str = "c001-l001",
    amostra: bool = False,
) -> list[tuple[str, str]]:
    problemas = conferir_adaptacao(
        [CapituloLimpo("c001", LIMPOS)],
        [pedido],
        [RespostaDaAdaptacao(lote, grupos)],
        GLOSSARIO,
        amostra=amostra,
    )
    return [(p.id, p.motivo) for p in problemas]


def _trocar(posicao: int, grupo: Grupo) -> tuple[Grupo, ...]:
    return (*FIEL[:posicao], grupo, *FIEL[posicao + 1 :])


def test_adaptacao_inteira_e_fiel_nao_tem_problema() -> None:
    assert _conferir(FIEL) == []


def test_segmento_sem_grupo_e_acusado_menos_na_amostra() -> None:
    assert _conferir(FIEL[:3]) == [("c001", "1 segmentos sem adaptação")]
    assert _conferir(FIEL[:3], amostra=True) == []


def test_segmento_em_dois_grupos_e_acusado() -> None:
    grupos = (*FIEL, Grupo(("c001-s0004",), TipoDoGrupo.IGUAL))
    assert _conferir(grupos) == [("c001-s0004", "em 2 grupos")]


def test_fonte_que_o_lote_nao_pediu_e_acusada() -> None:
    pedido = Pedido("c001-l001", LIMPOS[:4])
    assert _conferir(FIEL, pedido=pedido) == [("c001-s0005", "no lote c001-l001, que não o pediu")]


def test_resposta_sem_pedido_e_acusada() -> None:
    assert ("c001-l002", "resposta sem pedido") in _conferir(FIEL, lote="c001-l002")


def test_fontes_que_nao_sao_vizinhas_sao_acusadas() -> None:
    grupos = (
        FIEL[0],
        Grupo(("c001-s0002", "c001-s0004"), TipoDoGrupo.TEXTO, texto=FIEL[1].texto),
        Grupo(("c001-s0003",), TipoDoGrupo.IGUAL),
        FIEL[3],
    )
    assert ("c001-s0002", "fontes que não são vizinhas no pedido") in _conferir(grupos)


def test_grupo_que_mistura_titulo_e_paragrafo_e_acusado() -> None:
    grupo = Grupo(("c001-s0001", "c001-s0002", "c001-s0003"), TipoDoGrupo.TEXTO, FIEL[1].texto)
    assert _conferir((grupo, *FIEL[2:])) == [("c001-s0001", "o grupo mistura título e parágrafo")]


def test_titulo_com_mais_de_um_paragrafo_e_acusado() -> None:
    grupo = Grupo(("c001-s0001",), TipoDoGrupo.TEXTO, texto=("Critérios", "do DSM"))
    assert _conferir(_trocar(0, grupo)) == [("c001-s0001", "o título tem 2 parágrafos")]


def test_paragrafo_vazio_e_caractere_fora_do_xml_sao_acusados() -> None:
    grupo = Grupo(("c001-s0004",), TipoDoGrupo.TEXTO, texto=(" ", "A anedonia\x0c é a perda."))
    assert _conferir(_trocar(2, grupo)) == [
        ("c001-s0004", "parágrafo vazio"),
        ("c001-s0004", "texto com caractere que o XML não aceita: U+000C"),
    ]


def test_pedido_que_mudou_em_limpos_e_adaptacao_velha() -> None:
    velho = replace(LIMPOS[3], texto="A anedonia era outra coisa.")
    pedido = Pedido("c001-l001", (*LIMPOS[:3], velho, LIMPOS[4]))
    assert _conferir(FIEL, pedido=pedido) == [
        ("c001-s0004", "adaptação velha: o texto mudou em limpos depois do pedido")
    ]


def test_numero_e_termo_perdidos_sao_acusados_no_primeiro_id_do_grupo() -> None:
    grupo = replace(FIEL[1], texto=("Os critérios são humor deprimido por semanas.",))
    assert _conferir(_trocar(1, grupo)) == [
        ("c001-s0002", "o número 2 das fontes não está no texto"),
        ("c001-s0002", "o termo 'Anedonia' das fontes não está no texto nem em omitidos"),
    ]


def test_termo_omitido_de_proposito_vira_aviso_e_nao_problema() -> None:
    grupo = replace(
        FIEL[1],
        texto=("Os critérios são humor deprimido por 2 semanas.",),
        omitidos=(Omitido("Anedonia", "dita no parágrafo seguinte"),),
    )
    resposta = RespostaDaAdaptacao("c001-l001", _trocar(1, grupo))
    assert _conferir(resposta.grupos) == []
    assert [(p.id, p.motivo) for p in avisos_da_adaptacao([resposta])] == [
        ("c001-s0002", "omitiu 'Anedonia': dita no parágrafo seguinte")
    ]


def test_descarte_repetido_precisa_dos_termos_nos_grupos_vizinhos() -> None:
    provado = Grupo(("c001-s0004",), TipoDoGrupo.DESCARTE, descarte="repetido")
    assert _conferir(_trocar(2, provado)) == []
    sem_prova = replace(FIEL[1], texto=("Os critérios são humor deprimido por 2 semanas.",))
    grupos = (FIEL[0], sem_prova, provado, FIEL[3])
    assert ("c001-s0004", "descarte 'repetido' sem prova: 'anedonia' não está ao lado") in (
        _conferir(grupos)
    )


def test_descarte_de_rotulo_que_nao_e_rotulo_e_motivo_desconhecido_sao_acusados() -> None:
    rotulo = Grupo(("c001-s0004",), TipoDoGrupo.DESCARTE, descarte="rotulo")
    assert _conferir(_trocar(2, rotulo)) == [
        ("c001-s0004", "descarte 'rotulo' de um texto que não é rótulo")
    ]
    outro = Grupo(("c001-s0004",), TipoDoGrupo.DESCARTE, descarte="chato")
    assert _conferir(_trocar(2, outro)) == [
        ("c001-s0004", "motivo de descarte desconhecido: 'chato'")
    ]
    sem_secao = Grupo(("c001-s0004",), TipoDoGrupo.DESCARTE, descarte="decisao:")
    assert _conferir(_trocar(2, sem_secao)) == [
        ("c001-s0004", "descarte 'decisao' sem a seção de decisoes.md")
    ]


def test_descarte_por_decisao_vira_aviso() -> None:
    grupo = Grupo(("c001-s0004",), TipoDoGrupo.DESCARTE, descarte="decisao: o que sai do áudio")
    resposta = RespostaDaAdaptacao("c001-l001", _trocar(2, grupo))
    assert [(p.id, p.motivo) for p in avisos_da_adaptacao([resposta])] == [
        ("c001-s0004", "descartado por decisão: o que sai do áudio")
    ]


def test_sigla_que_o_glossario_manda_por_extenso_e_acusada() -> None:
    grupo = replace(FIEL[3], texto=("O SRAA regula a vigília.",))
    assert _conferir(_trocar(3, grupo)) == [
        ("c001-s0005", "'SRAA' ficou no original; o glossário diz 'sistema ativador'")
    ]


def test_o_que_so_funciona_no_papel_no_texto_adaptado_e_acusado() -> None:
    grupo = replace(FIEL[1], texto=("• Humor deprimido por 2 semanas", "• Anedonia"))
    assert _conferir(_trocar(1, grupo)) == [
        ("c001-s0002", "marcador de lista '•'"),
        ("c001-s0002", "marcador de lista '•'"),
    ]


def test_descarte_repetido_se_prova_tambem_pelo_grupo_seguinte() -> None:
    """O destaque da Distimia: o nome está no título antes, e o resto, no parágrafo depois."""
    limpos = (
        Segmento("c031-s0103", Papel.TITULO, "Distimia"),
        Segmento("c031-s0104", Papel.PARAGRAFO, "Distimia é uma depressão crônica, duradoura."),
        Segmento("c031-s0105", Papel.PARAGRAFO, "Trata-se de uma depressão crônica, duradoura."),
    )
    grupos = (
        Grupo(("c031-s0103",), TipoDoGrupo.IGUAL),
        Grupo(("c031-s0104",), TipoDoGrupo.DESCARTE, descarte="repetido"),
        Grupo(("c031-s0105",), TipoDoGrupo.IGUAL),
    )
    problemas = conferir_adaptacao(
        [CapituloLimpo("c031", limpos)],
        [Pedido("c031-l001", limpos)],
        [RespostaDaAdaptacao("c031-l001", grupos)],
        (),
        amostra=False,
    )
    assert problemas == ()


def test_item_do_sumario_juntado_num_paragrafo_so_e_acusado() -> None:
    grupo = Grupo(("c001-s0001", "c001-s0002"), TipoDoGrupo.TEXTO, texto=("Um e dois.",))
    resposta = RespostaDaAdaptacao("c001-l001", (grupo,))
    motivos = [(p.id, p.motivo) for p in conferir_sumario([resposta], frozenset({"c001-s0002"}))]
    assert motivos == [
        ("c001-s0002", "item do sumário não sai nem se junta: use igual ou um texto só dele")
    ]


_FONTE = Segmento("c002-s0001", Papel.PARAGRAFO, "Em 30 pessoas, 51,1% com 5 mg e 2 g/m2.")


def _omitindo(texto: str, numero: str, motivo: str, fonte: Segmento = _FONTE) -> list[str]:
    grupo = Grupo(
        (fonte.id,), TipoDoGrupo.TEXTO, texto=(texto,), omitidos=(Omitido(numero, motivo),)
    )
    problemas = conferir_adaptacao(
        [CapituloLimpo("c002", (fonte,))],
        [Pedido("c002-l001", (fonte,))],
        [RespostaDaAdaptacao("c002-l001", (grupo,))],
        (),
        amostra=False,
    )
    return [p.motivo for p in problemas]


def test_numero_omitido_com_motivo_da_lista_passa_e_vira_aviso() -> None:
    texto = "Em pessoas, 51,1% com 5 mg e 2 g/m2."
    assert _omitindo(texto, "30", "citação") == []
    grupo = Grupo(("c002-s0001",), TipoDoGrupo.TEXTO, texto=(texto,))
    grupo = replace(grupo, omitidos=(Omitido("30", "citação: ano partido"),))
    avisos = avisos_da_adaptacao([RespostaDaAdaptacao("c002-l001", (grupo,))])
    assert [(p.id, p.motivo) for p in avisos] == [
        ("c002-s0001", "omitiu o número 30: citação: ano partido")
    ]


def test_numero_omitido_com_motivo_fora_da_lista_e_problema() -> None:
    texto = "Em pessoas, 51,1% com 5 mg e 2 g/m2."
    assert _omitindo(texto, "30", "ficou melhor assim") == [
        "o número 30 foi omitido com motivo fora da lista: 'ficou melhor assim'"
    ]


def test_porcentagem_e_dose_nunca_se_omitem() -> None:
    assert _omitindo("Em 30 pessoas, com 5 mg e 2 g/m2.", "51,1", "citação") == [
        "o número 51,1 é porcentagem ou dose e não se omite"
    ]
    assert _omitindo("Em 30 pessoas, 51,1% e 2 g/m2.", "5", "unidade") == [
        "o número 5 é porcentagem ou dose e não se omite"
    ]


def test_numero_omitido_que_continua_no_texto_e_problema() -> None:
    assert _omitindo("Em 30 pessoas, 51,1% com 5 mg e 2 g/m2.", "30", "data") == [
        "o número 30 foi declarado omitido, mas continua no texto"
    ]


def test_numero_omitido_que_as_fontes_nao_tem_e_problema() -> None:
    texto = "Em 30 pessoas, 51,1% com 5 mg e 2 g/m2."
    assert _omitindo(texto, "77", "data") == ["o número 77 foi omitido, mas as fontes não o têm"]


def test_motivo_do_numero_pode_trazer_detalhe_depois_dos_dois_pontos() -> None:
    texto = "Em pessoas, 51,1% com 5 mg e 2 g/m2."
    assert _omitindo(texto, "30", "citação: ano partido pela quebra") == []


def test_numero_dentro_de_porcentagem_maior_nao_e_a_porcentagem() -> None:
    fonte = replace(_FONTE, texto="Em 1 caso, 51,1% melhoraram.")
    assert _omitindo("Em um caso, 51,1% melhoraram.", "1", "ordinal", fonte) == []


def test_numero_que_abre_faixa_de_porcentagem_ou_dose_nao_se_omite() -> None:
    faixas = (
        "De 5 a 15% dos adultos.",
        "De 5 e 15% dos adultos.",
        "De 5 ou 15% dos adultos.",
        "De 5-15% dos adultos.",
        "De 5 a 10 mg ao dia.",
    )
    for texto in faixas:
        fonte = replace(_FONTE, texto=texto)
        assert _omitindo(texto.replace("5 ", "", 1), "5", "data", fonte) == [
            "o número 5 é porcentagem ou dose e não se omite"
        ]


def test_numero_seguido_de_outro_numero_sem_medida_ainda_se_omite() -> None:
    fonte = replace(_FONTE, texto="De 5 a 15 pessoas.")
    assert _omitindo("De 15 pessoas.", "5", "data", fonte) == []


def test_numero_seguido_de_por_cento_nao_se_omite() -> None:
    fonte = replace(_FONTE, texto="Cerca de 5 por cento dos adultos.")
    assert _omitindo("Cerca de dos adultos.", "5", "data", fonte) == [
        "o número 5 é porcentagem ou dose e não se omite"
    ]
