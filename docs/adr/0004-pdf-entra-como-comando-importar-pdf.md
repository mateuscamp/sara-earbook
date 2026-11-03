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
- **Revisão nº 4:** número de página com fonte maior que a do corpo + 0,5 pt (12 pt com corpo de 10,5) não sai, porque o filtro de fonte protege número e título de capítulo grandes (A1). É falso negativo aceito: o número fica no áudio. Resolvido em "Número de página maior que o corpo" (2026-11-02).

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
- **Duas colunas:** a linha visual junta tudo o que está na mesma altura da página e descarta as caixas do pdfminer. Página em duas colunas sai intercalada linha a linha: no Hard Parts, é o índice remissivo (11 das 15 suspeitas); num artigo em duas colunas, seria o corpo. Resolvido em "Duas colunas" (2026-11-02).
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

### Duas colunas (2026-11-02)

O Mateus quer adaptar livros didáticos para o ouvido, e o primeiro é *Psicopatologia e Semiologia dos Transtornos Mentais* (Dalgalarrondo, Artmed 2008, 438 p., pt-BR), com o corpo em duas colunas. O `importar-pdf` juntava numa linha visual tudo o que estava na mesma altura da página, e as duas colunas saíam intercaladas linha a linha: "Assim, desde Aristóteles, o problema essas experiências são basicamenda classificação está intimamente ligado te semelhantes para todos." (`c004-s0028`, p. 30). O hífen de fim de linha colava pedaços de colunas diferentes. Medido antes da regra (HEAD `e8c727a`): 4.321 segmentos, 1.198 parágrafos que o `limpar` juntava e 226 "capitular perdida?".

**Por que não as caixas do pdfminer.** Elas separam as colunas, mas separam igualmente a célula de tabela e o pedaço da linha justificada partida: dos pares de pedaços na mesma altura, ficam em caixas diferentes 14.166 de 14.177 no Dalgalarrondo, 557 de 564 no Competente e 2.413 de 2.440 no Hard Parts. E a ordem das caixas (`boxes_flow`) mudaria a ordem de páginas de uma coluna só nos dois livros que já estavam bons.

**Decisão: a calha, pelo x das linhas.** O adaptador entrega também onde cada linha termina (`Linha.fim`, o `x1` do pdfminer), e `dominio/colunas.py` põe as linhas da página na ordem de leitura antes de juntar as da mesma altura:
- **calha:** um x que nenhuma linha atravessa, com 10 pt ou mais entre o fim das linhas da esquerda e o começo das da direita (o vão das colunas é de 16 a 40 pt nos livros medidos; o da linha justificada partida, abaixo de 10);
- **faixa:** linhas seguidas, de cima para baixo, que não atravessam a calha. A linha que atravessa (título, quadro de largura cheia) e o vão vertical de mais de 2,5 entrelinhas cortam a faixa. Sem o vão, "Questões de revisão" (p. 30) e a epígrafe da abertura do capítulo 3 (p. 31) entravam na coluna da esquerda. O vão não corta quando uma coluna só passa por ele, com a outra já acabada acima, e a mesma coluna continua embaixo com 3 linhas ou mais: aí ele é subtítulo ou quadro dela (correção da revisão, abaixo);
- **duas colunas** quando cada lado tem 3 linhas ou mais, 30% ou mais da largura da faixa, e é **texto corrido**: em 40% ou mais das linhas seguidas do lado, a de baixo continua a de cima (começa em minúscula ou vem depois de hífen). É o que separa a coluna da tabela de chave e valor ("Communication | Synchronous", "Component | Namespace | Responsibility"), que também tem calha;
- **ordem:** a coluna da esquerda inteira, depois a da direita, e cada coluna passa pela mesma regra: o destaque de margem dentro da coluna sai do texto ao lado dele. O resto da página segue como antes;
- **margem da coluna:** o `x` da linha de coluna passa a contar da margem dela (o x mais comum do lado). O `blocos` compara o recuo com a margem do parágrafo, e a página par e a ímpar têm margens diferentes (66 e 301, 46 e 245): o parágrafo que vira da coluna da direita de uma página para a da esquerda da seguinte se partiria a cada fim de frase;
- **virada de coluna:** a linha que sobe na página é a primeira da coluna seguinte, e o `blocos` a trata como a virada de página: só quebra no item de lista ou na frase fechada seguida de maiúscula, e, se o parágrafo segue, a margem dele passa a ser a da coluna nova (correção da revisão, abaixo).

Medido num protótipo, nas linhas que o pdfminer entrega: no Competente, nenhuma página muda de ordem; no Hard Parts, o índice remissivo (p. 443–459) e duas tabelas de vantagens e desvantagens com célula que quebra linha (p. 412 e 429), que saíam intercaladas ("Highly suitable for microservices architectures Requires contract coordination with data product quantum…") e passam a sair coluna a coluna; no Dalgalarrondo, 378 de 438 páginas. A calha de 8 a 12 pt, 3 ou 4 linhas por lado, 25% a 35% da largura e o vão de 2 a 3 entrelinhas não mudam o Competente nem o Hard Parts (com 35%, a p. 412 sai da lista). O limiar que decide é o da continuidade: com 30%, a tabela da p. 144 do Competente ("O que foi medido | Número | Que tipo de número", com célula que quebra) passaria a ser lida coluna a coluna, o que estraga a leitura; com 50%, o glossário do Dalgalarrondo fica intercalado em mais 14 páginas.

