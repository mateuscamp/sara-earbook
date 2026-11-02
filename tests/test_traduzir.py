# SPDX-License-Identifier: GPL-3.0-or-later
"""O comando `traduzir` de ponta a ponta (ADR-0006)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.comandos.cli import principal
from earbook.comandos.preparar import preparar
from earbook.comandos.traduzir import (
    CapituloNaTraducao,
    IdiomaIndefinidoError,
    TraducaoDesnecessariaError,
    traduzir,
)
from tests.livro_de_teste import montar_epub

CAPITULO_UM = (
    "<h1>One</h1><p>Then Lothar rode north with the others.</p>"
    "<p>They saw Lothar at the gate of the city.</p>"
)
CAPITULO_DOIS = "<h1>Two</h1><p>The end of the story.</p>"


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": CAPITULO_UM, "b.xhtml": CAPITULO_DOIS})
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    return pasta


def _responder(pasta: Path, lote: str, textos: dict[str, str]) -> None:
    """Grava a resposta como o agente grava: JSON escrito à mão."""
    registros = [{"id": id_, "texto": texto} for id_, texto in textos.items()]
    _ = trabalho.caminho_da_resposta(pasta, lote).write_text(json.dumps(registros))


def test_traduzir_pede_cada_capitulo_em_lotes(pasta: Path) -> None:
    exportacao = traduzir(pasta, palavras=8)
    assert exportacao.novos == 3
    assert exportacao.capitulos == (
        CapituloNaTraducao("c001", 3, 0, ("c001-l001", "c001-l002")),
        CapituloNaTraducao("c002", 2, 0, ("c002-l001",)),
    )
    assert [s.id for s in trabalho.ler_pedidos(pasta)[0].segmentos] == ["c001-s0001", "c001-s0002"]


def test_rodar_de_novo_nao_refaz_nenhum_pedido(pasta: Path) -> None:
    _ = traduzir(pasta, palavras=8)
    antes = trabalho.ler_pedidos(pasta)
    assert traduzir(pasta, palavras=1000).novos == 0
    assert trabalho.ler_pedidos(pasta) == antes


def test_lote_respondido_conta_como_traduzido(pasta: Path) -> None:
    _ = traduzir(pasta)
    _responder(pasta, "c002-l001", {"c002-s0001": "Dois", "c002-s0002": "O fim da história."})
    assert traduzir(pasta).capitulos == (
        CapituloNaTraducao("c001", 3, 0, ("c001-l001",)),
        CapituloNaTraducao("c002", 2, 2, ()),
    )


def test_candidatos_a_nome_vao_para_o_agente(pasta: Path) -> None:
    exportacao = traduzir(pasta)
    assert exportacao.candidatos == 1
    assert '"nome": "Lothar"' in exportacao.nomes.read_text(encoding="utf-8")


def test_livro_em_portugues_nao_e_traduzido(tmp_path: Path) -> None:
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": "<p>Texto.</p>"}, idioma="pt-BR")
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    with pytest.raises(TraducaoDesnecessariaError, match="pt-BR"):
        _ = traduzir(pasta)
    assert not (pasta / "pedidos").exists()


def test_cli_traduzir_diz_o_que_falta_e_onde_gravar(
    pasta: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert principal(["traduzir", str(pasta), "--palavras", "8"]) == 0
    saida = capsys.readouterr().out
    assert "0 de 5 segmentos traduzidos" in saida
    assert "c001: 0 de 3; pendentes: c001-l001, c001-l002" in saida
    assert str(pasta / "traduzidos") in saida


def test_livro_de_idioma_indefinido_pede_o_idioma(tmp_path: Path) -> None:
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": "<p>Texto.</p>"}, idioma="und")
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    with pytest.raises(IdiomaIndefinidoError, match=r"'und'.*--idioma"):
        _ = traduzir(pasta)
    assert not (pasta / "pedidos").exists()


def test_capitulo_sem_segmento_nao_entra_no_estado(tmp_path: Path) -> None:
    capitulos = {"capa.xhtml": "<div></div>", "a.xhtml": "<p>Texto in English.</p>"}
    epub = montar_epub(tmp_path / "livro.epub", capitulos)
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    assert [c.capitulo for c in traduzir(pasta).capitulos] == ["c002"]


def test_nome_que_ja_esta_no_glossario_nao_volta_como_candidato(pasta: Path) -> None:
    _ = trabalho.caminho_do_glossario(pasta).write_text(
        json.dumps([{"original": "Lothar", "traducao": "Lothar"}])
    )
    assert traduzir(pasta).candidatos == 0


def test_pedido_apagado_volta_com_numero_novo_e_nao_casa_com_a_resposta_velha(
    pasta: Path,
) -> None:
    # Achado da code-review, de ponta a ponta: apagado só o pedido, a resposta velha
    # vira "resposta sem pedido" no `conferir`, em vez de passar.
    _ = traduzir(pasta)
    _responder(pasta, "c002-l001", {"c002-s0001": "Dois", "c002-s0002": "O fim."})
    trabalho.caminho_do_pedido(pasta, "c002-l001").unlink()
    assert traduzir(pasta).capitulos[1].pendentes == ("c002-l002",)
