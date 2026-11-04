# earbook

Preparar livros para **ouvir** no ElevenReader e, quando o livro é em inglês, traduzi-lo
para pt-BR. Até 2026-11-01 o projeto se chamava ai-book; os ADRs 0001 a 0004 usam o nome antigo.
Desde 2026-11-02 o repositório e a pasta se chamam sara-earbook (os projetos de IA do Mateus
ficaram sob o nome Sara); o pacote e o comando continuam `earbook`.
O produto final é áudio, não página: o critério de qualidade é o que soa bem,
não o que fica bonito na tela.

Arquitetura: monólito modular, 1 quantum (CLI local + pasta de trabalho em arquivos).
ADRs em `docs/adr/`. O Claude Code traduz; o Python nunca chama o LLM (ADR-0001).

## Decisões (2026-10-31)

- Esteira (ADR-0003): `preparar → limpar → [traduzir] → conferir → montar`. O `montar` troca o texto no EPUB original e recusa o livro que o `conferir` reprova (ADR-0005). Livro em inglês é traduzido para pt-BR; livro em português só é preparado para o ouvido.
- Tradução (ADR-0006): o `traduzir` exporta pedidos por lote (~2 mil palavras); o subagente `tradutor` (`.claude/agents/tradutor.md`) grava a resposta de cada lote; o `conferir` cobra cada ID, o texto que ficou em inglês e o glossário, e o `montar` declara pt-BR. Nomes do Tides: a localização oficial pt-BR da Blizzard.
- Adaptação (ADR-0009): o `adaptar` exporta pedidos por lote, só de livro em português; o subagente `adaptador` (`.claude/agents/adaptador.md`) responde com grupos, em que N segmentos viram M parágrafos, e lê a página do PDF no Quadro; o `conferir` cobra cada ID, cada número e cada termo raro das fontes, e o que só funciona no papel; o `montar` põe o grupo no lugar do primeiro ID. As decisões de gosto do Dalgalarrondo estão no ADR-0009 ("Decisões do Mateus").
- A limpeza nunca apaga em silêncio: toda remoção fica em `limpeza.json`, com o ID do segmento de origem.
- Capitular deslocada (ADR-0007): o `limpar` devolve a letra quando o próprio livro prova a palavra, e registra em `capitulares`; a que o livro não prova fica suspeita. Nunca vai no brief do tradutor.
- Código, índice e marca d'água (ADR-0008): o `<pre>` que se declara código e o índice que o EPUB marca (`epub:type`, `role`, `data-type`; nunca pelo título nem pelo nome do arquivo) saem no `limpar`, registrados; o Gherkin fica, como parágrafo. Sai também o parágrafo idêntico em metade ou mais dos arquivos do spine, e em 10 ou mais ("OceanofPDF.com").
- Termo e decisão do livro (ADR-0007): o tradutor declara em `termos/<lote>.json` o que decidiu fora do glossário, e o `conferir` cobra. O que a amostra decidiu mora em `decisoes.md`, que todo tradutor lê.
- Entrada: EPUB. PDF entra pelo comando `importar-pdf` (ADR-0004), só para ouvir: sem fidelidade visual, sem OCR, e a biblioteca de PDF só em `adaptadores/`.
- Motor: o Claude Code na sessão, pela assinatura, com um subagente por capítulo. O limite de uso conta.
- Notas de rodapé: o marcador sai do meio da frase e o texto da nota vai para o fim do capítulo.
- Saída: um EPUB **só com a tradução**. O modo bilíngue é proibido, porque o TTS lê as duas línguas.
- Licença: GPL-3.0-or-later; repositório público. O ebook-GPT-translator (MIT) é só referência de leitura.

## Processo (pedido do Mateus, 2026-10-31)

