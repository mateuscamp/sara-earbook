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
from collections.abc import Collection, Iterable, Iterator, Sequence

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
# Antes do parêntese de data: o nome ("Sullivan (1983)"), o "et al.", o "e colaboradores" ou o
# ano entre colchetes ("Freud [1911] (1976)").
_DEPOIS_DE_NOME = re.compile(r"(?:[A-ZÀ-Ý][\w'\u2019-]*|al\.|colaboradores|\])\s*$")
_SO_DATA = re.compile(
    r"(?:cerca de\s+)?[\d\s,;:.\u2013-]*(?:p\.\s*[\d\s\u2013-]+)?(?:[ad]\.C\.)?\s*"
)
_INTERVALO = r"\d{3,4}\s*[\u2013-]\s*\d{2,4}"
_PAGINA = r"\bp\.\s*\d+(?:\s*[\u2013-]\s*\d+)?"
_SO_ANO_E_PAGINA = re.compile(rf"{_ANO}|{_INTERVALO}|{_PAGINA}")
# Depois do nome, só a forma de data é citação: "(15)" é dado, e o número é cobrado.
_FORMA_DE_DATA = re.compile(rf"{_ANO}|{_INTERVALO}|[ad]\.C\.")
_ROTULO = re.compile(
    r"\b(?:Quadros?|Tabelas?|Figuras?)\s+\d+(?:\.\d+)?(?:\s*(?:,|e|a)\s*\d+(?:\.\d+)?)*"
)
_ORDINAL_NO_COMECO = re.compile(r"^\s*\d+\.\s")
# A chamada de nota colada à palavra, depois de 3 letras: um algarismo só ("EUA1", "Brasil3") ou
# a lista com vírgula ("PCDT6,178", "altos16,17", do PCDT da Dor Crônica), que é citação. "B12",
# "B1", "F40", "T4" e "COVID19" são dados e contam (A3 da auditoria); "0,6" depois de espaço é
# decimal.
_CHAMADA_COLADA = re.compile(r"(?<=[^\W\d_]{3})(?:\d+(?:,\d+)+|\d(?!\d))")
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


# Medido no livro: 138 porcentagens, 34 faixas e nenhuma dose com unidade; "por cento" só com o
# número por extenso, 9 vezes (ADR-0009, "O número omitido"). A faixa conta pelo número que a abre.
_FIM_DA_FAIXA = r"(?:\s*(?:a|e|ou|[\u2013-])\s*\d+(?:[.,]\d+)*)?"
_MEDIDA = rf"{_FIM_DA_FAIXA}\s*(?:%|por cento|(?:mg|ml|mcg|\u00b5g|\u03bcg|UI|g)(?![^\W\d_]))"
MOTIVOS_DO_NUMERO = frozenset({"citação", "data", "ordinal", "página", "potência", "unidade"})


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
    # O PDF pode trazer o acento separado da letra (NFD, "reumatolo\u0301gicas" no PCDT), e o
    # acento solto parte a palavra. O `conferir` compara em NFC; `limpos/` fica como veio
    # (ADR-0009, "O PCDT da Dor Crônica"). A raridade do livro também passa por aqui.
    composto = unicodedata.normalize("NFC", texto)
    return [achado.group() for achado in _PALAVRA_COM_HIFEN.finditer(composto)]


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
    fontes: Sequence[str],
    texto: Sequence[str],
    omitidos: Collection[str],
    raridade: Raridade,
    corrigidos: Sequence[tuple[str, str]] = (),
) -> list[str]:
    """O que o texto adaptado perdeu ou inventou em relação às fontes do grupo."""
    corrido = " ".join(texto)
    declarados = set(omitidos)
    faltam, inventados = _numeros_em_falta_e_novos(fontes, corrido, corrigidos)
    motivos = [f"o número {n} das fontes não está no texto" for n in faltam if n not in declarados]
    motivos += [f"o número {n} não está nas fontes" for n in inventados]
    return motivos + [
        f"o termo '{forma}' das fontes não está no texto nem em omitidos"
        for forma in termos_que_faltam(fontes, corrido, omitidos, raridade)
    ]


def eh_numero(termo: str) -> bool:
    return _NUMERO.fullmatch(termo) is not None


