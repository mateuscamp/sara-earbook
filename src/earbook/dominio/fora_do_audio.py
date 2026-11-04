# SPDX-License-Identifier: GPL-3.0-or-later
"""O que sai inteiro do texto lido (ADR-0008): pelo papel, o bloco de código e o índice
remissivo; pela repetição, a marca d'água e o destaque de margem; pelo conteúdo de cada
parágrafo, a bibliografia, o índice remissivo sem marcação, o sumário de papel e a propaganda.
A limpeza registra cada um, com o motivo daqui.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Sequence

from earbook.dominio.segmento import PALAVRA, Papel, Segmento, primeira_letra

MOTIVO_DO_PAPEL = {Papel.CODIGO: "código-fonte", Papel.INDICE: "índice remissivo"}
# Medido nos sete livros de livros/trabalho/ (2026-11-02): a marca d'água "OceanofPDF.com" está
# em 321 de 321 arquivos do Learning DDD; o parágrafo de verdade que mais se repete está em 6
# arquivos (2%), e a maior fração é 33%, em 2 arquivos do Tides. O título se repete de propósito
# ("Questões de revisão" em 65% do Dalgalarrondo) e não conta.
FRACAO_MINIMA_DA_MARCA = 0.5
# Num livro de poucos arquivos (o Huxley tem 4 com texto), 2 ou 3 iguais ainda são texto.
ARQUIVOS_MINIMOS_DA_MARCA = 10
# O destaque de margem (ADR-0008, "Destaque de margem repetido"). Medido no Dalgalarrondo: a
# janela de 2 a 6 segmentos e o mínimo de 4 a 8 palavras tiram de 238 a 239 destaques, e nada
# no Competente, no Hard Parts, no Huxley, no Tides nem no Learning DDD.
JANELA_DO_DESTAQUE = 3
PALAVRAS_DO_DESTAQUE = 6
MOTIVO_DO_DESTAQUE = "destaque de margem: repete o texto vizinho"
# Aspa ou parêntese depois do ponto ainda fecham a frase.
_FECHA_FRASE = re.compile(r"[.!?\u2026][\u201d\u2019\"')]*$")
# O hífen da quebra ("pri-" + "meiros") e o do composto ("divi-dem-se", contra "dividem-se" no
# destaque) não contam na comparação.
_HIFEN_NA_PALAVRA = re.compile(r"(?<=[^\W\d_])[-\u2010\u00ad]\s*(?=[^\W\d_])")
# A bibliografia (ADR-0008, "Bibliografia"), no padrão ABNT: o sobrenome, ou a instituição, em
# maiúsculas, seguido de vírgula ou ponto ("ABDO, C. H. N.", "ALONSO FERNANDES, F.", "AMERICAN
# PSYCHIATRIC ASSOCIATION.", "WORLD HEALTH ORGANIZATION (WHO)."), e um ano. Medido: o
# Dalgalarrondo tem 24 parágrafos-referência seguidos (p. 417 a 431); o Competente, no máximo 3
# (as referências dele se partem entre nota e parágrafo); o Learning DDD, 0 (APA: "Evans, E.").
REFERENCIAS_SEGUIDAS = 10
MOTIVO_DA_BIBLIOGRAFIA = "bibliografia: referências no padrão ABNT"
# O índice remissivo sem marcação (ADR-0008, "Índice pelo conteúdo"): cada parágrafo-entrada traz
# números de página depois de vírgula e espaço, com até 8 palavras por número. Medido: os
# parágrafos do índice têm no máximo 4,4 palavras por número (Dalgalarrondo) e 5,8 (Hard Parts);
# fora do índice, as sequências não passam de 1 parágrafo (as referências soltas do Competente).
ENTRADAS_SEGUIDAS = 10
PALAVRAS_POR_PAGINA = 8
MOTIVO_DO_INDICE_PELO_CONTEUDO = "índice remissivo: termos seguidos do número da página"
# O sumário de papel (ADR-0009): a linha com 5 pontos seguidos e número no fim. Só quando há 5 ou
# mais no capítulo: a linha solta pode ser de um quadro ou formulário. Medido: o Dalgalarrondo
# tem 41, todas no capítulo de abertura, e os outros cinco livros, nenhuma.
LINHAS_DO_SUMARIO = 5
MOTIVO_DO_SUMARIO_DE_PAPEL = "sumário de papel: pontilhado e número de página"
_LINHA_DE_SUMARIO = re.compile(r"\.{5,}\s*\d+\s*$")
# A propaganda (ADR-0009): o título "Conheça também" e os parágrafos até o próximo título. Com
# mais de 5, é texto do livro: a propaganda é curta, e o título não leva um capítulo junto.
TITULO_DA_PROPAGANDA = "conheça também"
PARAGRAFOS_DA_PROPAGANDA = 5
MOTIVO_DA_PROPAGANDA = "propaganda do livro: Conheça também"
# ", 346-347", ", 66", ", 200-203". A vírgula decimal ("2,0", as tabelas do Dalgalarrondo) não tem
# espaço; o ano ("Porto Alegre, 2004") e o número antes do parêntese ("(Cummings, 20)") não contam.
_PAGINA_DO_INDICE = re.compile(
    r",\s+(?!(?:1[5-9]|20)\d\d\b)\d{1,4}(?:\s*[-\u2013]\s*\d{1,4})?(?=[\s,;.]|$)"
)
_AUTOR_ABNT = re.compile(r"[A-ZÀ-Ý][A-ZÀ-Ý'\u2019-]+(?:\s+[A-ZÀ-Ý(][A-ZÀ-Ý'\u2019()-]*)*[,.]\s")
_ANO = re.compile(r"\b(?:1[5-9]|20)\d\d\b")
# O número conta: o destaque com "3 a 25 segundos" não repete o texto com "5 a 30".
_PALAVRA_OU_NUMERO = re.compile(rf"{PALAVRA.pattern}|\d+")


def bibliografia(capitulos: Sequence[tuple[str, Sequence[Segmento]]]) -> dict[str, str]:
    """ID → motivo de cada referência das sequências de 10 ou mais parágrafos-referência seguidos
    no mesmo capítulo, e do título logo antes de cada sequência (ADR-0008, "Bibliografia").

    O título nunca dispara a regra: o ADR-0008 proíbe reconhecer pelo título ("Índice" é o
    sumário em português). Ele só sai junto, como o "Index" do índice remissivo.
    """
    saem: dict[str, str] = {}
    for _, segmentos in capitulos:
        for inicio, fim in _sequencias_de_referencias(segmentos):
            saem |= _com_o_titulo_antes(segmentos, inicio, fim, MOTIVO_DA_BIBLIOGRAFIA)
    return saem


def _com_o_titulo_antes(
    segmentos: Sequence[Segmento], inicio: int, fim: int, motivo: str
) -> dict[str, str]:
    """ID → `motivo` dos segmentos de `inicio` a `fim`, e do título logo antes, se houver."""
    titulo_antes = inicio > 0 and segmentos[inicio - 1].papel is Papel.TITULO
    primeiro = inicio - 1 if titulo_antes else inicio
    return {s.id: motivo for s in segmentos[primeiro:fim]}


def indice_pelo_conteudo(capitulos: Sequence[tuple[str, Sequence[Segmento]]]) -> dict[str, str]:
    """ID → motivo de cada parágrafo das sequências de 10 ou mais parágrafos-entrada seguidos no
    mesmo capítulo, das letras no meio delas ("A", "B"…, Hard Parts) e do título logo antes
    (ADR-0008, "Índice pelo conteúdo").

    É o índice que a marcação não diz: o do PDF importado e o do EPUB sem `epub:type`. Como na
    bibliografia, o título ("Índice", "Index") nunca dispara a regra.
    """
    saem: dict[str, str] = {}
    for _, segmentos in capitulos:
        for inicio, fim in _sequencias_de_entradas(segmentos):
            saem |= _com_o_titulo_antes(segmentos, inicio, fim, MOTIVO_DO_INDICE_PELO_CONTEUDO)
    return saem


def _sequencias_de_entradas(segmentos: Sequence[Segmento]) -> list[tuple[int, int]]:
    """(início, fim) de cada sequência de `ENTRADAS_SEGUIDAS` ou mais entradas. A letra no meio
    não parte a sequência; ela pode abrir a sequência, mas nunca a fecha."""
    sequencias: list[tuple[int, int]] = []
    inicio: int | None = None
    fim = entradas = 0
    for posicao, segmento in enumerate([*segmentos, None]):
        entrada = segmento is not None and _entrada_de_indice(segmento)
        if entrada or (segmento is not None and _letra_do_indice(segmento)):
            inicio = posicao if inicio is None else inicio
            if entrada:
                fim, entradas = posicao + 1, entradas + 1
            continue
        if inicio is not None and entradas >= ENTRADAS_SEGUIDAS:
            sequencias.append((inicio, fim))
        inicio, entradas = None, 0
    return sequencias


def _entrada_de_indice(segmento: Segmento) -> bool:
    """O parágrafo com número de página e até `PALAVRAS_POR_PAGINA` palavras por número. Ele não
    precisa terminar no número: a entrada do Hard Parts termina na remissão ("(see also …)")."""
    paginas = len(_PAGINA_DO_INDICE.findall(segmento.texto))
    palavras = len(PALAVRA.findall(segmento.texto))
    densa = paginas > 0 and palavras <= PALAVRAS_POR_PAGINA * paginas
    return segmento.papel is Papel.PARAGRAFO and densa


def _letra_do_indice(segmento: Segmento) -> bool:
    """O título de uma letra só, que separa as letras do índice do Hard Parts."""
    texto = segmento.texto.strip()
    return segmento.papel is Papel.TITULO and len(texto) == 1 and texto.isalpha()


def _sequencias_de_referencias(segmentos: Sequence[Segmento]) -> list[tuple[int, int]]:
    """(início, fim) de cada sequência de `REFERENCIAS_SEGUIDAS` ou mais parágrafos-referência."""
    sequencias: list[tuple[int, int]] = []
    inicio = 0
    for posicao, segmento in enumerate([*segmentos, None]):
        if segmento is not None and _referencia(segmento):
            continue
        if posicao - inicio >= REFERENCIAS_SEGUIDAS:
            sequencias.append((inicio, posicao))
        inicio = posicao + 1
    return sequencias


def _referencia(segmento: Segmento) -> bool:
    """O parágrafo que abre com o autor em maiúsculas, no padrão ABNT, e traz um ano."""
    texto = segmento.texto
    abnt = _AUTOR_ABNT.match(texto) is not None and _ANO.search(texto) is not None
    return segmento.papel is Papel.PARAGRAFO and abnt


def sumario_de_papel(capitulos: Sequence[tuple[str, Sequence[Segmento]]]) -> dict[str, str]:
    """ID → motivo de cada linha do sumário de papel, quando o capítulo tem 5 ou mais. As linhas
    do meio que não têm pontilhado (o título da parte, o título em duas linhas) ficam."""
    saem: dict[str, str] = {}
    for _, segmentos in capitulos:
        linhas = [s.id for s in segmentos if _LINHA_DE_SUMARIO.search(s.texto)]
        if len(linhas) >= LINHAS_DO_SUMARIO:
            saem |= dict.fromkeys(linhas, MOTIVO_DO_SUMARIO_DE_PAPEL)
    return saem


def propaganda(capitulos: Sequence[tuple[str, Sequence[Segmento]]]) -> dict[str, str]:
    """ID → motivo do título "Conheça também" e dos parágrafos até o próximo título, ou o fim
    do capítulo. O título nunca dispara a regra com mais de 5 parágrafos depois dele."""
    saem: dict[str, str] = {}
    for _, segmentos in capitulos:
        for n, segmento in enumerate(segmentos):
            if _titulo_da_propaganda(segmento):
                bloco = _ate_o_proximo_titulo(segmentos, n)
                if len(bloco) - 1 <= PARAGRAFOS_DA_PROPAGANDA:
                    saem |= dict.fromkeys((s.id for s in bloco), MOTIVO_DA_PROPAGANDA)
    return saem


def _titulo_da_propaganda(segmento: Segmento) -> bool:
    return segmento.papel is Papel.TITULO and segmento.texto.casefold() == TITULO_DA_PROPAGANDA


def _ate_o_proximo_titulo(segmentos: Sequence[Segmento], inicio: int) -> Sequence[Segmento]:
    for n in range(inicio + 1, len(segmentos)):
        if segmentos[n].papel is Papel.TITULO:
            return segmentos[inicio:n]
    return segmentos[inicio:]


def pelo_papel(capitulos: Sequence[tuple[str, Sequence[Segmento]]]) -> dict[str, str]:
    """ID → motivo de cada bloco de código e de cada índice remissivo."""
    return {
        segmento.id: MOTIVO_DO_PAPEL[segmento.papel]
        for _, segmentos in capitulos
        for segmento in segmentos
        if segmento.papel in MOTIVO_DO_PAPEL
    }


def marcas_dagua(capitulos: Sequence[tuple[str, Sequence[Segmento]]]) -> dict[str, str]:
    """ID → motivo de cada parágrafo idêntico em metade ou mais dos arquivos com texto, e em 10
    ou mais. Só parágrafo, e só com letra: título, citação e item repetem de propósito, e a pausa
    de cena ("* * *") marca a pausa.
    """
    com_texto = sum(1 for _, segmentos in capitulos if segmentos)
    minimo = max(ARQUIVOS_MINIMOS_DA_MARCA, FRACAO_MINIMA_DA_MARCA * com_texto)
    motivos = {
        texto: f"marca d'água: o mesmo parágrafo em {len(onde)} de {com_texto} arquivos"
        for texto, onde in _arquivos_de_cada_paragrafo(capitulos).items()
        if len(onde) >= minimo
    }
    return {
        segmento.id: motivos[segmento.texto]
        for _, segmentos in capitulos
        for segmento in segmentos
        if _pode_ser_marca(segmento) and segmento.texto in motivos
    }


def _arquivos_de_cada_paragrafo(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]],
) -> dict[str, set[str]]:
    """Texto → capítulos em que ele aparece, contando só o que pode ser marca d'água."""
    arquivos: defaultdict[str, set[str]] = defaultdict(set)
    for capitulo, segmentos in capitulos:
        for segmento in segmentos:
            if _pode_ser_marca(segmento):
                arquivos[segmento.texto].add(capitulo)
    return arquivos


