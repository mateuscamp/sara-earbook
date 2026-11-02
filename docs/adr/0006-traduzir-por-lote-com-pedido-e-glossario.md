# 0006 — O Python exporta a tradução em lotes, o Claude Code traduz por capítulo e o `conferir` cobra cada ID

**Status:** Aceito
**Data:** 2026-11-01
**Driver ★:** qualidade da escuta no ElevenReader (ADR-0001)

## Contexto

A esteira é `preparar → limpar → [traduzir] → conferir → montar` (ADR-0003), e falta o
`traduzir`: nenhum livro em inglês chega a pronto. O ADR-0001 já decidiu que quem traduz é o
Claude Code na sessão, pela assinatura, com um subagente por capítulo, e que o Python nunca
chama o LLM. A saída é um EPUB só com a tradução, porque o TTS leria as duas línguas. O ADR-0005
deixou o lugar pronto: o texto final vem de `limpos/` e, "quando a tradução existir, vem do
segmento traduzido".

O que os livros de medição pedem (contado em 2026-11-01, nos segmentos mantidos):

| Livro | Capítulos com texto | Segmentos | Palavras | Maior capítulo |
|---|---|---|---|---|
| *The Doors of Perception* | 4 | 142 | 16.476 | o ensaio, c005: 134 segmentos, 16.438 palavras (99,8%) |
| *Tides of Darkness* | 6 | 1.720 | 89.442 | c006: 573 segmentos, 29.488 palavras (o "capítulo" é um arquivo do spine, que junta vários capítulos do livro) |

Um capítulo passa do que um subagente grava de uma vez com segurança, e o limite de uso conta:
refazer o que já foi traduzido é desperdício. No Tides há centenas de nomes de lugar e de
personagem, traduzidos por subagentes que não se veem.

Quantum atual: 1 (CLI local + pasta de trabalho em arquivos). Continua 1.

## Drivers

| ★ | Característica | Como se mede |
|---|---|---|
| ★ | Escuta | o `conferir` acha 0 segmento sem tradução, 0 que parece inglês e 0 nome fora do glossário; o livro declara pt-BR; o capítulo de teste é ouvido sem tropeço |
| | Integridade | cada ID mantido tem uma tradução só, no capítulo dele, e nenhuma tradução sobra |
| | Retomabilidade | refazer custa 0 tradução para lote já gravado e conferido |
| | Testabilidade sem LLM | a suíte roda offline; a tradução nos testes é JSON montado em código |

## Alternativas consideradas

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. O agente lê `limpos/` e grava `traducao/cNNN.json` no mesmo formato | nenhum comando novo | o agente copia papel e notas e pode estragá-los; o capítulo do Huxley sai numa gravação de ~25 mil tokens, e o maior do Tides, de ~40 mil, e a falha no meio perde o capítulo; o agente precisa saber o layout, que hoje só o adaptador conhece | falha na retomabilidade e na fronteira |
| B. O agente reescreve o texto dentro de `limpos/` | nenhum arquivo novo | perde a origem limpa: não dá para cobrar o glossário (que compara com o original) nem saber se a tradução é de um texto que mudou | falha na integridade |
| C. O Python chama `claude -p` por lote | roda sozinho | é a opção C que o ADR-0001 rejeitou, e a fronteira proíbe `subprocess` | contradiz o ADR-0001 |
| **D. O Python exporta pedidos por lote, o agente grava a tradução do lote e o `conferir` valida** | o agente só escreve ID e texto; o lote (~2 mil palavras) é a unidade de retomada; o pedido guarda o texto que foi traduzido; o CLI diz os caminhos, e o layout fica no adaptador | duas pastas e três formatos novos na pasta de trabalho; a ordem do trabalho depende de o agente seguir as instruções | — |

Para o glossário: sem glossário, cada subagente escolhe sozinho (`Stormwind` num capítulo,
`Ventobravo` no outro); o glossário que cresce durante a tradução, com cada subagente
acrescentando, briga quando os subagentes rodam em paralelo. Fica o glossário montado **antes**
da tradução, lido por todos e cobrado pelo `conferir`.

