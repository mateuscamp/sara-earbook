# 0003 — O produto é preparar o livro para o ouvido; traduzir é uma etapa opcional

**Status:** Aceito
**Data:** 2026-11-01
**Driver ★:** qualidade da escuta no ElevenReader (o mesmo do ADR-0001)

## Contexto

Em 2026-11-01 o `preparar` rodou em dois EPUBs reais, guardados em `livros/`, que o git
ignora. Os dois rodaram sem erro e com as notas tratadas, mas sobrou muita coisa que seria
lida em voz alta:

| Livro | Palavras | O que atrapalharia a escuta |
|---|---|---|
| Huxley, *The Doors of Perception* (epubBooks) | 16.566 | Sumário e página de copyright/propaganda viram capítulos. O ensaio inteiro está num único XHTML. |
| Rosenberg, *Tides of Darkness* (convertido de PDF, epdf.pub) | 91.021 | 423 cabeçalhos de página: 258 viram parágrafo próprio (203 `Tides of Darkness N` nas páginas pares, 55 `N Aaron Rosenberg` nas ímpares), e 165 ficam colados no fim de um parágrafo (6 com o título, 159 com o autor; contagem corrigida pela auditoria de 2026-11-01). O parágrafo se parte na quebra de página. A letra capitular falta no próprio arquivo (`re we ready?”`, `awn, and fog`, `hadgar`). Títulos de capítulo vêm como `<p>`. Há ISBN, endereço e URL da editora. |

Nenhum desses defeitos é de tradução. Na mesma data, o Mateus pediu que o projeto também
prepare livros **em português**, sem traduzir, só para ouvir melhor. Já os defeitos do
A6 a A10 da auditoria não apareceram nos dois livros: o A7 (nota sem `<sup>`) teve zero
ocorrências.

Quantum atual: 1 (CLI local + pasta de trabalho em arquivos).

## Alternativas consideradas

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. A limpeza fica dentro do prompt de tradução | nenhuma etapa nova | o livro em português fica sem caminho; a limpeza não é determinística nem verificável; gasta assinatura para tirar cabeçalho de página | falha no pedido e no ★ |
| B. Dois projetos, um que prepara e outro que traduz | cada um fica menor | duplica `preparar`, `conferir` e `montar`; vira 2 quanta sem nenhum driver de modularidade com evidência | distribuir por antecipação |
| **C. Uma esteira com etapas, em que o modo diz se traduz** | o livro em português usa 4 das 5 etapas; a limpeza determinística é testável e barata e roda antes de gastar assinatura; a tradução recebe texto já limpo | a pasta de trabalho ganha mais uma camada de arquivos (segmento original e segmento limpo); o `conferir` precisa saber o modo | — |

## Decisão

Esteira única: `preparar → limpar → [traduzir] → conferir → montar`. A tradução só entra
quando o idioma do livro é diferente do idioma de saída.

- O **`limpar`** é Python e determinístico. Ele tira cabeçalho corrente e número de página, junta o parágrafo partido na quebra de página e separa o que vem antes e depois do texto (sumário, copyright, ISBN, propaganda) do que vai para o áudio.
- O que pede julgamento é **marcado** e fica com o Claude Code: a capitular perdida (`re we ready?”` → `Are we ready?”`) e o título de capítulo que veio como parágrafo.
- **Só sai cabeçalho que é do livro.** Frase com número que se repete com 3 ou mais números diferentes só é removida se estiver, como palavras inteiras, no título ou no autor do OPF. A que se repete sem estar lá ("Dia 1", "Dia 2", "Dia 3" num diário) fica no texto e entra em `suspeitas` no `limpeza.json`, para o Claude Code decidir. Rótulo de capítulo (`Chapter N`, `Cap. N`) nunca sai. Essa regra veio do achado H1 da auditoria, em 2026-11-01.
- **Nada é apagado em silêncio.** Toda remoção e toda junção fica registrada na pasta de trabalho, com o ID do segmento de origem, e o `conferir` cobra que origem = mantidos + removidos + juntados.

- **Cabeçalho colado e parágrafo partido** (2026-11-01). O cabeçalho de uma frase já firmada como cabeçalho do livro sai do fim do parágrafo e fica registrado como `aparo`. Depois disso, dois parágrafos seguidos viram um só (`juncao`) quando o primeiro não termina em `.`, `!`, `?`, `…`, `:` ou `;` e a primeira letra do segundo, depois de aspas e travessões, é minúscula. Aspas e apóstrofo no fim não fecham: `of course,”` + `he answered` é uma fala só, e `warriors’` + `reach` é um possessivo. Quando um dos dois é linha curta sem pontuação (até 3 palavras, como `first prologue`, `ONE` ou `acknowledgments`), não junto e marco suspeita: é título que veio como `<p>`, quase sempre seguido de capitular perdida. Correções da auditoria de 2026-11-01:
  - só `paragrafo` se junta com `paragrafo`. O segmentador passou a dar papel próprio a item de lista (`item`: li, dt, dd), célula (`celula`: td, th) e bloco dentro de `<blockquote>` (`citacao`); antes, o `<p>` sem ponto engolia a lista seguinte;
  - travessão que fecha um parágrafo seguido de travessão que abre o próximo não junta, porque é ação interrompida de propósito;
  - cabeçalho colado logo depois de hífen (`sub-429 Aaron Rosenberg`) também sai, e a palavra hifenizada volta sem espaço (`sub-commander`).
