# SPDX-License-Identifier: GPL-3.0-or-later
"""O `conferir`: nada some, sobra ou se repete entre a origem e o livro montado (ADR-0005)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from earbook.dominio.segmento import FORA_DO_XML, Segmento


@dataclass(frozen=True)
class CapituloParaConferir:
    capitulo: str
    origem: tuple[str, ...]
    """IDs de `segmentos/`, na ordem do capítulo."""
    mantidos: tuple[str, ...]
    """IDs de `limpos/`."""
    marcados: tuple[str, ...]
    """IDs marcados com `data-earbook` no XHTML."""


@dataclass(frozen=True)
class Problema:
    id: str
    motivo: str


def conferir(
    capitulos: Sequence[CapituloParaConferir],
    removidos: Sequence[str],
    juntados: Sequence[tuple[str, str]],
) -> tuple[Problema, ...]:
    """Os problemas que impedem o `montar`, em ordem de ID; vazio quando o livro está inteiro.

    `removidos` e `juntados` (pares ID, destino) vêm como estão no `limpeza.json`, com as
    repetições: a leitura que as juntasse esconderia o registro repetido (A7 da auditoria).
    """
    origem = {id_: capitulo.capitulo for capitulo in capitulos for id_ in capitulo.origem}
    mantidos = {id_ for capitulo in capitulos for id_ in capitulo.mantidos}
    destinos = Counter(
        [*(id_ for c in capitulos for id_ in c.mantidos), *removidos, *(id_ for id_, _ in juntados)]
    )
    problemas = [
        Problema(id_, "sumiu: não está em limpos, nas remoções nem nas junções")
        for id_ in sorted(origem.keys() - destinos.keys())
    ]
    problemas += _destinos(destinos, origem)
    problemas += [
        Problema(id_, f"juntado em {em}, que não foi mantido")
        for id_, em in juntados
        if em not in mantidos
    ]
    for capitulo in capitulos:
        problemas += _marcas(capitulo) + _fora_do_capitulo(capitulo, origem)
    return tuple(sorted(problemas, key=lambda problema: problema.id))


def _destinos(destinos: Counter[str], origem: Mapping[str, str]) -> list[Problema]:
    problemas: list[Problema] = []
    for id_, vezes in destinos.items():
        if vezes > 1:
            motivo = f"aparece {vezes} vezes entre mantidos, remoções e junções"
            problemas.append(Problema(id_, motivo))
        if id_ not in origem:
            problemas.append(Problema(id_, "não existe na origem"))
    return problemas


def _fora_do_capitulo(capitulo: CapituloParaConferir, origem: Mapping[str, str]) -> list[Problema]:
    """O `montar` lê os textos do `limpos/` de cada capítulo: o segmento posto no capítulo
    errado sumiria do livro montado (A2 da auditoria)."""
    return [
        Problema(id_, f"mantido no capítulo {capitulo.capitulo}, mas é do {origem[id_]}")
        for id_ in capitulo.mantidos
        if id_ in origem and origem[id_] != capitulo.capitulo
    ]


def _marcas(capitulo: CapituloParaConferir) -> list[Problema]:
    """O `montar` troca o texto pela marca: cada ID da origem, marcado uma vez só."""
    marcas = Counter(capitulo.marcados)
    problemas = [
        Problema(id_, f"marcado {vezes} vezes no XHTML")
        for id_, vezes in marcas.items()
        if vezes > 1
    ]
    problemas += [
        Problema(id_, "sem marca no XHTML") for id_ in capitulo.origem if id_ not in marcas
    ]
    problemas += [
        Problema(id_, "marcado no XHTML fora da origem")
        for id_ in marcas
        if id_ not in capitulo.origem
    ]
    return problemas


def conferir_textos(segmentos: Iterable[Segmento]) -> tuple[Problema, ...]:
    """O texto que o XML não aceita, com o ID: o `montar` não consegue gravá-lo."""
    problemas: list[Problema] = []
    for segmento in segmentos:
        achados = (achado.group() for achado in FORA_DO_XML.finditer(segmento.texto))
        if caracteres := dict.fromkeys(achados):
            codigos = ", ".join(f"U+{ord(caractere):04X}" for caractere in caracteres)
            motivo = f"texto com caractere que o XML não aceita: {codigos}"
            problemas.append(Problema(segmento.id, motivo))
    return tuple(problemas)


def do_capitulo(problemas: Iterable[Problema], capitulo: str) -> tuple[Problema, ...]:
    """Só os problemas do capítulo e dos lotes dele: o tradutor em paralelo não vê os dos
    outros, nem os do glossário, que são da sessão (ADR-0007)."""
    return tuple(p for p in problemas if p.id == capitulo or p.id.startswith(f"{capitulo}-"))
