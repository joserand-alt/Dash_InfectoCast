import os
import json
import base64
import urllib.request
import urllib.parse
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
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return True, data, None
    except Exception as e:
        return False, None, str(e)

def fetch_all_vindi_subscriptions():
    """Busca todas as assinaturas cadastradas na Vindi com paginação completa."""
    subs = []
    page = 1
    print("[VINDI] Buscando assinaturas na API Vindi...")
    while True:
        ok, data, err = _api_get(f"subscriptions?per_page=50&page={page}")
        if not ok or not data:
            break
        batch = data.get('subscriptions', [])
        if not batch:
            break
        subs.extend(batch)
        page += 1
    print(f"[VINDI] Total de {len(subs)} assinaturas encontradas.")
    return subs

def fetch_all_vindi_bills():
    """Busca todas as faturas na API Vindi de forma paralela (ou usa raw se recente)."""
    if os.path.exists(RAW_BILLS_PATH):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(RAW_BILLS_PATH))
            if datetime.now() - mtime < timedelta(hours=CACHE_TTL_HOURS):
                with open(RAW_BILLS_PATH, 'r', encoding='utf-8') as f:
                    bills = json.load(f)
                print(f"[VINDI] Carregadas {len(bills)} faturas do raw cache local.")
                return bills
        except Exception as e:
            print(f"[VINDI] Erro ao ler raw bills: {e}")

    print("[VINDI] Baixando faturas da API Vindi com ThreadPoolExecutor...")
    bills = []
    max_pages = 85
    def _fetch(p):
        ok, data, _ = _api_get(f"bills?per_page=50&page={p}")
        return p, data.get('bills', []) if ok and data else []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch, p): p for p in range(1, max_pages + 1)}
        for f in as_completed(futures):
            p, batch = f.result()
            if batch:
                bills.extend(batch)

    print(f"[VINDI] Total de {len(bills)} faturas baixadas.")
    try:
        with open(RAW_BILLS_PATH, 'w', encoding='utf-8') as f:
            json.dump(bills, f)
    except: pass
    return bills

def _format_date(iso_str):
    if not iso_str: return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y')
    except:
        return iso_str[:10]

