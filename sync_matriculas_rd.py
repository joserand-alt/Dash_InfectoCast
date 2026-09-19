# -*- coding: utf-8 -*-
"""
Sincronizador Inteligente de Matrículas e Pagamentos com o RD Station
- Sincroniza alunos e matrículas da Cativa Digital, Academy, Vindi e Asaas
- Classifica automaticamente em Pós-Graduação vs Curso Livre e tags do curso
- Garante idempotência salvando histórico em rd_tagged_matriculas.json
"""

import os
import json
import time
import logging
from datetime import datetime
import pandas as pd

import rd_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyncMatriculasRD")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TAGGED_HISTORY_FILE = os.path.join(BASE_DIR, "rd_tagged_matriculas.json")
CATIVA_CACHE_FILE = os.path.join(BASE_DIR, "cativa_cache.json")
ASAAS_CACHE_FILE = os.path.join(BASE_DIR, "asaas_cache.json")
VINDI_CACHE_FILE = os.path.join(BASE_DIR, "vindi_cache.json")

def get_inscricoes_file():
    p1 = os.path.join(BASE_DIR, "BD", "Inscrições.xlsx")
    if os.path.exists(p1):
        return p1
    p2 = r"C:\Users\DELL\Desktop\Acompanhamento de acessos\BD\Inscrições.xlsx"
    if os.path.exists(p2):
        return p2
    return p1

