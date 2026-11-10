# SPDX-License-Identifier: GPL-3.0-or-later
"""Ponto de entrada do `earbook`. A saída é texto para humano; os dados ficam na pasta."""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from earbook.comandos import montar as montagem
from earbook.comandos.adaptar import ExportacaoDaAdaptacao, adaptar
from earbook.comandos.importar_pdf import Importacao, epub_padrao, importar_pdf
from earbook.comandos.preparar import Preparo, pasta_padrao, preparar
from earbook.comandos.roteiro import minutos
from earbook.comandos.traduzir import Exportacao, traduzir
from earbook.dominio.conferencia import Problema
from earbook.dominio.livro_limpo import LivroLimpo
from earbook.dominio.tipo_da_linha import TipoDeBloco
from earbook.dominio.trabalho import LivroPreparado
from earbook.dominio.traducao import PALAVRAS_POR_LOTE, Modo

EXEMPLOS_DE_TEXTO_FORA = 5
PROBLEMAS_LISTADOS = 50


class _Opcoes(argparse.Namespace):
    """Tipa o resultado do argparse, que de outro modo devolve atributos `Any`.

    Os valores aqui são só o ponto de partida; o argparse sobrescreve os do subcomando.
    """

    comando: str = ""
    epub: Path = Path()
    pasta: Path | None = None
    pdf: Path = Path()
    saida: Path | None = None
    idioma: str = "und"
    titulo: str | None = None
    autor: str | None = None
    trabalho: Path = Path()
    palavras: int = PALAVRAS_POR_LOTE
    modo: Modo | None = None
    capitulo: str | None = None
    ids: list[str] | None = None


def principal(argumentos: list[str] | None = None) -> int:
    """`principal(["preparar", "Duna.epub"])` cria `Duna.earbook/` e devolve 0."""
    opcoes = _analisador().parse_args(argumentos, namespace=_Opcoes())
    try:
        resumo, codigo = _COMANDOS[opcoes.comando](opcoes)
    except (OSError, ValueError) as erro:
        print(f"earbook: {erro}", file=sys.stderr)
        return 1
    # Fora do try: saída fechada (`| head`) não é falha do trabalho, que já está gravado.
    try:
        # flush aqui: num cano, o print só enche o buffer, e o EPIPE viria no fim do
        # processo, fora deste try (B1 da pós-auditoria).
        print(resumo, flush=True)
    except BrokenPipeError:
        _calar_a_saida()
    return codigo


def _calar_a_saida() -> None:
    """Manda o resto da saída para /dev/null, receita da documentação do Python (signal).

    Sem isso, o flush do fim do processo escreve de novo no cano fechado e mostra
    "Exception ignored" com traceback.
    """
    with contextlib.suppress(io.UnsupportedOperation):  # saída sem descritor (teste)
        descritor = sys.stdout.fileno()
        nulo = os.open(os.devnull, os.O_WRONLY)
        _ = os.dup2(nulo, descritor)
        os.close(nulo)


def _importar(opcoes: _Opcoes) -> tuple[str, int]:
    epub = opcoes.saida or epub_padrao(opcoes.pdf)
    importacao = importar_pdf(opcoes.pdf, epub, opcoes.idioma, opcoes.titulo, opcoes.autor)
    return _resumo_da_importacao(importacao), 0


def _preparar(opcoes: _Opcoes) -> tuple[str, int]:
    pasta = opcoes.pasta or pasta_padrao(opcoes.epub)
    return _resumo(preparar(opcoes.epub, pasta), pasta), 0


def _conferir(opcoes: _Opcoes) -> tuple[str, int]:
    """Código 1 quando há problema: o `montar` recusaria o livro (ADR-0005)."""
    pasta = opcoes.trabalho
    conferencia = montagem.conferencia_da_pasta(pasta, opcoes.modo, opcoes.capitulo)
    problemas = conferencia.problemas
    avisos = _linhas_dos_avisos(conferencia.avisos)
    if not problemas and opcoes.capitulo is not None:
        # Lote A da revisão: "pode montar" escondia o resto do livro, que não foi conferido.
        linhas = [f"{pasta}: nada a corrigir no capítulo {opcoes.capitulo}."]
        return "\n".join([*linhas, *avisos]), 0
    if not problemas:
        linhas = [f"{pasta}: nada faltando, sobrando ou repetido; pode montar."]
        return "\n".join([*linhas, *avisos]), 0
    linhas = [f"{pasta}: {len(problemas)} problemas; o montar recusaria o livro."]
    linhas += [f"  {p.id}: {p.motivo}" for p in problemas[:PROBLEMAS_LISTADOS]]
    if len(problemas) > PROBLEMAS_LISTADOS:
        linhas.append(f"  ... e mais {len(problemas) - PROBLEMAS_LISTADOS}")
    return "\n".join([*linhas, *avisos]), 1