def _parse_iso(iso_str):
    if not iso_str: return None
    try:
        return datetime.fromisoformat(iso_str.replace('Z', '+00:00')).replace(tzinfo=None)
    except:
        return None

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

    bills_by_cid = {}
    bills_by_email = {}
    
    total_recebido = 0.0
    total_faturas_pagas = 0
    recebido_mes_atual = 0.0
    total_em_atraso = 0.0
    qtd_em_atraso = 0
    historico_mensal_map = {}
    projecao_mensal_map = {}
    
    faturas_para_tabela_geral = []
    current_ym = now.strftime('%Y-%m')

    for b in bills:
        cid = b.get('customer', {}).get('id')
        cemail = (b.get('customer', {}).get('email') or '').strip().lower()
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
            "plano": b.get('subscription', {}).get('plan', {}).get('name') if b.get('subscription') else ""
        }

        if cid:
            bills_by_cid.setdefault(cid, []).append(fatura_item)
        if cemail:
            bills_by_email.setdefault(cemail, []).append(fatura_item)
        if status == 'paid':
            # Se for vencimento futuro sem data de pagamento efetiva, vai para projeção
            is_future_paid = (paid_dt is None) and (due_dt and due_dt.date() > now.date())
            if is_future_paid:
                ym = due_dt.strftime("%Y-%m")
                projecao_mensal_map[ym] = projecao_mensal_map.get(ym, 0.0) + amount_val
            else:
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
    mrr_ativo_total = 0.0

    for sub in subs:
        c = sub.get('customer', {})
        email = (c.get('email') or '').strip().lower()
        cid = c.get('id')
        if not email:
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

        aluno_bills = []
        if cid and cid in bills_by_cid:
            aluno_bills.extend(bills_by_cid[cid])
        elif email in bills_by_email:
            aluno_bills.extend(bills_by_email[email])

        seen_ids = set()
        unique_bills = []
        for b in aluno_bills:
            if b['id'] not in seen_ids:
                seen_ids.add(b['id'])
                unique_bills.append(b)

        student_overdue_bills = [b for b in unique_bills if b['status'] == 'em_atraso']
        valor_atraso = sum(b['valor'] for b in student_overdue_bills)
        dias_atraso = max([b['dias_atraso'] for b in student_overdue_bills], default=0)

        if sub_status == 'canceled':
            st_fin = 'cancelado'
            st_lbl = 'Cancelado'
            st_color = 'var(--muted)'
            st_bg = 'rgba(0,0,0,0.06)'
        elif student_overdue_bills or overdue_since:
            st_fin = 'em_atraso'
            st_lbl = f'Atraso ({dias_atraso}d)' if dias_atraso > 0 else 'Em Atraso'
            st_color = '#e11d48'
            st_bg = 'rgba(225,29,72,0.1)'
        elif sub_status == 'active':
            st_fin = 'adimplente'
            st_lbl = 'Em Dia'
            st_color = '#059669'
            st_bg = 'rgba(16,185,129,0.1)'
            mrr_ativo_total += price
            
            if next_b_dt:
                base_dt = next_b_dt if next_b_dt > now else (now + timedelta(days=5))
                for m_offset in range(6):
                    proj_dt = base_dt + timedelta(days=30 * m_offset)
                    ym = proj_dt.strftime('%Y-%m')
                    projecao_mensal_map[ym] = projecao_mensal_map.get(ym, 0.0) + price
                    
                    if m_offset > 0 or not any(b['status'] == 'a_vencer' for b in unique_bills):
                        proj_fmt = proj_dt.strftime('%d/%m/%Y')
                        unique_bills.append({
                            "id": f"proj-{sub.get('id')}-{m_offset}",
                            "status": "futuro",
                            "status_label": "Futuro (Agendado)",
                            "valor": price,
                            "valor_fmt": f"R$ {price:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                            "vencimento": proj_fmt,
                            "vencimento_iso": proj_dt.isoformat(),
                            "data_pagamento": "",
                            "data_pagamento_iso": "",
                            "forma_pagamento": sub.get('payment_method', {}).get('public_name') or 'Recorrência',
                            "url": f"https://app.vindi.com.br/admin/subscriptions/{sub.get('id')}",
                            "dias_atraso": 0,
                            "aluno": c.get('name'),
                            "email": email,
                            "plano": sub.get('plan', {}).get('name') or ""
                        })
        elif sub_status in ['expired', 'inactive']:
            st_fin = 'quitado'
            st_lbl = 'Quitado'
            st_color = '#64748b'
            st_bg = 'rgba(100,116,139,0.1)'
        else:
            st_fin = sub_status
            st_lbl = sub_status.capitalize()
            st_color = 'var(--muted)'
            st_bg = 'rgba(0,0,0,0.05)'

        sub_pm = sub.get('payment_method', {}).get('public_name') or sub.get('payment_method', {}).get('name') or 'Outro'
        unique_bills.sort(key=lambda x: x.get('vencimento_iso') or x.get('data_pagamento_iso') or '', reverse=True)

        students_vindi[email] = {
            "has_vindi": True,
            "customer_id": cid,
            "customer_name": c.get('name') or '',
            "customer_email": email,
            "subscription_id": sub.get('id'),
            "plano": sub.get('plan', {}).get('name') or 'Assinatura Pós-Graduação',
            "status_assinatura": sub_status,
            "status_financeiro": st_fin,
            "status_label": st_lbl,
            "status_color": st_color,
            "status_bg": st_bg,
            "forma_pagamento": sub_pm,
            "valor_parcela": price,
            "proximo_vencimento": next_b_fmt,
            "dias_atraso": dias_atraso,
            "valor_atraso": valor_atraso,
            "faturas": unique_bills
        }

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

    projecao_mensal = []
    sorted_proj_ym = sorted(projecao_mensal_map.keys())
    for ym in sorted_proj_ym:
        if ym < current_ym: continue
        y, m = ym.split('-')
        lbl = f"{meses_pt.get(m, m)}/{y[2:]}"
        realizado_val = historico_mensal_map.get(ym, {}).get('pago', 0.0) if ym == current_ym else 0.0
        projecao_mensal.append({
            "mes": ym,
            "label": lbl,
            "previsto": round(projecao_mensal_map[ym], 2),
            "realizado": round(realizado_val, 2)
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
        "financeiro": financeiro_global
    }

    try:
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(result, f)
        print(f"[VINDI] Cache atualizado com sucesso ({len(students_vindi)} alunos e financeiro global).")
    except Exception as e:
        print(f"[VINDI] Erro ao salvar cache: {e}")

    return result

if __name__ == '__main__':
    res = get_vindi_data(force_reload=True)
    print("Concluído!")
    print(f"Alunos mapeados: {len(res['data'])}")
    print(f"Receita Total: {res['financeiro']['kpis']['total_recebido_fmt']}")
    print(f"Em Atraso: {res['financeiro']['kpis']['total_em_atraso_fmt']}")
    print(f"MRR Ativo: {res['financeiro']['kpis']['mrr_ativo_fmt']}")
