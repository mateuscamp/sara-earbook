# SPDX-License-Identifier: GPL-3.0-or-later
"""A chamada de referência que a regra do sobrescrito não pegava (ADR-0004, "Camada do OCR sobre
as figuras e chamada colada").

No Miller, 1.056 chamadas escapavam: depois de "»", de letra solta ("6 h"), de número ("0,62"),
no começo da linha, depois de espaço ou de travessão, e a faixa com o hífen invisível. A voz lia
o número colado à palavra.
"""

from __future__ import annotations

from pathlib import Path

from earbook.adaptadores.pdf import ler_paginas
from earbook.dominio.caracteres import (
    CHAMADAS_CERTAS_NA_PAGINA,
    Caractere,
    pagina_usa_chamadas,
    texto_da_linha,
)
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf

CORPO = 10.0
BASE = 300.0
LARGURA = 5.0


def _linha(texto: str) -> list[Caractere]:
    """ "^" abre e fecha o sobrescrito e "_" é o espaço que o pdfminer inventa, sem caractere."""
    caracteres: list[Caractere] = []
    x, sobe = 0.0, False
    for letra in texto:
        if letra == "^":
            sobe = not sobe
        elif letra == "_":
            caracteres.append(Caractere(" ", x, x + 2.5, 0.0, 0.0, virtual=True))
            x += 2.5
        else:
            tamanho, base = (5.8, BASE + 3.3) if sobe else (CORPO, BASE)
            caracteres.append(Caractere(letra, x, x + LARGURA, tamanho, base))
            x += LARGURA
    return caracteres


def _texto(texto: str) -> str:
    """Só com o que a linha sabe: a chamada certa sai, a duvidosa fica."""
    return texto_da_linha(_linha(texto), CORPO).texto


def _texto_na_pagina_com_chamadas(texto: str) -> str:
    return texto_da_linha(_linha(texto), CORPO, com_duvidosas=True).texto


def test_chamada_depois_da_aspa_do_espanhol_sai() -> None:
    assert _texto("«el paciente»^52^. El resto") == "«el paciente». El resto"


def test_chamada_depois_de_exclamacao_e_de_interrogacao_sai() -> None:
    assert _texto("con todo!^111^. O con EAPC?^170^ Además") == "con todo!. O con EAPC? Además"


def test_faixa_com_o_hifen_invisivel_sai() -> None:
    # O Miller grava o hífen como U+00AD: "19\xad21".
    assert _texto("vulnerable^19\u00ad21^. Con el anestésico^24,105\u00ad107^.") == (
        "vulnerable. Con el anestésico."
    )


def test_numero_de_referencia_com_letra_sai() -> None:
    assert _texto("refractaria^138a^. Y las directrices^116a,166b^.") == (
        "refractaria. Y las directrices."
    )


def test_chamada_que_abre_a_linha_antes_de_pontuacao_e_duvidosa() -> None:
    # A palavra ficou na linha de cima: "…anestesia" | "¹¹⁸. No hay…". Na linha, tem a cara do
    # número de uma nota ("¹. Ver o capítulo 3"): só a página decide.
    assert _texto("^118^. No hay datos") == "118. No hay datos"
    assert _texto_na_pagina_com_chamadas("^118^. No hay datos") == ". No hay datos"
    assert _texto_na_pagina_com_chamadas("^137,138^; los otros") == "; los otros"


def test_isotopo_que_abre_a_linha_fica() -> None:
    assert _texto("^125^I-yodo y ^133^Xe") == "125I-yodo y 133Xe"


def _fim_da_linha(caracteres: list[Caractere]) -> list[Caractere]:
    """A linha como o pdfminer a entrega: com a quebra no fim, sem posição."""
    x = caracteres[-1].x1
    return [*caracteres, Caractere("\n", x, x, 0.0, 0.0, virtual=True)]


def test_chamada_depois_de_espaco_antes_de_pontuacao_ou_do_fim_sai() -> None:
    assert _texto("alivia el dolor ^280^.") == "alivia el dolor ."
    assert _texto("como se dijo antes ^41,122^") == "como se dijo antes "
    linha = _fim_da_linha(_linha("como se dijo antes ^41,122^"))
    assert texto_da_linha(linha, CORPO).texto == "como se dijo antes \n"


def test_isotopo_depois_de_espaco_fica() -> None:
    assert _texto("lavado del gas ^133^Xe en reposo") == "lavado del gas 133Xe en reposo"


def test_chamada_depois_de_travessao_sai() -> None:
    assert _texto("la respuesta\u2013^11^. Como la fiebre\u2014^229^") == (
        "la respuesta\u2013. Como la fiebre\u2014"
    )


