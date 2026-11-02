# SPDX-License-Identifier: GPL-3.0-or-later
"""Pedidos, respostas e glossário na pasta de trabalho (ADR-0006)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from earbook.adaptadores import pasta_de_trabalho as trabalho
from earbook.adaptadores.pasta_de_trabalho import PastaDeTrabalhoInvalidaError
from earbook.dominio.glossario import CandidatoANome, EntradaDoGlossario
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.trabalho import LivroPreparado
from earbook.dominio.traducao import Pedido, Resposta, Traduzido

PEDIDO = Pedido(
    "c005-l001",
    (
        Segmento("c005-s0001", Papel.TITULO, "The Doors of Perception"),
        Segmento("c005-s0002", Papel.PARAGRAFO, "It was in 1886."),
    ),
)


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    pasta = tmp_path / "livro.earbook"
    trabalho.criar_pasta_de_trabalho(pasta)
    trabalho.criar_pastas_da_traducao(pasta)
    return pasta


def _json(conteudo: object) -> str:
    """O texto exato que a pasta de trabalho grava; comparar texto evita o `Any` do json.loads."""
    return json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n"


def _gravar(caminho: Path, conteudo: object) -> None:
    """Grava como o agente grava: JSON escrito à mão, fora do adaptador."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    _ = caminho.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")


def test_idioma_vem_do_livro(pasta: Path) -> None:
    trabalho.gravar_livro(pasta, LivroPreparado("l.epub", "T", "A", "en", (), ()))
    assert trabalho.ler_idioma(pasta) == "en"


def test_pedido_volta_como_foi_gravado_sem_as_notas(pasta: Path) -> None:
    trabalho.gravar_pedido(pasta, PEDIDO)
    assert trabalho.ler_pedidos(pasta) == (PEDIDO,)
    assert trabalho.caminho_do_pedido(pasta, "c005-l001").read_text(encoding="utf-8") == _json(
        [
            {"id": "c005-s0001", "papel": "titulo", "texto": "The Doors of Perception"},
            {"id": "c005-s0002", "papel": "paragrafo", "texto": "It was in 1886."},
        ]
    )


def test_pedido_gravado_nao_e_reescrito(pasta: Path) -> None:
    trabalho.gravar_pedido(pasta, PEDIDO)
    with pytest.raises(FileExistsError, match="c005-l001"):
        trabalho.gravar_pedido(pasta, Pedido("c005-l001", ()))
    assert trabalho.ler_pedidos(pasta) == (PEDIDO,)


def test_resposta_do_agente_volta_por_lote_em_ordem(pasta: Path) -> None:
    _gravar(trabalho.caminho_da_resposta(pasta, "c005-l002"), [])
    _gravar(
        trabalho.caminho_da_resposta(pasta, "c005-l001"),
        [{"id": "c005-s0001", "texto": "As Portas da Percepção"}],
    )
    assert trabalho.ler_respostas(pasta) == (
        Resposta("c005-l001", (Traduzido("c005-s0001", "As Portas da Percepção"),)),
        Resposta("c005-l002", ()),
    )


def test_pasta_sem_traducao_nao_tem_pedido_resposta_nem_glossario(tmp_path: Path) -> None:
    pasta = tmp_path / "livro.earbook"
    trabalho.criar_pasta_de_trabalho(pasta)
    assert trabalho.ler_pedidos(pasta) == ()
    assert trabalho.ler_respostas(pasta) == ()
    assert trabalho.ler_glossario(pasta) == ()


def test_resposta_com_nome_fora_do_formato_do_lote_e_recusada(pasta: Path) -> None:
    # Uma cópia de segurança do agente (`c005-l001-v2.json`) seria uma resposta sem pedido
    # que ninguém pediu para ler.
    _gravar(pasta / "traduzidos" / "c005-l001-v2.json", [])
    with pytest.raises(PastaDeTrabalhoInvalidaError, match=r"c005-l001-v2\.json"):
        _ = trabalho.ler_respostas(pasta)


def test_resposta_sem_texto_e_recusada_com_o_caminho(pasta: Path) -> None:
    _gravar(trabalho.caminho_da_resposta(pasta, "c005-l001"), [{"id": "c005-s0001"}])
    with pytest.raises(PastaDeTrabalhoInvalidaError, match=r"c005-l001\.json.*'texto'"):
        _ = trabalho.ler_respostas(pasta)


def test_resposta_que_e_objeto_e_recusada(pasta: Path) -> None:
    # Num objeto, o `json` guarda só a última chave repetida: o ID repetido sumiria.
    _gravar(trabalho.caminho_da_resposta(pasta, "c005-l001"), {"c005-s0001": "Texto"})
    with pytest.raises(PastaDeTrabalhoInvalidaError, match="esperava uma lista"):
        _ = trabalho.ler_respostas(pasta)


def test_glossario_volta_como_o_agente_gravou(pasta: Path) -> None:
    _gravar(
        trabalho.caminho_do_glossario(pasta),
        [{"original": "Stormwind", "traducao": "Ventobravo", "nota": "cidade dos humanos"}],
    )
    assert trabalho.ler_glossario(pasta) == (EntradaDoGlossario("Stormwind", "Ventobravo"),)


