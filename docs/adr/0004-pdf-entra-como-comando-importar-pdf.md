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

### Escuta no ElevenReader (2026-11-01)

O Mateus ouviu o EPUB do Competente pelas 7 paradas do roteiro (abertura, começo de capítulo, legenda, lista, código, parágrafo longo no meio e último capítulo): 7 de 7 ok, com um defeito só. O PDF desenha os rótulos com letra espaçada (`P A R T E I`), e o ElevenReader cola as letras soltas: leu "PARTEI" como o verbo "partei" e "FABIOAKITA" como uma palavra só. O TTS não soletra, como o ADR supunha; ele cola, o que é pior, porque às vezes forma uma palavra que existe.

Correção: `dominio/pagina.py` (`juntar_letras_espacadas`) recompõe o trecho espaçado pelas posições reais das letras, que o adaptador entrega (`Letra`); o espaço que o pdfminer põe não serve, porque em `B O M 15` ele pôs um só antes de um vão de 10,5 pt. A decisão é por trecho, não pela linha:
- as letras se cortam nos vãos abertos, de mais de 0,08 do tamanho da fonte (medido: 0,14 a 0,22 na letra espaçada, perto de zero dentro da palavra comum);
- um trecho é recomposto quando é feito de caracteres soltos seguidos, com 3 pares de letras vizinhas ou mais, e quando o vão entre as letras dele fica abaixo de 0,75 do espaço comum da linha, se a linha tem palavra comum para servir de régua. Os pares protegem a fórmula `D = A + I − 1` (Hard Parts p. 87), que tem sempre um operador entre duas letras; a régua protege a prosa com caracteres soltos (`passos 1 2 3 4 e 5`, `Notas 1 2 3 4 5 6`), que a code-audit mostrou colada em `1234e5`;
- dentro do trecho, a palavra termina onde o vão passa do dobro do vão entre letras, medido pelo primeiro quartil dos vãos do trecho (4,4 contra 1,4 pt em `PARTE I`; 6,4 contra 2,2 pt em `FABIO AKITA`). O quartil, e não a mediana: em `É O FIM`, com tantos vãos de palavra quanto de letra, a mediana caía entre os dois e saía `ÉOFIM` (code-audit).

Na linha mista, a palavra comum fica como está (`Capítulo 3 E S P E C I A L` → `Capítulo 3 ESPECIAL`; pela linha inteira, sairia `Capítulo3`, como a code-review mostrou). Linha de código fica de fora, porque na fonte monoespaçada o espaço tem a largura de uma letra (`a = 1 2 3 4 5`). Fica como limite, sem caso nos dois livros: uma linha só de caracteres soltos com o espaço comum e 3 pares ou mais, sem palavra comum para servir de régua (`1 2 3 4` sozinho), ainda cola. Medido: 433 linhas recompostas no Competente, todas de letra espaçada de verdade (207 do cabeçalho corrente, que sai depois, e os títulos, as aberturas de parte e os apêndices); 0 no Hard Parts. Blocos, borda e segmentos não mudaram. Registrados pela code-review, sem caso nos dois livros: texto justificado pelo espaçamento entre caracteres pode passar por letra espaçada, se a folga entre as letras passar de 0,08 do tamanho da fonte; e o rótulo recomposto fica em maiúsculas com algarismo romano (`PARTE I`), que o TTS pode ler como a letra i. Esse último é para conferir na próxima escuta.

A escuta trouxe ainda, para o próximo ciclo:
- **Título do livro:** era o nome do arquivo (`Competente-o-Suficiente-ebook`), e o ElevenReader o mostrava também como cabeçalho dentro do capítulo. Resolvido logo depois; ver "Título e autor do metadado".
- **Página de direitos autorais:** era lida em voz alta ("© 2026 Fabio Akita. Todos os direitos…"). Resolvido logo depois, na limpeza (ADR-0003, "Página de direitos autorais").

### Título e autor do metadado (2026-11-01)