## Decisão

### O que é do Python: `earbook traduzir livro.earbook [--palavras 2000]`

- Recusa o livro em português e o de idioma indefinido (ver "O que o `conferir` passa a cobrar"):
  não há o que traduzir, ou não se sabe de que língua.
- **Exporta** o que falta: os segmentos mantidos que ainda não estão em nenhum pedido viram
  lotes de até `--palavras` palavras, sem atravessar capítulo e sem partir segmento (o segmento
  maior que o limite vai sozinho). O lote se chama `c005-l001`. Pedido gravado nunca é
  reescrito, para que a tradução em andamento não fique sem o pedido dela.
- **Lista os candidatos a nome próprio** que ainda não estão no glossário: palavra com
  maiúscula fora do começo da frase, com as vizinhas de maiúscula juntas (`Anduin Lothar`),
  que aparece 2 vezes ou mais, com a contagem e o ID de um exemplo. É determinístico e barato;
  o agente decide o que é nome e como fica, sem ler o livro inteiro para achá-los.
- Imprime, por capítulo, o que está traduzido e os lotes pendentes, a pasta dos pedidos e o
  modelo do caminho da resposta (`traduzidos/<lote>.json`), que o adaptador dá. Rodar de novo
  não refaz nada: é assim que se retoma. O lote novo é numerado depois do maior que já tem
  pedido **ou** resposta, para que o pedido apagado nunca volte com o nome de uma resposta
  velha.

### O que é do Claude Code

1. Rodar `earbook traduzir`.
2. Montar o glossário a partir dos candidatos (`glossario.json`), antes de traduzir.
3. Um subagente por capítulo, com as instruções versionadas em `.claude/agents/tradutor.md`.
   Capítulo menor que um lote vai junto com outros no mesmo subagente. O subagente lê o
   glossário e os pedidos do capítulo em ordem, grava a resposta de cada lote assim que o
   termina, e não escreve no glossário: nome novo vai no relatório dele, e a sessão principal
   acrescenta e roda o `conferir`, que cobra o nome novo também nos capítulos já traduzidos.
4. Rodar `earbook conferir` e corrigir o que ele apontar.

### Onde a tradução mora (só `adaptadores/pasta_de_trabalho.py` conhece)

```
pedidos/cNNN-lNNN.json     Python grava: [{id, papel, texto}] do lote
traduzidos/cNNN-lNNN.json  agente grava: [{id, texto}], a resposta do lote de mesmo nome
glossario.json             agente grava: [{original, traducao}]
nomes.json                 Python grava: [{nome, vezes, exemplo}], candidatos fora do glossário
```

JSON, como o resto da pasta, lido pelo mesmo caminho validado campo a campo. A resposta é
lista, não objeto: num objeto, o `json` guarda só a última chave repetida, e o ID repetido
sumiria sem aviso. O agente escreve só ID e texto; papel e notas vêm de `limpos/`.

### O que o `conferir` passa a cobrar no modo tradução

O modo vem do `idioma` do `livro.json` (ADR-0003). O código é normalizado (`pt_BR`, `pt-BR` e
`por` são `pt`; `eng` é `en`), e o livro que não está em português é traduzido para pt-BR. O
de idioma indefinido (`und`, ou vazio) monta o texto limpo, como antes deste ADR, e o
`traduzir` o recusa pedindo o idioma (decisão do Mateus): é o PDF importado sem `--idioma`.
Além do que já cobra (ADR-0005), por capítulo:
- **todo segmento traduzido:** "N segmentos sem tradução", uma linha por capítulo;
- **nenhum a mais, nenhum repetido, IDs batendo:** tradução de ID que não está em `limpos/`
  do capítulo; ID traduzido em dois lotes; resposta sem pedido; ID respondido num lote que não
  o pediu;
- **tradução velha:** o texto do pedido difere do texto de `limpos/` hoje (o agente corrigiu a
  capitular depois de exportar). Corrige-se apagando o pedido e a resposta e rodando
  `traduzir` de novo;