- A skill `arquitetura-ai-first` orienta toda decisão estrutural; fronteira nova exige ADR antes do código.
- Ao fim de toda implementação de código, nesta ordem: a skill `code-review` e, depois dela, a skill `code-audit` (pedido do Mateus, 2026-11-01).
- O asset se julga **ouvindo no ElevenReader**, não lendo lado a lado.
- **Uma escuta de teste só** é o que buscamos, não uma regra absoluta (pedido do Mateus, 2026-11-03).
  - Defeito que a máquina acha se corrige antes da escuta: o inventário por script contra "O que atrapalha o ouvido", no livro montado. Defeito conhecido nunca vai para a escuta.
  - Decisão de gosto (citação, sigla, o que sai do áudio) se toma por texto, com o antes e o depois escritos.
  - A escuta de teste, antes do livro pronto, é só para o que é novo e que só o ouvido julga: uma etapa nova (o `adaptar`), o `tradutor.md` que mudou. O alvo é uma, num trecho que cobre cada decisão; uma segunda só quando a primeira reprovar algo que a máquina não mede.
  - O roteiro do livro pronto não é escuta à parte: são as paradas da leitura que o Mateus já faz.
- O repositório é público, e o `README.md` é a porta dele. Toda mudança de comando, de opção, do que sai do áudio ou da pasta de trabalho atualiza o README no mesmo commit (pedido do Mateus, 2026-11-02).
- A sessão principal só orquestra (pedido do Mateus, 2026-11-01). Cada implementação roda numa sessão filha, com brief completo, e todo o processo deste arquivo vale nela. A filha usa esta mesma pasta, porque `livros/` e `.venv` ficam aqui, e roda uma por vez. Quando ela termina, o que importa volta para a principal: o commit, as medições, as decisões e os limites. Depois a filha é arquivada.

## Livros de medição (o original fica em `~/Documentos/livros/ingles/`)

`livros/` fica fora do git e tem duas pastas (pedido do Mateus, 2026-11-01):
- `livros/trabalho/`: o que ainda está na esteira, de livro de medição ou não (pasta `.earbook`, EPUB do `importar-pdf`).
- `livros/prontos/`: só o EPUB final, que sai do `montar`.

Saída de medição vai para `livros/trabalho/`, nunca para `/tmp` nem para o scratchpad: o Mateus ouve dali.

- Huxley, *The Doors of Perception*: notas de rodapé e sumário. Serve de régua de tradução, porque existe edição brasileira (*As Portas da Percepção*).
- Rosenberg, *Tides of Darkness*: convertido de PDF, com cabeçalho de página, parágrafo partido e capitular perdida. Muito nome próprio de lugar e personagem a preservar (glossário).
- Mudou a limpeza ou a segmentação? Rode `earbook preparar` nos dois e compare as contagens com as do ADR-0003.
- Mudou o `tradutor` ou a tradução? Traduza a amostra do Huxley (`montar --amostra`), compare com a medição do ADR-0006 e peça a escuta ao Mateus.
- PDF: *Competente o Suficiente* (`~/Documentos/Akita/`, pt-BR) e *Software Architecture: The Hard Parts* (`~/Documentos/livros/arquitetura-ai-first/`, en). Mudou o `importar-pdf`? Rode `importar-pdf --epub livros/trabalho/<nome>.epub` e depois `preparar` nos dois e compare com a tabela de ponta a ponta do ADR-0004.

## Comandos

- Setup: `uv sync`.
- Portão: `make check` (`scripts/portao.sh`: lock, formato, lint, supressão, tipos, fronteiras, testes, `uv audit`). O hook Stop roda o mesmo. Rodar antes de declarar qualquer tarefa concluída e mostrar a saída.
- Uso: `uv run earbook preparar livro.epub` → `livro.earbook/`.
- PDF: `uv run earbook importar-pdf livro.pdf --idioma pt-BR [--titulo T] [--autor A]` → `livro.epub`, que segue para o `preparar`. Título e autor vêm do metadado do PDF quando não são dados.
- Tradução: `uv run earbook traduzir livro.earbook [--palavras 2000]` → `pedidos/` e `nomes.json`, e diz os lotes pendentes. Depois: o glossário a partir de `nomes.json`, um subagente `tradutor` por capítulo (capítulo menor que um lote vai junto com outros) e o `conferir`. Antes de um livro inteiro, mostre ao Mateus o custo estimado (lotes e segmentos) e peça o sim.
- Adaptação: `uv run earbook adaptar livro.earbook [--palavras 2000]` → `para-adaptar/` e `siglas.json`, e diz os lotes pendentes. Depois: o glossário das siglas a partir de `siglas.json`, `decisoes.md` com o caminho do PDF, um subagente `adaptador` por capítulo e o `conferir`, que lista também os avisos (termo omitido, descarte por decisão). No livro em adaptação, `--amostra` monta só o adaptado e `--original`, o texto limpo.
- Fim da esteira: `uv run earbook conferir livro.earbook [--capitulo cNNN]` e `uv run earbook montar livro.earbook` → `livro.pronto.epub`. Roteiro de escuta: `uv run earbook minuto livro.earbook <ID>...`. No livro que se traduz, `--amostra` monta só o traduzido (`livro.amostra.epub`) e `--original` monta o texto limpo no idioma do original (`livro.original.epub`), que nunca vai para `livros/prontos/`.

