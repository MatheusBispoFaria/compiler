from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


def _clamp(valor: int | float, minimo: int = 0, maximo: int = 100) -> int:
    return max(minimo, min(maximo, int(round(valor))))


def _nivel(score: int) -> str:
    if score >= 65:
        return "ALTO"
    if score >= 35:
        return "MEDIO"
    return "BAIXO"


def _nivel_satisfacao(score: int) -> str:
    if score >= 70:
        return "ALTA"
    if score >= 40:
        return "MEDIA"
    return "BAIXA"


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", texto).strip()


@dataclass
class Turno:
    locutor: str
    texto: str
    norm: str


def _turnos(transcricao: str) -> list[Turno]:
    """Agrupa falas por locutor quando a transcrição tem o formato Nome:\ntexto.

    Se o arquivo não seguir esse formato, cada linha útil vira um turno. Isso permite
    regras contextuais sem depender de um modelo externo.
    """
    linhas = [linha.rstrip() for linha in transcricao.splitlines()]
    turnos: list[Turno] = []
    locutor_atual = ""
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if buffer:
            texto = " ".join(x.strip() for x in buffer if x.strip()).strip()
            if texto:
                turnos.append(Turno(locutor_atual, texto, _normalizar(texto)))
        buffer = []

    for linha in linhas:
        limpa = linha.strip()
        if not limpa:
            flush()
            continue

        # Evita interpretar cabeçalhos longos como locutor, mas aceita "Renato:" e "[LOCUTOR 10]:".
        if limpa.endswith(":") and len(limpa) <= 80:
            flush()
            locutor_atual = limpa[:-1].strip()
            continue

        # Também cobre "Renato: frase".
        m = re.match(r"^([^:]{1,60}):\s*(.+)$", limpa)
        if m:
            flush()
            locutor_atual = m.group(1).strip()
            buffer = [m.group(2).strip()]
            flush()
            continue

        buffer.append(limpa)

    flush()

    if not turnos:
        for linha in linhas:
            limpa = linha.strip()
            if limpa:
                turnos.append(Turno("", limpa, _normalizar(limpa)))
    return turnos


def _compactar_evidencia(turno: Turno, limite: int = 260) -> str:
    prefixo = f"{turno.locutor}: " if turno.locutor else ""
    texto = re.sub(r"\s+", " ", turno.texto).strip()
    if len(texto) > limite:
        texto = texto[: limite - 1].rstrip() + "…"
    return prefixo + texto


def _add_evidencia(evidencias: list[str], turno: Turno, limite: int = 3) -> None:
    item = _compactar_evidencia(turno)
    if item not in evidencias and len(evidencias) < limite:
        evidencias.append(item)


def _regex_hit(texto_norm: str, padroes: list[str]) -> bool:
    return any(re.search(p, texto_norm, flags=re.IGNORECASE) for p in padroes)


def _score_regras_turnos(
    turnos: list[Turno],
    base: int,
    regras: list[tuple[str, int]],
    max_evidencias: int = 3,
) -> tuple[int, list[str]]:
    score = base
    evidencias: list[str] = []
    vistos: set[str] = set()

    for padrao, peso in regras:
        for turno in turnos:
            if re.search(padrao, turno.norm, flags=re.IGNORECASE):
                chave = f"{padrao}|{turno.norm}"
                if chave in vistos:
                    continue
                vistos.add(chave)
                score += peso
                if len(evidencias) < max_evidencias:
                    _add_evidencia(evidencias, turno, max_evidencias)
                # Cada regra conta no máximo uma vez; evita inflação por repetição mecânica.
                break

    return _clamp(score), evidencias


# Só consideramos um produto "mencionado" para intenção comercial quando aparece pelo nome/alias,
# e não apenas porque palavras genéricas (RH, financeiro, portal) acionaram o dicionário legado.
PRODUTOS_ALIASES: dict[str, list[str]] = {
    "TOTVS RM": [r"\btotvs\s+rm\b", r"\brm\b"],
    "TOTVS Protheus": [r"\btotvs\s+protheus\b", r"\bprotheus\b"],
    "TOTVS Fluig": [r"\btotvs\s+fluig\b", r"\bfluig\b"],
    "TOTVS ClockIn": [r"\btotvs\s+clock\s*in\b", r"\bclock\s*in\b", r"\bclockin\b"],
    "TOTVS Meu RH": [r"\bmeu\s+rh\b"],
    "TOTVS Analytics": [r"\btotvs\s+analytics\b", r"\banalytics\b"],
}

