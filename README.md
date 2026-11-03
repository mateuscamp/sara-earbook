# earbook

Prepara livros para **ouvir** no ElevenReader. Tira do EPUB o que o leitor de voz leria e não é
do livro e, quando o livro é em inglês, traduz para pt-BR. PDF com camada de texto entra pelo
comando `importar-pdf` ([ADR-0004](docs/adr/0004-pdf-entra-como-comando-importar-pdf.md)).

O repositório se chama sara-earbook desde 2026-11-02; o pacote e o comando continuam
`earbook`.

O Claude Code comanda o trabalho: monta o glossário, traduz e revisa. O CLI `earbook` faz o que
é mecânico e verificável: abre o EPUB, quebra o texto em segmentos, limpa o que atrapalha o
ouvido, exporta os lotes de tradução, confere e remonta o livro. O Python nunca chama o modelo.
A decisão está no [ADR-0001](docs/adr/0001-reescrever-com-claude-code-orquestrando.md).

## O que sai do áudio

- O cabeçalho e o número de página. O parágrafo partido pela troca de página volta a ser um só.
- O marcador de nota no meio da frase ("…disse ele.12"). O texto da nota vai para o fim do
  capítulo, sob "Notas".
- O trecho que seria lido duas vezes (`<p>` dentro de `<blockquote>`).
- A página de direitos autorais.
- O bloco de código e o índice remissivo que o EPUB marca como tais. Sai também o parágrafo
  idêntico em metade ou mais dos arquivos do livro, como a marca d'água "OceanofPDF.com"
  ([ADR-0008](docs/adr/0008-codigo-e-indice-saem-do-audio.md)).
- A capitular deslocada, que volta para a palavra quando o próprio livro prova que a palavra
  existe ([ADR-0007](docs/adr/0007-a-proxima-traducao-sem-trabalho-a-mao.md)).

Nada sai em silêncio: cada remoção fica registrada em `limpeza.json`, com o segmento de origem.

## Uso

```bash
uv sync
uv run earbook preparar livro.epub
```

O comando `preparar` cria `livro.earbook/` (ou onde `--pasta` mandar) com:

- `livro.json`: os metadados, os capítulos na ordem do spine e o texto que ficou fora de
  segmento.
- `segmentos/cNNN.json`: os segmentos de cada capítulo como vieram do EPUB. Cada um tem `id`,
  `texto`, `notas` e `papel`, que pode ser `titulo`, `paragrafo`, `nota`, `item`, `celula`,
  `citacao`, `codigo` ou `indice`.
- `limpos/cNNN.json`: os mesmos segmentos, sem o que a limpeza tirou. É o que segue na esteira.
- `limpeza.json`, com cinco listas:
  - `remocoes`: cada segmento que saiu;
  - `aparos`: cada cabeçalho aparado do fim de um parágrafo;
  - `juncoes`: cada parágrafo partido que foi juntado ao anterior;
  - `capitulares`: cada capitular devolvida;
  - `suspeitas`: os suspeitos que ficaram no texto para decidir.
- `epub/`: o EPUB extraído, com cada segmento marcado no XHTML por `data-earbook`.

### Conferir e montar

```bash
uv run earbook conferir livro.earbook
uv run earbook montar livro.earbook
```

O `conferir` cobra que nenhum trecho sumiu, sobrou ou se repetiu entre o EPUB original e a
pasta de trabalho, e o `montar` recusa o livro quando ele acha problema
([ADR-0005](docs/adr/0005-montar-substitui-o-texto-no-epub-original.md)). O `montar` grava
`livro.pronto.epub` (ou onde `--epub` mandar): o EPUB original, com o texto limpo no lugar, sem
as marcas de trabalho e com cada nota de rodapé no fim do capítulo.

Opções dos dois:

- `--capitulo cNNN` (só no `conferir`): só os problemas daquele capítulo.
- `--original`: o texto limpo no idioma do original. É para ouvir a limpeza antes de traduzir,
  e o `montar` grava `livro.original.epub`.
- `--amostra`: no livro em tradução, só o que já foi traduzido. O `montar` grava
  `livro.amostra.epub`.

### Traduzir

```bash
uv run earbook traduzir livro.earbook
```

O `traduzir` divide cada capítulo do texto limpo em lotes de até ~2 mil palavras (`--palavras`)
e grava o pedido de cada lote em `pedidos/`. Ele lista em `nomes.json` os candidatos a nome
próprio que ainda não estão no glossário e cria `decisoes.md`, para as decisões do livro. Rodar
de novo não refaz nada: é assim que se retoma
([ADR-0006](docs/adr/0006-traduzir-por-lote-com-pedido-e-glossario.md)).

Quem traduz é o Claude Code. O roteiro está na skill
[`traduzir-livro`](.claude/skills/traduzir-livro/SKILL.md), em quatro passos:

1. o glossário (`glossario.json`);
2. as decisões do livro;
3. um subagente [`tradutor`](.claude/agents/tradutor.md) por capítulo, em paralelo;
4. a rodada de correção.

Cada tradutor grava a resposta do lote em `traduzidos/`. O termo que ele decidiu fora do
glossário vai para `termos/`.

No livro em tradução, o `conferir` cobra mais quatro coisas:
- cada segmento traduzido uma vez;
- nenhum texto que ficou em inglês;
- cada nome e termo do glossário traduzido sempre do mesmo jeito;
- nenhuma tradução velha, isto é, de um texto de origem que mudou depois do pedido.

O `montar` grava só a tradução, nunca as duas línguas, porque o leitor de voz leria as duas. O
livro sai declarado em pt-BR.

### Roteiro de escuta

```bash
uv run earbook minuto livro.earbook c005-s0288 c006-s0022
```

Diz em que minuto da escuta cai cada segmento. Conta a 160 palavras por minuto, pelo texto que
se ouve: a tradução, quando existe.

### PDF

```bash
uv run earbook importar-pdf livro.pdf --idioma pt-BR
uv run earbook preparar livro.epub
```

O `importar-pdf` grava `livro.epub` ao lado do PDF (ou onde `--epub` mandar), com o título e o
autor do metadado do PDF (ou os de `--titulo` e `--autor`). O que ele faz:

- tira o número de página e o cabeçalho repetido, pela posição na página;
- junta as linhas em parágrafos e devolve inteira a palavra partida no fim da linha;
- lê a página em duas colunas coluna por coluna, pela calha entre elas, quando os dois lados
  são texto corrido. A tabela continua lida linha a linha;
- divide os capítulos pelo tamanho dos títulos.

O EPUB serve para ouvir, não para ler na tela. Sai sem imagem e sem estilo, e cada linha de
tabela vira um parágrafo. O índice remissivo e o bloco de código do PDF ainda são lidos. PDF
escaneado, sem camada de texto, é recusado, porque não há OCR.

## Desenvolvimento

```bash
make check
```

É o portão: lock, formato, lint, tipos, fronteiras entre módulos, testes e `uv audit`. As
decisões de arquitetura estão em [`docs/adr/`](docs/adr/), e as regras para quem mexe no código
(gente ou agente) estão no [`AGENTS.md`](AGENTS.md).

## Licença

GPL-3.0-or-later. O [ebook-GPT-translator](https://github.com/jesselau76/ebook-GPT-translator)
(MIT) serviu de referência de leitura; nenhum código dele foi copiado.
