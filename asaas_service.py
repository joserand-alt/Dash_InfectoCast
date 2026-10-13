from datetime import datetime, date, timedelta
import calendar
import re

import os

import json

import urllib.request

from datetime import datetime, timedelta

from concurrent.futures import ThreadPoolExecutor



def _load_key():

    """Carrega a chave do arquivo local (nao commitado)."""

    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "asaas_config.json")

    if os.path.exists(cfg_path):

        with open(cfg_path, "r", encoding="utf-8-sig") as f:

            return json.load(f).get("api_key", "")

    return ""



API_KEY   = os.environ.get("ASAAS_API_KEY") or _load_key()

BASE_URL  = "https://api.asaas.com/v3/"

CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "asaas_cache.json")

CACHE_TTL_HOURS = 3



STATUS_MAP = {

    "RECEIVED":  ("pago",      "Pago",         "#059669", "rgba(5,150,105,0.1)"),

    "CONFIRMED": ("pago",      "Confirmado",   "#059669", "rgba(5,150,105,0.1)"),

    "PENDING":   ("a_vencer",  "A Vencer",     "#d97706", "rgba(217,119,6,0.1)"),

    "OVERDUE":   ("em_atraso", "Em Atraso",    "#e11d48", "rgba(225,29,72,0.1)"),

    "REFUNDED":  ("quitado",   "Reembolsado",  "#64748b", "rgba(100,116,139,0.1)"),

    "CANCELED":  ("cancelado", "Cancelado",    "#94a3b8", "rgba(0,0,0,0.05)"),

}



def _get_headers():

    return {"access_token": API_KEY, "Content-Type": "application/json", "User-Agent": "InfectoCast-Dashboard/2.0"}



def _api_get(endpoint):

    req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers=_get_headers())

    try:

        with urllib.request.urlopen(req, timeout=20) as resp:

            return True, json.loads(resp.read().decode("utf-8")), None

    except Exception as e:

        return False, None, str(e)



def _fmt_date(iso):

    if not iso: return ""

    try: return datetime.fromisoformat(iso[:10]).strftime("%d/%m/%Y")

    except (ValueError, TypeError): return iso[:10]



def _parse_date(iso):

    if not iso: return None

    try: return datetime.fromisoformat(iso[:10])

    except (ValueError, TypeError): return None



def _fetch_all(endpoint_base):

    items, offset, limit = [], 0, 100

    while True:

        sep = "&" if "?" in endpoint_base else "?"

        ok, data, err = _api_get(f"{endpoint_base}{sep}limit={limit}&offset={offset}")

        if not ok or not data: break

        items.extend(data.get("data", []))

        if not data.get("hasMore"): break

        offset += limit

    return items



def fetch_all_customers():

    print("[ASAAS] Buscando customers...")

    c = _fetch_all("customers")

    print(f"[ASAAS] {len(c)} customers."); return c



def fetch_all_payments():

    print("[ASAAS] Buscando payments...")

    all_p, seen = [], set()

    for status in ["RECEIVED", "CONFIRMED", "PENDING", "OVERDUE", "REFUNDED"]:

        batch = _fetch_all(f"payments?status={status}")

        for p in batch:

            if p["id"] not in seen:

                seen.add(p["id"]); all_p.append(p)

        print(f"[ASAAS]   {status}: {len(batch)}")

    print(f"[ASAAS] Total: {len(all_p)} payments."); return all_p



def _enrich_customers_with_academy_api(customers):

    print("[ASAAS] Enriquecendo customers via API da Academy (/api/alunos/{id})...")

    ACADEMY_TOKEN = "idIsYOe8egEasc4xwhxmwu2uSZyWy3oEhWzE3kEHakhcPJzQpp7kGLmYrk7lcrMQ"

    enriched = 0

    def fetch_acad(c):

        nonlocal enriched

        ext = (c.get("externalReference") or "").strip()

        if not ext: return

        url = f"https://academy.infectocast.com.br/api/alunos/{ext}"

        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {ACADEMY_TOKEN}", "Accept": "application/json", "User-Agent": "Mozilla/5.0"})

        try:

            with urllib.request.urlopen(req, timeout=10) as resp:

                d = json.loads(resp.read().decode("utf-8"))

                if d.get("success") and d.get("data"):

                    st = d["data"]

                    if st.get("email"):

                        c["email"] = st["email"].strip()

                    if st.get("nome"):

                        c["name"] = st["nome"].strip()

                    enriched += 1

        except Exception:

            pass



    with ThreadPoolExecutor(max_workers=10) as ex:

        list(ex.map(fetch_acad, customers))

    print(f"[ASAAS] {enriched} customers enriquecidos com email/nome direto da API Academy!")



