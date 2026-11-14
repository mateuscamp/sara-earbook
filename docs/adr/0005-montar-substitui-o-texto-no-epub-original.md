# 0005 — O `montar` substitui o texto no EPUB original e recusa o livro que o `conferir` reprova

**Status:** Aceito
**Data:** 2026-11-01
**Driver ★:** qualidade da escuta (ADR-0001); o livro montado é o que o ElevenReader lê

## Contexto

A esteira é `preparar → limpar → [traduzir] → conferir → montar` (ADR-0003), e até aqui só existiam
o `preparar` (que já limpa) e o `importar-pdf` (ADR-0004). O livro limpo ficava na pasta de
trabalho, e o Mateus ouvia a saída do `importar-pdf`, antes da limpeza. O que já estava decidido:
- remontar o livro substituindo o texto no XHTML original, para não perder estrutura nem a
  navegação no ElevenReader (ADR-0001);
- o `montar` recusa o livro quando o `conferir` acha ID faltando, sobrando ou repetido, e cobra
  que cada segmento de origem foi mantido, removido ou juntado (ADR-0001 e ADR-0003);
- a nota de rodapé vai para o fim do capítulo (AGENTS.md).

Ainda não existe a tradução, então o texto final de cada segmento é o de `limpos/`.

## Alternativas consideradas

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Gerar um EPUB novo a partir dos segmentos, como o `importar-pdf` faz | código simples | perde CSS, imagens, capa e a estrutura de arquivos do original; é o defeito que o ADR-0001 apontou no ebook-GPT-translator | contradiz o ADR-0001 |
| **B. Copiar o EPUB extraído e trocar só o conteúdo dos elementos marcados** | mantém tudo o que não é texto; a pasta `epub/` continua sendo a fonte, e o `montar` pode rodar de novo depois da tradução | o texto do segmento entra sem a marcação interna (itálico, negrito, link) | — |
| C. Como B, mas preservando a marcação interna quando o texto não mudou | o livro na tela fica igual ao original | dois caminhos de montagem; a chamada de nota precisa sair de dentro da marcação; nada disso muda o áudio | o ganho é só visual, e o produto é áudio |

## Decisão

- `earbook montar livro.earbook [--epub destino]` grava `livro.pronto.epub` ao lado da pasta
  (pedido do Mateus). O destino que já existe é recusado; a falha no meio apaga o arquivo parcial.
- Antes de montar, o `conferir` (também `earbook conferir livro.earbook`) cobra, por capítulo:
  todo ID de `segmentos/` aparece uma vez só, como mantido (`limpos/`), removido ou juntado
  (`limpeza.json`); nenhum ID mantido ou marcado no XHTML fica fora da origem; toda junção aponta
  para um segmento mantido. Com qualquer problema, o `montar` recusa e lista os problemas.
- Para cada elemento marcado (`data-earbook`): mantido, o conteúdo vira o texto final, sem
  marcação interna; removido ou juntado, o elemento sai, e o contêiner que ficar vazio sai junto.
  A marca `data-earbook` sai de todos. O resto do EPUB (OPF, sumário, CSS, imagens) vai como está.
- No sumário (`<nav>`), nada sai: o texto final entra no link, que mantém o `href`, e o item não
  recebe âncora de fora. Tirar um item do sumário na limpeza não tem efeito no livro montado: sem o
  item, ou sem o `<nav>`, o leitor perde a navegação.
- A nota de rodapé (papel `nota`) sai do lugar e entra no fim do capítulo, sob um título
  "Notas", como parágrafo comum (pedido do Mateus): o ElevenReader a lê depois do texto, sem
  interromper. Marcada como nota, ele poderia pular, e não sabemos o que ele faz.
- O texto final vem de `limpos/`. Quando a tradução existir, vem do segmento traduzido; o
  resto da montagem não muda.

### Medição (2026-11-01)

O `conferir` passou nas três pastas de trabalho de `livros/trabalho/`. Cada livro montado foi lido de novo pelo `preparar`, que deve achar só os segmentos mantidos, mais um título "Notas" por capítulo com nota:

