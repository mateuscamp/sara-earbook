# SPDX-License-Identifier: GPL-3.0-or-later
"""Layout da pasta de trabalho de um livro. Só este módulo sabe onde cada arquivo fica.

livro.json            metadados, capítulos e texto fora de segmento
segmentos/cNNN.json   segmentos de cada capítulo como vieram do EPUB (a origem)
limpos/cNNN.json      os mesmos, sem o que a limpeza tirou: é o que segue na esteira
limpeza.json          remoções, suspeitas, aparos e junções da limpeza, com o motivo (ADR-0003)
epub/                 EPUB extraído, com o XHTML marcado por `data-earbook`

A tradução (ADR-0006):
pedidos/cNNN-lNNN.json     o Python grava o que traduzir no lote: [{id, papel, texto}]
traduzidos/cNNN-lNNN.json  o agente grava a resposta do lote de mesmo nome: [{id, texto}]
glossario.json             o agente grava os nomes próprios: [{original, traducao}]
nomes.json                 o Python grava os candidatos a nome fora do glossário
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from earbook.dominio.glossario import CandidatoANome, EntradaDoGlossario
from earbook.dominio.limpeza import CapituloLimpo, LivroLimpo
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.trabalho import CapituloPreparado, LivroPreparado
from earbook.dominio.traducao import LOTE, Pedido, Resposta, Traduzido

_ID_DO_CAPITULO = re.compile(r"c[0-9]{3,}")
# O `mkstemp` cria com 0600; os arquivos da pasta eram 0644, como os do `write_text`.
PERMISSAO_DOS_ARQUIVOS = 0o644

type Json = bool | int | float | str | list[Json] | dict[str, Json] | None


class PastaDeTrabalhoInvalidaError(ValueError):
    pass


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
    _gravar_json(pasta / "segmentos" / f"{capitulo}.json", [asdict(s) for s in segmentos])


def gravar_limpos(pasta: Path, capitulo: CapituloLimpo) -> None:
    caminho = pasta / "limpos" / f"{capitulo.capitulo}.json"
    _gravar_json(caminho, [asdict(s) for s in capitulo.segmentos])


def gravar_limpeza(pasta: Path, limpeza: LivroLimpo) -> None:
    registro = {
        "remocoes": [asdict(r) for r in limpeza.remocoes],
        "suspeitas": [asdict(s) for s in limpeza.suspeitas],
        "aparos": [asdict(a) for a in limpeza.aparos],
        "juncoes": [asdict(j) for j in limpeza.juncoes],
    }
    _gravar_json(pasta / "limpeza.json", registro)


def gravar_livro(pasta: Path, livro: LivroPreparado) -> None:
    _gravar_json(pasta / "livro.json", asdict(livro))


def _gravar_json(caminho: Path, conteudo: object) -> None:
    """Num temporário e depois no lugar: o link, físico ou simbólico, é trocado sem tocar no
    alvo (A5 da pós-auditoria curta), e a queda no meio deixa o arquivo antigo inteiro."""
    texto = json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n"
    descritor, nome = tempfile.mkstemp(dir=caminho.parent, prefix=f".{caminho.name}.")
    temporario = Path(nome)
    try:
        os.fchmod(descritor, PERMISSAO_DOS_ARQUIVOS)
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            _ = arquivo.write(texto)
        _ = temporario.replace(caminho)
    except BaseException:
        temporario.unlink(missing_ok=True)
        raise


def ler_segmentos(pasta: Path, capitulo: str) -> tuple[Segmento, ...]:
    return _segmentos(pasta / "segmentos" / f"{capitulo}.json")


def ler_limpos(pasta: Path, capitulo: str) -> tuple[Segmento, ...]:
    return _segmentos(pasta / "limpos" / f"{capitulo}.json")


def ler_capitulos(pasta: Path) -> tuple[CapituloPreparado, ...]:
    caminho = pasta / "livro.json"
    livro = _objeto(_ler_json(caminho), caminho)
    capitulos = [_objeto(item, caminho) for item in _lista(livro.get("capitulos"), caminho)]
    return tuple(
        CapituloPreparado(
            _id_do_capitulo(capitulo, caminho),
            _arquivo_do_capitulo(capitulo, caminho),
            _inteiro(capitulo, "segmentos", caminho),
        )
        for capitulo in capitulos
    )


def _id_do_capitulo(capitulo: dict[str, Json], caminho: Path) -> str:
    id_ = _texto(capitulo, "id", caminho)
    if not _ID_DO_CAPITULO.fullmatch(id_):
        mensagem = f"{caminho}: id de capítulo fora do formato cNNN: {id_!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return id_


def _arquivo_do_capitulo(capitulo: dict[str, Json], caminho: Path) -> str:
    """O caminho dentro de `epub/`, na forma que o `preparar` grava (A5 da auditoria): com
    `./` o `montar` não achava o arquivo para trocar, e com `../` lia fora da pasta."""
    arquivo = _texto(capitulo, "arquivo", caminho)
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
    registro = _objeto(_ler_json(caminho), caminho)
    remocoes = [_objeto(item, caminho) for item in _lista(registro.get("remocoes"), caminho)]
    juncoes = [_objeto(item, caminho) for item in _lista(registro.get("juncoes"), caminho)]
    return LimpezaRegistrada(
        tuple(_texto(remocao, "id", caminho) for remocao in remocoes),
        tuple((_texto(juncao, "id", caminho), _texto(juncao, "em", caminho)) for juncao in juncoes),
    )


def ler_idioma(pasta: Path) -> str:
    caminho = pasta / "livro.json"
    return _texto(_objeto(_ler_json(caminho), caminho), "idioma", caminho)


def criar_pastas_da_traducao(pasta: Path) -> None:
    """`pedidos/` e `traduzidos/`, onde o agente grava a resposta; não apaga nada."""
    pasta_dos_pedidos(pasta).mkdir(exist_ok=True)
    pasta_das_respostas(pasta).mkdir(exist_ok=True)


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


def caminho_dos_candidatos(pasta: Path) -> Path:
    return pasta / "nomes.json"


def gravar_pedido(pasta: Path, pedido: Pedido) -> None:
    """Recusa o pedido que já existe: a tradução em andamento ficaria sem o pedido dela.

    Sem as notas: o destino da chamada de nota é do `montar`, não do tradutor.
    """
    registros = [{"id": s.id, "papel": s.papel.value, "texto": s.texto} for s in pedido.segmentos]
    texto = json.dumps(registros, ensure_ascii=False, indent=2) + "\n"
    with caminho_do_pedido(pasta, pedido.lote).open("x", encoding="utf-8") as arquivo:
        _ = arquivo.write(texto)


def ler_pedidos(pasta: Path) -> tuple[Pedido, ...]:
    return tuple(
        Pedido(lote, tuple(_segmento_do_pedido(registro, caminho) for registro in registros))
        for lote, caminho, registros in _lotes(pasta_dos_pedidos(pasta))
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
    _recusar_link(caminho)
    if not caminho.exists():
        return ()
    registros = [_objeto(item, caminho) for item in _lista(_ler_json(caminho), caminho)]
    return tuple(
        EntradaDoGlossario(_nome(r, "original", caminho), _nome(r, "traducao", caminho))
        for r in registros
    )


def gravar_candidatos(pasta: Path, candidatos: tuple[CandidatoANome, ...]) -> None:
    """Pelo link, a gravação sairia da pasta de trabalho e apagaria o alvo (F4 da pós)."""
    caminho = caminho_dos_candidatos(pasta)
    _recusar_link(caminho)
    _gravar_json(caminho, [asdict(c) for c in candidatos])


def _lotes(pasta: Path) -> list[tuple[str, Path, list[dict[str, Json]]]]:
    """Os arquivos `cNNN-lNNN.json` da pasta, em ordem de lote; a pasta que não existe é vazia."""
    _recusar_link(pasta)
    if not pasta.is_dir():
        return []
    lotes: list[tuple[str, Path, list[dict[str, Json]]]] = []
    for caminho in sorted(pasta.glob("*.json")):
        _recusar_link(caminho)
        if not LOTE.fullmatch(caminho.stem):
            mensagem = f"{caminho}: nome fora do formato cNNN-lNNN.json de um lote"
            raise PastaDeTrabalhoInvalidaError(mensagem)
        registros = [_objeto(item, caminho) for item in _lista(_ler_json(caminho), caminho)]
        lotes.append((caminho.stem, caminho, registros))
    return lotes


def _recusar_link(caminho: Path) -> None:
    """A tradução é escrita pelo agente: o link traria para o livro a resposta de outro livro,
    sem aviso (A5 da auditoria). O `epub/` já recusa link pelo mesmo motivo (ADR-0005)."""
    if caminho.is_symlink():
        mensagem = f"{caminho}: link simbólico na pasta de trabalho; não leio"
        raise PastaDeTrabalhoInvalidaError(mensagem)


def _segmento_do_pedido(registro: dict[str, Json], caminho: Path) -> Segmento:
    return Segmento(
        _texto(registro, "id", caminho),
        _papel(registro, caminho),
        _texto(registro, "texto", caminho),
    )


def _traduzido(registro: dict[str, Json], caminho: Path) -> Traduzido:
    return Traduzido(_texto(registro, "id", caminho), _texto(registro, "texto", caminho))


def _nome(registro: dict[str, Json], chave: str, caminho: Path) -> str:
    """O nome vazio "aparece" em todo segmento e acusaria o livro inteiro."""
    nome = _texto(registro, chave, caminho)
    if not nome.strip():
        mensagem = f"{caminho}: {chave!r} vazio no glossário: {registro!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return nome


def _segmentos(caminho: Path) -> tuple[Segmento, ...]:
    registros = [_objeto(item, caminho) for item in _lista(_ler_json(caminho), caminho)]
    return tuple(_segmento(registro, caminho) for registro in registros)


def _segmento(registro: dict[str, Json], caminho: Path) -> Segmento:
    notas = tuple(
        _como_texto(nota, "notas", caminho) for nota in _lista(registro.get("notas"), caminho)
    )
    return Segmento(
        _texto(registro, "id", caminho),
        _papel(registro, caminho),
        _texto(registro, "texto", caminho),
        notas,
    )


def _papel(registro: dict[str, Json], caminho: Path) -> Papel:
    papel = _texto(registro, "papel", caminho)
    if papel not in {p.value for p in Papel}:
        mensagem = f"{caminho}: papel desconhecido {papel!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return Papel(papel)


def _ler_json(caminho: Path) -> Json:
    """O arquivo é escrito por nós e, depois, pela tradução: valida-se tudo o que se lê."""
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))  # pyright: ignore[reportAny]  # motivo: o json devolve Any; Json é o que o formato garante, e cada campo é validado ao ser lido
    # Todo ValueError (JSON quebrado, texto que não é UTF-8, inteiro de mais de 4.300
    # algarismos) e o RecursionError (JSON aninhado demais) viram erro com o caminho: sem
    # ele, a CLI mostrava a mensagem crua ou um traceback (A6 da auditoria; N5 da pós).
    except (ValueError, RecursionError) as erro:
        mensagem = f"{caminho}: JSON inválido ({type(erro).__name__}: {erro})"
        raise PastaDeTrabalhoInvalidaError(mensagem) from erro


def _objeto(valor: Json, caminho: Path) -> dict[str, Json]:
    if not isinstance(valor, dict):
        mensagem = f"{caminho}: esperava um objeto, veio {valor!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return valor


def _lista(valor: Json, caminho: Path) -> list[Json]:
    if not isinstance(valor, list):
        mensagem = f"{caminho}: esperava uma lista, veio {valor!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return valor


def _texto(registro: dict[str, Json], chave: str, caminho: Path) -> str:
    return _como_texto(registro.get(chave), chave, caminho)


def _como_texto(valor: Json, chave: str, caminho: Path) -> str:
    if not isinstance(valor, str):
        mensagem = f"{caminho}: {chave!r} devia ser texto, veio {valor!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return valor


def _inteiro(registro: dict[str, Json], chave: str, caminho: Path) -> int:
    valor = registro.get(chave)
    if not isinstance(valor, int) or isinstance(valor, bool):
        mensagem = f"{caminho}: {chave!r} devia ser número inteiro, veio {valor!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return valor
