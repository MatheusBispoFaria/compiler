from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _resumo_local(transcricao: str, analise: dict[str, Any]) -> str:
    insights = analise.get("insights_ia", {})
    empresa = analise.get("EMPRESA") or "o cliente"
    produtos = insights.get("produtos_identificados", [])
    sinais = insights.get("sinais_negocio", {})
    prioridades = insights.get("prioridades", [])

    nomes_produtos = [
        item.get("produto")
        for item in produtos
        if isinstance(item, dict) and item.get("produto")
    ]

    partes = [f"A reunião com {empresa} foi analisada com foco em relacionamento e oportunidade comercial."]

    if nomes_produtos:
        partes.append("Foram identificadas menções a " + ", ".join(nomes_produtos) + ".")

    leituras = []
    mapa = [
        ("churn", "risco de churn"),
        ("satisfacao", "satisfação"),
        ("upsell", "potencial de upsell"),
        ("cross_sell", "potencial de cross-sell"),
        ("urgencia", "urgência"),
        ("risco_oportunidade", "risco da oportunidade"),
    ]
    for chave, rotulo in mapa:
        sinal = sinais.get(chave, {}) if isinstance(sinais, dict) else {}
        nivel = sinal.get("nivel") if isinstance(sinal, dict) else None
        if nivel:
            leituras.append(f"{rotulo} {str(nivel).lower()}")

    if leituras:
        partes.append("A leitura de negócio aponta " + ", ".join(leituras) + ".")

    acoes = []
    for item in prioridades[:3]:
        if isinstance(item, dict) and item.get("acao"):
            acoes.append(str(item["acao"]))
    if acoes:
        partes.append("As prioridades são: " + "; ".join(acoes) + ".")

    return " ".join(partes)


def gerar_resumo(transcricao: str, analise: dict[str, Any]) -> dict[str, str]:
    """Gera resumo com OpenAI quando há chave configurada; caso contrário usa fallback local."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip() or "gpt-5.6-luna"

    if not api_key:
        return {
            "resumo": _resumo_local(transcricao, analise),
            "fonte": "local",
            "modelo": "",
            "aviso": "OPENAI_API_KEY não configurada; foi usado um resumo local.",
        }

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        insights = analise.get("insights_ia", {})
        contexto = {
            "empresa": analise.get("EMPRESA"),
            "cliente_recorrente": analise.get("cliente_recorrente"),
            "produtos": insights.get("produtos_identificados", []),
            "areas": insights.get("areas_detectadas", []),
            "problemas": insights.get("problemas_detectados", []),
            "potencial_comercial": insights.get("potencial_cliente"),
            "pontuacao_comercial": insights.get("pontuacao_comercial"),
            "sinais_negocio": insights.get("sinais_negocio", {}),
            "leitura_principal": insights.get("leitura_principal", []),
            "prioridades": insights.get("prioridades", []),
            "recomendacoes": insights.get("recomendacoes_ia", []),
        }

        limite = int(os.getenv("OPENAI_MAX_TRANSCRIPT_CHARS", "50000"))
        transcricao_limitada = transcricao[: max(1000, limite)]

        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente de inteligência comercial para reuniões corporativas da TOTVS. "
                        "Escreva um resumo executivo em português do Brasil, com 1 a 3 parágrafos curtos. "
                        "Use somente informações presentes na transcrição e na análise estruturada. "
                        "Priorize contexto do cliente, produtos TOTVS citados, dores, riscos, concorrentes, "
                        "oportunidades comerciais, decisões e próximos passos. Não invente fatos."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "ANÁLISE ESTRUTURADA:\n"
                        + json.dumps(contexto, ensure_ascii=False, indent=2)
                        + "\n\nTRANSCRIÇÃO:\n"
                        + transcricao_limitada
                    ),
                },
            ],
            max_output_tokens=600,
        )

        texto = (response.output_text or "").strip()
        if not texto:
            raise RuntimeError("A API retornou um resumo vazio.")

        return {
            "resumo": texto,
            "fonte": "openai",
            "modelo": model,
            "aviso": "",
        }
    except Exception:
        return {
            "resumo": _resumo_local(transcricao, analise),
            "fonte": "local",
            "modelo": "",
            "aviso": "Não foi possível gerar o resumo com a OpenAI. Verifique a OPENAI_API_KEY e o modelo configurado; foi usado o resumo local.",
        }
