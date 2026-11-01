# SPDX-License-Identifier: GPL-3.0-or-later
"""Layout da pasta de trabalho de um livro. Só este módulo sabe onde cada arquivo fica.

livro.json            metadados, capítulos e texto fora de segmento
segmentos/cNNN.json   segmentos de cada capítulo como vieram do EPUB (a origem)
limpos/cNNN.json      os mesmos, sem o que a limpeza tirou: é o que segue na esteira
limpeza.json          remoções, suspeitas, aparos e junções da limpeza, com o motivo (ADR-0003)
epub/                 EPUB extraído, com o XHTML marcado por `data-earbook`
"""

from __future__ import annotations

import json
import posixpath
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from earbook.dominio.limpeza import CapituloLimpo, LivroLimpo
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.trabalho import CapituloPreparado, LivroPreparado

_ID_DO_CAPITULO = re.compile(r"c[0-9]{3,}")

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
    texto = json.dumps(conteudo, ensure_ascii=False, indent=2)
    _ = caminho.write_text(texto + "\n", encoding="utf-8")


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


def _segmentos(caminho: Path) -> tuple[Segmento, ...]:
    registros = [_objeto(item, caminho) for item in _lista(_ler_json(caminho), caminho)]
    return tuple(_segmento(registro, caminho) for registro in registros)


def _segmento(registro: dict[str, Json], caminho: Path) -> Segmento:
    papel = _texto(registro, "papel", caminho)
    if papel not in {p.value for p in Papel}:
        mensagem = f"{caminho}: papel desconhecido {papel!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    notas = tuple(
        _como_texto(nota, "notas", caminho) for nota in _lista(registro.get("notas"), caminho)
    )
    return Segmento(
        _texto(registro, "id", caminho), Papel(papel), _texto(registro, "texto", caminho), notas
    )


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