| Livro | Montado | Mantidos | Notas no fim | De novo pelo `preparar` |
|---|---|---|---|---|
| *Competente o Suficiente* (pt-BR, do `importar-pdf`) | `livros/prontos/`, 0,2 s | 4.636 em 23 capítulos | 337 | 4.659 segmentos (4.636 + 23 "Notas"); 0 remoções; 47 junções e 3 suspeitas, todas dentro de "Notas": pedaços da bibliografia que o `importar-pdf` já parte entre nota e parágrafo (ADR-0004, "nota que não é nota") |
| *The Doors of Perception* (EPUB, en) | `livros/trabalho/` | 145 em 5 capítulos | 7 | 146 (145 + 1 "Notas"); 0 remoções, 0 junções |
| *Tides of Darkness* (EPUB, en) | `livros/trabalho/` | 1.727 em 7 capítulos | 0 | 1.727; 0 remoções e 0 junções (os 258 cabeçalhos e os 290 parágrafos partidos saíram resolvidos); 26 suspeitas, as capitulares que ficam com o agente |

O trecho fora de segmento de cada livro de EPUB (`www.epubbooks.com`, `Tides of Darkness`) é o mesmo antes e depois da montagem. Os livros em inglês ficam em `livros/trabalho/`, porque o produto deles só fica pronto depois da tradução.

Correções da code-review (2026-11-01), cada uma com o teste visto falhar antes:
- **Âncoras:** trocar o texto levava junto as âncoras de dentro do elemento, e tirar o elemento levava as dele. Um sumário que aponta para `cap.xhtml#calibre_toc_3`, dentro do título, perderia o destino. Agora todo `id` do capítulo continua no capítulo montado, como `<a id>` vazio. O Huxley perdia 4 âncoras referenciadas (as das notas) e agora não perde nenhuma.
- **Texto que o XML não aceita:** o lxml recusava o texto sem dizer o arquivo nem o segmento. O `conferir` agora acusa o caractere com o ID (`texto com caractere que o XML não aceita: U+000C`), e a regra mora em `dominio/segmento.py` (`FORA_DO_XML`), a mesma do gravador do `importar-pdf`.
- **Link simbólico:** a pasta `epub/` é editada pelo agente e pela tradução, e um link para fora levaria um arquivo qualquer do computador para dentro do EPUB. O empacotamento recusa o link, com o caminho.

Registrados sem correção: o `conferir` e o `montar` leem e analisam cada XHTML e cada `limpos/` duas vezes (0,2 s no Competente); e as funções `conferir`, `montar` e `montar_xhtml` passam da meta de 20 linhas do AGENTS.md, dentro do teto de 40.

Correções da code-audit (2026-11-01), cada uma com o teste visto falhar antes (pela asserção, ou com o defeito plantado numa cópia quando o comportamento já existia):
- **A1, sumário EPUB3:** o item do `nav` é segmento, e trocar o texto tirava o `<a href>`. O Huxley montado ficava com `<li>Epigraph</li>`, e o epubcheck acusava 4 erros novos. Dentro do `<nav>`, a marcação agora fica (e veja N1 a N3 abaixo).
- **A2, segmento no capítulo errado:** o `conferir` comparava origem e mantidos no livro inteiro, e o `montar` lê os textos do `limpos/` de cada capítulo. Um parágrafo posto no `limpos/` de outro capítulo passava e sumia do livro montado. Agora o `conferir` cobra por capítulo: `mantido no capítulo c001, mas é do c002`.
- **A3, nota de fim de livro:** o código levava para "Notas" também a nota que mora num arquivo só de notas, contra a decisão acima. O capítulo que só tem notas e títulos agora deixa cada nota no lugar (`notas_para_o_fim`, em `dominio/segmento.py`).
- **A4, âncora onde o XHTML não aceita:** `<a id>` solto no `<ul>` ou no `<body>` do EPUB2 é inválido. A âncora do elemento tirado vai para o começo do próximo bloco mantido; depois do último, para o fim dele; sem bloco mantido no capítulo, para um `<div>`.
- **A5, caminho do capítulo:** com `"arquivo": "OEBPS/./ch01.xhtml"`, o capítulo saía cru e o comando dizia que tinha montado; com `../`, o `conferir` lia fora da pasta. A leitura recusa o caminho fora da forma normal e o `id` fora de `cNNN`, e o empacotamento recusa a troca que não achou arquivo.
- **A6:** JSON que não é UTF-8, ou aninhado demais, falhava sem o caminho (ou com traceback); agora é `PastaDeTrabalhoInvalidaError` com o arquivo.
- **A7:** a leitura juntava as repetições do `limpeza.json` antes de contar. As remoções e as junções (pares ID, destino) chegam como estão, e o `conferir` acusa a repetida.
- Testes novos para os mutantes que sobreviviam: âncora neta, marca repetida no XHTML e as checagens de forma do JSON.