## Livro novo (pedido do Mateus, 2026-11-02)

O Mateus diz o caminho do livro; a sessão o leva até `livros/prontos/`. O original fica onde está.
1. PDF: `importar-pdf <pdf> --idioma <pt-BR|en> --epub livros/trabalho/<nome>.epub`. EPUB: direto ao passo 2.
2. `preparar <epub> --pasta livros/trabalho/<nome>.earbook`. Leia o resumo: segmento suspeito fica no texto e é lido.
3. PDF novo é onde mora a surpresa (cada diagramação é uma). Antes de seguir, faça o inventário por script no livro montado (o `montar --original`, se for en, porque defeito de diagramação traduzido se paga duas vezes) e corrija o que ele achar, sem pedir escuta (ver "Uma escuta de teste só").
4. Em inglês: a skill `traduzir-livro` (`.claude/skills/traduzir-livro/SKILL.md`) leva do `traduzir` ao livro pronto: glossário, `decisoes.md`, custo, tradutores em paralelo, rodada de correção, `montar --epub livros/prontos/<nome>.pronto.epub`, epubcheck e roteiro de escuta. Termo, nome e tom sem precedente vão ao Mateus por texto, na mesma mensagem do custo; a escuta é do livro pronto. A amostra só volta quando o `tradutor.md` mudou ou o livro traz uma escolha que só o ouvido julga e nenhum livro anterior decidiu (pedido do Mateus, 2026-11-02; ADR-0006).
5. Em português: `conferir`, `montar --epub livros/prontos/<nome>.pronto.epub` (o padrão grava ao lado da pasta, em `livros/trabalho/`), epubcheck e `livros/trabalho/roteiro-de-escuta-<nome>.md`.
- Defeito de código achado num livro: pare e relate. A correção é uma sessão filha, com o processo deste arquivo.
- Conversão sem tradução roda na sessão principal; tradução de livro inteiro, numa filha.
- Custo de referência (ADR-0006, Huxley inteiro): ~8 tokens de saída por palavra e ~850 palavras por minuto por subagente; as 16 mil palavras gastaram menos de 1% da semana.

## Fronteiras (ADR-0001)

Verificadas por ferramenta (import-linter e `tests/test_arquitetura.py`):
- `dominio/` importa só stdlib. `adaptadores/` importa `dominio/`, `lxml` e `pdfminer`. `comandos/` importa os dois, mas nenhuma biblioteca de borda.
- `pdfminer` entra só por `adaptadores/pdf.py` (ADR-0004).
- Proibido em todo o pacote: `subprocess`, `socket`, `http`, `requests`, `httpx`.
- Arquivo ≤ 400 linhas; função ≤ 20 linhas (teto 40); primeira linha de todo `.py` é o SPDX.

