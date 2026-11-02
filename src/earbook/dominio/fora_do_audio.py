# SPDX-License-Identifier: GPL-3.0-or-later
"""O que sai inteiro do texto lido (ADR-0008): pelo papel, o bloco de código e o índice
remissivo; pela repetição, a marca d'água. A limpeza registra cada um, com o motivo daqui.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from earbook.dominio.segmento import PALAVRA, Papel, Segmento

MOTIVO_DO_PAPEL = {Papel.CODIGO: "código-fonte", Papel.INDICE: "índice remissivo"}
# Medido nos sete livros de livros/trabalho/ (2026-11-02): a marca d'água "OceanofPDF.com" está
# em 321 de 321 arquivos do Learning DDD; o parágrafo de verdade que mais se repete está em 6
# arquivos (2%), e a maior fração é 33%, em 2 arquivos do Tides. O título se repete de propósito
# ("Questões de revisão" em 65% do Dalgalarrondo) e não conta.
FRACAO_MINIMA_DA_MARCA = 0.5
# Num livro de poucos arquivos (o Huxley tem 4 com texto), 2 ou 3 iguais ainda são texto.
ARQUIVOS_MINIMOS_DA_MARCA = 10


def pelo_papel(capitulos: Sequence[tuple[str, Sequence[Segmento]]]) -> dict[str, str]:
    """ID → motivo de cada bloco de código e de cada índice remissivo."""
    return {
        segmento.id: MOTIVO_DO_PAPEL[segmento.papel]
        for _, segmentos in capitulos
        for segmento in segmentos
        if segmento.papel in MOTIVO_DO_PAPEL
    }


def marcas_dagua(capitulos: Sequence[tuple[str, Sequence[Segmento]]]) -> dict[str, str]:
    """ID → motivo de cada parágrafo idêntico em metade ou mais dos arquivos com texto, e em 10
    ou mais. Só parágrafo, e só com letra: título, citação e item repetem de propósito, e a pausa
    de cena ("* * *") marca a pausa.
    """
    com_texto = sum(1 for _, segmentos in capitulos if segmentos)
    minimo = max(ARQUIVOS_MINIMOS_DA_MARCA, FRACAO_MINIMA_DA_MARCA * com_texto)
    motivos = {
        texto: f"marca d'água: o mesmo parágrafo em {len(onde)} de {com_texto} arquivos"
        for texto, onde in _arquivos_de_cada_paragrafo(capitulos).items()
        if len(onde) >= minimo
    }
    return {
        segmento.id: motivos[segmento.texto]
        for _, segmentos in capitulos
        for segmento in segmentos
        if _pode_ser_marca(segmento) and segmento.texto in motivos
    }


def _arquivos_de_cada_paragrafo(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]],
) -> dict[str, set[str]]:
    """Texto → capítulos em que ele aparece, contando só o que pode ser marca d'água."""
    arquivos: defaultdict[str, set[str]] = defaultdict(set)
    for capitulo, segmentos in capitulos:
        for segmento in segmentos:
            if _pode_ser_marca(segmento):
                arquivos[segmento.texto].add(capitulo)
    return arquivos


def _pode_ser_marca(segmento: Segmento) -> bool:
    return segmento.papel is Papel.PARAGRAFO and PALAVRA.search(segmento.texto) is not None
