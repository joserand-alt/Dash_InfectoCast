# -*- coding: utf-8 -*-
"""
Módulo Oficial de Integração com a API do RD Station Conversas (Tallos v2)
- Extração de Contatos, Atendentes e Integrações de WhatsApp
- Cruzamento Cronológico com Alunos da Cativa Digital e Assinaturas Vindi/Asaas
- Diferenciação rigorosa:
  1. Comercial - Oportunidades Quentes (Sem matrícula)
  2. Comercial - Vendas Convertidas (Contato no WhatsApp ANTES da matrícula)
  3. Suporte & CX - Atendimento ao Aluno (Matrícula ANTERIOR ao contato no WhatsApp)
"""

import os
import json
import time
import datetime
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

def parse_iso(d_str):
    if not d_str: return None
    s = str(d_str).strip()
    try:
        return datetime.datetime.fromisoformat(s[:19])
    except Exception:
        pass
    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"]:
        try:
            return datetime.datetime.strptime(s[:19], fmt)
        except Exception:
            pass
    return None

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
    Diferencia Comercial vs Suporte através da cronologia da Matrícula vs Data do Contato.
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

    c_students = cativa_students or []
    v_subs_list = vindi_subs or []
    a_subs_list = asaas_subs or []

    # Mapear a data da primeira fatura / matrícula de cada aluno
    student_first_date = {}
    student_course_map = {}

    for sub in v_subs_list:
        em = str(sub.get('customer_email') or '').strip().lower()
        fats = sub.get('faturas', [])
        dates = [parse_iso(f.get('vencimento_iso') or f.get('vencimento') or f.get('data_pagamento_iso')) for f in fats]
        dates = [d for d in dates if d]
        if dates:
            first_d = min(dates)
            if em and (em not in student_first_date or first_d < student_first_date[em]):
                student_first_date[em] = first_d
                student_course_map[em] = sub.get('plano') or 'Pós-Graduação'

    for sub in a_subs_list:
        em = str(sub.get('customer_email') or '').strip().lower()
        dt = parse_iso(sub.get('dateCreated') or sub.get('primeira_fatura') or sub.get('inicio'))
        if dt and em:
            if em not in student_first_date or dt < student_first_date[em]:
                student_first_date[em] = dt
                student_course_map[em] = sub.get('description') or 'Pós-Graduação'

    cativa_emails = {}
    cativa_phones = {}
    for s in c_students:
        em = str(s.get('email', '')).strip().lower()
        raw_ph = re.sub(r'\D', '', str(s.get('celular') or s.get('telefone') or ''))
        if em:
            cativa_emails[em] = s
            if em not in student_course_map:
                student_course_map[em] = s.get('curso_nome') or s.get('curso') or 'Aluno Cativa'
        if len(raw_ph) >= 8:
            cativa_phones[raw_ph[-8:]] = s
        
        courses = s.get('courses', [])
        for c in courses:
            for l in c.get('lessons', []):
                dt = parse_iso(l.get('updatedAt') or l.get('createdAt'))
                if dt and em:
                    if em not in student_first_date or dt < student_first_date[em]:
                        student_first_date[em] = dt

    leads_oportunidades = []
    leads_convertidos_comercial = []
    leads_suporte_alunos = []
    
    mrr_comercial_convertido = 0.0
    mrr_suporte_base = 0.0

    for c in customers:
        c_id = c.get('id') or c.get('_id') or ''
        c_name = (c.get('full_name') or 'Lead WhatsApp').strip()
        c_email = (c.get('email') or '').strip().lower()
        c_phone = re.sub(r'\D', '', str(c.get('cel_phone') or ''))
        
        # Extrair data de criação do contato a partir do ObjectId MongoDB
        c_dt = None
        if len(c_id) >= 8:
            try:
                c_dt = datetime.datetime.fromtimestamp(int(c_id[:8], 16))
            except Exception:
                pass

        # Verificar se é aluno
        match_s = cativa_emails.get(c_email) or (cativa_phones.get(c_phone[-8:]) if len(c_phone) >= 8 else None)
        first_matr = student_first_date.get(c_email) or (match_s and parse_iso(match_s.get('data_matricula') or match_s.get('created_at')))
        curso = student_course_map.get(c_email) or (match_s and (match_s.get('curso_nome') or match_s.get('curso'))) or ''

        # Buscar MRR
        v_sub = next((s for s in v_subs_list if str(s.get('customer_email', '')).lower() == c_email), None)
        a_sub = next((s for s in a_subs_list if str(s.get('customer_email', '')).lower() == c_email), None)
        sub_val = 0.0
        if v_sub and v_sub.get('status_assinatura') in ['active', 'em_dia', 'ativo']:
            sub_val += float(v_sub.get('valor_parcela') or 0)
        if a_sub and str(a_sub.get('status_assinatura', '')).lower() in ['active', 'em_dia', 'received']:
            sub_val += float(a_sub.get('valor_parcela') or 0)

        is_student = bool(match_s or first_matr or v_sub or a_sub)

        lead_obj = {
            "id": c_id,
            "nome": c_name,
            "email": c_email or "-",
            "telefone": c_phone,
            "telefone_fmt": f"({c_phone[:2]}) {c_phone[2:7]}-{c_phone[7:]}" if len(c_phone) == 11 else (f"({c_phone[:2]}) {c_phone[2:6]}-{c_phone[6:]}" if len(c_phone) == 10 else (c_phone if c_phone else "-")),
            "wa_link": f"https://wa.me/55{c_phone}" if len(c_phone) >= 10 else None,
            "data_contato": c_dt.strftime("%d/%m/%Y") if c_dt else "-",
            "data_matricula": first_matr.strftime("%d/%m/%Y") if first_matr else "-",
            "curso_matriculado": curso or ("Aluno Cativa" if is_student else "Oportunidade Comercial"),
            "mrr": sub_val
        }

        if is_student:
            # SE MATRÍCULA OCORREU ANTES DO CONTATO -> SUPORTE / PÓS-VENDA
            if first_matr and c_dt and first_matr < (c_dt - datetime.timedelta(days=2)):
                lead_obj["tipo_canal"] = "suporte"
                lead_obj["badge_label"] = "Suporte / Aluno Existente"
                lead_obj["badge_color"] = "blue"
                leads_suporte_alunos.append(lead_obj)
                mrr_suporte_base += sub_val
            else:
                # CONTATO OCORREU ANTES OU JUNTO DA MATRÍCULA -> COMERCIAL / VENDA CONVERTIDA
                lead_obj["tipo_canal"] = "venda_convertida"
                lead_obj["badge_label"] = "Comercial / Venda Convertida"
                lead_obj["badge_color"] = "green"
                leads_convertidos_comercial.append(lead_obj)
                mrr_comercial_convertido += sub_val
        else:
            # SEM MATRÍCULA -> OPORTUNIDADE COMERCIAL QUENTE
            lead_obj["tipo_canal"] = "oportunidade"
            lead_obj["badge_label"] = "Comercial / Oportunidade Quente"
            lead_obj["badge_color"] = "amber"
            leads_oportunidades.append(lead_obj)

    total_customers = len(customers)
    total_comercial_atendidos = len(leads_oportunidades) + len(leads_convertidos_comercial)
    total_vendas = len(leads_convertidos_comercial)
    total_suporte = len(leads_suporte_alunos)
    total_oportunidades = len(leads_oportunidades)

    taxa_conversao_comercial = (total_vendas / total_comercial_atendidos * 100) if total_comercial_atendidos > 0 else 0.0

    return {
        "status": "ONLINE",
        "label": "RD Station Conversas (WhatsApp)",
        "total_contatos": total_customers,
        "total_comercial": total_comercial_atendidos,
        "total_oportunidades": total_oportunidades,
        "total_vendas_convertidas": total_vendas,
        "total_suporte": total_suporte,
        "taxa_conversao_comercial": round(taxa_conversao_comercial, 1),
        "mrr_comercial_convertido": round(mrr_comercial_convertido, 2),
        "mrr_suporte_base": round(mrr_suporte_base, 2),
        "employees": employees or [
            {"name": "José Rand", "email": "jose.rand@infectocast.com.br"},
            {"name": "Ester Fortunato", "email": "ester@infectocast.com.br"}
        ],
        "leads_oportunidades": leads_oportunidades,
        "leads_vendas": leads_convertidos_comercial,
        "leads_suporte": leads_suporte_alunos
    }

if __name__ == "__main__":
    res = get_rd_conversas_data(force_refresh=False)
    print("RD Conversas Status:", res["status"])
    print(f"Total Geral Contatos WhatsApp: {res['total_contatos']}")
    print(f"1. Comercial - Total Atendidos: {res['total_comercial']}")
    print(f"   -> Oportunidades Quentes em Aberto: {res['total_oportunidades']}")
    print(f"   -> Vendas Convertidas (Contato <= Matrícula): {res['total_vendas_convertidas']} ({res['taxa_conversao_comercial']}%)")
    print(f"2. Suporte & CX - Atendimento a Alunos Existentes (Matrícula < Contato): {res['total_suporte']}")
