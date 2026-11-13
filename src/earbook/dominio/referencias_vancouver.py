# SPDX-License-Identifier: GPL-3.0-or-later
"""As referências no estilo Vancouver, das obras médicas (ADR-0008, "Referências no estilo
Vancouver"): a região de pedaços de referência com 10 citações de periódico ou mais. Nunca pelo
título ("References"), que o ADR-0008 proíbe como critério.

Medido no Practical Management of Pain (um parágrafo por referência, partido na quebra de página)
e no Bonica (até 30 referências coladas numa nota, que pode abrir no meio de uma).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from enum import Enum, auto

from earbook.dominio.segmento import Papel, Segmento

# A citação de periódico: ano, ponto e vírgula, volume, dois-pontos e página ("1980;62:358",
# "2011;36:E629", "2018;9(1):2957", "2006;25Suppl (1):S16"). A prosa dos dois livros cita por
# número sobrescrito ("Fanuele et al.7"), nunca assim; "2011;36" sem a página não conta.
_PARENTESE = r"(?:\s?\([^)]{1,20}\))?"
_ANO = rf"\b\d{{4}}[a-z]?{_PARENTESE}"
_VOLUME = rf"\d+[A-Za-z]?{_PARENTESE}(?:\s?[Ss]uppl\s?\d*)?"
_ANO_PONTO_E_VIRGULA = rf"{_ANO};\s*{_VOLUME}:\s*[A-Za-z]{{0,2}}\d+"
# A citação do Miller, com o ano no fim: volume, dois-pontos, página, vírgula e ano ("269:259,
# 1955", "27(8):673, 2010", "62:4-11, 2007", "121:e4, 2008"; ADR-0008, "Tratado em português e em
# espanhol"). A proporção e a hora da prosa não têm o ano depois da vírgula ("1:2 en 2010").
_PAGINA = r"[A-Za-z]?\d+"
_VOLUME_PAGINA_ANO = (
    rf"\b\d{{1,4}}{_PARENTESE}:\s?{_PAGINA}(?:[-\u2013]{_PAGINA})?,\s?(?:19|20)\d\d\b"
)
CITACAO_DE_PERIODICO = re.compile(rf"{_ANO_PONTO_E_VIRGULA}|{_VOLUME_PAGINA_ANO}")
"""A citação de periódico, nas duas formas. A bibliografia do PDF, que sai pela letra, conta a
mesma (ADR-0004, "Bibliografia pela letra")."""
# O sobrenome com minúscula e as iniciais: "Adams MA", "Kirkaldy-Willis WH", "van Tulder MW". O
# crédito do capítulo em maiúsculas ("JIMMY CHEN YANG, ATHAR N. MALIK", Bonica) não é autor, e o
# romano não é inicial ("Stage IV,", "Type II,").
_SOBRENOME = r"[A-Z][a-z'\u2019][\w'\u2019-]*"
_INICIAIS = r"(?![IVX]+\b)[A-Z]{1,4}"
_AUTOR = rf"(?:[a-z]{{1,3}}\s)?{_SOBRENOME}(?:[\s-]{_SOBRENOME})?\s{_INICIAIS}"
# "86. Adams MA," no começo ou no meio do segmento (o Bonica cola as referências).
_INICIO_NUMERADO = re.compile(rf"(?:^|(?<=[.\s]))\d{{1,4}}\.\s+{_AUTOR}[,.]")
# A lista de autores sem número, das "Suggested Readings": "Bartley EJ, Fillingim RB,".
_AUTORES = re.compile(rf"^{_AUTOR}(?:\s(?:Jr|Sr|II|III|IV))?,\s")
_NUMERADO = re.compile(r"^\d{1,4}\.\s")
# O pedaço sem autor nem citação: o site, o DOI e a editora com o ano ("Philadelphia: Saunders;
# 1996").
_PEDACO_FRACO = re.compile(
    r"Available at|Accessed|https?://|\bdoi:|www\.|:\s[^;:.]{2,60};\s?(?:19|20)\d\d\b"
)
# Medido: com 5, saem duas tabelas do Bonica (c005-s5706, definições numeradas com a fonte;
# c006-s0365, farmacocinética). Com 10, só as listas de referências.
CITACOES_MINIMAS = 10
# Os segmentos sem sinal entre dois pedaços: o fim de um título partido, "Section II", "1913.".
# Com 3, a caixa "Key Points" do Practical, que cai no meio da lista, sairia.
LACUNA = 2
# Os títulos entre as leituras e a lista: "Suggested Readings" fica antes da corrida curta, e
# "References", entre ela e a região. Mais que 2 é outra seção do livro.
TITULOS_ENTRE = 2


class _Sinal(Enum):
    TITULO = auto()
    FORTE = auto()  # começa a região: citação de periódico, início numerado ou autores
    FRACO = auto()  # só a estende: o número no começo, o site, a editora
    NENHUM = auto()


def regioes_de_referencias(segmentos: Sequence[Segmento]) -> list[tuple[int, int]]:
    """(início, fim) de cada região de referências Vancouver do capítulo, com o título antes.

    A corrida de pedaços não atravessa título. A corrida curta com citação ("Suggested
    Readings") se junta à região logo depois do título seguinte ("References"); o título do
    próximo capítulo não se atravessa, porque a prosa dele nunca soma 10 citações.
    """
    citacoes = [len(CITACAO_DE_PERIODICO.findall(s.texto)) for s in segmentos]
    sinais = [_sinal(s, n) for s, n in zip(segmentos, citacoes, strict=True)]
    regioes: list[tuple[int, int]] = []
    for inicio, fim in reversed(_corridas(sinais)):
        comeco = _inicio_da_regiao(segmentos, sinais, inicio)
        soma = sum(citacoes[inicio:fim])
        if regioes and soma > 0 and _logo_antes(sinais, fim, regioes[-1][0]):
            regioes[-1] = (comeco, regioes[-1][1])
        elif soma >= CITACOES_MINIMAS:
            regioes.append((comeco, fim))
    return regioes[::-1]


def _corridas(sinais: Sequence[_Sinal]) -> list[tuple[int, int]]:
    """(início, fim) de cada corrida de pedaços, do pedaço forte ao último pedaço."""
    corridas: list[tuple[int, int]] = []
    posicao = 0
    while posicao < len(sinais):
        if sinais[posicao] is not _Sinal.FORTE:
            posicao += 1
            continue
        fim = _fim_da_corrida(sinais, posicao)
        corridas.append((posicao, fim))
        posicao = fim
    return corridas


def _fim_da_corrida(sinais: Sequence[_Sinal], inicio: int) -> int:
    """Depois do último pedaço. A lacuna de até `LACUNA` segmentos sem sinal não a fecha."""
    fim, lacuna = inicio + 1, 0
    for posicao in range(inicio + 1, len(sinais)):
        if sinais[posicao] is _Sinal.TITULO:
            break
        if sinais[posicao] is _Sinal.NENHUM:
            lacuna += 1
            if lacuna > LACUNA:
                break
        else:
            fim, lacuna = posicao + 1, 0
    return fim


def _logo_antes(sinais: Sequence[_Sinal], fim: int, proxima: int) -> bool:
    """Entre a corrida e a próxima região, de 1 a `TITULOS_ENTRE` títulos e até `LACUNA` outros."""
    entre = sinais[fim:proxima]
    titulos = sum(1 for sinal in entre if sinal is _Sinal.TITULO)
    # A região já leva o título logo antes dela ("References"): ele conta como o do meio.
    titulo_da_regiao = sinais[proxima] is _Sinal.TITULO
    return 0 < titulos + titulo_da_regiao <= TITULOS_ENTRE and len(entre) - titulos <= LACUNA


def _inicio_da_regiao(
    segmentos: Sequence[Segmento], sinais: Sequence[_Sinal], primeiro_forte: int
) -> int:
    """Até `LACUNA` referências numeradas sem citação antes do primeiro pedaço forte ("1. American
    Hospital Association."), e o título logo antes. A prosa com URL, que é pedaço fraco, fica."""
    inicio = primeiro_forte
    while (
        inicio > 0
        and primeiro_forte - inicio < LACUNA
        and sinais[inicio - 1] is _Sinal.FRACO
        and _NUMERADO.match(segmentos[inicio - 1].texto)
    ):
        inicio -= 1
    titulo_antes = inicio > 0 and sinais[inicio - 1] is _Sinal.TITULO
    return inicio - 1 if titulo_antes else inicio


def _sinal(segmento: Segmento, citacoes: int) -> _Sinal:
    """O que o segmento é para a região. A referência vem como parágrafo (Practical) ou como nota
    (Bonica); o resto (item, célula, citação) nunca é pedaço."""
    texto = segmento.texto
    if segmento.papel is Papel.TITULO:
        return _Sinal.TITULO
    if segmento.papel not in (Papel.PARAGRAFO, Papel.NOTA):
        return _Sinal.NENHUM
    if citacoes or _INICIO_NUMERADO.search(texto) or _AUTORES.match(texto):
        return _Sinal.FORTE
    if _NUMERADO.match(texto) or _PEDACO_FRACO.search(texto):
        return _Sinal.FRACO
    return _Sinal.NENHUM
