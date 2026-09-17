import pandas as pd
import json
import datetime
import math
import os
import re

def prepare_template(template_path):
    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    start_str = "const DATA = {"
    end_str = "};"
    
    start_idx = html.find(start_str)
    if start_idx == -1:
        return html, ""
    
    end_idx = html.find(end_str, start_idx) + 1
    
    pre = html[:start_idx]
    post = html[end_idx:]
    
    return pre, post

import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BD_LOCAL = os.path.join(BASE_DIR, "BD")
BD_FALLBACK = r"C:\Users\DELL\Desktop\Acompanhamento de acessos\BD"

def get_bd_file(filename):
    p1 = os.path.join(BD_LOCAL, filename)
    if os.path.exists(p1):
        return p1
    p2 = os.path.join(BD_FALLBACK, filename)
    if os.path.exists(p2):
        return p2
    return p1

def fetch_logs_from_api(students_df=None):
    print("Buscando logs de uso via API InfectoCast Academy...")
    token = 'idIsYOe8egEasc4xwhxmwu2uSZyWy3oEhWzE3kEHakhcPJzQpp7kGLmYrk7lcrMQ'
    if students_df is None or students_df.empty:
        return pd.DataFrame(columns=['Data log', 'Nome aluno', 'E-mail', 'Ação / Local', 'ID Item', 'Desc. Item'])
    students = students_df[['ID Aluno', 'Aluno', 'E-mail']].dropna(subset=['ID Aluno']).drop_duplicates(subset=['ID Aluno'])

    def fetch_student_logs(row):
        id_aluno = int(row['ID Aluno'])
        email = str(row['E-mail']).strip()
        nome = str(row['Aluno']).strip()
        url = f'https://academy.infectocast.com.br/api/alunos/{id_aluno}/log'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'})
        logs_list = []
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                if res.get('success') and isinstance(res.get('data'), list):
                    for item in res['data']:
                        logs_list.append({
                            'Data log': item.get('data_hora'),
                            'Nome aluno': nome,
                            'E-mail': email,
                            'Ação / Local': item.get('acao_evento'),
                            'ID Item': item.get('item_objeto'),
                            'Desc. Item': item.get('complemento') or item.get('item_objeto')
                        })
        except Exception:
            pass
        return logs_list

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_student_logs, [row for _, row in students.iterrows()]))

    flat_logs = [item for sublist in results for item in sublist]
    df_log = pd.DataFrame(flat_logs)
    if not df_log.empty:
        df_log['Data log'] = pd.to_datetime(df_log['Data log'], errors='coerce')
    else:
        df_log = pd.DataFrame(columns=['Data log', 'Nome aluno', 'E-mail', 'Ação / Local', 'ID Item', 'Desc. Item'])
    
    print(f"Total de {len(df_log)} registros de logs carregados via API de {len(students)} alunos.")
    return df_log


def is_checkout_event(ev_name):
    low = (ev_name or '').lower().strip()
    return any(x in low for x in [
        'pago', 'pendente', 'recorrencia', 'checkout', 'compra',
        'pagamento', 'problema', 'hotmart', 'woocommerce'
    ])

def categorize_rd_event(ev_name):
    low = (ev_name or '').lower().strip()
    if is_checkout_event(low): return 'Checkout / Matrícula'
    if any(x in low for x in ['ebook', 'e-book', 'biofilme', 'candidiase', 'imuno', 'orto', 'ist']): return 'E-book / Material'
    if any(x in low for x in ['jornada', 'live', 'infectoxpert', 'congresso', 'webinar', 'webnar', 'evento', 'aula']): return 'Evento / Live'
    if any(x in low for x in ['fale-conosco', 'duvida', 'contato', 'form_3', 'fluentform', 'atendimento']): return 'Fale Conosco / Contato'
    if any(x in low for x in ['lista-espera', 'lista de espera', 'pre-inscricao', 'pré-inscrição', 'pre_antifungico', 'sos', 'grade_pos']): return 'Lista de Espera / Grade'
    if any(x in low for x in ['ex alunos', 'alunos infectoped', 'ex-alunos']): return 'Comunidade / Base Prévia'
    return 'Outras Ações'

def clean_rd_event_name(ev_name):
    low = ev_name.lower().strip()
    if 'fale-conosco' in low: return 'Fale Conosco (Dúvidas/Suporte)'
    if 'ebook doses' in low: return 'E-book: Doses de Antibióticos'
    if 'ebook pav' in low: return 'E-book: Prevenção de PAV'
    if 'ebook imuno' in low or 'profilaxias' in low: return 'E-book: Imunodeprimidos'
    if 'ebook orto' in low: return 'E-book: Infecções Ortopédicas'
    if 'biofilme' in low: return 'E-book: Biofilme'
    if 'ebook ist' in low or 'e-book ist' in low: return 'E-book: IST'
    if 'candidiase' in low: return 'Material: Candidíase Intra-abdominal'
    if 'jornada multi-r' in low: return 'Jornada Multi-R'
    if 'infectoxpert' in low: return 'Inscrição InfectoXpert'
    if 'pre_antifungico' in low or 'antifungico' in low: return 'Live: Antifúngicos'
    if 'osteoarticulares' in low: return 'Webinar: Infecções Osteoarticulares'
    if 'sos' in low and ('pre' in low or 'pr' in low): return 'Pré-Inscrição SOS Antibiótico'
    if 'congresso' in low: return 'Congresso Brasileiro 2023'
    if 'lista-de-espera' in low or 'lista de espera' in low: return 'Lista de Espera: Pós Ortopedia'
    if 'alunos infectoped' in low: return 'Comunidade Alunos Infectoped'
    if 'ex alunos fabrizio' in low: return 'Base Ex-alunos Dr. Fabrizio'
    if 'fluentform_3' in low or 'formulario atendimento' in low: return 'Formulário de Interesse (Site)'
    if 'pos-graduacao-pediatria-pendente' in low: return 'Checkout Iniciado (Pós Pediatria)'
    if 'pos-graduacao-pediatria-pago' in low: return 'Pagamento Confirmado (Pós Pediatria)'
    if 'recorrencia-18-x-pendente' in low or 'recorrencia-18x-pendente' in low: return 'Checkout Recorrência 18x (Pendente)'
    if 'recorrencia-18-x-pago' in low: return 'Checkout Recorrência 18x (Aprovado)'
    if 'grade_pos_pediatria' in low: return 'Download da Grade Curricular'
    if 'live-12-nov' in low or 'live-06-11' in low or 'lp-live' in low: return 'Live / Masterclass InfectoCast'
    if 'aula' in low and 'imuno' in low: return 'Aula Aberta: Imunodeprimidos'
    return ev_name.replace('---', ' - ').replace('__', ' ').strip()


def optimize_payload_for_dashboard(data):
    """
    Otimiza e enxuga o payload JSON injetado no HTML para reduzir drasticamente
    o tamanho do index.html (de ~23MB para ~10MB) sem perder nenhuma métrica ou funcionalidade.
    """
    # 1. Otimizar Vindi Financeiro
    if "financeiro" in data and isinstance(data["financeiro"], dict):
        data["financeiro"].pop("data", None) # Não utilizado no frontend JS (economiza ~5MB)
        data["financeiro"].pop("faturas_recentes", None)
        if "subscriptions" in data["financeiro"] and isinstance(data["financeiro"]["subscriptions"], list):
            for sub in data["financeiro"]["subscriptions"]:
                sub.pop("faturas", None) # Faturas já estão centralizadas em faturas_tabela
                sub.pop("_score", None)

    # 2. Otimizar Asaas Financeiro
    if "financeiro_asaas" in data and isinstance(data["financeiro_asaas"], dict):
        data["financeiro_asaas"].pop("data", None)
        data["financeiro_asaas"].pop("faturas_recentes", None)
        if "subscriptions" in data["financeiro_asaas"] and isinstance(data["financeiro_asaas"]["subscriptions"], list):
            for sub in data["financeiro_asaas"]["subscriptions"]:
                sub.pop("faturas", None)
                sub.pop("_score", None)

    # 3. Campos necessários para faturas nos modais dos alunos
    FATURA_FIELDS = {'id', 'status', 'status_label', 'valor', 'valor_fmt', 'vencimento', 'data_pagamento', 'forma_pagamento', 'url', 'dias_atraso'}

    # 4. Otimizar lista de alunos e eventos
    if "students" in data and isinstance(data["students"], list):
        for s in data["students"]:
            # Compactar eventos (remover chaves vazias/nulas)
            if "events" in s and isinstance(s["events"], list):
                s["events"] = [{k: v for k, v in e.items() if v not in (None, "", [], {})} for e in s["events"]]

            # Compactar faturas aninhadas de Vindi
            if s.get("vindi") and isinstance(s["vindi"], dict):
                s["vindi"].pop("_score", None)
                if "faturas" in s["vindi"] and isinstance(s["vindi"]["faturas"], list):
                    s["vindi"]["faturas"] = [
                        {k: v for k, v in f.items() if k in FATURA_FIELDS and v not in (None, "", [], {})}
                        for f in s["vindi"]["faturas"]
                    ]

            # Compactar faturas aninhadas de Asaas
            if s.get("asaas") and isinstance(s["asaas"], dict):
                if "faturas" in s["asaas"] and isinstance(s["asaas"]["faturas"], list):
                    s["asaas"]["faturas"] = [
                        {k: v for k, v in f.items() if k in FATURA_FIELDS and v not in (None, "", [], {})}
                        for f in s["asaas"]["faturas"]
                    ]

    return data

