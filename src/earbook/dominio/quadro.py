# SPDX-License-Identifier: GPL-3.0-or-later
"""O Quadro do PDF: o rótulo que o abre, a letra que o continua e a linha que o solta na leitura
(ADR-0004, "Quadro no lugar").

No Dalgalarrondo, o quadro abre com o rótulo "Quadro 5.1" em 12 pt (o corpo tem 10), e a legenda
e o conteúdo vêm em 8, 9 e 11 pt. O `blocos` guarda o estado: se a linha está num quadro e os
blocos dele que esperam a frase acabar. Saiu de `blocos.py` para ele caber nas 400 linhas do
ADR-0001.
"""

from __future__ import annotations

import re

from earbook.dominio.pagina import (
    DIFERENCA_DE_TAMANHO,
    RAZAO_DO_TITULO,
    Linha,
    comeca_em_minuscula,
)

# O rótulo em letra de título abre o quadro: 79 "Quadro N.N" e 2 "Tabela N.N" em 12 pt no
# Dalgalarrondo, nenhum nos outros PDFs medidos ("Table 1-1." e "Figure 1-1." do Hard Parts vêm
# no tamanho do corpo).
_ROTULO_DO_QUADRO = re.compile(r"(?:Quadro|Tabela)\s+\d+(?:\.\d+)?\b")


def abre_o_quadro(linha: Linha, *, titulo: bool) -> bool:
    """A linha de título que começa com "Quadro" ou "Tabela" e um número. Outro rótulo, dentro do
    quadro, o continua ("Quadro 8.2" na página seguinte). A menção no corpo ("Tabela 19.1, são
    apresentados…", p. 223) tem a letra do corpo e não é título."""
    return titulo and _ROTULO_DO_QUADRO.match(linha.texto) is not None


def letra_de_quadro(linha: Linha, corpo: float) -> bool:
    """Nem a letra do corpo nem a de título: dentro dos quadros do Dalgalarrondo há linhas de 8,
    9 e 11 pt, nunca de 10. A primeira linha do corpo, ou o primeiro título que não é rótulo
    ("Questões de revisão", número de capítulo), fecha o quadro."""
    do_corpo = abs(linha.tamanho - corpo) <= DIFERENCA_DE_TAMANHO
    return not do_corpo and linha.tamanho < corpo * RAZAO_DO_TITULO


def solta_o_quadro(linha: Linha, corpo: float, *, titulo: bool, paragrafo: bool) -> bool:
    """O título, ou o parágrafo do corpo ou maior que não começa em minúscula: a frase que o
    quadro interrompe acabou, e ele entra na leitura. O destaque de 9 pt e a continuação em
    minúscula, não: o destaque que parte a continuação ("os pri-" | destaque | "meiros", p. 70)
    ficava longe do texto dele, e o `limpar` não o tirava."""
    do_corpo = linha.tamanho >= corpo - DIFERENCA_DE_TAMANHO
    return titulo or (paragrafo and do_corpo and not comeca_em_minuscula(linha.texto))
