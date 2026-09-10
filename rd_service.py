import os
import json
import urllib.request
import urllib.parse
import time

CLIENT_ID = "8dd9632d-c758-44de-ac07-a0c14b0f2a30"
CLIENT_SECRET = "789fb08d84244d7ca7e3afe4abb911b0"
REDIRECT_URI = "https://joserand-alt.github.io/Dash_InfectoCast/"

TOKENS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rd_tokens.json")

def get_auth_url():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI
    }
    return f"https://api.rd.services/auth/dialog?{urllib.parse.urlencode(params)}"

def exchange_code_for_token(code):
    """Troca o authorization code pelo access_token e refresh_token"""
    url = "https://api.rd.services/auth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = response.read().decode('utf-8')
            tokens = json.loads(res_body)
            tokens['created_at'] = int(time.time())
            with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
                json.dump(tokens, f, indent=2)
            print("Tokens obtidos e salvos com sucesso em rd_tokens.json!")
            return tokens
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        print(f"Erro ao trocar código ({e.code}): {error_body}")
        raise

def refresh_access_token():
    """Renova o access_token usando o refresh_token salvo"""
    if not os.path.exists(TOKENS_FILE):
        raise FileNotFoundError("Arquivo rd_tokens.json não encontrado. Faça a autenticação inicial.")
        
    with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
        tokens = json.load(f)
        
    refresh_token = tokens.get('refresh_token')
    if not refresh_token:
        raise ValueError("refresh_token não encontrado em rd_tokens.json.")
        
    url = "https://api.rd.services/auth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = response.read().decode('utf-8')
            new_tokens = json.loads(res_body)
            new_tokens['created_at'] = int(time.time())
            with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_tokens, f, indent=2)
            print("Access token renovado com sucesso!")
            return new_tokens.get('access_token')
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        print(f"Erro ao renovar token ({e.code}): {error_body}")
        raise

def get_access_token():
    """Retorna um access_token válido, renovando se necessário"""
    if not os.path.exists(TOKENS_FILE):
        raise FileNotFoundError("rd_tokens.json inexistente. Necessário autenticar primeiro.")
        
    with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
        tokens = json.load(f)
        
    created_at = tokens.get('created_at', 0)
    expires_in = tokens.get('expires_in', 86400)
    
    # Se expirou ou vai expirar nos próximos 10 minutos, renova
    if int(time.time()) >= (created_at + expires_in - 600):
        return refresh_access_token()
        
    return tokens.get('access_token')

if __name__ == '__main__':
    print("URL de Autorização:")
    print(get_auth_url())
