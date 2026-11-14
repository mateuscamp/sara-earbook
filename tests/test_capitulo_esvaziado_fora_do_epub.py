# SPDX-License-Identifier: GPL-3.0-or-later
"""O capítulo que uma regra da limpeza esvaziou fica fora do EPUB montado, como o declarado no
`preparar --sem-capitulo` (ADR-0005, "Todo capítulo sem texto fora do EPUB montado").

O capítulo do índice remissivo saía do áudio e continuava no livro, com o corpo vazio e o item no
sumário: o leitor listava "Index", que leva a uma página em branco.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.comandos.cli import principal
from earbook.comandos.montar import MontagemRecusadaError, montar
from earbook.comandos.preparar import preparar
from earbook.comandos.traduzir import traduzir
from earbook.dominio.fora_do_audio import capitulos_com_remocao
from earbook.dominio.traducao import Modo
from tests.livro_de_teste import xhtml

INDICE = (
    '<section epub:type="index"><h1>Índice</h1><ul>'
    '<li>acoplamento, <a href="a.xhtml#x">12</a></li>'
    '<li>coesão, <a href="a.xhtml#y">15</a></li></ul></section>'
)
CAPITULOS = {
    "a.xhtml": "<h1>Um</h1><p>O texto do primeiro capítulo.</p>",
    "b.xhtml": "<h1>Dois</h1><p>O texto do segundo capítulo.</p>",
    "ix.xhtml": INDICE,
}
EM_INGLES = {
    "a.xhtml": "<h1>One</h1><p>The text of the first chapter.</p>",
    "b.xhtml": "<h1>Two</h1><p>The text of the second chapter.</p>",
    "ix.xhtml": INDICE.replace("Índice", "Index"),
}


def _epub(destino: Path, capitulos: dict[str, str], idioma: str = "pt-BR") -> Path:
    """Um EPUB com o sumário (`nav.xhtml`) no manifesto, fora do spine, e um item por capítulo."""
    itens = "".join(
        f'<item id="{nome}" href="{nome}" media-type="application/xhtml+xml"/>'
        for nome in capitulos
    )
    nav = '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    spine = "".join(f'<itemref idref="{nome}"/>' for nome in capitulos)
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:identifier id="id">teste</dc:identifier><dc:title>Livro de Teste</dc:title>'
        f"<dc:creator>Fulano</dc:creator><dc:language>{idioma}</dc:language></metadata>"
        f"<manifest>{itens}{nav}</manifest><spine>{spine}</spine></package>"
    )
    container = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf"'
        ' media-type="application/oebps-package+xml"/></rootfiles></container>'
    )
    links = "".join(f'<li><a href="{nome}">{nome}</a></li>' for nome in capitulos)
    with zipfile.ZipFile(destino, "w") as zip_:
        zip_.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zip_.writestr("META-INF/container.xml", container)
        zip_.writestr("OEBPS/content.opf", opf)
        zip_.writestr("OEBPS/nav.xhtml", xhtml(f'<nav epub:type="toc"><ol>{links}</ol></nav>'))
        for nome, corpo in capitulos.items():
            zip_.writestr(f"OEBPS/{nome}", xhtml(corpo))
    return destino


def _preparado(
    tmp_path: Path,
    capitulos: dict[str, str] | None = None,
    sem_capitulos: tuple[str, ...] = (),
    idioma: str = "pt-BR",
) -> Path:
    pasta = tmp_path / "livro.earbook"
    epub = _epub(tmp_path / "livro.epub", capitulos or CAPITULOS, idioma)
    _ = preparar(epub, pasta, sem_capitulos)
    return pasta


def _membros(epub: Path) -> dict[str, str]:
    with zipfile.ZipFile(epub) as zip_:
        return {nome: zip_.read(nome).decode() for nome in zip_.namelist()}


def _traduzido(tmp_path: Path, capitulos: tuple[str, ...]) -> Path:
    """O livro em inglês com o índice marcado e os `capitulos` já traduzidos."""
    pasta = _preparado(tmp_path, EM_INGLES, idioma="en")
    _ = traduzir(pasta)
    for pedido in trabalho.ler_pedidos(pasta):
        if pedido.lote.split("-")[0] in capitulos:
            registros = [{"id": s.id, "texto": f"Tradução de {s.id}."} for s in pedido.segmentos]
            caminho = trabalho.caminho_da_resposta(pasta, pedido.lote)
            _ = caminho.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")
    return pasta


def test_registro_da_limpeza_diz_os_capitulos_de_que_algo_saiu() -> None:
    motivos = {"c001-s0002": "marca d'água", "c003-s0001": "índice remissivo"}
    assert capitulos_com_remocao(motivos) == {"c001", "c003"}


def test_capitulo_que_o_indice_esvaziou_nao_vai_para_o_pacote(tmp_path: Path) -> None:
    montado = _membros(montar(_preparado(tmp_path), tmp_path / "livro.pronto.epub").epub)
    assert sorted(nome for nome in montado if nome.endswith(".xhtml")) == [
        "OEBPS/a.xhtml",
        "OEBPS/b.xhtml",
        "OEBPS/nav.xhtml",
    ]


def test_capitulo_que_o_indice_esvaziou_sai_do_manifesto_do_spine_e_do_sumario(
    tmp_path: Path,
) -> None:
    montado = _membros(montar(_preparado(tmp_path), tmp_path / "livro.pronto.epub").epub)
    restos = ["ix.xhtml" in montado[nome] for nome in ("OEBPS/content.opf", "OEBPS/nav.xhtml")]
    assert restos == [False, False]


def test_montagem_diz_o_capitulo_que_a_regra_esvaziou(tmp_path: Path) -> None:
    montagem = montar(_preparado(tmp_path), tmp_path / "livro.pronto.epub")
    assert (montagem.capitulos, montagem.sem_texto) == (2, ("c003",))


def test_capitulo_declarado_e_capitulo_esvaziado_saem_juntos(tmp_path: Path) -> None:
    pasta = _preparado(tmp_path, sem_capitulos=("c001",))
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    assert (montagem.capitulos, montagem.sem_texto) == (1, ("c001", "c003"))


def test_capitulo_que_perdeu_so_parte_do_texto_fica(tmp_path: Path) -> None:
    # O índice no fim de um capítulo com prosa: sai o índice, e o capítulo continua no livro.
    capitulos = {**CAPITULOS, "ix.xhtml": f"<h1>Fim</h1><p>Uma palavra final.</p>{INDICE}"}
    pasta = _preparado(tmp_path, capitulos)
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    assert ("OEBPS/ix.xhtml" in _membros(montagem.epub), montagem.sem_texto) == (True, ())


def test_no_original_o_capitulo_esvaziado_tambem_sai(tmp_path: Path) -> None:
    pasta = _traduzido(tmp_path, ())
    montagem = montar(pasta, tmp_path / "livro.original.epub", Modo.ORIGINAL)
    assert ("OEBPS/ix.xhtml" in _membros(montagem.epub), montagem.sem_texto) == (False, ("c003",))


def test_na_amostra_o_capitulo_esvaziado_sai_e_o_que_falta_traduzir_fica(tmp_path: Path) -> None:
    pasta = _traduzido(tmp_path, ("c001",))
    montagem = montar(pasta, tmp_path / "livro.amostra.epub", Modo.AMOSTRA)
    montado = _membros(montagem.epub)
    assert ["OEBPS/b.xhtml" in montado, "OEBPS/ix.xhtml" in montado] == [True, False]
    assert (montagem.capitulos, montagem.sem_texto) == (2, ("c003",))


def test_na_traducao_o_capitulo_esvaziado_tambem_sai(tmp_path: Path) -> None:
    pasta = _traduzido(tmp_path, ("c001", "c002"))
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    assert ("OEBPS/ix.xhtml" in _membros(montagem.epub), montagem.sem_texto) == (False, ("c003",))


def test_cli_diz_o_capitulo_esvaziado_que_ficou_fora_do_epub(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert principal(["montar", str(_preparado(tmp_path))]) == 0
    saida = capsys.readouterr().out
    assert "2 capítulos, 4 segmentos" in saida
    assert "1 capítulo sem texto ficou fora do EPUB: c003." in saida


def test_livro_que_a_limpeza_esvaziou_inteiro_e_recusado(tmp_path: Path) -> None:
    pasta = _preparado(tmp_path, sem_capitulos=("c001", "c002"))
    destino = tmp_path / "livro.pronto.epub"
    with pytest.raises(MontagemRecusadaError, match="nenhum capítulo com texto"):
        _ = montar(pasta, destino)
    assert not destino.exists()


def test_livro_so_com_a_capa_e_capitulos_esvaziados_e_recusado(tmp_path: Path) -> None:
    # A capa nunca teve segmento e fica, mas não é texto: sem capítulo que se ouça, o livro é
    # recusado (R3 da code-review).
    capitulos = {"capa.xhtml": '<div><img src="capa.png" alt=""/></div>', **CAPITULOS}
    pasta = _preparado(tmp_path, capitulos, sem_capitulos=("c002", "c003"))
    destino = tmp_path / "livro.pronto.epub"
    with pytest.raises(MontagemRecusadaError, match="nenhum capítulo com texto"):
        _ = montar(pasta, destino)
    assert not destino.exists()
