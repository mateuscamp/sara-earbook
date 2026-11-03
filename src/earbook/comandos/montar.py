# SPDX-License-Identifier: GPL-3.0-or-later
"""Comandos `conferir` e `montar`: da pasta de trabalho ao EPUB para ouvir (ADR-0005).

O livro que precisa de tradução monta a tradução, a amostra ou o original (ADR-0006).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.adaptadores.pacote_epub import empacotar_pasta, opf_em_outro_idioma
from earbook.adaptadores.xhtml import (
    acrescentar_paragrafos,
    ids_marcados,
    ids_no_sumario,
    montar_xhtml,
)
from earbook.dominio.adaptacao import RespostaDaAdaptacao, pode_adaptar, textos_da_adaptacao
from earbook.dominio.conferencia import (
    CapituloParaConferir,
    Problema,
    conferir,
    conferir_textos,
    do_capitulo,
)
from earbook.dominio.conferencia_da_adaptacao import (
    avisos_da_adaptacao,
    conferir_adaptacao,
    conferir_sumario,
)
from earbook.dominio.conferencia_da_traducao import conferir_termos, conferir_traducao
from earbook.dominio.limpeza import CapituloLimpo
from earbook.dominio.segmento import Segmento, notas_para_o_fim
from earbook.dominio.trabalho import CapituloPreparado
from earbook.dominio.traducao import (
    IDIOMA_DE_SAIDA,
    Modo,
    Resposta,
    TrocaDeIdioma,
    precisa_traduzir,
)

PROBLEMAS_NA_MENSAGEM = 5
_SUFIXOS = {
    None: ".pronto.epub",
    Modo.TRADUCAO: ".pronto.epub",
    Modo.AMOSTRA: ".amostra.epub",
    Modo.ORIGINAL: ".original.epub",
    Modo.ADAPTACAO: ".pronto.epub",
}


class MontagemRecusadaError(ValueError):
    pass


class ModoInvalidoError(ValueError):
    pass


@dataclass(frozen=True)
class Montagem:
    epub: Path
    capitulos: int
    segmentos: int
    notas: int
    """Notas de rodapé levadas para o fim do capítulo."""
    fora: int = 0
    """Na amostra, os segmentos sem tradução, que ficaram de fora (ADR-0006)."""
    no_original: int = 0
    """Na amostra, os itens do sumário sem tradução, que ficam no original (ADR-0005)."""
    adaptado: bool = False
    """O livro em português adaptado (ADR-0009): o que fica de fora está sem adaptação."""


@dataclass(frozen=True)
class _Livro:
    modo: Modo
    idioma: str
    capitulos: tuple[CapituloPreparado, ...]
    limpos: Mapping[str, tuple[Segmento, ...]]
    finais: Mapping[str, tuple[Segmento, ...]]
    """Por capítulo, cada segmento com o texto que vai para o livro; na amostra, só os
    traduzidos."""
    respostas: tuple[Resposta, ...]
    cobertos: frozenset[str]
    """Os IDs que a tradução ou a adaptação cobre; no original, todos."""
    adaptados: tuple[RespostaDaAdaptacao, ...] = ()
    seguintes: Mapping[str, tuple[str, ...]] = field(default_factory=dict[str, tuple[str, ...]])
    """Na adaptação, os parágrafos que o grupo põe depois do primeiro (ADR-0009)."""
    adaptado: bool = False
    """O livro em português que passou pelo `adaptar`, na adaptação ou na amostra."""


def epub_padrao(pasta: Path, modo: Modo | None = None) -> Path:
    """`epub_padrao(Path("Duna.earbook"))` → `Path("Duna.pronto.epub")`; a amostra e o
    original dizem o modo no nome, para nunca passarem pelo livro pronto."""
    return pasta.with_suffix(_SUFIXOS[modo])


class CapituloDesconhecidoError(ValueError):
    pass


@dataclass(frozen=True)
class Conferencia:
    problemas: tuple[Problema, ...]
    """O que impede o `montar`."""
    avisos: tuple[Problema, ...]
    """O que não recusa o livro: na adaptação, o termo omitido e o descarte por decisão do
    livro (ADR-0009)."""


def conferir_pasta(
    pasta: Path, modo: Modo | None = None, capitulo: str | None = None
) -> tuple[Problema, ...]:
    """Os problemas que impedem o `montar`; vazio quando nada some, sobra ou se repete."""
    return conferencia_da_pasta(pasta, modo, capitulo).problemas


def conferencia_da_pasta(
    pasta: Path, modo: Modo | None = None, capitulo: str | None = None
) -> Conferencia:
    """Os problemas e os avisos, de uma leitura só da pasta.

    Com `capitulo`, só os dele e dos lotes dele (ADR-0007). O capítulo que o livro não tem é
    recusado: o filtro vazio diria que está tudo certo (lote A da revisão).
    """
    livro = _ler_livro(pasta, modo)
    problemas = _conferir(pasta, livro)
    avisos = avisos_da_adaptacao(livro.adaptados) if livro.adaptado else ()
    if capitulo is None:
        return Conferencia(problemas, avisos)
    if capitulo not in (ids := [c.id for c in livro.capitulos]):
        mensagem = f"{pasta}: o livro não tem o capítulo {capitulo!r}; tem {', '.join(ids)}"
        raise CapituloDesconhecidoError(mensagem)
    return Conferencia(do_capitulo(problemas, capitulo), do_capitulo(avisos, capitulo))


def montar(pasta: Path, destino: Path, modo: Modo | None = None) -> Montagem:
    """Grava em `destino` o EPUB original com o texto final de cada segmento.

    Recusa antes de gravar qualquer coisa se o `conferir` acha problema, para que o livro
    montado nunca perca texto em silêncio.
    """
    if destino.exists():
        mensagem = f"{destino} já existe"
        raise FileExistsError(mensagem)
    livro = _ler_livro(pasta, modo)
    if problemas := _conferir(pasta, livro):
        raise MontagemRecusadaError(_recusa(pasta, problemas))
    no_idioma_dele = livro.modo is Modo.ORIGINAL or livro.adaptado
    troca = None if no_idioma_dele else TrocaDeIdioma(livro.idioma, IDIOMA_DE_SAIDA)
    substituicoes = {c.arquivo: _montar_capitulo(pasta, c, livro, troca) for c in livro.capitulos}
    if troca is not None:
        opf, conteudo = opf_em_outro_idioma(trabalho.pasta_do_epub(pasta), troca)
        substituicoes[opf] = conteudo
    empacotar_pasta(trabalho.pasta_do_epub(pasta), destino, substituicoes)
    no_original = sum(len(_no_sumario_sem_traducao(pasta, c, livro)) for c in livro.capitulos)
    return _montagem(destino, livro, no_original)


def _modo(pasta: Path, pedido: Modo | None) -> tuple[Modo, str]:
    """O livro em português, ou de idioma indefinido, só monta o texto limpo (ADR-0003); o
    outro, a tradução, a amostra ou o original (ADR-0006); o português que passou pelo
    `adaptar`, a adaptação, a amostra ou o original (ADR-0009). Devolve também o idioma."""
    idioma = trabalho.ler_idioma(pasta)
    if precisa_traduzir(idioma):
        return pedido or Modo.TRADUCAO, idioma
    if trabalho.ha_adaptacao(pasta) and pode_adaptar(idioma):
        return pedido or Modo.ADAPTACAO, idioma
    if pedido is not None:
        mensagem = (
            f"{pasta}: o livro está em {idioma!r}, que não se traduz;"
            f" --{pedido} é só para livro traduzido ou adaptado"
        )
        raise ModoInvalidoError(mensagem)
    return Modo.ORIGINAL, idioma


def _ler_livro(pasta: Path, pedido: Modo | None) -> _Livro:
    modo, idioma = _modo(pasta, pedido)
    capitulos = trabalho.ler_capitulos(pasta)
    limpos = {c.id: trabalho.ler_limpos(pasta, c.id) for c in capitulos}
    if modo is Modo.ORIGINAL:
        todos = frozenset(s.id for lista in limpos.values() for s in lista)
        return _Livro(modo, idioma, capitulos, limpos, limpos, (), todos)
    if not precisa_traduzir(idioma):
        adaptados = trabalho.ler_adaptados(pasta)
        textos = textos_da_adaptacao(limpos, adaptados)
        return _Livro(
            modo,
            idioma,
            capitulos,
            limpos,
            textos.finais,
            (),
            textos.cobertos,
            adaptados,
            textos.seguintes,
            adaptado=True,
        )
    respostas = trabalho.ler_respostas(pasta)
    traducao = {t.id: t.texto for resposta in respostas for t in resposta.traduzidos}
    finais = {
        capitulo: tuple(replace(s, texto=traducao[s.id]) for s in lista if s.id in traducao)
        for capitulo, lista in limpos.items()
    }
    return _Livro(modo, idioma, capitulos, limpos, finais, respostas, frozenset(traducao))


def _conferir(pasta: Path, livro: _Livro) -> tuple[Problema, ...]:
    limpeza = trabalho.ler_limpeza(pasta)
    ids = conferir(
        [_para_conferir(pasta, c, livro.limpos[c.id]) for c in livro.capitulos],
        limpeza.removidos,
        limpeza.juntados,
    )
    # Na adaptação, o `conferir_adaptacao` já confere cada parágrafo, o primeiro inclusive.
    finais = [] if livro.adaptado else [s for lista in livro.finais.values() for s in lista]
    problemas = [*ids, *conferir_textos(finais), *_conferir_traducao(pasta, livro)]
    return tuple(sorted(problemas, key=lambda problema: problema.id))


def _conferir_traducao(pasta: Path, livro: _Livro) -> tuple[Problema, ...]:
    if livro.modo is Modo.ORIGINAL:
        return ()
    amostra = livro.modo is Modo.AMOSTRA
    glossario = trabalho.ler_glossario(pasta)
    capitulos = [CapituloLimpo(capitulo, lista) for capitulo, lista in livro.limpos.items()]
    if livro.adaptado:
        pedidos = trabalho.ler_pedidos_da_adaptacao(pasta)
        adaptacao = conferir_adaptacao(
            capitulos, pedidos, livro.adaptados, glossario, amostra=amostra
        )
        return (*adaptacao, *conferir_sumario(livro.adaptados, _no_sumario(pasta, livro)))
    traducao = conferir_traducao(
        [CapituloLimpo(capitulo, lista) for capitulo, lista in livro.limpos.items()],
        trabalho.ler_pedidos(pasta),
        livro.respostas,
        glossario,
        amostra=amostra,
    )
    return (*traducao, *conferir_termos(trabalho.ler_termos(pasta), glossario, amostra=amostra))


def _no_sumario(pasta: Path, livro: _Livro) -> frozenset[str]:
    return frozenset(
        id_
        for capitulo in livro.capitulos
        for id_ in ids_no_sumario(trabalho.ler_xhtml(pasta, capitulo.arquivo), capitulo.arquivo)
    )


def _para_conferir(
    pasta: Path, capitulo: CapituloPreparado, limpos: tuple[Segmento, ...]
) -> CapituloParaConferir:
    return CapituloParaConferir(
        capitulo.id,
        tuple(s.id for s in trabalho.ler_segmentos(pasta, capitulo.id)),
        tuple(s.id for s in limpos),
        ids_marcados(trabalho.ler_xhtml(pasta, capitulo.arquivo), capitulo.arquivo),
    )


def _montar_capitulo(
    pasta: Path, capitulo: CapituloPreparado, livro: _Livro, troca: TrocaDeIdioma | None
) -> bytes:
    """Na amostra, o segmento sem tradução não está em `textos` e sai, como o removido."""
    textos = {segmento.id: segmento.texto for segmento in livro.finais[capitulo.id]}
    notas = notas_para_o_fim(livro.limpos[capitulo.id])
    lido = trabalho.ler_xhtml(pasta, capitulo.arquivo)
    conteudo = acrescentar_paragrafos(lido, livro.seguintes, capitulo.arquivo)
    return montar_xhtml(conteudo, textos, notas, capitulo.arquivo, troca)


def _no_sumario_sem_traducao(
    pasta: Path, capitulo: CapituloPreparado, livro: _Livro
) -> frozenset[str]:
    """Na amostra, o item do sumário sem tradução fica no original, e não "de fora" (F5)."""
    if not (sem_traducao := {s.id for s in livro.limpos[capitulo.id]} - livro.cobertos):
        return frozenset()
    conteudo = trabalho.ler_xhtml(pasta, capitulo.arquivo)
    return ids_no_sumario(conteudo, capitulo.arquivo) & sem_traducao


def _montagem(destino: Path, livro: _Livro, no_original: int) -> Montagem:
    usados = sum(len(lista) for lista in livro.finais.values())
    notas = sum(
        len(notas_para_o_fim(livro.limpos[capitulo]) & {s.id for s in lista})
        for capitulo, lista in livro.finais.items()
    )
    todos = {s.id for lista in livro.limpos.values() for s in lista}
    fora = len(todos - livro.cobertos) - no_original
    return Montagem(
        destino, len(livro.capitulos), usados, notas, fora, no_original, adaptado=livro.adaptado
    )


def _recusa(pasta: Path, problemas: tuple[Problema, ...]) -> str:
    primeiros = "; ".join(f"{p.id}: {p.motivo}" for p in problemas[:PROBLEMAS_NA_MENSAGEM])
    resto = len(problemas) - PROBLEMAS_NA_MENSAGEM
    mais = f"; e mais {resto} (earbook conferir {pasta})" if resto > 0 else ""
    return f"{pasta}: o conferir achou {len(problemas)} problemas: {primeiros}{mais}"
