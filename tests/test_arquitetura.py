# SPDX-License-Identifier: GPL-3.0-or-later
"""Fitness functions: cada teste verifica uma decisão de docs/adr/, não o domínio.

Falha aqui quer dizer que a arquitetura foi atravessada, não que a feature quebrou.
Ao mudar um limite, mude também o ADR: número sem registro não governa nada.
A direção das camadas fica no import-linter (`[tool.importlinter]`, ADR-0002), que
também enxerga import relativo; este arquivo cobre o que ele não expressa.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PACOTE = "earbook"
SRC = RAIZ / "src" / PACOTE

# ADR-0001: biblioteca de terceiro só no adaptador; o domínio fica testável sem nada.
TERCEIROS_PERMITIDOS: dict[str, set[str]] = {
    "dominio": set(),
    "adaptadores": {"lxml", "pdfminer"},  # ADR-0004: PDF só pelo adaptador
    "comandos": set(),
}
# ADR-0001: o Python não chama o LLM nem a rede; quem traduz é o Claude Code.
MODULOS_PROIBIDOS = {"subprocess", "socket", "http", "urllib.request", "requests", "httpx"}
LIMITE_LINHAS_ARQUIVO = 400  # ADR-0001, driver de legibilidade para agente
LIMITE_LINHAS_FUNCAO = 40  # teto duro; o alvo no AGENTS.md é 20
SPDX = "# SPDX-License-Identifier: GPL-3.0-or-later"


def _arquivos() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def _relativo(caminho: Path) -> str:
    return caminho.relative_to(RAIZ).as_posix()


def _camada(caminho: Path) -> str | None:
    partes = caminho.relative_to(SRC).parts
    return partes[0] if len(partes) > 1 else None


def _imports(caminho: Path) -> list[tuple[str, int]]:
    """(nome completo do módulo importado, linha) de cada import do arquivo."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    nomes: list[tuple[str, int]] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes += [(alias.name, no.lineno) for alias in no.names]
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            nomes.append((no.module, no.lineno))
    return nomes


def test_terceiros_so_entram_pelo_adaptador() -> None:
    violacoes: list[str] = []
    for caminho in _arquivos():
        camada = _camada(caminho) or ""
        permitidos = TERCEIROS_PERMITIDOS.get(camada, set())
        for nome, linha in _imports(caminho):
            raiz = nome.split(".")[0]
            if raiz in sys.stdlib_module_names or raiz == PACOTE or raiz in permitidos:
                continue
            violacoes.append(f"{_relativo(caminho)}:{linha} — '{camada}' importa '{nome}'")
    assert not violacoes, "\n" + "\n".join(violacoes)


def test_nenhum_modulo_chama_processo_ou_rede() -> None:
    violacoes = [
        f"{_relativo(caminho)}:{linha} — importa '{nome}'"
        for caminho in _arquivos()
        for nome, linha in _imports(caminho)
        if any(nome == p or nome.startswith(f"{p}.") for p in MODULOS_PROIBIDOS)
    ]
    assert not violacoes, "\n" + "\n".join(violacoes)


def test_arquivos_cabem_em_uma_leitura() -> None:
    grandes = [
        f"{_relativo(c)} — {n} linhas (limite {LIMITE_LINHAS_ARQUIVO})"
        for c in _arquivos()
        if (n := len(c.read_text(encoding="utf-8").splitlines())) > LIMITE_LINHAS_ARQUIVO
    ]
    assert not grandes, "\n" + "\n".join(grandes)


def test_funcoes_dentro_do_teto() -> None:
    longas: list[str] = []
    for caminho in _arquivos():
        for no in ast.walk(ast.parse(caminho.read_text(encoding="utf-8"))):
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                tamanho = (no.end_lineno or no.lineno) - no.lineno + 1
                if tamanho > LIMITE_LINHAS_FUNCAO:
                    longas.append(f"{_relativo(caminho)}:{no.lineno} — {no.name}(): {tamanho}")
    assert not longas, "\n" + "\n".join(longas)


def test_todo_arquivo_python_declara_a_licenca() -> None:
    arquivos = _arquivos() + sorted((RAIZ / "tests").glob("*.py"))
    sem_spdx = [
        _relativo(c) for c in arquivos if not c.read_text(encoding="utf-8").startswith(SPDX)
    ]
    assert not sem_spdx, f"sem '{SPDX}' na primeira linha:\n" + "\n".join(sem_spdx)


def test_so_o_adaptador_de_pdf_importa_o_pdfminer() -> None:
    """ADR-0004: a biblioteca de PDF entra por um módulo só, para poder sair por ele."""
    importadores = sorted(
        _relativo(caminho)
        for caminho in _arquivos()
        if any(nome.split(".")[0] == "pdfminer" for nome, _ in _imports(caminho))
    )
    assert importadores == ["src/earbook/adaptadores/pdf.py"]
