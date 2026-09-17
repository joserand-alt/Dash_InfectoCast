# -*- coding: utf-8 -*-
"""
RD Station Marketing API v2 Service
Integração com a API do RD Station:
- Autenticação OAuth 2.0 e Renovação Automática de Access Token
- Tagueamento direto de Leads/Contatos
- Disparo de Eventos de Conversão (Matrículas, Pagamentos e Onboarding)
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
import time
import unicodedata
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RDService")

CLIENT_ID = "8dd9632d-c758-44de-ac07-a0c14b0f2a30"
CLIENT_SECRET = "789fb08d84244d7ca7e3afe4abb911b0"
REDIRECT_URI = "https://joserand-alt.github.io/Dash_InfectoCast/"

TOKENS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rd_tokens.json")

def normalize_text(text):
    if not text:
        return ""
    text = str(text).strip()
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def slugify_tag(text, prefix=""):
    """Gera uma tag limpa e padronizada para o RD Station (ex: 'matricula-pos-infecto')"""
    if not text:
        return ""
    clean = normalize_text(text).lower()
    for ch in ['/', '\\', '.', ',', ':', ';', '(', ')', '[', ']', '{', '}', '!', '?', '"', "'", '@', '#', '$', '%', '*', '+']:
        clean = clean.replace(ch, ' ')
    slug = '-'.join(clean.split())
    if prefix:
        return f"{prefix.rstrip('-')}-{slug}"
    return slug

def get_auth_url():
    """Gera a URL de consentimento OAuth do RD Station"""
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
            logger.info("Tokens obtidos e salvos com sucesso em rd_tokens.json!")
            return tokens
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        logger.error(f"Erro ao trocar código ({e.code}): {error_body}")
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
            logger.info("Access token RD Station renovado com sucesso!")
            return new_tokens.get('access_token')
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        logger.error(f"Erro ao renovar token RD Station ({e.code}): {error_body}")
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

def add_tags_to_contact(email, tags):
    """
    Adiciona tags a um contato existente no RD Station.
    Endpoint: POST https://api.rd.services/platform/contacts/email:{email}/tag
    """
    if not email:
        raise ValueError("E-mail do contato é obrigatório.")
    if isinstance(tags, str):
        tags = [tags]
    tags = [t.strip() for t in tags if t and t.strip()]
    if not tags:
        return {"status": "skipped", "message": "Nenhuma tag fornecida"}

    token = get_access_token()
    clean_email = email.strip().lower()
    url = f"https://api.rd.services/platform/contacts/email:{urllib.parse.quote(clean_email)}/tag"
    
    payload = {"tags": tags}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = response.read().decode('utf-8')
            return {"status": "success", "code": response.status, "data": json.loads(res_body) if res_body else {}}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        logger.error(f"Erro ao adicionar tags para {email} ({e.code}): {error_body}")
        return {"status": "error", "code": e.code, "error": error_body}
    except Exception as e:
        logger.error(f"Exceção ao adicionar tags para {email}: {e}")
        return {"status": "error", "error": str(e)}

def register_matricula_event(email, nome=None, curso=None, valor=None, gateway='Academy', id_matricula=None, tags_adicionais=None):
    """
    Registra um evento oficial de Conversão de Matrícula (ORDER_PLACED / CONVERSION) no RD Station.
    Aplica automaticamente tags de matrícula, curso, status ativo e registra na timeline do lead.
    Endpoint: POST https://api.rd.services/platform/events
    """
    if not email:
        raise ValueError("E-mail do aluno é obrigatório.")

    token = get_access_token()
    clean_email = email.strip().lower()
    
    # 1. Montagem das Tags Padronizadas
    tags = ["aluno-ativo", "aluno-matriculado", "academy-pago"]
    if curso:
        tags.append(slugify_tag(curso, prefix="curso"))
        tags.append(slugify_tag(curso, prefix="matricula"))
    if gateway:
        tags.append(slugify_tag(gateway, prefix="gateway"))
    if tags_adicionais:
        if isinstance(tags_adicionais, str):
            tags_adicionais = [tags_adicionais]
        tags.extend([t.strip() for t in tags_adicionais if t and t.strip()])
    
    # Remove duplicadas mantendo ordem
    seen = set()
    tags = [t for t in tags if not (t in seen or seen.add(t))]

    # 2. Payload do Evento de Conversão no RD Station
    payload_data = {
        "conversion_identifier": "matricula_confirmada_infectocast",
        "email": clean_email,
        "tags": tags
    }
    if nome:
        payload_data["name"] = nome.strip()
    if curso:
        payload_data["cf_curso_matriculado"] = curso
        payload_data["cf_produto_adquirido"] = curso
    if valor is not None:
        try:
            payload_data["cf_valor_matricula"] = float(valor)
        except Exception:
            pass
    if gateway:
        payload_data["cf_gateway_pagamento"] = gateway
    if id_matricula:
        payload_data["cf_id_matricula"] = str(id_matricula)

    event_body = {
        "event_type": "CONVERSION",
        "event_family": "CDP",
        "payload": payload_data
    }

    url = "https://api.rd.services/platform/events"
    data = json.dumps(event_body).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = response.read().decode('utf-8')
            logger.info(f"✅ Evento de Matrícula disparado com sucesso para {clean_email}! Tags: {tags}")
            return {
                "status": "success",
                "code": response.status,
                "tags_applied": tags,
                "data": json.loads(res_body) if res_body else {}
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        logger.error(f"Erro ao disparar evento de matrícula para {email} ({e.code}): {error_body}")
        
        # Fallback: Tenta adicionar as tags diretamente caso a conversão falhe
        fallback_res = add_tags_to_contact(clean_email, tags)
        return {"status": "partial_fallback", "conversion_error": error_body, "tag_fallback": fallback_res}
    except Exception as e:
        logger.error(f"Exceção ao registrar matrícula para {email}: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == '__main__':
    print("Módulo RD Service carregado com suporte a Matrículas & Tags.")
