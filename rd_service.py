# -*- coding: utf-8 -*-
"""
Módulo Oficial de Integração com a API RD Station (OAuth 2.0 & Endpoints Oficiais)
- Renovação automática de access_token via refresh_token
- Aplicação DIRETA de tags em leads/contatos (POST /platform/contacts/email:{email}/tag e PATCH)
- Disparo de eventos de conversão e matrícula (POST /platform/events)
- Classificação inteligente de tags por Tipo de Curso (pos-graduacao / curso-livre) e Curso Específico
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import unicodedata
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RDService")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKENS_FILE = os.path.join(BASE_DIR, "rd_tokens.json")

CLIENT_ID = os.environ.get("RD_CLIENT_ID", "1b4f494f-f173-455b-a496-e26a454be896")
CLIENT_SECRET = os.environ.get("RD_CLIENT_SECRET", "7ea8940ca58a43628bb948dbbc8bc704")
REDIRECT_URI = "https://joserand-alt.github.io/Dash_InfectoCast/"

def slugify_tag(text, prefix=""):
    """Converte texto em slug limpo para tags RD Station (ex: 'aluno-pos-ccih')"""
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    slug = re.sub(r'[-\s]+', '-', text)
    if prefix:
        slug = f"{prefix.strip().lower()}-{slug}"
    return slug

def classify_course_tags(curso_nome):
    """
    Retorna as tags oficiais padronizadas:
    1. Tipo de Curso: 'pos-graduacao' ou 'curso-livre'
    2. Tag Específica do Curso: 'pos-ccih', 'sos-antibiotico', etc.
    """
    if not curso_nome:
        return ["pos-graduacao", "pos-infectocast"]
        
    c_upper = unicodedata.normalize('NFKD', str(curso_nome)).encode('ascii', 'ignore').decode('utf-8').upper().strip()
    tags = []
    
    # 1. Tipo de Curso: pós-graduação vs curso livre
    is_pos = (
        "POS" in c_upper or 
        "PÓS" in c_upper or 
        "ESPECIALIZACAO" in c_upper or 
        "CCIH" in c_upper or 
        "IMUNODEPRIMIDO" in c_upper or 
        "ORTOPED" in c_upper or 
        "INFECTOPED" in c_upper
    )
    
    if is_pos:
        tags.append("pos-graduacao")
    else:
        tags.append("curso-livre")
        
    # 2. Tag Específica do Curso
    if "CCIH" in c_upper or "PREVENCAO" in c_upper or "CONTROLE DE INFECCAO" in c_upper:
        tags.append("pos-ccih")
    elif "IMUNODEPRIMIDO" in c_upper:
        tags.append("pos-imunodeprimido")
    elif "ORTOPED" in c_upper or "PARTES MOLES" in c_upper:
        tags.append("pos-infeccoes-ortopedicas")
    elif "INFECTOPED" in c_upper or "PEDIATR" in c_upper:
        tags.append("pos-infectopediatria")
    elif "MULTI-R" in c_upper or "MULTIR" in c_upper or "JORNADA" in c_upper:
        tags.append("jornada-multi-r")
    elif "FUNGO" in c_upper or "ANTIFUNGICO" in c_upper:
        tags.append("do-fungo-ao-antifungico")
    elif "SOS" in c_upper or "ANTIBIOTICO" in c_upper or "S.O.S" in c_upper:
        tags.append("sos-antibiotico")
    elif "INFECTOXPERT" in c_upper:
        tags.append("infectoxpert")
    else:
        # Tag gerada por slug do nome do curso
        tags.append(slugify_tag(curso_nome, prefix="curso"))

    return tags

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
    
    if int(time.time()) >= (created_at + expires_in - 600):
        return refresh_access_token()
        
    return tokens.get('access_token')

def upsert_contact_tags(email, tags, nome=None):
    """
    Garante que o contato exista e atribui as tags diretamente ao perfil dele no RD Station.
    Usa PATCH /platform/contacts/email:{email} e POST /platform/contacts/email:{email}/tag
    """
    if not email or "@" not in email:
        raise ValueError("E-mail válido é obrigatório.")
    if isinstance(tags, str):
        tags = [tags]
    tags = [t.strip() for t in tags if t and t.strip()]
    if not tags:
        return {"status": "skipped", "message": "Nenhuma tag fornecida"}

    token = get_access_token()
    clean_email = email.strip().lower()
    
    # 1. Tentar PATCH no contato para atualizar nome e tags
    patch_url = f"https://api.rd.services/platform/contacts/email:{urllib.parse.quote(clean_email)}"
    patch_payload = {"tags": tags}
    if nome:
        patch_payload["name"] = nome.strip()

    req_patch = urllib.request.Request(
        patch_url,
        data=json.dumps(patch_payload).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="PATCH"
    )

    try:
        with urllib.request.urlopen(req_patch, timeout=12) as response:
            res_body = response.read().decode('utf-8')
            logger.info(f"✅ Tags {tags} aplicadas com sucesso (PATCH) em {clean_email}")
            return {"status": "success", "method": "PATCH", "tags": tags}
    except urllib.error.HTTPError as e:
        tag_url = f"https://api.rd.services/platform/contacts/email:{urllib.parse.quote(clean_email)}/tag"
        req_tag = urllib.request.Request(
            tag_url,
            data=json.dumps({"tags": tags}).encode('utf-8'),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req_tag, timeout=12) as resp_tag:
                logger.info(f"✅ Tags {tags} aplicadas com sucesso (POST tag) em {clean_email}")
                return {"status": "success", "method": "POST_TAG", "tags": tags}
        except Exception as e2:
            logger.error(f"Erro no POST tag para {clean_email}: {e2}")
            return {"status": "error", "code": e.code, "error": str(e2)}

def register_matricula_event(email, nome=None, curso=None, valor=None, gateway='Academy', id_matricula=None, tags_adicionais=None):
    """
    Registra um evento oficial de Matrícula/Pagamento no RD Station E garante a atribuição direta das tags no perfil do Lead:
    - #aluno-ativo, #aluno-matriculado, #academy-pago
    - #pos-graduacao OU #curso-livre (Tipo de curso)
    - Tag do Curso Específico (ex: #pos-ccih, #sos-antibiotico)
    - Mantém a conversão oficial CDP
    """
    if not email or "@" not in email:
        raise ValueError("E-mail do aluno é obrigatório.")

    clean_email = email.strip().lower()
    
    # 1. Montagem das Tags Padronizadas
    tags = ["aluno-ativo", "aluno-matriculado", "academy-pago"]
    
    # Adicionar tags de Tipo de Curso e Curso Específico
    course_tags = classify_course_tags(curso)
    tags.extend(course_tags)

    if gateway:
        tags.append(slugify_tag(gateway, prefix="gateway"))
    if tags_adicionais:
        if isinstance(tags_adicionais, str):
            tags_adicionais = [tags_adicionais]
        tags.extend([t.strip() for t in tags_adicionais if t and t.strip()])
    
    seen = set()
    tags = [t for t in tags if not (t in seen or seen.add(t))]

    # 2. Aplicação DIRETA das tags no Lead/Contato do RD Station
    tag_result = upsert_contact_tags(clean_email, tags, nome=nome)

    # 3. Disparo do Evento de Conversão oficial para a linha do tempo do RD Station
    token = get_access_token()
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
        payload_data["cf_tipo_curso"] = "Pós-Graduação" if "pos-graduacao" in tags else "Curso Livre"
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
            logger.info(f"✅ Evento de Matrícula & Tags disparados com sucesso para {clean_email}! Tags: {tags}")
            return {
                "status": "success",
                "code": response.status,
                "tags_applied": tags,
                "tag_result": tag_result,
                "event_data": json.loads(res_body) if res_body else {}
            }
    except Exception as e:
        logger.warning(f"Aviso no evento de conversão para {clean_email}: {e}. Tagging direto status: {tag_result}")
        return {
            "status": "partial",
            "tags_applied": tags,
            "tag_result": tag_result,
            "event_error": str(e)
        }

if __name__ == '__main__':
    print("Módulo RD Service atualizado com suporte a Tipo de Curso e Curso Específico.")
