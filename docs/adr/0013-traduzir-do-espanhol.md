# 0013 — Traduzir do espanhol: o mesmo transporte, com a língua do original como parâmetro

**Status:** Aceito
**Data:** 2026-11-17
**Driver ★:** escuta: o *Miller Anestesia* (8.ª edición, em espanhol) em pt-BR, no lugar do
original que está em `livros/prontos/` desde 2026-11-13

**Bottom line:** o transporte do ADR-0006 já serve ao espanhol: o `traduzir` aceita `es`, o lote,
o pedido, a resposta, `termos/` e o `montar` (que troca `es` por `pt-BR`) não sabem a língua. O que
é inglês está em três lugares, e só eles mudam: o `conferir` acusa o texto que ficou em inglês, mas
deixa passar o que ficou em espanhol; o `tradutor.md` traduz do inglês; o glossário procura nome
próprio, e o que se repete num tratado médico é termo e sigla. A decisão: a lista de palavras
funcionais passa a ser da língua do original (inglês e espanhol, medidas), o `traduzir` recusa a
língua sem lista, um agente novo (`tradutor-es`) traduz do espanhol sem tocar no `tradutor` que a
escuta do Huxley aprovou, e o `traduzir` grava também `siglas.json`. A régua da terminologia é o
*Manica* (*Anestesiologia*, pt-BR, em `livros/trabalho/`): o termo vai para o glossário na forma
que o Manica usa. Inverte se uma terceira língua de origem pedir a mesma lista: aí as palavras
funcionais viram dado medido por língua, e não constante no código.

## Contexto

O Miller foi montado no original em 2026-11-13 (decisão do Mateus: obra comercial se ouve no
original). Agora o Mateus quer ouvi-lo em pt-BR. Medido em `livros/trabalho/miller-anestesia.earbook`:

| | Miller |
|---|---|
| Capítulos | 118 (6 de abertura e 112 do livro) |
| Segmentos limpos | 26.445 |
| Palavras | 2.434.002 (~252 horas de áudio) |
| Lotes de 2 mil palavras | ~1.220 |

O que já funciona sem código: `precisa_traduzir("es")` é verdadeiro, o `montar` troca o `lang`, o
`xml:lang` e o `dc:language` de `es` para `pt-BR` (`TrocaDeIdioma`), e o pedido, a resposta e a
declaração de termos não dependem da língua.

O que é inglês, e por quê importa no espanhol:

| Onde | Hoje | No Miller |
|---|---|---|
| `conferencia_da_traducao.py`, "parece inglês" | palavras funcionais inglesas, 20% do segmento | o segmento esquecido em espanhol passa calado |
| `conferencia_da_traducao.py`, "igual ao original" | só acusa se o igual tem palavra inglesa | o espanhol copiado passa |
| `conferencia_da_traducao.py`, título de obra | Title Case com "of", "the" | não pega nada; o título de obra em espanhol vem em caixa de frase |
| `.claude/agents/tradutor.md` | "do inglês" | falso amigo, sigla e nome de fármaco do espanhol não estão nas regras |
| `glossario.py`, candidatos | palavra com maiúscula fora do começo da frase | o que se repete é "fentanilo", "EPOC", "anestesia intradural" |

## Drivers

| ★ | Característica | Origem | Como se mede |
|---|---|---|---|
| ★ | Escuta | "o livro pronto" | uma escuta de teste da amostra do `tradutor-es`; depois, a leitura do Mateus |
| | Nada fica em espanhol | ADR-0006 | o `conferir` acusa; medido no Miller e no Manica |
| | Terminologia do anestesista brasileiro | tratado médico | o termo do glossário existe no Manica |
| | O inglês não muda | ADR-0006, ADR-0007 | os livros de medição saem idênticos; o `tradutor.md` intacto |
| | Custo | limite semanal | lotes e segmentos mostrados antes, com o sim do Mateus |

## Decisão

### 1. O `conferir` cobra a língua do original, não o inglês

As palavras funcionais passam a ser por língua: as inglesas de hoje e uma lista espanhola, sem as
palavras que o português também tem ("de", "que", "como", "para", "por", "se", "sobre", "entre",
"está"). A mensagem diz a língua ("parece espanhol: 9 de 31 palavras são como 'el', 'los', 'y'").
O "igual ao original" passa a usar a lista da língua do livro.

