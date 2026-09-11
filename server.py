import http.server
import socketserver
import json
import subprocess
import os
import openpyxl

PORT = 8085
EXCEL_PATH = r'C:\Users\DELL\Desktop\Acompanhamento de acessos\BD\CURSOS.xlsx'

class APIHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/alocar-aula':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            curso = data.get('curso')
            aula = data.get('aula')
            modulo_nome = data.get('modulo')
            
            try:
                # Carregar planilha usando openpyxl para manter formatação
                wb = openpyxl.load_workbook(EXCEL_PATH)
                ws_mods = wb.worksheets[1] # Aba "Módulos"
                ws_aulas = wb.worksheets[2] # Aba "Aulas"
                
                # 1. Achar ou criar o Módulo
                modulo_id = None
                max_mod_id = 0
                
                # Procura o módulo pelo nome
                for row in ws_mods.iter_rows(min_row=2, values_only=False):
                    m_id_val = row[1].value
                    m_nome_val = row[3].value
                    
                    if isinstance(m_id_val, (int, float)):
                        max_mod_id = max(max_mod_id, int(m_id_val))
                    elif isinstance(m_id_val, str) and m_id_val.isdigit():
                        max_mod_id = max(max_mod_id, int(m_id_val))
                        
                    if m_nome_val and str(m_nome_val).strip().lower() == modulo_nome.lower():
                        modulo_id = m_id_val
                        break
                        
                if not modulo_id:
                    modulo_id = max_mod_id + 1
                    # Append new module
                    # Columns: ['CURSO', 'ID MÓDULO', 'Ordem MÓDULO', 'Nome módulo', 'Descrição', 'Aulas', 'Datas Turmas', 'Ativo']
                    ws_mods.append([curso, modulo_id, "", modulo_nome, "", "", "", ""])
                    
                # 2. Adicionar a Aula
                # Precisamos de um ID para a aula também
                max_aula_id = 0
                for row in ws_aulas.iter_rows(min_row=2, values_only=True):
                    a_id_val = row[2]
                    if isinstance(a_id_val, (int, float)):
                        max_aula_id = max(max_aula_id, int(a_id_val))
                    elif isinstance(a_id_val, str) and a_id_val.isdigit():
                        max_aula_id = max(max_aula_id, int(a_id_val))
                        
                nova_aula_id = max_aula_id + 1
                
                # Columns: ['CURSO', 'MÓDULO' (ID), 'ID' (Aula ID), 'Ordem', 'Nome da aula', 'Vídeo', 'Materiais', 'Atividades', 'Ativo']
                ws_aulas.append([curso, modulo_id, nova_aula_id, "", aula, "", "", "", ""])
                
                # Salvar a planilha
                wb.save(EXCEL_PATH)
                
                # Regerar o dashboard
                subprocess.run(['python', 'gerador.py'], check=True)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
                
            except Exception as e:
                print(f"Erro: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/atualizar':
            try:
                print("Iniciando atualização manual da API InfectoCast...")
                subprocess.run(['python', 'gerador.py'], check=True)
                if os.path.exists('dashboard_gerado.html'):
                    with open('dashboard_gerado.html', 'rb') as src, open('index.html', 'wb') as dst:
                        dst.write(src.read())
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "message": "Atualizado com sucesso"}).encode('utf-8'))
            except Exception as e:
                print(f"Erro na atualização: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

# Prevent address already in use by killing old server if possible
# (Handled externally via manage_task)
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), APIHandler) as httpd:
    print(f"Servidor backend rodando na porta {PORT}...")
    httpd.serve_forever()