O Mateus aprovou a decisão inteira ("Sim aos três"): o critério com continuidade de 40%, a leitura coluna a coluna das tabelas das p. 412 e 429 do Hard Parts, sem restringir a regra, e a bibliografia do Dalgalarrondo ainda intercalada, que fica para o `adaptar`.

Ficam como limite:
- **colunas de verbete que começa em maiúscula**: a bibliografia do Dalgalarrondo (p. 416–431: "BERGSON, H.", "São Paulo:") e algumas páginas do glossário têm continuidade de 0,33 a 0,4 e continuam intercaladas. No protótipo, 43 páginas do Dalgalarrondo ainda têm alguma faixa larga recusada (bibliografia, quadros e tabelas);
- **tabela de célula curta** (chave e valor) continua linha a linha, como antes: Competente p. 144 e 377–380, as tabelas do Hard Parts e os Quadros do Dalgalarrondo. É o certo para o ouvido. A tabela de registro com célula que quebra linha, como a p. 144, seria lida coluna a coluna se passasse do limiar;
- **destaque de margem** (pull quote, fora deste ciclo): vira parágrafo próprio, antes ou depois do pedaço de texto ao lado dele, quando a frase fecha antes dele (69 viradas de coluna trocam de tamanho, o destaque de 9 pt para o texto de 10). Quando a frase do texto atravessa o destaque, ele ainda entra no meio da frase (p. 250: "O corpo é um dos principais palcos" | destaque | "de nossas vidas");
- **página de uma coluna com figura ao lado**: rótulos de figura com 3 linhas ou mais que se continuam virariam coluna; nenhum caso nos três livros;
- **coluna sem a vizinha**: a página em que o texto termina na coluna da esquerda, sem nada à direita, não tem calha, e o `x` dela continua contado da borda da página. O parágrafo que vem da coluna da direita da página anterior se parte nos fins de frase dela.

Ponta a ponta (`importar-pdf` e `preparar`), contra o HEAD `e8c727a`, já com as correções da revisão:

| Livro | `importar-pdf` | `preparar` |
|---|---|---|
| *Dalgalarrondo* | 7,4 → 8,6 s; títulos 586 (igual); parágrafos 3.577 → 3.697; notas 158 → 171; hífen tirado 4.751 → 10.890, mantido 127 → 191 | segmentos 4.321 → 4.454; **junções 1.198 → 19**; capitulares devolvidas 4 → 9; suspeitas 239 → 197 ("capitular perdida?" 226 → 194; linha curta 13 → 3). Montado: 4.434 segmentos; epubcheck limpo |
| *Competente o Suficiente* | igual | `segmentos/`, `limpos/`, `limpeza.json` e `livro.json` idênticos (só o nome do EPUB de origem muda) |
| *Hard Parts* | títulos 387 → 401; parágrafos 2.837 → 2.855; hífen tirado 1.265 → 1.281, mantido 43 → 44 | mudam só 3 capítulos: o índice (c022, 47 → 67 segmentos) e as duas tabelas aprovadas (c017, p. 412, e c018, p. 429). O `limpeza.json` é idêntico fora deles |

O hífen tirado dobra no Dalgalarrondo porque o hífen da coluna da esquerda ficava no meio da linha visual, colado ao pedaço da coluna da direita, e não contava como quebra. Das 19 junções que sobram, 6 são parágrafos que o `limpar` emenda, como em livro de uma coluna; 12 ficam em regiões de quadro, tabela ou lista (c022, c027, c029, c030 e c032); e 1 é o cabeçalho de página colado ao texto (c001, "Prefácio da 1a edição 15").

No Hard Parts, as p. 412 e 429 saem como cabeçalho e lista ("Synchronous advantage" / "Credit approval is guaranteed to start before customer request ends"). O índice sai em ordem: cada letra abre a sua seção, e os verbetes vêm em ordem alfabética. Antes, as letras se colavam ("F G") ou se juntavam a um verbete da coluna da direita ("B stateless choreography, 313"). As "capitular perdida?" do índice vão de 11 a 16, pela mesma causa: a letra da seção é título, e o primeiro verbete começa em minúscula. Agora é uma por letra cujo primeiro verbete começa em minúscula; antes, a letra colada a um verbete escapava da regra.

