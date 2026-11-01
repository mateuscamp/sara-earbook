# ai-book

Traduz ebooks (EPUB, inglês → pt-BR) para **ouvir** no ElevenReader.

O Claude Code comanda o trabalho: monta o glossário, traduz e revisa. O CLI
`ai-book` faz o que é mecânico e verificável: abre o EPUB, quebra o texto em
segmentos, confere a tradução e remonta o livro. A decisão está em
[docs/adr/0001](docs/adr/0001-reescrever-com-claude-code-orquestrando.md).

## Uso

```bash
uv sync
uv run ai-book preparar livro.epub
```

O comando `preparar` cria `livro.ai-book/` com:

- `livro.json`: metadados, capítulos na ordem do spine e texto que ficou fora de segmento.
- `segmentos/cNNN.json`: os segmentos de cada capítulo, cada um com `id`, `papel` (`titulo`, `paragrafo` ou `nota`), `texto` e `notas`.
- `epub/`: o EPUB extraído, com cada segmento marcado no XHTML por `data-ai-book`.

## Licença

GPL-3.0-or-later. O [ebook-GPT-translator](https://github.com/jesselau76/ebook-GPT-translator)
(MIT) serviu de referência de leitura; nenhum código dele foi copiado.
