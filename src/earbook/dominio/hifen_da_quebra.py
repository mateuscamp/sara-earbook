# SPDX-License-Identifier: GPL-3.0-or-later
"""O hífen da quebra de linha do PDF: o próprio livro é o dicionário (ADR-0004).

A palavra partida no fim da linha volta inteira, a não ser que o livro escreva a mesma palavra
com hífen em outro lugar (`non-productive`, `anti-pattern`). Saiu de `blocos.py` para ele caber
no limite de 400 linhas do ADR-0001, quando o quadro entrou (ADR-0004, "Quadro no lugar").
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from earbook.dominio.pagina import HIFEN_TIPOGRAFICO, Pagina

_PONTUACAO_DA_PONTA = ".,;:!?\"'()[]\u201c\u201d\u2018\u2019"


@dataclass(frozen=True)
class Dicionario:
    """O que o próprio livro diz sobre as palavras: decide o hífen da quebra de linha."""

    com_hifen: frozenset[str]
    """Escritas com hífen no meio da linha (`non-productive`)."""
    palavras: frozenset[str]
    """Escritas inteiras, sem hífen (`oriented`, `perguntou`)."""

    def mantem_o_hifen(self, antes: str, depois: str) -> bool:
        """`antes` e `depois` são as metades da palavra partida, já sem o hífen da quebra."""
        if "-" not in antes and "-" not in depois:
            return f"{antes}-{depois}" in self.com_hifen
        # A2 da auditoria: palavra que já tem outro hífen ("--no-agent-state", "proof-of-
        # concepts") é composta, e a quebra caiu num hífen dela. A não ser que as metades
        # vizinhas à quebra formem palavra do livro: então caiu numa sílaba ("ser-" +
        # "vice-based", "pergun-" + "tou-me"; B2 da pós-auditoria).
        silaba = antes.rsplit("-", 1)[-1] + depois.split("-", 1)[0]
        return silaba not in self.palavras


def dicionario_do_livro(paginas: Sequence[Pagina]) -> Dicionario:
    """As palavras do livro, com e sem hífen no meio: o dicionário do hífen da quebra."""
    com_hifen: set[str] = set()
    inteiras: set[str] = set()
    for pagina in paginas:
        for linha in pagina.linhas:
            for palavra in linha.texto.split():
                limpa = no_dicionario(palavra)
                if "-" in limpa.strip("-"):
                    com_hifen.add(limpa)
                elif limpa.isalpha():
                    inteiras.add(limpa)
    return Dicionario(frozenset(com_hifen), frozenset(inteiras))


def no_dicionario(palavra: str) -> str:
    """A forma que o dicionário do hífen guarda: sem pontuação na ponta, com "-", minúscula."""
    return palavra.strip(_PONTUACAO_DA_PONTA).replace(HIFEN_TIPOGRAFICO, "-").casefold()
