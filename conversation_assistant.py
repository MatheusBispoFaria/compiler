"""Assistente local simples, limitado à análise da conversa fornecida."""

import re
import unicodedata

from approaches import LABELS


def normalize(text):
    return "".join(char for char in unicodedata.normalize("NFKD", text.lower())
                   if not unicodedata.combining(char))


def _topic(question, history):
    text = normalize(question)
    if any(word in text for word in ("abord", "postura", "conduz", "recomend", "como agir")):
        return "abordagens"
    for topic, words in (
        ("cross_sell", ("cross", "complementar")),
        ("risco_oportunidade", ("bloqueio", "travar", "risco da oportunidade", "condicionante")),
        ("concorrencia", ("concorr", "fornecedor", "alternativa")),
        ("churn", ("churn", "cancel", "renov", "retenc", "saida")),
        ("satisfacao", ("satisf", "sentimento", "percepcao")),
        ("urgencia", ("urgen", "prazo", "quando")),
        ("upsell", ("upsell", "expans", "licenca", "crescer")),
        ("produtos", ("produto", "solucao", "sistema")),
        ("scores", ("score", "pontuacao", "indicador")),
    ):
        if any(word in text for word in words):
            return topic
    if any(word in text for word in ("evidencia", "trecho", "por que", "porque", "justific")):
        for item in reversed(history):
            previous = item.get("topico")
            if item.get("role") == "assistant" and isinstance(previous, str) and previous in LABELS:
                return previous
        return "evidencias"
    if any(word in text for word in ("resum", "geral", "principal", "reuniao", "conversa", "risco", "oportunidade")):
        return "geral"
    if re.fullmatch(r"\s*(oi|ola|bom dia|boa tarde|boa noite)[!.?\s]*", text):
        return "saudacao"
    return "desconhecido"


def responder(pergunta, analise, historico=None):
    topic = _topic(pergunta, historico or [])
    insights = analise.get("insights_ia", {})
    signals = insights.get("sinais_negocio", {})
    approaches = insights.get("abordagens_recomendadas", [])
    evidence = []
    if topic in LABELS:
        signal = signals.get(topic, {})
        evidence = signal.get("evidencias", [])
        answer = (
            f"{LABELS[topic]}: {signal.get('nivel', 'não disponível')} "
            f"({signal.get('score', 0)}/100). {signal.get('motivo', '')}"
        )
        if not evidence:
            answer += " Não há trechos específicos sustentando esse sinal nesta transcrição."
        answer += "\n\nO score é um índice das regras de análise, não uma probabilidade estatística."
    elif topic == "abordagens":
        answer = "\n\n".join(
            f"{item['titulo']}: {item['abordagem']}\n{item['condicao']}"
            for item in approaches[:3]
        ) or "Ainda não há abordagens disponíveis para esta conversa."
        evidence = [text for item in approaches[:3] for text in item.get("evidencias", [])]
    elif topic == "produtos":
        products = insights.get("diagnostico_intencoes", {}).get("produtos", {})
        if products:
            lines = []
            for name, context in products.items():
                status = "uso atual identificado" if context.get("produto_atual") else "mencionado na conversa"
                if context.get("nao_utiliza"):
                    status = "há indicação de que ainda não é utilizado"
                if context.get("interesse"):
                    status += "; há sinal de interesse"
                lines.append(f"{name}: {status}.")
            answer = "\n".join(lines) + "\n\nUma menção, isoladamente, não confirma uso ou intenção de compra."
        else:
            answer = "Não encontrei menções explícitas a produtos reconhecidos pelo catálogo nesta conversa."
    elif topic == "scores":
        answer = "\n".join(
            f"{label}: {signals.get(key, {}).get('score', 0)}/100 · {signals.get(key, {}).get('nivel', 'N/D')}"
            for key, label in LABELS.items()
        ) + "\n\nEsses índices são leituras heurísticas da transcrição. Valores altos têm sentidos diferentes em satisfação, risco e oportunidade."
    elif topic == "evidencias":
        evidence = [text for signal in signals.values() for text in signal.get("evidencias", [])]
        answer = ("Estes são os trechos utilizados pelas regras de análise. Você pode perguntar sobre um sinal específico para entender sua relação com o score."
                  if evidence else "Não encontrei trechos suficientes para explicar um sinal específico. Os scores básicos não substituem evidências.")
    elif topic == "geral":
        readings = insights.get("leitura_principal", [])
        answer = f"A conversa com {analise.get('EMPRESA', 'cliente não identificado')} apresenta a seguinte leitura:\n\n"
        answer += "\n".join(item["texto"] for item in readings) or "Ainda há pouca informação para uma leitura comercial específica."
        if approaches:
            answer += f"\n\nAbordagem em destaque: {approaches[0]['titulo']}. {approaches[0]['abordagem']}"
            evidence = approaches[0].get("evidencias", [])
    elif topic == "saudacao":
        answer = "Olá! Posso explicar os scores, mostrar evidências, identificar produtos mencionados ou comentar as abordagens sugeridas para esta reunião."
    else:
        answer = "Não encontrei essa informação nos dados desta reunião. Posso ajudar com os scores, as evidências, os produtos mencionados e as abordagens sugeridas."
    return {
        "resposta": answer, "topico": topic, "modo": "local",
        "evidencias": list(dict.fromkeys(evidence))[:4],
        "analysis_id": analise.get("analysis_id"),
        "sugestoes": ["Qual abordagem combina com esta conversa?", "Explique o risco de churn", "Quais são as evidências?"],
    }
