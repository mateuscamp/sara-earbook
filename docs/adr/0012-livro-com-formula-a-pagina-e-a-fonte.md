# 0012 — Livro com fórmula: a página é a fonte, e o tradutor diz a fórmula lendo a página

**Status:** Aceito
**Data:** 2026-11-07
**Driver ★:** escuta: *Philosophy of Physics: Quantum Theory* (Tim Maudlin, Princeton, 2019) em
`livros/prontos/`, primeiro livro com fórmulas

**Bottom line:** a fórmula vem da página, não do texto do PDF. O pacote ganha duas regras no
`importar-pdf` (ADR-0004, "Cabeçalho fora da faixa e versalete de fonte própria"); o resto do que
este PDF pede é caminho, sem código: um script fora do repositório filtra as páginas antes do
`importar-pdf`, e `decisoes.md` manda o tradutor ler a página renderizada nos segmentos com fórmula.
Um revisor que não traduziu confere cada fórmula contra a página. O `tradutor.md` não muda.
Inverte se um segundo livro com fórmula pedir o mesmo filtro: aí o filtro das equações e o marcador
de nota viram decisão de código.

## Contexto

PDF de editora, 250 páginas, 396 x 612 pt, ~84 mil palavras numa coluna, com camada de texto. Medido
no HEAD `9af7ac9`, o `importar-pdf` e o `preparar` davam 1.327 segmentos e 86 suspeitos. O que
atrapalhava:

| Defeito | Medida | Onde se resolve |
|---|---|---|
| Cabeçalho corrente e número de página fora da faixa de 8% | 222 cabeçalhos e 230 números no meio das frases | código (ADR-0004) |
| Título em versalete de fonte própria (`Archer-Medium-SC700`) | 34 títulos que viravam nota | código (ADR-0004) |
| Fórmula: o texto do PDF perde ψ em parte das vezes, o √ de 1/√2 ("2 1"), o chapéu do operador; troca a seta do ket por "-" e "."; parte as matrizes | 157 segmentos com fórmula, em ~50 páginas; 82 equações de exibição partidas em até 25 pedaços | página renderizada + script |
| Fragmento de fórmula em letra pequena (índice, expoente, denominador) | 286 linhas, que viravam nota no fim do capítulo | script |
| Texto de dentro das figuras (fonte MyriadPro) e rótulo "Figure N" | 245 + 29 linhas; "(a) (b)" e "N", "S" viravam título | script |
| Marcador de nota colado ao texto ("obscure.1 Besides") | 69 | script |
| "CHAPTER 1" em linha própria, acima do título | ficava no fim do capítulo anterior | script |
| Capa, série, folha de rosto, direitos, sumário, References, índice | 82 + 130 + 235 linhas | script |

## Drivers

| ★ | Característica | Origem | Como se mede |
|---|---|---|---|
| ★ | Escuta | "o livro pronto" | nenhum símbolo de fórmula chega à voz; o inventário por script no livro montado |
| | Fidelidade da fórmula | física: coeficiente, sinal, estado e índice certos | revisor que não traduziu, contra a página |
| | Livros de medição intactos | ADR-0007 | os seis saem idênticos |
| | Custo | medidor semanal em 29% | ~760 mil tokens previstos |

## Alternativas consideradas

### 1. De onde vem a fórmula

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. O texto do PDF, com um mapa dos glifos | sem imagem | o que se perdeu (√, ψ, chapéu, a ordem das frações) não volta por mapa | o texto não tem a fórmula |
| B. Um passe antes da tradução, que transcreve cada fórmula da página para o texto-fonte | a fonte fica certa | reescreve `limpos/`, que o agente nunca grava; trabalho dobrado | fronteira do ADR-0006 |
| **C. A página renderizada, lida pelo tradutor, e um revisor contra a página** | a fórmula certa sem tocar no texto-fonte; o tradutor já fala física | o revisor custa uma leitura a mais das ~90 páginas | — |

### 2. Código ou caminho para o resto

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Tudo no `importar-pdf` | serve ao próximo livro | o texto de figura e a equação partida não têm critério geral medido: a fonte da figura é deste livro, e nos outros PDFs a figura é imagem | TDD e revisão para regras de um livro |
| **B. Duas regras gerais no código; o resto num script fora de `src/`** | as regras medidas em seis livros ficam; o resto não muda nenhum livro, por construção | o script é por livro, sem teste | — |

## Decisão

### O caminho

`fonte.py` (pasta de notas, `maudlin-mapa/`) chama o `importar-pdf` por dentro (`ler_paginas`,
`tirar_texto_escondido`, `tirar_cabecalhos_e_rodapes`, `montar_blocos`, `gravar_epub`), com um
filtro por página antes. Cada linha tirada fica em `retirado.json`, com a página e o motivo.

- **Fora, por página:** capa, falsa folha de rosto, série, folha de rosto, direitos, sumário,
  References (p. 227 a 230 do livro, 988 palavras), índice remissivo (p. 231 a 233, 886 palavras).
- **Fora, por linha:** o texto em fonte de figura (MyriadPro, CambriaMath), sem letra do corpo;
  "Figure N" sozinho e as duas legendas com crédito; o fragmento de fórmula abaixo de 7 pt, e o
  menor que o corpo com fonte de fórmula e sem palavra de 4 letras.
- **A equação de exibição vira uma linha:** os pedaços que não são prosa (fora da margem e do
  recuo do parágrafo, sem duas palavras de 4 letras) e que não estão na altura de uma linha de prosa
  se juntam por proximidade (até 0,03 da altura). Pedaço sozinho e sem palavra vai para a equação
  mais perto. Assim cada equação é um segmento.
