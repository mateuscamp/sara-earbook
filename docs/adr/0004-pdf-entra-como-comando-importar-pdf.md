# 0004 — PDF entra no ai-book como o comando `importar-pdf`, não como projeto à parte

**Status:** Aceito
**Data:** 2026-11-01
**Driver ★:** qualidade da escuta (ADR-0001); o EPUB que sai do PDF serve só para ouvir

## Contexto

O ai-book tem dois braços: traduzir do inglês e preparar para o áudio (ADR-0003). O
Mateus quis saber se o terceiro, converter PDF para EPUB, deveria entrar aqui ou virar um
projeto novo. A resposta depende de para que serve o EPUB convertido. Se for para ler na
tela, a fidelidade visual (itálico, tabela, imagem, índice) vira requisito, com régua e
dependências próprias, e o projeto novo vence. Se for só para ouvir, a formatação importa
só até onde muda o áudio. O Mateus respondeu: **só para ouvir**.

Medição que pesa: hoje o ai-book depende só do `lxml`, e `make check` roda em segundos. Os
defeitos que o `limpar` corrige no Tides of Darkness (423 cabeçalhos de página, 290
parágrafos partidos, 25 capitulares deslocadas) nascem na conversão de PDF. No PDF, a
posição na página denuncia o cabeçalho, e o tamanho da fonte denuncia a capitular.

Quantum atual: 1 (CLI local + pasta de trabalho em arquivos).

## Alternativas consideradas

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Projeto novo, conversor fiel à formatação, falando com o ai-book só por EPUB | drivers, testes e dependências separados; serve também para leitura | 2 quanta sem driver de modularidade, já que a leitura não é requisito; duplica a lógica de limpeza; mais um repositório para manter | o requisito que justificaria (leitura visual) não existe |
| B. Comando dentro do ai-book, com conversor pesado (PyMuPDF, que é AGPL, ou modelos de layout com torch) | melhor extração de layout | o portão fica lento e pesado para todo mundo, inclusive para quem só prepara EPUB em português | custo alto para um ganho que o áudio não ouve |
| **C. Comando `ai-book importar-pdf`, com dependência leve** | um quantum só; a saída cai direto na esteira (`importar-pdf → preparar → limpar → ...`); usa a geometria do PDF para tirar cabeçalho e capitular na origem | sem fidelidade visual; PDF escaneado (sem camada de texto) fica fora | — |

## Decisão

- `ai-book importar-pdf livro.pdf` gera um EPUB simples (títulos, parágrafos e notas), que segue pela esteira normal. O contrato com o resto do projeto continua sendo o EPUB.
- O conversor usa o que só o PDF sabe: a posição na página, para cabeçalho e número de página, e o tamanho da fonte, para título e capitular. O `limpar` continua existindo, porque EPUB mal convertido por outros (como o do epdf.pub) segue chegando.
- A biblioteca é **`pdfminer.six`** (MIT, Python puro), escolhida pela medição abaixo. O `pdfplumber` dá a mesma informação por caractere, mas traz 28 MB a mais (Pillow e pdfium, para renderizar página, o que não fazemos). PyMuPDF (AGPL) e modelos de layout ficam fora, pelo peso.
- PDF escaneado, sem camada de texto, fica fora do escopo. OCR seria outro ADR.

### Spike (2026-11-01, descartado depois da medição)

Foram medidas as páginas 21 a 60 de dois PDFs do Mateus, com `pdfminer.six`:

| Medida | *Competente o Suficiente* (pt-BR, 503 p.) | *Software Architecture: The Hard Parts* (en, 462 p.) |
|---|---|---|
| Velocidade | 20 ms/página: o livro inteiro em ~10 s | 14 ms/página |
| Camada de texto | todas as páginas | 1 página é só imagem |
| Cabeçalho corrente | em cima: número de página (27/40) e o título do livro e do capítulo com letras espaçadas (`C O M P E T E N T E …`) | embaixo: número, `|` e `Chapter N: <título do capítulo>` |
| Títulos | pelo tamanho da fonte (19 pt contra 10,5 pt no corpo) | hierarquia pelo tamanho (18,9 / 15,8 / 15 pt) |
| Parágrafo | recuo da primeira linha (x 67 contra a margem 54) | recuo (x 90 contra a margem 72) |
| Hifenização no fim da linha | 16 em 40 páginas | 14 em 40 páginas |
| Código | nenhum | fonte monoespaçada (UbuntuMono) |
| Capitular | nenhuma | nenhuma (os 3 casos que a medição achou eram a 1ª letra de títulos) |

