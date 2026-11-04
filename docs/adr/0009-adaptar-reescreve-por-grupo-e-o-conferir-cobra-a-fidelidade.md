# 0009 — O `adaptar` reescreve o livro didático por grupo de segmentos, e o `conferir` cobra a fidelidade

**Status:** Aceito
**Data:** 2026-11-03
**Driver ★:** escuta: o livro didático vira texto corrido, feito para ser ouvido (pedido do Mateus)

**Bottom line:** o Python exporta pedidos por lote, como na tradução; o subagente `adaptador`
responde com grupos, em que N segmentos de origem viram M parágrafos; o `conferir` cobra que cada
ID foi usado uma vez e que nenhum número e nenhum termo raro das fontes se perdeu ou foi
inventado; o `montar` põe o texto do grupo no lugar do primeiro segmento. Inverte se a medição
do trecho de teste mostrar que o `conferir` de fidelidade deixa passar um critério ou um número
perdido que a leitura humana acha, ou se o custo do livro inteiro passar de 6 pontos do
medidor semanal.

## Contexto

O Mateus pediu: "Adaptar livros didáticos e técnicos para um formato corrido feito para ser
ouvido." O protótipo é o *Psicopatologia e Semiologia dos Transtornos Mentais*, de Paulo
Dalgalarrondo (Artmed, 2008, 438 páginas, pt-BR), importado de PDF. A conversão limpa fechou na
Fase 1 (commits `50cd35b` a `d15ea05`): colunas, número de página, capitular, destaque de margem,
Quadro no lugar, versalete, bibliografia, índice e texto repetido.

Já está decidido (2026-11-02, decisão do Mateus) que a adaptação é uma etapa do earbook, o
comando `earbook adaptar`, e não um projeto à parte: copiar o earbook duplicaria toda correção, e
um projeto que lê o EPUB do earbook reescreveria o `preparar`, o `conferir` e o `montar`, a
duplicação que o ADR-0003 recusou. Já está decidido também que ela segue a tradução: o Python
exporta, confere e monta; o Claude Code adapta; o Python nunca chama o LLM (ADR-0001).

O que o livro pede, medido em 2026-11-03 em `livros/trabalho/dalgalarrondo-curto.earbook`
(HEAD `d15ea05`, segmentos mantidos):

| Medida | Valor |
|---|---|
| Capítulos, segmentos, palavras | 42, 4.180 (3.922 parágrafos, 258 títulos), 152.259 |
| Maior capítulo | `c022`, "O juízo de realidade e suas alterações": 257 segmentos, 10.954 palavras |
| Segmentos com algo que só funciona no papel | 1.994 (48%), com 68.404 palavras (45%) |
| Citação autor-ano entre parênteses | 382, em 331 segmentos; mais 229 na forma "Autor (ano)" e 30 "et al." |
| Quadro e Tabela | 79 Quadros e 2 Tabelas, 626 segmentos e 6.771 palavras dentro deles; 42 remissões "(Quadro N.N)" no texto |
| Marcador de lista | 374 `•`, 225 itens que abrem em "– " e 612 que abrem em "N. " |
| Sigla | 74 distintas, 291 ocorrências (fora as 159 linhas em caixa alta) |
| Subtítulo em caixa alta, como parágrafo | 159 ("SINTOMAS AFETIVOS", "DEFINIÇÕES BÁSICAS") |
| "Questões de revisão" e "Semiotécnica" | 38 blocos de questões (204 perguntas, 2.515 palavras); 22 "Semiotécnica", quase todas dentro de um Quadro |
| Destaque de margem que o `limpar` não tirou | uns 60 (ADR-0008, "O que fica"); 107 parágrafos repetem 8 palavras de um vizinho |
| Ortografia anterior a 2009 | 417 tremas, 384 "idéia"/"paranóide", 216 hífens antigos ("auto-estima") |

**A diferença de modelo.** Na tradução, um segmento de entrada é um de saída (ADR-0006). Na
adaptação, N viram M: o Quadro de 15 segmentos vira três parágrafos, a lista vira uma frase, o
destaque repetido sai, e a frase que o destaque partia ("…piora dos sintomas no período da ma-"
| destaque | "nhã…") volta a ser uma.

**O que a medição achou e o rascunho não previa.** O Quadro é uma tabela de duas ou mais colunas
lida linha a linha, e as colunas chegam misturadas no mesmo segmento:

```
c031-s0098 | • Baixa auto-estima TD grave sem ou com sintomas psicóticos
c031-s0099 | • Concentração prejudicada TD com características catatônicas (estupor
c031-s0100 | • Pensamentos de morte ou suicídio depressivo): imobilidade, negativismo, mutismo,
```

A coluna da esquerda são os critérios do DSM-IV-TR; a da direita, os subtipos. A caixa de
sintomas sem rótulo do mesmo capítulo (`c031-s0011` a `c031-s0065`) tem o mesmo defeito: "SINTOMAS
PSICÓTICOS" seguido de "Ruminações com mágoas antigas", que é sintoma ideativo. Pelo texto, nem o
agente desfaz com segurança o que é de cada coluna. A página do PDF, lida com o layout
(`pdftotext -layout`, p. 310), separa as duas colunas sem ambiguidade. O Quadro 9.1 depende de cor
("Em preto… Em branco… Em azul"), que só a imagem da página mostra.

Quantum atual: 1 (CLI local + pasta de trabalho em arquivos). Continua 1: nada aqui distribui.

## Drivers

