# SPDX-License-Identifier: GPL-3.0-or-later
"""Letra espaçada: a linha "P A R T E   I" volta a ser "PARTE I" (ADR-0004).

Os vãos são os medidos no Competente: entre letras, 1 a 2,2 pt; entre palavras, 3,6 a
6,4 pt; no texto comum, perto de zero dentro da palavra.
"""

from __future__ import annotations

from earbook.dominio.pagina import Letra, juntar_letras_espacadas

LARGURA = 5.0


def _letras(texto: str, vaos: list[float]) -> list[Letra]:
    """Uma `Letra` por caractere de `texto`, com `vaos[i]` antes do caractere i + 1."""
    letras: list[Letra] = []
    x = 100.0
    for i, caractere in enumerate(texto):
        letras.append(Letra(caractere, x, x + LARGURA))
        x += LARGURA + (vaos[i] if i < len(vaos) else 0.0)
    return letras


def test_letras_espacadas_voltam_a_ser_palavras() -> None:
    # Competente p. 20: a escuta no ElevenReader leu "PARTEI", o verbo "partei".
    letras = _letras("PARTEI", [0.99, 1.36, 1.22, 1.36, 4.42])
    assert juntar_letras_espacadas(letras, 8.5) == "PARTE I"


def test_nome_espacado_com_vao_maior_entre_as_palavras() -> None:
    letras = _letras("FABIOAKITA", [1.82, 2.2, 2.2, 2.2, 6.4, 2.2, 2.2, 2.2, 1.8])
    assert juntar_letras_espacadas(letras, 10.0) == "FABIO AKITA"


def test_pontuacao_e_numero_seguem_os_vaos_reais() -> None:
    # O "·" separado por vão de palavra; a vírgula colada; o número de página a 10,5 pt.
    letras = _letras(
        "·OCOISA,BOM15", [5.1, 4.42, 1.08, 1.36, 1.36, 1.36, 1.36, 4.42, 1.05, 1.05, 10.5, 0]
    )
    assert juntar_letras_espacadas(letras, 8.5) == "· O COISA, BOM 15"


def test_texto_comum_nao_e_espacado() -> None:
    # "Como ler este": até 0,3 pt dentro da palavra e 2,45 pt entre as palavras.
    letras = _letras("Comolereste", [0.3, 0.2, 0.11, 2.45, 0.3, 0.2, 2.45, 0.1, 0.3, 0.2])
    assert juntar_letras_espacadas(letras, 10.5) is None


def test_linha_de_pontinhos_do_sumario_nao_e_espacada() -> None:
    # "Prefácio . . . ." tem os pontos espaçados, mas as letras vêm coladas.
    # São uns 40 pontinhos por linha (Competente p. 6): contando todos os vãos, e não só os
    # entre letras, a mediana seria a dos pontinhos.
    letras = _letras("Prefácio" + "." * 30, [0] * 7 + [6.65] + [2.71] * 29)
    assert juntar_letras_espacadas(letras, 10.5) is None


def test_linha_curta_demais_nao_e_espacada() -> None:
    assert juntar_letras_espacadas(_letras("AB", [1.4]), 8.5) is None


def test_linha_mista_recompoe_so_o_trecho_espacado() -> None:
    # Revisão: a decisão era da linha inteira, e o limite tirado do trecho espaçado
    # (2 x 1,4 pt) colava as palavras comuns, separadas por 2,45 pt: "Capítulo3".
    vaos = [0, 0, 0, 0, 0, 0, 0, 2.45, 4.42, *[1.4] * 7]
    letras = _letras("Capítulo3ESPECIAL", vaos)
    assert juntar_letras_espacadas(letras, 8.5) == "Capítulo 3 ESPECIAL"


def test_formula_com_espaco_comum_nao_e_espacada() -> None:
    # Hard Parts p. 87: "D = A + I - 1" (com sinal de menos) é feito de caracteres soltos,
    # mas entre duas letras há sempre um operador; letra espaçada tem letras vizinhas.
    letras = _letras("D=A+I\u22121", [2.45] * 6)
    assert juntar_letras_espacadas(letras, 10.5) is None


def test_letras_soltas_sem_vizinhas_ficam_como_estao_na_linha_mista() -> None:
    letras = _letras("D=AemPARTE", [2.45, 2.45, 2.45, 0, 4.42, 1.4, 1.4, 1.4, 1.4])
    assert juntar_letras_espacadas(letras, 8.5) == "D = A em PARTE"


def test_caracteres_soltos_na_prosa_ficam_como_estao() -> None:
    # F1 da auditoria: "passos 1 2 3 4 e 5" tem todos os vãos do espaço comum (2,45 pt), e
    # nenhum passava do dobro da mediana: saía "passos 1234e5". O espaço entre as palavras
    # comuns da mesma linha é a régua: letra espaçada tem o vão bem menor que ele.
    letras = _letras("passos1234e5", [0.2, 0.1, 0.3, 0.2, 0.1, 2.45, 2.45, 2.45, 2.45, 2.45, 2.45])
    assert juntar_letras_espacadas(letras, 10.5) is None


def test_algarismos_soltos_depois_de_palavra_ficam_como_estao() -> None:
    letras = _letras("Notas123456", [0.2, 0.1, 0.3, 0.2, 2.45, 2.45, 2.45, 2.45, 2.45, 2.45])
    assert juntar_letras_espacadas(letras, 10.5) is None


def test_tres_pares_de_letras_vizinhas_bastam() -> None:
    # F2 da auditoria: o limite de 3 pares não era fixado por teste. "C A S A" tem 3.
    assert juntar_letras_espacadas(_letras("CASA", [1.4, 1.4, 1.4]), 8.5) == "CASA"


def test_dois_pares_sozinhos_na_linha_nao_bastam() -> None:
    # Com 2, "de 2 a 7" (16 linhas do Competente) colaria; sem palavra comum na linha,
    # é só o limite de pares que segura.
    assert juntar_letras_espacadas(_letras("2a7", [2.45, 2.45]), 10.5) is None


def test_rotulo_com_maioria_de_palavras_de_uma_letra() -> None:
    # F1 da auditoria: com dois vãos de palavra (4,4) e dois de letra (1,4), a mediana caía
    # entre eles e saía "ÉOFIM". A fronteira se mede pelo vão menor do trecho.
    letras = _letras("\u00c9OFIM", [4.4, 4.4, 1.4, 1.4])
    assert juntar_letras_espacadas(letras, 8.5) == "\u00c9 O FIM"
