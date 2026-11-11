# SPDX-License-Identifier: GPL-3.0-or-later
"""Os caracteres da linha do PDF antes de virarem texto (ADR-0004, "Número de referência e
espaço falso").

No Practical, a chamada de referência vem sobrescrita, a 0,58 do corpo e com a linha de base
0,33 do corpo acima ("wages.¹", "84%-90%.²,³", "et al.¹⁹⁴"), e a voz lia "wages ponto um". O nome
do autor vem em Gotham-Bold com 1 pt a mais entre as letras, e o pdfminer punha espaço onde o vão
é só o da letra espaçada ("NATALI E MORY L").
"""

from __future__ import annotations

from earbook.dominio.caracteres import Caractere, texto_da_linha, texto_lido

CORPO = 10.0
BASE = 300.0
LARGURA = 5.0


def _linha(texto: str, *, vao: float = 0.0) -> list[Caractere]:
    """ "^" abre e fecha o sobrescrito, "~" o subscrito e "_" é o espaço que o pdfminer inventa."""
    caracteres: list[Caractere] = []
    x, deslocamento = 0.0, 0.0
    for letra in texto:
        if letra in "^~":
            alvo = 3.3 if letra == "^" else -3.3
            deslocamento = 0.0 if deslocamento else alvo
            continue
        if letra == "_":
            caracteres.append(Caractere(" ", x, x + vao, 0.0, 0.0, virtual=True))
            continue
        tamanho = 5.8 if deslocamento else CORPO
        caracteres.append(Caractere(letra, x, x + LARGURA, tamanho, BASE + deslocamento))
        x += LARGURA + vao
    return caracteres


def _texto(texto: str, *, vao: float = 0.0) -> str:
    return texto_da_linha(_linha(texto, vao=vao), CORPO).texto


def test_numero_sobrescrito_depois_do_ponto_sai() -> None:
    assert _texto("of the wages.^1^ (to") == "of the wages. (to"


def test_numero_sobrescrito_colado_na_palavra_sai() -> None:
    assert _texto("Dr. John Bonica^7^") == "Dr. John Bonica"


def test_lista_e_faixa_sobrescritas_saem() -> None:
    assert _texto("84%\u201390%.^2,3^ and syndromes.^12\u201315^ or et al.^194^ 2010") == (
        "84%\u201390%. and syndromes. or et al. 2010"
    )


def test_a_chamada_tirada_fica_registrada_com_a_palavra_antes() -> None:
    linha = texto_da_linha(_linha("the wages.^1^ and pain^2,3^"), CORPO)
    assert linha.chamadas == ("wages.[1]", "pain[2,3]")


def test_expoente_depois_de_algarismo_fica() -> None:
    assert _texto("10^6^ cells") == "106 cells"


def test_chamada_colada_ao_ano_sai_e_o_ano_fica() -> None:
    # Practical p. 332: "sciatica in 1934²²¹" virava "1934221"; p. 933: "Lutz, 2017¹⁰¹".
    assert _texto("sciatica in 1934^221^; and Lutz, 2017^101^ One and 2018^81\u201387^ of") == (
        "sciatica in 1934; and Lutz, 2017 One and 2018 of"
    )


def test_expoente_depois_de_numero_que_nao_e_ano_fica() -> None:
    assert _texto("10^6^ and 1000^2^ and 12017^3^ and 3.2017^2^") == (
        "106 and 10002 and 120173 and 3.20172"
    )


def test_carga_do_ion_fica() -> None:
    assert _texto("Ca^2+^ influx") == "Ca2+ influx"


def test_unidade_ao_quadrado_e_letra_solta_ficam() -> None:
    assert _texto("kg/m^2^ and cm^2^ and r^2^") == "kg/m2 and cm2 and r2"


def test_subscrito_fica() -> None:
    assert _texto("CO~2~ levels") == "CO2 levels"


