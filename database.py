from __future__ import annotations

from contextlib import contextmanager
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from business_signals import analisar_sinais_negocio
from approaches import recomendar_abordagens

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("COMPILER_DB_PATH", "").strip() or BASE_DIR / "reunioes.db").expanduser()
if not DB_PATH.is_absolute():
    DB_PATH = BASE_DIR / DB_PATH


@contextmanager
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def verificar_banco() -> None:
    """Verifica a conexão e o schema sem alterar as reuniões salvas."""
    with _connect() as conn:
        conn.execute("SELECT id FROM reunioes LIMIT 1").fetchone()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reunioes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                empresa TEXT NOT NULL,
                data_reuniao TEXT NOT NULL,
                transcricao TEXT NOT NULL,
                resumo TEXT,
                resumo_fonte TEXT,
                cliente_recorrente INTEGER NOT NULL DEFAULT 0,
                potencial_comercial TEXT,
                pontuacao_comercial INTEGER,
                analise_json TEXT NOT NULL,
                criado_em TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reunioes_empresa ON reunioes(empresa)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reunioes_data ON reunioes(criado_em DESC)"
        )


def empresa_tem_historico(empresa: str) -> bool:
    if not empresa or empresa == "Cliente Desconhecido":
        return False

    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM reunioes WHERE lower(empresa) = lower(?) LIMIT 1",
            (empresa,),
        ).fetchone()
    return row is not None


def salvar_reuniao(
    *,
    titulo: str,
    empresa: str,
    transcricao: str,
    analise: dict[str, Any],
    data_reuniao: str | None = None,
) -> dict[str, Any]:
    insights = analise.get("insights_ia", {}) if isinstance(analise, dict) else {}
    resumo = str(insights.get("resumo") or "").strip()
    resumo_fonte = str(insights.get("resumo_fonte") or "").strip()
    potencial = str(insights.get("potencial_cliente") or "").strip()
    pontuacao = insights.get("pontuacao_comercial")
    recorrente = bool(analise.get("cliente_recorrente", False))

    agora = datetime.now().isoformat(timespec="seconds")
    data = (data_reuniao or agora).strip()
    titulo_final = titulo.strip() or f"Reunião - {empresa}"

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reunioes (
                titulo, empresa, data_reuniao, transcricao, resumo, resumo_fonte,
                cliente_recorrente, potencial_comercial, pontuacao_comercial,
                analise_json, criado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                titulo_final,
                empresa,
                data,
                transcricao,
                resumo,
                resumo_fonte,
                1 if recorrente else 0,
                potencial,
                int(pontuacao) if isinstance(pontuacao, (int, float)) else None,
                json.dumps(analise, ensure_ascii=False),
                agora,
            ),
        )
        reuniao_id = cursor.lastrowid

    return obter_reuniao(reuniao_id)


def _row_to_meeting(row: sqlite3.Row, *, include_full: bool = True) -> dict[str, Any]:
    item = {
        "id": row["id"],
        "titulo": row["titulo"],
        "empresa": row["empresa"],
        "data_reuniao": row["data_reuniao"],
        "resumo": row["resumo"] or "",
        "resumo_fonte": row["resumo_fonte"] or "",
        "cliente_recorrente": bool(row["cliente_recorrente"]),
        "potencial_comercial": row["potencial_comercial"] or "",
        "pontuacao_comercial": row["pontuacao_comercial"],
        "criado_em": row["criado_em"],
    }

    try:
        analise = json.loads(row["analise_json"])
    except (json.JSONDecodeError, TypeError):
        analise = {}

    if not isinstance(analise, dict):
        analise = {}
    insights = analise.setdefault("insights_ia", {})
    sinais = insights.get("sinais_negocio")
    if not isinstance(sinais, dict) or not sinais:
        pacote = analisar_sinais_negocio(row["transcricao"], analise)
        sinais = pacote["sinais"]
        insights["sinais_negocio"] = sinais
        insights["leitura_principal"] = pacote["leitura_principal"]
        insights["prioridades"] = pacote["prioridades"]

    insights["abordagens_recomendadas"] = recomendar_abordagens(sinais)

    produtos = insights.get("produtos_identificados", [])
    item["produtos"] = [
        p.get("produto") for p in produtos if isinstance(p, dict) and p.get("produto")
    ]
    item["sinais"] = sinais

    if include_full:
        item["transcricao"] = row["transcricao"]
        item["analise"] = analise

    return item


def listar_reunioes(busca: str = "", limite: int = 100) -> list[dict[str, Any]]:
    busca = busca.strip()
    limite = max(1, min(int(limite), 200))

    with _connect() as conn:
        if busca:
            termo = f"%{busca}%"
            rows = conn.execute(
                """
                SELECT * FROM reunioes
                WHERE titulo LIKE ? OR empresa LIKE ? OR resumo LIKE ?
                ORDER BY criado_em DESC
                LIMIT ?
                """,
                (termo, termo, termo, limite),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM reunioes ORDER BY criado_em DESC LIMIT ?",
                (limite,),
            ).fetchall()

    return [_row_to_meeting(row, include_full=False) for row in rows]


def obter_reuniao(reuniao_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM reunioes WHERE id = ?",
            (reuniao_id,),
        ).fetchone()

    if row is None:
        return None
    return _row_to_meeting(row, include_full=True)