def load_tagged_history():
    """Carrega o histórico de alunos/matrículas que já receberam a tag no RD"""
    if os.path.exists(TAGGED_HISTORY_FILE):
        try:
            with open(TAGGED_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao ler {TAGGED_HISTORY_FILE}: {e}. Criando novo.")
    return {}

def save_tagged_history(history):
    """Salva o histórico atualizado"""
    with open(TAGGED_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def get_cativa_enrollments():
    """Extrai lista de alunos e cursos da Cativa Digital"""
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
            if not em or "@" not in em or em.endswith("@infectocast.com") or "teste" in em:
                continue
                
            nome = str(s.get("fullName", "")).strip()
            meta = users_meta.get(em, {})
            if not nome:
                fn = meta.get("first_name", "")
                ln = meta.get("last_name", "")
                nome = f"{fn} {ln}".strip()
                
            courses = s.get("courses", [])
            if not courses:
                enrollments.append({
                    "email": em,
                    "nome": nome,
                    "curso": "Pós-Graduação InfectoCast",
                    "gateway": "Cativa Digital",
                    "origem": "Cativa",
                    "id": f"CAT-{em}"
                })
            else:
                for c in courses:
                    c_name = c.get("courseName") or "Pós-Graduação InfectoCast"
                    enrollments.append({
                        "email": em,
                        "nome": nome,
                        "curso": c_name,
                        "gateway": "Cativa Digital",
                        "origem": "Cativa",
                        "id": f"CAT-{em}-{rd_service.slugify_tag(c_name)}"
                    })
    except Exception as e:
        logger.error(f"Erro ao processar alunos da Cativa: {e}")
        
    return enrollments

def get_asaas_enrollments():
    """Extrai alunos matriculados com pagamento confirmado no Asaas"""
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
            if (st.get("total_pago") or 0) <= 0:
                continue
                
            em = str(st.get("customer_email") or "").lower().strip()
            if not em or "@" not in em or em.endswith("@infectocast.com") or "teste" in em:
                continue
                
            nome = str(st.get("customer_name") or "Aluno Academy").strip()
            faturas = st.get("faturas", [])
            
            # Identificação inteligente de curso
            curso = "Curso Academy"
            tot_pago = float(st.get("total_pago") or 0)
            
            desc_text = " ".join(str(ft.get("description", ft.get("plano", ""))) for ft in faturas).lower()
            if "sos" in desc_text or "antibiotico" in desc_text or abs(tot_pago - 487.0) < 5:
                curso = "S.O.S ANTIBIÓTICO"
            elif "ccih" in desc_text or "hospitalar" in desc_text:
                curso = "PÓS-GRADUAÇÃO EM PREVENÇÃO E CONTROLE DE INFECÇÃO HOSPITALAR (CCIH)"
            elif "pediatria" in desc_text or "infectoped" in desc_text:
                curso = "PÓS-GRADUAÇÃO EM INFECTOPEDIATRIA"
            elif "ortoped" in desc_text:
                curso = "PÓS-GRADUAÇÃO EM INFECÇÕES ORTOPÉDICAS E DE PARTES MOLES"
            elif "imuno" in desc_text:
                curso = "PÓS-GRADUAÇÃO EM INFECÇÕES EM IMUNODEPRIMIDOS"
            else:
                curso = "S.O.S ANTIBIÓTICO" if abs(tot_pago - 487.0) < 5 else "Pós-Graduação InfectoCast"
                
            enrollments.append({
                "email": em,
                "nome": nome,
                "curso": curso,
                "valor": tot_pago,
                "gateway": "Asaas",
                "origem": "Asaas",
                "id": str(st.get("aluno_id_extref") or st.get("customer_id") or f"ASAAS-{em}")
            })
    except Exception as e:
        logger.error(f"Erro ao processar alunos do Asaas: {e}")
        
    return enrollments

def get_vindi_enrollments():
    """Extrai alunos matriculados com assinatura/fatura paga na Vindi"""
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
            if (st.get("total_pago") or 0) <= 0 and st.get("status_assinatura") != "active":
                continue
                
            em_clean = str(em).lower().strip()
            if not em_clean or "@" not in em_clean or em_clean.endswith("@infectocast.com") or "teste" in em_clean:
                continue
                
            nome = str(st.get("customer_name") or "Aluno Vindi").strip()
            subs = st.get("subscriptions", [])
            for sub in subs:
                p_name = sub.get("plan_name") or "Pós-Graduação InfectoCast"
                enrollments.append({
                    "email": em_clean,
                    "nome": nome,
                    "curso": p_name,
                    "valor": sub.get("valor"),
                    "gateway": "Vindi",
                    "origem": "Vindi",
                    "id": str(sub.get("id") or f"VINDI-{em_clean}")
                })
    except Exception as e:
        logger.error(f"Erro ao processar alunos da Vindi: {e}")
        
    return enrollments

def sync_pending_matriculas(dry_run=False):
    """
    Identifica matrículas confirmadas (Academy + Cativa Digital + Asaas + Vindi) que ainda não foram marcadas no RD Station e realiza o disparo.
    """
    history = load_tagged_history()
    novos_tagueados = 0
    erros = 0

    todas_matriculas = []

    # 1. Carregar Inscrições / Matrículas da InfectoCast Academy API
    academy_students_path = os.path.join(BASE_DIR, "academy_students_cache.json")
    academy_logs_path = os.path.join(BASE_DIR, "academy_logs_cache.json")
    
    academy_course_map = {}
    if os.path.exists(academy_logs_path):
        try:
            with open(academy_logs_path, "r", encoding="utf-8") as f_al:
                logs_data = json.load(f_al)
                for l in logs_data:
                    em = str(l.get("E-mail", "")).lower().strip()
                    acao = str(l.get("Ação / Local", "")).upper()
                    item = str(l.get("ID Item") or l.get("Desc. Item") or "").strip()
                    if "TURMA" in acao and item and item != "nan":
                        academy_course_map[em] = item
        except Exception:
            pass

    if os.path.exists(academy_students_path):
        try:
            with open(academy_students_path, "r", encoding="utf-8") as f_ast:
                ast_data = json.load(f_ast)
                for aid, s in ast_data.items():
                    em = str(s.get("email", "")).lower().strip()
                    if not em or "@" not in em or em.endswith("@infectocast.com") or "teste" in em:
                        continue
                    curso_resolved = academy_course_map.get(em, "Pós-Graduação InfectoCast")
                    todas_matriculas.append({
                        "email": em,
                        "nome": str(s.get("nome") or "Aluno Academy").strip(),
                        "curso": curso_resolved,
                        "valor": None,
                        "gateway": "Academy",
                        "origem": "Academy",
                        "id": f"MAT-AC-{aid}"
                    })
        except Exception as e:
            logger.error(f"Erro ao carregar alunos da Academy API: {e}")

    # 2. Carregar Matrículas da Cativa Digital
    todas_matriculas.extend(get_cativa_enrollments())

    # 3. Carregar Matrículas do Asaas
    todas_matriculas.extend(get_asaas_enrollments())

    # 4. Carregar Matrículas da Vindi
    todas_matriculas.extend(get_vindi_enrollments())

    # Deduplicação por chave única email + curso slug
    unique_matriculas = {}
    for m in todas_matriculas:
        key = f"{m['email']}|{rd_service.slugify_tag(m.get('curso', ''))}"
        if key not in unique_matriculas:
            unique_matriculas[key] = m

    total_encontrados = len(unique_matriculas)
    logger.info(f"Analisando total consolidado de {total_encontrados} matrículas únicas (Academy + Cativa + Asaas + Vindi)...")

    for unique_key, m in unique_matriculas.items():
        email = m["email"]
        nome = m.get("nome", "")
        curso = m.get("curso", "Pós-Graduação InfectoCast")
        valor = m.get("valor")
        gateway = m.get("gateway", "Academy")
        id_matricula = m.get("id", f"MAT-{email}")

        if unique_key in history and history[unique_key].get("status") == "success":
            continue

        logger.info(f"📢 [{m['origem']}] Nova matrícula a taguear no RD: {nome} ({email}) - Curso: {curso}")

        if dry_run:
            logger.info(f"   [DRY-RUN] Dispararia tag para {email}")
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
                "status": "success",
                "data_tagueamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tags_aplicadas": res.get("tags_applied", [])
            }
            novos_tagueados += 1
            save_tagged_history(history)
            time.sleep(0.3)
        except Exception as e:
            erros += 1
            logger.error(f"❌ Falha ao processar {email}: {e}")

    logger.info(f"🏁 Sincronização concluída! Novos tagueados: {novos_tagueados}, Erros: {erros}, Total histórico: {len(history)}")
    return {
        "status": "completed",
        "novos_tagueados": novos_tagueados,
        "erros": erros,
        "total_historico": len(history)
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sincronizador Unificado de Matrículas RD Station (Academy + Cativa + Asaas + Vindi)")
    parser.add_argument("--dry-run", action="store_true", help="Apenas simula sem enviar para o RD")
    args = parser.parse_args()
    
    sync_pending_matriculas(dry_run=args.dry_run)
