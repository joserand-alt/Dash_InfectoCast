import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import pandas as pd
from datetime import datetime
import os

EXCEL_PATH = r"C:\Users\DELL\Desktop\Acompanhamento de acessos\BD\Registro de mensagens.xlsx"

class WhatsAppHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == '/mensagens_recentes':
            try:
                mensagens_recentes = {}
                if os.path.exists(EXCEL_PATH):
                    df_msgs = pd.read_excel(EXCEL_PATH)
                    df_msgs['data'] = pd.to_datetime(df_msgs['data'], errors='coerce')
                    
                    hoje = datetime.now()
                    limite_data = hoje - pd.Timedelta(days=10)
                    recent = df_msgs[df_msgs['data'] >= limite_data]
                    
                    for _, row in recent.iterrows():
                        if pd.isna(row['e-mail']) or pd.isna(row['data']):
                            continue
                        email_msg = str(row['e-mail']).strip().lower()
                        dias_atras = max(0, (pd.Timestamp(hoje) - row['data']).days)
                        
                        if email_msg not in mensagens_recentes or row['data'] > pd.to_datetime(mensagens_recentes[email_msg]['data']):
                            mensagens_recentes[email_msg] = {
                                'data': row['data'].strftime('%Y-%m-%d %H:%M:%S'),
                                'dias': dias_atras
                            }
                
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(mensagens_recentes).encode('utf-8'))
            except Exception as e:
                print(f"X Erro ao ler mensagens: {e}")
                self.send_response(500)
                self._send_cors_headers()
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/registrar':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_response(400)
                self.end_headers()
                return
                
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                
                email = data.get('email', '')
                telefone = data.get('telefone', '')
                status = data.get('status', '')
                mensagem = data.get('mensagem', '')
                data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Append to Excel
                if os.path.exists(EXCEL_PATH):
                    df = pd.read_excel(EXCEL_PATH)
                else:
                    df = pd.DataFrame(columns=['data', 'e-mail', 'telefone', 'status', 'mensagem'])
                
                new_row = pd.DataFrame([{
                    'data': data_atual,
                    'e-mail': email,
                    'telefone': telefone,
                    'status': status,
                    'mensagem': mensagem
                }])
                
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_excel(EXCEL_PATH, index=False)
                
                print(f"-> Registrado: {email} | Status: {status}")
                
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                print(f"X Erro ao registrar: {e}")
                self.send_response(500)
                self._send_cors_headers()
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run(server_class=HTTPServer, handler_class=WhatsAppHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"-> Servidor rodando na porta {port}...")
    print(f"-> Salvando registros em: {EXCEL_PATH}")
    print("Pressione Ctrl+C para parar.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Servidor parado.")

if __name__ == '__main__':
    run()
