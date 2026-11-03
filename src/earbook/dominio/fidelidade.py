# SPDX-License-Identifier: GPL-3.0-or-later
"""A fidelidade de um grupo adaptado às fontes dele (ADR-0009).

Num livro de psiquiatria, perder ou inventar um critério, um número ou uma dose é o risco
maior. Sem LLM (ADR-0001), o Python cobra o que dá para medir: todo número das fontes está no
texto, nenhum número novo aparece, e todo termo raro das fontes continua lá ou foi declarado
como omitido. O que só funciona no papel ("\u2022", "Quadro 27.1", "(Autor, ano)") não pode sobrar.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence

from earbook.dominio.segmento import Segmento

# O termo raro: 8 letras ou mais, em até 20 segmentos do livro. No Dalgalarrondo, 6,7 por
# parágrafo ("anedonia", "catatônicas", "distímico"). Régua de partida, que o trecho de teste
# calibra (ADR-0009, Governança).
LETRAS_DO_TERMO = 8
SEGMENTOS_DO_TERMO_RARO = 20
_TERMINACOES = ("as", "os", "es", "a", "o", "s")
_RADICAL_MINIMO = 5
_PALAVRA_COM_HIFEN = re.compile(r"[^\W\d_]+(?:-[^\W\d_]+)*")
_NUMERO = re.compile(r"\d+(?:[.,]\d+)*")
_ANO = r"\b(?:1[5-9]\d\d|20[0-2]\d)[a-z]?\b"
_PARENTESE = re.compile(r"\(([^()]*)\)")
# Antes do parêntese de data: o nome ("Sullivan (1983)"), o "et al." ou o ano entre colchetes
# ("Freud [1911] (1976)").
_DEPOIS_DE_NOME = re.compile(r"(?:[A-ZÀ-Ý][\w'\u2019-]*|al\.|\])\s*$")
_SO_DATA = re.compile(r"[\d\s,;:.\u2013-]*(?:p\.\s*[\d\s\u2013-]+)?(?:[ad]\.C\.)?\s*")
_INTERVALO = r"\d{3,4}\s*[\u2013-]\s*\d{2,4}"
_PAGINA = r"\bp\.\s*\d+(?:\s*[\u2013-]\s*\d+)?"
_SO_ANO_E_PAGINA = re.compile(rf"{_ANO}|{_INTERVALO}|{_PAGINA}")
_ROTULO = re.compile(
    r"\b(?:Quadros?|Tabelas?|Figuras?)\s+\d+(?:\.\d+)?(?:\s*(?:,|e|a)\s*\d+(?:\.\d+)?)*"
)
_ORDINAL_NO_COMECO = re.compile(r"^\s*\d+\.\s")
# A chamada de nota colada à palavra da tabela ("EUA1", "Brasil3"): um algarismo só, depois de
# 3 letras. "B12", "B1", "F40" e "T4" são dados e contam (A3 da auditoria).
_CHAMADA_COLADA = re.compile(r"(?<=[^\W\d_]{3})\d(?!\d)")
_SO_ROTULO = re.compile(r"(?:(?:Quadro|Tabela|Figura)\s+\d+(?:\.\d+)*|\d+)")
_PAPEL: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile("\u2022"), "marcador de lista '•'"),
    (re.compile(r"^\s*[\u2013-]\s"), "item de lista com travessão"),
    (_ORDINAL_NO_COMECO, "item de lista numerado"),
    (re.compile(r"\bet al\."), "'et al.'"),
    (re.compile(r"\bp\.\s?ex\."), "'p. ex.'"),
    (re.compile(r"\.{5,}|\u2026{2,}"), "pontilhado de sumário"),
    (re.compile(r"[\u2013_]{3,}"), "linha de formulário"),
    (re.compile(r"\[(?:\.\.\.|\u2026)\]"), "'[...]'"),
)


class Raridade:
    """Em quantos segmentos do livro aparece cada radical: o raro é o termo técnico."""

    def __init__(self, segmentos_por_radical: Counter[str]) -> None:
        self._vezes: Counter[str] = segmentos_por_radical

    @classmethod
    def do_livro(cls, segmentos: Iterable[Segmento]) -> Raridade:
        vezes: Counter[str] = Counter()
        for segmento in segmentos:
            vezes.update({radical(p) for p in _palavras(segmento.texto)})
        return cls(vezes)

    def termos(self, texto: str) -> dict[str, str]:
        """Os termos raros fora de citação, por radical, com a primeira forma do texto."""
        termos: dict[str, str] = {}
        for palavra in _palavras(_sem_os_isentos(texto, numeros=False)):
            chave = radical(palavra)
            raro = self._vezes[chave] <= SEGMENTOS_DO_TERMO_RARO
            if raro and len(palavra.replace("-", "")) >= LETRAS_DO_TERMO:
                _ = termos.setdefault(chave, palavra)
        return termos


def _palavras(texto: str) -> list[str]:
    return [achado.group() for achado in _PALAVRA_COM_HIFEN.finditer(texto)]


def _numeros(texto: str) -> list[str]:
    return [achado.group() for achado in _NUMERO.finditer(texto)]


def radical(palavra: str) -> str:
    """Sem caixa, acento, hífen e terminação de gênero e número: "freqüente" é "frequente",
    "auto-estima" é "autoestima", e "deprimido" é "deprimida"."""
    sem_acento = unicodedata.normalize("NFD", palavra.casefold().replace("-", ""))
    base = "".join(letra for letra in sem_acento if unicodedata.category(letra) != "Mn")
    for terminacao in _TERMINACOES:
        if base.endswith(terminacao) and len(base) - len(terminacao) >= _RADICAL_MINIMO:
            return base[: -len(terminacao)]
    return base


def faltas_de_fidelidade(
    fontes: Sequence[str], texto: Sequence[str], omitidos: Iterable[str], raridade: Raridade
) -> list[str]:
    """O que o texto adaptado perdeu ou inventou em relação às fontes do grupo."""
    corrido = " ".join(texto)
    motivos = [
        f"o número {n} das fontes não está no texto" for n in numeros_que_faltam(fontes, corrido)
    ]
    motivos += [f"o número {n} não está nas fontes" for n in _numeros_inventados(fontes, corrido)]
    return motivos + [
        f"o termo '{forma}' das fontes não está no texto nem em omitidos"
        for forma in termos_que_faltam(fontes, corrido, omitidos, raridade)
    ]


def numeros_que_faltam(fontes: Sequence[str], corrido: str) -> list[str]:
    """Cada número das fontes, fora o ano de citação e o rótulo, tantas vezes quantas aparece."""
    exigidos: Counter[str] = Counter()
    for fonte in fontes:
        exigidos.update(_numeros(_sem_os_isentos(fonte, numeros=True)))
    no_texto = _numeros_do_texto(corrido)
    return [numero for numero in exigidos if no_texto[numero] < exigidos[numero]]


def _numeros_inventados(fontes: Sequence[str], corrido: str) -> list[str]:
    """O ano de citação pode ficar como data do fato ("em 1949"); o número novo, nunca."""
    todos = {numero for fonte in fontes for numero in _numeros(fonte)}
    return [numero for numero in _numeros_do_texto(corrido) if numero not in todos]


def _numeros_do_texto(corrido: str) -> Counter[str]:
    return Counter(_numeros(_CHAMADA_COLADA.sub(" ", corrido)))


def termos_que_faltam(
    fontes: Sequence[str], corrido: str, omitidos: Iterable[str], raridade: Raridade
) -> list[str]:
    """Os termos raros das fontes, na forma da primeira vez, que o texto não tem."""
    no_texto = {radical(p) for p in _palavras(corrido)}
    no_texto |= {radical(p) for omitido in omitidos for p in _palavras(omitido)}
    das_fontes: dict[str, str] = {}
    for fonte in fontes:
        for chave, forma in raridade.termos(fonte).items():
            _ = das_fontes.setdefault(chave, forma)
    return [forma for chave, forma in das_fontes.items() if chave not in no_texto]


def so_funciona_no_papel(paragrafo: str) -> list[str]:
    """O que sobrou da página no texto adaptado: marcador, rótulo, citação, pontilhado."""
    motivos = [motivo for padrao, motivo in _PAPEL if padrao.search(paragrafo)]
    motivos += [f"rótulo ou remissão '{a.group()}'" for a in _ROTULO.finditer(paragrafo)]
    return motivos + [f"citação '{citacao}'" for citacao in _citacoes(paragrafo)]


def eh_rotulo(texto: str) -> bool:
    """O texto do descarte `rotulo`: só "Quadro 27.1", "Tabela 19.1" ou o número do capítulo."""
    return _SO_ROTULO.fullmatch(texto.strip()) is not None


def _citacoes(texto: str) -> Iterator[str]:
    for achado in _PARENTESE.finditer(texto):
        if _eh_citacao(texto, achado):
            yield achado.group()


def _eh_citacao(texto: str, achado: re.Match[str]) -> bool:
    """ "(Del Pino, 2003)": só ano e página, com autor; "Sullivan (1983)", "Kraepelin
    (1856-1926)", "Aristóteles (348-322 a.C.)": só data, logo depois do nome."""
    conteudo = achado.group(1)
    if _DEPOIS_DE_NOME.search(texto[: achado.start()]) and _SO_DATA.fullmatch(conteudo):
        return any(letra.isdigit() for letra in conteudo)
    sem_datas = _SO_ANO_E_PAGINA.sub(" ", conteudo)
    # Só o ano de verdade faz a citação; o intervalo e a página, sozinhos, não (A4 da auditoria).
    tem_ano = re.search(_ANO, conteudo) is not None
    return (
        tem_ano
        and not any(letra.isdigit() for letra in sem_datas)
        and any(letra.isupper() for letra in conteudo)
    )


def _sem_os_isentos(texto: str, *, numeros: bool) -> str:
    """O texto sem a citação, que a política tira inteira (ADR-0009). Para os números, sem
    também o rótulo, a remissão, o ordinal do item e a chamada de nota colada ("EUA1")."""
    partes: list[str] = []
    inicio = 0
    for achado in _PARENTESE.finditer(texto):
        if _eh_citacao(texto, achado):
            partes.append(texto[inicio : achado.start()])
            inicio = achado.end()
    sem_citacao = "".join([*partes, texto[inicio:]])
    if not numeros:
        return sem_citacao
    sem_rotulo = _ROTULO.sub(" ", _ORDINAL_NO_COMECO.sub(" ", sem_citacao))
    return _CHAMADA_COLADA.sub(" ", sem_rotulo)
