# SPDX-License-Identifier: GPL-3.0-or-later
"""A nota em outra língua que não a do livro sai do áudio (ADR-0008, "Nota em outra língua";
ADR-0011, decisão 4 do Mateus: "fora a nota com o original em inglês do poema que o texto já
leu traduzido"; decisão C do Mateus, 2026-11-20).

No Kafka à beira-mar, a nota "****" traz o verso de Macbeth em inglês, que o texto leu na
tradução de Manuel Bandeira: "No, this my hand will rather/ The multitudinous seas incarnadine /
Making the green one red! (Trad. de Manuel Bandeira.) (N. da T.)". A voz de pt-BR lê o inglês
com a pronúncia do português.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.comandos.preparar import preparar
from earbook.dominio.limpeza import limpar_para_o_ouvido
from earbook.dominio.livro_limpo import LivroLimpo
from earbook.dominio.segmento import Papel, Segmento
from tests.livro_de_teste import montar_epub

MOTIVO = "nota em outra língua que não a do livro"
MACBETH = (
    "No, this my hand will rather/ The multitudinous seas incarnadine / Making the green one "
    "red! (Trad. de Manuel Bandeira.) (N. da T.)"
)
TEXTO = "Será que todo o oceano de Netuno conseguirá lavar o sangue desta mão?"


def _limpar(itens: list[tuple[Papel, str]], idioma: str) -> LivroLimpo:
    segmentos = [
        Segmento(f"c001-s{n:04d}", papel, texto) for n, (papel, texto) in enumerate(itens, 1)
    ]
    return limpar_para_o_ouvido(
        [("c001", segmentos)], "Kafka à beira-mar", "Murakami", idioma=idioma
    )


def _saem(livro: LivroLimpo) -> list[tuple[str, str]]:
    return [(r.id, r.motivo) for r in livro.remocoes]


def test_nota_com_o_original_em_ingles_sai_do_livro_em_portugues() -> None:
    livro = _limpar([(Papel.PARAGRAFO, TEXTO), (Papel.NOTA, MACBETH)], "pt-BR")
    assert _saem(livro) == [("c001-s0002", MOTIVO)]
    assert [s.texto for c in livro.capitulos for s in c.segmentos] == [TEXTO]


@pytest.mark.parametrize(
    "nota",
    [
        "Incidente Morro da Tigela, 1944: Relatório (N. da T.)",
        (
            "Instrumento musical japonês de três cordas, em que a caixa de ressonância é "
            "coberta por pele de gato. (N. do E.)"
        ),
        # O título em inglês dentro da nota em português: a nota é da língua do livro.
        "Ver o ensaio The Doors of Perception, de Aldous Huxley, sobre a mescalina.",
        # Auditoria: menos de 3 palavras funcionais não dizem a língua, mesmo na proporção.
        "Ver The Doors.",
        # Auditoria: o inglês entre parênteses não conta; fora deles, a nota é em português.
        (
            "O verso original (no, this my hand will rather the seas incarnadine) foi traduzido "
            "por Manuel Bandeira."
        ),
        # Auditoria: 5 palavras do inglês numa nota longa em português ficam abaixo da proporção.
        (
            "Ver o ensaio The Doors of Perception and the Heaven and Hell, de Aldous Huxley, que "
            "trata da mescalina, da experiência mística e da arte visionária em detalhe, com "
            "relatos do próprio autor e uma discussão longa sobre a percepção."
        ),
        # A nota sem palavra de ligação de língua nenhuma não diz a língua.
        "Rice Bowl Hill Incident, 1944: Report",
    ],
)
def test_nota_na_lingua_do_livro_ou_sem_lingua_clara_fica(nota: str) -> None:
    assert _saem(_limpar([(Papel.PARAGRAFO, TEXTO), (Papel.NOTA, nota)], "pt-BR")) == []


def test_paragrafo_em_outra_lingua_fica() -> None:
    # A epígrafe e a citação no original ficam (ADR-0011, decisão 11): a regra é só da nota.
    epigrafe = (
        "No, this my hand will rather the multitudinous seas incarnadine, making the green one red."
    )
    assert _saem(_limpar([(Papel.PARAGRAFO, epigrafe)], "pt-BR")) == []


def test_nota_em_espanhol_sai_do_livro_em_portugues() -> None:
    nota = "El autor la escribió con los nombres de su época y no la tradujo al portugués."
    assert _saem(_limpar([(Papel.NOTA, nota)], "pt-BR")) == [("c001-s0001", MOTIVO)]


def test_livro_em_ingles_nao_tira_nota() -> None:
    # As listas medidas são do inglês e do espanhol contra o português (ADR-0013): no livro em
    # inglês, a nota em português fica, e a em inglês também.
    em_portugues = "Esta é a tradução que o autor usou, e não a de outro tradutor da obra."
    em_ingles = "This is the translation that the author used, and not the one of the others."
    livro = _limpar([(Papel.NOTA, em_portugues), (Papel.NOTA, em_ingles)], "en")
    assert _saem(livro) == []


def test_livro_sem_lingua_declarada_nao_tira_nota() -> None:
    assert _saem(_limpar([(Papel.NOTA, MACBETH)], "und")) == []


def test_preparar_tira_a_nota_em_outra_lingua_pela_lingua_do_epub(tmp_path: Path) -> None:
    corpo = f'<p>{TEXTO}</p><aside epub:type="footnote"><p>{MACBETH}</p></aside>'
    epub = montar_epub(tmp_path / "l.epub", {"c1.xhtml": corpo}, idioma="pt-BR")
    preparo = preparar(epub, tmp_path / "l.earbook")
    assert [r.motivo for r in preparo.limpeza.remocoes] == [MOTIVO]
