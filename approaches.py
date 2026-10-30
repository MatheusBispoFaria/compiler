"""Sugestões de postura comercial vinculadas aos sinais e às evidências."""

LABELS = {
    "churn": "Risco de churn", "satisfacao": "Satisfação", "upsell": "Upsell",
    "cross_sell": "Cross-sell", "concorrencia": "Concorrência",
    "urgencia": "Urgência", "risco_oportunidade": "Risco da oportunidade",
}


def recomendar_abordagens(sinais):
    approaches = []

    def score(key):
        return sinais.get(key, {}).get("score", 0)

    def supported(key):
        return bool(sinais.get(key, {}).get("evidencias"))

    def add(key, title, tone, text, keys, condition):
        evidence = list(dict.fromkeys(
            item for signal in keys for item in sinais.get(signal, {}).get("evidencias", [])
        ))[:4]
        reasons = [sinais[signal].get("motivo", "") for signal in keys if supported(signal)]
        approaches.append({
            "id": key, "titulo": title, "tom": tone, "abordagem": text,
            "motivo": " ".join(dict.fromkeys(reasons)), "sinais": keys,
            "evidencias": evidence, "condicao": condition,
        })

    sensitive = (score("churn") >= 35 and supported("churn")) or (
        score("satisfacao") < 40 and supported("satisfacao")
    )
    if score("churn") >= 35 and supported("churn"):
        add("cautelosa", "Cautelosa e orientada à confiança", "cautela",
            "Os sinais de possível saída favorecem uma conversa acolhedora e investigativa. "
            "Uma postura que reconheça as preocupações tende a ser mais adequada do que "
            "acelerar a oferta de novos produtos neste momento.", ["churn"],
            "A abertura para expansão depende de compreender melhor os motivos de insatisfação ou saída.")
    if score("satisfacao") < 40 and supported("satisfacao"):
        add("empatica", "Empática e centrada na experiência", "cautela",
            "A percepção negativa identificada sugere uma abordagem receptiva, com espaço "
            "para o cliente explicar o impacto das dificuldades. Reconhecimento e clareza "
            "sobre o que pode ser atendido ganham relevância na condução da conversa.", ["satisfacao"],
            "Promessas e propostas de expansão pedem cautela enquanto a percepção permanecer negativa.")
    if score("risco_oportunidade") >= 35 and supported("risco_oportunidade"):
        add("consultiva", "Consultiva e baseada em critérios", "atencao",
            "As condicionantes da negociação favorecem uma conversa de diagnóstico. "
            "É recomendável dar mais peso à compreensão dos critérios de decisão, "
            "às dependências e aos limites da solução do que à pressão por fechamento.", ["risco_oportunidade"],
            "O interesse registrado ainda não equivale a uma decisão de compra.")
    if score("concorrencia") >= 35 and supported("concorrencia"):
        add("comparativa", "Comparativa e objetiva", "atencao",
            "A presença de alternativas na decisão sugere uma postura transparente e "
            "comparativa, conectada aos critérios mencionados pelo cliente. Diferenciais "
            "fazem mais sentido quando ligados ao contexto da operação, sem desqualificar concorrentes.", ["concorrencia"],
            "A menção de uma alternativa não confirma uma troca de fornecedor.")
    if score("urgencia") >= 35 and supported("urgencia"):
        add("objetiva", "Objetiva e sensível ao prazo", "atencao",
            "O prazo identificado favorece uma comunicação concisa e previsível. "
            "Uma abordagem que explicite possibilidades e dependências pode reduzir "
            "incertezas sem transformar a urgência em pressão comercial adicional.", ["urgencia"],
            "Datas, responsáveis e capacidade de atendimento ainda precisam ser confirmados entre as partes.")
    if score("upsell") >= 35 and supported("upsell"):
        add("expansao", "Expansão gradual e contextualizada", "oportunidade",
            ("Há sinais de ampliação do uso atual, acompanhados de questões de relacionamento. "
             "Uma abordagem gradual e condicionada à recuperação de confiança parece mais adequada."
             if sensitive else
             "Os sinais de ampliação do uso atual permitem uma abordagem de evolução gradual. "
             "A conversa pode conectar a necessidade identificada à capacidade e ao valor da expansão, "
             "preservando espaço para validação pelo cliente."), ["upsell"],
            "Intenção de expansão não confirma orçamento, escopo nem aprovação.")
    if score("cross_sell") >= 35 and supported("cross_sell"):
        add("exploratoria", "Exploratória e focada em aderência", "oportunidade",
            ("O interesse por uma solução complementar aparece junto a sinais de desgaste. "
             "Uma postura exploratória, sem antecipar uma nova venda, preserva espaço para "
             "entender a necessidade e a confiança do cliente."
             if sensitive else
             "O interesse em uma solução complementar favorece uma abordagem exploratória. "
             "A aderência à necessidade expressa ganha prioridade sobre ampliar o portfólio "
             "apenas porque um produto foi mencionado."), ["cross_sell"],
            "A adequação da solução depende de requisitos e interesse efetivo, não apenas de uma menção.")
    if score("satisfacao") >= 70 and supported("satisfacao") and not sensitive:
        add("colaborativa", "Colaborativa e orientada à continuidade", "positivo",
            "Os trechos de satisfação favorecem uma conversa de parceria, com reconhecimento "
            "do que está funcionando e abertura para explorar necessidades futuras no ritmo do cliente.", ["satisfacao"],
            "Uma percepção positiva nesta conversa não garante a ausência de riscos em outros momentos.")
    if not approaches:
        add("entendimento", "Investigativa e aberta ao contexto", "neutro",
            "A conversa não oferece evidências suficientes para sustentar uma postura "
            "comercial específica. Uma abordagem aberta, voltada a compreender necessidades "
            "e critérios do cliente, é mais compatível com o contexto disponível.", [],
            "A ausência de sinais detectados não comprova satisfação, risco baixo ou oportunidade de venda.")
        approaches[-1]["motivo"] = "Não foram identificados trechos suficientes para uma orientação mais específica."
    return approaches