A primeira versão do comando usava o nome do arquivo como título, porque se supôs que o metadado do PDF costuma trazer o nome do arquivo do editor. A medição desmentiu a suposição nos dois livros: o `/Info` do Competente traz "Competente o Suficiente", de Fabio Akita, e o do Hard Parts, "Software Architecture: the Hard Parts", de "Ford, Neal;Richards, Mark;Sadalage, Pramod;Dehghani, Zhamak;". Agora:
- o título vem de `--titulo`; sem ele, do metadado; e, se o metadado parece nome de arquivo ou valor padrão de editor de texto ("Microsoft Word - cap1.doc", `.pdf`, "Untitled", "Documento1"), do nome do PDF (`dominio/metadados.py`);
- o autor vem de `--autor` ou do metadado, separado por "; " e sem o nome de máquina ("Administrator", "User"); vai para o `dc:creator` do EPUB, e com ele a limpeza também reconhece o cabeçalho com o nome do autor;
- `adaptadores/pdf.py` (`ler_metadados`) lê o `/Info` pela mesma tradução de erros das páginas (`_pelo_pdfminer`); o valor vem cru do PDF, e só texto passa (PDFDocEncoding ou UTF-16 com BOM). O pdfminer não tipa o `info` e o `resolve1` devolve `Any`: as duas supressões ficam na borda, com o motivo.

O resumo do comando diz o que entrou: "Título: Competente o Suficiente, de Fabio Akita."

Correções da code-review (2026-11-01): o título em UTF-8 com BOM, que o PDF 2.0 aceita e o `decode_text` do pdfminer não conhece, agora é decodificado como UTF-8 (saía "ï»¿AÃ§Ã£o"); e "Untitled" ou "Sem título" só são recusados quando são o título inteiro ("Untitled: Notes on Art" é título). Correções da code-audit: o título feito só de caractere de controle (`\0\0`) virava `dc:title` vazio e agora cede ao nome do PDF; o UTF-16LE com BOM, fora da especificação mas visto, é decodificado (saía "ÿþAção"); e, do Office, só o padrão do editor com o traço ("Microsoft Word - cap1") é recusado ("Microsoft Excel 2019 Bible" é título). Correções da pós-auditoria: o `resolve1` do pdfminer segue referência sem limite, e um `/Title` que aponta para um objeto que aponta para si mesmo travava o `importar-pdf` para sempre depois de ler todas as páginas (N1, regressão desta rodada, porque antes o metadado nem era lido). Agora a leitura segue uma referência só, e referência de referência vira vazio. A decodificação, que é nossa, saiu do `try` do pdfminer (N2). O título ou o autor sem nenhuma letra ou algarismo (só `\u200b`, `\ufeff` ou `\ufffd`) cede ao nome do PDF ou fica vazio (H1). Registrado sem correção: o `importar-pdf` abre o PDF duas vezes, uma para as páginas e outra para o `/Info`; a segunda leitura é só da tabela de objetos, desprezível perto do layout das páginas.

### Subtítulo em negrito do tamanho do corpo (2026-11-01)

No Competente, o subtítulo de seção tem o tamanho do corpo (10,5 pt) e só muda a fonte, para negrito. O `_tipo` olhava só o tamanho, e o subtítulo entrava colado no parágrafo seguinte: "Pedaços de palavra O modelo não enxerga letras…", "Uma peça de cada vez Agora o mecanismo inteiro…".

Medido, contando a linha inteira em fonte de estilo negrito no nome (`-Bold`, `-Semibold`, `,Bold`, `-Black`, `-Heavy`, `-Demi`) e com o tamanho na faixa do parágrafo (de 0,85 a 1,2 do corpo):
- **Competente (679 linhas):** 302 subtítulos de 10,5 pt (266 em SourceSans3-SemiboldIt e 36 em SourceSerif4-Bold, os grupos das referências do apêndice), sempre na margem, depois de frase fechada; 228 seções de 12 pt, que também saíam como parágrafo, só que separadas pelo espaço ("O corretor do celular, só que enorme"); 146 verbetes do glossário em 9,5 pt ("Tokenizador"), colados na definição; e 3 linhas soltas (o nome do autor na capa e 2 títulos de referência bibliográfica em 9 pt). As 619 linhas com negrito misto são ênfase no meio da prosa.
- **Hard Parts (1.572 linhas):** 1.401 em semibold de 9 pt, quase todas rodapé de página (1.275 no pé, das quais a paginação tira 1.222); as 179 que sobram depois da paginação são rodapé de seção que ela não tirou (as outras 53 do pé), cabeçalho de tabela ("Instances") e 1 linha da página de direitos (medição corrigida em "Verbete em negrito abaixo do corpo"); 118 células de tabela em 10 pt ("Advantages / Disadvantages"); 29 subtítulos em 11,6 pt, que saíam como parágrafo ("Scalability", "Fault tolerance", "Fitness function: …"); o sumário em 12 pt; e 1 linha de código em UbuntuMono-Bold, que continua código.

