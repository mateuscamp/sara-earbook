# SPDX-License-Identifier: GPL-3.0-or-later
"""O quadro do tratado em inglês fica no lugar, depois da frase que ele interrompe (ADR-0004,
"Quadro no lugar" e "Quadro em inglês").

No Practical, o "• BOX 10.1 Overview of Neuroimaging Modalities" (MyriadPro negrito de 10 pt, com
o corpo em AGaramondPro de 10) abre a página, entre "…confirmed that damage" e "to S1/S2
produces…", e o conteúdo vem em HelveticaNeueLTStd de 8,5 e de 9,5 pt. A linha de 9,5 pt passava
por corpo, pelo tamanho só, e soltava o quadro no meio da frase.
"""

from __future__ import annotations

from earbook.dominio.blocos import montar_blocos
from earbook.dominio.pagina import Linha, Pagina

CORPO = "AGaramondPro"
QUADRO = "HelveticaNeueLTStd"
ENTRELINHA = 0.014


def _linhas(topo: float, *textos: str, fonte: str = CORPO, tamanho: float = 10.0) -> list[Linha]:
    return [
        Linha(texto, x=42.0, fim=296.0, topo=topo + n * ENTRELINHA, tamanho=tamanho, fonte=fonte)
        for n, texto in enumerate(textos)
    ]


def _textos(*paginas: list[Linha]) -> list[str]:
    livro = montar_blocos([Pagina(n, tuple(linhas)) for n, linhas in enumerate(paginas, 1)])
    return [bloco.texto for bloco in livro.blocos]


def test_quadro_em_ingles_entra_depois_da_frase_que_ele_interrompe() -> None:
    # A linha do corpo tem a medida da do Practical (~60 caracteres): com linhas curtas, o rótulo
    # do quadro em negrito passaria por prosa em negrito (ADR-0004, "Prosa em negrito do tamanho
    # do corpo").
    meio = ["segue com as medidas do livro inteiro, longa como uma linha dele"] * 8
    corpo = _linhas(0.1, "Um parágrafo de corpo que", *meio, "acaba aqui.")
    interrompido = _linhas(0.4, "Discussions in the field revolved around", "lesions that damage")
    rotulo = Linha(
        "• BOX 10.1 Overview of Neuroimaging Modalities",
        x=42.0,
        fim=276.0,
        topo=0.074,
        tamanho=10.0,
        negrito=True,
        fonte="MyriadPro",
    )
    conteudo = [
        *_linhas(0.1, "Neuroimaging techniques are defined", fonte=QUADRO, tamanho=8.5),
        *_linhas(0.13, "Advanced MRI Techniques Functional MRI", fonte=QUADRO, tamanho=9.5),
        *_linhas(0.16, "fMRI: fMRI involves the acquisition.", fonte=QUADRO, tamanho=8.5),
    ]
    continuacao = _linhas(0.3, "to S1/S2 produces impairments in perceiving.")
    textos = _textos([*corpo, *interrompido], [rotulo, *conteudo, *continuacao])
    assert textos[1:] == [
        (
            "Discussions in the field revolved around lesions that damage to S1/S2 produces "
            "impairments in perceiving."
        ),
        "• BOX 10.1 Overview of Neuroimaging Modalities",
        "Neuroimaging techniques are defined",
        "Advanced MRI Techniques Functional MRI",
        "fMRI: fMRI involves the acquisition.",
    ]
