# SPDX-License-Identifier: GPL-3.0-or-later
"""O glossário de nomes próprios: o mesmo nome sai igual em todo capítulo (ADR-0006).

Os subagentes traduzem capítulos em paralelo e não se veem. O glossário é montado antes,
lido por todos e cobrado pelo `conferir`.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from earbook.dominio.segmento import Segmento

MINIMO_DE_VEZES = 2
_PALAVRA = re.compile(r"[^\W\d_]+(?:['\u2019-][^\W\d_]+)*")
_FIM_DE_FRASE = ".!?…:;"
# O que pode vir entre o fim da frase e a palavra seguinte: espaço, aspas, parêntese, travessão.
# O ponto destes não fecha a frase, e eles mesmos não são nome (achado da code-review).
TITULOS_ABREVIADOS = frozenset({
    "Dr", "Mr", "Mrs", "Ms", "St", "Lt", "Sr", "Jr", "Prof", "Capt", "Col", "Gen", "Sgt", "Rev",
    "Sra", "Srta", "Dra",
})  # fmt: skip
ULTIMA_PALAVRA = re.compile(r"(\w+)$")
_ENTRE_FRASES = " \t\n\"'\u201c\u201d\u2018\u2019«»()[]\u2014\u2013-"


@dataclass(frozen=True)
class EntradaDoGlossario:
    original: str
    traducao: str


@dataclass(frozen=True)
class TermosDoLote:
    """O que o tradutor decidiu fora do glossário num lote: nome ou termo comum (ADR-0007)."""

    lote: str
    termos: tuple[EntradaDoGlossario, ...]


@dataclass(frozen=True)
class CandidatoANome:
    nome: str
    vezes: int
    exemplo: str
    """O ID do primeiro segmento em que o nome aparece."""


def candidatos_a_nome(
    segmentos: Iterable[Segmento], glossario: Iterable[EntradaDoGlossario]
) -> tuple[CandidatoANome, ...]:
    """Palavras com maiúscula fora do começo da frase, vizinhas juntas (`Anduin Lothar`),
    que aparecem `MINIMO_DE_VEZES` ou mais e ainda não estão no glossário; da mais
    frequente para a menos."""
    no_glossario = {entrada.original for entrada in glossario}
    vezes: Counter[str] = Counter()
    exemplos: dict[str, str] = {}
    for segmento in segmentos:
        for nome in _nomes_do_texto(segmento.texto):
            vezes[nome] += 1
            _ = exemplos.setdefault(nome, segmento.id)
    candidatos = [
        CandidatoANome(nome, n, exemplos[nome])
        for nome, n in vezes.items()
        if n >= MINIMO_DE_VEZES and nome not in no_glossario
    ]
    return tuple(sorted(candidatos, key=lambda candidato: (-candidato.vezes, candidato.nome)))


def _nomes_do_texto(texto: str) -> list[str]:
    """As sequências de palavras com maiúscula separadas por um espaço só."""
    nomes: list[list[str]] = []
    fim_do_ultimo = -1
    for achado in _PALAVRA.finditer(texto):
        if not _parece_nome(achado.group()) or _comeca_frase(texto, achado.start()):
            fim_do_ultimo = -1
            continue
        if fim_do_ultimo >= 0 and texto[fim_do_ultimo : achado.start()] == " ":
            nomes[-1].append(achado.group())
        else:
            nomes.append([achado.group()])
        fim_do_ultimo = achado.end()
    return [_sem_possessivo(" ".join(palavras)) for palavras in nomes]


def _sem_possessivo(nome: str) -> str:
    """`Lothar's` é `Lothar`: o glossário cobra palavra inteira, e o apóstrofo não é letra."""
    return nome.removesuffix("\u2019s").removesuffix("'s")


def _parece_nome(palavra: str) -> bool:
    """Maiúscula com duas letras ou mais: a letra solta é a capitular deslocada do PDF
    (ADR-0003) ou o pronome `I`, que também abre `I'm`."""
    return (
        palavra[0].isupper()
        and len(palavra) > 1
        and not palavra.startswith(("I'", "I\u2019"))
        and palavra not in TITULOS_ABREVIADOS
    )


def _comeca_frase(texto: str, inicio: int) -> bool:
    antes = texto[:inicio].rstrip(_ENTRE_FRASES)
    if antes.endswith(".") and (titulo := ULTIMA_PALAVRA.search(antes[:-1])):
        return titulo.group(1) not in TITULOS_ABREVIADOS
    return not antes or antes[-1] in _FIM_DE_FRASE


class ConferenciaDeNomes:
    """Compila o glossário uma vez: um livro tem ~1.700 segmentos e centenas de nomes."""

    def __init__(self, glossario: Iterable[EntradaDoGlossario]) -> None:
        self._glossario: tuple[EntradaDoGlossario, ...] = tuple(glossario)
        self._termos: list[tuple[EntradaDoGlossario, re.Pattern[str], re.Pattern[str]]] = [
            (entrada, _palavra_inteira(entrada.original), _palavra_inteira(entrada.traducao))
            for entrada in self._glossario
        ]

    def motivos(self, original: str, traducao: str) -> list[str]:
        """O que a tradução fez com os nomes do glossário que estão no original.

        O nome trocado por pronome também é motivo: o tradutor repete o nome (ADR-0006).
        """
        motivos: list[str] = []
        for entrada, do_original, da_traducao in self._termos:
            if not do_original.search(original):
                continue
            # A forma do glossário pode conter o original ("Lothar" → "Lorde Lothar").
            sem_a_forma = da_traducao.sub(" ", traducao)
            if entrada.original != entrada.traducao and do_original.search(sem_a_forma):
                motivos.append(
                    f"'{entrada.original}' ficou no original; o glossário diz '{entrada.traducao}'"
                )
            elif not da_traducao.search(traducao):
                motivos.append(
                    f"sem '{entrada.traducao}', que o glossário dá para '{entrada.original}'"
                )
        return motivos

    def repetidos(self) -> list[str]:
        """Os nomes que aparecem mais de uma vez no glossário: qual das formas vale?"""
        vezes = Counter(entrada.original for entrada in self._glossario)
        return sorted(nome for nome, n in vezes.items() if n > 1)


def _palavra_inteira(termo: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(termo)}(?!\w)")
