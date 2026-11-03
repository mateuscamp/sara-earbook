# SPDX-License-Identifier: GPL-3.0-or-later
"""O Quadro do PDF fica no lugar, depois da frase que ele interrompe (ADR-0004, "Quadro no lugar").

No Dalgalarrondo, o quadro abre com o rótulo "Quadro 5.1" em 12 pt (o corpo tem 10), e a legenda
e o conteúdo vêm em 8 e 9 pt. O conteúdo virava nota e ia para "Notas", no fim do capítulo, e a
continuação da frase que o quadro interrompe colava na legenda dele.
"""

from __future__ import annotations

from pathlib import Path

from earbook.comandos.importar_pdf import importar_pdf
from earbook.comandos.preparar import preparar
from earbook.dominio.blocos import LivroMontado, montar_blocos
from earbook.dominio.pagina import Linha, Pagina
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf

ENTRELINHA = 0.017
ROTULO = "Quadro 5.1"
LEGENDA = "Exemplos de formulação diagnóstica"
EIXO_1 = "Eixo 1. Diagnóstico do transtorno mental Esquizofrenia e depressão grave."
EIXO_2 = "Eixo 2. Diagnóstico de personalidade e nível intelectual."
INTERROMPIDO = "O texto do capítulo começa aqui e segue até o pé da página, capaz de"
CONTINUACAO = "identificar o objeto pesquisado."
OUTRO = "Outro parágrafo começa aqui."


def _linhas(tamanho: float, topo: float, *textos: str, passo: float = ENTRELINHA) -> list[Linha]:
    """Linhas de largura cheia, de x = 66 a 446: nenhuma calha, nenhuma coluna."""
    return [
        Linha(texto, x=66.0, fim=446.0, topo=topo + n * passo, tamanho=tamanho)
        for n, texto in enumerate(textos)
    ]


def _corpo() -> list[Linha]:
    """Um parágrafo de 10 pt no alto da 1ª página: firma o corpo e a entrelinha do livro."""
    meio = ["segue com as medidas do livro"] * 7
    return _linhas(10.0, 0.1, "Um parágrafo de corpo que", *meio, "e acaba aqui.")


def _interrompido(topo: float = 0.3) -> list[Linha]:
    """O parágrafo que chega ao quadro sem fechar a frase."""
    return _linhas(
        10.0, topo, "O texto do capítulo começa aqui e", "segue até o pé da página, capaz de"
    )


def _quadro(topo: float, rotulo: str = ROTULO) -> list[Linha]:
    """O rótulo de 12 pt, a legenda de 9 pt e duas linhas de conteúdo de 8 pt (Quadro 5.1)."""
    return [
        *_linhas(12.0, topo, rotulo),
        *_linhas(9.0, topo + 0.03, LEGENDA),
        *_linhas(
            8.0,
            topo + 0.07,
            "Eixo 1. Diagnóstico do transtorno mental",
            "Esquizofrenia e depressão grave.",
            passo=0.013,
        ),
        *_linhas(8.0, topo + 0.12, EIXO_2),
    ]


def _montar(*paginas: list[Linha]) -> LivroMontado:
    """O `_corpo` entra no alto da 1ª página."""
    linhas = [[*_corpo(), *paginas[0]], *paginas[1:]]
    return montar_blocos([Pagina(n, tuple(lista)) for n, lista in enumerate(linhas, 1)])


def _resumo(livro: LivroMontado) -> list[tuple[str, str]]:
    """Tipo e texto de cada bloco, sem o parágrafo do `_corpo`."""
    return [(bloco.tipo.value, bloco.texto) for bloco in livro.blocos][1:]


def _textos(livro: LivroMontado) -> list[str]:
    return [texto for _, texto in _resumo(livro)]


def test_conteudo_do_quadro_em_letra_menor_e_paragrafo_e_nao_nota() -> None:
    # A nota ia para "Notas", no fim do capítulo, longe do texto (ADR-0005): 132 das 171 notas do
    # Dalgalarrondo eram conteúdo de quadro.
    livro = _montar([*_linhas(10.0, 0.3, "Um parágrafo que fecha a frase."), *_quadro(0.4)])
    assert _resumo(livro) == [
        ("paragrafo", "Um parágrafo que fecha a frase."),
        ("titulo", ROTULO),
        ("paragrafo", LEGENDA),
        ("paragrafo", EIXO_1),
        ("paragrafo", EIXO_2),
    ]