| ★ | Característica | Origem | Como se mede |
|---|---|---|---|
| ★ | Escuta | "formato corrido feito para ser ouvido" | no livro montado, 0 marcador de lista, 0 "Quadro N.N" ou "ver Tabela", 0 citação "(Autor, ano)", 0 sigla que a decisão manda por extenso; a escuta única do trecho de teste sem tropeço |
| | Fidelidade do conteúdo | num livro de psiquiatria, perder ou inventar critério, número ou dose é o risco maior | cada número das fontes (fora o ano de citação e o rótulo) está no texto do grupo, e nenhum número novo aparece; cada termo raro das fontes está no texto ou declarado como omitido; o Quadro 27.1 conferido à mão contra a p. 310 |
| | Integridade (ADR-0001) | um parágrafo perdido é um buraco no áudio | cada ID mantido aparece uma vez só, num grupo ou num descarte com motivo, no capítulo e no lote dele |
| | Retomabilidade | ~96 lotes; o limite de uso conta | refazer custa 0 adaptação para lote gravado e conferido |
| | Testabilidade sem LLM | quem escreve o código é o agente | a suíte roda offline; a adaptação nos testes é JSON montado em código |
| | Custo | a assinatura tem limite semanal | o livro inteiro move no máximo 6 pontos do medidor; o segmento sem nada a adaptar custa só o ID |

## Dimensões emaranhadas

- **Formato da resposta × `montar`:** se a resposta pode juntar segmentos, o `montar` precisa
  saber onde pôr o texto e o que tirar. Se pode criar parágrafos, precisa criar elementos.
- **Formato da resposta × `conferir`:** o grupo é a unidade de fidelidade. Grupo grande demais
  (o capítulo inteiro) dilui a cobrança: o número que sumiu de um parágrafo pode reaparecer em
  outro.
- **Política de citação × checagem de número:** se a citação sai, o ano dela sai junto. O
  `conferir` tem de saber que ano é de citação e que ano é dado ("primeiramente editada em 1913").
- **Política de sigla × glossário:** a sigla que vai por extenso é exatamente a regra do glossário
  da tradução (ADR-0006): onde o original tem a forma, o texto tem a outra.
- **Corte do lote × frase partida:** o grupo não atravessa lote; se o lote corta no meio de uma
  frase que o destaque partia, o agente não a junta.

## Alternativas consideradas

### 1. Quem decide e onde mora a adaptação

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Regras determinísticas no `limpar` (tirar `•`, tirar "(Autor, ano)", expandir sigla por tabela) | barato, testável, sem LLM | a lista não vira frase, o Quadro não vira parágrafo, a coluna misturada continua misturada, a sigla que o livro expande sozinho fica dita duas vezes | resolve 1/3 do pedido; o resto pede julgamento |
| B. O agente reescreve `limpos/` | nenhum formato novo | perde a origem limpa, contra a qual se cobra a fidelidade; contradiz o ADR-0006 e o ADR-0007 | falha na fidelidade |
| C. O agente reescreve o capítulo inteiro num arquivo só, sem IDs | o texto fica mais livre | não há como cobrar ID, número ou termo por trecho; a falha no meio perde o capítulo; o `montar` perde a estrutura (ADR-0005) | falha na fidelidade e na retomabilidade |
| **D. Pedido por lote, resposta por grupo `{fontes, texto}`, `conferir` de fidelidade** | o agente escreve só o que muda; a unidade de retomada é o lote; a fidelidade é cobrada por grupo; o `montar` continua trocando texto no XHTML original | dois formatos e duas pastas novas; o `conferir` ganha regras heurísticas (termo raro) que vão errar nos dois sentidos | — |

A opção A não é descartada: o que for regra segura (o `•` do item de questão, o sumário de papel
com pontilhado) pode descer para o `limpar` depois, quando a adaptação mostrar o que se repete
sem julgamento.

### 2. Como a resposta representa N → M

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Um segmento de entrada, um de saída (como a tradução) | o `montar` não muda | o Quadro, a lista e o destaque não se resolvem | não adapta |
| B. Grupo de fontes vizinhas, um parágrafo por grupo (o rascunho) | o `montar` só troca e tira, como na junção do ADR-0003 | o Quadro de duas colunas misturadas não se separa em dois parágrafos: as palavras de cada coluna estão em todos os segmentos | falha no Quadro, que é o caso que mais pede |
| **C. Grupo de fontes vizinhas, um ou mais parágrafos por grupo** | o Quadro 27.1 vira "os critérios" e "os subtipos", cada um num parágrafo; a epígrafe põe a atribuição antes dos versos | o `montar` cria elementos novos, irmãos do primeiro, com a mesma tag | — |
| D. Grupo com fontes não vizinhas | junta o que a página separou | a ordem do áudio deixa de ser a do livro; a fidelidade fica difícil de cobrar | sem caso que a opção C não resolva |

### 3. Como o agente lê o Quadro de colunas misturadas

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Só pelo texto do pedido | nada novo | o agente adivinha a coluna: é o "inventar critério" do segundo driver | falha na fidelidade |
| B. O `importar-pdf` passa a separar as colunas da tabela | resolve na origem, para o `--original` também | detectar tabela pelas caixas do pdfminer é outra Fase 1, com régua de um livro só; atrasa a Fase 2 | fica como melhoria, se a adaptação mostrar que custa caro |
| **C. O agente lê a página do PDF original (`pdftotext -layout`, ou a imagem da página quando há cor)** | separa as colunas que o texto mistura; nenhum código novo no Python | só vale para livro que veio de PDF; o agente gasta a leitura da página (~2 mil tokens por Quadro); o caminho do PDF vem de `decisoes.md` | — |

O `conferir` continua cobrando contra o texto das fontes, não contra o PDF: as palavras e os
números do Quadro são os mesmos, só a ordem muda, e a cobrança é por conjunto, não por ordem.

## Decisão

### O que é do Python: `earbook adaptar livro.earbook [--palavras 2000]`

- **Recusa** o livro que não está em português (`pt`, pela normalização do ADR-0006). A adaptação
  do livro técnico em inglês, depois da tradução, fica fora desta decisão.