USO_ATUAL = [
    r"\b(?:utilizamos|utilizo|usamos|uso|temos|possui|possuimos|ja\s+utilizamos|ja\s+usamos)\b",
    r"\b(?:e|eh|continua\s+sendo)\s+(?:nosso|nossa|o\s+nosso|a\s+nossa)\b",
    r"\b(?:atende|funciona|esta\s+estavel|estao\s+estaveis|faz\s+parte|centro\s+da\s+nossa\s+operacao)\b",
]

NAO_USA = [
    r"\bnao\s+(?:utilizamos|usamos|temos|implantamos|contratamos)\b",
    r"\bnunca\s+(?:utilizamos|usamos|implantamos|contratamos)\b",
    r"\bainda\s+nao\b",
]

INTERESSE = [
    r"\b(?:tenho|temos)\s+(?:bastante\s+)?interesse\b",
    r"\b(?:me|nos)\s+interessa\b",
    r"\bseria\s+interessante\b",
    r"\bvale\s+(?:uma\s+)?demonstracao\b",
    r"\b(?:queremos|gostariamos|pretendemos)\s+(?:avaliar|conhecer|ver|entender|implantar|adotar)\b",
    r"\b(?:podemos|pode)\s+(?:avaliar|avancar|incluir|colocar)\b",
    r"\b(?:abertos?|abertas?)\s+(?:a|para)\s+(?:avaliar|conhecer)\b",
    r"\b(?:faz|faria)\s+sentido\b",
]

AFIRMACAO_CURTA = [
    r"^(?:sim|com\s+certeza|exatamente|concordo|perfeito|isso|isso\s+mesmo|pode\s+ser|faz\s+sentido)[.!]?$",
]

EXPANSAO_FORTE = [
    r"\b(?:ampliacao|expansao|aumento)\s+(?:de|das?|do|dos)?\s*(?:licencas|usuarios|acessos|contrato|capacidade|uso|utilizacao)\b",
    r"\b(?:ampliar|expandir|aumentar)\s+(?:as?|o|os)?\s*(?:licencas|usuarios|acessos|contrato|uso|utilizacao)\b",
    r"\b(?:mais|novas?)\s+(?:licencas|usuarios|acessos)\b",
    r"\b(?:upgrade|up-grade)\b",
]

EXPANSAO_MEDIA = [
    r"\b(?:ampliar|expandir)\s+(?:o\s+)?uso\b",
    r"\b(?:mais|novos?)\s+(?:modulos|funcionalidades)\b",
    r"\b(?:modulo|pacote)\s+adicional\b",
]

CRESCIMENTO_EMPRESA = [
    r"\babrir\w*\s+(?:\d+\s+)?(?:novas?\s+)?(?:filiais|unidades)\b",
    r"\b(?:novas?\s+)?(?:filiais|unidades)\b.{0,50}\b(?:proximo|este)\s+ano\b",
    r"\b(?:adicionar|contratar|chegar\s+a)\b.{0,35}\b\d+\s+(?:funcionarios|colaboradores|usuarios)\b",
    r"\b\d+\s+(?:novos?\s+)?(?:funcionarios|colaboradores|usuarios)\b",
]


def _produto_presente(turno: Turno, aliases: list[str]) -> bool:
    return _regex_hit(turno.norm, aliases)