def _linhas_dos_avisos(avisos: tuple[Problema, ...]) -> list[str]:
    """O termo omitido e o descarte por decisão, que a sessão lê antes do `montar` (ADR-0009)."""
    if not avisos:
        return []
    if len(avisos) == 1:
        cabecalho = "1 aviso, que não recusa o livro:"
    else:
        cabecalho = f"{len(avisos)} avisos, que não recusam o livro:"
    return [cabecalho, *(f"  {a.id}: {a.motivo}" for a in avisos)]


def _traduzir(opcoes: _Opcoes) -> tuple[str, int]:
    return _resumo_da_traducao(traduzir(opcoes.trabalho, opcoes.palavras), opcoes.trabalho), 0


def _adaptar(opcoes: _Opcoes) -> tuple[str, int]:
    return _resumo_da_adaptacao(adaptar(opcoes.trabalho, opcoes.palavras), opcoes.trabalho), 0


def _montar(opcoes: _Opcoes) -> tuple[str, int]:
    pasta, modo = opcoes.trabalho, opcoes.modo
    feito = montagem.montar(pasta, opcoes.saida or montagem.epub_padrao(pasta, modo), modo)
    resumo = (
        f"Montado em {feito.epub}: {feito.capitulos} capítulos, {feito.segmentos} segmentos "
        f"({feito.notas} notas levadas para o fim do capítulo)."
    )
    return resumo + _resumo_da_amostra(feito), 0


def _minuto(opcoes: _Opcoes) -> tuple[str, int]:
    linhas = [
        (
            f"{p.id}: minuto {p.minuto_no_livro} do livro; minuto {p.minuto_no_capitulo}"
            f" do capítulo {p.capitulo}"
        )
        for p in minutos(opcoes.trabalho, opcoes.ids or [])
    ]
    return "\n".join(linhas), 0


def _resumo_da_amostra(feito: montagem.Montagem) -> str:
    partes: list[str] = []
    if feito.fora:
        sem = "sem adaptação" if feito.adaptado else "sem tradução"
        partes.append(f"{feito.fora} {sem} ficaram de fora")
    if feito.no_original == 1:
        partes.append("1 item do sumário ficou no original")
    elif feito.no_original:
        partes.append(f"{feito.no_original} itens do sumário ficaram no original")
    return f" Amostra: {'; '.join(partes)}." if partes else ""


_COMANDOS: dict[str, Callable[[_Opcoes], tuple[str, int]]] = {
    "preparar": _preparar,
    "importar-pdf": _importar,
    "traduzir": _traduzir,
    "adaptar": _adaptar,
    "conferir": _conferir,
    "montar": _montar,
    "minuto": _minuto,
}


def _analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(prog="earbook")
    comandos = analisador.add_subparsers(dest="comando", required=True)
    preparo = comandos.add_parser("preparar", help="EPUB → pasta de trabalho com segmentos")
    _ = preparo.add_argument("epub", type=Path)
    _ = preparo.add_argument("--pasta", type=Path, help="padrão: ao lado do EPUB, com .earbook")
    importacao = comandos.add_parser("importar-pdf", help="PDF com texto → EPUB para o preparar")
    _ = importacao.add_argument("pdf", type=Path)
    _ = importacao.add_argument(
        "--epub", dest="saida", type=Path, help="padrão: ao lado do PDF, com .epub"
    )
    _ = importacao.add_argument("--idioma", default="und", help="pt-BR, en... (padrão: und)")
    _ = importacao.add_argument(
        "--titulo", help="padrão: o do metadado do PDF ou o nome do arquivo"
    )
    _ = importacao.add_argument("--autor", help="padrão: o do metadado do PDF")
    ajuda = "exporta em lotes o que o Claude Code traduz (ADR-0006)"
    _por_lote(comandos.add_parser("traduzir", help=ajuda))
    ajuda = "exporta em lotes o que o Claude Code adapta para o ouvido (ADR-0009)"
    _por_lote(comandos.add_parser("adaptar", help=ajuda))
    conferencia = comandos.add_parser("conferir", help="confere se nada some antes de montar")
    _ = conferencia.add_argument("trabalho", type=Path, help="a pasta .earbook")
    _ = conferencia.add_argument("--capitulo", help="só os problemas deste capítulo (cNNN)")
    _modos(conferencia)
    montagem_ = comandos.add_parser("montar", help="pasta de trabalho → EPUB para ouvir")
    _ = montagem_.add_argument("trabalho", type=Path, help="a pasta .earbook")
    _modos(montagem_)
    _ = montagem_.add_argument(
        "--epub", dest="saida", type=Path, help="padrão: ao lado da pasta, com .pronto.epub"
    )
    minuto = comandos.add_parser("minuto", help="em que minuto da escuta cai cada segmento")
    _ = minuto.add_argument("trabalho", type=Path, help="a pasta .earbook")
    _ = minuto.add_argument("ids", nargs="+", help="IDs de segmento (cNNN-sNNNN)")
    return analisador