O que muda no plano:
- **O cabeçalho sai pela posição na página, não pelo texto.** Nos dois livros, o cabeçalho tem o título do *capítulo*, que a regra do `limpar` (frase no título ou no autor do livro) só marcaria como suspeita. As letras espaçadas tornam o reconhecimento por texto quase impossível.
- A hifenização no fim da linha precisa de regra própria, porque o português tem palavra composta com hífen (`guarda-chuva`).
- O código precisa de uma decisão para o áudio (ler, resumir ou pular), que é outro ADR.

### Primeira regra: cabeçalho e rodapé pela posição (2026-11-01)

`dominio/paginacao.py` olha só a faixa de 8% no alto e no pé da página e, nela, só a linha com fonte não maior que a do corpo (o tamanho com mais caracteres no livro, +0,5 pt). Dessas linhas, sai:
- o **número de página**: algarismo ou romano, com ou sem separador (`| 23`, `xii`), quando o deslocamento entre o número impresso e a página do PDF se repete em 3 páginas ou mais da mesma sequência. Um número sozinho (`2020.`, `1.`, `mix`) não prova sequência e fica;
- a **linha repetida**: a mesma, sem contar espaço, caixa e número, em 3 páginas ou mais **no mesmo topo** (tolerância de 0,01).

O segundo critério (fonte, coerência e topo) veio do A1 da auditoria de 2026-11-01. Sem ele, título de capítulo em 20 pt, "IV" grande e "2020." no pé saíam. Livros inteiros, lidos por `adaptadores/pdf.py` uma página por vez:

| Livro | Páginas | Números de página | Cabeçalho/rodapé repetido | O que sobrou na borda | Memória |
|---|---|---|---|---|---|
| *Competente o Suficiente* | 503 (10 s) | 398 (impresso = página − 7) | 389 (título do livro 207; títulos de capítulo espaçados) | 15 linhas: cabeçalho de capítulo curto, em 1 ou 2 páginas | 92 MB (eram 720 MB guardando a página inteira) |
| *Hard Parts* | 462 (5 s) | 440: 429 arábicos (impresso = página − 18) e 11 romanos (`v`–`xv`) | 782: 416 `|` sozinhos e 366 `Chapter N: …`, `Index` | 60 linhas: rodapé de seção curta, títulos perto do alto e 4 algarismos de 1,4–2,8 pt que não são número de página | 67 MB |

Os dois PDFs estão fora de `livros/`: `~/Documentos/Akita/` e a pasta de fontes do projeto do ChatGPT. A medição se reproduz com `earbook importar-pdf <pdf> --epub <destino>` e depois `earbook preparar` (tabela da ponta a ponta, abaixo).

Limites registrados pela auditoria, sem caso nos livros medidos:
- **A4:** texto dentro de Form XObject (`LTFigure`) é descartado sem registro; página sem camada de texto volta vazia. Os dois livros têm zero caracteres em `LTFigure`.
- **A5:** a faixa é medida na MediaBox, não na CropBox. Com sangria, o cabeçalho cai fora da faixa e fica (falso negativo).
- **A8:** a marca de fonte monoespaçada vem do nome da fonte e erra nos dois sentidos (`MonotypeCorsiva` passa como mono, `CMTT10` não). Desde a montagem de blocos, a marca decide o que é código: o erro vira prosa lida como código (vai para `<pre>`, e o `preparar` a lê como parágrafo do mesmo jeito) ou código lido como prosa.
- **P2 (pós-auditoria):** um PDF de ~1,5 KB, com coordenadas enormes, prendeu o pdfminer por mais de 120 s na análise de layout (`find_neighbors`). O comando `importar-pdf` existe e ainda não tem o limite de tempo por página: um PDF assim prende o comando até o Ctrl+C, que sai sem deixar EPUB. Continua registrado para o próximo ciclo.
- **Revisão nº 4:** número de página com fonte maior que a do corpo + 0,5 pt (12 pt com corpo de 10,5) não sai, porque o filtro de fonte protege número e título de capítulo grandes (A1). É falso negativo aceito: o número fica no áudio.

