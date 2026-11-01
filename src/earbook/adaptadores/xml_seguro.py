# SPDX-License-Identifier: GPL-3.0-or-later
"""O único parser XML do projeto. EPUB é entrada não confiável (ADR-0001)."""

from __future__ import annotations

from lxml import etree
from lxml.etree import _Element  # pyright: ignore[reportPrivateUsage]  # motivo: o lxml não exporta tipo público para o elemento

type Elemento = _Element

# Sem entidade externa, DTD ou rede: fecha XXE e leitura de arquivo local. Entidade interna
# (<!ENTITY x "...">) é resolvida; com `False`, ela sumia do texto sem aviso (A1 da auditoria).
PARSER_SEGURO = etree.XMLParser(resolve_entities="internal", no_network=True, load_dtd=False)
