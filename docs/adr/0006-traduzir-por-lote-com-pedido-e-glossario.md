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
- **tradução velha:** o texto do pedido difere do texto de `limpos/` hoje (o `limpar` mudou
  depois de exportar; a capitular não se corrige em `limpos/`, ver "Amostra do Tides").
  Corrige-se apagando o pedido e a resposta e rodando `traduzir` de novo;
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

### Escuta da amostra e o livro inteiro (2026-11-02)

O Mateus ouviu `huxley.amostra.epub` no ElevenReader e aprovou as 8 paradas do roteiro ("amostra
está perfeita"). Isso liberou o resto do livro, cujo custo ele já tinha aprovado.

**Glossário**, de 27 para 42 entradas. Antes da tradução entraram os quatro conceitos aprovados
na escuta, na grafia do original: *Mind at Large* → "Mente Ampla", *reducing valve* → "válvula
redutora", *Suchness* → "Talidade" e *Dharma–Body* → "Corpo do Dharma". O *Dharma–Body* do
original usa travessão curto (U+2013), não hífen. Entrou também *Plato* → "Platão". Dos nomes
que a amostra devolveu, ele é o único que volta no resto. Adão, Euclides e os Irmãos Marx só
aparecem na amostra, e o "Meister Eckhart" também: no resto o original diz só "Eckhart", que já
estava no glossário. Com o glossário novo, a amostra continuou passando no `conferir --amostra`.
Depois da tradução, entraram 10 formas que o tradutor devolveu e que ele usou do mesmo jeito em
todas as ocorrências, cada uma em dois segmentos ou mais: *Not–self* → "Não-Eu" (com travessão
curto no original), *Void* → "Vazio", *God* → "Deus", *Constable*, *Lyric Suite* → "Suíte
Lírica", *Doors in the Wall* e *Door in the Wall* → "Portas no Muro" e "Porta no Muro" (pelo
título brasileiro do conto de Wells), *World’s Biggest Drug Store* → "Maior Drogaria do Mundo",
*Native Americans* → "nativos americanos" e *Peyotists* → "peiotistas". Com elas o `conferir`
continuou limpo.

**Tradução.** Os 8 lotes que faltavam (`c005-l003` a `c005-l010`) foram feitos num subagente
`tradutor` só (Opus, o modelo da sessão), como manda o "um por capítulo". O contexto terminou
em 165 mil tokens, longe do limite de 1 milhão, então não houve motivo para dividir.

| | Amostra (2026-11-01) | Resto (2026-11-02) | Estimativa do resto |
|---|---|---|---|
| Lotes, segmentos, palavras | 5, 38, 3.869 | 8, 104, 12.607 | 8, 104, 12.607 |
| Tempo | 5,5 min | 14,9 min | ~18 min |
| Respostas do modelo / chamadas de ferramenta | 12 / 13 | 29 / 28 | — |
| Contexto no fim (o "tokens" do aviso do subagente) | 125.104 | 164.558 | ~410 mil |
| Tokens de saída | 36.395 (9,4 por palavra) | 101.497 (8,1 por palavra) | — |
| Cache lido / cache criado | 907.771 / 123.653 | 2.791.619 / 226.432 | — |
| Medidor semanal da assinatura | 59% → 59% | 64% → 64% | — |

A estimativa errou de medida, não de escala. O número que o aviso do subagente dá é o tamanho
do contexto no fim, e não a soma do que se gastou. A projeção linear da amostra (125 mil × 3,3 ≈
410 mil) multiplicou um pico. O gasto que escala com o livro está na saída (~8 tokens por
palavra) e no cache lido (~220 por palavra), somados da transcrição do subagente. O tempo foi de
~850 palavras por minuto, contra 700 na amostra. Pela mesma régua, o Tides (89.442 palavras)
fica em ~720 mil tokens de saída e ~1 h 45 min de subagente em série. Em paralelo, um subagente
por capítulo, ele cai para o tempo do maior capítulo (c006, 29.488 palavras: ~35 min, com
contexto final na casa dos 300 mil). Nenhuma das duas medições moveu o medidor semanal, que anda de
1 em 1%: o resto do Huxley gastou menos de 1% da semana, e, pelo mesmo teto, o Tides fica abaixo
de ~7%.