- **escuta:** tradução vazia; caractere que o XML não aceita; texto igual ao original com
  palavra funcional inglesa (`Table of Contents`); trecho que parece inglês, com 8 palavras ou
  mais e 20% delas palavras funcionais inglesas, URLs fora da conta. O trecho é o segmento
  inteiro e, depois, cada frase: medida só no segmento, a frase inglesa deixada num parágrafo
  traduzido se diluía no português (A1 da auditoria). A frase de 8 palavras ou mais é julgada
  sozinha, e as curtas seguidas, juntas, até ter 8; a frase não se corta depois de inicial
  ("J. R.") nem de título abreviado ("Dr."). Na **nota**, o título de obra em Title Case que
  está igual no original sai da conta, porque as instruções mandam mantê-lo, e as frases
  curtas não se juntam, porque a referência bibliográfica é feita delas (decisões do Mateus,
  F1 da pós-auditoria e A2 e A3 da curta). Fora da nota não há isenção: ela deixava escapar a
  fala esquecida em inglês ("And I will see them suffer for it."). A lista não tem "a",
  "me", "for" nem "do", que também são palavras do português. Medido em 2026-11-01, nos
  segmentos de 8 palavras ou mais: o inglês tem mediana de 36% no Huxley e 37% no Tides, e o
  limiar pega 115 de 124 e 1.508 de 1.546 (os que escapam são verso em francês e frase curta
  só de nomes). O Competente, em português, tem mediana 0% e 28 segmentos acima de 20% em
  3.864, quase todos bibliografia e citação em inglês, que no livro traduzido se traduzem.
  Por frase, o limiar pega 658 de 685 frases do Huxley e 4.417 de 4.628 do Tides, e acusa 73
  de 7.276 do Competente (1%). Com o segmento, as frases juntas e o título isento, o
  `conferir` acusa 117 de 124 segmentos ingleses do Huxley e 1.513 de 1.543 do Tides (114 e
  1.504 se o texto todo for copiado do original, com os títulos fora), e 82 de 4.936 do
  Competente. Cada frase inglesa que o limiar acusa sozinha (4.417 no Tides, 655 no Huxley),
  posta num parágrafo traduzido logo depois de uma frase curta em português ("Ele parou."),
  continua acusada: nenhuma escapa. A amostra traduzida do Huxley chega no máximo a 0,7% no segmento e 1,8% na
  frase. As notas bibliográficas do Huxley, traduzidas como mandam as instruções, passam;
  sem a isenção do título, 2 das 4 seriam recusadas;
- **glossário:** quando o original do segmento tem o nome (palavra inteira), a tradução tem a
  forma do glossário; e, se a forma é outra, o nome original não aparece na tradução. Nome
  repetido no glossário é problema.

### Como o `montar` usa a tradução

- O texto final de cada segmento vem de `traduzidos/`; papel e notas, de `limpos/`. O resto da
  montagem do ADR-0005 não muda: a nota vai para o fim do capítulo, sob "Notas".
- O livro passa a declarar pt-BR: `dc:language` e `dcterms:language` no OPF, e todo `lang` e
  `xml:lang` dos XHTML que tem o idioma do original. Sem isso, o leitor pode escolher a voz
  inglesa para ler português. Trecho marcado com outra língua (`xml:lang="fr"`) fica.

### Nota de rodapé, título e citação (instruções do tradutor)

- **Nota:** traduz-se como parágrafo. O marcador já saiu no `preparar`, e o `montar` a leva
  para o fim. Referência bibliográfica mantém o título da obra no original e traduz o resto
  ("By" → "De", "Vol." fica, mês por extenso em português).
- **Título:** continua título, curto e sem ponto final. Número romano de capítulo vira arábico
  ("Chapter IV" → "Capítulo 4"), porque o TTS lê "i vê".
