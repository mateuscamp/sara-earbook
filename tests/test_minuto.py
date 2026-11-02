# SPDX-License-Identifier: GPL-3.0-or-later
"""Em que minuto da escuta cai cada segmento (ADR-0007): a conta do roteiro de escuta, que no
Tides foi feita à mão, a 160 palavras por minuto."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.comandos.cli import principal
from earbook.comandos.preparar import preparar
from earbook.comandos.traduzir import traduzir
from earbook.dominio.escuta import Posicao, SegmentoDesconhecidoError, posicoes
from earbook.dominio.segmento import Papel, Segmento
from tests.livro_de_teste import montar_epub


def _paragrafo(id_: str, palavras: int) -> Segmento:
    return Segmento(id_, Papel.PARAGRAFO, " ".join(["palavra"] * palavras))


def test_minuto_conta_as_palavras_antes_do_segmento_no_livro_e_no_capitulo() -> None:
    capitulos = [
        ("c001", [_paragrafo("c001-s0001", 320), _paragrafo("c001-s0002", 10)]),
        ("c002", [_paragrafo("c002-s0001", 170), _paragrafo("c002-s0002", 5)]),
    ]
    assert posicoes(capitulos, ["c002-s0002", "c001-s0001"]) == (
        Posicao("c002-s0002", "c002", minuto_no_livro=3, minuto_no_capitulo=1),
        Posicao("c001-s0001", "c001", minuto_no_livro=0, minuto_no_capitulo=0),
    )


def test_id_que_o_livro_nao_tem_e_recusado_com_o_id() -> None:
    with pytest.raises(SegmentoDesconhecidoError, match="c009-s0001"):
        _ = posicoes([("c001", [_paragrafo("c001-s0001", 3)])], ["c009-s0001"])


def test_cli_conta_pela_traducao_quando_ela_existe(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # O original tem 400 palavras antes; a tradução, 170: o minuto é o do livro que se ouve.
    corpo = f"<p>{' '.join(['word'] * 400)}</p><p>The end.</p>"
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": corpo})
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    _ = traduzir(pasta, palavras=1000)
    resposta = [
        {"id": "c001-s0001", "texto": " ".join(["palavra"] * 170)},
        {"id": "c001-s0002", "texto": "O fim."},
    ]
    caminho = trabalho.caminho_da_resposta(pasta, "c001-l001")
    _ = caminho.write_text(json.dumps(resposta), encoding="utf-8")
    assert principal(["minuto", str(pasta), "c001-s0002"]) == 0
    assert "c001-s0002: minuto 1 do livro; minuto 1 do capítulo c001" in capsys.readouterr().out