def test_frase_interrompida_pelo_quadro_volta_inteira_e_o_quadro_vem_depois() -> None:
    # Dalgalarrondo p. 43 e 44: a continuação em minúscula colava na legenda do quadro,
    # "Exemplos de formulação diagnóstica satisfatoriamente o objeto pesquisado…".
    pagina_2 = [*_linhas(10.0, 0.1, CONTINUACAO), *_linhas(10.0, 0.15, OUTRO)]
    livro = _montar([*_interrompido(), *_quadro(0.4)], pagina_2)
    assert _textos(livro) == [
        f"{INTERROMPIDO} {CONTINUACAO}",
        ROTULO,
        LEGENDA,
        EIXO_1,
        EIXO_2,
        OUTRO,
    ]


def test_continuacao_depois_de_quadro_que_acaba_em_linha_de_9_pt_volta_ao_texto() -> None:
    # Quando a última linha do quadro é de 9 pt (cabeçalho de coluna), ela é parágrafo, e a
    # continuação na página seguinte colava nela.
    quadro = [*_quadro(0.4), *_linhas(9.0, 0.56, "Fonte: adaptado de Carlat")]
    livro = _montar([*_interrompido(), *quadro], _linhas(10.0, 0.1, CONTINUACAO))
    assert _textos(livro) == [
        f"{INTERROMPIDO} {CONTINUACAO}",
        ROTULO,
        LEGENDA,
        EIXO_1,
        EIXO_2,
        "Fonte: adaptado de Carlat",
    ]


def test_quadro_espera_a_frase_partida_por_um_destaque_acabar() -> None:
    # Dalgalarrondo p. 70: depois do quadro, a continuação ("…os pri-") é partida por um destaque
    # de 9 pt, e a frase acaba em "meiros três minutos…". Se o quadro ficasse logo depois do
    # parágrafo retomado, ele cairia entre o destaque e o resto da frase, e o `limpar` não
    # tiraria o destaque nem emendaria a palavra.
    pagina_2 = [
        *_linhas(10.0, 0.1, "com alguma experiência, os pri-"),
        *_linhas(9.0, 0.14, "Os primeiros minutos", "são decisivos.", passo=0.015),
        *_linhas(10.0, 0.2, "meiros minutos são decisivos."),
        *_linhas(10.0, 0.25, OUTRO),
    ]
    livro = _montar([*_interrompido(), *_quadro(0.4)], pagina_2)
    assert _textos(livro) == [
        f"{INTERROMPIDO} com alguma experiência, os pri-",
        "Os primeiros minutos são decisivos.",
        "meiros minutos são decisivos.",
        ROTULO,
        LEGENDA,
        EIXO_1,
        EIXO_2,
        OUTRO,
    ]


def test_quadro_entre_paragrafos_fica_no_lugar() -> None:
    antes = _linhas(10.0, 0.3, "Um parágrafo que fecha a frase.")
    depois = _linhas(10.0, 0.6, OUTRO)
    livro = _montar([*antes, *_quadro(0.4), *depois])
    assert _textos(livro) == [
        "Um parágrafo que fecha a frase.",
        ROTULO,
        LEGENDA,
        EIXO_1,
        EIXO_2,
        OUTRO,
    ]


def test_quadro_entra_antes_do_titulo_seguinte() -> None:
    # "Questões de revisão" (12 pt) depois do quadro: o quadro é da seção de antes.
    titulo = _linhas(12.0, 0.6, "Questões de revisão")
    livro = _montar([*_interrompido(), *_quadro(0.4), *titulo])
    assert _textos(livro) == [INTERROMPIDO, ROTULO, LEGENDA, EIXO_1, EIXO_2, "Questões de revisão"]


def test_quadro_no_fim_do_livro_nao_se_perde() -> None:
    livro = _montar([*_interrompido(), *_quadro(0.4)])
    assert _textos(livro) == [INTERROMPIDO, ROTULO, LEGENDA, EIXO_1, EIXO_2]


def test_rotulo_seguido_continua_o_quadro() -> None:
    # Dalgalarrondo p. 71 e 72: "Quadro 8.2" na página seguinte, a continuação do mesmo quadro,
    # e o texto interrompido antes do primeiro rótulo só continua depois do segundo.
    pagina_2 = [*_quadro(0.1, "Quadro 5.1"), *_linhas(10.0, 0.3, CONTINUACAO)]
    livro = _montar([*_interrompido(), *_quadro(0.4)], pagina_2)
    quadro = [ROTULO, LEGENDA, EIXO_1, EIXO_2]
    assert _textos(livro) == [f"{INTERROMPIDO} {CONTINUACAO}", *quadro, *quadro]


