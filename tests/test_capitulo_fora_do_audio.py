# SPDX-License-Identifier: GPL-3.0-or-later
"""O capítulo declarado no `preparar` sai inteiro do áudio, registrado (ADR-0008, "Tratado em
português e em espanhol", decisão 4).

O Mateus não quer ouvir a lista de autores, o sumário de papel nem os anexos de um tratado. O
`preparar --sem-capitulo cNNN` tira o capítulo pelo ID, e nenhum nome de capítulo entra no pacote.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.comandos.cli import principal
from earbook.comandos.montar import conferir_pasta
from earbook.comandos.preparar import preparar
from earbook.dominio.fora_do_audio import MOTIVO_DO_CAPITULO_FORA, CapituloDesconhecidoError
from earbook.dominio.limpeza import limpar_para_o_ouvido
from earbook.dominio.segmento import Papel, Segmento
from tests.livro_de_teste import montar_epub


def _capitulo(capitulo: str, textos: list[str]) -> tuple[str, list[Segmento]]:
    segmentos = [
        Segmento(f"{capitulo}-s{n:04d}", Papel.PARAGRAFO, texto)
        for n, texto in enumerate(textos, 1)
    ]
    return capitulo, segmentos


LIVRO = [
    _capitulo("c001", ["O texto do primeiro capítulo."]),
    _capitulo("c002", ["Fulano de Tal, professor.", "Beltrano de Tal, professora."]),
    _capitulo("c003", ["O texto do terceiro capítulo."]),
]


def test_capitulo_declarado_sai_inteiro_com_cada_segmento_registrado() -> None:
    livro = limpar_para_o_ouvido(LIVRO, "Livro", "Autor", fora=("c002",))
    assert [(c.capitulo, [s.texto for s in c.segmentos]) for c in livro.capitulos] == [
        ("c001", ["O texto do primeiro capítulo."]),
        ("c002", []),
        ("c003", ["O texto do terceiro capítulo."]),
    ]
    assert [(r.id, r.motivo, r.texto) for r in livro.remocoes] == [
        ("c002-s0001", MOTIVO_DO_CAPITULO_FORA, "Fulano de Tal, professor."),
        ("c002-s0002", MOTIVO_DO_CAPITULO_FORA, "Beltrano de Tal, professora."),
    ]


def test_sem_capitulo_declarado_nada_sai() -> None:
    livro = limpar_para_o_ouvido(LIVRO, "Livro", "Autor")
    assert livro.remocoes == ()


def test_capitulo_que_o_livro_nao_tem_e_erro_com_o_valor_recebido() -> None:
    with pytest.raises(CapituloDesconhecidoError, match="c009"):
        _ = limpar_para_o_ouvido(LIVRO, "Livro", "Autor", fora=("c002", "c009"))


def test_o_capitulo_declarado_nao_conta_como_prova_para_o_resto_do_livro() -> None:
    # O capítulo que sai não prova o hífen da quebra: "identifi-" + "car" só perde o hífen
    # quando o livro que fica escreve "identificar" (ADR-0003).
    livro = [
        _capitulo("c001", ["O médico deve observar e identifi-", "car o sinal."]),
        _capitulo("c002", ["Sumário: como identificar o sinal."]),
    ]
    limpo = limpar_para_o_ouvido(livro, "Livro", "Autor", fora=("c002",))
    assert limpo.capitulos[0].segmentos[0].texto == "O médico deve observar e identifi-car o sinal."


def test_preparar_tira_o_capitulo_pedido_e_o_conferir_aceita(tmp_path: Path) -> None:
    epub = montar_epub(
        tmp_path / "livro.epub",
        {
            "a.xhtml": "<h1>Um</h1><p>O texto do primeiro capítulo.</p>",
            "b.xhtml": "<h1>Autores</h1><p>Fulano de Tal, professor.</p>",
        },
        idioma="pt-BR",
    )
    pasta = tmp_path / "livro.earbook"
    preparo = preparar(epub, pasta, sem_capitulos=("c002",))
    assert [(r.id, r.motivo) for r in preparo.limpeza.remocoes] == [
        ("c002-s0001", MOTIVO_DO_CAPITULO_FORA),
        ("c002-s0002", MOTIVO_DO_CAPITULO_FORA),
    ]
    assert conferir_pasta(pasta) == ()


def test_cli_aceita_a_opcao_repetida_e_resume_o_motivo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    epub = montar_epub(
        tmp_path / "livro.epub",
        {
            "a.xhtml": "<p>O texto do primeiro capítulo.</p>",
            "b.xhtml": "<p>Fulano de Tal, professor.</p>",
            "c.xhtml": "<p>Respostas das questões.</p>",
        },
    )
    codigo = principal(["preparar", str(epub), "--sem-capitulo", "c002", "--sem-capitulo", "c003"])
    assert codigo == 0
    assert f"  {MOTIVO_DO_CAPITULO_FORA}: 2" in capsys.readouterr().out


def test_cli_com_capitulo_desconhecido_sai_com_1_e_nao_deixa_pasta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    epub = montar_epub(tmp_path / "livro.epub", {"a.xhtml": "<p>O texto.</p>"})
    assert principal(["preparar", str(epub), "--sem-capitulo", "c007"]) == 1
    assert "c007" in capsys.readouterr().err
    assert not (tmp_path / "livro.earbook").exists()