Correções da code-review e da code-audit (2026-11-02), cada uma com o teste visto falhar na asserção e aprovadas pelo Mateus ("Os dois (A e B)"):
- **A1, vão numa coluna só:** a coluna da direita acaba cedo, e a da esquerda tem um subtítulo 3 entrelinhas abaixo; o corte no vão mandava o resto da esquerda para depois da direita. A primeira correção (cortar só onde as duas colunas acabam ou começam) estragou a p. 343: o destaque alonga a coluna da direita, e "Questões de revisão" entrava na da esquerda. Em 161 vãos do Dalgalarrondo, o que vinha abaixo era o número do capítulo, o título do quadro e "Questões de revisão", seguidos do quadro de largura cheia. A regra que ficou corta sempre, a não ser que a mesma coluna, a única ativa acima do vão, continue abaixo dele com 3 linhas ou mais. Ela deixa 15 vãos sem corte no Dalgalarrondo, nenhum no Competente nem no Hard Parts, e só muda a ordem da p. 283, para melhor: a tabela do retardo mental passa a sair linha a linha ("RM leve 50 a 69 9 a 12 anos…"). Testes: o vão numa coluna só, o título do quadro depois de colunas desiguais e a epígrafe acima das colunas;
- **A2, pedaço na altura da linha que atravessa:** o pdfminer parte a linha de largura cheia, e o pedaço à direita da calha ia para a coluna da direita. Agora o pedaço colado à linha que atravessa (vão menor que a calha) atravessa com ela. A primeira correção (a altura inteira atravessa) tirava da coluna a linha da outra coluna na altura de um título que só invade a calha (p. 308: "mais nada.”) ALTERAÇÕES DA VOLIÇÃO") e mudava a ordem de 6 páginas (quadros, listas, glossário e bibliografia). Testes: o pedaço colado e a linha da outra coluna na altura de um título;
- **A3, item de lista que vira de coluna:** a margem pela moda da coluna da direita, cheia de itens, era o recuo do item, e o item se partia no ponto. Agora a virada de coluna é decidida no `blocos` (ver "virada de coluna", acima). Medido: das 165 viradas de coluna que quebram parágrafo, 99 não têm recuo; 69 delas trocam de tamanho (o destaque de 9 pt que sai do texto de 10 pt, o subtítulo de 11 pt), e das 30 do mesmo tamanho, 16 são verbete de glossário, 7 são linha da bibliografia, 2 são parágrafo com rótulo ("Valor diagnóstico:") e 1 é a lista de um diagrama. Só 4 partem um parágrafo que continuaria ("Segundo ele, esses estados…"): uma pausa a mais, sem palavra perdida. A margem da coluna fica, para a virada de página, e ganhou teste próprio. Testes: o item de lista que vira de coluna e o parágrafo que vira a página de margem diferente;
- **A4, busca quadrática da calha:** um passe pela página por candidato a calha, recursivo. A página com mais de 200 começos de linha diferentes vai como antes, por altura: a página real com mais começos tem 97 (Dalgalarrondo p. 302). 1.600 linhas em x distintos: 2,4 s → 0,01 s; 200 começos e 6.400 linhas, 1,25 s. Juntar os candidatos por ponto inteiro (a primeira correção) tirava as colunas de 9 páginas do Dalgalarrondo, onde a calha meio ponto à direita parte a faixa e as partes passam no limiar. Teste: a página com mais de 200 começos de linha;
- **lote B:** o `fim` virou campo obrigatório (o padrão infinito escondia o construtor que o esquecesse); os hífens da quebra e `comeca_em_minuscula` foram para `dominio/pagina.py`; a faixa guarda se é de colunas, e a calha escolhida não é recalculada; as docstrings de `CONTINUIDADE` e `LARGURA_DA_COLUNA` passaram a citar a medida do código final.

Contra a primeira versão das colunas, o Competente e o Hard Parts saem idênticos. No Dalgalarrondo, as mesmas palavras vêm com 101 divisões de parágrafo a mais e 5 junções (as viradas de coluna do A3), e só 5 trechos mudam a ordem das palavras, todos dentro de quadro e tabela (c017, c027 duas vezes, c043): os dois do c027 melhoram, e os outros trocam uma célula de lugar numa tabela que já saía embaralhada.

Achados na medição, de outras regras, que a ordem certa deixou à vista:
- **Número de página maior que o corpo:** 193 das 194 "capitular perdida?" que sobram no Dalgalarrondo vêm do número de página em 12 pt (corpo de 10), que a paginação não tira (limite "Revisão nº 4"). Ele vira título no alto de cada página, é lido ("32") e parte o parágrafo que vem da página anterior. Antes da regra das colunas, a causa era a mesma, só que escondida no meio do intercalado.
- **Capitular falsa em português:** as 9 "capitulares devolvidas" do Dalgalarrondo são todas falsas, e na base já eram 4. Depois do número de página que virou título, a pista do ADR-0007 ("a primeira maiúscula sozinha, fora o I") acha o artigo "A" ou "O" de uma frase próxima e o cola no começo do parágrafo em minúscula: "lho, não via" vira "Alho, não via", e "desejo. A resultante" vira "desejo. resultante". O texto fica errado nas duas pontas.

Os dois foram resolvidos em "Número de página maior que o corpo", abaixo, e no ADR-0007, "A letra que abre frase".

### Número de página maior que o corpo (2026-11-02)

No Dalgalarrondo, o número de página tem 12 pt, e o corpo, 10. A primeira regra só olha, na faixa da borda, a linha com fonte de rodapé (até o corpo + 0,5 pt), para não tirar o número de capítulo grande (A1), e por isso o número ficava (limite "Revisão nº 4"). Ele virava título no alto de 402 páginas, era lido ("trinta e dois") e partia o parágrafo que vinha da página anterior. Respondia pelas 194 "capitular perdida?" do livro (193 com o número sozinho; 1 com ele colado ao cabeçalho, "14 Prefácio da 1a edição") e era o gatilho das 9 capitulares falsas.

Medido na faixa da borda dos três PDFs, contando só as linhas que são número:
- **Dalgalarrondo:** 412 números maiores que o corpo + 0,5 pt, todos de 12 pt, a 0,069 do alto e com o número impresso igual à página do PDF. As 26 páginas sem número são a abertura do livro (p. 1–23), aberturas de parte e páginas em branco.
- **Competente e Hard Parts:** nenhum. Os números deles são de 7,5 e 9 pt.
- **Número de capítulo:** fica fora da faixa nos três (60 pt no Dalgalarrondo, 30 pt no Competente, 12 e 14 pt no Hard Parts).