def _infer_course_from_desc_or_val(desc, val=0.0):
    d = str(desc or "").upper()
    v = float(val or 0.0)
    if "MULTI-R" in d or "MULTIR" in d or "MULTI R" in d or "219,00" in d or "219.00" in d or any(abs(v - p) < 0.05 for p in [219.0, 73.0, 43.80, 36.50]):
        return "JORNADA MULTI-R"
    if "QUALIDADE" in d or "FERRAMENTAS" in d or "1.197" in d or "1197" in d or any(abs(v - p) < 0.05 for p in [1197.0, 99.75]):
        return "FERRAMENTAS DE QUALIDADE"
    if any(k in d for k in ["24.984", "18.000", "17.488", "17.460", "8.407", "9.342"]) or v > 3000 or any(abs(v - p) < 0.05 for p in [24984.0, 18000.0, 17488.80, 17460.0, 8407.80, 9342.0, 2082.0, 1388.0, 1000.0, 971.60, 970.0, 467.10, 778.50]):
        return "POS-GRADUACAO INFECTOCAST"
    if any(k in d for k in ["2.187", "2187", "819,00", "819.00", "487,00", "487.00", "519,00", "540,00", "719,00", "1.749", "ANTIBIOTICO", "SOS"]) or any(abs(v - p) < 0.05 for p in [2187.0, 1968.30, 819.0, 540.0, 519.0, 487.0, 449.0, 437.40, 364.50, 218.70, 204.75, 196.83, 182.25, 136.50, 121.75, 81.17, 68.25, 45.0, 40.58, 59.91, 59.99, 291.60, 224.50]):
        return "S.O.S ANTIBIOTICO"
    clean_desc = (desc or "").split(" - ")[0].strip()
    if clean_desc and not clean_desc.upper().startswith(("PARCELA", "PAGAMENTO #")):
        return clean_desc
    return "PLATAFORMA GERAL"