def test_letra_sobrescrita_fica() -> None:
    assert _texto("Aspirin^a^ and") == "Aspirina and"


def test_sobrescrito_no_comeco_da_linha_fica() -> None:
    assert _texto("^1^ The note") == "1 The note"


def test_sobrescrito_depois_de_espaco_fica() -> None:
    assert _texto("dose ^5^ mg") == "dose 5 mg"


def test_espaco_inventado_no_vao_da_letra_espacada_sai() -> None:
    assert _texto("NATALI_E MORY_L, CH_ARLE_S", vao=1.0) == "NATALIE MORYL, CHARLES"


def test_espaco_inventado_no_vao_maior_que_o_da_letra_fica() -> None:
    caracteres = _linha("NATALIE", vao=1.0)
    x = caracteres[-1].x1
    caracteres += [Caractere(" ", x, x + 3.0, 0.0, 0.0, virtual=True)]
    caracteres += [Caractere("M", x + 3.0, x + 8.0, CORPO, BASE)]
    assert texto_da_linha(caracteres, CORPO).texto == "NATALIE M"


def test_espaco_inventado_no_texto_comum_fica() -> None:
    # O texto comum não tem vão entre as letras; o pdfminer só põe espaço no vão da palavra.
    caracteres = _linha("word")
    x = caracteres[-1].x1
    caracteres += [Caractere(" ", x, x + 2.5, 0.0, 0.0, virtual=True)]
    caracteres += [Caractere("s", x + 2.5, x + 7.5, CORPO, BASE)]
    assert texto_da_linha(caracteres, CORPO).texto == "word s"


def test_chamada_com_espaco_dentro_sai_inteira() -> None:
    # R5 da code-review: o espaço da letra pequena partia a chamada, e o "9" ficava.
    assert _texto("techniques.^1,8, 9^ Then") == "techniques. Then"


def test_chamada_com_virgula_sobrescrita_no_fim_sai() -> None:
    # R6 da code-review.
    assert _texto("pain^2,^ and") == "pain and"