- **Citação:** traduz-se. Título de obra com tradução brasileira consagrada usa a consagrada
  (*O Casamento do Céu e do Inferno*). Trecho que já vem numa terceira língua no original (os
  versos em francês do Huxley) fica como está: é escolha do autor, e não é a leitura bilíngue
  que o projeto proíbe.
- **Para o ouvido:** sem nota do tradutor, colchete, markdown ou explicação entre parênteses
  que o original não tem; um segmento de entrada é um segmento de saída, nunca juntado nem
  partido.

### Decisões do Mateus (2026-11-01)

- **Amostra:** o Huxley tem um capítulo só, então a amostra é o sumário, o rosto, a epígrafe e
  os 2 primeiros lotes do ensaio. `earbook conferir --amostra` não cobra o segmento sem
  tradução, e `earbook montar --amostra` grava `livro.amostra.epub` só com o traduzido: o
  segmento sem tradução sai, como removido, e nunca fica em inglês. Exceção: o item do sumário
  (`<nav>`) sem tradução fica no original, porque no sumário nada sai (ADR-0005). O custo do
  livro inteiro é mostrado ao Mateus antes de traduzi-lo.
- **Nomes do Tides:** a localização oficial pt-BR da Blizzard (Ventobravo, Altaforja, Horda,
  Aliança, Portal Negro, Orgrim Martelo da Perdição, Alleria Correventos). O nome sem tradução
  oficial fica como está (Khadgar, Turalyon, Anduin Lothar). É o que o fã brasileiro conhece, e
  a voz pt-BR pronuncia melhor.
- **Modelo:** o subagente tradutor usa o modelo da sessão (Opus). A amostra mede o custo.
- **Original:** `earbook montar --original` grava `livro.original.epub` com o texto limpo no
  idioma do original, como o `montar` fazia antes, para ouvir a limpeza antes de gastar a
  tradução. Não é a leitura bilíngue: é uma língua só, e o arquivo nunca vai para
  `livros/prontos/`.
- **Idioma indefinido** (depois da auditoria): o livro `und` ou sem idioma monta o texto
  limpo, como antes deste ADR, e o `traduzir` o recusa pedindo o idioma.

### Medição (2026-11-01)

A amostra do Huxley foi exportada, traduzida por um subagente (Opus, o modelo da sessão),
conferida e montada em `livros/trabalho/huxley.amostra.epub`:

| Etapa | Resultado |
|---|---|
| `traduzir` | 13 lotes em 0,14 s: 3 capítulos pequenos (sumário, rosto, epígrafe) e 10 do ensaio, de 260 a 1.991 palavras |
| Glossário | 27 nomes, montados dos 80 candidatos (Homero, Buda, *Livro Tibetano dos Mortos*, Juízo Final); depois dele e do `Dr` fora da lista, 56 candidatos |
| Tradução | 5 lotes (c002-l001, c003-l001, c004-l001, c005-l001, c005-l002), 38 segmentos e 3.869 palavras (23% do livro), num subagente só: 125.104 tokens, 13 chamadas de ferramenta, 5,5 minutos. O medidor semanal da assinatura ficou em 59% (ele anda de 1 em 1%) |
| `conferir --amostra` | nada faltando; o `conferir` sem opção acusa "c005: 104 segmentos sem tradução" |
| `montar --amostra` | 0,14 s; 38 segmentos, 104 de fora; OPF com `pt-BR` no `dc:language` e no `dcterms:language`, e `xml:lang="pt-BR"` na folha de rosto |
| Releitura pelo `preparar` | 39 segmentos: os 38 traduzidos e o `www.epubbooks.com` da folha de rosto, que no original ficava fora de segmento e continua no livro |
| epubcheck | o mesmo único erro do original (OPF-096, a capa sem link) |

Estimativa para o resto do Huxley, pela amostra: 8 lotes, 104 segmentos e 12.607 palavras,
~410 mil tokens e ~18 minutos. O Tides (89.442 palavras) seria ~23 amostras, ~2,9 milhões
de tokens. O que a amostra não diz: quanto do limite semanal isso é, porque a amostra não
moveu o medidor.

