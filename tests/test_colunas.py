# SPDX-License-Identifier: GPL-3.0-or-later
"""A ordem de leitura da página em colunas (ADR-0004, "Duas colunas").

As medidas imitam o Dalgalarrondo: corpo de 10 pt, coluna da esquerda de x = 66 a 247 e da
direita de 287 a 446, entrelinha de 0,017 da altura da página.
"""

from __future__ import annotations

from dataclasses import replace

from earbook.dominio.blocos import montar_blocos
from earbook.dominio.colunas import linhas_visuais
from earbook.dominio.pagina import Linha, Pagina

ENTRELINHA = 0.017
ESQUERDA = (66.0, 247.0)
DIREITA = (287.0, 446.0)


def _linha(texto: str, coluna: tuple[float, float], n: int, topo: float = 0.1) -> Linha:
    """A linha `n` da coluna, a contar de `topo`."""
    x, fim = coluna
    return Linha(texto, x=x, topo=topo + n * ENTRELINHA, tamanho=10.0, fim=fim)


def _coluna(coluna: tuple[float, float], *textos: str, topo: float = 0.1) -> list[Linha]:
    return [_linha(texto, coluna, n, topo) for n, texto in enumerate(textos)]


def _lidas(linhas: list[Linha]) -> list[str]:
    return [linha.texto for linha, _ in linhas_visuais(linhas, 10.0)]


def test_tabela_de_chave_e_valor_continua_lida_linha_a_linha() -> None:
    # Hard Parts p. 347: célula curta que começa em maiúscula não continua a de cima. Lida
    # coluna a coluna, a tabela perde o par: "Communication Consistency… Synchronous Atomic…".
    chaves = _coluna(ESQUERDA, "Communication", "Consistency", "Coordination", "Coupling")
    valores = _coluna(DIREITA, "Synchronous", "Atomic", "Orchestrated", "Very high")
    assert _lidas(chaves + valores) == [
        "Communication Synchronous",
        "Consistency Atomic",
        "Coordination Orchestrated",
        "Coupling Very high",
    ]


def test_coluna_estreita_e_celula_de_tabela_mesmo_em_minuscula() -> None:
    # Competente p. 379, a linha do tempo: o mês abreviado ("fev.", "mar.") começa em
    # minúscula e passaria por texto corrido. A coluna de data tem 17% da largura da faixa.
    datas = _coluna((58.0, 95.0), "jan. 2023", "fev. 2023", "mar. 2023", "abr. 2023")
    fatos = _coluna(
        (107.0, 280.0),
        "a empolgação com IA é",
        "inversamente proporcional",
        "ao conhecimento sobre",
        "inteligência artificial.",
    )
    assert _lidas(datas + fatos) == [
        "jan. 2023 a empolgação com IA é",
        "fev. 2023 inversamente proporcional",
        "mar. 2023 ao conhecimento sobre",
        "abr. 2023 inteligência artificial.",
    ]


def _texto_corrido(coluna: tuple[float, float], nome: str, topo: float = 0.1) -> list[Linha]:
    """Quatro linhas de texto corrido numa coluna, com o `nome` dela no texto."""
    textos = (f"{nome} começa aqui e", "segue na linha de baixo", "até o fim da", "coluna.")
    return _coluna(coluna, *textos, topo=topo)


def test_vao_grande_fecha_as_colunas_antes_do_que_vem_embaixo() -> None:
    # Dalgalarrondo p. 30: "Questões de revisão" fica à esquerda da calha, 5 entrelinhas abaixo
    # das colunas, e era lida no meio delas, antes da coluna da direita.
    colunas = _texto_corrido(ESQUERDA, "A esquerda") + _texto_corrido(DIREITA, "A direita")
    questoes = Linha("Questões de revisão", x=90, topo=0.25, tamanho=24, fim=190)
    item = Linha("• Defina psicopatologia.", x=90, topo=0.29, tamanho=9, fim=369)
    lidas = _lidas([*colunas, questoes, item])
    assert lidas[3:6] == ["coluna.", "A direita começa aqui e", "segue na linha de baixo"]
    assert lidas[-2:] == ["Questões de revisão", "• Defina psicopatologia."]


