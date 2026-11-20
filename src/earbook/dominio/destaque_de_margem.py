# SPDX-License-Identifier: GPL-3.0-or-later
"""O destaque de margem que repete o texto vizinho (ADR-0008, "Destaque de margem repetido"): o
parágrafo com forma de frase cujas palavras o texto ao lado já diz, na mesma ordem. A limpeza o
registra com o motivo daqui.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from earbook.dominio.segmento import PALAVRA, Papel, Segmento, primeira_letra

# O destaque de margem (ADR-0008, "Destaque de margem repetido"). Medido no Dalgalarrondo: a
# janela de 2 a 6 segmentos e o mínimo de 4 a 8 palavras tiram de 238 a 239 destaques, e nada
# no Competente, no Hard Parts, no Huxley, no Tides nem no Learning DDD.
JANELA_DO_DESTAQUE = 3
PALAVRAS_DO_DESTAQUE = 6
MOTIVO_DO_DESTAQUE = "destaque de margem: repete o texto vizinho"
DESTAQUES_DO_LIVRO = 3
"""O livro diagramado com destaque de margem tem muitos que cortam ou mudam a frase do texto (o
Dalgalarrondo); o romance que repete uma frase inteira, nenhum (o Kafka à beira-mar). Com menos
de 3, a cópia exata de uma frase inteira fica (ADR-0008, "Repetição do autor e cópia lado a
lado")."""
# Aspa ou parêntese depois do ponto ainda fecham a frase.
_FECHA_FRASE = re.compile(r"[.!?\u2026][\u201d\u2019\"')]*$")
# A fala de diálogo abre com travessão ou meia-risca; o destaque de margem, nunca. A fala que
# repete a anterior ("— Um lugar para onde possam retornar?") é a resposta, e fica (ADR-0008,
# "Fala de diálogo não é destaque": 4 no Kafka à beira-mar).
_ABRE_FALA = re.compile(r"^\s*[\u2014\u2013]")
# O hífen da quebra ("pri-" + "meiros") e o do composto ("divi-dem-se", contra "dividem-se" no
# destaque) não contam na comparação.
_HIFEN_NA_PALAVRA = re.compile(r"(?<=[^\W\d_])[-\u2010\u00ad]\s*(?=[^\W\d_])")
# O número conta: o destaque com "3 a 25 segundos" não repete o texto com "5 a 30".
_PALAVRA_OU_NUMERO = re.compile(rf"{PALAVRA.pattern}|\d+")


@dataclass(frozen=True)
class _Achado:
    id: str
    inteiro: bool
    """O destaque é a cópia exata de uma frase inteira de um vizinho, fora do meio da frase: a
    forma que também tem a frase que o autor repete (o Kafka à beira-mar)."""


def destaques(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]],
    no_meio_da_frase: Callable[[Segmento, Segmento], bool],
) -> dict[str, str]:
    """ID → motivo de cada destaque de margem: o parágrafo com forma de frase, de 6 palavras ou
    mais, cujas palavras aparecem seguidas no texto dos parágrafos vizinhos (3 antes e 3
    depois, no mesmo capítulo), juntados. Juntar os vizinhos pega o destaque que parte uma frase
    ("…principais palcos" | destaque | "de nossas vidas…", Dalgalarrondo p. 250).

    O destaque igual a um parágrafo inteiro do texto é um par de gêmeos: sai a cópia que
    `no_meio_da_frase(anterior, seguinte)`, a regra da junção, aponta, e a segunda de duas cópias
    lado a lado (Dalgalarrondo, p. 151). A cópia exata de uma frase inteira, fora do meio da
    frase, só sai no livro com `DESTAQUES_DO_LIVRO` destaques que cortam ou mudam a frase, ou que
    caem no meio dela: o destaque é diagramação, e se repete pelo livro; a frase que o autor
    repete fica (o Kafka), e as duas referências iguais e seguidas do Learning DDD também.
    """
    achados: list[_Achado] = []
    for _, segmentos in capitulos:
        # A chave de cada segmento uma vez só, para o gêmeo (lote A da revisão).
        chaves = [_chave(segmento.texto) for segmento in segmentos]
        for i in range(len(segmentos)):
            achado = _destaque(segmentos, chaves, i, no_meio_da_frase)
            if achado is not None:
                achados.append(achado)
    # Só o destaque que corta ou muda a frase, ou que cai no meio dela, prova a diagramação: a
    # cópia inteira não prova nada, e a frase repetida 30 vezes não faz o livro diagramado.
    diagramado = sum(not a.inteiro for a in achados) >= DESTAQUES_DO_LIVRO
    return {a.id: MOTIVO_DO_DESTAQUE for a in achados if diagramado or not a.inteiro}


