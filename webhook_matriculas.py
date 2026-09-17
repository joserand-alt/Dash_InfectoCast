# -*- coding: utf-8 -*-
"""
Webhook Receiver de Pagamentos e Matrículas (Academy & Gateways)
Recebe requisições HTTP POST instantâneas e dispara o tagueamento no RD Station.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging
import threading
import time

import rd_service
from sync_matriculas_rd import load_tagged_history, save_tagged_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WebhookReceiver")

PORT = 8089

class WebhookHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ONLINE", "service": "InfectoCast RD Webhook Gateway"})
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        if self.path in ["/webhook/matricula", "/webhook/academy/payment", "/api/matricula"]:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json(400, {"error": "Corpo da requisição vazio"})
                return

            raw_body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(raw_body)
            except Exception:
                self._send_json(400, {"error": "JSON inválido"})
                return

            logger.info(f"📥 Notificação de matrícula recebida: {payload}")

            # Extração flexível dos dados
            email = payload.get("email") or payload.get("aluno_email") or payload.get("customer_email")
            nome = payload.get("nome") or payload.get("aluno_nome") or payload.get("customer_name")
            curso = payload.get("curso") or payload.get("produto") or payload.get("nome_curso") or "Pós InfectoCast"
            valor = payload.get("valor") or payload.get("amount") or None
            gateway = payload.get("gateway") or "Academy"
            id_matricula = payload.get("id_matricula") or payload.get("id")

            if not email:
                self._send_json(400, {"error": "E-mail do aluno é obrigatório no payload"})
                return

            # Processamento assíncrono para resposta imediata
            def process_and_tag():
                history = load_tagged_history()
                unique_key = f"{email.strip().lower()}|{rd_service.slugify_tag(curso)}"
                
                res = rd_service.register_matricula_event(
                    email=email,
                    nome=nome,
                    curso=curso,
                    valor=valor,
                    gateway=gateway,
                    id_matricula=id_matricula
                )
                
                if res.get("status") in ["success", "partial_fallback"]:
                    history[unique_key] = {
                        "email": email,
                        "nome": nome,
                        "curso": curso,
                        "data_tagueamento": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "tags_aplicadas": res.get("tags_applied", []),
                        "resposta_rd": res
                    }
                    save_tagged_history(history)

            threading.Thread(target=process_and_tag, daemon=True).start()

            self._send_json(200, {
                "status": "received",
                "message": f"Matrícula de {email} recebida com sucesso. Tags e evento RD em processamento.",
                "aluno": {"email": email, "nome": nome, "curso": curso}
            })
        else:
            self._send_json(404, {"error": f"Rota {self.path} não encontrada"})

def start_webhook_server(port=PORT):
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    logger.info(f"🚀 Servidor Webhook de Matrículas RD Station ativo na porta {port} (http://localhost:{port}/webhook/matricula)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Servidor Webhook encerrado.")
        server.server_close()

if __name__ == "__main__":
    start_webhook_server()
