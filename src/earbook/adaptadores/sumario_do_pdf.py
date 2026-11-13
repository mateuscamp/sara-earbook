# SPDX-License-Identifier: GPL-3.0-or-later
"""O sumário interno do PDF (os marcadores) percorrido com passos contados (ADR-0004, "Capítulos
pelo sumário interno do PDF").

O PDF é entrada não confiável, e o `get_outlines` do pdfminer segue referência sem limite: um
`/Outlines` que aponta para um objeto que aponta para si mesmo não voltava nunca, e 991 itens
irmãos (Bonica) estouravam a recursão. Aqui o percurso é nosso: cada item é visitado uma vez, e a
árvore de nomes de destino, também. Este módulo não importa o pdfminer; quem segue a referência é
o `Leitor`, que `adaptadores/pdf.py` implementa.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from earbook.dominio.segmento import normalizar_espacos
from earbook.dominio.sumario_interno import ItemDoSumario

ITENS_MAXIMOS = 100_000
"""O Miller tem 7.079 itens no sumário e outros tantos nomes de destino."""
PASSOS_DO_DESTINO = 8
"""Quantos nomes e dicionários se seguem até a página de um item: o caminho mais longo medido
tem 3 (ação, nome, lista)."""


class Leitor(Protocol):
    """O que este módulo precisa da biblioteca de PDF, sem conhecê-la."""

    def seguir(self, valor: object) -> object:
        """O valor depois de seguir a referência, por um número fixo de passos; None se ela não
        leva a nada."""
        ...

    def objeto(self, valor: object) -> int | None:
        """O número do objeto, se o valor é uma referência; None se não é."""
        ...

    def texto(self, valor: object) -> str:
        """O texto de uma cadeia do PDF; vazio se o valor não é cadeia."""
        ...


def itens_do_sumario(
    catalogo: object, leitor: Leitor, paginas: Mapping[int, int]
) -> tuple[ItemDoSumario, ...]:
    """Os itens do sumário, na ordem do livro, com o nível, o título e a página (`paginas`: do
    número do objeto da página ao número dela). O item sem título ou cujo destino não leva a uma
    página fica de fora; o item já visitado fecha o círculo, e o percurso acaba ali."""
    raiz = leitor.seguir(_valor(catalogo, "Outlines"))
    destinos: dict[bytes, object] | None = None
    itens: list[ItemDoSumario] = []
    vistos: set[int] = set()
    pilha: list[tuple[object, int]] = [(_valor(raiz, "First"), 1)]
    while pilha and len(vistos) < ITENS_MAXIMOS:
        referencia, nivel = pilha.pop()
        objeto, entrada = leitor.objeto(referencia), leitor.seguir(referencia)
        # O item é sempre objeto indireto: é o número dele que prova que o percurso acaba.
        if objeto is None or objeto in vistos or not _e_dicionario(entrada):
            continue
        vistos.add(objeto)
        # O irmão espera na pilha enquanto os filhos são lidos: a ordem é a do livro.
        pilha += [(_valor(entrada, "Next"), nivel), (_valor(entrada, "First"), nivel + 1)]
        alvo = _alvo(entrada, leitor)
        if destinos is None and isinstance(alvo, (bytes, str)):
            destinos = _destinos_com_nome(catalogo, leitor)
        pagina = _pagina(alvo, leitor, destinos or {}, paginas)
        titulo = normalizar_espacos(leitor.texto(leitor.seguir(_valor(entrada, "Title"))))
        if pagina is not None and titulo:
            itens.append(ItemDoSumario(nivel, titulo, pagina))
    return tuple(itens)


def _alvo(entrada: object, leitor: Leitor) -> object:
    """O destino do item: o direto (`/Dest`) ou o da ação (`/A << /S /GoTo /D … >>`)."""
    direto = leitor.seguir(_valor(entrada, "Dest"))
    if direto is not None:
        return direto
    return leitor.seguir(_valor(leitor.seguir(_valor(entrada, "A")), "D"))


def _pagina(
    alvo: object, leitor: Leitor, destinos: Mapping[bytes, object], paginas: Mapping[int, int]
) -> int | None:
    """A página do destino: a lista `[página /Fit]`, o nome que leva a ela ou o dicionário com
    `/D`."""
    for _ in range(PASSOS_DO_DESTINO):
        if isinstance(alvo, (bytes, str)):
            alvo = leitor.seguir(destinos.get(_chave(alvo)))
        elif isinstance(alvo, dict):
            alvo = leitor.seguir(_valor(alvo, "D"))  # pyright: ignore[reportUnknownArgumentType]  # motivo: dicionário cru do PDF; `_valor` só lê a chave
        else:
            break
    primeiro = alvo[0] if isinstance(alvo, list) and alvo else None  # pyright: ignore[reportUnknownVariableType]  # motivo: lista crua do PDF; o `Leitor` valida a referência
    objeto = leitor.objeto(primeiro)  # pyright: ignore[reportUnknownArgumentType]  # motivo: idem
    return paginas.get(objeto) if objeto is not None else None


def _destinos_com_nome(catalogo: object, leitor: Leitor) -> dict[bytes, object]:
    """Os destinos com nome do PDF: a árvore de nomes (`/Names /Dests`), percorrida uma vez, com
    cada nó visitado uma vez só, e o dicionário do PDF 1.1 (`/Dests`)."""
    destinos: dict[bytes, object] = {}
    vistos: set[int] = set()
    pilha: list[object] = [_valor(leitor.seguir(_valor(catalogo, "Names")), "Dests")]
    while pilha and len(vistos) < ITENS_MAXIMOS and len(destinos) < ITENS_MAXIMOS:
        referencia = pilha.pop()
        objeto, no = leitor.objeto(referencia), leitor.seguir(referencia)
        if objeto in vistos:
            continue
        if objeto is not None:
            vistos.add(objeto)
        pares = _lista(leitor, _valor(no, "Names"))
        for chave, valor in zip(pares[::2], pares[1::2], strict=False):
            nome = leitor.seguir(chave)
            if isinstance(nome, bytes):
                _ = destinos.setdefault(nome, valor)
        # O nó filho é objeto indireto: sem número, não há como provar que a árvore acaba.
        filhos = _lista(leitor, _valor(no, "Kids"))
        pilha += [filho for filho in filhos if leitor.objeto(filho) is not None]
    return _com_os_do_pdf_1_1(destinos, leitor.seguir(_valor(catalogo, "Dests")))


def _com_os_do_pdf_1_1(destinos: dict[bytes, object], antigos: object) -> dict[bytes, object]:
    """Mais os destinos do dicionário `/Dests` do catálogo, a forma do PDF 1.1, cuja chave é nome
    e não cadeia; o da árvore de nomes ganha."""
    if not isinstance(antigos, dict):
        return destinos
    for chave in antigos:  # pyright: ignore[reportUnknownVariableType]  # motivo: dicionário cru do PDF; o isinstance a seguir valida a chave
        if isinstance(chave, str):
            _ = destinos.setdefault(_chave(chave), _valor(antigos, chave))  # pyright: ignore[reportUnknownArgumentType]  # motivo: dicionário cru do PDF; `_valor` só lê a chave
    return destinos


def _lista(leitor: Leitor, valor: object) -> list[object]:
    seguido = leitor.seguir(valor)
    return list(seguido) if isinstance(seguido, list) else []  # pyright: ignore[reportUnknownArgumentType]  # motivo: lista crua do PDF; cada elemento é validado por quem a usa


def _e_dicionario(valor: object) -> bool:
    """Sem estreitar o tipo: o dicionário cru do PDF só é lido por `_valor`."""
    return isinstance(valor, dict)


def _chave(nome: bytes | str) -> bytes:
    return nome if isinstance(nome, bytes) else nome.encode("latin-1", "replace")


def _valor(dicionario: object, chave: str) -> object:
    if not isinstance(dicionario, dict):
        return None
    return dicionario.get(chave)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]  # motivo: dicionário cru do PDF; quem chama valida o valor