Correções da revisão e da pós-auditoria (2026-11-01): o `try` do adaptador cobre só o pdfminer, com captura ampla nessa borda (P1: `AttributeError` escapava), e bug da nossa conversão continua aparecendo como bug; a sequência de números conta páginas, não ocorrências; alto e pé são agrupados separadamente antes da mediana do topo; o ponto deixou de ser separador de número ("1.2" virava 12).

Correções da pós-auditoria antes do push (2026-11-01):
- **F1:** o nome de fonte malformado no descritor (`(Courier)` ou `5`) chegava como bytes ou número e quebrava a regex de fonte monoespaçada com `TypeError`. Agora só nome em texto é testado. Um nome em bytes que é de fato monoespaçado (`b"Courier"`) fica marcado como não monoespaçado: é falso negativo aceito, e o código dessa fonte sai como parágrafo (nenhum caso nos dois livros).
- **F2:** um xref com deslocamento negativo dava `OSError` de `seek`, que o adaptador relançava como "arquivo inacessível". Agora o arquivo abre fora do `try`, e dentro dele só `MemoryError` passa direto. Custo aceito: um erro de disco no meio da leitura (EIO) também sai como "não é um PDF válido", com a causa guardada no `from`.

Correções da pós-auditoria no ciclo seguinte (2026-11-01):
- **O1:** a linha só de número ("2020." no pé de 3 páginas) virava `#.` na chave da repetição e saía como rodapé repetido, mesmo reprovada na coerência da numeração. Agora número sozinho só sai pela regra do número de página.
- **O2:** a mediana do topo do grupo inteiro caía entre duas alturas quando a mesma frase aparecia em duas (3 páginas a 0,02 e 3 a 0,05), e nada saía; com 4 e 3, só a maioria saía. Agora as ocorrências se agrupam por altura (tolerância de 0,01), e cada altura com 3 páginas ou mais sai.

Pendente: letra espaçada na borda é sinal forte de cabeçalho, mesmo sem repetição, porque texto do livro não vem espaçado.

### Segunda regra: blocos e capítulos (2026-11-01)

`dominio/blocos.py` monta, a partir das linhas que sobram, os blocos que o ouvido usa. Cada regra entrou com um teste visto falhar e veio de um defeito medido nos dois livros:
- **tipo pela fonte:** título é 1,2 vez o corpo ou mais; nota, menos de 0,85; código, linha **toda** em fonte monoespaçada. No Hard Parts, as 584 linhas de código são 100% monoespaçadas, e 183 linhas de prosa com um nome de código no meio (`ss.survey`) ficam entre 0 e 90%. Com "alguma letra monoespaçada", essas 183 viravam código e partiam o parágrafo (180 blocos de código, agora 79).
- **parágrafo novo:** recuo de 3 pt ou mais depois de frase fechada (o parágrafo recua 13 pt no Competente e 18 no Hard Parts; item de lista, 4 e 5; nenhuma linha de corpo entre 1 e 3), espaço acima de 1,35 entrelinha, marcador de lista (`–`, `•`, `1.`), ou página nova que começa com maiúscula depois de frase fechada. Recuo que aparece no meio da frase (texto contornando figura) não quebra.
- **linha visual:** o pdfminer parte a linha justificada em pedaços na mesma altura; eles voltam a ser uma linha. Com 3 pedaços ou mais, é linha de tabela, e cada uma vira um bloco.
- **hífen de fim de linha:** o hífen suave (U+00AD, 790 quebras no Competente) sempre sai. O `-` e o U+2010 (1.058 quebras no Hard Parts, que nunca o usa no meio da linha) saem, a não ser que o livro escreva a palavra inteira com hífen em outro lugar: o próprio livro é o dicionário (`non-productive`, 42 mantidos no Hard Parts).
- **legenda ou nota no meio do parágrafo:** quando a linha seguinte continua a frase em minúscula, o parágrafo é retomado e a legenda vai para depois dele.
- **capítulo:** começa no maior tamanho de título que aparece em 3 páginas ou mais (30 pt, o número do capítulo no Competente; 25,2 pt, o título no Hard Parts). O que vem antes vira um capítulo de abertura. Os títulos menores ganham nível 2 a 6, pela ordem de tamanho.