def main():
    cursos_path = get_bd_file('CURSOS.xlsx')
    log_uso_path = get_bd_file('Log de uso.xlsx')
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.html')
    
    print("Carregando logs de uso da plataforma Academy...")
    if os.path.exists(log_uso_path):
        df_log = pd.read_excel(log_uso_path)
        df_log['Data log'] = pd.to_datetime(df_log['Data log'], errors='coerce')
        df_log['Plataforma'] = 'Academy'
    else:
        df_log = pd.DataFrame(columns=['Data log', 'Nome aluno', 'E-mail', 'Ação / Local', 'ID Item', 'Desc. Item', 'Plataforma'])
        
    xls_cursos = pd.ExcelFile(cursos_path)
    df_mods = xls_cursos.parse(1)
    df_aulas = xls_cursos.parse(2)
    
    hoje = df_log['Data log'].max().date() + datetime.timedelta(days=1) if not df_log['Data log'].dropna().empty else datetime.date.today()
    inscritos = df_log['E-mail'].dropna().unique()
    
    mensagens_path = get_bd_file('Registro de mensagens.xlsx')
    mensagens_recentes = {}
    if os.path.exists(mensagens_path):
        df_msgs = pd.read_excel(mensagens_path)
        df_msgs['data'] = pd.to_datetime(df_msgs['data'], errors='coerce')
        limite_data = pd.Timestamp(hoje) - pd.Timedelta(days=10)
        recent = df_msgs[df_msgs['data'] >= limite_data]
        
        for _, row in recent.iterrows():
            if pd.isna(row['e-mail']) or pd.isna(row['data']):
                continue
            email_msg = str(row['e-mail']).strip().lower()
            
            dias_atras = max(0, (pd.Timestamp(hoje) - row['data']).days)
            
            if email_msg not in mensagens_recentes or row['data'] > pd.to_datetime(mensagens_recentes[email_msg]['data']):
                mensagens_recentes[email_msg] = {
                    'data': row['data'].strftime('%Y-%m-%d %H:%M:%S'),
                    'dias': dias_atras
                }
    import unicodedata
    def normalize_curso(name):
        if pd.isna(name) or not name or str(name).strip().upper() in ['SEM CURSO', 'NONE', 'NAN', '']:
            return "PLATAFORMA GERAL"
        name = str(name).strip().upper()
        return ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    
    def norm_title(s):
        if not s or pd.isna(s): return ''
        s = str(s).strip().upper()
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    # ============================================
    # BUILD CURRICULUM FROM API LOGS & CANONICAL COURSES
    # ============================================
    def canonicalize_curso(turma, email=None):
        if not turma or pd.isna(turma) or str(turma).strip() in ['nan', '', 'None']:
            if email and 'rd_course_hints' in locals() and email in rd_course_hints:
                return rd_course_hints[email]
            return normalize_curso('PLATAFORMA GERAL')
            
        t_norm = norm_title(turma)
        if any(k in t_norm for k in ['INFECTOPEDI', 'PEDIAT', 'CRIANCA', 'NEONATAL']):
            return normalize_curso('POS-GRADUACAO EM INFECTOPEDIATRIA')
        if any(k in t_norm for k in ['ORTO', 'PELE', 'PARTES MOLES', 'MUSCULO']):
            return normalize_curso('POS-GRADUACAO EM INFECCOES ORTOPEDICAS E DE PARTES MOLES')
        if any(k in t_norm for k in ['CCIH', 'HOSPITALAR', 'PREVENCAO', 'PAV', 'ISC']):
            if 'FARM' in t_norm:
                return normalize_curso('POS-GRADUACAO EM PREVENCAO E CONTROLE DE INFECCAO HOSPITALAR (CCIH) - FARMACIA')
            elif 'ENF' in t_norm:
                return normalize_curso('POS-GRADUACAO EM PREVENCAO E CONTROLE DE INFECCAO HOSPITALAR (CCIH) - ENFERMAGEM')
            else:
                return normalize_curso('POS-GRADUACAO EM PREVENCAO E CONTROLE DE INFECCAO HOSPITALAR (CCIH)')
        if any(k in t_norm for k in ['IMUNO', 'INUNO', 'TRANSPLANT']):
            return normalize_curso('POS-GRADUACAO EM INFECTOLOGIA DO PACIENTE IMUNODEPRIMIDO')
        if any(k in t_norm for k in ['FUNGO', 'ANTIFUNGIC']):
            return normalize_curso('DO FUNGO AO ANTIFUNGICO')
        if any(k in t_norm for k in ['MULTI-R', 'MULTIR', 'MULTI R']):
            return normalize_curso('JORNADA MULTI-R')
        if any(k in t_norm for k in ['S.O.S', 'SOS', 'ANTIBIOTICO', 'ATB', 'MDR', 'ESBL', 'KPC']):
            return normalize_curso('S.O.S ANTIBIOTICO')
        if any(k in t_norm for k in ['FERRAMENTAS', 'QUALIDADE', 'ISHIKAWA', 'PDCA', 'SIPOC']):
            return normalize_curso('FERRAMENTAS DE QUALIDADE')
        if any(k in t_norm for k in ['INFECTOXPERT', 'EXPERT']):
            return normalize_curso('INFECTOXPERT')
        if any(k in t_norm for k in ['NUTRIFY']):
            return normalize_curso('NUTRIFY CONNECT')
            
        if email and 'rd_course_hints' in locals() and email in rd_course_hints:
            return rd_course_hints[email]
            
        return normalize_curso('PLATAFORMA GERAL')

    def get_core_subject(name):
        name = str(name).upper()
        if 'INFECTOPEDI' in name: return 'INFECTOPEDIATRIA'
        if 'ORTO' in name or 'PARTES MOLES' in name or 'PELE' in name: return 'ORTOPEDIA'
        if 'CCIH' in name or 'HOSPITALAR' in name: return 'CCIH'
        if 'IMUNO' in name or 'INUNO' in name: return 'IMUNODEPRIMIDOS'
        if 'FUNGO' in name or 'ANTIFUNGICO' in name: return 'FUNGO'
        if 'MULTI-R' in name or 'MULTIR' in name or 'MULTI R' in name: return 'MULTIR'
        if 'S.O.S' in name or 'ANTIBIOTICO' in name: return 'SOS'
        return name
    
    # 1. Integração com logs em tempo real da API InfectoCast Academy
    academy_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'academy_logs_cache.json')
    academy_api_logs = []
    
    inscricoes_path = get_bd_file('Inscrições.xlsx')
    if os.path.exists(inscricoes_path):
        try:
            df_insc = pd.read_excel(inscricoes_path)
            df_acad_live = fetch_logs_from_api(df_insc)
            if not df_acad_live.empty:
                for _, row in df_acad_live.iterrows():
                    academy_api_logs.append({
                        'Data log': pd.to_datetime(row['Data log'], errors='coerce'),
                        'Nome aluno': str(row.get('Nome aluno', '')).strip(),
                        'E-mail': str(row.get('E-mail', '')).lower().strip(),
                        'Ação / Local': row.get('Ação / Local', 'AÇÃO'),
                        'ID Item': row.get('ID Item', ''),
                        'Desc. Item': row.get('Desc. Item', ''),
                        'Modulo': 'Geral',
                        'Curso': 'PLATAFORMA GERAL',
                        'Plataforma': 'Academy'
                    })
                with open(academy_cache_path, 'w', encoding='utf-8') as f:
                    json.dump(df_acad_live.to_dict(orient='records'), f, default=str, ensure_ascii=False)
                print(f"[ACADEMY API] Consultados {len(academy_api_logs)} logs ao vivo diretamente da API InfectoCast Academy.")
        except Exception as e:
            print(f"[ACADEMY API] Erro ao consultar API ao vivo: {e}")

    if not academy_api_logs and os.path.exists(academy_cache_path):
        try:
            with open(academy_cache_path, 'r', encoding='utf-8') as f:
                acad_data = json.load(f)
                for item in acad_data:
                    academy_api_logs.append({
                        'Data log': pd.to_datetime(item.get('Data log'), errors='coerce'),
                        'Nome aluno': str(item.get('Nome aluno', '')).strip(),
                        'E-mail': str(item.get('E-mail', '')).lower().strip(),
                        'Ação / Local': item.get('Ação / Local', 'AÇÃO'),
                        'ID Item': item.get('ID Item', ''),
                        'Desc. Item': item.get('Desc. Item', ''),
                        'Modulo': item.get('Modulo', 'Geral'),
                        'Curso': item.get('Curso', 'PLATAFORMA GERAL'),
                        'Plataforma': 'Academy'
                    })
            print(f"[ACADEMY API] Carregados {len(academy_api_logs)} logs de backup do cache local.")
        except Exception as e:
            print(f"[ACADEMY API] Erro lendo cache de logs: {e}")

    if academy_api_logs:
        df_acad_api = pd.DataFrame(academy_api_logs)
        df_log = pd.concat([df_log, df_acad_api], ignore_index=True)

    df_log['Plataforma'] = df_log['Plataforma'].fillna('Academy')

    # 2. Integração com logs e alunos em tempo real da Cativa Digital (forçando consulta ao vivo da API)
    import cativa_api
    cativa_data = cativa_api.fetch_all_cativa_data(force_refresh=True)
    cativa_users_meta = cativa_data.get('users_metadata', {})
    cativa_students = cativa_data.get('students', [])
    cativa_logs = []

    for s in cativa_students:
        em = str(s.get('email', '')).lower().strip()
        nome = str(s.get('fullName', '')).strip()
        for c in s.get('courses', []):
            c_canon = canonicalize_curso(c.get('courseName', ''))
            for l in c.get('lessons', []):
                dt_s = l.get('watchedAt', '')[:19]
                dt_val = pd.to_datetime(dt_s, errors='coerce')
                if pd.notnull(dt_val):
                    dt_val = dt_val - pd.Timedelta(hours=3) # Cativa API retorna em UTC, converter para Horario de Brasilia (UTC-3)
                lesson_name = str(l.get('lessonName', '')).strip()
                mod_name = str(l.get('moduleName', '')).strip() or 'Geral'
                cativa_logs.append({
                    'Data log': dt_val,
                    'Nome aluno': nome,
                    'E-mail': em,
                    'Ação / Local': 'CONCLUIU AULA',
                    'ID Item': lesson_name,
                    'Desc. Item': lesson_name,
                    'Modulo': mod_name,
                    'Curso': c_canon,
                    'Plataforma': 'Cativa'
                })

    # Adicionar acessos/logins da Cativa de users_metadata
    for em, meta in cativa_users_meta.items():
        last_log = meta.get('last_login_at')
        if last_log:
            dt_val = pd.to_datetime(last_log[:19], errors='coerce')
            if pd.notnull(dt_val):
                dt_val = dt_val - pd.Timedelta(hours=3) # Cativa API retorna em UTC, converter para Horario de Brasilia (UTC-3)
            first_n = meta.get('first_name') or ''
            last_n = meta.get('last_name') or ''
            full_n = f"{first_n} {last_n}".strip() or em
            cativa_logs.append({
                'Data log': dt_val,
                'Nome aluno': full_n,
                'E-mail': em.lower().strip(),
                'Ação / Local': 'LOGIN WEB',
                'ID Item': 'Ambiente de Aprendizagem Cativa',
                'Desc. Item': 'Acesso Web à Plataforma Cativa',
                'Modulo': 'Geral',
                'Curso': 'PLATAFORMA GERAL',
                'Plataforma': 'Cativa'
            })

    df_cativa_logs = pd.DataFrame(cativa_logs)
    print(f"Total de {len(df_cativa_logs)} registros de logs (aulas + logins) carregados da Cativa Digital.")
    df_log = pd.concat([df_log, df_cativa_logs], ignore_index=True)
    
    # Garantir ordenação temporal e data de hoje oficial
    df_log = df_log.dropna(subset=['Data log']).sort_values('Data log')
    hoje = datetime.date.today()

    print("Montando grade curricular a partir dos logs da API...")
    
    student_course_map = {}
    
    pg_events = df_log[df_log['Ação / Local'] == 'PG INSCRIÇÃO TURMA']
    for _, row in pg_events.iterrows():
        email = str(row['E-mail']).strip()
        turma = str(row['ID Item'] or row['Desc. Item'] or '').strip()
        if turma and turma != 'nan' and email not in student_course_map:
            c_norm = canonicalize_curso(turma)
            if c_norm:
                student_course_map[email] = c_norm
    
    # Second pass: infer from watched lessons content for students without explicit PG event
    for email in df_log['E-mail'].dropna().unique():
        email = str(email).strip()
        if email in student_course_map:
            continue

        student_logs = df_log[df_log['E-mail'] == email]
        aula_logs = student_logs[student_logs['Ação / Local'].isin(['INICIOU AULA', 'CONCLUIU AULA'])]
        all_text = ' '.join(aula_logs['ID Item'].fillna('').astype(str)).upper()
        all_text = norm_title(all_text)

        if any(w in all_text for w in ['PEDIATRIA', 'INFECTOPEDIATRIA', 'NEONATAL', 'CRIANCA', 'SIFILIS CONGENITA']):
            student_course_map[email] = normalize_curso('PÓS-GRADUAÇÃO EM INFECTOPEDIATRIA')
        elif any(w in all_text for w in ['ORTOPEDIA', 'ORTO', 'PARTES MOLES', 'MUSCULOESQUELETICA']):
            student_course_map[email] = normalize_curso('PÓS-GRADUAÇÃO EM INFECÇÕES ORTOPÉDICAS E DE PARTES MOLES')
        elif any(w in all_text for w in ['CCIH', 'INFECCAO HOSPITALAR', 'PREVENCAO', 'VIGILANCIA', 'PAV', 'ISC', 'IPCSL']):
            student_course_map[email] = normalize_curso('PÓS-GRADUAÇÃO EM PREVENÇÃO E CONTROLE DE INFECÇÃO HOSPITALAR (CCIH)')
        elif any(w in all_text for w in ['IMUNO', 'IMUNODEPRIMIDO', 'TRANSPLANTE']):
            student_course_map[email] = normalize_curso('PÓS-GRADUAÇÃO EM INFECÇÕES EM IMUNODEPRIMIDOS')
        elif any(w in all_text for w in ['ANTIBIOTICO', 'S.O.S', 'ESBL', 'KPC', 'NDM', 'CRAB', 'PARC', 'MDR']):
            student_course_map[email] = normalize_curso('S.O.S ANTIBIÓTICO')
        elif any(w in all_text for w in ['FERRAMENTAS', 'ISHIKAWA', 'PARETO', 'PDCA', 'SIPOC', 'BRAINSTORMING', 'GEMBA']):
            student_course_map[email] = normalize_curso('FERRAMENTAS DE QUALIDADE')
        else:
            student_course_map[email] = normalize_curso('PLATAFORMA GERAL')
    
    # Step 2: Collect all lessons per course
    course_lessons = {}  # normalized_course -> {norm_title: original_title}
    course_modules = {}  # normalized_course -> {mod_name}
    
    aula_events = df_log[df_log['Ação / Local'].isin(['INICIOU AULA', 'CONCLUIU AULA'])]
    teste_events = df_log[df_log['Ação / Local'].str.contains('TESTE|MÓDULO', case=False, na=False)]
    
    for _, row in aula_events.iterrows():
        email = str(row['E-mail']).strip()
        item = str(row['ID Item'] or '').strip()
        if not item or item == 'nan':
            continue
        if pd.notna(row.get('Curso')) and row.get('Curso'):
            curso = row['Curso']
        else:
            curso = student_course_map.get(email, normalize_curso('PLATAFORMA GERAL'))
        if curso not in course_lessons:
            course_lessons[curso] = {}
        n_key = norm_title(item)
        if n_key and n_key not in course_lessons[curso]:
            course_lessons[curso][n_key] = item
        mod_val = row.get('Modulo')
        if pd.notna(mod_val) and str(mod_val).strip() and str(mod_val).strip() != 'nan':
            m_name = str(mod_val).strip()
            if curso not in course_modules:
                course_modules[curso] = set()
            course_modules[curso].add(m_name)
    
    for _, row in teste_events.iterrows():
        email = str(row['E-mail']).strip()
        item = str(row['ID Item'] or '').strip()
        if not item or item == 'nan':
            continue
        curso = student_course_map.get(email, normalize_curso('PLATAFORMA GERAL'))
        if curso not in course_modules:
            course_modules[curso] = set()
        course_modules[curso].add(item)
    
    # Step 3: Build final_curriculum with Module mapping
    # Scoped mapping (curso, lesson_normalized_name) -> module name to prevent cross-course collisions
    course_lesson_to_module = {}
    mod_id_to_name = {}
    mod_id_to_curso = {}
    
    def clean_module_name(m):
        if not m: return 'Geral'
        m_str = str(m).strip()
        low = m_str.lower()
        if 'encontros ao vivo' in low: return 'Encontros Ao Vivo'
        if 'journal club' in low: return 'Journal Club'
        return m_str

    for _, row in df_mods.iterrows():
        m_curso = canonicalize_curso(str(row.iloc[0]).strip())
        m_id = row.iloc[1]
        m_nome = clean_module_name(row.iloc[3])
        mod_id_to_name[m_id] = m_nome
        mod_id_to_curso[m_id] = m_curso

    for _, row in df_aulas.iterrows():
        m_id = row.iloc[1]
        a_nome = str(row.iloc[4])
        a_norm = norm_title(a_nome)
        if m_id in mod_id_to_name and a_norm:
            m_nome = mod_id_to_name[m_id]
            m_curso = mod_id_to_curso.get(m_id, '')
            course_lesson_to_module[(m_curso, a_norm)] = m_nome
            if m_curso:
                if m_curso not in course_modules: course_modules[m_curso] = set()
                course_modules[m_curso].add(m_nome)

    # Integrar grade curricular oficial em tempo real da API InfectoCast Academy
    try:
        from academy_service import AcademyService
        acad_serv = AcademyService()
        acad_curric = acad_serv.get_curriculo_completo()
        
        for c_orig_nome, c_mods in acad_curric.items():
            c_canon = canonicalize_curso(c_orig_nome)
            if c_canon not in course_modules:
                course_modules[c_canon] = set()
            if c_canon not in course_lessons:
                course_lessons[c_canon] = {}
                
            for m_obj in c_mods:
                m_nome = clean_module_name(m_obj.get('modulo', 'Geral'))
                course_modules[c_canon].add(m_nome)
                
                for a_obj in m_obj.get('aulas', []):
                    a_nome = a_obj.get('nome', '')
                    n_key = norm_title(a_nome)
                    if n_key:
                        course_lesson_to_module[(c_canon, n_key)] = m_nome
                        course_lessons[c_canon][n_key] = a_nome
        print(f"Grade curricular da API Academy integrada com sucesso: {len(acad_curric)} cursos.")
    except Exception as e_curric:
        print(f"Aviso ao carregar grade da API Academy: {e_curric}")

    for _, row in df_cativa_logs.iterrows():
        c = row['Curso']
        m = clean_module_name(row['Modulo'])
        l = row['ID Item']
        n_key = norm_title(l)
        if n_key and m:
            course_lesson_to_module[(c, n_key)] = m
            if c not in course_modules: course_modules[c] = set()
            course_modules[c].add(m)
            if c not in course_lessons: course_lessons[c] = {}
            course_lessons[c][n_key] = l

    final_curriculum = {}
    mod_map = {}  # module_id -> module_name
    lesson_id_counter = 900000  # synthetic IDs for API-derived lessons

    for curso, lessons_dict in course_lessons.items():
        modules_for_course = course_modules.get(curso, set())
        
        # We will create a dict mapping module_name -> list of lesson objects
        mod_dict = {m: [] for m in modules_for_course}
        mod_dict["Aulas Adicionais"] = []
        
        for n_key, original_name in sorted(lessons_dict.items(), key=lambda x: x[1]):
            lesson_id_counter += 1
            lesson_obj = {
                "id": lesson_id_counter,
                "nome": original_name,
                "curriculo": True,
                "ordem": 0 # updated later
            }
            
            # Use scoped lookup for this specific course
            mapped_mod = course_lesson_to_module.get((curso, n_key))
            if mapped_mod and mapped_mod in mod_dict:
                mod_dict[mapped_mod].append(lesson_obj)
            else:
                mod_dict["Aulas Adicionais"].append(lesson_obj)
                
        # Transform into final list format, skipping modules with 0 lessons
        mod_list = []
        for mod_name, aulas in mod_dict.items():
            if len(aulas) == 0:
                continue
            for idx, a in enumerate(aulas):
                a["ordem"] = str(idx + 1)
                
            mod_list.append({
                "modulo": mod_name,
                "n_curric": len(aulas),
                "n_fora": 0,
                "aulas": aulas
            })
            
        # Ordena a lista de módulos (Aulas Adicionais por último)
        mod_list.sort(key=lambda x: (x["modulo"] == "Aulas Adicionais", x["modulo"]))
        final_curriculum[curso] = mod_list
    
    print(f"Grade montada: {len(final_curriculum)} cursos, {sum(len(m) for m in final_curriculum.values())} módulos, {sum(len(a) for mods in final_curriculum.values() for m in mods for a in m['aulas'])} aulas.")
        
    def normalize_phone(phone_str):
        if pd.isna(phone_str): return ''
        digits = re.sub(r'\D', '', str(phone_str))
        if not digits: return ''
        if digits.startswith('55') and len(digits) in [12, 13]:
            digits = digits[2:]
        if len(digits) == 10:
            digits = digits[:2] + '9' + digits[2:]
        if len(digits) == 11:
            digits = '55' + digits
        return digits

    # ============================================
    # PROCESSAMENTO WA LOGS
    # ============================================
    wa_log_path = get_bd_file('Log mensagems.csv')
    wa_history = {}
    wa_chats = {}
    if os.path.exists(wa_log_path):
        try:
            with open(wa_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                wa_content = f.read()
            
            rows = wa_content.split('\n"')
            for r in rows:
                if '@c.us' not in r: continue
                parts = r.split('","')
                if len(parts) < 10: continue
                
                msg_id = parts[0]
                direction = 'true_' in msg_id # true = sent by us
                
                phone_m = re.search(r'(\d{10,13})@c\.us', msg_id)
                if not phone_m: continue
                phone = normalize_phone(phone_m.group(1))
                if not phone or phone == '5511947706357': continue # Company number
                
                body = parts[3].replace('""', '"') if len(parts) > 3 else ''
                if not body.strip() and len(parts) > 29:
                    msg_type = parts[29]
                    if msg_type == 'ptt' or msg_type == 'audio': body = '🎤 Áudio'
                    elif msg_type == 'image': body = '📷 Imagem'
                    elif msg_type == 'video': body = '🎥 Vídeo'
                    elif msg_type == 'document': body = '📄 Documento'
                    elif msg_type == 'sticker': body = '🧩 Sticker'
                    elif msg_type == 'vcard' or msg_type == 'contact': body = '👤 Contato'
                    elif msg_type == 'location': body = '📍 Localização'
                    elif msg_type != 'chat': body = f'[{msg_type}]'
                
                ts_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', r)
                if not ts_match: continue
                
                timestamp = ts_match.group(1)
                dt = datetime.datetime.fromisoformat(timestamp).replace(tzinfo=None)
                
                if phone not in wa_history:
                    wa_history[phone] = {'primeira': dt, 'ultima': dt, 'total': 0}
                    wa_chats[phone] = []
                else:
                    if dt < wa_history[phone]['primeira']: wa_history[phone]['primeira'] = dt
                    if dt > wa_history[phone]['ultima']: wa_history[phone]['ultima'] = dt
                
                wa_history[phone]['total'] += 1
                wa_chats[phone].append({
                    'sent': direction,
                    'text': body,
                    'date': dt.strftime('%Y-%m-%d %H:%M:%S')
                })
                
            for p in wa_chats:
                wa_chats[p].sort(key=lambda x: x['date'])
                
        except Exception as e:
            print("Erro processando log do WA:", e)

    def get_student_course_and_date(email, logs_df, default_d):
        det_curso = student_course_map.get(str(email).strip(), normalize_curso('PLATAFORMA GERAL'))
        det_date = default_d

        if not logs_df.empty:
            pg_logs = logs_df[logs_df['Ação / Local'] == 'PG INSCRIÇÃO TURMA']
            if not pg_logs.empty:
                pg_row = pg_logs.iloc[0]
                if pd.notna(pg_row['Data log']):
                    det_date = pg_row['Data log']

            if (pd.isna(det_date) or not det_date) and pd.notna(logs_df['Data log'].min()):
                det_date = logs_df['Data log'].min()

        return det_curso, det_date

    # ============================================
    # LEITURA LOGRD.CSV & DICAS DE CURSO
    # ============================================
    logrd_path = get_bd_file('LogRD.csv')
    rd_events_map = {}
    rd_course_hints = {}
    
    if os.path.exists(logrd_path):
        df_rd = pd.read_csv(logrd_path, encoding='utf-8', low_memory=False)
        df_rd['email_lower'] = df_rd['Email'].astype(str).str.lower().str.strip()
        
        # Build hints and events for all rows
        ev_col_name = 'Eventos (Últimos 100)' if 'Eventos (Últimos 100)' in df_rd.columns else None
        for _, row in df_rd.iterrows():
            email_k = str(row['email_lower']).strip()
            if not email_k or email_k == 'nan': continue
            
            tags_r = str(row.get('Tags', '')).lower()
            events_r = str(row.get(ev_col_name, '')).lower() if ev_col_name else ''
            curso_r = str(row.get('Curso', '')).lower()
            pos_r = str(row.get('Curso da Pós-graduação InfectoCast', '')).lower()
            comb_r = f"{tags_r} {events_r} {curso_r} {pos_r}"
            c_hint = canonicalize_curso(comb_r)
            if c_hint and c_hint != normalize_curso('PLATAFORMA GERAL'):
                rd_course_hints[email_k] = c_hint

    students = []
    
    df_acad = df_log[df_log.get('Plataforma', 'Academy') == 'Academy'] if 'Plataforma' in df_log.columns else df_log
    unique_academy_students = df_acad.dropna(subset=['E-mail']).drop_duplicates(subset=['E-mail'])
    
    for _, log_row in unique_academy_students.iterrows():
        email = str(log_row['E-mail']).strip()
        email_str = email.lower()
        if not email_str or email_str == 'nan' or 'teste' in email_str or '@infectocast' in email_str or '@vectorcomunica' in email_str or 'rand' in email_str:
            continue
            
        logs = df_log[df_log['E-mail'] == email]
        acessou = len(logs) > 0
        nome_aluno = str(logs['Nome aluno'].dropna().iloc[0]).strip() if not logs['Nome aluno'].dropna().empty else email_str

        curso_aluno, dt_insc_aluno = get_student_course_and_date(email, logs, None)
        
        c_inferido = False
        c_origem = "Log de Acesso"
        if curso_aluno in ["PLATAFORMA GERAL", "SEM CURSO", "CURSO DESCONHECIDO"] and 'rd_course_hints' in locals() and email_str in rd_course_hints:
            curso_aluno = rd_course_hints[email_str]
            c_inferido = True
            c_origem = "RD Station"
        
        # Safely compute dias_desde_insc and data_insc
        try:
            if dt_insc_aluno is not None and pd.notna(dt_insc_aluno):
                if hasattr(dt_insc_aluno, 'date'):
                    dias_desde_insc = (hoje - dt_insc_aluno.date()).days
                    data_insc_fmt = dt_insc_aluno.strftime("%d/%m/%Y")
                else:
                    dias_desde_insc = 0
                    data_insc_fmt = None
            else:
                dias_desde_insc = 0
                data_insc_fmt = None
        except Exception:
            dias_desde_insc = 0
            data_insc_fmt = None
        
        telefone = ""
        if email_str in cativa_users_meta:
            telefone = normalize_phone(cativa_users_meta[email_str].get('phone', ''))
            
        student_data = {
            "email": str(email),
            "nome": nome_aluno,
            "curso": curso_aluno,
            "curso_inferido": c_inferido,
            "curso_origem": c_origem,
            "telefone": telefone,
            "acessou": acessou,
            "data_insc": data_insc_fmt,
            "data_inscricao": data_insc_fmt,
            "inscricao": data_insc_fmt,
            "dias_desde_insc": dias_desde_insc,
            "plataforma": "Academy",
            "id_aluno": ""
        }
        
        if acessou:
            first_log = logs['Data log'].min()
            last_log = logs['Data log'].max()
            
            dias_ativo = (last_log - first_log).days
            logins_count = len(logs[logs.iloc[:, 3] == 'LOGIN WEB'])
            cadencia = dias_ativo / max(1, logins_count - 1)
            
            student_data.update({
                "first": first_log.strftime("%d/%m/%Y"),
                "last": last_log.strftime("%d/%m/%Y"),
                "dias_ativo": dias_ativo,
                "dias_inativo": (hoje - last_log.date()).days,
                "logins": logins_count,
                "cadencia": cadencia,
                "aulas_iniciadas": len(logs[logs.iloc[:, 3] == 'INICIOU AULA']),
                "aulas_concluidas": len(logs[logs.iloc[:, 3] == 'CONCLUIU AULA']),
                "materiais": len(logs[logs.iloc[:, 3] == 'BAIXOU MATERIAL PDF']),
                "testes": len(logs[logs.iloc[:, 3] == 'CONCLUIU TESTE/MÓDULO']),
                "lag": 0,
                "last_fmt": last_log.strftime("%d/%m/%Y"),
                "events": [],
                "wa_dt_primeira": None,
                "wa_dt_ultima": None,
                "wa_total": 0
            })
            
            # WA Mapping for Student
            # Try to find their phone from insc dataframe
            phone1 = telefone
            phone2 = ''
            if phone1 and phone1 in wa_history:
                student_data['wa_dt_primeira'] = wa_history[phone1]['primeira'].strftime('%d/%m/%Y')
                student_data['wa_dt_ultima'] = wa_history[phone1]['ultima'].strftime('%d/%m/%Y')
                student_data['wa_total'] = wa_history[phone1]['total']
            elif phone2 and phone2 in wa_history:
                student_data['wa_dt_primeira'] = wa_history[phone2]['primeira'].strftime('%d/%m/%Y')
                student_data['wa_dt_ultima'] = wa_history[phone2]['ultima'].strftime('%d/%m/%Y')
                student_data['wa_total'] = wa_history[phone2]['total']
            
            # Helper function for text normalization
            def norm_str(s):
                if not s or pd.isna(s): return ''
                s = str(s).strip().upper()
                return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

            # Create flat maps for quick lesson lookup (by ID and by Normalized Title)
            if 'lesson_map' not in locals():
                lesson_map = {}
                name_to_lesson = {}
                for c_n, mds in final_curriculum.items():
                    for m_d in mds:
                        for a_d in m_d["aulas"]:
                            a_id_val = a_d["id"]
                            a_name_val = a_d["nome"]
                            m_name_val = m_d["modulo"]
                            
                            lesson_map[str(a_id_val)] = (a_name_val, m_name_val, a_id_val)
                            n_key = norm_str(a_name_val)
                            if n_key:
                                name_to_lesson[n_key] = (a_name_val, m_name_val, a_id_val)
                            
            # Create a more robust mod_map lookup
            if 'robust_mod_map' not in locals():
                robust_mod_map = {}
                for k, v in mod_map.items():
                    if pd.notna(k):
                        robust_mod_map[str(int(k))] = v
                        robust_mod_map[norm_str(v)] = v
                        
            # Create lightweight events array (deduplicating "ASSISTIU AULA")
            last_event_key = None
            
            for _, r in logs.sort_values('Data log', ascending=False).iterrows():
                acao = str(r.iloc[3])
                
                # Consolidate INICIOU AULA and CONCLUIU AULA
                if acao in ["INICIOU AULA", "CONCLUIU AULA"]:
                    acao = "ASSISTIU AULA"
                    
                cat = "login" if "LOGIN" in acao else "iniciou" if "ASSISTIU" in acao else "concluiu" if "CONCLUIU" in acao else "outros"
                
                item_id = r.iloc[4]
                item_name = ""
                mod_name = ""
                numeric_item_id = None
                
                if pd.notna(item_id) and str(item_id).strip():
                    raw_str = str(item_id).strip()
                    norm_item = norm_str(raw_str)
                    
                    if "TESTE" in acao or "MÓDULO" in acao:
                        item_name = robust_mod_map.get(raw_str, robust_mod_map.get(norm_item, raw_str))
                        numeric_item_id = raw_str
                    else:
                        # Try exact ID lookup
                        if raw_str in lesson_map:
                            item_name, mod_name, numeric_item_id = lesson_map[raw_str]
                        # Try exact normalized name lookup
                        elif norm_item in name_to_lesson:
                            item_name, mod_name, numeric_item_id = name_to_lesson[norm_item]
                        else:
                            # Try partial/fuzzy title match
                            matched_tup = None
                            for k_norm, tup in name_to_lesson.items():
                                if len(k_norm) > 4 and (k_norm in norm_item or norm_item in k_norm):
                                    matched_tup = tup
                                    break
                            if matched_tup:
                                item_name, mod_name, numeric_item_id = matched_tup
                            else:
                                item_name = raw_str
                                numeric_item_id = raw_str
                            
                # Deduplicate ASSISTIU AULA in the same minute
                d_str = r['Data log'].strftime("%d/%m/%Y %H:%M") if pd.notna(r['Data log']) else ""
                event_key = (d_str, acao, item_name)
                
                if acao == "ASSISTIU AULA" and event_key == last_event_key:
                    continue
                last_event_key = event_key
                
                student_data["events"].append({
                    "d": d_str,
                    "acao": acao,
                    "cat": cat,
                    "item_id": numeric_item_id,
                    "item": item_name,
                    "mod": mod_name
                })
            
        students.append(student_data)
        
    # Inserir alunos exclusivos da Cativa Digital
    processed_student_keys = set()
    for s_obj in students:
        processed_student_keys.add((s_obj['email'].lower().strip(), s_obj['curso']))

    for s in cativa_students:
        email = str(s.get('email', '')).lower().strip()
        if not email or any(x in email for x in ['teste', '@infectocast', '@vectorcomunica', 'rand', 'gcotta29']):
            continue
        
        nome = str(s.get('fullName', '')).strip()
        u_meta = cativa_users_meta.get(email, {})
        phone = u_meta.get('phone', '')
        created_at = u_meta.get('created_at', '')
        
        dt_insc = pd.to_datetime(created_at[:19], errors='coerce') if created_at else None
        if pd.notnull(dt_insc):
            dt_insc = dt_insc - pd.Timedelta(hours=3) # Cativa API retorna em UTC, converter para Horario de Brasilia (UTC-3)
        
        courses = s.get('courses', [])
        if not courses:
            continue
            
        for c in courses:
            c_canon = canonicalize_curso(c.get('courseName', ''))
            key = (email, c_canon)
            if key in processed_student_keys:
                continue
            processed_student_keys.add(key)
            
            logs = df_log[(df_log['E-mail'] == email) & ((df_log['Curso'] == c_canon) | (df_log['Curso'] == 'PLATAFORMA GERAL'))]
            if logs.empty:
                logs = df_log[df_log['E-mail'] == email]
                
            acessou = len(logs) > 0
            
            dt_insc_fmt = dt_insc.strftime("%d/%m/%Y") if pd.notna(dt_insc) else None
            dias_desde_insc = (hoje - dt_insc.date()).days if pd.notna(dt_insc) else 0
            
            has_acad = any(logs['Plataforma'] == 'Academy')
            has_cat = any(logs['Plataforma'] == 'Cativa')
            plat_str = 'Ambas' if (has_acad and has_cat) else ('Cativa' if has_cat else 'Academy')
            
            tel = normalize_phone(phone)
            student_data = {
                "email": email,
                "nome": nome,
                "curso": c_canon,
                "telefone": tel,
                "acessou": acessou,
                "data_insc": dt_insc_fmt,
                "data_inscricao": dt_insc_fmt,
                "inscricao": dt_insc_fmt,
                "dias_desde_insc": dias_desde_insc,
                "plataforma": plat_str
            }
            
            if acessou:
                first_log = logs['Data log'].min()
                last_log = logs['Data log'].max()
                dias_ativo = (last_log - first_log).days
                logins_count = max(1, len(logs['Data log'].dt.date.unique()))
                cadencia = dias_ativo / max(1, logins_count - 1)
                
                student_data.update({
                    "first": first_log.strftime("%d/%m/%Y") if pd.notna(first_log) else "",
                    "last": last_log.strftime("%d/%m/%Y") if pd.notna(last_log) else "",
                    "dias_ativo": dias_ativo,
                    "dias_inativo": (hoje - last_log.date()).days if pd.notna(last_log) else 0,
                    "logins": logins_count,
                    "cadencia": cadencia,
                    "aulas_iniciadas": len(logs),
                    "aulas_concluidas": len(logs),
                    "materiais": 0,
                    "testes": 0,
                    "lag": (first_log.date() - dt_insc.date()).days if (pd.notna(dt_insc) and pd.notna(first_log)) else 0,
                    "last_fmt": last_log.strftime("%d/%m/%Y") if pd.notna(last_log) else "",
                    "events": [],
                    "wa_dt_primeira": None,
                    "wa_dt_ultima": None,
                    "wa_total": 0
                })
                
                if tel and tel in wa_history:
                    student_data['wa_dt_primeira'] = wa_history[tel]['primeira'].strftime('%d/%m/%Y')
                    student_data['wa_dt_ultima'] = wa_history[tel]['ultima'].strftime('%d/%m/%Y')
                    student_data['wa_total'] = wa_history[tel]['total']
                    
                last_event_key = None
                for _, r in logs.sort_values('Data log', ascending=False).iterrows():
                    raw_acao = str(r.iloc[3] if len(r) > 3 else "ASSISTIU AULA").upper()

                    acao = "LOGIN WEB (Cativa)" if "LOGIN" in raw_acao else "ASSISTIU AULA"

                    cat = "login" if "LOGIN" in raw_acao else "concluiu"
                    item_name = str(r['ID Item']).strip()
                    mod_name = str(r.get('Modulo', '')).strip()
                    d_str = r['Data log'].strftime("%d/%m/%Y %H:%M") if pd.notna(r['Data log']) else ""
                    event_key = (d_str, acao, item_name)
                    if event_key == last_event_key:
                        continue
                    last_event_key = event_key
                    student_data["events"].append({
                        "d": d_str,
                        "acao": acao,
                        "cat": cat,
                        "item_id": item_name,
                        "item": item_name,
                        "mod": mod_name
                    })
            else:
                student_data.update({
                    "dias_inativo": 999,
                    "logins": 0,
                    "aulas_iniciadas": 0,
                    "aulas_concluidas": 0,
                    "materiais": 0,
                    "testes": 0,
                    "events": []
                })
                
            students.append(student_data)
        
    print(f"Total consolidado de estudantes gerados: {len(students)} ({len(set(s['email'] for s in students))} únicos).")
        
    # ============================================
    # FUNIL DE LEADS — Processamento LogRD.csv
    # ============================================
    logrd_path = get_bd_file('LogRD.csv')
    funil_data = {}
    
    if os.path.exists(logrd_path):
        df_rd = pd.read_csv(logrd_path, encoding='utf-8', low_memory=False)
        
        emails_inscritos_set = set(str(s['email']).lower().strip() for s in students if s.get('email'))
        for s in cativa_students:
            em_c = str(s.get('email', '')).lower().strip()
            if em_c:
                emails_inscritos_set.add(em_c)
        df_rd['email_lower'] = df_rd['Email'].str.lower().str.strip()
        
        def check_aluno(row):
            if row['email_lower'] in emails_inscritos_set:
                return True
            tags = str(row['Tags']).lower()
            if '[pós] todos os alunos' in tags or 'aluno pós' in tags:
                return True
            return False
            
        df_rd['e_aluno'] = df_rd.apply(check_aluno, axis=1)
        
        # Parse dates
        df_rd['dt_primeira'] = pd.to_datetime(df_rd['Data da primeira conversão'].str[:19], errors='coerce')
        df_rd['dt_ultima'] = pd.to_datetime(df_rd['Data da última conversão'].str[:19], errors='coerce')
        df_rd['dt_venda'] = pd.to_datetime(df_rd['Data da última venda'].str[:19], errors='coerce')
        
        # WhatsApp matching
        def get_wa_info(row):
            phone1 = normalize_phone(row.get('Telefone'))
            phone2 = normalize_phone(row.get('Celular'))
            if phone1 and phone1 in wa_history: return wa_history[phone1]
            if phone2 and phone2 in wa_history: return wa_history[phone2]
            return None
        
        df_rd['wa_info'] = df_rd.apply(get_wa_info, axis=1)
        df_rd['contatado_wa'] = df_rd['wa_info'].notnull()
        
        # --- 1. KPIs do Funil ---
        total_leads = len(df_rd)
        n_lead = len(df_rd[df_rd['Estágio no funil'] == 'Lead'])
        n_lq = len(df_rd[df_rd['Estágio no funil'] == 'Lead Qualificado'])
        n_wa = int(df_rd['contatado_wa'].sum())
        n_cliente = len(df_rd[df_rd['Estágio no funil'] == 'Cliente'])
        n_alunos_cruzados = int(df_rd['e_aluno'].sum())
        
        funil_kpis = {
            'total': total_leads,
            'lead': n_lead,
            'lead_qualificado': n_lq,
            'wa_contatados': n_wa,
            'cliente': n_cliente,
            'aluno': n_alunos_cruzados,
            'taxa_lq': round(n_lq / max(1, total_leads) * 100, 1),
            'taxa_wa': round(n_wa / max(1, total_leads) * 100, 1),
            'taxa_cliente': round(n_cliente / max(1, total_leads) * 100, 1),
            'taxa_aluno': round(n_alunos_cruzados / max(1, total_leads) * 100, 2),
        }
        
        # --- 2. Origens ---
        def normalizar_origem(origem):
            if pd.isna(origem): return 'Desconhecido'
            o = str(origem).lower()
            if 'desconhecido' in o: return 'Desconhecido'
            if 'direto' in o: return 'Tráfego Direto'
            if 'google' in o and 'org' in o: return 'Busca Orgânica (Google)'
            
            # Anúncios
            if 'ads' in o or 'paid' in o or 'cpl' in o or 'auto' in o or 'feed' in o or 'envolvimento' in o:
                if 'facebook' in o or 'fb' in o: return 'Facebook Ads'
                if 'instagram' in o or 'ig' in o: return 'Instagram Ads'
                return 'Anúncios (Outros)'
                
            # Social Orgânico
            if 'instagram' in o or 'ig' in o or 'linktr' in o: return 'Instagram (Orgânico)'
            if 'facebook' in o or 'fb' in o: return 'Facebook (Orgânico)'
            
            if 'email' in o: return 'Email Marketing'
            if 'infectocast' in o: return 'Site InfectoCast'
            
            # Retorna o nome original limpo se não classificado acima, para não perder informação valiosa
            return str(origem).split('|')[0].strip() if '|' in str(origem) else str(origem)

        col_origem = [c for c in df_rd.columns if 'Origem da primeira convers' in c]
        if col_origem:
            df_rd['Origem_Agrupada'] = df_rd[col_origem[0]].apply(normalizar_origem)
        else:
            df_rd['Origem_Agrupada'] = 'Desconhecido'
            
        origens_all = df_rd['Origem_Agrupada'].value_counts().head(10).to_dict()
        origens_alunos = df_rd[df_rd['e_aluno']]['Origem_Agrupada'].value_counts().head(10).to_dict()
        
        # --- 3. Tempo de conversão dos alunos ---
        alunos_rd = df_rd[df_rd['e_aluno']].copy()
        
        # Cruzar com data de inscrição
        insc_dates = {}
        for s in students:
            em = str(s.get('email', '')).lower().strip()
            dt_raw = s.get('data_insc') or s.get('data_inscricao') or s.get('inscricao')
            if em and dt_raw:
                try:
                    dt = pd.to_datetime(dt_raw, dayfirst=True)
                    if em not in insc_dates or dt < insc_dates[em]:
                        insc_dates[em] = dt
                except Exception:
                    pass
        
        tempo_conv = []
        for _, row in alunos_rd.iterrows():
            em = row['email_lower']
            if em in insc_dates and pd.notna(row['dt_primeira']):
                dias = (insc_dates[em] - row['dt_primeira']).days
                if dias >= 0:
                    tempo_conv.append(dias)
        
        # Histograma: distribuição em faixas
        faixas = [0, 7, 30, 60, 90, 120, 180, 365, 9999]
        faixa_labels = ['0-7d', '8-30d', '31-60d', '61-90d', '91-120d', '121-180d', '181-365d', '365d+']
        hist_conv = []
        for i in range(len(faixas)-1):
            count = len([d for d in tempo_conv if faixas[i] <= d < faixas[i+1]])
            hist_conv.append({'faixa': faixa_labels[i], 'count': count})
        
        media_conv = round(sum(tempo_conv) / max(1, len(tempo_conv)), 1)
        mediana_conv = sorted(tempo_conv)[len(tempo_conv)//2] if tempo_conv else 0
        
        # --- 4. Eventos que antecedem a matrícula ---
        ev_col = [c for c in df_rd.columns if 'ltimos' in c]
        ev_col_name = ev_col[0] if ev_col else None
        
        eventos_alunos = {}
        eventos_nao_alunos = {}
        
        if ev_col_name:
            for _, row in df_rd.iterrows():
                evs = str(row[ev_col_name])
                if evs == 'nan' or not evs.strip():
                    continue
                event_list = [e.strip() for e in evs.split('/') if e.strip()]
                target = eventos_alunos if row['e_aluno'] else eventos_nao_alunos
                for ev in event_list:
                    # Normalizar eventos
                    ev_norm = ev.lower().strip()
                    
                    # Ignorar eventos financeiros / pós-matrícula
                    if ev_norm in ['26', 'v1', 'compra'] or ev_norm == '':
                        continue
                    if any(x in ev_norm for x in ['pago', 'pendente', 'recorrencia', 'marco', 'compra', 'inscricoes-finalizadas', '[pós]']):
                        continue
                        
                    # Agrupar tipos
                    if 'ebook' in ev_norm or 'e-book' in ev_norm:
                        cat = 'Ebook'
                    elif 'lead ads' in ev_norm:
                        cat = 'Lead Ads'
                    elif 'live' in ev_norm:
                        cat = 'Live'
                    elif 'webnar' in ev_norm or 'webinar' in ev_norm:
                        cat = 'Webinar'
                    elif 'pos-graduacao' in ev_norm or 'pós' in ev_norm:
                        cat = 'Interesse Pós-Graduação'
                    elif 'jornada' in ev_norm:
                        cat = 'Jornada'
                    elif 'infectoxpert' in ev_norm:
                        cat = 'InfectoXpert'
                    elif 'lista-espera' in ev_norm or 'espera' in ev_norm:
                        cat = 'Lista de Espera'
                    elif 'sos' in ev_norm:
                        cat = 'Curso SOS'
                    elif 'aula' in ev_norm:
                        cat = 'Aulas Gratuitas'
                    elif 'newsletter' in ev_norm or 'substack' in ev_norm:
                        cat = 'Newsletter'
                    elif 'congresso' in ev_norm or 'ciop' in ev_norm:
                        cat = 'Eventos/Congresso'
                    elif 'fale-conosco' in ev_norm or 'atendimento' in ev_norm or 'formul' in ev_norm or 'fluentform' in ev_norm:
                        cat = 'Contato/Formulários'
                    elif 'importacao' in ev_norm or 'atualizado' in ev_norm or 'alunos' in ev_norm or 'carrinho' in ev_norm or 'unimed' in ev_norm:
                        continue  # Skip internal/admin events
                    else:
                        cat = 'Outro'
                    target[cat] = target.get(cat, 0) + 1
        
        # Top events for students
        top_eventos_alunos = sorted(eventos_alunos.items(), key=lambda x: -x[1])[:10]
        top_eventos_nao = sorted(eventos_nao_alunos.items(), key=lambda x: -x[1])[:10]
        
        # --- 5. Scoring de Maturidade ---
        leads_scoring = []
        keywords_pos = ['pos-graduacao', 'pós', 'pos', 'ccih', 'infectoped', 'pediatria', 'ortoped', 'imuno', 'multi-r', 'biofilme', 'pga', 'enfermagem', 'especializacao', 'diploma', 'grade_pos']
        icp_profs = ['enferm', 'medic', 'médic', 'farmac', 'infecto', 'biomed', 'bioméd', 'fisio', 'nutri', 'biolog', 'biólog']

        for _, row in df_rd[~df_rd['e_aluno']].iterrows():
            conversoes = row['Total de conversões'] if pd.notna(row['Total de conversões']) else 0
            scoring_rd = row['Lead Scoring - Interesse'] if pd.notna(row['Lead Scoring - Interesse']) else 0
            
            # Dias desde primeira conversão e última conversão
            dias_desde = 0
            if pd.notna(row['dt_primeira']):
                dias_desde = (pd.Timestamp(hoje) - row['dt_primeira']).days
                
            dias_ultima = 9999
            if pd.notna(row['dt_ultima']):
                dias_ultima = (pd.Timestamp(hoje) - row['dt_ultima']).days
            
            # Check events
            evs_str = str(row[ev_col_name]) if ev_col_name else ''
            ev_list_raw = [e.strip() for e in evs_str.split('/') if e.strip()] if evs_str != 'nan' else []
            ev_list = []
            for e in ev_list_raw:
                e_low = e.lower().strip()
                if e_low == '26': continue
                if not any(x in e_low for x in ['pago', 'pendente', 'recorrencia', 'marco', '[pós]', '[pos]', 'aluno']):
                    ev_list.append(e)
            
            # Remove duplicated events maintaining order
            ev_list = list(dict.fromkeys(ev_list))
            
            tags_lower = str(row['Tags']).lower() if pd.notna(row['Tags']) else ''
            evs_text = ' '.join(ev_list).lower() + ' ' + tags_lower
                    
            tem_pos = any(k in evs_text for k in keywords_pos)
            tem_lista_espera = any('lista-espera' in e.lower() or 'espera' in e.lower() for e in ev_list)
            
            # Curso recomendado via Tags
            cursos_rec = []
            if '[ped]' in tags_lower or 'ped' in tags_lower or 'pediatria' in evs_text: cursos_rec.append('Ped')
            if '[ccih]' in tags_lower or 'ccih' in tags_lower or 'ccih' in evs_text: cursos_rec.append('CCIH')
            if '[imuno]' in tags_lower or 'imuno' in tags_lower or 'imuno' in evs_text: cursos_rec.append('Imuno')
            if '[orto]' in tags_lower or 'orto' in tags_lower or 'ortoped' in evs_text: cursos_rec.append('Orto')
            curso_str = ', '.join(cursos_rec) if cursos_rec else '-'
            
            # Profissão consolidada
            prof_cols = ['Especialidade', 'Eu sou:', 'E a sua profissão?', 'Profissão', 'Profissão.1', 'Profissão:', 'Qual a sua Formação', 'Qual a sua profissão', 'Qual é a sua profissão?', 'Cargo', 'Qual a sua outra profissão', 'Medical specialty']
            profs = []
            for col in prof_cols:
                if col in row and pd.notna(row[col]):
                    val = str(row[col]).strip()
                    if val and val.lower() not in [p.lower() for p in profs] and val.lower() not in ['outro', 'outros', 'nenhuma', 'nd', 'n/a', 'nenhum']:
                        profs.append(val)
            profissao_str = ' | '.join(profs) if profs else '-'
            if len(profissao_str) > 45:
                profissao_str = profissao_str[:42] + '...'
            
            tem_icp_prof = any(p in profissao_str.lower() for p in icp_profs)
            
            # Score calculation (0-100)
            score = 0
            # 1. Volume de conversões (máx 30 pts)
            score += min(30, (conversoes / 8) * 30)
            
            # 2. Maturidade / Fidelidade / Recência (máx 20 pts)
            if (dias_desde > 180 and (dias_ultima <= 120 or conversoes >= 4)) or (30 <= dias_desde <= 180):
                score += 20
            else:
                score += 10
                
            # 3. Interesse temático em Cursos / Pós-graduação (máx 25 pts)
            if tem_pos:
                score += 25
                
            # 4. Lista de Espera (máx 10 pts)
            if tem_lista_espera:
                score += 10
                
            # 5. Afinidade de Profissão / Perfil ICP (máx 15 pts)
            if tem_icp_prof:
                score += 15
                
            # 6. Scoring RD Station (bônus máx 5 pts)
            score += min(5, (scoring_rd / 100) * 5)
            
            score = min(100, round(score))
            
            # Classificar
            if score >= 70:
                maturidade = 'Pronto'
            elif score >= 50:
                maturidade = 'Quente'
            elif score >= 25:
                maturidade = 'Morno'
            else:
                maturidade = 'Frio'
            
            if score >= 25:  # Só incluir leads relevantes
                leads_scoring.append({
                    'email': row['Email'],
                    'nome': str(row['Nome']) if pd.notna(row['Nome']) else '',
                    'telefone': str(row['Telefone']) if pd.notna(row['Telefone']) else (str(row['Celular']) if pd.notna(row['Celular']) else ''),
                    'estagio': row['Estágio no funil'] if pd.notna(row['Estágio no funil']) else 'Lead',
                    'conversoes': int(conversoes),
                    'scoring_rd': int(scoring_rd),
                    'dias_desde': dias_desde,
                    'score': score,
                    'maturidade': maturidade,
                    'origem': str(row['Origem da primeira conversão']) if pd.notna(row['Origem da primeira conversão']) else '-',
                    'curso': curso_str,
                    'profissao': profissao_str,
                    'dt_primeira': row['dt_primeira'].strftime('%d/%m/%Y') if pd.notna(row['dt_primeira']) else '—',
                    'dt_ultima': row['dt_ultima'].strftime('%d/%m/%Y') if pd.notna(row['dt_ultima']) else '—',
                    'wa_dt_primeira': row['wa_info']['primeira'].strftime('%d/%m/%Y') if row['wa_info'] else None,
                    'wa_total': row['wa_info']['total'] if row['wa_info'] else 0,
                    'eventos': ev_list,
                })
        
        leads_scoring.sort(key=lambda x: -x['score'])
        
        # Inject WA-only leads
        rd_phones = set()
        for _, row in df_rd.iterrows():
            if 'Celular' in row and pd.notna(row['Celular']): rd_phones.add(normalize_phone(row['Celular']))
            if 'Telefone' in row and pd.notna(row['Telefone']): rd_phones.add(normalize_phone(row['Telefone']))
        for s in students:
            if s.get('telefone'): rd_phones.add(s['telefone'])
            
        wa_only_count = 0
        for phone, history in wa_history.items():
            if phone not in rd_phones and history['total'] > 0:
                wa_only_count += 1
                leads_scoring.append({
                    'email': f'{phone}@whatsapp', # Fake email for unique ID
                    'nome': f'WhatsApp: {phone}',
                    'telefone': phone,
                    'estagio': 'Lead',
                    'conversoes': 0,
                    'scoring_rd': 0,
                    'dias_desde': 0,
                    'score': 25, 
                    'maturidade': 'Morno',
                    'origem': 'WhatsApp Direto',
                    'curso': '-',
                    'profissao': '-',
                    'dt_primeira': '—',
                    'dt_ultima': '—',
                    'wa_dt_primeira': history['primeira'].strftime('%d/%m/%Y'),
                    'wa_total': history['total'],
                    'eventos': ['Contato Exclusivo via WhatsApp']
                })
        print(f"Adicionados {wa_only_count} leads exclusivos do WA.")
        
        # Contagem por maturidade
        mat_counts = {}
        for ls in leads_scoring:
            mat_counts[ls['maturidade']] = mat_counts.get(ls['maturidade'], 0) + 1
        
        # Timeline de captação
        df_rd['mes_primeira'] = df_rd['dt_primeira'].dt.to_period('M')
        captacao_mensal = df_rd.dropna(subset=['dt_primeira']).groupby('mes_primeira').agg(
            leads=('Email', 'count'),
            alunos=('e_aluno', 'sum')
        ).reset_index()
        captacao_mensal['mes'] = captacao_mensal['mes_primeira'].astype(str)
        captacao_timeline = captacao_mensal[['mes', 'leads', 'alunos']].to_dict('records')
        for item in captacao_timeline:
            item['alunos'] = int(item['alunos'])
            
        # Extract RD history and course hints from LogRD
        rd_events_map = {}
        rd_course_hints = {}
        for _, row in df_rd.iterrows():
            email_k = str(row['email_lower']).strip()
            if not email_k or email_k == 'nan': continue
            
            # Infer course hint from RD lead tags and events
            tags_r = str(row.get('Tags', '')).lower()
            events_r = str(row.get(ev_col_name, '')).lower() if ev_col_name else ''
            curso_r = str(row.get('Curso', '')).lower()
            pos_r = str(row.get('Curso da Pós-graduação InfectoCast', '')).lower()
            comb_r = f"{tags_r} {events_r} {curso_r} {pos_r}"
            
            if '[ccih]' in tags_r or 'pos-ccih' in comb_r or 'ebook ccih' in comb_r or 'pga enfermagem' in comb_r or 'prevenção e controle' in comb_r:
                rd_course_hints[email_k] = normalize_curso('PÓS-GRADUAÇÃO EM PREVENÇÃO E CONTROLE DE INFECÇÃO HOSPITALAR (CCIH)')
            elif '[ped]' in tags_r or 'pos-ped' in comb_r or 'infectoped' in comb_r or 'pediatria' in comb_r:
                rd_course_hints[email_k] = normalize_curso('PÓS-GRADUAÇÃO EM INFECTOPEDIATRIA')
            elif '[ortoped]' in tags_r or 'ortoped' in comb_r or 'partes moles' in comb_r:
                rd_course_hints[email_k] = normalize_curso('PÓS-GRADUAÇÃO EM INFECÇÕES ORTOPÉDICAS E DE PARTES MOLES')
            elif '[imuno]' in tags_r or 'imuno' in comb_r or 'imunodeprimidos' in comb_r:
                rd_course_hints[email_k] = normalize_curso('PÓS-GRADUAÇÃO EM INFECÇÕES EM IMUNODEPRIMIDOS')
            elif 'sos-antibiotico' in comb_r or 'sos atb' in comb_r or 'ebook-novos-antibioticos' in comb_r or 'jornada multi-r' in comb_r:
                rd_course_hints[email_k] = normalize_curso('S.O.S ANTIBIÓTICO')
            evs_str = str(row[ev_col_name]) if ev_col_name else ''
            ev_list_raw = [e.strip() for e in evs_str.split('/') if e.strip()] if evs_str != 'nan' else []
            ev_list = []
            for e in ev_list_raw:
                e_low = e.lower().strip()
                if e_low in ['26', 'v1', 'compra', '']: continue
                if not any(x in e_low for x in ['pago', 'pendente', 'recorrencia', 'marco', '[pós]', '[pos]', 'aluno']):
                    ev_list.append(e)
            
            # Remove duplicated events maintaining order
            ev_list = list(dict.fromkeys(ev_list))
            
            dias_venda = ''
            if pd.notna(row['dt_primeira']):
                if pd.notna(row['dt_venda']):
                    dias_venda = (row['dt_venda'] - row['dt_primeira']).days
                elif row['email_lower'] in insc_dates:
                    diff = (insc_dates[row['email_lower']] - row['dt_primeira']).days
                    if diff >= 0:
                        dias_venda = diff
                
            fmt_eventos_logrd = []
            for e in ev_list:
                c_name = clean_rd_event_name(e)
                cat = categorize_rd_event(e)
                fmt_eventos_logrd.append(f"<b>{c_name}</b> <span style='font-size:10px; color:var(--muted)'>({cat})</span>")
                
            rd_events_map[row['email_lower']] = {
                'origem': str(row['Origem da primeira conversão']) if pd.notna(row['Origem da primeira conversão']) else '-',
                'conversoes': int(row['Total de conversões']) if pd.notna(row['Total de conversões']) else 0,
                'conversoes_antes': len(ev_list),
                'scoring': int(row['Lead Scoring - Interesse']) if pd.notna(row['Lead Scoring - Interesse']) else 0,
                'dias_venda': dias_venda,
                'dt_primeira': row['dt_primeira'].strftime('%d/%m/%Y') if pd.notna(row['dt_primeira']) else '—',
                'dt_ultima': row['dt_ultima'].strftime('%d/%m/%Y') if pd.notna(row['dt_ultima']) else '—',
                'eventos': fmt_eventos_logrd,
                'eventos_detalhados': [{'data': '', 'evento_raw': e, 'evento_clean': clean_rd_event_name(e), 'categoria': categorize_rd_event(e)} for e in ev_list],
                'fonte': 'LogRD.csv'
            }
            
        # Carregar cache da API Oficial do RD Station
        rd_api_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rd_students_cache.json')
        rd_api_data = {}
        if os.path.exists(rd_api_cache_path):
            try:
                with open(rd_api_cache_path, 'r', encoding='utf-8') as f_rd:
                    rd_api_data = json.load(f_rd)
                print(f"[RD API] {len(rd_api_data)} alunos carregados do cache oficial da API do RD Station.")
            except Exception as e_rd:
                print(f"[RD API] Erro ao ler cache da API: {e_rd}")

        for s in students:
            em = s['email'].lower().strip()
            
            # Prioridade: Dados diretos da API Oficial do RD Station
            if em in rd_api_data and rd_api_data[em].get('encontrado_rd'):
                ast = rd_api_data[em]
                conv_antes = ast.get('conversoes_antes_matricula', [])
                
                # Se não houver conversões estritamente antes, usar todas
                conv_list = conv_antes if conv_antes else ast.get('conversoes_todas', [])
                
                # Formatar e deduplicar eventos consecutivos idênticos
                fmt_eventos = []
                eventos_raw_list = []
                last_ident = None
                for ev in conv_list:
                    data_f = ev.get('data_formatada', '')
                    ident = ev.get('evento', '')
                    cat = categorize_rd_event(ident)
                    clean_name = clean_rd_event_name(ident)
                    
                    # Desconsiderar tudo que for Checkout / Matrícula (conversão final de compra)
                    if cat == 'Checkout / Matrícula' or is_checkout_event(ident):
                        continue
                    
                    if (data_f, ident) == last_ident:
                        continue
                    last_ident = (data_f, ident)
                    
                    fmt_eventos.append(f"<span style='color:var(--muted)'>{data_f}</span> &mdash; <b>{clean_name}</b>")
                    eventos_raw_list.append({
                        'data': data_f,
                        'evento_raw': ident,
                        'evento_clean': clean_name,
                        'categoria': cat
                    })
                
                # Calcular dias de maturação com precisão (Data Matrícula - 1ª Conversão RD Pré-Matrícula)
                dias_maturacao = ''
                dt_primeira_real = ast.get('dt_primeira')
                if eventos_raw_list:
                    dt_primeira_real = eventos_raw_list[0].get('data') or ast.get('dt_primeira')
                else:
                    dt_primeira_real = '—'
                
                try:
                    dt_insc_raw = s.get('data_insc') or s.get('data_inscricao') or s.get('inscricao')
                    if dt_insc_raw and dt_primeira_real and dt_primeira_real not in ('?', '—', '-'):
                        d_insc = pd.to_datetime(dt_insc_raw, dayfirst=True)
                        d_pri = pd.to_datetime(dt_primeira_real[:10], dayfirst=True)
                        diff = (d_insc.date() - d_pri.date()).days
                        if diff >= 0:
                            dias_maturacao = int(diff)
                except Exception as e_mat:
                    pass
                    
                s['rd_funnel'] = {
                    'origem': ast.get('origem_funil') or 'Desconhecido',
                    'conversoes': ast.get('total_conversoes', 0),
                    'conversoes_antes': len(eventos_raw_list),
                    'scoring': ast.get('score_interesse', 0),
                    'dias_venda': dias_maturacao,
                    'dt_primeira': dt_primeira_real,
                    'dt_ultima': ast.get('dt_ultima', '—'),
                    'eventos': fmt_eventos,
                    'eventos_detalhados': eventos_raw_list,
                    'fonte': 'API Oficial RD Station'
                }
            elif em in rd_events_map:
                rd_copy = dict(rd_events_map[em])
                if not rd_copy.get('dias_venda'):
                    try:
                        dt_insc_raw = s.get('data_insc') or s.get('data_inscricao') or s.get('inscricao')
                        dt_pri_raw = rd_copy.get('dt_primeira')
                        if dt_insc_raw and dt_pri_raw and dt_pri_raw not in ('—', '?', '-'):
                            d_insc = pd.to_datetime(dt_insc_raw, dayfirst=True)
                            d_pri = pd.to_datetime(dt_pri_raw[:10], dayfirst=True)
                            diff = (d_insc.date() - d_pri.date()).days
                            if diff >= 0:
                                rd_copy['dias_venda'] = int(diff)
                    except Exception:
                        pass
                s['rd_funnel'] = rd_copy
        
        funil_data = {
            'kpis': funil_kpis,
            'origens_all': origens_all,
            'origens_alunos': origens_alunos,
            'tempo_conv': {
                'histograma': hist_conv,
                'media': media_conv,
                'mediana': mediana_conv,
                'total_amostras': len(tempo_conv),
            },
            'eventos_alunos': [{'cat': k, 'n': v} for k, v in top_eventos_alunos],
            'eventos_nao_alunos': [{'cat': k, 'n': v} for k, v in top_eventos_nao],
            'scoring': leads_scoring[:200],  # Top 200 leads
            'mat_counts': mat_counts,
            'captacao_timeline': captacao_timeline,
        }
    
    # ============================================
    # VINDI FINANCEIRO
    # ============================================
    vindi_matched = 0
    financeiro_data = {}
    try:
        from vindi_service import get_vindi_data
        vindi_res = get_vindi_data(force_reload=False)
        vindi_map = vindi_res.get('data', {}) if isinstance(vindi_res, dict) and 'data' in vindi_res else vindi_res
        financeiro_data = vindi_res.get('financeiro', {}) if isinstance(vindi_res, dict) else {}
        if isinstance(vindi_res, dict):
            financeiro_data['subscriptions'] = vindi_res.get('subscriptions', [])
            financeiro_data['data'] = vindi_res.get('data', {})
        
        # Link Vindi to existing students (matching by email + course first)
        for s in students:
            em = str(s.get('email', '')).lower().strip()
            c_s = str(s.get('curso', '')).strip()
            key_ec = f"{em}___{c_s}"
            if key_ec in vindi_map:
                s['vindi'] = vindi_map[key_ec]
                vindi_matched += 1
            elif em in vindi_map:
                s['vindi'] = vindi_map[em]
                vindi_matched += 1
            else:
                s['vindi'] = None
                
        # Add Vindi subscribers who don't have access logs yet (as inferred students)
        existing_vindi_keys = set((str(s.get('email', '')).lower().strip(), str(s.get('curso', '')).strip()) for s in students if s.get('email'))
        for em, v_obj in vindi_map.items():
            if '___' in em: continue # Skip composite dictionary keys
            em_clean = str(em).lower().strip()
            if not em_clean or not isinstance(v_obj, dict): continue
            
            # Cadastro != Matrícula: se foi cancelado sem pagamento e sem acesso, descarta
            v_sub_st = str(v_obj.get('status_assinatura', '')).lower()
            v_fin_st = str(v_obj.get('status_financeiro', '')).lower()
            fats = v_obj.get('faturas', [])
            has_paid = any(f.get('status') in ['paid', 'pago'] for f in fats)
            if v_sub_st in ['canceled', 'inactive'] and v_fin_st == 'cancelado' and not has_paid:
                continue
            
            c_inferido = v_obj.get('curso') or "PLATAFORMA GERAL"
            c_orig = "Plano Vindi"
            if c_inferido == "PLATAFORMA GERAL" and 'rd_course_hints' in locals() and em_clean in rd_course_hints:
                c_inferido = rd_course_hints[em_clean]
                c_orig = "RD Station"
                
            c_inferido = canonicalize_curso(c_inferido, em_clean)
            pair_key = (em_clean, c_inferido)
            if pair_key not in existing_vindi_keys:
                existing_vindi_keys.add(pair_key)
                # Check if this Vindi subscriber has Cativa account / login
                st_plat = "Academy"
                st_nome = v_obj.get('customer_name') or 'Aluno Vindi'
                st_tel = ""
                st_acessou = False
                st_events = []
                st_last_fmt = None
                st_dias_inativo = None
                
                if em_clean in cativa_users_meta:
                    c_meta = cativa_users_meta[em_clean]
                    st_plat = "Cativa"
                    st_tel = normalize_phone(c_meta.get('phone', ''))
                    if c_meta.get('first_name') or c_meta.get('last_name'):
                        c_fullname = f"{c_meta.get('first_name', '')} {c_meta.get('last_name', '')}".strip()
                        if c_fullname: st_nome = c_fullname
                    
                    last_login_s = c_meta.get('last_login_at')
                    if last_login_s:
                        dt_c_login = pd.to_datetime(last_login_s[:19], errors='coerce')
                        if pd.notnull(dt_c_login):
                            dt_c_login = dt_c_login - pd.Timedelta(hours=3) # Cativa API retorna em UTC, converter para Horario de Brasilia (UTC-3)
                        if pd.notna(dt_c_login):
                            st_acessou = True
                            st_events.append({
                                "d": dt_c_login.strftime("%d/%m/%Y %H:%M"),
                                "acao": "LOGIN WEB (Cativa)",
                                "cat": "login",
                                "item": "Plataforma Cativa Digital",
                                "mod": ""
                            })
                            st_last_fmt = dt_c_login.strftime("%d/%m/%Y")
                            st_dias_inativo = max(0, (hoje - dt_c_login.date()).days)

                new_v_st = {
                    "email": em_clean,
                    "nome": st_nome,
                    "curso": c_inferido,
                    "curso_inferido": True,
                    "curso_origem": c_orig,
                    "telefone": st_tel,
                    "acessou": st_acessou,
                    "data_insc": None,
                    "data_inscricao": None,
                    "inscricao": None,
                    "dias_desde_insc": 0,
                    "plataforma": st_plat,
                    "id_aluno": str(v_obj.get('customer_id', '')),
                    "events": st_events,
                    "last_fmt": st_last_fmt,
                    "dias_inativo": st_dias_inativo,
                    "vindi": v_obj,
                    "asaas": None
                }
                if 'rd_events_map' in locals() and em_clean in rd_events_map:
                    new_v_st['rd_funnel'] = dict(rd_events_map[em_clean])
                students.append(new_v_st)
                vindi_matched += 1
                
        print(f"[VINDI] {vindi_matched} estudantes vinculados com dados financeiros da Vindi.")
    except Exception as e_vindi:
        print(f"[VINDI] Erro ao integrar Vindi no gerador: {e_vindi}")
        for s in students:
            s['vindi'] = None

    # ============================================
    # ASAAS FINANCEIRO — 100% via API (Asaas + Academy API)
    # ============================================
    asaas_matched = 0
    asaas_financeiro = {}
    try:
        from asaas_service import get_asaas_data
        asaas_res = get_asaas_data(force_reload=True)
        asaas_map = asaas_res.get('data', {}) if isinstance(asaas_res, dict) else {}
        asaas_financeiro = asaas_res.get('financeiro', {}) if isinstance(asaas_res, dict) else {}
        if isinstance(asaas_res, dict):
            asaas_financeiro['data'] = asaas_res.get('data', {})

        # 1. Vincular aos estudantes existentes por e-mail (resolvido 100% pela API) ou ID
        for s in students:
            em = str(s.get('email', '')).lower().strip()
            aluno_id = str(s.get('id_aluno', '')).strip()
            matched = False
            if em and em in asaas_map:
                s['asaas'] = asaas_map[em]
                asaas_matched += 1
                matched = True
            elif aluno_id and aluno_id in asaas_map:
                s['asaas'] = asaas_map[aluno_id]
                asaas_matched += 1
                matched = True
            if not matched:
                s['asaas'] = None

        # 2. Adicionar alunos do Asaas/Academy API que ainda não estavam na lista de estudantes
        existing_emails = set(str(s.get('email', '')).lower().strip() for s in students if s.get('email'))
        added_from_api = 0
        def _infer_curso_from_asaas(asaas_st, email):
            """Tenta resolver o curso do aluno Asaas usando student_course_map, RD Station ou descrição da fatura.
            Retorna: (curso_nome, is_inferred, origem_str)"""
            if email in student_course_map and student_course_map[email] != normalize_curso('PLATAFORMA GERAL'):
                return student_course_map[email], False, "Oficial"
            
            if 'rd_course_hints' in locals() and email in rd_course_hints:
                return rd_course_hints[email], True, "RD Station"
            
            faturas = asaas_st.get('faturas', [])
            desc_text = ' '.join(str(ft.get('description', ft.get('descricao', ''))) for ft in faturas)
            c_res = canonicalize_curso(desc_text, email)
            if c_res and c_res != normalize_curso('PLATAFORMA GERAL'):
                return c_res, True, "Fatura Asaas"
            
            return normalize_curso('PLATAFORMA GERAL'), False, "Geral" 

        for key, asaas_st in asaas_map.items():
            if not isinstance(asaas_st, dict): continue
            # Só considera como matriculado vindo da API se tiver ao menos um pagamento
            if (asaas_st.get('total_pago') or 0) <= 0:
                continue
            st_email = (asaas_st.get('customer_email') or '').lower().strip()
            if st_email and st_email not in existing_emails:
                existing_emails.add(st_email)
                curso_resolved, curso_inferido, curso_origem = _infer_curso_from_asaas(asaas_st, st_email)
                new_st = {
                    "email": st_email,
                    "nome": asaas_st.get('customer_name') or 'Aluno Academy',
                    "curso": curso_resolved,
                    "curso_inferido": curso_inferido,
                    "curso_origem": curso_origem,
                    "telefone": "",
                    "acessou": False,
                    "data_insc": None,
                    "data_inscricao": None,
                    "inscricao": None,
                    "dias_desde_insc": 0,
                    "plataforma": "Academy",
                    "id_aluno": str(asaas_st.get('aluno_id_extref', '')),
                    "events": [],
                    "vindi": None,
                    "asaas": asaas_st
                }
                if 'rd_events_map' in locals() and st_email in rd_events_map:
                    new_st['rd_funnel'] = dict(rd_events_map[st_email])
                students.append(new_st)
                if curso_resolved != "PLATAFORMA GERAL":
                    tag_info = f" (INFERIDO via {curso_origem})" if curso_inferido else ""
                    print(f"  [ASAAS] Curso resolvido para {st_email}: {curso_resolved}{tag_info}")
                added_from_api += 1
                asaas_matched += 1

        print(f"[ASAAS] {asaas_matched} estudantes vinculados 100% via API ({added_from_api} matriculados adicionados da API Academy).")
    except Exception as e_asaas:
        print(f"[ASAAS] Erro ao integrar Asaas no gerador: {e_asaas}")
        for s in students:
            s['asaas'] = None

    for s in students:
        s.setdefault('curso_inferido', False)
        s.setdefault('curso_origem', 'Oficial')

    # =========================================================================
    # REGRA DE NEGÓCIO DEFINITIVA: 
    # 1. Desconsiderar curso NUTRIFY CONNECT
    # 2. Desconsiderar e-mails @infectocast, @integralmedica, @nutrify
    # 3. Desconsiderar palavra 'teste' no nome ou e-mail
    # 4. Desconsiderar registros sem acesso (0 logins) e sem pagamento/contrato
    # =========================================================================
    def is_invalid_or_internal(email, nome='', curso=''):
        em = str(email or '').lower().strip()
        nm = str(nome or '').lower().strip()
        cr = str(curso or '').upper().strip()
        
        if 'NUTRIFY' in cr:
            return True
        if any(dom in em for dom in ['@infectocast', '@integralmedica', '@nutrify', '@vectorcomunica']):
            return True
        if 'teste' in em or 'teste' in nm:
            return True
        if any(x in em for x in ['gcotta29', 'j.o.s.e.r.a.n.d@gmail.com', 'email@email.com']):
            return True
        return False

    fin_emails = set()
    fin_names = set()
    if isinstance(financeiro_data, dict):
        for f in financeiro_data.get('faturas_tabela', []):
            em = str(f.get('email', '')).lower().strip()
            nm = str(f.get('aluno', '')).lower().strip()
            cr = str(f.get('curso', '')).upper().strip()
            if not is_invalid_or_internal(em, nm, cr):
                if em: fin_emails.add(em)
                if nm: fin_names.add(nm)

    if isinstance(asaas_financeiro, dict):
        for f in asaas_financeiro.get('faturas_tabela', []):
            em = str(f.get('email', '')).lower().strip()
            nm = str(f.get('aluno', '')).lower().strip()
            cr = str(f.get('curso', '')).upper().strip()
            if not is_invalid_or_internal(em, nm, cr):
                if em: fin_emails.add(em)
                if nm: fin_names.add(nm)

    matriculas_legitimas = []
    expurgados_count = 0
    for s in students:
        em = str(s.get('email', '')).lower().strip()
        nm = str(s.get('nome', '')).lower().strip()
        cr = str(s.get('curso', '')).upper().strip()
        
        # 1. Regra de exclusão de internos, testes e Nutrify Connect
        if is_invalid_or_internal(em, nm, cr):
            expurgados_count += 1
            continue
            
        acessou = bool(s.get('acessou', False))
        logins = int(s.get('logins', 0) or 0)
        has_access = (acessou and logins > 0)
        
        v = s.get('vindi') or {}
        a = s.get('asaas') or {}
        has_finance = bool(v or a or em in fin_emails or nm in fin_names)
        
        # 2. Regra de vínculo (tem acesso ou tem contrato/pagamento)
        if has_access or has_finance:
            matriculas_legitimas.append(s)
        else:
            expurgados_count += 1

    print(f"[MATRÍCULAS] Base final oficial sanitizada: {len(matriculas_legitimas)} matrículas ({expurgados_count} desconsiderados por serem teste/internos/Nutrify Connect/sem vínculo).")
    students = matriculas_legitimas

    now_dt = datetime.datetime.now()
    data = {
        "meta": {
            "generated": now_dt.strftime("%d/%m/%Y"),
            "updated_at": now_dt.strftime("%d/%m/%Y %H:%M:%S"),
            "updated_iso": now_dt.isoformat(),
            "hora_atualizacao": now_dt.strftime("%H:%M"),
            "report_start": df_log['Data log'].min().strftime("%d/%m/%Y"),
            "date_max": df_log['Data log'].max().strftime("%d/%m/%Y"),
            "ref_date": hoje.strftime("%d/%m/%Y")
        },
        "curriculum": final_curriculum,
        "students": students,
        "mensagens_recentes": mensagens_recentes,
        "funil": funil_data,
        "survival": [{"t": i, "frac": 100 - i} for i in range(50)],
        "wa_chats": wa_chats,
        "financeiro": financeiro_data,
        "financeiro_asaas": asaas_financeiro
    }

    # Otimização de alta performance do payload JSON
    data = optimize_payload_for_dashboard(data)

    pre, post = prepare_template(template_path)
    if pre == template_path:
        print("Erro: não encontrou DATA no template.")
        return
        
    json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    
    final_html = pre + "const DATA = " + json_str + post
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(base_dir, 'dashboard_gerado.html')
    index_path = os.path.join(base_dir, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f_idx:
        f_idx.write(final_html)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    print(f"Relatório gerado em: {out_path}")

if __name__ == "__main__":
    main()
