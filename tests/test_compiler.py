"""Regressão da análise, sugestões contextuais, chat e histórico isolado."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["OPENAI_API_KEY"] = ""
# api.py inicializa o banco ao importar. Isolamos também essa inicialização,
# antes de os bancos de cada teste serem criados (o disco do Render não existe no build).
IMPORT_DATABASE = tempfile.TemporaryDirectory(prefix="compiler-test-import-", dir=ROOT)
os.environ["COMPILER_DB_PATH"] = str(Path(IMPORT_DATABASE.name) / "bootstrap.db")
unittest.addModuleCleanup(IMPORT_DATABASE.cleanup)

import api
import database
from analysis_engine import analisar_transcricao
from approaches import recomendar_abordagens
from business_signals import analisar_sinais_negocio

CAUTIOUS = """Empresa: Cliente Teste Aurora
Cliente: Utilizamos o RM. Estamos insatisfeitos com o suporte.
Cliente: Queremos cancelar o contrato e migrar para a Senior. Estamos avaliando a proposta da Senior.
Cliente: Precisamos de retorno até sexta. Antes de decidir, precisamos dessas respostas.
"""
EXPANSION = """Empresa: Cliente Teste Horizonte
Cliente: Utilizamos o TOTVS RM e estamos satisfeitos. O sistema atende bem.
Cliente: Queremos ampliar as licenças do RM para as novas filiais.
Cliente: Não utilizamos o Fluig. Temos interesse em uma demonstração do Fluig.
"""
NEUTRAL = "Empresa: Cliente Teste Neutro\nParticipante: Estamos iniciando esta reunião para conhecer o contexto."


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=ROOT)
        self.db_patch = patch.object(database, "DB_PATH", Path(self.directory.name) / "meetings.db")
        self.db_patch.start()
        database.init_db()
        self.client = api.app.test_client()

    def tearDown(self):
        self.db_patch.stop()
        self.directory.cleanup()

    def analyze(self, text):
        response = self.client.post("/api/analisar", json={"transcricao": text})
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_complete_analysis_preserves_seven_signals_without_saving(self):
        analysis = self.analyze(CAUTIOUS)
        signals = analysis["insights_ia"]["sinais_negocio"]
        self.assertEqual(set(signals), {"churn", "satisfacao", "upsell", "cross_sell", "concorrencia", "urgencia", "risco_oportunidade"})
        self.assertGreaterEqual(signals["churn"]["score"], 65)
        self.assertLess(signals["satisfacao"]["score"], 40)
        self.assertEqual(self.client.get("/api/reunioes").get_json()["reunioes"], [])
        self.assertIn("abordagens_recomendadas", analysis["insights_ia"])

    def test_contextual_scores_match_the_existing_engine(self):
        for text in (CAUTIOUS, EXPANSION, NEUTRAL):
            with self.subTest(text=text.splitlines()[0]):
                original = analisar_sinais_negocio(text, analisar_transcricao(text))
                actual = self.analyze(text)["insights_ia"]
                self.assertEqual(actual["sinais_negocio"], original["sinais"])
                self.assertEqual(actual["diagnostico_intencoes"], original["diagnostico_intencoes"])

    def test_negated_satisfaction_and_plural_are_not_positive(self):
        for text in ("Não estamos satisfeitos", "Estamos insatisfeitos", "Não estou satisfeito"):
            with self.subTest(text=text):
                score = self.analyze(f"Empresa: Teste\nCliente: {text}.")["insights_ia"]["sinais_negocio"]["satisfacao"]["score"]
                self.assertEqual(score, 15)
        self.assertEqual(self.analyze("Empresa: Teste\nCliente: Estou satisfeito.")["insights_ia"]["sinais_negocio"]["satisfacao"]["score"], 76)

    def test_simultaneous_analyses_do_not_mix_companies_or_text(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(analisar_transcricao, [CAUTIOUS, EXPANSION]))
        self.assertEqual([result["EMPRESA"] for result in results], ["Cliente Teste Aurora", "Cliente Teste Horizonte"])
        self.assertIsNot(results[0]["insights_ia"], results[1]["insights_ia"])
        first = analisar_transcricao("Empresa: A\ninventario inventario inventario inventario inventario inventario")
        second = analisar_transcricao(NEUTRAL)
        self.assertTrue(first["insights_ia"]["sugestoes_dicionario"])
        self.assertEqual(second["insights_ia"]["sugestoes_dicionario"], [])

    def test_product_mentions_alone_do_not_create_cross_sell_approach(self):
        analysis = self.analyze("Empresa: Teste\nParticipante: A pauta cita RM, Fluig e Protheus para referência.")
        approaches = analysis["insights_ia"]["abordagens_recomendadas"]
        self.assertNotIn("exploratoria", [item["id"] for item in approaches])

    def test_recommendations_quote_only_available_signal_evidence(self):
        for text in (CAUTIOUS, EXPANSION):
            insights = self.analyze(text)["insights_ia"]
            evidence = {item for signal in insights["sinais_negocio"].values() for item in signal["evidencias"]}
            for approach in insights["abordagens_recomendadas"]:
                self.assertTrue(set(approach["evidencias"]).issubset(evidence))
                self.assertTrue(approach["condicao"])

    def test_expansion_advice_remains_cautious_when_relationship_is_sensitive(self):
        signals = {
            "churn": {"score": 80, "evidencias": ["Cliente: podemos sair."], "motivo": "Intenção de saída."},
            "upsell": {"score": 80, "evidencias": ["Cliente: precisamos de mais licenças."], "motivo": "Expansão."},
        }
        approaches = recomendar_abordagens(signals)
        expansion = next(item for item in approaches if item["id"] == "expansao")
        self.assertIn("recuperação de confiança", expansion["abordagem"])

    def test_weak_context_has_explicit_uncertainty(self):
        approaches = self.analyze(NEUTRAL)["insights_ia"]["abordagens_recomendadas"]
        self.assertEqual(approaches[0]["id"], "entendimento")
        self.assertEqual(approaches[0]["evidencias"], [])
        self.assertIn("não comprova", approaches[0]["condicao"])

    def test_chat_answers_with_evidence_and_supports_follow_up(self):
        response = self.client.post("/api/chat", json={"transcricao": CAUTIOUS, "pergunta": "Explique o risco de churn"})
        self.assertEqual(response.status_code, 200)
        answer = response.get_json()
        self.assertEqual(answer["modo"], "local")
        self.assertEqual(answer["topico"], "churn")
        self.assertTrue(answer["evidencias"])
        self.assertIn("não uma probabilidade", answer["resposta"])
        follow_up = self.client.post("/api/chat", json={
            "transcricao": CAUTIOUS, "pergunta": "Por quê?",
            "historico": [{"role": "assistant", "topico": "churn", "content": answer["resposta"]}],
        }).get_json()
        self.assertEqual(follow_up["topico"], "churn")

    def test_chat_stays_with_current_meeting_and_declines_unavailable_facts(self):
        first = self.client.post("/api/chat", json={"transcricao": CAUTIOUS, "pergunta": "Resumo da reunião"}).get_json()
        second = self.client.post("/api/chat", json={"transcricao": NEUTRAL, "pergunta": "Resumo da reunião"}).get_json()
        self.assertNotEqual(first["analysis_id"], second["analysis_id"])
        self.assertNotIn("Aurora", second["resposta"])
        unknown = self.client.post("/api/chat", json={"transcricao": NEUTRAL, "pergunta": "Qual o faturamento anual exato?"}).get_json()
        self.assertIn("Não encontrei", unknown["resposta"])

    def test_explicit_save_search_and_reopen_keep_context(self):
        analysis = self.analyze(EXPANSION)
        saved = self.client.post("/api/reunioes", json={"transcricao": EXPANSION, "analise": analysis, "titulo": "Expansão teste"})
        self.assertEqual(saved.status_code, 201)
        meeting = saved.get_json()
        self.assertEqual(meeting["transcricao"], EXPANSION.strip())
        self.assertTrue(meeting["analise"]["insights_ia"]["abordagens_recomendadas"])
        listed = self.client.get("/api/reunioes?busca=Expansão").get_json()["reunioes"]
        self.assertEqual([item["id"] for item in listed], [meeting["id"]])
        opened = self.client.get(f"/api/reunioes/{meeting['id']}").get_json()
        self.assertEqual(opened["transcricao"], EXPANSION.strip())

    def test_saving_a_different_transcript_requires_new_analysis(self):
        analysis = self.analyze(CAUTIOUS)
        response = self.client.post("/api/reunioes", json={"transcricao": EXPANSION, "analise": analysis})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(database.listar_reunioes(), [])

    def test_old_saved_meetings_gain_approaches_without_schema_change(self):
        old = analisar_transcricao(CAUTIOUS)
        meeting = database.salvar_reuniao(titulo="Legado", empresa=old["EMPRESA"], transcricao=CAUTIOUS, analise=old)
        self.assertTrue(meeting["analise"]["insights_ia"]["sinais_negocio"])
        self.assertTrue(meeting["analise"]["insights_ia"]["abordagens_recomendadas"])

    def test_invalid_requests_are_rejected(self):
        for payload in (None, [], {}, {"transcricao": ""}, {"transcricao": 123}, {"transcricao": "a" * 200001}):
            with self.subTest(payload_type=type(payload).__name__):
                self.assertEqual(self.client.post("/api/analisar", json=payload).status_code, 400)
        self.assertEqual(self.client.post("/api/chat", json={"transcricao": NEUTRAL, "pergunta": ""}).status_code, 400)
        self.assertEqual(self.client.post("/api/chat", json={"transcricao": NEUTRAL, "pergunta": "Oi", "historico": {}}).status_code, 400)
        self.assertEqual(self.client.get("/api/reunioes/999999").status_code, 404)

    def test_built_frontend_is_served_by_backend(self):
        if not (ROOT / "frontend/dist/index.html").exists():
            self.skipTest("Execute npm run build para verificar a interface compilada.")
        response = self.client.get("/")
        try:
            self.assertEqual(response.status_code, 200)
            self.assertIn("Compiler-AI", response.get_data(as_text=True))
        finally:
            response.close()

    def test_database_directory_is_created_for_hosted_storage(self):
        nested = Path(self.directory.name) / "persistent" / "compiler" / "history.db"
        with patch.object(database, "DB_PATH", nested):
            database.init_db()
            database.verificar_banco()
            self.assertTrue(nested.is_file())
            self.assertEqual(database.listar_reunioes(), [])

    def test_health_checks_database_and_does_not_cache_meeting_data(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        history = self.client.get("/api/reunioes")
        self.assertEqual(history.headers["Cache-Control"], "no-store")
        with patch.object(api, "verificar_banco", side_effect=RuntimeError("database unavailable")):
            with self.assertLogs(api.app.logger, level="ERROR"):
                failure = self.client.get("/api/health")
        self.assertEqual(failure.status_code, 503)
        self.assertEqual(failure.get_json()["motivo"], "database_unavailable")

    def test_missing_frontend_does_not_report_production_ready(self):
        with patch.dict(api.app.config, {"COMPILER_PRODUCTION": True}):
            with patch.object(api, "FRONTEND_DIST", Path(self.directory.name) / "absent-dist"):
                response = self.client.get("/")
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("localhost", response.get_data(as_text=True))
                health = self.client.get("/api/health")
                self.assertEqual(health.status_code, 503)
                self.assertEqual(health.get_json()["motivo"], "frontend_missing")

    def test_production_server_uses_the_port_provided_by_render(self):
        with patch.dict(os.environ, {"PORT": "17321"}):
            config = runpy.run_path(str(ROOT / "gunicorn.conf.py"))
        self.assertEqual(config["bind"], "0.0.0.0:17321")
        self.assertEqual(config["workers"], 1)
        self.assertEqual(config["worker_class"], "gthread")
        self.assertGreaterEqual(config["threads"], 2)

    def test_compiled_assets_share_the_api_origin_and_exclude_legacy_data(self):
        if not (ROOT / "frontend/dist/index.html").exists():
            self.skipTest("Execute npm run build para verificar os arquivos compilados.")
        with patch.dict(api.app.config, {"COMPILER_PRODUCTION": True}):
            response = self.client.get("/")
            try:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["Cache-Control"], "no-cache")
                assets = re.findall(r'(?:src|href)="(/assets/[^"\s]+)"', response.get_data(as_text=True))
                self.assertGreaterEqual(len(assets), 2)
            finally:
                response.close()
            for asset in assets:
                result = self.client.get(asset)
                try:
                    self.assertEqual(result.status_code, 200, asset)
                finally:
                    result.close()
        self.assertEqual(self.client.get("/data.json").status_code, 404)


if __name__ == "__main__":
    unittest.main()
