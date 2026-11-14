# SPDX-License-Identifier: GPL-3.0-or-later
"""O capítulo que a limpeza esvaziou fica fora do EPUB montado (ADR-0005, "Capítulo sem texto fora
do EPUB montado").

O `preparar --sem-capitulo` tirava o texto, e o `montar` deixava o arquivo vazio no livro e o item
dele no sumário: o leitor listava um capítulo que leva a uma página em branco.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.adaptadores.pacote_epub import EpubInvalidoError
from earbook.comandos.cli import principal
from earbook.comandos.montar import MontagemRecusadaError, montar
from earbook.comandos.preparar import preparar
from earbook.comandos.traduzir import traduzir
from earbook.dominio.fora_do_audio import capitulos_declarados
from earbook.dominio.traducao import Modo
from tests.livro_de_teste import xhtml

CAPITULOS = {
    "a.xhtml": "<h1>Um</h1><p>O texto do primeiro capítulo.</p>",
    "b.xhtml": "<h1>Autores</h1><p>Fulano de Tal, professor.</p>",
    "c.xhtml": "<h1>Três</h1><p>O texto do terceiro capítulo.</p>",
}
SUMARIO = (
    '<nav epub:type="toc"><ol><li><a href="a.xhtml">Um</a></li>'
    '<li><a href="b.xhtml">Autores</a></li><li><a href="c.xhtml">Três</a></li></ol></nav>'
)
NCX = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><navMap>{pontos}</navMap>'
    "{listas}</ncx>"
)


def _ponto(numero: int, arquivo: str, dentro: str = "") -> str:
    return (
        f'<navPoint id="p{numero}" playOrder="{numero}"><navLabel><text>{arquivo}</text></navLabel>'
        f'<content src="{arquivo}"/>{dentro}</navPoint>'
    )


def _propriedade(nome: str) -> str:
    return ' properties="nav"' if nome == "nav.xhtml" else ""


def _opf(arquivos: list[str], idioma: str, extras: str, guia: str) -> bytes:
    itens = "".join(
        f'<item id="{nome}" href="{nome}" media-type="application/xhtml+xml"{_propriedade(nome)}/>'
        for nome in arquivos
    )
    spine = "".join(f'<itemref idref="{nome}"/>' for nome in arquivos)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:identifier id="id">teste</dc:identifier><dc:title>Livro de Teste</dc:title>'
        f"<dc:creator>Fulano</dc:creator><dc:language>{idioma}</dc:language></metadata>"
        f"<manifest>{itens}{extras}</manifest><spine>{spine}</spine>{guia}</package>"
    ).encode()


def _epub(
    destino: Path,
    capitulos: dict[str, str] | None = None,
    sumario: str = SUMARIO,
    *,
    partes: dict[str, str] | None = None,
    idioma: str = "pt-BR",
) -> Path:
    """Um EPUB como o do `importar-pdf`: o sumário (`nav.xhtml`) no manifesto e fora do spine.
    Em `partes`, o `ncx` (o conteúdo do `toc.ncx`) e o `guia` (o `<guide>` do OPF). Se
    `capitulos` traz o `nav.xhtml`, ele vai no spine."""
    capitulos = capitulos or CAPITULOS
    ncx, guia = (partes or {}).get("ncx", ""), (partes or {}).get("guia", "")
    extras = ""
    if "nav.xhtml" not in capitulos:
        extras = (
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
        )
    if ncx:
        extras += '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
    container = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf"'
        ' media-type="application/oebps-package+xml"/></rootfiles></container>'
    )
    with zipfile.ZipFile(destino, "w") as zip_:
        zip_.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zip_.writestr("META-INF/container.xml", container)
        zip_.writestr("OEBPS/content.opf", _opf(list(capitulos), idioma, extras, guia))
        if ncx:
            zip_.writestr("OEBPS/toc.ncx", ncx)
        for nome, corpo in {"nav.xhtml": sumario, **capitulos}.items():
            zip_.writestr(f"OEBPS/{nome}", xhtml(corpo))
    return destino


def _preparado(tmp_path: Path, epub: Path, sem_capitulos: tuple[str, ...] = ("c002",)) -> Path:
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta, sem_capitulos)
    return pasta


def _membros(epub: Path) -> dict[str, str]:
    with zipfile.ZipFile(epub) as zip_:
        return {nome: zip_.read(nome).decode() for nome in zip_.namelist()}


@pytest.fixture
def montado(tmp_path: Path) -> dict[str, str]:
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub"))
    return _membros(montar(pasta, tmp_path / "livro.pronto.epub").epub)


def test_registro_da_limpeza_diz_os_capitulos_declarados(tmp_path: Path) -> None:
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub"), ("c001", "c003"))
    assert capitulos_declarados(trabalho.ler_limpeza(pasta).motivos) == {"c001", "c003"}


def test_remocao_por_outro_motivo_nao_declara_o_capitulo() -> None:
    motivos = {"c001-s0001": "índice remissivo", "c002-s0001": "página de direitos autorais"}
    assert capitulos_declarados(motivos) == frozenset()


def test_arquivo_do_capitulo_sem_texto_nao_vai_para_o_pacote(montado: dict[str, str]) -> None:
    assert sorted(nome for nome in montado if nome.endswith(".xhtml")) == [
        "OEBPS/a.xhtml",
        "OEBPS/c.xhtml",
        "OEBPS/nav.xhtml",
    ]


def test_capitulo_sem_texto_sai_do_manifesto_e_do_spine(montado: dict[str, str]) -> None:
    opf = montado["OEBPS/content.opf"]
    assert 'href="b.xhtml"' not in opf
    assert 'idref="b.xhtml"' not in opf
    assert [f'idref="{nome}"' in opf for nome in ("a.xhtml", "c.xhtml")] == [True, True]


def test_capitulo_sem_texto_sai_do_sumario(montado: dict[str, str]) -> None:
    assert (
        '<ol><li><a href="a.xhtml">Um</a></li><li><a href="c.xhtml">Três</a></li></ol>'
        in montado["OEBPS/nav.xhtml"]
    )


def test_montagem_conta_os_capitulos_que_foram_e_diz_os_que_ficaram_de_fora(
    tmp_path: Path,
) -> None:
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub"))
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    assert (montagem.capitulos, montagem.sem_texto) == (2, ("c002",))


def test_livro_montado_volta_pelo_preparar_so_com_os_capitulos_que_se_ouvem(
    tmp_path: Path,
) -> None:
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub"))
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    relido = preparar(montagem.epub, tmp_path / "volta.earbook")
    assert [[s.texto for s in c.segmentos] for c in relido.limpeza.capitulos] == [
        ["Um", "O texto do primeiro capítulo."],
        ["Três", "O texto do terceiro capítulo."],
    ]


def test_cli_diz_quais_capitulos_ficaram_fora_do_epub(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub"), ("c002", "c003"))
    assert principal(["montar", str(pasta)]) == 0
    saida = capsys.readouterr().out
    assert "1 capítulos, 2 segmentos" in saida
    assert "2 capítulos sem texto ficaram fora do EPUB: c002, c003." in saida


def test_item_do_sumario_que_sai_da_o_lugar_aos_filhos_de_outro_arquivo(tmp_path: Path) -> None:
    sumario = (
        '<nav epub:type="toc"><ol><li><a href="a.xhtml">Um</a></li>'
        '<li><a href="b.xhtml">Autores</a><ol><li><a href="b.xhtml#fulano">Fulano</a></li>'
        '<li><a href="c.xhtml">Três</a></li></ol></li></ol></nav>'
    )
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub", sumario=sumario))
    nav = _membros(montar(pasta, tmp_path / "livro.pronto.epub").epub)["OEBPS/nav.xhtml"]
    assert '<ol><li><a href="a.xhtml">Um</a></li><li><a href="c.xhtml">Três</a></li></ol>' in nav


def test_lista_de_dentro_que_fica_vazia_sai_com_o_item(tmp_path: Path) -> None:
    sumario = (
        '<nav epub:type="toc"><ol><li><a href="a.xhtml">Um</a>'
        '<ol><li><a href="b.xhtml">Autores</a></li></ol></li>'
        '<li><a href="c.xhtml">Três</a></li></ol></nav>'
    )
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub", sumario=sumario))
    nav = _membros(montar(pasta, tmp_path / "livro.pronto.epub").epub)["OEBPS/nav.xhtml"]
    assert '<ol><li><a href="a.xhtml">Um</a></li><li><a href="c.xhtml">Três</a></li></ol>' in nav


def test_nav_que_nao_e_o_sumario_sai_inteiro_quando_fica_sem_item(tmp_path: Path) -> None:
    marcos = (
        '<nav epub:type="landmarks"><ol><li><a epub:type="bodymatter" href="b.xhtml">Começo</a>'
        "</li></ol></nav>"
    )
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub", sumario=SUMARIO + marcos))
    nav = _membros(montar(pasta, tmp_path / "livro.pronto.epub").epub)["OEBPS/nav.xhtml"]
    assert "landmarks" not in nav
    assert 'epub:type="toc"' in nav


def test_capitulo_sem_texto_sai_do_toc_ncx_e_os_filhos_sobem(tmp_path: Path) -> None:
    pontos = _ponto(1, "a.xhtml") + _ponto(2, "b.xhtml", _ponto(3, "c.xhtml"))
    pagina = (
        '<pageList><pageTarget id="pg1" type="normal" value="1"><navLabel><text>1</text>'
        '</navLabel><content src="b.xhtml#p1"/></pageTarget></pageList>'
    )
    ncx = NCX.format(pontos=pontos, listas=pagina)
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub", partes={"ncx": ncx}))
    montado = _membros(montar(pasta, tmp_path / "livro.pronto.epub").epub)["OEBPS/toc.ncx"]
    assert "b.xhtml" not in montado
    assert "pageList" not in montado
    sem_ordem = re.sub(r' playOrder="\d+"', "", montado)
    esperado = re.sub(r' playOrder="\d+"', "", _ponto(1, "a.xhtml") + _ponto(3, "c.xhtml"))
    assert f"<navMap>{esperado}</navMap>" in sem_ordem


def test_ordem_de_leitura_do_toc_ncx_fica_sem_salto(tmp_path: Path) -> None:
    # O epubcheck recusa o salto: "playOrder sequence has gaps".
    pontos = _ponto(1, "a.xhtml") + _ponto(2, "b.xhtml", _ponto(3, "c.xhtml"))
    paginas = (
        '<pageList><pageTarget id="pg1" type="normal" value="1" playOrder="4"><navLabel>'
        '<text>1</text></navLabel><content src="c.xhtml#p1"/></pageTarget></pageList>'
    )
    ncx = NCX.format(pontos=pontos, listas=paginas)
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub", partes={"ncx": ncx}))
    montado = _membros(montar(pasta, tmp_path / "livro.pronto.epub").epub)["OEBPS/toc.ncx"]
    assert re.findall(r'playOrder="(\d+)"', montado) == ["1", "2", "3"]


def test_referencia_do_guia_ao_capitulo_sem_texto_sai(tmp_path: Path) -> None:
    guia = '<guide><reference type="text" title="Começo" href="b.xhtml#x"/></guide>'
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub", partes={"guia": guia}))
    opf = _membros(montar(pasta, tmp_path / "livro.pronto.epub").epub)["OEBPS/content.opf"]
    assert "guide" not in opf


def test_capitulo_que_nunca_teve_segmento_fica(tmp_path: Path) -> None:
    # A capa e a página só de imagem: não foi a limpeza que as esvaziou.
    capitulos = {"capa.xhtml": '<div><img src="capa.png" alt=""/></div>', **CAPITULOS}
    sumario = SUMARIO.replace("<ol>", '<ol><li><a href="capa.xhtml">Capa</a></li>', 1)
    epub = _epub(tmp_path / "livro.epub", capitulos, sumario)
    pasta = _preparado(tmp_path, epub, ("c003",))
    montado = _membros(montar(pasta, tmp_path / "livro.pronto.epub").epub)
    assert "OEBPS/capa.xhtml" in montado
    assert 'idref="capa.xhtml"' in montado["OEBPS/content.opf"]
    assert '<a href="capa.xhtml">Capa</a>' in montado["OEBPS/nav.xhtml"]


def test_arquivo_do_sumario_no_spine_fica_mesmo_sem_texto(tmp_path: Path) -> None:
    # Sem o item `nav` no manifesto o EPUB 3 é inválido; e no sumário nada sai (ADR-0005).
    epub = _epub(tmp_path / "livro.epub", {"nav.xhtml": SUMARIO, **CAPITULOS})
    pasta = _preparado(tmp_path, epub, ("c001",))
    montado = _membros(montar(pasta, tmp_path / "livro.pronto.epub").epub)
    assert "OEBPS/nav.xhtml" in montado
    assert 'idref="nav.xhtml"' in montado["OEBPS/content.opf"]


def test_sem_capitulo_vazio_o_opf_e_o_sumario_vao_como_estao(tmp_path: Path) -> None:
    epub = _epub(tmp_path / "livro.epub")
    pasta = _preparado(tmp_path, epub, ())
    montado = _membros(montar(pasta, tmp_path / "livro.pronto.epub").epub)
    original = _membros(epub)
    assert [
        montado[nome] == original[nome] for nome in ("OEBPS/content.opf", "OEBPS/nav.xhtml")
    ] == [
        True,
        True,
    ]


def _traduzido(tmp_path: Path, capitulos: tuple[str, ...]) -> Path:
    """O livro em inglês com o segundo capítulo fora do áudio e os `capitulos` já traduzidos."""
    em_ingles = {
        "a.xhtml": "<h1>One</h1><p>The text of the first chapter.</p>",
        "b.xhtml": "<h1>Authors</h1><p>John Doe, professor.</p>",
        "c.xhtml": "<h1>Three</h1><p>The text of the third chapter.</p>",
    }
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub", em_ingles, idioma="en"))
    _ = traduzir(pasta)
    for pedido in trabalho.ler_pedidos(pasta):
        if pedido.lote.split("-")[0] in capitulos:
            registros = [{"id": s.id, "texto": f"Tradução de {s.id}."} for s in pedido.segmentos]
            caminho = trabalho.caminho_da_resposta(pasta, pedido.lote)
            _ = caminho.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")
    return pasta


def test_no_original_o_capitulo_sem_texto_tambem_sai(tmp_path: Path) -> None:
    pasta = _traduzido(tmp_path, ())
    montagem = montar(pasta, tmp_path / "livro.original.epub", Modo.ORIGINAL)
    assert "OEBPS/b.xhtml" not in _membros(montagem.epub)
    assert montagem.sem_texto == ("c002",)


def test_na_amostra_sai_o_que_a_limpeza_esvaziou_e_fica_o_que_falta_traduzir(
    tmp_path: Path,
) -> None:
    # O capítulo sem tradução não está vazio, só não foi feito (ADR-0006): continua no EPUB.
    pasta = _traduzido(tmp_path, ("c001",))
    montagem = montar(pasta, tmp_path / "livro.amostra.epub", Modo.AMOSTRA)
    montado = _membros(montagem.epub)
    assert ["OEBPS/b.xhtml" in montado, "OEBPS/c.xhtml" in montado] == [False, True]
    assert (montagem.capitulos, montagem.sem_texto) == (2, ("c002",))


def test_livro_em_que_todo_capitulo_ficaria_de_fora_e_recusado(tmp_path: Path) -> None:
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub"), ("c001", "c002", "c003"))
    destino = tmp_path / "livro.pronto.epub"
    with pytest.raises(MontagemRecusadaError, match="nenhum capítulo com texto"):
        _ = montar(pasta, destino)
    assert not destino.exists()


def test_sumario_que_ficaria_sem_item_e_recusado_com_o_arquivo(tmp_path: Path) -> None:
    sumario = '<nav epub:type="toc"><ol><li><a href="b.xhtml">Autores</a></li></ol></nav>'
    pasta = _preparado(tmp_path, _epub(tmp_path / "livro.epub", sumario=sumario))
    destino = tmp_path / "livro.pronto.epub"
    with pytest.raises(EpubInvalidoError, match=r"OEBPS/nav\.xhtml"):
        _ = montar(pasta, destino)
    assert not destino.exists()
