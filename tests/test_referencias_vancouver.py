# SPDX-License-Identifier: GPL-3.0-or-later
"""As referências no estilo Vancouver saem do texto lido, registradas (ADR-0008, "Referências no
estilo Vancouver").

O Practical Management of Pain traz um parágrafo por referência ("86. Adams MA, Hutton WC. …
J Bone Joint Surg Br. 1980;62:358\u2013362."); o Bonica cola até 30 numa nota só, que pode abrir no
meio de uma. O Mateus decidiu tirá-las antes de estimar a tradução. A regra olha o conteúdo,
nunca o título.
"""

from __future__ import annotations

from pathlib import Path

from earbook.comandos.preparar import preparar
from earbook.dominio.fora_do_audio import MOTIVO_DO_VANCOUVER
from earbook.dominio.limpeza import LivroLimpo, limpar_para_o_ouvido
from earbook.dominio.segmento import Papel, Segmento
from tests.livro_de_teste import montar_epub

REFERENCES = (Papel.TITULO, "References")
PROSA = (Papel.PARAGRAFO, "Facet joint pain is common in older adults with back pain.")
PROXIMO = (Papel.TITULO, "CHAPTER 91 Assessment and Treatment of Substance Use Disorders")
# O crédito do capítulo do Bonica, em maiúsculas: não é lista de autores.
CREDITO = (Papel.PARAGRAFO, "ANDREW J. SAXON, JAMES P. ROBINSON, and MARK D.")


def _referencia(n: int) -> str:
    return (
        f"{n}. Adams MA, Hutton WC. The effect of posture on the apophysial joints. "
        f"J Bone Joint Surg Br. {1980 + n % 30};{n}:358\u2013362."
    )


def _numeradas(de: int, ate: int) -> list[tuple[Papel, str]]:
    return [(Papel.PARAGRAFO, _referencia(n)) for n in range(de, ate + 1)]


def _limpar(segmentos: list[tuple[Papel, str]]) -> LivroLimpo:
    capitulo = [
        Segmento(f"c001-s{n:04d}", papel, texto) for n, (papel, texto) in enumerate(segmentos, 1)
    ]
    return limpar_para_o_ouvido([("c001", capitulo)], "Livro", "Autor")


def _sobrou(livro: LivroLimpo) -> list[str]:
    return [s.texto for capitulo in livro.capitulos for s in capitulo.segmentos]


def test_dez_referencias_numeradas_e_o_titulo_logo_antes_saem_registrados() -> None:
    livro = _limpar([PROSA, REFERENCES, *_numeradas(1, 10), PROXIMO])
    assert _sobrou(livro) == [PROSA[1], PROXIMO[1]]
    assert [(r.id, r.motivo) for r in livro.remocoes] == [
        (f"c001-s{n:04d}", MOTIVO_DO_VANCOUVER) for n in range(2, 13)
    ]


def test_nove_citacoes_de_periodico_ficam() -> None:
    assert len(_sobrou(_limpar([REFERENCES, *_numeradas(1, 9)]))) == 10


def test_referencias_coladas_numa_nota_que_abre_no_meio_saem() -> None:
    # Bonica, c006-s1632: o segmento abre no meio da referência 107, e o fim da lista é seguido
    # do título do próximo capítulo e do crédito em maiúsculas.
    primeira = "behavioral approach. Phys Ther 1002;72:279\u2013290. " + " ".join(
        _referencia(n) for n in range(108, 113)
    )
    segunda = " ".join(_referencia(n) for n in range(113, 118))
    notas = [(Papel.NOTA, primeira), (Papel.NOTA, segunda)]
    livro = _limpar([PROSA, REFERENCES, *notas, PROXIMO, CREDITO])
    assert _sobrou(livro) == [PROSA[1], PROXIMO[1], CREDITO[1]]


def test_prosa_com_et_al_e_ano_com_ponto_e_virgula_fica() -> None:
    # A prosa dos dois livros cita por número sobrescrito ("Fanuele et al.7"): nunca traz
    # ano;volume:página.
    prosa = [
        (Papel.PARAGRAFO, f"Adams et al.{n} found that in 2011;36 of the 50 patients improved.")
        for n in range(12)
    ]
    assert len(_sobrou(_limpar(prosa))) == 12


def test_pedaco_sem_sinal_entre_referencias_sai_com_elas() -> None:
    # Practical: a quebra de página parte a referência, e o pedaço do meio não tem número nem
    # citação ("…between nonorganic physical findings (Waddell signs) and second-").
    pedaco = (Papel.PARAGRAFO, "between nonorganic physical findings (Waddell signs) and second-")
    livro = _limpar([*_numeradas(1, 5), pedaco, *_numeradas(6, 10)])
    assert _sobrou(livro) == []


