# SPDX-License-Identifier: GPL-3.0-or-later
"""Termo declarado pelo tradutor e cobrado pelo `conferir` (ADR-0007).

No Tides, *stormhammer* saiu "martelo da tempestade" no c005 e "martelo de tempestade" no c006,
e nenhuma ferramenta viu. O tradutor declara em `termos/<lote>.json` o que decidiu fora do
glossário, e o `conferir` cobra que a sessão escolha a forma e a ponha no glossário.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.comandos.cli import principal
from earbook.comandos.preparar import preparar
from earbook.comandos.traduzir import traduzir
from earbook.dominio.conferencia import Problema
from earbook.dominio.conferencia_da_traducao import conferir_termos
from earbook.dominio.glossario import EntradaDoGlossario, TermosDoLote
from tests.livro_de_teste import montar_epub

DA = EntradaDoGlossario("stormhammer", "martelo da tempestade")
DE = EntradaDoGlossario("stormhammer", "martelo de tempestade")


def _conferir(
    termos: tuple[TermosDoLote, ...],
    glossario: tuple[EntradaDoGlossario, ...] = (),
    *,
    amostra: bool = False,
) -> tuple[Problema, ...]:
    return tuple(conferir_termos(termos, glossario, amostra=amostra))


def test_termo_declarado_fora_do_glossario_lista_as_formas_e_os_lotes() -> None:
    termos = (TermosDoLote("c005-l001", (DA,)), TermosDoLote("c006-l004", (DE,)))
    assert _conferir(termos) == (
        Problema(
            "glossário",
            (
                "'stormhammer' fora do glossário, declarado como 'martelo da tempestade'"
                " (c005-l001) e 'martelo de tempestade' (c006-l004): escolha a forma e acrescente"
            ),
        ),
    )


def test_termo_declarado_que_o_glossario_tem_igual_nao_e_problema() -> None:
    assert _conferir((TermosDoLote("c005-l001", (DA,)),), (DA,)) == ()


def test_termo_declarado_com_outra_forma_e_problema_do_lote() -> None:
    # O glossário escolheu "da"; o lote que declarou "de" corrige a resposta e a declaração.
    problemas = _conferir((TermosDoLote("c006-l004", (DE,)),), (DA,))
    assert problemas == (
        Problema(
            "c006-l004",
            (
                "declarou 'stormhammer' → 'martelo de tempestade', mas o glossário diz"
                " 'martelo da tempestade': corrija a resposta e a declaração"
            ),
        ),
    )


def test_na_amostra_o_termo_fora_do_glossario_espera_a_escuta() -> None:
    # A escolha da amostra entra no glossário depois da escuta (AGENTS.md): não recusa antes.
    assert _conferir((TermosDoLote("c005-l001", (DA,)),), amostra=True) == ()


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    capitulos = {
        "a.xhtml": "<h1>One</h1><p>He raised the stormhammer high.</p>",
        "b.xhtml": "<h1>Two</h1><p>She held a stormhammer too.</p>",
    }
    epub = montar_epub(tmp_path / "livro.epub", capitulos)
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    _ = traduzir(pasta)
    return pasta


def _gravar(caminho: Path, conteudo: object) -> None:
    _ = caminho.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")


def _traduzir_tudo(pasta: Path) -> None:
    textos = {
        "c001-l001": {
            "c001-s0001": "Um",
            "c001-s0002": "Ele ergueu bem alto o martelo da tempestade.",
        },
        "c002-l001": {"c002-s0001": "Dois", "c002-s0002": "Ela segurava um martelo de tempestade."},
    }
    for lote, traducao in textos.items():
        registros = [{"id": id_, "texto": texto} for id_, texto in traducao.items()]
        _gravar(trabalho.caminho_da_resposta(pasta, lote), registros)


def test_traduzir_cria_a_pasta_dos_termos(pasta: Path) -> None:
    assert trabalho.caminho_dos_termos(pasta, "c001-l001").parent.is_dir()


def test_termos_gravados_pelo_tradutor_sao_lidos_por_lote(pasta: Path) -> None:
    _gravar(
        trabalho.caminho_dos_termos(pasta, "c001-l001"),
        [{"original": "stormhammer", "traducao": "martelo da tempestade"}],
    )
    assert trabalho.ler_termos(pasta) == (TermosDoLote("c001-l001", (DA,)),)


def test_arquivo_de_termos_fora_do_nome_de_lote_e_recusado(pasta: Path) -> None:
    _gravar(trabalho.caminho_dos_termos(pasta, "c001-l001").parent / "notas.json", [])
    with pytest.raises(ValueError, match=r"notas\.json"):
        _ = trabalho.ler_termos(pasta)


def test_cli_conferir_mostra_o_termo_dos_dois_tradutores(
    pasta: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _traduzir_tudo(pasta)
    _gravar(
        trabalho.caminho_dos_termos(pasta, "c001-l001"),
        [{"original": "stormhammer", "traducao": "martelo da tempestade"}],
    )
    _gravar(
        trabalho.caminho_dos_termos(pasta, "c002-l001"),
        [{"original": "stormhammer", "traducao": "martelo de tempestade"}],
    )
    assert principal(["conferir", str(pasta)]) == 1
    assert "'stormhammer' fora do glossário" in capsys.readouterr().out


def test_conferir_de_um_capitulo_so_esconde_os_outros_e_o_glossario(
    pasta: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Item 3 da lista do Tides: o tradutor do c005 via os problemas do c007 em andamento.
    _traduzir_tudo(pasta)
    _gravar(
        trabalho.caminho_dos_termos(pasta, "c002-l001"),
        [{"original": "stormhammer", "traducao": "martelo de tempestade"}],
    )
    _gravar(
        trabalho.caminho_do_glossario(pasta),
        [{"original": "stormhammer", "traducao": "martelo da tempestade"}],
    )
    assert principal(["conferir", str(pasta), "--capitulo", "c001"]) == 0
    # Lote A da revisão: "pode montar" escondia o resto do livro, que não foi conferido.
    assert "nada a corrigir no capítulo c001" in capsys.readouterr().out
    assert principal(["conferir", str(pasta), "--capitulo", "c002"]) == 1
    saida = capsys.readouterr().out
    assert "c002-l001: declarou 'stormhammer'" in saida
    assert "c001" not in saida.replace(str(pasta), "")


def test_traduzir_cria_as_decisoes_do_livro_uma_vez_so(pasta: Path) -> None:
    decisoes = trabalho.caminho_das_decisoes(pasta)
    assert "Nome fora do glossário" in decisoes.read_text(encoding="utf-8")
    _ = decisoes.write_text("# Decisões\n\nNome: a localização oficial.\n", encoding="utf-8")
    _ = traduzir(pasta)
    assert decisoes.read_text(encoding="utf-8") == "# Decisões\n\nNome: a localização oficial.\n"


def test_traduzir_diz_as_palavras_pendentes_de_cada_capitulo(
    pasta: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # "One" + "He raised the stormhammer high." são 6 palavras: a conta da divisão e do custo.
    assert principal(["traduzir", str(pasta)]) == 0
    saida = capsys.readouterr().out
    assert "  c001: 0 de 2; pendentes: c001-l001 (6 palavras)" in saida
    assert "decisoes.md" in saida


def test_conferir_recusa_capitulo_que_o_livro_nao_tem(
    pasta: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Lote A da revisão: "--capitulo c5" filtrava tudo e dizia "pode montar", com código 0.
    _traduzir_tudo(pasta)
    _gravar(trabalho.caminho_dos_termos(pasta, "c002-l001"), [{"original": "x", "traducao": "y"}])
    assert principal(["conferir", str(pasta), "--capitulo", "c5"]) == 1
    erro = capsys.readouterr().err
    assert "'c5'" in erro
    assert "c001, c002" in erro
