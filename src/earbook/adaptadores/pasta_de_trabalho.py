# SPDX-License-Identifier: GPL-3.0-or-later
"""Layout da pasta de trabalho de um livro. Só este módulo sabe onde cada arquivo fica.

livro.json            metadados, capítulos e texto fora de segmento
segmentos/cNNN.json   segmentos de cada capítulo como vieram do EPUB (a origem)
limpos/cNNN.json      os mesmos, sem o que a limpeza tirou: é o que segue na esteira
limpeza.json          remoções, suspeitas, aparos, junções e capitulares devolvidas (ADR-0003, 0007)
epub/                 EPUB extraído, com o XHTML marcado por `data-earbook`

A tradução (ADR-0006):
pedidos/cNNN-lNNN.json     o Python grava o que traduzir no lote: [{id, papel, texto}]
traduzidos/cNNN-lNNN.json  o agente grava a resposta do lote de mesmo nome: [{id, texto}]
glossario.json             o agente grava os nomes próprios: [{original, traducao}]
nomes.json                 o Python grava os candidatos a nome fora do glossário
termos/cNNN-lNNN.json      o agente grava o que decidiu fora do glossário: [{original, traducao}]
decisoes.md                as decisões do livro: o Python cria o modelo, a sessão escreve (ADR-0007)
"""

from __future__ import annotations

import contextlib
import json
import posixpath
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from earbook.adaptadores.registros_da_pasta import (
    Json,
    PastaDeTrabalhoInvalidaError,
    campo_inteiro,
    campo_nome,
    campo_papel,
    campo_texto,
    gravar_json,
    grupo_do_registro,
    ler_json,
    lista,
    objeto,
    recusar_link,
    segmentos_do_arquivo,
)
from earbook.dominio.adaptacao import RespostaDaAdaptacao
from earbook.dominio.glossario import CandidatoANome, EntradaDoGlossario, TermosDoLote
from earbook.dominio.limpeza import CapituloLimpo, LivroLimpo
from earbook.dominio.segmento import Segmento
from earbook.dominio.siglas import CandidatoASigla
from earbook.dominio.trabalho import CapituloPreparado, LivroPreparado
from earbook.dominio.traducao import LOTE, Pedido, Resposta, Traduzido

_ID_DO_CAPITULO = re.compile(r"c[0-9]{3,}")


@dataclass(frozen=True)
class LimpezaRegistrada:
    """O que o `conferir` precisa do `limpeza.json`: quem saiu e quem foi juntado em quem."""

    removidos: tuple[str, ...]
    juntados: tuple[tuple[str, str], ...]
    """Pares (ID, destino), com as repetições do registro: o `conferir` as conta (A7)."""


def criar_pasta_de_trabalho(pasta: Path) -> None:
    """Cria a pasta; recusa se ela já existe, para não apagar tradução já feita."""
    if pasta.exists():
        mensagem = f"a pasta de trabalho {pasta} já existe; apague-a ou use outra"
        raise FileExistsError(mensagem)
    (pasta / "segmentos").mkdir(parents=True)
    (pasta / "limpos").mkdir()


def pasta_do_epub(pasta: Path) -> Path:
    return pasta / "epub"


def ler_xhtml(pasta: Path, arquivo: str) -> bytes:
    return (pasta_do_epub(pasta) / arquivo).read_bytes()


def gravar_xhtml(pasta: Path, arquivo: str, conteudo: bytes) -> None:
    _ = (pasta_do_epub(pasta) / arquivo).write_bytes(conteudo)


def gravar_segmentos(pasta: Path, capitulo: str, segmentos: list[Segmento]) -> None:
    gravar_json(pasta / "segmentos" / f"{capitulo}.json", [asdict(s) for s in segmentos])


def gravar_limpos(pasta: Path, capitulo: CapituloLimpo) -> None:
    caminho = pasta / "limpos" / f"{capitulo.capitulo}.json"
    gravar_json(caminho, [asdict(s) for s in capitulo.segmentos])