Regra: a linha visual **toda** em negrito, do tamanho do corpo (menos 0,5 pt de folga) até 1,2 vez o corpo, é título. Toda, e não alguma, pela mesma razão do código: a ênfase no meio da prosa não pode partir o parágrafo; na linha visual feita de pedaços, todos precisam ser negrito ("Ticket Shared" em negrito ao lado de "ss.ticket.shared" segue parágrafo). O piso no corpo porque, nos dois livros, nenhum subtítulo é menor que o texto, e o negrito menor é cabeçalho de tabela, rodapé de seção, verbete ou referência: sem o piso, as 97 linhas visuais em negrito de 9 pt que sobram no Hard Parts depois da paginação viravam título. A ordem das perguntas se mantém: monoespaçada é código mesmo em negrito, e a fonte menor que 0,85 do corpo é nota. O estilo vem depois do traço ou da vírgula do nome, para "Blackadder" não ser negrito. O nível sai do tamanho, como os outros títulos.

Ponta a ponta (`importar-pdf`, `preparar` e `montar`):

| Livro | Títulos | Segmentos | Limpeza | Montado |
|---|---|---|---|---|
| *Competente o Suficiente* | 74 → 602 (+528: as seções de 12 pt e os subtítulos de 10,5 pt; nenhum perdido) | 4.636 → 4.937 (os subtítulos saíram do parágrafo) | igual: 1 remoção, 0 junções, 0 suspeitas | 4.936 segmentos, 336 notas; epubcheck limpo |
| *Hard Parts* | 306 → 387 (+81: os subtítulos de 11,6 pt, os cabeçalhos de tabela e as linhas do sumário; nenhum perdido) | 3.215 → 3.261 | 7 remoções iguais; 20 → 19 junções e 15 → 14 suspeitas: as duas que saíram eram cabeçalho de tabela em negrito (p. 421 e 429), que agora é título | 3.235 segmentos; epubcheck limpo |

Capítulos (23 e 22) e o sumário `nav` não mudaram.

Correções da code-review (2026-11-01):
- **nº 1:** o negrito valia sozinho; num livro com o corpo inteiro numa fonte de nome negrito (`-Semibold`), toda linha viraria título e o livro sairia sem parágrafo. Agora o negrito só marca subtítulo quando a maior parte do texto do tamanho do corpo não está em negrito (`corpo_em_negrito`, em `dominio/pagina.py`). Nos dois livros, o corpo é regular.
- **nº 2:** o título aberto juntava qualquer linha seguinte do mesmo tamanho. No sumário do Hard Parts, "Preface … xi" e "1. What Happens…", que eram dois parágrafos porque o "1." abre item de lista, viraram um título só. Agora o item de lista quebra título também (só o da faixa do subtítulo, depois do N1 da pós-auditoria).
- **nº 5:** teste da folga de 0,5 pt abaixo do corpo (10 pt é título com corpo de 10,5; 9,9 não); **9 a 12:** uma função só para o nome da fonte (`_fonte_casa`), constante própria para a folga (`FOLGA_DO_SUBTITULO`), o filtro de letra visível calculado uma vez e o comentário citando este ADR.
- A divisão em capítulos saiu de `blocos.py` para `dominio/capitulos.py`, para o arquivo caber nas 400 linhas do ADR-0001.

Correção da code-audit (2026-11-01): **A1**, o título continuava por cima do vão de parágrafo. No sumário do Hard Parts (p. 12), "A. Concept…", "B. Architecture…", "C. Trade-Off…" e "Index", em negrito de 12 pt a 2 entrelinhas um do outro, eram quatro parágrafos e saíam num título só de 537 caracteres; a correção nº 2 da revisão só cobria o item numérico. Agora o título quebra no vão de parágrafo (1,35 entrelinha), como o parágrafo. Sem entrelinha medida (nenhum par de linhas de parágrafo), o vão não tem régua e o título segue junto, como antes. Medido: o Competente saiu idêntico segmento a segmento; no Hard Parts, só a p. 12 (+3 títulos). A auditoria pediu também um teste para o filtro de letra visível do negrito (o espaço em fonte comum entre palavras em negrito), que nenhum teste prendia.

