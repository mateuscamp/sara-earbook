# SPDX-License-Identifier: GPL-3.0-or-later
"""A seção de questões de múltipla escolha sai do texto lido, registrada (ADR-0008, "Tratado em
português e em espanhol", decisão 2).

No Manica, 61 capítulos terminam numa seção de questões de prova: o enunciado ("34.1 (TSA/2012)
…") e as alternativas ("A. …", "b. …"). O título vem em 20 grafias, 2 delas ilegíveis, e o
ADR-0008 proíbe reconhecer pelo título: a regra olha as alternativas e o enunciado. A lista de
letras no meio da prosa (o questionário do PCDT, as notas do GRADE) fica.
"""

from __future__ import annotations

import time

from earbook.dominio.limpeza import limpar_para_o_ouvido
from earbook.dominio.livro_limpo import LivroLimpo
from earbook.dominio.questoes_de_prova import MOTIVO_DAS_QUESTOES
from earbook.dominio.segmento import Papel, Segmento

PROSA = (Papel.PARAGRAFO, "O equilíbrio ácido-base depende de três variáveis independentes.")
TITULO = (Papel.TITULO, "Exercícios do capítulo")
OUTRO = (Papel.TITULO, "Considerações finais")
FIM = (Papel.PARAGRAFO, "O capítulo seguinte trata dos anestésicos locais.")


def _questao(enunciado: str, n: int = 4) -> list[tuple[Papel, str]]:
    letras = ["A", "b", "c", "D", "e"][:n]
    alternativas = [
        (Papel.PARAGRAFO, f"{letra}. Opção {k} da questão.") for k, letra in enumerate(letras)
    ]
    return [(Papel.PARAGRAFO, enunciado), *alternativas]


Q1 = _questao("34.1 (XYZ/2012) Qual variável determina a concentração de hidrogênio no plasma?")
Q2 = _questao("34.2 (XYZ/2013) Mulher de 51 anos chega torporosa. O distúrbio mais provável é:")
PROVA = _questao("34.3 (XYZ/2014) As variáveis que determinam o pH são:")
Q_SEM_PROVA = _questao("Qual destas variáveis determina a concentração de hidrogênio?")
# Medido: 40 mil segmentos em menos de 1 s com a conta acumulada; 3 s com 16 mil sem ela.
TEMPO_DO_CAPITULO_ENORME = 6.0


def _limpar(segmentos: list[tuple[Papel, str]]) -> LivroLimpo:
    capitulo = [
        Segmento(f"c001-s{n:04d}", papel, texto) for n, (papel, texto) in enumerate(segmentos, 1)
    ]
    return limpar_para_o_ouvido([("c001", capitulo)], "Livro", "Autor")


def _sobrou(livro: LivroLimpo) -> list[str]:
    return [s.texto for capitulo in livro.capitulos for s in capitulo.segmentos]


def test_secao_com_duas_questoes_sai_do_titulo_ao_fim_do_capitulo_registrada() -> None:
    livro = _limpar([PROSA, TITULO, *Q1, *Q2])
    assert _sobrou(livro) == [PROSA[1]]
    assert [(r.id, r.motivo) for r in livro.remocoes] == [
        (f"c001-s{n:04d}", MOTIVO_DAS_QUESTOES) for n in range(2, 13)
    ]


def test_o_titulo_ilegivel_nao_importa() -> None:
    assert _sobrou(_limpar([PROSA, (Papel.TITULO, "Qu esõ e d Provae"), *Q1, *Q2])) == [PROSA[1]]


def test_uma_lista_de_letras_depois_de_um_titulo_fica() -> None:
    # Um grupo só, sem enunciado de prova: é enumeração da prosa ("a) leves; b) moderadas…").
    lista = [PROSA, TITULO, *Q_SEM_PROVA]
    assert _sobrou(_limpar(lista)) == [texto for _, texto in lista]


def test_uma_questao_com_enunciado_de_prova_sai() -> None:
    assert _sobrou(_limpar([PROSA, TITULO, *PROVA])) == [PROSA[1]]