**Conferência e montagem.** O `conferir` sem `--amostra` deu 0 segmento faltando, 0 em inglês e
0 nome fora do glossário, já na primeira rodada do tradutor: nada precisou ser corrigido. O
`montar --epub livros/prontos/huxley.pronto.epub` levou 0,26 s e montou 5 capítulos, 142
segmentos e 7 notas no fim do capítulo. O OPF declara `pt-BR` no `dc:language` e no
`dcterms:language`. O epubcheck deu o mesmo único erro do original (OPF-096, a capa sem link).
Relido pelo `preparar`, o livro tem 144 segmentos: os 142 traduzidos, o `www.epubbooks.com` da
folha de rosto e o título "Notas" que o `montar` cria (ADR-0005). A escuta do livro inteiro tem
roteiro próprio (9 paradas, só na parte nova) e espera o Mateus.

**O que o tradutor devolveu como dúvida**, sem que o `conferir` acusasse nada:
- dois erros de digitação do original, traduzidos pelo que o autor quis dizer: "reducing value"
  por *reducing valve* (s0040, que o glossário não cobra, porque o original não tem o termo) e
  "band of geometry, Vermeer" por *branch… . Vermeer* (s0047);
- *the Card in person*, alusão ao romance *The Card*, de Bennett, virou "o Figura em pessoa"
  (s0043): o sentido passa, a referência ao livro se perde;
- *Five and Ten* e *dime-store* viraram "loja de cinco e dez centavos" e "navio de bazar
  barato" (s0056 a s0059). Ele manteve a referência americana em vez de "loja de 1,99";
- a paródia de Pope traduzida com rima (s0115 e s0116), e o haicai de Shiki, literal e sem
  métrica (s0091 a s0093);
- o separador "* * * * *" (s0101) ficou como está. Se a voz ler "asterisco", o defeito é da
  limpeza, e o livro em inglês tem o mesmo;
- nas notas, "Vol. xcviii" virou "Vol. 98" e "No." virou "Número" (s0129 a s0132), para a voz
  não soletrar. As instruções só dizem que o "Vol." fica: converter o número foi escolha dele,
  como a regra do capítulo em romano;
- a sigla "W.B.D.S." virou "M.D.M." (s0035), que a voz lê "eme dê eme", e "Mme Moitessier"
  virou "Madame Moitessier" (s0039);
- a aspa de fechamento solta no fim da nota de Slotkin saiu (s0134). No original, a última
  citação já fecha em "failed.’", e a aspa do fim não tem abertura.

### Amostra do Tides (2026-11-02)

O Mateus escolheu traduzir o Tides, o segundo livro de medição, começando pela amostra.

**Preparar de novo.** Com o código de hoje, o `preparar` deu 2.275 segmentos. Saíram 265 (258
cabeçalhos de página e 7 linhas da página de direitos autorais), com 165 aparos, 290 junções e 26
suspeitas: 25 capitulares, 24 delas com pista, e 1 título. Ficam 1.720 segmentos mantidos. São as
contagens do ADR-0003 e as da tabela do "Contexto", e a pasta nova é idêntica à de 2026-11-01
(`warcraft.earbook`), arquivo por arquivo. O `traduzir` exportou 49 lotes em 0,3 s: 6 capítulos,
o maior lote com 2.000 palavras, e o `c007-l009` (o sumário do fim) com 56.

**Capitular deslocada: corrigida na tradução, pelo brief do tradutor.** (Vale só para livro preparado antes do ADR-0007, que passou a correção para o `limpar`.) O ADR-0003 diz que quem
corrige as duas pontas é o Claude Code, a partir da pista, e esta decisão diz que o agente nunca
grava em `limpos/`. Nenhum comando corrige `limpos/`, e a "tradução velha" acima citava como
exemplo uma correção que não tem caminho. A correção fica em `traduzidos/`: a sessão principal
lê as suspeitas do capítulo em `limpeza.json` e põe no brief de cada `tradutor` o ID, a palavra
inteira e onde está a letra solta. O tradutor traduz a frase reconstruída e descarta a letra.
- **Por que assim:** não muda código, `tradutor.md` nem regra, a amostra mede o resultado na
  escuta, e o pedido continua igual a `limpos/`, sem tradução velha.