- **Capitular perdida** (2026-11-01, corrigido pela auditoria no mesmo dia). O parágrafo que começa em minúscula, depois de aspas e travessões, logo depois de um título ou de uma linha curta (título que veio como `<p>`), vira suspeita com o motivo "capitular perdida". A linha curta em si (`first prologue`) nunca é capitular, e o começo de capítulo sem título não é marcado, porque não teve nenhum caso medido (A3). A letra **não sumiu, foi deslocada**: a conversão do PDF a deixou sozinha no meio do texto (`stirred, D unable`, `present K both`, `G demanded.`). A suspeita traz uma `pista` com a primeira maiúscula sozinha (fora o `I`, que se confunde com o pronome) no parágrafo marcado ou nos dois seguintes: o ID, a posição e a letra. O texto não muda. Quem corrige as duas pontas é o Claude Code. No Tides são 25 começos de capítulo, todos com a letra deslocada. Em 24 a pista acerta a letra; no 25º a letra é um `I`, e a suspeita sai sem pista. Nenhum outro parágrafo em minúscula do livro estava nessa posição. Um segmento entra uma vez só nas suspeitas, com o primeiro motivo que o marcou (A4).

### Medição depois da limpeza (2026-11-01)

| Livro | Removidos | Aparos | Junções | Suspeitas | O que ainda sobra |
|---|---|---|---|---|---|
| *The Doors of Perception* | 0 | 0 | 0 | 0 | sumário e página do epubBooks |
| *Tides of Darkness* | 258 | 165 | 290 | 26 (25 capitulares, 24 com pista; 1 título) | as 25 capitulares estão marcadas, mas ainda não corrigidas, porque isso é com o agente; cerca de 20 pausas no meio da frase onde havia cabeçalho entre os dois parágrafos e o seguinte começa com nome próprio (`…had` + `Proudmoore’s`), que a regra da minúscula não junta (A5 da auditoria); folha de rosto com ISBN e URL |

Limite conhecido (A6 da auditoria): o cabeçalho solto é comparado em `casefold`, que desfaz ligaduras (`ﬁ` → `fi`), mas o colado é procurado no texto cru. Cabeçalho colado com ligadura tipográfica fica no texto. Nenhum dos dois livros medidos tem esse caso.

### Página de direitos autorais (2026-11-01)

A escuta do Competente no ElevenReader leu o aviso "© 2026 Fabio Akita. Todos os direitos reservados. Nenhuma parte deste livro…". O `limpar` agora tira a página de direitos (`dominio/direitos.py`), como primeira etapa:
- sai o segmento com **marca forte**: `©`, `(c) 2020`, "direitos reservados", "all rights reserved", ISBN. Nos quatro livros medidos, a marca forte só apareceu em página de direitos e em boilerplate de editora, nunca no corpo;
- saem também as linhas vizinhas com **marca fraca** (copyright, marca registrada, trademark, editora, publisher, published by, impresso, printed in, catalogação, Library of Congress, edição, edition, `http`, `www.`), seguidas, nos dois sentidos. A corrente atravessa uma linha sem marca quando a seguinte tem ("Visit us on the World Wide Web:" antes da URL), mas nunca um título: o capítulo que começa logo depois fica inteiro. Sozinha, a marca fraca é texto comum ("a segunda edição") e não tira nada;
- cada remoção fica no `limpeza.json`, com o motivo "página de direitos autorais" ou "página de direitos autorais: linha vizinha".

Medido nos quatro livros:

| Livro | Saíram | O quê |
|---|---|---|
| *Competente o Suficiente* | 1 | o segmento com título, subtítulo e aviso de direitos |
| *The Doors of Perception* | 3 | "Copyright © 2020 epubBooks", "All Rights Reserved." e o aviso longo de uso |
| *Tides of Darkness* | 7 | do © até a URL da editora; a dedicatória logo depois ficou |
| *Software Architecture: The Hard Parts* | 7 | o copyright, os créditos da equipe e o histórico de revisões da página de rosto; o parágrafo de atribuição do prefácio ("…title, author, publisher, and ISBN"), que é boilerplate da O'Reilly; e o texto invertido da contracapa |

Correções da code-review (2026-11-01), cada uma com o teste visto falhar antes:
- a marca forte só abre página de direitos nas **pontas do livro**: nos primeiros ou nos últimos 10% dos segmentos, e nunca menos de 20 de cada lado. No meio do livro, "© Oracle" ou um ISBN citado é texto, e antes puxava os vizinhos com link. A posição conta no livro inteiro, não no capítulo;
- a travessia **não leva a dedicatória** ("Para…", "To…", "In memory…"), que pode vir entre o aviso e a linha da edição.