def gravar_limpeza(pasta: Path, limpeza: LivroLimpo) -> None:
    registro = {
        "remocoes": [asdict(r) for r in limpeza.remocoes],
        "suspeitas": [asdict(s) for s in limpeza.suspeitas],
        "aparos": [asdict(a) for a in limpeza.aparos],
        "juncoes": [asdict(j) for j in limpeza.juncoes],
        "capitulares": [asdict(c) for c in limpeza.capitulares],
    }
    gravar_json(pasta / "limpeza.json", registro)


def gravar_livro(pasta: Path, livro: LivroPreparado) -> None:
    gravar_json(pasta / "livro.json", asdict(livro))


def ler_segmentos(pasta: Path, capitulo: str) -> tuple[Segmento, ...]:
    return segmentos_do_arquivo(pasta / "segmentos" / f"{capitulo}.json")


def ler_limpos(pasta: Path, capitulo: str) -> tuple[Segmento, ...]:
    return segmentos_do_arquivo(pasta / "limpos" / f"{capitulo}.json")


def ler_capitulos(pasta: Path) -> tuple[CapituloPreparado, ...]:
    caminho = pasta / "livro.json"
    livro = objeto(ler_json(caminho), caminho)
    capitulos = [objeto(item, caminho) for item in lista(livro.get("capitulos"), caminho)]
    return tuple(
        CapituloPreparado(
            _id_do_capitulo(capitulo, caminho),
            _arquivo_do_capitulo(capitulo, caminho),
            campo_inteiro(capitulo, "segmentos", caminho),
        )
        for capitulo in capitulos
    )


def _id_do_capitulo(capitulo: dict[str, Json], caminho: Path) -> str:
    id_ = campo_texto(capitulo, "id", caminho)
    if not _ID_DO_CAPITULO.fullmatch(id_):
        mensagem = f"{caminho}: id de capítulo fora do formato cNNN: {id_!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return id_


def _arquivo_do_capitulo(capitulo: dict[str, Json], caminho: Path) -> str:
    """O caminho dentro de `epub/`, na forma que o `preparar` grava (A5 da auditoria): com
    `./` o `montar` não achava o arquivo para trocar, e com `../` lia fora da pasta."""
    arquivo = campo_texto(capitulo, "arquivo", caminho)
    if (
        posixpath.normpath(arquivo) != arquivo
        or arquivo.startswith(("/", "../"))
        or arquivo == ".."
    ):
        mensagem = f"{caminho}: arquivo de capítulo fora de epub/ ou da forma normal: {arquivo!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return arquivo


def ler_limpeza(pasta: Path) -> LimpezaRegistrada:
    caminho = pasta / "limpeza.json"
    registro = objeto(ler_json(caminho), caminho)
    remocoes = [objeto(item, caminho) for item in lista(registro.get("remocoes"), caminho)]
    juncoes = [objeto(item, caminho) for item in lista(registro.get("juncoes"), caminho)]
    return LimpezaRegistrada(
        tuple(campo_texto(remocao, "id", caminho) for remocao in remocoes),
        tuple(
            (campo_texto(juncao, "id", caminho), campo_texto(juncao, "em", caminho))
            for juncao in juncoes
        ),
    )


def ler_idioma(pasta: Path) -> str:
    caminho = pasta / "livro.json"
    return campo_texto(objeto(ler_json(caminho), caminho), "idioma", caminho)


def criar_pastas_da_traducao(pasta: Path) -> None:
    """`pedidos/`, `traduzidos/` e `termos/`, onde o agente grava; não apaga nada."""
    pasta_dos_pedidos(pasta).mkdir(exist_ok=True)
    pasta_das_respostas(pasta).mkdir(exist_ok=True)
    pasta_dos_termos(pasta).mkdir(exist_ok=True)


def pasta_dos_pedidos(pasta: Path) -> Path:
    return pasta / "pedidos"


def pasta_das_respostas(pasta: Path) -> Path:
    return pasta / "traduzidos"


