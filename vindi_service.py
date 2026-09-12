# -*- coding: utf-8 -*-
"""
Vindi API Service
Integração 100% via API com a Vindi:
1. Coleta todas as assinaturas (/api/v1/subscriptions)
2. Coleta todas as faturas/cobranças (/api/v1/bills)
3. Relaciona dados por aluno, isolando as faturas por assinatura/curso.
"""

import os
import json
import base64
import urllib.request
import urllib.parse
import unicodedata
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = "aSMUzblpf9KDU0hrzVT-RkUJyIT7xfuMipfjfQsqoBY"
BASE_URL = "https://app.vindi.com.br/api/v1/"
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vindi_cache.json')
RAW_BILLS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'all_vindi_bills_raw.json')
CACHE_TTL_HOURS = 3

def _get_headers():
    auth_str = base64.b64encode(f"{API_KEY}:".encode('utf-8')).decode('ascii')
    return {
        'Authorization': f'Basic {auth_str}',
        'Content-Type': 'application/json',
        'User-Agent': 'InfectoCast-Dashboard/2.0'
    }

def _api_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers=_get_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"[VINDI] Erro ao consultar {endpoint}: {e}")
        return None

def fetch_all_vindi_subscriptions():
    print("[VINDI] Buscando assinaturas na API Vindi...")
    subscriptions = []
    page = 1
    per_page = 50
    while True:
        data = _api_get(f"subscriptions?page={page}&per_page={per_page}")
        if not data or 'subscriptions' not in data:
            break
        items = data['subscriptions']
        if not items:
            break
        subscriptions.extend(items)
        if len(items) < per_page:
            break
        page += 1
    print(f"[VINDI] Total de {len(subscriptions)} assinaturas encontradas.")
    return subscriptions

def fetch_all_vindi_bills():
    if os.path.exists(RAW_BILLS_PATH):
        try:
            with open(RAW_BILLS_PATH, 'r', encoding='utf-8') as f:
                cached_bills = json.load(f)
                if len(cached_bills) > 0:
                    print(f"[VINDI] Carregadas {len(cached_bills)} faturas do raw cache local.")
                    return cached_bills
        except Exception:
            pass

    print("[VINDI] Baixando faturas da API Vindi com ThreadPoolExecutor...")
    first_page = _api_get("bills?page=1&per_page=50")
    if not first_page or 'bills' not in first_page:
        return []
    
    total_est_pages = 80
    all_bills = list(first_page['bills'])

    def _fetch(p):
        d = _api_get(f"bills?page={p}&per_page=50")
        return d.get('bills', []) if d else []

    with ThreadPoolExecutor(max_workers=10) as ex:
        pages_data = list(ex.map(_fetch, range(2, total_est_pages + 1)))

    for b_list in pages_data:
        all_bills.extend(b_list)

    seen = set()
    unique_bills = []
    for b in all_bills:
        if b['id'] not in seen:
            seen.add(b['id'])
            unique_bills.append(b)

    try:
        with open(RAW_BILLS_PATH, 'w', encoding='utf-8') as f:
            json.dump(unique_bills, f, ensure_ascii=False)
    except Exception:
        pass

    print(f"[VINDI] Total de {len(unique_bills)} faturas baixadas.")
    return unique_bills

def _format_date(iso_str):
    if not iso_str: return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return iso_str[:10] if len(iso_str) >= 10 else iso_str

def _parse_iso(iso_str):
    if not iso_str: return None
    try:
        return datetime.fromisoformat(iso_str.replace('Z', '+00:00')).replace(tzinfo=None)
    except Exception:
        return None

