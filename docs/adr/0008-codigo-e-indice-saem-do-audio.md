# 0008 — O `limpar` tira do áudio o bloco de código, o índice remissivo e a marca d'água

**Status:** Aceito
**Data:** 2026-11-02
**Driver ★:** qualidade da escuta no ElevenReader (ADR-0001)

**Bottom line:** o `preparar` dá papel próprio ao bloco de código e ao índice remissivo, quando
a marcação do EPUB diz o que eles são, e o `limpar` os tira do texto, registrados em
`limpeza.json`. O Gherkin fica no texto, como parágrafo, porque é feito para ser lido por gente.
O `limpar` tira também o parágrafo idêntico que se repete em metade ou mais dos arquivos do
spine (a marca d'água "OceanofPDF.com") e, desde 2026-11-03, o destaque de margem que repete,
palavra por palavra, o texto vizinho (seção "Destaque de margem repetido"), e a bibliografia no
padrão ABNT, reconhecida pelo conteúdo (seção "Bibliografia"), e o índice remissivo sem
marcação, também pelo conteúdo (seção "Índice pelo conteúdo"). Inverte se a escuta mostrar que o
ouvinte se perde sem o código ("depois da linha 7"), ou se um livro medido perder um texto que
não é código, índice, marca d'água, destaque nem bibliografia.

## Contexto

Quantum atual: 1 (CLI local + pasta de trabalho em arquivos). Continua 1.

O próximo livro da tradução é *Learning Domain-Driven Design* (Vlad Khononov, O'Reilly, EPUB).
O `preparar` no HEAD b3904d2 deu 321 capítulos (um por arquivo do spine), 4.246 segmentos,
6 remoções (direitos), 1 junção, 696 trechos fora de segmento e 81.708 palavras em `limpos/`.
Dois defeitos iriam para o áudio e para a tradução:

| Defeito | Medido no DDD | O que causa |
|---|---|---|
| **Bloco de código vira parágrafo** | 65 `<pre>`, todos com `data-code-language` ou `data-type="programlisting"` e `<code>` dentro: 51 `csharp`, 9 `json`, 1 `sql`, 1 `javascript`, 1 `gherkin` e 2 sem linguagem (dados: `LeadId: 12 FirstNames: …`). São 2.853 palavras, numa linha só (`c178-s0005`: "public class Player { public Guid Id { get; set; } … }") | a voz lê chave e ponto e vírgula; na tradução, o código fica igual ao original e o `conferir` o acusa de "igual ao original" ou "parece inglês" |
| **Índice remissivo lido e traduzido** | `c318` ("Index") e `c319` ("L"): 973 segmentos e 5.252 palavras, mais os 696 trechos fora de segmento, todos desses dois arquivos (o termo pai de uma entrada com subentradas, e as vírgulas e hífens entre os links) | uns 33 minutos de "accidental complexity, case study of applying DDD, The real problem…"; 973 segmentos traduzidos para nada. O índice está em "O que atrapalha o ouvido" no `AGENTS.md` |
| **Marca d'água no fim de todo arquivo** | "OceanofPDF.com", parágrafo com link, último segmento de cada um dos 321 arquivos do spine (o `c001` só tem ela) | a voz diz "OceanofPDF ponto com" a cada poucos minutos, 321 vezes. Não tem número de página, então a regra do cabeçalho corrente (ADR-0003) não a vê |

O que a prosa faz com o código: os 65 blocos vêm depois de um parágrafo que termina em ":" e
anuncia o código ("see the following test", "For example:"). Em 19 dos 65, o parágrafo seguinte
fala das linhas ("after line 7 but before line 9") ou do "previous example".

O Gherkin (`c044-s0007`, 44 palavras) é um teste escrito em inglês estruturado: "Scenario: Notify
the agent about a new support case / Given Vincent Jules submits a new support case… / When the
ticket is assigned to Mr. Wolf / Then the agent receives a notification…". A prosa de antes diz
para que ele está ali: "Domain experts can read the tests and verify the system's expected
behavior. For example, see the following test". O C# não se lê; o Gherkin foi feito para isso.

O código em linha (`<code>` dentro de `<p>`) é outra coisa: 129 elementos, 132 palavras, em 18
arquivos, quase todos nomes de classe e de método (`AppendEvent`, `Ticket`) no meio da frase.
Fica de fora desta decisão: tirá-los quebraria a frase.

O que o EPUB marca no índice: `<section data-type="index" epub:type="index">` nos dois arquivos,
com `<div data-type="index">`, `indexdiv`, `index-term` e `index:locator` dentro. O `epub:type`
é o vocabulário de semântica estrutural do EPUB 3 (a especificação de índices do EPUB pede
`index` num `<body>` ou num `<section>`); o `data-type` é o HTMLBook da O'Reilly; o
`role="doc-index"` é o DPUB-ARIA.

Os outros livros medidos:

| Livro | `<pre>` | Marca de índice | O que acontece |
|---|---|---|---|
| Huxley, *The Doors of Perception* (EPUB) | 0 | 0 | nada muda. O arquivo `OEBPS/index.xhtml` é a folha de rosto |
| Rosenberg, *Tides of Darkness* (EPUB) | 0 | 0 | nada muda. Os arquivos se chamam `index_split_003.html`… |
| *Competente o Suficiente* (PDF, pt-BR) | 8, do `importar-pdf`, sem `<code>` | 0 | nada muda. São comandos curtos (`tmutil localsnapshot`, `sudo timeshift --create …`), e a parada "código" do roteiro de escuta foi aprovada pelo Mateus (ADR-0004) |
| *Software Architecture: The Hard Parts* (PDF, en) | 79, do `importar-pdf`, sem `<code>` | 0 | nada muda. A fonte monoespaçada marca também prosa: os carimbos da saga ("Wednesday, November 3, 13:00"), as convenções tipográficas do prefácio ("Constant width") e um pedaço de palavra ("tion"). O índice (`c022`, título "Index", 47 segmentos, 6.198 palavras em duas colunas intercaladas) continua lido, porque o EPUB do `importar-pdf` não o marca |

O nome do arquivo e o título não servem de regra no EPUB: o Huxley e o Tides têm "index" no nome
do arquivo sem ter índice, e "Índice", em português, é muitas vezes o sumário.

O que se repete entre arquivos do spine, medido nos sete livros de `livros/trabalho/` (o mesmo
texto em mais de um arquivo; a fração é sobre os arquivos com algum segmento):

| Livro | Arquivos com texto | O que mais se repete | Parágrafo que mais se repete, fora a marca |
|---|---|---|---|
| *Learning DDD* | 321 | "OceanofPDF.com", parágrafo, em 321 (100%) | "Anticorruption layer" e "Open-host service", em 6 (2%, como item e parágrafo) |
| *Huxley* | 4 | "The Doors of Perception", título, em 3 (75%) | nenhum |
| *Tides* | 6 | "POCKET STAR BOOKS", título, em 2 (33%) | "re we ready?”", em 2 (33%: a abertura repetida do livro) |
| *Competente* | 23 | 12 títulos de capítulo, em 2 (9%: o sumário e o capítulo) | nenhum |
| *Hard Parts* | 22 | "Trade-Offs", título, em 9 (41%) | "Component Namespace Responsibility", em 2 (9%) |
| *Dalgalarrondo* | 43 | "Questões de revisão", título, em 28 (65%) | "Em caso positivo", em 3 (7%) |
| *Warcraft* | 6 | igual ao Tides | igual ao Tides |

O título se repete de propósito ("Conclusion", "Exercises", "Questões de revisão") e chega a 65%
dos arquivos. Nenhum parágrafo de verdade passa de 6 arquivos nem de 33%.

## Drivers

| ★ | Característica | Como se mede |
|---|---|---|
| ★ | Escuta | 0 bloco de código, 0 entrada de índice e 0 "OceanofPDF.com" no texto lido do DDD; o Gherkin lido como frase |
| | Nada some em silêncio (ADR-0003) | cada bloco e cada índice tirado fica em `limpeza.json`, com o ID e o texto; o `conferir` cobra origem = mantidos + removidos + juntados |
| | Nada a mais some | Huxley, Tides, Competente e Hard Parts com `limpos/` idêntico ao de antes |
| | Custo da tradução | as palavras que vão para a tradução do DDD caem de 81.708 para ~73.650 (−10%) |

## Alternativas consideradas

### 1. O que o bloco de código vira

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| **A. Sai do texto, registrado em `limpeza.json`** | a voz não lê código; nada novo no `traduzir`, no `conferir` nem no `montar`: o removido já sai do livro montado (ADR-0005) | o livro montado perde o código também na tela; em 19 de 65 casos a prosa seguinte fala de "line 7", que o ouvinte não tem | — |
| B. Fica no livro, fora da tradução e da cobrança | o livro na tela continua com o código | a voz lê chave e ponto e vírgula, que é o defeito; um estado novo de segmento ("mantido sem tradução") no `traduzir`, no `conferir` e no `montar` | falha no ★ e custa um caminho novo em três comandos |
| C. Troca por um aviso falado ("Trecho de código omitido.") | o ouvinte sabe que havia código | inventa texto que o livro não tem; o `montar` passa a escrever frase própria; e os 65 blocos já são anunciados pela prosa de antes, que termina em ":" | o anúncio já existe; fica para a escuta decidir (ver Consequências) |
| D. Lê o Gherkin como os outros e tira tudo | uma regra só | o único exemplo de "o especialista do domínio lê o teste" some do capítulo que fala disso | o Gherkin é prosa estruturada, feito para ser lido |

### 2. Como o índice sai

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Cada entrada vira segmento com papel `indice` e sai | segue o bloco-folha de sempre | o termo pai de entrada com subentradas e as vírgulas entre os links não são segmento: ficam no livro montado e são lidos (os 696 trechos) | não resolve |
| **B. O elemento marcado como índice, o mais externo, vira um segmento só, que sai** | o índice sai inteiro, com o título "Index", os termos pais e a pontuação, por um ID só; o `montar` já tira o elemento removido | o registro em `limpeza.json` guarda um texto de ~3 mil palavras por arquivo; é o único segmento com bloco dentro | — |
| C. Pelo título ("Index") ou pelo nome do arquivo | pega também o EPUB sem marcação | "index" no nome de arquivo do Huxley e do Tides; "Índice" é sumário em português | tira texto que não é índice |
| D. O segmentador pula o índice | nenhum registro grande | sumiria sem registro, e o `montar`, que não sabe dele, o deixaria no livro | contradiz o ADR-0003 |

### 3. Como a marca d'água sai

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Pelo nome do site ("OceanofPDF", "epubBooks"…) | certeiro no caso conhecido | uma lista que nunca termina; o site seguinte passa | não é regra |
| B. Pela posição (último segmento do arquivo) | pega a marca no rodapé | a marca no topo ou no meio passa; o último parágrafo de verdade de um capítulo curto pode coincidir em 2 arquivos | a posição não acrescenta nada à repetição, na medição |
| **C. O mesmo parágrafo em metade ou mais dos arquivos do spine, e em 10 ou mais** | não depende do site nem da posição; a folga da medição é grande (100% contra no máximo 33%) | um livro de poucos arquivos (menos de 10) não é coberto; um refrão de verdade, idêntico em metade dos capítulos, sairia (registrado) | — |

## Decisão

### 1. Bloco de código

- O `preparar` dá papel `codigo` ao `<pre>` que se declara código: com `data-code-language`, com
  `data-type="programlisting"` ou com `<code>` dentro. O `<pre>` dentro de uma nota de rodapé
  continua nota, porque a nota vence tudo, como hoje.
- O `limpar` tira todo segmento `codigo`, com o motivo "código-fonte", no fim da limpeza: assim
  o bloco de código continua separando os dois parágrafos em volta dele, e a junção não cola o
  parágrafo de antes, que não fechou a frase, no de depois.
- **O Gherkin fica**: o `<pre>` com `data-code-language="gherkin"` continua `paragrafo`, como
  hoje, e é traduzido como frase ("Cenário: … Dado que … Quando … Então …").
- O `<pre>` sem marca de código fica `paragrafo`, como hoje. É o `<pre>` do `importar-pdf`, em
  que a fonte monoespaçada marca também prosa (os carimbos da saga do Hard Parts), e é onde um
  EPUB mal feito põe verso.

### 2. Índice remissivo

- O elemento de bloco marcado como índice (`index` no `epub:type`, `role="doc-index"` ou
  `data-type="index"`) é um segmento só, de papel `indice`, com todo o texto de dentro; nada
  dentro dele vira outro segmento nem trecho fora de segmento. Vale o mais externo: o
  `<div data-type="index">` dentro do `<section epub:type="index">` não abre outro.
- Com a marca no `<body>`, cada elemento filho dele é um segmento `indice`.
- O link de índice (`<a epub:type="index">` no `landmarks` do `nav`) não é bloco e não conta.
- O `limpar` tira todo segmento `indice`, com o motivo "índice remissivo", no mesmo passo do
  código.

### 3. Marca d'água

- O `limpar` tira o parágrafo (papel `paragrafo`) cujo texto, idêntico, aparece em **metade ou
  mais** dos arquivos do spine que têm algum segmento, e em **10 arquivos ou mais**. Sai cada
  ocorrência, com o motivo "marca d'água: o mesmo parágrafo em N de M arquivos".
- Por que não pega o texto que se repete de propósito:
  - **título** nunca conta ("Conclusion", "Exercises", "Notes", "Questões de revisão", que chega a
    65% no Dalgalarrondo): só o papel `paragrafo` entra;
  - **epígrafe** e **citação** (`<blockquote>`) têm papel `citacao`, e item de lista, `item`;
  - o **parágrafo de verdade** que mais se repete nos sete livros está em 6 arquivos (2% do DDD);
    a maior fração é 33%, em 2 arquivos do Tides. A metade dá folga de 17 pontos, e os 10
    arquivos impedem que um livro de 4 ou 6 arquivos (Huxley, Tides) perca o que aparece em 2 ou 3;
  - o parágrafo **sem letra** ("* * *", a pausa de cena) fica: não é lido como palavra e marca a
    pausa;
  - o texto precisa ser **idêntico**: a frase parecida, com uma palavra diferente, não conta.
- Roda logo depois da página de direitos e antes do cabeçalho de página: como o cabeçalho, a marca
  pode estar no meio de um parágrafo partido, e as duas metades só se juntam depois que ela sai.

### Fronteiras que mudam

- `Papel` ganha `codigo` e `indice`. Os dois aparecem em `segmentos/` e nunca em `limpos/`.
- O segmento de índice é o único com bloco dentro (o bloco-folha do ADR-0001 continua valendo
  para o resto); o texto dos blocos de dentro se junta com espaço.
- A classificação do bloco pela marcação sai de `adaptadores/xhtml.py`, que passaria das 400
  linhas, para um módulo próprio do adaptador.

### O PDF fica como está

O índice do Hard Parts continua lido, e o código do `importar-pdf` também. Marcar no
`importar-pdf` o capítulo de título "Index" ou "Índice remissivo" com
`<section epub:type="index">` faria o `preparar` tirá-lo pela regra acima, mas é outra
mudança, no `importar-pdf`, e fica proposta para depois (ver "Fora desta decisão"). Desde
2026-11-03, o índice do PDF sai pelo conteúdo, no `limpar` (seção "Índice pelo conteúdo").

## Medição (2026-11-02, depois do código)

O `preparar` rodou em pastas novas de `livros/trabalho/`, sem tocar nas medições anteriores.

| Livro | Segmentos | Mantidos | Palavras mantidas | Fora de segmento | Remoções | Junções |
|---|---|---|---|---|---|---|
| *Learning DDD* antes (`ddd.earbook`) | 4.246 | 4.239 | 81.708 | 696 | 6 | 1 |
| *Learning DDD* depois (`ddd-v2.earbook`) | 3.277 | 2.883 | 73.328 | 0 | 393: 321 marcas d'água, 64 códigos, 6 de direitos, 2 índices | 1 |

- **DDD:** nenhum segmento mantido mudou de texto nem de papel; os 1.356 que saíram são exatamente
  as 321 marcas, os 64 blocos de código e os 971 segmentos que o índice tinha (agora 2, um por
  arquivo). As 6 remoções de direitos, a junção, as suspeitas (0) e as capitulares (0) são as
  mesmas. O Gherkin (`c044-s0007`) ficou como parágrafo. O `conferir --original` passa, e o
  `montar --original` (`livros/trabalho/ddd-v2.original.epub`), lido de novo pelo `preparar`, dá
  0 trecho fora de segmento, 0 remoção e nenhum "OceanofPDF".
- **epubcheck do DDD montado:** 3.425 erros, contra 11.963 do original; todo tipo de erro já vinha
  do original, menos um: "body incompleto" em 307 arquivos. O EPUB é 2.0 (XHTML 1.1) e usa
  `<section>` e `<figure>`, que o XHTML 1.1 não aceita; em 307 arquivos, o `<div>` da marca d'água
  era o único bloco válido do `<body>`. Nenhum `<body>` ficou vazio: os dois arquivos do índice
  ficam com as âncoras num `<div>` (ADR-0005), e a folha de rosto, com a capa.
- **Huxley e Tides** (`huxley-adr0008`, `tides-adr0008`) e **Competente e Hard Parts**, pelo
  `importar-pdf` e o `preparar` (`competente-adr0008`, `hard-parts-adr0008`): `segmentos/`,
  `limpos/`, `limpeza.json` e `livro.json` idênticos aos da medição do ADR-0007 (fora a origem).

### Correções da revisão (2026-11-02)

A code-review e a code-audit não acharam bloqueador. O Mateus aprovou os dois lotes ("Os dois (A
e B)"). Cada correção do lote A tem um teste de regressão, visto falhar na asserção antes dela:
- **A1:** a pista da capitular olhava os 3 segmentos seguintes, inclusive o código. Num livro
  sintético, "var x = N + 1;" perdia o "N", que ia para "ight fell…". O mecanismo vinha de antes
  (o código era parágrafo), e agora o código e o índice não servem de pista. Vermelho:
  `'var x = + 1;' != 'var x = N + 1;'`.
- **A2:** com a marca de índice no `<body>`, só o filho de bloco virava índice, e um `<p>` dentro
  de um `<span>` saía como parágrafo. Agora a raiz é o bloco mais externo dentro da marca,
  qualquer que seja o elemento marcado. Vermelho: `('paragrafo', 'abstractness, 67') != ('indice', …)`.
- **A3:** o Gherkin marcado pela classe (`language-gherkin` no `<code>`, a recomendação do HTML,
  ou `sourceCode gherkin`, do pandoc) saía como código. A linguagem agora vem também da classe do
  `<pre>` e do `<code>`. Vermelho: `('codigo', …) != ('paragrafo', …)`, nas duas formas.

Lote B, refatoração com a suíte verde: as regras puras do cabeçalho de página saíram de
`limpeza.py` para `dominio/cabecalho.py` (de 396 para 354 linhas); a remoção da página de
direitos passou a usar o mesmo `_tirar` da marca d'água e do código; `marcas_dagua` e
`limpar_para_o_ouvido` voltaram para 20 linhas ou menos.

Fica registrado, sem correção: o Gherkin, como parágrafo, pode absorver um parágrafo seguinte que
comece em minúscula (nenhum caso no DDD; ver Consequências).

Remedido depois das correções, em pastas novas: o DDD (`ddd-v3.earbook`) saiu idêntico ao
`ddd-v2.earbook` (`segmentos/`, `limpos/`, `limpeza.json` e `livro.json`), e Huxley, Tides,
Competente e Hard Parts (`*-adr0008-revisado`), idênticos aos da medição do ADR-0007. O
post-audit do intervalo inteiro não achou defeito novo. Resíduo que vem de antes, sem caso
medido: a prova da palavra da capitular (ADR-0007) ainda conta as palavras do código e do índice.

## Destaque de margem repetido (2026-11-03)

### Contexto

O Mateus ouviu o Dalgalarrondo no ElevenReader e relatou: "O conceito de saúde de normalidade em
psicopatologia é questão de grande controvérsia. Se repetiu esse trecho." No livro impresso, a
frase está no texto e de novo na margem: é o destaque (*pull quote*). Ele tem 9 pt, numa coluna
estreita (p. 31: x 46 a 123), ao lado do texto de 10 pt, e repete uma frase do texto que fica
ao lado dele, às vezes resumida.

O `limpar` não sabe da fonte nem da posição; o que ele vê é a repetição. Medido no HEAD
`0038af9`, nas pastas `*-base-destaque` de `livros/trabalho/`:
- **parágrafo próprio contido num parágrafo vizinho:** 65 a 78 no Dalgalarrondo, conforme a
  normalização, e 2 no Competente (o subtítulo da folha de rosto e um pedaço de bibliografia);
  nada no Hard Parts, no Huxley, no Tides nem no Learning DDD;
- **o destaque colado:** a virada de coluna o emendava ao texto (ADR-0004, "Destaque de margem
  na virada de coluna"), e 221 segmentos do Dalgalarrondo repetem dentro de si 8 palavras
  seguidas. Com a quebra nova do `importar-pdf`, o destaque vira parágrafo próprio.
- **o que também repete o vizinho e não é destaque:** o título que veio como parágrafo
  ("Relações da psicopatologia com a psicologia geral", "ATO VOLITIVO OU ATO DE VONTADE"), o
  cabeçalho de tabela repetido na página seguinte, a questão de revisão que começa igual à
  anterior ("Como estabelecer um diagnóstico diferencial entre:"), a continuação em minúscula
  do texto em que o destaque ficou colado, o pedaço de bibliografia que abre em algarismo e as
  duas notas seguidas do Learning DDD que citam a mesma obra (`c095`, "Fowler, M. (2002)…").

Nenhum dos três EPUBs marca destaque (`epub:type="pullquote"`, `role="doc-pullquote"` ou classe
"pullquote"). Os 3 `<aside data-type="sidebar">` do Learning DDD são quadros com texto próprio,
não repetido, e ficam.

### Alternativas

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| **A. Palavras seguidas: o destaque repete, palavra por palavra, um trecho do texto vizinho** | sai só o que o texto já diz, na mesma ordem: nenhuma palavra do livro se perde | o destaque que resume (omite palavras) ou reescreve fica | — |
| B. Palavras na mesma ordem, com folga de 1,5 vez para as omitidas | pega mais 16 destaques resumidos no Dalgalarrondo | no Learning DDD, tira a referência de outra obra: "Vernon, V., & Jaskula, T. (2021). Strategic Monoliths and Microservices…", ao lado de "…Implementing Strategic Monoliths and Microservices…" | perde texto que não está no vizinho |
| C. Pela fonte e pela posição, no `importar-pdf` | pega o resumido e o reescrito | só serve ao PDF; a régua (9 pt numa coluna estreita) é de um livro; e nada fica em `limpeza.json` | quebra o "nada sai em silêncio" (ADR-0003) |
| D. Pela marcação do EPUB (`pullquote`) | certeira quando existe | nenhum livro medido a tem | fica para quando aparecer (Fora desta decisão) |

### Decisão

O `limpar` tira o parágrafo (papel `paragrafo`) que:
1. **tem forma de frase:** abre em maiúscula, depois de aspa e travessão, e fecha em `.`, `!`,
   `?` ou `…`, com aspa ou parêntese depois. Isso recusa o título como parágrafo, o cabeçalho de
   tabela, a questão que termina em ":", a continuação em minúscula e o pedaço que abre em
   algarismo;
2. **tem 6 palavras ou mais;**
3. **repete o texto vizinho:** as palavras e os números dele, em minúscula e sem o hífen de
   dentro da palavra, aparecem seguidos no texto dos parágrafos vizinhos (3 antes e 3 depois, no
   mesmo capítulo), juntados. Juntar os vizinhos é o que pega o destaque que parte uma frase
   ("…principais palcos" | destaque | "de nossas vidas…", p. 250) ou uma palavra ("os pri-" |
   destaque | "meiros três minutos…"). O hífen não conta porque o texto ficou com
   "divi-dem-se" (regra do composto, ADR-0004) e o destaque, com "dividem-se". O número conta:
   "3 a 25 segundos" não repete "5 a 30 segundos";
4. **gêmeo:** quando um vizinho tem exatamente as mesmas palavras, o texto é um parágrafo de uma
   frase só e o destaque o repete inteiro. Aí só sai a cópia que está no meio da frase, pela
   regra da junção: o parágrafo antes dela não fechou a frase, e o seguinte começa em minúscula
   ("As ilusões ocor-" | destaque | "rem basicamente…"). As outras ficam, e as duas notas
   iguais do Learning DDD também.

Sai com o motivo "destaque de margem: repete o texto vizinho", depois do aparo do cabeçalho
colado e antes da junção, como a marca d'água: as metades da frase que ele partia se emendam
pela junção de sempre (ADR-0003). A regra é textual e vale para o EPUB também; medido, ela não
tira nada dos três EPUBs.

O Mateus aprovou. A pergunta foi "Aprova o destaque A + B, com os 8 pares e os 60 restantes
indo para o 'adaptar'?", e a resposta, "Aprovar". O A é a quebra do `importar-pdf` (ADR-0004);
o B, esta regra.

### Medição (2026-11-03, depois do código)

`importar-pdf` e `preparar` em pastas novas (`*-destaque`), contra o HEAD `0038af9`:

| Livro | Destaques | O resto |
|---|---|---|
| *Dalgalarrondo* | **238**, com 5.558 palavras (3,3% do livro) | junções 19 → 193: 174 frases emendadas onde o destaque estava; suspeitas 3 → 9 (6 "capitular perdida?", nenhuma devolvida); segmentos que repetem 8 palavras dentro de si 221 → 18 |
| *Competente*, *Hard Parts* | 0 | `segmentos/`, `limpos/`, `limpeza.json` e `livro.json` idênticos (fora a origem) |
| *Huxley*, *Tides*, *Learning DDD* | 0 | idênticos: as traduções do Tides e do DDD não ficam velhas |

- **Nenhuma palavra do texto se perde:** o Dalgalarrondo vai de 167.501 para 161.849 palavras.
  A diferença são as 5.558 dos destaques mais 94 palavras que o destaque partia e que voltam a
  ser uma (188 pedaços). Os 238 foram lidos um a um, e são todos frases-tema em destaque. Dois
  deles (`c011-s0036`, `c023-s0079`) partiam o texto junto com um Quadro, que fica entre as
  metades.
- **Sensibilidade:** a janela de 2 a 6 segmentos e o mínimo de 4 a 8 palavras tiram de 238 a 239
  no Dalgalarrondo e nada nos outros cinco.
- **Gêmeos:** 5 saem por estarem no meio da frase. Ficam **8 pares** (`c014-s0038/39`,
  `c021-s0007/08`, `c027-s0016/17`…): as duas cópias são lidas.
- **As 6 suspeitas novas** não mudam o texto. Duas são o começo da frase que o destaque partia,
  com até 3 palavras ("O fenômeno", "As ilusões ocor-"): a junção o trata como título e não
  emenda, e fica uma pausa onde antes estava o destaque. As outras quatro vêm do subtítulo de
  9 pt que a quebra nova soltou do texto (ADR-0004).

### O que fica (vai para o `adaptar`)

Uns 60 destaques continuam lidos no Dalgalarrondo: os 8 pares gêmeos; o destaque resumido
("Semiologia psicopatológica é o estudo…" para "…é, por sua vez, o estudo…") e o reescrito
("No pensamento prolixo, o paciente…" para "O paciente…"); uns 15 colados sem virada de coluna;
e os que têm o texto partido por um Quadro. O `adaptar` reescreve com a cobrança de fidelidade do
`conferir`, que garante que nada do texto se perde.

### Correções da revisão (2026-11-03)

A code-review e a code-audit não acharam bloqueador. O Mateus aprovou os três lotes ("A, B e C").

- **A, refatoração com a suíte verde:** a chave de cada parágrafo é calculada uma vez por
  capítulo; a dos vizinhos juntados continua por candidato, porque o hífen da quebra fica entre
  dois segmentos. A primeira letra depois de aspas e travessões virou uma regra só
  (`segmento.primeira_letra`), usada pela junção e pelo destaque. Os seis livros saíram
  idênticos à rodada anterior, fora o hífen do lote B.
- **B, o hífen da quebra:** a junção emendava a palavra que o destaque partia com o hífen no
  meio ("identifi-car"). Agora o hífen sai quando o livro escreve a palavra inteira (ADR-0003,
  "Hífen da quebra na junção"): 87 de 95 no Dalgalarrondo, e nada nos outros cinco.
- **C, limites registrados,** sem caso nos seis livros medidos:
  - **a cópia contida sai, mesmo quando é o texto:** se o texto é um parágrafo de uma frase e o
    destaque o repete com palavras a mais, sai o texto, e o destaque fica no lugar dele. Nos 238
    lidos, todo vizinho que contém o removido é o texto, mais longo;
  - **a frase repetida de propósito:** a regra vale também para o EPUB. A frase de 6 palavras ou
    mais que o parágrafo vizinho repete dentro de um parágrafo mais longo (a fala que a multidão
    devolve, o refrão de um poema) sairia, registrada. Não há caso no Huxley, no Tides nem no
    Learning DDD;
  - **a virada de página:** o `importar-pdf` só separa o destaque na virada de coluna. O que fica
    no alto da página seguinte, com a frase do texto aberta, continua colado;
  - **o tamanho comparado é o da 1ª linha** do parágrafo aberto: um parágrafo que abre com uma
    linha de outro tamanho se partiria na virada de coluna;
  - **as notas do destaque:** o destaque removido leva as notas dele. Nos 238, não há nenhuma;
  - **a ordem não tem teste:** tirar o destaque depois da primeira junção dá o mesmo, porque a
    segunda junção, depois da capitular, emenda as metades (mutante equivalente).

## Bibliografia (2026-11-03)

### Contexto

No Dalgalarrondo, as p. 417 a 431 trazem a bibliografia, depois do título "Referências
bibliográficas e leituras recomendadas". São 9 pt, duas colunas e o padrão ABNT ("ABDO, C. H. N.
Diagnóstico em psiquiatria e relação médico-paciente. Revista da Associação Médica do Brasil,
n. 42, p. 222-228, 1996."). Medido no HEAD `f60971a`: 127 segmentos e 8.021 palavras, lidos com
as colunas intercaladas. O Mateus decidiu: "Sim, sai".

O índice remissivo deste ADR sai pela marcação do EPUB, e o reconhecimento pelo título ou pelo
nome do arquivo foi recusado (alternativa C do índice). O PDF importado não tem marcação, e o
título ("Referências", "Bibliografia", "Leituras") também aparece no meio do livro.

### Alternativas

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| **A. Pelo conteúdo de cada parágrafo** (escolhida) | não depende do título nem da marcação; nenhum livro medido além do Dalgalarrondo muda | só o padrão ABNT; a bibliografia partida em pedaços curtos não chega às 10 referências seguidas | — |
| B. O `importar-pdf` marca `<section epub:type="bibliography">`, e o `preparar` dá papel próprio, como ao índice | a forma geral, que pega também o EPUB marcado | o Learning DDD já marca a dele (`c317`, 30 segmentos traduzidos), que sairia, e a tradução ficaria velha; o `importar-pdf` ainda precisaria reconhecer a bibliografia do PDF | muda um livro traduzido, e o reconhecimento continua sendo o da opção A |
| C. Pelo título | pega qualquer padrão | o ADR-0008 proíbe; o título de seção no meio do livro levaria o texto seguinte | tira texto que não é bibliografia |

### Decisão

- **O parágrafo-referência** abre com o autor em maiúsculas, o sobrenome ou a instituição,
  seguido de vírgula ou ponto ("ABDO, C. H. N.", "ALONSO FERNANDES, F.", "AMERICAN PSYCHIATRIC
  ASSOCIATION.", "WORLD HEALTH ORGANIZATION (WHO).") e traz um ano, de 1500 a 2099.
- **Sai a sequência de 10 ou mais** parágrafos-referência seguidos, no mesmo capítulo, e o título
  **logo antes dela**. O título nunca dispara a regra; ele só sai junto, como o "Index" sai com o
  índice.
- O motivo registrado é "bibliografia: referências no padrão ABNT". A regra fica em
  `fora_do_audio.bibliografia` e roda por último, depois do código e do índice, enquanto a
  bibliografia ainda separa os parágrafos em volta dela.
- No Dalgalarrondo, a sequência só existe depois que as colunas saem em ordem: intercaladas, as
  referências tinham no máximo 7 seguidas. A ordem vem do texto justificado (ADR-0004, "O que
  ficou da Fase 1").

O Mateus aprovou ("Aprovar"), junto com as regras do `importar-pdf` do fim da Fase 1.

### Medição (2026-11-03, depois do código)

| Livro | Maior sequência de parágrafos-referência | O que muda |
|---|---|---|
| *Dalgalarrondo* | 24 (p. 417 a 431) | saem os 24 parágrafos e o título: 25 remoções e 7.943 palavras |
| *Competente* | 3 (118 referências ABNT nas p. 481 a 503, partidas entre nota e parágrafo) | nada |
| *Hard Parts*, *Huxley*, *Tides* | 0 | nada |
| *Learning DDD* | 0 (APA: "Evans, E. (2003).") | nada |

Os cinco livros que não são o Dalgalarrondo saem com `segmentos/`, `limpos/` e `limpeza.json`
idênticos.

### O que fica

- **A bibliografia de outro padrão** (APA, Vancouver, numerada) continua lida.
- **A do Competente** também, porque metade das entradas vira nota. Está na fila do ADR-0004.
- **A lista curta,** com menos de 10 referências (no fim de um capítulo), continua lida.
- **A referência sem ano** ("s.d.") parte a sequência, e a entrada fora do padrão também
  ("McDONALD", "LeRESCHE", o autor entre aspas). Numa bibliografia de uma referência por
  parágrafo, os pedaços com menos de 10 ficam lidos, soltos entre os que saem (R5 da
  code-review, aceito como limite em "A, B, C e commit"). No Dalgalarrondo isso não acontece,
  porque cada coluna é um parágrafo.
- **O que sairia:** um trecho de prosa com 10 parágrafos seguidos, cada um abrindo em maiúsculas
  com vírgula e um ano. Não há caso nos livros medidos.

## Índice pelo conteúdo (2026-11-03)

### Contexto

O índice remissivo sai pela marcação do EPUB (seção "Índice remissivo" da Decisão), e o PDF
importado não tem marcação. Medido no HEAD `56b7891` (pastas `*-base-curto` de
`livros/trabalho/`), dois índices eram lidos no fim do livro:
- **Dalgalarrondo** (p. 433 em diante): o título "Índice" e 18 parágrafos, um por letra, com
  1.737 palavras ("Abuso e dependência de substâncias, 346-347 Afetividade, 155-173…");
- **Hard Parts** (p. 443 a 459): o título "Index", 25 títulos de uma letra ("A", "B"…) e 26
  parágrafos, com 5.507 palavras ("abstractness of codebase, 67 distance from main sequence,
  69…").

Reconhecer pelo título está proibido (alternativa C do índice): "Índice" é o sumário em português.

### Alternativas

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| **A. Pelo conteúdo de cada parágrafo, no `limpar`** (escolhida) | não depende do título nem da marcação; pega também o EPUB sem marca | o índice com termo-pai sem página no meio se parte; o índice curto fica | — |
| B. O `importar-pdf` marca `<section epub:type="index">` ("Fora desta decisão") | o `preparar` tira pelo papel, como o índice do EPUB | pelo título, é proibido; pelo conteúdo, o reconhecimento é o mesmo da A, mas no `importar-pdf`, que não vê os parágrafos juntados e não serve ao EPUB sem marca | a mesma regra num lugar pior |
| C. A entrada termina em número de página | mais estreita | parte o índice do Hard Parts no "W", que termina na remissão "(see also distributed workflows)" | deixa parte do índice lida |

### Decisão

- **O parágrafo-entrada** traz números de página depois de vírgula e espaço (", 346-347", ", 66,
  68", ", 12"), com **8 palavras ou menos por número**. Ele não precisa terminar no número.
  - A vírgula decimal ("2,0 1,3", as tabelas do Dalgalarrondo) não tem espaço e não conta.
  - O número com cara de ano (1500 a 2099) e o que vem antes de ")" não contam: "Porto Alegre,
    2004", "(Cummings, 2004)", "(apud Evans, 1980)".
- **Sai a sequência de 10 ou mais** parágrafos-entrada seguidos, no mesmo capítulo. O título de
  **uma letra só** no meio não a parte e sai junto (os "A", "B"… do Hard Parts). Sai também o
  título **logo antes** da sequência ("Índice", "Index"), que nunca dispara a regra, como na
  bibliografia.
- O motivo registrado é "índice remissivo: termos seguidos do número da página". A regra fica em
  `fora_do_audio.indice_pelo_conteudo` e roda por último, depois da bibliografia.
- O índice marcado no EPUB continua saindo pelo papel, como antes. Esta regra pega o resto.

O Mateus aprovou ("Aprovar"), junto com o negrito feito à mão do ADR-0004.

### Medição

| Livro | Maior sequência de parágrafos-entrada | O que muda |
|---|---|---|
| *Dalgalarrondo* | 18 | saem o "Índice" e os 18 parágrafos: 19 remoções, 1.737 palavras |
| *Hard Parts* | 26 | saem o "Index", as 25 letras e os 26 parágrafos: 52 remoções, 5.507 palavras. "About the Authors" e o colofão ficam |
| *Competente* | 1 (10 referências soltas com o dia do mês, ", 16 set. 2026", nunca 2 seguidas) | nada |
| *Huxley*, *Tides*, *Learning DDD* | 0 | nada |

- **A folga:** os parágrafos dos dois índices têm no máximo 4,4 palavras por número de página
  (Dalgalarrondo) e 5,8 (Hard Parts). Fora do índice, o Hard Parts não desce de 21.
- Com o limite de 6 ou de 8 palavras, o resultado é o mesmo. Com 10, o Competente sobe para 28
  referências soltas, ainda sem sequência.
- **Depois do código** (pastas `*-curto`, idênticas ao protótipo `*-prototipo-curto`): o
  Dalgalarrondo e o Hard Parts mudam só como acima, e mais o negrito feito à mão (ADR-0004). O
  Competente, o Huxley, o Tides e o Learning DDD saem com `segmentos/`, `limpos/` e
  `limpeza.json` idênticos, e o `limpos/` do Learning DDD é igual ao da pasta traduzida.

### O que fica

- **O índice com termo-pai sem página no meio** (num EPUB sem marca, uma entrada por parágrafo):
  ele se parte, e os pedaços com menos de 10 entradas ficam lidos.
- **O índice curto,** com menos de 10 parágrafos-entrada, fica.
- **O que sairia:** 10 parágrafos seguidos com até 8 palavras por ", N". Não há caso. O mais
  perto são as referências soltas do Competente.
- **A página de 1500 a 2099** não conta como número de página, porque tem cara de ano (R3 da
  code-review). No índice de um livro de mais de 1.500 páginas, a entrada que só aponta para
  essas páginas parte a sequência, e os pedaços com menos de 10 entradas ficam lidos. Nenhum
  livro medido passa de 503 páginas.
- **A bibliografia do Competente** (p. 481 a 503) fica lida, por decisão do Mateus.
  - Depois de "Referências" (`c023-s1864`) vêm 534 segmentos até o fim do livro: 308 parágrafos e
    226 notas, 7.441 palavras de 154.293. Cada entrada se parte entre parágrafo e nota, às vezes
    em pedaços soltos ("em: 13 out. 2026.", "cnbc.com/2026/06/30/…"), e a sequência ABNT da
    seção "Bibliografia" nunca passa de 1.
  - **Alternativa medida e recusada: a região tolerante.** Aceitar o autor ABNT ou um pedaço com
    "Disponível em", "Acesso em", URL ou "www.", em parágrafo ou nota, com lacunas de até 2
    segmentos que não casam, sem atravessar título, e exigir 10 referências ABNT com ano na
    região. Ela tira 533 segmentos, só do Competente. A lacuna sozinha pegava também a lista de
    posts do autor (`c023-s1332` a `s1506`, 151 segmentos), que tem 0 referência ABNT.
  - **Por que não:** a causa nasce no `importar-pdf`, onde a linha da referência vira nota pela
    fonte, e é lá que se conserta. A região seria a terceira camada de heurística, escrita para um
    livro só, e ainda deixaria a entrada "A10K." e o título "Referências".
- **Fila:** a lista de posts do Competente lê a URL inteira em voz alta ("https://www.
  akitaonrails.com/2026/02/08/…"). É o item "URL" de "O que atrapalha o ouvido", no `AGENTS.md`.

### Correções da revisão (2026-11-03)

Aprovadas pelo Mateus ("Sim, e commitar"). Os seis livros saíram idênticos à medição acima.
- **Lote A, três guardas que já existiam e ganharam teste próprio.** O teste "a vírgula decimal, o
  ano e o ano entre parênteses não são página" tinha os três casos intercalados, e o do ano partia
  a sequência sozinho. Os mutantes M14 (o número antes de ")" conta) e M15 (a vírgula sem espaço
  conta) sobreviviam. O M15 muda o Hard Parts: a tabela do `c008`, com separador de milhar
  ("Billing Payment ss.billing.payment 5 4,312 23"), sairia como índice falso. Agora cada caso
  fica no meio de 10 entradas, num teste próprio, e cada teste passa no código e foi visto falhar
  na asserção com o seu mutante (M13, M14 e M15) numa cópia.
- **Lote B:** `_entrada_de_indice` roda uma vez por segmento (R6).
- **Lote C:** a página de 1500 a 2099 entrou em "O que fica" (R3). **Pendências**, guardas sem
  teste que não mudam os seis livros:
  - **M17:** o título de uma letra só, e não de até 3 caracteres, é a letra do índice;
  - **M18:** a letra depois da última entrada não fecha a sequência;
  - **M20:** só o parágrafo é entrada;
  - **M21:** a entrada precisa de um número de página.

## Consequências

**Ganha:**
- O DDD perde do áudio 64 blocos de código (2.809 palavras), o índice inteiro (5.252 palavras e
  os 696 trechos fora de segmento) e as 321 marcas d'água; a tradução cai para ~73.300 palavras,
  e o `conferir` deixa de acusar código "igual ao original".
- A regra é da marcação, não do livro: todo EPUB da O'Reilly (HTMLBook), todo EPUB 3 com
  semântica estrutural e todo DPUB-ARIA cai nela.

**Perde:**
- O livro montado perde o código também na tela: quem quiser ver o código abre o original.
- Em 19 dos 65 blocos, o parágrafo seguinte cita a linha do código ("after line 7"), e o
  ouvinte não tem a linha.
- O índice no EPUB sem marca (calibre de EPUB 2 antigo, PDF importado) continua lido. Desde
  2026-11-03, sai pelo conteúdo quando tem 10 parágrafos-entrada seguidos ou mais (seção "Índice
  pelo conteúdo").
- O registro do índice em `limpeza.json` é grande (~3 mil palavras por arquivo).
- O Gherkin vira uma linha só: "Given", "When" e "Then" sem pausa entre eles, a não ser a que o
  tradutor puser. E, como `paragrafo`, um parágrafo em minúscula logo depois dele seria juntado
  a ele (nenhum caso no DDD: o de depois começa em maiúscula).

**Aceito conscientemente:**
- O código sai sem aviso. Revisitar pela escuta: se o "depois da linha 7" confundir, a opção C
  (um aviso curto no lugar do bloco) volta à mesa.
- Só o Gherkin é linguagem de prosa. Revisitar quando um livro trouxer outra (Cucumber em outra
  marca, SQL descrito como frase).
- O código em linha (`<code>` no meio do parágrafo) fica.
- A marca d'água num livro de menos de 10 arquivos, ou em menos da metade deles, fica. E um
  parágrafo de verdade idêntico em metade dos capítulos (um refrão) sairia, registrado. Revisitar
  se algum dos dois aparecer num livro medido.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Código sai e fica registrado | teste com EPUB sintético: `<pre data-code-language="csharp">`, `<pre data-type="programlisting">` e `<pre><code>` saem com o motivo "código-fonte" | portão | o bloco fica no texto ou sai sem registro |
| O que não é código fica | testes: Gherkin, `<pre>` sem marca e `<code>` em linha continuam no texto | portão | algum deles sai |
| A junção não atravessa o código | teste: parágrafo sem ponto + código + parágrafo em minúscula continuam três | portão | os dois parágrafos se juntam |
| Índice sai inteiro | testes: `epub:type="index"` no `<section>` e no `<body>`, `role="doc-index"`, `data-type="index"`; o livro montado não tem o termo pai nem as vírgulas | portão | sobra texto do índice no livro montado ou em `texto_fora_de_segmento` |
| O link do `landmarks` não é índice | teste: `<a epub:type="index">` no `nav` fica | portão | o sumário perde o item |
| Marca d'água sai, o repetido de propósito fica | testes: o parágrafo em metade dos arquivos sai, registrado; abaixo da metade, em menos de 10 arquivos, como título, como citação ou sem letra, fica | portão | a marca fica, ou sai texto que não é marca |
| Destaque sai, registrado, e a frase se emenda | testes (`tests/test_destaque.py`): o destaque ao lado do texto, no meio da frase, no meio da palavra partida, com hífen diferente e abrindo no meio da frase do texto sai com o motivo "destaque de margem: repete o texto vizinho"; do PDF de ponta a ponta, a frase da p. 250 volta inteira | portão | o destaque fica, ou a frase não se emenda |
| O que não é destaque fica | testes: título como parágrafo, continuação em minúscula, pergunta com ":", pedaço que abre em algarismo, outro número, outra obra com uma palavra a menos, menos de 6 palavras, texto a mais de 3 segmentos ou em outro capítulo, citação e nota, gêmeos fora do meio da frase | portão | sai texto que o vizinho não repete |
| Bibliografia sai, registrada, só pelo conteúdo | testes (`tests/test_bibliografia.py`): 10 referências ABNT seguidas e o título logo antes saem com o motivo "bibliografia: referências no padrão ABNT"; 9 ficam; a referência sem ano parte a sequência; a APA fica; o título sozinho não tira nada; o título longe das referências fica | portão | a bibliografia fica, ou o título sozinho tira texto |
| Índice sai pelo conteúdo, registrado | testes (`tests/test_indice_pelo_conteudo.py`): 10 entradas seguidas e o título logo antes saem com o motivo "índice remissivo: termos seguidos do número da página"; 9 ficam; a letra no meio sai com o índice; a entrada que termina em remissão conta; mais de 8 palavras por número não é entrada; a vírgula sem espaço (decimal e milhar), o ano e o número antes do parêntese não são página, cada um no meio de 10 entradas; o título sozinho não tira nada | portão | o índice fica, ou sai texto que não é índice |
| Nada a mais some | `preparar` no Huxley e no Tides, `importar-pdf` e `preparar` no Competente e no Hard Parts, comparados com o ADR-0003 e o ADR-0004 | a cada mudança na limpeza | `limpos/` diferente sem explicação |
| Escuta ★ (manual) | o `montar --original` do DDD, num trecho com código e no fim do livro | depois desta mudança; responsável: Mateus | o ouvinte se perde onde o código saiu |

Regras derivadas no `AGENTS.md`: em "O que atrapalha o ouvido", o índice remissivo e o bloco de
código passam a feitos no `preparar` (quando o EPUB os marca), o Gherkin fica, e entra a marca
d'água repetida em metade dos arquivos. Desde 2026-11-03, entram também o destaque de margem que
repete o texto vizinho e a bibliografia ABNT; e o índice do PDF importado passa a sair pelo
conteúdo.

## Fora desta decisão (medido no DDD, para o Mateus escolher a ordem)

- **O índice do PDF:** o `importar-pdf` marcaria o capítulo de título "Index" ou "Índice
  remissivo" com `epub:type="index"`. No Hard Parts, tira 6.198 palavras do áudio; nos outros
  três PDFs medidos não há capítulo com esse título. Resolvido em 2026-11-03 pelo conteúdo, no
  `limpar` (seção "Índice pelo conteúdo"; a marcação pelo título foi recusada).
- **Tabela e legenda:** 217 células com 221 palavras, uma por segmento; 133 legendas "Figure N-N."
  e 3 "Table N-N.", com 1.228 palavras, lidas sem a imagem. Ficam para a escuta da amostra.
- **O destaque marcado no EPUB** (`epub:type="pullquote"`, `role="doc-pullquote"`): sairia pela
  marcação, como o índice, inclusive o resumido. Nenhum dos livros medidos o tem (2026-11-03).
- **Divisão dos tradutores:** o livro vem partido pelo calibre em 321 arquivos
  (`part0007_split_000.html`…), com mediana de 178 palavras; 319 arquivos têm menos de um lote.

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-02 · Aprovado em: 2026-11-02 (pelo Mateus,
na sessão principal: "Aceitar com a marca", que acrescentou a marca d'água à proposta). A seção
"Destaque de margem repetido" foi aprovada em 2026-11-03 ("Aprovar"), e a seção "Bibliografia",
no mesmo dia ("Aprovar"). A seção "Índice pelo conteúdo" foi aprovada em 2026-11-03 ("Aprovar"),
com a bibliografia do Competente de fora.
O número 0008 estava reservado num rascunho para o `earbook adaptar`, que ainda não está no
repositório: aquele ADR passa a ser o próximo número livre.