### O comando `earbook importar-pdf` (2026-11-01)

`earbook importar-pdf livro.pdf [--epub destino] [--idioma pt-BR]` lê, tira cabeçalho e rodapé, monta os blocos, divide os capítulos e grava, por `adaptadores/epub_simples.py`, um EPUB 3 mínimo: `mimetype` primeiro e sem compressão, um XHTML por capítulo (`h1`–`h6`, `p`, `pre` e `aside epub:type="footnote"`), sumário `nav` fora do spine, `dc:title` com o nome do arquivo (o metadado de título do PDF costuma ser o nome do arquivo do editor) e `dc:language` com o `--idioma` (padrão `und`). Caractere que o XML 1.0 não aceita sai do texto, para o `preparar` não recusar o livro inteiro. O comando recusa EPUB que já existe antes de ler o PDF, recusa PDF sem texto (escaneado: não há OCR) e, se a gravação falhar no meio, apaga o EPUB parcial. O teste de contrato é o próprio `preparar`: o EPUB gravado precisa voltar com os mesmos papéis e textos.

Ponta a ponta (`importar-pdf` e depois `preparar`):

| Livro | `importar-pdf` | Blocos: título / parágrafo / código / nota | Capítulos | Hífen tirado / mantido | `preparar` | O que sobrou para o `limpar` |
|---|---|---|---|---|---|---|
| *Competente o Suficiente* | 503 p. em 10 s; EPUB de 375 KB | 74 / 4.217 / 8 / 337 | 23 | 739 / 3 | 4.636 segmentos em 0,2 s; nenhum texto fora | nada: 0 remoções, 0 junções, 0 suspeitas |
| *Hard Parts* | 462 p. em 4 s; EPUB de 252 KB | 306 / 2.820 / 79 / 10 | 22 | 1.265 / 43 | 3.215 segmentos em 0,2 s; nenhum texto fora | 20 junções e 15 suspeitas |

Antes das duas últimas regras (U+2010 e linha toda monoespaçada), o `limpar` ainda juntava 5 parágrafos no Competente e 57 no Hard Parts, 9 deles com palavra partida (`imple‐ mented`). As 20 junções que sobraram no Hard Parts são legenda colada em código (o `preparar` lê `<pre>` como parágrafo), linha de tabela e nome de código partido sem hífen (`ss.report` + `ing)`). Os 16 `x‐ y` que restam dentro de segmento são células de tabela. Das 15 suspeitas, 11 são do índice remissivo em duas colunas: a letra da seção (`A`, `B`…) se junta, na mesma altura, à entrada da coluna da direita, e a entrada seguinte começa em minúscula. O índice é ruído para o ouvido; o `limpar` o mostra como suspeita em vez de colar em silêncio.

Correções da revisão (code-review, 2026-11-01), cada uma com o teste visto falhar:
- **nº 1:** com um título aberto, a linha em minúscula retomava o parágrafo de antes do título, e o título ia parar depois do texto. Só nota e código interrompem parágrafo agora. É o que trouxe à tona as 11 suspeitas do índice.
- **nº 2:** os pedaços na mesma altura eram ordenados por (topo, x), e o da direita, um pouco mais alto, vinha primeiro (618 vezes no Hard Parts: célula de tabela, `October 2021: First Edition`). Agora se agrupa por altura e se ordena só pelo x.
- **nº 3:** o `close` do EPUB ficava fora do `try`, e o disco cheio no último flush deixava um EPUB truncado, que o próximo `importar-pdf` recusaria como existente.

