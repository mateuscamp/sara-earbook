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

## Consequências

**Ganha:** o livro limpo chega ao ElevenReader com a estrutura do original, e o `conferir` vira
a garantia de que nada sumiu entre a origem e o livro montado.

**Perde:**
- A marcação interna (itálico, negrito, link) some do texto montado. Na tela, o livro fica mais
  pobre; no áudio, nada muda.
- O livro do `importar-pdf` (ADR-0004) leva para "Notas" tudo que tem letra pequena: no
  Competente, também as legendas e a bibliografia.

**Aceito conscientemente:** a nota que mora num arquivo próprio do EPUB (nota de fim de livro)
fica onde está, porque o fim do "capítulo" dela já é ela mesma.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Nada some entre a origem e o livro montado | `conferir` antes de todo `montar` | `montar` (recusa) e testes | ID faltando, sobrando ou repetido |
| O livro montado é lido pela esteira | teste de contrato: EPUB montado → `preparar` → textos e papéis esperados | portão | papel ou texto diferente |
| Escuta ★ (manual) | ouvir o livro de `livros/prontos/` no ElevenReader | a cada mudança no `montar`; responsável: Mateus | tropeço audível |

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-01 · Aprovado em: 2026-11-01
