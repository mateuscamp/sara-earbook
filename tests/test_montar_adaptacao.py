# SPDX-License-Identifier: GPL-3.0-or-later
"""O `conferir` e o `montar` do livro adaptado, da amostra e do original (ADR-0009)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.comandos.adaptar import adaptar
from earbook.comandos.cli import principal
from earbook.comandos.montar import MontagemRecusadaError, conferir_pasta, montar
from earbook.comandos.preparar import Preparo, preparar
from earbook.dominio.traducao import Modo
from tests.livro_de_teste import montar_epub

CAPITULO_UM = (
    "<h1>Um</h1><h6>Quadro 1.1</h6><p>• Humor deprimido por 2 semanas</p><p>• Anedonia</p>"
    "<p>A anedonia (Del Pino, 2003) é a perda do prazer.</p>"
)
CAPITULO_DOIS = "<h1>Dois</h1><p>O fim da história.</p>"
GRUPOS: dict[str, list[dict[str, object]]] = {
    "c001-l001": [
        {"fontes": ["c001-s0001"], "igual": True},
        {"fontes": ["c001-s0002"], "descarte": "rotulo"},
        {
            "fontes": ["c001-s0003", "c001-s0004"],
            "texto": ["Os critérios são dois.", "Humor deprimido por 2 semanas e anedonia."],
        },
        {"fontes": ["c001-s0005"], "texto": ["A anedonia é a perda do prazer."]},
    ],
    "c002-l001": [
        {"fontes": ["c002-s0001"], "igual": True},
        {"fontes": ["c002-s0002"], "igual": True},
    ],
}


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    capitulos = {"a.xhtml": CAPITULO_UM, "b.xhtml": CAPITULO_DOIS}
    epub = montar_epub(tmp_path / "livro.epub", capitulos, idioma="pt-BR")
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    _ = adaptar(pasta)
    return pasta


def _responder(pasta: Path, grupos: dict[str, list[dict[str, object]]] = GRUPOS) -> None:
    """Responde aos lotes como o agente responde: JSON escrito à mão, por lote."""
    for lote, registros in grupos.items():
        caminho = trabalho.caminho_do_adaptado(pasta, lote)
        _ = caminho.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")


def _papeis_e_textos(preparo: Preparo) -> list[list[tuple[str, str]]]:
    return [[(str(s.papel), s.texto) for s in c.segmentos] for c in preparo.limpeza.capitulos]


def test_livro_adaptado_e_montado_com_n_fontes_em_m_paragrafos(pasta: Path, tmp_path: Path) -> None:
    _responder(pasta)
    assert conferir_pasta(pasta) == ()
    feito = montar(pasta, tmp_path / "livro.pronto.epub")
    assert (feito.capitulos, feito.segmentos, feito.fora) == (2, 5, 0)
    relido = preparar(feito.epub, tmp_path / "relido.earbook")
    assert _papeis_e_textos(relido) == [
        [
            ("titulo", "Um"),
            ("paragrafo", "Os critérios são dois."),
            ("paragrafo", "Humor deprimido por 2 semanas e anedonia."),
            ("paragrafo", "A anedonia é a perda do prazer."),
        ],
        [("titulo", "Dois"), ("paragrafo", "O fim da história.")],
    ]


def test_conferir_do_livro_adaptado_cobra_a_fidelidade(pasta: Path) -> None:
    grupos = dict(GRUPOS)
    grupos["c001-l001"] = [
        *GRUPOS["c001-l001"][:2],
        {"fontes": ["c001-s0003", "c001-s0004"], "texto": ["Humor deprimido e anedonia."]},
        GRUPOS["c001-l001"][3],
    ]
    _responder(pasta, grupos)
    assert [(p.id, p.motivo) for p in conferir_pasta(pasta)] == [
        ("c001-s0003", "o número 2 das fontes não está no texto")
    ]


def test_montar_recusa_o_livro_com_segmento_sem_adaptacao(pasta: Path, tmp_path: Path) -> None:
    _responder(pasta, {"c001-l001": GRUPOS["c001-l001"]})
    with pytest.raises(MontagemRecusadaError, match="c002: 2 segmentos sem adaptação"):
        _ = montar(pasta, tmp_path / "livro.pronto.epub")


def test_amostra_monta_so_o_adaptado(pasta: Path, tmp_path: Path) -> None:
    _responder(pasta, {"c001-l001": GRUPOS["c001-l001"]})
    feito = montar(pasta, tmp_path / "livro.amostra.epub", Modo.AMOSTRA)
    assert (feito.segmentos, feito.fora) == (3, 2)
    relido = preparar(feito.epub, tmp_path / "relido.earbook")
    assert [len(c) for c in _papeis_e_textos(relido)] == [4, 0]


def test_original_monta_o_texto_limpo_do_livro_em_adaptacao(pasta: Path, tmp_path: Path) -> None:
    feito = montar(pasta, tmp_path / "livro.original.epub", Modo.ORIGINAL)
    relido = preparar(feito.epub, tmp_path / "relido.earbook")
    assert _papeis_e_textos(relido)[0][2] == ("paragrafo", "• Humor deprimido por 2 semanas")


def test_cli_conferir_lista_os_avisos_sem_recusar(
    pasta: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    grupos = dict(GRUPOS)
    grupos["c002-l001"] = [
        {"fontes": ["c002-s0001"], "igual": True},
        {"fontes": ["c002-s0002"], "descarte": "decisao: o que sai do áudio"},
    ]
    _responder(pasta, grupos)
    assert principal(["conferir", str(pasta)]) == 0
    saida = capsys.readouterr().out
    assert "1 aviso, que não recusa o livro:" in saida
    assert "  c002-s0002: descartado por decisão: o que sai do áudio" in saida


def test_item_do_sumario_em_descarte_ou_juntado_e_acusado(tmp_path: Path) -> None:
    """A7 da auditoria: no sumário nada sai (ADR-0005); o descarte ficava no original calado."""
    sumario = (
        '<nav epub:type="toc"><ol><li><a href="b.xhtml">Dois</a></li>'
        '<li><a href="b.xhtml#fim">Fim</a></li></ol></nav>'
    )
    epub = montar_epub(
        tmp_path / "livro.epub", {"nav.xhtml": sumario, "b.xhtml": CAPITULO_DOIS}, idioma="pt-BR"
    )
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    _ = adaptar(pasta)
    _responder(
        pasta,
        {
            "c001-l001": [
                {"fontes": ["c001-s0001"], "descarte": "rotulo"},
                {"fontes": ["c001-s0002"], "igual": True},
            ],
            "c002-l001": [{"fontes": ["c002-s0001", "c002-s0002"], "texto": ["Dois.", "O fim."]}],
        },
    )
    assert [(p.id, p.motivo) for p in conferir_pasta(pasta) if "sumário" in p.motivo] == [
        ("c001-s0001", "item do sumário não sai nem se junta: use igual ou um texto só dele")
    ]


def test_cli_amostra_do_livro_adaptado_diz_sem_adaptacao(
    pasta: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """O resumo dizia "sem tradução" no livro em português, que não se traduz."""
    _responder(pasta, {"c001-l001": GRUPOS["c001-l001"]})
    destino = tmp_path / "livro.amostra.epub"
    assert principal(["montar", str(pasta), "--amostra", "--epub", str(destino)]) == 0
    assert "Amostra: 2 sem adaptação ficaram de fora." in capsys.readouterr().out