def _process(customers, payments):

    now = datetime.now(); current_ym = now.strftime("%Y-%m")

    _enrich_customers_with_academy_api(customers)

    cust_by_id = {c["id"]: c for c in customers}



    # Regra de negócio: uma cobrança/fatura só deve ser considerada se o aluno tiver ao menos um pagamento.

    # Se nunca pagou, seu financeiro deve ser desconsiderado até que ele pague uma.

    paid_customer_ids = set()

    for p in payments:

        if p.get("status") in ("RECEIVED", "CONFIRMED"):

            paid_customer_ids.add(p.get("customer"))

    # Regra inteligente de Deduplicação de Checkouts / Tentativas Abandonadas:

    # Agrupa pagamentos por cliente e número do pedido (#XXXXXX ou installment).

    # Se o cliente possui um pedido com pagamento confirmado (RECEIVED / CONFIRMED),

    # pedidos com ZERO pagamentos (ex: PIX abandonado ou carnê duplicado que não foi pago)

    # são desconsiderados para evitar cobranças fantasmas em atraso ou projeções duplicadas.

    orders_by_cust = {}

    for p in payments:

        cid = p.get("customer", "")

        if cid not in paid_customer_ids:

            continue

        desc = p.get("description") or ""

        m_num = re.search(r'#(\d+)', desc)

        order_key = m_num.group(1) if m_num else (p.get("installment") or p.get("id") or "single")

        orders_by_cust.setdefault(cid, {}).setdefault(order_key, []).append(p)



    valid_payment_ids = set()

    for cid, orders in orders_by_cust.items():

        paid_orders = [ord_k for ord_k, p_list in orders.items() if any(x.get("status") in ("RECEIVED", "CONFIRMED") for x in p_list)]

        for ord_k, p_list in orders.items():

            has_paid = any(x.get("status") in ("RECEIVED", "CONFIRMED") for x in p_list)

            if not has_paid and len(paid_orders) > 0:

                continue

            for x in p_list:

                valid_payment_ids.add(x.get("id"))



    payments_by_cid = {}

    total_recebido = total_em_atraso = recebido_mes = 0.0

    qtd_em_atraso = total_pagas = 0

    historico_map = {}
    projecao_map = {}

    faturas_tabela = []



    for p in payments:

        cid = p.get("customer", "")

        # Regra: se o cliente nunca pagou nenhuma fatura, desconsidera do financeiro

        if cid not in paid_customer_ids:

            continue

        if p.get("id") not in valid_payment_ids:

            continue

        cust = cust_by_id.get(cid, {})

        valor = float(p.get("value") or 0)

        status_raw = p.get("status", "PENDING")

        st_fin, st_label, st_color, st_bg = STATUS_MAP.get(status_raw, ("pendente", status_raw, "#94a3b8", "rgba(0,0,0,0.05)"))

        due_iso = p.get("dueDate") or ""

        paid_iso = p.get("paymentDate") or p.get("clientPaymentDate") or p.get("confirmedDate") or ""

        due_dt = _parse_date(due_iso); paid_dt = _parse_date(paid_iso)

        dias_atraso = max((now.date() - due_dt.date()).days, 0) if status_raw == "OVERDUE" and due_dt else 0
        is_past_or_today = due_dt and (due_dt.date() <= now.date())
        is_received = status_raw in ("RECEIVED", "RECEIVED_IN_CASH")
        
        # Pagamento só é REALIZADO se já foi recebido ou se é CONFIRMED com vencimento até hoje
        if is_received or (status_raw == "CONFIRMED" and is_past_or_today):
            total_recebido += valor
            total_pagas += 1
            ref_dt = (paid_dt if (paid_dt and paid_dt.date() <= now.date()) else None) or due_dt
            if ref_dt:
                ym = ref_dt.strftime("%Y-%m")
                if ym not in historico_map: historico_map[ym] = {"pago": 0.0, "qtd": 0}
                historico_map[ym]["pago"] += valor
                historico_map[ym]["qtd"] += 1
                if ym == current_ym: recebido_mes += valor
            st_fin = "pago"
            st_label = "Pago"
            st_color = "#059669"
            st_bg = "rgba(5,150,105,0.1)"
        elif status_raw == "CONFIRMED" and not is_past_or_today:
            # Parcelas futuras em cartão de crédito -> PROJEÇÃO no mês de vencimento
            st_fin = "futuro"
            st_label = "Futuro (Cartão)"
            st_color = "#3b82f6"
            st_bg = "rgba(59,130,246,0.1)"
            if due_dt:
                ym = due_dt.strftime("%Y-%m")
                projecao_map[ym] = projecao_map.get(ym, 0.0) + valor
        elif status_raw == "OVERDUE":
            total_em_atraso += valor
            qtd_em_atraso += 1
            st_fin = "em_atraso"
            st_label = "Em Atraso"
            st_color = "#e11d48"
            st_bg = "rgba(225,29,72,0.1)"
        elif status_raw == "PENDING":
            if due_dt and due_dt.date() >= now.date():
                ym = due_dt.strftime("%Y-%m")
                projecao_map[ym] = projecao_map.get(ym, 0.0) + valor
            st_fin = "a_vencer"
            st_label = "A Vencer"
            st_color = "#d97706"
            st_bg = "rgba(217,119,6,0.1)" 



        curso_fatura = _infer_course_from_desc_or_val(p.get("description", ""), valor)

        fatura = {

            "id": p.get("id"), "status": st_fin, "status_raw": status_raw,

            "status_label": st_label, "status_color": st_color, "status_bg": st_bg,

            "valor": valor, "valor_fmt": f"R$ {valor:,.2f}".replace(",","X").replace(".",",").replace("X","."),

            "vencimento": _fmt_date(due_iso), "vencimento_iso": due_iso,

            "data_pagamento": _fmt_date(paid_iso), "data_pagamento_iso": paid_iso,

            "forma_pagamento": p.get("billingType", ""), "url": p.get("invoiceUrl", ""),

            "dias_atraso": dias_atraso, "aluno": cust.get("name", ""),

            "email": cust.get("email", ""), "cpfcnpj": cust.get("cpfCnpj", ""),

            "customer_ext_ref": (cust.get("externalReference") or ""),

            "description": p.get("description", ""),

            "curso": curso_fatura,

            "plano": curso_fatura if curso_fatura != "PLATAFORMA GERAL" else (p.get("description") or "").split(" - ")[0],

        }

        payments_by_cid.setdefault(cid, []).append(fatura)

        faturas_tabela.append(fatura)



    faturas_tabela.sort(key=lambda x: x.get("data_pagamento_iso") or x.get("vencimento_iso") or "", reverse=True)



    students_asaas = {}

    for cid, faturas in payments_by_cid.items():

        cust = cust_by_id.get(cid, {})

        ext = (cust.get("externalReference") or "").strip()

        if not ext: continue

        has_overdue = any(f["status"] == "em_atraso" for f in faturas)

        has_canceled = all(f["status_raw"] in ("CANCELED","REFUNDED") for f in faturas)

        dias_at = max((f["dias_atraso"] for f in faturas if f["status"] == "em_atraso"), default=0)

        val_at  = sum(f["valor"] for f in faturas if f["status"] == "em_atraso")

        if has_overdue:

            st_fin="em_atraso"; st_lbl=f"Atraso ({dias_at}d)"; st_clr="#e11d48"; st_bg="rgba(225,29,72,0.1)"

        elif has_canceled:

            st_fin="cancelado"; st_lbl="Cancelado"; st_clr="#94a3b8"; st_bg="rgba(0,0,0,0.05)"

        else:

            st_fin="adimplente"; st_lbl="Em Dia"; st_clr="#059669"; st_bg="rgba(5,150,105,0.1)"

        best_curso = "PLATAFORMA GERAL"
        for ft in faturas:
            c_f = ft.get("curso")
            if c_f and c_f != "PLATAFORMA GERAL":
                best_curso = c_f
                break

        st_obj = {

            "has_asaas": True, "customer_id": cid, "customer_name": cust.get("name",""),

            "customer_email": cust.get("email",""), "cpfcnpj": cust.get("cpfCnpj",""),

            "aluno_id_extref": ext, "status_financeiro": st_fin, "status_assinatura": st_fin,

            "status_label": st_lbl, "status_color": st_clr, "status_bg": st_bg,

            "dias_atraso": dias_at, "valor_atraso": val_at,

            "total_pago": round(sum(f["valor"] for f in faturas if f["status"]=="pago"),2),

            "curso": best_curso,

            "plano": best_curso,

            "faturas": sorted(faturas, key=lambda x: x.get("vencimento_iso") or "", reverse=True),

        }

        students_asaas[ext] = st_obj

        c_mail = (cust.get("email") or "").lower().strip()

        if c_mail:

            students_asaas[c_mail] = st_obj

    # Incluir tambem clientes com cobrancas pendentes/a vencer (Matriculas Pendentes)
    for c in customers:
        cid = c.get("id")
        if not cid or cid in payments_by_cid:
            continue
        c_payments = [p for p in payments if p.get("customer") == cid]
        if not c_payments:
            continue
        cust = cust_by_id.get(cid, c)
        ext = (cust.get("externalReference") or "").strip()
        c_mail = (cust.get("email") or "").lower().strip()
        if not ext and not c_mail:
            continue

        unpaid_faturas = []
        for p in c_payments:
            valor = float(p.get("value") or 0)
            status_raw = p.get("status", "PENDING")
            due_iso = p.get("dueDate") or ""
            created_iso = p.get("dateCreated") or due_iso
            curso_unp = _infer_course_from_desc_or_val(p.get("description", ""), valor)
            unpaid_faturas.append({
                "id": p.get("id"),
                "status": "a_vencer" if status_raw == "PENDING" else "em_atraso",
                "status_raw": status_raw,
                "status_label": "A Vencer" if status_raw == "PENDING" else "Em Atraso",
                "status_color": "#d97706" if status_raw == "PENDING" else "#e11d48",
                "status_bg": "rgba(217,119,6,0.1)",
                "valor": valor,
                "valor_fmt": f"R$ {valor:,.2f}".replace(",","X").replace(".",",").replace("X","."),
                "vencimento": _fmt_date(due_iso),
                "vencimento_iso": due_iso,
                "data_criacao": created_iso,
                "dateCreated": created_iso,
                "data_pagamento": "",
                "data_pagamento_iso": "",
                "forma_pagamento": p.get("billingType", ""),
                "url": p.get("invoiceUrl", ""),
                "dias_atraso": 0,
                "aluno": cust.get("name", ""),
                "email": cust.get("email", ""),
                "cpfcnpj": cust.get("cpfCnpj", ""),
                "customer_ext_ref": ext,
                "description": p.get("description", ""),
                "curso": curso_unp,
                "plano": curso_unp if curso_unp != "PLATAFORMA GERAL" else (p.get("description") or "").split(" - ")[0],
            })

        best_unp_curso = "PLATAFORMA GERAL"
        for ft in unpaid_faturas:
            c_f = ft.get("curso")
            if c_f and c_f != "PLATAFORMA GERAL":
                best_unp_curso = c_f
                break

        st_obj = {
            "has_asaas": True,
            "customer_id": cid,
            "customer_name": cust.get("name", ""),
            "customer_email": cust.get("email", ""),
            "cpfcnpj": cust.get("cpfCnpj", ""),
            "aluno_id_extref": ext,
            "status_financeiro": "PENDING",
            "status_assinatura": "PENDING",
            "status_label": "Matrícula Pendente (Aguardando Pagamento)",
            "status_color": "#d97706",
            "status_bg": "rgba(217,119,6,0.1)",
            "dias_atraso": 0,
            "valor_atraso": 0,
            "total_pago": 0.0,
            "curso": best_unp_curso,
            "plano": best_unp_curso,
            "faturas": sorted(unpaid_faturas, key=lambda x: x.get("dateCreated") or x.get("vencimento_iso") or "", reverse=True),
        }
        if ext:
            students_asaas[ext] = st_obj
        if c_mail:
            students_asaas[c_mail] = st_obj




    meses_pt = {"01":"Jan","02":"Fev","03":"Mar","04":"Abr","05":"Mai","06":"Jun","07":"Jul","08":"Ago","09":"Set","10":"Out","11":"Nov","12":"Dez"}

    historico_mensal = []

    for ym in sorted(historico_map.keys())[-14:]:

        y,m = ym.split("-")

        historico_mensal.append({"mes":ym,"label":f"{meses_pt.get(m,m)}/{y[2:]}","pago":round(historico_map[ym]["pago"],2),"qtd":historico_map[ym]["qtd"]})



    projecao_map = {}

    for p in payments:

        if p.get("customer") not in paid_customer_ids:

            continue

        if p.get("id") not in valid_payment_ids:

            continue

        if p.get("status") == "PENDING":

            due_dt = _parse_date(p.get("dueDate") or "")

            if due_dt and due_dt.date() >= now.date():

                ym = due_dt.strftime("%Y-%m")

                projecao_map[ym] = projecao_map.get(ym,0.0) + float(p.get("value") or 0)



    projecao_mensal = []

    for ym in sorted(projecao_map.keys()):

        y,m = ym.split("-")

        realizado = historico_map.get(ym,{}).get("pago",0.0) if ym==current_ym else 0.0

        projecao_mensal.append({"mes":ym,"label":f"{meses_pt.get(m,m)}/{y[2:]}","previsto":round(projecao_map[ym],2),"realizado":round(realizado,2)})

    mrr = sum(p.get("previsto", 0) for p in projecao_mensal[:2])

    # Calculo preciso Asaas: a vencer no mes vs projecao 30 dias (D+30)
    today = now.date()
    end_of_month = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    d30_date = today + timedelta(days=30)

    a_vencer_mes_atual = 0.0
    proj_30d = 0.0

    for p in payments:
        if p.get("customer") not in paid_customer_ids or p.get("id") not in valid_payment_ids:
            continue
        if p.get("status") == "PENDING":
            due_dt = _parse_date(p.get("dueDate") or "")
            if due_dt:
                val = float(p.get("value") or 0)
                if today <= due_dt.date() <= end_of_month:
                    a_vencer_mes_atual += val
                if today <= due_dt.date() <= d30_date:
                    proj_30d += val

    if a_vencer_mes_atual == 0.0 and len(projecao_mensal) > 0:
        a_vencer_mes_atual = projecao_mensal[0]['previsto']
    future_proj = [p for p in projecao_mensal if p['mes'] > current_ym]
    proj_3m = sum(p['previsto'] for p in future_proj[:3]) if len(future_proj) >= 3 else (mrr * 3)
    proj_6m = sum(p['previsto'] for p in future_proj[:6]) if len(future_proj) >= 6 else (mrr * 6)
    proj_12m = sum(p['previsto'] for p in future_proj[:12]) if len(future_proj) >= 12 else (mrr * 12)

    total_fat = total_recebido + total_em_atraso
    taxa_adimp = round(total_recebido/total_fat*100) if total_fat>0 else 100

    def _fmt(v): return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")

    unique_asaas_subs = list({v['customer_id']: v for v in students_asaas.values() if isinstance(v, dict) and v.get('has_asaas')}.values())

    financeiro_global = {
        "fonte": "Asaas",
        "kpis": {
            "total_recebido": round(total_recebido,2), "total_recebido_fmt": _fmt(total_recebido),
            "total_faturas_pagas": total_pagas,
            "recebido_mes_atual": round(recebido_mes,2), "recebido_mes_fmt": _fmt(recebido_mes),
            "a_vencer_mes_atual": round(a_vencer_mes_atual,2), "a_vencer_mes_atual_fmt": _fmt(a_vencer_mes_atual),
            "previsto_mes_vigente": round(recebido_mes + a_vencer_mes_atual, 2), "previsto_mes_vigente_fmt": _fmt(recebido_mes + a_vencer_mes_atual),
            "total_em_atraso": round(total_em_atraso,2), "total_em_atraso_fmt": _fmt(total_em_atraso),
            "qtd_em_atraso": qtd_em_atraso,
            "mrr_ativo": round(mrr,2), "mrr_ativo_fmt": _fmt(mrr),
            "projecao_30d": round(proj_30d,2), "projecao_30d_fmt": _fmt(proj_30d),
            "projecao_3m": round(proj_3m,2), "projecao_3m_fmt": _fmt(proj_3m),
            "projecao_6m": round(proj_6m,2), "projecao_6m_fmt": _fmt(proj_6m),
            "projecao_12m": round(proj_12m,2), "projecao_12m_fmt": _fmt(proj_12m),
            "taxa_adimplencia": taxa_adimp,
        },
        "historico_mensal": historico_mensal,
        "projecao_mensal": projecao_mensal,
        "projecao_mensal_map": projecao_map,
        "subscriptions": unique_asaas_subs,
        "faturas_tabela": faturas_tabela,
        "faturas_recentes": faturas_tabela[:300],
    }

    return students_asaas, financeiro_global



