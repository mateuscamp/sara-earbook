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
