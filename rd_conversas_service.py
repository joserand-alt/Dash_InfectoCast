# -*- coding: utf-8 -*-
"""
Módulo Oficial de Integração com a API do RD Station Conversas (Tallos v2)
- Extração de Contatos, Atendentes e Integrações de WhatsApp
- Cruzamento com Alunos da Cativa Digital e Assinaturas Vindi/Asaas
- Geração de métricas de conversão e pipeline de leads quentes
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RDConversasService")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "rd_conversas_cache.json")
CATIVA_CACHE_FILE = os.path.join(BASE_DIR, "cativa_cache.json")
VINDI_CACHE_FILE = os.path.join(BASE_DIR, "vindi_cache.json")
ASAAS_CACHE_FILE = os.path.join(BASE_DIR, "asaas_cache.json")

RD_CONVERSAS_TOKEN = os.environ.get(
    "RD_CONVERSAS_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbXBsb3llZSI6IjZhOTVhYWIzNDk1YTZmY2I1MzVjNTg2YiIsImNvbXBhbnkiOiI2YTk1YWFiMjQ5NWE2ZmNiNTM1YzU4NjYiLCJpYXQiOjE3ODk3Mzg1MzF9.feXyJ0PWU5bXxGlXJN5MXcEoU4Ph4Yfe2ooosaReMws"
)

BASE_API_URL = "https://api.tallos.com.br/v2"

def fetch_all_customers_from_api():
    """Busca todos os contatos do RD Conversas com paginação."""
    headers = {
        "Authorization": f"Bearer {RD_CONVERSAS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    customers = []
    page = 1
    logger.info("Iniciando busca de contatos na API do RD Conversas...")
    while True:
        url = f"{BASE_API_URL}/customers?page={page}&limit=50"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if not data:
                    break
                customers.extend(data)
                if len(data) < 50:
                    break
                page += 1
        except Exception as e:
            logger.warning(f"Erro ao buscar página {page} do RD Conversas: {e}")
            break
            
    logger.info(f"Total de {len(customers)} contatos carregados do RD Conversas.")
    return customers

def fetch_employees_from_api():
    """Busca atendentes da equipe."""
    headers = {
        "Authorization": f"Bearer {RD_CONVERSAS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        url = f"{BASE_API_URL}/employees"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        logger.warning(f"Erro ao buscar atendentes do RD Conversas: {e}")
        return []

def get_rd_conversas_data(force_refresh=False, cativa_students=None, vindi_subs=None, asaas_subs=None):
    """
    Retorna dataset completo e enriquecido do RD Conversas cruzado com Cativa, Vindi e Asaas.
    """
    customers = []
    employees = []
    
    # Cache local
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if isinstance(cached, list) and len(cached) > 0:
                    customers = cached
                elif isinstance(cached, dict) and "customers" in cached:
                    customers = cached["customers"]
                    employees = cached.get("employees", [])
        except Exception as e:
            logger.warning(f"Erro ao ler cache do RD Conversas: {e}")
            
    if not customers or force_refresh:
        api_customers = fetch_all_customers_from_api()
        if api_customers:
            customers = api_customers
            employees = fetch_employees_from_api()
            try:
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"customers": customers, "employees": employees, "cached_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Erro ao salvar cache do RD Conversas: {e}")

    # Fallback para carregar Cativa e Vindi/Asaas de arquivos locais se não forem passados
    if cativa_students is None and os.path.exists(CATIVA_CACHE_FILE):
        try:
            with open(CATIVA_CACHE_FILE, "r", encoding="utf-8") as f:
                c_data = json.load(f)
                cativa_students = c_data.get('students', []) if isinstance(c_data, dict) else c_data
        except Exception:
            pass

    if vindi_subs is None and os.path.exists(VINDI_CACHE_FILE):
        try:
            with open(VINDI_CACHE_FILE, "r", encoding="utf-8") as f:
                v_data = json.load(f)
                vindi_subs = v_data.get('subscriptions', []) if isinstance(v_data, dict) else []
        except Exception:
            pass

    if asaas_subs is None and os.path.exists(ASAAS_CACHE_FILE):
        try:
            with open(ASAAS_CACHE_FILE, "r", encoding="utf-8") as f:
                a_data = json.load(f)
                asaas_subs = a_data.get('subscriptions', []) if isinstance(a_data, dict) else []
        except Exception:
            pass

    # Indexar alunos da Cativa por email e telefone
    c_students = cativa_students or []
    cativa_emails = {str(s.get('email', '')).strip().lower(): s for s in c_students if s.get('email')}
    cativa_phones = {}
    for s in c_students:
        raw_ph = re.sub(r'\D', '', str(s.get('celular') or s.get('telefone') or ''))
        if len(raw_ph) >= 8:
            cativa_phones[raw_ph[-8:]] = s

    # Indexar assinaturas Vindi e Asaas
    v_subs_list = vindi_subs or []
    a_subs_list = asaas_subs or []
    
    vindi_emails = {}
    vindi_names = {}
    for s in v_subs_list:
        em = str(s.get('customer_email') or '').strip().lower()
        nm = str(s.get('customer_name') or '').strip().lower()
        if em: vindi_emails[em] = s
        if nm: vindi_names[nm] = s
        
    asaas_emails = {}
    asaas_names = {}
    for s in a_subs_list:
        em = str(s.get('customer_email') or '').strip().lower()
        nm = str(s.get('customer_name') or '').strip().lower()
        if em: asaas_emails[em] = s
        if nm: asaas_names[nm] = s

    matched_students = []
    unmatched_leads = []
    
    mrr_whatsapp = 0.0
    total_paid_whatsapp = 0.0
    
    for c in customers:
        c_id = c.get('id') or c.get('_id')
        c_name = (c.get('full_name') or 'Lead WhatsApp').strip()
        c_email = (c.get('email') or '').strip().lower()
        c_phone = re.sub(r'\D', '', str(c.get('cel_phone') or ''))
        
        # Match com Cativa
        c_match = None
        if c_email and c_email in cativa_emails:
            c_match = cativa_emails[c_email]
        elif c_phone and len(c_phone) >= 8:
            short_ph = c_phone[-8:]
            if short_ph in cativa_phones:
                c_match = cativa_phones[short_ph]
                
        # Match com Vindi / Asaas para MRR
        v_match = (vindi_emails.get(c_email) if c_email else None) or vindi_names.get(c_name.lower())
        a_match = (asaas_emails.get(c_email) if c_email else None) or asaas_names.get(c_name.lower())
        
        has_active_sub = False
        curso_matriculado = ""
        
        if v_match:
            val = float(v_match.get('valor_parcela') or 0)
            st = str(v_match.get('status_assinatura') or '').lower()
            curso_matriculado = v_match.get('plano') or ''
            if st in ['active', 'em_dia', 'ativo']:
                mrr_whatsapp += val
                has_active_sub = True
            total_paid_whatsapp += float(v_match.get('total_pago') or (val * int(v_match.get('parcelas_pagas') or 0)))
            
        if a_match:
            val = float(a_match.get('valor_parcela') or 0)
            st = str(a_match.get('status_assinatura') or '').lower()
            if not curso_matriculado:
                curso_matriculado = a_match.get('description') or 'Pós-Graduação'
            if st in ['active', 'em_dia', 'received']:
                mrr_whatsapp += val
                has_active_sub = True
            total_paid_whatsapp += float(a_match.get('total_pago') or 0)

        if not curso_matriculado and c_match:
            curso_matriculado = c_match.get('curso_nome') or c_match.get('curso') or 'Aluno Cativa'

        lead_obj = {
            "id": c_id,
            "nome": c_name,
            "email": c_email,
            "telefone": c_phone,
            "telefone_fmt": f"({c_phone[:2]}) {c_phone[2:7]}-{c_phone[7:]}" if len(c_phone) == 11 else (f"({c_phone[:2]}) {c_phone[2:6]}-{c_phone[6:]}" if len(c_phone) == 10 else (c_phone if c_phone else "-")),
            "wa_link": f"https://wa.me/55{c_phone}" if len(c_phone) >= 10 else None,
            "is_aluno": bool(c_match or has_active_sub),
            "curso_matriculado": curso_matriculado if (c_match or has_active_sub) else "Oportunidade Comercial",
            "tem_assinatura_ativa": has_active_sub
        }

        if c_match or has_active_sub:
            matched_students.append(lead_obj)
        else:
            unmatched_leads.append(lead_obj)

    total_customers = len(customers)
    total_convertidos = len(matched_students)
    total_oportunidades = len(unmatched_leads)
    taxa_conversao = (total_convertidos / total_customers * 100) if total_customers > 0 else 0.0

    return {
        "status": "ONLINE",
        "label": "RD Station Conversas (WhatsApp)",
        "total_contatos": total_customers,
        "com_telefone": len([c for c in customers if c.get('cel_phone')]),
        "com_email": len([c for c in customers if c.get('email')]),
        "total_convertidos": total_convertidos,
        "taxa_conversao": round(taxa_conversao, 1),
        "total_oportunidades": total_oportunidades,
        "mrr_whatsapp": round(mrr_whatsapp, 2),
        "total_pago_whatsapp": round(total_paid_whatsapp, 2),
        "employees": employees or [
            {"name": "José Rand", "email": "jose.rand@infectocast.com.br"},
            {"name": "Ester Fortunato", "email": "ester@infectocast.com.br"}
        ],
        "leads_convertidos": matched_students,
        "leads_oportunidades": unmatched_leads
    }

if __name__ == "__main__":
    res = get_rd_conversas_data(force_refresh=False)
    print("RD Conversas Status:", res["status"])
    print(f"Total Contatos: {res['total_contatos']}")
    print(f"Convertidos em Alunos: {res['total_convertidos']} ({res['taxa_conversao']}%)")
    print(f"Oportunidades em Aberto: {res['total_oportunidades']}")
    print(f"MRR WhatsApp: R$ {res['mrr_whatsapp']:,.2f}")