def test_glossario_com_nome_vazio_e_recusado(pasta: Path) -> None:
    # O nome vazio "aparece" em todo segmento e acusaria o livro inteiro.
    _gravar(trabalho.caminho_do_glossario(pasta), [{"original": " ", "traducao": "x"}])
    with pytest.raises(PastaDeTrabalhoInvalidaError, match=r"glossario\.json.*vazio"):
        _ = trabalho.ler_glossario(pasta)


def test_candidatos_vao_para_nomes_json(pasta: Path) -> None:
    trabalho.gravar_candidatos(pasta, (CandidatoANome("Lothar", 192, "c004-s0003"),))
    assert trabalho.caminho_dos_candidatos(pasta).read_text(encoding="utf-8") == _json(
        [{"nome": "Lothar", "vezes": 192, "exemplo": "c004-s0003"}]
    )


def test_resposta_por_link_simbolico_e_recusada(pasta: Path, tmp_path: Path) -> None:
    # A5 da auditoria: a pasta é escrita pelo agente, e o link traria para o livro a resposta
    # de outro livro, sem aviso. O `epub/` já recusa link pelo mesmo motivo (ADR-0005).
    fora = tmp_path / "outro.json"
    _gravar(fora, [{"id": "c005-s0001", "texto": "Texto de outro livro"}])
    trabalho.caminho_da_resposta(pasta, "c005-l001").symlink_to(fora)
    with pytest.raises(PastaDeTrabalhoInvalidaError, match=r"c005-l001\.json: link simbólico"):
        _ = trabalho.ler_respostas(pasta)


def test_pasta_de_respostas_por_link_simbolico_e_recusada(tmp_path: Path) -> None:
    pasta = tmp_path / "livro.earbook"
    trabalho.criar_pasta_de_trabalho(pasta)
    (tmp_path / "fora").mkdir()
    (pasta / "traduzidos").symlink_to(tmp_path / "fora")
    with pytest.raises(PastaDeTrabalhoInvalidaError, match="traduzidos: link simbólico"):
        _ = trabalho.ler_respostas(pasta)


def test_glossario_por_link_simbolico_e_recusado(pasta: Path, tmp_path: Path) -> None:
    fora = tmp_path / "glossario-de-outro.json"
    _gravar(fora, [])
    trabalho.caminho_do_glossario(pasta).symlink_to(fora)
    with pytest.raises(PastaDeTrabalhoInvalidaError, match=r"glossario\.json: link simbólico"):
        _ = trabalho.ler_glossario(pasta)


def test_resposta_com_id_que_nao_e_texto_e_recusada(pasta: Path) -> None:
    _gravar(trabalho.caminho_da_resposta(pasta, "c005-l001"), [{"id": 5, "texto": "x"}])
    with pytest.raises(PastaDeTrabalhoInvalidaError, match="'id' devia ser texto"):
        _ = trabalho.ler_respostas(pasta)


def test_glossario_com_traducao_vazia_e_recusado(pasta: Path) -> None:
    # Com a forma vazia, a cobrança daquele nome se desligava em silêncio (P10 da auditoria).
    _gravar(trabalho.caminho_do_glossario(pasta), [{"original": "Lothar", "traducao": ""}])
    with pytest.raises(PastaDeTrabalhoInvalidaError, match="'traducao' vazio"):
        _ = trabalho.ler_glossario(pasta)


def test_idioma_que_nao_e_texto_e_recusado(pasta: Path) -> None:
    _gravar(pasta / "livro.json", {"idioma": None})
    with pytest.raises(PastaDeTrabalhoInvalidaError, match="'idioma' devia ser texto"):
        _ = trabalho.ler_idioma(pasta)


def test_glossario_que_e_link_pendurado_e_recusado(pasta: Path, tmp_path: Path) -> None:
    # Pendurado, o link parecia glossário ausente, e a cobrança dos nomes se desligava.
    trabalho.caminho_do_glossario(pasta).symlink_to(tmp_path / "nao-existe.json")
    with pytest.raises(PastaDeTrabalhoInvalidaError, match="link simbólico"):
        _ = trabalho.ler_glossario(pasta)


def test_candidatos_nao_sao_gravados_atraves_de_link(pasta: Path, tmp_path: Path) -> None:
    # F4 da pós-auditoria: a gravação sairia da pasta de trabalho e apagaria o alvo.
    fora = tmp_path / "importante.txt"
    _ = fora.write_text("não apagar")
    trabalho.caminho_dos_candidatos(pasta).symlink_to(fora)
    with pytest.raises(PastaDeTrabalhoInvalidaError, match="link simbólico"):
        trabalho.gravar_candidatos(pasta, ())
    assert fora.read_text() == "não apagar"


def test_candidatos_nao_sao_gravados_atraves_de_link_fisico(pasta: Path, tmp_path: Path) -> None:
    # A5 da pós-auditoria curta: o link físico passava pela recusa do simbólico, e o
    # arquivo de fora era sobrescrito. A gravação agora troca o arquivo no lugar.
    fora = tmp_path / "importante.txt"
    _ = fora.write_text("não apagar")
    os.link(fora, trabalho.caminho_dos_candidatos(pasta))
    trabalho.gravar_candidatos(pasta, ())
    assert fora.read_text() == "não apagar"
    assert trabalho.caminho_dos_candidatos(pasta).read_text(encoding="utf-8") == _json([])
