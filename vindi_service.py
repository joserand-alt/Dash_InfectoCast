import urllib.request
import base64
import json
import ssl
import os
from datetime import datetime, timedelta

API_KEY = 'aSMUzblpf9KDU0hrzVT-RkUJyIT7xfuMipfjfQsqoBY'
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vindi_cache.json')
CACHE_TTL_HOURS = 3

auth_str = base64.b64encode(f'{API_KEY}:'.encode('utf-8')).decode('utf-8')
HEADERS = {
    'Authorization': f'Basic {auth_str}',
    'Accept': 'application/json',
    'User-Agent': 'InfectoCast-Dashboard/1.0'
}

ctx = ssl.create_default_context()

def _api_get(endpoint):
    url = f'https://app.vindi.com.br/api/v1/{endpoint}'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=25) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            total = resp.headers.get('Total', None)
            return True, data, total
    except Exception as e:
        return False, str(e), None

def fetch_all_vindi_subscriptions():
    print("[VINDI] Buscando todas as assinaturas na API Vindi...")
    all_subs = []
    page = 1
    while True:
        ok, res, total = _api_get(f'subscriptions?per_page=50&page={page}')
        if not ok:
            print(f"[VINDI] Erro ao buscar assinaturas na página {page}: {res}")
            break
        batch = res.get('subscriptions', [])
        if not batch:
            break
        all_subs.extend(batch)
        if len(all_subs) >= int(total or 0) or len(batch) < 50:
            break
        page += 1
    print(f"[VINDI] Total de {len(all_subs)} assinaturas carregadas.")
    return all_subs

def fetch_pending_and_recent_bills():
    print("[VINDI] Buscando faturas pendentes e recentes na API Vindi...")
    bills = []
    # 1. Faturas pendentes (status:pending)
    page = 1
    while True:
        ok, res, total = _api_get(f'bills?query=status:pending&per_page=50&page={page}')
        if not ok: break
        batch = res.get('bills', [])
        if not batch: break
        bills.extend(batch)
        if len(batch) < 50 or (total and len(bills) >= int(total)):
            break
        page += 1
    print(f"[VINDI] {len(bills)} faturas pendentes carregadas.")
    
    # 2. Amostra de faturas recentes pagas (primeiras 2 páginas = 100 faturas mais recentes)
    page = 1
    while page <= 2:
        ok, res, _ = _api_get(f'bills?query=status:paid&per_page=50&page={page}')
        if ok:
            batch = res.get('bills', [])
            if not batch: break
            bills.extend(batch)
            page += 1
        else:
            break
    print(f"[VINDI] Total combinado de {len(bills)} faturas para conciliação.")
    return bills

