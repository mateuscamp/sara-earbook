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

### Medição depois da limpeza (2026-11-01)

| Livro | Removidos | Aparos | Junções | Suspeitas | O que ainda sobra |
|---|---|---|---|---|---|
| *The Doors of Perception* | 0 | 0 | 0 | 0 | sumário e página do epubBooks |
| *Tides of Darkness* | 258 | 165 | 290 | 9 | cerca de 20 capitulares perdidas depois de título `<h1>` (`re we ready?”`), ainda sem marca; cerca de 20 pausas no meio da frase onde havia cabeçalho entre os dois parágrafos e o seguinte começa com nome próprio (`…had` + `Proudmoore’s`), que a regra da minúscula não junta (A5 da auditoria); folha de rosto com ISBN e URL |

Limite conhecido (A6 da auditoria): o cabeçalho solto é comparado em `casefold`, que desfaz ligaduras (`ﬁ` → `fi`), mas o colado é procurado no texto cru. Cabeçalho colado com ligadura tipográfica fica no texto. Nenhum dos dois livros medidos tem esse caso.

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

**Aceito conscientemente:** a letra capitular perdida não tem conserto determinístico. Se o
agente errar a letra, o erro vai para o áudio. Revisitar se a taxa de acerto do agente ficar
abaixo de quase todas, medida nos livros de `livros/`.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Nada some na limpeza | `conferir`: origem = mantidos + removidos + juntados, por ID | antes do `montar` | algum ID de origem não aparece em nenhum dos três |
| Padrões medidos | testes com EPUB sintético que reproduz cada padrão (cabeçalho `Título N`, parágrafo partido, capitular ausente, sumário) | portão | o padrão volta a passar para o texto |
| Escuta ★ (manual) | rodar a esteira nos livros de `livros/` e contar o que sobrou | a cada mudança na limpeza; responsável: Mateus | a contagem sobe |

Regra derivada no `AGENTS.md`: a limpeza registra toda remoção; nada sai do texto sem o ID de origem.

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-01 · Aprovado em: 2026-11-01