**Decisão: o número grande forma a sua própria sequência.** O número maior que o corpo + 0,5 pt também passa pela regra do número de página, mas a sequência dele se conta só entre os números do mesmo tamanho. Ele sai quando os números daquele tamanho, sozinhos, seguem a paginação com o mesmo deslocamento em 3 páginas ou mais. O número de rodapé, até o corpo + 0,5 pt, continua contado junto, de qualquer tamanho, como hoje. A linha repetida continua só com fonte de rodapé: "Capítulo N" em 20 pt no alto de três aberturas fica (A1). O "3" em 48 pt e o "IV" em 24 pt de uma abertura de capítulo também ficam, porque sozinhos no tamanho deles não fazem sequência; são os testes do A1, que continuam valendo.

O que se perde: a seção numerada uma por página, com o número no alto num tamanho só dela e acompanhando a paginação (soneto, exercício, ficha), passa a sair como número de página e não é lida. Não há caso nos três PDFs. Hoje, o mesmo já acontece quando esse número tem o tamanho do corpo.

Medido depois do código, junto com a regra do ADR-0007 ("A letra que abre frase"), contra o HEAD `50cd35b`, nas pastas `*-base-pagina` e `*-pagina` de `livros/trabalho/`. O protótipo, numa cópia descartável, tinha dado os mesmos números:

| Livro | `importar-pdf` | `preparar` |
|---|---|---|
| *Dalgalarrondo* | número de página 0 → 412; títulos 586 → 222: saem os 402 títulos só de número, e o número sai também do começo de 6 títulos ("12 Prefácio à 2a edição"). Os 41 títulos de número que ficam são números de capítulo. Parágrafos 3.697 → 3.479; hífen tirado 10.890 → 10.962 | segmentos 4.454 → 3.872; junções 19 → 19; capitulares devolvidas 9 → 0; suspeitas 197 → 3 ("capitular perdida?" 194 → 0; ficam as 3 linhas curtas) |
| *Competente*, *Hard Parts* | igual: o EPUB só muda no `dc:identifier`, sorteado a cada importação | `segmentos/`, `limpos/`, `limpeza.json` e `livro.json` idênticos (só muda o nome do EPUB de origem) |

O que acontece com o texto que vinha depois dos 402 números que eram título:
- **195 emendas certas:** o parágrafo partido pela página volta inteiro. Em 64 delas, o hífen da virada também volta a juntar a palavra ("que com- 24 preende" → "que compreende"). Em mais 8, volta certa a palavra que a capitular falsa tinha trocado ("como uma “forma- 37 Ação de compromisso”" → "como uma “formação de compromisso”"). Uma fica com o hífen no meio, pela regra do composto (B2): "não-correspon- 410 didos" → "não-correspon-didos".
- **100 parágrafos novos,** quando a frase fecha no pé da página, e **79 títulos.**
- **21 emendas no título de um quadro.** Quando a página termina num Quadro ou numa tabela (que viram nota, defeito fora deste ciclo), a continuação em minúscula retoma o título do quadro: "Semiotécnica simplificada da afasia nica, por conflitos interpessoais ou por imitação.". Na base, o mesmo pedaço já era um parágrafo solto depois do número lido ("239. nica, por conflitos…"). Nos dois casos, o começo da frase fica antes do quadro. O conserto é o do Quadro.
- **6 junto ao destaque de margem repetido,** também fora deste ciclo, e 1 "(continuação)" de tabela.

O Mateus aprovou as duas regras, esta e a do ADR-0007 ("Sim, as duas"), e aceitou as 21 emendas no título do quadro até o ciclo do Quadro.

Ficam como limite conhecido:
- **o cabeçalho de duas páginas:** "Prefácio da 1a edição", em 9 pt no alto das p. 14 e 15, não chega às 3 páginas da linha repetida e fica, como antes. Sem o número que o colava num título ("14 Prefácio da 1a edição"), ele entra no meio da frase partida pela página: "Bernard e Si- Prefácio da 1a edição mone Trouvé (1977)". As junções continuam 19 porque esta entra e uma sai: a de `c011`, "Sullivan (1983) afirmava que" + "o entrevistador desempenha", que é um dos 21 casos do quadro, abaixo. O começo da frase ("senciais da clínica…") vai para o título do quadro, e "o entrevistador desempenha…" fica depois do quadro, num parágrafo próprio;
- **a continuação emendada no título do quadro:** quando a página termina num Quadro ou numa tabela, que viram nota, a continuação em minúscula da página seguinte retoma o título do quadro, e não o parágrafo de antes dele ("Semiotécnica simplificada da afasia nica, por conflitos interpessoais ou por imitação.", p. 239; "Exemplos de formulação diagnóstica satisfatoriamente o objeto pesquisado…", p. 44). Some com o conserto do Quadro, que precisa tirar o quadro do fluxo do parágrafo. Resolvido em "Quadro no lugar" (2026-11-03), que contou 33 casos.

Registrados pela code-review, sem correção, porque não têm caso nos três PDFs:
- **o tamanho exato:** a sequência do número grande se conta pelo tamanho arredondado a 0,1 pt. Um PDF com o número entre 11,9 e 12,0 pt parte a sequência em duas, e a parte com menos de 3 páginas fica no áudio. No Dalgalarrondo, os 412 têm 12,0;
- **sem a altura:** o número grande do alto e o do pé se contam juntos, e a altura não é cobrada. Um número de tabela, maior que o corpo, que acompanhe a paginação em 3 páginas na faixa da borda sairia como número de página.

