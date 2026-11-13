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
- **colunas de verbete que começa em maiúscula**: a bibliografia do Dalgalarrondo (p. 416–431: "BERGSON, H.", "São Paulo:") e algumas páginas do glossário têm continuidade de 0,33 a 0,4 e continuam intercaladas. No protótipo, 43 páginas do Dalgalarrondo ainda têm alguma faixa larga recusada (bibliografia, quadros e tabelas). Resolvido em "O que ficou da Fase 1" (2026-11-03), pelo texto justificado;
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
- **o cabeçalho de duas páginas:** "Prefácio da 1a edição", em 9 pt no alto das p. 14 e 15, não chega às 3 páginas da linha repetida e fica, como antes. Sem o número que o colava num título ("14 Prefácio da 1a edição"), ele entra no meio da frase partida pela página: "Bernard e Si- Prefácio da 1a edição mone Trouvé (1977)". As junções continuam 19 porque esta entra e uma sai: a de `c011`, "Sullivan (1983) afirmava que" + "o entrevistador desempenha", que é um dos 21 casos do quadro, abaixo. O começo da frase ("senciais da clínica…") vai para o título do quadro, e "o entrevistador desempenha…" fica depois do quadro, num parágrafo próprio. Resolvido em "O que ficou da Fase 1" (2026-11-03), pelas páginas vizinhas;
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