Correção da pós-auditoria (2026-11-01): **N1**, as duas regras (item de lista e vão) valiam para todo título, mas a evidência delas é toda negrito de 12 pt, na faixa do subtítulo. No título grande, "CAPÍTULO 1", uma linha em branco e "O começo" virava dois títulos e, como o corte de capítulo abre capítulo em todo título do tamanho do capítulo, dois capítulos, o primeiro vazio; "Arquitetura de software" / "— as partes difíceis" também se partia. Agora só o título abaixo de 1,2 vez o corpo quebra como o parágrafo; o grande volta ao que era (muda de tamanho ou de página). Sem a escala pela fonte da primeira versão do A1: na faixa do subtítulo ela fica entre 0,95 e 1,2 e não mudava nada. Medido: os dois livros saíram idênticos segmento a segmento à versão do A1. Sem correção, observado pela pós-auditoria: o `_medir` mede a entrelinha sem as linhas de subtítulo em negrito, o que só pode mexer na moda da entrelinha; nos dois livros, nada mudou.

Ficam como limite (o verbete do glossário, que ficava abaixo do piso e colado na definição, foi resolvido em "Verbete em negrito abaixo do corpo"):
- o negrito que não vem no nome da fonte (o falso negrito desenhado com contorno, `Tr 2`, ou a família TeX `CMBX`) não é reconhecido, e o subtítulo continua colado;
- uma linha inteira de ênfase em negrito no meio do parágrafo o partiria em três; não apareceu nos livros medidos. A guarda óbvia (a linha de antes fechou a frase) quebraria os 36 subtítulos do apêndice do Competente, que vêm depois de linha terminada em URL (revisão nº 3);
- um PDF sem título grande em 3 páginas ou mais, como um artigo com o título só na primeira, passa a cortar capítulo em cada subtítulo em negrito do corpo, onde antes saía um capítulo só (revisão nº 4);
- o subtítulo com um glifo de fonte de reserva (aspa curva, seta, travessão de outra fonte) não é todo negrito e continua colado (revisão nº 7); e a regex só conhece o estilo por extenso depois de `-` ou `,`: abreviação (`-Bd`, `-Blk`, `-Sb`) e nome com espaço (`Arial Bold`, de `#20`) ficam de fora (revisão nº 8);
- o nível sai da ordem dos tamanhos no livro todo, até o `h6`: no Competente, a seção de 12 pt e o subtítulo de 10,5 caem os dois no `h6`. O ouvido não percebe; a tela perderia a hierarquia.

Próximo ciclo (revisão em xhigh, medidos, sem correção ainda):
- **Duas colunas:** a linha visual junta tudo o que está na mesma altura da página e descarta as caixas do pdfminer. Página em duas colunas sai intercalada linha a linha: no Hard Parts, é o índice remissivo (11 das 15 suspeitas); num artigo em duas colunas, seria o corpo.
- **Nota de rodapé que não é nota:** das 337 notas do Competente, 3 são rodapé numerado; o resto é legenda (56), bibliografia e rótulo espaçado, e tudo sai como `aside epub:type="footnote"`. A bibliografia ainda oscila entre nota e parágrafo, com o tamanho na beira de 0,85 do corpo.
- **Pedaço da esquerda decide o tamanho:** depois da correção nº 2, o tamanho da linha visual é o do pedaço mais à esquerda; uma capitular grande ao lado do corpo faria a linha inteira virar título. Sem capitular nos dois livros.

### Verbete em negrito abaixo do corpo (2026-11-02)

No glossário do Competente (p. 466 a 480), o verbete vem em negrito de 9,5 pt na margem (x = 54), e a definição, em 9,5 pt comum, recuada para x = 66,6. Abaixo do piso do subtítulo, o verbete era parágrafo como a definição e entrava colado nela: "Tokenizador A parte do modelo que quebra o texto…". O ouvinte não ouvia onde o termo acabava.

