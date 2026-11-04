# 0011 — Livro escaneado entra por OCR fora do pacote, com a fonte refeita por script

**Status:** Aceito
**Data:** 2026-11-04
**Driver ★:** escuta: os dois volumes de *World of Warcraft: Chronicle* em `livros/prontos/`

**Bottom line:** nenhuma linha muda em `src/`. O tesseract roda por fora, um script fora do repositório
transforma o texto em blocos e grava um EPUB limpo, e o `preparar` segue dali. Revisa o "sem OCR" do
ADR-0004 só neste ponto: o pacote continua sem OCR e o `importar-pdf` continua recusando PDF sem texto.
Inverte se um terceiro livro escaneado pedir o mesmo caminho: aí vira decisão de código, com TDD.

## Contexto

| Volume | Fonte | O que chegou |
|---|---|---|
| 1 | PDF de 174 páginas, escaneado, sem camada de texto, 163 ppi | nada: `importar-pdf` recusaria |
| 2 | EPUB do Internet Archive, feito de OCR | 203 arquivos, um `<p>` por página; sem capitular, sem sumário e sem metadado; títulos, legendas e rodapés dentro do bloco |

Quantum: 1. Continua 1.

## Alternativas consideradas (volume 1)

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. PDF-sanduíche do tesseract no `importar-pdf` | usa o comando que existe | 6 capítulos no lugar de 8, com vários capítulos num arquivo; lixo de ilustração virou título e nota; 41 capitulares perdidas | medido e descartado |
| B. OCR no pacote | serve a outro livro | `subprocess` é proibido no pacote; TDD, revisão e auditoria para um livro | sem driver |
| **C. Texto do tesseract, um script por volume, EPUB gravado e `preparar`** | o mesmo fim de caminho nos dois volumes; título, capítulo e parágrafo sob controle; cada remoção registrada com a página | o script é por livro e não tem teste | — |

## Decisão

- **OCR por fora.** `pdftoppm -r 300 -gray` e `tesseract --psm 4 -l eng`, um processo por página. Uma
  segunda leitura, a 400 dpi com `--psm 6`, serve só para achar erro pela discordância.
- **O script não é o pacote.** Mora na pasta de notas, em `cronicas-mapa/`. Ele importa
  `gravar_epub` do `earbook`, e o `preparar` é o teste de contrato do que foi gravado.
- **O que sai fica registrado com a página:** rodapé, número de página, legenda, mapa, arte, sumário,
  créditos, índice.
- **Quadro lateral fica.** Quando ele corta uma frase, vai para depois dela.
- **Erro de OCR se corrige por lista,** com palavra inteira, a partir das palavras fora do vocabulário
  (cracklib e os livros em inglês já limpos) e da discordância entre as duas leituras.
- **Capitular perdida se devolve por tabela.** No volume 2 a capitular ornada levou uma ou duas
  palavras em 12 aberturas, reconstruídas pelo sentido e listadas abaixo.
- **Parágrafo do volume 2 por regra:** quebra em fim de frase, perto de 60 a 90 palavras, de preferência
  antes de frase que abre assunto. Parágrafo falso custa uma pausa.
- **Nomes pelas tabelas do jogo.** `wago.tools/db2/<tabela>/csv?locale=` dá inglês e português casados
  pelo ID: 238 mil pares, sem o limite do Wowhead.
- **Sem ilustrações** no EPUB pronto (ADR-0004: só para ouvir).
- **O sumário fecha por fora.** O `montar` só traduz o item que aponta para um ID, e o EPUB gravado por
  `gravar_epub` aponta para o arquivo. `fecha_epub.py` põe em português o sumário e o `<title>`; `ebook-meta`
  dá título, autores e idioma.

### Decisões do Mateus (2026-11-04: "Aprovar e soltar")

1. Fonte por script, fora de `src/`, registrada aqui e no "Livro novo".
2. Parágrafo do volume 2 por regra.
3. Sem ilustrações no EPUB pronto.
4. Nomes oficiais do jogo: Nascente da Eternidade, Caos, Guardião para Keeper e para Guardian, Eluna,
   vraikal, terrano, Asa da Morte, Karrath.
5. Lobo do Gelo, Brado Guerreiro e Mão Despedaçada, embora a *Ascensão da Horda* os tenha em inglês.
6. O Tides vence o oficial em dois: Antonidas sem acento e altos elfos.
7. Sem fonte: Verdor Eterno, Monte de Esporos, Goriano, Forja das Vontades, Andarilho Vermelho, Lâmina
   do Relâmpago, Guardiania, tirisfaleno.
