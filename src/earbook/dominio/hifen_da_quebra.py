# SPDX-License-Identifier: GPL-3.0-or-later
"""O hífen da quebra de linha do PDF: o próprio livro é o dicionário (ADR-0004).

A palavra partida no fim da linha volta inteira, a não ser que o livro escreva a mesma palavra
com hífen em outro lugar (`non-productive`, `anti-pattern`). Saiu de `blocos.py` para ele caber
no limite de 400 linhas do ADR-0001, quando o quadro entrou (ADR-0004, "Quadro no lugar").
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace

from earbook.dominio.pagina import HIFEN_SUAVE, HIFEN_TIPOGRAFICO, Linha, Pagina

_PONTUACAO_DA_PONTA = ".,;:!?\"'()[]\u201c\u201d\u2018\u2019"
LINHAS_COM_HIFEN_INVISIVEL = 3
"""Com o U+00AD no meio de 3 linhas ou mais, o livro o usa como hífen, também no fim da linha."""
# O U+00AD que não é o último caractere da linha: seguido de letra, de algarismo ou de espaço
# ("pré" + U+00AD + " e pós-operatório").
_INVISIVEL_NO_MEIO = re.compile(f"{HIFEN_SUAVE}(?=.)")


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


def mostrar_hifen_invisivel(paginas: Sequence[Pagina]) -> tuple[Pagina, ...]:
    """As páginas com o U+00AD que é hífen de verdade trocado por "-" (ADR-0004, "Hífen
    invisível").

    No meio da linha ele é sempre hífen de verdade: o Manica e o Miller gravam assim o hífen
    ("pós" + U+00AD + "anestesia", "tabla 6" + U+00AD + "1"), e a voz colava as metades. O livro
    que o usa assim em 3 linhas ou mais usa-o como o hífen dele: o do fim da linha também vira
    "-" e segue para a regra do hífen da quebra. No livro que só o tem no fim da linha (o
    Competente), ele continua como veio, e o `blocos` o tira sem consultar o livro.
    """
    no_meio = sum(
        _INVISIVEL_NO_MEIO.search(linha.texto) is not None
        for pagina in paginas
        for linha in pagina.linhas
    )
    if not no_meio:
        return tuple(paginas)
    no_fim = no_meio >= LINHAS_COM_HIFEN_INVISIVEL
    return tuple(
        Pagina(pagina.numero, tuple(_com_o_hifen(linha, no_fim=no_fim) for linha in pagina.linhas))
        for pagina in paginas
    )


def _com_o_hifen(linha: Linha, *, no_fim: bool) -> Linha:
    texto = _INVISIVEL_NO_MEIO.sub("-", linha.texto)
    if no_fim and texto.endswith(HIFEN_SUAVE):
        texto = texto[:-1] + "-"
    return linha if texto == linha.texto else replace(linha, texto=texto)