Medido antes da regra, nas linhas visuais todas em negrito e do tamanho do parágrafo que sobram depois da paginação:
- **Competente (148):** os 146 verbetes, cada um numa linha só, e 2 linhas no meio de referência do apêndice, onde o título da obra vem em negrito (p. 486, depois de "Procee-"; p. 493, depois de "(EMNLP 2024).").
- **Hard Parts (97, de 179 linhas do pdfminer):** cerca de 60 rodapés de seção que a paginação não tirou (no pé, em 1 ou 2 páginas: "Sysops Squad Saga: …", "| Preface"), cerca de 36 cabeçalhos de tabela ("Table Responsibility", "Component Namespace") e "Revision History for the First Edition", na página de direitos. A medição do subtítulo chamava os 1.401 de "rótulos de figura"; eram quase todos rodapé de página.

O Mateus escolheu entre três formas, medidas de ponta a ponta nos dois livros:

| Forma | Competente | Hard Parts | Por que não |
|---|---|---|---|
| **Parágrafo próprio** (escolhida) | os 146 verbetes separados; mais nada muda | 52 pausas novas, mesmas palavras; 24 junções e 18 suspeitas | — |
| Título pequeno (`h6`) | igual no áudio; 602 → 748 títulos | 65 títulos novos (rodapés e cabeçalhos de tabela); 24 suspeitas de capitular perdida; "Revision History…" vira título, para a corrente da página de direitos e o histórico de revisões volta a ser lido | piora o Hard Parts |
| Termo com dois-pontos ("Tokenizador: A parte…") | um parágrafo só, pausa menor | o ":" entra no cabeçalho de tabela e no rodapé colado | inventa pontuação que o livro não tem |

Regra, em `dominio/blocos.py`, só num livro de corpo regular (`negrito_destaca`):
- o parágrafo aberto por linha toda em negrito é verbete, e a primeira linha comum abre parágrafo novo: é onde o termo acaba e a definição começa. O verbete de duas linhas em negrito segue um parágrafo só;
- o verbete abre parágrafo depois de frase fechada, como o recuo: quando sai da margem do parágrafo aberto, ou, se o parágrafo tem uma linha só e não é ele mesmo negrito, em qualquer margem. Depois de outro negrito, segue: o verbete de duas linhas com ":" no fim da primeira ("RAG:" / "Retrieval Augmented Generation") e o quadro todo em negrito pequeno ficam num parágrafo só (correção da revisão). A definição de uma linha só ("Prompt", p. 475) não tem margem de corpo, e voltar à margem nela é, no parágrafo comum, a segunda linha dele. Na margem do parágrafo de várias linhas, a linha em negrito segue nele: é o título da obra no meio da referência (p. 493, "…(EMNLP 2024)." e "Proceedings of … Lan-" + "guage"). Sem frase fechada, segue sempre (p. 486, "Procee-" + "dings");
- o verbete fecha a retomada como o título e a linha de tabela: ele não fecha frase, e a linha em minúscula depois de uma nota colaria nele ("Tokenizador a parte…") ou no parágrafo de antes dele. Nenhum caso nos dois livros. Diferente do título, o verbete passa pela retomada quando começa em minúscula (limite abaixo).

A pista da code-review ("a linha toda em negrito sempre fecha o bloco aberto") partia as duas referências do apêndice; a versão só com a linha comum depois do verbete perdia "Prompt caching", que vem depois de uma definição de uma linha só.

Ponta a ponta (`importar-pdf`, `preparar` e `montar`; o Hard Parts, em inglês, com `montar --original`):

| Livro | Títulos | Parágrafos | Segmentos | Limpeza | Montado |
|---|---|---|---|---|---|
| *Competente o Suficiente* | 602 (igual) | 3.990 → 4.136 (+146, os verbetes) | 4.937 → 5.083 | igual: 1 remoção, 0 junções, 0 suspeitas | 4.936 → 5.082 segmentos, 336 notas; epubcheck limpo |
| *Hard Parts* | 387 (igual) | 2.785 → 2.837 (+52) | 3.261 → 3.313 | 7 remoções iguais; 19 → 24 junções e 14 → 18 suspeitas | 3.235 → 3.282 segmentos; epubcheck limpo |

