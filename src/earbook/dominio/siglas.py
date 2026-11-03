# SPDX-License-Identifier: GPL-3.0-or-later
"""As siglas candidatas ao glossário da adaptação (ADR-0009).

É o `nomes.json` da sigla: barato e determinístico, e a sessão decide qual fica sigla, qual vai
por extenso e qual sai. A forma por extenso é a que o próprio livro dá antes de "(SIGLA)".
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from earbook.dominio.glossario import EntradaDoGlossario
from earbook.dominio.segmento import PALAVRA, Segmento

# Duas maiúsculas ou mais, com algarismo e hífen ("CID-10", "DSM-IV-TR", "NT-3") e o plural
# minúsculo ("AVCs").
_SIGLA = re.compile(r"(?<![\w-])[A-ZÀ-Ú][A-ZÀ-Ú0-9]+(?:-[A-Z0-9]+)*s?(?![\w-])")
_ROMANO = re.compile(r"[IVXLCDM]+")
# A linha toda em maiúsculas é subtítulo, não sigla ("SINTOMAS AFETIVOS").
PROPORCAO_DE_MAIUSCULAS = 0.6
_LIGACOES = frozenset({"de", "da", "do", "das", "dos", "e", "a", "o", "em", "para", "por"})


@dataclass(frozen=True)
class CandidatoASigla:
    sigla: str
    vezes: int
    exemplo: str
    """O ID da primeira vez."""
    extenso: str
    """A forma que o livro dá antes de "(SIGLA)"; vazio quando ele não dá."""


def siglas_candidatas(
    segmentos: Iterable[Segmento], glossario: Sequence[EntradaDoGlossario]
) -> tuple[CandidatoASigla, ...]:
    """As siglas fora do glossário, da mais frequente para a menos, com a contagem."""
    lista = list(segmentos)
    minusculas = {
        p.group().casefold()
        for s in lista
        for p in PALAVRA.finditer(s.texto)
        if p.group().islower()
    }
    ja_no_glossario = {entrada.original for entrada in glossario}
    vezes: Counter[str] = Counter()
    exemplos: dict[str, str] = {}
    extensos: dict[str, str] = {}
    for segmento in (s for s in lista if not _caixa_alta(s.texto)):
        for achado in _SIGLA.finditer(segmento.texto):
            sigla = achado.group()
            if _nao_e_sigla(sigla, minusculas) or sigla in ja_no_glossario:
                continue
            vezes[sigla] += 1
            _ = exemplos.setdefault(sigla, segmento.id)
            if not extensos.get(sigla):
                extensos[sigla] = _extenso(segmento.texto, achado.start(), sigla)
    ordem = sorted(vezes, key=lambda sigla: (-vezes[sigla], sigla))
    return tuple(CandidatoASigla(s, vezes[s], exemplos[s], extensos[s]) for s in ordem)


def _caixa_alta(texto: str) -> bool:
    letras = [letra for letra in texto if letra.isalpha()]
    maiusculas = sum(letra.isupper() for letra in letras)
    return bool(letras) and maiusculas > PROPORCAO_DE_MAIUSCULAS * len(letras)


def _nao_e_sigla(sigla: str, minusculas: set[str]) -> bool:
    """O algarismo romano ("IV") e a palavra que o livro também escreve em minúscula
    ("CAPÍTULO", numa frase em que só ela está em maiúsculas)."""
    return _ROMANO.fullmatch(sigla) is not None or sigla.casefold() in minusculas


def _extenso(texto: str, inicio: int, sigla: str) -> str:
    """ "…ativador ascendente (SRAA)": as palavras antes do parêntese, uma por letra da sigla,
    sem contar "de", "da", "e"…, e a primeira com a inicial da sigla. Sem isso, vazio."""
    antes = texto[:inicio]
    if not antes.endswith("("):
        return ""
    letras = len(re.sub(r"[^A-ZÀ-Ú]", "", sigla.split("-", maxsplit=1)[0]))
    palavras = [p for p in PALAVRA.finditer(antes) if p.group().casefold() not in _LIGACOES]
    if len(palavras) < letras:
        return ""
    primeira = palavras[-letras]
    if _sem_acento(primeira.group()[0]) != _sem_acento(sigla[0]):
        return ""
    return antes[primeira.start() :].rstrip(" (,")


def _sem_acento(letra: str) -> str:
    return unicodedata.normalize("NFD", letra.casefold())[0]
