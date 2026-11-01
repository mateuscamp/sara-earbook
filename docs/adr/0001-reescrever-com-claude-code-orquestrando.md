# 0001 — Reescrever em Python, com o Claude Code orquestrando e o CLI como ferramenta

**Status:** Aceito
**Data:** 2026-10-31
**Driver ★:** qualidade da escuta no ElevenReader

## Contexto

O objetivo é traduzir EPUBs do inglês para pt-BR e ouvir o resultado no
ElevenReader. A tradução usa a assinatura do Claude, e o projeto será publicado
sob GPL-3.0. A referência é o `jesselau76/ebook-GPT-translator`, com licença MIT,
cerca de 4.500 linhas de Python e sete providers. Na leitura do código dele, em
2026-10-31, apareceram três problemas no núcleo:

- `documents.py:117` extrai `p`, `li` e `blockquote` com `get_text`. Com isso,
  um `<p>` dentro de um `<blockquote>` sai duas vezes e o TTS lê o trecho duas
  vezes. O número da nota (`<sup><a>12</a></sup>`) entra colado na frase. E o
  texto solto em `<div>`, fora de qualquer `<p>`, se perde.
- `_write_epub` monta um EPUB novo a partir de texto plano. Saem o CSS, o
  itálico e a navegação original. Sobra uma entrada por arquivo XHTML.
- O provider `claude` roda um `claude -p` novo para cada bloco, com
  `--max-turns 1`. Por padrão, cada chamada sobe uma sessão inteira do Claude
  Code, com o CLAUDE.md do usuário e os servidores MCP. Para o Claude, cada
  chamada é só uma função de texto: sem julgamento, sem revisão.

Quantum atual: nenhum. O projeto ainda vai existir, e será **um** quantum, um
CLI local que guarda o estado do job em arquivos.

## Drivers

| ★ | Característica | Origem | Como se mede |
|---|---|---|---|
| ★ | Qualidade da escuta | "ouvindo no ElevenReader" | `conferir` encontra 0 marcadores de nota, 0 parágrafos em inglês e 0 grafias divergentes de nome do glossário; e um capítulo de teste ouvido sem tropeço |
| | Integridade | um parágrafo perdido ou duplicado é um buraco no áudio | IDs de segmento na origem = IDs na tradução, por capítulo |
| | Retomabilidade | um livro tem 25+ capítulos e a assinatura tem limite de uso | refazer um job custa 0 traduções para segmentos já validados |
| | Testabilidade sem LLM | quem escreve o código é o agente | a suíte roda offline, sem `claude` no PATH |
| | Legibilidade para agente | Claude Code como ambiente principal | nenhum módulo passa de 400 linhas, e a fronteira de import tem teste |

## Alternativas consideradas

| Opção | Ganha | Perde | Por que não |
|---|---|---|---|
| A. Adotar o ebook-GPT-translator como está | funciona hoje | traz as três falhas acima, que batem direto no ★; não é GPL | falha no ★ |
| B. Fork, relicenciar como GPL-3.0 e podar | ponto de partida pronto; o MIT permite relicenciar mantendo o aviso | o defeito está no modelo de dados (`Block` com texto plano), que é o que sustenta todo o resto; seria podar ~70% de código alheio e ainda reescrever o núcleo | o núcleo teria de ser reescrito de qualquer jeito |
| C. Reescrever com o Claude como provider (`claude -p` em loop Python) | roda sozinho, sem acompanhamento | o agente vira uma função de texto; cada chamada tem cold start com a config do usuário; sem glossário vivo nem revisão | não usa o que o Claude Code tem de melhor |
| D. Reescrever com o Claude Code orquestrando e o CLI Python como ferramenta | limpeza para o ouvido e IDs estáveis no modelo de dados desde o início; substitui o texto no XHTML original, sem perder estrutura; subagente por capítulo; GPL desde o primeiro commit | semanas até a primeira saída boa; não roda sozinho com a mesma facilidade; amarra o projeto ao Claude Code; a orquestração por agente varia mais, então o `conferir` precisa ser forte | — |

## Decisão

Reescrever em Python sob GPL-3.0-or-later e dividir o trabalho em dois lados:

- **Python faz tudo o que é determinístico e verificável:** abrir o EPUB,
  segmentar com ID estável, limpar para o ouvido, guardar o estado do job,
  verificar e remontar o livro substituindo o texto no XHTML original.
- **O Claude Code faz o que pede julgamento:** montar o glossário, traduzir
  lotes de segmentos (um subagente por capítulo, que lê e grava arquivo e não
  passa o livro pelo contexto principal) e revisar o que o `conferir` apontar.

O ebook-GPT-translator fica como **referência de leitura**. Código dele não é
copiado. Se algum trecho for copiado, o aviso MIT vai junto, no arquivo e em
`NOTICE`.

## Consequências

**Ganha:** o ★ é atacado onde nasce, no modelo de dados (nota, número de página
e trecho duplicado são tratados antes da tradução, não remendados depois). A
estrutura do EPUB, e com ela a navegação no ElevenReader, é preservada.

**Perde:** o tempo até o primeiro livro ouvível; o modo "aperta o botão e
volta amanhã"; a portabilidade para outros agentes. A orquestração por agente
varia mais do que um loop Python, e o `conferir` passa a ser a única garantia.

**Aceito conscientemente:** o custo por livro dentro da assinatura ainda não
foi medido. Revisitar esta decisão se um livro de ~100 mil palavras não couber
em uma semana de uso, ou se surgir a necessidade de rodar sem acompanhamento.
Nos dois casos, a opção C entra **por trás da mesma interface de lote**, sem
mexer no resto.

## Governança

| O que verifica | Mecanismo | Onde roda | Falha quando |
|---|---|---|---|
| Integridade | `ai-book conferir` | antes do `montar` (o `montar` recusa) e no CI com fixture | algum ID faltando, sobrando ou repetido |
| Escuta ★ | `ai-book conferir` | idem | aparece marcador de nota, parágrafo com proporção alta de stopwords em inglês ou nome fora do glossário |
| Escuta ★ (manual) | ouvir o capítulo de teste no ElevenReader | a cada mudança no prompt ou na limpeza; responsável: Mateus | houve tropeço audível |
| Fronteira | import-linter e `tests/test_arquitetura.py` (ADR-0002) | portão (`make check`) | o domínio importa `lxml`, uma camada importa a de cima, ou algum módulo importa `subprocess` |
| Offline | suíte com `PATH` sem `claude` | CI | algum teste chama processo externo |
| Licença | teste do cabeçalho SPDX | CI | algum `.py` sem `GPL-3.0-or-later` |
| Tamanho | `test_arquitetura.py` | CI | algum módulo passa de 400 linhas |

Regra derivada no `AGENTS.md`: ver a seção "Contrato".

## Notas

Autor: Mateus, com o Claude Code · Criado em: 2026-10-31 · Aprovado em: 2026-10-31
