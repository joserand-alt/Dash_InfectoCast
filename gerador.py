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

def fetch_logs_from_api(df_insc):
    print("Buscando logs de uso via API InfectoCast Academy (substituindo planilha)...")
    token = 'idIsYOe8egEasc4xwhxmwu2uSZyWy3oEhWzE3kEHakhcPJzQpp7kGLmYrk7lcrMQ'
    students = df_insc[['ID Aluno', 'Aluno', 'E-mail']].dropna(subset=['ID Aluno']).drop_duplicates(subset=['ID Aluno'])

    def fetch_student_logs(row):
        id_aluno = int(row['ID Aluno'])
        email = str(row['E-mail']).strip()
        nome = str(row['Aluno']).strip()
        url = f'https://academy.infectocast.com.br/api/alunos/{id_aluno}/log'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
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


def categorize_rd_event(ev_name):
    low = ev_name.lower().strip()
    if any(x in low for x in ['ebook', 'e-book']): return 'E-book / Material'
    if any(x in low for x in ['jornada', 'live', 'infectoxpert', 'congresso', 'webinar', 'evento']): return 'Evento / Live'
    if any(x in low for x in ['fale-conosco', 'duvida', 'contato', 'form_3', 'fluentform']): return 'Fale Conosco / Contato'
    if any(x in low for x in ['lista-espera', 'lista de espera', 'pre-inscricao', 'pré-inscrição', 'grade_pos']): return 'Lista de Espera / Grade'
    if any(x in low for x in ['ex alunos', 'alunos infectoped', 'ex-alunos']): return 'Comunidade / Base Prévia'
    if any(x in low for x in ['pago', 'pendente', 'recorrencia', 'checkout', 'compra']): return 'Checkout / Matrícula'
    return 'Outras Ações'

def clean_rd_event_name(ev_name):
    low = ev_name.lower().strip()
    if 'fale-conosco' in low: return 'Fale Conosco (Dúvidas/Suporte)'
    if 'ebook doses' in low: return 'E-book: Doses de Antibióticos'
    if 'ebook pav' in low: return 'E-book: Prevenção de PAV'
    if 'jornada multi-r' in low: return 'Jornada Multi-R'
    if 'alunos infectoped' in low: return 'Comunidade Alunos Infectoped'
    if 'ex alunos fabrizio' in low: return 'Base Ex-alunos Dr. Fabrizio'
    if 'fluentform_3' in low: return 'Formulário de Interesse (Site)'
    if 'pos-graduacao-pediatria-pendente' in low: return 'Checkout Iniciado (Pós Pediatria)'
    if 'pos-graduacao-pediatria-pago' in low: return 'Pagamento Confirmado (Pós Pediatria)'
    if 'recorrencia-18-x-pendente' in low or 'recorrencia-18x-pendente' in low: return 'Checkout Recorrência 18x (Pendente)'
    if 'recorrencia-18-x-pago' in low: return 'Checkout Recorrência 18x (Aprovado)'
    if 'grade_pos_pediatria' in low: return 'Download da Grade Curricular'
    return ev_name.replace('---', ' - ').replace('__', ' ')

