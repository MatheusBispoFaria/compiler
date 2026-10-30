"""Combina o motor original com sinais contextuais, resumos e abordagens."""

from datetime import datetime, timezone
import hashlib

from ai_summary import gerar_resumo
from analysis_engine import analisar_transcricao
from approaches import recomendar_abordagens
from business_signals import analisar_sinais_negocio
from database import empresa_tem_historico


def analisar_conversa(transcricao, *, incluir_resumo=True):
    analysis = analisar_transcricao(transcricao)
    analysis["cliente_recorrente"] = empresa_tem_historico(analysis["EMPRESA"])
    package = analisar_sinais_negocio(transcricao, analysis)
    insights = analysis["insights_ia"]
    insights.update({
        "sinais_negocio": package["sinais"],
        "leitura_principal": package["leitura_principal"],
        "prioridades": package["prioridades"],
        "diagnostico_intencoes": package["diagnostico_intencoes"],
        "abordagens_recomendadas": recomendar_abordagens(package["sinais"]),
    })
    if incluir_resumo:
        summary = gerar_resumo(transcricao, analysis)
        insights.update({
            "resumo": summary["resumo"], "resumo_fonte": summary["fonte"],
            "resumo_modelo": summary["modelo"], "resumo_aviso": summary["aviso"],
        })
    analysis["analysis_id"] = hashlib.sha256(transcricao.encode("utf-8")).hexdigest()[:20]
    analysis["analisado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return analysis
