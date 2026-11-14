# SPDX-License-Identifier: GPL-3.0-or-later
"""Lê o PDF com o pdfminer.six e devolve páginas do domínio (ADR-0004).

É o único módulo que importa a biblioteca de PDF.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import multimode
from typing import BinaryIO, override

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTChar, LTPage, LTTextBox, LTTextLine
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
from earbook.dominio.caracteres import Caractere, lido, pagina_usa_chamadas, texto_da_linha
from earbook.dominio.pagina import Linha, Pagina, em_versalete
from earbook.dominio.segmento import normalizar_espacos
from earbook.dominio.sumario_interno import ItemDoSumario

# Medido no spike: o código do "Hard Parts" vem em UbuntuMono.
_FONTE_MONOESPACADA = re.compile(r"mono|courier|code|consol", re.IGNORECASE)
# O estilo vem depois do traço ou da vírgula do nome: "SourceSans3-SemiboldIt" (Competente),
# "MyriadPro-SemiboldCond" (Hard Parts), "Arial,Bold". Sem o separador, "Blackadder" seria
# negrito. ADR-0004, "Subtítulo em negrito do tamanho do corpo".
_FONTE_NEGRITO = re.compile(r"[-,]\w*(?:bold|black|heavy|demi)", re.IGNORECASE)

# O versalete de fonte própria vem num tamanho só, e por isso a letra maior não o acha: no Maudlin,
# "Archer-Medium-SC700" (ADR-0004, "Versalete de fonte própria"). O "SC" vem no fim do nome,
# depois do separador: sem ele, "DiscoSC" seria versalete. Sem caixa, como as outras fontes.
_FONTE_VERSALETE = re.compile(r"[-_]SC\d*$", re.IGNORECASE)
# A família da letra: o nome sem o prefixo do subconjunto ("TCMKGG+") e sem o estilo, depois do
# traço ou da vírgula ("AGaramondPro-Regular", "Arial,Bold"). ADR-0004, "Tabela e figura pela
# letra". O "MT" do fim fica: "TimesNewRomanPSMT" e "TimesNewRomanPS-BoldMT" saem como duas
# famílias, e é por isso que o rótulo "TABLE 1.1" do Bonica, em negrito no tamanho do corpo, não
# conta como letra do corpo (ADR-0004, "Tratado em português e em espanhol", "O que fica").
_ESTILO_DA_FONTE = re.compile(r"[-,].*$")

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
    lidas = [_linha(bruta, layout.height, agregador.nao_pinta) for bruta in brutas]
    # A página com chamadas certas prova as duvidosas: só as linhas que as têm são lidas de novo.
    if pagina_usa_chamadas(sum(len(lida.linha.chamadas) for lida in lidas if lida is not None)):
        lidas = [
            _linha(bruta, layout.height, agregador.nao_pinta, com_duvidosas=True)
            if lida is not None and lida.duvidosas
            else lida
            for bruta, lida in zip(brutas, lidas, strict=True)
        ]
    return Pagina(numero, tuple(lida.linha for lida in lidas if lida is not None))


def _linha(
    linha: LTTextLine,
    altura: float,
    nao_pinta: Callable[[LTChar], bool],
    *,
    com_duvidosas: bool = False,
) -> _LinhaLida | None:
    caracteres = [c for c in linha if isinstance(c, LTChar)]
    if not caracteres or not normalizar_espacos(linha.get_text()):
        return None
    # A moda, não a média: nome de código em 8,5 pt numa linha de 9 pt puxava a média
    # para baixo de 0,85 do corpo, e a prosa virava nota (A1 da auditoria, Hard Parts).
    # No empate, o maior: a letra menor é a do código ou da nota (pós-revisão).
    tamanho = max(multimode(round(c.size, 1) for c in caracteres))
    # A chamada sobrescrita e o espaço inventado saem aqui, onde o caractere ainda tem tamanho e
    # posição (ADR-0004, "Número de referência e espaço falso").
    lida = texto_da_linha(_caracteres(linha), tamanho, com_duvidosas=com_duvidosas)
    # Toda letra, não alguma: no Hard Parts, as 584 linhas de código são 100% monoespaçadas
    # e as 183 de prosa com um nome de código no meio ("ss.survey") ficam entre 0 e 90%.
    monoespacada = all(_fonte_casa(_FONTE_MONOESPACADA, c.fontname) for c in caracteres)
    texto = normalizar_espacos(lida.texto) if monoespacada else lido(lida, tamanho)
    pronta = Linha(
        texto,
        x=linha.x0,
        topo=1 - linha.y1 / altura,
        tamanho=tamanho,
        monoespacada=monoespacada,
        fim=linha.x1,
        chamadas=lida.chamadas,
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
        negrito=all(_fonte_casa(_FONTE_NEGRITO, c.fontname) for c in visiveis),
        versalete=_versalete(visiveis, linha.tamanho),
        fonte=_familia(visiveis),
        # Toda letra visível, como no negrito. O `upright` do pdfminer é a matriz sem giro: a
        # itálica, que só inclina, continua de pé (ADR-0004, "Texto girado").
        girada=bool(visiveis) and not any(c.upright for c in visiveis),
        # Toda letra visível, como no negrito: a linha que mistura fica (ADR-0004, "Camada do OCR").
        nao_pintada=bool(visiveis) and all(nao_pinta(c) for c in visiveis),
    )


def _caracteres(linha: LTTextLine) -> list[Caractere]:
    """Os caracteres da linha para o domínio. O espaço do pdfminer (`LTAnno`) não tem posição:
    ganha o fim da letra antes e o começo da letra depois. Uma passada de trás para frente guarda
    o começo da próxima letra."""
    caracteres: list[Caractere] = []
    comeco_da_seguinte: float | None = None
    for item in reversed(list(linha)):
        if isinstance(item, LTChar):
            # O pé da caixa, e não a matriz: a subida do `Ts` só entra na caixa (pdfminer).
            caracteres.append(Caractere(item.get_text(), item.x0, item.x1, item.size, item.y0))
            comeco_da_seguinte = item.x0
        else:
            caracteres.append(
                Caractere(item.get_text(), 0.0, comeco_da_seguinte or 0.0, 0.0, 0.0, virtual=True)
            )
    caracteres.reverse()
    fim_da_anterior = 0.0
    for i, caractere in enumerate(caracteres):
        if caractere.virtual:
            depois = caractere.x1 or fim_da_anterior
            caracteres[i] = replace(caractere, x0=fim_da_anterior, x1=depois)
        else:
            fim_da_anterior = caractere.x1
    return caracteres


def _familia(visiveis: list[LTChar]) -> str:
    """A família da letra da maioria dos caracteres visíveis; vazia se o nome não é texto."""
    familias = Counter(
        _ESTILO_DA_FONTE.sub("", c.fontname.rsplit("+", 1)[-1])
        for c in visiveis
        if isinstance(c.fontname, str)
    )
    return familias.most_common(1)[0][0] if familias else ""


def _versalete(visiveis: list[LTChar], tamanho: float) -> bool:
    """O versalete feito à mão, pela letra maior, ou o de fonte própria, pelo nome da fonte.

    Toda letra visível, como no negrito: a abertura de capítulo com as primeiras palavras em
    versalete e o resto no corpo é parágrafo.
    """
    feito_a_mao = em_versalete([(c.get_text(), c.size) for c in visiveis], tamanho)
    de_fonte = all(_fonte_casa(_FONTE_VERSALETE, c.fontname) for c in visiveis)
    return feito_a_mao or de_fonte


def _fonte_casa(padrao: re.Pattern[str], nome_da_fonte: object) -> bool:
    """O pdfminer entrega o nome cru quando ele não é nome PDF: bytes ou número (F1)."""
    return isinstance(nome_da_fonte, str) and padrao.search(nome_da_fonte) is not None