Verificadas só em revisão (`code-audit`):
- O agente grava só `traduzidos/`, `termos/`, `adaptados/`, `glossario.json` e `decisoes.md`; nunca `segmentos/`, `limpos/`, `pedidos/` nem `para-adaptar/` (ADR-0006, ADR-0007, ADR-0009). O tradutor e o adaptador não gravam `glossario.json` nem `decisoes.md`, que são da sessão. Pedido gravado nunca é reescrito. O Python cria `decisoes.md` uma vez e nunca o lê. O adaptador nunca escreve número que as fontes não têm, nem tira número que elas têm, fora o ano de citação; o termo raro omitido vai em `omitidos`, com o motivo.
- Só `adaptadores/pasta_de_trabalho.py` conhece o layout da pasta de trabalho, e todo JSON lido dela é validado campo a campo por `adaptadores/registros_da_pasta.py` (o tipo `Json`; a única supressão é a do `json.loads`, lá).
- EPUB é entrada não confiável: XML só pelo `PARSER_SEGURO` de `adaptadores/xml_seguro.py`; nenhum caminho sai da pasta de trabalho.
- PDF também é entrada não confiável (pode vir de site de terceiros): toda falha do pdfminer vira `PdfInvalidoError` com o nome do arquivo, menos falta de memória, que passa como veio. O arquivo abre fora do `try`: inexistente ou sem permissão chega como `OSError`; um erro de disco no meio da leitura sai como "não é um PDF válido", com a causa no `from`. O `try` cobre só a biblioteca, nunca a nossa conversão. O que vem do pdfminer com tipo incerto (nome de fonte) é validado no adaptador. O PDF é lido uma página por vez.
- O EPUB que o `importar-pdf` grava carrega texto do PDF: todo texto passa por `escape` e pela retirada do caractere que o XML 1.0 não aceita, e o `preparar` é o teste de contrato do que foi gravado.

## O que atrapalha o ouvido (alvo da limpeza)

- Marcador de nota no meio da frase ("...disse ele.12"). Feito no `preparar`.
- Trecho lido duas vezes (`<p>` dentro de `<blockquote>`). Feito no `preparar`.
- Número de página, cabeçalho repetido, sumário duplicado. No PDF, o cabeçalho de duas páginas vizinhas também sai; o de duas páginas alternadas ainda é lido (ADR-0004, "O que ficou da Fase 1").
- Sumário de papel e propaganda: feitos no `preparar` (ADR-0009). Sai a linha com 5 pontos seguidos e número no fim, quando o capítulo tem 5 ou mais; sai o título "Conheça também" com até 5 parágrafos até o próximo título. Ficam o título "Sumário", os títulos das partes e a linha sem pontilhado; a propaganda com outro título ainda é lida. O pontilhado com espaços (". . . . . 23", 37 linhas no Competente e 20 no Hard Parts) ainda é lido: rodada própria, depois do Dalgalarrondo.
- Índice remissivo, bloco de código e marca d'água repetida: feitos no `preparar` quando o EPUB marca o índice e o código (ADR-0008). O índice sem marca, como o do PDF importado, sai pelo conteúdo: 10 parágrafos de "termo, página" seguidos ou mais (ADR-0008, "Índice pelo conteúdo"). O índice curto e o código do PDF importado ainda são lidos.
- Destaque de margem que repete a frase do texto: feito no `importar-pdf` e no `preparar` (ADR-0004, ADR-0008). O destaque resumido ou reescrito ainda é lido.
- Quadro do PDF que vira nota e vai para o fim do capítulo, longe do texto: feito no `importar-pdf` (ADR-0004, "Quadro no lugar"). O quadro sem rótulo "Quadro N.N" ou "Tabela N.N" em letra de título ainda não é reconhecido.
- Subtítulo em versalete do PDF que vira nota, e texto escondido debaixo de outro que abre capítulo falso: feitos no `importar-pdf` (ADR-0004, "O que ficou da Fase 1"). O versalete de fonte própria, de um tamanho só, ainda vira nota.
- Bibliografia: feita no `preparar` para a do padrão ABNT, 10 referências seguidas ou mais (ADR-0008, "Bibliografia"). A de outro padrão, a lista curta e a do Competente, partida entre nota e parágrafo, ainda são lidas; a do Competente se conserta no `importar-pdf`, onde nasce (decisão do Mateus, 2026-11-03).
- Negrito feito à mão (o mesmo texto desenhado de novo por cima, no mesmo tamanho): feito no `importar-pdf` (ADR-0004, "Negrito feito à mão"). A cópia de uma letra só ainda é lida.
- Alternativa de exercício cuja letra só existe no CSS do `<ol>`: a voz lê "B e C" sem que nada tenha letra. Pendente.
- Algarismo romano em título de capítulo ("Chapter IV").
- Abreviação, URL, tabela e legenda de imagem. A lista de posts do Competente lê a URL inteira.
- Nome próprio traduzido de um jeito num capítulo e de outro no seguinte (precisa de glossário).

## Ciclo de mudança (TDD)