- **Exporta** o que falta, em lotes de até `--palavras`, sem atravessar capítulo. O lote termina
  antes de um título; sem título entre a metade e o limite, entre duas frases (o anterior fecha
  com `.`, `!`, `?`, `…` ou `:` e o seguinte não abre em minúscula); sem nenhum dos dois, no
  primeiro corte entre frases depois do limite. Assim o destaque e a frase que ele partia caem no
  mesmo lote (a regra da junção do ADR-0003 deixaria cortar antes do destaque, que abre em
  maiúscula). Pedido gravado nunca é reescrito, e a
  numeração conta pedidos e respostas, como na tradução.
- **Lista as siglas** que o glossário ainda não tem (`siglas.json`): a palavra de duas letras
  maiúsculas ou mais que o livro não escreve em minúscula, com as vezes, o ID de um exemplo e a
  forma por extenso que o próprio livro dá, quando ela vem antes de "(SIGLA)". É o `nomes.json` da
  sigla: barato, e a sessão decide.
- **Cria `decisoes.md`** com as seções da adaptação quando ele não existe (citação, sigla, lista,
  Quadro, questões, epígrafe, ortografia, o PDF de origem), e nunca o lê (ADR-0007).
- Imprime, por capítulo, os lotes pendentes, as palavras e os caminhos.

### O que é do Claude Code

1. Rodar `earbook adaptar`.
2. Montar o glossário das siglas a partir de `siglas.json` e escrever `decisoes.md`, pelas
   decisões do Mateus, antes de distribuir.
3. Um subagente `adaptador` por capítulo (`.claude/agents/adaptador.md`), como o `tradutor`. Ele
   lê o glossário e `decisoes.md`, lê cada pedido em ordem, consulta a página do PDF quando o lote
   tem Quadro, Tabela ou caixa de colunas, grava a resposta de cada lote assim que o termina e roda
   `conferir --amostra --capitulo`.
4. Rodar `earbook conferir` e a rodada de correção, como na skill `traduzir-livro`.

### Onde a adaptação mora (só `adaptadores/pasta_de_trabalho.py` conhece)

```
para-adaptar/cNNN-lNNN.json   Python grava: [{id, papel, texto}] do lote, em ordem
adaptados/cNNN-lNNN.json      agente grava: a lista de grupos do lote (abaixo)
siglas.json                   Python grava: [{sigla, vezes, exemplo, extenso}], fora do glossário
glossario.json                agente grava: [{original, traducao}], a sigla e a forma que se ouve
decisoes.md                   Python cria uma vez; a sessão escreve
```

A resposta é uma lista de grupos. Cada grupo tem `fontes` (IDs vizinhos, na ordem do pedido) e
exatamente um destes:

```json
[
  {"fontes": ["c031-s0003", "c031-s0004", "c031-s0005", "c031-s0006"],
   "texto": ["Versos de Fagundes Varela.", "E pouco a pouco se esvaece a bruma, …", "…", "Como isto é pobre, insípido, enfadonho!"]},
  {"fontes": ["c031-s0008"], "texto": ["Do ponto de vista psicopatológico, as síndromes depressivas têm como elementos mais salientes o humor triste e o desânimo. …"]},
  {"fontes": ["c031-s0010"], "igual": true},
  {"fontes": ["c031-s0087"], "descarte": "rotulo"},
  {"fontes": ["c031-s0116"], "descarte": "repetido"},
  {"fontes": ["c041-s0130"], "texto": ["…"], "omitidos": [{"termo": "Minimental", "motivo": "o grupo diz miniexame do estado mental, o nome que o livro dá ao lado"}]}
]
```

- **`texto`**: um ou mais parágrafos. O grupo de título tem um só, e o grupo não mistura papéis:
  o rótulo "Quadro 27.1" sai como descarte, e a legenda e o conteúdo viram parágrafos.
- **`igual`**: o segmento fica como está em `limpos/`. Custa o ID, não o texto: 52% dos segmentos
  do Dalgalarrondo não têm nada a adaptar.
- **`descarte`** com motivo fechado: `repetido` (o destaque e o gêmeo; o `conferir` prova que cada
  número e termo dele está no texto de um grupo vizinho), `rotulo` (o texto é só "Quadro N.N",
  "Tabela N.N" ou o número do capítulo repetido; o `conferir` confere pela forma) e
  `decisao: <seção de decisoes.md>` (o que o Mateus mandou tirar; o `conferir` conta e lista, para
  a sessão ler).
- **`omitidos`**: o termo raro que o grupo deixou de fora de propósito, com o motivo. O `conferir`
  não o acusa e lista todos no resumo.

Lista e não objeto, pelo motivo do ADR-0006: a chave repetida sumiria sem aviso.

### O que o `conferir` passa a cobrar no modo adaptação (fitness functions)

O modo vem da existência de `para-adaptar/`, num livro em português. Além do que já cobra
(ADR-0005), por capítulo e por lote, cada um vira um problema com o ID e o lote:

1. **Integridade.** Cada ID mantido do capítulo está em exatamente um grupo, de qualquer tipo.
   Falha: ID sem grupo ("N segmentos sem adaptação", por capítulo); ID em dois grupos ou em dois
   lotes; ID que não está no pedido do lote; fontes que não são vizinhas na ordem do pedido;
   resposta sem pedido; grupo vazio; grupo que mistura título e parágrafo; grupo de título com
   mais de um parágrafo.
2. **Adaptação velha.** O texto do pedido difere de `limpos/` hoje. Corrige-se como na tradução:
   apagar pedido e resposta e rodar `adaptar` de novo.
3. **Número.** Falha quando um número das fontes não aparece no texto do grupo, com a mesma
   contagem ou mais, ou quando o texto tem um número que as fontes não têm. Número é a sequência de
   algarismos com vírgula ou ponto decimal ("51,1", "17,5", "1-4", "10h"), comparada como está.
   Ficam fora da conta, porque a política de citação os tira: o número dentro de um parêntese de
   citação ("(Del Pino, 2003)", "(1985, p. 16)", "(Murray; Lopez, 1996)"), o ano logo depois de um
   nome ("Sullivan (1983)"), o número do rótulo "Quadro 27.1" e da remissão "(Quadro 27.1)", e o
   ordinal "N." que abre o segmento e a chamada de nota colada à palavra ("EUA1", "Áustria2", na
   Tabela 19.1). O ano entre colchetes ("Freud [1911]") é dado e conta. A
   dose ("mg") não aparece no livro, mas, se aparecer, conta como qualquer número.