O subagente devolveu, como pedem as instruções, os nomes fora do glossário (Adão, Platão,
Euclides, Mestre Eckhart, Irmãos Marx), os conceitos com maiúscula que escolheu (Mente Ampla
para *Mind at Large*, válvula redutora, Talidade, Corpo do Dharma) e os trechos em que
hesitou (o "Æ" de George William Russell, "Belle of Portugal", a glosa de *Istigkeit*). Os
conceitos que voltam no resto do ensaio entram no glossário depois da escuta.

### Correções da revisão (2026-11-01)

Da code-review, cada uma com o teste visto falhar antes:
- o pedido apagado do último lote voltava com o mesmo nome e casava com a resposta velha,
  que passava no `conferir`: a numeração agora conta pedidos e respostas, só do capítulo;
- o livro `und` exigia tradução, e o PDF em português importado sem `--idioma` deixava de
  montar (ver "Idioma indefinido");
- `epub_padrao(pasta, Modo.TRADUCAO)` dava `KeyError`;
- o nome logo depois de "Dr." ou "Mr." não virava candidato, e o "Dr" virava;
- as funções novas passavam da meta de 20 linhas; a pasta dos pedidos saía de um lote
  fictício "x"; o mapa de pedidos era montado duas vezes.

Da code-audit, numa cópia descartável:
- **A1:** a frase inteira em inglês dentro de um parágrafo traduzido passava; agora cada frase
  é medida;
- **A2 e A3:** `por`, `pt_BR` e `eng` não eram reconhecidos: o livro brasileiro com `por`
  virava livro a traduzir, e com `eng` no OPF o `lang="en"` do XHTML ficava;
- **A4:** o livro sem `dc:language` era traduzido e montado sem declarar pt-BR; agora é de
  idioma indefinido e não se traduz;
- **A5:** resposta, pedido e glossário eram lidos através de link simbólico; agora são
  recusados com o caminho, como o `epub/` (ADR-0005);
- testes para os 20 mutantes que sobreviviam (limiares do inglês, bordas do lote, `lang` da
  raiz `<html>`, `dcterms:language`, o item do sumário na amostra, validações da resposta, do
  glossário e do idioma). Dos 105 mutantes da auditoria, mais 17 escritos depois das
  correções, sobram 6, equivalentes.

Da pós-auditoria, numa segunda cópia descartável, cada uma com o teste visto falhar antes:
- **F1:** a nota com o título da obra no original, como as instruções mandam, era recusada
  como "parece inglês" (o "the" e o "of" do título); agora o título em Title Case copiado do
  original sai da conta (decisão do Mateus);
- **F2:** o corte por frase partia em "J. R." e "Dr.", e o pedaço solto passava dos 20%;
- **F3:** três frases curtas em inglês seguidas passavam, cada uma abaixo de 8 palavras;
- **F4:** `nomes.json` era gravado através de link simbólico, para fora da pasta;
- **F5:** a amostra contava como "de fora" o item do sumário que fica no original; agora a
  CLI diz "1 item do sumário ficou no original";
- idioma por extenso ("Portuguese", "English") é reconhecido;
- testes para os 6 mutantes que sobreviviam (os cortes depois de aspas, reticências, "?" e
  "!"; o "Dr" que não vira candidato; o glossário que é link pendurado; o livro em francês).
  Dos 54 mutantes da pós-auditoria, 52 morrem e 2 são equivalentes; os 13 reescritos para o
  código depois desta rodada morrem todos.

Da pós-auditoria curta, sobre a rodada acima, cada uma com o teste visto falhar antes:
- **A1:** a junção do F3 colava a frase curta em português na frase inglesa seguinte e a
  diluía: 187 frases inglesas reais do Tides escapavam depois de "Ele parou." e 522 depois de
  "Ela olhou para trás, assustada."; agora a frase longa é julgada sozinha, e nenhuma escapa;
