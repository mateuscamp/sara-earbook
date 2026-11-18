# SPDX-License-Identifier: GPL-3.0-or-later
"""O subtítulo em versalete que abre o parágrafo na mesma linha é título, e o resto da linha é o
começo do parágrafo (ADR-0004, "Subtítulo em versalete no começo do parágrafo").

No Miller, o subtítulo corrido vem em StoneSerif-Semibold-SC700, com a caixa trocada, e a frase
começa na mesma linha, em StoneSerif: "uso clínico dE sugammadEx En paciEntEs sanos. La primera"
(p. 1185). Pela letra da maioria, a linha virava nota e ia para "Notas", com o começo da frase.
"""

from __future__ import annotations

from pathlib import Path

from earbook.adaptadores.pdf import ler_paginas
from earbook.dominio.blocos import montar_blocos
from earbook.dominio.hifen_da_quebra import mostrar_hifen_invisivel
from earbook.dominio.nome_da_fonte import fim_da_abertura_em_versalete, toda_em_versalete
from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.subtitulo_em_versalete import pecas_da_linha
from tests.linhas_de_teste import (
    ENTRELINHA,
    FIM_DA_LINHA,
    RECUO,
    linha,
    montar,
    resumo,
    texto_corrido,
)
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf_com_nome_de_fonte

VERSALETE = 7.4
"""A letra pequena do versalete, abaixo de 0,85 do corpo de 10,5: sozinha, a linha é nota."""


SEMIBOLD = "StoneSerif-Semibold-SC700"
BOLD = "StoneSerif-Bold-SC700"


def _versalete_e_corpo(
    abertura: str,
    resto: str,
    topo: float,
    tamanho: float = VERSALETE,
    *,
    fonte: str = SEMIBOLD,
) -> Linha:
    """A linha como o adaptador a dá: inteira, com a letra da maioria, e partida em duas."""
    x = RECUO
    fim_da_abertura = x + len(abertura) * 4.5
    em_versalete = Linha(
        abertura, x=x, fim=fim_da_abertura, topo=topo, tamanho=VERSALETE, versalete=True,
        fonte_do_versalete=fonte,
    )  # fmt: skip
    no_corpo = linha(resto, topo, fim_da_abertura + 3)
    return Linha(
        f"{abertura} {resto}",
        x=x,
        fim=FIM_DA_LINHA,
        topo=topo,
        tamanho=tamanho,
        partes=(em_versalete, no_corpo),
    )


def test_subtitulo_em_versalete_com_o_comeco_da_frase_vira_titulo_e_paragrafo() -> None:
    # Miller p. 1185 (c041-s0122 e s0123): a frase "La primera…" perdia o começo.
    pagina = [
        *texto_corrido(0.1),
        _versalete_e_corpo("uso clínico dE sugammadEx En paciEntEs sanos.", "La primera", 0.3),
        linha("evaluación se hizo en voluntarios sanos.", 0.3 + ENTRELINHA),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("titulo", "uso clínico dE sugammadEx En paciEntEs sanos."),
        ("paragrafo", "La primera evaluación se hizo en voluntarios sanos."),
    ]


def test_subtitulo_curto_na_linha_de_paragrafo_tambem_vira_titulo() -> None:
    # Miller p. 1183: "bronCoConstriCCión." é curto, e a linha tem a letra do corpo na maioria.
    pagina = [
        *texto_corrido(0.1),
        _versalete_e_corpo("bronCoConstriCCión.", "Tras la neostigmina puede", 0.3, 10.5),
        linha("aparecer broncoespasmo en el quirófano.", 0.3 + ENTRELINHA),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("titulo", "bronCoConstriCCión."),
        ("paragrafo", "Tras la neostigmina puede aparecer broncoespasmo en el quirófano."),
    ]


def test_subtitulo_que_comeca_na_linha_de_cima_continua_o_titulo() -> None:
    # Miller (c008-s0267): "…anES-" fecha a linha toda em versalete; "tESiología…" abre a seguinte.
    de_cima = Linha(
        "SociEdad EuropEa dE anES-", x=RECUO, fim=200, topo=0.3, tamanho=VERSALETE, versalete=True,
        fonte_do_versalete=SEMIBOLD,
    )  # fmt: skip
    pagina = [
        *texto_corrido(0.1),
        de_cima,
        _versalete_e_corpo("tESiología.", "En 2005 la sociedad", 0.3 + ENTRELINHA),
        linha("nació de dos sociedades.", 0.3 + ENTRELINHA * 2),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("titulo", "SociEdad EuropEa dE anEStESiología."),
        ("paragrafo", "En 2005 la sociedad nació de dos sociedades."),
    ]


