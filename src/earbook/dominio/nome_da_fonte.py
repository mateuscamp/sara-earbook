# SPDX-License-Identifier: GPL-3.0-or-later
"""O que o nome da fonte do PDF diz da letra: monoespaçada, negrito, versalete e família
(ADR-0004).

O adaptador de PDF entrega o nome cru, como o pdfminer o dá; as regras sobre ele moram aqui. O
pdfminer entrega o nome cru quando ele não é nome PDF: bytes ou número (F1). Esse nome não casa
com regra nenhuma. Saiu de `adaptadores/pdf.py` para ele caber nas 400 linhas do ADR-0001.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from functools import cache

# Medido no spike: o código do "Hard Parts" vem em UbuntuMono.
_FONTE_MONOESPACADA = re.compile(r"mono|courier|code|consol", re.IGNORECASE)
# O estilo vem depois do traço ou da vírgula do nome: "SourceSans3-SemiboldIt" (Competente),
# "MyriadPro-SemiboldCond" (Hard Parts), "Arial,Bold". Sem o separador, "Blackadder" seria
# negrito. ADR-0004, "Subtítulo em negrito do tamanho do corpo".
_FONTE_NEGRITO = re.compile(r"[-,]\w*(?:bold|black|heavy|demi)", re.IGNORECASE)
# O versalete de fonte própria vem num tamanho só, e por isso a letra maior não o acha: no Maudlin,
# "Archer-Medium-SC700" (ADR-0004, "Versalete de fonte própria"). O "SC" vem no fim do nome,
# depois do separador: sem ele, "DiscoSC" seria versalete. Sem caixa, como as outras fontes.
_FONTE_VERSALETE = re.compile(r"[-_]SC\d*$", re.IGNORECASE)
# A família da letra: o nome sem o prefixo do subconjunto ("TCMKGG+") e sem o estilo, depois do
# traço ou da vírgula ("AGaramondPro-Regular", "Arial,Bold"). ADR-0004, "Tabela e figura pela
# letra". O "MT" do fim fica: "TimesNewRomanPSMT" e "TimesNewRomanPS-BoldMT" saem como duas
# famílias, e é por isso que o rótulo "TABLE 1.1" do Bonica, em negrito no tamanho do corpo, não
# conta como letra do corpo (ADR-0004, "Tratado em português e em espanhol", "O que fica").
_ESTILO_DA_FONTE = re.compile(r"[-,].*$")

# A fonte de símbolo cujo PDF diz a letra latina e não o que ela desenha. Só entra na tabela o que
# foi visto na página renderizada do Miller (ADR-0004, "Letra grega da fonte de símbolo"): a
# Mathematical Pi One, com o estilo no nome ("MathematicalPi-One-SC700", "MathPiOneItalic",
# "MathPiOneBold", "MathPiOneBoldItalic"); a Four, que no Miller só tem estas quatro letras; e a
# Symbol, cujas outras letras o PDF já diz em grego. O ponto do "V̇" (U+E03F) não é letra, e fica.
_MATHEMATICAL_PI_FOUR = {"a": "\u03b1", "b": "\u03b2", "g": "\u03b3", "m": "\u03bc"}
_MATHEMATICAL_PI_ONE = {
    **_MATHEMATICAL_PI_FOUR,
    "d": "\u03b4",
    "l": "\u03bb",
    "u": "\u03b8",
    "9": "\u2032",
    "\ue024": "\u2265",
}
_FONTES_DE_SIMBOLO = (
    (re.compile(r"Math(?:ematical)?Pi-?One"), _MATHEMATICAL_PI_ONE),
    (re.compile(r"Math(?:ematical)?Pi-?Four"), _MATHEMATICAL_PI_FOUR),
    (re.compile(r"Symbol(?:$|[-,])"), {"k": "\u03ba", "w": "\u03c9"}),
)


def monoespacada(nome_da_fonte: object) -> bool:
    return _casa(_FONTE_MONOESPACADA, nome_da_fonte)


def negrito(nome_da_fonte: object) -> bool:
    return _casa(_FONTE_NEGRITO, nome_da_fonte)


def de_versalete(nome_da_fonte: object) -> bool:
    """A fonte só de versaletes, pelo "SC" no fim do nome ("Archer-Medium-SC700")."""
    return _casa(_FONTE_VERSALETE, nome_da_fonte)


def sem_subconjunto(nome_da_fonte: object) -> str:
    """ "Times-BoldMT" para "AAAAAA+Times-BoldMT"; vazio se o nome não é texto (F1)."""
    return nome_da_fonte.rsplit("+", 1)[-1] if isinstance(nome_da_fonte, str) else ""


def familia(nomes_das_fontes: Iterable[object]) -> str:
    """A família da letra da maioria dos nomes; vazia se nenhum nome é texto."""
    familias = Counter(
        _ESTILO_DA_FONTE.sub("", sem_subconjunto(nome))
        for nome in nomes_das_fontes
        if isinstance(nome, str)
    )
    return familias.most_common(1)[0][0] if familias else ""


def fim_da_abertura_em_versalete(letras: Iterable[tuple[str, object]]) -> int | None:
    """Onde acaba a abertura em fonte de versalete, entre as `letras` da linha (o texto e o nome da
    fonte de cada uma): logo depois da última letra dela, antes do espaço que a separa do resto,
    que vem na letra do corpo e mudaria a letra da abertura ("do." e o espaço, Miller p. 1730).
    None se a linha não abre em versalete ou é toda nela (ADR-0004, "Subtítulo em versalete no
    começo do parágrafo")."""
    fim, abriu = 0, False
    for i, (texto, fonte) in enumerate(letras):
        # A letra grega do subtítulo vem na fonte de símbolo, e não na de versalete ("ReceptoRes
        # β-adRenéRgicos.", Miller p. 3341): ela não acaba a abertura, nem a abre sozinha.
        if not texto.strip():
            continue
        if not de_versalete(fonte) and not _de_simbolo(fonte):
            return fim if abriu else None
        fim, abriu = i + 1, abriu or de_versalete(fonte)
    return None


def toda_em_versalete(nomes_das_fontes: Iterable[object]) -> bool:
    """Toda letra em fonte de versalete, fora a da fonte de símbolo, que o subtítulo em versalete
    usa para a letra grega; e alguma em fonte de versalete."""
    nomes = [nome for nome in nomes_das_fontes if not _de_simbolo(nome)]
    return bool(nomes) and all(de_versalete(nome) for nome in nomes)


def fonte_do_versalete(nomes_das_fontes: Iterable[object]) -> str:
    """O nome da fonte de versalete mais comum, sem o subconjunto ("StoneSerif-Bold-SC700"), quando
    toda letra é de fonte de versalete (`toda_em_versalete`); vazio nos outros casos."""
    nomes = list(nomes_das_fontes)
    if not toda_em_versalete(nomes):
        return ""
    fontes = Counter(
        sem_subconjunto(nome) for nome in nomes if isinstance(nome, str) and de_versalete(nome)
    )
    return fontes.most_common(1)[0][0]


def _de_simbolo(nome_da_fonte: object) -> bool:
    return _desenhos_da_fonte(nome_da_fonte) is not None


def _desenhos_da_fonte(nome_da_fonte: object) -> Mapping[str, str] | None:
    """A tabela da fonte de símbolo; None nas outras fontes e no nome que não é texto, que o PDF
    malformado pode dar como lista, e a lista não serve de chave do cache."""
    return _desenhos_pelo_nome(nome_da_fonte) if isinstance(nome_da_fonte, str) else None


@cache
def _desenhos_pelo_nome(nome_da_fonte: str) -> Mapping[str, str] | None:
    """Pelo nome sem o subconjunto, guardada por nome: o livro tem poucas fontes, e milhões de
    letras (code-review)."""
    sem_o_prefixo = sem_subconjunto(nome_da_fonte)
    return next((d for padrao, d in _FONTES_DE_SIMBOLO if padrao.match(sem_o_prefixo)), None)


def _casa(padrao: re.Pattern[str], nome_da_fonte: object) -> bool:
    return isinstance(nome_da_fonte, str) and _casa_o_nome(padrao, nome_da_fonte)


@cache
def _casa_o_nome(padrao: re.Pattern[str], nome_da_fonte: str) -> bool:
    return padrao.search(nome_da_fonte) is not None


def letra_desenhada(texto: str, nome_da_fonte: object) -> str:
    """O que a fonte de símbolo desenha no lugar da letra que o PDF diz; o próprio `texto` em
    qualquer outra fonte, e na letra que a tabela não tem (ADR-0004, "Letra grega da fonte de
    símbolo")."""
    desenhos = _desenhos_da_fonte(nome_da_fonte)
    return texto if desenhos is None else desenhos.get(texto, texto)