def normalize_vindi_course(name):
    if not name or str(name).lower() in ['none', 'nan', '']:
        return 'PLATAFORMA GERAL'
    n = str(name).strip().upper()
    n = ''.join(c for c in unicodedata.normalize('NFD', n) if unicodedata.category(c) != 'Mn')
    
    if any(k in n for k in ['ORTOPED', 'ORTO', 'PARTES MOLES', 'PELE', 'MUSCULO']):
        return 'POS-GRADUACAO EM INFECCOES ORTOPEDICAS E DE PARTES MOLES'
    if any(k in n for k in ['CCIH', 'PREVENCAO', 'HOSPITALAR', 'PAV', 'ISC']):
        if 'FARM' in n:
            return 'POS-GRADUACAO EM PREVENCAO E CONTROLE DE INFECCAO HOSPITALAR (CCIH) - FARMACIA'
        elif 'ENF' in n:
            return 'POS-GRADUACAO EM PREVENCAO E CONTROLE DE INFECCAO HOSPITALAR (CCIH) - ENFERMAGEM'
        return 'POS-GRADUACAO EM PREVENCAO E CONTROLE DE INFECCAO HOSPITALAR (CCIH)'
    if any(k in n for k in ['IMUNO', 'INUNO', 'TRANSPLANT']):
        return 'POS-GRADUACAO EM INFECTOLOGIA DO PACIENTE IMUNODEPRIMIDO'
    if any(k in n for k in ['PED', 'INFECTOPED', 'CRIANCA', 'NEONATAL']):
        return 'POS-GRADUACAO EM INFECTOPEDIATRIA'
    if any(k in n for k in ['MULTI-R', 'MULTIR', 'MULTI R']):
        return 'JORNADA MULTI-R'
    if any(k in n for k in ['FUNGO', 'ANTIFUNGIC']):
        return 'DO FUNGO AO ANTIFUNGICO'
    if any(k in n for k in ['SOS', 'ANTIBIOTICO', 'ATB', 'MDR']):
        return 'S.O.S ANTIBIOTICO'
    if any(k in n for k in ['FERRAMENTA', 'QUALIDADE', 'ISHIKAWA', 'PDCA']):
        return 'FERRAMENTAS DE QUALIDADE'
    if any(k in n for k in ['INFECTOXPERT', 'EXPERT']):
        return 'INFECTOXPERT'
    if any(k in n for k in ['NUTRIFY']):
        return 'NUTRIFY CONNECT'
        
    return 'PLATAFORMA GERAL'


