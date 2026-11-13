# SPDX-License-Identifier: GPL-3.0-or-later
"""Dos blocos do livro aos capítulos, e o nível de cada título (ADR-0004).

Saiu de `blocos.py` para ele caber no limite de 400 linhas do ADR-0001.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import takewhile

from earbook.dominio.blocos import Bloco
from earbook.dominio.pagina import DIFERENCA_DE_TAMANHO, PALAVRAS_DO_ROTULO
from earbook.dominio.sumario_interno import Abertura
from earbook.dominio.tipo_da_linha import TipoDeBloco

PAGINAS_DO_CAPITULO = 3


@dataclass(frozen=True)
class Divisao:
    """Os capítulos e o nome que o sumário interno do PDF dá a cada um; None sem nome."""

    capitulos: tuple[tuple[Bloco, ...], ...]
    nomes: tuple[str | None, ...]

    def com_o_nome_no_primeiro_bloco(self) -> tuple[tuple[Bloco, ...], ...]:
        """Os capítulos com o nome gravado no primeiro bloco de cada um, de onde o
        `nome_do_capitulo` o lê para o sumário do EPUB."""
        return tuple(
            (replace(capitulo[0], capitulo=nome or ""), *capitulo[1:])
            for capitulo, nome in zip(self.capitulos, self.nomes, strict=True)
        )


def dividir_pelo_sumario(blocos: Sequence[Bloco], aberturas: Sequence[Abertura]) -> Divisao:
    """Corta o livro nas aberturas do sumário interno do PDF, em ordem de página (ADR-0004,
    "Capítulos pelo sumário interno do PDF").

    O capítulo abre no primeiro título da página da abertura, e o que vem antes dele na página é
    o fim do capítulo anterior; na página sem título, abre no primeiro bloco. Só fecha depois de
    ter texto: a página da parte fica com o primeiro capítulo dela, e o nome é o da última
    abertura. O rótulo e o tamanho dos títulos não abrem capítulo aqui: o "Capítulo N" do
    gabarito do Manica fica dentro do anexo.
    """
    com_titulo = {bloco.pagina for bloco in blocos if bloco.tipo is TipoDeBloco.TITULO}
    niveis = _niveis(blocos, _tamanho_das_aberturas(blocos, aberturas))
    capitulos: list[list[Bloco]] = [[]]
    nomes: list[str | None] = [None]
    proxima = 0
    for bloco in blocos:
        while proxima < len(aberturas) and _abre(bloco, aberturas[proxima], com_titulo):
            if _tem_texto(capitulos[-1]):
                capitulos.append([])
                nomes.append(None)
            nomes[-1] = aberturas[proxima].nome
            proxima += 1
        com_nivel = bloco.tipo is TipoDeBloco.TITULO
        nivel = niveis[round(bloco.tamanho, 1)] if com_nivel else bloco.nivel
        capitulos[-1].append(replace(bloco, nivel=nivel))
    cheios = [(tuple(c), nome) for c, nome in zip(capitulos, nomes, strict=True) if c]
    return Divisao(tuple(c for c, _ in cheios), tuple(nome for _, nome in cheios))


def _abre(bloco: Bloco, abertura: Abertura, com_titulo: set[int]) -> bool:
    """O bloco é o primeiro do capítulo da abertura: está depois da página dela, ou é título na
    página dela, ou qualquer bloco na página dela, se ela não tem título."""
    if bloco.pagina != abertura.pagina:
        return bloco.pagina > abertura.pagina
    return bloco.tipo is TipoDeBloco.TITULO or abertura.pagina not in com_titulo


def _tamanho_das_aberturas(blocos: Sequence[Bloco], aberturas: Sequence[Abertura]) -> float | None:
    """O tamanho mais comum do primeiro título das páginas de abertura: o do capítulo (30 pt no
    Manica, contra os 55 das 12 partes e os 82 dos restos de figura)."""
    paginas = {abertura.pagina for abertura in aberturas}
    primeiros: dict[int, float] = {}
    for bloco in blocos:
        if bloco.tipo is TipoDeBloco.TITULO and bloco.pagina in paginas:
            _ = primeiros.setdefault(bloco.pagina, round(bloco.tamanho, 1))
    tamanhos = Counter(primeiros.values())
    return tamanhos.most_common(1)[0][0] if tamanhos else None


def dividir_em_capitulos(blocos: Sequence[Bloco]) -> tuple[tuple[Bloco, ...], ...]:
    """Corta o livro no maior tamanho de título que aparece em 3 páginas ou mais, e no rótulo
    de capítulo ("CHAPTER 24") que aparece em 3 páginas ou mais.

    No Competente é o número do capítulo (30 pt); no Hard Parts, o título do capítulo
    (25,2 pt); no Bonica, o rótulo, que tem o tamanho da seção (ADR-0004, "Rótulo de
    capítulo"). O que vem antes do primeiro capítulo fica num capítulo de abertura. O capítulo
    só fecha depois de ter texto: a parte e o rótulo ficam com o título que vem logo depois.
    """
    capitulo = _tamanho_do_capitulo(blocos)
    niveis = _niveis(blocos, capitulo)
    com_rotulo = _ha_rotulos(blocos)
    capitulos: list[list[Bloco]] = [[]]
    for bloco in blocos:
        if bloco.tipo is TipoDeBloco.TITULO:
            bloco = replace(bloco, nivel=niveis[round(bloco.tamanho, 1)])  # noqa: PLW2901  # motivo: o mesmo bloco, agora com o nível
            abre = _do_tamanho(bloco, capitulo) or (com_rotulo and _tem_rotulo(bloco))
            if abre and _tem_texto(capitulos[-1]):
                capitulos.append([])
        capitulos[-1].append(bloco)
    return tuple(tuple(capitulo) for capitulo in capitulos if capitulo)


# O rótulo no começo do título, ou depois do nome da subparte em maiúsculas ("NEUROPATHIC PAIN
# CONDITIONS CHAPTER 24 Painful Neuropathies", Bonica p. 1138). O dois-pontos é da linha do
# sumário ("CHAPTER 6: Supraspinal Mechanisms of Pain and 377"), que não abre capítulo.
_ROTULO = re.compile(rf"\b(?:{PALAVRAS_DO_ROTULO})\s+\d+(?=\s|$)")
# A pontuação que liga o rótulo ao título ("CHAPTER 6 — Gate Control") sai do nome.
_LIGACAO = ":.\u2013\u2014- "


def _tem_rotulo(bloco: Bloco) -> bool:
    achado = _ROTULO.search(bloco.texto)
    if achado is None:
        return False
    antes = bloco.texto[: achado.start()]
    return antes == antes.upper()


def nome_do_capitulo(blocos: Sequence[Bloco]) -> str | None:
    """O nome do capítulo no sumário do EPUB: o que o sumário interno do PDF dá, gravado no
    primeiro bloco (ADR-0004, "Capítulos pelo sumário interno do PDF"); sem ele, "Chapter 1: Pain
    Mechanisms", quando um dos títulos da abertura (antes do primeiro texto) traz o rótulo; None
    sem um nem outro.

    O rótulo vai em caixa normal, e o título é o resto do mesmo bloco ou, no rótulo sozinho, o
    título seguinte (ADR-0004, "Rótulo no sumário"). O nome da parte e o da subparte, antes do
    rótulo, ficam de fora: são o primeiro título do capítulo, e o sumário dizia só eles.
    """
    if blocos and blocos[0].capitulo:
        return blocos[0].capitulo
    abertura = list(takewhile(lambda b: b.tipo is TipoDeBloco.TITULO, blocos))
    for posicao, bloco in enumerate(abertura):
        achado = _ROTULO.search(bloco.texto)
        if achado is None or not _tem_rotulo(bloco):
            continue
        palavra, numero = achado.group().split()
        rotulo = f"{palavra.capitalize()} {numero}"
        resto = bloco.texto[achado.end() :].strip(_LIGACAO)
        seguinte = abertura[posicao + 1].texto if posicao + 1 < len(abertura) else ""
        titulo = resto or seguinte
        return f"{rotulo}: {titulo}" if titulo else rotulo
    return None


def _ha_rotulos(blocos: Sequence[Bloco]) -> bool:
    paginas = {b.pagina for b in blocos if b.tipo is TipoDeBloco.TITULO and _tem_rotulo(b)}
    return len(paginas) >= PAGINAS_DO_CAPITULO


def _do_tamanho(bloco: Bloco, capitulo: float | None) -> bool:
    return capitulo is not None and abs(bloco.tamanho - capitulo) <= DIFERENCA_DE_TAMANHO


def _tem_texto(capitulo: Sequence[Bloco]) -> bool:
    return any(b.tipo is not TipoDeBloco.TITULO for b in capitulo)


def _tamanho_do_capitulo(blocos: Sequence[Bloco]) -> float | None:
    paginas_por_tamanho: dict[float, set[int]] = {}
    for bloco in blocos:
        if bloco.tipo is TipoDeBloco.TITULO:
            paginas_por_tamanho.setdefault(round(bloco.tamanho, 1), set()).add(bloco.pagina)
    frequentes = [
        t for t, paginas in paginas_por_tamanho.items() if len(paginas) >= PAGINAS_DO_CAPITULO
    ]
    return max(frequentes) if frequentes else None


def _niveis(blocos: Sequence[Bloco], capitulo: float | None) -> dict[float, int]:
    """Nível 1 para o capítulo e o que for maior que ele; os menores descem, até o 6."""
    tamanhos = sorted(
        {round(b.tamanho, 1) for b in blocos if b.tipo is TipoDeBloco.TITULO}, reverse=True
    )
    topo = capitulo if capitulo is not None else (tamanhos[0] if tamanhos else 0.0)
    menores = [t for t in tamanhos if t < topo - DIFERENCA_DE_TAMANHO]
    niveis = {t: 1 for t in tamanhos if t not in menores}
    niveis.update({t: min(n, 6) for n, t in enumerate(menores, 2)})
    return niveis
