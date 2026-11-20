# SPDX-License-Identifier: GPL-3.0-or-later
"""A nota em outra língua que não a do livro (ADR-0008, "Repetição do autor, cópia lado a lado e
nota em outra língua").

Decisão 4 do Mateus no ADR-0011: "fora a nota com o original em inglês do poema que o texto já
leu traduzido"; e a decisão C de 2026-11-20, a nota "****" do Kafka à beira-mar ("No, this my
hand will rather/ The multitudinous seas incarnadine / Making the green one red! (Trad. de Manuel
Bandeira.) (N. da T.)"), como regra geral. A voz do livro lê a outra língua com a pronúncia da
dela.

A língua se reconhece como o `conferir` reconhece o texto que ficou sem tradução: pelas palavras
funcionais do inglês e do espanhol que o português não tem, na proporção que faz o trecho
parecer o original (`lingua_do_original`, ADR-0013). Por isso a regra vale para o livro em
português, contra as duas línguas medidas. O que está entre parênteses não conta: a atribuição
"(Trad. de Manuel Bandeira.) (N. da T.)" é da língua do livro e sai com a nota.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from earbook.dominio.lingua_do_original import ESPANHOL, INGLES, contar
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.traducao import mesmo_idioma

MOTIVO_DA_NOTA_EM_OUTRA_LINGUA = "nota em outra língua que não a do livro"
PALAVRAS_DA_OUTRA_LINGUA = 3
"""A nota sai com 3 palavras funcionais da outra língua ou mais: o verso do Macbeth tem 6 do
inglês ("this", "my", "will", "the", "the", "one") em 15; o título em inglês dentro da nota em
português ("Ver o ensaio The Doors of Perception…") tem 2, e fica."""
_OUTRAS_LINGUAS = (INGLES, ESPANHOL)
_ENTRE_PARENTESES = re.compile(r"\([^()]*\)")


def notas_em_outra_lingua(
    capitulos: Sequence[tuple[str, Sequence[Segmento]]], idioma: str
) -> dict[str, str]:
    """ID → motivo de cada nota em inglês ou em espanhol no livro em português (`idioma`, o do
    EPUB); nada no livro de outra língua ou sem língua declarada ("und")."""
    if not mesmo_idioma(idioma, "pt"):
        return {}
    return {
        segmento.id: MOTIVO_DA_NOTA_EM_OUTRA_LINGUA
        for _, segmentos in capitulos
        for segmento in segmentos
        if segmento.papel is Papel.NOTA and _em_outra_lingua(segmento.texto)
    }


def _em_outra_lingua(texto: str) -> bool:
    sem_parenteses = _ENTRE_PARENTESES.sub(" ", texto)
    for lingua in _OUTRAS_LINGUAS:
        dela, total = contar(lingua, sem_parenteses)
        if dela >= PALAVRAS_DA_OUTRA_LINGUA and dela >= lingua.proporcao * total:
            return True
    return False
