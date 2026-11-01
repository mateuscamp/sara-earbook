# 0002 — Adotar o trilho python-on-rails, com dívida zero e um desvio no CLI

**Status:** Aceito
**Data:** 2026-11-01
**Driver ★:** legibilidade para agente (ADR-0001): o código é escrito por agente, e o portão é o que fecha os atalhos dele

## Contexto

Com o `preparar` implementado (ADR-0001), surgiu a skill `python-on-rails`. Ela troca
conselho por ferramenta que reprova: basedpyright estrito, ruff com regras de segurança e
de exceção, import-linter, pytest estrito, `uv audit` e um portão único. Em 2026-11-01, o
trilho medido sobre o projeto numa cópia descartável deu 21 reprovações do ruff e 195 do
basedpyright. Com os stubs do lxml (`types-lxml`), as do basedpyright caíram para 48. O
import-linter e a suíte passaram.

Quantum atual: 1 (CLI local + pasta de trabalho em arquivos).

## Alternativas consideradas

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| Corrigir A1–A5 da auditoria antes e ligar o trilho depois | fecha os defeitos mais cedo | os mesmos arquivos são mexidos duas vezes, e as correções nascem fora do portão | retrabalho |
| Trilho com linha de base (`--writebaseline`, `--add-noqa`) | não mexe no código agora | um ADR de dívida e um prazo para cerca de 70 reprovações pequenas | cerimônia maior que a dívida |
| **Trilho antes, com dívida zero** | as correções já nascem sob o portão estrito; não há linha de base | uma rodada de ajustes mecânicos antes das correções | — |

## Decisão

- O `pyproject.toml` recebe o trilho inteiro, com `pythonVersion` e `.python-version` em 3.14.
- `make check` chama `scripts/portao.sh`, que é o mesmo comando do hook Stop (`.claude/settings.json`) e do CI quando ele existir.
- A direção das camadas sai de `tests/test_arquitetura.py` e passa ao import-linter (contrato `layers`), que também enxerga import relativo. Isso fecha uma brecha apontada pela auditoria (A9). O `test_arquitetura.py` fica com o que o import-linter não expressa: a lista de terceiros por camada, os módulos proibidos, os tamanhos e o SPDX.
- O tipo `_Element` do lxml é privado. Ele entra uma vez só, em `adaptadores/xml_seguro.py`, com supressão nomeada e motivo, e o resto do código usa o alias `Elemento`. O mesmo módulo passa a ser o único dono do parser seguro, que antes estava duplicado.
- Dependências de desenvolvimento novas:
  - `basedpyright`, `import-linter` e `ruff`: são o portão.
  - `types-lxml`: os stubs do lxml, mantidos por Abel Cheung. Sem eles, 147 avisos `reportUnknown*` vinham só da falta de tipo do lxml.

### Desvio declarado: `print` no CLI

`src/ai_book/comandos/cli.py` ganha `per-file-ignores = ["T201"]`. A regra do trilho é
"`logging` no lugar de `print` **fora da camada de interface**", e o CLI é essa camada: o
resumo do `preparar` é texto para humano, não evento de log. Trocar por
`sys.stdout.write` passaria no portão sem resolver nada; usar `logging` poria nível e
formato de log no meio do texto para humano.

## Consequências

**Ganha:** o agente não consegue mais chegar ao verde com `Any`, `except` amplo, import relativo, supressão sem motivo ou dependência com vulnerabilidade conhecida. Além disso, o hook Stop reprova antes de ele dizer "pronto".

**Perde:**
- `requires-python` passa a >=3.14, e quem clonar o repositório público precisa do Python 3.14.
- O portão fica mais lento: o basedpyright leva alguns segundos e o `uv audit` precisa de rede.
- Tudo o que lê JSON vai precisar de validação na borda. Quando o `conferir` ler a tradução do agente, isso provavelmente vira `pydantic` (dependência nova, com ADR próprio).

**Aceito conscientemente:** a etapa "supressão sem motivo" usa `git ls-files` e não enxerga arquivo que ainda não está no git. Até o primeiro commit, ela não confere nada.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| O trilho inteiro | `make check` → `scripts/portao.sh` | agente, hook Stop, CI | qualquer etapa reprova |
| Camadas e domínio sem `lxml` | import-linter (`[tool.importlinter]`) | portão | contrato quebrado |
| Desvio do `print` só no CLI | `per-file-ignores` restrito a `cli.py` | portão | `print` em outro arquivo |

Regra derivada no `AGENTS.md`: seção "Python".

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-01 · Aprovado em: 2026-11-01
