# 0007 — A próxima tradução sem trabalho à mão: capitular no `limpar`, termos declarados e o roteiro numa skill

**Status:** Aceito
**Data:** 2026-11-02
**Driver ★:** qualidade da escuta no ElevenReader (ADR-0001); a tradução de um livro novo não pode
depender do que a sessão lembra

**Bottom line:** a capitular se corrige no `limpar` quando o próprio livro prova a palavra, o
tradutor declara o termo que criou e o `conferir` o cobra, e o roteiro vira a skill
`traduzir-livro`. Inverte se a regra da capitular tocar parágrafo certo num livro medido, ou se
um livro chegar ao `montar` com termo divergente que nenhum tradutor declarou.

## Contexto

Quantum atual: 1 (CLI local + pasta de trabalho em arquivos). Continua 1: nada aqui distribui.

O Tides foi traduzido inteiro em 2026-11-02 (ADR-0006, "O Tides inteiro"), e saiu certo porque a
sessão orquestradora fez muita coisa à mão. A sessão que traduziu listou tudo, com contagem e ID
(`tides-o-que-foi-a-mao.md`, na pasta de notas das sessões): 13 passos manuais, 7 divergências entre
tradutores, 7 furos do `conferir` e 11 lacunas do `tradutor.md`. O Mateus escolheu três frentes,
nesta ordem:

1. **A capitular deslocada.** O ADR-0003 marca a suspeita e dá uma pista (a primeira maiúscula
   sozinha por perto), e a correção ficou com o agente. No Tides, isso virou 25 linhas copiadas à
   mão nos briefs, cada uma com a palavra reconstruída ("awn" → *Dawn*) deduzida pela sessão. O
   `montar --original` lê a letra fora do lugar, e um livro em português, que não passa pelo
   tradutor, não tem caminho nenhum. O próprio ADR-0003 deixou a revisão marcada: "Revisitar, e
   talvez tornar a correção determinística, se o agente acertar quase todas". Acertou 25 de 25.
2. **O mesmo termo traduzido de dois jeitos.** *Stormhammer* saiu "martelo da tempestade" no `c005`
   e "martelo de tempestade" no `c006` e no `c007`. Dois tradutores seguiram políticas opostas para
   nome fora do glossário: o `c007` deixou 4 em inglês, como manda o `tradutor.md`, e o `c006` usou
   4 formas oficiais de memória. "Necrólitos", "Rainha Dragão" e "thane-chefe" foram criados por um
   tradutor só e ficaram sem registro. Nenhuma ferramenta viu: a consistência foi conferida por
   script descartável, e o *stormhammer* só apareceu porque o tradutor do `c005` acrescentou ao
   relatório uma seção que ninguém pediu.
3. **O roteiro mora na memória da sessão.** A divisão dos capítulos, a estimativa de custo (que
   errou para cima, porque usou a amostra como régua), as escolhas da amostra copiadas em 4
   briefs, a rodada de correção, o caminho de saída, o epubcheck e o roteiro de escuta foram feitos
   de memória, alguns com script descartável.

### A capitular, medida no estado vivo (2026-11-02)

A regra abaixo foi prototipada em `livros/trabalho/tides.earbook` e na pasta do *Software
Architecture: The Hard Parts* (o único outro livro com suspeita de capitular: 17, todas falsas).

| Livro | Suspeitas de capitular | Com pista | Corrigidas pela regra | Ficam suspeitas |
|---|---|---|---|---|
| *Tides of Darkness* | 25 | 24 | 24: 23 pela palavra inteira, 1 pelo "A" separado | 1, `c007-s0381` (o "I") |
| *Software Architecture* | 17 | 12 | 0 | 17 |
| Huxley, *Competente* | 0 | — | — | — |