4. **Termo.** Termo é a palavra de 8 letras ou mais das fontes que aparece em até 20 segmentos do
   livro (no Dalgalarrondo, 6,7 por parágrafo: "anedonia", "hipersonia", "catatônicas",
   "distímico"). Comparada sem acento, sem caixa, sem o hífen de dentro da palavra (o
   "divi-dem-se" da regra do composto, ADR-0008) e sem a terminação de gênero e número (`-a`, `-o`,
   `-as`, `-os`, `-es`, `-s`), para que "freqüente" seja "frequente" e "deprimido" seja "deprimida".
   Falha quando o termo das fontes não está no texto do grupo nem em `omitidos`. O nome de autor
   dentro da citação fica fora, como o ano. **A régua (8 letras, 20 segmentos) é um ponto de
   partida:** ela se calibra no trecho de teste, contando o que acusa e o que deixa passar, antes do
   livro inteiro.
5. **Descarte.** `repetido` falha quando um número ou termo do segmento descartado não está no
   texto dos grupos vizinhos, o anterior e o seguinte juntos, no lote (o destaque "Distimia é uma
   depressão crônica…", `c031-s0104`, tem "Distimia" no título antes e o resto no parágrafo
   depois). O destaque que fica no meio da frase que ele parte não é descarte: entra no grupo que
   emenda a frase, porque as fontes de um grupo são vizinhas. `rotulo` falha quando o texto não é
   um rótulo. `decisao` falha sem o nome da seção.
6. **Só funciona no papel**, no texto adaptado. Falha com: `•`; travessão ou "N." abrindo
   parágrafo de lista; "Quadro N.N", "Tabela N.N", "Figura N"; "ver p.", "p. N" fora de citação
   mantida; "(Autor, ano)" e "et al."; pontilhado de sumário ("....."); linha de formulário ("–––",
   "___"); "p. ex."; e a sigla que o glossário manda por extenso (a regra do glossário do ADR-0006,
   sem mudança).
7. **Escuta,** como na tradução: parágrafo vazio e caractere que o XML não aceita.

O resumo do `conferir` lista, sem recusar, os `omitidos` e os `decisao`, por motivo, para a
sessão ler antes do `montar`.

### Como o `montar` usa N → M

- Para cada grupo com `texto`: o primeiro parágrafo entra no elemento do primeiro ID das fontes;
  cada parágrafo seguinte vira um elemento novo, irmão logo depois, com a mesma tag e sem
  `data-earbook`; os outros IDs das fontes saem, como a junção do ADR-0003 (a âncora vai para o
  bloco seguinte, ADR-0005).
- `igual`: o texto de `limpos/`. `descarte`: o elemento sai.
- O resto do ADR-0005 não muda. `montar --amostra` monta só o que tem adaptação, como na tradução:
  é o EPUB da escuta de teste.

### Fronteiras que mudam

- O agente grava também `adaptados/`; nunca `para-adaptar/`, `segmentos/` nem `limpos/`.
- O agente `adaptador` lê o PDF original (fora da pasta de trabalho, só leitura), pelo caminho que
  a sessão põe em `decisoes.md`. O Python não lê o PDF nessa etapa: o `pdfminer` continua só em
  `adaptadores/pdf.py` (ADR-0004).
- `siglas.json` é do Python; o glossário das siglas, da sessão.

### Decisões do Mateus (2026-11-03)

As decisões de gosto foram tomadas por texto, sem ouvir, em
`livros/trabalho/decisoes-adaptar-dalgalarrondo.md`, que tem o antes e o depois de cada uma. A
pergunta foi "Aceita as recomendações? Se sim, as 'Questões de revisão' ficam ou saem?", e a
resposta, "Sim, para estudar". Entram em `decisoes.md` do livro e no `adaptador.md`:

1. **O mecanismo deste ADR:** grupos N → M, a página do PDF lida pelo adaptador, o `conferir` de
   fidelidade.
2. **Citação:** "(Autor, ano)" sai inteira; em "Autor (ano)", fica o nome e sai o ano; "et al."
   vira "e colaboradores"; o ano entre colchetes e a data dada como fato ficam. O ano também fica,
   como "em 1949", quando a frase diz que ele é a data do fato.
3. **Sigla:** a consagrada fica sigla, com o nome antes na primeira vez do capítulo quando o livro
   o dá (OMS, QI, TDAH, CID-10); a do livro vai sempre por extenso (SRAA, SNC, TD, RM); EUA vira
   "Estados Unidos"; o "(MN)" do `c042` sai. "DSM-IV" vira "DSM quatro", e a escuta confirma.
4. **Subtítulo em caixa alta:** caixa normal, com ponto.
5. **Lista:** até 5 itens curtos viram uma frase; lista maior, ou de frases, fica um item por
   parágrafo, sem marcador; o "N." sai; nunca se anuncia quantos itens são.
6. **Quadro e Tabela:** o rótulo sai, a legenda abre o parágrafo, o conteúdo vira parágrafos pela
   página do PDF; na tabela de números, uma frase por linha, repetindo o lugar.
7. **Remissão:** "(Quadro N.N)" sai; "No Quadro 27.2, são apresentadas…" vira "A seguir, são
   apresentadas…".
8. **Questões de revisão: ficam, uma por parágrafo, sem o marcador, porque o Mateus ouve para
   estudar.**