Correções da code-audit (2026-11-01), cada uma com o teste visto falhar antes:
- **A1:** a âncora ficava na ponta, mas a corrente de vizinhas andava pelo livro adentro enquanto houvesse marca fraca. Num teste com o Competente modificado, um ISBN numa referência levou 60 entradas da bibliografia. Agora a corrente só anda dentro das pontas e leva no máximo 5 linhas sem marca forte de cada lado (a página real mais longa, a do Tides, tem 3). Limite que fica: um colofão logo depois de uma lista de links, na ponta, ainda leva até 5 dessas linhas.
- **A2:** a dedicatória ao lado do aviso, com palavra de editora ("Para minha editora, Beltrana…"), saía; a proteção valia só para a linha atravessada. Agora a corrente nunca leva dedicatória.
- Testes para o que estava sem proteção: cada marca forte isolada, a fronteira exata das pontas e a corrente para trás.

Correções da pós-auditoria (2026-11-01), cada uma com o teste visto falhar antes:
- **N3:** o limite de 5 era conferido antes do passo, e a travessia, que leva duas linhas de uma vez, chegava a 6. Agora o limite conta o passo inteiro.
- **N5:** a dedicatória só era reconhecida se começava com "Para", "To", "For" e afins; "This book is dedicated to…", "Dedico este livro…", "In loving memory…" e "Dedicatória:" saíam. A lista de aberturas cresceu. Continua sendo pelo começo da linha: a dedicatória que não começa com uma abertura conhecida ainda pode sair, registrada.
- **N6:** a linha cuja única marca forte é o ISBN sai sozinha, sem abrir corrente. O ISBN aparece também em referência bibliográfica, cercada de outras referências com link, e levava até 10 delas. Os quatro livros continuam tirando os mesmos 18 segmentos.
- Teste da ponta de 10% num livro de 300 segmentos, além do mínimo de 20.

Limite conservador registrado (N4): uma linha de editora que começa como dedicatória ("For more information about our books, visit www…", "Para mais informações, acesse…", "To order additional copies…") para a corrente, e o resto da página de direitos depois dela fica no texto e é lido. Nenhum dos quatro livros tem esse caso.

Ficaram de fora, sem marca: o endereço da editora no Tides ("A Division of Simon & Schuster, Inc. 1230 Avenue of the Americas" e "10020") e o título repetido nas páginas de rosto.

## Consequências

**Ganha:**
- O ★ é atacado onde a medição mostrou o dano: são 423 cabeçalhos lidos em voz alta num livro só.
- O braço "só preparar" sai antes da tradução.
- Livro em português vira caso de uso, não exceção.

**Perde:**
- Mais um formato na pasta de trabalho.
- Heurística de cabeçalho corrente pode tirar uma linha legítima, por exemplo um parágrafo que repete o título do livro com número três vezes. Por isso o registro de remoções é obrigatório e revisável.
- Cabeçalho com o título do *capítulo* (comum em não ficção) não está no título do livro: ele não sai sozinho e vira suspeita, o que custa uma decisão do agente por frase.
- O `conferir` deixa de poder procurar "parágrafo em inglês" de forma cega, porque depende do modo.

**Aceito conscientemente:** a capitular deslocada é corrigida pelo agente a partir da pista, não pelo Python. A pista é a primeira maiúscula sozinha por perto, e num livro com "A" no começo de frase ela pode apontar a letra errada. Revisitar, e talvez tornar a correção determinística, se o agente acertar quase todas nos livros de `livros/` (no Tides, a pista acerta 24 de 24).

**Revisto pelo ADR-0007 (2026-11-02):** o agente acertou as 25 no Tides, e a correção passou a ser do `limpar`, quando o próprio livro prova a palavra reconstruída. A suspeita sem prova continua como aqui.

Limites registrados pela auditoria de 2026-11-01, sem caso nos livros medidos:
- A2: depois de uma linha curta que não é título (verso, entrada de índice, cabeçalho que ficou como suspeita), o motivo diz "capitular" quando o certo seria juntar ou tirar.
- A5: a capitular depois de uma epígrafe em `<blockquote>`, de um título em `<p>` com pontuação (`Chapter One: The Dark Portal`) ou de um `<hr>` não é marcada.
- A6: se a primeira palavra vinha em versalete e virou maiúscula (`AWN, and fog`), a regra da minúscula não vê.
- Capítulo que abre em minúscula de propósito depois do título (`— disse ele` em português, poesia moderna) é marcado como capitular: o agente descarta.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Nada some na limpeza | `conferir`: origem = mantidos + removidos + juntados, por ID | antes do `montar` | algum ID de origem não aparece em nenhum dos três |
| Padrões medidos | testes com EPUB sintético que reproduz cada padrão (cabeçalho `Título N`, parágrafo partido, capitular ausente, sumário) | portão | o padrão volta a passar para o texto |
| Escuta ★ (manual) | rodar a esteira nos livros de `livros/` e contar o que sobrou | a cada mudança na limpeza; responsável: Mateus | a contagem sobe |

Regra derivada no `AGENTS.md`: a limpeza registra toda remoção; nada sai do texto sem o ID de origem.

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-01 · Aprovado em: 2026-11-01