def problemas_do_numero_omitido(
    numero: str, motivo: str, fontes: Sequence[str], corrido: str
) -> list[str]:
    """A guarda do número omitido (ADR-0009): só com motivo da lista, nunca porcentagem nem
    dose, e só o que as fontes têm e o texto de fato deixou de dizer."""
    if motivo.partition(":")[0].strip() not in MOTIVOS_DO_NUMERO:
        return [f"o número {numero} foi omitido com motivo fora da lista: {motivo!r}"]
    vezes = sum(_declaraveis(fonte).count(numero) for fonte in fontes)
    if not vezes:
        return [f"o número {numero} foi omitido, mas as fontes não o têm"]
    if any(re.search(rf"(?<![\d.,]){re.escape(numero)}{_MEDIDA}", fonte) for fonte in fontes):
        return [f"o número {numero} é porcentagem ou dose e não se omite"]
    if _numeros_do_texto(corrido)[numero] >= vezes:
        return [f"o número {numero} foi declarado omitido, mas continua no texto"]
    return []


def numeros_que_faltam(fontes: Sequence[str], corrido: str) -> list[str]:
    """Cada número das fontes, fora o ano de citação e o rótulo, tantas vezes quantas aparece."""
    return list(_deficit(fontes, corrido))


def _deficit(fontes: Sequence[str], corrido: str) -> Counter[str]:
    exigidos: Counter[str] = Counter()
    for fonte in fontes:
        exigidos.update(_numeros(_sem_os_isentos(fonte, numeros=True)))
    return exigidos - _numeros_do_texto(corrido)


def _numeros_em_falta_e_novos(
    fontes: Sequence[str], corrido: str, corrigidos: Sequence[tuple[str, str]]
) -> tuple[list[str], list[str]]:
    """Os números das fontes que o texto não diz e os do texto que as fontes não têm, fora a
    correção declarada do original (de, para) e o denominador partido pela linha da tabela."""
    velhos = Counter(numero for de, _ in corrigidos for numero in _numeros(de))
    novos = {numero for _, para in corrigidos for numero in _numeros(para)}
    inventados = [n for n in _numeros_inventados(fontes, corrido) if n not in novos]
    return _sem_os_partidos(fontes, _deficit(fontes, corrido) - velhos, inventados)


def _numeros_inventados(fontes: Sequence[str], corrido: str) -> list[str]:
    """O ano de citação pode ficar como data do fato ("em 1949"); o número novo, nunca."""
    todos = {numero for fonte in fontes for numero in _declaraveis(fonte)}
    return [numero for numero in _numeros_do_texto(corrido) if numero not in todos]


def _declaraveis(fonte: str) -> list[str]:
    """Os números da fonte que o grupo pode dizer ou declarar omitidos: a chamada colada com
    vírgula conta inteira ("6,178") e por número ("6", "178"), a mesma leitura que a isenta."""
    numeros = _numeros(_CHAMADA_COLADA.sub(" ", fonte))
    for chamada in _CHAMADA_COLADA.finditer(fonte):
        partes = chamada.group().split(",")
        numeros += [chamada.group(), *partes] if len(partes) > 1 else partes
    return numeros


def _sem_os_partidos(
    fontes: Sequence[str], faltam: Counter[str], inventados: Sequence[str]
) -> tuple[list[str], list[str]]:
    """A coluna da tabela partida no PDF: "920/197" e, adiante, "0" são o "920/1970" que o texto
    diz (PCDT, c090-s1407). O número novo se aceita só como cabeça logo depois da barra da
    fração e cauda depois dela nas fontes, as duas ausentes do texto; o resto segue acusado."""
    corrido = " ".join(_sem_os_isentos(fonte, numeros=True) for fonte in fontes)
    achados = list(_NUMERO.finditer(corrido))
    restam = Counter(faltam)
    novos: list[str] = []
    for numero in inventados:
        if (par := _cabeca_e_cauda(numero, corrido, achados, restam)) is None:
            novos.append(numero)
        else:
            restam -= Counter(par)
    return list(restam), novos


def _cabeca_e_cauda(
    numero: str, corrido: str, achados: Sequence[re.Match[str]], restam: Counter[str]
) -> tuple[str, str] | None:
    for n, achado in enumerate(achados):
        cabeca = achado.group()
        if corrido[achado.start() - 1 : achado.start()] != "/" or not numero.startswith(cabeca):
            continue
        cauda = numero[len(cabeca) :]
        depois = any(seguinte.group() == cauda for seguinte in achados[n + 1 :])
        if cauda and depois and not Counter((cabeca, cauda)) - restam:
            return cabeca, cauda
    return None


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
        return _FORMA_DE_DATA.search(conteudo) is not None
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
