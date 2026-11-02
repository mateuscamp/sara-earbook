# SPDX-License-Identifier: GPL-3.0-or-later
"""O bloco de código e o índice remissivo saem do áudio, registrados (ADR-0008)."""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.adaptadores.xhtml import CapituloSegmentado, segmentar_xhtml
from earbook.comandos.montar import montar
from earbook.comandos.preparar import Preparo, preparar
from earbook.dominio.limpeza import limpar_para_o_ouvido
from earbook.dominio.segmento import Papel, Segmento
from tests.livro_de_teste import montar_epub, xhtml

CAMINHO = "OEBPS/cap1.xhtml"
CSHARP = '<pre data-code-language="csharp"><code>public class Player { }</code></pre>'
# A forma do índice do Learning DDD: o termo pai com subentradas não é bloco-folha, e o texto
# dele, com as vírgulas entre os links, ficava fora de segmento e era lido no livro montado.
INDICE = (
    "<h1>Index</h1><ul><li><span>accidental complexity</span><ul>"
    '<li>case study, <a href="c.xhtml#x">The real problem</a></li>'
    '<li>growth and, <a href="c.xhtml#y">Growth</a></li></ul></li></ul>'
)
TEXTO_DO_INDICE = "Index accidental complexity case study, The real problem growth and, Growth"


def _segmentar(conteudo: bytes) -> CapituloSegmentado:
    return segmentar_xhtml(conteudo, "c001", CAMINHO)


def _papeis(corpo: str) -> list[tuple[str, str]]:
    return [(str(s.papel), s.texto) for s in _segmentar(xhtml(corpo)).segmentos]


def _textos_limpos(preparo: Preparo) -> list[list[str]]:
    return [[s.texto for s in capitulo.segmentos] for capitulo in preparo.limpeza.capitulos]


@pytest.mark.parametrize(
    "bloco",
    [
        '<pre data-code-language="csharp">var x = 1;</pre>',
        '<pre data-type="programlisting">LeadId: 12</pre>',
        "<pre><code>var x = 1;</code></pre>",
    ],
)
def test_bloco_que_se_declara_codigo_tem_papel_codigo(bloco: str) -> None:
    assert [papel for papel, _ in _papeis(bloco)] == ["codigo"]


def test_pre_sem_marca_de_codigo_continua_paragrafo() -> None:
    # O <pre> do importar-pdf: a fonte monoespaçada marca também prosa, como os carimbos da
    # saga do Hard Parts (ADR-0008).
    assert _papeis("<pre>Wednesday, November 3, 13:00</pre>") == [
        ("paragrafo", "Wednesday, November 3, 13:00")
    ]


def test_gherkin_continua_paragrafo_para_ser_traduzido() -> None:
    # Medido no Learning DDD (c044-s0007): o teste que o especialista do domínio lê.
    bloco = (
        '<pre data-type="programlisting" data-code-language="gherkin">'
        "<code>Scenario: Notify the agent</code>\n<code>    Given a new lead</code></pre>"
    )
    assert _papeis(bloco) == [("paragrafo", "Scenario: Notify the agent Given a new lead")]


def test_codigo_em_linha_fica_no_paragrafo() -> None:
    assert _papeis("<p>Call <code>AppendEvent</code> twice.</p>") == [
        ("paragrafo", "Call AppendEvent twice.")
    ]


@pytest.mark.parametrize("marca", ['epub:type="index"', 'role="doc-index"', 'data-type="index"'])
def test_indice_marcado_vira_um_segmento_so_com_todo_o_texto(marca: str) -> None:
    capitulo = _segmentar(xhtml(f"<section {marca}>{INDICE}</section>"))
    assert [(str(s.papel), s.texto) for s in capitulo.segmentos] == [("indice", TEXTO_DO_INDICE)]
    assert capitulo.texto_fora_de_segmento == []


def test_marca_de_indice_dentro_de_outra_nao_abre_segmento_novo() -> None:
    corpo = f'<section epub:type="index"><div data-type="index">{INDICE}</div></section>'
    assert _papeis(corpo) == [("indice", TEXTO_DO_INDICE)]


def test_indice_marcado_no_body_vira_um_segmento_por_filho() -> None:
    conteudo = xhtml(f"<section>{INDICE}</section><p>Symbols, 12</p>")
    conteudo = conteudo.replace(b"<body>", b'<body epub:type="index">')
    assert [(str(s.papel), s.texto) for s in _segmentar(conteudo).segmentos] == [
        ("indice", TEXTO_DO_INDICE),
        ("indice", "Symbols, 12"),
    ]