def test_quadros_seguidos_esperam_juntos_a_frase_partida_por_um_destaque() -> None:
    # Dalgalarrondo p. 180 e 181: os Quadros 17.2 e 17.3 seguidos. O rótulo do segundo não solta o
    # primeiro: a frase que eles interrompem ainda não acabou. Soltando, "tigar detidamente…"
    # descia para depois do Quadro 17.2 (P1 da pós-auditoria, 15 posições do livro).
    pagina_2 = [
        *_linhas(10.0, 0.1, "com alguma experiência, os pri-"),
        *_linhas(9.0, 0.14, "Os primeiros minutos", "são decisivos.", passo=0.015),
        *_linhas(10.0, 0.2, "meiros minutos são decisivos."),
        *_linhas(10.0, 0.25, OUTRO),
    ]
    livro = _montar([*_interrompido(), *_quadro(0.4), *_quadro(0.6, "Quadro 5.2")], pagina_2)
    assert _textos(livro) == [
        f"{INTERROMPIDO} com alguma experiência, os pri-",
        "Os primeiros minutos são decisivos.",
        "meiros minutos são decisivos.",
        *[ROTULO, LEGENDA, EIXO_1, EIXO_2],
        *["Quadro 5.2", LEGENDA, EIXO_1, EIXO_2],
        OUTRO,
    ]


def test_rotulo_tabela_tambem_abre_o_quadro() -> None:
    # Dalgalarrondo p. 224 e 302: "Tabela 19.1" e "Tabela 25.1" em 12 pt são quadros como os outros
    # (P2 da pós-auditoria: sem a "Tabela", 2.430 posições do livro mudavam).
    pagina_2 = _linhas(10.0, 0.1, CONTINUACAO)
    livro = _montar([*_interrompido(), *_quadro(0.4, "Tabela 19.1")], pagina_2)
    assert _resumo(livro) == [
        ("paragrafo", f"{INTERROMPIDO} {CONTINUACAO}"),
        ("titulo", "Tabela 19.1"),
        ("paragrafo", LEGENDA),
        ("paragrafo", EIXO_1),
        ("paragrafo", EIXO_2),
    ]


def test_linha_de_11_pt_dentro_do_quadro_segue_no_quadro() -> None:
    # Medido: dentro dos quadros do Dalgalarrondo há linhas de 8, 9 e 11 pt, nunca de 10. A de
    # 11 pt fica entre o corpo e o título, e não fecha o quadro.
    quadro = [*_quadro(0.4), *_linhas(11.0, 0.56, "Total")]
    livro = _montar([*_interrompido(), *quadro], _linhas(10.0, 0.1, CONTINUACAO))
    assert _textos(livro) == [
        f"{INTERROMPIDO} {CONTINUACAO}",
        ROTULO,
        LEGENDA,
        EIXO_1,
        EIXO_2,
        "Total",
    ]


def test_letra_do_corpo_fecha_o_quadro_e_a_letra_menor_depois_volta_a_ser_nota() -> None:
    depois = [
        *_linhas(10.0, 0.6, "Um parágrafo de corpo depois do quadro."),
        *_linhas(8.0, 0.65, "Uma nota de rodapé."),
    ]
    livro = _montar([*_quadro(0.4), *depois])
    assert _resumo(livro)[-2:] == [
        ("paragrafo", "Um parágrafo de corpo depois do quadro."),
        ("nota", "Uma nota de rodapé."),
    ]


def test_corpo_colado_na_ultima_linha_do_quadro_abre_bloco_proprio() -> None:
    # Dalgalarrondo p. 29: a última linha do quadro ("Cultura") não fecha a frase, e o texto do
    # corpo vem logo abaixo, sem vão de parágrafo. Sem a quebra na fronteira, ele colava no quadro:
    # "…Cultura Assim, desde Aristóteles…" (mutante da code-audit, 5 blocos do livro).
    quadro = [*_quadro(0.4), *_linhas(8.0, 0.55, "Cultura")]
    depois = _linhas(10.0, 0.565, "Assim, desde Aristóteles, o problema ficou.")
    livro = _montar([*_linhas(10.0, 0.3, "Um parágrafo que fecha a frase."), *quadro, *depois])
    assert _textos(livro)[-2:] == ["Cultura", "Assim, desde Aristóteles, o problema ficou."]


def test_codigo_dentro_do_quadro_nao_retoma_o_texto_interrompido() -> None:
    # A retomada é do texto do corpo, e a linha do quadro em minúscula depois de um código dentro
    # dele não a faz: ela iria colar no parágrafo de antes do quadro (A2 da code-audit).
    codigo = Linha("x = 1", x=66.0, fim=446.0, topo=0.56, tamanho=8.0, monoespacada=True)
    quadro = [*_quadro(0.4), codigo, *_linhas(8.0, 0.59, "seguido do texto do quadro.")]
    livro = _montar([*_interrompido(), *quadro], _linhas(10.0, 0.1, CONTINUACAO))
    assert _resumo(livro) == [
        ("paragrafo", f"{INTERROMPIDO} {CONTINUACAO}"),
        ("titulo", ROTULO),
        ("paragrafo", LEGENDA),
        ("paragrafo", EIXO_1),
        ("paragrafo", EIXO_2),
        ("codigo", "x = 1"),
        ("paragrafo", "seguido do texto do quadro."),
    ]