Os casos do Tides que o brief do Mateus cobra:
- **Letra no mesmo segmento:** "stirred, D unable" + "awn, and fog" → "Dawn, and fog" (`c004-s0015`).
- **Letra abrindo o segmento seguinte:** `c004-s0488` ("G demanded."), `c005-s0122` ("A Lothar
  nodded"), `c005-s0201` ("N Dragonmaw clan") e `c007-s0004` ("A Daelin…"). Num deles a letra
  estava no meio de uma frase partida pela página: `c004-s0487` termina em "he" e, sem o "G",
  `c004-s0488` começa em "demanded.". Hoje a junção não vê o par, porque o "G" é maiúscula.
- **O falso amigo:** "From his vantage A point" + "dark figure stood" → "A dark figure stood". "Adark"
  não existe no livro; "a dark" existe.
- **Sem pista:** `c007-s0381`, "t will be", com o "I" em "near the I cliff's edge". O "I" sozinho no
  meio da frase é o pronome em quase todo o livro; não há regra segura.
- **No *Software Architecture*,** a regra não pode tocar "saga A long story of heroic
  achievement." (um verbete de glossário, em que o "A" é artigo de verdade) nem o índice remissivo
  ("abstractness of codebase, 67 … B").

## Drivers

| ★ | Característica | Como se mede |
|---|---|---|
| ★ | Escuta | nenhuma letra solta lida em voz alta no `--original`, no livro em português nem na tradução; o mesmo termo soa igual em todos os capítulos |
| | Nada some em silêncio (ADR-0003) | toda letra devolvida fica em `limpeza.json`, com o ID de onde saiu e o de onde entrou |
| | Repetibilidade | a próxima tradução segue a skill e não precisa de script descartável nem de cópia entre briefs |
| | Custo | nenhuma etapa nova chama o LLM no Python (ADR-0001); a correção de termo custa uma rodada curta, como no Tides (9 segmentos, 16 e 26 segundos) |

## Alternativas consideradas

### 1. Onde a capitular se corrige

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Como hoje: pista no `limpeza.json`, correção no brief do tradutor | nada muda | o `--original` e o livro em português ficam errados; a palavra é deduzida à mão em cada livro | é o trabalho à mão que este ADR tira |
| B. O agente corrige `limpos/` | o Python não decide nada | quebra a regra do ADR-0006 (o agente nunca escreve em `limpos/`) e a correção vira julgamento sem registro | contradiz o ADR-0006 |
| **C. O `limpar` corrige quando a palavra reconstruída existe no próprio livro** | determinístico, testável e registrado; vale para o livro em português; a pista sai do brief | regra nova na limpeza; o livro já traduzido com o código antigo fica com "tradução velha" se for preparado de novo | — |

### 2. Onde a consistência de termo é cobrada

| Opção | Custo | Por que sim ou não |
|---|---|---|
| A. O `conferir` acha o mesmo termo de origem traduzido de dois jeitos, sozinho | alto: para saber que *stormhammer* virou "martelo da tempestade", o Python teria de alinhar palavra de origem com palavra traduzida, sem dicionário e sem LLM (ADR-0001). Cada heurística de alinhamento erraria nos dois sentidos | não |
| B. O `traduzir` sugere termos comuns recorrentes para o glossário, antes da distribuição | médio, e repetido em todo livro: sem lista de palavras comuns do inglês, os candidatos são centenas ("sword", "battle"); com lista, é um arquivo de dados com licença a conferir. O agente lê centenas de candidatos para achar meia dúzia | não agora; fica como melhoria se a opção C deixar escapar termo |
| **C. O tradutor declara o que decidiu fora do glossário, num arquivo, e o `conferir` cobra a declaração** | baixo: um formato pequeno, uma regra no `conferir`; o tradutor já sabe o que criou (o `c005` contou o *stormhammer* sem ninguém pedir) | sim. A divergência aparece na primeira conferência, e a correção custa uma rodada curta |

A opção C não impede que dois tradutores em paralelo escolham formas diferentes; ela garante que
a diferença aparece, com nome e lote, antes do `montar`, e que a forma escolhida passa a ser
cobrada em todos os capítulos pelo glossário. No Tides, a correção de 9 segmentos custou 16 e 26
segundos de tradutor. Prevenir antes da distribuição (opção B) custaria mais, em todo livro.

### 3. Onde o roteiro mora

| Opção | Por que não |
|---|---|
| A. No `AGENTS.md`, como hoje | o `AGENTS.md` entra em toda sessão; o roteiro de tradução só serve na sessão que traduz |
| B. Em `.claude/agents/tradutor.md` | é o roteiro de um tradutor, não da sessão que distribui; mudar o tradutor pede nova escuta (ADR-0006) |
| **C. Numa skill do projeto, `.claude/skills/traduzir-livro/SKILL.md`** | — : é carregada quando o assunto é traduzir um livro, versionada no repositório e lida pela sessão orquestradora e pela filha |

## Decisão

### 1. O `limpar` devolve a capitular deslocada (revisa o ADR-0003 e o ADR-0006)

Depois de marcar as capitulares (ADR-0003), o `limpar` tenta corrigir cada uma que tem pista:
- **Palavra inteira:** se a letra da pista mais a primeira palavra do parágrafo marcado (depois de
  aspas e travessões) formam uma palavra que existe no livro, a letra entra no começo da palavra
  ("awn" → "Dawn"). A comparação ignora caixa e trata ’ e ' como o mesmo apóstrofo
  (`ul'dan` → `Gul'dan`).
- **Letra que é palavra:** se não forma, mas a letra minúscula seguida da primeira palavra existe
  no livro como par de palavras ("a dark"), a letra entra como palavra ("A dark figure"). Como esse
  caso imita o artigo de verdade (o "saga A long story" do *Software Architecture*), ele só vale
  quando a maioria das capitulares com pista do livro foi corrigida pela palavra inteira: é a
  prova de que aquela conversão desloca a capitular. No Tides, são 23 de 24.
- **Ambíguo ou sem prova:** se as duas leituras existem, se nenhuma existe, ou se tirar a letra
  deixaria o segmento vazio, nada muda e a suspeita fica, como hoje.
- **A letra solta sai** com um espaço vizinho, no segmento da pista, que pode ser o próprio
  parágrafo ou um dos dois seguintes (`c004-s0488`: "G demanded." → "demanded.").
- **Junção de novo:** depois de devolver as letras, a junção do parágrafo partido (ADR-0003) roda
  outra vez, porque a letra solta podia esconder uma continuação em minúscula. No Tides, isso junta
  `c004-s0488` em `c004-s0487` ("“Why have you not succeeded yet?” he demanded.").
- **Registro:** cada correção vai para `limpeza.json`, em `capitulares`, com o ID que recebeu a
  letra, o ID de onde ela saiu, a posição e a letra. A suspeita corrigida sai de `suspeitas`; a que
  ficou continua lá, com a pista. O resumo do `preparar` diz quantas foram devolvidas.
- **O `conferir` não muda:** nenhum segmento sai, e origem = mantidos + removidos + juntados
  continua valendo. A junção nova é registrada como as outras.

Efeito no ADR-0006: a pista sai do brief do tradutor, e a seção "Capitular deslocada: corrigida na
tradução" passa a valer só para o livro preparado antes deste ADR. O `tradutor.md` não fala de
capitular.

**O que acontece com `livros/trabalho/tides.earbook`:** nada, se ninguém rodar o `preparar` nele
de novo. O `preparar` recusa pasta que existe, e o livro pronto (`livros/prontos/tides.pronto.epub`)
já tem as capitulares certas, corrigidas na tradução. Preparado de novo numa pasta nova, o texto de
`limpos/` muda em 36 segmentos (a letra que entra, a letra que sai e o `c004-s0487`, que recebe a
junção nova), o `c004-s0488` deixa de ser mantido, e o `conferir` da tradução de hoje acusaria 37
problemas em 24 dos 49 lotes (medido, ver "Medição"). A medição deste ADR roda numa pasta nova em
`livros/trabalho/`, sem tocar na do Tides.

### 2. Termo declarado e cobrado; decisões do livro num arquivo

**O tradutor declara.** Para cada lote, junto com a resposta, o tradutor grava
`termos/<lote>.json`: uma lista de `{"original", "traducao"}` com tudo o que decidiu e que não está
no glossário, nome próprio ou termo comum que volta em outro capítulo (*stormhammer*,
*necrolyte*, *Dragonqueen*). Lote sem termo novo não precisa do arquivo. O formato é o do
glossário, lido pelo mesmo caminho validado (só o adaptador conhece o layout).

**O `conferir` cobra a declaração**, no modo tradução:
- termo declarado que o glossário não tem: um problema por termo, com todas as formas declaradas
  e os lotes ("'stormhammer' fora do glossário: 'martelo da tempestade' (c005-l002), 'martelo de
  tempestade' (c006-l004)"). Quem resolve é a sessão: escolhe a forma e acrescenta ao glossário.
  O `montar` recusa enquanto isso não acontece;
- termo declarado com forma diferente da do glossário: problema no lote, para o tradutor corrigir a
  resposta e a declaração. Os segmentos do capítulo que não usam a forma do glossário já são
  cobrados pela regra de hoje (ADR-0006).
- na amostra (`conferir --amostra`), o termo fora do glossário não é problema: a escolha da
  amostra entra no glossário depois da escuta (decidido na implementação, 2026-11-02). A forma
  diferente da do glossário continua sendo.

Assim o fluxo do *stormhammer* fica automático: o `conferir` mostra as duas formas, a sessão
escolhe uma e a põe no glossário, e o `conferir` seguinte acusa os segmentos que usaram a outra,
em todos os capítulos.

**As decisões do livro moram em `decisoes.md`**, na pasta de trabalho, e não no brief:
- o `traduzir` cria o arquivo com as seções em branco quando ele não existe, e nunca o reescreve;
- quem escreve é a sessão, depois da escuta da amostra. São as seções: nome fora do glossário
  (a política do livro: a localização oficial, como no Tides, ou ficar como no original), tom e
  registro, dialeto, títulos e caixa, tratamento ("Sir", "Lord", "you" plural) e as escolhas da
  amostra;
- todo tradutor lê o arquivo antes do primeiro lote. O Python não lê o Markdown: é texto para o
  agente, como o `tradutor.md`.

**O `tradutor.md` muda nas lacunas que causaram divergência** (seção 4 da lista):
- **Nome fora do glossário:** segue a política de `decisoes.md`; sem política, fica como no
  original. Nos dois casos, entra em `termos/`.
- **Termo criado:** todo termo que pode voltar em outro capítulo entra em `termos/` e no
  relatório, numa seção própria: "termos criados que valem para outros capítulos".
- **Título por extenso e caixa alta:** "ONE" → "Um", "first prologue" → "Primeiro prólogo";
  CAIXA ALTA vira caixa normal, para a voz não soletrar. `decisoes.md` pode dizer outra coisa.
- **Erro do original:** traduz-se pelo que o autor quis dizer, e o ID vai para o relatório.
- **Dialeto:** segue `decisoes.md`. Sem decisão, o tradutor escolhe, aplica a todas as falas do
  mesmo grupo no capítulo e registra a escolha no relatório.
- **Conferir só o seu capítulo:** `conferir --amostra --capitulo cNNN`.

### 3. O roteiro numa skill, e o que era script vira opção

A skill `.claude/skills/traduzir-livro/SKILL.md` cobre, para a sessão que traduz:
- a divisão: um tradutor por capítulo, e o capítulo menor que um lote vai junto com outros;
- a estimativa de custo pela régua do livro inteiro (ADR-0006, "O Tides inteiro": 6,4 tokens de
  saída por palavra, de 4,1 a 7,8 por capítulo, e ~1.160 palavras por minuto por tradutor), e não
  pela amostra, que erra para cima;
- o brief curto: a pasta, os lotes e a ordem de ler o glossário e `decisoes.md`. As escolhas da
  amostra não são copiadas: estão em `decisoes.md`;
- a rodada de correção depois do `conferir`: os termos para o glossário e uma mensagem ao tradutor
  de cada capítulo com problema;
- o `montar --epub livros/prontos/<nome>.pronto.epub`, o epubcheck e o roteiro de escuta.

O que era script descartável e cabe na CLI:
- `conferir --capitulo cNNN`: só os problemas daquele capítulo e dos lotes dele, para o tradutor
  em paralelo não ver os dos outros;
- o `traduzir` imprime as palavras pendentes de cada capítulo, que é o que a estimativa e a
  divisão precisam;
- `earbook minuto <pasta> <ID>…`: em que minuto da escuta cada segmento cai, a 160 palavras por
  minuto, no livro e no capítulo, contando o texto que o `montar` usaria (a tradução, quando
  existe). É a conta que o roteiro de escuta fazia à mão.

Ficam fora, sem caminho na CLI: a medição de tokens pela transcrição do subagente (o layout é do
Claude Code, não do livro) e a pesquisa de nome oficial na web.

### Fronteiras que mudam

- O agente grava `traduzidos/`, `termos/`, `glossario.json` e `decisoes.md`; nunca `segmentos/`,
  `limpos/` nem `pedidos/` (era "só `traduzidos/` e `glossario.json`").
- O Python grava `decisoes.md` uma vez, vazio, e nunca o lê.
- `limpeza.json` ganha a lista `capitulares`.

## Medição (2026-11-02, depois do código)

O `preparar` rodou em pastas novas (`livros/trabalho/tides-adr0007.earbook` e
`huxley-adr0007.earbook`), sem tocar nas pastas traduzidas.

| Livro | Removidos | Aparos | Junções | Capitulares devolvidas | Suspeitas | Mantidos |
|---|---|---|---|---|---|---|
| *Tides* antes (ADR-0003, ADR-0006) | 265 | 165 | 290 | — | 26 | 1.720 |
| *Tides* depois | 265 | 165 | 291 | 24 | 2 | 1.719 |
| *Huxley* antes e depois | 3 | 0 | 0 | 0 | 0 | 142 |

- **Tides:** as 24 devolvidas foram conferidas uma a uma e estão certas, inclusive o "A dark
  figure" e as quatro com a letra no segmento seguinte. A junção a mais é a de `c004-s0488` em
  `c004-s0487` ("“Why have you not succeeded yet?” he demanded."). Ficam suspeitos o
  `c007-s0381` (o "I") e o título "acknowledgments". O `conferir --original` passa.
- **Huxley:** `limpos/` idêntico; o `limpeza.json` só ganha `"capitulares": []`.
- **PDFs do ADR-0004,** pelo `importar-pdf` e o `preparar`: o *Competente* dá 5.083 segmentos e 1
  remoção, e o *Hard Parts*, 3.313 segmentos, 7 remoções, 24 junções e 18 suspeitas (17 de
  capitular), com 0 capitular devolvida. São os números da última tabela do ADR-0004: o "saga A
  long story" e o índice remissivo ficam como estavam.
- **Tradução velha:** com os pedidos e as respostas do Tides copiados para a pasta nova, o
  `conferir` acusa 36 segmentos com "o texto em limpos/ mudou depois do pedido", em 24 lotes, e o
  `c004-s0488` como "traduzido, mas não está em limpos/". Refazer custaria 24 lotes. Por isso a
  pasta traduzida fica como está: o livro pronto já tem as capitulares certas.

### Correções da revisão (2026-11-02)

Da code-review e da code-audit, aprovadas pelo Mateus ("Todos (A–D)"), cada uma com o teste
visto falhar antes:
- **A:** `conferir --capitulo c5`, num livro sem esse capítulo, filtrava tudo e dizia "pode
  montar", com código 0, numa pasta com 37 problemas. Agora o capítulo desconhecido é recusado
  com a lista dos que existem. Sem problema no capítulo, a frase é "nada a corrigir no capítulo
  cNNN", porque o resto do livro não foi conferido.
- **B:** a maioria que libera o "A" separado contava a colada que não chegou a ser devolvida, e
  "saga A long story" virava "A saga long story" num livro sintético. Agora as coladas entram
  primeiro, e só as devolvidas contam.
- **C:** o par que a própria letra solta forma ("Quando O rei") servia de prova da leitura
  separada. Agora esse par é descontado.
- **D:** a marcação e a devolução usam o mesmo prefixo de aspas, travessões e espaço
  (`ABRE_PARAGRAFO`); antes, com espaço inseparável, a letra entrava antes dele. A regex de
  palavra ficou uma só (`PALAVRA`, em `segmento.py`), a `conferir_termos` foi partida em
  funções menores, e um teste cobre a suspeita única quando a junção roda duas vezes. Esse
  teste reprovou com a deduplicação revertida numa cópia descartável (3 suspeitas em vez de 1).

Remedido depois das correções, em pastas novas (`tides-adr0007-revisado.earbook` e
`hard-parts-adr0007-revisado.earbook`): `limpos/` é idêntico ao da primeira medição nos dois
livros. O registro do Tides é o mesmo, agora ordenado por ID.

### A letra que abre frase (2026-11-02)

No Dalgalarrondo (pt-BR, PDF em duas colunas), o número de página de 12 pt virava título
(ADR-0004, "Número de página maior que o corpo"). O texto que vinha depois dele começava em
minúscula, às vezes no meio de uma palavra ("ção de compromisso", de "forma-" na página
anterior), e era marcado como capitular perdida. A pista achava o artigo "A" ou "O" que abre
uma frase próxima, e o livro provava a palavra colada ("A" + "ção" = "Ação"). Foram 9
capitulares devolvidas, todas falsas, que trocam palavra nas duas pontas, em silêncio:
"desejo. A resultante" → "desejo. resultante", e "lho, não via" → "Alho, não via". O ADR-0004
tira o gatilho, mas a regra tem de recusar esse caso sozinha, porque outro título falso
(cabeçalho, rótulo) faria o mesmo.

A diferença está na caixa: a maiúscula no começo da frase é a caixa normal da palavra, e a
capitular deslocada é a maiúscula fora do lugar ("stirred, D unable", "vantage A point").

Medido nas pistas, na base de hoje:
- **Dalgalarrondo:** as 9 devolvidas abrem frase antes de palavra em minúscula ("diagnóstico.
  A validade", "3. A prosopagnosia", "A noção de Eu"), assim como 120 das 136 suspeitas com
  pista. "a", "o" e "e" aparecem milhares de vezes sozinhos e em minúscula.
- **Tides, 24 devolvidas certas:** só "G demanded." (`c004-s0488`) abre frase antes de
  minúscula, e "g" nunca aparece sozinho em minúscula no livro. "A Lothar", "N Dragonmaw" e
  "A Daelin" vêm antes de maiúscula, e as outras 20 estão no meio da frase.
- **Hard Parts:** nenhuma das 16 suspeitas com pista abre frase antes de minúscula ("saga A
  long story" e as letras do índice, sem palavra depois).
- **Huxley, Competente e Learning DDD:** nenhuma pista.

**Decisão:** a letra da pista é palavra no lugar dela, e a capitular não volta, quando três
coisas valem juntas:
- **abre frase:** está no começo do segmento, depois das aspas e travessões, ou depois de fim
  de frase (`. ! ? … : ;`, com aspa ou parêntese que fecha) e de espaço;
- **a palavra seguinte** começa em minúscula;
- **a letra é palavra minúscula no livro:** aparece sozinha, em minúscula, em algum lugar ("a",
  "o", "e").

O Mateus aprovou a regra, junto com a do número de página do ADR-0004 ("Sim, as duas").

As três juntas porque cada uma sozinha recusa uma do Tides: sem a minúscula seguinte, "A
Lothar" ficaria; sem a palavra minúscula, "G demanded." ficaria. É a mesma regra do ambíguo
(seção 1): a letra no lugar é uma terceira leitura, e com duas leituras nada muda. A suspeita
fica no registro com a pista, como hoje.

O que se perde:
- **A capitular de verdade que é palavra** e cai no começo de uma frase, antes de minúscula
  ("…disse ele. O rei" com o "O" da capitular), fica suspeita. É a leitura que imita o artigo,
  e o livro não a distingue; o "Perde" deste ADR já aceitava a letra que é palavra.
- **A letra que aparece em minúscula por outro motivo** ("5 g de", "p. 32") conta como palavra:
  a capitular nessa letra, no começo de frase antes de minúscula, também fica suspeita. Nenhum
  caso nos livros medidos.
- **Fica de fora:** o artigo antes de maiúscula ("A Maria disse") não é recusado e ainda vira
  capitular falsa, se o livro provar a palavra colada. Nenhum caso medido; no Dalgalarrondo, as
  9 vinham antes de minúscula.

Medido depois do código, contra o HEAD `50cd35b` (o protótipo, numa cópia descartável, deu o
mesmo):
- **Só esta regra, no EPUB do Dalgalarrondo de hoje:** capitulares devolvidas 9 → 0; suspeitas
  197 → 206 (as 9 voltam a suspeitas, com a pista).
- **Com a regra do número de página do ADR-0004:** 0 devolvidas e 0 "capitular perdida?". As 9
  palavras voltam certas pela emenda da página ("como uma “forma-” + “ção de compromisso”" →
  "formação de compromisso"; "desejo. A resultante" fica como no livro).
- **Tides, Huxley, Learning DDD, Competente e Hard Parts:** `segmentos/`, `limpos/`,
  `limpeza.json` e `livro.json` idênticos. As traduções do Tides e do Learning DDD não ficam
  velhas.

Correções da code-review e da code-audit, aprovadas pelo Mateus ("A e B"):
- **A, teste:** nenhum teste prendia a aspa e o parêntese que fecham a frase, nem o ":" e o
  ";". Com o mutante que tirava a aspa, a suíte passava, e "…é o desejo.” A resultante" voltava
  a trocar palavra. O comportamento já existia, e o teste passou na hora; ele reprova na
  asserção com cada um dos dois mutantes (3 e 2 casos).
- **B, simplificação:** a guarda recebe a pista, em vez de reler a letra no texto, e olha só o
  fim do que vem antes da letra, em vez de varrer o parágrafo com uma expressão regular. Os
  seis livros saem idênticos.

Registrados, sem correção, porque não têm caso nos livros medidos:
- o ponto de abreviação ("Sr. A") conta como fim de frase e recusa a capitular verdadeira
  depois dele, o que é o lado seguro;
- a guarda olha a letra, e não o parágrafo que a recebe. Num título falso, o artigo antes de
  maiúscula ("compromisso, A Maria disse.") ainda vira "Ação…". A guarda no parágrafo que recebe
  (o parágrafo antes do título não fecha a frase) atacaria a causa: medido, 8 das 9 falsas do
  Dalgalarrondo tinham o anterior aberto, e os 21 do Tides que têm parágrafo antes do título o
  tinham fechado.

## O resto da lista, para o Mateus escolher a ordem

Defeitos que se ouvem e que ficam fora desta rodada:

| Ordem sugerida | Defeito | Ganho | Custo |
|---|---|---|---|
| 1 | **Frase partida pelo cabeçalho de página**, com a continuação em maiúscula ("…had" + "Proudmoore’s"): uns 44 parágrafos do Tides que terminam no meio da frase, e a voz pode pausar (A5 do ADR-0003) | o maior: 44 pausas num livro só, e todo PDF de romance tem o padrão | médio: o `limpar` sabe onde tirou um cabeçalho solto, então pode juntar o par em volta dele mesmo com maiúscula, quando o primeiro não fecha a frase. Muda `limpos/` (tradução velha no Tides, sem efeito em livro novo) |
| 2 | **Linha duplicada** `c004-s0481`, cópia truncada do começo de `c004-s0482` | uma frase lida duas vezes no Tides | baixo: parágrafo que é o começo exato do seguinte sai, registrado. Um caso medido; a regra é genérica |
| 3 | **"Tides of Darkness" em inglês fora dos segmentos**: o sumário do fim (lido), o `dc:title` e o `toc.ncx` (mostrados) | uma leitura em inglês no fim do livro; o título certo na estante do ElevenReader | médio: o título traduzido precisa de fonte (o glossário ou `decisoes.md`) e o `montar` passa a trocar texto fora de segmento, no OPF e no NCX |

## Consequências

**Ganha:**
- O `--original` e o livro em português saem com a capitular certa; o brief perde 25 linhas.
- A divergência entre tradutores aparece no `conferir`, com o termo e os lotes, e a forma
  escolhida passa a ser cobrada em todo o livro.
- As decisões do livro sobrevivem à sessão: a próxima sessão, ou o próximo livro da série, lê
  `decisoes.md` e o glossário.
- A próxima tradução segue uma skill, e não a memória da sessão.

**Perde:**
- Mais uma regra heurística na limpeza. A prova da "maioria" é por livro: um livro com poucas
  capitulares, todas de letra que é palavra ("O rei…", "A casa…"), fica sem correção.
- Uma pasta e um arquivo novos na pasta de trabalho, e o agente grava em mais dois lugares.
- O `montar` recusa enquanto houver termo declarado fora do glossário: o termo de uma ocorrência
  só também tem de entrar.
- A cobrança depende de o tradutor declarar. O termo que ele criou e não declarou só aparece se
  outro tradutor declarar o mesmo original.

**Aceito conscientemente:**
- `c007-s0381` (o "I") continua suspeito. Revisitar se outro livro trouxer capitular em "I" com
  frequência.
- A opção B do item 2 (sugerir termos antes da distribuição) fica de fora. Revisitar se um livro
  chegar ao `montar` com termo divergente que nenhum tradutor declarou.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Capitular devolvida e registrada | testes com EPUB sintético: letra no mesmo segmento, no seguinte, o "A" que é palavra, o "A" sem prova, o "I", a junção depois da devolução, o artigo que abre frase antes de minúscula | portão | a letra fica solta, sai sem registro ou entra onde o livro não prova |
| Contagens dos livros | `preparar` no Huxley e no Tides, comparado com o ADR-0003 | a cada mudança na limpeza | contagem diferente sem explicação |
| Termo declarado | `conferir` no modo tradução | antes do `montar` (recusa) e testes | termo fora do glossário ou com forma diferente |
| Conferir de um capítulo | teste: `--capitulo` mostra só os IDs e lotes do capítulo, e nenhum do glossário | portão | problema de outro capítulo aparece |
| Onde o agente grava | revisão (`code-audit`), como hoje: `termos/` e `decisoes.md` entram na lista | a cada mudança no `tradutor.md` ou na skill | instrução manda gravar fora da lista |
| Escuta ★ (manual) | amostra de novo, por causa do `tradutor.md` | depois desta mudança; responsável: Mateus | tropeço audível |

Regras derivadas no `AGENTS.md`: o agente grava `traduzidos/`, `termos/`, `glossario.json` e
`decisoes.md`; a capitular se corrige no `limpar`; a tradução de livro segue a skill
`traduzir-livro`.

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-11-02 · Aprovado em: 2026-11-02 (pelo Mateus, na sessão principal)
