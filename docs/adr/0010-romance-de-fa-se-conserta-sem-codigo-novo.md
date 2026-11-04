# 0010 — Romance de fã se conserta com o Calibre e com o original como mapa, sem código novo

**Status:** Aceito
**Data:** 2026-11-04
**Driver ★:** escuta: o produto final em `livros/prontos/` (pedido do Mateus)

**Bottom line:** nenhuma linha muda em `src/`. O Calibre, antes do `preparar`, resolve metadado,
títulos, capítulos e frase partida. O `adaptar` serve de transporte: um script, fora do repositório,
grava `adaptados/`, e o `conferir` e uma prova palavra a palavra cobram o resultado. Inverte se um
terceiro livro pedir o mesmo mapa ou a mesma regra de parágrafo: aí vira comando, com TDD, e as
travas medidas abaixo são o ponto de partida.

## Contexto

O Mateus pediu: "usar o Sara Earbook para melhorar esses dois produtos e deixar um produto final
melhor, lá em pronto". São dois romances de Warcraft já em português, traduções de fã. Só o que
precisa de código entraria por TDD.

| Livro | Fonte | O que atrapalhava, medido no HEAD `366ce78` |
|---|---|---|
| *Ascensão da Horda* (Christie Golden), 71.716 palavras | EPUB feito de PDF por toepub.com | `dc:language` `en` e autor "David Freitas"; `toc.ncx` com 1 entrada; os títulos são `<p><b>`; cada `<p>` é uma linha de página: 4.889 `<p>`, 2.579 junções e 134 frases partidas com a continuação em maiúscula; 2 frases partidas entre arquivos do spine; erros de espaço ("eredar!Talvez"); a seção "Notas" lê uma URL |
| *O Último Guardião* (Jeff Grubb), 71.528 palavras | PDF de 274 páginas, gerado pelo Calibre a partir de texto | 44 segmentos com mais de 400 palavras e o maior com 4.989; autor Charles L. Grant; "8. Lições", "10. A Emissária", "12. Vida em tempos de guerra", "Prólogo" e "Epílogo" na letra do corpo; "Hadggar" 1.106 vezes |

Quantum: 1 (CLI local + pasta de trabalho em arquivos). Continua 1.

## Drivers

| ★ | Característica | Origem | Como se mede |
|---|---|---|---|
| ★ | Escuta | "um produto final melhor" | no livro montado, 0 frase aberta por defeito, nenhum parágrafo acima de 400 palavras, capítulos certos no sumário; o inventário contra "O que atrapalha o ouvido" |
| | Fidelidade | fonte de terceiros: nenhuma palavra muda sem declaração | prova palavra a palavra da fonte ao EPUB: 0 trecho não declarado |
| | Livros prontos intactos | Tides traduzido e Dalgalarrondo adaptado não se preparam de novo (ADR-0007) | `src/` sem mudança, ou trava que os deixe de fora |
| | Custo | medidor semanal em 91% | sem subagente; 0 tokens de adaptação por palavra |

## Alternativas consideradas

### 1. Parágrafos do *Último Guardião*

O português segue o inglês frase a frase: 5.918 frases nos dois lados, 5.801 dos 5.879 pares são
1:1. Da p. 34 em diante, a linha que não fecha frase nunca termina antes de ~285 pt, e a primeira
linha de parágrafo para em 393 pt, contra 421 das outras, porque o recuo se perdeu. Até a p. 33
não há esse sinal. Há uns 2 vãos por página, mas 56% deles não são parágrafo no inglês.

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Regra da linha no `importar-pdf`, com trava de margem única (99,99% no UG; 63% ou menos nos outros) | vale para outro PDF sem o original | só cobre da p. 34 em diante; precisão 95%, cobertura 92% contra o mapa; TDD, revisão e auditoria sem melhorar este livro | um livro só, e o mapa acerta mais |
| B. Subagente `adaptador` que só quebra parágrafo | sem script | ~19 mil palavras reescritas pelo agente, com risco de mudar palavra; custo em tokens | o que o script faz de graça não precisa de julgamento |
| **C. Alinhar as frases e cortar onde o inglês fecha parágrafo** | o livro inteiro por uma regra só; 0 tokens; o corte não muda palavra | 20 parágrafos que o português tem e o inglês não (1,4%) viram frase seguida; só vale com o original à mão | — |

