# earbook

Prepara livros para **ouvir** no ElevenReader. Tira do EPUB o que o leitor de voz leria e não é
do livro e, quando o livro é em inglês, traduz para pt-BR. O livro didático em português pode ser
adaptado para o ouvido: a lista vira frase, o Quadro vira parágrafo e a citação sai
([ADR-0009](docs/adr/0009-adaptar-reescreve-por-grupo-e-o-conferir-cobra-a-fidelidade.md)). PDF com camada de texto entra pelo
comando `importar-pdf` ([ADR-0004](docs/adr/0004-pdf-entra-como-comando-importar-pdf.md)).

O repositório se chama sara-earbook desde 2026-11-02; o pacote e o comando continuam
`earbook`.

O Claude Code comanda o trabalho: monta o glossário, traduz e revisa. O CLI `earbook` faz o que
é mecânico e verificável: abre o EPUB, quebra o texto em segmentos, limpa o que atrapalha o
ouvido, exporta os lotes de tradução, confere e remonta o livro. O Python nunca chama o modelo.
A decisão está no [ADR-0001](docs/adr/0001-reescrever-com-claude-code-orquestrando.md).

## O que sai do áudio

- O cabeçalho e o número de página. O parágrafo partido pela troca de página volta a ser um só,
  e a palavra partida no fim dele volta sem o hífen quando o livro a escreve inteira em outro
  lugar.
- O marcador de nota no meio da frase ("…disse ele.12"). O texto da nota vai para o fim do
  capítulo, sob "Notas". No PDF, sai também o número de referência sobrescrito ("wages.¹",
  "84%–90%.²,³", "et al.¹⁹⁴", "in 1934²²¹", "paciente»⁵²", "¹¹⁸. No"), pela letra menor e mais
  alta; o ano fica, e o expoente, a carga do íon e a unidade ao quadrado também. O número só
  depois de letra solta ou de outro número ("6 h¹⁴⁸", "0,62¹¹¹"), que na linha tem a cara de um
  expoente, sai na página que tem 3 chamadas ou mais
  ([ADR-0004](docs/adr/0004-pdf-entra-como-comando-importar-pdf.md)).
- No PDF, o texto que a página não pinta: o que um OCR leu dentro das figuras e gravou por cima
  delas, invisível ("1", "l", "o o o", "~ ~"). Sai na página em que o texto pintado é a maior
  parte; a página escaneada, cujo texto só existe nessa camada, fica
  ([ADR-0004](docs/adr/0004-pdf-entra-como-comando-importar-pdf.md)).
- No PDF, a tabela, o quadro e a figura: o rótulo em inglês ("TABLE 2.1", "• Figure 2.1",
  "FIGURE 1.1"), em português ou em espanhol ("Figura 1.2", "Quadro 1.1", "Tabela 8.1",
  "TABLA 2-1", "CUADRO 4-1"), as células, os rótulos do diagrama e a legenda, quando vêm em
  letra diferente da do corpo
  ([ADR-0004](docs/adr/0004-pdf-entra-como-comando-importar-pdf.md)). O "Quadro" e a "Tabela"
  com o rótulo em letra de título, do livro didático, ficam no lugar.
- No PDF, o texto girado: a tabela deitada na página e o rótulo de lado, que o leitor de PDF
  monta uma letra de cada coluna ("d u r n n n o o , i i t f…")
  ([ADR-0004](docs/adr/0004-pdf-entra-como-comando-importar-pdf.md)).
- No PDF, a página de lista inteira: o índice remissivo e o sumário (muitas linhas terminam em
  ", página"), o sumário sem número de página ou com o número sem vírgula (as páginas seguidas
  sem frase com 3 rótulos "CHAPTER N" ou mais) e a lista de colaboradores ("Nome, MD" ou
  "NOME, MD" e a afiliação, também na página vizinha com 2 nomes ou mais e na última, só de
  afiliação)
  ([ADR-0004](docs/adr/0004-pdf-entra-como-comando-importar-pdf.md)).
