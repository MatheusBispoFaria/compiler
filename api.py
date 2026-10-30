"""API e publicação local do Compiler-AI."""

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge

from analysis_service import analisar_conversa
from conversation_assistant import responder
from database import init_db, listar_reunioes, obter_reuniao, salvar_reuniao

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
MAX_TRANSCRIPT = 200_000

app = Flask(__name__, static_folder=str(FRONTEND_DIST), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
init_db()


def _transcript(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("transcricao"), str):
        return None
    text = payload["transcricao"].strip()
    return text if 0 < len(text) <= MAX_TRANSCRIPT else None


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    return jsonify({"erro": "O conteúdo enviado ultrapassa o limite de 2 MB."}), 413


@app.get("/")
def home():
    if (FRONTEND_DIST / "index.html").is_file():
        return send_from_directory(FRONTEND_DIST, "index.html")
    return '<h1>Compiler-AI</h1><p>API ativa. Abra <a href="http://localhost:5173">a interface de desenvolvimento</a>.</p>'


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "assistente": "local", "max_transcript_chars": MAX_TRANSCRIPT})


@app.post("/api/analisar")
def analisar_reuniao():
    text = _transcript(request.get_json(silent=True))
    if text is None:
        return jsonify({"erro": f"Informe uma transcrição com até {MAX_TRANSCRIPT:,} caracteres."}), 400
    try:
        return jsonify(analisar_conversa(text))
    except Exception:
        app.logger.exception("Falha na análise da reunião")
        return jsonify({"erro": "Não foi possível analisar a reunião. Tente novamente."}), 500


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True)
    text = _transcript(payload)
    if text is None:
        return jsonify({"erro": "O assistente precisa da transcrição da reunião atual."}), 400
    question = payload.get("pergunta")
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        return jsonify({"erro": "Escreva uma pergunta com até 2.000 caracteres."}), 400
    history = payload.get("historico", [])
    if not isinstance(history, list):
        return jsonify({"erro": "Histórico de conversa inválido."}), 400
    history = [item for item in history[-12:] if isinstance(item, dict)]
    # Reconstrói o contexto a partir da transcrição, sem consultar outras reuniões
    # e sem depender de scores alterados no navegador ou de um provedor externo.
    analysis = analisar_conversa(text, incluir_resumo=False)
    return jsonify(responder(question.strip(), analysis, history))


@app.get("/api/reunioes")
def reunioes_listar():
    return jsonify({"reunioes": listar_reunioes(busca=request.args.get("busca", ""))})


@app.get("/api/reunioes/<int:meeting_id>")
def reuniao_detalhe(meeting_id):
    meeting = obter_reuniao(meeting_id)
    if meeting is None:
        return jsonify({"erro": "Reunião não encontrada."}), 404
    return jsonify(meeting)


@app.post("/api/reunioes")
def reuniao_salvar():
    payload = request.get_json(silent=True)
    text = _transcript(payload)
    if text is None or not isinstance(payload.get("analise"), dict):
        return jsonify({"erro": "A reunião precisa de uma transcrição e de uma análise antes de ser salva."}), 400
    submitted = payload["analise"]
    submitted_insights = submitted.get("insights_ia")
    if not isinstance(submitted_insights, dict):
        return jsonify({"erro": "A estrutura da análise é inválida."}), 400
    canonical = analisar_conversa(text, incluir_resumo=False)
    if submitted.get("analysis_id") != canonical["analysis_id"]:
        return jsonify({"erro": "A transcrição mudou. Analise a versão atual antes de salvar."}), 409
    # O resumo já gerado pertence à análise exibida; os sinais são recalculados
    # para manter a correspondência com a transcrição que está sendo salva.
    for key in ("resumo", "resumo_fonte", "resumo_modelo", "resumo_aviso"):
        value = submitted_insights.get(key, "")
        canonical["insights_ia"][key] = value if isinstance(value, str) else ""
    title = payload.get("titulo", "")
    title = title.strip()[:250] if isinstance(title, str) else ""
    date = payload.get("data_reuniao")
    date = date[:80] if isinstance(date, str) and date.strip() else None
    meeting = salvar_reuniao(
        titulo=title, empresa=canonical["EMPRESA"], transcricao=text,
        analise=canonical, data_reuniao=date,
    )
    return jsonify(meeting), 201


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("COMPILER_PORT", "5000")), debug=False)