def test_paragrafo_que_vira_para_a_coluna_da_direita_segue_inteiro() -> None:
    # O `blocos` compara o recuo com a margem do parágrafo: contado da borda da página, o x
    # da coluna da direita (287) parecia recuo de 221 pt e partia o parágrafo no fim da frase.
    esquerda = [
        Linha("O parágrafo começa na coluna", x=88.7, topo=0.1, tamanho=10.0, fim=247.0),
        *_coluna(
            ESQUERDA,
            "da esquerda e continua pela",
            "linha de baixo até chegar ao",
            "fim dela, sem fechar a",
            topo=0.1 + ENTRELINHA,
        ),
    ]
    direita = _coluna(
        DIREITA,
        "frase, que acaba na coluna",
        "da direita com um ponto.",
        "Depois, a linha de baixo",
        "continua o mesmo parágrafo.",
    )
    livro = montar_blocos([Pagina(1, tuple(esquerda + direita))])
    paragrafo = " ".join(linha.texto for linha in esquerda + direita)
    assert [bloco.texto for bloco in livro.blocos] == [paragrafo]


def test_linha_que_atravessa_a_calha_fecha_as_colunas_de_cima() -> None:
    # Título de largura cheia no meio da página: as colunas de cima acabam antes dele.
    em_cima = _texto_corrido(ESQUERDA, "A de cima") + _texto_corrido(DIREITA, "A outra de cima")
    titulo = Linha("Um título de lado a lado", x=66, topo=0.18, tamanho=10.0, fim=446)
    embaixo = _texto_corrido(ESQUERDA, "A de baixo", topo=0.2) + _texto_corrido(
        DIREITA, "A outra de baixo", topo=0.2
    )
    lidas = _lidas([*em_cima, titulo, *embaixo])
    comecos = [texto for texto in lidas if texto.startswith(("A ", "Um "))]
    assert comecos == [
        "A de cima começa aqui e",
        "A outra de cima começa aqui e",
        "Um título de lado a lado",
        "A de baixo começa aqui e",
        "A outra de baixo começa aqui e",
    ]


def test_destaque_dentro_da_coluna_sai_do_texto_ao_lado_dele() -> None:
    # Dalgalarrondo p. 31: o destaque (x 46 a 123) ocupa o alto da coluna da esquerda, e o
    # texto o contorna (x 143 a 228) até voltar à largura cheia da coluna.
    destaque = _coluna(
        (46.0, 123.0), "O destaque repete", "uma frase do texto", "ao lado dele", "na margem."
    )
    contorno = _coluna(
        (143.0, 228.0),
        "O texto ao lado",
        "do destaque segue",
        "estreito e depois",
        "volta à largura",
    )
    cheia = _coluna(
        (46.0, 228.0),
        "cheia da coluna da",
        "esquerda, até o fim",
        "dela, e só então",
        "vai para a direita.",
        topo=0.1 + 4 * ENTRELINHA,
    )
    direita = _texto_corrido((245.0, 426.0), "A direita")
    lidas = _lidas([*destaque, *contorno, *cheia, *direita])
    assert lidas == [
        "O destaque repete", "uma frase do texto", "ao lado dele", "na margem.",
        "O texto ao lado", "do destaque segue", "estreito e depois", "volta à largura",
        "cheia da coluna da", "esquerda, até o fim", "dela, e só então", "vai para a direita.",
        "A direita começa aqui e", "segue na linha de baixo", "até o fim da", "coluna.",
    ]  # fmt: skip


def test_vao_de_linha_justificada_partida_nao_e_calha() -> None:
    # O pdfminer parte a linha justificada em pedaços a menos de 10 pt um do outro.
    comecos = _coluna((66.0, 150.0), "o começo da linha", "o começo da outra", "o começo da última")
    fins = _coluna((155.0, 247.0), "e o fim", "e o fim", "e o fim")
    assert _lidas(comecos + fins) == [
        "o começo da linha e o fim",
        "o começo da outra e o fim",
        "o começo da última e o fim",
    ]


def test_duas_linhas_de_cada_lado_nao_fazem_coluna() -> None:
    esquerda = _coluna(ESQUERDA, "duas linhas à", "esquerda da calha")
    direita = _coluna(DIREITA, "e duas linhas", "à direita dela")
    assert _lidas(esquerda + direita) == [
        "duas linhas à e duas linhas",
        "esquerda da calha à direita dela",
    ]


def test_linha_depois_de_hifen_continua_mesmo_sem_minuscula() -> None:
    # Bibliografia: "p. 115-" / "131, 1997." O algarismo depois do hífen continua a linha.
    esquerda = _texto_corrido(ESQUERDA, "A esquerda")
    direita = _coluna(
        DIREITA,
        "Revista, v. 7, p. 115-",
        "131, 1997. Outra, p. 20-",
        "34, 2001. Mais, p. 9-",
        "12, 2005.",
    )
    assert _lidas(esquerda + direita)[4:] == [
        "Revista, v. 7, p. 115-", "131, 1997. Outra, p. 20-", "34, 2001. Mais, p. 9-", "12, 2005.",
    ]  # fmt: skip


