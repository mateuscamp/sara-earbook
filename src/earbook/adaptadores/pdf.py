# SPDX-License-Identifier: GPL-3.0-or-later
"""Lê o PDF com o pdfminer.six e devolve páginas do domínio (ADR-0004).

É o único módulo que importa a biblioteca de PDF.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import BinaryIO, override

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTAnno, LTChar, LTPage, LTTextBox, LTTextLine
from pdfminer.pdfcolor import PDFColorSpace
from pdfminer.pdfdevice import PDFTextSeq
from pdfminer.pdfdocument import PDFDocument, PDFEncryptionError
from pdfminer.pdfinterp import (
    PDFGraphicState,
    PDFPageInterpreter,
    PDFResourceManager,
    PDFTextState,
)
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import PDFObjRef
from pdfminer.utils import decode_text

from earbook.adaptadores.sumario_do_pdf import itens_do_sumario
from earbook.dominio import nome_da_fonte
from earbook.dominio.caracteres import (
    Caractere,
    espacos_no_lugar,
    lido,
    pagina_usa_chamadas,
    tamanho_da_linha,
    texto_da_linha,
)
from earbook.dominio.pagina import Linha, Pagina, em_versalete
from earbook.dominio.segmento import normalizar_espacos
from earbook.dominio.sumario_interno import ItemDoSumario

_MODO_SEM_TINTA = 3
"""O modo de pintura do PDF em que a letra nem se preenche nem se contorna (`3 Tr`): a camada que
o OCR põe sobre a imagem (ADR-0004, "Camada do OCR sobre as figuras")."""
_BOM_UTF8 = b"\xef\xbb\xbf"
_BOM_UTF16LE = b"\xff\xfe"
_PASSOS_DA_REFERENCIA = 8
"""Quantas referências seguidas se seguem até um valor: no PDF bem formado, uma."""
_LOG = logging.getLogger(__name__)


class PdfInvalidoError(ValueError):
    pass


@dataclass(frozen=True)
class MetadadosDoPdf:
    titulo: str
    autor: str


def ler_metadados(pdf: Path) -> MetadadosDoPdf:
    """Título e autor do dicionário `/Info` do PDF, vazios quando ele não os tem.

    O valor vem cru do PDF (texto em PDFDocEncoding, UTF-16 ou UTF-8, ou referência a outro
    objeto): só texto passa, e o resto vira vazio.
    """
    with pdf.open("rb") as arquivo:
        info = _pelo_pdfminer(pdf, lambda: _info(PDFDocument(PDFParser(arquivo))))
        titulo = _pelo_pdfminer(pdf, lambda: _bytes_do_info(info, "Title"))
        autor = _pelo_pdfminer(pdf, lambda: _bytes_do_info(info, "Author"))
    # Fora do `try`: a decodificação é nossa, e bug nosso não é PDF inválido (N2 da
    # pós-auditoria).
    return MetadadosDoPdf(_decodificar(titulo), _decodificar(autor))


def _info(documento: PDFDocument) -> list[dict[str, object]]:
    return documento.info  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]  # motivo: o pdfminer não tipa o `info`; cada valor é validado em `_texto_do_info`


def _bytes_do_info(info: list[dict[str, object]], chave: str) -> bytes:
    """O valor cru de `chave`, seguindo uma referência só: o `resolve1` do pdfminer segue
    sem limite, e um objeto que aponta para si mesmo travava o importar-pdf (N1 da
    pós-auditoria). Referência de referência, ou o que não é texto, vira vazio."""
    for dicionario in info:
        valor = dicionario.get(chave)
        if isinstance(valor, PDFObjRef):
            valor = valor.resolve()  # pyright: ignore[reportAny]  # motivo: o pdfminer devolve Any; o isinstance a seguir valida
        if isinstance(valor, bytes):
            return valor
    return b""


def _decodificar(valor: bytes) -> str:
    """O texto do `/Info`: PDFDocEncoding ou UTF-16BE com BOM, pelo pdfminer; UTF-8 com BOM,
    que o PDF 2.0 aceita (revisão); e UTF-16LE com BOM, fora da especificação mas visto
    (A3 da auditoria). O `decode_text` do pdfminer só conhece o UTF-16BE."""
    for bom, codificacao in ((_BOM_UTF8, "utf-8"), (_BOM_UTF16LE, "utf-16-le")):
        if valor.startswith(bom):
            return valor[len(bom) :].decode(codificacao, errors="replace")
    return decode_text(valor)


def ler_sumario(pdf: Path) -> tuple[ItemDoSumario, ...]:
    """O sumário interno do PDF (os marcadores), com o nível, o título e a página de cada item;
    vazio se o PDF não o tem ou se ele não se deixa ler (ADR-0004, "Capítulos pelo sumário
    interno do PDF").

    O sumário é opcional: a falha ao abri-lo vira aviso e sumário vazio, e não derruba a
    importação de um livro cujas páginas se leem. O percurso é de `adaptadores/sumario_do_pdf.py`,
    com passos contados, e não o `get_outlines` do pdfminer, que segue referência sem limite.
    """
    with pdf.open("rb") as arquivo:
        try:
            documento = _pelo_pdfminer(pdf, lambda: PDFDocument(PDFParser(arquivo)))
            numeros = _pelo_pdfminer(pdf, lambda: _numeros_das_paginas(documento))
        except PdfInvalidoError as erro:
            _LOG.warning("o sumário interno não pôde ser lido e foi ignorado: %s", erro)
            return ()
        return itens_do_sumario(documento.catalog, _Leitor(pdf), numeros)


def _numeros_das_paginas(documento: PDFDocument) -> dict[int, int]:
    """O número de cada página (a partir de 1) pelo identificador do objeto dela no PDF."""
    numeros: dict[int, int] = {}
    for numero, pagina in enumerate(PDFPage.create_pages(documento), 1):
        # O pdfminer tipa o identificador como objeto: só o inteiro serve de chave.
        if isinstance(pagina.pageid, int):
            numeros[pagina.pageid] = numero
    return numeros


@dataclass(frozen=True)
class _Leitor:
    """O que o percurso do sumário precisa do pdfminer (`sumario_do_pdf.Leitor`)."""

    pdf: Path

    def seguir(self, valor: object) -> object:
        """Segue a referência por um número fixo de passos, sem o `resolve1` do pdfminer, que não
        tem limite (N1 da pós-auditoria): a que aponta para si mesma, para um objeto que não
        existe ou para um que o pdfminer não consegue ler vira None."""
        for _ in range(_PASSOS_DA_REFERENCIA):
            if not isinstance(valor, PDFObjRef):
                return valor
            try:
                valor = _pelo_pdfminer(self.pdf, valor.resolve)  # pyright: ignore[reportAny]  # motivo: o pdfminer devolve Any; quem chama valida com isinstance
            except PdfInvalidoError:
                return None
        return None

    def objeto(self, valor: object) -> int | None:
        return valor.objid if isinstance(valor, PDFObjRef) else None

    def texto(self, valor: object) -> str:
        return _decodificar(valor) if isinstance(valor, bytes) else ""


class _Agregador(PDFPageAggregator):
    """O agregador de página do pdfminer, que também lembra o que a página não pinta.

    O pdfminer não entrega o modo de pintura na letra. Cada trecho escrito chega com uma cópia
    só dele do estado gráfico, e toda letra do trecho aponta para ela: guardar a cópia dos
    trechos escritos no modo 3 basta para reconhecer as letras (ADR-0004, "Camada do OCR sobre as
    figuras"). Guarda a cópia, e não só o `id` dela: o `id` de um objeto solto volta a ser usado.
    """

    def __init__(self, gerente: PDFResourceManager) -> None:
        super().__init__(gerente, laparams=LAParams())
        self._sem_tinta: dict[int, PDFGraphicState] = {}

    @override
    def render_string(
        self,
        textstate: PDFTextState,
        seq: PDFTextSeq,
        ncs: PDFColorSpace,
        graphicstate: PDFGraphicState,
    ) -> None:
        if textstate.render == _MODO_SEM_TINTA:
            self._sem_tinta[id(graphicstate)] = graphicstate
        super().render_string(textstate, seq, ncs, graphicstate)

    def nao_pinta(self, letra: LTChar) -> bool:
        return id(letra.graphicstate) in self._sem_tinta

    def esquecer(self) -> None:
        """Entre uma página e a seguinte: as letras da anterior já viraram `Linha`."""
        self._sem_tinta.clear()


def ler_paginas(pdf: Path) -> tuple[Pagina, ...]:
    """Uma `Pagina` por página do PDF, com as linhas de texto na ordem do pdfminer.

    Converte uma página por vez: guardar todos os layouts do pdfminer levava o
    Competente (503 páginas) a 720 MB de memória (A3 da auditoria).
    """
    # O arquivo abre fora do `try`: arquivo inexistente é OSError da máquina, enquanto o
    # OSError de dentro da leitura vem do conteúdo (F2: xref com deslocamento negativo).
    with pdf.open("rb") as arquivo:
        agregador = _pelo_pdfminer(pdf, lambda: _Agregador(PDFResourceManager()))
        layouts = layouts_das_paginas(arquivo, agregador)
        paginas: list[Pagina] = []
        while (layout := _proximo_layout(pdf, layouts)) is not None:
            paginas.append(_pagina(pdf, len(paginas) + 1, layout, agregador))
    return tuple(paginas)


def layouts_das_paginas(arquivo: BinaryIO, agregador: _Agregador) -> Iterator[LTPage]:
    """O laço do `extract_pages` do pdfminer, com o nosso agregador no lugar do dele: uma página
    por vez, com as opções padrão. Nada roda antes do primeiro `next`, que já está no `try`.

    É o ponto em que o teste da falta de memória troca a leitura (`tests/test_pdf.py`).
    """
    interpretador = PDFPageInterpreter(agregador.rsrcmgr, agregador)
    for pagina in PDFPage.get_pages(arquivo):
        agregador.esquecer()
        interpretador.process_page(pagina)
        yield agregador.get_result()


def _proximo_layout(pdf: Path, layouts: Iterator[LTPage]) -> LTPage | None:
    return _pelo_pdfminer(pdf, lambda: next(layouts, None))


def _pelo_pdfminer[T](pdf: Path, chamada: Callable[[], T]) -> T:
    """`chamada()`, com toda falha do pdfminer virando `PdfInvalidoError`.

    O `try` cobre só a biblioteca, não a nossa conversão: bug do adaptador continua
    aparecendo como bug, não como "PDF inválido" (revisão nº 1). Falta de memória é da
    máquina, não do PDF, e passa como veio.
    """
    try:
        return chamada()
    except MemoryError:
        raise
    except PDFEncryptionError as erro:
        mensagem = f"{pdf}: PDF protegido por senha ({type(erro).__name__})"
        raise PdfInvalidoError(mensagem) from erro
    # PDF é entrada hostil, e o pdfminer deixa escapar qualquer exceção (A2 e P1:
    # RecursionError, AttributeError, TypeError...). O `from` guarda a causa.
    except Exception as erro:
        mensagem = f"{pdf}: não é um PDF válido ({type(erro).__name__}: {erro})"
        raise PdfInvalidoError(mensagem) from erro


@dataclass(frozen=True)
class _LinhaLida:
    linha: Linha
    duvidosas: int
    """As chamadas duvidosas que ficaram no texto ("6 h¹⁴⁸"): saem se a página tem chamadas
    certas (ADR-0004, "Camada do OCR sobre as figuras e chamada colada")."""


def _pagina(pdf: Path, numero: int, layout: LTPage, agregador: _Agregador) -> Pagina:
    if layout.height <= 0:
        mensagem = f"{pdf}: a página {numero} tem altura {layout.height}"
        raise PdfInvalidoError(mensagem)
    # LTTextBox é tipado como contêiner de LTTextLine; o LTTextContainer genérico não.
    brutas = [linha for caixa in layout if isinstance(caixa, LTTextBox) for linha in caixa]
    lidas = [_linha(bruta, layout, agregador.nao_pinta) for bruta in brutas]
    # A página com chamadas certas prova as duvidosas: só as linhas que as têm são lidas de novo.
    # A chamada da linha fora da página não conta: ela sai do áudio.
    visiveis = [lida.linha for lida in lidas if lida is not None and not lida.linha.fora_da_pagina]
    if pagina_usa_chamadas(sum(len(linha.chamadas) for linha in visiveis)):
        lidas = [
            _linha(bruta, layout, agregador.nao_pinta, com_duvidosas=True)
            if lida is not None and lida.duvidosas
            else lida
            for bruta, lida in zip(brutas, lidas, strict=True)
        ]
    return Pagina(numero, tuple(lida.linha for lida in lidas if lida is not None))


def _linha(
    linha: LTTextLine,
    pagina: LTPage,
    nao_pinta: Callable[[LTChar], bool],
    *,
    com_duvidosas: bool = False,
) -> _LinhaLida | None:
    """A linha lida e, se ela abre em fonte de versalete e continua noutra, as duas partes
    (ADR-0004, "Subtítulo em versalete no começo do parágrafo")."""
    itens = list(linha)
    topo = 1 - linha.y1 / pagina.height
    lida = _trecho(itens, topo, pagina, nao_pinta, com_duvidosas=com_duvidosas)
    corte = nome_da_fonte.fim_da_abertura_em_versalete(
        (item.get_text(), item.fontname if isinstance(item, LTChar) else None) for item in itens
    )
    if lida is None or corte is None:
        return lida
    # O espaço entre a abertura e o resto não vai para nenhuma das duas.
    comeco = next((i for i in range(corte, len(itens)) if itens[i].get_text().strip()), corte)
    partes = tuple(
        parte.linha
        for pedaco in (itens[:corte], itens[comeco:])
        if (parte := _trecho(pedaco, topo, pagina, nao_pinta, com_duvidosas=com_duvidosas))
    )
    match partes:
        case (_, _):
            return replace(lida, linha=replace(lida.linha, partes=partes))
        case _:
            return lida


def _trecho(
    itens: Sequence[LTChar | LTAnno],
    topo: float,
    pagina: LTPage,
    nao_pinta: Callable[[LTChar], bool],
    *,
    com_duvidosas: bool,
) -> _LinhaLida | None:
    """A linha do domínio feita dos caracteres `itens`: a linha inteira ou uma parte dela."""
    caracteres = [c for c in itens if isinstance(c, LTChar)]
    if not caracteres or not normalizar_espacos("".join(item.get_text() for item in itens)):
        return None
    dela = _caracteres(itens)
    tamanho = tamanho_da_linha(dela)
    # A chamada sobrescrita e o espaço inventado saem aqui, onde o caractere ainda tem tamanho e
    # posição (ADR-0004, "Número de referência e espaço falso").
    lida = texto_da_linha(dela, tamanho, com_duvidosas=com_duvidosas)
    # Toda letra, não alguma: no Hard Parts, as 584 linhas de código são 100% monoespaçadas
    # e as 183 de prosa com um nome de código no meio ("ss.survey") ficam entre 0 e 90%.
    monoespacada = all(nome_da_fonte.monoespacada(c.fontname) for c in caracteres)
    texto = normalizar_espacos(lida.texto) if monoespacada else lido(lida, tamanho)
    x0, x1 = min(c.x0 for c in caracteres), max(c.x1 for c in caracteres)
    pronta = Linha(
        texto,
        x=x0,
        topo=topo,
        tamanho=tamanho,
        monoespacada=monoespacada,
        fim=x1,
        chamadas=lida.chamadas,
        letras_gregas=sum(_desenhada(c) != c.get_text() for c in caracteres),
        # Inteira além da borda do papel, que o leitor não mostra; a que passa da borda só em parte
        # fica (ADR-0004, "A ordem das colunas no Miller").
        fora_da_pagina=x1 <= pagina.x0 or x0 >= pagina.x1,
        espacos_inventados=lida.espacos_inventados(texto),
    )
    visiveis = [c for c in caracteres if c.get_text().strip()]
    return _LinhaLida(_com_a_letra(pronta, visiveis, nao_pinta), lida.duvidosas)


def _com_a_letra(
    linha: Linha, visiveis: list[LTChar], nao_pinta: Callable[[LTChar], bool]
) -> Linha:
    """A linha com o que as letras visíveis dizem, quando todas dizem o mesmo."""
    return replace(
        linha,
        # Toda letra visível, como na monoespaçada: a ênfase no meio da prosa (619 linhas no
        # Competente) não faz a linha negrito.
        negrito=all(nome_da_fonte.negrito(c.fontname) for c in visiveis),
        versalete=_versalete(visiveis, linha.tamanho),
        fonte=nome_da_fonte.familia(c.fontname for c in visiveis),
        fonte_do_versalete=nome_da_fonte.fonte_do_versalete(c.fontname for c in visiveis),
        # Toda letra visível, como no negrito. O `upright` do pdfminer é a matriz sem giro: a
        # itálica, que só inclina, continua de pé (ADR-0004, "Texto girado").
        girada=bool(visiveis) and not any(c.upright for c in visiveis),
        # Toda letra visível, como no negrito: a linha que mistura fica (ADR-0004, "Camada do OCR").
        nao_pintada=bool(visiveis) and all(nao_pinta(c) for c in visiveis),
    )


def _caracteres(itens: Sequence[LTChar | LTAnno]) -> list[Caractere]:
    """Os caracteres da linha para o domínio. O espaço do pdfminer (`LTAnno`) não tem posição:
    `espacos_no_lugar` a dá."""
    return espacos_no_lugar(_caractere(item) for item in itens)


def _caractere(item: LTChar | LTAnno) -> Caractere:
    if not isinstance(item, LTChar):
        return Caractere(item.get_text(), 0.0, 0.0, 0.0, 0.0, virtual=True)
    # O pé da caixa, e não a matriz: a subida do `Ts` só entra na caixa (pdfminer).
    # A letra da fonte de símbolo é a grega que ela desenha (ADR-0004, "Letra grega da fonte
    # de símbolo"). A fonte de cada letra serve à letra larga (ADR-0004, "Romance convertido pelo
    # Calibre").
    fonte = nome_da_fonte.sem_subconjunto(item.fontname)
    return Caractere(_desenhada(item), item.x0, item.x1, item.size, item.y0, fonte=fonte)


def _desenhada(letra: LTChar) -> str:
    return nome_da_fonte.letra_desenhada(letra.get_text(), letra.fontname)


def _versalete(visiveis: list[LTChar], tamanho: float) -> bool:
    """O versalete feito à mão, pela letra maior, ou o de fonte própria, pelo nome da fonte.

    Toda letra visível, como no negrito: a abertura de capítulo com as primeiras palavras em
    versalete e o resto no corpo é parágrafo.
    """
    feito_a_mao = em_versalete([(c.get_text(), c.size) for c in visiveis], tamanho)
    de_fonte = nome_da_fonte.toda_em_versalete(c.fontname for c in visiveis)
    return feito_a_mao or de_fonte