Correções da pós-auditoria (2026-11-01), cada uma com o teste visto falhar antes:
- **N1:** a correção A1 deixava o item do sumário com o texto original: no livro traduzido, o sumário sairia em inglês, a leitura bilíngue que o projeto proíbe. O texto final agora entra no link, que mantém o `href`.
- **N2:** tirar os itens do sumário esvaziava o `<nav>`, que saía inteiro, e o epubcheck acusava "Exactly one toc nav element must be present". Dentro do `<nav>`, nada sai.
- **N3:** a âncora tirada antes do sumário entrava no `<li>` (`<a id>` sem texto no `<nav>`, dois erros novos no epubcheck). O item do sumário não recebe âncora de fora.
- **N4:** testes para o que já funcionava e estava sem proteção: a âncora no começo do bloco (no fim, o salto pularia o parágrafo), o `id` `c001/../x`, o `arquivo` `..` e a junção repetida na leitura e no `conferir`.
- **N5:** o `json` recusa inteiro de mais de 4.300 algarismos com um `ValueError` simples, que saía sem o caminho; todo `ValueError` da leitura vira `PastaDeTrabalhoInvalidaError` com o arquivo.

Depois das correções, o epubcheck acusa nos três livros montados os mesmos erros dos originais (mensagens comparadas sem linha e coluna): 0 no Competente; o mesmo OPF-096 no Huxley; e no Tides os mesmos 9 RSC-005, 6 de `img` sem `alt`, 1 de `img` fora de lugar, 1 de atributo `name` e 1 de `id` inválido no `toc.ncx`.

Limite registrado pela pós-auditoria: o arquivo de notas de fim de livro com um parágrafo de introdução deixa de ser "só notas e títulos", e as notas vão para "Notas", separadas dos subtítulos de capítulo. Nenhum dos três livros tem esse caso.

Registradas pela auditoria, sem caso nos livros: marca aninhada dentro de outro elemento marcado perde o texto de dentro (o `preparar` só marca folha); `<img>` dentro de um elemento mantido some com a marcação interna (não muda o áudio; nos três livros a contagem de imagens ficou igual); destino do `--epub` dentro da própria pasta `epub/` entra no pacote.

### Capítulo sem texto fora do EPUB montado (2026-11-13)

**Contexto.** O `preparar --sem-capitulo cNNN` (ADR-0008) tira o capítulo inteiro do áudio, mas o
`montar` trocava só o texto: o arquivo do capítulo continuava no livro, com o corpo vazio, e o
item dele no sumário também. No *Manica*, o leitor ainda listava "Autores", "Sumário", "Anexo 1" e
"Anexo 2", quatro itens que levam a uma página em branco. Decisão do Mateus (2026-11-13): o
capítulo vazio fica fora do EPUB montado.

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Deixar o arquivo vazio e tirar só o item do sumário | mexe em um arquivo só | o leitor ainda passa por uma página em branco entre dois capítulos; o arquivo vazio continua no pacote | resolve metade |
| **B. O `montar` tira o arquivo do pacote, do manifesto, do spine e do sumário (`nav` e `toc.ncx`)** | o livro montado só tem o que se ouve; a pasta de trabalho não muda | o `montar` passa a reescrever o OPF e o sumário, que antes iam como estavam | — |
| C. O `preparar` tira o arquivo da pasta `epub/` | o `montar` não muda | a pasta `epub/` deixa de ser a cópia do original; o `conferir` cobra cada ID da origem contra o XHTML marcado, e o arquivo sumido quebraria a conta | contradiz "a pasta `epub/` continua sendo a fonte" |

