# SPDX-License-Identifier: GPL-3.0-or-later
"""A língua do original que o `conferir` sabe achar na tradução (ADR-0006, ADR-0013).

O texto que ficou sem tradução se reconhece pelas palavras funcionais da língua do original
("the", "of"; "el", "los"), que o português não tem. A língua sem lista medida não se traduz:
o que ficasse no original iria calado para a voz.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from earbook.dominio.segmento import PALAVRA
from earbook.dominio.siglas import caixa_alta
from earbook.dominio.traducao import mesmo_idioma

_URL = re.compile(r"\S*(?:https?://|www\.)\S*")
# O hífen ASCII, o tipográfico (U+2010) e o não separável (U+2011): o pronome colado
# ("preveni-los") não conta com nenhum deles (ADR-0013).
_HIFENS = ("-", "\u2010", "\u2011")


class LinguaSemListaError(ValueError):
    pass


@dataclass(frozen=True)
class LinguaDoOriginal:
    nome: str
    """Como a mensagem do `conferir` a diz: "parece espanhol"."""
    funcionais: frozenset[str]
    proporcao: float
    """A parte das palavras do trecho que, sendo funcionais, o faz parecer o original."""
    exemplos: str
    so_a_palavra_solta: bool
    """Conta só a palavra em minúsculas e sem hífen, como no espanhol: em português,
    "AL" é sigla (anestésico local), "Y" é eixo, "Le Fort" é nome, "preveni-los" tem o
    pronome colado e "et al." é latim (ADR-0013). A maiúscula conta na linha toda em
    maiúsculas."""


# Medido em 2026-11-01 (ADR-0006): o texto em inglês do Huxley e do Tides tem mediana de 37%
# destas palavras, e o Competente, em português, 0%. Sem "a", "me", "for" e "do", que também
# são palavras do português.
PALAVRAS_FUNCIONAIS_INGLESAS = frozenset({
    "the", "and", "of", "to", "is", "was", "which", "that", "with", "it", "he", "she", "they",
    "this", "not", "but", "be", "have", "had", "his", "her", "its", "were", "are", "been",
    "would", "could", "from", "by", "at", "an", "or", "my", "we", "you", "there", "their",
    "what", "when", "who", "will", "one", "all", "so", "than", "them", "these", "those",
    "into", "upon",
})  # fmt: skip
# Medido em 2026-11-17 (ADR-0013, "Calibragem"): o Miller, em espanhol, tem mediana de 24,5%
# destas palavras, e o Manica, em português, 0%. Sem as que o português também tem ("de",
# "que", "como", "para", "por", "se", "sobre", "entre", "está"); "la" só no pronome colado
# ("fazê-la"), que não conta.
PALAVRAS_FUNCIONAIS_ESPANHOLAS = frozenset({
    "el", "la", "los", "las", "y", "del", "al", "un", "una", "con", "es", "en", "lo", "le",
    "les", "su", "sus", "pero", "muy", "más", "hay", "puede", "pueden", "también", "cuando",
    "donde", "sin", "son", "fue", "han", "según", "ya", "aunque", "mismo", "están",
})  # fmt: skip
INGLES = LinguaDoOriginal(
    "inglês", PALAVRAS_FUNCIONAIS_INGLESAS, 0.2, "'the', 'of', 'and'", so_a_palavra_solta=False
)
ESPANHOL = LinguaDoOriginal(
    "espanhol", PALAVRAS_FUNCIONAIS_ESPANHOLAS, 0.1, "'el', 'los', 'y'", so_a_palavra_solta=True
)
_LINGUAS = (("en", INGLES), ("es", ESPANHOL))


def lingua_do_original(idioma: str) -> LinguaDoOriginal | None:
    """A língua do livro, pelo código do `livro.json` ("es", "en-US", "spa"); `None` quando
    não há lista para ela."""
    return next((lingua for codigo, lingua in _LINGUAS if mesmo_idioma(idioma, codigo)), None)


def exigir_lingua_do_original(idioma: str, onde: str) -> LinguaDoOriginal:
    """A língua do livro, ou o erro que diz o idioma e as línguas que têm lista."""
    if (lingua := lingua_do_original(idioma)) is None:
        linguas = " e ".join(lingua.nome for _, lingua in _LINGUAS)
        mensagem = (
            f"{onde}: o livro está em {idioma!r}, e o conferir só acha o que ficou sem tradução"
            f" em {linguas}; sem a lista de palavras funcionais da língua, o texto esquecido no"
            " original iria calado para a voz (ADR-0013)"
        )
        raise LinguaSemListaError(mensagem)
    return lingua


def palavras(texto: str) -> list[str]:
    """As palavras em minúsculas, sem URL: o link tem "the" e "of" e não é lido como frase."""
    return [achado.group().casefold() for achado in PALAVRA.finditer(_URL.sub(" ", texto))]


def funcionais(lingua: LinguaDoOriginal, texto: str) -> int:
    """Quantas palavras do texto são funcionais da língua do original."""
    return contar(lingua, texto)[0]


def contar(lingua: LinguaDoOriginal, texto: str) -> tuple[int, int]:
    """As palavras funcionais da língua do original e o total de palavras, numa passada só."""
    texto = _URL.sub(" ", texto)
    em_caixa_alta = lingua.so_a_palavra_solta and caixa_alta(texto)
    total = do_original = 0
    for achado in PALAVRA.finditer(texto):
        total += 1
        if achado.group().casefold() in lingua.funcionais and (
            not lingua.so_a_palavra_solta or _solta(achado, texto, caixa_alta=em_caixa_alta)
        ):
            do_original += 1
    return do_original, total


def _solta(achado: re.Match[str], texto: str, *, caixa_alta: bool) -> bool:
    palavra = achado.group()
    if not (palavra.islower() or (caixa_alta and palavra.isupper())):
        return False
    antes = texto[max(0, achado.start() - 3) : achado.start()]
    # O "al" de "et al.", que a tradução mantém, é latim (999 segmentos do Miller).
    depois = texto[achado.end() : achado.end() + 1]
    return not antes.endswith((*_HIFENS, "et ")) and depois not in _HIFENS