def _pode_ser_marca(segmento: Segmento) -> bool:
    return segmento.papel is Papel.PARAGRAFO and PALAVRA.search(segmento.texto) is not None


def destaques(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]],
    no_meio_da_frase: Callable[[Segmento, Segmento], bool],
) -> dict[str, str]:
    """ID → motivo de cada destaque de margem: o parágrafo com forma de frase, de 6 palavras ou
    mais, cujas palavras aparecem seguidas no texto dos parágrafos vizinhos (3 antes e 3
    depois, no mesmo capítulo), juntados. Juntar os vizinhos pega o destaque que parte uma frase
    ("…principais palcos" | destaque | "de nossas vidas…", Dalgalarrondo p. 250).

    O destaque igual a um parágrafo inteiro do texto é um par de gêmeos: só sai a cópia que
    `no_meio_da_frase(anterior, seguinte)`, a regra da junção, aponta. As duas referências
    iguais e seguidas do Learning DDD ficam.
    """
    saem: dict[str, str] = {}
    for _, segmentos in capitulos:
        # A chave de cada segmento uma vez só, para o gêmeo (lote A da revisão).
        chaves = [_chave(segmento.texto) for segmento in segmentos]
        for i, segmento in enumerate(segmentos):
            if _e_destaque(segmentos, chaves, i, no_meio_da_frase):
                saem[segmento.id] = MOTIVO_DO_DESTAQUE
    return saem


