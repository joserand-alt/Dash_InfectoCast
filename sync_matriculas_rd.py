# -*- coding: utf-8 -*-
"""
Sincronizador Inteligente de Matrículas e Pagamentos com o RD Station
- Sincroniza alunos e matrículas da Cativa Digital E da Academy / Vindi / Asaas
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
                    "origem": "Cativa"
                })
            else:
                for c in courses:
                    c_name = c.get("courseName") or "Pós-Graduação InfectoCast"
                    enrollments.append({
                        "email": em,
                        "nome": nome,
                        "curso": c_name,
                        "gateway": "Cativa Digital",
                        "origem": "Cativa"
                    })
    except Exception as e:
        logger.error(f"Erro ao processar alunos da Cativa: {e}")
        
    return enrollments

def sync_pending_matriculas(dry_run=False):
    """
    Identifica matrículas confirmadas (Academy + Cativa Digital) que ainda não foram marcadas no RD Station e realiza o disparo.
    """
    history = load_tagged_history()
    novos_tagueados = 0
    erros = 0
    total_encontrados = 0

    todas_matriculas = []

    # 1. Carregar Inscrições / Matrículas da Academy
    insc_file = get_inscricoes_file()
    if os.path.exists(insc_file):
        try:
            df_insc = pd.read_excel(insc_file)
            for idx, row in df_insc.iterrows():
                em = str(row.get("E-mail") or "").strip().lower()
                if not em or "@" not in em or em.endswith("@infectocast.com") or "teste" in em:
                    continue
                todas_matriculas.append({
                    "email": em,
                    "nome": str(row.get("Nome") or "").strip(),
                    "curso": str(row.get("Curso") or row.get("Pós") or "Pós-Graduação InfectoCast").strip(),
                    "valor": row.get("Valor") or row.get("Valor Pago") or None,
                    "gateway": "Academy",
                    "origem": "Academy",
                    "id": str(row.get("ID") or f"MAT-AC-{idx+1}").strip()
                })
        except Exception as e:
            logger.error(f"Erro ao ler planilha de inscrições Academy: {e}")

    # 2. Carregar Matrículas da Cativa Digital
    cativa_matriculas = get_cativa_enrollments()
    todas_matriculas.extend(cativa_matriculas)

    total_encontrados = len(todas_matriculas)
    logger.info(f"Analisando total consolidado de {total_encontrados} matrículas (Academy + Cativa Digital)...")

    for idx, m in enumerate(todas_matriculas, 1):
        email = m["email"]
        nome = m.get("nome", "")
        curso = m.get("curso", "Pós-Graduação InfectoCast")
        valor = m.get("valor")
        gateway = m.get("gateway", "Cativa Digital")
        id_matricula = m.get("id", f"MAT-{idx}")
        
        unique_key = f"{email}|{rd_service.slugify_tag(curso)}"

        if unique_key in history and history[unique_key].get("status") == "success":
            continue

        logger.info(f"📢 [{m['origem']}] Nova matrícula a taguear no RD: {nome} ({email}) - Curso: {curso}")

        if dry_run:
            logger.info(f"   [DRY-RUN] Dispararia tag para {email}")
            novos_tagueados += 1
            continue

        try:
            res = rd_service.register_matricula_event(
                email=email,
                nome=nome,
                curso=curso,
                valor=valor,
                gateway=gateway,
                id_matricula=id_matricula,
                tags_adicionais=["cativa-digital"] if m["origem"] == "Cativa" else ["academy-pago"]
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
    parser = argparse.ArgumentParser(description="Sincronizador de Matrículas RD Station (Academy + Cativa)")
    parser.add_argument("--dry-run", action="store_true", help="Apenas simula sem enviar para o RD")
    args = parser.parse_args()
    
    sync_pending_matriculas(dry_run=args.dry_run)