def get_vindi_data(force_reload=False):
    """
    Retorna um dicionário indexado por e-mail com os dados financeiros da Vindi:
    {
      "aluno@email.com": {
         "has_vindi": True,
         "customer_id": 12345,
         "customer_name": "Nome",
         "status_financeiro": "adimplente" | "em_atraso" | "a_vencer" | "quitado" | "cancelado",
         "plano": "Pós-Graduação ...",
         "forma_pagamento": "Boleto",
         "valor_parcela": 1179.80,
         "proximo_vencimento": "17/09/2026",
         "dias_atraso": 0,
         "valor_atraso": 0.0,
         "faturas": [ ... ]
      }
    }
    """
    # Verificar cache
    if not force_reload and os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            cached_at = datetime.fromisoformat(cached.get('cached_at', '2000-01-01'))
            if datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS):
                print(f"[VINDI CACHE] Carregados dados da Vindi do cache local ({cached.get('total_matched', 0)} alunos mapeados).")
                return cached.get('data', {})
        except Exception as e:
            print(f"[VINDI CACHE] Erro ao ler cache: {e}. Rebuscando na API...")

    # Buscar dados frescos
    subs = fetch_all_vindi_subscriptions()
    bills = fetch_pending_and_recent_bills()
    
    # Agrupar faturas por customer_id
    bills_by_customer = {}
    now = datetime.now()
    
    for b in bills:
        c = b.get('customer', {})
        cid = c.get('id')
        if not cid: continue
        if cid not in bills_by_customer:
            bills_by_customer[cid] = []
            
        due_str = b.get('due_at')
        is_overdue = False
        days_overdue = 0
        if b.get('status') == 'pending' and due_str:
            try:
                # Ex: 2025-03-17T23:59:59.000-03:00
                due_dt = datetime.fromisoformat(due_str.replace('Z', '+00:00')).replace(tzinfo=None)
                if due_dt < now:
                    is_overdue = True
                    days_overdue = (now - due_dt).days
            except:
                pass
                
        # Detalhes de pagamento
        charges = b.get('charges', [])
        pm_name = 'Boleto / PIX'
        if charges:
            pm = charges[0].get('payment_method', {})
            pm_name = pm.get('public_name') or pm.get('name') or pm_name
            
        due_fmt = ""
        if due_str:
            try:
                due_fmt = datetime.fromisoformat(due_str.replace('Z', '+00:00')).strftime('%d/%m/%Y')
            except:
                due_fmt = due_str[:10]

        bills_by_customer[cid].append({
            "id": b.get('id'),
            "valor": float(b.get('amount') or 0.0),
            "status": b.get('status'),
            "vencimento": due_fmt,
            "url": b.get('url'),
            "forma": pm_name,
            "is_overdue": is_overdue,
            "days_overdue": days_overdue
        })

    # Processar cada assinatura por e-mail do cliente
    vindi_map = {}
    
    for s in subs:
        c = s.get('customer', {})
        email = (c.get('email') or '').lower().strip()
        if not email: continue
        
        cid = c.get('id')
        plan = s.get('plan', {})
        plan_name = plan.get('name', 'Pós-Graduação')
        sub_status = s.get('status') # active, expired, canceled
        
        # Próxima cobrança
        next_bill_str = s.get('next_billing_at')
        next_bill_fmt = None
        days_to_next = 999
        if next_bill_str:
            try:
                nb_dt = datetime.fromisoformat(next_bill_str.replace('Z', '+00:00')).replace(tzinfo=None)
                next_bill_fmt = nb_dt.strftime('%d/%m/%Y')
                days_to_next = (nb_dt - now).days
            except:
                next_bill_fmt = next_bill_str[:10]

        # Faturas do cliente
        c_bills = bills_by_customer.get(cid, [])
        overdue_bills = [b for b in c_bills if b.get('is_overdue')]
        total_overdue_val = sum(b.get('valor', 0.0) for b in overdue_bills)
        max_days_overdue = max([b.get('days_overdue', 0) for b in overdue_bills], default=0)
        
        # Determinar status financeiro consolidado
        if overdue_bills or s.get('overdue_since'):
            fin_status = 'em_atraso'
            fin_label = f'Em Atraso ({max_days_overdue}d)'
            fin_color = 'var(--coral)'
            fin_bg = 'var(--coral-w)'
        elif sub_status == 'active':
            if 0 <= days_to_next <= 7:
                fin_status = 'a_vencer'
                fin_label = f'Vence em {days_to_next}d'
                fin_color = 'var(--amber)'
                fin_bg = 'var(--amber-w)'
            else:
                fin_status = 'adimplente'
                fin_label = 'Em Dia'
                fin_color = 'var(--emerald-d)'
                fin_bg = 'var(--emerald-w)'
        elif sub_status == 'expired':
            fin_status = 'quitado'
            fin_label = 'Ciclo Concluído'
            fin_color = '#64748b'
            fin_bg = 'rgba(100,116,139,0.1)'
        elif sub_status == 'canceled':
            fin_status = 'cancelado'
            fin_label = 'Cancelado'
            fin_color = 'var(--muted)'
            fin_bg = 'rgba(0,0,0,0.06)'
        else:
            fin_status = sub_status or 'outro'
            fin_label = str(sub_status).title()
            fin_color = 'var(--muted)'
            fin_bg = 'rgba(0,0,0,0.06)'

        # Forma de pagamento da assinatura
        pm = s.get('payment_method', {})
        forma_pgto = pm.get('public_name') or pm.get('name') or 'Boleto / Cartão'
        
        # Estimar valor da parcela pelo primeiro produto ou fatura
        valor_parcela = 0.0
        if c_bills:
            valor_parcela = c_bills[0].get('valor', 0.0)
            
        sub_info = {
            "has_vindi": True,
            "customer_id": cid,
            "customer_name": c.get('name'),
            "customer_email": email,
            "subscription_id": s.get('id'),
            "plano": plan_name,
            "status_assinatura": sub_status,
            "status_financeiro": fin_status,
            "status_label": fin_label,
            "status_color": fin_color,
            "status_bg": fin_bg,
            "forma_pagamento": forma_pgto,
            "valor_parcela": valor_parcela,
            "proximo_vencimento": next_bill_fmt,
            "dias_atraso": max_days_overdue,
            "valor_atraso": total_overdue_val,
            "faturas": c_bills[:8] # últimas 8 faturas
        }
        
        # Se o cliente já tiver registro (ex: mais de uma assinatura), priorizar a ativa ou em atraso
        if email in vindi_map:
            old_st = vindi_map[email].get('status_financeiro')
            if fin_status == 'em_atraso' or (fin_status == 'adimplente' and old_st != 'em_atraso'):
                vindi_map[email] = sub_info
        else:
            vindi_map[email] = sub_info

    # Salvar cache
    try:
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump({
                'cached_at': datetime.now().isoformat(),
                'total_matched': len(vindi_map),
                'data': vindi_map
            }, f, ensure_ascii=False, indent=2)
        print(f"[VINDI CACHE] Cache salvo com sucesso: {len(vindi_map)} alunos mapeados.")
    except Exception as ex:
        print(f"[VINDI CACHE] Erro ao salvar cache: {ex}")

    return vindi_map

if __name__ == '__main__':
    data = get_vindi_data(force_reload=True)
    print(f"\nConcluído! {len(data)} alunos indexados na Vindi.")
    # Contagem de status
    from collections import Counter
    st_count = Counter(v.get('status_financeiro') for v in data.values())
    print("Distribuição de status financeiro:", st_count)
    
    # Exemplo de aluno em atraso
    for email, v in data.items():
        if v.get('status_financeiro') == 'em_atraso':
            print(f"Exemplo em atraso: {v['customer_name']} ({email}) -> {v['dias_atraso']} dias, R$ {v['valor_atraso']:.2f}, Plano: {v['plano']}")
            break
