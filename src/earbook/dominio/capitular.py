# SPDX-License-Identifier: GPL-3.0-or-later
"""Capitular deslocada (ADR-0007): a letra que a conversão do PDF deixou no meio do texto
volta para o começo do capítulo, quando o próprio livro prova a palavra."""

from __future__ import annotations

import itertools
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

from earbook.dominio.segmento import ABRE_PARAGRAFO, PALAVRA

_ANTES_DA_PALAVRA = re.compile(ABRE_PARAGRAFO)
# O fim da frase antes da letra que abre a seguinte ("desejo. A", "3. A"), com a aspa ou o
# parêntese que fecham a frase entre os dois ("desejo.” A").
_FIM_DA_FRASE = tuple(".!?\u2026:;")
_FECHA_A_FRASE = '"\u201d\u2019)'


class _Pista(Protocol):
    @property
    def id(self) -> str: ...
    @property
    def posicao(self) -> int: ...
    @property
    def letra(self) -> str: ...


class Suspeita(Protocol):
    """O que este módulo lê da `Suspeita` da limpeza, que importa este módulo: sem ciclo."""

    @property
    def id(self) -> str: ...
    @property
    def texto(self) -> str: ...
    @property
    def pista(self) -> _Pista | None: ...


@dataclass(frozen=True)
class CapitularDevolvida:
    """A letra que saiu de `origem`, na `posicao`, e entrou no começo de `id`."""

    id: str
    origem: str
    posicao: int
    letra: str


@dataclass(frozen=True)
class Leitura:
    """Como a letra entra: colada na primeira palavra ("Dawn") ou como palavra ("A dark")."""

    letra: str
    colada: bool


class Vocabulario:
    """As palavras e os pares de palavras do livro, sem caixa e com um apóstrofo só: é a
    prova de que a palavra reconstruída existe ("Dawn", "Gul'dan", "a dark"). Guarda também
    as letras que o livro usa sozinhas em minúscula ("a", "o", "e"): as que são palavra."""

    def __init__(self, textos: Iterable[str]) -> None:
        self._palavras: set[str] = set()
        self._pares: Counter[tuple[str, str]] = Counter()
        self._letras_minusculas: set[str] = set()
        for texto in textos:
            cruas = [p.group() for p in PALAVRA.finditer(texto)]
            self._letras_minusculas.update(p for p in cruas if len(p) == 1 and p.islower())
            palavras = [_normal(p) for p in cruas]
            self._palavras.update(palavras)
            self._pares.update(itertools.pairwise(palavras))

    def letra_e_palavra(self, letra: str) -> bool:
        """`letra_e_palavra("A")` é True quando o livro tem "a" sozinho, em minúscula."""
        return letra.lower() in self._letras_minusculas

    def leitura(self, letra: str, primeira: str, *, da_pista: bool) -> Leitura | None:
        """None quando nenhuma leitura existe ou quando as duas existem. Com `da_pista`, um
        dos pares é o que a própria letra solta forma ("Quando O rei"), e não prova nada
        (lote C da revisão)."""
        colada = _normal(letra + primeira) in self._palavras
        separada = self._pares[_normal(letra), _normal(primeira)] > int(da_pista)
        if colada == separada:
            return None
        return Leitura(letra, colada)


def devolver(
    texto: str, letra_de: str, posicao: int, leitura: Leitura, *, mesmo_segmento: bool
) -> tuple[str, str] | None:
    """(texto do parágrafo marcado, texto de onde a letra saiu); None se a origem ficaria
    vazia, porque a limpeza não apaga em silêncio (ADR-0003)."""
    sem_a_letra = _tirar_a_letra(letra_de, posicao)
    if not sem_a_letra.strip():
        return None
    base = sem_a_letra if mesmo_segmento else texto
    inicio = _inicio_da_palavra(base)
    letra = leitura.letra if leitura.colada else f"{leitura.letra} "
    return base[:inicio] + letra + base[inicio:], sem_a_letra


