# SPDX-License-Identifier: GPL-3.0-or-later
"""Limpeza para o ouvido (ADR-0003): tira do texto o que o TTS leria e não é do livro."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from earbook.dominio.cabecalho import (
    frase_repetida,
    frases_de_cabecalho,
    frases_do_cabecalho,
    frases_do_livro,
)
from earbook.dominio.capitular import CapitularDevolvida, devolver_uma, leituras
from earbook.dominio.direitos import nas_pontas, pagina_de_direitos
from earbook.dominio.fora_do_audio import MOTIVO_DO_PAPEL, marcas_dagua, pelo_papel
from earbook.dominio.segmento import ABRE_PARAGRAFO, Papel, Segmento

# Parágrafo que continua: a primeira letra, depois de aspas e travessões, é minúscula.
_PRIMEIRA_LETRA = re.compile(rf"^{ABRE_PARAGRAFO}(?P<letra>\w)")
# Termina frase. Aspas e apóstrofo não estão aqui: a fala que fecha aspas com vírgula segue
# em "he answered" na página seguinte, e o possessivo "warriors" + apóstrofo segue em "reach".
_FIM_DE_FRASE = tuple(".!?…:;")
# A1 da auditoria: "...trees" + travessão / travessão + "and found" é pausa de propósito.
TRAVESSAO = "\u2014"
_HIFEN_NO_FIM = re.compile(r"\w-$")
_PONTUACAO = re.compile(r"[.,;:!?…“”\"]")
# "first prologue", "ONE", "acknowledgments": título de capítulo que veio como <p>.
PALAVRAS_DA_LINHA_CURTA = 3
MOTIVO_DA_LINHA_CURTA = "parágrafo partido ou título? linha curta sem pontuação: não juntei"
# Letra maiúscula sozinha, sem ser inicial ("J."), contração ou pronome "I": a capitular
# que a conversão do PDF deixou no meio do texto.
_LETRA_SOLTA = re.compile(r"(?<![\w\u2019'.\-])(?P<letra>[A-HJ-Z])(?![\w\u2019'.\-])")
# O parágrafo marcado e os dois seguintes: no Tides, a letra solta nunca foi mais longe.
PARAGRAFOS_DA_PISTA = 3
MOTIVO_DA_CAPITULAR = (
    "capitular perdida? começa em minúscula logo depois de título: corrigir a primeira letra"
)


@dataclass(frozen=True)
class Remocao:
    """Um segmento que saiu do áudio, com o motivo, para o `conferir` e para revisão."""

    id: str
    motivo: str
    texto: str


@dataclass(frozen=True)
class Pista:
    id: str
    posicao: int
    letra: str


@dataclass(frozen=True)
class Suspeita:
    """Um segmento que parece lixo de página, mas ficou no texto: quem decide é o agente."""

    id: str
    motivo: str
    texto: str
    pista: Pista | None = None


@dataclass(frozen=True)
class Aparo:
    """Um pedaço tirado do fim de um segmento que continua no texto, como o cabeçalho colado."""

    id: str
    motivo: str
    texto: str


@dataclass(frozen=True)
class Juncao:
    """O segmento `id` foi juntado ao fim do segmento `em`: era o mesmo parágrafo partido."""

    id: str
    em: str


@dataclass(frozen=True)
class CapituloLimpo:
    capitulo: str
    segmentos: tuple[Segmento, ...]


@dataclass(frozen=True)
class LivroLimpo:
    capitulos: tuple[CapituloLimpo, ...]
    remocoes: tuple[Remocao, ...]
    suspeitas: tuple[Suspeita, ...] = ()
    aparos: tuple[Aparo, ...] = ()
    juncoes: tuple[Juncao, ...] = ()
    capitulares: tuple[CapitularDevolvida, ...] = ()


def limpar_para_o_ouvido(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]],
    titulo: str,
    autor: str,
) -> LivroLimpo:
    """A limpeza inteira, na ordem: direitos, marca d'água, cabeçalho solto, cabeçalho colado,
    parágrafo partido, capitular e, por último, código e índice.

    A ordem importa: o cabeçalho, solto ou colado, fica exatamente onde o parágrafo se
    partiu, e só some do meio depois que as duas metades ficam lado a lado.
    """
    sem_cabecalho = _tirar_paginas_marcas_e_cabecalhos(capitulos, titulo, autor)
    frases = frases_do_cabecalho(capitulos, titulo, autor)
    juntado = _juntar_paragrafos_partidos(_aparar_cabecalhos_colados(sem_cabecalho, frases))
    # ADR-0007: sem a letra solta, uma continuação em minúscula pode aparecer ("he" + "demanded.").
    juntado = _juntar_paragrafos_partidos(
        _devolver_capitulares(_marcar_capitulares_perdidas(juntado))
    )
    # ADR-0008: código e índice saem por último: até aqui, separam os parágrafos em volta deles.
    return _tirar_pelo_papel(juntado)


def _tirar_paginas_marcas_e_cabecalhos(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]], titulo: str, autor: str
) -> LivroLimpo:
    """A página de direitos, a marca d'água e o cabeçalho solto. A marca sai antes da junção, como
    o cabeçalho, para as metades do parágrafo partido se juntarem (ADR-0008)."""
    sem_direitos, direitos = tirar_paginas_de_direitos(capitulos)
    sem_marca, marcas = _tirar(sem_direitos, marcas_dagua(sem_direitos))
    livro = tirar_cabecalhos_de_pagina(sem_marca, titulo, autor)
    return replace(livro, remocoes=(*direitos, *marcas, *livro.remocoes))


def _tirar(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]], saem: Mapping[str, str]
) -> tuple[list[tuple[str, list[Segmento]]], list[Remocao]]:
    """Tira os IDs de `saem`, cada um com o seu motivo: nada sai sem registro (ADR-0003)."""
    restantes = [(c, [s for s in segmentos if s.id not in saem]) for c, segmentos in capitulos]
    remocoes = [
        Remocao(s.id, saem[s.id], s.texto) for _, segs in capitulos for s in segs if s.id in saem
    ]
    return restantes, remocoes


def _tirar_pelo_papel(livro: LivroLimpo) -> LivroLimpo:
    capitulos = [(capitulo.capitulo, capitulo.segmentos) for capitulo in livro.capitulos]
    restantes, remocoes = _tirar(capitulos, pelo_papel(capitulos))
    limpos = tuple(CapituloLimpo(capitulo, tuple(segmentos)) for capitulo, segmentos in restantes)
    return replace(livro, capitulos=limpos, remocoes=(*livro.remocoes, *remocoes))


def tirar_paginas_de_direitos(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]],
) -> tuple[list[tuple[str, list[Segmento]]], list[Remocao]]:
    """Tira a página de direitos autorais: o segmento com marca forte (©, direitos
    reservados, ISBN) e as linhas vizinhas com marca fraca, que formam a página com ele.

    Cada remoção fica registrada, como toda remoção da limpeza (ADR-0003).
    """
    na_ponta = nas_pontas(sum(len(segmentos) for _, segmentos in capitulos))
    saem: dict[str, str] = {}
    inicio = 0
    for _, segmentos in capitulos:
        motivos = pagina_de_direitos(segmentos, lambda i, base=inicio: na_ponta(base + i))
        saem |= {segmentos[i].id: motivo for i, motivo in motivos.items()}
        inicio += len(segmentos)
    return _tirar(capitulos, saem)


def _aparar_cabecalhos_colados(livro: LivroLimpo, frases: set[str]) -> LivroLimpo:
    """Tira "… trying Tides of Darkness 2" do fim do parágrafo e registra o pedaço tirado."""
    if not frases:
        return livro
    alternativas = "|".join(re.escape(f) for f in sorted(frases, key=len, reverse=True))
    colado = re.compile(
        rf"(?:\s+|(?<=\w-))(?P<cabecalho>(?P<f1>{alternativas})\s+\d{{1,4}}|\d{{1,4}}\s+(?P<f2>{alternativas}))$",
        re.IGNORECASE,
    )
    aparos: list[Aparo] = []
    capitulos: list[CapituloLimpo] = []
    for capitulo in livro.capitulos:
        segmentos: list[Segmento] = []
        for segmento in capitulo.segmentos:
            achado = colado.search(segmento.texto) if segmento.papel is Papel.PARAGRAFO else None
            if achado is None:
                segmentos.append(segmento)
                continue
            motivo = f"cabeçalho de página {achado['f1'] or achado['f2']!r} colado no fim"
            aparos.append(Aparo(segmento.id, motivo, achado["cabecalho"]))
            segmentos.append(replace(segmento, texto=segmento.texto[: achado.start()]))
        capitulos.append(CapituloLimpo(capitulo.capitulo, tuple(segmentos)))
    return replace(livro, capitulos=tuple(capitulos), aparos=tuple(aparos))


def _juntar_paragrafos_partidos(livro: LivroLimpo) -> LivroLimpo:
    juncoes: list[Juncao] = list(livro.juncoes)
    suspeitas: list[Suspeita] = list(livro.suspeitas)
    ja_marcados = {s.id for s in livro.suspeitas}
    capitulos: list[CapituloLimpo] = []
    for capitulo in livro.capitulos:
        saida: list[Segmento] = []
        for segmento in capitulo.segmentos:
            anterior = saida[-1] if saida else None
            if anterior is None or not _parece_continuacao(anterior, segmento):
                saida.append(segmento)
            elif _linha_curta(anterior.texto) or _linha_curta(segmento.texto):
                # Linha curta antes: o seguinte perdeu a capitular, e quem marca é o passo
                # da capitular. Linha curta depois: o seguinte é o título, marcado aqui uma
                # vez só, porque a junção roda de novo depois da capitular (ADR-0007).
                if _linha_curta(segmento.texto) and segmento.id not in ja_marcados:
                    suspeitas.append(Suspeita(segmento.id, MOTIVO_DA_LINHA_CURTA, segmento.texto))
                saida.append(segmento)
            else:
                saida[-1] = _juntar(anterior, segmento)
                juncoes.append(Juncao(segmento.id, anterior.id))
        capitulos.append(CapituloLimpo(capitulo.capitulo, tuple(saida)))
    return replace(
        livro, capitulos=tuple(capitulos), suspeitas=tuple(suspeitas), juncoes=tuple(juncoes)
    )


def _parece_continuacao(anterior: Segmento, segmento: Segmento) -> bool:
    """O anterior ficou aberto e este começa em minúscula: a quebra de página partiu os dois."""
    if anterior.papel is not Papel.PARAGRAFO or segmento.papel is not Papel.PARAGRAFO:
        return False
    if anterior.texto.endswith(TRAVESSAO) and segmento.texto.startswith(TRAVESSAO):
        return False
    return not anterior.texto.endswith(_FIM_DE_FRASE) and _comeca_em_minuscula(segmento.texto)


def _comeca_em_minuscula(texto: str) -> bool:
    """A primeira letra, depois de aspas e travessões, é minúscula."""
    primeira = _PRIMEIRA_LETRA.match(texto)
    return primeira is not None and primeira["letra"].islower()


def _marcar_capitulares_perdidas(livro: LivroLimpo) -> LivroLimpo:
    """Parágrafo em minúscula logo depois do título ou de linha curta (título como <p>).

    Medido no Tides of Darkness: os 25 começos de capítulo tinham a capitular deslocada para
    o meio do texto ("stirred, D unable"), e nenhum outro parágrafo em minúscula estava nessa
    posição. A pista aponta a letra solta, para o agente corrigir as duas pontas (A1).
    """
    # A4 da auditoria: um segmento entra uma vez só, com o primeiro motivo que o marcou.
    ja_marcados = {s.id for s in livro.suspeitas}
    novas: list[Suspeita] = []
    for capitulo in livro.capitulos:
        segmentos = capitulo.segmentos
        for i, segmento in enumerate(segmentos):
            anterior = segmentos[i - 1] if i else None
            if segmento.id in ja_marcados or not _perdeu_a_capitular(anterior, segmento):
                continue
            pista = _pista_da_letra_solta(segmentos[i : i + PARAGRAFOS_DA_PISTA])
            novas.append(Suspeita(segmento.id, MOTIVO_DA_CAPITULAR, segmento.texto, pista))
    return replace(livro, suspeitas=livro.suspeitas + tuple(novas))


def _devolver_capitulares(livro: LivroLimpo) -> LivroLimpo:
    """A letra da pista volta para o começo da palavra quando o livro prova a leitura (ADR-0007).

    A letra que é palavra ("A dark") imita o artigo de verdade ("saga A long story"); ela só
    volta quando a maioria das capitulares com pista do livro já voltou como palavra colada:
    é a prova de que esta conversão desloca a capitular (no Tides, 23 de 24).
    """
    textos = {s.id: s.texto for capitulo in livro.capitulos for s in capitulo.segmentos}
    propostas = leituras(livro.suspeitas, textos)
    devolvidas: list[CapitularDevolvida] = []
    for suspeita, leitura in (p for p in propostas if p[1].colada):
        devolvidas += devolver_uma(suspeita, leitura, textos, devolvidas)
    # Lote B da revisão: só a colada devolvida prova; a que não entrou não conta.
    if 2 * len(devolvidas) > sum(s.pista is not None for s in livro.suspeitas):
        for suspeita, leitura in (p for p in propostas if not p[1].colada):
            devolvidas += devolver_uma(suspeita, leitura, textos, devolvidas)
    corrigidos = {d.id for d in devolvidas}
    capitulos = tuple(
        replace(c, segmentos=tuple(replace(s, texto=textos[s.id]) for s in c.segmentos))
        for c in livro.capitulos
    )
    suspeitas = tuple(s for s in livro.suspeitas if s.id not in corrigidos)
    return replace(
        livro,
        capitulos=capitulos,
        suspeitas=suspeitas,
        capitulares=tuple(sorted(devolvidas, key=lambda d: d.id)),
    )


def _pista_da_letra_solta(segmentos: Sequence[Segmento]) -> Pista | None:
    """A primeira maiúscula sozinha, fora o "I": no Tides, 24 das 25 capitulares estavam assim.
    A do código e a do índice não são capitular (A1 da code-audit do ADR-0008)."""
    for segmento in (s for s in segmentos if s.papel not in MOTIVO_DO_PAPEL):
        achado = _LETRA_SOLTA.search(segmento.texto)
        if achado is not None:
            return Pista(segmento.id, achado.start("letra"), achado["letra"])
    return None


def _perdeu_a_capitular(anterior: Segmento | None, segmento: Segmento) -> bool:
    if segmento.papel is not Papel.PARAGRAFO or not _comeca_em_minuscula(segmento.texto):
        return False
    # "first prologue" no começo do capítulo é o título em minúscula, não a capitular.
    if _linha_curta(segmento.texto):
        return False
    # A3 da auditoria: sem título antes (começo do capítulo), o Tides não teve nenhum caso.
    if anterior is None:
        return False
    if anterior.papel is Papel.TITULO:
        return True
    return anterior.papel is Papel.PARAGRAFO and _linha_curta(anterior.texto)


def _linha_curta(texto: str) -> bool:
    return len(texto.split()) <= PALAVRAS_DA_LINHA_CURTA and not _PONTUACAO.search(texto)


def _juntar(anterior: Segmento, segmento: Segmento) -> Segmento:
    # "sub-" + "commander": palavra hifenizada partida na quebra de página volta sem espaço.
    separador = "" if _HIFEN_NO_FIM.search(anterior.texto) else " "
    texto = f"{anterior.texto}{separador}{segmento.texto}"
    return replace(anterior, texto=texto, notas=anterior.notas + segmento.notas)


def tirar_cabecalhos_de_pagina(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]],
    titulo: str,
    autor: str,
) -> LivroLimpo:
    """Tira os parágrafos que são cabeçalho corrente com número de página.

    A repetição se conta no livro inteiro, porque o cabeçalho atravessa capítulos. Só sai a
    frase que está no título ou no autor do OPF; a que se repete sem estar lá ("Dia 1",
    "Dia 2", "Dia 3" num diário) fica no texto como suspeita, para o agente decidir (H1 da
    auditoria). `tirar_cabecalhos_de_pagina([("c001", segmentos)], titulo, autor)`.
    """
    repetidas = frases_de_cabecalho([s for _, segmentos in capitulos for s in segmentos])
    do_livro = frases_do_livro(repetidas, titulo, autor)
    limpos: list[CapituloLimpo] = []
    remocoes: list[Remocao] = []
    suspeitas: list[Suspeita] = []
    for capitulo, segmentos in capitulos:
        mantidos: list[Segmento] = []
        for segmento in segmentos:
            frase = frase_repetida(segmento, repetidas)
            if frase is not None and frase.casefold() in do_livro:
                motivo = f"cabeçalho de página {frase!r}"
                remocoes.append(Remocao(segmento.id, motivo, segmento.texto))
                continue
            if frase is not None:
                motivo = f"possível cabeçalho de página {frase!r}: não está no título nem no autor"
                suspeitas.append(Suspeita(segmento.id, motivo, segmento.texto))
            mantidos.append(segmento)
        limpos.append(CapituloLimpo(capitulo, tuple(mantidos)))
    return LivroLimpo(tuple(limpos), tuple(remocoes), tuple(suspeitas))
