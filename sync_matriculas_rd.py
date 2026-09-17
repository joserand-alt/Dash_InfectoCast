# -*- coding: utf-8 -*-
"""
Sincronizador Inteligente de Matrículas e Pagamentos com o RD Station
- Lê as matrículas e pagamentos confirmados do Academy / Asaas / Vindi / Cativa
- Garante idempotência salvando histórico em rd_tagged_matriculas.json
- Aplica tags automáticas e registra evento de conversão no RD Station
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

BASE_DIR = r"C:\Users\DELL\Desktop\Dash_InfectoCast"
TAGGED_HISTORY_FILE = os.path.join(BASE_DIR, "rd_tagged_matriculas.json")
EXCEL_INSCRICOES = r"C:\Users\DELL\Desktop\Acompanhamento de acessos\BD\Inscrições.xlsx"

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

def sync_pending_matriculas(dry_run=False):
    """
    Identifica matrículas confirmadas que ainda não foram marcadas no RD Station e realiza o disparo.
    """
    history = load_tagged_history()
    novos_tagueados = 0
    erros = 0

    # 1. Carregar Inscrições / Matrículas da base
    if not os.path.exists(EXCEL_INSCRICOES):
        logger.error(f"Arquivo de inscrições não encontrado em {EXCEL_INSCRICOES}")
        return {"status": "error", "message": "Arquivo de inscrições não encontrado"}

    try:
        df_insc = pd.read_excel(EXCEL_INSCRICOES)
    except Exception as e:
        logger.error(f"Erro ao ler planilha de inscrições: {e}")
        return {"status": "error", "error": str(e)}

    logger.info(f"Analisando {len(df_insc)} registros de matrículas...")

    for idx, row in df_insc.iterrows():
        email = str(row.get("E-mail") or "").strip().lower()
        if not email or "@" not in email:
            continue

        nome = str(row.get("Nome") or "").strip()
        curso = str(row.get("Curso") or row.get("Pós") or "Pós-Graduação InfectoCast").strip()
        valor = row.get("Valor") or row.get("Valor Pago") or None
        id_matricula = str(row.get("ID") or row.get("Matrícula") or f"MAT-{idx+1}").strip()
        
        # Chave única de idempotência: email + curso
        unique_key = f"{email}|{rd_service.slugify_tag(curso)}"

        if unique_key in history:
            # Já processado anteriormente
            continue

        logger.info(f"📢 Nova matrícula identificada: {nome} ({email}) - Curso: {curso}")

        if dry_run:
            logger.info(f"   [DRY-RUN] Dispararia tag e conversão para {email} no curso {curso}")
            novos_tagueados += 1
            continue

        # Executa o disparo no RD Station
        res = rd_service.register_matricula_event(
            email=email,
            nome=nome,
            curso=curso,
            valor=valor,
            gateway="Academy",
            id_matricula=id_matricula
        )

        if res.get("status") in ["success", "partial_fallback"]:
            history[unique_key] = {
                "email": email,
                "nome": nome,
                "curso": curso,
                "data_tagueamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "tags_aplicadas": res.get("tags_applied", []),
                "resposta_rd": res
            }
            novos_tagueados += 1
            save_tagged_history(history)
            time.sleep(0.4) # Intervalo preventivo de rate-limit
        else:
            erros += 1
            logger.error(f"❌ Falha ao processar {email}: {res}")

    logger.info(f"🏁 Sincronização concluída! Novos tagueados: {novos_tagueados}, Erros: {erros}, Total histórico: {len(history)}")
    return {
        "status": "completed",
        "novos_tagueados": novos_tagueados,
        "erros": erros,
        "total_historico": len(history)
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sincronizador de Matrículas RD Station")
    parser.add_argument("--dry-run", action="store_true", help="Apenas simula sem enviar para o RD")
    args = parser.parse_args()
    
    sync_pending_matriculas(dry_run=args.dry_run)