def get_asaas_data(force_reload=False):
    if not force_reload and os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached_at = datetime.fromisoformat(cached.get("_cached_at", "2000-01-01"))
            if datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS):
                print(f"[ASAAS CACHE] {len(cached.get('data', {}))} alunos carregados.")
                return cached
        except Exception as e:
            print(f"[ASAAS CACHE] Erro ao ler cache: {e}")

    try:
        customers = fetch_all_customers()
        payments  = fetch_all_payments()
        if customers or payments:
            students_asaas, financeiro_global = _process(customers, payments)
            subs_list_asaas = financeiro_global.get("subscriptions", [])
            result = {
                "_cached_at": datetime.now().isoformat(),
                "data": students_asaas,
                "subscriptions": subs_list_asaas,
                "financeiro": financeiro_global
            }
            try:
                with open(CACHE_PATH, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"[ASAAS] Cache salvo ({len(students_asaas)} alunos).")
            except Exception as e_c:
                print(f"[ASAAS] Erro ao salvar cache: {e_c}")
            return result
        else:
            print("[ASAAS API] Nenhum dado retornado da API (sem chave configurada ou conexao). Acionando fallback para cache local...")
    except Exception as e_api:
        print(f"[ASAAS API] Falha na chamada da API Asaas: {e_api}. Usando cache local como fallback de resiliência.")

    # FALLBACK DE RESILIÊNCIA: Se a chamada de API falhar (ex: no GitHub Actions sem chave), usa o CACHE_PATH existente
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                cached = json.load(f)
            fat_cnt = len(cached.get("financeiro", {}).get("faturas_tabela", []))
            print(f"[ASAAS CACHE FALLBACK] {len(cached.get('data', {}))} alunos e {fat_cnt} faturas carregados do cache local.")
            return cached
        except Exception as e_fb:
            print(f"[ASAAS CACHE] Falha no fallback: {e_fb}")

    return {"data": {}, "subscriptions": [], "financeiro": {"faturas_tabela": []}}

if __name__ == "__main__":
    res = get_asaas_data(force_reload=True)
    k = res.get("financeiro", {}).get("kpis", {})
    print(f"\nTotal Recebido : {k.get('total_recebido_fmt')}")

    print(f"Recebido/mes   : {k['recebido_mes_fmt']}")

    print(f"Em Atraso      : {k['total_em_atraso_fmt']} ({k['qtd_em_atraso']} fatura(s))")

    print(f"MRR (Pending)  : {k['mrr_ativo_fmt']}")

    print(f"Proj. 30d      : {k['projecao_30d_fmt']}")

    print(f"Adimplencia    : {k['taxa_adimplencia']}%")

    print(f"Alunos mapeados: {len(res['data'])}")

    print(f"Faturas tabela : {len(res['financeiro']['faturas_tabela'])}")

