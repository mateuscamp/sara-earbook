# SPDX-License-Identifier: GPL-3.0-or-later
"""Comando `adaptar`: exporta o que falta adaptar e diz onde gravar a resposta (ADR-0009).

O Python nunca chama o LLM (ADR-0001). Quem adapta é o Claude Code, um subagente por
capítulo, com as instruções de `.claude/agents/adaptador.md`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.dominio.adaptacao import RespostaDaAdaptacao, pedidos_da_adaptacao, pode_adaptar
from earbook.dominio.segmento import Segmento
from earbook.dominio.siglas import siglas_candidatas
from earbook.dominio.traducao import PALAVRAS_POR_LOTE, Pedido, capitulo_do_lote

# ADR-0009: as decisões de gosto do livro moram aqui, e não no brief de cada adaptador.
MODELO_DAS_DECISOES = """# Decisões do livro

A sessão escreve, a partir das decisões do Mateus; todo adaptador lê antes do primeiro lote
(ADR-0009). Seção vazia: vale a regra do `adaptador.md`.

## PDF de origem

## Citação

## Sigla

## Lista

## Quadro e Tabela

## Questões de revisão

## Semiotécnica

## Epígrafe

## Ortografia

## O que sai do áudio
"""


class AdaptacaoSoEmPortuguesError(ValueError):
    pass


@dataclass(frozen=True)
class CapituloNaAdaptacao:
    capitulo: str
    segmentos: int
    adaptados: int
    """Os segmentos que já estão num grupo de alguma resposta."""
    pendentes: tuple[str, ...]
    """Os lotes pedidos que ainda não têm resposta."""


@dataclass(frozen=True)
class ExportacaoDaAdaptacao:
    novos: int
    """Lotes pedidos agora; rodar de novo não refaz os que já existem."""
    capitulos: tuple[CapituloNaAdaptacao, ...]
    siglas: int
    """Siglas fora do glossário, em `caminho_das_siglas`."""
    pedidos: Path
    resposta: Path
    """O modelo do caminho da resposta, com `<lote>` no lugar do nome do lote."""
    glossario: Path
    caminho_das_siglas: Path
    decisoes: Path
    palavras_pendentes: Mapping[str, int]
    """Por capítulo, as palavras ainda sem adaptação: a conta da divisão e do custo."""


def adaptar(pasta: Path, palavras: int = PALAVRAS_POR_LOTE) -> ExportacaoDaAdaptacao:
    """Grava os pedidos do que ainda não foi pedido e as siglas candidatas. Recusa o livro que
    não está em português: adaptar depois de traduzir fica fora do ADR-0009."""
    if not pode_adaptar(idioma := trabalho.ler_idioma(pasta)):
        mensagem = f"{pasta}: o livro está em {idioma!r}; o adaptar é só para livro em português"
        raise AdaptacaoSoEmPortuguesError(mensagem)
    trabalho.criar_pastas_da_adaptacao(pasta)
    limpos = {c.id: trabalho.ler_limpos(pasta, c.id) for c in trabalho.ler_capitulos(pasta)}
    pedidos = list(trabalho.ler_pedidos_da_adaptacao(pasta))
    respostas = trabalho.ler_adaptados(pasta)
    novos = _pedir(pasta, limpos, pedidos, [r.lote for r in respostas], palavras)
    siglas = siglas_candidatas(
        (s for lista in limpos.values() for s in lista), trabalho.ler_glossario(pasta)
    )
    trabalho.gravar_siglas(pasta, siglas)
    trabalho.gravar_decisoes_se_faltar(pasta, MODELO_DAS_DECISOES)
    return ExportacaoDaAdaptacao(
        len(novos),
        _estado(limpos, [*pedidos, *novos], respostas),
        len(siglas),
        trabalho.pasta_para_adaptar(pasta),
        trabalho.caminho_do_adaptado(pasta, "<lote>"),
        trabalho.caminho_do_glossario(pasta),
        trabalho.caminho_das_siglas(pasta),
        trabalho.caminho_das_decisoes(pasta),
        _palavras_pendentes(limpos, respostas),
    )


def _pedir(
    pasta: Path,
    limpos: Mapping[str, Sequence[Segmento]],
    pedidos: Sequence[Pedido],
    respondidos: Sequence[str],
    palavras: int,
) -> list[Pedido]:
    novos = [
        pedido
        for capitulo, segmentos in limpos.items()
        for pedido in pedidos_da_adaptacao(
            capitulo, segmentos, _do_capitulo(pedidos, capitulo), palavras, respondidos
        )
    ]
    for pedido in novos:
        trabalho.gravar_pedido_da_adaptacao(pasta, pedido)
    return novos


def _do_capitulo(pedidos: Sequence[Pedido], capitulo: str) -> list[Pedido]:
    return [pedido for pedido in pedidos if capitulo_do_lote(pedido.lote) == capitulo]


def _adaptados(respostas: Sequence[RespostaDaAdaptacao]) -> set[str]:
    return {id_ for resposta in respostas for grupo in resposta.grupos for id_ in grupo.fontes}


def _palavras_pendentes(
    limpos: Mapping[str, Sequence[Segmento]], respostas: Sequence[RespostaDaAdaptacao]
) -> dict[str, int]:
    adaptados = _adaptados(respostas)
    return {
        capitulo: sum(len(s.texto.split()) for s in segmentos if s.id not in adaptados)
        for capitulo, segmentos in limpos.items()
    }


def _estado(
    limpos: Mapping[str, Sequence[Segmento]],
    pedidos: Sequence[Pedido],
    respostas: Sequence[RespostaDaAdaptacao],
) -> tuple[CapituloNaAdaptacao, ...]:
    """Só os capítulos com texto: a capa sem segmento não tem o que adaptar."""
    respondidos = {resposta.lote for resposta in respostas}
    adaptados = _adaptados(respostas)
    return tuple(
        CapituloNaAdaptacao(
            capitulo,
            len(segmentos),
            sum(segmento.id in adaptados for segmento in segmentos),
            tuple(p.lote for p in _do_capitulo(pedidos, capitulo) if p.lote not in respondidos),
        )
        for capitulo, segmentos in limpos.items()
        if segmentos
    )
