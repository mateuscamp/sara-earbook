# SPDX-License-Identifier: GPL-3.0-or-later
"""O rótulo que abre a tabela, a figura e o quadro do PDF (ADR-0004, "Tabela e figura pela letra"
e "Rótulo e cabeçalho do capítulo na borda").

Mora aqui porque três regras o leem: a borda (`paginacao`), que não o tira como cabeçalho; a
tabela e a figura (`tabelas_e_figuras`), que saem a partir dele; e o quadro (`quadro`), que ele
abre. A `paginacao` não pode importar a `tabelas_e_figuras`, que a importa.
"""

from __future__ import annotations

import re

# "TABLE" sozinho na linha (o número vem na de baixo, no Practical), ou o rótulo com o número
# seguido de ponto, maiúscula ou fim de linha: "Table 2.1 Pain Axes", "Table 5-7. Components",
# "• Figure 2.1  International…". A menção que a linha quebrou ("Table 5-7 shows…", "Figure 5-2),
# Addison…", Hard Parts) e "Table of Contents" não são rótulo.
_NUMERO_E_LEGENDA = r"\s+\d+(?:[.\-\u2013]\d+)*[A-Z]?(?:\.?\s+[A-Z]|\.?\s*$)"
ROTULO_DA_TABELA = re.compile(rf"TABLE\s*$|(?:TABLE|Table){_NUMERO_E_LEGENDA}")
# A continuação da figura na página seguinte também é rótulo: "• Figure 3.1, cont'd." e "• Figure
# 20.4, cont'd Note (G)…", no Practical (ADR-0004, "Figura pelo diagrama e quadro depois da
# tabela").
_CONTINUADA = r"\s+\d+(?:[.\-\u2013]\d+)*[A-Z]?,\s*cont"
ROTULO_DA_FIGURA = re.compile(
    rf"(?:•\s*)?(?:FIGURE|Figure|Fig\.)(?:{_NUMERO_E_LEGENDA}|{_CONTINUADA})"
)
# O rótulo em português e em espanhol, sem olhar a caixa: o versalete do Manica sai "FigurA",
# "quAdro", "tAbelA", e o do Miller, "TABLA" e "CUADRO". O número é composto, com ponto ou traço
# ("1.2", "2-1", "2.7.1", "42.1a"): "Figura 3 mostra…" não é rótulo.
_NUMERO_COMPOSTO = r"\s+\d+(?:[.\-\u2013]\d+)+[A-Za-z]?(?!\w)"
TABELA_LOCAL = re.compile(rf"(?:quadro|tabela|tabla|cuadro){_NUMERO_COMPOSTO}", re.IGNORECASE)
FIGURA_LOCAL = re.compile(rf"(?:•\s*)?(?:figura|fig\.){_NUMERO_COMPOSTO}", re.IGNORECASE)
ROTULO_DA_CAIXA = re.compile(r"(?:•\s*)?(?:BOX|Box)\s+\d+(?:[.\-\u2013]\d+)*[A-Za-z]?(?!\w)")
"""O quadro do tratado em inglês: "• BOX 10.1", "• Box 49.4", "•Box 76.2" (97 no Practical, em
MyriadPro negrito de 10 pt, com o corpo em AGaramondPro). A menção na prosa ("Box 6.4 lists…") tem
a letra do corpo."""


def abre_com_rotulo(texto: str) -> bool:
    """A linha abre com o rótulo de uma tabela, de uma figura ou de um quadro."""
    rotulos = (ROTULO_DA_TABELA, ROTULO_DA_FIGURA, TABELA_LOCAL, FIGURA_LOCAL, ROTULO_DA_CAIXA)
    return any(rotulo.match(texto) for rotulo in rotulos)