**Decisão (B).**
- **Qual capítulo sai:** o que o `preparar --sem-capitulo` declarou fora do áudio. O `montar` o
  reconhece pelo registro: todo segmento dele está em `limpeza.json` com o motivo "capítulo fora
  do áudio: pedido no preparar" (`dominio/fora_do_audio.capitulos_declarados`), e nenhum ficou em
  `limpos/`. Vale no livro pronto, no `--original` e no `--amostra`: o capítulo declarado não tem
  texto limpo, nem para traduzir.
- **O que não sai:** o capítulo que nunca teve segmento (a capa, a página só de imagem); o
  arquivo que é o sumário do EPUB 3 (o item `nav` do manifesto), mesmo declarado, porque sem ele
  o EPUB é inválido; na amostra, o capítulo que ainda não tem tradução ou adaptação, que não está
  vazio, só não foi feito (ADR-0006 e ADR-0009: "a amostra monta só o traduzido").
- **O capítulo que outra regra da limpeza esvaziou** (o do índice remissivo marcado no EPUB, o
  que só tinha a página de direitos) **continua no livro, vazio, como antes.** A regra geral
  ("sai todo capítulo que ficou sem segmento") foi escrita primeiro e recusada nesta rodada: o
  teste `test_livro_montado_nao_tem_codigo_nem_indice` (ADR-0008) cobra o capítulo do índice
  vazio no livro montado, e o processo proíbe mudar asserção de teste existente para a mudança
  passar. Fica como decisão do Mateus (abaixo, "O que fica").
- **O que o `montar` reescreve,** além dos capítulos: no OPF, saem o `<item>` do manifesto, o
  `<itemref>` do spine e a `<reference>` do `<guide>` que apontam para o arquivo; no sumário do
  EPUB 3 (todo `<nav>` do arquivo `nav`: sumário, `landmarks`, lista de páginas), sai o `<li>`
  cujo link aponta para o arquivo; no `toc.ncx`, saem o `<navPoint>`, o `<pageTarget>` e o
  `<navTarget>`. O item que sai e tem itens filhos de outro arquivo dá o lugar a eles: os filhos
  sobem um nível. A lista que ficar vazia sai com o `<nav>` dela (ou com o `<pageList>`, o
  `<navList>`, o `<guide>`).
