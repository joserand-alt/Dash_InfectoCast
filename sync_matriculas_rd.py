# -*- coding: utf-8 -*-
"""
Sincronizador Inteligente de Matrículas e Pagamentos com o RD Station
- REGRA DE OURO: O disparo de conversão e aplicação de tags de aluno no RD Station
  SÓ OCORRE NA CONFIRMAÇÃO DO PRIMEIRO PAGAMENTO DO CURSO NO GATEWAY (Vindi / Asaas / Cativa).
- Cadastros simples de plataforma sem pagamento aprovado NÃO disparam evento de conversão.
- Classifica automaticamente em Pós-Graduação vs Curso Livre e tags oficiais do curso.
- Garante idempotência salvando histórico em rd_tagged_matriculas.json (não redispara parcelas recorrentes).
"""

import os
import json
import time
import logging
from datetime import datetime
import unicodedata
import re

import rd_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyncMatriculasRD")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TAGGED_HISTORY_FILE = os.path.join(BASE_DIR, "rd_tagged_matriculas.json")
TAGGED_PENDENTES_FILE = os.path.join(BASE_DIR, "rd_tagged_pendentes.json")
CATIVA_CACHE_FILE = os.path.join(BASE_DIR, "cativa_cache.json")
ASAAS_CACHE_FILE = os.path.join(BASE_DIR, "asaas_cache.json")
VINDI_CACHE_FILE = os.path.join(BASE_DIR, "vindi_cache.json")
DASHBOARD_HTML_FILE = os.path.join(BASE_DIR, "dashboard_gerado.html")

def parse_date_universal(d_str):
    if not d_str:
        return None
    s = str(d_str).strip()
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"]:
        try:
            return datetime.strptime(s.split('+')[0].split('.')[0], fmt if '.' not in fmt else "%Y-%m-%d")
        except Exception:
            pass
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
    if m:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None

def normalize_curso_name(cName):
    if not cName:
        return 'PÓS-GRADUAÇÃO INFECTOCAST'
    s = unicodedata.normalize('NFKD', str(cName)).encode('ascii', 'ignore').decode('utf-8').upper().strip()
    if 'INFECTOPEDIATRIA' in s or 'PEDIATRIA' in s:
        return 'POS-GRADUACAO EM INFECTOPEDIATRIA'
    if 'IMUNODEPRIMIDO' in s:
        return 'POS-GRADUACAO EM INFECTOLOGIA DO PACIENTE IMUNODEPRIMIDO'
    if 'ORTOPEDIC' in s or 'PARTES MOLES' in s:
        return 'POS-GRADUACAO EM INFECCOES ORTOPEDICAS E DE PARTES MOLES'
    if 'CCIH' in s or 'HOSPITALAR' in s:
        return 'POS-GRADUACAO EM PREVENCAO E CONTROLE DE INFECCAO HOSPITALAR (CCIH)'
    if 'TERAPIA INTENSIVA' in s or 'UTI' in s:
        return 'POS-GRADUACAO EM INFECTOLOGIA EM TERAPIA INTENSIVA'
    if 'ANTIBIOTICO' in s or 'SOS' in s:
        return 'S.O.S ANTIBIOTICO'
    if 'FUNGO' in s or 'ANTIFUNGICO' in s:
        return 'DO FUNGO AO ANTIFUNGICO'
    if 'MULTI-R' in s or 'JORNADA' in s:
        return 'JORNADA MULTI-R'
    if 'GESTACAO' in s or 'GESTANTE' in s:
        return 'INFECCOES NA GESTACAO'
    if 'HIV' in s or 'HEPATITE' in s:
        return 'HIV E HEPATITES VIRAIS'
    if 'INFECTOCAST' in s:
        return 'POS-GRADUACAO INFECTOCAST'
    return s