Medidos e registrados, sem caso nos dois livros:
- **nº 4:** linha que começa com travessão ou meia-risca abre item de lista mesmo no meio da frase. Traço seguido de minúscula depois de frase aberta: 0 no Competente, 0 no Hard Parts. Os 341 do Competente com traço e minúscula vêm depois de `:` ou `;`, são itens de verdade.
- **nº 5:** notas de rodapé seguidas na mesma página viram uma nota só, porque nota não quebra por espaço. Nenhuma no Hard Parts; no Competente, as 4 notas com outra dentro são sumário, cronologia e bibliografia em letra pequena, não rodapé.
- **nº 6:** o agrupamento por altura do O2 encadeia: ocorrências que andam 0,009 por página formam um grupo maior que a tolerância. Medido: 0 grupos no Competente; no Hard Parts, 1 (os 433 números de página, de 0,012 de largura), que o O1 já tira da regra da repetição.

Correções da auditoria e da revisão em xhigh (2026-11-01), cada uma com o teste visto falhar:
- **A1:** o tamanho da linha era a média das letras. Na saga do Hard Parts (9 pt, corpo de 10,5), um nome de código em 8,5 pt puxava a média para baixo de 0,85 do corpo, e a linha de prosa virava nota. O hífen da linha de cima então se juntava à linha seguinte do parágrafo: `Addi-` + `removed` virou `Addiremoved`, e "Addison created…" foi parar numa nota de rodapé. Agora vale a moda (o tamanho da maioria das letras). Notas: 392 → 337 no Competente (340 com a moda; o empate para o maior, da pós-revisão, tirou mais 3 referências da bibliografia que partiam entre parágrafo e nota), 24 → 10 no Hard Parts. Cabeçalho e rodapé não mudaram (398/389 e 440/782).
- **A2:** a quebra no hífen de palavra que já tem outro hífen tirava o hífen: `--noagent-state` (Competente) e `proof-ofconcepts` (Hard Parts). Palavra com outro hífen antes ou depois da quebra agora é composta.
- **Hífen repetido (norma brasileira):** `human-` / `-friendliness` saía `human- -friendliness`; agora fica um hífen só (2 casos no Competente).
- **A3:** o O1 pulava toda linha sem letra, e o rodapé fixo (`2021`, `© 2020`, uma data) deixou de sair. Agora a linha sem letra se agrupa pelo texto literal: números diferentes (`2020.`, `1999.`) ficam, e o mesmo texto em toda página sai.
- **Saída fechada:** o `print` do resumo ficava dentro do `try`, e `| head` transformava o EPUB gravado em "earbook: [Errno 32] Broken pipe" com código 1. O código 1 agora quer dizer só que o trabalho falhou.
- **A4:** 4 testes para comportamento que já existia (título fecha a retomada mesmo com nota depois, linha de tabela não entra no parágrafo aberto, prosa e código na mesma altura seguem no parágrafo, e o sumário `nav`), cada um visto falhar com o defeito plantado numa cópia.

Pós-revisão das correções (2026-11-01): no empate entre tamanhos (tantas letras de código quanto de prosa), a moda ficava com o que vinha primeiro e a linha voltava a virar nota; agora fica o maior. A saída fechada (`| head`) agora sai quieta, com código 0, em vez de traceback. O `tests/test_blocos.py` passou de 400 linhas e se dividiu em três, com os ajudantes em `tests/linhas_de_teste.py`. Registrados sem correção, sem caso nos livros: a linha que começa com `-` e letra depois de linha terminada em hífen é colada sem espaço mesmo quando é uma opção de comando (`force-` + `-rf`); e o mesmo número sem letra repetido em 3 páginas na faixa da borda (rótulo de eixo de gráfico) sai como rodapé, como já saía antes do O1.