def _e_destaque(
    segmentos: Sequence[Segmento],
    chaves: Sequence[str],
    i: int,
    no_meio_da_frase: Callable[[Segmento, Segmento], bool],
) -> bool:
    if not _parece_frase(segmentos[i]):
        return False
    janela = range(max(0, i - JANELA_DO_DESTAQUE), min(len(segmentos), i + JANELA_DO_DESTAQUE + 1))
    vizinhos = [k for k in janela if k != i and segmentos[k].papel is Papel.PARAGRAFO]
    # O texto dos vizinhos se junta antes da chave: o hífen da quebra fica no fim de um e o
    # resto da palavra no começo do outro ("os pri-" + "meiros").
    juntos = _chave(" ".join(segmentos[k].texto for k in vizinhos))
    if f" {chaves[i]} " not in f" {juntos} ":
        return False
    if all(chaves[k] != chaves[i] for k in vizinhos):
        return True
    return 0 < i < len(segmentos) - 1 and no_meio_da_frase(segmentos[i - 1], segmentos[i + 1])


def _parece_frase(segmento: Segmento) -> bool:
    """Parágrafo que abre em maiúscula e fecha frase. O título que veio como parágrafo ("ATO
    VOLITIVO OU ATO DE VONTADE"), a continuação em minúscula e a pergunta que termina em ":"
    também repetem o vizinho, e ficam."""
    return (
        segmento.papel is Papel.PARAGRAFO
        and primeira_letra(segmento.texto).isupper()
        and _FECHA_FRASE.search(segmento.texto) is not None
        and len(PALAVRA.findall(segmento.texto)) >= PALAVRAS_DO_DESTAQUE
    )


def _chave(texto: str) -> str:
    """As palavras e os números, em minúscula e sem hífen dentro da palavra, separados por um
    espaço: a pontuação e a citação entre parênteses não separam o destaque do texto."""
    sem_hifen = _HIFEN_NA_PALAVRA.sub("", texto)
    return " ".join(achado.group().casefold() for achado in _PALAVRA_OU_NUMERO.finditer(sem_hifen))