Achados na medição, para a fila da próxima filha, sem correção aqui (resolvidos em "O que ficou
da Fase 1", abaixo):
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

### O que ficou da Fase 1 (2026-11-03)

A Fase 1 do Dalgalarrondo é a conversão limpa, sem escuta. Ela fecha com cinco regras do
`importar-pdf`, que estavam na fila do Quadro e das rodadas anteriores, e uma do `limpar` (a
bibliografia, no ADR-0008, "Bibliografia"). Medido no HEAD `f60971a`, nas pastas `*-base-fase1`
de `livros/trabalho/`:
- **43 notas em "Notas":**
  - 39 são subtítulos em versalete;
  - 3 são pedaços do Quadro 22.4, que o texto escondido da p. 275 fechava;
  - 1 é a coluna da direita da tabela do Quadro 29.1 (p. 324).
- **1 capítulo falso** (`c026`).
- **17 páginas intercaladas:** o glossário (p. 405 e 416) e a bibliografia (p. 418 a 431).
- **A lista da p. 384** intercalada com o texto.
- **"Bernard e Si- Prefácio da 1a edição mone Trouvé"**, a frase partida pelo cabeçalho.

O Mateus aprovou as seis regras, com o cabeçalho na forma estreita ("Aprovar").

**1. Subtítulo em versalete.**
- **O defeito:** são 39 subtítulos, em 48 linhas, nas p. 126 a 342 ("DELÍRIO DE GRANDEZA (DE
  ENORMIDADE)", "TRANSTORNO DA PERSONALIDADE PARANÓIDE"). O versalete é feito à mão: só
  maiúsculas, a inicial de cada palavra em 10,5 pt e o resto em 7,4. Pela moda, a linha tinha
  7,4 pt, virava nota e ia para "Notas", longe da seção que nomeia.
- **A regra:**
  - o adaptador marca a linha só em maiúsculas que tem alguma **letra** maior que a moda
    (`Linha.versalete`, `em_versalete` em `dominio/pagina.py`), e ela é título;
  - a linha de nota seguinte, só em maiúsculas e do mesmo tamanho, continua o título. Na segunda
    linha não há letra maior ("PERSONALIDADE PARANÓIDE").
- **Recusado: "nota toda em maiúsculas".** Pegaria 37 linhas do Competente, de um tamanho só: o
  sumário ("PARTE I · O QUE É ESSA COISA"), "PREFÁCIO", "APÊNDICE A" e "CRÉDITOS DAS IMAGENS".
  Com a marca, o Competente tem 0 linhas e o Hard Parts tem 1 ("ML = 100 * ∑"), que fica de fora
  porque o "∑" não é letra.
- **O que se perde:** o versalete de fonte própria, de um tamanho só, continua nota.

**2. Texto escondido.**
- **O defeito:** debaixo do Quadro 22.4 (p. 275) ficou o resto de uma abertura de capítulo
  antiga: "24" em 60 pt, e "A inteligência e" / "suas alterações" em 22 pt. O capítulo real é o
  23, com o mesmo título.
  - Na mesma altura de linhas do quadro, essas linhas se juntavam a elas.
  - O "24" virava título do tamanho do capítulo e abria o `c026`.
  - O quadro fechava, e 3 pedaços dele iam para "Notas".
- **A regra:** a linha em letra de título que, na mesma altura, se sobrepõe na horizontal (mais
  de 1 pt) a uma linha de **outro tamanho** sai antes da paginação, com o motivo "texto escondido
  debaixo de outro" (`dominio/texto_escondido.py`). O resumo do comando passa a dizer "linhas
  tiradas da página: a borda e o texto escondido".
- **Medido nos três PDFs:** só os 3 da p. 275.
  - O texto repetido por cima, do mesmo tamanho, fica. É negrito feito à mão: "Conheça também"
    no Dalgalarrondo (p. 2) e "Beijing" no Hard Parts (p. 5). Desde 2026-11-03, a cópia sai por
    outra regra ("Negrito feito à mão", abaixo).
  - A letra miúda sobreposta também fica: Hard Parts p. 462, de 0,7 a 3,6 pt.
- **O que se perde:**
  - o texto escondido do tamanho do corpo continua;
  - o título legítimo que encosta numa linha de outro tamanho, na mesma altura, sairia. Não há
    caso.
- **"Para personalidade paranóide"** (8 pt, dentro do quadro) passa a colar na pergunta de cima,
  como "Para personalidade anti-social" já colava. É o quadro lido como lista de linhas, que vai
  para o `adaptar`.

**3. As colunas das p. 324 e 384** (`dominio/colunas.py`, que passa a receber o tamanho do corpo,
`linhas_visuais(linhas, corpo)`).

- **p. 324:** a tabela do Quadro 29.1 (8 pt, duas colunas) e o corpo de baixo (10 pt) ficavam
  na mesma faixa. O vão entre eles era de 0,036, abaixo do vão das faixas (2,5 entrelinhas, ou
  0,038). A coluna da direita da tabela vinha depois do corpo, fora do quadro.
  - **Regra (`_acaba_a_tabela`):** o vão de parágrafo (1,35 entrelinha) antes de uma linha do
    corpo também fecha as colunas, quando os **dois** lados acabam, logo acima, em 3 linhas ou
    mais de letra menor que o corpo.
  - **Recusado: cortar em toda troca de letra.** Mudava 6 páginas para pior, porque o subtítulo
    de 11 pt partia as colunas (p. 193 e 332), e mudava o Hard Parts.
  - **Recusado: sem as 3 linhas dos dois lados.** O versalete de um lado só estragava a p. 219.
- **p. 384:** no pé da página, o resto do parágrafo tinha 2 linhas à esquerda ("…é classi-" /
  "camente definida pela tríade:"), e a lista "1. 2. 3." ficava à direita. Uma coluna precisava
  de 3 linhas.
  - **Regra (`_curta_do_corpo`):** o lado de 2 linhas do corpo também é coluna quando a de cima
    termina no hífen da quebra e a de baixo começa em minúscula.
  - **Recusado: "2 linhas bastam".** Mudava a p. 257 do Hard Parts, porque a célula de duas
    linhas continua em minúscula sem se partir em sílaba, e 4 páginas de quadro do
    Dalgalarrondo.
- **Medido:** só essas duas páginas mudam nos três PDFs.
  - A p. 324 sai com o corpo inteiro ("Já a somatização… síndromes pseudoneurológicas."), e o
    Quadro 29.1 vem depois, coluna a coluna: "Crise dissociativa histérica" e depois "Crise
    epiléptica".
  - A p. 384 sai com "…é classicamente definida pela tríade:" e depois a lista.

**4. O glossário, pelo texto justificado.**
- **O defeito:** os verbetes abrem em maiúscula, e a continuidade do glossário (p. 405 e 416) e
  da bibliografia (p. 418 a 431) fica entre 0,31 e 0,4, abaixo dos 40% de "Duas colunas". As
  colunas saíam intercaladas ("Prová- Lambuzão: desleixado…", "denomi- Zebra: pouco
  inteligente…").
- **A regra:** o lado também é texto corrido quando continua em 30% ou mais dos pares e **40% ou
  mais** das linhas terminam na margem direita dele (a menos de 1 pt), ou seja, é justificado
  (`_justificado`).
- **Medido:**
  - o glossário tem de 0,40 a 0,55 de linhas cheias;
  - a bibliografia, de 0,62 a 0,77;
  - as tabelas do Competente e do Hard Parts que passam de 0,3 de continuidade têm no máximo 0,25
    (a p. 144 do Competente, 0,11);
  - as tabelas com a coluna da direita alinhada (Hard Parts p. 59, 143 e 144) têm linhas cheias,
    mas continuidade zero, e por isso as linhas cheias sozinhas não bastam.
- **O que muda:** só páginas do Dalgalarrondo.
  - O glossário fica sem intercalação.
  - A bibliografia fica em ordem, e sai inteira (ADR-0008).
  - As p. 219 e 273, com versaletes nas colunas, ficam em ordem.
  - A p. 309 deixa de sair intercalada ("…fatores A ordenação da depressão…"), e o destaque dela
    passa a sair.
  - A tabela do Quadro 24.2 (p. 299) passa a sair por coluna; já saía embaralhada.
- **O que se perde:**
  - o texto justificado com menos de 30% de continuação continua intercalado;
  - as páginas que ainda saem intercaladas são quadros e tabelas, lidos como lista de linhas.

**5. O cabeçalho de duas páginas.**
- **O defeito:** "Prefácio da 1a edição" (p. 14 e 15) e "Sumário" (p. 18 e 19), em 9 pt no mesmo
  topo, não chegam às 3 páginas da linha repetida (limite "o cabeçalho de duas páginas", acima).
- **A regra (forma estreita):** a linha repetida também sai quando aparece em 2 páginas
  **vizinhas**, as duas de uma abertura (`PAGINAS_VIZINHAS`). O teste "a linha no alto em duas
  páginas só fica", que tinha as duas páginas vizinhas, passou a ter uma página entre elas: esse
  caso fica.
- **Recusado: a forma geral,** com até uma página entre as duas.
  - **Competente:** tiraria 8 cabeçalhos ("PREFÁCIO", p. 10 e 12; "DO GNU GO AO KATAGO"; "COMO
    ESTE LIVRO FOI FEITO"; "AI-MEMORY"), que hoje vão para "Notas".
  - **Hard Parts:** tiraria 30 rodapés de seção curta ("| Preface", "Sysops Squad Saga: …", o
    limite da primeira regra), com 28 emendas certas.
  - **Mas há 2 colagens novas no Hard Parts.** O rodapé separava, por acaso, um item de lista do
    parágrafo da página seguinte. Sem ele, a virada de página os cola: "…better deployability
    Consequences The migration effort…" e "• Authorization Consequences Teams should not…".
  - Volta quando a virada de página não colar mais o item de lista sem pontuação no parágrafo
    seguinte.

**Medido depois do código, contra o HEAD `f60971a`** (pastas `*-fase1`). O Dalgalarrondo saiu
idêntico ao protótipo (`*-prototipo-fase1`), fora o texto do motivo da bibliografia.

| Livro | `importar-pdf` | `preparar` |
|---|---|---|
| *Dalgalarrondo* | capítulos 43 → **42**; títulos 222 → 260; parágrafos 4.524 → 4.436; **notas 44 → 1** (a página de direitos, que o `limpar` tira); linhas tiradas 819 → 826 (+3 escondidas, +4 do cabeçalho); hífen tirado 10.973 → 11.075, mantido 193 → 196 | segmentos 4.790 → 4.719; remoções 243 → 269 (+25 da bibliografia, +1 destaque, o da p. 309); junções 237 → 229 (6 remendavam a p. 309 intercalada, e 2, o prefácio); suspeitas 23 → 23. `limpos/`: 4.310 → 4.199 segmentos, **0 notas** |
| *Competente*, *Hard Parts* | igual: o XHTML do EPUB é idêntico | `segmentos/`, `limpos/`, `limpeza.json` e `livro.json` idênticos (fora a origem) |
| *Huxley*, *Tides*, *Learning DDD* | — | idênticos; o `limpos/` do Learning DDD é igual ao da pasta traduzida |

- **Nenhuma letra se perde.** Contando o `limpos/`, os destaques e a bibliografia tirados, a
  diferença, caractere a caractere, é exatamente o texto escondido e as 4 linhas de cabeçalho.
- **Em palavras:** 167.749 → 167.628. São 16 palavras dessas linhas e ~105 palavras partidas
  entre as colunas do glossário e da bibliografia, que voltam inteiras.
- **Frases:** "…Paul Bernard e Simone Trouvé (1977)…" e "…é classicamente definida pela tríade:"
  saem inteiras. "DELÍRIO DE RELAÇÃO" e "DELÍRIO DE GRANDEZA (DE ENORMIDADE)" saem como títulos,
  cada um antes do seu texto.

Para caber nas 400 linhas, o `blocos.py` foi dividido por assunto, sem mudar o comportamento. O
tipo da linha pela fonte e as medidas do livro (`TipoDeBloco`, `tipo_da_linha`, `medir`) foram
para `dominio/tipo_da_linha.py`.

Correções da code-review e da code-audit (2026-11-03), aprovadas pelo Mateus ("A, B, C e
commit"). Os seis livros saíram idênticos à medição acima.
- **Lote A, duas guardas que já existiam e ganharam teste.** Cada teste passa no código e foi
  visto falhar na asserção com o mutante plantado numa cópia:
  - **M6, só o título em versalete se continua:** sem a guarda, a linha só em maiúsculas
    depois de uma nota virava título. Mudavam os três PDFs: "ISBN 978-85-363-1493-8" na página
    de direitos do Dalgalarrondo, "1957)" na linha do tempo do Competente e 3 blocos do Hard
    Parts;
  - **M15, a tabela só acaba no vão de parágrafo:** sem o vão, 3 linhas de letra menor em cada
    coluna, seguidas do corpo na entrelinha comum, cortavam as colunas. Mudavam 4 páginas do
    Dalgalarrondo (p. 91, "O inconsciente").
- **Lote B, código, sem mudar a saída:**
  - **R1:** o texto escondido compara só as linhas da mesma altura, na ordem do topo, e não
    todos os pares da página. O PDF é entrada não confiável: uma página de 10 mil linhas leva
    0,1 s. Fica quadrático só o que está numa altura só (2 mil linhas, 0,6 s);
  - **R2:** o par de páginas vizinhas só vale para a linha com letra. A pausa de cena ("* * *")
    no alto de duas páginas seguidas fica e continua precisando de 3 páginas. Teste novo, visto
    falhar na asserção antes da correção;
  - **R7 e R9:** o ajudante `so_maiusculas` (`dominio/pagina.py`) serve ao versalete e à linha
    que o continua; e `tirar_texto_escondido`, `acrescentar` e `_repetidas` foram divididos.
- **Lote C, limites sem caso nos livros medidos:**
  - **R3:** a contagem de letra menor de `_acaba_a_tabela` vem desde o alto da página e pula a
    linha que atravessa a calha. Ela pode somar linhas de uma faixa anterior;
  - **R4:** uma linha toda em maiúsculas com uma capitular maior passa por versalete e vira
    título;
  - **pendências, guardas sem teste que não mudam os três PDFs:**
    - **M5:** o tamanho da linha que continua o versalete;
    - **M7:** o `all` dos pedaços da mesma altura no versalete;
    - **M18:** a letra do corpo na coluna curta.

**Fila, achada nesta medição e fora do ciclo** (vai para um ciclo curto depois deste):
- **"Conheça Conheça Conheça também…"** (`c001-s0002`, p. 2): negrito feito com o texto repetido
  por cima, do mesmo tamanho. É lido cinco vezes. Resolvido em "Negrito feito à mão", abaixo;
- **o índice remissivo do Dalgalarrondo** (p. 433 em diante): continua lido. É "o índice do PDF
  importado", já pendente no `AGENTS.md`. Resolvido no ADR-0008, "Índice pelo conteúdo";
- **a bibliografia do Competente** (p. 481 a 503): 118 referências ABNT partidas entre nota e
  parágrafo, que nunca chegam a 10 seguidas. São 226 notas. Fica, por decisão do Mateus (ADR-0008,
  "Índice pelo conteúdo", "A bibliografia do Competente").

### Negrito feito à mão (2026-11-03)

- **O defeito:** na p. 2 do Dalgalarrondo, "Conheça também" (24 pt) está desenhado cinco vezes,
  deslocado de 0,5 a 1 pt, para engrossar a letra. O pdfminer devolve 9 linhas na mesma altura:
  4 "Conheça", 4 "também" e 1 "Conheça também". A voz lia "Conheça Conheça Conheça também
  Conheça Conheça também também também também" (`c001-s0002`).
- **O mesmo defeito no Hard Parts,** também lido: na p. 5, as cidades da editora estão desenhadas
  duas vezes, no mesmo lugar ("Beijing Beijing Boston Boston Farnham Sebastopol Farnham
  Sebastopol Tokyo Tokyo", `c001-s0015`).
- **Medido no HEAD `56b7891`** (pares de linhas na mesma altura que se sobrepõem na horizontal,
  pastas `*-base-curto`):
  - **Dalgalarrondo:** 20 pares do mesmo tamanho, com o texto de uma contido no da outra, todos na
    p. 2;
  - **Competente:** nenhum;
  - **Hard Parts:** 4 pares na p. 5, idênticos e no mesmo x, e 3 pares "l"/"l" na p. 462. A
    p. 462 é texto vertical, uma letra por linha ("O'Reilly Media, Inc. is a registered
    trademark…"), e o "ll" de "Reilly" são duas linhas iguais, a 0,0014 de altura.
- **A regra** (`dominio/texto_escondido.py`, no mesmo passo do texto escondido): sai a linha que é
  cópia de outra. Uma linha é cópia quando:
  - as duas estão na mesma altura (`MESMA_ALTURA`) e no mesmo tamanho (até 0,5 pt);
  - o texto dela está contido no da outra;
  - a outra cobre 90% ou mais da largura dela;
  - ela tem 2 letras ou mais.

  Entre duas iguais, fica a primeira na ordem da página, e a que contém as outras ("Conheça
  também") sempre fica. O motivo é "texto repetido por cima: negrito feito à mão", e ele aparece
  no resumo do `importar-pdf`.
- **Recusado: deduplicar no adaptador** (`adaptadores/pdf.py`). O pdfminer já entrega as cópias
  em linhas separadas, e a decisão é do domínio: o adaptador só traduz a biblioteca.
- **O teste que mudou:** `test_texto_repetido_por_cima_do_mesmo_tamanho_fica`, de "O que ficou da
  Fase 1", dizia que as duas cópias ficavam. Ele virou
  `test_texto_repetido_por_cima_do_mesmo_tamanho_nao_e_escondido`: a guarda de que a cópia não é
  texto escondido continua, e agora uma cópia sai, com o motivo do repetido.
- **O que se perde:**
  - a cópia de uma letra só fica (a guarda do texto vertical);
  - a cópia deslocada mais de 10% da largura fica;
  - uma linha contida noutra, do mesmo tamanho, na mesma altura e por cima dela, sairia. Não há
    caso: no texto composto, duas linhas não ocupam o mesmo lugar.
- **Medido depois do código** (pastas `*-curto`, idênticas ao protótipo `*-prototipo-curto`):
  - **Dalgalarrondo:** saem 8 linhas, e "Conheça também" é lido uma vez;
  - **Hard Parts:** saem 4 linhas, e fica "Beijing Boston Farnham Sebastopol Tokyo". O texto da
    p. 462 não muda;
  - **Competente:** o XHTML do EPUB é idêntico.

O Mateus aprovou ("Aprovar"), junto com o índice pelo conteúdo do ADR-0008.

Correções da code-review e da code-audit (2026-11-03), aprovadas pelo Mateus ("Sim, e
commitar"). Os seis livros saíram idênticos à medição acima.
- **R1, um registro só:** a cópia se procura entre as linhas que ficam depois do texto escondido.
  O título escondido desenhado duas vezes saía duas vezes no registro, como escondido e como
  repetido. Não há caso nos três PDFs. O teste novo foi visto falhar na asserção antes.
- **R2, o resumo:** a linha do `importar-pdf` passa a "N linhas tiradas da página: a borda, o
  texto escondido e o texto repetido.", com teste visto falhar antes.
- **Pendência, guarda sem teste que não muda os três PDFs:** M6, a largura maior que zero da
  cópia. E M7 é equivalente: entre duas cópias de texto igual, qual fica não muda o livro.

### Cabeçalho fora da faixa e versalete de fonte própria (2026-11-07)

Medido no HEAD `9af7ac9`, no *Philosophy of Physics: Quantum Theory* (Tim Maudlin, Princeton,
2019), PDF de editora de 250 páginas, 396 x 612 pt. O Mateus aprovou ("Aprovar as cinco"), junto
com o caminho do livro (ADR-0012).

**1. Cabeçalho e número de página fora da faixa.**
- **O defeito:** a margem é larga. O cabeçalho corrente ("Chapter 2" nas pares, o título do
  capítulo nas ímpares, 9 pt) fica a 13,6% do alto, e o corpo começa a 17%. O número de página
  fica na margem de fora, a 81% da altura, ao lado da coluna (x 392 nas ímpares, 62 nas pares). Os
  dois caem fora da faixa de 8%, e nada saía: 230 números e 222 cabeçalhos no meio das frases
  ("what 5 Chapter 1 we want"), 179 junções de parágrafo erradas e o número de página no fim de
  cada nota de rodapé.
- **A regra** (`dominio/paginacao.py`): além da faixa, entra como candidata a linha fora da
  **mancha**, a área do corpo no livro inteiro, medida pelas linhas largas do tamanho do corpo
  (pelo menos metade da largura mediana), no percentil 1 (o alto e a margem esquerda) e no 99 (a
  margem direita):
  - acima da mancha, por mais de 0,005, qualquer linha: o cabeçalho, que vai às duas regras de
    sempre (o número sai se segue a paginação em 3 páginas, e a linha sai se se repete no mesmo
    topo em 3 páginas, com a fonte do tamanho do corpo ou menor);
  - ao lado da coluna, qualquer linha, mas só para a regra do número de página.
  O motivo diz "cabeçalho" na metade de cima da página e "rodapé" na de baixo. A faixa de 8% fica
  junto da mancha, e não some, para não mudar os livros já medidos.
- **Recusado: a linha mais alta de cada página.** Pegava o cabeçalho de tabela que abre três
  páginas no Hard Parts ("Advantage Disadvantage", "Component Namespace Responsibility",
  "Consistency") e 5 linhas de URL repetidas no Competente. Pela mancha do livro, o cabeçalho de
  tabela está na altura do corpo, e fica.
- **Recusado: o texto repetido ao lado da coluna.** A nota de margem que se repete é do livro, e
  o "x" do eixo de uma figura na mesma altura em três páginas também (R2 da auditoria).
- **Por que as linhas largas** (R1 da auditoria): o cabeçalho e o número do tamanho do corpo, um
  por página contra ~30 linhas de corpo, passam de 1% das linhas e entrariam na mancha; a regra
  deixaria de valer, em silêncio. O percentil continua: uma epígrafe no alto, ou uma equação que
  avança sobre a margem, não desloca a mancha.
- **O que se perde:** uma linha que se repete em 3 páginas acima de onde o corpo começa, e um
  número de linha na margem que coincida com a paginação. Não há caso nos quatro PDFs.

**2. Versalete de fonte própria.**
- **O defeito:** os 8 experimentos e as seções do Maudlin ("further reading", "The PBR Theorem")
  vêm em `Archer-Medium-SC700`, uma fonte só de versaletes, de um tamanho só (9 pt, contra o corpo
  de 10). A letra maior do versalete feito à mão não existe, e a linha virava nota no fim do
  capítulo. Era o item pendente "o versalete de fonte própria, de um tamanho só, ainda vira nota".
- **A regra** (`adaptadores/pdf.py`): a linha cuja letra visível é **toda** de fonte com o nome
  terminado em "SC", depois do traço ou do sublinhado, com um número opcional (`-SC`, `-SC700`),
  sem distinguir caixa, como as outras regras de fonte, é versalete, e vira título pela regra que já existe. A abertura de capítulo com as primeiras
  palavras em versalete e o resto em Minion continua parágrafo.
- **O que se perde:** uma linha inteira de corpo em versalete de fonte própria (uma epígrafe, por
  exemplo) viraria título. A fonte de versalete sem o "SC" no fim do nome ("MinionPro-RegularSC")
  continua nota.

**Medido depois do código:**

| Livro | O que muda |
|---|---|
| *Maudlin* (`importar-pdf` + `preparar`) | saem 235 cabeçalhos e 237 números; títulos 41 → 75 (os 34 versaletes); notas 144 → 126; segmentos 1.327 → 1.281; junções 179 → 72; suspeitos 86 → 45 |
| *Competente*, *Hard Parts*, *Dalgalarrondo* | o resumo do `importar-pdf`, `segmentos/`, `limpos/` e `limpeza.json` idênticos |
| *Huxley*, *Tides*, *Learning DDD* | EPUB, não passam pelo `importar-pdf`; `preparar` idêntico |

Nenhum dos três PDFs tem fonte com "SC" no nome, com ou sem caixa. Depois da auditoria (a mancha
pelas linhas largas, o candidato ao lado da coluna só na regra do número, a regex sem caixa), os
seis livros e o Maudlin saem iguais à medição acima.

### Tratado médico: número de referência, espaço falso, tabela, figura e páginas de lista (2026-11-10)

Medido no HEAD `8a0226b`, no *Practical Management of Pain* (6ª ed., 1.503 páginas) e no
*Bonica's Management of Pain* (5ª ed., 6.053 páginas). O Mateus decidiu em 2026-11-10, antes da
tradução do Practical, tirar do áudio o número de referência colado, as tabelas embaralhadas, os
restos de figura e as legendas, a lista de colaboradores e o sumário. O índice remissivo já era
alvo do ADR-0008. Tudo sai no `importar-pdf`, onde o PDF ainda tem letra, posição e página; no
texto montado, a tabela e a lista viram blocos sem marca, misturados ao corpo.

**1. Número de referência e espaço falso** (`dominio/caracteres.py`; o adaptador entrega os
caracteres da linha, com tamanho, posição e os espaços que o pdfminer deduz).
- **O defeito:** a chamada vem sobrescrita, a 0,58 do corpo e com a linha de base 0,33 do corpo
  acima ("wages.¹", "84%–90%.²,³", "et al.¹⁹⁴", "syndromes.¹²⁻¹⁵"), e ia colada à palavra:
  9.706 no Practical, 13.155 no Bonica, pelo inventário do texto limpo.
- **A regra:** sai o trecho de caracteres com letra menor que 0,85 da letra da linha e o pé mais
  de 0,15 dela acima do pé da linha, que é só algarismo, vírgula e traço, colado a uma palavra de
  2 letras ou mais ou a uma pontuação que fecha (`. , ; : ) ] % ’ ” "`). Ficam o expoente depois
  de algarismo ("10⁶"), a carga do íon ("Ca²⁺"), a unidade ao quadrado ("kg/m²", "cm²"), a letra
  solta ("r²"), o subscrito, a letra sobrescrita ("ᵃ") e o sobrescrito no começo da linha ou
  depois de espaço. Cada chamada fica no registro do `importar-pdf`, com a palavra antes
  ("wages.[1]"), e o resumo a conta.
- **O pé, e não a matriz:** o pdfminer põe a subida do `Ts` na caixa do caractere e não na
  matriz; no Practical, a posição vem pela matriz, e a caixa sobe junto.
- **O espaço falso:** o nome do autor vem em Gotham-Bold com 1 pt a mais entre as letras, e o
  pdfminer punha espaço onde o vão passa de 0,1 da letra ("NATALI E MORY L, CH ARLE S", 167
  segmentos). A regra antiga da letra espaçada não pegava, porque o par apertado ("AT", 0,1 pt)
  parecia palavra. Agora o espaço deduzido some quando o vão dele não passa do vão típico entre
  as letras da linha (a mediana) por mais de 0,03 da letra. No texto comum o vão entre letras é
  quase zero, e o da palavra, mais de 2 pt.

**2. Tabela e figura pela letra** (`dominio/tabelas_e_figuras.py`; a linha ganha a família da
letra, o nome da fonte sem o prefixo do subconjunto e sem o estilo).
- **O defeito:** no Practical, o corpo é AGaramondPro de 10 pt. O rótulo "TABLE" vem em
  Gotham-Bold numa linha, o número em outra, o título em MyriadPro-Bold e as células em
  HelveticaNeueLTStd-Cn de 8,5 pt, lidas coluna a coluna (78 "TABLE" soltos). A figura traz os
  rótulos do diagrama em Helvetica de 7 pt, que viravam nota no fim do capítulo (191 notas,
  17.631 palavras), e a legenda "• Figure 2.1 …" (204, 13.274 palavras). No Bonica, a tabela abre
  num título "TABLE 1.1 …" e segue em nota, na letra do corpo menor, e a legenda é "FIGURE 1.1 …".
- **A regra:** a letra do corpo é a família e o tamanho com mais caracteres no livro. Uma
  corrida é uma sequência de linhas seguidas, no livro todo, fora da letra do corpo e da de
  título. Sai a corrida que tem um rótulo em inglês: "TABLE" sozinho na linha, ou "TABLE",
  "Table", "FIGURE", "Figure", "Fig." e "• Figure" com o número seguido de ponto, maiúscula ou
  fim de linha. Da tabela, sai do rótulo em diante, também na página seguinte (a continuação);
  da figura, a corrida na página da legenda, para os dois lados, porque o diagrama vem antes
  dela. A linha da letra do corpo, ou de título que não é rótulo, fecha a corrida.
- **Não é rótulo:** "Table of Contents"; a menção quebrada na linha ("Table 5-7 shows…"); e a
  linha que continua a frase da de cima na mesma letra ("…components in" | "Figure 5-11.", na
  prosa em MyriadPro de 9 pt da "Sysops Squad Saga" do Hard Parts).
- **Só o rótulo em inglês:** o "Quadro" e a "Tabela" do Dalgalarrondo ficam no lugar (seção
  "Quadro no lugar"), e o "Figura" do Competente não pôde ser medido (o PDF não está neste Mac).
- **O livro sem família de letra** (o nome da fonte que não é texto) não muda.
- **Recusado: pela letra, sem rótulo.** A caixa "Key Points" e a prosa da saga do Hard Parts
  vêm noutra letra e são texto do livro.

**3. Páginas de lista** (`dominio/paginas_de_lista.py`, por página, antes da tabela).
- **O defeito:** o índice remissivo do Practical (p. 1467 a 1503) é página escaneada com OCR, em
  Times de 8,3 pt; o pdfminer o lê intercalado entre nota e parágrafo, e a regra do ADR-0008, de
  10 parágrafos de "termo, página" seguidos, não dispara (cerca de 28 mil palavras). O sumário
  (p. 19 a 22) e os colaboradores (p. 6 a 13) vêm em duas colunas e se misturam.
- **A regra:** sai a página inteira em que 8 linhas ou mais, e 25% das linhas ou mais, terminam em
  vírgula, espaço e número de página ("pelvic pain in, 617", "Interdisciplinary Pain Management,
  39", com "621 t", "99f" e "977- 978"), sem contar o ano ("Philadelphia, 2004") nem a vírgula
  decimal ("17,6"). Sai também a página com 5 nomes ou mais com título acadêmico ("Honorio T.
  Benzon, MD") que sejam 10% das linhas ou mais; o nome em maiúsculas (o autor do capítulo) não
  conta.
- **O resumo** do `importar-pdf` conta a tabela, a figura e a página de lista numa linha à parte,
  cada uma com o seu motivo; a linha da borda continua contando só a borda, o texto escondido e o
  texto repetido.

**Correções da code-review (esforço alto) e da code-audit**, cada uma com o teste visto falhar
na asserção antes:
- **R1:** a página com mais linhas de prosa (8 palavras ou mais, sem remissão) que de remissões
  fica: uma tabela de doses não leva a prosa da página.
- **R2:** a tabela que vira a página só continua na letra que as células dela já usaram; o
  crédito do autor no alto da página seguinte fica.
- **R3:** antes da legenda, só sai o diagrama em letra não maior que a dela (mais 0,25 pt); a
  caixa de 9 pt logo antes fica.
- **R5 e R6:** a chamada com espaço dentro ("1,8, 9") e com a vírgula sobrescrita no fim sai
  inteira.
- **R9:** o adaptador acha a letra seguinte de cada espaço numa passada só.
- **O nome com vários pares apertados** (2026-11-11, depois da medição do livro inteiro): em 10
  créditos de autor do Practical ("PREETMA KAU R KO ONER, GREGO RY W. TERMAN", p. 39), o espaço
  falso saía certo, mas a regra antiga da letra espaçada rodava depois e repartia o nome, porque
  os pares apertados (0,45 a 0,8 pt) formavam "palavras" de 2 e 3 letras. Agora, se algum espaço
  inventado saiu, os espaços de verdade já separam as palavras, e a regra antiga não roda
  (`caracteres.lido`). No Dalgalarrondo e no Hard Parts, nenhuma linha tem espaço inventado tirado;
  na amostra do Practical, 6 linhas têm, e só a da p. 39 muda.
- **O hífen:** com o índice tirado antes dos blocos, o Hard Parts perdia a prova de "east-west"
  e lia "eastwest". O dicionário do hífen vem agora das páginas de antes da lista e da tabela.
- **Ficam, declarados:** R4, o expoente depois de parêntese ("(m)²") sai como chamada; R7, a
  chamada de uma linha que depois sai inteira (célula de tabela) conta também no resumo das
  chamadas.

**Medido depois do código** (`livros/trabalho/medicao-8a0226b/` contra
`livros/trabalho/medicao-nova-0004/`):

| Livro | O que muda |
|---|---|
| *Dalgalarrondo* | `limpos/` idêntico, menos 2 segmentos: os marcadores sobrescritos "EUA¹ Áustria² Brasil³ Brasil⁴" da tabela e "(Balada de Loucos¹)"; o índice (p. 433 a 438, 545 linhas) sai no `importar-pdf`, e as 19 remoções de índice do `limpar` deixam de existir; nenhuma tabela, figura nem colaborador |
| *Hard Parts* | `limpos/` idêntico, menos o marcador "Fowler's site.¹"; o índice (p. 443 a 459, 1.588 linhas) sai no `importar-pdf` (antes, 52 remoções no `limpar`), e 16 suspeitas de capitular, que eram linhas do índice, somem; capítulos 22 → 21 (o "Index"); a legenda e a tabela do Hard Parts vêm na letra do corpo e ficam |
| *Huxley*, *Tides* | EPUB: não passam pelo `importar-pdf`, e o `limpar` não mudou |
| *Practical*, amostra de 146 páginas (p. 1 a 60, 400 a 430, 860 a 870, 1460 a 1503) | 454 chamadas tiradas, todas no padrão; 13 páginas de colaboradores (p. 3 e 6 a 17) e 41 de remissões (sumário p. 19 a 22 e índice p. 1467 a 1503); o prefácio (p. 18) fica; as linhas longas tiradas como tabela e figura são células, legendas e fontes, e os títulos tirados são todos títulos de tabela |

**Medido nos dois tratados inteiros** (2026-11-11, HEAD `430026c`; palavras de `limpos/`
contadas por espaço, e as do `importar-pdf`, pelas linhas tiradas):

| Classe | *Practical* | *Bonica* |
|---|---|---|
| Número de referência sobrescrito (chamadas) | 12.344; coladas no texto limpo: 9.706 → 18 | 17.133; coladas: 13.155 → 57 |
| Índice remissivo e sumário | 41 páginas (19 a 22, 1467 a 1503), 29.391 palavras | 433 páginas (5464 a 5898), 67.886 palavras |
| Colaboradores | 13 páginas (3, 6 a 17), 4.584 palavras | 26 páginas, 2.824 palavras |
| Tabela | 11.464 linhas, 24.844 palavras | 26.975 linhas, 75.035 palavras |
| Figura e legenda | 5.157 linhas, 27.508 palavras | 2.560 linhas, 29.737 palavras |
| Palavras de `limpos/` | 918.398 → 831.823 (−9,4%) | 1.371.709 → 1.268.221 (−7,5%); o `limpar` tira 71 mil a menos, que a regra Vancouver tirava e agora saem antes |
| Lotes do `traduzir` | 530 → 473 | não traduzido |

Procurados os falsos positivos: nenhuma página de lista fora do sumário, do índice e dos
colaboradores, nos dois livros; nas amostras de linhas longas tiradas como tabela e figura, só
células, notas e fontes de tabela e legendas (a "NOTE:" da tabela do Bonica p. 328, a legenda de
4 linhas do Practical p. 1267). Créditos de autor partidos no Practical: de 10 para 0 com
o par apertado ou espaço falso; o inventário de letra espaçada cai de 167 para 79 segmentos (o
que sobra é maiúscula de verdade: "OF PAIN", "SECTION I").

**O que fica:**
- a chamada que o pdfminer põe numa linha só dela ("period.48,49,50", Practical p. 54): a linha
  inteira tem a letra pequena, e nada nela é menor que a linha;
- o rótulo do diagrama em letra maior que a da legenda, e o que o pdfminer põe longe da legenda
  ("A B C", os painéis);
- a tabela e a legenda na letra do corpo, a tabela sem rótulo e o rótulo em português;
- a página do índice ou do sumário com menos de 5 remissões ou com mais prosa que remissão;
- o registro do `importar-pdf` é o resumo por motivo; a lista linha a linha não é gravada.

Decidido pelo Mateus (o que sai, 2026-11-10, pela sessão principal); os sinais e os limiares são
desta sessão e vão à revisão.

### Texto girado e chamada colada ao ano (2026-11-11)

O Mateus decidiu ouvir o *Practical* em inglês, limpo, sem tradução, e pediu antes a correção dos
dois defeitos que o inventário do livro montado achou. Medido no HEAD `bd39b93`.

**1. Texto girado** (`dominio/tabelas_e_figuras.tirar_texto_girado`; a linha ganha `girada`).
- **O defeito:** a tabela dos programas de reabilitação do *Practical* (p. 70 a 73, c005) vem
  deitada na página. A letra tem a
  matriz de lado, e o pdfminer, que monta a linha na horizontal, fazia de cada letra uma linha e
  lia uma letra de cada coluna: "d u r n n n o o , i i t f e i s n a n k…", 9.664 palavras no
  c005 (s0058 a s0082), que também partiam o parágrafo em volta. O mesmo com o rótulo de eixo de
  gráfico, de lado ("e s o d n o i t a i d a r", c074), com a Figura 40.2 (p. 724, c041) e com as Tabelas 49.1 e 49.2 (p. 899 e 900).
- **O sinal:** a matriz, e não a letra nem o rótulo. A tabela deitada vem em HelveticaNeue
  condensada, como as outras, mas cada letra é uma linha de 1 caractere, com o tamanho medido
  pela altura da caixa (de 1,7 a 6,7 pt, p. 72), e nenhuma traz rótulo de tabela em pé.
- **A regra:** o adaptador marca a linha em que toda letra visível tem o `upright` do pdfminer
  falso, a matriz de lado. Ela sai antes da borda, porque a letra solta contaria na paginação, e
  cada linha fica no registro, com a página e o motivo "texto girado: tabela deitada e rótulo de
  lado"; o resumo a conta com a tabela e a figura. A itálica, que só inclina, fica de pé (teste
  com a matriz `1 0 0.2 1`).
- **O livro de lado** (metade das letras giradas ou mais, o `/Rotate` que o pdfminer aplica à
  matriz) não muda: a página inteira de lado é o livro, e não uma tabela no meio dele.

**2. Chamada colada ao ano** (`dominio/caracteres.py`).
- **O defeito:** a chamada depois de algarismo ficava, para guardar o expoente ("10⁶"), e o ano
  levava a chamada junto: "sciatica in 1934²²¹" (p. 332) virava "1934221", "Lutz, 2017¹⁰¹"
  (p. 933), "Black et al. 2018⁸¹⁻⁸⁷"; 29 no texto limpo.
- **A regra:** sai também a chamada depois de um ano, quatro algarismos de 1500 a 2099 sem
  algarismo, ponto ou vírgula antes. "10⁶", "1000²", "12017³" e "3.2017²" ficam (teste).

**Medido** (rodada anterior movida para `livros/trabalho/medicao-bd39b93/`; a nova, com a lista
linha a linha, em `livros/trabalho/medicao-girado/`):

| Livro | O que muda |
|---|---|
| *Practical* | 17.273 linhas giradas em 17 páginas (70 a 73, 724, 899, 900 e 10 com menos de 110), todas de 1 a 3 caracteres; a regra da tabela tira 5.694 linhas a menos e a da figura 528, que agora saem como girado. Chamadas: 12.344 → 12.392, as 48 novas todas depois de ano. `limpos/`: 14.017 → 14.004 segmentos, 831.823 → 820.778 palavras. Mudaram 61 segmentos: o que saiu é letra solta, e a prosa que a tabela partia voltou inteira (c005, "behavior interventions…"; a seção do TMJ, c041, na ordem). Ano com chamada colada no limpo: 29 → 0 |
| *Bonica* | nenhuma letra girada; chamadas 17.133 → 17.147, as 14 novas todas depois de ano ("in 1940⁴ and 1959⁵", "in 2026⁸"); `limpos/` com os mesmos 15.477 segmentos e 1.268.221 palavras, 9 segmentos mudam só pelo ano |
| *Dalgalarrondo* | `limpos/` e resumo idênticos ao HEAD |
| *Hard Parts* | `limpos/` idêntico; saem 77 linhas giradas da última página (p. 462, o crédito "© 2019 O'Reilly Media", de lado), que viravam uma nota que o `preparar` já tirava |
| *Huxley*, *Tides* | EPUB: não passam pelo `importar-pdf` |

Da lista do inventário (89 segmentos, 11.936 palavras de letra solta), saem o c005 inteiro e o
grosso do c041 (1.262 → 26 palavras); ficam 52 segmentos e 445 palavras de tabela em pé, na
letra do corpo ("[ ] dull [ ] stabbing", doses do c046, c050 e c073), que esta regra não cobre.

**O que fica:**
- a linha mista, com letra girada e algarismo em pé (o eixo "100 80 60 40 20" do c074 continua
  lido, sem as letras);
- o texto de cabeça para baixo, que o `upright` dá como de pé;
- o expoente de verdade de um número entre 1500 e 2099 ("2048²") sai como chamada.

Decidido pelo Mateus (o que sai, 2026-11-11, pela sessão principal); o sinal e o limiar são desta
sessão e foram à revisão.

### Rótulo de capítulo (2026-11-11)

O *Bonica* (6.053 páginas, 115 capítulos em 6 partes) saía do `importar-pdf` com 7 capítulos.
Medido no HEAD `c830106`.

- **O defeito:** o corte de capítulo é o maior tamanho de título em 3 páginas ou mais
  ("Segunda regra"). No *Bonica*, é o nome da parte ("Basic Considerations", 30 pt, 6 páginas).
  O capítulo ("C H A P T E R 1", e o título embaixo) vem em 21 pt, o mesmo tamanho dos 786
  títulos de seção; só a cor os separa, e a linha não traz cor. Nenhum tamanho separa o
  capítulo da seção.
- **O sinal:** o rótulo. O título que começa por "CHAPTER 24", "Chapter 24", "CAPÍTULO 3" ou
  "Capítulo 3", seguido de espaço ou do fim, abre capítulo, quando o livro o tem em 3 páginas
  ou mais. Antes do rótulo pode vir só texto em maiúsculas: o nome da subparte, que o título de
  mesmo tamanho junta ("NEUROPATHIC PAIN CONDITIONS CHAPTER 24 Painful Neuropathies"). Ficam de
  fora o título que só cita outro capítulo ("Radiofrequency Denervation (see also Chapter 66…)",
  *Practical*) e a linha do sumário, com dois-pontos ("CHAPTER 6: Supraspinal Mechanisms of Pain
  and 377").
- **O capítulo só fecha depois de ter texto.** Sem isso, a parte (30 pt) abriria um capítulo e o
  rótulo logo abaixo, outro, e a parte seria um capítulo só de título. Com isso, a parte fica
  com o primeiro capítulo dela; e o "CHAPTER 2" pequeno do *Hard Parts*, que vem antes do título
  de 25,2 pt, fica com o capítulo que abre. A regra vale também para o corte pelo tamanho: no
  *Dalgalarrondo*, a página de parte ("1", "ASPECTOS GERAIS DA PSICOPATOLOGIA"), que era um
  capítulo de dois títulos, passa a abrir o primeiro capítulo da parte.
- O nível do título continua pelo tamanho: o rótulo do *Bonica* segue no nível da seção.

**Medido** (`livros/trabalho/medicao-rotulo/`; o antes é `medicao-girado/` e, no *Practical*, a
pasta do HEAD em `livros/trabalho/`). Em todos, a sequência de segmentos de `segmentos/` e de
`limpos/` é idêntica, e o `limpeza.json` tem as mesmas contagens; só mudam as fronteiras:

| Livro | Capítulos | O que muda |
|---|---|---|
| *Bonica* | 7 → 116 | a abertura e os 115 capítulos; cada parte e cada subparte ficam no primeiro capítulo delas |
| *Practical* | 87 → 87 | nada: os capítulos são idênticos, segmento a segmento |
| *Hard Parts* | 21 → 21 | os 15 "CHAPTER N" saem do fim do capítulo anterior e abrem o seu; o sumário do EPUB passa a chamar esses capítulos de "CHAPTER N" |
| *Dalgalarrondo* | 42 → 39 | as 3 páginas de parte, de dois títulos cada, abrem o primeiro capítulo da parte |
| *Huxley*, *Tides* | — | EPUB: não passam pelo `importar-pdf` |

**O que fica:**
- o rótulo em algarismo romano ("Chapter IV") e o rótulo por extenso ("Chapter One") não abrem
  capítulo;
- o rótulo que o kerning parte ("CHAPTER 11 0", do capítulo 110 ao 115 do *Bonica*) abre
  capítulo, mas é lido "eleven zero";
- o sumário do fim do *Bonica* (p. 5899 a 6053, em 18 pt, que a regra das páginas de lista não
  tira) fica no último capítulo e é lido (os dois resolvidos na seção "Sumário sem número…", a
  seguir).

Sem precedente, decidido nesta sessão e levado à sessão principal: a parte vai com o primeiro
capítulo dela, e não num capítulo próprio.

### Sumário sem número, colaboradores vizinhos, espaço de verdade e rótulo no sumário (2026-11-11)

O inventário do *Bonica* montado (commit `264949a`) achou o que ainda se lia e não devia. O
Mateus decidiu corrigir antes da escuta e juntar o rótulo ao título no sumário do EPUB. Medido
no HEAD `264949a`.

**1. Sumário sem número de página** (`dominio/paginas_de_lista.py`, motivo próprio).
- **O defeito:** o sumário da frente (p. 67 a 194, c001-s0226 em diante, 13.936 palavras) não
  traz número de página: cada capítulo é o rótulo, o título, os autores em maiúsculas e as
  seções, uma por linha. O do fim (p. 5899 a 6053, c116-s0016 a s0171, 17.047 palavras) traz o
  número sem vírgula ("Breast Cancer 2069", ou "377" numa linha só). A regra das remissões exige
  ", 23" no fim da linha, e nenhuma das duas casa.
- **O sinal:** a página sem frase. Nas 283 páginas dos dois sumários não há palavra de 3
  minúsculas ou mais seguida de ponto (o título com "?" não conta); a prosa tem dezenas. E o
  rótulo: 1 ou 2 "CHAPTER N" por página, contra um por capítulo no corpo.
- **A regra:** sai a sequência de páginas seguidas sem frase com 3 rótulos ou mais no começo da
  linha ("CHAPTER 4", "CHAPTER 6: Supraspinal…", também depois do nome da subparte em
  maiúsculas), do primeiro rótulo ao último. A abertura de capítulo sem frase é uma página, com
  um rótulo, e fica. A frase seguida da chamada que o adaptador não tirou ("pain.12 The",
  "pain.[3]") conta como frase. A dedicatória antes e a página da parte depois, sem frase e sem
  rótulo, ficam (correções da code-review).

**2. Colaboradores na página vizinha** (`dominio/paginas_de_lista.py`).
- **O defeito:** a lista do *Bonica* (p. 9 a 54) tem de 3 a 7 colaboradores por página; as 21
  páginas com 3 ou 4 não chegavam ao mínimo de 5, e a p. 54 é só o fim da afiliação de quem
  começou na p. 53 (2.188 palavras no c001).
- **A regra:** sai também a página vizinha de uma página de colaboradores, sem frase, com 2 nomes
  com afiliação ou mais, em corrente para os dois lados; e a página logo depois da lista, sem
  frase e só nas letras da lista, mesmo sem nome. Antes da lista, a página sem nome fica (a
  dedicatória e a foto do *Bonica*, p. 7 e 8); a página de título maior depois dela também.

**3. Espaço menor que o espaço de verdade** (`dominio/caracteres.py`).
- **O defeito:** "PA R T O N E" (os 6 nomes de parte do sumário) e "CHAPTER 11 0" a "11 5" (5
  títulos de capítulo). A letra espaçada vem com 1,7 a 2,3 pt entre as letras de 15 a 21 pt, e o
  pdfminer põe espaço em cada vão; o par apertado pelo kerning ("PA", 1,1 pt; "11", 1 pt) não
  ganha espaço e vira "palavra", e as duas réguas antigas falham: a do espaço falso não tem 3
  vãos entre letras coladas para medir, e a da letra espaçada toma o "PA" por palavra comum.
- **O sinal:** a linha tem espaço de verdade, caractere do PDF, com 8 pt da letra antes à letra
  depois; os espaços que o pdfminer inventa têm menos da metade disso.
- **A regra:** sai o espaço inventado com menos da metade do menor vão de espaço de verdade da
  linha, se todos os inventados da linha cabem nessa régua. Com um vão maior, a linha é
  irregular, e a regra da letra espaçada a lê como antes ("PARTE I", e não "PAR TE I"); a
  palavra separada só pela posição, com o vão do espaço de verdade, fica.

**4. Rótulo no sumário** (`dominio/capitulos.nome_do_capitulo`, usado pelo `adaptadores/epub_simples`).
- **O defeito:** o sumário do EPUB dava a cada capítulo o primeiro título: "Basic
  Considerations" (o nome da parte) no capítulo 1 do *Bonica*, e "CHAPTER 2" sozinho no *Hard
  Parts*.
- **A regra:** se um dos títulos da abertura do capítulo (antes do primeiro texto) traz o
  rótulo, o capítulo leva no sumário o rótulo em caixa normal e o título: o resto do mesmo
  bloco ou, no rótulo sozinho, o título seguinte, sem a pontuação de ligação ("Chapter 1:
  Intellectual Milestones…", "Capítulo 3: A consciência"). O nome da parte e o da subparte,
  antes do rótulo, ficam de fora. Sem rótulo, segue o primeiro título.

**Medido** (`livros/trabalho/medicao-sumario/`, apagada depois do relatório; as páginas lidas
uma vez, e as regras rodadas sobre elas com o código antes e depois):

| Livro | Páginas de lista | Espaço de verdade | Sumário do EPUB | `limpos/` |
|---|---|---|---|---|
| *Bonica* | sumário sem número: 12.678 linhas e 30.981 palavras saem (p. 67 a 194 e 5899 a 6053); colaboradores: 807 → 1.398 linhas, 2.824 → 5.012 palavras (as 21 páginas de 3 ou 4 nomes e a p. 54) | 11 segmentos mudam: os 6 "PART ONE"… do sumário e "CHAPTER 110", 112 a 115 (o 111 já saía inteiro) | 115 de 116 capítulos mudam: todos "Chapter N: título"; a abertura segue "Library of Congress…" | 15.477 → 14.870 segmentos, 1.268.221 → 1.235.019 palavras; 116 capítulos |
| *Practical* | nada muda (o sumário e os colaboradores já saíam pela vírgula e pelos 5 nomes) | 17 trechos em 16 segmentos: o espaço antes de ")", "”" e "’" ("instead of )", "Onuf ’s"), o depois de "”" antes da chamada ("invested.” 17") e dois títulos partidos ("ACUTE PA IN", "PAT IENTS") | nada muda: o capítulo abre no número ("1", "2") | 14.004 segmentos; 820.778 → 820.761 palavras |
| *Hard Parts* | nada muda | 2 linhas: "what if ”" → "what if”" (p. 421 e 425) | os 15 "CHAPTER N" viram "Chapter 1: What Happens When There Are No “Best Practices”?"… | 2 segmentos mudam só por esse espaço |
| *Dalgalarrondo* | nada muda | 3 linhas: "(continuação )", "Psiquiatria ." e a linha pontilhada do sumário, sem o espaço antes da pontuação | nada muda: sem rótulo | 1 segmento muda ("História psiquiátrica (continuação)") |

Das 13.269 linhas novas fora do *Bonica*, nenhuma é prosa: todas estão nas páginas dos dois
sumários e da lista; as 13 com fim de frase são títulos com "?" ("What Is Transdermal Pain?"), e
as mais longas, títulos, autores e afiliações ("Pain Caused by Cancer of the Head and Neck and
Oral and Oropharynx", "KELLY A. BRUNO, HOWARD S. SMITH, IRFAN LALANI, AND CHARLES E. ARGOFF").

**O que fica:**
- o "PART ONE", "PART TWO" e "PART SIX" do corpo no fim do capítulo anterior, antes do nome da
  parte, que abre o capítulo seguinte (como no HEAD);
- o sumário sem número sem rótulo "CHAPTER N" (rótulo por extenso, romano ou só o número), e o
  de uma ou duas páginas, com menos de 3 rótulos;
- o nome no sumário do EPUB não olha se o livro repete o rótulo: num livro em que o capítulo
  abre pelo tamanho e traz "Capítulo 1" na abertura, o sumário passa a "Capítulo 1: título" (o
  *Competente*, que não está neste Mac, não foi medido).

Decidido pelo Mateus (o que sai e o formato do nome, 2026-11-11, pela sessão principal); os
sinais e os limiares são desta sessão e foram à revisão.

### Tratado em português e em espanhol: sumário interno, cabeçalho na altura do número, rótulo, hífen invisível e colaboradores (2026-11-13)

Dois tratados de anestesiologia entraram pelo `importar-pdf` no HEAD `8b8352e`: o *Manica*
(*Anestesiologia*, 4ª ed., pt-BR, 1.601 páginas) e o *Miller* (*Miller Anestesia*, 8ª ed., em
espanhol, 3.787 páginas). O inventário por script do texto limpo achou seis defeitos. O Mateus
decidiu em 2026-11-13 que nos dois vale o corte dos tratados em inglês ("Tratado médico"): saem
tabela, quadro, figura, legenda, bibliografia e colaboradores, agora também pelo rótulo em
português e em espanhol. A bibliografia e as questões de prova do *Manica* são do `limpar` e
ficam para outra rodada.

**1. Capítulos pelo sumário interno do PDF** (`adaptadores/pdf.ler_sumario`,
`adaptadores/sumario_do_pdf.py`, `dominio/sumario_interno.py`,
`dominio/capitulos.dividir_pelo_sumario`).
- **O defeito:** o *Manica* saía com 86 capítulos falsos, o primeiro com 239 mil palavras. O corte
  é o maior tamanho de título em 3 páginas ou mais, e os restos de figura (o texto que o OCR leu
  dentro das imagens, em Times e Helvetica de 20 a 82 pt) passam de 3 páginas e ganham. Sem
  eles ganharia a parte ("Parte I", 55 pt, 12 páginas), e não o capítulo, que abre no número
  ("84.", 30 pt, 98 páginas). E o rótulo "Capítulo N" do gabarito do fim do livro abria 59
  capítulos de poucas linhas.
- **O sinal:** o sumário interno do PDF (os marcadores), que diz a página de cada item. No
  *Manica*, o nível 1 é a parte e o nível 2, o capítulo ("Capítulo 1. …", 95 dos 107 itens; os
  outros são a abertura e um erro de digitação). No *Miller*, o capítulo está no nível 1
  ("Capitulo 1_ …", sem acento) e no nível 2 ("Capítulo 1 - …", os 112 itens), e as seções vão
  do nível 3 ao 9 (7.078 itens).
- **A regra:** o nível do capítulo é o mais fundo em que a maioria dos itens (mais da metade, e 3
  ou mais) começa pelo rótulo de capítulo, "Capítulo", "Capitulo" ou "Chapter" e um número, sem
  olhar a caixa. Todo item desse nível e dos níveis acima dele abre capítulo, na página que o
  sumário diz: o prefácio, a parte e o anexo são irmãos do capítulo. O capítulo abre no primeiro
  título da página (o que vem antes dele na página é o fim do capítulo anterior) ou, na página
  sem título, no primeiro bloco. Continua valendo que o capítulo só fecha depois de ter texto: a
  página da parte fica com o primeiro capítulo dela. Com o sumário interno, o rótulo e o tamanho
  dos títulos não abrem capítulo: o "Capítulo N" do gabarito fica dentro do anexo.
- **O nome no sumário do EPUB** é o título do item, como o PDF o escreve ("Capítulo 1. A
  história da anestesia"), e não o título lido da página, que no *Manica* vem com a caixa
  trocada. Com mais de um item na mesma página, ou com a parte que se junta ao capítulo, vale o
  último: o do capítulo.
- **O nível dos títulos** conta do tamanho mais comum entre os títulos que abrem capítulo (30 pt
  no *Manica*).
- **O sumário que não serve não muda nada:** sem sumário interno, ou sem rótulo de capítulo na
  maioria de um nível (o *Practical*, cujos 970 itens são "1 History…"; o sumário plano do
  *Bonica*, com capítulo e seção no mesmo nível, 115 rótulos em 3.826 itens), vale a regra de
  antes, pelo tamanho e pelo rótulo. O item cujo destino não leva a uma página fica de fora.
- **Entrada não confiável:** o sumário é lido só pelo adaptador, e o percurso é nosso
  (`adaptadores/sumario_do_pdf.py`, que não importa o pdfminer), não o `get_outlines` da
  biblioteca: ele segue referência sem limite e desce um nível por item irmão (os 3.826 itens
  do *Bonica* estouravam a recursão). Cada item e cada nó da árvore de nomes de destino é
  visitado uma vez só, pelo número do objeto, e cada referência é seguida por um número fixo de
  passos. A falha ao abrir o documento não derruba a importação, que já leu as páginas: vira
  aviso no log e sumário vazio.

**2. Cabeçalho na altura do número de página** (`dominio/paginacao.py`).
- **O defeito:** o cabeçalho do *Manica* fica a 6,4% do alto, em MyriadPro negrito de 10 pt, com
  o corpo de 9,3: nas páginas pares, o número e "Anestesiologia"; nas ímpares, o título do
  capítulo e o número. A regra da linha repetida só vale para a letra não maior que a do corpo
  (mais 0,5 pt), porque o título e o número do capítulo também caem na faixa. Só o número saía,
  e 1.573 linhas de cabeçalho ficavam no texto, uma por página.
- **O sinal:** o número de página. A linha da borda na mesma altura do número que segue a
  paginação, na letra dele, é o cabeçalho corrente, repita ou não: o título do capítulo de 3
  páginas aparece uma vez só.
- **A regra:** sai a linha com letra, na faixa da borda ou acima da mancha, maior que a letra de
  rodapé (o que a regra da repetição não olha), a menos de 0,01 da altura do número de página
  da mesma página e a menos de 0,5 pt do tamanho dele, quando isso acontece em 3 páginas ou
  mais. Motivo próprio no registro: "cabeçalho de página na altura do número". O número ao
  lado da coluna (o do *Maudlin*, na margem) não serve de régua: na altura dele mora o corpo.
- **O carimbo da gráfica:** cada página do *Manica* traz no pé, fora da área impressa, o nome do
  arquivo e a data com a hora ("27/09/2017 20:12:36", Helvetica de 6 pt). O nome saía como
  rodapé repetido; a data, que muda a cada página, virava nota (cerca de 400). A linha sem
  letra só se agrupa pelo texto literal, para "2020." e "1999." não formarem um rodapé falso;
  a que tem a forma de data com hora (`dd/mm/aaaa hh:mm`, com ou sem segundos) se agrupa pela
  forma, e sai quando se repete na mesma altura em 3 páginas ou mais.

**3. Rótulo de tabela, quadro e figura em português e em espanhol**
(`dominio/tabelas_e_figuras.py`).
- **O defeito:** a regra da tabela e da figura só conhecia o rótulo em inglês. No *Manica*, a
  legenda ("Figura 1.2 …", MyriadPro de 9 pt), o rótulo do quadro e da tabela ("Quadro 1.1 …",
  "Tabela 8.1 …", MyriadPro de 10 pt) e as células (MyriadPro de 9,7 pt) vêm fora da letra do
  corpo (Times New Roman de 9,3 pt), como nos tratados em inglês.
- **A regra:** o rótulo é também "Figura", "Fig.", "Quadro", "Tabela", "Tabla" e "Cuadro", sem
  olhar a caixa (o versalete do *Manica* sai "FigurA", "quAdro", "tAbelA"), seguido de número
  composto, com ponto ou traço ("1.2", "2-1", "2.7.1"). O que sai é o mesmo da regra em inglês:
  a corrida fora da letra do corpo que tem o rótulo; a menção na letra do corpo e a que continua
  a frase da linha de cima ficam.
- **O Quadro que fica no lugar** ("Quadro no lugar", *Dalgalarrondo*) não muda: lá o rótulo vem
  em letra de título (12 pt, com o corpo de 10), e é ele que abre o quadro que o `adaptar`
  reescreve. O rótulo em português ou em espanhol em letra de título (1,2 vez o corpo ou mais)
  não é rótulo desta regra, e fecha a corrida como qualquer título. O sinal é o do livro: no
  livro didático o quadro é texto com manchete; no tratado, o rótulo é uma legenda pequena
  sobre células.
- **O rótulo em negrito na letra do corpo:** no *Miller*, a figura ("Figura 1-1. …", StoneSans
  de 8 pt) e a tabela ("TABLA 2-1 …", StoneSans de 9 pt, com as células em 8) vêm fora da letra
  do corpo (StoneSerif de 9 pt), mas o título do quadro ("CUADRO 4-1 …") vem em StoneSerif
  negrito de 9,5 pt, a letra do corpo, em uma ou duas linhas, e só o conteúdo vem em StoneSans
  de 8 pt. A linha toda em negrito que abre com o rótulo em português ou em espanhol é rótulo
  também na letra do corpo, e as linhas em negrito da mesma letra logo abaixo continuam o título
  dele, até 6 linhas e sem passar de página (medido: de 1 a 5 linhas nos 308 "CUADRO"). Só para
  esses rótulos: o rótulo em inglês em negrito continua como estava. No livro de corpo em
  negrito a regra não vale: lá a linha em negrito é a prosa.
- **Recusado: juntar "TimesNewRomanPSMT" e "TimesNewRomanPS-ItalicMT" numa família só**,
  tirando o "MT" do fim do nome. No *Manica* não muda linha nenhuma (os mesmos 22.535 e 11.451),
  e no *Bonica* as tabelas deixavam de sair (26.975 → 227 linhas): lá o rótulo "TABLE 1.1" vem
  em negrito na família e no tamanho do corpo, e só não conta como letra do corpo porque o nome
  da fonte em negrito difere. A regressão achou; a família continua como o nome a dá.

**4. Hífen invisível** (`dominio/hifen_da_quebra.mostrar_hifen_invisivel`).
- **O defeito:** uma parte do *Manica* e o *Miller* gravam o hífen como U+00AD, que a voz não
  lê e que cola as duas metades ("pós" + U+00AD + "anestesia", "tabla 6" + U+00AD + "1"). No
  *Manica*, 459 no meio da linha e 1.443 no fim, onde ele é o hífen da quebra. O `blocos` só
  conhecia o do fim da linha, do *Competente*, e o tirava sem consultar o livro.
- **A regra:** o U+00AD seguido de letra ou de algarismo, no meio da linha, é hífen de verdade
  e vira "-". O livro que o usa assim em 3 linhas ou mais usa-o como o hífen dele: o do fim da
  linha também vira "-" e segue para a regra do hífen da quebra, que consulta o livro
  ("pós-" | "operatório" fica com o hífen, porque o livro escreve "pós-operatório"). No livro
  sem U+00AD no meio da linha (o *Competente*), o do fim continua saindo como antes.
- **O número partido na quebra:** "tabla 6-" | "1" e "684-" | "696" se juntam sem espaço, com o
  hífen: algarismo, hífen, fim da linha e algarismo no começo da linha de baixo.

**5. Colaboradores com o nome em maiúsculas** (`dominio/paginas_de_lista.py`).
- **O defeito:** a lista do *Miller* (p. 5 a 19, 5,8 mil palavras) ficava no texto. O nome vem
  em maiúsculas com o título acadêmico ("NOME SOBRENOME, MD"), e a regra só contava o nome com
  minúscula, para o crédito de autor do capítulo não parecer colaborador.
- **A regra:** o nome em maiúsculas com título acadêmico também conta. O que separa a lista do
  crédito de autor continua sendo a linha de baixo: só conta o nome seguido de uma linha que não
  é nome, a afiliação. Os autores do capítulo vêm um embaixo do outro, e a página deles não
  chega a 5 nomes com afiliação.

**6. Versalete com a caixa trocada: fica.** Os dois livros desenham o versalete com a fonte
comum, e o PDF mapeia uma parte das letras pequenas para a maiúscula ("históriA", "BiBliografía",
"FigurA"). Qual letra troca muda de fonte para fonte, e a caixa certa não está no PDF: uma regra
que a refizesse apagaria a sigla de verdade ("TSA", "EEG") e a unidade ("mmHg"). Ver "O que
fica".

**Medido nos dois livros inteiros** (2026-11-13; o antes é o HEAD `8b8352e`, guardado em
`livros/trabalho/<nome>.earbook.antes`; palavras de `limpos/` contadas por espaço, e as do
`importar-pdf`, pelas linhas tiradas):

| Classe | *Manica* | *Miller* |
|---|---|---|
| Capítulos | 86 → 112: 13 de abertura, os 96, os 2 anexos e o material de apoio; o número de 30 pt de cada um dos 96 está na página que o sumário interno diz | 118 → 118: os 112 abrem nos mesmos três títulos de antes; na abertura, a lista de colaboradores e o índice de vídeos saem, e a capa, os créditos e a dedicatória passam a ser capítulos |
| Nome no sumário do EPUB | "Capítulo 1. A história da anestesia" … "Anexo 2. Ilustrações e fotos coloridas" (antes, o primeiro título lido, com a caixa trocada) | "Capítulo 1 - Ámbito de la práctica anestésica moderna" (antes "Capítulo 1: …", pelo rótulo); a abertura leva o nome do item ("5. Prologo") |
| Cabeçalho na altura do número | 1.573 linhas, uma por página; "Anestesiologia" como segmento: 645 → 5 (os 5 são da capa e da última página) | nenhuma: o cabeçalho tem o tamanho do corpo e já saía pela repetição (3.700) |
| Carimbo da gráfica | 395 linhas (rodapé repetido: 2.818 → 3.213); notas sem palavra: 653 → 159 | não tem |
| Tabela e quadro | 22.535 linhas, 96.537 palavras | 35.132 linhas, 141.994 palavras |
| Figura e legenda | 11.451 linhas, 46.248 palavras | 11.355 linhas, 131.672 palavras |
| Segmento que abre em rótulo, sem olhar a caixa | 1.291 → 21 | 1.632 → 11 |
| Hífen invisível no texto limpo | 470 → 0 | 7.619 → 0 |
| Colaboradores | o *Manica* lista os autores sem título acadêmico: ficam (ver "O que fica") | 16 páginas (5 a 19 e 26, o índice de vídeos, que tem a mesma forma), 1.644 linhas, 5.982 palavras |
| `limpos/` | 36.225 → 22.549 segmentos; 1.141.900 → 994.431 palavras (−12,9%) | 39.706 → 29.282 segmentos; 3.488.861 → 3.210.143 palavras (−8,0%) |
| Suspeitos do `preparar` | 1.537 → 547 | 558 → 253 |

**Regressão nos tratados em inglês** (`importar-pdf` e `preparar` para pasta nova, contra as
pastas e os resumos de referência em `livros/trabalho/`):

| Livro | Capítulos | Resumo do `importar-pdf` | `segmentos/` e `limpos/` |
|---|---|---|---|
| *Practical* | 87 → 87 | idêntico, menos o hífen mantido: 1.268 → 1.345 | os mesmos 26.994 e 14.004 segmentos; mudam 77 e 2, todos o número partido na quebra que volta inteiro ("684-" e "696") |
| *Bonica* | 116 → 116 | idêntico, menos o hífen mantido: 1.291 → 1.309 | os mesmos 15.946 e 14.870 segmentos; mudam 16 e 1, pelo mesmo motivo |

O sumário interno dos dois é lido (970 e 3.826 itens) e não serve: nenhum nível tem o rótulo
de capítulo na maioria dos itens.

Procurados os falsos positivos, sobre as páginas lidas uma vez e as regras rodadas nelas:
- **tabela e figura, pela letra de cada linha tirada:** no *Manica*, tudo em MyriadPro (9,7, 8, 9
  e 10 pt), a família das células e das legendas; nenhuma linha em Times New Roman. No *Miller*,
  a figura sai em StoneSans de 8 pt (11.130 das 11.355 linhas, a letra da legenda, que lá tem
  até 9 linhas) e a tabela em StoneSans de 8, 7,5 e 6,5 pt e no StoneSerif negrito de 9,5 pt dos
  títulos de "CUADRO" (664 linhas); nenhuma linha em StoneSerif de 9 pt, o corpo. As linhas
  longas amostradas são legenda, célula, nota de tabela, fonte e item de quadro;
- **páginas de lista:** só as 16 do *Miller*; no *Manica*, nenhuma;
- **cabeçalho:** as 1.573 linhas são o título do livro (785) e os títulos de capítulo, todas em
  negrito de 10 pt a 6,4% (ou 2,9%) do alto;
- **quadro do *Dalgalarrondo*:** os testes de `tests/test_quadro.py` e o teste do rótulo em
  português em letra de título seguem verdes, sem mudança.

**Correções da code-review (esforço alto)**, com o teste visto falhar na asserção antes:
- **o título em negrito do rótulo não tinha fim:** toda linha em negrito na letra do corpo
  depois do rótulo seguia na corrida, também na página seguinte, e num livro de corpo em negrito
  a prosa sairia com a caixa seguinte. Agora são até 6 linhas, na mesma página, e só no livro
  de corpo regular. No *Miller* nada muda (as mesmas 35.132, 11.355 e 1.644 linhas).
- **Medidos e mantidos:** a leitura do sumário do *Miller* (7.079 itens, 6.960 destinos com
  nome) leva 2,9 s; depois do número, o rótulo tirado traz ponto ou maiúscula em 2.362 dos
  2.371 do *Miller*, e no *Manica* os 85 com minúscula são legendas com a caixa trocada
  ("Figura 1.3 deusa…"), que uma regra mais estreita perderia.

**Correções da code-audit**, com o teste junto:
- **o sumário que aponta para si mesmo travava a importação:** com `/Outlines` levando a um
  objeto que é a referência a ele mesmo, o `get_outlines` do pdfminer não voltava, num PDF cujas
  páginas se leem (visto com tempo limite de 15 s; o teste não tem vermelho na asserção, porque
  a falha era não acabar). O mesmo valia para a árvore de nomes de destino. O percurso passou a
  ser nosso, com cada objeto visitado uma vez. De quebra, o sumário plano de mais de mil itens
  é lido inteiro (teste visto falhar: 0 de 1.200) e o sumário em círculo acaba onde o círculo
  fecha. No *Manica* e no *Miller* os itens lidos são os mesmos (124 e 7.079), em 0,5 e 2,5 s.
- **o U+00AD literal num teste** virou a sequência de escape.
- **Fica, de antes:** o PDF cuja árvore de páginas aponta para si mesma trava o `ler_paginas`
  dentro do pdfminer, no HEAD também; o sumário não acrescenta esse caminho.

**O que fica:**
- **a menção que abre a frase numa caixa em outra letra** ("Tabla 6-1 muestra…" depois de uma
  linha que fecha a frase) é lida como rótulo, e o resto da caixa sai; nos dois livros não houve
  caso;
- **o bloco antes do primeiro título da página de abertura** fica no capítulo anterior: 4
  aberturas do *Manica*, 39 palavras (p. 3, 306, 324 e 639), nenhuma no *Miller*;
- **o título do tamanho do número de página, na linha dele, no alto de 3 páginas ou mais** sairia
  como cabeçalho; nos dois livros, as 1.573 linhas são cabeçalho;
- **o livro com 3 U+00AD perdidos no meio da linha** passa a tratar o do fim da linha pela regra
  do "-": antes de maiúscula ou de algarismo, a palavra partida sai com hífen e espaço;
- **a faixa com meia-risca partida na quebra** ("684–" | "696") segue com espaço;
- **a ordem na página de abertura em duas colunas:** em 10 dos 96 capítulos do *Manica* o
  primeiro título não é o número, porque o título do capítulo, na coluna da esquerda, se
  intercala com o texto da direita, ou porque o resto de figura vem antes ("10." colado à linha
  ao lado). O corte está na página certa; a ordem dentro dela é a da regra "Duas colunas";
- **o capítulo que abre no meio da página, depois de outro título:** o corte cai no primeiro
  título da página;
- **o resto de figura:** o texto que o OCR leu dentro das imagens do *Manica* (Times, Helvetica
  e HiddenHorzOCR sem subconjunto, de 4 a 82 pt) continua virando título e nota: 748 títulos
  sem nenhuma palavra ("•", "---", "l"), 1.368 "palavras". Com o sumário interno ele não abre
  mais capítulo;
- **a lista de autores do *Manica*** (p. 6 a 12, 4,6 mil palavras, o nome com o capítulo entre
  parênteses e sem título acadêmico) e **o sumário de papel dele** (p. 19 a 22, 1,5 mil
  palavras, sem pontilhado nem vírgula antes da página): ficam, cada um no seu capítulo
  ("Autores", "Sumário");
- **o rótulo que continua a linha de cima na mesma letra**, sem ponto: a legenda logo abaixo do
  rótulo solto do diagrama (19 no *Manica*) e o "CUADRO" logo abaixo de outro negrito (5 no
  *Miller*);
- **o quadro, a tabela e a legenda na letra do corpo**, o rótulo com número simples ("Figura
  3") e o rótulo em inglês em negrito na letra do corpo;
- **o hífen do fim da linha antes de maiúscula ou depois de letra e antes de número** ("pré-" |
  "2010") segue com espaço; o inventário de "hífen de quebra que sobrou" fica em 18 ocorrências
  no *Manica* (eram 96) e 294 no *Miller* (eram 297);
- **o cabeçalho das páginas de bibliografia do *Miller*** numeradas "49.e1": 80 parágrafos
  "Capítulo N: …" no fim dos capítulos, em 1 ou 2 páginas cada, que não se repetem 3 vezes e
  cujo número não segue a paginação. Saem com a bibliografia, na rodada do `limpar`;
- **o versalete com a caixa trocada:** 159 títulos no *Manica* ("AnestesiA", "cirurgiA") e 231
  no *Miller* ("BiBliografía", "EfEctos"), e as menções no corpo ("QuAdro 1.1", cerca de 450 no
  *Manica*);
- **os livros que não estão neste Mac** (*Dalgalarrondo*, *Hard Parts*, *Competente*,
  *Maudlin*) não foram medidos: o sumário interno deles, se a maioria de um nível trouxer o
  rótulo de capítulo, passa a cortar os capítulos; a legenda "Figura N.N" em letra fora do
  corpo passa a sair; a linha em negrito do corpo que abre com esse rótulo passa a contar.

Decidido pelo Mateus (o que sai, 2026-11-13, pela sessão principal); o sumário interno como
fonte dos capítulos, os sinais e os limiares são desta sessão e vão à revisão.

### Bibliografia pela letra e rótulo com a caixa trocada (2026-11-13)

A rodada do `limpar` nos dois tratados (ADR-0008, "Tratado em português e em espanhol") mediu
antes de desenhar, no HEAD `fee3cb5`, e achou que duas das cinco correções nascem na página e
não se consertam no texto.

**1. A bibliografia sai pela letra** (`dominio/bibliografia_do_pdf.py`).
- **O defeito:** no *Miller*, a bibliografia do fim do capítulo vem em StoneSerif de 7,5 pt, a
  família do corpo (9 pt), uma referência por linha ("1. Bedford PD: Lancet 269:259, 1955."), na
  coluna ao lado do fim da prosa. A coluna de linhas curtas não é texto corrido para a regra
  "Duas colunas" (continua em 0,2 dos pares; o limite é 0,4), a página é lida por altura, e a
  prosa sai intercalada com as referências ("…el descontrol percibido Bibliografía completa
  disponible… del período perioperatorio… 3. Brown JK, et al: …"). Medido: 432 parágrafos, em 88
  dos 112 capítulos, misturam prosa e referência (37,8 mil palavras), e 249 páginas trocam de
  coluna 4 vezes ou mais na leitura. Uma regra do `limpar` não desfaz a mistura: ou a referência
  fica no meio da frase, ou a prosa sai com ela.
- **O sinal:** a letra e o conteúdo, juntos. No *Miller*, 37.706 das 94.811 linhas de StoneSerif
  de 7,5 pt trazem citação de periódico, contra 2 das 263.328 linhas do corpo; no *Manica*,
  7.249 das 32.890 linhas de MyriadPro de 6 pt, contra 3 das 107.103 do corpo.
- **A regra:** na corrida de linhas seguidas fora da letra do corpo e da de título (a mesma
  corrida da tabela e da figura), a **letra das citações** é a letra, menor que a do corpo, com
  mais linhas de citação de periódico ("269:259, 1955", "1980;62:358"; a mesma citação do
  `limpar`, ADR-0008). Sai o **trecho** de linhas nessa letra com **10 linhas de citação ou
  mais**. Até 3 linhas seguidas de outra letra entre duas dele saem junto: o cabeçalho e o
  número das páginas de bibliografia online ("Capítulo 2: …", "47.e1"). Saem também até 2 linhas
  em negrito ou versalete logo antes do trecho: o título ("BiBliografía", "referências").
- **O que fica:** a caixa em outra letra antes da lista, na mesma corrida (no *Miller*, 227
  linhas de StoneSans de 8 pt em 6 corridas: objetivos, listas de recursos); a fonte da tabela e
  a legenda com menos de 10 citações; a referência na letra do corpo, que continua com o
  `limpar`.
- Roda depois da tabela e da figura, e antes dos blocos: a ordem de leitura da página já não vê
  a lista. Cada linha fica registrada com a página e o motivo "bibliografia: letra menor que a do
  corpo, com citações de periódico", e o resumo do `importar-pdf` as conta numa linha própria.

| Alternativa | Ganha | Perde | Por que não |
|---|---|---|---|
| **A. Tirar a corrida pela letra e pelo conteúdo, antes da ordem de leitura** (escolhida) | usa a ordem do pdfminer, em que as linhas da lista vêm seguidas; a mistura some qualquer que seja o desenho da página; não toca na regra das colunas | a remoção fica no registro do `importar-pdf` (página e motivo), e não em `limpeza.json`; no livro com a bibliografia em letra menor, ela deixa de passar pelo `limpar` | — |
| B. Consertar a regra "Duas colunas": a coluna de lista ao lado da prosa é coluna | as referências chegariam inteiras ao `limpar`, que as registra em `limpeza.json` | a regra das colunas foi medida no *Dalgalarrondo*, no *Hard Parts* e no *Competente*, que não estão neste Mac; o sinal geométrico (linhas desalinhadas dos dois lados) acerta por acaso em cerca de 1 de 4 páginas quando a lista começa na coluna da prosa | muda a ordem de leitura de livros que não dá para medir |
| C. Só o `limpar`, pelo conteúdo | nenhuma regra nova na página | tira os 432 parágrafos de prosa misturada, ou deixa as referências dentro deles | falso positivo medido |

**2. A palavra de rótulo com a caixa trocada** (`dominio/caixa_do_rotulo.py`).
- **O defeito:** o versalete do *Manica* mapeia parte das letras pequenas para a maiúscula, e a
  menção no corpo sai "No QuAdro 13.1", "ver FigurA 12.3", "(tAb. 4.2)". Medido: 802 menções
  fora de título (289 "QuAdro", 97 "FigurA", 93 "tAb.", 49 "tAbelA" e outras 26 formas) e 3 em
  título; nenhuma no *Miller*, cujo versalete trocado só está nos títulos.
- **A regra:** nos blocos que não são título, a palavra de rótulo em português ou em espanhol
  ("figura", "fig.", "quadro", "tabela", "tab.", "tabla", "cuadro", com o plural) seguida de
  número, quando tem maiúscula depois da primeira letra sem estar toda em maiúsculas, fica com a
  primeira letra como veio e o resto em minúscula: "QuAdro 13.1" vira "Quadro 13.1", e "tAb. 4.2",
  "tab. 4.2". "QUADRO 2.1", "Quadro 2.1" e "quadro 2.1" não mudam, nem a palavra sem número depois
  ("a FigurA mostra"), nem outra palavra ("AnestesiA").
- **Decisão do Mateus (2026-11-13):** acertar só as palavras de rótulo nas menções; os títulos
  ficam como estão. A caixa certa das outras palavras não está no PDF.
- Mora no `importar-pdf`, depois dos blocos, porque o defeito é do PDF, como o hífen invisível.
  No `limpar` ele pediria um registro novo em `limpeza.json` (texto trocado, e não tirado) e a
  conferência dele. O resumo conta os rótulos acertados.

Decidido pelo Mateus (a bibliografia sai; a caixa só nas menções); os sinais e os limiares são
desta sessão e vão à revisão.

**Medição (2026-11-13, depois do código; HEAD `fee3cb5` → esta mudança).** Um PDF por vez.

| | *Manica* | *Miller* |
|---|---|---|
| Linhas de bibliografia tiradas | 32.272, em 93 trechos (cerca de 208 mil palavras); 88 com o título "referências" | 94.747, em 120 trechos (cerca de 802 mil palavras); 101 linhas de título |
| Blocos (títulos, parágrafos, notas) | 5.060, 17.187, 806 → 4.971, 17.151, 599 | 5.802, 21.358, 2.572 → 5.750, 20.814, 544 |
| Parágrafos com prosa e referência misturadas | 0 → 0 | 432 → 2 |
| Páginas que trocam de coluna 4 vezes ou mais na leitura | 159 → 148 | 372 → 125; entre as que tinham bibliografia, 249 → 2 |
| Linhas com citação de periódico que ficam | 20 (listas curtas) | 29 (fonte de tabela e de figura, em StoneSans) |
| Palavras de rótulo acertadas | 802; ficam 0 fora de título e 3 em título | 0 |
| Hífen de fim de linha (tirados, mantidos) | 34.772, 824 → 33.250, 582 | 48.744, 1.876 → 40.722, 252 |

- **O que saiu é referência:** no *Miller*, 94.548 das linhas são StoneSerif de 7,5 pt, a letra
  das citações; o resto é o título (101) e as linhas de outra letra presas entre duas
  referências (98, quase todas o cabeçalho e o número das páginas online). No *Manica*, 32.152 são MyriadPro de
  6 pt, 88 o título e 32 linhas de MyriadPro de 10 pt entre referências ("Leituras sugeridas").
- **A frase da bibliografia online:** no *Miller*, "Bibliografía completa disponible online en
  expertconsult.com." fica sozinha em 97 dos 118 capítulos, e a regra da marca d'água do
  `limpar` a tira sem regra nova (ADR-0008).
- **Falsos positivos procurados:** a linha logo antes de cada trecho (no *Manica*, "Questão de
  prova", "Estimulação dos receptores…" e outras 3, que ficam; no *Miller*, a frase da
  bibliografia online, em letra do corpo, que fica); a caixa em outra letra na mesma corrida
  (227 linhas de StoneSans de 8 pt em 6 corridas do *Miller*, que ficam); as corridas com 1 a 9
  linhas de citação (26 no *Miller*, 5 no *Manica*: fonte de tabela, que fica). Nenhuma linha na
  letra do corpo sai. A primeira versão levava como título 4 linhas em negrito de outra seção
  no *Manica*: a segunda linha do título passou a exigir a letra da primeira (R2 da revisão).
- **O `limpar` sozinho, medido no EPUB de antes:** com a citação "volume:página, ano" e sem esta
  regra, saem 2.946 segmentos do *Miller* (819 mil palavras), e 455 deles (39 mil palavras)
  levam prosa junto. É a alternativa C.

**O que fica:**
- **a lista curta,** com menos de 10 linhas de citação no trecho: 11 notas com cara de
  referência no *Manica* (2,6 mil palavras; eram 13, com 3,2 mil) e 7 títulos "referências"
  soltos; no *Miller*, 3 títulos "BiBliografía" de capítulos com poucas referências;
- **o título no pé de uma coluna,** quando a lista abre o alto da outra: fica, porque na ordem
  do PDF ele não se distingue do título de outra seção;
- **o cabeçalho da página online antes da primeira referência dela** (3 no *Miller*: "Capítulo
  4: … 72.e1"), e a frase da bibliografia online colada ao fim de um parágrafo (2);
- **o bloco de notas de rodapé com 10 linhas de citação ou mais** sairia inteiro, com o
  comentário que estiver na mesma letra. Não há caso nos dois livros;
- **a ordem das colunas:** a coluna de linhas curtas ao lado da prosa continua lida por altura
  quando não é bibliografia. No *Miller*, 125 páginas ainda trocam de coluna 4 vezes ou mais, e
  110 segmentos trazem o hífen da quebra seguido de uma linha da outra coluna ("…incre- rápido,
  la Palv…"). A causa mora na regra "Duas colunas", e consertá-la pede os livros em que ela foi
  medida;
- **os livros cujo PDF não está neste Mac** (*Practical*, *Bonica*, *Dalgalarrondo*,
  *Competente*, *Hard Parts*, *Maudlin*) não foram medidos: numa reimportação, a bibliografia em
  letra menor com 10 linhas de citação sai na página, e não mais no `limpar`;
- **a chamada de referência que ainda fica colada** no *Miller*: cerca de 360 ("anestésico24,
  105-107", "»106"), de 22.492 tiradas; e 10 rótulos que abrem segmento (5 "CUADRO" abaixo de
  outro negrito, 3 "TABLA" e 2 legendas na letra do corpo). São limites das regras de
  2026-11-10 e 2026-11-13, medidos e não consertados nesta rodada.

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
| O que ficou da Fase 1 | testes: o versalete feito à mão é título e o continua a linha de maiúsculas seguinte, e as maiúsculas de um tamanho só, a minúscula e o símbolo maior não são versalete, e as maiúsculas depois de uma nota continuam nota (`tests/test_versalete.py`, com o adaptador lendo um PDF); a linha de título sobre outra de outro tamanho sai, o texto repetido do mesmo tamanho não é texto escondido, e a linha ao lado e a letra miúda ficam; o `importar-pdf` não abre o capítulo falso (`tests/test_texto_escondido.py`); os verbetes justificados saem coluna a coluna, e a célula com alguma continuação sem margem comum segue linha a linha; o corpo depois da tabela de letra menor é outra faixa, e o destaque de um lado só não a corta, nem a letra menor dos dois lados sem o vão de parágrafo; a coluna de duas linhas ligadas pelo hífen vem antes da outra, e a de duas linhas sem o hífen segue linha a linha (`tests/test_colunas_curtas_e_justificadas.py`); o cabeçalho de duas páginas vizinhas sai, e o de duas com uma entre elas e a linha sem letra em duas vizinhas ficam (`tests/test_paginacao.py`) | portão | volta uma nota de versalete, o capítulo falso, a intercalação do glossário, ou muda um livro sem versalete, texto escondido nem cabeçalho de abertura |
| Cabeçalho fora da faixa e versalete de fonte própria | testes (`tests/test_cabecalho_fora_da_faixa.py`): o cabeçalho acima da mancha que se repete sai, e o título único acima dela fica; o número de página ao lado da coluna, dos dois lados, sai, e dentro da coluna fica; o cabeçalho e o número do tamanho do corpo saem; o cabeçalho largo em letra menor sai; a epígrafe no alto e a linha que passa da margem não deslocam a mancha; a linha repetida no alto da mancha, o texto repetido e o "x" repetido ao lado da coluna ficam; a linha toda em fonte "-SC" ou "-sc" é versalete, e a fonte comum, o "SC" sem separador e a linha que mistura versalete e corpo não são (`tests/test_versalete_de_fonte.py`, com o adaptador lendo um PDF) | portão | volta o cabeçalho no meio da frase, o versalete de fonte própria volta a ser nota, ou muda um livro sem margem larga nem fonte SC |
| Negrito feito à mão | testes (`tests/test_texto_repetido.py`): a cópia do mesmo tamanho sai e fica a primeira; a cópia do texto escondido tem um registro só; o resumo do comando diz o texto repetido; as 9 linhas da p. 2 do Dalgalarrondo viram "Conheça também"; a cópia de uma letra, a deslocada mais de 10%, a de outro tamanho, a de outra altura e o texto diferente ficam; do PDF montado em código, o `importar-pdf` lê a palavra uma vez | portão | a cópia volta a ser lida, ou sai uma linha que não repete outra |
| Tratado médico | testes (`tests/test_caracteres.py`, `tests/test_caracteres_no_pdf.py`): a chamada sobrescrita depois de ponto, colada à palavra, em lista, em faixa, com espaço dentro e com vírgula no fim sai e fica registrada; o expoente depois de algarismo, a carga do íon, a unidade ao quadrado, a letra solta, o subscrito, a letra sobrescrita e o sobrescrito no começo da linha ou depois de espaço ficam; o espaço inventado no vão da letra espaçada sai, e o do vão maior e o do texto comum ficam; do PDF montado em código, com `Ts`, `Tc` e o par apertado, a linha sai certa e traz a família da letra. (`tests/test_tabelas_e_figuras.py`): a tabela sai do rótulo à letra do corpo, também a que abre em título e a que continua na página seguinte na letra das células; a figura sai com o diagrama e a legenda; o título de seção fecha a tabela; a caixa sem rótulo, a menção na letra do corpo, a menção quebrada na linha, o rótulo em português, o crédito do autor na página seguinte, a caixa antes do diagrama e o livro sem família de letra ficam. (`tests/test_paginas_de_lista.py`): o índice, o sumário (também a página curta) e os colaboradores saem inteiros; a página de texto com poucas remissões ou com tabela de doses, a lista de anos, a vírgula decimal, as assinaturas do prefácio e os autores em maiúsculas ficam; o índice que sai ainda prova o hífen do livro | portão | volta a chamada colada, o espaço no nome, a tabela, a figura ou a lista, ou sai texto do corpo |
| Rótulo de capítulo | testes (`tests/test_blocos_capitulos.py`): o rótulo no tamanho da seção abre capítulo, também depois do nome da subparte em maiúsculas, e a parte fica com o primeiro capítulo dela; o rótulo menor que o título vai com o capítulo que abre; o título que só cita um capítulo e a linha do sumário com dois-pontos não abrem; o número grande seguido de "Capítulo 1" continua um capítulo só | portão | o *Bonica* volta a sair por parte, o rótulo fica no capítulo anterior, ou o sumário abre capítulo |
| Sumário sem número, colaboradores vizinhos, espaço de verdade e rótulo no sumário | testes (`tests/test_paginas_de_lista.py`): o sumário sem número e o do número sem vírgula saem, do primeiro rótulo ao último; a abertura sem frase, a página com frase depois do sumário, a prosa com chamada colada, a dedicatória e a página da parte ficam; os colaboradores da vizinha e o fim da lista saem, e a dedicatória, o prefácio e o título maior depois da lista ficam. (`tests/test_caracteres.py`, `tests/test_caracteres_no_pdf.py`): "PA R T O N E" e "CHAPTER 11 0" saem inteiros, também do PDF montado em código; o espaço do tamanho do de verdade fica; a linha irregular continua lida pela regra da letra espaçada. (`tests/test_epub_simples.py`): o rótulo e o título no sumário do EPUB; o rótulo depois do texto, o citado e o do sumário com dois-pontos não dão nome | portão | o sumário ou a lista voltam a ser lidos, sai uma página com frase, a letra espaçada volta partida, ou o sumário do EPUB volta ao nome da parte |
| Tratado em português e em espanhol | testes (`tests/test_sumario_interno.py`): a parte no nível de cima e o capítulo com rótulo abrem capítulo, com o nome do item; a seção abaixo do nível do capítulo não abre; o sumário sem rótulo, o plano, o de dois rótulos e o de três rótulos na mesma página não servem. (`tests/test_capitulos_pelo_sumario.py`): o capítulo abre no primeiro título da página, e o que vem antes fica no anterior; a página sem título abre no primeiro bloco; a parte fica com o primeiro capítulo, com o nome dele; o rótulo dentro do anexo e o resto de figura não abrem capítulo; a abertura em página que saiu inteira abre no bloco seguinte; o nível conta do tamanho que mais abre capítulo. (`tests/test_sumario_do_pdf.py`, com o adaptador lendo um PDF com marcadores montado em código): nível, título e página, pelo destino direto, pela ação e pelo nome; o nome que não existe, a referência a si mesma e a referência a objeto que não existe ficam de fora; o PDF sem sumário devolve vazio sem aviso, e o arquivo que não é PDF, vazio com aviso; o sumário em círculo acaba onde o círculo fecha, o plano de 1.200 itens é lido inteiro, e o sumário e a árvore de nomes que apontam para si mesmos não travam; o `importar-pdf` corta pelo sumário e dá os nomes ao sumário do EPUB, e com sumário que não serve corta como antes. (`tests/test_cabecalho_na_altura_do_numero.py`): o cabeçalho maior que o corpo na altura do número sai sem se repetir; com o número no pé, de outro tamanho, em duas páginas ou sem letra, fica; a linha do corpo na altura do número do pé fica; o carimbo de data e hora sai, e a data sem hora fica. (`tests/test_rotulo_em_portugues_e_espanhol.py`): a legenda, o quadro, a tabela, a "TABLA" e o "CUADRO" em negrito na letra do corpo saem; o rótulo em letra de título, a menção na letra do corpo, a que continua a frase, o número simples e o rótulo em inglês em negrito na letra do corpo ficam. (`tests/test_hifen_invisivel.py`): o U+00AD no meio da linha vira hífen, o do fim só no livro que o usa no meio em 3 linhas ou mais; o número partido na quebra volta inteiro, e a letra antes do hífen segue com espaço. (`tests/test_colaboradores_em_maiusculas.py`): a lista com o nome em maiúsculas sai; três autores com afiliação e o nome sem título acadêmico ficam | portão | o *Manica* volta a sair com capítulo falso, o cabeçalho, o rótulo, o hífen invisível ou a lista voltam a ser lidos, sai texto do corpo, ou muda o quadro do *Dalgalarrondo* |
| Bibliografia pela letra e rótulo com a caixa trocada | testes (`tests/test_bibliografia_do_pdf.py`): 10 linhas de citação em letra menor e o título em negrito saem, registrados com a página; 9 ficam; a citação "ano;volume:página" conta; a linha sem citação no meio sai; o título em letra de título logo acima sai, e o que fica abaixo da lista na página não; a linha do corpo antes fica; a caixa em outra letra antes fica; o cabeçalho da página online entre as referências sai, e 4 linhas de outra letra partem o trecho; dois trechos de 9 ficam; a lista continua na página seguinte; as citações na letra do corpo, em outra família do tamanho do corpo e no PDF sem família ficam; do PDF de ponta a ponta, o resumo conta as linhas. (`tests/test_caixa_do_rotulo.py`): "FigurA 12.3", "QuAdro 13.1", "tAb. 4.2", "tAblA 6-1" voltam à caixa normal no parágrafo e na nota; a caixa normal, as maiúsculas, a palavra sem número, outra palavra e o título não mudam; do PDF de ponta a ponta, o resumo conta as palavras | portão | o *Miller* volta a sair com a prosa intercalada com as referências, sai linha do corpo, ou muda palavra que não é rótulo |
| A escuta ★ | rodar `importar-pdf` + `preparar` num PDF real em `livros/` e contar o que o `limpar` ainda precisa tirar | a cada mudança no conversor | a contagem sobe |

Regra derivada no `AGENTS.md`: a biblioteca de PDF só entra em `adaptadores/`.

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-01 · Aprovado em: 2026-11-01