Nos dois livros montados, a sequência de palavras é a mesma de antes (154.385 e 113.664 palavras): a regra só acrescenta pausas. No Hard Parts, o cabeçalho de tabela sai separado das linhas, e o rodapé de seção que a paginação não tirou sai separado do texto da página seguinte, onde antes colava. Ficam colados, como antes, 9 cabeçalhos de tabela cuja linha de cima não fecha a frase: os 7 "Ratings" do capítulo 12, logo depois da legenda ("Table 12-2. Ratings for the Epic Saga(sao) Epic Saga(sao) pattern Ratings…"), e os 2 repetidos no alto das p. 39 e 197, na virada de página, depois da última linha da tabela ("…Payments processed for billings Table Responsibility…"; code-audit e pós-auditoria). As 5 junções a mais são 4 rodapés longos ("Sysops Squad Saga: Understanding Quanta") e 1 cabeçalho de tabela ("Table Proposed data domains" + "customer Customer…"), que o `limpar` cola de novo na continuação em minúscula, como saíam antes; as 4 suspeitas a mais são rodapés curtos ("| Preface", "Interservice Communication Pattern", "Finding Entangled Dimensions", duas vezes) seguidos de minúscula, que antes colavam calados no texto e agora aparecem como "capitular perdida?". O conserto deles é na paginação (o rodapé de seção curta, já registrado na primeira regra). Capítulos (23 e 22) e o sumário `nav` não mudaram.

Mutantes nas linhas novas. Na primeira rodada, 11, com 9 mortos e 2 vivos equivalentes: o `negrito` também fora do parágrafo (só o parágrafo o lê) e o fim do verbete pela marca crua da linha (o verbete só existe com o corpo regular). O que tirava a tabela da retomada mostrou um comportamento antigo sem teste, que ganhou o seu. A code-audit plantou 20: 14 mortos, 3 vivos equivalentes (os dois acima e o `negrito` só fora da tabela, que quebra antes) e 3 vivos não equivalentes, que ganharam teste, cada um visto falhar com o mutante plantado: o verbete no pé da página com a definição na seguinte (sem a regra na virada, 42 rodapés do Hard Parts, todos na última linha da página, colam na primeira linha da página nova; 30 deles voltam a se partir uma linha depois, porque o parágrafo colado abriu em negrito, e por isso a conta cai só de 3.313 para 3.301 blocos), o negrito depois de frase aberta (p. 486) e a retomada depois de legenda e código. A pós-auditoria plantou 23 nas linhas corrigidas: 22 mortos e 1 vivo não equivalente, o código fechando a retomada na ordem código → legenda, que também ganhou teste. Os testes de retomada desta mudança ficam em `tests/test_blocos_retomada.py`, para o `test_blocos.py` caber nas 400 linhas.

Ficam como limite, sem caso nos dois livros:
- a definição que termina sem fechar a frase cola nela o verbete seguinte, pela mesma razão das referências;
- no glossário sem recuo, com a definição de várias linhas na margem do verbete, o verbete segue colado na definição de cima, porque, na margem do parágrafo, o negrito segue (p. 493); só a definição de uma linha só separa;
- no parágrafo de uma linha só, comum, que fecha a frase, a linha seguinte toda em negrito e menor que o corpo abre parágrafo, mesmo que seja ênfase que continua o texto;
- o parágrafo menor que o corpo que abre com uma linha toda em negrito se parte na primeira linha comum, mesmo no meio da frase ("Atenção: o modelo não guarda a conversa entre" | "uma chamada e outra…", code-audit); o caso extremo é o negrito que termina em hífen ("Lan-" | "guage"). O `limpar` junta de novo a continuação em minúscula quando a linha de cima não é curta. Medido: os 146 verbetes têm uma linha só, e nenhum parágrafo todo em negrito termina em hífen antes de linha comum;
- o verbete que começa em minúscula ("npm", "embedding") logo depois de nota ou código, com parágrafo interrompido antes, entra nele pela retomada ("…sem fechar embedding O vetor…"). Os 146 verbetes começam em maiúscula. Recusar a retomada para a linha em negrito partiria a referência cuja continuação em negrito vem depois de uma legenda;
- dois verbetes seguidos, sem definição entre eles (a remissão "Prompt injection" / "Injeção de prompt"), saem num parágrafo só, como o verbete de duas linhas;
- o glossário corrido, com o termo em negrito e a definição na mesma linha ("**Tokenizador** A parte…"), não é coberto: a linha visual mista não é negrito, e o termo segue colado.

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
