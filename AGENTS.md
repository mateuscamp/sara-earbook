# ai-book

Traduzir ebooks do inglês para pt-BR e **ouvir** o resultado no ElevenReader.
O produto final é áudio, não página: o critério de qualidade é o que soa bem,
não o que fica bonito na tela.

Arquitetura: monólito modular, 1 quantum (CLI local + pasta de trabalho em arquivos).
ADRs em `docs/adr/`. O Claude Code traduz; o Python nunca chama o LLM (ADR-0001).

## Decisões (2026-10-31)

- Esteira (ADR-0003): `preparar → limpar → [traduzir] → conferir → montar`. Livro em inglês é traduzido para pt-BR; livro em português só é preparado para o ouvido.
- A limpeza nunca apaga em silêncio: toda remoção fica em `limpeza.json`, com o ID do segmento de origem.
- Entrada: EPUB. PDF entra pelo comando `importar-pdf` (ADR-0004), só para ouvir: sem fidelidade visual, sem OCR, e a biblioteca de PDF só em `adaptadores/`.
- Motor: o Claude Code na sessão, pela assinatura, com um subagente por capítulo. O limite de uso conta.
- Notas de rodapé: o marcador sai do meio da frase e o texto da nota vai para o fim do capítulo.
- Saída: um EPUB **só com a tradução**. O modo bilíngue é proibido, porque o TTS lê as duas línguas.
- Licença: GPL-3.0-or-later; repositório público. O ebook-GPT-translator (MIT) é só referência de leitura.

## Processo (pedido do Mateus, 2026-10-31)

- A skill `arquitetura-ai-first` orienta toda decisão estrutural; fronteira nova exige ADR antes do código.
- A skill `code-audit` roda ao fim de toda implementação de código.
- O asset se julga **ouvindo no ElevenReader**, não lendo lado a lado.

## Livros de medição (em `livros/`, fora do git; o original fica em `~/Documentos/livros/ingles/`)

- Huxley, *The Doors of Perception*: notas de rodapé e sumário. Serve de régua de tradução, porque existe edição brasileira (*As Portas da Percepção*).
- Rosenberg, *Tides of Darkness*: convertido de PDF, com cabeçalho de página, parágrafo partido e capitular perdida. Muito nome próprio de lugar e personagem a preservar (glossário).
- Mudou a limpeza ou a segmentação? Rode `ai-book preparar` nos dois e compare as contagens com as do ADR-0003.

## Comandos

- Setup: `uv sync`.
- Portão: `make check` (`scripts/portao.sh`: lock, formato, lint, supressão, tipos, fronteiras, testes, `uv audit`). O hook Stop roda o mesmo. Rodar antes de declarar qualquer tarefa concluída e mostrar a saída.
- Uso: `uv run ai-book preparar livro.epub` → `livro.ai-book/`.

## Fronteiras (ADR-0001)

Verificadas por ferramenta (import-linter e `tests/test_arquitetura.py`):
- `dominio/` importa só stdlib. `adaptadores/` importa `dominio/` e `lxml`. `comandos/` importa os dois.
- Proibido em todo o pacote: `subprocess`, `socket`, `http`, `requests`, `httpx`.
- Arquivo ≤ 400 linhas; função ≤ 20 linhas (teto 40); primeira linha de todo `.py` é o SPDX.

Verificadas só em revisão (`code-audit`):
- Só `adaptadores/pasta_de_trabalho.py` conhece o layout da pasta de trabalho.
- EPUB é entrada não confiável: XML só pelo `PARSER_SEGURO` de `adaptadores/xml_seguro.py`; nenhum caminho sai da pasta de trabalho.

## O que atrapalha o ouvido (alvo da limpeza)

- Marcador de nota no meio da frase ("...disse ele.12"). Feito no `preparar`.
- Trecho lido duas vezes (`<p>` dentro de `<blockquote>`). Feito no `preparar`.
- Número de página, cabeçalho repetido, sumário duplicado, índice remissivo.
- Algarismo romano em título de capítulo ("Chapter IV").
- Abreviação, URL, tabela e legenda de imagem.
- Nome próprio traduzido de um jeito num capítulo e de outro no seguinte (precisa de glossário).

## Ciclo de mudança (TDD)

1. Vermelho: um teste, um comportamento, nomeado pelo comportamento. Ver falhar NA ASSERÇÃO.
2. Verde: o mínimo que passa, sem editar o teste. Rodar a suíte inteira.
3. Refatorar com a suíte verde; depois `make check`.

- Bug: primeiro o teste de regressão visto falhando, depois a correção.
- O relatório mostra a linha de falha do vermelho e o resumo do verde.
- Proibido para ficar verde: mudar asserção, `skip`/`xfail`, apagar teste, asserção mais fraca, mock do sujeito.
- EPUB de teste é montado em código (`tests/livro_de_teste.py`), nunca binário no repositório.

## Python (trilho python-on-rails, ADR-0002)

- Dependência entra com `uv add`, nunca `pip install`, e sempre com justificativa no relatório (o que faz que a stdlib não faz, quem mantém). Confira o nome exato do pacote.
- Proibido mexer em `[tool.ruff]`, `[tool.basedpyright]`, `[tool.pytest]` ou `[tool.importlinter]`, e acrescentar ignore, exclude ou linha de base. Regra parece errada? Diga no relatório e pare.
- Supressão só com regra e motivo na mesma linha: `# pyright: ignore[reportX]  # motivo: ...`. `cast` também é supressão.
- Sem `Any` e sem `dict` solto entre funções: miolo em `@dataclass(frozen=True)`. `Any` de biblioteca (`json.loads`) é validado na borda.
- Exceção própria com sufixo `Error` e o valor recebido na mensagem (`mensagem = f"..."; raise XError(mensagem)`). Nada de `except` amplo; relançar com `from`.
- `print` só em `comandos/cli.py` (desvio do ADR-0002). Fora dele, `logging`.
- Valor de retorno ignorado de propósito vai para `_`.

## Estilo

- Código, nomes e mensagens em português. Nomes grepáveis; nada de `utils`, `helper`, `data`.
- Comentário diz o porquê e cita o ADR quando a linha existe por causa dele. Não apagar em refactor.
- Mensagem de erro traz o valor recebido (caminho, href, membro do zip).

## Estrutura

```
src/ai_book/
  dominio/      segmento.py (Segmento, IDs), trabalho.py (LivroPreparado), limpeza.py (regras do ouvido)
  adaptadores/  xml_seguro.py (parser), pacote_epub.py (zip + OPF), xhtml.py, pasta_de_trabalho.py
  comandos/     preparar.py, cli.py
tests/          test_<módulo>.py, test_arquitetura.py, livro_de_teste.py
```