def caminho_do_pedido(pasta: Path, lote: str) -> Path:
    return pasta_dos_pedidos(pasta) / f"{lote}.json"


def caminho_da_resposta(pasta: Path, lote: str) -> Path:
    """Com `lote="<lote>"`, é o modelo do caminho que a CLI mostra ao agente."""
    return pasta_das_respostas(pasta) / f"{lote}.json"


def caminho_do_glossario(pasta: Path) -> Path:
    return pasta / "glossario.json"


def pasta_dos_termos(pasta: Path) -> Path:
    return pasta / "termos"


def caminho_dos_termos(pasta: Path, lote: str) -> Path:
    """O que o tradutor decidiu fora do glossário no lote (ADR-0007)."""
    return pasta_dos_termos(pasta) / f"{lote}.json"


def caminho_das_decisoes(pasta: Path) -> Path:
    """As decisões do livro, em Markdown: a sessão escreve, o tradutor lê (ADR-0007)."""
    return pasta / "decisoes.md"


def gravar_decisoes_se_faltar(pasta: Path, modelo: str) -> None:
    """Grava o modelo uma vez só: o arquivo que existe é da sessão e nunca é reescrito."""
    caminho = caminho_das_decisoes(pasta)
    recusar_link(caminho)
    with contextlib.suppress(FileExistsError), caminho.open("x", encoding="utf-8") as arquivo:
        _ = arquivo.write(modelo)


def ler_termos(pasta: Path) -> tuple[TermosDoLote, ...]:
    """Escritos pelo agente, como a resposta: nome de lote e cada campo validados."""
    return tuple(
        TermosDoLote(lote, tuple(_entrada(r, caminho) for r in registros))
        for lote, caminho, registros in _lotes(pasta_dos_termos(pasta))
    )


def caminho_dos_candidatos(pasta: Path) -> Path:
    return pasta / "nomes.json"


def gravar_pedido(pasta: Path, pedido: Pedido) -> None:
    """Recusa o pedido que já existe: a tradução em andamento ficaria sem o pedido dela.

    Sem as notas: o destino da chamada de nota é do `montar`, não do tradutor.
    """
    _gravar_pedido(caminho_do_pedido(pasta, pedido.lote), pedido)


def _gravar_pedido(caminho: Path, pedido: Pedido) -> None:
    registros = [{"id": s.id, "papel": s.papel.value, "texto": s.texto} for s in pedido.segmentos]
    texto = json.dumps(registros, ensure_ascii=False, indent=2) + "\n"
    with caminho.open("x", encoding="utf-8") as arquivo:
        _ = arquivo.write(texto)


def ler_pedidos(pasta: Path) -> tuple[Pedido, ...]:
    return _pedidos(pasta_dos_pedidos(pasta))


def _pedidos(pasta: Path) -> tuple[Pedido, ...]:
    return tuple(
        Pedido(lote, tuple(_segmento_do_pedido(registro, caminho) for registro in registros))
        for lote, caminho, registros in _lotes(pasta)
    )


def ler_respostas(pasta: Path) -> tuple[Resposta, ...]:
    """A resposta é escrita pelo agente: tudo é validado, e o nome tem de ser o de um lote."""
    return tuple(
        Resposta(lote, tuple(_traduzido(registro, caminho) for registro in registros))
        for lote, caminho, registros in _lotes(pasta_das_respostas(pasta))
    )


def ler_glossario(pasta: Path) -> tuple[EntradaDoGlossario, ...]:
    """Sem `glossario.json`, o glossário é vazio. Campo além dos dois (uma nota do agente)
    é ignorado."""
    caminho = caminho_do_glossario(pasta)
    recusar_link(caminho)
    if not caminho.exists():
        return ()
    registros = [objeto(item, caminho) for item in lista(ler_json(caminho), caminho)]
    return tuple(_entrada(r, caminho) for r in registros)