- **O `playOrder` do `toc.ncx`** é renumerado em sequência, na mesma ordem, e os itens que
  dividiam um número continuam dividindo: o epubcheck recusa a sequência com salto ("playOrder
  sequence has gaps").
- **O que o `montar` recusa:** o livro em que todo capítulo ficaria de fora, e o livro cujo sumário
  ficaria sem nenhum item. O spine sem `<itemref>` e o `<nav>` sem `<li>` são inválidos, e gravar
  um EPUB que o leitor recusa seria pior do que dizer por quê.
- **Sem capítulo declarado, nada muda:** o OPF e o sumário vão para o livro byte a byte, como
  antes.
- **Nada some calado:** o resumo do `montar` diz quantos capítulos ficaram de fora e quais
  ("4 capítulos sem texto ficaram fora do EPUB: c006, c013, c110, c111"), e `Montagem.capitulos`
  conta os que foram para o livro. Cada segmento desses capítulos já está em `limpeza.json`, com o
  motivo.
- **Onde mora:** a escolha do capítulo, em `comandos/montar.py`; o OPF, em
  `adaptadores/pacote_epub.py`; o sumário (`nav` e `toc.ncx`), em `adaptadores/sumario_do_epub.py`,
  novo, porque o `xhtml.py` está no limite de linhas e o sumário é outro assunto. Tudo pelo
  `PARSER_SEGURO`; nenhum caminho sai da pasta de trabalho.

**O que fica (declarado).**
- **O capítulo esvaziado por outra regra da limpeza** fica no EPUB, com o corpo vazio e o item
  no sumário. Estender a regra a ele é tirar a condição do motivo em `_sem_texto` e trocar uma
  asserção de `tests/test_codigo_e_indice.py` (`[[…], []]` por `[[…]]`): decisão do Mateus.
- O link para o capítulo que saiu, fora do sumário (num `<a href>` do corpo de outro capítulo que
  o `montar` não troca, num trecho fora de segmento): o destino some e o epubcheck acusa o link
  quebrado. O `montar` já tira a marcação interna de todo segmento, link inclusive, e nenhum livro
  medido tem o caso.
- O `<meta refines="#id">` do OPF que descreve o item tirado fica órfão. Nenhum livro medido tem.
- Com o sumário (`nav`) no spine, o item dele que aponta para o capítulo declarado é segmento
  mantido e sai do livro com o `<li>`: continua contado em "segmentos" no resumo do `montar` e,
  na amostra, em "itens do sumário no original" (achado da code-review). Nenhum livro medido
  tem o `nav` no spine e capítulo declarado.

## Consequências

**Ganha:** o livro limpo chega ao ElevenReader com a estrutura do original, e o `conferir` vira
a garantia de que nada sumiu entre a origem e o livro montado.

**Perde:**
- A marcação interna (itálico, negrito, link) some do texto montado. Na tela, o livro fica mais
  pobre; no áudio, nada muda.
- O livro do `importar-pdf` (ADR-0004) leva para "Notas" tudo que tem letra pequena: no
  Competente, também as legendas e a bibliografia. O conteúdo do quadro com rótulo ("Quadro
  5.1") deixou de ser nota e fica no lugar (ADR-0004, "Quadro no lugar", 2026-11-03), e o
  subtítulo em versalete feito à mão também (ADR-0004, "O que ficou da Fase 1", 2026-11-03).

**Aceito conscientemente:** a nota que mora num arquivo próprio do EPUB (nota de fim de livro)
fica onde está, porque o fim do "capítulo" dela já é ela mesma.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Nada some entre a origem e o livro montado | `conferir` antes de todo `montar` | `montar` (recusa) e testes | ID faltando, sobrando ou repetido |
| O livro montado é lido pela esteira | teste de contrato: EPUB montado → `preparar` → textos e papéis esperados | portão | papel ou texto diferente |
| O capítulo declarado fica fora do EPUB | testes (`tests/test_capitulo_sem_texto_fora_do_epub.py`): o arquivo sai do pacote, do manifesto, do spine, do `nav` e do `toc.ncx`, com os filhos de outro arquivo subindo um nível, a lista vazia e o `landmarks` vazio saindo, a referência do `<guide>` também, e o `playOrder` sem salto; vale no original e na amostra; o resumo e a `Montagem` dizem quais saíram; o livro montado volta pelo `preparar` só com os capítulos que se ouvem; o capítulo que nunca teve segmento, o `nav` no spine, o capítulo esvaziado por outro motivo e o capítulo sem tradução na amostra ficam; sem capítulo declarado o OPF e o sumário vão byte a byte; o livro em que nada ficaria e o sumário que ficaria vazio são recusados. O epubcheck, rodado à mão no livro montado | portão; epubcheck a cada livro | o capítulo vazio fica no livro, ou sai o que não foi declarado |
| Escuta ★ (manual) | ouvir o livro de `livros/prontos/` no ElevenReader | a cada mudança no `montar`; responsável: Mateus | tropeço audível |

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-01 · Aprovado em: 2026-11-01
A seção "Capítulo sem texto fora do EPUB montado" (2026-11-13) executa a decisão do Mateus do
mesmo dia (o capítulo vazio fica fora do EPUB montado), levada pela sessão principal. O alcance
(só o capítulo declarado no `--sem-capitulo`) e o mecanismo vão à revisão dele.
