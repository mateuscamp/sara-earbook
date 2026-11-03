# SPDX-License-Identifier: GPL-3.0-or-later
"""O `conferir` no modo adaptação: cada ID num grupo, e cada grupo fiel às fontes (ADR-0009).
Junta-se ao `conferir` do ADR-0005, que continua valendo."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from earbook.dominio.adaptacao import Grupo, MotivoDoDescarte, RespostaDaAdaptacao, TipoDoGrupo
from earbook.dominio.conferencia import Problema, conferir_textos
from earbook.dominio.fidelidade import (
    Raridade,
    eh_rotulo,
    faltas_de_fidelidade,
    numeros_que_faltam,
    so_funciona_no_papel,
    termos_que_faltam,
)
from earbook.dominio.glossario import ConferenciaDeNomes, EntradaDoGlossario
from earbook.dominio.limpeza import CapituloLimpo
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.traducao import Pedido


@dataclass(frozen=True)
class _Regua:
    """O que todo grupo consulta: o texto de `limpos/`, a raridade dos termos e o glossário."""

    limpos: Mapping[str, Segmento]
    raridade: Raridade
    nomes: ConferenciaDeNomes


def conferir_adaptacao(
    capitulos: Sequence[CapituloLimpo],
    pedidos: Sequence[Pedido],
    respostas: Sequence[RespostaDaAdaptacao],
    glossario: Sequence[EntradaDoGlossario],
    *,
    amostra: bool,
) -> tuple[Problema, ...]:
    """Os problemas que impedem o `montar` do livro adaptado, em ordem de ID. Na `amostra`,
    o segmento sem adaptação não é problema: o `montar --amostra` o tira."""
    limpos = {s.id: s for capitulo in capitulos for s in capitulo.segmentos}
    regua = _Regua(limpos, Raridade.do_livro(limpos.values()), ConferenciaDeNomes(glossario))
    pedidos_por_lote = {pedido.lote: pedido for pedido in pedidos}
    problemas = _repetidos(respostas)
    for resposta in respostas:
        if (pedido := pedidos_por_lote.get(resposta.lote)) is None:
            problemas.append(Problema(resposta.lote, "resposta sem pedido"))
        else:
            problemas += _resposta(resposta, pedido, regua)
    if not amostra:
        problemas += _sem_adaptacao(capitulos, respostas)
    problemas += [
        Problema("glossário", f"'{n}' aparece mais de uma vez") for n in regua.nomes.repetidos()
    ]
    return tuple(sorted(problemas, key=lambda problema: problema.id))


def avisos_da_adaptacao(respostas: Sequence[RespostaDaAdaptacao]) -> tuple[Problema, ...]:
    """O que não recusa o livro e a sessão lê antes do `montar`: o termo omitido de propósito
    e o descarte por decisão do livro (ADR-0009)."""
    avisos: list[Problema] = []
    for grupo in (grupo for resposta in respostas for grupo in resposta.grupos):
        avisos += [
            Problema(grupo.fontes[0], f"omitiu '{o.termo}': {o.motivo}") for o in grupo.omitidos
        ]
        base, _, secao = grupo.descarte.partition(":")
        if base.strip() == MotivoDoDescarte.DECISAO and secao.strip():
            avisos.append(Problema(grupo.fontes[0], f"descartado por decisão: {secao.strip()}"))
    return tuple(avisos)


def conferir_sumario(
    respostas: Sequence[RespostaDaAdaptacao], no_sumario: frozenset[str]
) -> list[Problema]:
    """No sumário nada sai e nada se junta (ADR-0005): o item em descarte, o que não é a
    primeira fonte do grupo e o de mais de um parágrafo ficavam no original, calados (A7)."""
    motivo = "item do sumário não sai nem se junta: use igual ou um texto só dele"
    problemas: list[Problema] = []
    for grupo in (grupo for resposta in respostas for grupo in resposta.grupos):
        if grupo.tipo is TipoDoGrupo.DESCARTE or len(grupo.texto) > 1:
            presos = grupo.fontes
        else:
            presos = grupo.fontes[1:]
        problemas += [Problema(id_, motivo) for id_ in presos if id_ in no_sumario]
    return problemas


def _repetidos(respostas: Sequence[RespostaDaAdaptacao]) -> list[Problema]:
    vezes = Counter(id_ for r in respostas for grupo in r.grupos for id_ in grupo.fontes)
    return [Problema(id_, f"em {n} grupos") for id_, n in vezes.items() if n > 1]


def _sem_adaptacao(
    capitulos: Sequence[CapituloLimpo], respostas: Sequence[RespostaDaAdaptacao]
) -> list[Problema]:
    cobertos = {id_ for r in respostas for grupo in r.grupos for id_ in grupo.fontes}
    faltam = {c.capitulo: sum(s.id not in cobertos for s in c.segmentos) for c in capitulos}
    return [Problema(c, f"{n} segmentos sem adaptação") for c, n in faltam.items() if n]


def _resposta(resposta: RespostaDaAdaptacao, pedido: Pedido, regua: _Regua) -> list[Problema]:
    """Cada grupo contra o pedido do lote dele; o grupo de fora ou partido não é conferido."""
    posicao = {segmento.id: n for n, segmento in enumerate(pedido.segmentos)}
    do_pedido = {segmento.id: segmento for segmento in pedido.segmentos}
    ouvidos = [_ouvido(grupo, regua.limpos) for grupo in resposta.grupos]
    problemas: list[Problema] = []
    for n, grupo in enumerate(resposta.grupos):
        if fora := [id_ for id_ in grupo.fontes if id_ not in do_pedido]:
            motivo = f"no lote {resposta.lote}, que não o pediu"
            problemas += [Problema(id_, motivo) for id_ in fora]
            continue
        lugares = [posicao[id_] for id_ in grupo.fontes]
        if lugares != list(range(lugares[0], lugares[0] + len(lugares))):
            problemas.append(Problema(grupo.fontes[0], "fontes que não são vizinhas no pedido"))
            continue
        fontes = [do_pedido[id_] for id_ in grupo.fontes]
        vizinhos = " ".join(ouvidos[max(n - 1, 0) : n] + ouvidos[n + 1 : n + 2])
        problemas += _velhos(fontes, regua.limpos)
        problemas += _grupo(grupo, fontes, vizinhos, regua)
    return problemas


def _ouvido(grupo: Grupo, limpos: Mapping[str, Segmento]) -> str:
    """O que se ouve no lugar do grupo: a prova do descarte `repetido` dos vizinhos."""
    if grupo.tipo is TipoDoGrupo.TEXTO:
        return " ".join(grupo.texto)
    if grupo.tipo is TipoDoGrupo.IGUAL:
        return " ".join(limpos[id_].texto for id_ in grupo.fontes if id_ in limpos)
    return ""


def _velhos(fontes: Sequence[Segmento], limpos: Mapping[str, Segmento]) -> list[Problema]:
    problemas: list[Problema] = []
    for fonte in fontes:
        if (limpo := limpos.get(fonte.id)) is None:
            problemas.append(Problema(fonte.id, "não está em limpos"))
        elif limpo.texto != fonte.texto:
            motivo = "adaptação velha: o texto mudou em limpos depois do pedido"
            problemas.append(Problema(fonte.id, motivo))
    return problemas


def _grupo(
    grupo: Grupo, fontes: Sequence[Segmento], vizinhos: str, regua: _Regua
) -> list[Problema]:
    primeiro = grupo.fontes[0]
    papeis = {fonte.papel for fonte in fontes}
    motivos = (
        ["o grupo mistura título e parágrafo"] if Papel.TITULO in papeis and len(papeis) > 1 else []
    )
    if grupo.tipo is TipoDoGrupo.DESCARTE:
        motivos += _descarte(grupo.descarte, fontes, vizinhos, regua.raridade)
        return [Problema(primeiro, motivo) for motivo in motivos]
    ouvido = grupo.texto if grupo.tipo is TipoDoGrupo.TEXTO else tuple(f.texto for f in fontes)
    if Papel.TITULO in papeis and len(ouvido) > 1:
        motivos.append(f"o título tem {len(ouvido)} parágrafos")
    motivos += ["parágrafo vazio" for paragrafo in ouvido if not paragrafo.strip()]
    problemas = [Problema(primeiro, motivo) for motivo in motivos]
    problemas += conferir_textos(Segmento(primeiro, Papel.PARAGRAFO, p) for p in ouvido)
    textos = [fonte.texto for fonte in fontes]
    omitidos = [omitido.termo for omitido in grupo.omitidos]
    motivos = faltas_de_fidelidade(textos, ouvido, omitidos, regua.raridade)
    motivos += regua.nomes.motivos(" ".join(textos), " ".join(ouvido))
    motivos += [motivo for paragrafo in ouvido for motivo in so_funciona_no_papel(paragrafo)]
    return problemas + [Problema(primeiro, motivo) for motivo in motivos]


def _descarte(
    descarte: str, fontes: Sequence[Segmento], vizinhos: str, raridade: Raridade
) -> list[str]:
    base, dois_pontos, secao = descarte.partition(":")
    textos = [fonte.texto for fonte in fontes]
    match base.strip():
        case MotivoDoDescarte.REPETIDO:
            faltam = numeros_que_faltam(textos, vizinhos)
            faltam += termos_que_faltam(textos, vizinhos, (), raridade)
            return [
                f"descarte 'repetido' sem prova: '{falta}' não está ao lado" for falta in faltam
            ]
        case MotivoDoDescarte.ROTULO:
            if all(eh_rotulo(texto) for texto in textos):
                return []
            return ["descarte 'rotulo' de um texto que não é rótulo"]
        case MotivoDoDescarte.DECISAO if dois_pontos and secao.strip():
            return []
        case MotivoDoDescarte.DECISAO:
            return ["descarte 'decisao' sem a seção de decisoes.md"]
        case _:
            return [f"motivo de descarte desconhecido: {descarte!r}"]