def _destaque(
    segmentos: Sequence[Segmento],
    chaves: Sequence[str],
    i: int,
    no_meio_da_frase: Callable[[Segmento, Segmento], bool],
) -> _Achado | None:
    if not _parece_frase(segmentos[i]):
        return None
    janela = range(max(0, i - JANELA_DO_DESTAQUE), min(len(segmentos), i + JANELA_DO_DESTAQUE + 1))
    vizinhos = [k for k in janela if k != i and segmentos[k].papel is Papel.PARAGRAFO]
    # O texto dos vizinhos se junta antes da chave: o hífen da quebra fica no fim de um e o
    # resto da palavra no começo do outro ("os pri-" + "meiros").
    juntos = _chave(" ".join(segmentos[k].texto for k in vizinhos))
    if f" {chaves[i]} " not in f" {juntos} ":
        return None
    meio = 0 < i < len(segmentos) - 1 and no_meio_da_frase(segmentos[i - 1], segmentos[i + 1])
    texto = segmentos[i].texto
    inteiro = not meio and any(_frase_inteira(texto, segmentos[k].texto) for k in vizinhos)
    if all(chaves[k] != chaves[i] for k in vizinhos):
        return _Achado(segmentos[i].id, inteiro)
    # O gêmeo: a segunda cópia lado a lado, ou a que parte a frase (decisão B do Mateus). Ele é
    # cópia inteira pela chave, mesmo com outra pontuação, e só a do meio da frase prova a
    # diagramação (revisão).
    segunda = i - 1 in vizinhos and chaves[i - 1] == chaves[i]
    return _Achado(segmentos[i].id, not meio) if meio or segunda else None


def _frase_inteira(texto: str, vizinho: str) -> bool:
    """`texto` está em `vizinho` letra por letra, como frase inteira: depois do começo dele ou de
    uma frase fechada (o destaque repete a frase cortada ou mudada: "Just as…" do Bonica, contra
    "that, just as…")."""
    frase, onde = " ".join(texto.split()), " ".join(vizinho.split())
    inicio = onde.find(frase)
    while inicio >= 0:
        antes = onde[:inicio].rstrip()
        if not antes or _FECHA_FRASE.search(antes) is not None:
            return True
        inicio = onde.find(frase, inicio + 1)
    return False


def _parece_frase(segmento: Segmento) -> bool:
    """Parágrafo que abre em maiúscula e fecha frase. O título que veio como parágrafo ("ATO
    VOLITIVO OU ATO DE VONTADE"), a continuação em minúscula, a pergunta que termina em ":" e a
    fala de diálogo que ecoa a anterior também repetem o vizinho, e ficam."""
    return (
        segmento.papel is Papel.PARAGRAFO
        and _ABRE_FALA.match(segmento.texto) is None
        and primeira_letra(segmento.texto).isupper()
        and _FECHA_FRASE.search(segmento.texto) is not None
        and len(PALAVRA.findall(segmento.texto)) >= PALAVRAS_DO_DESTAQUE
    )


def _chave(texto: str) -> str:
    """As palavras e os números, em minúscula e sem hífen dentro da palavra, separados por um
    espaço: a pontuação e a citação entre parênteses não separam o destaque do texto."""
    sem_hifen = _HIFEN_NA_PALAVRA.sub("", texto)
    return " ".join(achado.group().casefold() for achado in _PALAVRA_OU_NUMERO.finditer(sem_hifen))
