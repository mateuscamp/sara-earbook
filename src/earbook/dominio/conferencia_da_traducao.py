# SPDX-License-Identifier: GPL-3.0-or-later
"""O `conferir` no modo tradução: todo segmento traduzido, nada a mais e nada em inglês
(ADR-0006). Junta-se ao `conferir` do ADR-0005, que continua valendo."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator, Sequence

from earbook.dominio.conferencia import Problema
from earbook.dominio.glossario import (
    TITULOS_ABREVIADOS,
    ULTIMA_PALAVRA,
    ConferenciaDeNomes,
    EntradaDoGlossario,
)
from earbook.dominio.limpeza import CapituloLimpo
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.traducao import Pedido, Resposta, Traduzido

# Medido em 2026-11-01 (ADR-0006): o texto em inglês do Huxley e do Tides tem mediana de 37%
# destas palavras, e o Competente, em português, 0%. Sem "a", "me", "for" e "do", que também
# são palavras do português.
PALAVRAS_FUNCIONAIS_INGLESAS = frozenset({
    "the", "and", "of", "to", "is", "was", "which", "that", "with", "it", "he", "she", "they",
    "this", "not", "but", "be", "have", "had", "his", "her", "its", "were", "are", "been",
    "would", "could", "from", "by", "at", "an", "or", "my", "we", "you", "there", "their",
    "what", "when", "who", "will", "one", "all", "so", "than", "them", "these", "those",
    "into", "upon",
})  # fmt: skip
PALAVRAS_PARA_JULGAR_O_INGLES = 8
PROPORCAO_DE_INGLES = 0.2
_PALAVRA = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*")
_URL = re.compile(r"\S*(?:https?://|www\.)\S*")
_FIM_DE_FRASE = re.compile('[.!?\u2026]["\u201d\u2019)]*\\s+')
# T\u00edtulo de obra em Title Case: palavras com mai\u00fascula, com "of", "the"\u2026 entre elas.
_PALAVRA_DE_TITULO = r"[A-Z][\w'\u2019-]*"
_LIGA_TITULO = r"(?:of|the|and|in|for|on|a|an|to|at|by|with|from|or)"
_TITULO_DE_OBRA = re.compile(
    rf"{_PALAVRA_DE_TITULO}(?: +(?:{_LIGA_TITULO} +)*{_PALAVRA_DE_TITULO})+"
)
_COMECO_DE_PALAVRA = re.compile(r"(?<!\S)[A-Z]")
_PALAVRAS_NO_INICIO = 5


def conferir_traducao(
    capitulos: Sequence[CapituloLimpo],
    pedidos: Sequence[Pedido],
    respostas: Sequence[Resposta],
    glossario: Sequence[EntradaDoGlossario],
    *,
    amostra: bool,
) -> tuple[Problema, ...]:
    """Os problemas que impedem o `montar` do livro traduzido, em ordem de ID. Na `amostra`,
    o segmento sem tradução não é problema: o `montar --amostra` o tira."""
    limpos = {s.id: s for capitulo in capitulos for s in capitulo.segmentos}
    nomes = ConferenciaDeNomes(glossario)
    problemas, respondidos = _respostas(pedidos, respostas)
    for lote, traduzido, pedido in respondidos:
        problemas += _traduzido(lote, traduzido, pedido, limpos.get(traduzido.id), nomes)
    if not amostra:
        problemas += _sem_traducao(capitulos, respostas)
    problemas += _glossario_repetido(nomes)
    return tuple(sorted(problemas, key=lambda problema: problema.id))


def _glossario_repetido(nomes: ConferenciaDeNomes) -> list[Problema]:
    return [Problema("glossário", f"'{n}' aparece mais de uma vez") for n in nomes.repetidos()]


def _respostas(
    pedidos: Sequence[Pedido], respostas: Sequence[Resposta]
) -> tuple[list[Problema], list[tuple[str, Traduzido, Segmento]]]:
    """Cada tradução com o segmento que o pedido do lote dela mandou traduzir, e o ID
    repetido. A resposta cobre só o seu lote: o ID de outro lote não tem o texto pedido
    para comparar com `limpos/`."""
    pedidos_por_lote = {p.lote: {s.id: s for s in p.segmentos} for p in pedidos}
    problemas = _repetidos(respostas)
    respondidos: list[tuple[str, Traduzido, Segmento]] = []
    for resposta in respostas:
        if (do_lote := pedidos_por_lote.get(resposta.lote)) is None:
            problemas.append(Problema(resposta.lote, "resposta sem pedido"))
            continue
        for traduzido in resposta.traduzidos:
            if (pedido := do_lote.get(traduzido.id)) is None:
                motivo = f"respondido no lote {resposta.lote}, que não o pediu"
                problemas.append(Problema(traduzido.id, motivo))
            else:
                respondidos.append((resposta.lote, traduzido, pedido))
    return problemas, respondidos


def _repetidos(respostas: Sequence[Resposta]) -> list[Problema]:
    vezes = Counter(t.id for resposta in respostas for t in resposta.traduzidos)
    return [Problema(id_, f"traduzido {n} vezes") for id_, n in vezes.items() if n > 1]


def _traduzido(
    lote: str,
    traduzido: Traduzido,
    pedido: Segmento,
    limpo: Segmento | None,
    nomes: ConferenciaDeNomes,
) -> list[Problema]:
    id_ = traduzido.id
    if limpo is None:
        return [Problema(id_, "traduzido, mas não está em limpos/")]
    if limpo.texto != pedido.texto:
        motivo = (
            f"o texto em limpos/ mudou depois do pedido {lote}: apague o pedido e a resposta"
            " e rode o traduzir"
        )
        return [Problema(id_, motivo)]
    return [Problema(id_, motivo) for motivo in _escuta(limpo, traduzido.texto, nomes)]


def _escuta(limpo: Segmento, traducao: str, nomes: ConferenciaDeNomes) -> list[str]:
    """O que soaria errado no ElevenReader: silêncio, inglês e nome trocado."""
    original = limpo.texto
    if not traducao.strip():
        return ["tradução vazia"]
    motivos: list[str] = []
    if traducao.strip() == original.strip() and _inglesas(_palavras(traducao)):
        motivos.append("igual ao original, em inglês")
    elif motivo := _parece_ingles_no_papel(limpo.papel, original, traducao):
        motivos.append(motivo)
    return motivos + nomes.motivos(original, traducao)


def _parece_ingles_no_papel(papel: Papel, original: str, traducao: str) -> str | None:
    """Na nota, o título da obra fica no original e as frases curtas não se juntam: a
    referência bibliográfica é feita delas (F1 da pós-auditoria; A3 da curta). No corpo, a
    isenção deixava escapar a fala esquecida em inglês (A2 da curta)."""
    if papel is Papel.NOTA:
        return _parece_ingles(_sem_titulos_do_original(traducao, original), juntar=False)
    return _parece_ingles(traducao, juntar=True)


def _sem_titulos_do_original(traducao: str, original: str) -> str:
    """O título da obra citada fica no original, como mandam as instruções do tradutor: o
    "the" e o "of" dele não contam (F1 da pós-auditoria). Vale o trecho final da sequência
    que está no original: em "Ver The Varieties…", o "Ver" é da tradução (A4 da curta)."""

    def tirar(titulo: re.Match[str]) -> str:
        sequencia = titulo.group()
        for comeco in (achado.start() for achado in _COMECO_DE_PALAVRA.finditer(sequencia)):
            if sequencia[comeco:] in original:
                return sequencia[:comeco] + " "
        return sequencia

    return _TITULO_DE_OBRA.sub(tirar, traducao)


def _parece_ingles(traducao: str, *, juntar: bool) -> str | None:
    """O segmento inteiro e depois cada frase: medida só no segmento, a frase inglesa
    deixada num parágrafo traduzido se diluía no português (A1 da auditoria)."""
    if motivo := _proporcao(traducao):
        return motivo
    for trecho in _trechos(traducao, juntar=juntar):
        if motivo := _proporcao(trecho):
            inicio = " ".join(trecho.split()[:_PALAVRAS_NO_INICIO])
            return f"{motivo}, na frase \u201c{inicio}\u2026\u201d"
    return None


def _trechos(texto: str, *, juntar: bool) -> Iterator[str]:
    """A frase longa, sempre sozinha; as curtas seguidas, juntas até ter as palavras para
    julgar, ou três frases curtas em inglês passariam (F3 da pós-auditoria). A curta nunca
    se junta à longa: o português dela diluía a frase inglesa (A1 da curta)."""
    curtas: list[str] = []
    for frase in _frases(texto):
        if len(_palavras(frase)) >= PALAVRAS_PARA_JULGAR_O_INGLES:
            curtas = []
            yield frase
        elif juntar:
            curtas.append(frase)
            if len(_palavras(" ".join(curtas))) >= PALAVRAS_PARA_JULGAR_O_INGLES:
                yield " ".join(curtas)
                curtas = []


def _frases(texto: str) -> list[str]:
    """Corta depois de ".", "!", "?" e "…", mas não depois de inicial ("J. R.") nem de
    título abreviado ("Dr."): o pedaço solto passava dos 20% (F2 da pós-auditoria)."""
    frases: list[str] = []
    inicio = 0
    for achado in _FIM_DE_FRASE.finditer(texto):
        if texto[achado.start()] == "." and _abreviacao(texto[: achado.start()]):
            continue
        frases.append(texto[inicio : achado.end()])
        inicio = achado.end()
    return [*frases, texto[inicio:]]


def _abreviacao(antes: str) -> bool:
    if (palavra := ULTIMA_PALAVRA.search(antes)) is None:
        return False
    texto = palavra.group(1)
    return (len(texto) == 1 and texto.isupper()) or texto in TITULOS_ABREVIADOS


def _proporcao(trecho: str) -> str | None:
    palavras = _palavras(trecho)
    inglesas = _inglesas(palavras)
    if (
        len(palavras) < PALAVRAS_PARA_JULGAR_O_INGLES
        or inglesas / len(palavras) < PROPORCAO_DE_INGLES
    ):
        return None
    return f"parece inglês: {inglesas} de {len(palavras)} palavras são como 'the', 'of', 'and'"


def _inglesas(palavras: list[str]) -> int:
    return sum(palavra in PALAVRAS_FUNCIONAIS_INGLESAS for palavra in palavras)


def _palavras(texto: str) -> list[str]:
    """As palavras em minúsculas, sem URL: o link tem "the" e "of" e não é lido como frase."""
    return [achado.group().casefold() for achado in _PALAVRA.finditer(_URL.sub(" ", texto))]


def _sem_traducao(
    capitulos: Sequence[CapituloLimpo], respostas: Sequence[Resposta]
) -> list[Problema]:
    """Uma linha por capítulo: o livro recém-exportado tem centenas de segmentos."""
    traduzidos = {t.id for resposta in respostas for t in resposta.traduzidos}
    problemas: list[Problema] = []
    for capitulo in capitulos:
        if faltam := [s.id for s in capitulo.segmentos if s.id not in traduzidos]:
            motivo = f"{len(faltam)} segmentos sem tradução (o primeiro é {faltam[0]})"
            problemas.append(Problema(capitulo.capitulo, motivo))
    return problemas