def test_expoente_depois_de_travessao_no_meio_da_formula_fica() -> None:
    assert _texto("Na+\u2013Cl\u2013^2^/4") == "Na+\u2013Cl\u20132/4"


def test_lista_e_faixa_depois_de_letra_solta_e_de_numero_saem() -> None:
    assert _texto("con el N2O^198,199^. Dura 23,5 h^29-34^. En 1:73.000^3,4^.") == (
        "con el N2O. Dura 23,5 h. En 1:73.000."
    )


def test_lista_de_numeros_com_letra_depois_de_letra_solta_sai() -> None:
    assert _texto("más de 6 h^116a,166b^. La otra") == "más de 6 h. La otra"


def test_numero_so_depois_de_letra_solta_e_duvidoso() -> None:
    # "6 h¹⁴⁸" e "r¹²" têm a mesma cara na linha: só a página decide.
    linha = texto_da_linha(_linha("más de 6 h^148^. La cinasa C^19^. Se"), CORPO)
    assert (linha.texto, linha.chamadas, linha.duvidosas) == (
        "más de 6 h148. La cinasa C19. Se",
        (),
        2,
    )


def test_numero_so_depois_de_algarismo_e_duvidoso() -> None:
    linha = texto_da_linha(_linha("FiO2 de 0,62^111^. Con RyR1^48^."), CORPO)
    assert (linha.texto, linha.duvidosas) == ("FiO2 de 0,62111. Con RyR148.", 2)


def test_na_pagina_com_chamadas_a_duvidosa_sai_registrada() -> None:
    linha = texto_da_linha(_linha("más de 6 h^148^. FiO2 de 0,62^111^."), CORPO, com_duvidosas=True)
    assert (linha.texto, linha.chamadas, linha.duvidosas) == (
        "más de 6 h. FiO2 de 0,62.",
        ("h[148]", "0,62[111]"),
        0,
    )


def test_chamada_depois_do_sinal_de_grau_e_duvidosa() -> None:
    assert _texto("girado 90°^91^; pronto") == "girado 90°91; pronto"
    assert _texto_na_pagina_com_chamadas("girado 90°^91^; pronto") == "girado 90°; pronto"


def test_expoente_da_base_dez_fica_mesmo_na_pagina_com_chamadas() -> None:
    assert _texto_na_pagina_com_chamadas("son 2 \u00d7 10^12^ células y 10^23^ iones") == (
        "son 2 \u00d7 1012 células y 1023 iones"
    )


def test_um_algarismo_so_depois_de_letra_solta_ou_de_numero_fica_sempre() -> None:
    assert _texto_na_pagina_com_chamadas("de 35 kg/m^2^ o más, en T10^2^. Y r^2^.") == (
        "de 35 kg/m2 o más, en T102. Y r2."
    )


def test_expoente_no_meio_da_formula_fica_mesmo_na_pagina_com_chamadas() -> None:
    # A configuração eletrônica do Miller: o falso positivo que a amostra achou.
    assert _texto_na_pagina_com_chamadas("[Kr]5s^2^4d^10^5p^6^)") == "[Kr]5s24d105p6)"


def test_pagina_prova_as_duvidosas_com_tres_chamadas_certas() -> None:
    assert CHAMADAS_CERTAS_NA_PAGINA == 3
    assert [pagina_usa_chamadas(certas) for certas in (0, 2, 3, 40)] == [False, False, True, True]


def _pagina(certas: int) -> list[LinhaDeTeste]:
    frases = [
        LinhaDeTeste(f"La frase número {k} del libro termina aquí.^{k + 10}^ Y sigue.", 72, y)
        for k, y in zip(range(certas), range(700, 100, -14), strict=False)
    ]
    duvidosa = LinhaDeTeste("La vida media es de 6 h^148^. Y nada más.", 72, 100)
    return [
        LinhaDeTeste(linha.texto, linha.x, linha.y, sobrescrito=True)
        for linha in (*frases, duvidosa)
    ]


def test_adaptador_tira_a_duvidosa_so_na_pagina_com_tres_chamadas_certas(tmp_path: Path) -> None:
    paginas = ler_paginas(montar_pdf(tmp_path / "livro.pdf", [_pagina(3), _pagina(2)]))
    assert [pagina.linhas[-1].texto for pagina in paginas] == [
        "La vida media es de 6 h. Y nada más.",
        "La vida media es de 6 h148. Y nada más.",
    ]
    assert [pagina.linhas[-1].chamadas for pagina in paginas] == [("h[148]",), ()]