8. Datas como "16 mil anos antes do Portal Negro."
9. Título "World of Warcraft: Crônica, Volume N", como a edição brasileira do volume 1 (Leya, 2016).
   Não tivemos acesso ao texto dessa edição, e os termos vêm do jogo.

### Medição antes de traduzir

| Medida | Volume 1 | Volume 2 |
|---|---|---|
| Palavras, parágrafos | 53.049, 966 | 74.039, 1.127 |
| Palavras por parágrafo: mediana, maior | 54, 150 | 69, 114 |
| OCR | confiança média 90,8%; 188 discordâncias entre as duas leituras, em 56.532 palavras | não medido: OCR da Archive |
| Corrigido por lista | 140 trocas, 110 formas | 51 trocas, 47 formas; ~90 aberturas de seção |
| Rodapé e número de página fora | 186 | 270 |
| Legenda fora | 33 | 34 |
| Página sem texto corrido fora | 23 | 18 |
| Quadro lateral movido | 1 | 6 |

Depois da tradução: *Crônica, Volume 1*, 53,9 mil palavras; *Volume 2*, 74,8 mil. `conferir` e epubcheck
limpos nos dois. Custo e rodada de correção no ADR-0006.

A regra de parágrafo, medida no volume 1, onde os parágrafos do autor são conhecidos: mediana 68 contra
56, percentil 90 de 90 contra 87, maior 109 contra 150. Ela reproduz o ritmo, não o lugar: 34% das
quebras dela são quebras do autor.

### Conjecturas do volume 2

A capitular ilegível levou a palavra. Páginas do EPUB de origem: p. 16 "From the skies", p. 31 "After
defeating", p. 53 "As Shattrath City", p. 68 "Fear and desperation", p. 71 "While Gul'dan was", p. 93
"Auchindoun's destruction", p. 94 "As the orcs", p. 123 "As the war", p. 134 e p. 152 "Orgrim Doomhammer",
p. 162 "Lothar and his allies", p. 187 "Blade's Edge was". Entre as p. 86 e 87, o script completou
"Yet he would not accept this “gift”" sem ver que o resto da frase vinha no segmento seguinte. O tradutor
achou o fragmento, "he would not allow his clan to partake of Gul'dan", e refez a frase em `c005-s0218`.

## Fila

- **Quadro lateral no meio do parágrafo:** ele fica, mas às vezes a frase seguinte depende do que veio antes
  (`c006-s0195` e `c007-s0161` no volume 1, `c003-s0067` e `c003-s0088` no volume 2).
- **Título partido no volume 1:** `c008-s0250` e `s0251`, erro do script; e "Capítulo 1." repetido em
  `c003-s0002` no volume 2. Consertar na fonte mudaria os IDs.
- **Conflito de nomes com a *Ascensão da Horda*:** ela ficou em inglês com Frostwolf (63), Warsong (15) e
  Shattered Hand (7); as Crônicas usam o oficial. O ajuste é outra decisão do Mateus.

## Consequências

**Ganha:** os dois volumes entram sem tocar em `src/`, e os livros de medição não mudam, por construção.

**Perde:**
- A receita é por livro, sem teste, e os scripts moram fora do git. Se a pasta de notas sumir, sobra a
  descrição daqui.
- No volume 2 os parágrafos não são os do autor, e as 12 conjecturas não têm prova na fonte.
- O erro de OCR que forma palavra real passa pela lista; quem o pega é o tradutor, pelo sentido.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Nada entra no pacote | `make check` e `test_arquitetura.py`, sem mudança | portão | `subprocess` ou OCR em `src/` |
| Integridade e nome | `conferir`, sem mudança | antes do `montar` (recusa) | ID sem tradução, nome fora do glossário |
| Escuta ★: o que a máquina acha | `inventario.py` | a cada volume; responsável: a sessão | achado novo contra "O que atrapalha o ouvido" |
| Livro válido | epubcheck | depois do `montar`; responsável: a sessão | qualquer erro |
| Escuta ★ (manual) | as paradas do roteiro, na leitura do Mateus | livro pronto; responsável: Mateus | tropeço audível |

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-04 · Aprovado em: 2026-11-04 (pelo Mateus, por meio
da sessão principal: "Aprovar e soltar").