def load_tagged_history():
    """Carrega o histórico de alunos/matrículas confirmadas que já receberam a tag no RD"""
    if os.path.exists(TAGGED_HISTORY_FILE):
        try:
            with open(TAGGED_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao ler {TAGGED_HISTORY_FILE}: {e}. Criando novo.")
    return {}

def save_tagged_history(history):
    """Salva o histórico atualizado de matrículas confirmadas"""
    with open(TAGGED_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def load_tagged_pendentes_history():
    """Carrega o histórico de leads com matrícula pendente já disparados para o RD"""
    if os.path.exists(TAGGED_PENDENTES_FILE):
        try:
            with open(TAGGED_PENDENTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao ler {TAGGED_PENDENTES_FILE}: {e}. Criando novo.")
    return {}

def save_tagged_pendentes_history(history):
    """Salva o histórico atualizado de pendentes"""
    with open(TAGGED_PENDENTES_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def is_internal_or_test(email, nome=""):
    em = str(email or "").lower().strip()
    nm = str(nome or "").lower().strip()
    if not em or "@" not in em:
        return True
    if any(x in em for x in ['@infectocast', '@integralmedica', '@nutrify', '@cativa', '@estrategia1', '@adtivo', 'teste']):
        return True
    if 'teste' in nm or em in ['gcotta29@gmail.com', 'j.o.s.e.r.a.n.d@gmail.com', 'email@email.com', 'wgww@gmail.com']:
        return True
    return False

def get_cativa_confirmed_enrollments():
    """Extrai lista de alunos com matrículas/cursos confirmados na Cativa Digital"""
    enrollments = []
    if not os.path.exists(CATIVA_CACHE_FILE):
        return enrollments
        
    try:
        with open(CATIVA_CACHE_FILE, "r", encoding="utf-8") as f:
            cativa = json.load(f)
            
        students = cativa.get("students", [])
        users_meta = cativa.get("users_metadata", {})
        
        for s in students:
            em = str(s.get("email", "")).lower().strip()
            if is_internal_or_test(em, s.get("fullName")):
                continue
                
            nome = str(s.get("fullName", "")).strip()
            meta = users_meta.get(em, {})
            if not nome:
                fn = meta.get("first_name", "")
                ln = meta.get("last_name", "")
                nome = f"{fn} {ln}".strip() or "Aluno Cativa"
                
            courses = s.get("courses", [])
            for c in courses:
                c_name = c.get("courseName") or "Pós-Graduação InfectoCast"
                c_norm = normalize_curso_name(c_name)
                enrollments.append({
                    "email": em,
                    "nome": nome,
                    "curso": c_norm,
                    "valor": None,
                    "gateway": "Cativa Digital",
                    "origem": "Cativa",
                    "data_matricula": c.get("enrollmentDate") or datetime.now().strftime("%Y-%m-%d"),
                    "id": f"CAT-{em}-{rd_service.slugify_tag(c_norm)}"
                })
    except Exception as e:
        logger.error(f"Erro ao processar alunos da Cativa: {e}")
        
    return enrollments

def get_asaas_confirmed_enrollments():
    """
    Extrai SOMENTE alunos com PAGAMENTO CONFIRMADO/PAGO no Asaas.
    A data da matrícula é a data do PRIMEIRO pagamento aprovado.
    """
    enrollments = []
    if not os.path.exists(ASAAS_CACHE_FILE):
        return enrollments
        
    try:
        with open(ASAAS_CACHE_FILE, "r", encoding="utf-8") as f:
            as_data = json.load(f)
            
        data_map = as_data.get("data", {})
        for k, st in data_map.items():
            if not isinstance(st, dict):
                continue
            
            # REGRA ESTRITA: Deve possuir total pago > 0 e faturas pagas confirmadas
            tot_pago = float(st.get("total_pago") or 0)
            faturas = st.get("faturas", [])
            paid_fats = [f for f in faturas if str(f.get("status", "")).upper() in ["RECEIVED", "CONFIRMED", "PAGO", "PAID"]]
            
            if tot_pago <= 0 and len(paid_fats) == 0:
                continue
                
            em = str(st.get("customer_email") or "").lower().strip()
            nome = str(st.get("customer_name") or "Aluno Asaas").strip()
            if is_internal_or_test(em, nome):
                continue

            # Identificar curso por descrição ou tabela inteligente de preços
            desc_text = ' '.join(str(f.get('description') or f.get('descricao') or '') for f in faturas)
            desc_norm = normalize_curso_name(desc_text)
            
            # Preços conhecidos do catálogo
            f_vals = [float(ft.get('valor') or 0) for ft in faturas]
            sos_prices = [819.0, 487.0, 2187.0, 1968.30, 519.0, 204.75, 68.25, 182.25, 218.70, 437.40, 196.83]
            
            if 'ANTIBIOTICO' in desc_norm or 'SOS' in desc_norm or any(any(abs(v - sp) < 2 for sp in sos_prices) for v in ([tot_pago] + f_vals)):
                curso_resolved = 'S.O.S ANTIBIOTICO'
            elif desc_norm and desc_norm != 'PÓS-GRADUAÇÃO INFECTOCAST':
                curso_resolved = desc_norm
            else:
                curso_resolved = 'S.O.S ANTIBIOTICO' if tot_pago < 3000 else 'POS-GRADUACAO INFECTOCAST'
                
            # Identificar a data e valor do primeiro pagamento aprovado
            first_date = None
            first_val = tot_pago
            if paid_fats:
                paid_fats.sort(key=lambda x: str(x.get("data_pagamento") or x.get("vencimento") or ""))
                first_date = paid_fats[0].get("data_pagamento") or paid_fats[0].get("vencimento")
                first_val = float(paid_fats[0].get("valor") or tot_pago)
                
            enrollments.append({
                "email": em,
                "nome": nome,
                "curso": curso_resolved,
                "valor": first_val,
                "gateway": "Asaas",
                "origem": "Asaas",
                "data_matricula": first_date or datetime.now().strftime("%Y-%m-%d"),
                "id": str(st.get("aluno_id_extref") or st.get("customer_id") or f"ASAAS-{em}")
            })
    except Exception as e:
        logger.error(f"Erro ao processar alunos do Asaas: {e}")
        
    return enrollments

def get_vindi_confirmed_enrollments():
    """
    Extrai SOMENTE alunos com FATURA PAGA CONFIRMADA na Vindi.
    A data da matrícula é a data do PRIMEIRO pagamento aprovado.
    """
    enrollments = []
    if not os.path.exists(VINDI_CACHE_FILE):
        return enrollments
        
    try:
        with open(VINDI_CACHE_FILE, "r", encoding="utf-8") as f:
            v_data = json.load(f)
            
        st_map = v_data.get("data", {})
        for em, st in st_map.items():
            if not isinstance(st, dict):
                continue
            
            em_clean = str(em).lower().strip()
            nome = str(st.get("customer_name") or "Aluno Vindi").strip()
            if is_internal_or_test(em_clean, nome):
                continue
                
            faturas = st.get("faturas", [])
            paid_fats = [f for f in faturas if str(f.get("status", "")).lower() in ["pago", "paid"]]
            
            # REGRA ESTRITA: Apenas se tiver fatura paga confirmada
            if len(paid_fats) == 0 and float(st.get("total_pago") or 0) <= 0:
                continue
                
            subs = st.get("subscriptions", [])
            if subs:
                for sub in subs:
                    p_name = sub.get("plan_name") or "Pós-Graduação InfectoCast"
                    c_norm = normalize_curso_name(p_name)
                    enrollments.append({
                        "email": em_clean,
                        "nome": nome,
                        "curso": c_norm,
                        "valor": sub.get("valor"),
                        "gateway": "Vindi",
                        "origem": "Vindi",
                        "data_matricula": sub.get("start_at") or (paid_fats[0].get("data_pagamento") if paid_fats else datetime.now().strftime("%Y-%m-%d")),
                        "id": str(sub.get("id") or f"VINDI-{em_clean}")
                    })
            else:
                p_name = st.get("plano") or "Pós-Graduação InfectoCast"
                c_norm = normalize_curso_name(p_name)
                first_date = paid_fats[0].get("data_pagamento") if paid_fats else datetime.now().strftime("%Y-%m-%d")
                enrollments.append({
                    "email": em_clean,
                    "nome": nome,
                    "curso": c_norm,
                    "valor": float(paid_fats[0].get("valor") or 0) if paid_fats else None,
                    "gateway": "Vindi",
                    "origem": "Vindi",
                    "data_matricula": first_date,
                    "id": f"VINDI-{em_clean}"
                })
    except Exception as e:
        logger.error(f"Erro ao processar alunos da Vindi: {e}")
        
    return enrollments

def sync_pending_matriculas(dry_run=False):
    """
    Identifica matrículas confirmadas por pagamento (Cativa Digital + Asaas + Vindi)
    que ainda não foram disparadas para o RD Station e realiza o disparo oficial.
    """
    history = load_tagged_history()
    novos_tagueados = 0
    erros = 0

    todas_matriculas = []

    # 1. Carregar Matrículas Confirmadas da Cativa Digital
    todas_matriculas.extend(get_cativa_confirmed_enrollments())

    # 2. Carregar Matrículas Confirmadas do Asaas (1º Pagamento Aprovado)
    todas_matriculas.extend(get_asaas_confirmed_enrollments())

    # 3. Carregar Matrículas Confirmadas da Vindi (1º Pagamento Aprovado)
    todas_matriculas.extend(get_vindi_confirmed_enrollments())

    # Deduplicação estrita por chave única email + curso slug
    unique_matriculas = {}
    for m in todas_matriculas:
        key = f"{m['email']}|{rd_service.slugify_tag(m.get('curso', ''))}"
        if key not in unique_matriculas:
            unique_matriculas[key] = m

    total_encontrados = len(unique_matriculas)
    logger.info(f"Analisando total de {total_encontrados} matrículas pagas confirmadas (Cativa + Asaas + Vindi)...")

    for unique_key, m in unique_matriculas.items():
        email = m["email"]
        nome = m.get("nome", "")
        curso = m.get("curso", "Pós-Graduação InfectoCast")
        valor = m.get("valor")
        gateway = m.get("gateway", "Gateway")
        id_matricula = m.get("id", f"MAT-{email}")
        data_mat = m.get("data_matricula")

        # Se já foi disparado com sucesso para este curso, NÃO redispara (idempotência)
        if unique_key in history and history[unique_key].get("status") == "success":
            continue

        logger.info(f"📢 [{m['origem']}] Disparando conversão de matrícula confirmada no RD: {nome} ({email}) - Curso: {curso} - Gateway: {gateway}")

        if dry_run:
            logger.info(f"   [DRY-RUN] Simulação: dispararia conversão e tags para {email} (Curso: {curso})")
            novos_tagueados += 1
            continue

        try:
            extra_tags = ["academy-pago"]
            if m["origem"] == "Cativa":
                extra_tags.append("cativa-digital")
            elif m["origem"] == "Asaas":
                extra_tags.append("asaas-pago")
            elif m["origem"] == "Vindi":
                extra_tags.append("vindi-pago")

            res = rd_service.register_matricula_event(
                email=email,
                nome=nome,
                curso=curso,
                valor=valor,
                gateway=gateway,
                id_matricula=id_matricula,
                tags_adicionais=extra_tags
            )
            history[unique_key] = {
                "email": email,
                "nome": nome,
                "curso": curso,
                "origem": m["origem"],
                "data_matricula": data_mat,
                "status": "success",
                "data_tagueamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tags_aplicadas": res.get("tags_applied", [])
            }
            novos_tagueados += 1
            save_tagged_history(history)
            time.sleep(0.3)
        except Exception as e:
            erros += 1
            logger.error(f"❌ Falha ao disparar conversão de {email}: {e}")

    logger.info(f"🏁 Sincronização de Matrículas Confirmadas concluída! Novos disparos: {novos_tagueados}, Erros: {erros}, Total histórico: {len(history)}")
    return {
        "status": "completed",
        "novos_tagueados": novos_tagueados,
        "erros": erros,
        "total_historico": len(history)
    }

def get_pending_enrollments(days=30):
    """
    Identifica leads com Matrícula Pendente (inscrição/cadastro sem pagamento confirmado e sem aulas assistidas)
    registrados nos últimos `days` dias.
    """
    students = []
    v_fats = []
    a_fats = []

    # 1. Tentar ler do dataset consolidado em dashboard_gerado.html
    html_sources = [
        DASHBOARD_HTML_FILE,
        os.path.join(r"C:\Users\DELL\Desktop\Dash_InfectoCast", "dashboard_gerado.html")
    ]
    loaded_from_html = False
    for html_path in html_sources:
        if os.path.exists(html_path):
            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    html = f.read()
                pos = html.find('const DATA = {')
                if pos != -1:
                    end_pos = html.find('let CURRENT_DATA', pos)
                    semicolon_pos = html.rfind(';', pos, end_pos + 10)
                    data_str = html[pos + len('const DATA = '):semicolon_pos]
                    data = json.loads(data_str)
                    students = data.get("students", [])
                    v_fats = (data.get("financeiro") or {}).get("faturas_tabela", [])
                    a_fats = (data.get("financeiro_asaas") or {}).get("faturas_tabela", [])
                    loaded_from_html = True
                    break
            except Exception as e:
                logger.warning(f"Aviso ao ler DATA de {html_path}: {e}")

    # Fallback para caches locais de Cativa, Vindi e Asaas caso HTML não esteja acessível
    if not loaded_from_html:
        if os.path.exists(CATIVA_CACHE_FILE):
            try:
                with open(CATIVA_CACHE_FILE, "r", encoding="utf-8") as f:
                    cativa = json.load(f)
                students = cativa.get("students", [])
            except Exception:
                pass
        if os.path.exists(VINDI_CACHE_FILE):
            try:
                with open(VINDI_CACHE_FILE, "r", encoding="utf-8") as f:
                    v_fats = json.load(f).get("data", {})
            except Exception:
                pass

    # Mapeamento de emails com faturas pagas
    paid_emails = set()
    for f in (v_fats + a_fats):
        st = str(f.get("status") or "").lower()
        if st in ["pago", "paid", "received", "confirmed"]:
            em = str(f.get("email") or "").lower().strip()
            if em:
                paid_emails.add(em)

    now = datetime.now()
    from datetime import timedelta
    cutoff_date = now - timedelta(days=days)

    pending_list = []
    seen = set()

    for s in students:
        em = str(s.get("email") or "").lower().strip()
        nm = str(s.get("nome") or s.get("fullName") or "Lead / Inscrição").strip()
        if is_internal_or_test(em, nm):
            continue

        curso = s.get("curso")
        if not curso and s.get("courses"):
            curso = s["courses"][0].get("courseName")
        curso_norm = normalize_curso_name(curso or "PÓS-GRADUAÇÃO INFECTOCAST")

        pair_key = f"{em}|{rd_service.slugify_tag(curso_norm)}"
        if pair_key in seen:
            continue
        seen.add(pair_key)

        # Regra estrita de Matrícula Pendente
        v_st = str((s.get("vindi") or {}).get("status_financeiro") or "").lower()
        a_st = str((s.get("asaas") or {}).get("status_financeiro") or "").lower()
        v_active = v_st in ["active", "ativo", "adimplente", "em_dia"]
        a_active = a_st in ["active", "ativo", "received", "confirmed", "adimplente", "em_dia"]
        v_f = (s.get("vindi") or {}).get("faturas") or []
        a_f = (s.get("asaas") or {}).get("faturas") or []
        v_paid = any(str(x.get("status") or "").lower() in ["pago", "paid"] or x.get("pago") for x in v_f)
        a_paid = any(str(x.get("status") or "").lower() in ["pago", "paid", "received", "confirmed"] or x.get("pago") for x in a_f)

        has_fin = (em in paid_emails) or v_active or a_active or v_paid or a_paid
        has_consumo = float(s.get("aulas_feitas") or 0) > 0

        if not has_fin and not has_consumo and s.get("status") != "Concluído":
            dt_raw = s.get("data_insc") or s.get("data_inscricao") or s.get("data_matricula") or s.get("first") or s.get("createdAt")
            dt_insc = parse_date_universal(dt_raw)
            if dt_insc and dt_insc >= cutoff_date:
                pending_list.append({
                    "email": em,
                    "nome": nm,
                    "curso": curso_norm,
                    "data_inscricao": dt_insc.strftime("%Y-%m-%d %H:%M:%S"),
                    "plataforma": s.get("plataforma") or "Academy",
                    "aulas_feitas": s.get("aulas_feitas") or 0
                })

    return pending_list

def sync_pending_leads(days=30, dry_run=False):
    """
    Identifica leads com matrícula pendente nos últimos `days` dias e dispara a conversão
    'matricula_pendente_infectocast' e as tags de curso correspondentes para o RD Station.
    Garante idempotência salvando histórico em rd_tagged_pendentes.json.
    """
    history = load_tagged_pendentes_history()
    novos_tagueados = 0
    erros = 0

    pending_leads = get_pending_enrollments(days=days)
    total_encontrados = len(pending_leads)
    logger.info(f"Analisando total de {total_encontrados} leads com matrícula pendente nos últimos {days} dias...")

    for p in pending_leads:
        email = p["email"]
        nome = p.get("nome", "")
        curso = p.get("curso", "Pós-Graduação InfectoCast")
        data_insc = p.get("data_inscricao")
        plataforma = p.get("plataforma", "Academy")
        unique_key = f"{email}|{rd_service.slugify_tag(curso)}"

        # Se já foi disparado com sucesso para este curso, NÃO redispara (idempotência)
        if unique_key in history and history[unique_key].get("status") == "success":
            continue

        logger.info(f"⏳ Disparando conversão de Matrícula Pendente no RD: {nome} ({email}) - Curso: {curso} - Inscrição: {data_insc}")

        if dry_run:
            logger.info(f"   [DRY-RUN] Simulação: dispararia conversão 'matricula_pendente_infectocast' e tags para {email} (Curso: {curso})")
            novos_tagueados += 1
            continue

        try:
            res = rd_service.register_matricula_pendente_event(
                email=email,
                nome=nome,
                curso=curso,
                data_inscricao=data_insc,
                plataforma=plataforma
            )
            history[unique_key] = {
                "email": email,
                "nome": nome,
                "curso": curso,
                "plataforma": plataforma,
                "data_inscricao": data_insc,
                "status": "success",
                "data_tagueamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tags_aplicadas": res.get("tags_applied", [])
            }
            novos_tagueados += 1
            save_tagged_pendentes_history(history)
            time.sleep(0.3)
        except Exception as e:
            erros += 1
            logger.error(f"❌ Falha ao disparar conversão pendente de {email}: {e}")

    logger.info(f"🏁 Sincronização de Matrículas Pendentes concluída! Novos disparos: {novos_tagueados}, Erros: {erros}, Total histórico: {len(history)}")
    return {
        "status": "completed",
        "novos_tagueados": novos_tagueados,
        "erros": erros,
        "total_historico": len(history)
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sincronizador Oficial de Matrículas Confirmadas e Pendentes para RD Station")
    parser.add_argument("--dry-run", action="store_true", help="Apenas simula sem enviar para a API do RD")
    parser.add_argument("--days", type=int, default=30, help="Janela de dias para processamento de pendentes (padrão: 30 dias)")
    args = parser.parse_args()
    
    # 1. Sincroniza Matrículas Confirmadas (Pagas)
    sync_pending_matriculas(dry_run=args.dry_run)
    
    # 2. Sincroniza Matrículas Pendentes (Últimos 30 dias)
    sync_pending_leads(days=args.days, dry_run=args.dry_run)
