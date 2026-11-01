# SPDX-License-Identifier: GPL-3.0-or-later
"""Título e autor do livro que vem do PDF (ADR-0004).

Os dois PDFs medidos trazem título e autor certos no metadado; o nome do arquivo
("Competente-o-Suficiente-ebook") era lido em voz alta como título (escuta de 2026-11-01).
"""

from __future__ import annotations

import re

from earbook.dominio.segmento import FORA_DO_XML, normalizar_espacos

# Metadado que é nome de arquivo ou valor padrão de editor de texto, não título. Do Office,
# só o padrão com o traço ("Microsoft Word - cap1"): "Microsoft Excel 2019 Bible" é título.
_NOME_PADRAO = (
    r"^(?:microsoft (?:word|powerpoint|excel) - |(?:untitled|sem t[ií]tulo|documento?\d*)$)"
)
_EXTENSAO = r"\.(?:pdf|docx?|odt|rtf|tex|indd|pages|txt|epub)$"
_PARECE_ARQUIVO = re.compile(f"{_NOME_PADRAO}|{_EXTENSAO}", re.IGNORECASE)
# Autor que é o usuário da máquina que gerou o PDF, não a pessoa que escreveu.
_AUTOR_DE_MAQUINA = frozenset(
    {"admin", "administrator", "administrador", "user", "usuario", "usuário", "owner", "unknown"}
)


def titulo_do_livro(do_metadado: str, do_arquivo: str) -> str:
    """O título do metadado, se parece título; senão, o nome do arquivo."""
    titulo = normalizar_espacos(FORA_DO_XML.sub(" ", do_metadado))
    # Sem letra nem algarismo, o título é invisível ("\u200b", "\ufeff") ou lixo (H1).
    eh_titulo = any(c.isalnum() for c in titulo) and not _PARECE_ARQUIVO.search(titulo)
    return titulo if eh_titulo else do_arquivo


def autor_do_livro(do_metadado: str) -> str:
    """Os autores do metadado separados por "; ", sem o nome da máquina; vazio sem autor."""
    partes = (normalizar_espacos(FORA_DO_XML.sub(" ", p)) for p in do_metadado.split(";"))
    autores = (p for p in partes if any(c.isalnum() for c in p))
    return "; ".join(p for p in autores if p.casefold() not in _AUTOR_DE_MAQUINA)