### Escuta do Dalgalarrondo (2026-11-03)

O Mateus ouviu `dalgalarrondo-pagina.pronto.epub` no ElevenReader. Ouviu o capítulo "3" do começo até o minuto 5:29, o que passa do fim do item "2. Normalidade ideal". As palavras dele: "Está perfeito. A única questão é essa que eu já tratei anteriormente."

- **Ordem e número de página:** a lista de "1. Psiquiatria legal ou forense" a "6. Prática clínica" sai inteira, sem o "32" no meio. Isso confirma as duas colunas e o número de página na escuta.
- **Defeito:** o destaque de margem lido duas vezes ("O conceito de saúde e de normalidade em psicopatologia é questão de grande controvérsia", `c005-s0008` e `c005-s0009`). Vai para um ciclo próprio na limpeza.
- **Sotaque:** no meio do capítulo, a voz passou a ler com sotaque de Portugal e, no fim, voltou ao do Brasil. Ele trocou de voz, e o sotaque continuou. O EPUB declara `pt-BR` no OPF e nas 88 marcas de língua dos XHTML, sem outra língua em trecho nenhum, então o defeito é do ElevenReader.
- **O minuto:** o ElevenReader mostra o tempo do capítulo, não o do livro, e o roteiro dava o do livro (37 a 41). O capítulo dura 10:12 para 1.408 palavras. O trecho, de 755 palavras, coube até 5:29. São ~138 palavras por minuto, contra as 160 do `earbook minuto`. A partir de agora, o roteiro dá a frase de início e a de fim e o minuto aproximado do capítulo (skill `traduzir-livro`, passo 9).

### Destaque de margem na virada de coluna (2026-11-03)

O defeito da escuta acima é o destaque de margem. No Dalgalarrondo, ele tem 9 pt, numa coluna
estreita na margem (p. 31: x 46 a 123), e o texto de 10 pt ao lado estreita para dar lugar a ele
(x 143 a 228). O `colunas` já o lê antes ou depois do texto ao lado ("Duas colunas"). Mas a
virada de coluna é como a de página: só abre parágrafo na frase fechada seguida de maiúscula. O
destaque fecha a frase, e o texto que ele interrompe continua em minúscula, por isso ele colava:
- **no começo da continuação:** "O corpo é um dos principais palcos" | "O corpo é um dos
  principais palcos de nossas vidas. Lugar de dor… desejo. de nossas vidas. Lugar de dor…"
  (p. 250);
- **no fim do texto,** quando a frase ainda não fechou: "…Só após o agravamento Geralmente a
  desorientação ocorre…";
- **no meio da palavra:** "As ilusões ocor-" | destaque | "rem basicamente…".

Medido no HEAD `0038af9`: 221 segmentos do Dalgalarrondo repetem dentro de si 8 palavras
seguidas. Os 7 do Competente e os 12 do Hard Parts são repetição do próprio texto, não destaque.

**Decisão:** na virada de coluna, a linha cuja letra difere da do parágrafo aberto em mais de 0,5
pt (`DIFERENCA_DE_TAMANHO`, a folga do título) abre parágrafo novo. O destaque vira parágrafo
próprio, e o texto em volta dele fica em dois. Quando o destaque sai, o `limpar` emenda os dois
(ADR-0008, "Destaque de margem repetido").

Alternativa recusada: abrir parágrafo em toda linha que muda de tamanho, e não só na virada.
Pegaria também o destaque que fica abaixo do texto, na mesma coluna, mas muda o Competente (+177
parágrafos) e o Hard Parts (+21), que não têm destaque.

Medido depois do código, contra o HEAD `0038af9`, nas pastas `*-destaque` de `livros/trabalho/`:

| Livro | `importar-pdf` | `preparar` |
|---|---|---|
| *Dalgalarrondo* | parágrafos 3.479 → 3.747 | segmentos 3.872 → 4.140; destaques, junções e suspeitas no ADR-0008 |
| *Competente*, *Hard Parts* | igual: o XHTML do EPUB é idêntico | `segmentos/`, `limpos/`, `limpeza.json` e `livro.json` idênticos (fora a origem) |

A quebra nova separa também o subtítulo de 9 pt que vinha colado num pedaço de texto fora de
ordem ("As alucinações imagem perceptiva real…", "Constituição corporal mentos são…"). O
pedaço continua fora de ordem, agora depois de uma linha curta: são 4 das 6 "capitular
perdida?" novas, sem pista que mude o texto.

O Mateus aprovou junto com a regra do `limpar` ("Aprovar").

Fica como limite o destaque colado sem virada de coluna, abaixo do texto na mesma coluna: uns 15
no Dalgalarrondo (`c019-s0048`, `c011-s0025`). Vai, com os outros destaques que ficam, para o
`adaptar` (ADR-0008).

### Quadro no lugar (2026-11-03)

O Dalgalarrondo tem 81 quadros: 79 "Quadro N.N" e 2 "Tabela N.N". O rótulo vem numa linha
própria de 12 pt (o corpo tem 10), a legenda em 9 pt e o conteúdo em 8 e 9 pt. O `blocos` lia o
rótulo como título, a legenda e o cabeçalho de coluna (9 pt) como parágrafo e o conteúdo (8 pt)
como nota. O `montar` leva a nota para "Notas", no fim do capítulo (ADR-0005), longe do texto.