Medida do mapa: dos 2.685 fins de frase no meio da linha, onde o PDF prova que não há parágrafo, ele
erra 2.

### 2. Títulos, capítulos e metadado

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Título pela sequência numerada no `importar-pdf` e título em `<p><b>` no `preparar` | regra durável | duas regras para 5 títulos e um livro; a do `preparar` roda em todo EPUB | muito código para pouco caso |
| **B. Calibre: `--search-replace`, `--chapter`, `--page-breaks-before`, `--level1-toc`, `ebook-meta`** | sumário, capítulos, autor, capa e idioma sem código | receita por livro; o Calibre é dependência do caminho, não do pacote | — |

### 3. Frase partida com maiúscula

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Regra no `limpar`, com trava de `<p>` como linha: junções em 1/3 dos parágrafos ou mais (Ascensão 53%; Tides 13%, Dalgalarrondo 5%, Hard Parts 0,8%, os outros 0) | 122 junções; serve a outro EPUB assim | TDD, revisão e auditoria; os 44 casos do Tides continuam de fora pela trava | o Calibre faz mais sem código |
| **B. Heurística do Calibre, só o unwrap (`--html-unwrap-factor 0.4`)** | tira 140 quebras, 134 de frase aberta e 6 depois de `;` ou `:`, sem quebra nova; os livros prontos nem passam por ela | 3 hífens colados, consertados no script; não vale para o Tides | — |

## Decisão

Sem código em `src/`. Calibre e script são caminho, não fronteira: `subprocess` continua proibido
no pacote, e nada aqui entra em `dominio/`, `adaptadores/` ou `comandos/`.

- **Antes do `preparar`, o Calibre.** `ebook-convert` com um arquivo de `--search-replace`, que
  promove título a `<h1>`; `ebook-meta` para idioma, autor, capa e crédito. Em Ascensão, o
  `search-replace` também junta a linha justificada que fecha frase (94 parágrafos falsos: o
  espaço duplo prova que não é a última linha), e os 4 XHTML viram um arquivo só antes da conversão.
- **Depois do `preparar`, o `adaptar` como transporte.** O `earbook adaptar` exporta os lotes; o
  script grava `adaptados/` (`igual`, `texto` cortado, `descarte`), `glossario.json` e `decisoes.md`
  é escrito pela sessão. Nenhum adaptador lê o livro. O `conferir` no modo adaptação cobra cada ID,
  cada número, cada termo raro e o glossário. Ele reprovou 14 trocas, que foram declaradas em
  `omitidos`.
- **O inglês é mapa, nunca texto.** Nenhuma palavra dele entra no livro.
- **A prova.** `provar.py` compara, com difflib, a fonte e o EPUB montado, palavra a palavra, e põe
  cada trecho numa categoria declarada. Sai com erro se sobrar trecho sem categoria.

### Decisões do Mateus (2026-11-04: "Aprovar os seis")

1. Caminho sem código, com o mapa no *Último Guardião* inteiro.
2. A abertura do *Último Guardião* diz "Warcraft: O Último Guardião, de Jeff Grubb."; a versão da
   tradução vai para o metadado.
3. Títulos do *Último Guardião* como "Capítulo 1: Karazhan". O `conferir` acusa "1. Karazhan" como
   item de lista.
4. A seção "Notas" de Ascensão sai do áudio, registrada; o crédito da tradução vai para o metadado.
5. Erros de espaço de Ascensão e o hífen no lugar do travessão se corrigem.
6. Ascensão usa os 9 nomes que o Tides decidiu. Os sem precedente (Frostwolf, Shattered Hand)
   ficam em inglês.

### Os scripts

Ficam fora do repositório, na pasta de notas destas sessões:
`~/.config/Claude/side-session-notes/local_6c1a5889-6a59-4fcf-8b7d-af6c9517aaa3/warcraft-mapa/`.

| Arquivo | O que faz |
|---|---|
| `receita.sh` | a sequência inteira dos dois livros, de `livros/cru/` a `livros/prontos/` |
| `ug.sr`, `asc.sr` | os `search-replace` do Calibre |
| `unir_xhtml.py` | une os XHTML de Ascensão e tira o que o epubcheck reprova na origem |
| `alinha.py`, `ingles.py` | o alinhamento de frases por tamanho, nome e aspas, e os parágrafos do original |
| `mapa_ug.py`, `mapa_asc.py` | gravam `adaptados/` e `glossario.json` de cada livro |
| `provar.py`, `inventario.py`, `paradas.py` | a prova palavra a palavra, o inventário por script e os minutos do roteiro |

