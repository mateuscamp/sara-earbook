# SPDX-License-Identifier: GPL-3.0-or-later
"""O texto girado sai do áudio (ADR-0004, "Texto girado").

No Practical, a tabela dos programas de reabilitação (p. 70 a 73) vem deitada na página: as
letras têm a matriz de lado, e o pdfminer, que monta a linha na horizontal, lia uma letra de cada
coluna ("d u r n n n o o , i i t f e i s n a n k…"), 9.664 palavras no c005. O rótulo de eixo de
gráfico, de lado, vinha do mesmo jeito ("e s o d n o i t a i d a r").
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.comandos.cli import principal
from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.tabelas_e_figuras import MOTIVO_DO_TEXTO_GIRADO, tirar_texto_girado
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf


def _linha(texto: str, topo: float, *, girada: bool = False) -> Linha:
    return Linha(texto, x=42.0, fim=296.0, topo=topo, tamanho=10.0, girada=girada)


def _corpo(topo: float, n: int = 12) -> list[Linha]:
    return [_linha(f"Texto corrido da linha {k} do livro.", topo + 0.014 * k) for k in range(n)]


def test_linha_girada_sai_registrada_com_a_pagina() -> None:
    deitada = [_linha("d u r n n", 0.5, girada=True), _linha("o o , i i", 0.6, girada=True)]
    paginas = [
        Pagina(1, tuple(_corpo(0.1))),
        Pagina(2, tuple(deitada)),
        Pagina(3, (_linha("Fim.", 0.1),)),
    ]
    limpas = tirar_texto_girado(paginas)
    assert [[linha.texto for linha in p.linhas] for p in limpas.paginas][1:] == [[], ["Fim."]]
    assert [(r.pagina, r.motivo, r.texto) for r in limpas.remocoes] == [
        (2, MOTIVO_DO_TEXTO_GIRADO, "d u r n n"),
        (2, MOTIVO_DO_TEXTO_GIRADO, "o o , i i"),
    ]


def test_livro_quase_todo_girado_nao_muda() -> None:
    # O PDF com a página toda de lado (o `/Rotate` que o pdfminer aplica à matriz) é o próprio
    # livro, e não uma tabela no meio dele.
    deitadas = [
        _linha(f"Texto corrido da linha {k} do livro.", 0.1 + 0.014 * k, girada=True)
        for k in range(12)
    ]
    paginas = [Pagina(1, (*deitadas, _linha("Nota de pé.", 0.9)))]
    assert tirar_texto_girado(paginas).remocoes == ()


def test_importar_pdf_tira_a_tabela_deitada_e_o_resumo_a_conta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpo = [
        LinhaDeTeste(f"Linha {n} do texto corrido do livro.", 72, 700 - 14 * n) for n in range(12)
    ]
    deitada = [
        LinhaDeTeste("Sweden Health System", 300 + 12 * n, 200, girada=True) for n in range(3)
    ]
    pdf = montar_pdf(tmp_path / "livro.pdf", [corpo, deitada])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub")
    motivos = {r.motivo for r in importacao.remocoes}
    assert motivos == {MOTIVO_DO_TEXTO_GIRADO}
    assert all(r.pagina == 2 for r in importacao.remocoes)
    assert principal(["importar-pdf", str(pdf), "--epub", str(tmp_path / "outro.epub")]) == 0
    saida = capsys.readouterr().out
    removidas = len(importacao.remocoes)
    assert f"{removidas} linhas de tabela, figura e página de lista tiradas." in saida
    assert f"  {MOTIVO_DO_TEXTO_GIRADO}: {removidas}" in saida
