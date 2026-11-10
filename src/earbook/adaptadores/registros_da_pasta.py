# SPDX-License-Identifier: GPL-3.0-or-later
"""A leitura e a gravação validadas dos JSON da pasta de trabalho, campo a campo.

Não sabe onde cada arquivo fica: isso é de `pasta_de_trabalho.py`. Sabe o formato de cada
registro, porque o JSON é escrito por nós e, depois, pelo agente (ADR-0006, ADR-0009).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from earbook.dominio.adaptacao import Correcao, Grupo, Omitido, TipoDoGrupo
from earbook.dominio.segmento import Papel, Segmento

# O `mkstemp` cria com 0600; os arquivos da pasta eram 0644, como os do `write_text`.
PERMISSAO_DOS_ARQUIVOS = 0o644

type Json = bool | int | float | str | list[Json] | dict[str, Json] | None


class PastaDeTrabalhoInvalidaError(ValueError):
    pass


def gravar_json(caminho: Path, conteudo: object) -> None:
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


def recusar_link(caminho: Path) -> None:
    """A tradução é escrita pelo agente: o link traria para o livro a resposta de outro livro,
    sem aviso (A5 da auditoria). O `epub/` já recusa link pelo mesmo motivo (ADR-0005)."""
    if caminho.is_symlink():
        mensagem = f"{caminho}: link simbólico na pasta de trabalho; não leio"
        raise PastaDeTrabalhoInvalidaError(mensagem)


def campo_nome(registro: dict[str, Json], chave: str, caminho: Path) -> str:
    """O nome vazio "aparece" em todo segmento e acusaria o livro inteiro."""
    nome = campo_texto(registro, chave, caminho)
    if not nome.strip():
        mensagem = f"{caminho}: {chave!r} vazio no glossário: {registro!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return nome


def segmentos_do_arquivo(caminho: Path) -> tuple[Segmento, ...]:
    registros = [objeto(item, caminho) for item in lista(ler_json(caminho), caminho)]
    return tuple(segmento_do_registro(registro, caminho) for registro in registros)


def segmento_do_registro(registro: dict[str, Json], caminho: Path) -> Segmento:
    notas = tuple(
        como_texto(nota, "notas", caminho) for nota in lista(registro.get("notas"), caminho)
    )
    return Segmento(
        campo_texto(registro, "id", caminho),
        campo_papel(registro, caminho),
        campo_texto(registro, "texto", caminho),
        notas,
    )


def campo_papel(registro: dict[str, Json], caminho: Path) -> Papel:
    papel = campo_texto(registro, "papel", caminho)
    if papel not in {p.value for p in Papel}:
        mensagem = f"{caminho}: papel desconhecido {papel!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return Papel(papel)


def ler_json(caminho: Path) -> Json:
    """O arquivo é escrito por nós e, depois, pela tradução: valida-se tudo o que se lê."""
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))  # pyright: ignore[reportAny]  # motivo: o json devolve Any; Json é o que o formato garante, e cada campo é validado ao ser lido
    # Todo ValueError (JSON quebrado, texto que não é UTF-8, inteiro de mais de 4.300
    # algarismos) e o RecursionError (JSON aninhado demais) viram erro com o caminho: sem
    # ele, a CLI mostrava a mensagem crua ou um traceback (A6 da auditoria; N5 da pós).
    except (ValueError, RecursionError) as erro:
        mensagem = f"{caminho}: JSON inválido ({type(erro).__name__}: {erro})"
        raise PastaDeTrabalhoInvalidaError(mensagem) from erro


def objeto(valor: Json, caminho: Path) -> dict[str, Json]:
    if not isinstance(valor, dict):
        mensagem = f"{caminho}: esperava um objeto, veio {valor!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return valor


def lista(valor: Json, caminho: Path) -> list[Json]:
    if not isinstance(valor, list):
        mensagem = f"{caminho}: esperava uma lista, veio {valor!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return valor


def campo_texto(registro: dict[str, Json], chave: str, caminho: Path) -> str:
    return como_texto(registro.get(chave), chave, caminho)


def como_texto(valor: Json, chave: str, caminho: Path) -> str:
    if not isinstance(valor, str):
        mensagem = f"{caminho}: {chave!r} devia ser texto, veio {valor!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return valor


def campo_inteiro(registro: dict[str, Json], chave: str, caminho: Path) -> int:
    valor = registro.get(chave)
    if not isinstance(valor, int) or isinstance(valor, bool):
        mensagem = f"{caminho}: {chave!r} devia ser número inteiro, veio {valor!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return valor


def grupo_do_registro(registro: dict[str, Json], caminho: Path) -> Grupo:
    """Um grupo da resposta da adaptação: as fontes e exatamente um de `texto`, `igual` e
    `descarte` (ADR-0009). `omitidos` e `corrigidos` só valem com `texto`."""
    fontes = tuple(
        como_texto(item, "fontes", caminho) for item in lista(registro.get("fontes"), caminho)
    )
    if not fontes:
        mensagem = f"{caminho}: 'fontes' vazio no grupo: {registro!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    tipos = [tipo for tipo in TipoDoGrupo if tipo.value in registro]
    if len(tipos) != 1:
        mensagem = (
            f"{caminho}: o grupo tem de ter um só de 'texto', 'igual' e 'descarte': {registro!r}"
        )
        raise PastaDeTrabalhoInvalidaError(mensagem)
    for chave in ("omitidos", "corrigidos"):
        if chave in registro and tipos[0] is not TipoDoGrupo.TEXTO:
            mensagem = f"{caminho}: {chave!r} só vale no grupo com 'texto': {registro!r}"
            raise PastaDeTrabalhoInvalidaError(mensagem)
    return _grupo_do_tipo(tipos[0], fontes, registro, caminho)


def _grupo_do_tipo(
    tipo: TipoDoGrupo, fontes: tuple[str, ...], registro: dict[str, Json], caminho: Path
) -> Grupo:
    if tipo is TipoDoGrupo.IGUAL:
        if registro["igual"] is not True:
            mensagem = f"{caminho}: 'igual' só vale true: {registro!r}"
            raise PastaDeTrabalhoInvalidaError(mensagem)
        return Grupo(fontes, tipo)
    if tipo is TipoDoGrupo.DESCARTE:
        return Grupo(fontes, tipo, descarte=campo_texto(registro, "descarte", caminho))
    if not isinstance(valores := registro["texto"], list):
        mensagem = f"{caminho}: 'texto' devia ser uma lista de parágrafos, veio {valores!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    if not valores:
        # A2 da auditoria: sem parágrafo, o `montar` tirava as fontes sem descarte nem motivo.
        mensagem = f"{caminho}: 'texto' vazio no grupo; o que sai do áudio é descarte: {registro!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    paragrafos = tuple(como_texto(item, "texto", caminho) for item in valores)
    omitidos = tuple(
        _omitido(objeto(item, caminho), caminho)
        for item in lista(registro.get("omitidos", []), caminho)
    )
    corrigidos = tuple(
        _correcao(objeto(item, caminho), caminho)
        for item in lista(registro.get("corrigidos", []), caminho)
    )
    return Grupo(fontes, tipo, texto=paragrafos, omitidos=omitidos, corrigidos=corrigidos)


def _omitido(registro: dict[str, Json], caminho: Path) -> Omitido:
    return Omitido(
        campo_texto(registro, "termo", caminho), campo_texto(registro, "motivo", caminho)
    )


def _correcao(registro: dict[str, Json], caminho: Path) -> Correcao:
    """A correção do original: o trecho errado das fontes, o certo e a página que o prova."""
    pagina = campo_inteiro(registro, "pagina", caminho)
    if pagina < 1:
        mensagem = f"{caminho}: 'pagina' devia ser 1 ou mais, veio {pagina!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    de, para = campo_texto(registro, "de", caminho), campo_texto(registro, "para", caminho)
    # O trecho vazio "está" em qualquer texto, e a correção igual não corrige nada (auditoria).
    for chave, trecho in (("de", de), ("para", para)):
        if not trecho.strip():
            mensagem = f"{caminho}: {chave!r} vazio na correção: {registro!r}"
            raise PastaDeTrabalhoInvalidaError(mensagem)
    if de == para:
        mensagem = f"{caminho}: correção com 'de' igual a 'para': {registro!r}"
        raise PastaDeTrabalhoInvalidaError(mensagem)
    return Correcao(de, para, pagina)