def leituras(
    suspeitas: Sequence[Suspeita], textos: dict[str, str]
) -> list[tuple[Suspeita, Leitura]]:
    """As capitulares com pista que têm uma leitura só, provada pelas palavras do livro."""
    vocabulario = Vocabulario(textos.values())
    propostas: list[tuple[Suspeita, Leitura]] = []
    for suspeita in suspeitas:
        if suspeita.pista is None:
            continue
        primeira = primeira_palavra(suspeita.texto)
        pista = suspeita.pista
        depois = PALAVRA.search(textos[pista.id], pista.posicao + 1)
        if _no_lugar(pista, textos[pista.id], depois, vocabulario):
            continue
        da_pista = depois is not None and _normal(depois.group()) == _normal(primeira)
        leitura = vocabulario.leitura(pista.letra, primeira, da_pista=da_pista)
        if leitura is not None:
            propostas.append((suspeita, leitura))
    return propostas


def _no_lugar(
    pista: _Pista, texto: str, depois: re.Match[str] | None, vocabulario: Vocabulario
) -> bool:
    """A letra que abre frase, antes de palavra em minúscula, e que o livro usa como palavra:
    é o artigo no lugar dele ("desejo. A resultante"), não a capitular (ADR-0007, "A letra que
    abre frase"). "A Lothar" (antes de nome) e "G demanded." (o livro não tem "g") voltam.
    `texto` é o do segmento da pista."""
    return (
        depois is not None
        and depois.group()[0].islower()
        and _abre_frase(texto, pista.posicao)
        and vocabulario.letra_e_palavra(pista.letra)
    )


def _abre_frase(texto: str, posicao: int) -> bool:
    """A letra está no começo do parágrafo, depois das aspas e travessões, ou depois de fim de
    frase e de espaço. Só o fim do que vem antes dela importa (lote B da revisão)."""
    if _inicio_da_palavra(texto) == posicao:
        return True
    antes = texto[:posicao].rstrip()
    return len(antes) < posicao and antes.rstrip(_FECHA_A_FRASE).endswith(_FIM_DA_FRASE)


def devolver_uma(
    suspeita: Suspeita,
    leitura: Leitura,
    textos: dict[str, str],
    feitas: Sequence[CapitularDevolvida],
) -> list[CapitularDevolvida]:
    """Muda `textos` no lugar. Segmento já mexido fica como está: a posição da pista mudou."""
    pista = suspeita.pista
    tocados = {i for d in feitas for i in (d.id, d.origem)}
    if pista is None or suspeita.id in tocados or pista.id in tocados:
        return []
    mesmo = pista.id == suspeita.id
    feito = devolver(
        textos[suspeita.id], textos[pista.id], pista.posicao, leitura, mesmo_segmento=mesmo
    )
    if feito is None:
        return []
    textos[pista.id], textos[suspeita.id] = feito[1], feito[0]
    return [CapitularDevolvida(suspeita.id, pista.id, pista.posicao, pista.letra)]


def primeira_palavra(texto: str) -> str:
    achado = PALAVRA.search(texto, _inicio_da_palavra(texto))
    return achado.group() if achado is not None else ""


def _tirar_a_letra(texto: str, posicao: int) -> str:
    """Sai a letra e um espaço vizinho: "stirred, D unable" → "stirred, unable"."""
    if posicao > 0 and texto[posicao - 1].isspace():
        return texto[: posicao - 1] + texto[posicao + 1 :]
    return texto[:posicao] + texto[posicao + 1 :].lstrip(" ")


def _inicio_da_palavra(texto: str) -> int:
    """Depois das aspas e dos travessões que abrem o parágrafo ("“o!”" → depois da aspa)."""
    achado = _ANTES_DA_PALAVRA.match(texto)
    return achado.end() if achado is not None else 0


def _normal(palavra: str) -> str:
    return palavra.casefold().replace("\u2019", "'")