Pós-auditoria das correções (2026-11-01):
- **B1:** a saída quieta só valia no teste. Num cano de verdade, o `print` só enchia o buffer, e o EPIPE vinha no flush do fim do processo, fora do `try`: `| true` saía com código 120 e "Exception ignored". Agora o resumo sai com `flush=True` dentro do `try`, e o teste usa um `os.pipe` com a ponta de leitura fechada.
- **B2:** a regra do A2 mantinha o hífen da quebra sempre que havia outro hífen por perto, também quando a quebra caía numa sílaba (`ser-` + `vice-based`, `pergun-` + `tou-me`, `service-ori‐` + `ented`). Agora, com outro hífen por perto, o hífen da quebra sai se as metades vizinhas a ela formam palavra que o livro escreve inteira (`service`, `perguntou`, `oriented`); `no` + `agent` e `of` + `concepts` não formam, e o hífen fica. Nos dois livros, nada muda além dos 2 casos do A2.
- **B3:** a linha do Competente nesta tabela tinha sido medida antes do empate para o maior; corrigida (337 notas, 739/3, 4.636 segmentos).

Medido e recusado: manter o hífen quando as duas metades existem como palavra no livro resolveria `idea-sparking`, mas manteria 265 hífens no Hard Parts, quase todos errados (`develop-ment`, `cus-tomer`, `exist-ing`). O composto de ocorrência única partido no próprio hífen fica sem hífen (`ideasparking`, `microfrontends`), como limite.

Próximo ciclo (revisão em xhigh, medidos, sem correção ainda):
- **Letra espaçada:** 40 blocos no Competente (`P A R T E I · O Q U E É…`, o nome do autor) chegam ao EPUB letra por letra, e o TTS soletra. O `normalizar_espacos` do adaptador apaga o espaço maior entre as palavras antes que alguém possa recompor.
- **Duas colunas:** a linha visual junta tudo o que está na mesma altura da página e descarta as caixas do pdfminer. Página em duas colunas sai intercalada linha a linha: no Hard Parts, é o índice remissivo (11 das 15 suspeitas); num artigo em duas colunas, seria o corpo.
- **Nota de rodapé que não é nota:** das 337 notas do Competente, 3 são rodapé numerado; o resto é legenda (56), bibliografia e rótulo espaçado, e tudo sai como `aside epub:type="footnote"`. A bibliografia ainda oscila entre nota e parágrafo, com o tamanho na beira de 0,85 do corpo.
- **Pedaço da esquerda decide o tamanho:** depois da correção nº 2, o tamanho da linha visual é o do pedaço mais à esquerda; uma capitular grande ao lado do corpo faria a linha inteira virar título. Sem capitular nos dois livros.

## Consequências

**Ganha:** um comando a mais na mesma esteira, sem repositório novo. Os defeitos de conversão são atacados onde nascem.

**Perde:**
- O EPUB convertido não serve para leitura bonita na tela.
- O ai-book ganha uma dependência nova, que precisa ficar atrás de um adaptador (`adaptadores/pdf.py`) para o domínio continuar puro.

**Aceito conscientemente:** se aparecer o requisito de ler o EPUB convertido na tela, esta decisão cai e a opção A volta, com o conversor saindo para um projeto próprio. A fronteira atrás do adaptador existe para essa saída custar pouco.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| A biblioteca de PDF só entra pelo adaptador | import-linter: `dominio` e `comandos` não importam a biblioteca de PDF | portão | contrato quebrado |
| O portão continua leve | tempo do `make check` | a cada mudança no conversor; responsável: Mateus | passar de 30 s |
| A escuta ★ | rodar `importar-pdf` + `preparar` num PDF real em `livros/` e contar o que o `limpar` ainda precisa tirar | a cada mudança no conversor | a contagem sobe |

Regra derivada no `AGENTS.md`: a biblioteca de PDF só entra em `adaptadores/`.

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-01 · Aprovado em: 2026-11-01
