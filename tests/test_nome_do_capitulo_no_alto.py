# SPDX-License-Identifier: GPL-3.0-or-later
"""O nome que o sumário interno do PDF dá ao capítulo, escrito na página que ele abre, é o título
do capítulo, mesmo no tamanho do corpo (ADR-0004, "Romance convertido pelo Calibre").

No Kafka à beira-mar (PDF do Calibre, corpo de 6 pt), a página que abre o capítulo começa por
"Capítulo 2" ou pelo nome do prólogo, com meia-risca, no tamanho e na fonte do corpo, e o sumário
interno chama a abertura de "Capítulo 2" e "Prólogo - Um Menino Chamado Corvo". Como parágrafo,
o nome não era lido como título, o prólogo colava na ficha catalográfica da página de antes, que
não fecha frase, e o capítulo abria no primeiro título da página ("RELATÓRIO…"), quatro
parágrafos depois.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.sumario_interno import Abertura, marcar_nomes_dos_capitulos
from earbook.dominio.tipo_da_linha import Medidas, TipoDeBloco, tipo_da_linha
from tests.pdf_de_teste import ItemDeTeste, LinhaDeTeste, montar_pdf_com_sumario

MEDIDAS = Medidas(6.0, 0.02, negrito_destaca=False, maiusculas_destacam=True)


def _linha(texto: str, topo: float) -> Linha:
    return Linha(texto, x=25, fim=227, topo=topo, tamanho=6.0)


def _marcadas(paginas: list[Pagina], aberturas: tuple[Abertura, ...]) -> list[str]:
    marcadas = marcar_nomes_dos_capitulos(paginas, aberturas)
    return [linha.texto for pagina in marcadas for linha in pagina.linhas if linha.nome_do_capitulo]


def test_linha_com_o_nome_da_abertura_na_pagina_dela_e_titulo() -> None:
    paginas = [
        Pagina(21, (_linha("Capítulo 2", 0.058), _linha("Este documento, de classificação.", 0.26)))
    ]
    marcadas = marcar_nomes_dos_capitulos(paginas, (Abertura(21, "Capítulo 2"),))
    rotulo = marcadas[0].linhas[0]
    assert rotulo.nome_do_capitulo
    assert tipo_da_linha(rotulo, MEDIDAS) is TipoDeBloco.TITULO
    assert tipo_da_linha(marcadas[0].linhas[1], MEDIDAS) is TipoDeBloco.PARAGRAFO


def test_nome_com_traco_e_espaco_diferentes_e_o_mesmo() -> None:
    paginas = [Pagina(9, (_linha("Prólogo \u2013  Um Menino Chamado Corvo", 0.058),))]
    aberturas = (Abertura(9, "Prólogo - Um Menino Chamado Corvo"),)
    assert _marcadas(paginas, aberturas) == ["Prólogo \u2013  Um Menino Chamado Corvo"]


def test_nome_da_abertura_em_outra_pagina_nao_e_titulo() -> None:
    # A frase que cita o capítulo, ou o "Capítulo 2" do sumário de papel, fica parágrafo.
    paginas = [Pagina(7, (_linha("Capítulo 2", 0.3),)), Pagina(21, (_linha("Texto.", 0.26),))]
    assert _marcadas(paginas, (Abertura(21, "Capítulo 2"),)) == []


def test_linha_que_so_comeca_pelo_nome_nao_e_titulo() -> None:
    paginas = [Pagina(21, (_linha("Capítulo 2 conta o relatório.", 0.26),))]
    assert _marcadas(paginas, (Abertura(21, "Capítulo 2"),)) == []


def test_so_a_primeira_linha_com_o_nome_e_titulo() -> None:
    # Regressão do Hard Parts: o rodapé da O'Reilly repete o nome da seção na página que ela abre
    # ("Introducing the Sysops Squad Saga | 13", sem o número). Marcado também, ele virava título no
    # meio do parágrafo que passa da página, e a borda deixava de tirá-lo.
    nome = "Introducing the Sysops Squad Saga"
    paginas = [
        Pagina(33, (_linha(nome, 0.1), _linha("Penultimate Electronics…", 0.3), _linha(nome, 0.96)))
    ]
    marcadas = marcar_nomes_dos_capitulos(paginas, (Abertura(33, nome),))
    assert [linha.nome_do_capitulo for linha in marcadas[0].linhas] == [True, False, False]


def _capitulos_do_epub(epub: Path) -> list[str]:
    with zipfile.ZipFile(epub) as zip_:
        nomes = sorted(n for n in zip_.namelist() if re.fullmatch(r"OEBPS/c\d{3}\.xhtml", n))
        return [zip_.read(nome).decode().split("<body>")[1] for nome in nomes]


def test_importar_pdf_abre_o_capitulo_no_nome_do_tamanho_do_corpo(tmp_path: Path) -> None:
    paginas = [
        [LinhaDeTeste("Rio de Janeiro: Objetiva, 2012. CDD: 895.63 CDU: 821.521-3", 72, 700)],
        [
            LinhaDeTeste("Prólogo \u2013 Um Menino Chamado Corvo", 72, 740),
            LinhaDeTeste("O menino chamado Corvo fala comigo.", 72, 600),
        ],
        [
            LinhaDeTeste("Capítulo 1", 72, 740),
            LinhaDeTeste("Este documento esteve arquivado.", 72, 600),
            LinhaDeTeste("RELATÓRIO DO SERVIÇO DE INTELIGÊNCIA", 72, 500, tamanho=14),
            LinhaDeTeste("A entrevista com a professora.", 72, 400),
        ],
        *[
            [LinhaDeTeste(f"Capítulo {n}", 72, 740), LinhaDeTeste("Quando despertei.", 72, 600)]
            for n in (2, 3)
        ],
    ]
    itens = [
        ItemDeTeste(1, "Créditos", 1),
        ItemDeTeste(1, "Prólogo - Um Menino Chamado Corvo", 2),
        *[ItemDeTeste(1, f"Capítulo {n}", n + 2) for n in (1, 2, 3)],
    ]
    epub = tmp_path / "livro.epub"
    _ = importar_pdf(montar_pdf_com_sumario(tmp_path / "l.pdf", paginas, itens), epub, "pt-BR")
    creditos, prologo, capitulo, *_ = _capitulos_do_epub(epub)
    assert "Prólogo" not in creditos
    assert prologo.lstrip().startswith("<h1>Prólogo \u2013 Um Menino Chamado Corvo</h1>")
    assert capitulo.lstrip().startswith("<h1>Capítulo 1</h1>\n<p>Este documento esteve arquivado.")