def test_linha_em_maiuscula_depois_do_quadro_nao_retoma_o_texto_interrompido() -> None:
    # A retomada é da continuação da frase, que começa em minúscula. A linha em maiúscula abre
    # parágrafo novo, e o quadro entra antes dela (P3 da pós-auditoria).
    pagina_2 = _linhas(10.0, 0.1, "Identificar o objeto é o passo seguinte.")
    livro = _montar([*_interrompido(), *_quadro(0.4)], pagina_2)
    assert _textos(livro) == [
        INTERROMPIDO,
        ROTULO,
        LEGENDA,
        EIXO_1,
        EIXO_2,
        "Identificar o objeto é o passo seguinte.",
    ]


def test_titulo_que_comeca_com_quadro_sem_numero_nao_abre_quadro() -> None:
    # O rótulo leva o número: "Quadro clínico" em letra de título é título, e a letra menor depois
    # dele continua nota (P4 da pós-auditoria).
    linhas = [*_linhas(12.0, 0.3, "Quadro clínico"), *_linhas(8.0, 0.35, "Uma nota de rodapé.")]
    assert _resumo(_montar(linhas)) == [
        ("titulo", "Quadro clínico"),
        ("nota", "Uma nota de rodapé."),
    ]


def test_titulo_que_nao_e_rotulo_fecha_o_quadro() -> None:
    depois = [*_linhas(12.0, 0.6, "Questões de revisão"), *_linhas(8.0, 0.65, "Uma nota.")]
    livro = _montar([*_quadro(0.4), *depois])
    assert _resumo(livro)[-1] == ("nota", "Uma nota.")


def test_mencao_ao_quadro_na_letra_do_corpo_nao_abre_quadro() -> None:
    # Dalgalarrondo p. 223: "Tabela 19.1, são apresentados…" começa uma linha do corpo.
    linhas = [
        *_linhas(10.0, 0.3, "Tabela 19.1, são apresentados os dados."),
        *_linhas(8.0, 0.35, "Uma nota de rodapé."),
    ]
    assert _resumo(_montar(linhas))[-1] == ("nota", "Uma nota de rodapé.")


ENTRELINHA_DO_PDF = 13.5  # pontos: 0,017 de uma página de 792 pt, como no Dalgalarrondo


def _no_pdf(
    tamanho: float, y: float, *textos: str, passo: float = ENTRELINHA_DO_PDF
) -> list[LinhaDeTeste]:
    return [
        LinhaDeTeste(texto, 66, y - n * passo, tamanho=tamanho) for n, texto in enumerate(textos)
    ]


def test_quadro_do_pdf_fica_no_lugar_e_a_frase_volta_inteira(tmp_path: Path) -> None:
    # De ponta a ponta, as p. 43 e 44 do Dalgalarrondo: nenhum pedaço do quadro é nota, e a
    # frase que ele interrompe volta inteira, antes dele.
    corpo = _no_pdf(10, 700, "Um parágrafo de corpo que", *["segue em linhas"] * 6, "e acaba.")
    interrompido = _no_pdf(
        10, 560, "O texto do capítulo começa aqui e", "segue até o pé da página, capaz de"
    )
    quadro = [
        *_no_pdf(12, 480, ROTULO),
        *_no_pdf(9, 456, LEGENDA),
        *_no_pdf(
            8,
            425,
            "Eixo 1. Diagnóstico do transtorno mental",
            "Esquizofrenia e depressão grave.",
            passo=10.5,
        ),
        *_no_pdf(8, 390, EIXO_2),
    ]
    pagina_2 = [*_no_pdf(10, 700, CONTINUACAO), *_no_pdf(10, 660, OUTRO)]
    pdf = montar_pdf(tmp_path / "livro.pdf", [[*corpo, *interrompido, *quadro], pagina_2])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub", idioma="pt-BR")
    limpeza = preparar(importacao.epub, tmp_path / "trabalho").limpeza
    segmentos = limpeza.capitulos[0].segmentos
    assert [(s.papel.value, s.texto) for s in segmentos][1:] == [
        ("paragrafo", f"{INTERROMPIDO} {CONTINUACAO}"),
        ("titulo", ROTULO),
        ("paragrafo", LEGENDA),
        ("paragrafo", EIXO_1),
        ("paragrafo", EIXO_2),
        ("paragrafo", OUTRO),
    ]