def test_dois_enunciados_de_prova_sem_alternativas_saem() -> None:
    enunciados = [
        (Papel.PARAGRAFO, "48.1 (XYZ/2013) Paciente de 32 anos é submetido a septoplastia."),
        (Papel.PARAGRAFO, "48.2 (XYZ/2014) Quando comparada à lidocaína, a procaína:"),
    ]
    assert _sobrou(_limpar([PROSA, TITULO, *enunciados])) == [PROSA[1]]


def test_um_enunciado_de_prova_sozinho_fica() -> None:
    norma = [PROSA, TITULO, (Papel.PARAGRAFO, "12.3 (RDC/2010) Dispõe sobre o funcionamento.")]
    assert _sobrou(_limpar(norma)) == [texto for _, texto in norma]


def test_duas_alternativas_nao_fazem_grupo() -> None:
    # Um enunciado de prova e duas alternativas: falta o segundo sinal.
    curta = [PROSA, TITULO, *_questao("34.1 (XYZ/2012) Qual das duas?", 2)]
    assert _sobrou(_limpar(curta)) == [texto for _, texto in curta]


def test_as_alternativas_fora_de_ordem_ou_sem_o_a_nao_fazem_grupo() -> None:
    def tres(*letras: str) -> list[tuple[Papel, str]]:
        return [(Papel.PARAGRAFO, f"{letra}. Opção.") for letra in letras]

    pergunta = (Papel.PARAGRAFO, "34.1 (XYZ/2012) Qual das opções?")
    for letras in (("B", "C", "D"), ("A", "C", "B")):
        soltas = [PROSA, TITULO, pergunta, *tres(*letras)]
        assert _sobrou(_limpar(soltas)) == [texto for _, texto in soltas]


def test_sem_titulo_perto_do_primeiro_grupo_nada_sai() -> None:
    # Mais de 3 parágrafos entre o título e o primeiro enunciado: questão solta no meio da prosa.
    longe = [TITULO, PROSA, PROSA, PROSA, PROSA, *Q1, *Q2]
    assert _sobrou(_limpar(longe)) == [texto for _, texto in longe]


def test_o_enunciado_em_tres_paragrafos_ainda_esta_perto_do_titulo() -> None:
    longo = [
        PROSA,
        TITULO,
        (Papel.PARAGRAFO, "Homem de 61 anos."),
        (Papel.PARAGRAFO, "Exames:"),
        *Q1,
        *Q2,
    ]
    assert _sobrou(_limpar(longo)) == [PROSA[1]]


def test_a_secao_seguida_de_outra_secao_de_prosa_sai_so_ate_o_proximo_titulo() -> None:
    prosa = [FIM, FIM, FIM, FIM, FIM, FIM, FIM, FIM, FIM, FIM, FIM, FIM]
    livro = _limpar([PROSA, TITULO, *Q1, *Q2, OUTRO, *prosa])
    assert _sobrou(livro) == [PROSA[1], OUTRO[1], *(texto for _, texto in prosa)]


def test_o_resto_de_figura_que_virou_titulo_dentro_da_secao_sai_com_ela() -> None:
    # No Manica, o gráfico de uma questão vira título e parágrafo curto no meio da seção.
    figura = [(Papel.TITULO, "C50"), (Papel.PARAGRAFO, "0 C50 C95 0,8")]
    livro = _limpar([PROSA, TITULO, *Q1, *figura, *Q2, *PROVA])
    assert _sobrou(livro) == [PROSA[1]]


def test_com_menos_da_metade_de_alternativas_e_enunciados_nada_sai() -> None:
    # Duas listas de letras com 20 parágrafos de prosa entre elas não são uma seção de questões.
    prosa = [FIM] * 20
    misto = [PROSA, TITULO, *Q1, *prosa, *Q2]
    assert _sobrou(_limpar(misto)) == [texto for _, texto in misto]


def test_a_nota_e_o_enunciado_sem_marca_saem_com_a_secao() -> None:
    nota = (Papel.NOTA, "V1 = volume do compartimento central.")
    assert _sobrou(_limpar([PROSA, TITULO, *Q1, nota, *Q2])) == [PROSA[1]]


def test_o_capitulo_sem_questoes_nao_muda() -> None:
    assert _sobrou(_limpar([TITULO, PROSA, OUTRO, FIM])) == [TITULO[1], PROSA[1], OUTRO[1], FIM[1]]


