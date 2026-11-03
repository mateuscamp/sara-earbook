# SPDX-License-Identifier: GPL-3.0-or-later
"""O comando `adaptar` de ponta a ponta (ADR-0009)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.comandos.adaptar import (
    AdaptacaoSoEmPortuguesError,
    CapituloNaAdaptacao,
    adaptar,
)
from earbook.comandos.cli import principal
from earbook.comandos.preparar import preparar
from tests.livro_de_teste import montar_epub

CAPITULO_UM = (
    "<h1>Um</h1><p>O sistema reticular ativador ascendente (SRAA) regula a vigília.</p>"
    "<h2>Distimia</h2><p>O SRAA se origina no tronco cerebral, segundo a OMS.</p>"
)
CAPITULO_DOIS = "<h1>Dois</h1><p>O fim da história.</p>"


def _preparado(tmp_path: Path, idioma: str = "pt-BR") -> Path:
    capitulos = {"a.xhtml": CAPITULO_UM, "b.xhtml": CAPITULO_DOIS}
    epub = montar_epub(tmp_path / "livro.epub", capitulos, idioma=idioma)
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    return pasta


def test_adaptar_recusa_o_livro_que_nao_esta_em_portugues(tmp_path: Path) -> None:
    pasta = _preparado(tmp_path, idioma="en")
    with pytest.raises(AdaptacaoSoEmPortuguesError, match="'en'"):
        _ = adaptar(pasta)
    assert not trabalho.ha_adaptacao(pasta)


def test_adaptar_pede_cada_capitulo_em_lotes_que_terminam_antes_do_titulo(tmp_path: Path) -> None:
    pasta = _preparado(tmp_path)
    exportacao = adaptar(pasta, palavras=12)
    assert exportacao.novos == 3
    assert exportacao.capitulos == (
        CapituloNaAdaptacao("c001", 4, 0, ("c001-l001", "c001-l002")),
        CapituloNaAdaptacao("c002", 2, 0, ("c002-l001",)),
    )
    lotes = [[s.id for s in p.segmentos] for p in trabalho.ler_pedidos_da_adaptacao(pasta)]
    assert lotes[:2] == [["c001-s0001", "c001-s0002"], ["c001-s0003", "c001-s0004"]]
    assert exportacao.palavras_pendentes == {"c001": 21, "c002": 5}


def test_adaptar_grava_as_siglas_candidatas_e_o_modelo_das_decisoes(tmp_path: Path) -> None:
    pasta = _preparado(tmp_path)
    exportacao = adaptar(pasta)
    assert exportacao.siglas == 2
    esperado = [
        {
            "sigla": "SRAA",
            "vezes": 2,
            "exemplo": "c001-s0002",
            "extenso": "sistema reticular ativador ascendente",
        },
        {"sigla": "OMS", "vezes": 1, "exemplo": "c001-s0004", "extenso": ""},
    ]
    texto = json.dumps(esperado, ensure_ascii=False, indent=2) + "\n"
    assert exportacao.caminho_das_siglas.read_text(encoding="utf-8") == texto
    assert "## Citação" in exportacao.decisoes.read_text(encoding="utf-8")


def test_rodar_de_novo_nao_refaz_pedido_nem_as_decisoes(tmp_path: Path) -> None:
    pasta = _preparado(tmp_path)
    exportacao = adaptar(pasta, palavras=12)
    _ = exportacao.decisoes.write_text("# A sessão escreveu\n", encoding="utf-8")
    antes = trabalho.ler_pedidos_da_adaptacao(pasta)
    assert adaptar(pasta, palavras=1000).novos == 0
    assert trabalho.ler_pedidos_da_adaptacao(pasta) == antes
    assert exportacao.decisoes.read_text(encoding="utf-8") == "# A sessão escreveu\n"


def test_grupo_respondido_conta_como_adaptado(tmp_path: Path) -> None:
    pasta = _preparado(tmp_path)
    _ = adaptar(pasta)
    resposta = [
        {"fontes": ["c002-s0001"], "igual": True},
        {"fontes": ["c002-s0002"], "texto": ["O fim da história."]},
    ]
    caminho = trabalho.caminho_do_adaptado(pasta, "c002-l001")
    _ = caminho.write_text(json.dumps(resposta), encoding="utf-8")
    assert adaptar(pasta).capitulos[1] == CapituloNaAdaptacao("c002", 2, 2, ())


def test_cli_adaptar_diz_os_lotes_e_onde_gravar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pasta = _preparado(tmp_path)
    assert principal(["adaptar", str(pasta)]) == 0
    saida = capsys.readouterr().out
    assert "2 lotes novos pedidos em" in saida
    assert "  c001: 0 de 4; pendentes: c001-l001 (21 palavras)" in saida
    assert str(trabalho.caminho_do_adaptado(pasta, "<lote>")) in saida
    assert "2 siglas fora do glossário" in saida