def _por_lote(comando: argparse.ArgumentParser) -> None:
    """O `traduzir` e o `adaptar`: a pasta e o tamanho do lote."""
    _ = comando.add_argument("trabalho", type=Path, help="a pasta .earbook")
    _ = comando.add_argument(
        "--palavras",
        type=int,
        default=PALAVRAS_POR_LOTE,
        help=f"palavras por lote (padrão: {PALAVRAS_POR_LOTE})",
    )


def _modos(comando: argparse.ArgumentParser) -> None:
    """Só para o livro que precisa de tradução (ADR-0006)."""
    modos = comando.add_mutually_exclusive_group()
    _ = modos.add_argument(
        "--amostra",
        dest="modo",
        action="store_const",
        const=Modo.AMOSTRA,
        help="só o que já foi traduzido; o resto fica de fora",
    )
    _ = modos.add_argument(
        "--original",
        dest="modo",
        action="store_const",
        const=Modo.ORIGINAL,
        help="o texto limpo no idioma do original, para ouvir a limpeza",
    )


def _resumo_da_traducao(exportacao: Exportacao, pasta: Path) -> str:
    """O que a sessão do Claude Code precisa para distribuir os lotes (ADR-0006)."""
    capitulos = exportacao.capitulos
    total = sum(c.segmentos for c in capitulos)
    feitos = sum(c.traduzidos for c in capitulos)
    linhas = [
        f"{pasta}: {feitos} de {total} segmentos traduzidos, em {len(capitulos)} capítulos.",
        f"{exportacao.novos} lotes novos pedidos em {exportacao.pedidos}.",
        *_linhas_dos_capitulos(exportacao),
        (
            f'Resposta de cada lote: {exportacao.resposta}, lista de {{"id", "texto"}}'
            " com os IDs do pedido."
        ),
        (
            f"Glossário: {exportacao.glossario} ({exportacao.candidatos} candidatos a nome"
            f" em {exportacao.nomes})."
        ),
        f"Decisões do livro, que todo tradutor lê: {exportacao.decisoes}",
        f"Depois: earbook conferir {pasta}",
    ]
    return "\n".join(linhas)


def _resumo_da_adaptacao(exportacao: ExportacaoDaAdaptacao, pasta: Path) -> str:
    """O que a sessão do Claude Code precisa para distribuir os lotes (ADR-0009)."""
    capitulos = exportacao.capitulos
    total = sum(c.segmentos for c in capitulos)
    feitos = sum(c.adaptados for c in capitulos)
    linhas = [
        f"{pasta}: {feitos} de {total} segmentos adaptados, em {len(capitulos)} capítulos.",
        f"{exportacao.novos} lotes novos pedidos em {exportacao.pedidos}.",
        *(
            f"  {c.capitulo}: {c.adaptados} de {c.segmentos}"
            + _pendentes(c.pendentes, exportacao.palavras_pendentes[c.capitulo])
            for c in capitulos
        ),
        (
            f'Resposta de cada lote: {exportacao.resposta}, lista de grupos {{"fontes", e'
            ' "texto", "igual" ou "descarte"}.'
        ),
        (
            f"Glossário das siglas: {exportacao.glossario} ({exportacao.siglas} siglas fora do"
            f" glossário em {exportacao.caminho_das_siglas})."
        ),
        f"Decisões do livro, que todo adaptador lê: {exportacao.decisoes}",
        f"Depois: earbook conferir {pasta}",
    ]
    return "\n".join(linhas)


def _pendentes(lotes: tuple[str, ...], palavras: int) -> str:
    return f"; pendentes: {', '.join(lotes)} ({palavras} palavras)" if lotes else ""


def _linhas_dos_capitulos(exportacao: Exportacao) -> list[str]:
    linhas: list[str] = []
    for c in exportacao.capitulos:
        pendentes = ""
        if c.pendentes:
            palavras = exportacao.palavras_pendentes[c.capitulo]
            pendentes = f"; pendentes: {', '.join(c.pendentes)} ({palavras} palavras)"
        linhas.append(f"  {c.capitulo}: {c.traduzidos} de {c.segmentos}{pendentes}")
    return linhas