1. Vermelho: um teste, um comportamento, nomeado pelo comportamento. Ver falhar NA ASSERÇÃO.
2. Verde: o mínimo que passa, sem editar o teste. Rodar a suíte inteira.
3. Refatorar com a suíte verde; depois `make check`.

- Bug: primeiro o teste de regressão visto falhando, depois a correção.
- O relatório mostra a linha de falha do vermelho e o resumo do verde.
- Proibido para ficar verde: mudar asserção, `skip`/`xfail`, apagar teste, asserção mais fraca, mock do sujeito.
- EPUB de teste é montado em código (`tests/livro_de_teste.py`), nunca binário no repositório.

## Python (trilho python-on-rails, ADR-0002)

- Dependência entra com `uv add`, nunca `pip install`, e sempre com justificativa no relatório (o que faz que a stdlib não faz, quem mantém). Confira o nome exato do pacote.
- Proibido mexer em `[tool.ruff]`, `[tool.basedpyright]`, `[tool.pytest]` ou `[tool.importlinter]`, e acrescentar ignore, exclude ou linha de base. Regra parece errada? Diga no relatório e pare.
- Supressão só com regra e motivo na mesma linha: `# pyright: ignore[reportX]  # motivo: ...`. `cast` também é supressão.
- Sem `Any` e sem `dict` solto entre funções: miolo em `@dataclass(frozen=True)`. `Any` de biblioteca (`json.loads`) é validado na borda.
- Exceção própria com sufixo `Error` e o valor recebido na mensagem (`mensagem = f"..."; raise XError(mensagem)`). Nada de `except` amplo; relançar com `from`.
- `print` só em `comandos/cli.py` (desvio do ADR-0002). Fora dele, `logging`.
- Valor de retorno ignorado de propósito vai para `_`.

## Estilo

- Código, nomes e mensagens em português. Nomes grepáveis; nada de `utils`, `helper`, `data`.
- Comentário diz o porquê e cita o ADR quando a linha existe por causa dele. Não apagar em refactor.
- Mensagem de erro traz o valor recebido (caminho, href, membro do zip).

## Estrutura

```
src/earbook/
  dominio/      segmento.py (Segmento, IDs), trabalho.py (LivroPreparado), limpeza.py (regras do ouvido),
                pagina.py (Pagina, Linha e letra espaçada do PDF), paginacao.py (cabeçalho do PDF
                pela posição), blocos.py (parágrafo, título, código, nota e quadro do PDF),
                tipo_da_linha.py (o tipo da linha do PDF pela fonte), texto_escondido.py (o texto
                desenhado por baixo de outro e a cópia por cima),
                hifen_da_quebra.py (o hífen do fim da linha do PDF), quadro.py (o Quadro do PDF),
                capitulos.py (capítulo e nível do título), conferencia.py (o conferir), direitos.py (página de direitos autorais),
                metadados.py (título e autor do PDF), traducao.py (lote, pedido, resposta, modo),
                glossario.py (candidatos a nome, termos declarados), conferencia_da_traducao.py,
                adaptacao.py (grupo, lote que não parte frase, textos do montar), siglas.py (siglas
                candidatas), fidelidade.py (número, termo raro e papel), conferencia_da_adaptacao.py,
                capitular.py (a capitular devolvida), escuta.py (o minuto de cada segmento),
                fora_do_audio.py (código, índice, marca d'água, destaque e bibliografia), cabecalho.py (cabeçalho de página),
                colunas.py (a ordem de leitura da página em colunas)
  adaptadores/  xml_seguro.py (parser), pacote_epub.py (zip + OPF), xhtml.py, papel_do_bloco.py (o papel
                pela marcação), pasta_de_trabalho.py (o layout), registros_da_pasta.py (o JSON
                validado campo a campo),
                pdf.py (pdfminer), epub_simples.py (grava o EPUB do PDF)
  comandos/     preparar.py, importar_pdf.py, traduzir.py, adaptar.py, montar.py (conferir e montar), roteiro.py
                (minuto), cli.py
tests/          test_<módulo>.py, test_arquitetura.py, livro_de_teste.py (EPUB), pdf_de_teste.py (PDF),
                linhas_de_teste.py (linhas do PDF já lidas, para os testes de blocos)
```