- No PDF, a bibliografia em letra menor que a do corpo: o trecho de linhas na letra das
  referências com 10 linhas de citação de periódico ou mais ("Lancet 269:259, 1955", "J Bone
  Joint Surg Br. 1980;62:358"), com o título logo antes e o cabeçalho das páginas de
  bibliografia entre elas. Sai antes da ordem de leitura, para a lista ao lado da prosa não se
  intercalar com ela. Sai com ele a lista de leitura sugerida que vem logo antes, na mesma letra
  e sob um título em letra de título, quando tem ao menos uma citação de periódico
  ([ADR-0004](docs/adr/0004-pdf-entra-como-comando-importar-pdf.md)).
- O trecho que seria lido duas vezes (`<p>` dentro de `<blockquote>`).
- A página de direitos autorais.
- O bloco de código e o índice remissivo que o EPUB marca como tais. Sai também o parágrafo
  idêntico em metade ou mais dos arquivos do livro, como a marca d'água "OceanofPDF.com"
  ([ADR-0008](docs/adr/0008-codigo-e-indice-saem-do-audio.md)).
- O índice remissivo sem marcação, como o do PDF importado: 10 parágrafos seguidos ou mais de
  termos seguidos do número da página ("Afetividade, 155-173"), com as letras do meio ("A", "B")
  e o título logo antes deles
  ([ADR-0008](docs/adr/0008-codigo-e-indice-saem-do-audio.md)). O índice curto fica.
- O destaque de margem que repete, palavra por palavra, uma frase do texto ao lado dele. A frase
  que ele partia volta inteira ([ADR-0008](docs/adr/0008-codigo-e-indice-saem-do-audio.md)). O
  destaque que resume ou reescreve a frase fica.
- A bibliografia no padrão ABNT ("ABDO, C. H. N. Diagnóstico… 1996."): 10 referências seguidas
  ou mais, com o título logo antes delas
  ([ADR-0008](docs/adr/0008-codigo-e-indice-saem-do-audio.md)). A bibliografia de outro padrão
  (APA), a lista curta e a bibliografia que o PDF partiu entre nota e parágrafo (a do
  Competente) ficam.
- As referências médicas no estilo Vancouver ("86. Adams MA, Hutton WC. … J Bone Joint Surg Br.
  1980;62:358–362."), uma por parágrafo ou coladas numa nota: a região de pedaços de referência
  com 10 citações de periódico ("ano;volume:página") ou mais, com os pedaços partidos pela página
  e o título logo antes ([ADR-0008](docs/adr/0008-codigo-e-indice-saem-do-audio.md)). A
  referência partida que a limpeza tinha juntado sai inteira, e cada pedaço fica em `remocoes`.
  A lista curta, com menos de 10 citações, fica; a prosa que cita "et al." também.
  A citação com o ano no fim ("1. Bedford PD: Lancet 269:259, 1955.") conta do mesmo jeito.
- A seção de questões de prova, do título até a última alternativa: o enunciado com a prova
  entre parênteses ("34.1 (TSA/2012) …") e as alternativas ("A. …", "b) …"), quando são metade
  dos parágrafos ou mais e há dois enunciados, ou um enunciado e um grupo de 3 alternativas. Sem
  enunciado de prova nada sai: a lista de letras no meio da prosa fica
  ([ADR-0008](docs/adr/0008-codigo-e-indice-saem-do-audio.md)).
- O título sem letra nem algarismo ("•", "---", "~"), resto de figura; o parágrafo que ele
  partia volta a ser um só. O título só de algarismo ("2012") e o de letra solta ("A") ficam
  ([ADR-0008](docs/adr/0008-codigo-e-indice-saem-do-audio.md)).
- O capítulo que você declarar: `preparar --sem-capitulo c006` tira o capítulo inteiro (a lista
  de autores, o sumário de papel, um anexo)
  ([ADR-0008](docs/adr/0008-codigo-e-indice-saem-do-audio.md)). No livro montado ele não
  aparece: nem o arquivo, nem o item do sumário
  ([ADR-0005](docs/adr/0005-montar-substitui-o-texto-no-epub-original.md)).
- O sumário de papel: a linha com 5 pontos seguidos e número no fim ("1. Introdução ……… 23"),
  quando o capítulo tem 5 ou mais. O título "Sumário", os títulos das partes e a linha sem
  pontilhado ficam
  ([ADR-0009](docs/adr/0009-adaptar-reescreve-por-grupo-e-o-conferir-cobra-a-fidelidade.md)).
- A propaganda: o título "Conheça também", com até 5 parágrafos até o próximo título. A propaganda
  com outro título fica
  ([ADR-0009](docs/adr/0009-adaptar-reescreve-por-grupo-e-o-conferir-cobra-a-fidelidade.md)).
- A capitular deslocada, que volta para a palavra quando o próprio livro prova que a palavra
  existe ([ADR-0007](docs/adr/0007-a-proxima-traducao-sem-trabalho-a-mao.md)). A letra que
  abre a frase antes de palavra em minúscula, como o artigo em "desejo. A resultante", fica
  onde está.

Nada sai em silêncio: cada remoção fica registrada em `limpeza.json`, com o segmento de origem.

## Uso

```bash
uv sync
uv run earbook preparar livro.epub
```

Para deixar um capítulo inteiro fora do áudio, declare-o pelo ID, quantas vezes precisar:

```bash
uv run earbook preparar livro.epub --sem-capitulo c006 --sem-capitulo c110
```

O ID é a posição do capítulo no livro (`c006` é o 6º arquivo do spine; `livro.json` lista todos,
com o arquivo de cada um). Cada segmento do capítulo fica em `limpeza.json`, com o motivo
"capítulo fora do áudio: pedido no preparar". O ID que o livro não tem é erro. O `montar` deixa
fora do EPUB todo capítulo que ficou sem texto, o declarado e o que uma regra esvaziou: sem o
arquivo, sem o item no sumário.

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

O capítulo que a limpeza deixou sem texto fica fora do EPUB montado, em qualquer modo: o que o
`preparar --sem-capitulo` tirou do áudio e o que uma regra esvaziou (o do índice remissivo, o que
era só bibliografia). O arquivo sai do pacote, do manifesto e do spine, e o item dele sai do
sumário (o `nav` e o `toc.ncx`); o item de dentro que aponta para outro capítulo sobe um nível. O
resumo diz quais ficaram de fora ("4 capítulos sem texto ficaram fora do EPUB: c006, c013, c110,
c111"), e o motivo de cada segmento deles está em `limpeza.json`. O capítulo que nunca teve texto
(a capa, a página só de imagem) continua no livro. O `montar` recusa o livro em que nenhum
capítulo ficaria com texto, e o sumário que ficaria sem item.

Opções dos dois:

- `--capitulo cNNN` (só no `conferir`): só os problemas daquele capítulo.
- `--original`: o texto limpo no idioma do original. É para ouvir a limpeza antes de traduzir,
  e o `montar` grava `livro.original.epub`.
- `--amostra`: no livro em tradução, só o que já foi traduzido; no livro em adaptação, só o que
  já foi adaptado. O `montar` grava `livro.amostra.epub`.

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

### Adaptar

```bash
uv run earbook adaptar livro.earbook
```

Só para livro em português. O `adaptar` divide cada capítulo em lotes de até ~2 mil palavras
(`--palavras`), que terminam antes de um título ou entre duas frases, e grava o pedido de cada
lote em `para-adaptar/`. Ele lista em `siglas.json` as siglas que ainda não estão no glossário,
com a forma por extenso que o livro dá, e cria `decisoes.md`. Rodar de novo não refaz nada
([ADR-0009](docs/adr/0009-adaptar-reescreve-por-grupo-e-o-conferir-cobra-a-fidelidade.md)).

Quem adapta é o Claude Code, um subagente [`adaptador`](.claude/agents/adaptador.md) por
capítulo, que lê a página do PDF original quando o lote tem Quadro. A resposta de cada lote vai
para `adaptados/`, como uma lista de grupos: as `fontes` (IDs vizinhos) e um destes:
- `texto`, os parágrafos que se ouvem no lugar delas: N segmentos viram M parágrafos;
- `igual`, quando o segmento fica como está;
- `descarte`, com o motivo: `repetido`, `rotulo` ou `decisao: <seção>`.

A sigla que vai por extenso entra no `glossario.json`, como o nome na tradução.

No livro em adaptação, o `conferir` cobra a fidelidade de cada grupo:
- cada segmento num grupo só, de fontes vizinhas, no lote que o pediu;
- cada número das fontes no texto, e nenhum número que elas não têm (o ano de citação, o rótulo
  "Quadro 27.1" e o ordinal "1." ficam fora da conta);
- cada termo raro das fontes (8 letras ou mais, em até 20 segmentos do livro) no texto, ou
  declarado em `omitidos`;
- o descarte `repetido` provado pelos grupos do lado;
- nada que só funciona no papel: `•`, "Quadro 27.1", "(Autor, ano)", "et al.", "p. ex.",
  pontilhado de sumário, linha de formulário e a sigla que o glossário manda por extenso.

O `omitidos` também aceita número, com motivo `citação`, `data`, `ordinal`, `página`, `potência`
ou `unidade`: é para a forma que o `conferir` não reconhece. Porcentagem e dose nunca se omitem, e
o número omitido não pode continuar no texto. A chamada de nota colada à palavra ("PCDT6,178")
fica fora da conta, e o denominador que a linha da tabela partiu ("920/197" e, adiante, "0") se
junta no texto ("920 de 1970"). O erro inequívoco do original num número vai em `corrigidos`,
com o trecho das fontes, o do texto e a página do PDF que prova o erro:
`"corrigidos": [{"de": "3 0%", "para": "30%", "pagina": 112}]`. O termo omitido, o número
omitido, a correção do original e o descarte por decisão saem como avisos, que não recusam o
livro. O `montar`
põe o primeiro parágrafo do grupo no elemento do primeiro ID, cada parágrafo a mais num elemento
irmão logo depois, e tira as outras fontes. `--original` monta o texto limpo, sem a adaptação.

### Roteiro de escuta

```bash
uv run earbook minuto livro.earbook c005-s0288 c006-s0022
```

Diz em que minuto da escuta cai cada segmento. Conta a 160 palavras por minuto, pelo texto que
se ouve: a tradução, quando existe. No livro adaptado, ainda conta o texto limpo.

### PDF

```bash
uv run earbook importar-pdf livro.pdf --idioma pt-BR
uv run earbook preparar livro.epub
```

O `importar-pdf` grava `livro.epub` ao lado do PDF (ou onde `--epub` mandar), com o título e o
autor do metadado do PDF (ou os de `--titulo` e `--autor`). O que ele faz:

- tira o número de página, também o que é maior que o texto, e o cabeçalho repetido, pela
  posição na página. O cabeçalho que aparece só nas duas páginas de uma abertura também sai. No
  livro de margem larga, sai também o cabeçalho acima de onde o texto começa e o número de página
  na margem, ao lado da coluna. O cabeçalho em letra maior que a do texto sai pela linha do
  número de página: o que está na altura do número, na letra dele, em 3 páginas ou mais. O
  carimbo de data e hora da gráfica no pé da página ("27/09/2017 20:12:36") sai também;
- devolve o hífen gravado como caractere invisível (U+00AD): no meio da linha ele vira "-"
  ("pós-anestesia", "tabela 6-1"), e no livro que o usa assim o do fim da linha segue a regra da
  palavra partida. O número partido na quebra ("6-" | "1") volta inteiro;
- tira o texto que a página não pinta (o modo de pintura 3 do PDF): a camada que um OCR põe
  sobre as figuras de um livro digital, com o que leu dentro delas. Só na página em que o texto
  pintado é a maior parte: o PDF escaneado com OCR embutido, cujo texto só existe nessa camada,
  entra como entrava. O resumo conta as linhas, com o motivo "texto que a página não pinta:
  camada do OCR sobre a imagem";
- tira o texto escondido: a linha em letra de título desenhada por cima de uma linha de outro
  tamanho, na mesma altura;
- lê uma vez só o negrito feito à mão: o mesmo texto desenhado de novo por cima, no mesmo
  tamanho, quase no mesmo lugar ("Conheça também"). A cópia de uma letra só fica. O resumo
  conta o texto escondido e o repetido junto com as linhas da borda, cada um com o seu motivo;
- tira o número de referência sobrescrito ("wages.¹"): algarismo, vírgula e traço em letra menor
  e acima da linha, colados a uma palavra, a uma pontuação ou a um ano ("in 1934²²¹"). O número
  pode levar uma letra ("¹³⁸ᵃ"), e a faixa, o hífen invisível. Sai também a chamada depois de
  "»", "!" e "?"; a que vem depois de espaço ou de travessão, antes de pontuação ou do fim da
  linha; e a lista ou faixa depois de letra solta ou de número ("N2O¹⁹⁸,¹⁹⁹"). O número só, de 2
  algarismos ou mais, depois de letra solta, de número ou do sinal de grau ("6 h¹⁴⁸",
  "0,62¹¹¹"), e a chamada que abre a linha antes de pontuação ("¹¹⁸. No") saem apenas na página
  que tem 3 chamadas certas ou mais, e nunca depois da base 10 ("10¹²"). O algarismo só ("m²", "T10²"), o isótopo
  ("¹³³Xe") e o expoente no meio da fórmula ficam. O resumo conta quantos saíram;
- não põe espaço no nome com letra espaçada ("NATALIE MORYL", e não "NATALI E MORY L"): o
  espaço que o pdfminer deduz do vão sai quando o vão é o mesmo que separa as letras, ou menos
  da metade do espaço de verdade da linha ("PART ONE", e não "PA R T O N E"; "CHAPTER 110", e
  não "CHAPTER 11 0");
- tira o texto girado (a tabela deitada, o rótulo de lado), a página de lista (índice
  remissivo, sumário, com ou sem número de página, e colaboradores) e a tabela, o quadro e a
  figura, pela letra e pelo rótulo em inglês, em português ou em espanhol. A tabela acaba na
  página seguinte, onde a letra muda, e a figura ou a outra tabela que vem depois sai pelo rótulo
  dela. O resumo conta essas linhas à parte, cada uma com o seu motivo;
- tira a bibliografia em letra menor que a do corpo, pelas citações de periódico, antes de montar
  os parágrafos. A nota do autor na mesma letra, logo acima do título da lista e sem citação,
  fica. A lista de leitura sugerida logo antes das referências, na letra delas, sai junto, com o
  título dela; a caixa em letra do corpo que o PDF grava no meio dela fica. O resumo conta as
  linhas de bibliografia e as de lista de leitura, cada uma na sua linha;
- junta as linhas em parágrafos e devolve inteira a palavra partida no fim da linha;
- acerta a caixa da palavra de rótulo que o versalete do PDF trocou nas menções ("No QuAdro
  13.1" vira "No Quadro 13.1"; "tAb. 4.2", "tab. 4.2"): só "figura", "fig.", "quadro", "tabela",
  "tab.", "tabla" e "cuadro" antes de número, e nunca no título. O resumo conta quantas;
- lê a página em duas colunas coluna por coluna, pela calha entre elas, quando os dois lados
  são texto corrido, também o de verbetes justificados (glossário, bibliografia). A tabela
  continua lida linha a linha;
- separa do texto o destaque de margem, que fica numa coluna estreita ao lado dele e tem letra
  de outro tamanho, para que o `preparar` o tire;
- deixa no lugar o quadro do livro didático. Ele abre no rótulo "Quadro 5.1" ou "Tabela 5.1" em
  letra de título (1,2 vez a do texto ou mais), e o conteúdo dele, em letra menor, é lido como parágrafo, e não como nota no fim do
  capítulo. Ele entra depois da frase que interrompe, e a frase volta a ser uma só;
- lê o subtítulo em versalete como título, e não como nota no fim do capítulo: o feito à mão
  (maiúsculas de dois tamanhos) e o de fonte própria (o nome da fonte termina em "SC", como
  "Archer-Medium-SC700");
- divide os capítulos pelo sumário interno do PDF (os marcadores), quando a maioria dos itens
  de um nível traz o rótulo "Capítulo 3" ou "Chapter 24": cada item desse nível e dos de cima
  abre capítulo na página que o sumário diz, e dá o nome dele no sumário do EPUB. Sem sumário
  interno que sirva, divide pelo tamanho dos títulos e pelo rótulo "CHAPTER 24" ou "Capítulo 3",
  quando o livro o repete, e o capítulo com rótulo leva no sumário do EPUB o rótulo e o título,
  em caixa normal ("Chapter 1: Pain Mechanisms"). Nos dois casos, a parte fica no capítulo que
  ela abre.

O EPUB serve para ouvir, não para ler na tela. Sai sem imagem e sem estilo, e cada linha de
tabela que fica (a da letra do corpo, a sem rótulo) vira um parágrafo. O bloco de código do
PDF ainda é lido; o índice remissivo sai pela página no `importar-pdf` e, o que sobrar, no
`preparar`, pelo conteúdo. PDF
escaneado, sem camada de texto, é recusado, porque não há OCR.

### Romance de fã: Calibre antes, mapa depois

Este é um caminho sem código no `earbook`, feito à mão pela sessão
([ADR-0010](docs/adr/0010-romance-de-fa-se-conserta-sem-codigo-novo.md)). Serve para o livro que o
`preparar` leria errado: metadado falso, título em parágrafo comum, `<p>` que é linha de página ou
parágrafo que o PDF perdeu. O [Calibre](https://calibre-ebook.com) não é dependência do pacote.

```bash
ebook-convert entrada.epub livro.epub --language pt-BR --authors "Autor" --title "Título" \
  --search-replace titulos.sr --chapter '//h:h1' --chapter-mark pagebreak \
  --page-breaks-before '//h:h1' --level1-toc '//h:h1' --use-auto-toc \
  --no-default-epub-cover --flow-size 0
ebook-meta livro.epub -l pt-BR --author-sort "Sobrenome, Nome" --cover capa.jpg
```

O `titulos.sr` traz, em linhas alternadas, a expressão regular e a troca que transformam o título
em `<h1>`. Quando cada `<p>` é uma linha de página, acrescente `--enable-heuristics` e
`--html-unwrap-factor 0.4`, com as outras heurísticas desligadas. O `ebook-meta` vem depois da
conversão, porque o `ebook-convert` grava `pt` no lugar de `pt-BR`.

Depois do `preparar`, o `adaptar` serve de transporte: um script grava `adaptados/` com o parágrafo
cortado, o nome trocado pelo glossário e o que sai do áudio, e o `conferir` cobra tudo isso. Quando
a tradução segue o original frase a frase, o original serve de mapa dos parágrafos e nunca entra no
livro.

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