9. **Semiotécnica:** fica no lugar, como Quadro; as perguntas ao paciente continuam perguntas.
10. **Destaques restantes:** saem pelo adaptador, com a prova do `repetido`.
11. **Epígrafe:** a atribuição vem antes ("Nas palavras de Fagundes Varela:"), sem ano nem datas
    de vida.
12. **Asterisco e fonte de tabela:** a nota entra no lugar da chamada; a fonte segue a regra da
    citação.
13. **Ortografia anterior a 2009:** não se atualiza; o adaptador copia a grafia do livro.
14. **Abreviação:** "p. ex." vira "por exemplo"; "a.C.", "antes de Cristo"; "[...]" sai; "etc."
    fica.
15. **Trecho de teste:** o capítulo 27 inteiro (`c031-s0001` a `c031-s0146`), a escuta única.
16. **O sumário de papel e a propaganda do `c001`:** vão para a fila do `limpar`, numa sessão à
    parte, antes do livro final. O adaptador não toca neles.
17. **Datas de vida no corpo do texto:** saem, como na epígrafe, e nenhuma palavra nova entra no
    lugar (decidido depois do capítulo 29: "Sim aos quatro").

### Implementação (2026-11-03)

O que o código decidiu além do texto acima, cada comportamento com o teste visto falhar na
asserção antes:
- **Módulos.** `dominio/adaptacao.py` (grupo, lote que não parte frase, os textos do `montar`),
  `dominio/siglas.py`, `dominio/fidelidade.py` (número, termo raro, papel e rótulo),
  `dominio/conferencia_da_adaptacao.py` e `comandos/adaptar.py`. A `pasta_de_trabalho.py` estava
  com 399 linhas: a leitura e a gravação validadas do JSON saíram para
  `adaptadores/registros_da_pasta.py`, que não sabe onde cada arquivo fica. O layout continua só
  em `pasta_de_trabalho.py`, e a única supressão do `json.loads` foi junto.
- **A numeração dos lotes** saiu de `novos_pedidos` para `lotes_numerados` e `ainda_sem_pedido`,
  usados pela tradução e pela adaptação. A tradução corta e numera como antes.
- **O `igual` também é conferido:** o que fica como está é o que se ouve, então o `•`, a
  "(Autor, ano)" e a sigla que vai por extenso que ficarem num `igual` são acusados.
- **O modo** é `Modo.ADAPTACAO`, escolhido quando o livro em português tem `para-adaptar/`. O
  livro em português sem ela continua recusando `--amostra` e `--original`. A adaptação não troca
  o idioma do OPF.
- **O N → M no XHTML** é uma passada própria, `acrescentar_paragrafos`, antes do `montar_xhtml`:
  os irmãos entram sem marca e com a classe do primeiro, e o `montar_xhtml` não mudou.
- **Avisos:** o `conferir` lista o termo omitido e o descarte por decisão, sem mudar o código de
  saída.

### Correções da revisão (2026-11-03)

A code-review (high) e a code-audit acharam quatro defeitos de comportamento, todos
reproduzidos. O Mateus aprovou os lotes A e B e, do C, o A7 e a leitura dupla ("Sim"). Cada
correção veio com o teste de regressão visto falhar na asserção antes:
- **A1:** o parágrafo a mais copiava o texto solto que vinha depois do elemento, e a voz o lia
  de novo. Agora o texto solto vai só depois do último irmão.
- **A2:** o grupo com `"texto": []` tirava as fontes sem descarte nem motivo, quando elas não
  tinham número nem termo raro. Agora a leitura o recusa.
- **A3:** "vitamina B12" trocada por "vitamina B6" passava, porque todo algarismo colado a uma
  letra era tido como chamada de nota. Agora só o algarismo único colado a uma palavra de 3
  letras ou mais ("EUA1", "Brasil3") fica fora da conta.
- **A4:** o parêntese com intervalo ou página e uma maiúscula virava citação: "(poeta chinês da
  Dinastia Tang, 618-960)" perdia os números sem aviso. Agora só o ano de verdade faz a citação,
  e os números e termos desse parêntese passam a ser cobrados.
- **A5:** o lote sem corte seguro crescia sem teto; 300 itens de lista sem ponto davam um lote de
  7.800 palavras. Agora o lote vai até 2 vezes o limite e, sem corte seguro, corta onde couber.
  No Dalgalarrondo, nada muda: são 103 lotes, e o maior tem 1.999 palavras.
- **A7:** o item do sumário em descarte, juntado a outro ou com mais de um parágrafo ficava no
  original, calado. Agora o `conferir` o acusa, porque no sumário nada sai (ADR-0005).
- **A leitura dupla:** o `conferir` lia `adaptados/` duas vezes, uma para os problemas e outra
  para os avisos. Agora `conferencia_da_pasta` devolve os dois de uma leitura só, e os avisos só
  saem no modo adaptação.
- **Mutantes que sobreviviam:** a metade no corte do lote, a prioridade do título e a prova do
  `repetido` pelo grupo seguinte ganharam teste, cada um visto falhar com o seu mutante.

Ficam registrados, sem correção:
- **A6:** a fala que abre com travessão é acusada como item de lista. São 22 parágrafos no
  livro: o diálogo literário e as perguntas da semiotécnica. O adaptador tira o travessão, o que
  o ouvido não percebe.
- **As funções acima da meta de 20 linhas** (`_grupo`, `adaptar`, `_resumo_da_adaptacao`,
  `textos_da_adaptacao`), dentro do teto de 40.

### O trecho de teste: o capítulo 27 (2026-11-03)

O Dalgalarrondo foi preparado de novo, com o código deste ADR, em
`livros/trabalho/dalgalarrondo-adaptado.earbook`. O `limpos/` é idêntico ao da
`dalgalarrondo-curto.earbook`. A sessão montou o glossário com as 9 siglas do capítulo e o
`decisoes.md` com as decisões do Mateus e o caminho do PDF. Um subagente `adaptador` (Opus, o
modelo da sessão) adaptou os 2 lotes.