- **Na amostra:** foram 3 capitulares, e as 3 saíram certas, sem nenhuma maiúscula solta no
  texto traduzido. O caso mais traiçoeiro é o "A" de *A dark figure*, que estava em "From his
  vantage A point" e parecia artigo.
- **No livro inteiro:** a 25ª capitular (`c007-s0381`, "t will be", com o "I" solto em "near
  the I cliff's edge") não tem pista e precisa ir no brief à mão.
- **O que se perde:** o `montar --original` continua com a letra fora do lugar. O livro em
  português não tem caminho nenhum, porque não passa pelo tradutor: a correção determinística
  que o ADR-0003 deixa para revisitar resolveria os dois casos.

**Glossário.** De 173 candidatos saíram 136 entradas: 74 nomes que ficam como estão e 62
traduzidos. Depois dele sobram 56 candidatos, que são combinações de nomes que já estão no
glossário ("King Terenas", "Orgrim Doomhammer") ou palavras comuns com maiúscula ("Majesty",
"Champion", "Paladin", "Father"), deixadas ao tradutor.
- **Fontes:** o título das páginas do Wowhead em português e as notícias da Blizzard pt-BR,
  registradas no campo `nota`. O Wowhead passou a responder 403 depois de umas 40 consultas.
- **De memória, por isso:** "Pântano das Mágoas" (*Swamp of Sorrows*) ficou de memória.
- **Pela forma do jogo, mesmo divergindo do livro:** Sylvanas → Sylvana, Proudmoore → Proudmore,
  Graymane → Greymane e *Shadow Council* → "Concílio das Sombras".
- **Escolhas do Mateus, onde as fontes divergem ou faltam:**
  - *Rend* e *Maim* → "Laceral" e "Mútilo", a forma oficial;
  - *Black Tooth Grin* → "Riso Dente Negro", pelo sentido, como os outros clãs;
  - *Silver Hand* → "Punho de Prata", a forma oficial, e não "Mão de Prata";
  - *Demon Soul* → "Alma Demoníaca", sem fonte pt-BR.
- **Limite:** "Trovão Furioso" (*Stormreaver*) só foi achado em nome de item. O glossário cobra
  maiúscula, por isso *warchief* e *Warchief* têm duas entradas, "chefe guerreiro" e "Chefe
  Guerreiro".

**Amostra.** Foram 6 lotes, 133 segmentos e 5.944 palavras (6,6% do livro): o rosto, a página
da editora, a dedicatória, os dois prólogos, o começo do capítulo 1 e o sumário do fim
(`c002-l001`, `c003-l001`, `c004-l001` a `c004-l003` e `c007-l009`). Entram 3 capitulares, 1
frase partida pelo cabeçalho de página e 34 nomes do glossário. Num subagente `tradutor` só
(Opus, o modelo da sessão):

| | Amostra do Huxley | Resto do Huxley | Amostra do Tides |
|---|---|---|---|
| Lotes, segmentos, palavras | 5, 38, 3.869 | 8, 104, 12.607 | 6, 133, 5.944 |
| Tempo | 5,5 min | 14,9 min | 8,8 min (676 palavras por minuto) |
| Respostas do modelo / chamadas de ferramenta | 12 / 13 | 29 / 28 | 16 / 18 |
| Contexto no fim | 125.104 | 164.558 | 110.212 |
| Tokens de saída | 36.395 (9,4 por palavra) | 101.497 (8,1 por palavra) | 60.062 (10,1 por palavra) |
| Cache lido / cache criado | 907.771 / 123.653 | 2.791.619 / 226.432 | 934.492 / 106.334 |
| Medidor semanal da assinatura | 59% → 59% | 64% → 64% | 66% → 66% |

O Tides gasta mais saída por palavra que o Huxley (10,1 contra 8,1 a 9,4). É a amostra com mais
coisa a decidir: nomes, capitulares e o registro das falas. A tradução tem 6.158 palavras, 3,6% a
mais que o original.

**Conferência e montagem.** O `conferir --amostra` passou já na primeira rodada do tradutor, sem
correção. O `montar --amostra` levou 0,3 s: 133 segmentos e 1.587 de fora. O OPF declara `pt-BR`
no `dc:language`, e a folha de rosto, `xml:lang="pt-BR"`. O epubcheck deu os mesmos 9 erros do
original, todos RSC-005: `img` sem `alt`, `img` fora de bloco, `name` em `<a>` e um `id` inválido
no `toc.ncx`. Relida pelo `preparar`, a amostra tem os mesmos 133 segmentos, e uma junção mostra
a frase partida: "…Eles soltaram" + "de repente os braços de Gul’dan". Com a continuação
traduzida em minúscula, a regra junta as duas metades. No livro montado elas continuam em dois
parágrafos, e o roteiro pergunta se a voz pausa no meio. Fica no texto, fora de segmento, o
"Tides of Darkness" do sumário do fim, que é lido em inglês.

**Estimativa do livro inteiro**, pela régua medida (8,1 a 10,1 tokens de saída por palavra e 676
a 850 palavras por minuto). Faltam 43 lotes, 1.587 segmentos e 83.498 palavras.
- **Saída e cache:** de 680 a 840 mil tokens de saída e de 13 a 18 milhões de cache lido.
- **Em série:** de 1 h 40 min a 2 h 05 min.
- **Em paralelo, um tradutor por capítulo:** são 4 subagentes, com 17.491, 20.713, 29.488 e
  15.806 palavras. O tempo é o do maior, o `c006`: de 35 a 44 minutos, com contexto final na
  casa dos 250 a 300 mil.
- **Medidor semanal:** nenhuma das três medições o moveu, e ele anda de 1 em 1%. O teto é de 1%
  para cada ~12 mil palavras, o que dá menos de ~7% da semana.

**O que o tradutor devolveu como dúvida**, sem que o `conferir` acusasse nada:
- **Registro das falas dos orcs:** o original é formal e não tem fala quebrada, e a tradução
  também. Ele usou "você" com pronome oblíquo ("Eu o reconheço como chefe guerreiro da Horda").
- **Nome composto como sujeito:** "Martelo da Perdição" e "Mão Negra" vão sem artigo e
  concordam no masculino ("Mão Negra está morto"). O plural de clã é "os Trovão Furioso". Para
  o ouvido, ele acrescentou "clã" em "líder do clã Rocha Negra". Em `c004-s0099`, o segmento é
  só "Martelo da Perdição.", que tanto pode ser o orc quanto a arma, como no original.
- **Termos de Warcraft sem fonte conferida:** "bruxo" (*warlock*, o nome da classe no jogo),
  "ogro-mago", "titã", "Cavaleiro Campeão", "espadão" (*greatsword*). "Magus", o título de
  Medivh, ficou "o Magus".
- **Títulos de capítulo:** "first prologue" e "ONE" viraram "Primeiro prólogo" e "Um". O
  roteiro pergunta se "Um" soa como título; se não soar, o resto pode usar "Capítulo 1", e isso
  se decide antes de traduzi-lo.
- **Página da editora:** "Pocket Star Books" e "Simon & Schuster" ficaram como no original, e
  "POCKET STAR BOOKS" foi para caixa normal. O endereço ("1230 Avenue of the Americas, New
  York, NY" e "10020") também ficou como está. Ele é sobra da página de direitos que a limpeza
  não reconhece (ADR-0003).
- **Lista de cidades:** ganhou vírgulas, para a voz pausar.
- **Fim do livro:** "New York City", na biografia, virou "Nova York".
- **Erros do original, traduzidos pelo que o autor quis dizer:** *refuges* virou "refugiados"
  e *speed their process* virou "aceleraria a marcha".
- **Nome no lugar do pronome:** em `c004-s0059`, "ele" ficava ambíguo, e ele escreveu "Lothar".
- **Pensamento sem aspas:** ficou "Maldito seja ele! Gul’dan pensou".
- **Medidas:** ficaram em pés, e *threescore* virou "sessenta".

**Escuta da amostra (2026-11-02).** O Mateus ouviu no ElevenReader as 9 paradas do roteiro, e
tudo passou. Ele decidiu que os títulos de capítulo ficam como no original ("Um", "Dois"…) e que
o sumário do fim e o endereço da editora ficam no texto.

Antes do resto, o glossário passou de 136 para 146 entradas. Entraram as escolhas da amostra que
voltam em outros capítulos: *warlock* → "bruxo" (74 vezes, em 4 capítulos), *ogre mage* →
"ogro-mago", *titan* → "titã", *greatsword* → "espadão" e *gryphon* → "grifo". Entraram também os
plurais delas e *death knight* → "cavaleiro da morte", a classe do jogo. Com o glossário novo, a
amostra continua passando no `conferir --amostra`. O livro inteiro espera o sim do Mateus ao
custo.

### O Tides inteiro (2026-11-02)

O Mateus disse sim ao custo ("Sim, traduzir"). Os 43 lotes que faltavam foram para 4 subagentes
`tradutor` em paralelo, um por capítulo (Opus, o modelo da sessão). Cada brief trazia as
capitulares e as frases partidas do capítulo, lidas de `limpeza.json` e dos pedidos: foram 22
capitulares e 23 frases partidas.

| Capítulo | Lotes | Palavras | Tempo | Saída (por palavra) | Cache lido | Contexto máximo |
|---|---|---|---|---|---|---|
| `c004` (resto) | 9 | 17.491 | 16,7 min | 126.839 (7,3) | 1.846.082 | 210.154 |
| `c005` | 11 | 20.713 | 13,0 min | 85.758 (4,1) | 3.191.853 | 173.936 |
| `c006` | 15 | 29.488 | 25,5 min | 197.907 (6,7) | 3.582.005 | 317.191 |
| `c007` (resto) | 8 | 15.806 | 16,9 min | 122.767 (7,8) | 3.156.869 | 202.042 |
| **Total** | 43 | 83.498 | 26,6 min de relógio | 533.271 (6,4) | 11.776.809 | — |

**Real contra a estimativa.** A estimativa errou para cima, e o erro foi de medida:
- **Saída:** 533 mil tokens, contra 680 a 840 mil (6,4 por palavra, contra 8,1 a 10,1).
- **Cache lido:** 11,8 milhões, contra 13 a 18 milhões.
- **Tempo:** 25,5 minutos para o maior capítulo, contra 35 a 44. Somados em série, os quatro
  dariam 72 minutos, contra 1 h 40 min a 2 h 05 min: cerca de 1.160 palavras por minuto por
  subagente.
- **Contexto do `c006`:** 317 mil, pouco acima dos 250 a 300 mil previstos.
- **Medidor semanal:** de 67% para 68%.

A amostra é a pior régua de custo: ela concentra as decisões (nomes, capitulares, registro), e o
capítulo longo dilui a leitura do glossário e das instruções. O `c005`, sem trecho difícil no
começo, ficou em 4,1 tokens por palavra. Com isso o Tides inteiro, amostra incluída, moveu o
medidor em no máximo 2 pontos (66% antes da amostra, 68% depois do livro, com o resto da sessão
no meio), e o "Aceito conscientemente" abaixo não precisa ser revisitado por ele.

**Glossário, de 146 para 158 entradas.** Os tradutores devolveram nomes fora do glossário, e
entraram:
- **Formas oficiais confirmadas na web:** Montanhas Cristarrubra (*Redridge Mountains*, zona 44
  do Wowhead pt), Lamaçal Negro (*Black Morass*), Ferro Negro (*Dark Iron*) e Olho Morto
  (*Deadeye*).
- **Formas do brief:** Estepes Ardentes (*Burning Steppes*) e General Patrulheira (*Ranger
  General*).
- **Uma forma só para *stormhammer*:** "martelo de tempestade", a do `c006` e do `c007`. O
  `c005` tinha escrito "da tempestade".
- **Formas oficiais que o `c006` usou de memória, sem conferir na web:** Floresta do Canto Eterno,
  Amparo da Luz, Vale da Lua Negra e Asaclara.

O `conferir` cobrou as entradas novas em 9 segmentos: 5 do `c005` e 4 do `c007`. Os mesmos
tradutores corrigiram tudo numa rodada, em 16 e 26 segundos.

**Conferência e montagem.**
- **`conferir`:** 0 segmento faltando, 0 em inglês e 0 nome fora do glossário.
- **`montar --epub livros/prontos/tides.pronto.epub`:** 1,3 s, 7 capítulos e 1.720 segmentos. O
  OPF declara `pt-BR`.
- **epubcheck:** os mesmos 9 erros RSC-005 do original.
- **Releitura pelo `preparar`:** 1.720 segmentos, 31 junções e 1 suspeita.
  - As junções são as frases partidas: com a continuação traduzida em minúscula, a regra as
    junta. No livro montado, cada uma continua em dois parágrafos.
  - A suspeita é um parágrafo só com "Os", que antes era "The", seguido de "irmãos Mão Negra…".
- **Capitulares:** nenhuma maiúscula solta no texto traduzido. A única é o "V" de "um V
  gigantesco", que é do texto.

**O que os tradutores devolveram como dúvida**, sem que o `conferir` acusasse nada:
- **Dialeto:** o original escreve em dialeto a fala dos trolls ("you be wantin'") e a dos anões
  (*ye*, *dinna*). Os trolls ganharam concordância quebrada ("Nós não conversa com petisco"); os
  anões, um registro popular leve ("a gente", "pra"). Os dois vão para a escuta.
- **Defeito do EPUB de origem:** `c004-s0481` é uma cópia truncada do começo de `c004-s0482`.
  Como segmento de entrada é segmento de saída, a voz lê a frase duas vezes. Tirá-la é mudança
  na limpeza.
- **Erros do original, traduzidos pelo que o autor quis dizer:**
  - *invaluable* no sentido de "sem valor" (`c004-s0286`);
  - *comented*;
  - *Alter of Storms*;
  - "well was I was gone";
  - "Turalyon’ hammer";
  - "Pikemen were defending by swordsman".
- **Nomes que ficaram em inglês, sem forma oficial achada:** Nekros Skullcrusher, a tribo
  Witherbark e Rakmar Sharpfang, uma vez cada, mais os nomes gaélicos dos anões.
- **Termos criados por um tradutor só:** "Rainha Dragão" (*Dragonqueen*), "necrólitos",
  "thane-chefe" e "Urluk Mata-Nuvens".
- **"Sir" e "Lorde":** "Sir" ficou. "Lorde" sai em minúscula no meio da frase em quase todo o
  livro, e o `c005` às vezes usa maiúscula. "Paladino" também varia de maiúscula entre
  capítulos. Nenhuma das duas diferenças se ouve.
- **Clímax:** "your world" virou "o mundo de vocês", para não soar "o mundo dele".

A escuta do livro inteiro tem roteiro próprio (`livros/trabalho/roteiro-de-escuta-tides.md`, 9
paradas, só na parte nova) e espera o Mateus.

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
- Até o ADR-0007, a capitular deslocada era corrigida só na tradução, pelo brief do tradutor (ver "Amostra do
  Tides"). O `conferir` não sabe se ela foi corrigida, o `--original` a lê fora do lugar e o
  livro em português fica sem correção.

**Aceito conscientemente:** o custo por livro é medido por um livro só, o Huxley inteiro
(2026-11-02, em "Escuta da amostra e o livro inteiro"). Revisitar o tamanho do lote e o modelo se
o Tides inteiro não couber em uma semana de uso (ADR-0001).

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

Autor: Mateus, com o Claude Code · Criado em: 2026-11-01 · Aprovado em: 2026-11-01 ·
Atualizado em: 2026-11-02 (escuta da amostra e medição do livro inteiro; amostra do Tides; o
Tides inteiro)
