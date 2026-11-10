# SPDX-License-Identifier: GPL-3.0-or-later
"""O que a limpeza para o ouvido devolve (ADR-0003): o texto limpo e o registro de cada
remoção, suspeita, aparo, junção e capitular, que vai para `limpeza.json`."""

from __future__ import annotations

from dataclasses import dataclass

from earbook.dominio.capitular import CapitularDevolvida
from earbook.dominio.segmento import Segmento


@dataclass(frozen=True)
class Remocao:
    """Um segmento que saiu do áudio, com o motivo, para o `conferir` e para revisão."""

    id: str
    motivo: str
    texto: str


@dataclass(frozen=True)
class Pista:
    id: str
    posicao: int
    letra: str


@dataclass(frozen=True)
class Suspeita:
    """Um segmento que parece lixo de página, mas ficou no texto: quem decide é o agente."""

    id: str
    motivo: str
    texto: str
    pista: Pista | None = None


@dataclass(frozen=True)
class Aparo:
    """Um pedaço tirado do fim de um segmento que continua no texto, como o cabeçalho colado."""

    id: str
    motivo: str
    texto: str


@dataclass(frozen=True)
class Juncao:
    """O segmento `id` foi juntado ao fim do segmento `em`: era o mesmo parágrafo partido."""

    id: str
    em: str


@dataclass(frozen=True)
class CapituloLimpo:
    capitulo: str
    segmentos: tuple[Segmento, ...]


@dataclass(frozen=True)
class LivroLimpo:
    capitulos: tuple[CapituloLimpo, ...]
    remocoes: tuple[Remocao, ...]
    suspeitas: tuple[Suspeita, ...] = ()
    aparos: tuple[Aparo, ...] = ()
    juncoes: tuple[Juncao, ...] = ()
    capitulares: tuple[CapitularDevolvida, ...] = ()