Medido em 2026-11-17, nos parágrafos de 8 palavras ou mais, com a lista `el, los, las, y, del, una,
es, en, lo, su, sus, pero, muy, más, hay, puede, pueden, también, cuando, donde, sin, son, fue,
han, al, le, les, según, ya, aunque, mismo, están`:

| | Segmentos | Mediana | p5 | p95 | Máximo | Acima de 8% |
|---|---|---|---|---|---|---|
| Miller (es) | 20.344 | 18,8% | 10,0% | 26,9% | 50% | 19.440 (95,6%) |
| Manica (pt-BR) | 13.966 | 0% | 0% | 1,7% | 14,3% | 12 (0,09%) |

A separação existe, mas é mais estreita que a do inglês (37% contra 0%). A sessão filha calibra o
limiar e a medida por frase, como no inglês (ADR-0006, F3 e A1 da curta), contra estes dois corpos,
e registra aqui os números finais. O limiar fica por língua.

#### Calibragem (2026-11-17, sessão filha)

Medida com o código final (`dominio/lingua_do_original.py` e `_parece_o_original_no_papel`), nos
`limpos/` do Miller reimportado em `cdc1a50` e do Manica, tratando o Manica inteiro como se fosse a
tradução. Três achados mudaram a lista e a conta:

- **O que soava espanhol no Manica não era espanhol.** Com a lista acima e a conta do inglês,
  32 segmentos do Manica eram acusados a 8%. As palavras eram o pronome colado ao verbo
  ("preveni-los", "conhecê-las", "com-pará-lo"), a sigla e o eixo ("instilar AL", anestésico
  local; "conector em Y"), o nome ("Le Fort", "Al Shetawi") e o "et al." da referência. Por isso,
  no espanhol, conta **só a palavra em minúsculas, sem hífen de nenhum dos lados e fora de
  "et al."**, que a tradução mantém (999 segmentos do Miller o têm). A maiúscula
  conta na linha toda em maiúsculas (mais de 60% das letras), porque o Miller tem títulos assim
  ("TRATAMIENTO DE LOS PACIENTES TOLERANTES A LOS OPIOIDES"), que o tradutor esquecido copiaria.
  O inglês fica com a conta de antes, sem mudança.
- **Com o pronome colado fora da conta, "la", "un" e "con" entram na lista.** São as palavras
  mais frequentes do espanhol que o português não escreve soltas.