def test_nome_com_kerning_em_varios_pares_sai_inteiro() -> None:
    # Practical p. 39, com os vãos medidos: 1 pt entre as letras, 5 pt no espaço, e os pares
    # apertados (0,8, 0,75, 0,45 e 0 no "W."). Os pares formavam "palavras" de 2 e 3 letras, e a
    # regra antiga da letra espaçada partia o nome que o espaço falso já tinha consertado ("KAU R
    # KO ONER").
    vaos = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 5.0, 0.8, 0.75, 1.0, 5.0, 0.45, 1.0, 1.0, 1.0, 1.0]
    vaos += [1.0, 5.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.75, 5.0, 0.0, 5.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    letras = "PREETMAKAURKOONER,GREGORYW.TERMAN"
    caracteres: list[Caractere] = []
    x = 0.0
    for letra, vao in zip(letras, [*vaos, 0.0], strict=True):
        caracteres.append(Caractere(letra, x, x + LARGURA, CORPO, BASE))
        x += LARGURA
        if vao == 5.0:
            caracteres.append(Caractere(" ", x + 1.0, x + 4.0, CORPO, BASE))
        elif vao == 1.0 and letra in "RIAOE":
            caracteres.append(Caractere(" ", x, x + vao, 0.0, 0.0, virtual=True))
        x += vao
    assert texto_lido(caracteres, CORPO) == "PREETMA KAUR KOONER, GREGORY W. TERMAN"


def _medida(pecas: list[tuple[str, float, float]]) -> list[Caractere]:
    """A linha com as posições medidas no PDF; "_" é o espaço que o pdfminer inventa, e " ", o
    espaço de verdade, que é caractere do PDF."""
    return [
        Caractere(" ", x0, x1, 0.0, 0.0, virtual=True)
        if texto == "_"
        else Caractere(texto, x0, x1, 15.0, BASE)
        for texto, x0, x1 in pecas
    ]


def test_par_apertado_na_letra_espacada_com_espaco_de_verdade_sai_junto() -> None:
    # Bonica p. 67, medido: o "PA" vem a 1,1 pt, as outras letras a 1,7 a 2,2 pt, e entre as
    # palavras há um espaço de verdade (8 pt de vão). A regra da letra espaçada tomava o "PA" por
    # palavra e lia "PA R T O N E" (ADR-0004, "Espaço menor que o espaço de verdade").
    pecas = [("P", 72.0, 81.16), ("A", 82.28, 93.11), ("_", 93.11, 95.36)]
    pecas += [("R", 95.36, 106.18), ("_", 106.18, 107.9), ("T", 107.9, 117.9)]
    pecas += [("_", 117.9, 119.87), (" ", 119.87, 123.62), ("_", 123.62, 125.87)]
    pecas += [("O", 125.87, 137.53), ("_", 137.53, 139.77), ("N", 139.77, 150.6)]
    pecas += [("_", 150.6, 152.84), ("E", 152.84, 162.84)]
    assert texto_lido(_medida(pecas), 15.0) == "PART ONE"


def test_numero_do_capitulo_partido_pelo_kerning_sai_inteiro() -> None:
    # Bonica p. 5315: "C H A P T E R   11 0", com o "11" a 1 pt e o "0" a 2,1 pt.
    pecas = [("C", 72.75, 86.75), ("_", 86.75, 88.87), ("H", 88.87, 104.02)]
    pecas += [("_", 104.02, 106.14), ("A", 106.14, 121.3), ("_", 121.3, 123.42)]
    pecas += [("P", 123.42, 135.09), ("_", 135.09, 137.21), ("T", 137.21, 150.03)]
    pecas += [("_", 150.03, 152.14), ("E", 152.14, 164.96), ("_", 164.96, 167.07)]
    pecas += [("R", 167.07, 181.07), ("_", 181.07, 183.19), (" ", 183.19, 188.44)]
    pecas += [("_", 188.44, 190.56), ("1", 190.56, 201.05), ("1", 202.03, 212.52)]
    pecas += [("_", 212.52, 214.64), ("0", 214.64, 225.13)]
    assert texto_lido(_medida(pecas), 21.0) == "CHAPTER 110"


def test_espaco_inventado_do_tamanho_do_espaco_de_verdade_fica() -> None:
    # A palavra separada só pela posição, na linha que também tem espaço de verdade: o vão é o da
    # palavra, e o espaço fica.
    pecas = [("o", 0.0, 5.0), ("f", 5.0, 10.0), (" ", 10.0, 13.0), ("p", 13.0, 18.0)]
    pecas += [("a", 18.0, 23.0), ("i", 23.0, 28.0), ("n", 28.0, 33.0), ("_", 33.0, 35.5)]
    pecas += [("a", 35.5, 40.5), ("n", 40.5, 45.5), ("d", 45.5, 50.5)]
    assert texto_lido(_medida(pecas), 10.0) == "of pain and"


def test_letra_espacada_irregular_com_espaco_de_verdade_ainda_se_junta() -> None:
    # Um vão entre as letras passa da metade do espaço de verdade: a régua do espaço não serve à
    # linha, e a regra da letra espaçada a lê ("PARTE I", e não "PAR TE I").
    pecas = [("P", 0.0, 10.0), ("_", 10.0, 13.0), ("A", 13.0, 23.0), ("_", 23.0, 26.0)]
    pecas += [("R", 26.0, 36.0), ("_", 36.0, 40.5), ("T", 40.5, 50.5), ("_", 50.5, 53.5)]
    pecas += [("E", 53.5, 63.5), ("_", 63.5, 65.5), (" ", 65.5, 69.5), ("_", 69.5, 71.5)]
    pecas += [("I", 71.5, 76.0)]
    assert texto_lido(_medida(pecas), 15.0) == "PARTE I"