def test_link_de_indice_no_sumario_continua_item() -> None:
    # O landmarks do nav aponta para o índice com epub:type="index" no <a>, que não é bloco.
    corpo = (
        '<nav epub:type="landmarks"><ol>'
        '<li><a epub:type="index" href="ix.xhtml">Index</a></li></ol></nav>'
    )
    assert _papeis(corpo) == [("item", "Index")]


def test_preparar_tira_codigo_e_indice_e_registra_em_limpeza_json(tmp_path: Path) -> None:
    epub = montar_epub(
        tmp_path / "livro.epub",
        {
            "a.xhtml": f"<p>See the code:</p>{CSHARP}<p>After the code.</p>",
            "ix.xhtml": f'<section epub:type="index">{INDICE}</section>',
        },
    )
    pasta = tmp_path / "livro.earbook"
    preparo = preparar(epub, pasta)
    assert _textos_limpos(preparo) == [["See the code:", "After the code."], []]
    assert [(r.id, r.motivo) for r in preparo.limpeza.remocoes] == [
        ("c001-s0002", "código-fonte"),
        ("c002-s0001", "índice remissivo"),
    ]
    registro = (pasta / "limpeza.json").read_text(encoding="utf-8")
    assert '"motivo": "código-fonte"' in registro
    assert '"motivo": "índice remissivo"' in registro


def test_codigo_continua_separando_os_paragrafos_em_volta(tmp_path: Path) -> None:
    # Sem o bloco no meio, "below" + "and then" seria um parágrafo partido (ADR-0003): o código
    # sai depois da junção, para continuar separando os dois.
    epub = montar_epub(
        tmp_path / "livro.epub",
        {"a.xhtml": f"<p>It runs the code below</p>{CSHARP}<p>and then it stops.</p>"},
    )
    preparo = preparar(epub, tmp_path / "livro.earbook")
    assert _textos_limpos(preparo) == [["It runs the code below", "and then it stops."]]


def test_livro_montado_nao_tem_codigo_nem_indice(tmp_path: Path) -> None:
    epub = montar_epub(
        tmp_path / "livro.epub",
        {
            "a.xhtml": f"<p>Veja o código:</p>{CSHARP}<p>Depois do código.</p>",
            "ix.xhtml": f'<section epub:type="index">{INDICE}</section>',
        },
        idioma="pt-BR",
    )
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    volta = preparar(montagem.epub, tmp_path / "volta.earbook")
    assert _textos_limpos(volta) == [["Veja o código:", "Depois do código."], []]
    assert volta.livro.texto_fora_de_segmento == ()


def test_pista_da_capitular_nao_tira_letra_de_dentro_do_codigo() -> None:
    # A1 da code-audit (ADR-0008): o "N" de "var x = N + 1;" servia de pista, e a devolução o
    # levava para "ight fell…", mexendo no código antes de ele sair.
    codigo = "var x = N + 1;"
    entrada = [
        (
            f"c{c:03d}",
            [
                Segmento(f"c{c:03d}-s0001", Papel.TITULO, f"Chapter {c}"),
                Segmento(f"c{c:03d}-s0002", Papel.PARAGRAFO, f"ight fell over the city {c}."),
                Segmento(f"c{c:03d}-s0003", Papel.CODIGO, codigo),
                Segmento(f"c{c:03d}-s0004", Papel.PARAGRAFO, "Night came again."),
            ],
        )
        for c in range(1, 4)
    ]
    livro = limpar_para_o_ouvido(entrada, "Livro", "Autor")
    assert [r.texto for r in livro.remocoes] == [codigo] * 3
    assert livro.capitulares == ()


def test_indice_no_body_leva_o_bloco_dentro_de_elemento_inline() -> None:
    # A2 da code-audit (ADR-0008): o <p> dentro de um <span> não era filho do <body> e saía
    # como parágrafo, lido e traduzido.
    conteudo = xhtml("<span><p>abstractness, 67</p></span><section><p>B</p></section>")
    conteudo = conteudo.replace(b"<body>", b'<body epub:type="index">')
    assert [(str(s.papel), s.texto) for s in _segmentar(conteudo).segmentos] == [
        ("indice", "abstractness, 67"),
        ("indice", "B"),
    ]


@pytest.mark.parametrize(
    "bloco",
    [
        '<pre><code class="language-gherkin">Scenario: Notify the agent</code></pre>',
        (
            '<pre class="sourceCode gherkin"><code class="sourceCode gherkin">'
            "Scenario: Notify the agent</code></pre>"
        ),
    ],
)
def test_gherkin_marcado_pela_classe_continua_paragrafo(bloco: str) -> None:
    # A3 da code-audit (ADR-0008): a recomendação do HTML (`language-x` no <code>) e o pandoc
    # (`sourceCode gherkin`) marcam a linguagem pela classe, e o Gherkin saía como código.
    assert _papeis(bloco) == [("paragrafo", "Scenario: Notify the agent")]