- **A nota do Manica que sobra** é a referência a um livro em espanhol ("Tratado de fisiología
  médica… madrid"), que é espanhol de fato.

A lista final (35 palavras): `el, la, los, las, y, del, al, un, una, con, es, en, lo, le, les, su,
sus, pero, muy, más, hay, puede, pueden, también, cuando, donde, sin, son, fue, han, según, ya,
aunque, mismo, están`. O limiar: **10%**, no segmento e em cada frase (o mesmo corte de frase e a
mesma junção das frases curtas do inglês). As 8 palavras mínimas para julgar ficam.

Nos parágrafos de 8 palavras ou mais:

| | Segmentos | Mediana | p1 | p5 | p95 | Máximo |
|---|---|---|---|---|---|---|
| Miller (es), segmento | 20.136 | 24,5% | 0% | 12,5% | 32,3% | 53,3% |
| Miller (es), frase ou junção | 91.320 | 24,3% | — | 10,5% | 36,5% | 66,7% |
| Manica (pt-BR), segmento | 13.958 | 0% | 0% | 0% | 0% | 2,2% |
| Manica (pt-BR), frase ou junção | 37.384 | 0% | — | 0% | 0% | 12,5% |

Acusados pelo `conferir`, por limiar, contra a lista final:

| Limiar | Miller, dos 20.136 longos | Miller, frases acima | Manica, dos 18.654 |
|---|---|---|---|
| 8% | 19.745 (98,1%) | 97,4% | 2 |
| **10%** | **19.648 (97,6%)** | **95,9%** | **1 (c046-s0178, a referência em espanhol)** |
| 12% | 19.388 (96,3%) | 93,1% | 1 |
| 15% | 18.997 (94,3%) | 88,0% | 0 |

Com a lista do ADR (sem "la", "un", "con") e a conta da palavra solta, os 10% acusavam 94,1% do
Miller e o mesmo 1 do Manica. Os 488 longos do Miller que escapam a 10% são, na amostra lida, a
afiliação e a referência em inglês, a tabela e a lista de números, e o título com a caixa trocada
("aSpEctoS médico-lEgalES"), que o tradutor devolve na caixa normal.

O "igual ao original" usa a mesma conta: o segmento copiado do Miller é acusado quando tem uma
palavra funcional, em 21.766 dos 26.442 (82%); os outros 4.676 são, quase todos (4.378), curtos e
sem palavra funcional ("Propofol", "Tabla 3-1"), que copiados podem estar certos. No Manica, 19
segmentos têm alguma.

O título de obra em espanhol mantido na nota seria acusado: a isenção do título (ADR-0006, F1 da
pós-auditoria) reconhece só o Title Case com conectivos ingleses, e o título em espanhol vem em
caixa de frase, igual à frase esquecida. Por isso o `tradutor-es` traduz o título de obra em
espanhol, e o título em inglês, que não tem palavra funcional espanhola, fica no original. O
Miller cita quase só obra em inglês.

O conferir dos dois livros em inglês já traduzidos neste Mac (*Being You*, *Practical*, e o
*Practical* de antes da reimportação) sai idêntico ao de antes desta mudança, inteiro e na
amostra: 7, 74 e 87 problemas, os mesmos.

A língua sem lista (francês, alemão) é recusada pelo `traduzir`, com o idioma na mensagem: sem a
lista, o `conferir` não acharia o texto que ficou no original, e o defeito iria calado para a voz.

### 2. Um agente novo, `tradutor-es`

`.claude/agents/tradutor-es.md`, com o mesmo contrato do `tradutor` (o pedido, a resposta,
`termos/`, o `conferir --amostra --capitulo` antes de terminar, o relatório) e as regras do
espanhol:

- **Falso amigo:** a lista dos que mudam o sentido num texto médico ("embarazada", "exquisito",
  "largo", "rato", "oficina", "apellido", "polvo", "pelado", "borrar", "salir"), e a regra de
  traduzir pelo sentido, nunca pela semelhança.
- **Sigla:** a forma brasileira, pelo glossário ("EPOC" → "DPOC", "SIDA" → "AIDS", "ADN" → "DNA",
  "TAC" → "TC"); a sigla que não está no glossário entra em `termos/`.
- **Fármaco e termo clínico:** a forma do glossário; fora dele, a de `decisoes.md`.
- **Título em versalete com a caixa trocada** ("EfEctos advErsos", 169 no Miller): o tradutor
  devolve na caixa normal. É o único caminho que conserta esses títulos, que o PDF não guarda
  (ADR-0004, "Bibliografia pela letra e rótulo com a caixa trocada").
- **Número:** o espanhol e o português usam a mesma vírgula decimal; "8.ª edición" vira "8ª edição" e
  "Dres." vira "Drs.".

O `tradutor.md` não muda, para não pedir nova escuta do inglês. A duplicação das regras comuns é
o preço: a regra que mudar num tem de ser revista no outro, e a `code-audit` confere.

### 3. Glossário de termo e sigla, com o Manica como régua

O `traduzir` grava `siglas.json` ao lado de `nomes.json`, com o `siglas_candidatas` do `adaptar`
(ADR-0009), em todo livro: a sigla também se repete no tratado em inglês. A ligação de sigla com
extenso, hoje só em português ("de", "da", "do"), ganha as do espanhol ("de", "del", "la", "los",
"y").

A sessão monta o glossário antes de distribuir os lotes: as siglas e os fármacos mais frequentes,
cada um na forma que o Manica usa. Medido no Manica: "fentanil" 290 vezes e "fentanila" nenhuma,
"remifentanil" 235, "raquianestesia" 196, "DPOC" 44. O que o Manica não tem vai para
`decisoes.md`, com o antes e o depois. No glossário entra só forma fixa (o `conferir` compara
palavra inteira, com caixa); o termo que flexiona mora em `decisoes.md` (ADR-0011).

### 4. O que vem antes da tradução

Defeito de diagramação traduzido se paga duas vezes. O roteiro do Miller lista o que ficou:
a página lida por altura e não por coluna (125 páginas, 107 segmentos com hífen sobrando), o
parágrafo só de números soltos (71 ou mais), o resto de legenda (10) e a fórmula lida como texto.
O tradutor recebe a frase já misturada e não a desmistura pelo ID. A correção da ordem das
colunas é código do `importar-pdf`, numa sessão filha própria, antes da tradução (ver
"Decisões do Mateus").

## Consequências

- O `conferir` de todo livro traduzido passa a cobrar a língua do original. Os livros de medição
  em inglês saem idênticos (a lista inglesa não muda).
- O `traduzir` grava `siglas.json` também nos livros em inglês.
- Um segundo agente de tradução, com a disciplina de revisar os dois juntos.
- O `tradutor-es` é novo: uma escuta de teste, numa amostra do Miller que cubra sigla, fármaco,
  título com a caixa trocada e falso amigo, antes do livro inteiro.
- O AGENTS.md e o README dizem que o livro em espanhol é traduzido, e a linha da obra comercial
  ouvida no original ganha a exceção do Miller.

## Custo

Pela referência do ADR-0006 (o Huxley, 16 mil palavras, menos de 1% da semana; ~8 tokens de saída
por palavra; ~850 palavras por minuto por subagente), o Miller é ~152 Huxleys: da ordem de 1,5
semana inteira de cota, ~19,5 milhões de tokens de saída e ~48 horas de subagente, sem a rodada de
correção. O espanhol está mais perto do português que o inglês, mas o texto médico é denso; a
amostra mede o custo real por palavra antes do sim do livro inteiro.

## Fitness functions

| Regra | Onde |
|---|---|
| O segmento que ficou em espanhol é acusado; o português do Manica não | `tests/test_conferencia_do_espanhol.py`, frases montadas no teste: a frase esquecida no parágrafo, o parágrafo copiado, o título em maiúsculas copiado, o pronome colado, a sigla, o eixo e o nome do Manica, a afiliação em inglês, que fica. Cada regra tem o mutante que um teste reprova |
| A língua sem lista é recusada pelo `traduzir`, com o idioma na mensagem | `tests/test_traduzir.py`, `tests/test_conferencia_do_espanhol.py` |
| `siglas.json` é gravado pelo `traduzir`, com a ligação do espanhol | `tests/test_traduzir.py` (o arquivo, a contagem e a linha do resumo), `tests/test_siglas.py` ("del", "la", "los", "y") |
| O inglês não muda | a suíte do inglês sem asserção mudada; a lista inglesa igual à de antes; o `conferir` do *Being You* e do *Practical* idêntico; `tradutor.md` sem diff. O teste do livro em francês que declara pt-BR passou a ser em espanhol: o francês agora é recusado |
| O agente grava só `traduzidos/` e `termos/` | revisão (`code-audit`) |

## Plano

1. Sessão filha: a ordem das colunas do Miller no `importar-pdf` (ADR-0004), e o Miller
   reimportado e preparado de novo.
2. Sessão filha: o `conferir` por língua, a recusa da língua sem lista, `siglas.json`, o
   `tradutor-es.md`, o ramo do espanhol na skill `traduzir-livro`, README e AGENTS.md; TDD,
   `make check`, `code-review` e `code-audit`.
3. Sessão principal: o glossário (siglas e fármacos pelo Manica) e `decisoes.md`.
4. A amostra do `tradutor-es` e a escuta de teste; o custo medido.
5. Sessão filha: o livro inteiro (ou a parte escolhida), a rodada de correção, `montar --epub
   livros/prontos/miller-anestesia.pronto.epub`, epubcheck e o roteiro de escuta.

## Decisões do Mateus

Tomadas em 2026-11-17, com este ADR na mão:

- **Escopo:** o livro inteiro, os 118 capítulos, sabendo do custo da ordem de 1,5 semana de cota.
  A amostra do `tradutor-es` continua antes do livro inteiro, por ser agente novo ("Uma escuta de
  teste só"); ela mede o custo real por palavra, que volta ao Mateus só se passar muito da
  estimativa.
- **Colunas:** a ordem das colunas se corrige no `importar-pdf` antes da tradução, e o Miller é
  reimportado (passo 1 do plano).
- **Fármaco e termo clínico:** a forma do uso clínico, a que o Manica escreve ("fentanil",
  "remifentanil", "raquianestesia", "DPOC"), e não a da DCB ("fentanila").
