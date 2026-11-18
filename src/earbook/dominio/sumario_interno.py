# SPDX-License-Identifier: GPL-3.0-or-later
"""O sumário interno do PDF (os marcadores) como fonte dos capítulos (ADR-0004, "Capítulos pelo
sumário interno do PDF").

O adaptador de PDF lê os itens; aqui se decide se eles servem e onde cada capítulo abre.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace

from earbook.dominio.pagina import Linha, Pagina

ROTULOS_MINIMOS = 3
"""O nível do capítulo tem o rótulo em 3 páginas ou mais, como o rótulo no título (`capitulos`)."""
# "Capítulo 1. …", "Capitulo 1_ …", "capitulo 4_ …" (Miller, sem acento e sem maiúscula), "CHAPTER
# 1: …": a palavra e o número, sem olhar a caixa. "Capítulos 1 a 3" não é rótulo.
_ROTULO = re.compile(r"\W*(?:cap[ií]tulo|chapter)\s*\d+(?!\w)", re.IGNORECASE)
_TRACOS = re.compile("[\u2010-\u2015]")


@dataclass(frozen=True)
class ItemDoSumario:
    nivel: int
    """1 para o item de fora; os filhos dele têm 2, e assim por diante."""
    titulo: str
    pagina: int
    """A página do PDF para onde o item leva, a partir de 1."""


@dataclass(frozen=True)
class Abertura:
    """Onde um capítulo abre, e o nome que o sumário interno dá a ele."""

    pagina: int
    nome: str


def aberturas_de_capitulo(itens: Sequence[ItemDoSumario]) -> tuple[Abertura, ...]:
    """As aberturas de capítulo que o sumário interno dá, em ordem de página; vazio se ele não
    serve.

    Todo item do nível do capítulo e dos níveis acima dele abre capítulo: o prefácio, a parte e o
    anexo são irmãos do capítulo. Com mais de um item na mesma página (Miller: "Capitulo 1_ …" no
    nível 1 e "Capítulo 1 - …" no 2), o nome é o do último.
    """
    nivel = _nivel_do_capitulo(itens)
    if nivel is None:
        return ()
    nomes: dict[int, str] = {}
    for item in itens:
        if item.nivel <= nivel:
            nomes[item.pagina] = item.titulo
    return tuple(Abertura(pagina, nomes[pagina]) for pagina in sorted(nomes))


def _nivel_do_capitulo(itens: Sequence[ItemDoSumario]) -> int | None:
    """O nível mais fundo em que a maioria dos itens começa pelo rótulo de capítulo, em 3 páginas
    ou mais; None se nenhum.

    O sumário sem rótulo (Practical: "1 History…") e o plano, com capítulo e seção no mesmo nível
    (Bonica), não dizem qual item é capítulo, e não servem.
    """
    por_nivel: defaultdict[int, list[ItemDoSumario]] = defaultdict(list)
    for item in itens:
        por_nivel[item.nivel].append(item)
    for nivel in sorted(por_nivel, reverse=True):
        do_nivel = por_nivel[nivel]
        com_rotulo = [item for item in do_nivel if _ROTULO.match(item.titulo)]
        paginas = {item.pagina for item in com_rotulo}
        if len(paginas) >= ROTULOS_MINIMOS and len(com_rotulo) * 2 > len(do_nivel):
            return nivel
    return None


def marcar_nomes_dos_capitulos(
    paginas: Sequence[Pagina], aberturas: Sequence[Abertura]
) -> tuple[Pagina, ...]:
    """As páginas com a linha que repete o nome da abertura, na página dela, marcada como nome do
    capítulo: o título, mesmo no tamanho do corpo (ADR-0004, "Romance convertido pelo Calibre").

    A linha inteira, e não o começo dela: "Capítulo 2 conta…" é a frase que cita o capítulo. O
    traço não conta, nem o espaço: a meia-risca do livro é o hífen do sumário ("Prólogo - Um
    Menino…").
    """
    nomes: defaultdict[int, set[str]] = defaultdict(set)
    for abertura in aberturas:
        nomes[abertura.pagina].add(_comparavel(abertura.nome))
    return tuple(_com_o_nome(pagina, nomes[pagina.numero]) for pagina in paginas)


def _com_o_nome(pagina: Pagina, nomes: set[str]) -> Pagina:
    """A página com a primeira linha de cada nome marcada; a página sem abertura volta como veio.

    Só a primeira: o rodapé da O'Reilly repete o nome da seção na página que ela abre (Hard Parts,
    "Introducing the Sysops Squad Saga"), e é rodapé (revisão da regressão).
    """
    if not nomes:
        return pagina
    faltam = set(nomes)
    linhas: list[Linha] = []
    for linha in pagina.linhas:
        nome = _comparavel(linha.texto)
        primeira = nome in faltam
        faltam.discard(nome)
        linhas.append(replace(linha, nome_do_capitulo=True) if primeira else linha)
    return Pagina(pagina.numero, tuple(linhas))


def _comparavel(texto: str) -> str:
    return " ".join(_TRACOS.sub("-", texto).casefold().split())
