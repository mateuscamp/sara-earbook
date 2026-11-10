# SPDX-License-Identifier: GPL-3.0-or-later
"""Os comandos `montar` e `conferir` de ponta a ponta (ADR-0005)."""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.comandos.cli import principal
from earbook.comandos.montar import (
    MontagemRecusadaError,
    conferir_pasta,
    epub_padrao,
    montar,
)
from earbook.comandos.preparar import Preparo, preparar
from earbook.dominio.livro_limpo import CapituloLimpo
from tests.livro_de_teste import montar_epub

CAPITULO_UM = (
    "<h1>Um</h1><p>O texto que segue até a quebra da</p><p>Livro de Teste 2</p><p>página.</p>"
    '<aside epub:type="footnote"><p>1 A nota.</p></aside><p>Livro de Teste 4</p><p>Fim.</p>'
)
CAPITULO_DOIS = "<p>Livro de Teste 6</p><h1>Dois</h1><p>Texto.</p>"


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    # Em pt-BR: aqui o texto final é o de `limpos/`; o livro em inglês exige a tradução
    # (ADR-0006), e o modo tradução é testado em test_montar_traducao.py.
    epub = montar_epub(
        tmp_path / "livro.epub",
        {"a.xhtml": CAPITULO_UM, "b.xhtml": CAPITULO_DOIS},
        idioma="pt-BR",
    )
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    return pasta


def _papeis_e_textos(preparo: Preparo) -> list[list[tuple[str, str]]]:
    return [[(str(s.papel), s.texto) for s in c.segmentos] for c in preparo.limpeza.capitulos]


def test_livro_montado_e_o_limpo_com_a_nota_no_fim_do_capitulo(pasta: Path, tmp_path: Path) -> None:
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    assert (montagem.capitulos, montagem.segmentos, montagem.notas) == (2, 6, 1)
    assert _papeis_e_textos(preparar(montagem.epub, tmp_path / "volta.earbook")) == [
        [
            ("titulo", "Um"),
            ("paragrafo", "O texto que segue até a quebra da página."),
            ("paragrafo", "Fim."),
            ("titulo", "Notas"),
            ("paragrafo", "1 A nota."),
        ],
        [("titulo", "Dois"), ("paragrafo", "Texto.")],
    ]


def test_montar_recusa_o_livro_que_o_conferir_reprova(pasta: Path, tmp_path: Path) -> None:
    # Sem os segmentos do capítulo 2 em `limpos/`, o "Dois" e o "Texto." sumiriam do áudio.
    _ = (pasta / "limpos" / "c002.json").write_text("[]\n")
    destino = tmp_path / "livro.pronto.epub"
    with pytest.raises(MontagemRecusadaError, match="c002-s0002"):
        _ = montar(pasta, destino)
    assert not destino.exists()


def test_montar_recusa_destino_que_ja_existe(pasta: Path, tmp_path: Path) -> None:
    # A recusa vem antes do conferir, que lê o livro inteiro: com a pasta também com
    # problema, o erro é o do destino.
    _ = (pasta / "limpos" / "c002.json").write_text("[]\n")
    destino = tmp_path / "livro.pronto.epub"
    _ = destino.write_bytes(b"antigo")
    with pytest.raises(FileExistsError, match=r"livro\.pronto\.epub"):
        _ = montar(pasta, destino)
    assert destino.read_bytes() == b"antigo"


def test_epub_padrao_fica_ao_lado_da_pasta() -> None:
    assert epub_padrao(Path("/livros/Duna.earbook")) == Path("/livros/Duna.pronto.epub")


def test_pasta_recem_preparada_passa_no_conferir(pasta: Path) -> None:
    assert conferir_pasta(pasta) == ()


def test_cli_montar_grava_ao_lado_da_pasta_e_resume(
    pasta: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert principal(["montar", str(pasta)]) == 0
    assert pasta.with_suffix(".pronto.epub").is_file()
    assert "2 capítulos, 6 segmentos" in capsys.readouterr().out


def test_cli_conferir_lista_os_problemas_e_sai_com_1(
    pasta: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = (pasta / "limpos" / "c002.json").write_text("[]\n")
    assert principal(["conferir", str(pasta)]) == 1
    saida = capsys.readouterr().out
    assert "c002-s0002" in saida
    assert "sumiu" in saida


def test_montar_recusa_texto_que_o_xml_nao_aceita_com_o_id(pasta: Path, tmp_path: Path) -> None:
    limpos = pasta / "limpos" / "c002.json"
    _ = limpos.write_text(limpos.read_text(encoding="utf-8").replace("Texto.", "Tex\\u000cto."))
    with pytest.raises(MontagemRecusadaError, match="c002-s0003: texto com caractere"):
        _ = montar(pasta, tmp_path / "livro.pronto.epub")


def test_arquivo_so_de_notas_deixa_cada_nota_no_lugar(tmp_path: Path) -> None:
    # A3 da auditoria e ADR-0005: a nota de fim de livro fica sob o subtítulo do capítulo
    # dela; movida para "Notas", perdia a relação com o capítulo.
    notas = (
        "<h1>Notas do livro</h1><h2>Capítulo 1</h2>"
        '<aside epub:type="endnote"><p>1. Nota um.</p></aside>'
        '<h2>Capítulo 2</h2><aside epub:type="endnote"><p>1. Nota dois.</p></aside>'
    )
    epub = montar_epub(
        tmp_path / "livro.epub", {"a.xhtml": "<p>Texto.</p>", "n.xhtml": notas}, idioma="pt-BR"
    )
    pasta = tmp_path / "livro.earbook"
    _ = preparar(epub, pasta)
    montagem = montar(pasta, tmp_path / "livro.pronto.epub")
    assert montagem.notas == 0
    assert _papeis_e_textos(preparar(montagem.epub, tmp_path / "volta.earbook"))[1] == [
        ("titulo", "Notas do livro"),
        ("titulo", "Capítulo 1"),
        ("nota", "1. Nota um."),
        ("titulo", "Capítulo 2"),
        ("nota", "1. Nota dois."),
    ]


def test_conferir_acusa_segmento_mantido_no_capitulo_errado(pasta: Path) -> None:
    # A2 da auditoria, de ponta a ponta: o "Texto." do capítulo 2 posto no `limpos/` do 1.
    um, dois = trabalho.ler_limpos(pasta, "c001"), trabalho.ler_limpos(pasta, "c002")
    trabalho.gravar_limpos(pasta, CapituloLimpo("c001", (*um, dois[-1])))
    trabalho.gravar_limpos(pasta, CapituloLimpo("c002", dois[:-1]))
    motivos = [(p.id, p.motivo) for p in conferir_pasta(pasta)]
    assert motivos == [("c002-s0003", "mantido no capítulo c001, mas é do c002")]