def _resumo_da_importacao(importacao: Importacao) -> str:
    livro = importacao.livro
    tipos = Counter(b.tipo for b in livro.blocos)
    paginas, capitulos = importacao.paginas, importacao.capitulos
    linhas = [f"Importado em {importacao.epub}: {paginas} páginas, {capitulos} capítulos."]
    de = f", de {importacao.autor}" if importacao.autor else ", sem autor"
    linhas.append(f"Título: {importacao.titulo}{de}.")
    titulos, paragrafos = tipos[TipoDeBloco.TITULO], tipos[TipoDeBloco.PARAGRAFO]
    codigo, notas = tipos[TipoDeBloco.CODIGO], tipos[TipoDeBloco.NOTA]
    linhas.append(
        f"Blocos: {titulos} títulos, {paragrafos} parágrafos, {codigo} de código, {notas} notas."
    )
    tiradas = len(importacao.remocoes)
    linhas.append(
        f"{tiradas} linhas tiradas da página: a borda, o texto escondido e o texto repetido."
    )
    motivos = Counter(r.motivo for r in importacao.remocoes)
    linhas += [f"  {motivo}: {n}" for motivo, n in motivos.most_common()]
    tirados, mantidos = livro.hifens_tirados, livro.hifens_mantidos
    linhas.append(f"Hífen de fim de linha: {tirados} tirados, {mantidos} mantidos.")
    linhas.append(f"Próximo passo: earbook preparar {importacao.epub}")
    return "\n".join(linhas)


def _resumo(preparo: Preparo, pasta: Path) -> str:
    livro = preparo.livro
    segmentos = sum(c.segmentos for c in livro.capitulos)
    fora = livro.texto_fora_de_segmento
    linhas = [
        f"Preparado em {pasta}: {len(livro.capitulos)} capítulos, {segmentos} segmentos.",
        f"{len(fora)} {'trecho' if len(fora) == 1 else 'trechos'} fora de segmento.",
    ]
    linhas += [f"  {t.capitulo}: {t.texto}" for t in fora[:EXEMPLOS_DE_TEXTO_FORA]]
    if len(fora) > EXEMPLOS_DE_TEXTO_FORA:
        linhas.append(f"  ... a lista completa está em {pasta / 'livro.json'}")
    linhas += _linhas_da_limpeza(preparo.limpeza, pasta)
    return "\n".join(linhas + _linhas_dos_ignorados(livro))


def _linhas_da_limpeza(limpeza: LivroLimpo, pasta: Path) -> list[str]:
    """Agrupadas por motivo: um livro tem centenas de cabeçalhos, e a lista mora no registro."""
    total = len(limpeza.remocoes)
    linhas = [f"{total} segmentos removidos na limpeza (registro em {pasta / 'limpeza.json'})."]
    motivos = Counter(r.motivo for r in limpeza.remocoes)
    linhas += [f"  {motivo}: {n}" for motivo, n in motivos.most_common()]
    if limpeza.aparos:
        aparos = len(limpeza.aparos)
        plural = "cabeçalho colado aparado" if aparos == 1 else "cabeçalhos colados aparados"
        linhas.append(f"{aparos} {plural} do fim de parágrafo.")
    if limpeza.juncoes:
        juncoes = len(limpeza.juncoes)
        plural = "parágrafo partido" if juncoes == 1 else "parágrafos partidos"
        linhas.append(
            f"{juncoes} {plural} na quebra de página {'juntado' if juncoes == 1 else 'juntados'}."
        )
    if capitulares := len(limpeza.capitulares):
        plural = (
            "capitular deslocada devolvida"
            if capitulares == 1
            else "capitulares deslocadas devolvidas"
        )
        linhas.append(f"{capitulares} {plural} ao começo do capítulo.")
    if limpeza.suspeitas:
        suspeitas = len(limpeza.suspeitas)
        linhas.append(f"{suspeitas} segmentos suspeitos ficaram no texto (decidir no registro).")
        por_motivo = Counter(s.motivo for s in limpeza.suspeitas)
        linhas += [f"  {motivo}: {n}" for motivo, n in por_motivo.most_common()]
    return linhas


def _linhas_dos_ignorados(livro: LivroPreparado) -> list[str]:
    """Todos, sem corte: cada um pode ser um capítulo inteiro fora do áudio."""
    ignorados = livro.itens_do_spine_ignorados
    if not ignorados:
        return []
    plural = "item do spine ignorado" if len(ignorados) == 1 else "itens do spine ignorados"
    return [f"{len(ignorados)} {plural}:"] + [f"  {i.idref}: {i.motivo}" for i in ignorados]