Medido no HEAD `4135b24`, nas pastas `*-base-quadro` de `livros/trabalho/`:
- **o conteúdo em "Notas":** os 81 quadros dão 334 blocos, 206 parágrafos e 128 notas. Com mais
  4 notas de quadro das p. 275 e 324 (ver os limites), são 132 das 171 notas do livro;
- **a frase partida:** em 33 das 64 regiões de quadro (rótulos seguidos contam como uma), o texto
  de antes não fecha a frase e a continuação vem em minúscula depois. Em 29, a continuação se
  emendava no quadro: 28 pela retomada do `blocos` (a legenda ou o cabeçalho de 9 pt era o
  parágrafo aberto quando a nota interrompia) e 1 pela junção do `limpar`. Exemplos: "Exemplos
  de formulação diagnóstica satisfatoriamente o objeto pesquisado…" (p. 44) e "Semiotécnica
  simplificada da afasia nica, por conflitos interpessoais…" (p. 239). Nas outras 4, ela ficava
  num parágrafo solto em minúscula, depois do quadro. A seção "Número de página maior que o
  corpo", acima, contava 21, só as emendadas no título;
- **o Competente e o Hard Parts:** nenhum rótulo em letra de título. No Competente, 49 das 337
  notas são legendas "Figura N.N" em 8,5 pt. No Hard Parts, "Table 1-1." (76) e "Figure 1-1."
  (261) vêm no tamanho do corpo, e as 10 notas são direitos autorais, rótulos de diagrama e 1
  rodapé.

