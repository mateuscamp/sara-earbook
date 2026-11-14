# SPDX-License-Identifier: GPL-3.0-or-later
"""Comando `importar-pdf`: PDF → EPUB simples, pronto para o `preparar` (ADR-0004)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from earbook.adaptadores.epub_simples import gravar_epub
from earbook.adaptadores.pdf import ler_metadados, ler_paginas, ler_sumario
from earbook.dominio.bibliografia_do_pdf import MOTIVO_DA_BIBLIOGRAFIA_DO_PDF, tirar_bibliografia
from earbook.dominio.blocos import Bloco, LivroMontado, montar_blocos
from earbook.dominio.caixa_do_rotulo import acertar_rotulos
from earbook.dominio.camada_do_ocr import tirar_camada_do_ocr
from earbook.dominio.capitulos import dividir_em_capitulos, dividir_pelo_sumario
from earbook.dominio.hifen_da_quebra import mostrar_hifen_invisivel
from earbook.dominio.metadados import autor_do_livro, titulo_do_livro
from earbook.dominio.pagina import Pagina
from earbook.dominio.paginacao import LinhaRemovida, tirar_cabecalhos_e_rodapes
from earbook.dominio.paginas_de_lista import (
    MOTIVO_DAS_REMISSOES,
    MOTIVO_DO_SUMARIO,
    MOTIVO_DOS_COLABORADORES,
    tirar_paginas_de_lista,
)
from earbook.dominio.sumario_interno import aberturas_de_capitulo
from earbook.dominio.tabelas_e_figuras import (
    MOTIVO_DA_FIGURA,
    MOTIVO_DA_TABELA,
    MOTIVO_DO_TEXTO_GIRADO,
    tirar_tabelas_e_figuras,
    tirar_texto_girado,
)
from earbook.dominio.texto_escondido import tirar_texto_escondido
from earbook.dominio.tipo_da_linha import TipoDeBloco

MOTIVO_DA_CHAMADA = "número de referência sobrescrito"
MOTIVOS_DO_CONTEUDO = frozenset(
    {
        MOTIVO_DAS_REMISSOES,
        MOTIVO_DO_SUMARIO,
        MOTIVO_DOS_COLABORADORES,
        MOTIVO_DA_TABELA,
        MOTIVO_DA_FIGURA,
        MOTIVO_DO_TEXTO_GIRADO,
    }
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
    rotulos_acertados: int = 0
    """As palavras de rótulo que voltaram à caixa normal nas menções ("QuAdro 13.1")."""


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
    limpas = _limpar(paginas)
    livro, rotulos = _montar_o_livro(pdf, limpas, len(paginas))
    capitulos = _dividir(pdf, livro)
    metadados = ler_metadados(pdf)
    titulo = titulo or titulo_do_livro(metadados.titulo, pdf.stem)
    autor = autor or autor_do_livro(metadados.autor)
    gravar_epub(epub, titulo, idioma, capitulos, autor=autor)
    remocoes, chamadas = limpas.remocoes, _chamadas(paginas)
    feito = Importacao(epub, len(paginas), remocoes, livro, len(capitulos), titulo, autor, chamadas)
    return replace(feito, rotulos_acertados=rotulos)


def _montar_o_livro(
    pdf: Path, limpas: _PaginasParaOsBlocos, paginas: int
) -> tuple[LivroMontado, int]:
    """Os blocos do livro, com a palavra de rótulo de caixa trocada acertada, e quantas foram: o
    versalete que troca a caixa ("QuAdro 13.1"), só nas menções (ADR-0004, "Bibliografia pela
    letra e rótulo com a caixa trocada")."""
    livro = montar_blocos(limpas.paginas, prova_do_hifen=limpas.prova_do_hifen)
    if not livro.blocos:
        mensagem = f"{pdf}: nenhum texto nas {paginas} páginas (escaneado? não há OCR)"
        raise PdfSemTextoError(mensagem)
    blocos, rotulos = acertar_rotulos(livro.blocos)
    return replace(livro, blocos=blocos), rotulos


def _dividir(pdf: Path, livro: LivroMontado) -> tuple[tuple[Bloco, ...], ...]:
    """Os capítulos pelo sumário interno do PDF, se ele serve, com o nome que ele dá a cada um;
    senão, pelo tamanho e pelo rótulo dos títulos (ADR-0004, "Capítulos pelo sumário interno do
    PDF")."""
    aberturas = aberturas_de_capitulo(ler_sumario(pdf))
    if aberturas:
        return dividir_pelo_sumario(livro.blocos, aberturas).com_o_nome_no_primeiro_bloco()
    return dividir_em_capitulos(livro.blocos)


@dataclass(frozen=True)
class _PaginasParaOsBlocos:
    paginas: tuple[Pagina, ...]
    prova_do_hifen: tuple[Pagina, ...]
    """As páginas antes da lista e da tabela: o dicionário do hífen vem delas (ADR-0004)."""
    remocoes: tuple[LinhaRemovida, ...]


def _limpar(paginas: Sequence[Pagina]) -> _PaginasParaOsBlocos:
    """O que sai da página antes dos blocos, na ordem, e o registro de cada remoção."""
    # Antes de tudo: o hífen gravado como U+00AD volta a ser hífen, e o dicionário do hífen e as
    # regras de texto já o veem (ADR-0004, "Hífen invisível").
    # A camada do OCR sai primeiro: a letra de 82 pt que ninguém vê contaria como título, na
    # paginação e no texto escondido (ADR-0004, "Camada do OCR sobre as figuras").
    pintadas = tirar_camada_do_ocr(mostrar_hifen_invisivel(paginas))
    # O texto escondido sai antes da borda: em letra de título, ele contaria no corpo e na
    # paginação (ADR-0004, "O que ficou da Fase 1").
    visiveis = tirar_texto_escondido(pintadas.paginas)
    # O texto girado também: a letra solta da tabela deitada contaria na paginação (ADR-0004,
    # "Texto girado").
    de_pe = tirar_texto_girado(visiveis.paginas)
    sem_borda = tirar_cabecalhos_e_rodapes(de_pe.paginas)
    # Depois da borda, que não conta como lista; antes da tabela, porque a letra do corpo se mede
    # sem o índice escaneado (ADR-0004, "Páginas de lista" e "Tabela e figura pela letra").
    listas = tirar_paginas_de_lista(sem_borda.paginas)
    sem_tabelas = tirar_tabelas_e_figuras(listas.paginas)
    # Depois da tabela, que tem a letra da lista no Manica; antes dos blocos, para a ordem de
    # leitura não intercalar a lista com a prosa (ADR-0004, "Bibliografia pela letra").
    sem_bibliografia = tirar_bibliografia(sem_tabelas.paginas)
    remocoes = (
        *pintadas.remocoes,
        *visiveis.remocoes,
        *de_pe.remocoes,
        *sem_borda.remocoes,
        *listas.remocoes,
        *sem_tabelas.remocoes,
        *sem_bibliografia.remocoes,
    )
    return _PaginasParaOsBlocos(sem_bibliografia.paginas, sem_borda.paginas, remocoes)


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
    linhas += _linhas_do_que_saiu(importacao.remocoes)
    chamadas = len(importacao.chamadas)
    plural = (
        "número de referência sobrescrito tirado"
        if chamadas == 1
        else ("números de referência sobrescritos tirados")
    )
    linhas.append(f"{chamadas} {plural}.")
    tirados, mantidos = livro.hifens_tirados, livro.hifens_mantidos
    linhas.append(f"Hífen de fim de linha: {tirados} tirados, {mantidos} mantidos.")
    if rotulos := importacao.rotulos_acertados:
        plural = "palavra" if rotulos == 1 else "palavras"
        linhas.append(
            f"{rotulos} {plural} de rótulo com a caixa acertada (Figura, Quadro, Tabela)."
        )
    linhas.append(f"Próximo passo: earbook preparar {importacao.epub}")
    return "\n".join(linhas)


def _linhas_do_que_saiu(remocoes: Sequence[LinhaRemovida]) -> list[str]:
    """A borda, o conteúdo (tabela, figura e página de lista) e a bibliografia, cada um na sua
    conta; a da bibliografia só aparece no livro que a tem."""
    bibliografia = [r for r in remocoes if r.motivo == MOTIVO_DA_BIBLIOGRAFIA_DO_PDF]
    do_conteudo = [r for r in remocoes if r.motivo in MOTIVOS_DO_CONTEUDO]
    fora_da_borda = MOTIVOS_DO_CONTEUDO | {MOTIVO_DA_BIBLIOGRAFIA_DO_PDF}
    da_borda = [r for r in remocoes if r.motivo not in fora_da_borda]
    linhas = [
        f"{len(da_borda)} linhas tiradas da página: a borda, o texto escondido e o texto repetido."
    ]
    linhas += _por_motivo(da_borda)
    # A tabela, a figura e a página de lista (ADR-0004): o que o livro diz, e não a página.
    linhas.append(f"{len(do_conteudo)} linhas de tabela, figura e página de lista tiradas.")
    linhas += _por_motivo(do_conteudo)
    if bibliografia:
        motivo = "letra menor que a do corpo, com citações de periódico"
        linhas.append(f"{len(bibliografia)} linhas de bibliografia tiradas: {motivo}.")
    return linhas


def _por_motivo(remocoes: list[LinhaRemovida]) -> list[str]:
    motivos = Counter(r.motivo for r in remocoes)
    return [f"  {motivo}: {n}" for motivo, n in motivos.most_common()]
