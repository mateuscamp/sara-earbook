# SPDX-License-Identifier: GPL-3.0-or-later
"""As siglas candidatas do livro em espanhol (ADR-0013); as do português estão em
`test_adaptacao.py` (ADR-0009)."""

from __future__ import annotations

import pytest

from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.siglas import siglas_candidatas


@pytest.mark.parametrize(
    ("frase", "extenso"),
    [
        (
            "El síndrome del distrés respiratorio agudo (SDRA) es frecuente.",
            "síndrome del distrés respiratorio agudo",
        ),
        (
            (
                "Presidente de la Asociación de Anestesia, Analgesia y Reanimación de Buenos"
                " Aires (AAARBA)."
            ),
            "Asociación de Anestesia, Analgesia y Reanimación de Buenos Aires",
        ),
        (
            "La unidad de cuidados de los pacientes intensivos (UCPI) del hospital.",
            "unidad de cuidados de los pacientes intensivos",
        ),
        (
            "El volumen de la sangre (VS) circulante.",
            "volumen de la sangre",
        ),
    ],
)
def test_extenso_em_espanhol_pula_del_la_los_e_y(frase: str, extenso: str) -> None:
    segmentos = [Segmento("c001-s0001", Papel.PARAGRAFO, frase)]
    assert [c.extenso for c in siglas_candidatas(segmentos, ())] == [extenso]