def test_vao_grande_fecha_o_que_vem_antes_das_colunas() -> None:
    # Dalgalarrondo p. 31: a epígrafe fica à direita da calha, 5 entrelinhas acima das colunas.
    # Sem o corte, ela entrava na coluna da direita e era lida depois da coluna da esquerda.
    epigrafe = _coluna(
        DIREITA,
        "Que é loucura: ser cavaleiro andante",
        "ou segui-lo como escudeiro?",
        "De nós dois, quem o louco verdadeiro?",
        topo=0.05,
    )
    colunas = _texto_corrido(ESQUERDA, "A esquerda", topo=0.18) + _texto_corrido(
        DIREITA, "A direita", topo=0.18
    )
    assert _lidas(epigrafe + colunas)[:4] == [
        "Que é loucura: ser cavaleiro andante",
        "ou segui-lo como escudeiro?",
        "De nós dois, quem o louco verdadeiro?",
        "A esquerda começa aqui e",
    ]


def test_vao_numa_coluna_so_nao_tira_dela_o_resto_do_texto() -> None:
    # A coluna da direita acaba cedo, e a da esquerda segue com um subtítulo 3 entrelinhas
    # abaixo (code-review): o vão é da coluna da esquerda, não da página. Cortado ali, o resto
    # da esquerda ia para depois da coluna da direita.
    antes = ("A esquerda começa aqui", "e segue na linha", "de baixo, desce", "mais e mais")
    depois = ("que segue na mesma", "coluna até o fim", "da página.")
    esquerda = [
        *_coluna(ESQUERDA, *antes, "até chegar ao fim", "do parágrafo."),
        _linha("Subtítulo da esquerda", (66.0, 200.0), 9),
        *_coluna(ESQUERDA, *depois, topo=0.1 + 10 * ENTRELINHA),
    ]
    direita = _coluna(DIREITA, "A direita começa", "aqui e acaba", "bem antes.")
    marcos = ("da página.", "A direita começa")
    assert [texto for texto in _lidas(esquerda + direita) if texto in marcos] == list(marcos)


def test_pedaco_na_altura_da_linha_que_atravessa_fica_com_ela() -> None:
    # O pdfminer partiu a linha de largura cheia em dois pedaços, a 5 pt um do outro
    # (code-review). O segundo fica à direita da calha, um pouco abaixo, e ia parar na coluna
    # da direita, lido depois da coluna da esquerda inteira.
    cheia = [
        Linha("A linha de largura cheia que passa da", x=66, topo=0.1, tamanho=10.0, fim=300),
        Linha("calha.", x=305, topo=0.1005, tamanho=10.0, fim=330),
    ]
    colunas = _texto_corrido(ESQUERDA, "A esquerda", topo=0.12) + _texto_corrido(
        DIREITA, "A direita", topo=0.12
    )
    assert _lidas(cheia + colunas)[:2] == [
        "A linha de largura cheia que passa da calha.",
        "A esquerda começa aqui e",
    ]


def test_item_de_lista_que_vira_de_coluna_segue_inteiro() -> None:
    # Dalgalarrondo p. 30: na coluna da direita, quase toda linha é continuação de item (x 301),
    # e a margem dela pela moda é o recuo do item; na da esquerda, é a margem do texto (66). O
    # item que vira de coluna se partia no ponto: a margem do parágrafo vinha da outra coluna.
    esquerda = [
        *_coluna(ESQUERDA, "Um parágrafo de texto", "corrido que ocupa a", "coluna e acaba aqui."),
        _linha("1. O item começa aqui e", (89.0, 247.0), 3),
        _linha("continua recuado até", (103.0, 247.0), 4),
        _linha("o fim da coluna sem", (103.0, 247.0), 5),
    ]
    direita = _coluna(
        (301.0, 446.0),
        "fechar a frase. Depois",
        "do ponto, o item segue.",
        "E continua mais um",
        "pouco no mesmo item.",
    )
    livro = montar_blocos([Pagina(1, tuple(esquerda + direita))])
    item = " ".join(linha.texto for linha in esquerda[3:] + direita)
    assert [bloco.texto for bloco in livro.blocos][1:] == [item]


