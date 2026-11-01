# earbook

Prepara livros para **ouvir** no ElevenReader: tira do EPUB o que o leitor de voz
leria e não é do livro (cabeçalho de página, parágrafo partido, capitular deslocada) e,
quando o livro é em inglês, traduz para pt-BR. PDF entra pelo comando `importar-pdf`
(em construção, ADR-0004).

O Claude Code comanda o trabalho: monta o glossário, traduz e revisa. O CLI
`earbook` faz o que é mecânico e verificável: abre o EPUB, quebra o texto em
segmentos, confere a tradução e remonta o livro. A decisão está em
[docs/adr/0001](docs/adr/0001-reescrever-com-claude-code-orquestrando.md).

## Uso

```bash
uv sync
uv run earbook preparar livro.epub
```

O comando `preparar` cria `livro.earbook/` com:

- `livro.json`: metadados, capítulos na ordem do spine e texto que ficou fora de segmento.
- `segmentos/cNNN.json`: os segmentos de cada capítulo como vieram do EPUB, cada um com `id`, `papel` (`titulo`, `paragrafo`, `nota`, `item`, `celula` ou `citacao`), `texto` e `notas`.
- `limpos/cNNN.json`: os mesmos segmentos, sem o que a limpeza para o ouvido tirou (por exemplo, o cabeçalho de página). É o que segue na esteira.
- `limpeza.json`: cada segmento que saiu (`remocoes`), cada cabeçalho aparado do fim de um parágrafo (`aparos`), cada parágrafo partido que foi juntado ao anterior (`juncoes`) e os suspeitos que ficaram no texto para decidir (`suspeitas`).
- `epub/`: o EPUB extraído, com cada segmento marcado no XHTML por `data-earbook`.

## Licença

GPL-3.0-or-later. O [ebook-GPT-translator](https://github.com/jesselau76/ebook-GPT-translator)
(MIT) serviu de referência de leitura; nenhum código dele foi copiado.
