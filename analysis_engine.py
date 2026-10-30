"""Análise lexical original, executada sem alterar arquivos compartilhados."""

from collections import Counter
from functools import lru_cache
import json
from pathlib import Path
import re

stopwords = {
    "de", "da", "do", "das", "dos", "a", "o", "as", "os",
    "que", "para", "com", "em", "um", "uma", "por", "no", "na",
    "e", "é", "eu", "você", "ele", "ela", "nós", "vocês",
    "isso", "essa", "esse", "então", "também", "aqui", "lá",
    "tá", "né", "sim", "não", "porque", "quando", "como"
}

@lru_cache(maxsize=1)
def carregar_dicionario():
    path = Path(__file__).resolve().parent / "Data.json" / "dicionario.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def analisar_transcricao(transcricao_original, dicionario=None):
    dicionario = carregar_dicionario() if dicionario is None else dicionario
    transcricao = transcricao_original.lower()
    dados = {"EMPRESA": "Cliente Desconhecido", "insights_ia": {"sugestoes_dicionario": []}}
    produtos_encontrados = []
    areas_detectadas = []
    problemas_detectados = []
    recomendacoes_ia = []

    pontuacao_comercial = 0

    palavras_conhecidas = set()

    for produto in dicionario["produtos_totvs"]:
        for palavra in produto ["palavras_associadas"]:
            palavras_conhecidas.add(palavra.lower())

    for area,palavras in dicionario["areas_empresa"].items():
        for palavra in palavras:
            palavras_conhecidas.add(palavra.lower())

    for problema in dicionario["problemas_encontrados"]:
        palavras_conhecidas.add(problema.lower())

    # quebra a transcrição em palavras
    palavras = re.findall(r"\b[a-záéíóúâêôãõç]{4,}\b", transcricao.lower())

    palavras_filtradas = [
        palavra for palavra in palavras
        if palavra not in stopwords and palavra not in palavras_conhecidas]
    contagem = Counter(palavras_filtradas)

    sugestoes =[]

    for palavra,ocorrencias in contagem.most_common(20):
        if ocorrencias >= 5:
            sugestoes.append({
                "palvras":palavra,
                "ocorrencia":ocorrencias,
                "status": "pendente"
            })
            dados["insights_ia"]["sugestoes_dicionario"] = sugestoes
    # =========================
    # DETECTAR EMPRESA
    # =========================
    empresa_detectada = "Cliente Desconhecido"

    # Primeiro prioriza um rótulo explícito da transcrição, por exemplo:
    # "Cliente: Grupo Horizonte Logística" ou "Empresa: XPTO".
    match_empresa = re.search(
        r"(?:cliente|empresa)\s*:\s*([^\n\r]+)",
        transcricao_original,
        flags=re.IGNORECASE,
    )
    if match_empresa:
        candidata = match_empresa.group(1).strip(" -–—\t")
        if candidata:
            empresa_detectada = candidata[:160]

    # Se não houver rótulo explícito, tenta usar o título da reunião, por exemplo:
    # "Reunião de acompanhamento – Grupo Atlas Construções".
    if empresa_detectada == "Cliente Desconhecido":
        for linha in transcricao_original.splitlines()[:8]:
            match_titulo = re.match(
                r"^\s*reuni[aã]o[^\n\r–—-]*[–—-]\s*(.+?)\s*$",
                linha,
                flags=re.IGNORECASE,
            )
            if match_titulo:
                candidata = match_titulo.group(1).strip(" -–—\t")
                if candidata and len(candidata) <= 160:
                    empresa_detectada = candidata
                    break

    # Por último, usa a lista de empresas conhecidas. "TOTVS" é ignorada como cliente,
    # porque aparece naturalmente em nomes de produtos e nos participantes da própria TOTVS.
    if empresa_detectada == "Cliente Desconhecido":
        for empresa in dicionario["empresas_conhecidas"]:
            if empresa.strip().lower() == "totvs":
                continue
            if empresa.lower() in transcricao:
                empresa_detectada = empresa
                break

    # SALVAR EMPRESA
    dados["EMPRESA"] = empresa_detectada

    # =========================
    # IDENTIFICAR PRODUTOS
    # =========================
    for produto in dicionario["produtos_totvs"]:

        pontuacao_produtos = 0

        for palavra in produto["palavras_associadas"]:

            ocorrencias = transcricao.count(palavra.lower())

            if ocorrencias > 0:

                pontuacao_produtos += ocorrencias

        if pontuacao_produtos >= 8:

            confianca = "ALTA"

        elif pontuacao_produtos >= 5:

            confianca = "MEDIA"

        else:

            confianca = "BAIXA"
        # PRECISA DE PELO MENOS 2 MATCHES
        if pontuacao_produtos >= 2:

            produtos_encontrados.append({
                "produto": produto["nome"],

                "pontuacao": pontuacao_produtos,

                "confianca": confianca
            })

    # =========================
    # IDENTIFICAR ÁREAS
    # =========================
    for area, palavras in dicionario["areas_empresa"].items():

        contador = 0

        for palavra in palavras:

            if palavra.lower() in transcricao:

                contador += 1

        if contador > 0:

            areas_detectadas.append({
                "area": area,
                "pontuacao": contador
            })

    # =========================
    # DETECTAR PROBLEMAS
    # =========================
    for problema in dicionario["problemas_encontrados"]:

        if problema.lower() in transcricao:

            problemas_detectados.append(problema)

    # =========================
    # SCORE COMERCIAL
    # =========================

    # ALTO INTERESSE
    for frase in dicionario["sentimentos_comportamentais"]["possivel_cliente_acordo"]:

        if frase.lower() in transcricao:

            pontuacao_comercial += 3

    # MÉDIO INTERESSE
    for frase in dicionario["sentimentos_comportamentais"]["medio_interesse"]:

        if frase.lower() in transcricao:

            pontuacao_comercial += 1

    # BAIXO INTERESSE
    for frase in dicionario["sentimentos_comportamentais"]["pouco_interesse"]:

        if frase.lower() in transcricao:

            pontuacao_comercial -= 1

    # =========================
    # CLASSIFICAR CLIENTE
    # =========================
    if pontuacao_comercial >= 6:

        potencial_cliente = "ALTO"

    elif pontuacao_comercial >= 3:

        potencial_cliente = "MEDIO"

    else:

        potencial_cliente = "BAIXO"

    # =========================
    # GERAR RECOMENDAÇÕES
    # =========================
    for area in areas_detectadas:

        nome_area = area["area"]

        if nome_area in dicionario["acoes_recomendadas"]:

            for acao in dicionario["acoes_recomendadas"][nome_area]:

                recomendacoes_ia.append({
                    "area": nome_area,
                    "acao": acao
                })

    # =========================
    # SALVAR INSIGHTS
    # =========================
    dados["insights_ia"]["produtos_identificados"] = produtos_encontrados

    dados["insights_ia"]["areas_detectadas"] = areas_detectadas

    dados["insights_ia"]["problemas_detectados"] = problemas_detectados

    dados["insights_ia"]["potencial_cliente"] = potencial_cliente

    dados["insights_ia"]["pontuacao_comercial"] = pontuacao_comercial

    dados["insights_ia"]["recomendacoes_ia"] = recomendacoes_ia

    dados["cliente_recorrente"] = False
    return dados