**Decisão**, em três partes, num protótipo antes do código:
1. **Como se reconhece: pelo rótulo e pela letra.** O quadro abre na linha em letra de título
   (1,2 vez o corpo ou mais) que começa com "Quadro" ou "Tabela" e um número
   (`_ROTULO_DO_QUADRO`). Ele segue enquanto a letra não é a do corpo (mais de 0,5 pt de
   diferença) nem a de título, e outro rótulo também o continua ("Quadro 8.2" na página
   seguinte, a continuação). A primeira linha do tamanho do corpo, ou o primeiro título que não
   é rótulo ("Questões de revisão", número de capítulo), o fecha. Dentro dos quadros do
   Dalgalarrondo há linhas de 8, 9 e 11 pt, nunca de 10. A menção no corpo ("Tabela 19.1, são
   apresentados…", p. 223) tem a letra do corpo e não abre quadro.
2. **Na pasta de trabalho, sem papel novo.** O rótulo sai `<hN>`, como antes, e a legenda e o
   conteúdo saem `<p>`. A letra menor do quadro deixa de ser nota, e cada linha do quadro vira
   um parágrafo, separada da seguinte pelo vão, como no corpo. O contrato da pasta de trabalho e
   os papéis do `preparar` não mudam.
3. **Onde entra na leitura: depois da frase que ele interrompe.** Os blocos do quadro esperam e
   entram antes do próximo título ou do próximo parágrafo do corpo, ou maior, que não começa em
   minúscula. A continuação em minúscula retoma o parágrafo de antes do quadro, como a nota no
   meio do parágrafo (Competente p. 33).

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| **Rótulo + letra** (escolhida) | só o Dalgalarrondo muda; usa o que a `Linha` já tem | o quadro sem rótulo, ou com rótulo do tamanho do corpo, não é reconhecido | — |
| Pela moldura (o retângulo do pdfminer) | pega o quadro sem rótulo | o destaque e as "Questões de revisão" também têm fundo (p. 44); o adaptador passaria a entregar retângulos, e a `Pagina` mudaria | não separa o quadro do resto |
| Só pela letra menor | dispensa o rótulo | pega o destaque, a legenda, as "Questões de revisão" e o versalete de 7,4 pt, e muda o Competente (legendas de 8,5 pt) | muda os livros que já estavam bons |
| Papel novo `quadro` na pasta de trabalho | o `adaptar` acharia o quadro pelo papel | o `preparar` precisaria de uma marca no XHTML. O `<aside data-type="sidebar">` mudaria os 3 do Learning DDD (o `limpos/` e a tradução ficariam velhos), e uma marca própria seria convenção de um comando que ainda não tem ADR. O `<aside>` arrisca o ElevenReader pular o quadro (ADR-0005) | fica para o ADR do `adaptar`, se ele precisar |
| O parágrafo retomado volta à posição dele, antes do quadro (o mecanismo da nota) | uma regra a menos | quando um destaque parte a continuação ("os pri-" \| destaque \| "meiros três minutos", p. 70), o resto da frase caía depois do quadro: 3 destaques voltavam a ser lidos duas vezes, e a palavra ficava partida | perde o que o destaque ganhou |

Medido e recusado também: partir o parágrafo do quadro quando a letra muda (9 pt para 8 pt).
Separa só 2 blocos no livro inteiro.

Medido depois do código, contra o HEAD `4135b24`, nas pastas `*-quadro` de `livros/trabalho/`.
O Dalgalarrondo sai idêntico ao protótipo:

| Livro | `importar-pdf` | `preparar` |
|---|---|---|
| *Dalgalarrondo* | parágrafos 3.747 → 4.524; **notas 171 → 44**; hífen tirado 10.962 → 10.973 | segmentos 4.140 → 4.790; destaques 238 → 242; junções 193 → 237; suspeitas 9 → 23. Montado: 3.708 → 4.310 segmentos; **notas em "Notas" 170 → 43** |
| *Competente*, *Hard Parts* | igual: o XHTML do EPUB é idêntico | `segmentos/`, `limpos/`, `limpeza.json` e `livro.json` idênticos (fora a origem) |
| *Huxley*, *Tides*, *Learning DDD* | — | idênticos: as traduções não ficam velhas |

- **As 33 frases voltam inteiras,** e o quadro vem logo depois do parágrafo. "…capaz de
  identificar satisfatoriamente o objeto pesquisado (de certo modo, mais próximo da “verdade”)."
  vem antes do Quadro 5.1. O caso de Sullivan (`c011`, abaixo, no limite do cabeçalho de duas
  páginas) sai num parágrafo só.
- **Nenhuma palavra se perde:** contando o `limpos/` e os destaques tirados, são 167.765 → 167.749
  palavras. A diferença são 16 palavras partidas que voltam inteiras ("pri-" + "meiros", "es-" +
  "senciais", "hu-" + "mor", "inves-" + "tigar"): 11 pelo hífen do fim da linha e 5 pela junção.
- **Destaques:** os 238 continuam saindo, e saem mais 4, que o quadro partia ou separava do texto
  ("Denomina-se amnésia…", "Somatização é um termo…", "Sempre que o examinador…",
  "Denomina-se alexitimia…").
- **Junções:** 199 fora do quadro (+6, as metades de frase que o destaque tirado deixa lado a
  lado) e 38 entre linhas do mesmo quadro, a célula que quebra linha. Nenhuma junta quadro e
  corpo.
- **As 14 suspeitas novas** estão todas dentro de quadro: célula curta sem pontuação seguida de
  minúscula ("sensorial", "motora", "vida (%)"). Ficam no texto e só aparecem no registro.
- **1.058 segmentos** são de quadro: cada linha dele é uma pausa, onde antes havia uma nota de até
  27 linhas coladas.

Para caber nas 400 linhas do ADR-0001, o `blocos.py` foi dividido pelo assunto, sem mudar o
comportamento: o dicionário do hífen da quebra foi para `dominio/hifen_da_quebra.py`, e as
regras do quadro (o rótulo, a letra do quadro e a linha que o solta) para `dominio/quadro.py`. A
letra de título (`RAZAO_DO_TITULO`) e a folga do tamanho (`DIFERENCA_DE_TAMANHO`) passaram para
`dominio/pagina.py`, para o `quadro` não importar o `blocos`, que o importa. O estado (se a
linha está num quadro e os blocos que esperam) continua no `blocos`.

O Mateus aprovou a decisão inteira e os limites abaixo ("Aprovar").

Ficam como limite:
- **4 pedaços de quadro continuam em "Notas",** por defeitos de outras regras:
  - na p. 275, há texto escondido debaixo do Quadro 22.4 ("24" em 60 pt e "A inteligência e" em
    22 pt). Ele se junta à linha do quadro na mesma altura, vira título do tamanho do capítulo,
    abre um capítulo falso (`c026`, 16 segmentos, já na base) e fecha o quadro. Ficam 3 notas;
  - na p. 324, a tabela do Quadro 29.1 tem célula que quebra linha, e o `colunas` a lê como duas
    colunas. A coluna da direita vem depois do texto do corpo e fica fora do quadro: 1 nota;
- as 14 suspeitas e as 38 junções dentro de quadro, acima;
- o quadro desce para depois do destaque ou da epígrafe de 9 pt e do parágrafo em minúscula que
  vierem antes da frase acabar. É de propósito;
- o quadro sem rótulo, o rótulo em inglês ("Table", "Box") e o rótulo do tamanho do corpo não são
  reconhecidos. Nos livros medidos, nenhum rótulo em inglês vem em letra de título;
- o quadro é lido como lista de linhas ("Eixo 1. Diagnóstico do Transtorno Mental Esquizofrenia
  paranóide…"). Virar prosa é o trabalho do `adaptar`;
- **o destaque de 9 pt logo depois do quadro entra no quadro:** a extensão é só pela letra, e o
  destaque que vem antes da continuação do corpo vira o último bloco do quadro e espera com ele,
  longe do texto que repete. Medido: 1 caso (p. 383, depois dos Quadros 37.2 e 37.3), e ele
  ainda sai, porque os vizinhos seguintes o cobrem. Com um quadro mais longo, ou com o texto
  repetido só antes do quadro, seria lido duas vezes (code-review).

Fica como dívida, sem caso nos livros medidos: **dois mecanismos para a interrupção no meio da
frase.** A nota e o código voltam o parágrafo retomado à posição dele (Competente p. 33), e o
quadro espera até a frase acabar. A legenda seguida de um destaque que parte a continuação teria
o defeito que o quadro tinha no primeiro protótipo: o resto da frase cairia depois da legenda.
Unificar os dois exige medir de novo as legendas do Competente (code-review).

Achados na medição, para a fila da próxima filha, sem correção aqui:
- **subtítulo em versalete de 7,4 pt:** são 39 no Dalgalarrondo ("DELÍRIO DE GRANDEZA (DE
  ENORMIDADE)", "TRANSTORNO DA PERSONALIDADE ESQUIZÓIDE"), que viram nota e vão para "Notas",
  longe da seção que nomeiam. São 39 das 43 notas que sobram;
- **o capítulo falso da p. 275** (`c026`, "24 transgressão ou violência…");
- **a ordem do `colunas` nas p. 324 e 384:** a tabela do Quadro 29.1 lida em colunas no meio do
  corpo, e a lista curta intercalada com o texto ("é classi- 1. perda da memória de fixação").

Correções da code-review e da code-audit (2026-11-03), aprovadas pelo Mateus ("A, B e C"), sem
mudar a saída: os seis livros saem idênticos à medição acima.
- **A1, a fronteira do quadro:** sem a quebra entre a última linha do quadro e a primeira do
  corpo, o corpo colava no quadro quando vinha logo abaixo, sem vão e depois de linha sem frase
  fechada. Um mutante que a tirava mudava 5 blocos do Dalgalarrondo ("…Cultura Assim, desde
  Aristóteles…", p. 29) e passava pela suíte. O comportamento já existia e ganhou teste, visto
  falhar na asserção com o mutante plantado;
- **A2, a retomada dentro do quadro:** a guarda que não deixa a linha do quadro retomar o texto
  do corpo só faz diferença com código monoespaçado dentro do quadro, que não aparece nos livros
  medidos. Ela também ganhou teste, visto falhar na asserção com o mutante da guarda;
- **lote A, do resto da revisão:** o comentário da retomada passou a citar o quadro, o nome
  `fora` virou `do_corpo`, e a abertura do bloco novo saiu do `acrescentar` (`_abrir`). Com isso,
  o `blocos.py` passaria de 400 linhas, e as regras do quadro foram para `dominio/quadro.py`
  (acima);
- **lote B:** a contagem de segmentos de quadro foi corrigida (1.060, medida num protótipo que
  ainda partia o parágrafo do quadro quando a letra mudava, para 1.058), e o destaque depois do
  quadro e os dois mecanismos de interrupção foram registrados acima.

Pós-auditoria das correções (2026-11-03), lote D aprovado pelo Mateus ("Fazer o D"), sem mudar a
saída. Dois comportamentos que já existiam ganharam teste, cada um visto falhar na asserção com o
mutante plantado:
- **P1, quadros seguidos:** o rótulo do segundo quadro não solta o primeiro, porque a frase que
  eles interrompem ainda não acabou. Sem a guarda, mudavam 15 posições do Dalgalarrondo ("tigar
  detidamente os impulsos suicidas…" descia para depois do Quadro 17.2, p. 181);
- **P2, a "Tabela":** o rótulo "Tabela 19.1" abre o quadro como o "Quadro". Sem ele, as 2 tabelas
  do Dalgalarrondo deixavam de ser quadro, e 2.430 posições do livro mudavam.

A pós-auditoria do lote D achou mais duas guardas sem teste. O Mateus aprovou o lote E e o commit
sem outra rodada de mutantes ("E e commitar"). As duas guardas já existiam e ganharam teste, cada
um visto falhar na asserção com o mutante plantado:
- **P3, a minúscula da retomada:** só a linha que começa em minúscula retoma o parágrafo
  interrompido, depois do quadro e depois da nota (o teste da nota fica em
  `tests/test_blocos_retomada.py`). A linha em maiúscula abre parágrafo novo. A
  regra vem da retomada da nota (Competente p. 33) e não tinha teste nem lá. Sem ela, os três
  PDFs mudavam: o Dalgalarrondo de 4.790 para 4.778 blocos, o Competente de 5.083 para 4.997 (o
  sumário) e o Hard Parts de 3.345 para 3.323;
- **P4, o número do rótulo:** "Quadro clínico" em letra de título, sem número, não abre quadro.
  Sem a guarda, os três PDFs saíam iguais.

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
| O destaque não cola no texto | testes (`tests/test_destaque.py`): a letra menor na virada de coluna abre parágrafo, para os dois lados; a mesma letra, ou meio ponto de diferença, segue; a letra menor sem virada segue; do PDF de ponta a ponta, a frase da p. 250 volta inteira | portão | o destaque cola na frase, ou um parágrafo sem destaque se parte |
| O quadro fica no lugar | testes (`tests/test_quadro.py`): o conteúdo do quadro é parágrafo, não nota; a frase interrompida volta inteira, com o quadro depois, também quando o quadro acaba em linha de 9 pt; o quadro espera o destaque que parte a continuação; fica no lugar entre parágrafos, entra antes do título seguinte e não se perde no fim do livro; o rótulo seguido ("Quadro" ou "Tabela") e a linha de 11 pt continuam o quadro, e os quadros seguidos esperam juntos a frase acabar; a letra do corpo e o título o fecham, e o corpo colado à última linha do quadro abre bloco próprio; o código dentro do quadro não retoma o texto, e a linha em maiúscula depois do quadro também não; o título "Quadro clínico", sem número, não abre quadro; a menção no corpo não o abre; do PDF de ponta a ponta, as p. 43 e 44 | portão | conteúdo de quadro vira nota, a frase se emenda no quadro, ou um bloco de quadro some |
| A escuta ★ | rodar `importar-pdf` + `preparar` num PDF real em `livros/` e contar o que o `limpar` ainda precisa tirar | a cada mudança no conversor | a contagem sobe |

Regra derivada no `AGENTS.md`: a biblioteca de PDF só entra em `adaptadores/`.

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-01 · Aprovado em: 2026-11-01
