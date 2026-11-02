# SPDX-License-Identifier: GPL-3.0-or-later
"""O `conferir` e o `montar` do livro traduzido, da amostra e do original (ADR-0006)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.comandos.cli import principal
from earbook.comandos.montar import (
    ModoInvalidoError,
    MontagemRecusadaError,
    conferir_pasta,
    epub_padrao,
    montar,
)
from earbook.comandos.preparar import Preparo, preparar
from earbook.comandos.traduzir import traduzir
from earbook.dominio.traducao import Modo
from tests.livro_de_teste import montar_epub

CAPITULO_UM = (
    '<div xml:lang="en"><h1>One</h1><p>The text of the first chapter.</p>'
    '<p xml:lang="fr">Les Zinnias ont l\u2019air d\u2019être en tôle vernie.</p>'
    '<aside epub:type="footnote"><p>1 See the note.</p></aside></div>'
)
CAPITULO_DOIS = "<h1>Two</h1><p>The end of the story.</p>"
TRADUCAO = {
    "c001-s0001": "Um",
    "c001-s0002": "O texto do primeiro capítulo.",
    "c001-s0003": "Les Zinnias ont l\u2019air d\u2019être en tôle vernie.",
    "c001-s0004": "1 Ver a nota.",
    "c002-s0001": "Dois",
    "c002-s0002": "O fim da história.",
}


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": CAPITULO_UM, "b.xhtml": CAPITULO_DOIS})
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    _ = traduzir(pasta)
    return pasta


def _responder(pasta: Path, capitulos: tuple[str, ...] = ("c001", "c002")) -> None:
    """Responde aos lotes como o agente responde: JSON escrito à mão, por lote."""
    for pedido in trabalho.ler_pedidos(pasta):
        if pedido.lote.split("-")[0] in capitulos:
            registros = [{"id": s.id, "texto": TRADUCAO[s.id]} for s in pedido.segmentos]
            caminho = trabalho.caminho_da_resposta(pasta, pedido.lote)
            _ = caminho.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")


def _papeis_e_textos(preparo: Preparo) -> list[list[tuple[str, str]]]:
    return [[(str(s.papel), s.texto) for s in c.segmentos] for c in preparo.limpeza.capitulos]


def _membro(epub: Path, nome: str) -> str:
    with zipfile.ZipFile(epub) as zip_:
        return zip_.read(nome).decode("utf-8")


def test_livro_traduzido_e_montado_so_com_a_traducao(pasta: Path, tmp_path: Path) -> None:
    _responder(pasta)
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    assert (montagem.capitulos, montagem.segmentos, montagem.notas) == (2, 6, 1)
    assert _papeis_e_textos(preparar(montagem.epub, tmp_path / "volta.earbook")) == [
        [
            ("titulo", "Um"),
            ("paragrafo", "O texto do primeiro capítulo."),
            ("paragrafo", "Les Zinnias ont l\u2019air d\u2019être en tôle vernie."),
            ("titulo", "Notas"),
            ("paragrafo", "1 Ver a nota."),
        ],
        [("titulo", "Dois"), ("paragrafo", "O fim da história.")],
    ]


def test_livro_traduzido_declara_pt_br_no_opf(pasta: Path, tmp_path: Path) -> None:
    # Com "en" no OPF, o leitor pode escolher a voz inglesa para ler português.
    _responder(pasta)
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    assert "<dc:language>pt-BR</dc:language>" in _membro(montagem.epub, "OEBPS/content.opf")


def test_lang_do_original_vira_pt_br_e_trecho_em_outra_lingua_fica(
    pasta: Path, tmp_path: Path
) -> None:
    _responder(pasta)
    capitulo = _membro(montar(pasta, tmp_path / "livro.pronto.epub").epub, "OEBPS/a.xhtml")
    assert 'xml:lang="pt-BR"' in capitulo
    assert 'xml:lang="fr"' in capitulo
    assert 'xml:lang="en"' not in capitulo


def test_montar_recusa_o_livro_em_ingles_sem_traducao(pasta: Path, tmp_path: Path) -> None:
    _responder(pasta, ("c001",))
    destino = tmp_path / "livro.pronto.epub"
    with pytest.raises(MontagemRecusadaError, match="c002: 2 segmentos sem tradução"):
        _ = montar(pasta, destino)
    assert not destino.exists()


def test_amostra_monta_so_o_traduzido(pasta: Path, tmp_path: Path) -> None:
    _responder(pasta, ("c001",))
    montagem = montar(pasta, tmp_path / "livro.amostra.epub", Modo.AMOSTRA)
    assert (montagem.segmentos, montagem.fora) == (4, 2)
    assert _papeis_e_textos(preparar(montagem.epub, tmp_path / "volta.earbook"))[1] == []
    assert "<dc:language>pt-BR</dc:language>" in _membro(montagem.epub, "OEBPS/content.opf")


def test_original_monta_o_texto_limpo_sem_traducao_e_no_idioma_dele(
    pasta: Path, tmp_path: Path
) -> None:
    montagem = montar(pasta, tmp_path / "livro.original.epub", Modo.ORIGINAL)
    assert _papeis_e_textos(preparar(montagem.epub, tmp_path / "volta.earbook"))[1] == [
        ("titulo", "Two"),
        ("paragrafo", "The end of the story."),
    ]
    assert "<dc:language>en</dc:language>" in _membro(montagem.epub, "OEBPS/content.opf")


def test_conferir_no_modo_traducao_acusa_o_que_ficou_em_ingles(pasta: Path) -> None:
    _responder(pasta)
    resposta = trabalho.caminho_da_resposta(pasta, "c002-l001")
    _ = resposta.write_text(
        json.dumps(
            [
                {"id": "c002-s0001", "texto": "Dois"},
                {"id": "c002-s0002", "texto": "The end of the story."},
            ]
        )
    )
    motivos = [(p.id, p.motivo) for p in conferir_pasta(pasta)]
    assert motivos == [("c002-s0002", "igual ao original, em inglês")]


def test_traducao_com_caractere_que_o_xml_nao_aceita_e_acusada(pasta: Path) -> None:
    _responder(pasta)
    resposta = trabalho.caminho_da_resposta(pasta, "c002-l001")
    _ = resposta.write_text(
        json.dumps(
            [
                {"id": "c002-s0001", "texto": "Dois"},
                {"id": "c002-s0002", "texto": "O fim\u000c da história."},
            ]
        )
    )
    motivos = [(p.id, p.motivo) for p in conferir_pasta(pasta)]
    assert motivos == [("c002-s0002", "texto com caractere que o XML não aceita: U+000C")]


def test_livro_em_portugues_recusa_amostra_e_original(tmp_path: Path) -> None:
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": "<p>Texto.</p>"}, idioma="pt-BR")
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    for modo in (Modo.AMOSTRA, Modo.ORIGINAL):
        with pytest.raises(ModoInvalidoError, match="pt-BR"):
            _ = montar(pasta, tmp_path / f"livro.{modo}.epub", modo)


def test_epub_padrao_diz_o_modo_no_nome() -> None:
    pasta = Path("/livros/Duna.earbook")
    modos = (None, Modo.TRADUCAO, Modo.AMOSTRA, Modo.ORIGINAL)
    assert [epub_padrao(pasta, modo) for modo in modos] == [
        Path("/livros/Duna.pronto.epub"),
        Path("/livros/Duna.pronto.epub"),
        Path("/livros/Duna.amostra.epub"),
        Path("/livros/Duna.original.epub"),
    ]


@pytest.mark.parametrize("idioma", ["und", "por"])
def test_livro_de_idioma_indefinido_ou_por_monta_o_texto_limpo(idioma: str, tmp_path: Path) -> None:
    # O PDF importado sem --idioma é "und", e montava antes do ADR-0006 (A2 da auditoria).
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": "<p>Texto.</p>"}, idioma=idioma)
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    assert montagem.segmentos == 1
    assert f"<dc:language>{idioma}</dc:language>" in _membro(montagem.epub, "OEBPS/content.opf")


def test_cli_monta_a_amostra_ao_lado_da_pasta_e_diz_o_que_ficou_de_fora(
    pasta: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _responder(pasta, ("c001",))
    assert principal(["conferir", str(pasta), "--amostra"]) == 0
    assert principal(["montar", str(pasta), "--amostra"]) == 0
    assert pasta.with_suffix(".amostra.epub").is_file()
    assert "2 sem tradução ficaram de fora" in capsys.readouterr().out


def test_nota_sem_traducao_na_amostra_nao_conta_como_levada_ao_fim(
    pasta: Path, tmp_path: Path
) -> None:
    textos = {k: v for k, v in TRADUCAO.items() if k.startswith("c001") and k != "c001-s0004"}
    registros = [{"id": id_, "texto": texto} for id_, texto in textos.items()]
    caminho = trabalho.caminho_da_resposta(pasta, "c001-l001")
    _ = caminho.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")
    montagem = montar(pasta, tmp_path / "livro.amostra.epub", Modo.AMOSTRA)
    assert (montagem.segmentos, montagem.notas, montagem.fora) == (3, 0, 3)


def test_item_do_sumario_sem_traducao_fica_no_original_na_amostra(tmp_path: Path) -> None:
    # ADR-0006: no sumário nada sai (ADR-0005), nem na amostra; o item fica no original.
    sumario = '<nav epub:type="toc"><ol><li><a href="b.xhtml">Two</a></li></ol></nav>'
    capitulos = {"nav.xhtml": sumario, "b.xhtml": CAPITULO_DOIS}
    epub = montar_epub(tmp_path / "livro.epub", capitulos)
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    _ = traduzir(pasta)
    _responder(pasta, ("c002",))
    montagem = montar(pasta, tmp_path / "livro.amostra.epub", Modo.AMOSTRA)
    assert '<a href="b.xhtml">Two</a>' in _membro(montagem.epub, "OEBPS/nav.xhtml")
    # F5 da pós-auditoria: o item que ficou no livro não é "de fora".
    assert (montagem.fora, montagem.no_original) == (0, 1)


def test_livro_em_frances_tambem_declara_pt_br(tmp_path: Path) -> None:
    # A troca vem do idioma do livro, não de um "en" fixo.
    corpo = '<p xml:lang="fr">Le texte du livre, en français.</p>'
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": corpo}, idioma="fr")
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    _ = traduzir(pasta)
    resposta = [{"id": "c001-s0001", "texto": "O texto do livro, em português."}]
    _ = trabalho.caminho_da_resposta(pasta, "c001-l001").write_text(json.dumps(resposta))
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    assert "<dc:language>pt-BR</dc:language>" in _membro(montagem.epub, "OEBPS/content.opf")
    assert 'xml:lang="pt-BR"' in _membro(montagem.epub, "OEBPS/a.xhtml")


def test_cli_diz_quantos_itens_do_sumario_ficaram_no_original(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sumario = '<nav epub:type="toc"><ol><li><a href="b.xhtml">Two</a></li></ol></nav>'
    epub = montar_epub(tmp_path / "livro.epub", {"nav.xhtml": sumario, "b.xhtml": CAPITULO_DOIS})
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    _ = traduzir(pasta)
    _responder(pasta, ("c002",))
    assert principal(["montar", str(pasta), "--amostra"]) == 0
    assert "1 item do sumário ficou no original" in capsys.readouterr().out
