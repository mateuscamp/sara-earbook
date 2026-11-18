# SPDX-License-Identifier: GPL-3.0-or-later
"""O espaço inventado depois da letra larga (ADR-0004, "Romance convertido pelo Calibre").

No Kafka à beira-mar (PDF do Calibre), o Q do negrito avança 1,33 pt além da largura que a fonte
declara, e o y do regular, 0,75 pt. O pdfminer põe espaço onde o vão passa de uma fração da
letra, e o PDF não tem espaço ali: "Q uando", "SQ -118", "Toy ama", "Ky oto". O vão é o da
largura errada da letra, o mesmo em toda ocorrência; na linha, ele passa às vezes do espaço de
verdade mais estreito (o do Q chega a 1,33 vez), e só o livro inteiro o separa do espaço de
palavra.

A prova é por fonte e por letra, só nas linhas que separam as palavras com o caractere de espaço
(`caracteres.espacos_entre_caracteres`): o espaço inventado depois da letra, em
`OCORRENCIAS_MINIMAS` linhas ou mais, quase sempre com o mesmo vão, a menos de `VARIACAO_DO_VAO`
da mediana. Só a letra: o algarismo da coluna de tabela alinhada também tem vão constante. O
espaço de palavra que o PDF não gravou muda com a linha justificada, e a letra solta de verdade
("série B da", "letra G do") tem o caractere de espaço depois dela.

O vão conta só abaixo de `FRACAO_DA_LETRA` do tamanho da linha: o de um espaço ou mais, mesmo
constante, é espaço de verdade sem o caractere. No Miller, o número de página do cabeçalho fica a
11,36 pt da última letra, em toda página; no Manica, "( B )" da legenda deixa 0,32 do tamanho; no
Practical, "to -17.4" da tabela, 0,28. O Q do Kafka fica em 0,22, e o y, em 0,125.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from statistics import median

from earbook.dominio.pagina import EspacoInventado, Linha, Pagina

OCORRENCIAS_MINIMAS = 3
VARIACAO_DO_VAO = 0.05
"""Em pontos, em volta da mediana: no Kafka, o vão do Q é 1,33 e o do y, 0,75."""
FRACAO_DA_LETRA = 0.25
"""O espaço de palavra do Times, em fração do tamanho da letra; o vão desse tamanho ou maior é o de
um espaço (revisão da regressão: Miller, Manica, Practical, Bonica)."""
FRACAO_NA_FAIXA = 0.8
"""Dos espaços inventados depois da letra, os que ficam na faixa da mediana: o espaço de palavra
que o PDF não gravou, fora dela, não derruba a prova, e fica (revisão)."""

type _Chave = tuple[str, str]
"""(fonte, letra)."""


@dataclass(frozen=True)
class LetraLarga:
    fonte: str
    letra: str
    vao: float
    """A mediana do vão medido depois dela."""
    espacos: int
    """Quantos espaços inventados saíram depois dela."""


@dataclass(frozen=True)
class LetrasLargas:
    paginas: tuple[Pagina, ...]
    letras: tuple[LetraLarga, ...]

    @property
    def tirados(self) -> int:
        return sum(letra.espacos for letra in self.letras)


def tirar_espacos_da_letra_larga(paginas: Sequence[Pagina]) -> LetrasLargas:
    """As páginas sem o espaço inventado depois da letra larga, e as letras provadas."""
    vaos: defaultdict[_Chave, list[float]] = defaultdict(list)
    for pagina in paginas:
        for linha in pagina.linhas:
            for espaco in linha.espacos_inventados:
                if _estreito(espaco, linha):
                    vaos[espaco.fonte, espaco.letra].append(espaco.vao)
    # Só a letra: a coluna de tabela alinhada tem o mesmo vão depois do algarismo (revisão).
    largas = {
        chave: median(lista)
        for chave, lista in vaos.items()
        if chave[1].isalpha() and _provada(lista)
    }
    feitas = tuple(
        Pagina(pagina.numero, tuple(_sem_os_espacos(linha, largas) for linha in pagina.linhas))
        for pagina in paginas
    )
    letras = tuple(
        LetraLarga(fonte, letra, vao, sum(_na_faixa(v, vao) for v in vaos[fonte, letra]))
        for (fonte, letra), vao in sorted(largas.items())
    )
    return LetrasLargas(feitas, letras)


def _provada(vaos: Sequence[float]) -> bool:
    """Vãos bastantes, quase todos na faixa da mediana."""
    na_faixa = sum(_na_faixa(vao, median(vaos)) for vao in vaos)
    return na_faixa >= OCORRENCIAS_MINIMAS and na_faixa >= FRACAO_NA_FAIXA * len(vaos)


def _estreito(espaco: EspacoInventado, linha: Linha) -> bool:
    """O vão menor que um espaço de palavra, na letra da linha."""
    return espaco.vao < FRACAO_DA_LETRA * linha.tamanho


def _na_faixa(vao: float, tipico: float) -> bool:
    return abs(vao - tipico) <= VARIACAO_DO_VAO


def _sem_os_espacos(linha: Linha, largas: dict[_Chave, float]) -> Linha:
    """A linha sem os espaços das letras largas na faixa do vão delas; a posição dos outros perde
    o sentido e some."""
    if not linha.espacos_inventados:
        return linha
    texto = linha.texto
    for espaco in sorted(linha.espacos_inventados, key=_posicao, reverse=True):
        tipico = largas.get((espaco.fonte, espaco.letra))
        # O PDF é entrada não confiável: a posição fora do texto não derruba a importação.
        no_espaco = texto[espaco.posicao : espaco.posicao + 1] == " "
        largo = tipico is not None and _na_faixa(espaco.vao, tipico) and _estreito(espaco, linha)
        if largo and no_espaco:
            texto = texto[: espaco.posicao] + texto[espaco.posicao + 1 :]
    return replace(linha, texto=texto, espacos_inventados=())


def _posicao(espaco: EspacoInventado) -> int:
    return espaco.posicao