| Etapa | Resultado |
|---|---|
| `adaptar` | 103 lotes no livro, o maior com 1.999 palavras; o `c031` em 2, e o segundo começa no rótulo do Quadro 27.1 |
| Adaptação | 45 grupos para 142 segmentos: 29 respostas do modelo, 55.572 tokens de saída, 3,6 min, 1,24 milhão de cache lido. Leu as p. 307 a 310 e 313 pelo layout e as 308 e 309 pela imagem |
| `conferir --amostra --capitulo c031` | 1 problema na primeira rodada: "transtorno depressivo" em minúscula, que o glossário cobra com a caixa. Depois, nada a corrigir; nenhum termo em `omitidos` |
| Quadro 27.1, à mão, contra a p. 310 | os 11 critérios na coluna deles, depois os 3 subtipos e as 5 características; nada perdido nem inventado; só saiu o "(APA, 2002)", pela regra da citação |
| `montar --amostra` | `livros/trabalho/dalgalarrondo-adaptado-c031.pronto.epub`, epubcheck sem erro nem advertência |
| Texto montado | 2.008 palavras, ~14,6 min a 138 palavras por minuto; roteiro em `livros/trabalho/roteiro-de-escuta-dalgalarrondo-c031.md`, com 12 paradas |

O que o adaptador decidiu sozinho, e que a escuta confere:
- a caixa de sintomas virou um grupo só (`c031-s0011` a `c031-s0069`), para pôr na ordem da
  página o poema de Schmidt, que o `importar-pdf` tinha posto antes de "Perdas e depressão". É o
  grupo grande que este ADR quer evitar, mas o trecho não tem número fora das citações;
- a atribuição do poema ficou na frase do próprio livro ("o poeta Augusto Frederico Schmidt
  fala…");
- "faz-se estão" virou "faz-se então".

O resumo do `montar --amostra` dizia "sem tradução" no livro adaptado; passou a dizer "sem
adaptação", com o teste visto falhar na asserção antes (o Mateus: "Commitar e publicar").

**Real contra a estimativa.** A estimativa errou para baixo na saída e para cima no tempo:
- **Saída:** 55.572 tokens, contra 25 a 45 mil: 25,4 por palavra do capítulo e 42,5 por palavra
  adaptada;
- **Tempo:** 3,6 min, contra 5 a 10, ou ~600 palavras de origem por minuto.

**A estimativa do livro inteiro, refeita pelo trecho:**
- **Saída:** a 42,5 tokens por palavra adaptada, dá ~2,9 milhões para as 68.404 palavras. Com o
  viés de amostra que a skill registra (o Tides gastou 0,63 vez a amostra, e o DDD, 1,47 vez), a
  faixa vai de 1,8 a 4,3 milhões.
- **Medidor:** pela régua do DDD (1,22 milhão moveu ~3 pontos), de 4,5 a 10,5 pontos, com ~7 no
  centro.
- **Tempo:** o maior capítulo (`c022`, 10.954 palavras) leva ~18 min, e o livro, uns 25 min de
  relógio, com um adaptador por capítulo em paralelo.

**A condição de inversão deste ADR é passar de 6 pontos, e o centro da estimativa passa.** O
capítulo 27 é mais denso que a média: tem 60% do texto a adaptar, contra 45% no livro, e um
Quadro e uma caixa lidos pela página. Fica para o Mateus decidir entre medir um capítulo típico
antes ou aceitar o custo.

### A escuta de teste (2026-11-03)

O Mateus ouviu o capítulo 27 no ElevenReader, pelo roteiro, e passou. A pergunta foi "Você já
ouviu o capítulo 27, e ele passou?", e a resposta, "Ouvi, passou". As 12 paradas passaram:
epígrafe, citação, sigla ("OMS", "CID-10", "DSM quatro TR"), caixa de sintomas, lista, Quadro,
remissão, destaque, Semiotécnica e Questões de revisão. O `adaptador.md` não muda, e esta é a
escuta única do `AGENTS.md`: a etapa nova fica aprovada pelo ouvido.

### O capítulo típico e o custo refeito (2026-11-03)

O capítulo 27 é o mais denso que se poderia medir, então o custo foi medido de novo num capítulo
típico, com a mesma pasta, o mesmo `adaptador.md` e um subagente só. Por script, o típico é o
**`c033`, capítulo 29, "Síndromes neuróticas"**:

| Medida | Livro | `c033` | `c031` | `c022` |
|---|---|---|---|---|
| Texto a adaptar, pela régua deste ADR | 45% | 42% | 59% | 40% |
| Texto a adaptar, pelas regras do `conferir` | 57% | 55% | 63% | 53% |
| Palavras | mediana 2.761, média 3.904 | 3.308 | 2.187 | 10.954 |
| Segmentos por mil palavras | 27,5 | 28,4 | 64,9 | 23,5 |
| Quadros e Tabelas por capítulo | ~2 | 2 | 2 | 3 |

A régua do Contexto (45%) não conta o "N." de item numerado, e a do `conferir` conta: é a mesma
pergunta, com duas contagens. O `c022` acerta a proporção, mas tem quase o triplo da média de
palavras. O `c039`, que parecia típico pelas regras do `conferir`, dá 56% na outra régua.

| Medida | `c031` (2 lotes) | `c033` (2 lotes) |
|---|---|---|
| Grupos, segmentos | 45, 142 | 56, 94 |
| Palavras do capítulo | 2.187 | 3.308 |
| Tokens de saída | 55.572 | 53.362 |
| Tokens por palavra do capítulo | 25,4 | 16,1 |
| Tempo | 3,6 min | 3,35 min |
| Palavras de origem por minuto | ~600 | ~990 |
| Cache lido | 1,24 milhão | 0,98 milhão |
| Palavras em `igual` | 22% | 30% |

Do `c033`:
- **`conferir`:** nada a corrigir, com 2 avisos: os termos "caracterizam" e "comporta", que só
  existiam no destaque ou partidos por ele;
- **Quadro 29.1, à mão, contra a p. 324:** as 13 linhas, cada lado na coluna certa, nada perdido
  nem inventado.

**O `igual` economiza menos do que este ADR previa.** O Contexto supõe que 55% das palavras
sairiam só pelo ID, e sai de 22% a 30%: o adaptador reescreve também o segmento que tem destaque,
frase partida ou hífen de quebra, que a contagem não vê. Por isso a régua boa é a palavra do
capítulo, e não a palavra adaptada.

**A estimativa do livro inteiro, pelos dois capítulos:**
- **Saída:** ~2,45 milhões de tokens a 16,1 por palavra, a régua do capítulo típico. Um ajuste
  aos dois capítulos (8,9 tokens por palavra mais 254 por segmento) dá 2,42 milhões, mas são dois
  pontos para dois parâmetros, sem prova nenhuma. Com a rodada de correção e o glossário das
  siglas, ~2,7 milhões. A faixa vai de 2,1 a 3,3 milhões: o piso é 15% de diluição no capítulo
  longo, e o teto, os dois capítulos somados (19,8 por palavra) com 10% de correção.
- **Medidor:** pela régua do DDD (1,22 milhão moveu ~3 pontos), **~6,6 pontos, de 5,1 a 8,0.** O
  medidor não foi lido antes e depois dos dois capítulos.
- **Tempo:** o maior capítulo (`c022`) leva de 11 a 18 min, e o livro, uns 20 min de relógio com
  um adaptador por capítulo.

**A condição de inversão.** O centro passa pouco dos 6 pontos, e a faixa a atravessa. A condição
foi escrita antes de qualquer medida. Ela existe para parar um custo fora de proporção, e 6,6
pontos para 152 mil palavras é a régua do livro técnico (~1 ponto a cada 22 mil palavras dá 6,9).
Não há alternativa mais barata com a mesma fidelidade: o custo vem do julgamento em cada parágrafo.
O Mateus decide, com o medidor zerado, se o custo fica.

**O Mateus aceitou o custo.** A pergunta foi "Aceita o custo e os outros três pontos?", e a
resposta, "Sim aos quatro": ~6,6 pontos (de 5,1 a 8,0), acima da condição dos 6. O livro inteiro
só começa depois que o medidor zerar, em 6 de novembro.

**Achados do `c033`, resolvidos pelo mesmo "Sim aos quatro":**
- **"Autor e colaboradores (ano)"** não era tido como citação, porque `_DEPOIS_DE_NOME` pedia
  maiúscula ou "al.". São 7 no livro. No `c033-s0096`, o adaptador tinha mantido "em 2004",
  contra a decisão 2. O `conferir` passou a reconhecê-lo.
- **Decisão 17: as datas de vida no corpo do texto saem,** como na epígrafe, e nenhuma palavra
  nova entra no lugar. São 44, como "Jaspers (1883-1969)". No `c033-s0094`, o adaptador tinha
  escrito "que viveu de 1839 a 1883". A regra da citação passou a aceitar "(cerca de 460-377
  a.C.)", o único caso que ela não pegava.

