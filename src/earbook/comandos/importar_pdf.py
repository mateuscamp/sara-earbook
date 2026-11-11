# SPDX-License-Identifier: GPL-3.0-or-later
"""Comando `importar-pdf`: PDF → EPUB simples, pronto para o `preparar` (ADR-0004)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from earbook.adaptadores.epub_simples import gravar_epub
from earbook.adaptadores.pdf import ler_metadados, ler_paginas
from earbook.dominio.blocos import LivroMontado, montar_blocos
from earbook.dominio.capitulos import dividir_em_capitulos
from earbook.dominio.metadados import autor_do_livro, titulo_do_livro
from earbook.dominio.pagina import Pagina
from earbook.dominio.paginacao import LinhaRemovida, tirar_cabecalhos_e_rodapes
from earbook.dominio.paginas_de_lista import (
    MOTIVO_DAS_REMISSOES,
    MOTIVO_DOS_COLABORADORES,
    tirar_paginas_de_lista,
)
from earbook.dominio.tabelas_e_figuras import (
    MOTIVO_DA_FIGURA,
    MOTIVO_DA_TABELA,
    tirar_tabelas_e_figuras,
)
from earbook.dominio.texto_escondido import tirar_texto_escondido
from earbook.dominio.tipo_da_linha import TipoDeBloco

MOTIVO_DA_CHAMADA = "número de referência sobrescrito"
MOTIVOS_DO_CONTEUDO = frozenset(
    {MOTIVO_DAS_REMISSOES, MOTIVO_DOS_COLABORADORES, MOTIVO_DA_TABELA, MOTIVO_DA_FIGURA}
)
"""O que sai pelo que o livro diz, e não pela borda da página: o resumo os conta à parte."""


class PdfSemTextoError(ValueError):
    pass


@dataclass(frozen=True)
class Importacao:
    epub: Path
    paginas: int
    remocoes: tuple[LinhaRemovida, ...]
    livro: LivroMontado
    capitulos: int
    titulo: str
    autor: str
    chamadas: tuple[LinhaRemovida, ...] = ()


def epub_padrao(pdf: Path) -> Path:
    """`epub_padrao(Path("Duna.pdf"))` → `Path("Duna.epub")`."""
    return pdf.with_suffix(".epub")


def importar_pdf(
    pdf: Path,
    epub: Path,
    idioma: str = "und",
    titulo: str | None = None,
    autor: str | None = None,
) -> Importacao:
    """Lê o PDF, tira cabeçalho e rodapé, monta parágrafos e grava o EPUB em `epub`.

    Título e autor vêm de `titulo` e `autor`, se dados; senão, do metadado do PDF, que os
    dois livros medidos trazem certos; o título que parece nome de arquivo ("Microsoft
    Word - cap1.doc") cede ao nome do PDF (`dominio/metadados.py`).
    """
    if epub.exists():
        # A gravação também recusa; checar antes poupa os minutos de leitura do PDF.
        mensagem = f"{epub} já existe"
        raise FileExistsError(mensagem)
    paginas = ler_paginas(pdf)
    # O texto escondido sai antes da borda: em letra de título, ele contaria no corpo e na
    # paginação (ADR-0004, "O que ficou da Fase 1").
    visiveis = tirar_texto_escondido(paginas)
    limpas = tirar_cabecalhos_e_rodapes(visiveis.paginas)
    # Depois da borda, que não conta como lista; antes da tabela, porque a letra do corpo se mede
    # sem o índice escaneado (ADR-0004, "Páginas de lista" e "Tabela e figura pela letra").
    listas = tirar_paginas_de_lista(limpas.paginas)
    sem_tabelas = tirar_tabelas_e_figuras(listas.paginas)
    livro = montar_blocos(sem_tabelas.paginas, prova_do_hifen=limpas.paginas)
    if not livro.blocos:
        mensagem = f"{pdf}: nenhum texto nas {len(paginas)} páginas (escaneado? não há OCR)"
        raise PdfSemTextoError(mensagem)
    capitulos = dividir_em_capitulos(livro.blocos)
    metadados = ler_metadados(pdf)
    titulo = titulo or titulo_do_livro(metadados.titulo, pdf.stem)
    autor = autor or autor_do_livro(metadados.autor)
    gravar_epub(epub, titulo, idioma, capitulos, autor=autor)
    remocoes = (*visiveis.remocoes, *limpas.remocoes, *listas.remocoes, *sem_tabelas.remocoes)
    chamadas = _chamadas(paginas)
    return Importacao(epub, len(paginas), remocoes, livro, len(capitulos), titulo, autor, chamadas)


def _chamadas(paginas: Sequence[Pagina]) -> tuple[LinhaRemovida, ...]:
    """Cada número de referência sobrescrito que o adaptador tirou, com a página (ADR-0004,
    "Número de referência e espaço falso")."""
    return tuple(
        LinhaRemovida(pagina.numero, MOTIVO_DA_CHAMADA, chamada)
        for pagina in paginas
        for linha in pagina.linhas
        for chamada in linha.chamadas
    )


def resumo_da_importacao(importacao: Importacao) -> str:
    """O resumo que o `importar-pdf` mostra: os blocos, o que saiu e por quê."""
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
    da_borda = [r for r in importacao.remocoes if r.motivo not in MOTIVOS_DO_CONTEUDO]
    do_conteudo = [r for r in importacao.remocoes if r.motivo in MOTIVOS_DO_CONTEUDO]
    linhas.append(
        f"{len(da_borda)} linhas tiradas da página: a borda, o texto escondido e o texto repetido."
    )
    linhas += _por_motivo(da_borda)
    # A tabela, a figura e a página de lista (ADR-0004): o que o livro diz, e não a página.
    linhas.append(f"{len(do_conteudo)} linhas de tabela, figura e página de lista tiradas.")
    linhas += _por_motivo(do_conteudo)
    chamadas = len(importacao.chamadas)
    plural = (
        "número de referência sobrescrito tirado"
        if chamadas == 1
        else ("números de referência sobrescritos tirados")
    )
    linhas.append(f"{chamadas} {plural}.")
    tirados, mantidos = livro.hifens_tirados, livro.hifens_mantidos
    linhas.append(f"Hífen de fim de linha: {tirados} tirados, {mantidos} mantidos.")
    linhas.append(f"Próximo passo: earbook preparar {importacao.epub}")
    return "\n".join(linhas)


def _por_motivo(remocoes: list[LinhaRemovida]) -> list[str]:
    motivos = Counter(r.motivo for r in remocoes)
    return [f"  {motivo}: {n}" for motivo, n in motivos.most_common()]