def _entrada(item: dict[str, Json], caminho: Path) -> EntradaDoGlossario:
    return EntradaDoGlossario(
        campo_nome(item, "original", caminho), campo_nome(item, "traducao", caminho)
    )


def gravar_candidatos(pasta: Path, candidatos: tuple[CandidatoANome, ...]) -> None:
    """Pelo link, a gravação sairia da pasta de trabalho e apagaria o alvo (F4 da pós)."""
    caminho = caminho_dos_candidatos(pasta)
    recusar_link(caminho)
    gravar_json(caminho, [asdict(c) for c in candidatos])


def _lotes(pasta: Path) -> list[tuple[str, Path, list[dict[str, Json]]]]:
    """Os arquivos `cNNN-lNNN.json` da pasta, em ordem de lote; a pasta que não existe é vazia."""
    recusar_link(pasta)
    if not pasta.is_dir():
        return []
    lotes: list[tuple[str, Path, list[dict[str, Json]]]] = []
    for caminho in sorted(pasta.glob("*.json")):
        recusar_link(caminho)
        if not LOTE.fullmatch(caminho.stem):
            mensagem = f"{caminho}: nome fora do formato cNNN-lNNN.json de um lote"
            raise PastaDeTrabalhoInvalidaError(mensagem)
        registros = [objeto(item, caminho) for item in lista(ler_json(caminho), caminho)]
        lotes.append((caminho.stem, caminho, registros))
    return lotes


def _segmento_do_pedido(registro: dict[str, Json], caminho: Path) -> Segmento:
    return Segmento(
        campo_texto(registro, "id", caminho),
        campo_papel(registro, caminho),
        campo_texto(registro, "texto", caminho),
    )


def _traduzido(registro: dict[str, Json], caminho: Path) -> Traduzido:
    return Traduzido(campo_texto(registro, "id", caminho), campo_texto(registro, "texto", caminho))


def criar_pastas_da_adaptacao(pasta: Path) -> None:
    """`para-adaptar/`, que o Python grava, e `adaptados/`, onde o agente grava (ADR-0009)."""
    pasta_para_adaptar(pasta).mkdir(exist_ok=True)
    pasta_dos_adaptados(pasta).mkdir(exist_ok=True)


def ha_adaptacao(pasta: Path) -> bool:
    """O `adaptar` já rodou: o `conferir` e o `montar` passam ao modo adaptação."""
    return pasta_para_adaptar(pasta).is_dir()


def pasta_para_adaptar(pasta: Path) -> Path:
    return pasta / "para-adaptar"


def pasta_dos_adaptados(pasta: Path) -> Path:
    return pasta / "adaptados"


def caminho_do_adaptado(pasta: Path, lote: str) -> Path:
    """Com `lote="<lote>"`, é o modelo do caminho que a CLI mostra ao agente."""
    return pasta_dos_adaptados(pasta) / f"{lote}.json"


def caminho_das_siglas(pasta: Path) -> Path:
    return pasta / "siglas.json"


def gravar_siglas(pasta: Path, candidatas: tuple[CandidatoASigla, ...]) -> None:
    caminho = caminho_das_siglas(pasta)
    recusar_link(caminho)
    gravar_json(caminho, [asdict(c) for c in candidatas])


def gravar_pedido_da_adaptacao(pasta: Path, pedido: Pedido) -> None:
    """Como o da tradução: o pedido gravado nunca é reescrito."""
    _gravar_pedido(pasta_para_adaptar(pasta) / f"{pedido.lote}.json", pedido)


def ler_pedidos_da_adaptacao(pasta: Path) -> tuple[Pedido, ...]:
    return _pedidos(pasta_para_adaptar(pasta))


def ler_adaptados(pasta: Path) -> tuple[RespostaDaAdaptacao, ...]:
    """Escritos pelo agente: nome de lote e cada campo de cada grupo validados."""
    return tuple(
        RespostaDaAdaptacao(lote, tuple(grupo_do_registro(r, caminho) for r in registros))
        for lote, caminho, registros in _lotes(pasta_dos_adaptados(pasta))
    )
