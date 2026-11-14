# SPDX-License-Identifier: GPL-3.0-or-later
"""A lista de leitura logo antes da bibliografia provada sai com ela (ADR-0004, "Lista de leitura
logo antes da bibliografia").

No Practical, a lista de leitura sugerida vem na letra das referências (AGaramondPro de 9 pt, com
o corpo de 10), sob um título em letra de título, logo antes do título da lista numerada. O
título fecha a corrida: a lista curta ficava numa corrida só dela, abaixo das 10 citações, e
voltava a ser lida. O texto aqui é sintético.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from earbook.comandos.cli import principal
from earbook.dominio.bibliografia_do_pdf import (
    MOTIVO_DA_BIBLIOGRAFIA_DO_PDF,
    MOTIVO_DA_LISTA_DE_LEITURA,
    tirar_bibliografia,
)
from earbook.dominio.pagina import Linha, Pagina
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf

CORPO = "Garamond"
SEM_SERIFA = "Myriad"
PASSO = 0.004


def _linha(texto: str, *, fonte: str = CORPO, tamanho: float = 10.0) -> Linha:
    return Linha(texto, x=42.0, fim=290.0, topo=0.0, tamanho=tamanho, fonte=fonte)


def _pequena(texto: str) -> Linha:
    """A letra das citações: a família do corpo, um ponto menor."""
    return _linha(texto, tamanho=9.0)


def _titulo(texto: str) -> Linha:
    return replace(_linha(texto, fonte=SEM_SERIFA, tamanho=13.0), negrito=True)


def _negrito_pequeno(texto: str) -> Linha:
    return replace(_linha(texto, fonte=SEM_SERIFA, tamanho=9.0), negrito=True)


def _corpo(n: int = 12, marca: str = "do texto") -> list[Linha]:
    # Linhas longas: a letra do corpo é a que tem mais caracteres no livro.
    texto = "Linha {k} {marca} corrido do livro, longa o bastante para a letra dela ser a do corpo."
    return [_linha(texto.format(k=k, marca=marca)) for k in range(n)]


def _leitura(n: int) -> list[Linha]:
    """Uma leitura em três linhas, como no livro: autores, título e periódico com a citação."""
    return [
        _pequena(f"Fulano AB, Beltrano CD. Um estudo inventado número {n} sobre"),
        _pequena("o assunto do capítulo, com o título em duas linhas."),
        _pequena(f"Rev Sint. 2001;{n}:10-{n + 20}."),
    ]


def _numerada(n: int) -> Linha:
    return _pequena(f"{n}. Sicrano EF. Outro estudo inventado. Rev Sint. 1999;{n}:1-{n + 5}.")


TITULO_DA_LEITURA = _titulo("Leituras sugeridas")
TITULO_DA_LISTA = _titulo("Referências")
LEITURAS = [*_leitura(1), *_leitura(2)]
FRASE = _negrito_pequeno("As referências deste capítulo estão no site da editora.")
LISTA = [_numerada(n) for n in range(1, 13)]
PROVADA = [TITULO_DA_LISTA, *LISTA]


def _paginas(*paginas: list[Linha]) -> list[Pagina]:
    """As páginas, com as linhas de cima para baixo na ordem em que foram dadas."""
    return [
        Pagina(
            numero,
            tuple(replace(linha, topo=0.05 + PASSO * k) for k, linha in enumerate(linhas)),
        )
        for numero, linhas in enumerate(paginas, 1)
    ]


def _sairam(*paginas: list[Linha], motivo: str = MOTIVO_DA_LISTA_DE_LEITURA) -> list[str]:
    limpas = tirar_bibliografia(_paginas(*paginas))
    return [r.texto for r in limpas.remocoes if r.motivo == motivo]


def _textos(linhas: list[Linha]) -> list[str]:
    return [linha.texto for linha in linhas]


def test_lista_de_leitura_antes_da_bibliografia_sai_com_o_titulo_dela() -> None:
    pagina = [*_corpo(), TITULO_DA_LEITURA, *LEITURAS, *PROVADA]
    assert _sairam(pagina) == _textos([TITULO_DA_LEITURA, *LEITURAS])


def test_lista_de_leitura_fica_registrada_com_a_pagina_e_o_motivo_dela() -> None:
    limpas = tirar_bibliografia(_paginas(_corpo(), [TITULO_DA_LEITURA, *LEITURAS, *PROVADA]))
    assert [(r.pagina, r.motivo) for r in limpas.remocoes][:2] == [
        (2, MOTIVO_DA_LISTA_DE_LEITURA),
        (2, MOTIVO_DA_LISTA_DE_LEITURA),
    ]


def test_bibliografia_provada_continua_saindo_com_o_motivo_dela() -> None:
    pagina = [*_corpo(), TITULO_DA_LEITURA, *LEITURAS, *PROVADA]
    assert _sairam(pagina, motivo=MOTIVO_DA_BIBLIOGRAFIA_DO_PDF) == _textos(PROVADA)


def test_paginas_ficam_sem_a_lista_de_leitura_e_com_o_corpo() -> None:
    corpo = _corpo()
    limpas = tirar_bibliografia(_paginas([*corpo, TITULO_DA_LEITURA, *LEITURAS, *PROVADA]))
    assert [linha.texto for linha in limpas.paginas[0].linhas] == _textos(corpo)


def test_frase_depois_da_ultima_leitura_fica() -> None:
    # A frase da bibliografia online, em outra letra: a marca d'água do `limpar` a tira, e só
    # se ela continuar na maioria dos capítulos (ADR-0008).
    pagina = [*_corpo(), TITULO_DA_LEITURA, *LEITURAS, FRASE, *PROVADA]
    assert _sairam(pagina) == _textos([TITULO_DA_LEITURA, *LEITURAS])


def test_subtitulo_em_outra_letra_no_meio_da_lista_sai_com_ela() -> None:
    parte = _negrito_pequeno("Parte I")
    pagina = [*_corpo(), TITULO_DA_LEITURA, parte, *LEITURAS, FRASE, *PROVADA]
    assert _sairam(pagina) == _textos([TITULO_DA_LEITURA, parte, *LEITURAS])


def test_caixa_do_corpo_no_meio_da_lista_fica_e_as_duas_metades_saem() -> None:
    # A caixa de pontos-chave da coluna ao lado, que o PDF grava entre as metades da lista.
    caixa = _corpo(8, "da caixa")
    pagina = [*_corpo(), TITULO_DA_LEITURA, *_leitura(1), *caixa, *_leitura(2), *PROVADA]
    assert _sairam(pagina) == _textos([TITULO_DA_LEITURA, *LEITURAS])


def test_caixa_do_corpo_no_meio_da_lista_continua_na_pagina() -> None:
    caixa = _corpo(8, "da caixa")
    pagina = [*_corpo(), TITULO_DA_LEITURA, *_leitura(1), *caixa, *_leitura(2), *PROVADA]
    ficam = [linha.texto for linha in tirar_bibliografia(_paginas(pagina)).paginas[0].linhas]
    assert ficam[-8:] == _textos(caixa)


def test_lista_de_leitura_na_pagina_anterior_sai() -> None:
    assert _sairam([*_corpo(), TITULO_DA_LEITURA, *LEITURAS, FRASE], PROVADA) == _textos(
        [TITULO_DA_LEITURA, *LEITURAS]
    )


def test_prosa_entre_o_fim_da_lista_e_a_bibliografia_e_nada_sai() -> None:
    # A lista de leitura termina encostada na bibliografia. O bloco com citação sob um título de
    # seção, com a prosa da seção depois dele, não é lista de leitura (R2 da code-review).
    bloco = [_pequena("Trecho citado de Fulano AB. Rev Sint. 2001;3:10-20.")]
    pagina = [*_corpo(), _titulo("Histórico"), *bloco, *_corpo(6, "da seção"), *PROVADA]
    assert _sairam(pagina) == []


def test_lista_sem_titulo_nenhum_antes_fica() -> None:
    # Livro sem letra de título: a caminhada chega ao começo sem achar quem encabece a lista.
    # A prosa longa vem depois, para a letra do corpo ser a dela sem ficar no caminho.
    pagina = [*LEITURAS, *_corpo(), *LEITURAS, *PROVADA, *_corpo(60, "do fim")]
    assert _sairam(pagina) == []


def test_titulo_na_mesma_letra_logo_acima_do_titulo_da_lista_de_leitura_fica() -> None:
    # No PDF em colunas, o título de outra seção pode vir gravado logo antes do da lista: só a
    # linha que encabeça a lista sai (A1 da code-audit). O título em duas linhas sai pela metade.
    cima = _titulo("Agradecimentos")
    pagina = [*_corpo(), cima, TITULO_DA_LEITURA, *LEITURAS, *PROVADA]
    assert _sairam(pagina) == _textos([TITULO_DA_LEITURA, *LEITURAS])


def test_titulo_de_outra_letra_acima_do_titulo_da_lista_de_leitura_fica() -> None:
    outro = replace(_titulo("Conclusão"), fonte="Gotica")
    pagina = [*_corpo(), outro, TITULO_DA_LEITURA, *LEITURAS, *PROVADA]
    assert _sairam(pagina) == _textos([TITULO_DA_LEITURA, *LEITURAS])


def test_lista_sem_citacao_de_periodico_fica() -> None:
    sites = [_pequena(f"Associação inventada número {n}. Disponível no site dela.") for n in (1, 2)]
    assert _sairam([*_corpo(), TITULO_DA_LEITURA, *sites, *PROVADA]) == []


def test_nota_de_rodape_com_citacao_sem_titulo_antes_fica() -> None:
    # A nota na letra das referências, depois da prosa: não há título que a encabece.
    nota = [_pequena("*Adaptado de Fulano AB. Rev Sint. 2001;3:10-20, com permissão.")]
    assert _sairam([_titulo("A dor"), *_corpo(), *nota, *PROVADA]) == []


def test_titulo_que_encabeca_prosa_nao_leva_a_nota_do_fim() -> None:
    # O título da seção, a prosa dela e a nota com citação: a linha depois do título é do corpo.
    nota = [_pequena("*Adaptado de Fulano AB. Rev Sint. 2001;3:10-20, com permissão.")]
    pagina = [*_corpo(), _titulo("Conclusão"), *_corpo(5, "da conclusão"), *nota, *PROVADA]
    assert _sairam(pagina) == []


def test_mais_de_quarenta_linhas_do_corpo_no_meio_da_lista_e_nada_sai() -> None:
    # A caixa da coluna ao lado tem até 32 linhas; com mais de 40 é o texto do capítulo.
    pagina = [TITULO_DA_LEITURA, *_leitura(1), *_corpo(41), *_leitura(2), *PROVADA]
    assert _sairam(pagina) == []


def test_quarenta_linhas_do_corpo_no_meio_da_lista_e_ela_sai() -> None:
    pagina = [TITULO_DA_LEITURA, *_leitura(1), *_corpo(40), *_leitura(2), *PROVADA]
    assert _sairam(pagina) == _textos([TITULO_DA_LEITURA, *LEITURAS])


def test_quatro_linhas_seguidas_de_outra_letra_e_nada_sai() -> None:
    caixa = [_negrito_pequeno(f"Linha {n} de uma caixa em outra letra.") for n in range(4)]
    pagina = [*_corpo(), TITULO_DA_LEITURA, *LEITURAS, *caixa, *PROVADA]
    assert _sairam(pagina) == []


def test_linhas_do_corpo_nao_zeram_a_conta_das_linhas_de_outra_letra() -> None:
    # Duas linhas de outra letra, a caixa do corpo e mais duas: são quatro sem referência entre
    # elas, e nada sai.
    caixa = [_negrito_pequeno(f"Linha {n} de uma caixa em outra letra.") for n in range(4)]
    meio = [*caixa[:2], *_corpo(3, "da caixa"), *caixa[2:]]
    pagina = [*_corpo(), TITULO_DA_LEITURA, *_leitura(1), *meio, *_leitura(2), *PROVADA]
    assert _sairam(pagina) == []


def test_outra_secao_entre_a_lista_e_a_bibliografia_e_a_lista_fica() -> None:
    # A regra para no primeiro título: a lista de leitura que não é vizinha da bibliografia fica.
    agradecimento = [_titulo("Agradecimentos"), *_corpo(2, "do agradecimento")]
    pagina = [*_corpo(), TITULO_DA_LEITURA, *LEITURAS, *agradecimento, *PROVADA]
    assert _sairam(pagina) == []


def test_lista_de_leitura_longa_que_ja_saia_nao_sai_duas_vezes() -> None:
    # Com 10 citações ou mais a lista de leitura já é um trecho provado: a regra para nele.
    longa = [linha for n in range(1, 11) for linha in _leitura(n)]
    limpas = tirar_bibliografia(_paginas([*_corpo(60), TITULO_DA_LEITURA, *longa, *PROVADA]))
    assert [r.motivo for r in limpas.remocoes] == [MOTIVO_DA_BIBLIOGRAFIA_DO_PDF] * (
        1 + len(longa) + len(PROVADA)
    )


def test_metade_da_lista_entre_dois_trechos_provados_sai() -> None:
    # A lista de leitura longa, partida pela caixa do corpo: a primeira metade já é um trecho
    # provado, e a segunda fica entre ele e a bibliografia.
    longa = [linha for n in range(1, 11) for linha in _leitura(n)]
    resto = [*_leitura(11), *_leitura(12)]
    caixa = _corpo(8, "da caixa")
    pagina = [*_corpo(60), TITULO_DA_LEITURA, *longa, *caixa, *resto, FRASE, *PROVADA]
    assert _sairam(pagina) == _textos(resto)


def test_caixa_do_corpo_entre_dois_trechos_provados_fica() -> None:
    longa = [linha for n in range(1, 11) for linha in _leitura(n)]
    caixa = _corpo(8, "da caixa")
    pagina = [*_corpo(60), TITULO_DA_LEITURA, *longa, *caixa, *_leitura(11), *PROVADA]
    ficam = [linha.texto for linha in tirar_bibliografia(_paginas(pagina)).paginas[0].linhas]
    assert ficam[-8:] == _textos(caixa)


def test_linhas_sem_citacao_entre_dois_trechos_provados_ficam() -> None:
    longa = [linha for n in range(1, 11) for linha in _leitura(n)]
    sites = [_pequena(f"Associação inventada número {n}. Disponível no site dela.") for n in (1, 2)]
    pagina = [*_corpo(60), TITULO_DA_LEITURA, *longa, *_corpo(8, "da caixa"), *sites, *PROVADA]
    assert _sairam(pagina) == []


def test_frases_em_outra_letra_entre_dois_trechos_provados_ficam() -> None:
    # Só o que vai da primeira à última linha na letra das citações: as frases das pontas ficam.
    longa = [linha for n in range(1, 11) for linha in _leitura(n)]
    resto = _leitura(11)
    caixa = _corpo(8, "da caixa")
    pagina = [*_corpo(60), TITULO_DA_LEITURA, *longa, FRASE, *caixa, *resto, FRASE, *PROVADA]
    assert _sairam(pagina) == _textos(resto)


def test_titulo_em_letra_de_titulo_acima_do_subtitulo_da_bibliografia_sai_com_ela() -> None:
    # A lista numerada dividida em partes: o título dela fica acima do subtítulo da primeira.
    parte = _negrito_pequeno("Parte I")
    pagina = [*_corpo(), TITULO_DA_LISTA, parte, *LISTA]
    assert _sairam(pagina, motivo=MOTIVO_DA_BIBLIOGRAFIA_DO_PDF) == _textos(
        [TITULO_DA_LISTA, parte, *LISTA]
    )


def test_lista_de_leitura_antes_da_bibliografia_dividida_em_partes_sai() -> None:
    parte = _negrito_pequeno("Parte I")
    pagina = [*_corpo(), TITULO_DA_LEITURA, *LEITURAS, FRASE, TITULO_DA_LISTA, parte, *LISTA]
    assert _sairam(pagina) == _textos([TITULO_DA_LEITURA, *LEITURAS])


def test_titulo_de_outra_secao_acima_do_titulo_da_bibliografia_fica() -> None:
    # Dois títulos em letra de título, de letras diferentes: só o de baixo é o da lista.
    outro = replace(_titulo("Conflito de interesses"), fonte="Gotica")
    pagina = [*_corpo(), outro, TITULO_DA_LISTA, *LISTA]
    assert _sairam(pagina, motivo=MOTIVO_DA_BIBLIOGRAFIA_DO_PDF) == _textos(PROVADA)


def test_titulo_maior_da_mesma_familia_acima_do_titulo_grande_da_bibliografia_fica() -> None:
    # Os dois em letra de título: o de cima é o da seção anterior, que ficou sem texto na página.
    outro = replace(_titulo("Conflito de interesses"), tamanho=16.0)
    pagina = [*_corpo(), outro, TITULO_DA_LISTA, *LISTA]
    assert _sairam(pagina, motivo=MOTIVO_DA_BIBLIOGRAFIA_DO_PDF) == _textos(PROVADA)


def test_titulo_grande_de_outra_familia_acima_do_titulo_pequeno_da_bibliografia_fica() -> None:
    # O título do capítulo acima do título pequeno em negrito da lista (R1 da code-review): só o
    # título da mesma família do subtítulo é o da lista dividida em partes.
    capitulo = replace(_titulo("Capítulo 2: A dor"), fonte="Gotica")
    pequeno = _negrito_pequeno("Referências")
    pagina = [*_corpo(), capitulo, pequeno, *LISTA]
    assert _sairam(pagina, motivo=MOTIVO_DA_BIBLIOGRAFIA_DO_PDF) == _textos([pequeno, *LISTA])


def test_resumo_do_importar_pdf_conta_a_lista_de_leitura(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpo = [
        LinhaDeTeste(
            f"Linha {n} do texto corrido do livro, longa o bastante para ser o corpo.",
            72,
            740 - 14 * n,
            serifa=True,
        )
        for n in range(12)
    ]
    titulo = LinhaDeTeste("Leituras sugeridas", 72, 560, tamanho=14, negrito=True)
    leituras = [
        LinhaDeTeste(f"Fulano AB. Estudo {n}. Rev Sint. 2001;{n}:10-{n + 20}.", 72, 545 - 9 * n)
        for n in range(1, 4)
    ]
    leituras = [replace(linha, tamanho=7.5, serifa=True) for linha in leituras]
    lista = [
        LinhaDeTeste(
            f"{n}. Autor AB, et al: Rev Sint {n}:{100 + n}, 1999.",
            72,
            480 - 9 * n,
            tamanho=7.5,
            serifa=True,
        )
        for n in range(1, 11)
    ]
    referencias = LinhaDeTeste("Referências", 72, 495, tamanho=14, negrito=True)
    pdf = montar_pdf(tmp_path / "livro.pdf", [[*corpo, titulo, *leituras, referencias, *lista]])
    assert principal(["importar-pdf", str(pdf), "--epub", str(tmp_path / "livro.epub")]) == 0
    saida = capsys.readouterr().out
    assert (
        "11 linhas de bibliografia tiradas: letra menor que a do corpo, com citações de periódico."
        in saida
    )
    assert (
        "4 linhas de lista de leitura tiradas: logo antes das referências, na letra delas." in saida
    )
