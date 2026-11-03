# SPDX-License-Identifier: GPL-3.0-or-later
"""A resposta da adaptação, lida da pasta e validada campo a campo (ADR-0009)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.adaptadores.registros_da_pasta import PastaDeTrabalhoInvalidaError
from earbook.dominio.adaptacao import Grupo, Omitido, RespostaDaAdaptacao, TipoDoGrupo
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.traducao import Pedido


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    pasta = tmp_path / "livro.earbook"
    pasta.mkdir()
    trabalho.criar_pastas_da_adaptacao(pasta)
    return pasta


def _responder(pasta: Path, grupos: object, lote: str = "c005-l001") -> None:
    caminho = trabalho.caminho_do_adaptado(pasta, lote)
    _ = caminho.write_text(json.dumps(grupos, ensure_ascii=False), encoding="utf-8")


def test_resposta_com_os_tres_tipos_de_grupo_e_lida(pasta: Path) -> None:
    _responder(
        pasta,
        [
            {"fontes": ["c005-s0001"], "igual": True},
            {"fontes": ["c005-s0002"], "descarte": "rotulo"},
            {
                "fontes": ["c005-s0003", "c005-s0004"],
                "texto": ["Um.", "Dois."],
                "omitidos": [{"termo": "Minimental", "motivo": "o nome ao lado"}],
            },
        ],
    )
    assert trabalho.ler_adaptados(pasta) == (
        RespostaDaAdaptacao(
            "c005-l001",
            (
                Grupo(("c005-s0001",), TipoDoGrupo.IGUAL),
                Grupo(("c005-s0002",), TipoDoGrupo.DESCARTE, descarte="rotulo"),
                Grupo(
                    ("c005-s0003", "c005-s0004"),
                    TipoDoGrupo.TEXTO,
                    texto=("Um.", "Dois."),
                    omitidos=(Omitido("Minimental", "o nome ao lado"),),
                ),
            ),
        ),
    )


@pytest.mark.parametrize(
    ("grupo", "motivo"),
    [
        ({"fontes": ["c005-s0001"], "igual": True, "texto": ["Um."]}, "um só de"),
        ({"fontes": ["c005-s0001"]}, "um só de"),
        ({"fontes": ["c005-s0001"], "igual": False}, "'igual'"),
        ({"fontes": ["c005-s0001"], "texto": "Um."}, "'texto'"),
        ({"fontes": ["c005-s0001"], "texto": ["Um.", 2]}, "'texto'"),
        ({"fontes": ["c005-s0001"], "texto": []}, "'texto' vazio"),
        ({"fontes": [], "igual": True}, "'fontes' vazio"),
        ({"fontes": "c005-s0001", "igual": True}, "esperava uma lista"),
        ({"fontes": ["c005-s0001"], "descarte": 3}, "'descarte'"),
        ({"fontes": ["c005-s0001"], "igual": True, "omitidos": []}, "'omitidos'"),
        ({"fontes": ["c005-s0001"], "texto": ["Um."], "omitidos": [{"termo": "x"}]}, "'motivo'"),
    ],
)
def test_grupo_fora_do_formato_e_recusado_com_o_arquivo(
    pasta: Path, grupo: dict[str, object], motivo: str
) -> None:
    _responder(pasta, [grupo])
    with pytest.raises(PastaDeTrabalhoInvalidaError, match=rf"c005-l001\.json.*{motivo}"):
        _ = trabalho.ler_adaptados(pasta)


def test_resposta_por_link_simbolico_e_recusada(pasta: Path, tmp_path: Path) -> None:
    alvo = tmp_path / "outro.json"
    _ = alvo.write_text("[]", encoding="utf-8")
    trabalho.caminho_do_adaptado(pasta, "c005-l001").symlink_to(alvo)
    with pytest.raises(PastaDeTrabalhoInvalidaError, match="link simbólico"):
        _ = trabalho.ler_adaptados(pasta)


def test_pedido_da_adaptacao_gravado_nao_e_reescrito(pasta: Path) -> None:
    pedido = Pedido("c005-l001", (Segmento("c005-s0001", Papel.PARAGRAFO, "Texto."),))
    trabalho.gravar_pedido_da_adaptacao(pasta, pedido)
    assert trabalho.ler_pedidos_da_adaptacao(pasta) == (pedido,)
    with pytest.raises(FileExistsError):
        trabalho.gravar_pedido_da_adaptacao(pasta, pedido)


def test_sem_pasta_da_adaptacao_o_livro_nao_esta_em_adaptacao(tmp_path: Path) -> None:
    pasta = tmp_path / "livro.earbook"
    pasta.mkdir()
    assert not trabalho.ha_adaptacao(pasta)
    trabalho.criar_pastas_da_adaptacao(pasta)
    assert trabalho.ha_adaptacao(pasta)
