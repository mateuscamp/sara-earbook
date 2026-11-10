# SPDX-License-Identifier: GPL-3.0-or-later
"""A adaptação por lote (ADR-0009): o que o Python pede e o que o agente responde.

Na tradução, um segmento de entrada é um de saída (ADR-0006). Na adaptação, N viram M: o
Quadro de 15 segmentos vira três parágrafos, a lista vira frase, o destaque repetido sai. A
resposta é uma lista de grupos de fontes vizinhas, e o `conferir` cobra a fidelidade de cada um.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from earbook.dominio.segmento import Papel, Segmento, primeira_letra
from earbook.dominio.traducao import Pedido, ainda_sem_pedido, lotes_numerados, mesmo_idioma

IDIOMA_DA_ADAPTACAO = "pt"
TETO_DO_LOTE = 2
"""Vezes o limite de palavras que o lote pode chegar, para não partir a frase."""
# Fecha frase: o ponto, a exclamação, a interrogação, as reticências e os dois-pontos, com
# aspa ou parêntese depois. O corte do lote só cai entre frases (ADR-0009).
_FECHA_FRASE = re.compile('[.!?\u2026:]["\u201d\u2019)]*$')


class TipoDoGrupo(StrEnum):
    TEXTO = "texto"
    """O que se ouve no lugar das fontes: um ou mais parágrafos."""
    IGUAL = "igual"
    """O segmento fica como está em `limpos/`: custa só o ID."""
    DESCARTE = "descarte"
    """Sai do áudio, com um motivo que o `conferir` confere."""


class MotivoDoDescarte(StrEnum):
    REPETIDO = "repetido"
    """O destaque e o gêmeo: cada número e termo dele está nos grupos vizinhos."""
    ROTULO = "rotulo"
    """"Quadro 27.1", "Tabela 19.1", o número do capítulo repetido."""
    DECISAO = "decisao"
    """O que `decisoes.md` manda tirar: "decisao: <seção>"."""


@dataclass(frozen=True)
class Omitido:
    """O termo raro das fontes que o grupo deixou de fora de propósito."""

    termo: str
    motivo: str


@dataclass(frozen=True)
class Correcao:
    """O erro inequívoco do PDF que o grupo corrigiu, com a página que o prova."""

    de: str
    para: str
    pagina: int


@dataclass(frozen=True)
class Grupo:
    fontes: tuple[str, ...]
    tipo: TipoDoGrupo
    texto: tuple[str, ...] = ()
    descarte: str = ""
    """Como o agente escreveu: "repetido", "rotulo" ou "decisao: <seção>"."""
    omitidos: tuple[Omitido, ...] = ()
    corrigidos: tuple[Correcao, ...] = ()


@dataclass(frozen=True)
class RespostaDaAdaptacao:
    """O que o agente gravou para o lote de mesmo nome."""

    lote: str
    grupos: tuple[Grupo, ...]


def pode_adaptar(idioma: str) -> bool:
    """Só o livro em português: adaptar depois de traduzir fica fora do ADR-0009."""
    return mesmo_idioma(idioma, IDIOMA_DA_ADAPTACAO)


def pedidos_da_adaptacao(
    capitulo: str,
    limpos: Sequence[Segmento],
    pedidos: Sequence[Pedido],
    palavras: int,
    respondidos: Sequence[str] = (),
) -> tuple[Pedido, ...]:
    """Os lotes como na tradução, mas cortados onde o grupo não precisa atravessar."""
    lotes = em_lotes_por_frase(ainda_sem_pedido(limpos, pedidos), palavras)
    return lotes_numerados(capitulo, lotes, [*(p.lote for p in pedidos), *respondidos])


def em_lotes_por_frase(segmentos: Sequence[Segmento], palavras: int) -> list[tuple[Segmento, ...]]:
    """O grupo não atravessa lote (ADR-0009): o lote termina antes de um título ou entre duas
    frases, para que o destaque e a frase que ele parte caiam juntos."""
    lotes: list[tuple[Segmento, ...]] = []
    resto = list(segmentos)
    while resto:
        fim = _corte(resto, palavras)
        lotes.append(tuple(resto[:fim]))
        resto = resto[fim:]
    return lotes


def _corte(segmentos: Sequence[Segmento], palavras: int) -> int:
    """Quantos segmentos vão no lote: antes do título entre a metade e o limite; sem ele,
    antes da frase que abre ali; sem nenhuma, o primeiro corte seguro depois do limite."""
    acumulado = [0]
    for segmento in segmentos:
        acumulado.append(acumulado[-1] + len(segmento.texto.split()))
    cabem = max(1, sum(1 for total in acumulado[1:] if total <= palavras))
    if cabem >= len(segmentos):
        return len(segmentos)
    candidatos = [j for j in range(cabem, 0, -1) if acumulado[j] * 2 >= palavras]
    for seguro in (_antes_de_titulo, _entre_frases):
        if escolhido := next((j for j in candidatos if seguro(segmentos, j)), None):
            return escolhido
    # Para a frente, até 2 vezes o limite: a lista sem ponto e sem título faria um lote do
    # capítulo inteiro, e a falha no meio perderia tudo (A5 da auditoria).
    teto = TETO_DO_LOTE * palavras
    depois = [j for j in range(cabem + 1, len(segmentos)) if acumulado[j] <= teto]
    if (seguro := next((j for j in depois if _entre_frases(segmentos, j)), None)) is not None:
        return seguro
    return len(segmentos) if acumulado[-1] <= teto else cabem


def _antes_de_titulo(segmentos: Sequence[Segmento], j: int) -> bool:
    return segmentos[j].papel is Papel.TITULO


def _entre_frases(segmentos: Sequence[Segmento], j: int) -> bool:
    """O anterior fecha frase e este não abre em minúscula: nada a emendar entre os dois."""
    if _antes_de_titulo(segmentos, j):
        return True
    fecha = _FECHA_FRASE.search(segmentos[j - 1].texto.rstrip()) is not None
    return fecha and not primeira_letra(segmentos[j].texto).islower()


@dataclass(frozen=True)
class TextosDaAdaptacao:
    """O que o `montar` põe no livro: por capítulo, o segmento de cada grupo que fica; por ID,
    os parágrafos que vêm depois do primeiro; e os IDs que algum grupo cobre."""

    finais: Mapping[str, tuple[Segmento, ...]]
    seguintes: Mapping[str, tuple[str, ...]]
    cobertos: frozenset[str]


def textos_da_adaptacao(
    limpos: Mapping[str, Sequence[Segmento]], respostas: Sequence[RespostaDaAdaptacao]
) -> TextosDaAdaptacao:
    """O grupo com texto fica no primeiro ID, com o primeiro parágrafo, e os outros IDs saem;
    o `igual` fica como está; o descarte sai. O ID sem grupo também sai: o `conferir` o recusa
    no livro inteiro, e a amostra o deixa de fora."""
    textos: dict[str, str] = {}
    seguintes: dict[str, tuple[str, ...]] = {}
    por_id = {s.id: s for lista in limpos.values() for s in lista}
    for grupo in (grupo for resposta in respostas for grupo in resposta.grupos):
        if grupo.tipo is TipoDoGrupo.TEXTO and grupo.texto:
            textos[grupo.fontes[0]] = grupo.texto[0]
            seguintes[grupo.fontes[0]] = grupo.texto[1:]
        elif grupo.tipo is TipoDoGrupo.IGUAL:
            textos.update({id_: por_id[id_].texto for id_ in grupo.fontes if id_ in por_id})
    finais = {
        capitulo: tuple(replace(s, texto=textos[s.id]) for s in lista if s.id in textos)
        for capitulo, lista in limpos.items()
    }
    cobertos = frozenset(id_ for r in respostas for grupo in r.grupos for id_ in grupo.fontes)
    return TextosDaAdaptacao(finais, {k: v for k, v in seguintes.items() if v}, cobertos)