### O sumário de papel e a propaganda saem no `limpar` (2026-11-03)

O Mateus aprovou ("Sim aos quatro"), antes do livro inteiro, porque a remoção muda o `limpos/` e
o adaptador não deve pagar por esse texto. As duas regras ficam em `dominio/fora_do_audio.py` e
entram em `limpeza.json`, com o motivo:
- **Sumário de papel:** sai a linha com 5 pontos seguidos e número no fim, quando o capítulo tem
  5 ou mais. A conta por capítulo é uma proteção acrescentada na implementação: a linha solta pode
  ser de um quadro ou de um formulário.
- **Propaganda:** sai o título exatamente "Conheça também", com os parágrafos até o próximo
  título, se forem até 5. Com mais, é texto do livro, e nada sai. A regra é de uma frase só: a
  propaganda com outro título fica.

Medido contra o HEAD `5d4325a`, com os seis livros de ponta a ponta:
- **Dalgalarrondo:** só o `c001` muda, de 94 para 50 segmentos: 41 linhas do sumário e 3 da
  propaganda. O `segmentos/` é idêntico, e no EPUB montado só muda o `c001.xhtml`.
- **Competente, Hard Parts, Huxley, Tides e Learning DDD:** `segmentos/`, `limpos/`,
  `limpeza.json`, `livro.json` e o EPUB montado são idênticos, fora o UUID e a data do OPF do
  `importar-pdf`, e o `conferir` das pastas traduzidas dá a mesma saída.

Ficam no `c001` 9 segmentos do sumário sem pontilhado: o título "Sumário", 4 títulos "parte", os
3 títulos das partes ("1 ASPECTOS GERAIS DA PSICOPATOLOGIA") e a primeira linha do capítulo 21. O
adaptador os descarta por decisão, quando chegar ao `c001`.

**A pasta.** O `preparar` recusa pasta que já existe, então o livro seguiu em
`livros/trabalho/dalgalarrondo-adaptado-2.earbook`, com o mesmo EPUB, o glossário, as decisões e
as respostas do `c031` e do `c033`. Os pedidos desses dois capítulos saíram byte a byte iguais, e
nenhuma resposta ficou velha. O `c001` ganhou pedidos novos e não tinha resposta.

**Fila, fora desta rodada:** o pontilhado com espaços (". . . . . 23") não sai. São 37 linhas no
Competente e 20 no Hard Parts, e cobri-lo muda esses dois livros: é uma rodada própria, depois do
Dalgalarrondo (decisão do Mateus). O título "Conheça também:", com dois-pontos, também não é
pego.

