# SPDX-License-Identifier: GPL-3.0-or-later
"""A leitura da pasta de trabalho devolve o que a gravação escreveu (ADR-0005)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.dominio.limpeza import CapituloLimpo, Juncao, LivroLimpo, Remocao
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.trabalho import CapituloPreparado, LivroPreparado

SEGMENTOS = (
    Segmento("c001-s0001", Papel.TITULO, "Um"),
    Segmento("c001-s0002", Papel.PARAGRAFO, "Texto com nota.", ("OEBPS/a.xhtml#n1",)),
    Segmento("c001-s0003", Papel.NOTA, "1 A nota."),
)


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    pasta = tmp_path / "livro.earbook"
    trabalho.criar_pasta_de_trabalho(pasta)
    return pasta


def test_segmentos_e_limpos_voltam_como_foram_gravados(pasta: Path) -> None:
    trabalho.gravar_segmentos(pasta, "c001", list(SEGMENTOS))
    trabalho.gravar_limpos(pasta, CapituloLimpo("c001", SEGMENTOS[:2]))
    assert trabalho.ler_segmentos(pasta, "c001") == SEGMENTOS
    assert trabalho.ler_limpos(pasta, "c001") == SEGMENTOS[:2]


def test_capitulos_do_livro_voltam_na_ordem(pasta: Path) -> None:
    capitulos = (
        CapituloPreparado("c001", "OEBPS/b.xhtml", 2),
        CapituloPreparado("c002", "OEBPS/a.xhtml", 1),
    )
    trabalho.gravar_livro(pasta, LivroPreparado("l.epub", "T", "A", "pt-BR", capitulos, ()))
    assert trabalho.ler_capitulos(pasta) == capitulos


def test_remocoes_e_juncoes_da_limpeza_voltam(pasta: Path) -> None:
    limpeza = LivroLimpo(
        (),
        (Remocao("c001-s0004", "cabeçalho de página 'T'", "T 2"),),
        juncoes=(Juncao("c001-s0006", "c001-s0005"),),
    )
    trabalho.gravar_limpeza(pasta, limpeza)
    registro = trabalho.ler_limpeza(pasta)
    assert (registro.removidos, registro.juntados) == (
        ("c001-s0004",),
        (("c001-s0006", "c001-s0005"),),
    )


def test_remocao_repetida_no_registro_chega_repetida(pasta: Path) -> None:
    # A7 da auditoria: a leitura num conjunto escondia a repetição do conferir.
    remocao = Remocao("c001-s0004", "cabeçalho de página 'T'", "T 2")
    trabalho.gravar_limpeza(pasta, LivroLimpo((), (remocao, remocao)))
    assert trabalho.ler_limpeza(pasta).removidos == ("c001-s0004", "c001-s0004")


def test_segmento_com_formato_errado_e_recusado_com_o_caminho(pasta: Path) -> None:
    arquivo = pasta / "limpos" / "c001.json"
    _ = arquivo.write_text('[{"id": "c001-s0001", "papel": "titulo", "texto": 3, "notas": []}]')
    with pytest.raises(trabalho.PastaDeTrabalhoInvalidaError, match=r"c001\.json.*texto"):
        _ = trabalho.ler_limpos(pasta, "c001")


def test_papel_desconhecido_e_recusado_com_o_caminho(pasta: Path) -> None:
    arquivo = pasta / "limpos" / "c001.json"
    _ = arquivo.write_text('[{"id": "c001-s0001", "papel": "rodape", "texto": "x", "notas": []}]')
    with pytest.raises(trabalho.PastaDeTrabalhoInvalidaError, match=r"c001\.json.*rodape"):
        _ = trabalho.ler_limpos(pasta, "c001")


def test_json_quebrado_e_recusado_com_o_caminho(pasta: Path) -> None:
    _ = (pasta / "limpeza.json").write_text('{"remocoes": [')
    with pytest.raises(trabalho.PastaDeTrabalhoInvalidaError, match=r"limpeza\.json"):
        _ = trabalho.ler_limpeza(pasta)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("arquivo", "OEBPS/./ch01.xhtml"),
        ("arquivo", "../../outra.earbook/epub/OEBPS/ch01.xhtml"),
        ("arquivo", "/etc/passwd"),
        ("id", "capitulo1"),
        ("id", "c001/../x"),
        ("arquivo", ".."),
    ],
)
def test_capitulo_com_caminho_ou_id_fora_do_formato_e_recusado(
    pasta: Path, campo: str, valor: str
) -> None:
    # A5 da auditoria: com "OEBPS/./ch01.xhtml", o montar não achava o arquivo para trocar e
    # empacotava o capítulo cru dizendo que tinha montado; com "../", lia fora da pasta.
    capitulo = {"id": "c001", "arquivo": "OEBPS/ch01.xhtml", "segmentos": 1} | {campo: valor}
    _ = (pasta / "livro.json").write_text(json.dumps({"capitulos": [capitulo]}))
    with pytest.raises(trabalho.PastaDeTrabalhoInvalidaError, match=r"livro\.json"):
        _ = trabalho.ler_capitulos(pasta)


@pytest.mark.parametrize(
    "conteudo",
    [
        '{"capitulos": [{"id": "c001", "arquivo": "a.xhtml", "segmentos": true}]}',
        '{"capitulos": {"id": "c001"}}',
        '{"capitulos": ["c001"]}',
        '[{"capitulos": []}]',
        '{"titulo": "sem a lista de capítulos"}',
    ],
)
def test_livro_json_com_forma_errada_e_recusado(pasta: Path, conteudo: str) -> None:
    _ = (pasta / "livro.json").write_text(conteudo)
    with pytest.raises(trabalho.PastaDeTrabalhoInvalidaError, match=r"livro\.json"):
        _ = trabalho.ler_capitulos(pasta)


def test_json_que_nao_e_utf8_e_recusado_com_o_caminho(pasta: Path) -> None:
    # A6 da auditoria: saía só "'utf-8' codec can't decode byte 0xff", sem o arquivo.
    _ = (pasta / "limpeza.json").write_bytes(b"\xff{}")
    with pytest.raises(trabalho.PastaDeTrabalhoInvalidaError, match=r"limpeza\.json"):
        _ = trabalho.ler_limpeza(pasta)


def test_json_aninhado_demais_e_recusado_com_o_caminho(pasta: Path) -> None:
    # A6 da auditoria: o RecursionError passava pela CLI como traceback.
    _ = (pasta / "limpeza.json").write_text("[" * 100_000 + "]" * 100_000)
    with pytest.raises(trabalho.PastaDeTrabalhoInvalidaError, match=r"limpeza\.json"):
        _ = trabalho.ler_limpeza(pasta)


def test_juncao_repetida_no_registro_chega_repetida(pasta: Path) -> None:
    juncao = Juncao("c001-s0006", "c001-s0005")
    trabalho.gravar_limpeza(pasta, LivroLimpo((), (), juncoes=(juncao, juncao)))
    assert len(trabalho.ler_limpeza(pasta).juntados) == 2


def test_numero_grande_demais_no_json_e_recusado_com_o_caminho(pasta: Path) -> None:
    # N5 da pós-auditoria: o json recusa inteiro de mais de 4.300 algarismos com um
    # ValueError simples, e a CLI mostrava a mensagem sem o arquivo.
    _ = (pasta / "limpeza.json").write_text('{"remocoes": [' + "9" * 5000 + "]}")
    with pytest.raises(trabalho.PastaDeTrabalhoInvalidaError, match=r"limpeza\.json"):
        _ = trabalho.ler_limpeza(pasta)