def test_tres_paragrafos_sem_sinal_partem_a_regiao_e_ficam() -> None:
    # Practical: a caixa "Key Points" do PDF cai no meio da lista.
    caixa = [(Papel.PARAGRAFO, f"• Key point number {n} about pediatric pain.") for n in range(3)]
    livro = _limpar([*_numeradas(1, 10), *caixa, *_numeradas(11, 20)])
    assert _sobrou(livro) == [texto for _, texto in caixa]


def test_leituras_sugeridas_antes_de_references_saem_com_a_lista() -> None:
    # Practical: "Suggested Readings", sem número, e logo depois "References".
    leituras = [
        (
            Papel.PARAGRAFO,
            f"Bartley EJ, Fillingim RB. Sex differences. Br J Anaesth. 2013;{n}:52\u20138.",
        )
        for n in range(4)
    ]
    sugeridas = (Papel.TITULO, "Suggested Readings")
    livro = _limpar([PROSA, sugeridas, *leituras, REFERENCES, *_numeradas(1, 10)])
    assert _sobrou(livro) == [PROSA[1]]


def test_referencia_numerada_sem_citacao_antes_da_primeira_sai() -> None:
    # Practical, c004-s0331: a primeira referência é de uma instituição, sem autor Vancouver.
    instituicao = (
        Papel.PARAGRAFO,
        "1. American Hospital Association. Utilization and volume. Washington, DC: AHA; 2016.",
    )
    livro = _limpar([PROSA, REFERENCES, instituicao, *_numeradas(2, 11)])
    assert _sobrou(livro) == [PROSA[1]]


def test_prosa_com_url_logo_antes_da_lista_fica() -> None:
    url = (Papel.PARAGRAFO, "More resources are available at https://www.iasp-pain.org today.")
    livro = _limpar([url, *_numeradas(1, 10)])
    assert _sobrou(livro) == [url[1]]


def test_preparar_registra_as_referencias_em_limpeza_json(tmp_path: Path) -> None:
    corpo = "<p>Facet pain is common.</p><h2>References</h2>" + "".join(
        f"<p>{_referencia(n)}</p>" for n in range(1, 11)
    )
    pasta = tmp_path / "livro.earbook"
    preparo = preparar(montar_epub(tmp_path / "livro.epub", {"a.xhtml": corpo}), pasta)
    assert len(preparo.limpeza.remocoes) == 11
    registro = (pasta / "limpeza.json").read_text(encoding="utf-8")
    assert registro.count(f'"motivo": "{MOTIVO_DO_VANCOUVER}"') == 11


def test_titulo_do_proximo_capitulo_e_a_prosa_que_cita_um_periodico_ficam() -> None:
    # Bonica: o fim da lista é seguido do título do próximo capítulo. A prosa dele que cita um
    # periódico por extenso não é referência, e o título não se atravessa por ela.
    cita = (Papel.PARAGRAFO, "Melzack showed (Pain 1997;72:227) that the gate can close.")
    livro = _limpar([*_numeradas(1, 10), PROXIMO, CREDITO, cita])
    assert _sobrou(livro) == [PROXIMO[1], CREDITO[1], cita[1]]


def test_estadio_em_romano_nao_e_autor() -> None:
    # "Stage IV," tem a forma de "Adams MA,": sobrenome e iniciais. O romano não é inicial.
    estadio = (Papel.PARAGRAFO, "Stage IV, the most severe, has distant bone metastases.")
    livro = _limpar([*_numeradas(1, 10), estadio])
    assert _sobrou(livro) == [estadio[1]]


def test_prosa_com_cara_de_autor_antes_do_titulo_fica() -> None:
    # Só a lista com citação de periódico se junta à região depois do título.
    prosa = (Papel.PARAGRAFO, "Melzack R, Wall PD, and their gate theory changed pain care.")
    livro = _limpar([prosa, REFERENCES, *_numeradas(1, 10)])
    assert _sobrou(livro) == [prosa[1]]


def test_pedaco_fraco_depois_da_ultima_referencia_sai() -> None:
    # Practical: o site da referência partida pela página, sem autor nem citação.
    site = (Papel.PARAGRAFO, "Available at: https://www.cdc.gov/drugoverdose/guideline.html.")
    livro = _limpar([*_numeradas(1, 10), site, PROXIMO])
    assert _sobrou(livro) == [PROXIMO[1]]


def test_subtitulo_entre_o_titulo_e_a_lista_sai_com_as_leituras() -> None:
    # Practical, c075: "Suggested Readings", as leituras, "References", o subtítulo da seção em
    # parágrafo e a lista numerada.
    leituras = [
        (Papel.PARAGRAFO, f"Alexander JW, Solomkin JS. Infections. Ann Surg. 2011;{n}:1082.")
        for n in range(3)
    ]
    subtitulo = (Papel.PARAGRAFO, "Risk of Infection in Interventional Pain Procedures")
    sugeridas = (Papel.TITULO, "Suggested Readings")
    livro = _limpar([PROSA, sugeridas, *leituras, REFERENCES, subtitulo, *_numeradas(1, 10)])
    assert _sobrou(livro) == [PROSA[1]]