def main():
    inscricoes_path = r'C:\Users\DELL\Desktop\Acompanhamento de acessos\BD\Inscrições.xlsx'
    cursos_path = r'C:\Users\DELL\Desktop\Acompanhamento de acessos\BD\CURSOS.xlsx'
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.html')
    
    print("Carregando planilhas...")
    df_insc = pd.read_excel(inscricoes_path)
    df_log = fetch_logs_from_api(df_insc)
    xls_cursos = pd.ExcelFile(cursos_path)
    
    df_mods = xls_cursos.parse(1)
    df_aulas = xls_cursos.parse(2)
    
    df_insc['Data Inscrição'] = pd.to_datetime(df_insc['Data Inscrição'], format='%d/%m/%Y %H:%M', errors='coerce')
    
    hoje = df_log['Data log'].max().date() + datetime.timedelta(days=1)
    inscritos = df_insc['E-mail'].dropna().unique()
    
    mensagens_path = r'C:\Users\DELL\Desktop\Acompanhamento de acessos\BD\Registro de mensagens.xlsx'
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
        if pd.isna(name): return "SEM CURSO"
        name = str(name).strip().upper()
        return ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    
    def norm_title(s):
        if not s or pd.isna(s): return ''
        s = str(s).strip().upper()
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    # ============================================
    # BUILD CURRICULUM FROM API LOGS
    # ============================================
    def canonicalize_curso(turma):
        t_norm = norm_title(turma)
        if 'INFECTOPEDI' in t_norm:
            return normalize_curso('PÓS-GRADUAÇÃO EM INFECTOPEDIATRIA')
        if 'ORTO' in t_norm or 'PELE' in t_norm or 'PARTES MOLES' in t_norm:
            return normalize_curso('PÓS-GRADUAÇÃO EM INFECÇÕES ORTOPÉDICAS E DE PARTES MOLES')
        if 'CCIH' in t_norm or 'HOSPITALAR' in t_norm:
            if 'FARM' in t_norm:
                return normalize_curso('PÓS-GRADUAÇÃO EM PREVENÇÃO E CONTROLE DE INFECÇÃO HOSPITALAR (CCIH) - FARMÁCIA')
            elif 'ENF' in t_norm:
                return normalize_curso('PÓS-GRADUAÇÃO EM PREVENÇÃO E CONTROLE DE INFECÇÃO HOSPITALAR (CCIH) - ENFERMAGEM')
            else:
                return normalize_curso('PÓS-GRADUAÇÃO EM PREVENÇÃO E CONTROLE DE INFECÇÃO HOSPITALAR (CCIH)')
        if 'S.O.S' in t_norm or 'SOS' in t_norm or 'ANTIBIOTICO' in t_norm:
            return normalize_curso('S.O.S ANTIBIÓTICO')
        if 'FERRAMENTAS' in t_norm or 'QUALIDADE' in t_norm:
            return normalize_curso('FERRAMENTAS DE QUALIDADE')
        if 'INFECTOXPERT' in t_norm or 'EXPERT' in t_norm:
            return normalize_curso('INFECTOXPERT')
        return normalize_curso(turma)
    
    def get_core_subject(name):
        name = str(name).upper()
        if 'INFECTOPEDI' in name: return 'INFECTOPEDIATRIA'
        if 'ORTO' in name or 'PARTES MOLES' in name: return 'ORTOPEDIA'
        if 'CCIH' in name or 'HOSPITALAR' in name: return 'CCIH'
        if 'IMUNO' in name: return 'IMUNODEPRIMIDOS'
        if 'S.O.S' in name or 'ANTIBIOTICO' in name: return 'SOS'
        return name
    
    print("Montando grade curricular a partir dos logs da API...")
    
    student_course_map = {}
    
    pg_events = df_log[df_log['Ação / Local'] == 'PG INSCRIÇÃO TURMA']
    for _, row in pg_events.iterrows():
        email = str(row['E-mail']).strip()
        turma = str(row['ID Item'] or row['Desc. Item'] or '').strip()
        if turma and turma != 'nan' and email not in student_course_map:
            student_course_map[email] = canonicalize_curso(turma)
    
    # Second pass: infer from content for students without PG event
    for _, insc in df_insc.dropna(subset=['E-mail']).drop_duplicates(subset=['E-mail']).iterrows():
        email = str(insc['E-mail']).strip()
        if email in student_course_map:
            continue
        
        excel_curso = str(insc.get('CURSO', '')).strip()
        core_excel = get_core_subject(excel_curso)
        
        if core_excel == 'INFECTOPEDIATRIA':
            student_course_map[email] = normalize_curso('PÓS-GRADUAÇÃO EM INFECTOPEDIATRIA')
            continue
        elif core_excel == 'ORTOPEDIA':
            student_course_map[email] = normalize_curso('PÓS-GRADUAÇÃO EM INFECÇÕES ORTOPÉDICAS E DE PARTES MOLES')
            continue
        elif core_excel == 'CCIH':
            if 'FARM' in norm_title(excel_curso) or 'ENF' in norm_title(excel_curso):
                student_course_map[email] = canonicalize_curso(excel_curso)
            else:
                student_course_map[email] = normalize_curso('PÓS-GRADUAÇÃO EM PREVENÇÃO E CONTROLE DE INFECÇÃO HOSPITALAR (CCIH)')
            continue
        elif core_excel == 'IMUNODEPRIMIDOS':
            student_course_map[email] = normalize_curso('PÓS-GRADUAÇÃO EM INFECÇÕES EM IMUNODEPRIMIDOS')
            continue
        elif core_excel == 'SOS':
            student_course_map[email] = normalize_curso('S.O.S ANTIBIÓTICO')
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
        elif any(w in all_text for w in ['ANTIBIOTICO', 'S.O.S', 'ESBL', 'KPC', 'NDM', 'CRAB', 'PARC', 'MDR']):
            student_course_map[email] = normalize_curso('S.O.S ANTIBIÓTICO')
        elif any(w in all_text for w in ['FERRAMENTAS', 'ISHIKAWA', 'PARETO', 'PDCA', 'SIPOC', 'BRAINSTORMING', 'GEMBA']):
            student_course_map[email] = normalize_curso('FERRAMENTAS DE QUALIDADE')
        else:
            excel_curso = str(insc.get('CURSO', '')).strip()
            if excel_curso and excel_curso != 'nan':
                student_course_map[email] = canonicalize_curso(excel_curso)
            else:
                student_course_map[email] = normalize_curso('CURSO DESCONHECIDO')
    
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
        curso = student_course_map.get(email, normalize_curso('PLATAFORMA GERAL'))
        if curso not in course_lessons:
            course_lessons[curso] = {}
        n_key = norm_title(item)
        if n_key and n_key not in course_lessons[curso]:
            course_lessons[curso][n_key] = item
    
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
    # Create a mapping from lesson normalized name -> module name using CURSOS.xlsx
    lesson_to_module = {}
    mod_id_to_name = {}
    mod_name_to_curso = {}
    
    for _, row in df_mods.iterrows():
        m_curso = str(row.iloc[0]).strip()
        m_id = row.iloc[1]
        m_nome = str(row.iloc[3]).strip()
        mod_id_to_name[m_id] = m_nome
        mod_name_to_curso[m_nome] = canonicalize_curso(m_curso)
        
    for _, row in df_aulas.iterrows():
        m_id = row.iloc[1]
        a_nome = str(row.iloc[4])
        a_norm = norm_title(a_nome)
        if m_id in mod_id_to_name and a_norm:
            lesson_to_module[a_norm] = mod_id_to_name[m_id]
            
    final_curriculum = {}
    mod_map = {}  # module_id -> module_name (for backwards compat)
    lesson_id_counter = 900000  # synthetic IDs for API-derived lessons
    
    for curso, lessons_dict in course_lessons.items():
        modules_for_course = course_modules.get(curso, set())
        
        # We will create a dict mapping module_name -> list of lesson objects
        mod_dict = {}
        for mod_name in modules_for_course:
            mod_dict[mod_name] = []
            
        mod_dict["Aulas Adicionais"] = []
        
        for n_key, original_name in sorted(lessons_dict.items(), key=lambda x: x[1]):
            lesson_id_counter += 1
            lesson_obj = {
                "id": lesson_id_counter,
                "nome": original_name,
                "curriculo": True,
                "ordem": 0 # updated later
            }
            
            mapped_mod = lesson_to_module.get(n_key)
            
            # Check if mapped_mod belongs to the current course to avoid module bleeding
            if mapped_mod:
                mod_curso = mod_name_to_curso.get(mapped_mod, "")
                
                # Compare by Core Subject instead of strict prefix to allow Journal/Lives merging
                base_curso = get_core_subject(curso)
                base_mod_curso = get_core_subject(mod_curso) if mod_curso else ""
                
                if base_mod_curso and base_curso != base_mod_curso:
                    continue # Pertence a outra disciplina base (ex: Pele vs Pediatria), descarta.
                
                # Se for da mesma disciplina base, verificar se é Journal ou Lives para sobrescrever o módulo
                if 'JOURNAL' in mod_curso.upper():
                    mapped_mod = "Journal"
                elif 'LIVE' in mod_curso.upper():
                    mapped_mod = "Lives"
                
                # Se chegou aqui, ou é do curso correto, ou é de um módulo sem curso atrelado
                if mapped_mod not in mod_dict:
                    mod_dict[mapped_mod] = []
                mod_dict[mapped_mod].append(lesson_obj)
            else:
                # Aula órfã (não mapeada para nenhum módulo), vai para Aulas Adicionais
                mod_dict["Aulas Adicionais"].append(lesson_obj)
                
        # Transform into final list format
        mod_list = []
        for mod_name, aulas in mod_dict.items():
            if not aulas and mod_name == "Aulas Adicionais":
                continue # Pula se "Aulas Adicionais" for vazio
                
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
    wa_log_path = r'C:\Users\DELL\Desktop\Acompanhamento de acessos\BD\Log mensagems.csv'
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

    students = []
    
    unique_insc = df_insc.dropna(subset=['E-mail']).drop_duplicates(subset=['E-mail', 'CURSO'])
    
    for _, insc in unique_insc.iterrows():
        email = insc['E-mail']
        email_str = str(email).lower()
        if 'teste' in email_str or '@infectocast' in email_str or '@vectorcomunica' in email_str or 'gcotta29@gmail.com' in email_str or 'rand' in email_str:
            continue
            
        logs = df_log[df_log['E-mail'] == email]
        acessou = len(logs) > 0

        excel_d = insc['Data Inscrição'] if pd.notna(insc['Data Inscrição']) else None
        curso_aluno, dt_insc_aluno = get_student_course_and_date(email, logs, excel_d)
        
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
        
        telefone = str(insc['Telefone']).strip() if 'Telefone' in insc and pd.notna(insc['Telefone']) else ""
        if telefone.endswith('.0'): telefone = telefone[:-2]
        if telefone == 'nan': telefone = ""
        
        student_data = {
            "email": str(email),
            "nome": str(insc['Aluno']),
            "curso": curso_aluno,
            "telefone": telefone,
            "acessou": acessou,
            "data_insc": data_insc_fmt,
            "data_inscricao": data_insc_fmt,
            "inscricao": data_insc_fmt,
            "dias_desde_insc": dias_desde_insc
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
                "lag": (first_log.date() - insc['Data Inscrição'].date()).days if pd.notna(insc['Data Inscrição']) else 0,
                "last_fmt": last_log.strftime("%d/%m/%Y"),
                "events": [],
                "wa_dt_primeira": None,
                "wa_dt_ultima": None,
                "wa_total": 0
            })
            
            # WA Mapping for Student
            # Try to find their phone from insc dataframe
            phone1 = normalize_phone(insc.get('Telefone'))
            phone2 = normalize_phone(insc.get('Celular'))
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
        
    # ============================================
    # FUNIL DE LEADS — Processamento LogRD.csv
    # ============================================
    logrd_path = r'C:\Users\DELL\Desktop\Acompanhamento de acessos\BD\LogRD.csv'
    funil_data = {}
    
    if os.path.exists(logrd_path):
        df_rd = pd.read_csv(logrd_path, encoding='utf-8', low_memory=False)
        
        emails_inscritos_set = set(str(e).lower().strip() for e in df_insc['E-mail'].dropna().unique())
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
        for _, row in df_insc.dropna(subset=['E-mail']).iterrows():
            em = str(row['E-mail']).lower().strip()
            dt = row['Data Inscrição']
            if pd.notna(dt):
                if em not in insc_dates or dt < insc_dates[em]:
                    insc_dates[em] = dt
        
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
        for _, row in df_rd[~df_rd['e_aluno']].iterrows():
            conversoes = row['Total de conversões'] if pd.notna(row['Total de conversões']) else 0
            scoring_rd = row['Lead Scoring - Interesse'] if pd.notna(row['Lead Scoring - Interesse']) else 0
            
            # Dias desde primeira conversão
            dias_desde = 0
            if pd.notna(row['dt_primeira']):
                dias_desde = (pd.Timestamp(hoje) - row['dt_primeira']).days
            
            # Check events for pós-graduação mentions
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
                    
            tem_pos = any('pos-graduacao' in e.lower() or 'pós' in e.lower() for e in ev_list)
            tem_lista_espera = any('lista-espera' in e.lower() for e in ev_list)
            
            # Curso recomendado via Tags
            tags_lower = str(row['Tags']).lower()
            cursos_rec = []
            if '[ped]' in tags_lower: cursos_rec.append('Ped')
            if '[ccih]' in tags_lower: cursos_rec.append('CCIH')
            if '[imuno]' in tags_lower: cursos_rec.append('Imuno')
            if '[orto]' in tags_lower: cursos_rec.append('Orto')
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
            
            # Score calculation (0-100)
            score = 0
            score += min(35, (conversoes / 16) * 35)
            if 30 <= dias_desde <= 200:
                score += 20
            elif dias_desde > 200:
                score += 10
            score += min(15, (scoring_rd / 100) * 15)
            if tem_pos:
                score += 20
            if tem_lista_espera:
                score += 10
            
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
                    'estagio': row['Estágio no funil'],
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
            
        # Extract RD history for enrolled students to embed in their object
        rd_events_map = {}
        for _, row in df_rd[df_rd['e_aluno']].iterrows():
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
            
            dias_venda = ''
            if pd.notna(row['dt_primeira']) and pd.notna(row['dt_venda']):
                dias_venda = (row['dt_venda'] - row['dt_primeira']).days
                
            rd_events_map[row['email_lower']] = {
                'origem': str(row['Origem da primeira conversão']) if pd.notna(row['Origem da primeira conversão']) else '-',
                'conversoes': int(row['Total de conversões']) if pd.notna(row['Total de conversões']) else 0,
                'scoring': int(row['Lead Scoring - Interesse']) if pd.notna(row['Lead Scoring - Interesse']) else 0,
                'dias_venda': dias_venda,
                'dt_primeira': row['dt_primeira'].strftime('%d/%m/%Y') if pd.notna(row['dt_primeira']) else '—',
                'dt_ultima': row['dt_ultima'].strftime('%d/%m/%Y') if pd.notna(row['dt_ultima']) else '—',
                'eventos': ev_list
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
                
                # Calcular dias de maturação com precisão (Data Matrícula - 1ª Conversão RD)
                dias_maturacao = ''
                try:
                    dt_insc_raw = s.get('data_insc') or s.get('data_inscricao') or s.get('inscricao')
                    dt_pri_raw = ast.get('dt_primeira')
                    if dt_insc_raw and dt_pri_raw and dt_pri_raw != '—':
                        d_insc = pd.to_datetime(dt_insc_raw, dayfirst=True)
                        d_pri = pd.to_datetime(dt_pri_raw[:10], dayfirst=True)
                        diff = (d_insc.date() - d_pri.date()).days
                        if diff >= 0:
                            dias_maturacao = int(diff)
                except Exception as e_mat:
                    pass
                    
                s['rd_funnel'] = {
                    'origem': ast.get('origem_funil') or 'Desconhecido',
                    'conversoes': ast.get('total_conversoes', 0),
                    'conversoes_antes': len(conv_antes),
                    'scoring': ast.get('score_interesse', 0),
                    'dias_venda': dias_maturacao,
                    'dt_primeira': ast.get('dt_primeira', '—'),
                    'dt_ultima': ast.get('dt_ultima', '—'),
                    'eventos': fmt_eventos,
                    'eventos_detalhados': eventos_raw_list,
                    'fonte': 'API Oficial RD Station'
                }
            elif em in rd_events_map:
                s['rd_funnel'] = rd_events_map[em]
        
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
    
    data = {
        "meta": {
            "generated": datetime.date.today().strftime("%d/%m/%Y"),
            "report_start": df_log['Data log'].min().strftime("%d/%m/%Y"),
            "date_max": df_log['Data log'].max().strftime("%d/%m/%Y"),
            "ref_date": hoje.strftime("%d/%m/%Y")
        },
        "curriculum": final_curriculum,
        "students": students,
        "mensagens_recentes": mensagens_recentes,
        "funil": funil_data,
        "survival": [{"t": i, "frac": 100 - i} for i in range(50)],
        "wa_chats": wa_chats
    }

    pre, post = prepare_template(template_path)
    if pre == template_path:
        print("Erro: não encontrou DATA no template.")
        return
        
    json_str = json.dumps(data, ensure_ascii=False)
    
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