def test_subtitulo_corrido_em_outra_fonte_de_versalete_nao_continua_o_titulo_de_cima() -> None:
    # Miller p. 1187 (c041-s0125): o título da seção vem em StoneSerif-Bold-SC700, e o subtítulo
    # corrido logo abaixo, em StoneSerif-Semibold-SC700; os dois saíam num título só.
    secao = Linha(
        "uso clínico dE sugammadEx En adultos mayorEs", x=RECUO, fim=300, topo=0.3,
        tamanho=VERSALETE, versalete=True, fonte_do_versalete=BOLD,
    )  # fmt: skip
    pagina = [
        *texto_corrido(0.1),
        secao,
        _versalete_e_corpo("pediatría.", "El uso de sugammadex", 0.3 + ENTRELINHA),
        linha("se examinó en un estudio.", 0.3 + ENTRELINHA * 2),
    ]
    assert resumo(montar(pagina))[-3:] == [
        ("titulo", "uso clínico dE sugammadEx En adultos mayorEs"),
        ("titulo", "pediatría."),
        ("paragrafo", "El uso de sugammadex se examinó en un estudio."),
    ]


def test_abertura_em_versalete_sem_ponto_continua_a_frase() -> None:
    # Maudlin p. 18: "Physics has TradiTionally been" abre o capítulo em versalete; não é título.
    pagina = [
        *texto_corrido(0.1),
        _versalete_e_corpo("Physics has TradiTionally", "been concerned", 0.3, 10.5),
        linha("with the motion of bodies.", 0.3 + ENTRELINHA),
    ]
    assert resumo(montar(pagina))[-1] == (
        "paragrafo",
        "Physics has TradiTionally been concerned with the motion of bodies.",
    )


def test_partes_que_nao_comecam_o_texto_da_linha_nao_partem_a_linha() -> None:
    # A linha visual juntada com o pedaço da esquerda antes leva as partes só do outro pedaço.
    partida = _versalete_e_corpo("dosis.", "La dosis", 0.3, 10.5)
    juntada = Linha(
        "La dosis habitual dosis. La dosis", x=RECUO, fim=FIM_DA_LINHA, topo=0.3, tamanho=10.5,
        partes=partida.partes,
    )  # fmt: skip
    pagina = [*texto_corrido(0.1), juntada]
    assert resumo(montar(pagina))[-1] == ("paragrafo", "La dosis habitual dosis. La dosis")


def test_linha_visual_com_outro_pedaco_depois_das_partes_tambem_se_parte() -> None:
    # Miller p. 2062: "fisiología Del fosfaTo. El PO4" e a carga sobrescrita, na mesma altura,
    # viram uma linha visual; o pedaço de depois vai com o resto (c065-s0129).
    partida = _versalete_e_corpo("fisiología Del fosfaTo.", "El PO4", 0.3)
    juntada = Linha(
        "fisiología Del fosfaTo. El PO4 3\u2013", x=RECUO, fim=FIM_DA_LINHA, topo=0.3,
        tamanho=VERSALETE, partes=partida.partes,
    )  # fmt: skip
    pagina = [
        *texto_corrido(0.1),
        juntada,
        linha("es el anión intracelular más abundante.", 0.3 + ENTRELINHA),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("titulo", "fisiología Del fosfaTo."),
        ("paragrafo", "El PO4 3\u2013 es el anión intracelular más abundante."),
    ]


def _ler(tmp_path: Path, linhas: list[LinhaDeTeste]) -> list[Linha]:
    """As linhas do PDF em que a Helvetica vira fonte de versalete; a Times é o corpo."""
    nome = f"/ULYLLH+{SEMIBOLD}".encode()
    pdf = montar_pdf_com_nome_de_fonte(tmp_path / "versalete.pdf", nome, linhas)
    return [lida for pagina in ler_paginas(pdf) for lida in pagina.linhas]


def test_adaptador_parte_a_linha_onde_acaba_a_fonte_de_versalete(tmp_path: Path) -> None:
    # A fonte trocada tem 600 de largura em toda letra: 26 letras de 7 pt medem 109,2 pt.
    linhas = _ler(
        tmp_path,
        [
            LinhaDeTeste("uso clinico de sugammadex.", 72, 700, tamanho=7),
            LinhaDeTeste(" La primera", 181.2, 700, serifa=True),
        ],
    )
    assert [
        (p.texto, p.versalete, round(p.x, 1), p.fonte_do_versalete) for p in linhas[0].partes
    ] == [
        ("uso clinico de sugammadex.", True, 72.0, "StoneSerif-Semibold-SC700"),
        ("La primera", False, 183.8, ""),
    ]


def test_linha_toda_em_versalete_e_a_que_abre_no_corpo_nao_se_partem(tmp_path: Path) -> None:
    linhas = _ler(
        tmp_path,
        [
            LinhaDeTeste("uso clinico de sugammadex", 72, 700, tamanho=7),
            LinhaDeTeste("La primera ", 72, 650, serifa=True),
            LinhaDeTeste("evaluacion", 122.8, 650, tamanho=7),
        ],
    )
    assert [lida.partes for lida in linhas] == [(), ()]