def _estado_produtos(turnos: list[Turno]) -> dict[str, dict[str, Any]]:
    estado: dict[str, dict[str, Any]] = {}

    for produto, aliases in PRODUTOS_ALIASES.items():
        info = {
            "mencionado": False,
            "atual": False,
            "nao_atual": False,
            "interesse": False,
            "evidencias_uso": [],
            "evidencias_interesse": [],
        }

        for i, turno in enumerate(turnos):
            if not _produto_presente(turno, aliases):
                continue

            info["mencionado"] = True
            if _regex_hit(turno.norm, NAO_USA):
                info["nao_atual"] = True
                _add_evidencia(info["evidencias_uso"], turno)
            elif _regex_hit(turno.norm, USO_ATUAL):
                info["atual"] = True
                _add_evidencia(info["evidencias_uso"], turno)

            if _regex_hit(turno.norm, INTERESSE):
                info["interesse"] = True
                _add_evidencia(info["evidencias_interesse"], turno)

            # Respostas logo depois do produto herdam o contexto da pergunta/oferta anterior.
            for j in range(i + 1, min(i + 3, len(turnos))):
                resposta = turnos[j]
                if _regex_hit(resposta.norm, NAO_USA):
                    info["nao_atual"] = True
                    info["atual"] = False
                    _add_evidencia(info["evidencias_uso"], resposta)
                if _regex_hit(resposta.norm, INTERESSE) or _regex_hit(resposta.norm, AFIRMACAO_CURTA):
                    info["interesse"] = True
                    _add_evidencia(info["evidencias_interesse"], resposta)
                    break

            # Também captura interesse expresso logo antes do nome do produto.
            if i > 0 and _regex_hit(turnos[i - 1].norm, INTERESSE):
                info["interesse"] = True
                _add_evidencia(info["evidencias_interesse"], turnos[i - 1])

        # "Não usamos" vence um falso positivo de "temos" na mesma conversa, a menos que haja
        # evidência posterior explícita de implantação atual.
        if info["nao_atual"] and not info["evidencias_uso"]:
            info["atual"] = False

        estado[produto] = info

    return estado


def _analisar_upsell(turnos: list[Turno], produtos: dict[str, dict[str, Any]]) -> tuple[int, list[str]]:
    score = 8
    evidencias: list[str] = []
    crescimento_detectado = False
    expansao_forte_detectada = False
    expansao_media_detectada = False

    # Cada categoria de evidência entra uma vez. Assim uma conversa repetitiva não chega a 100
    # apenas porque a mesma intenção foi dita várias vezes.
    for i, turno in enumerate(turnos):
        forte = _regex_hit(turno.norm, EXPANSAO_FORTE)
        media = _regex_hit(turno.norm, EXPANSAO_MEDIA)
        crescimento = _regex_hit(turno.norm, CRESCIMENTO_EMPRESA)

        if forte and not expansao_forte_detectada:
            expansao_forte_detectada = True
            score += 42
            _add_evidencia(evidencias, turno)
            if i + 1 < len(turnos) and _regex_hit(turnos[i + 1].norm, AFIRMACAO_CURTA):
                score += 10
                _add_evidencia(evidencias, turnos[i + 1])
        elif media and not expansao_media_detectada:
            expansao_media_detectada = True
            score += 22
            _add_evidencia(evidencias, turno)

        if crescimento and not crescimento_detectado:
            crescimento_detectado = True
            score += 10
            _add_evidencia(evidencias, turno)

    # Crescimento só vira reforço de upsell quando já existe uma solução atual identificável.
    atuais = [nome for nome, info in produtos.items() if info["atual"]]
    if atuais and crescimento_detectado:
        score += 6

    # Recursos/módulos adicionais do mesmo produto são upsell, mas valem menos que expansão de licença.
    for turno in turnos:
        if re.search(r"\b(?:recursos|funcionalidades|modulos)\s+adicionais\b", turno.norm):
            score += 12
            _add_evidencia(evidencias, turno)
            break

    return _clamp(score), evidencias

def _analisar_cross_sell(turnos: list[Turno], produtos: dict[str, dict[str, Any]]) -> tuple[int, list[str]]:
    score = 8
    evidencias: list[str] = []
    oportunidades = 0

    for produto, info in produtos.items():
        if not info["mencionado"] or not info["interesse"]:
            continue

        # Só é cross-sell quando há interesse por uma solução que não aparece como solução atual.
        if info["nao_atual"]:
            score += 35
        elif not info["atual"]:
            score += 28
        else:
            continue

        oportunidades += 1
        for ev in info["evidencias_interesse"][:2]:
            if ev not in evidencias and len(evidencias) < 3:
                evidencias.append(ev)

    # Interesse em duas ou mais soluções complementares é um sinal comercial forte.
    if oportunidades >= 2:
        score += 8

    # Sinais genéricos de portfólio só ajudam se houver intenção explícita.
    for turno in turnos:
        if re.search(r"\b(?:outras\s+solucoes|solucoes\s+complementares|outros\s+produtos)\b", turno.norm) and _regex_hit(turno.norm, INTERESSE):
            score += 18
            _add_evidencia(evidencias, turno)
            break

    return _clamp(score), evidencias