def test_paragrafo_que_vira_a_pagina_de_margem_diferente_segue_inteiro() -> None:
    # Dalgalarrondo: a página par tem a coluna da esquerda em x 66 e a da direita em 301; a
    # ímpar, em 46 e 245. O parágrafo que vira da coluna da direita da página par para a da
    # esquerda da ímpar se partia em cada fim de frase: o x 46 parecia recuo diante de 301.
    par = _texto_corrido(ESQUERDA, "A par") + _coluna(
        (301.0, 446.0), "O parágrafo começa na", "coluna da direita e vira", "a página sem fechar a"
    )
    impar = _coluna(
        (46.0, 228.0),
        "frase, que acaba aqui.",
        "Depois, a linha de baixo",
        "segue o mesmo parágrafo.",
    ) + _texto_corrido((245.0, 426.0), "A ímpar")
    livro = montar_blocos([Pagina(1, tuple(par)), Pagina(2, tuple(impar))])
    paragrafo = " ".join(linha.texto for linha in par[4:] + impar[:3])
    assert paragrafo in [bloco.texto for bloco in livro.blocos]


def test_pagina_com_mais_de_duzentos_comecos_de_linha_nao_procura_calha() -> None:
    # A busca da calha custa o quadrado das linhas: 1.600 linhas em x distintos levavam 2,4 s,
    # e o PDF é entrada não confiável (code-review). A página real com mais começos de linha
    # diferentes tem 97 (Dalgalarrondo p. 302). Com mais de 200, a página vai como antes.
    colunas = _texto_corrido(ESQUERDA, "A esquerda") + _texto_corrido(DIREITA, "A direita")
    rotulos = [
        Linha(
            f"r{n}", x=50.0 + 3 * n, topo=0.2 + ENTRELINHA * (n // 5), tamanho=8.0, fim=52.0 + 3 * n
        )
        for n in range(201)
    ]
    assert _lidas(colunas + rotulos)[0] == "A esquerda começa aqui e A direita começa aqui e"


def test_linha_da_outra_coluna_na_altura_de_um_titulo_fica_na_coluna_dela() -> None:
    # Dalgalarrondo p. 308: o título da coluna da direita começa na margem dela (x 264), à
    # esquerda dos itens (x 287), e cobre a calha que os itens marcam. A linha da coluna da
    # esquerda, 0,0035 abaixo dele e a 17 pt, ia junto com o título: "mais nada.”) ALTERAÇÕES
    # DA VOLIÇÃO". Só o pedaço colado (vão menor que a calha) é a mesma linha.
    itens = (287.0, 446.0)
    comeco = _coluna(ESQUERDA, "a esquerda começa aqui", "e segue na linha", "de baixo, até")
    fim_da_esquerda = ("que continua e", "desce até o", "fim da coluna.")
    esquerda = [
        comeco[0],
        replace(comeco[1], fim=270.0),  # invade a calha da margem (264)
        comeco[2],
        _linha("a segunda parte da coluna", ESQUERDA, 3),
        *_coluna(ESQUERDA, *fim_da_esquerda, topo=0.1 + 4 * ENTRELINHA),
    ]
    titulo = Linha(
        "ALTERAÇÕES DA VOLIÇÃO", x=264, topo=0.1 + 3 * ENTRELINHA - 0.0035, tamanho=11.0, fim=392
    )
    direita = [
        *_coluna(itens, "\u2013 o item que segue", "na linha de baixo", "e acaba aqui."),
        *_coluna(
            itens, "\u2013 o outro item", "que segue", "até o fim.", topo=0.1 + 4 * ENTRELINHA
        ),
    ]
    lidas = _lidas([*esquerda, titulo, *direita])
    assert "a segunda parte da coluna" in lidas


def test_titulo_do_quadro_depois_de_colunas_desiguais_vem_depois_das_duas() -> None:
    # Dalgalarrondo p. 343: o destaque alonga a coluna da direita, que acaba abaixo da da
    # esquerda. "Questões de revisão", à esquerda da calha e seguido pelo quadro de largura
    # cheia, entrava na coluna da esquerda, antes da coluna da direita.
    esquerda = _texto_corrido(ESQUERDA, "A esquerda")
    direita = _coluna(DIREITA, *(f"a direita {n} continua" for n in range(7)))
    questoes = Linha("Questões de revisão", x=90, topo=0.1 + 10 * ENTRELINHA, tamanho=12.0, fim=190)
    item = Linha(
        "• Cite as três dimensões.", x=90, topo=0.1 + 12 * ENTRELINHA, tamanho=9.0, fim=369
    )
    lidas = _lidas([*esquerda, *direita, questoes, item])
    assert lidas[-2:] == ["Questões de revisão", "• Cite as três dimensões."]
