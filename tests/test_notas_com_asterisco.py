# SPDX-License-Identifier: GPL-3.0-or-later
"""A nota que o livro marca com asterisco sai do meio do texto (ADR-0004, "Romance convertido pelo
Calibre"; ADR-0011, decisão 3 do Mateus: "nota '*' no fim do capítulo, sem o marcador").

No Kafka à beira-mar, a chamada vem colada à palavra ou à pontuação ("Report*", "“Owan-y
ama”.**", "shamisen,***", "pólo!”****"), no tamanho do corpo, e a nota fica no pé da última
página do capítulo, na mesma letra ("* Incidente Morro da Tigela, 1944: Relatório (N. da T.)").
O asterisco solto entre espaços ("na cidade de **", "rua ** do bairro") e o colado ao algarismo
("5* anos", "194*") são a censura do próprio livro e ficam.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from earbook.comandos.importar_pdf import importar_pdf, resumo_da_importacao
from earbook.dominio.blocos import montar_blocos
from earbook.dominio.notas_com_asterisco import notas_com_asterisco
from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.tipo_da_linha import TipoDeBloco
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf


def _linha(texto: str, topo: float = 0.5) -> Linha:
    return Linha(texto, x=25, fim=227, topo=topo, tamanho=6.0)


def _pagina(numero: int, *textos: str) -> Pagina:
    return Pagina(numero, tuple(_linha(t, 0.1 + 0.02 * i) for i, t in enumerate(textos)))


def _resumo(paginas: tuple[Pagina, ...]) -> list[tuple[str, str]]:
    def marca(linha: Linha) -> str:
        return "abre" if linha.abre_nota else "nota" if linha.nota else ""

    return [(marca(linha), linha.texto) for pagina in paginas for linha in pagina.linhas]


def test_chamada_sai_da_frase_e_a_nota_do_pe_da_pagina_vira_nota() -> None:
    feitas = notas_com_asterisco(
        [
            _pagina(21, "Título: Rice Bowl Hill Incident, 1944: Report*", "Documento número 4."),
            _pagina(
                26,
                "As crianças voltaram a si.",
                "* Incidente Morro da Tigela, 1944: Relatório (N. da T.)",
            ),
        ]
    )
    assert _resumo(feitas.paginas) == [
        ("", "Título: Rice Bowl Hill Incident, 1944: Report"),
        ("", "Documento número 4."),
        ("", "As crianças voltaram a si."),
        ("abre", "Incidente Morro da Tigela, 1944: Relatório (N. da T.)"),
    ]
    assert [(r.pagina, r.texto) for r in feitas.chamadas] == [(21, "Report[*]")]


def test_cada_nota_abre_a_sua_e_a_linha_seguinte_continua_a_nota() -> None:
    feitas = notas_com_asterisco(
        [
            _pagina(
                24, "conhecida como “Owan-y ama”.** Suas encostas", "couro de shamisen,*** mas"
            ),
            _pagina(
                26,
                "** Morro da Tigela. (N. da T.)",
                "*** Instrumento musical japonês de três cordas, em que a caixa é",
                "revestida de pele. (N. do E.)",
            ),
        ]
    )
    assert _resumo(feitas.paginas)[:2] == [
        ("", "conhecida como “Owan-y ama”. Suas encostas"),
        ("", "couro de shamisen, mas"),
    ]
    assert _resumo(feitas.paginas)[2:] == [
        ("abre", "Morro da Tigela. (N. da T.)"),
        ("abre", "Instrumento musical japonês de três cordas, em que a caixa é"),
        ("nota", "revestida de pele. (N. do E.)"),
    ]


def test_censura_do_livro_fica_e_a_linha_que_comeca_por_ela_nao_e_nota() -> None:
    # p. 21: "…da Escola Municipal" | "** à época do incidente." vem antes de qualquer chamada
    # "**"; a primeira só aparece na p. 24.
    paginas = [
        _pagina(
            21,
            "O inquérito no distrito de **, província de Yamanashi, e na cidade de **.",
            "Escola Municipal",
            "** à época do incidente. Depoimento registrado em gravador.",
        ),
        _pagina(195, "O corpo do escultor Koichi Tamura (5* anos)", "nasceu em 194* em Kokubunji."),
    ]
    feitas = notas_com_asterisco(paginas)
    assert feitas.paginas == tuple(paginas)
    assert feitas.chamadas == ()


def test_chamada_sem_nota_fica_no_texto() -> None:
    paginas = [_pagina(1, "Uma palavra marcada* sem nota no livro.", "E o texto segue.")]
    assert notas_com_asterisco(paginas).paginas == tuple(paginas)


def test_nota_com_mais_asteriscos_que_a_chamada_nao_e_dela() -> None:
    paginas = [_pagina(1, "A palavra*, e o texto segue."), _pagina(2, "** Não é a nota dela.")]
    assert notas_com_asterisco(paginas).paginas == tuple(paginas)


def test_cada_nota_e_um_bloco_de_nota_e_a_continuacao_vai_junto() -> None:
    paginas = notas_com_asterisco(
        [
            _pagina(1, "Report* e o resto do relatório, que o", "couro de shamisen,*** mas"),
            _pagina(
                2,
                "Fim do capítulo.",
                "* Incidente Morro da Tigela. (N. da T.)",
                "*** Instrumento musical japonês de três cordas, em que a caixa é",
                "revestida de pele. (N. do E.)",
            ),
        ]
    ).paginas
    blocos = montar_blocos(paginas).blocos
    assert [(b.tipo, b.texto) for b in blocos if b.tipo is TipoDeBloco.NOTA] == [
        (TipoDeBloco.NOTA, "Incidente Morro da Tigela. (N. da T.)"),
        (
            TipoDeBloco.NOTA,
            (
                "Instrumento musical japonês de três cordas, em que a caixa é revestida de pele. "
                "(N. do E.)"
            ),
        ),
    ]


def test_importar_pdf_leva_a_nota_de_asterisco_para_nota(tmp_path: Path) -> None:
    paginas = [
        [
            LinhaDeTeste("Título: Rice Bowl Hill Incident, 1944: Report*", 72, 700),
            LinhaDeTeste("As crianças voltaram a si.", 72, 600),
            LinhaDeTeste("* Incidente Morro da Tigela, 1944: Relatório (N. da T.)", 72, 100),
        ]
    ]
    epub = tmp_path / "livro.epub"
    importacao = importar_pdf(montar_pdf(tmp_path / "l.pdf", paginas), epub, "pt-BR")
    with zipfile.ZipFile(epub) as zip_:
        capitulo = zip_.read("OEBPS/c001.xhtml").decode()
    assert "1944: Report As crianças voltaram a si.</p>" in capitulo
    assert (
        '<aside epub:type="footnote"><p>Incidente Morro da Tigela, 1944: Relatório (N. da T.)</p>'
    ) in capitulo
    assert "1 chamada de nota com asterisco tirada" in resumo_da_importacao(importacao)


def test_chamada_longe_demais_nao_prova_a_nota() -> None:
    # Revisão: a chamada sem nota ficava pendente para sempre, e a censura que abre uma linha 40
    # páginas depois virava nota, levando o resto da página para o fim do capítulo.
    paginas = [
        _pagina(1, "A palavra marcada* e o texto segue."),
        _pagina(41, "Escola Municipal", "* à época do incidente. Depoimento registrado."),
    ]
    assert notas_com_asterisco(paginas).paginas == tuple(paginas)


def test_nota_no_pe_da_coluna_acaba_onde_a_outra_coluna_sobe() -> None:
    # Regressão do Dalgalarrondo, p. 151: a nota fica no pé da primeira coluna, e a ordem de
    # leitura segue pela segunda, do alto da página. Levada até o fim da página, a nota engolia a
    # segunda coluna inteira, e o texto dela ia para o fim do capítulo.
    pagina = Pagina(
        151,
        (
            _linha("e de falsas identificações.*", 0.40),
            _linha("Capgras que reconhecia seu marido (real)", 0.80),
            _linha("* Todas essas alterações poderiam muito bem ser", 0.90),
            _linha("em descrevê-las neste capítulo.", 0.92),
            _linha("como se ele fosse um sósia. Esse falso re-", 0.10),
            _linha("conhecimento ocorria não pela aparência", 0.12),
        ),
    )
    assert _resumo(notas_com_asterisco([pagina]).paginas) == [
        ("", "e de falsas identificações."),
        ("", "Capgras que reconhecia seu marido (real)"),
        ("abre", "Todas essas alterações poderiam muito bem ser"),
        ("nota", "em descrevê-las neste capítulo."),
        ("", "como se ele fosse um sósia. Esse falso re-"),
        ("", "conhecimento ocorria não pela aparência"),
    ]


def test_nota_da_tabela_acaba_onde_a_letra_volta_ao_tamanho_do_corpo() -> None:
    # Regressão do Practical: a nota da tabela ("* = Measure was selected…") fica no meio da
    # página, em letra menor, e o corpo segue embaixo dela. Levada até o fim da página, a nota
    # engolia os parágrafos do corpo ("pain interference…", "Historically…").
    pagina = Pagina(
        412,
        (
            Linha("Numerical rating scale (NRS)* Pain intensity", 25, 227, 0.30, 6.5),
            Linha("* = Measure was selected by the IMMPACT panel.", 25, 227, 0.40, 6.5),
            Linha("pain interference, or coping beliefs and provide", 25, 227, 0.45, 9.0),
            Linha("quantitative data that can be used.", 25, 227, 0.47, 9.0),
        ),
    )
    assert _resumo(notas_com_asterisco([pagina]).paginas) == [
        ("", "Numerical rating scale (NRS) Pain intensity"),
        ("abre", "= Measure was selected by the IMMPACT panel."),
        ("", "pain interference, or coping beliefs and provide"),
        ("", "quantitative data that can be used."),
    ]