def test_a_alternativa_com_parentese_e_em_minuscula_conta() -> None:
    q = [
        (Papel.PARAGRAFO, "7 (ABC-2019) O fármaco de escolha é:"),
        (Papel.PARAGRAFO, "a) propofol;"),
        (Papel.PARAGRAFO, "b) etomidato;"),
        (Papel.PARAGRAFO, "c) midazolam."),
    ]
    assert _sobrou(_limpar([PROSA, TITULO, *q, *q])) == [PROSA[1]]


def test_a_lista_de_letras_do_comeco_do_capitulo_nao_esconde_a_secao_do_fim() -> None:
    # A enumeração da prosa vem antes, com título perto, e não serve; a seção de verdade vem depois.
    lista = [(Papel.TITULO, "Classificação"), *Q_SEM_PROVA]
    prosa = [FIM] * 12
    livro = _limpar([*lista, *prosa, TITULO, *Q1, *Q2])
    assert _sobrou(livro) == [texto for _, texto in (*lista, *prosa)]


def test_duas_secoes_de_questoes_no_mesmo_capitulo_saem() -> None:
    prosa = [FIM] * 30
    livro = _limpar([PROSA, TITULO, *Q1, *Q2, OUTRO, *prosa, TITULO, *Q1, *PROVA])
    assert _sobrou(livro) == [PROSA[1], OUTRO[1], *(texto for _, texto in prosa)]


def test_o_que_vem_depois_da_ultima_alternativa_fica() -> None:
    # R1 da code-review: a seção acaba na última alternativa. A seção curta que fecha o capítulo
    # ("Pontos-chave") e o começo do capítulo seguinte que a página trouxe para cá não são questão.
    pontos = [(Papel.TITULO, "Pontos-chave"), FIM, FIM]
    livro = _limpar([PROSA, TITULO, *Q1, *Q2, *pontos])
    assert _sobrou(livro) == [PROSA[1], *(texto for _, texto in pontos)]


def test_o_paragrafo_solto_depois_da_ultima_alternativa_fica() -> None:
    livro = _limpar([PROSA, TITULO, *Q1, *Q2, FIM])
    assert _sobrou(livro) == [PROSA[1], FIM[1]]


def test_listas_de_letras_sem_enunciado_de_prova_ficam_mesmo_sendo_varias() -> None:
    # A1 da code-audit: três enumerações em seções vizinhas no fim do capítulo ("Critérios
    # maiores: a) … b) … c) …") são prosa. Sem enunciado de prova, a regra não sabe que é questão.
    def enumeracao(titulo: str) -> list[tuple[Papel, str]]:
        itens = [(Papel.PARAGRAFO, f"{letra}) critério {letra};") for letra in "abc"]
        return [(Papel.TITULO, titulo), (Papel.PARAGRAFO, "São eles:"), *itens, FIM]

    capitulo = [PROSA, *enumeracao("Maiores"), *enumeracao("Menores"), *enumeracao("Outros")]
    assert _sobrou(_limpar(capitulo)) == [texto for _, texto in capitulo]
    juntas = [PROSA, TITULO, *Q_SEM_PROVA, *Q_SEM_PROVA]
    assert _sobrou(_limpar(juntas)) == [texto for _, texto in juntas]


def test_o_capitulo_enorme_de_listas_que_nao_servem_nao_custa_o_quadrado() -> None:
    # A2 da code-audit: o EPUB é entrada não confiável. 16 mil segmentos levavam 3 s.
    # Um enunciado de prova por título, com prosa demais em volta: nenhum trecho serve.
    bloco = [TITULO, (Papel.PARAGRAFO, "9.1 (XYZ/2010) Item."), FIM, FIM, FIM, FIM, FIM, FIM]
    capitulo = [
        Segmento(f"c001-s{n:06d}", papel, texto) for n, (papel, texto) in enumerate(bloco * 5000)
    ]
    inicio = time.perf_counter()
    _ = limpar_para_o_ouvido([("c001", capitulo)], "Livro", "Autor")
    assert time.perf_counter() - inicio < TEMPO_DO_CAPITULO_ENORME
