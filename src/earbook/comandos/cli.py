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
from earbook.comandos.importar_pdf import Importacao, epub_padrao, importar_pdf
from earbook.comandos.preparar import Preparo, pasta_padrao, preparar
from earbook.dominio.blocos import TipoDeBloco
from earbook.dominio.limpeza import LivroLimpo
from earbook.dominio.trabalho import LivroPreparado

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
    problemas = montagem.conferir_pasta(pasta)
    if not problemas:
        return f"{pasta}: nada faltando, sobrando ou repetido; pode montar.", 0
    linhas = [f"{pasta}: {len(problemas)} problemas; o montar recusaria o livro."]
    linhas += [f"  {p.id}: {p.motivo}" for p in problemas[:PROBLEMAS_LISTADOS]]
    if len(problemas) > PROBLEMAS_LISTADOS:
        linhas.append(f"  ... e mais {len(problemas) - PROBLEMAS_LISTADOS}")
    return "\n".join(linhas), 1


def _montar(opcoes: _Opcoes) -> tuple[str, int]:
    pasta = opcoes.trabalho
    feito = montagem.montar(pasta, opcoes.saida or montagem.epub_padrao(pasta))
    resumo = (
        f"Montado em {feito.epub}: {feito.capitulos} capítulos, {feito.segmentos} segmentos "
        f"({feito.notas} notas levadas para o fim do capítulo)."
    )
    return resumo, 0


_COMANDOS: dict[str, Callable[[_Opcoes], tuple[str, int]]] = {
    "preparar": _preparar,
    "importar-pdf": _importar,
    "conferir": _conferir,
    "montar": _montar,
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
    conferencia = comandos.add_parser("conferir", help="confere se nada some antes de montar")
    _ = conferencia.add_argument("trabalho", type=Path, help="a pasta .earbook")
    montagem_ = comandos.add_parser("montar", help="pasta de trabalho → EPUB para ouvir")
    _ = montagem_.add_argument("trabalho", type=Path, help="a pasta .earbook")
    _ = montagem_.add_argument(
        "--epub", dest="saida", type=Path, help="padrão: ao lado da pasta, com .pronto.epub"
    )
    return analisador


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
    linhas.append(f"{len(importacao.remocoes)} linhas tiradas da borda da página.")
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