- **O marcador de nota sai** quando é algarismo abaixo de 7 pt, colado à palavra, seguido de espaço,
  e a página tem uma nota de rodapé com esse número. O expoente da fórmula fica.
- **Glifos devolvidos:** a seta do ket (MMArrow "-" e "." → ↑ ↓), as gregas e o ⇒ do Symbol, o ∂
  da MMEtc. O resto da fórmula fica como veio: quem a diz é a página.
- **O título do capítulo leva o número:** "Chapter 1: Eight Experiments".
- **A abertura** é "Philosophy of Physics: Quantum Theory" e "Tim Maudlin".

### A fórmula

- A sessão grava a página de cada segmento com fórmula em
  `livros/trabalho/philosophy-of-physics-quantum-paginas/pNNN.png`.
- `decisoes.md` traz as regras de como dizer a fórmula e a tabela segmento → página. Para esses IDs,
  o tradutor lê a página e diz a fórmula dela, não a do texto.
- **As regras** (aprovadas pelo Mateus, com os exemplos abaixo):
  - o ket vira palavra: |z↑⟩ → "z para cima"; |x↓⟩ de B → "x para baixo em B"; os rótulos espaciais
    em português (middle "no meio", upward "subindo");
  - o número e o coeficiente ficam, por extenso: "um sobre raiz de dois", "h cortado", "psi",
    "módulo de alfa ao quadrado"; ⇒ é "evolui para", como o livro o define;
  - a equação curta que o texto em volta explica se lê;
  - a derivação longa e a matriz viram a frase do que afirmam, com os números.
- **A prova:**
  1. por script, nos `traduzidos/`: nenhum símbolo de fórmula (| ⟩ > = + ↑ ↓, letras gregas, ∂, ℏ,
     "2 1") e nenhum marcador de nota;
  2. um revisor por capítulo com fórmula, que não traduziu, lê a página e o português de cada
     segmento da tabela e lista a divergência; o tradutor do capítulo corrige.

### Exemplos aprovados

1. Ket na prosa (livro p. 63). Antes: "represented by |x ↑ >|middle>, which is the same as ( 2 1 |z
   ↑ > + 2 1 |z ↓ >)|middle>". Depois: "representado pelo estado x para cima no meio, que é o mesmo
   que um sobre raiz de dois de z para cima, mais um sobre raiz de dois de z para baixo, tudo no
   meio."
2. Equação de exibição (p. 63). Depois: "Um sobre raiz de dois de z para cima no meio, mais um sobre
   raiz de dois de z para baixo no meio, evolui para um sobre raiz de dois de z para cima subindo,
   mais um sobre raiz de dois de z para baixo descendo."
3. Equação-guia (p. 142). Antes: "dq = & Im d ψ ( , ) x t . dt m d ψ ( , ) x t n". Depois: "A
   derivada de q k em relação ao tempo é igual a h cortado sobre m k, vezes a parte imaginária do
   gradiente k de psi de x e t, dividido por psi de x e t."
4. Espinor (p. 60): [1; 0] é "o espinor um, zero"; "(1/√2)(α+β)(1/√2)[1;1] = ½(α+β)[1;1]" é "…dá
   metade de alfa mais beta vezes o espinor um, um".

### Decisões do Mateus (2026-11-07: "Aprovar as cinco")

1. As regras de cabeçalho e de versalete no código; o resto pelo script.
2. As fórmulas pelas regras e exemplos acima, sem escuta de teste; o roteiro tem 3 paradas de
   fórmula.
3. References, índice e sumário fora do áudio, registrados.
4. Termos: "beables" e "beables locais" (neologismo de Bell, sem forma em português), "onda piloto",
   "muitos mundos", "ontologia de flashes", "emaranhamento", "autoestado", "equação-guia";
   Mach-Zehnder no lugar do "Mach-Zehender" do original; títulos em português. Alinhados com o
   *What Is Real?*, traduzido em paralelo.
5. A tradução do livro inteiro.

## Fila

Defeitos de código achados neste livro, resolvidos aqui pelo script e não no pacote:

- **o marcador de nota do PDF fica colado ao texto** ("obscure.1"); o `preparar` só o tira do EPUB
  com link de nota;
- **o número do capítulo em linha própria** ("CHAPTER 1"), acima do título, fica no fim do capítulo
  anterior;
- **a equação de exibição sai partida em pedaços**, um parágrafo por pedaço.

## Consequências

**Ganha:** o primeiro livro com fórmula, com a fórmula certa e sem símbolo na voz; duas regras do
`importar-pdf` que servem ao próximo livro de margem larga ou de versalete de fonte própria.

**Perde:**
- O script é por livro, sem teste, e mora fora do git.
- A fórmula depende do tradutor ler a imagem; o revisor é o que a prova.
- O texto em inglês da fórmula, em `limpos/` e no `montar --original`, continua estragado: a fonte
  em inglês da fórmula é a página.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Nada de fórmula na voz | script nos `traduzidos/` | antes do `montar`; responsável: a sessão | um símbolo de fórmula ou um marcador de nota |
| A fórmula certa | revisor que não traduziu, contra a página | depois da tradução; responsável: a sessão | divergência não corrigida |
| Integridade e nome | `conferir` | antes do `montar` (recusa) | ID sem tradução, nome fora do glossário |
| O que a máquina acha | inventário por script no livro montado | antes da tradução e no livro pronto | achado novo contra "O que atrapalha o ouvido" |
| Livro válido | epubcheck | depois do `montar` | qualquer erro |
| Escuta ★ (manual) | as paradas do roteiro | livro pronto; responsável: Mateus | tropeço audível |

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-07 · Aprovado em: 2026-11-07 (pelo Mateus, por
meio da sessão principal: "Aprovar as cinco").