def get_vindi_data(force_reload=False):
    """
    Retorna o dicionário completo com dados por aluno e agregações globais da Aba Financeiro.
    """
    if not force_reload and os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            cached_at = datetime.fromisoformat(cached.get('cached_at', '2000-01-01'))
            if datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS) and 'financeiro' in cached:
                print(f"[VINDI CACHE] Carregados dados da Vindi com financeiro global ({len(cached.get('data', {}))} alunos).")
                return cached
        except Exception as e:
            print(f"[VINDI CACHE] Rebuscando: {e}")

    subs = fetch_all_vindi_subscriptions()
    bills = fetch_all_vindi_bills()
    now = datetime.now()

    paid_customers_cid = set()
    paid_customers_email = set()
    for b in bills:
        if b.get('status') == 'paid':
            cid_p = b.get('customer', {}).get('id')
            cemail_p = (b.get('customer', {}).get('email') or '').strip().lower()
            if cid_p: paid_customers_cid.add(cid_p)
            if cemail_p: paid_customers_email.add(cemail_p)

    bills_by_sub_id = {}
    bills_by_cid = {}
    bills_by_email = {}
    
    total_recebido = 0.0
    total_faturas_pagas = 0
    recebido_mes_atual = 0.0
    total_em_atraso = 0.0
    qtd_em_atraso = 0
    historico_mensal_map = {}
    
    faturas_para_tabela_geral = []
    current_ym = now.strftime('%Y-%m')

    for b in bills:
        cid = b.get('customer', {}).get('id')
        cemail = (b.get('customer', {}).get('email') or '').strip().lower()
        if (cid not in paid_customers_cid) and (cemail not in paid_customers_email):
            continue
        cname = b.get('customer', {}).get('name') or 'Cliente'
        
        status = b.get('status', 'pending')
        amount_val = 0.0
        try: amount_val = float(b.get('amount', 0) or 0)
        except: pass

        due_iso = b.get('due_at')
        due_dt = _parse_iso(due_iso)
        due_fmt = _format_date(due_iso)

        charges = b.get('charges', [])
        c0 = charges[0] if charges else {}
        paid_iso = c0.get('paid_at')
        paid_dt = _parse_iso(paid_iso)
        paid_fmt = _format_date(paid_iso)

        pm_obj = c0.get('payment_method') or b.get('payment_method') or {}
        pm_name = pm_obj.get('public_name') or pm_obj.get('name') or pm_obj.get('type') or 'Outro'
        if 'cart' in pm_name.lower() or 'credit' in pm_name.lower():
            pm_tipo = 'Cartão de Crédito'
        elif 'boleto' in pm_name.lower():
            pm_tipo = 'Boleto'
        elif 'pix' in pm_name.lower():
            pm_tipo = 'Pix'
        else:
            pm_tipo = pm_name

        is_overdue = False
        days_overdue = 0
        if status == 'pending':
            if due_dt and due_dt < now:
                is_overdue = True
                days_overdue = max(1, (now - due_dt).days)
                status_label = f"Em Atraso ({days_overdue}d)"
                status_key = 'em_atraso'
            else:
                status_label = "A Vencer"
                status_key = 'a_vencer'
        elif status == 'paid':
            status_label = "Pago"
            status_key = 'pago'
        elif status == 'canceled':
            status_label = "Cancelado"
            status_key = 'cancelado'
        else:
            status_label = status.capitalize()
            status_key = status

        url = b.get('url') or (c0.get('print_url') if c0 else None) or f"https://app.vindi.com.br/customer/bills/{b.get('id')}"
        sub_obj = b.get('subscription') or {}
        sub_id_bill = sub_obj.get('id')
        plan_name_bill = sub_obj.get('plan', {}).get('name') or ""

        fatura_item = {
            "id": b.get('id'),
            "status": status_key,
            "status_label": status_label,
            "valor": amount_val,
            "valor_fmt": f"R$ {amount_val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            "vencimento": due_fmt,
            "vencimento_iso": due_iso or "",
            "data_pagamento": paid_fmt,
            "data_pagamento_iso": paid_iso or "",
            "forma_pagamento": pm_tipo,
            "url": url,
            "dias_atraso": days_overdue,
            "aluno": cname,
            "email": cemail,
            "subscription_id": sub_id_bill,
            "plano": plan_name_bill,
            "curso": normalize_vindi_course(plan_name_bill)
        }

        if sub_id_bill:
            bills_by_sub_id.setdefault(sub_id_bill, []).append(fatura_item)
        if cid:
            bills_by_cid.setdefault(cid, []).append(fatura_item)
        if cemail:
            bills_by_email.setdefault(cemail, []).append(fatura_item)

        if status == 'paid':
            total_recebido += amount_val
            total_faturas_pagas += 1
            ref_dt = paid_dt or due_dt or _parse_iso(b.get('created_at'))
            if ref_dt:
                ym = ref_dt.strftime('%Y-%m')
                if ym not in historico_mensal_map:
                    historico_mensal_map[ym] = {'pago': 0.0, 'qtd': 0}
                historico_mensal_map[ym]['pago'] += amount_val
                historico_mensal_map[ym]['qtd'] += 1
                if ym == current_ym:
                    recebido_mes_atual += amount_val
        elif is_overdue:
            total_em_atraso += amount_val
            qtd_em_atraso += 1

        faturas_para_tabela_geral.append(fatura_item)

    faturas_para_tabela_geral.sort(key=lambda x: x.get('data_pagamento_iso') or x.get('vencimento_iso') or '', reverse=True)

    students_vindi = {}
    subscriptions_list = []
    mrr_ativo_total = 0.0
    projecao_mensal_map = {}

    for sub in subs:
        c = sub.get('customer', {})
        email = (c.get('email') or '').strip().lower()
        cid = c.get('id')
        sub_id = sub.get('id')
        if not email:
            continue
        if (cid not in paid_customers_cid) and (email not in paid_customers_email):
            continue

        price = 0.0
        for it in sub.get('product_items', []):
            ps = it.get('pricing_schema', {})
            if ps.get('price'):
                try: price += float(ps['price'])
                except: pass
        if price == 0 and sub.get('plan'):
            for it in sub.get('plan', {}).get('plan_items', []):
                ps = it.get('pricing_schema', {})
                if ps.get('price'):
                    try: price += float(ps['price'])
                    except: pass

        sub_status = sub.get('status', 'active')
        next_b_iso = sub.get('next_billing_at')
        next_b_dt = _parse_iso(next_b_iso)
        next_b_fmt = _format_date(next_b_iso)
        overdue_since = sub.get('overdue_since')
        plan_name = sub.get('plan', {}).get('name') or 'Assinatura Pós-Graduação'
        course_name = normalize_vindi_course(plan_name)

        # Matched bills for this subscription + customer's faturas avulsas
        aluno_bills = []
        if sub_id and sub_id in bills_by_sub_id:
            aluno_bills.extend(bills_by_sub_id[sub_id])
            
        # Also include customer's faturas avulsas (subscription is None)
        faturas_avulsas = []
        if cid and cid in bills_by_cid:
            for b in bills_by_cid[cid]:
                if not b.get('subscription_id'):
                    faturas_avulsas.append(b)
        elif email in bills_by_email:
            for b in bills_by_email[email]:
                if not b.get('subscription_id'):
                    faturas_avulsas.append(b)
                    
        for fa in faturas_avulsas:
            fa_copy = dict(fa)
            fa_copy['is_fatura_avulsa'] = True
            fa_copy['plano'] = f"Fatura Avulsa ({plan_name})"
            fa_copy['curso'] = course_name
            aluno_bills.append(fa_copy)

        seen_ids = set()
        unique_bills = []
        for b in aluno_bills:
            if b['id'] not in seen_ids:
                seen_ids.add(b['id'])
                unique_bills.append(b)

        # Check for paid fatura avulsa (renegociação / acordo)
        has_paid_renegociacao = any(b.get('is_fatura_avulsa') and b.get('status') in ['paid', 'pago'] for b in unique_bills)
        
        student_overdue_bills = [b for b in unique_bills if b['status'] == 'em_atraso' and not b.get('is_fatura_avulsa')]
        dias_atraso = max([b.get('dias_atraso', 0) for b in student_overdue_bills], default=0)
        valor_atraso = sum(b.get('valor', 0) for b in student_overdue_bills)

        paid_bills_count = sum(1 for b in unique_bills if b['status'] in ['paid', 'pago'])

        if student_overdue_bills and not has_paid_renegociacao:
            st_fin = 'em_atraso'
            st_lbl = 'Em Atraso'
            st_color = 'var(--rose-d)'
            st_bg = 'var(--rose-bg)'
        elif sub_status == 'active':
            st_fin = 'adimplente'
            st_lbl = 'Adimplente'
            st_color = 'var(--emerald-d)'
            st_bg = 'var(--emerald-bg)'
        elif sub_status in ['expired', 'inactive']:
            if has_paid_renegociacao or paid_bills_count > 0:
                st_fin = 'quitado'
                st_lbl = 'Quitado (Acordo/Renegociação)' if has_paid_renegociacao else 'Quitado'
                st_color = '#64748b'
                st_bg = 'rgba(100,116,139,0.1)'
            else:
                st_fin = 'inativo'
                st_lbl = 'Inativo'
                st_color = 'var(--muted)'
                st_bg = 'rgba(0,0,0,0.05)'
        elif sub_status == 'canceled':
            if has_paid_renegociacao or paid_bills_count > 0:
                st_fin = 'quitado' if has_paid_renegociacao else 'cancelado'
                st_lbl = 'Quitado (Renegociação)' if has_paid_renegociacao else 'Cancelado'
                st_color = '#64748b' if has_paid_renegociacao else 'var(--muted)'
                st_bg = 'rgba(100,116,139,0.1)' if has_paid_renegociacao else 'rgba(0,0,0,0.05)'
            else:
                st_fin = 'cancelado'
                st_lbl = 'Cancelado'
                st_color = 'var(--muted)'
                st_bg = 'rgba(0,0,0,0.05)'
        else:
            st_fin = sub_status
            st_lbl = sub_status.capitalize()
            st_color = 'var(--muted)'
            st_bg = 'rgba(0,0,0,0.05)'

        sub_pm = sub.get('payment_method', {}).get('public_name') or sub.get('payment_method', {}).get('name') or 'Outro'
        unique_bills.sort(key=lambda x: x.get('vencimento_iso') or x.get('data_pagamento_iso') or '', reverse=True)

        # Calculate a quality score for this subscription to select the best one
        sub_score = 0
        if sub_status == 'active': sub_score += 1000
        elif sub_status in ['expired', 'inactive']: sub_score += 500
        elif sub_status == 'canceled': sub_score += 100
        sub_score += (paid_bills_count * 50)
        if has_paid_renegociacao: sub_score += 300

        sub_data = {
            "has_vindi": True,
            "customer_id": cid,
            "customer_name": c.get('name') or '',
            "customer_email": email,
            "subscription_id": sub_id,
            "plano": plan_name,
            "curso": course_name,
            "status_assinatura": sub_status,
            "status_financeiro": st_fin,
            "status_label": st_lbl,
            "status_color": st_color,
            "status_bg": st_bg,
            "forma_pagamento": sub_pm,
            "valor_parcela": price,
            "proximo_vencimento": next_b_fmt,
            "dias_atraso": dias_atraso if not has_paid_renegociacao else 0,
            "valor_atraso": valor_atraso if not has_paid_renegociacao else 0.0,
            "has_renegociacao": has_paid_renegociacao,
            "faturas": unique_bills,
            "_score": sub_score
        }

        subscriptions_list.append(sub_data)
        
        # Save by email prioritizing higher score
        if email not in students_vindi or sub_score > students_vindi[email].get('_score', 0):
            students_vindi[email] = sub_data
            
        key_ec = f"{email}___{course_name}"
        if key_ec not in students_vindi or sub_score > students_vindi[key_ec].get('_score', 0):
            students_vindi[key_ec] = sub_data


    sorted_ym = sorted(historico_mensal_map.keys())
    meses_pt = {'01':'Jan','02':'Fev','03':'Mar','04':'Abr','05':'Mai','06':'Jun','07':'Jul','08':'Ago','09':'Set','10':'Out','11':'Nov','12':'Dez'}
    historico_mensal = []
    for ym in sorted_ym[-14:]:
        y, m = ym.split('-')
        lbl = f"{meses_pt.get(m, m)}/{y[2:]}"
        historico_mensal.append({
            "mes": ym,
            "label": lbl,
            "pago": round(historico_mensal_map[ym]['pago'], 2),
            "qtd": historico_mensal_map[ym]['qtd']
        })

    sorted_proj_ym = sorted([ym for ym in projecao_mensal_map.keys() if ym >= current_ym])
    projecao_mensal = []
    for ym in sorted_proj_ym[:6]:
        y, m = ym.split('-')
        lbl = f"{meses_pt.get(m, m)}/{y[2:]}"
        projecao_mensal.append({
            "mes": ym,
            "label": lbl,
            "previsto": round(projecao_mensal_map[ym], 2)
        })

    proj_30d = projecao_mensal[0]['previsto'] if len(projecao_mensal) > 0 else mrr_ativo_total
    proj_60d = sum(p['previsto'] for p in projecao_mensal[:2]) if len(projecao_mensal) >= 2 else (mrr_ativo_total * 2)
    proj_12m = mrr_ativo_total * 12
    total_faturado = total_recebido + total_em_atraso
    taxa_adimp = round((total_recebido / total_faturado * 100)) if total_faturado > 0 else 100

    financeiro_global = {
        "kpis": {
            "total_recebido": round(total_recebido, 2),
            "total_recebido_fmt": f"R$ {total_recebido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            "total_faturas_pagas": total_faturas_pagas,
            "recebido_mes_atual": round(recebido_mes_atual, 2),
            "recebido_mes_atual_fmt": f"R$ {recebido_mes_atual:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            "total_em_atraso": round(total_em_atraso, 2),
            "total_em_atraso_fmt": f"R$ {total_em_atraso:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            "qtd_em_atraso": qtd_em_atraso,
            "mrr_ativo": round(mrr_ativo_total, 2),
            "mrr_ativo_fmt": f"R$ {mrr_ativo_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            "projecao_30d": round(proj_30d, 2),
            "projecao_30d_fmt": f"R$ {proj_30d:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            "projecao_60d": round(proj_60d, 2),
            "projecao_60d_fmt": f"R$ {proj_60d:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            "projecao_12m": round(proj_12m, 2),
            "projecao_12m_fmt": f"R$ {proj_12m:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            "taxa_adimplencia": taxa_adimp
        },
        "historico_mensal": historico_mensal,
        "projecao_mensal": projecao_mensal,
        "faturas_tabela": faturas_para_tabela_geral,
        "faturas_recentes": faturas_para_tabela_geral[:300]
    }

    result = {
        "cached_at": now.isoformat(),
        "total_matched": len(students_vindi),
        "data": students_vindi,
        "subscriptions": subscriptions_list,
        "financeiro": financeiro_global
    }

    try:
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[VINDI] Cache atualizado com sucesso ({len(students_vindi)} alunos e financeiro global).")
    except Exception as e:
        print(f"[VINDI] Erro ao salvar cache: {e}")

    return result

if __name__ == '__main__':
    res = get_vindi_data(force_reload=True)
    print("Concluído!")
    print(f"Alunos mapeados: {len(res['data'])}")
    print(f"Receita Total: {res['financeiro']['kpis']['total_recebido_fmt']}")
