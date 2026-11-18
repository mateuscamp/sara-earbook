# SPDX-License-Identifier: GPL-3.0-or-later
"""O subtítulo em versalete que abre o parágrafo na mesma linha (ADR-0004, "Subtítulo em versalete
no começo do parágrafo").

No Miller, o subtítulo corrido vem em fonte só de versaletes (StoneSerif-Semibold-SC700), fecha
com ponto, e a frase começa na mesma linha, na letra do corpo: "uso clínico dE sugammadEx En
paciEntEs sanos. La primera". A linha inteira tinha a letra pequena do versalete na maioria e
virava nota, que o `montar` leva para o fim do capítulo, com o começo da frase. Partida, a
abertura é título, pela regra do versalete de fonte própria, e o resto começa o parágrafo.

A caixa trocada do subtítulo fica como veio: a certa não está no PDF (decisão do Mateus,
2026-11-13). Quem a desfaz é o tradutor.
"""

from __future__ import annotations

from dataclasses import replace

from earbook.dominio.pagina import Linha
from earbook.dominio.segmento import normalizar_espacos

FECHA_O_SUBTITULO = "."
"""O subtítulo corrido fecha com ponto. A abertura de capítulo com as primeiras palavras em
versalete não fecha: "Physics has TradiTionally been" (Maudlin p. 18) é o começo da frase."""


def pecas_da_linha(linha: Linha) -> tuple[Linha, ...]:
    """A linha, ou o subtítulo em versalete e o começo do parágrafo, quando a abertura em
    versalete fecha com ponto e as duas partes começam o texto da linha.

    A linha visual juntada de pedaços na mesma altura leva as partes só do primeiro pedaço: o que
    vem depois delas vai com o resto ("El PO4" e a carga sobrescrita, Miller p. 2062); se elas não
    começam o texto da linha, ela fica inteira. O resto começa na margem da linha, para o recuo
    do parágrafo valer como na linha inteira. A abertura é toda na fonte de versalete, e por isso
    é versalete (`adaptadores/pdf.py`), e título.
    """
    match linha.partes:
        case (abertura, resto):
            pass
        case _:
            return (linha,)
    juntas = normalizar_espacos(f"{abertura.texto} {resto.texto}")
    fecha = abertura.texto.rstrip().endswith(FECHA_O_SUBTITULO)
    if not fecha or not linha.texto.startswith(juntas):
        return (linha,)
    depois = linha.texto[len(abertura.texto) :].strip()
    return (abertura, replace(resto, texto=depois, x=linha.x))