def _motivo_churn(score: int) -> str:
    if score >= 65:
        return "Há sinais claros de intenção de saída, substituição ou não continuidade da solução atual."
    if score >= 35:
        return "Existem sinais de atenção sobre continuidade, mas a intenção de saída ainda não está consolidada."
    return "Não aparecem sinais fortes de abandono da solução atual; há indícios de permanência ou estabilidade."


def _motivo_satisfacao(score: int) -> str:
    if score >= 70:
        return "Predominam declarações positivas sobre a solução ou o relacionamento atual."
    if score >= 40:
        return "A percepção é mista: existem pontos positivos e incômodos relevantes."
    return "Predominam reclamações, frustração ou insatisfação com a experiência atual."


def _motivo_oportunidade(nome: str, score: int) -> str:
    rotulo = "expansão do contrato/uso atual" if nome == "upsell" else "adoção de uma solução complementar"
    if score >= 65:
        return f"Há intenção concreta de {rotulo}, apoiada por falas da própria reunião."
    if score >= 35:
        return f"Há indícios de {rotulo}, mas ainda sem confirmação comercial forte."
    return f"Não foi encontrada intenção suficientemente clara de {rotulo}."


def _motivo_concorrencia(score: int, concorrentes: list[str]) -> str:
    if score >= 65 and concorrentes:
        return "Há concorrência ativa na decisão: " + ", ".join(concorrentes[:4]) + "."
    if score >= 35:
        return "Há comparação com alternativas de mercado, mas a pressão competitiva ainda é moderada."
    return "Não foi identificada pressão competitiva relevante na conversa."


def _motivo_urgencia(score: int) -> str:
    if score >= 65:
        return "Há prazo, prioridade ou necessidade explícita de retorno rápido."
    if score >= 35:
        return "Existe horizonte de decisão ou prazo comercial, mas sem caráter crítico."
    return "A conversa não demonstra pressão relevante de prazo."


def _motivo_risco_oportunidade(score: int) -> str:
    if score >= 65:
        return "A nova oportunidade pode travar ou ser perdida por pendências, condições ou bloqueios explícitos."
    if score >= 35:
        return "A oportunidade tem condicionantes relevantes, mas ainda pode avançar normalmente."
    return "Não aparecem bloqueios fortes para a continuidade da oportunidade comercial."


