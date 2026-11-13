# SPDX-License-Identifier: GPL-3.0-or-later
"""A lista de colaboradores com o nome em maiúsculas sai do áudio (ADR-0004, "Tratado em português
e em espanhol").

No Miller (p. 5 a 19), cada colaborador é o nome em maiúsculas com o título acadêmico e, nas
linhas de baixo, a afiliação. O crédito de autor do capítulo também vem em maiúsculas, mas um
nome embaixo do outro, sem afiliação.
"""

from __future__ import annotations

from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginas_de_lista import MOTIVO_DOS_COLABORADORES, tirar_paginas_de_lista

NOMES = [
    "ANA B. SILVA, MD",
    "JOÃO C. D'ÁVILA-PEREZ, MD, PhD",
    "D. G. SOUZA, MB, BS, FRCA",
    "MARIA DE LOURDES O'NEIL, MD",
    "PEDRO H. LIMA JR., DO",
    "RITA VAN DER BERG, PharmD",
]


def _pagina(numero: int, textos: list[str]) -> Pagina:
    linhas = [
        Linha(texto, x=60.0, fim=270.0, topo=0.05 + 0.013 * n, tamanho=9.0)
        for n, texto in enumerate(textos)
    ]
    return Pagina(numero, tuple(linhas))


def _corpo(numero: int) -> Pagina:
    return _pagina(
        numero, [f"Texto corrido da linha {k} do capítulo, sem nada." for k in range(40)]
    )


def _lista() -> list[str]:
    return [
        linha
        for nome in NOMES
        for linha in (nome, "Assistant Professor of Anesthesiology", "Cidade Inventada, Estado")
    ]


def test_lista_de_colaboradores_com_o_nome_em_maiusculas_sai() -> None:
    limpas = tirar_paginas_de_lista([_pagina(1, _lista()), _corpo(2)])
    assert {r.motivo for r in limpas.remocoes} == {MOTIVO_DOS_COLABORADORES}
    assert [len(pagina.linhas) for pagina in limpas.paginas] == [0, 40]


def test_tres_autores_em_maiusculas_com_afiliacao_na_abertura_do_capitulo_ficam() -> None:
    textos = _lista()[:9] + [
        f"Texto corrido da linha {k} do capítulo, sem nada." for k in range(30)
    ]
    assert tirar_paginas_de_lista([_pagina(1, textos)]).remocoes == ()


def test_nome_em_maiusculas_sem_titulo_academico_nao_conta() -> None:
    textos = [
        linha
        for k in range(8)
        for linha in (f"SEÇÃO NÚMERO {'I' * (k + 1)}, PARTE", "Uma linha de texto comum embaixo")
    ]
    assert tirar_paginas_de_lista([_pagina(1, textos), _corpo(2)]).remocoes == ()
