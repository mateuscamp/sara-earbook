# SPDX-License-Identifier: GPL-3.0-or-later
"""Os caracteres de uma linha do PDF antes de virarem texto (ADR-0004, "Número de referência e
espaço falso").

Duas coisas que só se veem no caractere, e não na linha pronta:
- **o número de referência sobrescrito** ("wages.¹", "84%-90%.²,³", "et al.¹⁹⁴"), que a voz lia
  colado à palavra. Medido no Practical: 0,58 do corpo, com a linha de base 0,33 do corpo acima.
  Sai só a chamada: algarismos, vírgula e traço, depois de letra, de pontuação ou de ano ("in
  1934²²¹"). O expoente depois de outro número ("10⁶"), a carga do íon ("Ca²⁺"), a unidade ao
  quadrado ("kg/m²") e a letra solta ("r²") ficam. A chamada de 2 algarismos ou mais depois de
  letra solta ou de número ("6 h¹⁴⁸", "0,62¹¹¹") é duvidosa: só sai na página que tem chamadas
  certas (ADR-0004, "Camada do OCR sobre as figuras e chamada colada");
- **o espaço que o pdfminer inventa** no nome com letra espaçada (Practical: Gotham-Bold com 1 pt
  a mais entre as letras, "NATALI E MORY L"). O pdfminer põe espaço onde o vão passa de uma
  fração da letra; quando o vão é o mesmo da letra espaçada, o espaço não existe no PDF.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import pairwise
from statistics import median

from earbook.dominio.pagina import Letra, juntar_letras_espacadas
from earbook.dominio.segmento import normalizar_espacos

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
FRACAO_DO_ESPACO_DE_VERDADE = 0.5
"""O espaço inventado entre as letras espaçadas tem menos da metade do vão do espaço de verdade
da mesma linha (medido no Bonica: 1,7 a 2,3 pt contra 8 pt). O vão da palavra separada só pela
posição é o do espaço de verdade, e fica."""
# A vírgula do texto composta na letra pequena, no fim, vai junto (R6 da code-review). O número
# pode levar uma letra ("138a", a referência acrescentada), e a faixa, o hífen invisível
# ("19\xad21", Miller): ADR-0004, "Camada do OCR sobre as figuras e chamada colada".
_NUMERO = r"\d+[a-z]?"
_TRACOS = "\u00ad\u2010-\u2014-"
_CHAMADA = re.compile(rf"{_NUMERO}(?:\s*[,{_TRACOS}]\s*{_NUMERO})*,?")
_LISTA_OU_FAIXA = re.compile(rf"\d[a-z]?\s*[,{_TRACOS}]\s*\d")
"""Mais de um número: expoente não vem em lista, e a chamada assim é certa em qualquer lugar."""
_DOIS_ALGARISMOS = re.compile(r"\d{2,}[a-z]?,?")
_PONTUACAO_ANTES = frozenset(".,;:)]%\u2019\u201d\"'\u00bb!?")
_TRAVESSOES = frozenset("\u2013\u2014")
_PONTUACAO_DEPOIS = frozenset(".,;:)")
_FIM_DA_LINHA = frozenset({"", "\n"})
"""Nada depois, ou a quebra que o pdfminer põe no fim de toda linha."""
# A unidade ao quadrado ou ao cubo: "m²", "cm²", "mm³", "μm²".
_UNIDADES = frozenset({"m", "cm", "mm", "km", "dm", "nm", "μm", "µm"})
_PALAVRA_ANTES = re.compile(r"[^\W\d_]+$")
# O ano antes da chamada ("in 1934²²¹", "Lutz, 2017¹⁰¹"): quatro algarismos de 1500 a 2099, sem
# algarismo, ponto ou vírgula antes. O expoente de outro número ("10⁶", "1000²") fica.
_ANO_ANTES = re.compile(r"(?:^|[^\d.,])(?:1[5-9]|20)\d\d$")
# A base da potência de dez ("10¹²", "2 vezes 10²³"): o que vem depois dela é expoente.
_BASE_DEZ = re.compile(r"(?:^|[^\d.,])10$")
CHAMADAS_CERTAS_NA_PAGINA = 3
"""A página com 3 chamadas certas ou mais prova que o livro numera as referências em sobrescrito:
nela a chamada duvidosa também sai (medido no Miller: 402 das 420 duvidosas; a mediana é 7
chamadas certas por página)."""


class _Chamada(Enum):
    CERTA = "certa"
    DUVIDOSA = "duvidosa"
    """O número só, de 2 algarismos ou mais, depois de letra solta, de algarismo ou do sinal de
    grau ("6 h¹⁴⁸", "0,62¹¹¹"): na linha, tem a cara de um expoente ("r¹²"). E a que abre a linha
    antes de pontuação ("¹¹⁸. No"), que tem a cara do número de uma nota ("¹. Ver")."""


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
    espacos_tirados: int = 0
    """Quantos espaços inventados saíram: a linha com letra espaçada e espaço de verdade."""
    duvidosas: int = 0
    """As chamadas duvidosas que ficaram no texto: só saem na página que tem chamadas certas
    (ADR-0004, "Camada do OCR sobre as figuras e chamada colada")."""


def texto_da_linha(
    caracteres: Sequence[Caractere], tamanho: float, *, com_duvidosas: bool = False
) -> TextoDaLinha:
    """O texto da linha sem as chamadas sobrescritas e sem o espaço inventado no vão da letra.

    A chamada duvidosa só sai com `com_duvidosas`, que a página dá (`pagina_usa_chamadas`); sem
    ele, fica no texto e é contada.
    """
    fora: set[int] = set()
    chamadas: list[str] = []
    duvidosas = 0
    for (inicio, fim), tipo in _chamadas(caracteres, tamanho):
        if tipo is _Chamada.DUVIDOSA and not com_duvidosas:
            duvidosas += 1
            continue
        fora.update(range(inicio, fim))
        chamadas.append(_registro(caracteres, inicio, fim))
    inventados = _espacos_inventados(caracteres, tamanho)
    fora.update(inventados)
    ficam = tuple(c for i, c in enumerate(caracteres) if i not in fora)
    texto = "".join(c.texto for c in ficam)
    return TextoDaLinha(texto, tuple(chamadas), ficam, len(inventados), duvidosas)


def pagina_usa_chamadas(certas: int) -> bool:
    """Se a página, com `certas` chamadas certas, prova as duvidosas (ADR-0004, "Camada do OCR
    sobre as figuras e chamada colada")."""
    return certas >= CHAMADAS_CERTAS_NA_PAGINA


def _chamadas(
    caracteres: Sequence[Caractere], tamanho: float
) -> list[tuple[tuple[int, int], _Chamada]]:
    """(início, fim) de cada trecho sobrescrito que é chamada de referência, e se é certa."""
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
    tipos = [(t, _tipo_da_chamada(caracteres, *t)) for t in aparados if t is not None]
    return [(trecho, tipo) for trecho, tipo in tipos if tipo is not None]


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


def _tipo_da_chamada(caracteres: Sequence[Caractere], inicio: int, fim: int) -> _Chamada | None:
    """Só algarismo, vírgula e traço, no lugar em que a chamada mora; None se é outra coisa."""
    texto = "".join(c.texto for c in caracteres[inicio:fim])
    if _CHAMADA.fullmatch(texto) is None:
        return None
    depois = caracteres[fim].texto if fim < len(caracteres) else ""
    fecha = depois in _PONTUACAO_DEPOIS
    solta = fecha or not depois.strip()
    texto_antes = "".join(c.texto for c in caracteres[:inicio])
    if not texto_antes.strip():
        # A palavra ficou na linha de cima ("¹¹⁸. No"); o isótopo ("¹²⁵I") e o número da nota
        # ("¹ The note") têm letra ou espaço depois.
        return _Chamada.DUVIDOSA if fecha else None
    antes = caracteres[inicio - 1]
    if antes.virtual or not antes.texto.strip():
        # "el dolor ²⁸⁰." e a chamada no fim da linha, que o pdfminer fecha com a quebra; o
        # número solto entre espaços ("dose ⁵ mg") e o isótopo ficam.
        return _Chamada.CERTA if fecha or depois in _FIM_DA_LINHA else None
    if antes.texto in _TRAVESSOES:
        return _Chamada.CERTA if solta else None
    if antes.texto in _PONTUACAO_ANTES or _ANO_ANTES.search(texto_antes):
        return _Chamada.CERTA
    return _colada(texto_antes, texto, solta=solta)


def _colada(texto_antes: str, chamada: str, *, solta: bool) -> _Chamada | None:
    """A chamada colada a palavra, a letra solta, a algarismo ou ao sinal de grau.

    Colada à palavra de 2 letras ou mais que não é unidade, é certa. Colada a letra solta, a
    algarismo ou ao grau, onde também mora o expoente: a lista ou faixa é certa; o número só, de
    2 algarismos ou mais e seguido de espaço, pontuação ou fim, é duvidoso; depois da base 10, e
    com um algarismo só, nunca ("10¹²", "m²", "T10²").
    """
    palavra = _PALAVRA_ANTES.search(texto_antes)
    if palavra is not None and len(palavra.group()) > 1:
        return None if palavra.group() in _UNIDADES else _Chamada.CERTA
    if palavra is None and not (texto_antes[-1].isdigit() or texto_antes[-1] == "\u00b0"):
        return None
    if _LISTA_OU_FAIXA.search(chamada):
        return _Chamada.CERTA
    expoente = _BASE_DEZ.search(texto_antes) is not None
    if solta and not expoente and _DOIS_ALGARISMOS.fullmatch(chamada):
        return _Chamada.DUVIDOSA
    return None


def _registro(caracteres: Sequence[Caractere], inicio: int, fim: int) -> str:
    antes = "".join(c.texto for c in caracteres[:inicio]).rsplit(maxsplit=1)
    chamada = "".join(c.texto for c in caracteres[inicio:fim])
    return f"{antes[-1] if antes else ''}[{chamada}]"


def _espacos_inventados(caracteres: Sequence[Caractere], tamanho: float) -> list[int]:
    """Os espaços do pdfminer cujo vão não passa do vão típico entre as letras da linha, ou que
    é menos da metade do vão do espaço de verdade da linha."""
    limites = [_limite_das_letras(caracteres, tamanho), _limite_do_espaco(caracteres)]
    limite = max((limite for limite in limites if limite is not None), default=None)
    if limite is None:
        return []
    return [
        i
        for i, c in enumerate(caracteres)
        if c.virtual and c.texto == " " and c.x1 - c.x0 <= limite
    ]


def _limite_das_letras(caracteres: Sequence[Caractere], tamanho: float) -> float | None:
    """O vão típico entre letras coladas, mais a folga (Practical: "NATALI E MORY L")."""
    vaos = [
        depois.x0 - antes.x1
        for antes, depois in pairwise(caracteres)
        if _letra(antes) and _letra(depois)
    ]
    if len(vaos) < VAOS_MINIMOS:
        return None
    return median(vaos) + tamanho * FOLGA_DO_VAO


def _limite_do_espaco(caracteres: Sequence[Caractere]) -> float | None:
    """Menos da metade do menor vão de palavra com espaço de verdade, que é caractere do PDF: da
    letra antes dele à letra depois. Na letra espaçada do Bonica, o par apertado ("PA R T O N E")
    e o kerning do número ("CHAPTER 11 0") deixam a regra das letras sem vãos para medir
    (ADR-0004, "Espaço menor que o espaço de verdade"). Vale só se todo espaço inventado da linha
    cabe na régua: com um vão maior, a linha é irregular, e a regra da letra espaçada a lê."""
    vaos: list[float] = []
    fim_da_letra: float | None = None
    espaco_aberto = False
    for caractere in caracteres:
        if _letra(caractere):
            if espaco_aberto and fim_da_letra is not None:
                vaos.append(caractere.x0 - fim_da_letra)
            fim_da_letra, espaco_aberto = caractere.x1, False
        elif not caractere.virtual and caractere.texto == " ":
            espaco_aberto = True
    if not vaos:
        return None
    limite = min(vaos) * FRACAO_DO_ESPACO_DE_VERDADE
    inventados = [c.x1 - c.x0 for c in caracteres if c.virtual and c.texto == " "]
    return limite if all(vao <= limite for vao in inventados) else None


def _letra(caractere: Caractere) -> bool:
    return not caractere.virtual and caractere.texto.strip() != ""


def texto_lido(caracteres: Sequence[Caractere], tamanho: float) -> str:
    """O texto da linha comum (não monoespaçada) como a voz o lê; ver `lido`."""
    return lido(texto_da_linha(caracteres, tamanho), tamanho)


def lido(linha: TextoDaLinha, tamanho: float) -> str:
    """O texto sem chamada e sem espaço inventado e, se nenhum espaço inventado saiu, com a letra
    espaçada juntada ("P A R T E   I", `pagina.juntar_letras_espacadas`). Se saiu, os espaços de
    verdade já separam as palavras: a regra antiga partia o nome com pares apertados ("KAU R KO
    ONER", Practical p. 39)."""
    texto = normalizar_espacos(linha.texto)
    if linha.espacos_tirados:
        return texto
    letras = [Letra(c.texto, c.x0, c.x1) for c in linha.caracteres if _letra(c)]
    return juntar_letras_espacadas(letras, tamanho) or texto
