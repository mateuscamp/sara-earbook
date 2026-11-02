---
name: traduzir-livro
description: Roteiro da sessão que traduz um livro inteiro do earbook do inglês para o pt-BR - glossário, amostra e escuta, decisões do livro, estimativa de custo, divisão em tradutores paralelos, rodada de correção, montagem em livros/prontos, epubcheck e roteiro de escuta (ADR-0006 e ADR-0007). Use quando o Mateus pedir para traduzir um livro, continuar uma tradução, distribuir os lotes, estimar o custo de uma tradução ou montar o roteiro de escuta.
---

# Traduzir um livro

O passo a passo da sessão que leva um livro em inglês de `livros/trabalho/<nome>.earbook` até
`livros/prontos/<nome>.pronto.epub`. Quem traduz é o subagente `tradutor`
(`.claude/agents/tradutor.md`). O Python exporta, confere e monta, e nunca chama o LLM
(ADR-0001).

Antes de começar: o livro já passou pelo `preparar` (e pelo `importar-pdf`, se veio de PDF), e o
Mateus ouviu o `montar --original` (passo 3 do "Livro novo" no `AGENTS.md`). A capitular
deslocada já foi corrigida no `preparar` (ADR-0007). Se o resumo listar suspeita de capitular,
ela é a que o livro não provou: decida com o Mateus antes de traduzir.

## 1. Exportar

```bash
uv run earbook traduzir livros/trabalho/<nome>.earbook
```

A saída dá, por capítulo, os segmentos, os lotes pendentes e as **palavras pendentes**. Ela dá
também os caminhos do glossário, dos candidatos a nome (`nomes.json`) e de `decisoes.md`, que o
comando cria com as seções em branco. Rodar de novo não refaz nada.

## 2. Glossário

- Monte `glossario.json` a partir de `nomes.json`, antes de qualquer tradução.
- Use a política de nomes do livro. No Tides, a localização oficial pt-BR da Blizzard, pesquisada
  no Wowhead em português, com a fonte no campo `nota`.
- A fonte bloqueia depois de umas 40 consultas: priorize os nomes mais frequentes.
- Leve ao Mateus as divergências entre fontes e os nomes sem fonte.
- O glossário compara palavra inteira com maiúscula: plural e variação de caixa precisam de
  entrada própria (`warlock` e `warlocks`, `warchief` e `Warchief`).

## 3. Amostra e escuta

- **Amostra:** de 5 a 7 lotes num tradutor só: o rosto, os prólogos, o começo do capítulo 1 e
  o fim. Se o livro tem fala em dialeto, um lote com ela; no Tides, a amostra não tinha, e cada
  tradutor decidiu o dialeto por conta própria.
- **Conferir e montar:** `conferir --amostra`, `montar --amostra` e um roteiro de escuta com as
  paradas (ver o passo 9).
- **Depois da escuta:** escreva `decisoes.md` com o que o Mateus aprovou e com o que o tradutor da
  amostra decidiu e ninguém reprovou. Ali entram a política de nome fora do glossário, o tom, o
  dialeto, os títulos e a caixa, o tratamento ("Sir", "Lord", "you" plural) e as escolhas da
  amostra.
- **Glossário:** os termos que a amostra declarou em `termos/` entram nele antes do resto.

O brief do resto não copia nada disso: o tradutor lê `decisoes.md`.

## 4. Custo, antes do sim do Mateus

Pela régua do livro inteiro (ADR-0006, "O Tides inteiro"), e **não pela amostra**, que
concentra as decisões e erra para cima (10,1 tokens por palavra no Tides, contra 6,4 no livro):

| Medida | Régua | Conta |
|---|---|---|
| Tokens de saída | 6,4 por palavra (de 4,1 a 7,8 por capítulo) | palavras pendentes × 6,4 |
| Tempo por tradutor | ~1.160 palavras por minuto | o maior capítulo ÷ 1.160 é o tempo de relógio |
| Medidor semanal | o Tides inteiro (89 mil palavras) moveu no máximo 2 pontos | ~1 ponto a cada 45 mil palavras |

Mostre ao Mateus os lotes, as palavras e a estimativa, e espere o sim.

## 5. Distribuir

- Um `tradutor` por capítulo, todos em paralelo, numa mensagem só.
- O capítulo menor que um lote (~2 mil palavras) vai junto com outro no mesmo tradutor.
- O "capítulo" é um arquivo do spine, e um arquivo pode juntar vários capítulos do livro: o maior
  define o tempo.

O brief é curto e igual para todos, mudando só o capítulo:

```
Traduza os lotes <c005-l001 … c005-l011> da pasta livros/trabalho/<nome>.earbook,
seguindo .claude/agents/tradutor.md. Leia glossario.json e decisoes.md antes do primeiro
lote. Grave a resposta e os termos de cada lote assim que terminá-lo. No fim, rode
uv run earbook conferir livros/trabalho/<nome>.earbook --amostra --capitulo c005.
```

Não acrescente pista de capitular nem as escolhas da amostra ao brief: as escolhas moram em
`decisoes.md`, e a capitular já foi corrigida no `preparar`.

## 6. Rodada de correção

Quando todos terminarem:

1. `uv run earbook conferir livros/trabalho/<nome>.earbook`.
2. Para cada "'X' fora do glossário, declarado como …", escolha uma forma (a oficial, se houver;
   senão, a mais usada) e acrescente ao glossário. Leia os relatórios: termo criado que um
   tradutor não declarou também entra.
3. Rode o `conferir` de novo: ele acusa, em todos os capítulos, os segmentos que usaram outra
   forma.
4. Mande uma mensagem (`SendMessage`) ao tradutor de cada capítulo com problema, com os IDs. No
   Tides foram 9 segmentos, corrigidos em 16 e 26 segundos.
5. Repita até o `conferir` dar "nada faltando".

Confira o arquivo gravado, não o relatório: no Tides, um relatório mostrou um texto que não era o
do arquivo.

## 7. Montar, direto em `livros/prontos/`

```bash
uv run earbook montar livros/trabalho/<nome>.earbook --epub livros/prontos/<nome>.pronto.epub
```

Sem o `--epub`, o livro vai para `livros/trabalho/`.

## 8. epubcheck

```bash
epubcheck livros/prontos/<nome>.pronto.epub
```

Compare com o epubcheck do EPUB original: o erro que já vinha nele (no Tides, 9 RSC-005) não é da
montagem.

## 9. Roteiro de escuta

`livros/trabalho/roteiro-de-escuta-<nome>.md`, com 8 a 10 paradas, só na parte nova. Cada parada
tem o ID, o minuto, o que ouvir e a pergunta para o Mateus. Os minutos vêm do comando:

```bash
uv run earbook minuto livros/trabalho/<nome>.earbook c005-s0288 c006-s0022
```

Ele conta a 160 palavras por minuto, pelo texto que se ouve (a tradução, quando existe). Escolha
as paradas nos relatórios dos tradutores: dialeto, termo criado, erro do original, título,
hesitação.

## 10. Registro

- Acrescente ao ADR-0006 a medição do livro, como em "O Tides inteiro": lotes, palavras, tempo e
  tokens de saída por capítulo, o glossário antes e depois, e o que os tradutores devolveram como
  dúvida.
- Os tokens de cada tradutor estão no aviso de fim do subagente.
- Commit só quando o Mateus pedir.
