#!/usr/bin/env bash
# Portão único do projeto Python: o mesmo comando para o agente, o hook Stop e o CI.
# Aprova só se tudo passar; a primeira etapa que reprova encerra com a saída dela.
#   scripts/portao.sh            completo (make check e CI)
#   scripts/portao.sh --rapido   sem a auditoria de dependências, que precisa de rede (hook Stop)
# Copiado da skill python-on-rails.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
rapido=false
[[ "${1:-}" == "--rapido" ]] && rapido=true

etapa() { printf '\n== %s\n' "$1"; }

etapa "lock em dia com o pyproject"
uv lock --check

etapa "formatação"
uv run --locked ruff format --check .

etapa "lint"
uv run --locked ruff check .

etapa "supressão sem motivo"
# Toda supressão diz por quê na mesma linha: `# noqa: S603  # motivo: ...`.
# Supressão de arquivo inteiro (`# ruff: noqa`, `# pyright: basic`) segue a mesma regra.
padrao='noqa|pyright: *(ignore|basic|standard|off)|type: *ignore'
if sem_motivo="$(git ls-files '*.py' | xargs -r grep -nE "$padrao" | grep -v 'motivo:')"; then
  printf '%s\n' "$sem_motivo"
  echo "Supressão sem '# motivo:' na mesma linha. Corrija o código ou escreva o motivo."
  exit 1
fi

etapa "tipos"
uv run --locked basedpyright

if grep -q '^\[tool.importlinter\]' pyproject.toml; then
  etapa "fronteiras"
  uv run --locked lint-imports
fi

etapa "testes"
uv run --locked pytest

if ! $rapido; then
  etapa "dependências com vulnerabilidade conhecida"
  uv audit --locked --preview-features audit
fi

printf '\nPortão aprovado.\n'
