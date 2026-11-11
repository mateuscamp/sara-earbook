# SPDX-License-Identifier: GPL-3.0-or-later
"""Os caracteres de uma linha do PDF antes de virarem texto (ADR-0004, "Número de referência e
espaço falso").

Duas coisas que só se veem no caractere, e não na linha pronta:
- **o número de referência sobrescrito** ("wages.¹", "84%-90%.²,³", "et al.¹⁹⁴"), que a voz lia
  colado à palavra. Medido no Practical: 0,58 do corpo, com a linha de base 0,33 do corpo acima.
  Sai só a chamada: algarismos, vírgula e traço, depois de letra ou de pontuação. O expoente
  depois de algarismo ("10⁶"), a carga do íon ("Ca²⁺"), a unidade ao quadrado ("kg/m²") e a letra
  solta ("r²") ficam;
- **o espaço que o pdfminer inventa** no nome com letra espaçada (Practical: Gotham-Bold com 1 pt
  a mais entre as letras, "NATALI E MORY L"). O pdfminer põe espaço onde o vão passa de uma
  fração da letra; quando o vão é o mesmo da letra espaçada, o espaço não existe no PDF.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from statistics import median

RAZAO_DO_SOBRESCRITO = 0.85
"""A letra da chamada é menor que 0,85 da letra da linha (medido: 0,58 no Practical, 0,59 na
tabela)."""
SUBIDA_MINIMA = 0.15
"""A linha de base da chamada sobe mais de 0,15 da letra da linha (medido: 0,33 no Practical)."""
FOLGA_DO_VAO = 0.03
"""O espaço inventado some se o vão dele passa do vão típico entre letras por até 0,03 da letra:
0,3 pt no corpo de 10. O vão da palavra, no texto comum, passa de 2 pt."""
DIFERENCA_DE_TAMANHO = 0.5
VAOS_MINIMOS = 3
# A vírgula do texto composta na letra pequena, no fim, vai junto (R6 da code-review).
_CHAMADA = re.compile(r"\d+(?:\s*[,\u2010-\u2014-]\s*\d+)*,?")
_PONTUACAO_ANTES = frozenset(".,;:)]%\u2019\u201d\"'")
# A unidade ao quadrado ou ao cubo: "m²", "cm²", "mm³", "μm²".
_UNIDADES = frozenset({"m", "cm", "mm", "km", "dm", "nm", "μm", "µm"})
_PALAVRA_ANTES = re.compile(r"[^\W\d_]+$")


@dataclass(frozen=True)
class Caractere:
    texto: str
    x0: float
    x1: float
    tamanho: float
    base: float
    """Altura do pé do caractere, em pontos, de baixo para cima, como no PDF. A chamada sobe
    a linha de base, e o pé sobe junto; o pé da letra menor na mesma linha de base sobe só a
    diferença da descendente (0,09 da letra da linha, na de 0,58)."""
    virtual: bool = False
    """O espaço que o pdfminer pôs pelo vão, sem caractere no PDF; `x0` e `x1` são o fim da
    letra antes e o começo da letra depois."""


@dataclass(frozen=True)
class TextoDaLinha:
    texto: str
    chamadas: tuple[str, ...]
    """Cada chamada tirada, entre colchetes, depois da palavra que ela segue: "wages.[1]"."""
    caracteres: tuple[Caractere, ...]
    """Os que ficaram, na ordem: a letra espaçada se mede neles."""


def texto_da_linha(caracteres: Sequence[Caractere], tamanho: float) -> TextoDaLinha:
    """O texto da linha sem as chamadas sobrescritas e sem o espaço inventado no vão da letra."""
    fora: set[int] = set()
    chamadas: list[str] = []
    for inicio, fim in _chamadas(caracteres, tamanho):
        fora.update(range(inicio, fim))
        chamadas.append(_registro(caracteres, inicio, fim))
    fora.update(_espacos_inventados(caracteres, tamanho))
    ficam = tuple(c for i, c in enumerate(caracteres) if i not in fora)
    return TextoDaLinha("".join(c.texto for c in ficam), tuple(chamadas), ficam)


def _chamadas(caracteres: Sequence[Caractere], tamanho: float) -> list[tuple[int, int]]:
    """(início, fim) de cada trecho sobrescrito que é chamada de referência."""
    base = _base_da_linha(caracteres, tamanho)
    if base is None:
        return []
    sobe = [_sobrescrito(c, tamanho, base) for c in caracteres]
    trechos: list[tuple[int, int]] = []
    inicio: int | None = None
    for i, sobrescrito in enumerate([*sobe, False]):
        if sobrescrito and inicio is None:
            inicio = i
        elif not sobrescrito and inicio is not None:
            trechos.append((inicio, i))
            inicio = None
    aparados = [_sem_espaco_nas_pontas(caracteres, inicio, fim) for inicio, fim in trechos]
    return [t for t in aparados if t is not None and _e_chamada(caracteres, *t)]


def _sem_espaco_nas_pontas(
    caracteres: Sequence[Caractere], inicio: int, fim: int
) -> tuple[int, int] | None:
    """O trecho sem o espaço da letra pequena nas pontas: o de dentro ("1,8, 9") fica nele, e o
    de fora separa a chamada da palavra seguinte (R5 da code-review)."""
    while inicio < fim and not caracteres[inicio].texto.strip():
        inicio += 1
    while fim > inicio and not caracteres[fim - 1].texto.strip():
        fim -= 1
    return (inicio, fim) if inicio < fim else None


def _base_da_linha(caracteres: Sequence[Caractere], tamanho: float) -> float | None:
    """A linha de base mais comum entre as letras do tamanho da linha."""
    bases = Counter(
        round(c.base, 1)
        for c in caracteres
        if not c.virtual and abs(c.tamanho - tamanho) <= DIFERENCA_DE_TAMANHO
    )
    return bases.most_common(1)[0][0] if bases else None


def _sobrescrito(caractere: Caractere, tamanho: float, base: float) -> bool:
    menor = caractere.tamanho < tamanho * RAZAO_DO_SOBRESCRITO
    acima = caractere.base - base > tamanho * SUBIDA_MINIMA
    # O espaço de verdade na letra pequena também sobe: é o de dentro da chamada ("1,8, 9").
    return not caractere.virtual and menor and acima


def _e_chamada(caracteres: Sequence[Caractere], inicio: int, fim: int) -> bool:
    """Só algarismo, vírgula e traço, colado a uma palavra ou a uma pontuação que fecha."""
    texto = "".join(c.texto for c in caracteres[inicio:fim])
    if inicio == 0 or _CHAMADA.fullmatch(texto) is None:
        return False
    antes = caracteres[inicio - 1]
    if antes.virtual or not antes.texto.strip():
        return False
    if antes.texto in _PONTUACAO_ANTES:
        return True
    palavra = _PALAVRA_ANTES.search("".join(c.texto for c in caracteres[:inicio]))
    return palavra is not None and len(palavra.group()) > 1 and palavra.group() not in _UNIDADES


def _registro(caracteres: Sequence[Caractere], inicio: int, fim: int) -> str:
    antes = "".join(c.texto for c in caracteres[:inicio]).rsplit(maxsplit=1)
    chamada = "".join(c.texto for c in caracteres[inicio:fim])
    return f"{antes[-1] if antes else ''}[{chamada}]"


def _espacos_inventados(caracteres: Sequence[Caractere], tamanho: float) -> list[int]:
    """Os espaços do pdfminer cujo vão não passa do vão típico entre as letras da linha."""
    vaos = [
        depois.x0 - antes.x1
        for antes, depois in pairwise(caracteres)
        if _letra(antes) and _letra(depois)
    ]
    if len(vaos) < VAOS_MINIMOS:
        return []
    limite = median(vaos) + tamanho * FOLGA_DO_VAO
    return [
        i
        for i, c in enumerate(caracteres)
        if c.virtual and c.texto == " " and c.x1 - c.x0 <= limite
    ]


def _letra(caractere: Caractere) -> bool:
    return not caractere.virtual and caractere.texto.strip() != ""