- **A2:** a isenção do título valia em todo papel, e a fala e a citação esquecidas em inglês
  escapavam (63 frases no Tides); agora vale só na nota;
- **A3:** na nota, a junção acusava a referência com título em minúsculas; na nota, as frases
  não se juntam;
- **A4:** o título logo depois de uma palavra da tradução ("Ver The Varieties…") não era
  isento; vale o trecho final da sequência que está no original;
- **A5:** `nomes.json` era gravado através de link físico; todo JSON da pasta agora é gravado
  num temporário e trocado no lugar, sem tocar no alvo do link.

## Consequências

**Ganha:**
- O ★ é cobrado por máquina antes do `montar`: inglês esquecido, nome trocado entre capítulos e
  idioma errado no OPF param o livro.
- Interromper no meio custa no máximo um lote (~2 mil palavras).
- O agente nunca toca em papel, nota ou estrutura: o que ele grava é ID e texto.

**Perde:**
- Três formatos novos e duas pastas na pasta de trabalho.
- A checagem de inglês é heurística: um parágrafo curto (`Roses:`, `Epigraph`) que ficou em
  inglês passa, e uma citação longa em inglês deixada de propósito é recusada.
- A checagem do glossário recusa a tradução que troca o nome por um pronome; o tradutor tem de
  repetir o nome.
- Ficam no original, sem segmento: o `dc:title` do OPF, o `<title>` de cada XHTML, o
  `toc.ncx` e o texto fora de segmento (`www.epubbooks.com`, que é lido). O leitor não lê os
  três primeiros como texto, mas pode mostrá-los.
- A troca de idioma só passa pelos XHTML do spine: um XHTML fora dele (um `nav` que não está
  no spine) fica com o `lang` do original.
- A frase toda em inglês com poucas palavras funcionais ("Orgrim Martelo da Perdição raised
  his hammer high above Blackrock Spire") passa: 2 de 15, abaixo dos 20%. A auditoria
  mostrou o caso, e baixar o limiar acusaria mais português (com 15%, 87 frases do
  Competente).
- Na nota, uma frase inglesa copiada do original que seja quase toda em Title Case sai da
  conta como título; o "igual ao original" pega a nota que é só ela.
- Até 7 palavras inglesas em frases curtas soltas entre frases longas em português passam.
- Fora da nota, o título de obra mantido em inglês pode ser acusado: as instruções mandam
  traduzi-lo.
- O idioma por extenso com a região ("Portuguese (Brazil)", "Português do Brasil") vira livro
  a traduzir; a falha é visível, porque o `conferir` acusa tudo sem tradução.
- As instruções do tradutor nomeiam `pedidos/` e `traduzidos/`, as pastas que a CLI imprime:
  o agente conhece esse pedaço do layout, e só esse.

**Aceito conscientemente:** o custo por livro ainda é medido pela amostra do Huxley. Revisitar
o tamanho do lote e o modelo se o Tides inteiro não couber em uma semana de uso (ADR-0001).

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Integridade | `conferir` no modo tradução | antes do `montar` (recusa) e testes | segmento sem tradução, ID a mais, repetido, sem pedido ou no lote errado |
| Tradução velha | `conferir`: pedido × `limpos/` | idem | o texto de origem mudou depois do pedido |
| Escuta ★ | `conferir`: vazio, igual ao original, parece inglês, glossário | idem | qualquer achado |
| Idioma do livro | teste de contrato: livro montado em modo tradução declara pt-BR | portão | OPF ou `lang` com o idioma do original |
| Python não chama LLM | `test_arquitetura.py` (sem `subprocess`, `http`, `socket`) e suíte offline | portão | algum módulo importa |
| Escuta ★ (manual) | roteiro de escuta no ElevenReader | a cada mudança em `.claude/agents/tradutor.md`; responsável: Mateus | tropeço audível |

Regra derivada no `AGENTS.md`: a tradução entra por `earbook traduzir` e pela resposta do
lote; o agente nunca escreve em `limpos/` nem em `pedidos/`.

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-01 · Aprovado em: 2026-11-01