def analisar_sinais_negocio(transcricao: str, analise: dict[str, Any]) -> dict[str, Any]:
    turnos = _turnos(transcricao)
    produtos_contexto = _estado_produtos(turnos)

    churn_regras = [
        (r"\brisco\s+real\s+de\s+(?:mudanca|troca)\b", 45),
        (r"\b(?:nao\s+renovar|cancelar\s+(?:o\s+)?contrato|deixar\s+a\s+totvs|sair\s+da\s+totvs)\b", 50),
        (r"\b(?:substituir|trocar)\b.{0,35}\b(?:protheus|rm|totvs|sistema)\b", 35),
        (r"\b(?:migrar|migracao)\b.{0,30}\b(?:sap|oracle|sankhya|senior|outro\s+fornecedor)\b", 35),
        (r"\bchance\s+de\s+troca\s+e\s+real\b", 45),
        (r"\bse\s+isso\s+nao\s+acontecer\b.{0,80}\boutro\s+fornecedor\b", 40),
        (r"\b(?:nao\s+pretendemos|nao\s+pretendo|nossa\s+intencao\s+nao\s+e)\s+trocar\b", -55),
        (r"\b(?:queremos|pretendemos)\s+continuar\s+com\s+a\s+totvs\b", -45),
        (r"\bpermanecer\s+com\s+a\s+totvs\b", -40),
        (r"\bnao\s+existe\s+discussao\s+de\s+troca\b", -50),
        (r"\bnao\s+troco\b.{0,40}\bsistema\b", -55),
    ]
    churn, churn_ev = _score_regras_turnos(turnos, 15, churn_regras)

    negacao_satisfacao = r"\bnao\s+(?:(?:estamos|estou|esta|estao)\s+)?(?:(?:muito|bem)\s+)?satisfeit[oa]s?\b"
    satisfacao_regras = [
        (rf"^(?!.*{negacao_satisfacao}).*\b(?:muito\s+)?satisfeit[oa]s?\b", 26),
        (rf"^(?!.*{negacao_satisfacao}).*\bbem\s+satisfeit[oa]s?\b", 30),
        (r"\b(?:protheus|rm|fluig|clock\s*in)\b.{0,45}\batende\s+bem\b", 20),
        (r"\batende\s+bem\b", 14),
        (r"\bfuncionando\s+(?:bem|normalmente)\b", 14),
        (r"\best(?:a|ao)\s+estaveis?\b", 12),
        (r"\bnada\s+critico\b", 10),
        (r"\bgostamos\s+(?:do|da|dos|das)?\b", 12),
        (r"\bmelhorou\s+bastante\b", 12),
        (negacao_satisfacao, -35),
        (r"\b(?:insatisfeit[oa]s?|insatisfacao)\b", -35),
        (r"\bsuporte\b.{0,45}\bdeixou\s+a\s+desejar\b", -25),
        (r"\binstabilidade\b.{0,45}\b(?:protheus|rm|sistema|processos?)\b", -20),
        (r"\b(?:protheus|rm|sistema)\b.{0,45}\binstabilidade\b", -20),
        (r"\b(?:problema|instabilidade|lentidao)\b.{0,55}\b(?:impacta|afetando|produtividade|operacao)\b", -18),
        (r"\bchamados?\b.{0,55}\b(?:cinco\s+dias|uma\s+semana|demoraram|demorou|demora)\b", -18),
        (r"\bmelhorar\s+(?:o\s+)?atendimento\b", -12),
    ]
    satisfacao, satisfacao_ev = _score_regras_turnos(turnos, 50, satisfacao_regras)

    upsell, upsell_ev = _analisar_upsell(turnos, produtos_contexto)
    cross_sell, cross_ev = _analisar_cross_sell(turnos, produtos_contexto)

    concorrentes_catalogo = {
        "SAP": [r"\bsap\b", r"\bs/?4hana\b"],
        "Oracle": [r"\boracle\b"],
        "Sankhya": [r"\bsankhya\b"],
        "Senior": [r"\bsenior\b"],
        "Microsoft Power BI": [r"\bpower\s*bi\b"],
    }
    concorrentes: list[str] = []
    concorrencia_ev: list[str] = []
    concorrencia = 5
    ativo_patterns = [
        r"\b(?:avaliando|avaliar|proposta|apresentacao|demonstracao|participando|comparando|negociando)\b",
        r"\b(?:decidir|decisao|fornecedor|migracao|migrar)\b",
    ]
    fraco_patterns = [r"\b(?:contato|email|e-mail|alternativa)\b"]

    for nome, aliases in concorrentes_catalogo.items():
        indices = [i for i, t in enumerate(turnos) if _regex_hit(t.norm, aliases)]
        if not indices:
            continue
        concorrentes.append(nome)
        peso_nome = 0
        for i in indices:
            janela = " ".join(t.norm for t in turnos[max(0, i - 1): min(len(turnos), i + 2)])
            if _regex_hit(janela, ativo_patterns):
                peso_nome = max(peso_nome, 35)
                _add_evidencia(concorrencia_ev, turnos[i])
            elif _regex_hit(janela, fraco_patterns):
                peso_nome = max(peso_nome, 12)
                _add_evidencia(concorrencia_ev, turnos[i])
            else:
                peso_nome = max(peso_nome, 5)
        concorrencia += peso_nome

    concorrencia = _clamp(concorrencia)

    urgencia_regras = [
        (r"\b(?:urgencia|urgente|prioridade\s+maxima|prioridade\s+absoluta)\b", 45),
        (r"\b(?:ate|antes\s+de)\s+(?:sexta|segunda|terca|quarta|quinta|amanha|dia\s+\d{1,2})\b", 38),
        (r"\bproxim(?:os|as)\s+\d+\s+dias\b", 35),
        (r"\b(?:30|trinta|45|quarenta\s+e\s+cinco|60|sessenta)\s+dias\b", 28),
        (r"\bproximas?\s+(?:seis|duas|tres|quatro)\s+semanas\b", 30),
        (r"\b(?:o\s+quanto\s+antes|retorno\s+rapido)\b", 28),
        (r"\b(?:precisamos|queremos|necessitamos)\b.{0,50}\brapidamente\b", 28),
        (r"\b(?:ainda\s+)?neste\s+trimestre\b", 22),
        (r"\bproxima\s+semana\b", 18),
        (r"\bainda\s+este\s+ano\b", 4),
    ]
    urgencia, urgencia_ev = _score_regras_turnos(turnos, 15, urgencia_regras)

    risco_regras = [
        (r"\b(?:somente|so)\s+depois\b.{0,80}\b(?:negociacao|avancar|comprar|aprovar)\b", 45),
        (r"\bdepende\b.{0,70}\b(?:respostas|retorno|diagnostico|demonstracao|requisitos)\b", 35),
        (r"\bse\b.{0,90}\bnao\b.{0,90}\b(?:outro\s+fornecedor|nao\s+avancar|nao\s+seguir)\b", 42),
        (r"\b(?:aguardando|pendente|pendencias)\b.{0,60}\b(?:resposta|tecnico|requisito|integracao)\b", 24),
        (r"\b(?:antes\s+de|para)\s+(?:decidir|avancar|aprovar)\b", 15),
        (r"\bprecisamos\s+dessas\s+respostas\b", 28),
        (r"\bnao\s+queremos\s+mais\s+promessa\b", 30),
    ]
    risco_oportunidade, risco_ev = _score_regras_turnos(turnos, 12, risco_regras)
    if concorrencia >= 65 and urgencia >= 65:
        risco_oportunidade = _clamp(risco_oportunidade + 12)

    sinais = {
        "churn": {
            "nivel": _nivel(churn),
            "score": churn,
            "motivo": _motivo_churn(churn),
            "evidencias": churn_ev,
        },
        "satisfacao": {
            "nivel": _nivel_satisfacao(satisfacao),
            "score": satisfacao,
            "motivo": _motivo_satisfacao(satisfacao),
            "evidencias": satisfacao_ev,
        },
        "upsell": {
            "nivel": _nivel(upsell),
            "score": upsell,
            "motivo": _motivo_oportunidade("upsell", upsell),
            "evidencias": upsell_ev,
        },
        "cross_sell": {
            "nivel": _nivel(cross_sell),
            "score": cross_sell,
            "motivo": _motivo_oportunidade("cross_sell", cross_sell),
            "evidencias": cross_ev,
        },
        "concorrencia": {
            "nivel": _nivel(concorrencia),
            "score": concorrencia,
            "motivo": _motivo_concorrencia(concorrencia, concorrentes),
            "evidencias": concorrencia_ev,
            "concorrentes": concorrentes,
        },
        "urgencia": {
            "nivel": _nivel(urgencia),
            "score": urgencia,
            "motivo": _motivo_urgencia(urgencia),
            "evidencias": urgencia_ev,
        },
        "risco_oportunidade": {
            "nivel": _nivel(risco_oportunidade),
            "score": risco_oportunidade,
            "motivo": _motivo_risco_oportunidade(risco_oportunidade),
            "evidencias": risco_ev,
        },
    }

    leitura: list[dict[str, str]] = []
    if churn <= 30:
        leitura.append({"tipo": "positivo", "texto": "A conta atual aparenta estabilidade, sem intenção forte de churn."})
    elif churn >= 65:
        leitura.append({"tipo": "risco", "texto": "Há intenção relevante de saída ou substituição e a retenção deve ser priorizada."})

    if satisfacao >= 70:
        leitura.append({"tipo": "positivo", "texto": "O cliente demonstra satisfação elevada com a solução ou relacionamento atual."})
    elif satisfacao < 40:
        leitura.append({"tipo": "risco", "texto": "A satisfação está baixa e há sinais de desgaste que precisam ser tratados."})

    if upsell >= 65:
        leitura.append({"tipo": "oportunidade", "texto": "Há intenção concreta de ampliar o contrato, licenças ou uso de uma solução já adotada."})
    if cross_sell >= 65:
        leitura.append({"tipo": "oportunidade", "texto": "Há interesse concreto em soluções TOTVS complementares ainda não adotadas."})

    if risco_oportunidade >= 65:
        leitura.append({"tipo": "risco", "texto": "A nova oportunidade comercial pode travar ou ser perdida se as pendências não forem resolvidas."})
    if urgencia >= 65:
        leitura.append({"tipo": "atencao", "texto": "O cliente sinaliza urgência; prazo e responsável pelo retorno devem ser definidos."})
    if concorrencia >= 65:
        leitura.append({"tipo": "risco", "texto": "Há pressão competitiva ativa na decisão do cliente."})

    # Priorizamos as quatro leituras mais úteis, colocando risco antes de observações neutras.
    ordem = {"risco": 0, "atencao": 1, "oportunidade": 2, "positivo": 3}
    leitura = sorted(leitura, key=lambda x: ordem.get(x["tipo"], 9))[:4]

    prioridades: list[dict[str, str]] = []

    def adicionar(prioridade: str, tipo: str, acao: str, motivo: str) -> None:
        if not any(item["acao"] == acao for item in prioridades):
            prioridades.append({
                "prioridade": prioridade,
                "tipo": tipo,
                "acao": acao,
                "motivo": motivo,
            })

    if churn >= 65:
        adicionar("ALTA", "Retenção", "Executar plano de retenção e atacar os motivos explícitos de possível saída.", "Há intenção relevante de churn.")
    if risco_oportunidade >= 65:
        adicionar("ALTA", "Comercial", "Resolver as pendências que bloqueiam a evolução da negociação.", "A oportunidade depende de condições ainda não resolvidas.")
    if urgencia >= 65:
        adicionar("ALTA", "Follow-up", "Definir responsável e prazo objetivo para o próximo retorno ao cliente.", "Há prazo ou urgência explícita.")
    if concorrencia >= 65:
        adicionar("ALTA", "Competitivo", "Mapear a proposta concorrente e preparar diferenciais relevantes para o cliente.", "Há concorrência ativa na decisão.")
    if satisfacao < 40:
        adicionar("ALTA", "Relacionamento", "Criar um plano de recuperação de satisfação antes de ampliar a conversa comercial.", "A percepção do cliente está negativa.")
    if upsell >= 65:
        adicionar("MEDIA", "Upsell", "Estruturar proposta de expansão do contrato, licenças ou uso atual.", "A transcrição contém intenção concreta de expansão.")
    if cross_sell >= 65:
        adicionar("MEDIA", "Cross-sell", "Preparar demonstração ou proposta das soluções complementares que despertaram interesse.", "Há intenção concreta de adoção de outra solução.")

    if len(prioridades) < 3:
        recomendacoes = analise.get("insights_ia", {}).get("recomendacoes_ia", [])
        for item in recomendacoes:
            acao = item if isinstance(item, str) else item.get("acao") if isinstance(item, dict) else None
            if acao:
                adicionar("MEDIA", "Operacional", str(acao), "Recomendação derivada das áreas e problemas detectados.")
            if len(prioridades) >= 3:
                break

    # Diagnóstico é útil para depuração, mas não altera o contrato atual do frontend.
    diagnostico_produtos = {
        nome: {
            "mencionado": info["mencionado"],
            "produto_atual": info["atual"],
            "nao_utiliza": info["nao_atual"],
            "interesse": info["interesse"],
        }
        for nome, info in produtos_contexto.items()
        if info["mencionado"]
    }

    return {
        "sinais": sinais,
        "leitura_principal": leitura,
        "prioridades": prioridades[:3],
        "diagnostico_intencoes": {
            "metodo": "regras_contextuais",
            "produtos": diagnostico_produtos,
        },
    }
