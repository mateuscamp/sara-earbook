# SPDX-License-Identifier: GPL-3.0-or-later
"""O subtítulo em versalete: título no lugar dele, e não nota no fim do capítulo (ADR-0004,
"O que ficou da Fase 1").

No Dalgalarrondo, o versalete é desenhado com maiúsculas de dois tamanhos: a inicial da palavra
em 10,5 pt e o resto em 7,4 pt, com o corpo de 10. Pelo tamanho da maioria das letras, a linha
virava nota, e o `montar` levava "DELÍRIO DE GRANDEZA (DE ENORMIDADE)" para "Notas".
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from earbook.adaptadores.pdf import ler_paginas
from earbook.dominio.pagina import Linha, em_versalete
from tests.linhas_de_teste import ENTRELINHA, linha, montar, resumo, texto_corrido
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf


def _letras(texto: str, maior: float = 10.5, menor: float = 7.4) -> list[tuple[str, float]]:
    """O versalete feito à mão: a inicial de cada palavra em `maior`, o resto em `menor`."""
    return [
        (letra, maior if i == 0 or texto[i - 1] == " " else menor)
        for i, letra in enumerate(texto)
        if letra != " "
    ]


def test_maiusculas_de_dois_tamanhos_sao_versalete() -> None:
    assert em_versalete(_letras("DELÍRIO DE REFERÊNCIA"), 7.4)


def test_maiusculas_de_um_tamanho_so_nao_sao_versalete() -> None:
    # Competente: "PREFÁCIO", "APÊNDICE A" e "PARTE I · O QUE É ESSA COISA" vêm em maiúsculas de
    # 7,5 e 8,5 pt, de um tamanho só. São rótulos do livro, e não podem virar título.
    assert not em_versalete(_letras("APÊNDICE A", 7.5, 7.5), 7.5)


def test_letra_minuscula_desfaz_o_versalete() -> None:
    assert not em_versalete(_letras("Delírio de referência"), 7.4)


def test_simbolo_maior_que_a_linha_nao_faz_versalete() -> None:
    # Hard Parts p. 69: "ML = 100 * ∑", com o somatório em 14 pt numa linha de 10.
    letras = [(c, 14.1 if c == "∑" else 10.0) for c in "ML=100*∑"]
    assert not em_versalete(letras, 10.0)


def _versalete(texto: str, topo: float) -> Linha:
    return replace(linha(texto, topo, tamanho=7.4), versalete=True)


def test_subtitulo_em_versalete_vira_titulo_e_nao_nota() -> None:
    livro = montar(
        [
            *texto_corrido(0.1),
            _versalete("DELÍRIO DE REFERÊNCIA", 0.3),
            linha("Aqui o indivíduo apresenta a tendência de interpretar.", 0.32),
        ]
    )
    assert resumo(livro)[1:] == [
        ("titulo", "DELÍRIO DE REFERÊNCIA"),
        ("paragrafo", "Aqui o indivíduo apresenta a tendência de interpretar."),
    ]


def test_linha_seguinte_em_maiusculas_continua_o_titulo_em_versalete() -> None:
    # Dalgalarrondo p. 270: na segunda linha, "PERSONALIDADE PARANÓIDE", nenhuma letra é maior.
    livro = montar(
        [
            *texto_corrido(0.1),
            _versalete("TRANSTORNO DA", 0.3),
            linha("PERSONALIDADE PARANÓIDE", 0.3 + ENTRELINHA, tamanho=7.4),
            linha("Sensibilidade excessiva a rejeições e a contratempos.", 0.3 + 2 * ENTRELINHA),
        ]
    )
    assert resumo(livro)[1:] == [
        ("titulo", "TRANSTORNO DA PERSONALIDADE PARANÓIDE"),
        ("paragrafo", "Sensibilidade excessiva a rejeições e a contratempos."),
    ]


def test_maiusculas_pequenas_sem_versalete_continuam_nota() -> None:
    livro = montar([*texto_corrido(0.1), linha("CRÉDITOS DAS IMAGENS", 0.3, tamanho=7.5)])
    assert resumo(livro)[-1] == ("nota", "CRÉDITOS DAS IMAGENS")


def test_maiusculas_depois_de_nota_que_nao_e_versalete_continuam_nota() -> None:
    # Só o título em versalete se continua. Sem essa guarda, a linha só em maiúsculas depois de
    # uma nota virava título: "ISBN 978-85-363-1493-8" na página de direitos do Dalgalarrondo e
    # "1957)" na linha do tempo do Competente (mutante M6 da auditoria).
    livro = montar(
        [
            *texto_corrido(0.1),
            linha("Reservados todos os direitos de publicação, 2008.", 0.3, tamanho=7.4),
            linha("ISBN 978-85-363-1493-8", 0.3 + ENTRELINHA, tamanho=7.4),
        ]
    )
    assert resumo(livro)[1:] == [
        ("nota", "Reservados todos os direitos de publicação, 2008. ISBN 978-85-363-1493-8")
    ]


def test_versalete_do_pdf_e_marcado_pelo_adaptador(tmp_path: Path) -> None:
    pdf = montar_pdf(
        tmp_path / "livro.pdf",
        [
            [
                LinhaDeTeste("DELÍRIO DE REFERÊNCIA", 72, 700, tamanho=7.4, versalete=True),
                LinhaDeTeste("CRÉDITOS DAS IMAGENS", 72, 680, tamanho=7.4),
                LinhaDeTeste("O indivíduo apresenta a tendência.", 72, 660, tamanho=10),
            ]
        ],
    )
    linhas = [(lida.texto, lida.versalete) for lida in ler_paginas(pdf)[0].linhas]
    assert linhas == [
        ("DELÍRIO DE REFERÊNCIA", True),
        ("CRÉDITOS DAS IMAGENS", False),
        ("O indivíduo apresenta a tendência.", False),
    ]
