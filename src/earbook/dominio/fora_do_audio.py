# SPDX-License-Identifier: GPL-3.0-or-later
"""O que sai inteiro do texto lido (ADR-0008): pelo papel, o bloco de código e o índice
remissivo; pela repetição, a marca d'água (o destaque de margem mora em `destaque_de_margem`);
pelo conteúdo de cada parágrafo, a bibliografia (ABNT e Vancouver), o índice remissivo sem
marcação, o sumário de papel e a propaganda. A limpeza registra cada um, com o motivo daqui.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence

from earbook.dominio.referencias_vancouver import regioes_de_referencias
from earbook.dominio.segmento import PALAVRA, Papel, Segmento

MOTIVO_DO_PAPEL = {Papel.CODIGO: "código-fonte", Papel.INDICE: "índice remissivo"}
# Medido nos sete livros de livros/trabalho/ (2026-11-02): a marca d'água "OceanofPDF.com" está
# em 321 de 321 arquivos do Learning DDD; o parágrafo de verdade que mais se repete está em 6
# arquivos (2%), e a maior fração é 33%, em 2 arquivos do Tides. O título se repete de propósito
# ("Questões de revisão" em 65% do Dalgalarrondo) e não conta.
FRACAO_MINIMA_DA_MARCA = 0.5
# Num livro de poucos arquivos (o Huxley tem 4 com texto), 2 ou 3 iguais ainda são texto.
ARQUIVOS_MINIMOS_DA_MARCA = 10
# A bibliografia (ADR-0008, "Bibliografia"), no padrão ABNT: o sobrenome, ou a instituição, em
# maiúsculas, seguido de vírgula ou ponto ("ABDO, C. H. N.", "ALONSO FERNANDES, F.", "AMERICAN
# PSYCHIATRIC ASSOCIATION.", "WORLD HEALTH ORGANIZATION (WHO)."), e um ano. Medido: o
# Dalgalarrondo tem 24 parágrafos-referência seguidos (p. 417 a 431); o Competente, no máximo 3
# (as referências dele se partem entre nota e parágrafo); o Learning DDD, 0 (APA: "Evans, E.").
REFERENCIAS_SEGUIDAS = 10
MOTIVO_DA_BIBLIOGRAFIA = "bibliografia: referências no padrão ABNT"
MOTIVO_DO_VANCOUVER = "bibliografia: referências no estilo Vancouver"
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
# O capítulo que quem prepara o livro declara fora do áudio (ADR-0008, "Tratado em português e em
# espanhol"): a lista de autores, o sumário de papel, o anexo de respostas.
MOTIVO_DO_CAPITULO_FORA = "capítulo fora do áudio: pedido no preparar"
# O título sem letra nem algarismo ("•", "• •", "---", "~"): o resto de figura que o OCR do PDF
# deixou (ADR-0008, "Tratado em português e em espanhol"). Medido: 375 no Manica.
MOTIVO_DO_TITULO_SEM_LETRA = "título sem letra nem algarismo"
# ", 346-347", ", 66", ", 200-203". A vírgula decimal ("2,0", as tabelas do Dalgalarrondo) não tem
# espaço; o ano ("Porto Alegre, 2004") e o número antes do parêntese ("(Cummings, 20)") não contam.
_PAGINA_DO_INDICE = re.compile(
    r",\s+(?!(?:1[5-9]|20)\d\d\b)\d{1,4}(?:\s*[-\u2013]\s*\d{1,4})?(?=[\s,;.]|$)"
)
_AUTOR_ABNT = re.compile(r"[A-ZÀ-Ý][A-ZÀ-Ý'\u2019-]+(?:\s+[A-ZÀ-Ý(][A-ZÀ-Ý'\u2019()-]*)*[,.]\s")
_ANO = re.compile(r"\b(?:1[5-9]|20)\d\d\b")


class CapituloDesconhecidoError(ValueError):
    pass


def capitulos_com_remocao(motivos: Mapping[str, str]) -> frozenset[str]:
    """Os capítulos de que a limpeza tirou algum segmento, pelo registro (ID do segmento →
    motivo), qualquer que seja a regra. O que ficou sem nenhum em `limpos/` foi esvaziado por ela,
    e o `montar` o deixa fora do EPUB; o que nunca teve segmento (a capa) não está aqui (ADR-0005,
    "Todo capítulo sem texto fora do EPUB montado")."""
    return frozenset(id_.partition("-")[0] for id_ in motivos)


def capitulos_pedidos(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]], fora: Sequence[str]
) -> dict[str, str]:
    """ID → motivo de cada segmento dos capítulos que o `preparar --sem-capitulo` declarou fora do
    áudio (ADR-0008, "Tratado em português e em espanhol"). O capítulo que o livro não tem é erro:
    o pedido errado não pode passar calado."""
    desconhecidos = sorted(set(fora) - {capitulo for capitulo, _ in capitulos})
    if desconhecidos:
        mensagem = f"o livro não tem o capítulo {', '.join(desconhecidos)}"
        raise CapituloDesconhecidoError(mensagem)
    return {
        segmento.id: MOTIVO_DO_CAPITULO_FORA
        for capitulo, segmentos in capitulos
        if capitulo in fora
        for segmento in segmentos
    }


def bibliografia(capitulos: Sequence[tuple[str, Sequence[Segmento]]]) -> dict[str, str]:
    """ID → motivo de cada referência das sequências de 10 ou mais parágrafos-referência ABNT
    seguidos no mesmo capítulo, e do título logo antes de cada sequência (ADR-0008,
    "Bibliografia"); e de cada região de referências Vancouver.

    O título nunca dispara a regra: o ADR-0008 proíbe reconhecer pelo título ("Índice" é o
    sumário em português). Ele só sai junto, como o "Index" do índice remissivo.
    """
    saem: dict[str, str] = {}
    for _, segmentos in capitulos:
        for inicio, fim in _sequencias_de_referencias(segmentos):
            saem |= _com_o_titulo_antes(segmentos, inicio, fim, MOTIVO_DA_BIBLIOGRAFIA)
        # As referências médicas, no estilo Vancouver (ADR-0008, "Referências no estilo Vancouver").
        for inicio, fim in regioes_de_referencias(segmentos):
            saem |= dict.fromkeys((s.id for s in segmentos[inicio:fim]), MOTIVO_DO_VANCOUVER)
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


def titulos_sem_letra(capitulos: Sequence[tuple[str, Sequence[Segmento]]]) -> dict[str, str]:
    """ID → motivo de cada título sem letra nem algarismo. O de algarismo ("2012", o ano; "1", o
    número do capítulo) e o de letra solta ("V", o capítulo em romano; "A", a letra do índice)
    ficam: também são título de verdade. Só título: a pausa de cena ("* * *") vem como parágrafo."""
    return {
        segmento.id: MOTIVO_DO_TITULO_SEM_LETRA
        for _, segmentos in capitulos
        for segmento in segmentos
        if segmento.papel is Papel.TITULO and not any(c.isalnum() for c in segmento.texto)
    }


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
