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