def test_do_pdf_o_subtitulo_em_versalete_sai_titulo_antes_do_paragrafo(tmp_path: Path) -> None:
    corpo = [
        LinhaDeTeste("Texto corrido para firmar a medida do corpo do livro.", 72, 740, serifa=True)
    ]
    linhas = _ler(
        tmp_path,
        [
            *corpo,
            LinhaDeTeste("uso clinico de sugammadex en sanos.", 72, 700, tamanho=7),
            LinhaDeTeste(" La primera", 219, 700, serifa=True),
            LinhaDeTeste("evaluacion se hizo en voluntarios.", 72, 688, serifa=True),
        ],
    )
    blocos = montar_blocos([Pagina(1, tuple(linhas))]).blocos
    assert [(b.tipo.value, b.texto) for b in blocos][-2:] == [
        ("titulo", "uso clinico de sugammadex en sanos."),
        ("paragrafo", "La primera evaluacion se hizo en voluntarios."),
    ]


def test_hifen_invisivel_da_linha_tambem_vira_hifen_nas_partes() -> None:
    # Miller: o U+00AD no meio da linha vira "-" na linha inteira (`mostrar_hifen_invisivel`); nas
    # partes ele ficava, e a linha não se partia.
    partida = _versalete_e_corpo("uso clínico.", "La pós­anestesia de", 0.3)
    paginas = [Pagina(1, (*texto_corrido(0.1), partida)) for _ in range(3)]
    linha_final = mostrar_hifen_invisivel(paginas)[0].linhas[-1]
    assert [parte.texto for parte in pecas_da_linha(linha_final)] == [
        "uso clínico.",
        "La pós-anestesia de",
    ]


def test_letra_de_fonte_de_simbolo_no_meio_do_versalete_nao_acaba_a_abertura() -> None:
    # Miller p. 3341 e c022-s0110: "ReceptoRes β-adRenéRgicos. Como el receptor", com o "β" na
    # MathematicalPi-One, que não é fonte de versalete.
    letras = [
        *[(letra, "X+StoneSerif-Bold-SC700") for letra in "ReceptoRes "],
        ("b", "X+MathematicalPi-One"),
        *[(letra, "X+StoneSerif-Bold-SC700") for letra in "-adRenéRgicos."],
        (" ", None),
        ("C", "X+StoneSerif"),
    ]
    assert fim_da_abertura_em_versalete(letras) == len(letras) - 2
    assert toda_em_versalete(nome for _, nome in letras[:-2])


def test_linha_so_de_fonte_de_simbolo_nao_e_versalete() -> None:
    assert not toda_em_versalete(["X+MathematicalPi-One", "X+MathematicalPi-One"])


def test_linha_em_maiusculas_sem_fonte_de_versalete_continua_o_titulo_em_versalete() -> None:
    # A segunda linha do título em versalete continua o título pela regra de antes (ADR-0004, "O
    # que ficou da Fase 1"): só a outra fonte de versalete o fecha.
    titulo = Linha(
        "DELÍRIO DE GRANDEZA", x=RECUO, fim=200, topo=0.3, tamanho=VERSALETE, versalete=True,
        fonte_do_versalete=BOLD,
    )  # fmt: skip
    segunda = Linha("(DE ENORMIDADE)", x=RECUO, fim=200, topo=0.3 + ENTRELINHA, tamanho=VERSALETE)
    pagina = [*texto_corrido(0.1), titulo, segunda, *texto_corrido(0.4)]
    assert resumo(montar(pagina))[1] == ("titulo", "DELÍRIO DE GRANDEZA (DE ENORMIDADE)")


def test_a_abertura_acaba_na_ultima_letra_do_versalete_sem_o_espaco_do_corpo() -> None:
    # Miller p. 1730: em "do." e o espaço na letra do corpo, o espaço dava 9 pt à abertura, e o
    # título "…no proCesa-" (6,3 pt) da linha de cima não continuava (c055-s0059 e s0060).
    letras = [
        ("d", "X+StoneSerif-Bold-SC700"),
        ("o", "X+StoneSerif-Bold-SC700"),
        (".", "X+StoneSerif-Bold-SC700"),
        (" ", "X+StoneSerif"),
        ("E", "X+StoneSerif"),
    ]
    assert fim_da_abertura_em_versalete(letras) == 3


def test_linha_que_abre_na_letra_grega_e_segue_no_corpo_nao_tem_abertura() -> None:
    # Miller p. 1279: "β-bloqueante", com o "β" na MathPiOneBold e o resto no corpo.
    letras = [("b", "X+MathPiOneBold"), ("-", "X+StoneSans"), ("b", "X+StoneSans")]
    assert fim_da_abertura_em_versalete(letras) is None