**Da revisão desta rodada,** com a pergunta "Corrijo os lotes A e B?" e a resposta "A e B":
- **A1:** um número sozinho entre parênteses depois de um nome era tido como citação: "Escala de
  Glasgow (15)" sem o 15 passava, e com o 15 era acusada. Agora, depois do nome, só a forma de
  data é citação: ano, intervalo de 3 ou 4 algarismos, ou data com "a.C.". Teste visto falhar
  na asserção antes; o Dalgalarrondo não tinha caso.
- **Dois testes novos** (o limite de exatos 5 parágrafos da propaganda e a caixa do título),
  cada um visto falhar com o seu mutante, e o comentário de `_PAGINA_DO_INDICE` de volta ao lugar.

No `c033`, os grupos `c033-s0094` e `c033-s0096` foram refeitos pelas decisões novas: "Georg Miller
Beard, em 1869," e "Segundo Kirmayer e colaboradores,". O `c031` não mudou: o `conferir` novo não
acusou nada nele.

## Consequências

**Ganha:**
- O livro didático chega ao ElevenReader como texto corrido: o Quadro é dito, a lista é frase, a
  citação não interrompe, a sigla é dita como o ouvinte entende.
- A fidelidade é cobrada por máquina, por grupo, antes do `montar`: número perdido, número
  inventado e termo sumido param o livro.
- O segmento que não precisa de nada custa o ID, e a retomada custa no máximo um lote.
- O que o `adaptar` mostrar que se repete sem julgamento pode descer para o `limpar`.

**Perde:**
- Dois formatos e duas pastas novas, mais `siglas.json`; o `montar` passa a criar elementos.
- A cobrança de termo é heurística: o termo comum reescrito por sinônimo passa (só o raro é
  cobrado), e o raro omitido de propósito tem de ser declarado. Um critério reescrito com as
  mesmas palavras raras e o sentido trocado ("pelo menos cinco" por "no máximo cinco") passa: o
  número está lá. Esse risco só a leitura humana pega, e é por isso que o Quadro 27.1 entra no
  trecho de teste e é conferido à mão contra a p. 310.
- O número escrito por extenso no original ("duas semanas") não é cobrado; o adaptador não pode
  trocá-lo por algarismo, nem o contrário.
- O agente lê o PDF: a adaptação de um Quadro depende de um arquivo fora da pasta de trabalho, e o
  livro de EPUB nativo com tabela não tem essa fonte (usa o `<table>`, que o `preparar` já parte
  em células).
- O agente escolhe o grupo: um grupo grande demais (um Quadro inteiro com o parágrafo seguinte)
  dilui a cobrança, porque o número pode migrar entre parágrafos do mesmo grupo. As instruções
  limitam o grupo ao Quadro, à lista ou à frase partida.
- A nota de rodapé adaptada em mais de um parágrafo: o primeiro vai para "Notas", no fim do
  capítulo, e os outros ficam onde a nota estava. O Dalgalarrondo não tem nota (Fase 1).
- Mais custo que a tradução de romance por palavra adaptada (estimativa abaixo, em
  `decisoes-adaptar-dalgalarrondo.md`, seção 13).

**Aceito conscientemente:**
- Só livro em português. Revisitar quando um livro técnico em inglês pedir adaptação depois da
  tradução: a fonte do pedido passa a ser `traduzidos/`.
- A separação das colunas do Quadro no `importar-pdf` (alternativa 3B) fica de fora. Revisitar se
  o trecho de teste mostrar que a leitura do PDF pelo agente custa mais de 1/3 do lote.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Integridade | `conferir` no modo adaptação | antes do `montar` (recusa) e testes | ID sem grupo, em dois grupos, fora do lote, fontes não vizinhas, grupo que mistura papéis |
| Fidelidade: número | `conferir`, por grupo | idem | número das fontes faltando, ou número que as fontes não têm |
| Fidelidade: termo | `conferir`, por grupo, com a régua calibrada no trecho de teste | idem | termo raro das fontes fora do texto e fora de `omitidos` |
| Descarte | `conferir` | idem | `repetido` com número ou termo que o vizinho não tem; `rotulo` que não é rótulo |
| Escuta ★: só funciona no papel | `conferir`, no texto adaptado | idem | `•`, "Quadro N.N", "(Autor, ano)", "et al.", "p. ex.", pontilhado, sigla por extenso que ficou sigla |
| N → M no livro montado | teste de contrato: grupo de 3 fontes e 2 parágrafos → `montar` → `preparar` lê 2 parágrafos na posição do primeiro | portão | texto fora do lugar, fonte que sobrou, âncora perdida |
| A régua do termo | contagem no trecho de teste: o que o `conferir` acusa e o que a leitura acha | uma vez, antes do livro inteiro; responsável: a sessão | acusação falsa em mais de 1 grupo a cada 10, ou um termo perdido que ele não acusou |
| Fidelidade (manual) | o Quadro 27.1 e a caixa de sintomas do `c031` comparados à mão com as p. 307 a 310 | no trecho de teste; responsável: a sessão, com o Mateus | critério ou subtipo trocado de coluna, perdido ou inventado |
| Escuta ★ (manual) | a escuta única do trecho de teste no ElevenReader | depois do código e a cada mudança no `adaptador.md`; responsável: Mateus | tropeço audível |
| Python não chama LLM nem lê o PDF nessa etapa | `test_arquitetura.py` e import-linter, sem mudança | portão | algum módulo importa |

Regras derivadas no `AGENTS.md`:
- A adaptação entra por `earbook adaptar` e pela resposta do lote; o agente grava `adaptados/` e
  nunca `para-adaptar/` nem `limpos/`.
- O adaptador nunca escreve número que as fontes não têm, nem tira número que elas têm, fora o ano
  de citação; termo raro omitido vai em `omitidos`, com o motivo.

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-03 · Aprovado em: 2026-11-03 (pelo Mateus, na sessão principal: "Sim, para estudar"; as correções: "Sim"; o commit: "Commitar e publicar")
Rascunho de origem: a nota de 2026-11-02 da sessão `~/Sara-bookadapt` (o número dela era 0008).
