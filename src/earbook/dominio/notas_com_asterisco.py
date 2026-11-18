# SPDX-License-Identifier: GPL-3.0-or-later
"""A nota que o livro marca com asterisco (ADR-0004, "Romance convertido pelo Calibre").

No Kafka à beira-mar (PDF do Calibre), a chamada vem colada à palavra ou à pontuação, no tamanho
do corpo ("Report*", "“Owan-y ama”.**", "shamisen,***", "pólo!”****"), e a nota fica no pé da
última página do capítulo, na mesma letra, aberta pelos mesmos asteriscos ("* Incidente Morro da
Tigela, 1944: Relatório (N. da T.)"). A letra não separa a nota do texto: a chamada a prova.

A nota é a linha que começa pelos asteriscos de uma chamada que veio antes e ainda não tem nota,
e vai até o fim da página, até a nota seguinte, até a linha que volta ao alto da página (a da
outra coluna) ou até a linha de outra letra (o corpo depois da nota da tabela). A chamada sai
da frase, e o marcador sai da nota: a voz não lê "asterisco" (ADR-0011, decisão 3 do Mateus:
"nota '*' no fim do capítulo, sem o marcador"). A chamada sem nota fica no texto.

O asterisco solto entre espaços ("na cidade de **", "rua ** do bairro") e o colado ao algarismo
("5* anos", "194*") são a censura do próprio livro, e ficam. A linha que começa pela censura
("** à época do incidente", quando "Escola Municipal" fecha a linha de cima) não é nota: nenhuma
chamada de dois asteriscos veio antes dela.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass, replace

from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginacao import LinhaRemovida

MOTIVO_DA_CHAMADA_DE_ASTERISCO = "chamada de nota com asterisco"
PAGINAS_ATE_A_NOTA = 15
"""A nota fica no fim do capítulo da chamada: no Kafka, a até 5 páginas dela, em capítulos de até
12. A chamada mais longe que isso não prova a linha que começa por asteriscos (revisão)."""
VARIACAO_DA_LETRA = 0.5
"""Em pontos: a nota continua só na letra da linha que a abre. A nota da tabela do Practical, em
letra menor no meio da página, levava o corpo de baixo junto (revisão da regressão)."""
# Colada a letra ou à pontuação que fecha a palavra, e seguida de espaço, pontuação ou fim.
_CHAMADA = re.compile(r"(?:(?<=[^\W\d_])|(?<=[.,;:!?)\u201d\u2019\"']))\*{1,4}(?![\w*])")
_NOTA = re.compile(r"(\*{1,4})\s+(?=\S)")

type _Lugar = tuple[int, int]
"""(posição da página, posição da linha na página)."""


@dataclass(frozen=True)
class NotasComAsterisco:
    paginas: tuple[Pagina, ...]
    chamadas: tuple[LinhaRemovida, ...]
    """Cada chamada tirada, com a palavra antes e os asteriscos entre colchetes: "Report[*]"."""


@dataclass(frozen=True)
class _Chamada:
    lugar: _Lugar
    inicio: int
    fim: int


def notas_com_asterisco(paginas: Sequence[Pagina]) -> NotasComAsterisco:
    """As páginas com a chamada provada fora da frase e a nota dela marcada, e o registro de cada
    chamada tirada."""
    chamadas, aberturas = _parear(paginas)
    if not chamadas:
        return NotasComAsterisco(tuple(paginas), ())
    por_linha: defaultdict[_Lugar, list[_Chamada]] = defaultdict(list)
    for chamada in chamadas:
        por_linha[chamada.lugar].append(chamada)
    feitas: list[Pagina] = []
    for i, pagina in enumerate(paginas):
        nota: Linha | None = None
        linhas: list[Linha] = []
        for j, linha in enumerate(pagina.linhas):
            abre = (i, j) in aberturas
            if abre:
                nota = linha
            elif nota is not None and not _continua(nota, pagina.linhas[j - 1], linha):
                nota = None
            linhas.append(_linha_feita(linha, por_linha[i, j], abre=abre, nota=nota is not None))
        feitas.append(Pagina(pagina.numero, tuple(linhas)))
    registro = tuple(_registro(paginas, chamada) for chamada in chamadas)
    return NotasComAsterisco(tuple(feitas), registro)


def _continua(abertura: Linha, anterior: Linha, linha: Linha) -> bool:
    """A linha segue a nota: na letra dela e sem voltar ao alto da página. A leitura que sobe é a
    outra coluna, e a nota do pé da primeira acaba ali (Dalgalarrondo, p. 151); a letra que muda
    é o corpo depois da nota da tabela (Practical). Revisão da regressão."""
    na_letra = abs(linha.tamanho - abertura.tamanho) <= VARIACAO_DA_LETRA
    return na_letra and linha.topo >= anterior.topo


def _parear(paginas: Sequence[Pagina]) -> tuple[list[_Chamada], set[_Lugar]]:
    """As chamadas que têm nota e onde cada nota abre: a nota consome a chamada mais antiga, ainda
    sem nota, com o mesmo número de asteriscos."""
    pendentes: defaultdict[int, deque[_Chamada]] = defaultdict(deque)
    provadas: list[_Chamada] = []
    aberturas: set[_Lugar] = set()
    for i, pagina in enumerate(paginas):
        for j, linha in enumerate(pagina.linhas):
            nota = _NOTA.match(linha.texto)
            fila = pendentes[len(nota.group(1))] if nota is not None else deque[_Chamada]()
            while fila and pagina.numero - paginas[fila[0].lugar[0]].numero > PAGINAS_ATE_A_NOTA:
                _ = fila.popleft()
            if fila:
                provadas.append(fila.popleft())
                aberturas.add((i, j))
                continue
            for achada in _CHAMADA.finditer(linha.texto):
                chamada = _Chamada((i, j), achada.start(), achada.end())
                pendentes[achada.end() - achada.start()].append(chamada)
    return provadas, aberturas


def _linha_feita(linha: Linha, chamadas: Sequence[_Chamada], *, abre: bool, nota: bool) -> Linha:
    texto = linha.texto
    for chamada in sorted(chamadas, key=lambda c: c.inicio, reverse=True):
        texto = texto[: chamada.inicio] + texto[chamada.fim :]
    if abre:
        texto = _NOTA.sub("", texto, count=1)
    return replace(linha, texto=texto, nota=nota, abre_nota=abre)


def _registro(paginas: Sequence[Pagina], chamada: _Chamada) -> LinhaRemovida:
    i, j = chamada.lugar
    texto = paginas[i].linhas[j].texto
    antes = texto[: chamada.inicio].rsplit(maxsplit=1)
    asteriscos = texto[chamada.inicio : chamada.fim]
    palavra = antes[-1] if antes else ""
    return LinhaRemovida(
        paginas[i].numero, MOTIVO_DA_CHAMADA_DE_ASTERISCO, f"{palavra}[{asteriscos}]"
    )
