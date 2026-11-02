# earbook

Prepara livros para **ouvir** no ElevenReader: tira do EPUB o que o leitor de voz
leria e não é do livro (cabeçalho de página, parágrafo partido, capitular deslocada) e,
quando o livro é em inglês, traduz para pt-BR. PDF com camada de texto entra pelo comando
`importar-pdf` ([ADR-0004](docs/adr/0004-pdf-entra-como-comando-importar-pdf.md)).

O repositório se chama sara-earbook desde 2026-11-02; o pacote e o comando continuam
`earbook`.

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
- `limpos/cNNN.json`: os mesmos segmentos, sem o que a limpeza para o ouvido tirou (por exemplo, o cabeçalho de página e a página de direitos autorais). É o que segue na esteira.
- `limpeza.json`: cada segmento que saiu (`remocoes`), cada cabeçalho aparado do fim de um parágrafo (`aparos`), cada parágrafo partido que foi juntado ao anterior (`juncoes`) e os suspeitos que ficaram no texto para decidir (`suspeitas`).
- `epub/`: o EPUB extraído, com cada segmento marcado no XHTML por `data-earbook`.

Depois de limpo (e, no livro em inglês, traduzido), o livro volta a ser EPUB:

```bash
uv run earbook conferir livro.earbook
uv run earbook montar livro.earbook
```

O `conferir` cobra que nenhum trecho sumiu, sobrou ou se repetiu entre o EPUB original e a
pasta de trabalho; o `montar` recusa o livro quando ele acha problema. O `montar` grava
`livro.pronto.epub` (ou onde `--epub` mandar): o EPUB original, com o texto limpo no lugar,
sem as marcas de trabalho e com cada nota de rodapé no fim do capítulo, sob "Notas".

### PDF

```bash
uv run earbook importar-pdf livro.pdf --idioma pt-BR
uv run earbook preparar livro.epub
```

O `importar-pdf` grava `livro.epub` ao lado do PDF (ou onde `--epub` mandar), com o título
e o autor do metadado do PDF (ou os de `--titulo` e `--autor`). Ele tira
número de página e cabeçalho repetido pela posição na página, junta as linhas em
parágrafos, devolve inteira a palavra partida no fim da linha e divide os capítulos pelo
tamanho dos títulos. O EPUB serve para ouvir, não para ler na tela: sai sem imagem e sem
estilo, e cada linha de tabela vira um parágrafo. PDF escaneado, sem camada de texto, é
recusado (não há OCR).

## Licença

GPL-3.0-or-later. O [ebook-GPT-translator](https://github.com/jesselau76/ebook-GPT-translator)
(MIT) serviu de referência de leitura; nenhum código dele foi copiado.