### Medição final

| Medida | *O Último Guardião* | *Ascensão da Horda* |
|---|---|---|
| Capítulos no sumário | 18 títulos | 24 títulos |
| Parágrafos | 1.987 | 2.045 |
| Palavras por parágrafo: mediana, maior | 30, 164 | 28, 217 |
| Prova: trecho não declarado | 0 | 0 |
| `conferir`; epubcheck | passou; 0 erro | passou; 0 erro |

Trocas declaradas no *Último Guardião*: 1.106 Hadggar → Khadgar, 6 hífens devolvidos, 18 títulos e
a abertura. Em Ascensão: 188 reticências, 12 pontuações coladas, 5 espaços antes de pontuação, 5
travessões, 232 nomes do Tides (133 Blackhand e 1 "Blachand", 43 Blackrock, 29 Doomhammer, 9 Rend, 8
Maim, 3 Dragonmaw, 3 Bleeding Hollow, 2 Proudmoore, 1 Deadeye), 5 grafias de Kil’jaeden e 3 segmentos
de "Notas" fora do áudio.

## Fila

Defeitos de código achados nestes livros, não corrigidos aqui. A correção é uma sessão filha, com o
sim do Mateus.

- **Hífen tirado sem prova.** O `importar-pdf` tira o hífen do fim da linha quando o livro não
  escreve a palavra com hífen em outro lugar: "abri-|los" vira "abrilos". Foram 6 no *Último
  Guardião*, todas erradas, 5 pronomes e "contra-atacado"; aqui, corrigidas por lista no script.
- **`<body>` vazio.** O `montar` deixa o corpo vazio quando todos os segmentos de um capítulo saem,
  e o epubcheck reprova (RSC-005). Aqui, evitado pondo "Notas" dentro do Epílogo e dando texto à
  abertura.
- **Frase partida do Tides.** Os 44 casos do ADR-0007 continuam.

## Consequências

**Ganha:**
- Dois livros prontos sem tocar em `src/`, e nenhum livro de referência muda, por construção.
- O mapa não custa adaptação por palavra.

**Perde:**
- A receita é por livro e não tem teste. Quem a repete é a sessão, à mão.
- Os scripts moram fora do git. Se a pasta de notas sumir, sobra a descrição daqui.
- O `importar-pdf` continua fundindo os parágrafos de PDF sem recuo, e não avisa.
- Um romance de fã sem o original em inglês à mão não tem mapa: sobra a alternativa 1A.
- O Calibre normaliza `pt-BR` para `pt`; o `ebook-meta -l pt-BR` precisa vir depois da conversão.

**Aceito conscientemente:** o `adaptar` foi usado num livro que não é didático, como transporte. O
`conferir` serve bem, mas o grupo que troca nome raro tem de declarar o termo em `omitidos`.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Fidelidade | `provar.py` | a cada livro por esta rota, antes de declarar pronto; responsável: a sessão | sobra trecho sem categoria |
| Integridade, nome e número | `conferir` no modo adaptação, sem mudança | antes do `montar` (recusa) | ID sem grupo, nome fora do glossário, termo raro sem declaração |
| Escuta ★: o que a máquina acha | `inventario.py` | a cada livro por esta rota; responsável: a sessão | achado novo contra "O que atrapalha o ouvido" |
| Livro válido | epubcheck | depois do `montar`; responsável: a sessão | qualquer erro |
| Escuta ★ (manual) | as paradas do roteiro, na leitura do Mateus | livro pronto; responsável: Mateus | tropeço audível |
| Nada entra no pacote | `make check` e `test_arquitetura.py`, sem mudança | portão | `subprocess` ou Calibre em `src/` |

Regra derivada no `AGENTS.md`: Calibre e mapa são caminho, sem código; o que eles fizerem a mais de
uma vez em livros diferentes volta a ser decisão de código.

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-04 · Aprovado em: 2026-11-04 (pelo Mateus,
por meio da sessão principal: "Aprovar os seis").
