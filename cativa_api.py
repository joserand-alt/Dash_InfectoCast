import urllib.request
import ssl
import json
import os
import time
import unicodedata
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb3NlcmFuZGNvc3RhIiwianRpIjoiYTdiMzg2Y2MtYTYwYi00NGRmLWQ0NWYtMDhkZTEwYmRmODVkIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQWRtaW4iLCJodHRwOi8vcGxhaC5zb2NpYWwvY2xhaW1zL2N1c3RvbWVyL2lkIjoiZjA5NGYxZTctZWY5MC00Mzc3LTlkYjYtMDhkY2E3NjQ4Y2IzIiwiaHR0cDovL3BsYWguc29jaWFsL2NsYWltcy9jdXN0b21lci9uYW1lIjoiaW5mZWN0b3hwZXJ0IiwiaHR0cDovL3BsYWguc29jaWFsL2NsYWltcy91c2VyL2VtYWlsQ29uZmlybWVkIjoidHJ1ZSIsImh0dHA6Ly9wbGFoLnNvY2lhbC9jbGFpbXMvYXBpL2tleSI6ImYzOWExMTU5LTM3NDMtNGEwMi1hNmI1LTBmMzU1OWU4NGE5MSIsImh0dHBzOi8vY2F0aXZhLmRpZ2l0YWwvY2xhaW1zL3VzZXIvYmFkZ2UiOiI1ZTM4YTI5YS01M2I3LTQyNTEtOWM1ZS0wOGRlMjc1ODg0OGMiLCJleHAiOjIxMDQ0MTc3NjIsImlzcyI6InBsYWgtYXBpIiwiYXVkIjoicGxhaC1hcGkifQ.FuDmRu_dzMZfw6bmeJlhm53FqJuZkipJP_z77Dwy0qI"
CUSTOMER = "infectoxpert"
BASE_URL = "https://backoffice.cativalab.digital/api"
CACHE_FILE = r"C:\Users\DELL\Desktop\Dash_InfectoCast\cativa_cache.json"
CURRICULUM_CACHE_FILE = r"C:\Users\DELL\Desktop\Dash_InfectoCast\cativa_curriculum_cache.json"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Plah-Customer": CUSTOMER,
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
}

def normalize_text(s):
    if not s: return ""
    s = str(s).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def parse_utc_to_brt(dt_str):
    if not dt_str:
        return pd.NaT
    try:
        dt = pd.to_datetime(dt_str, errors='coerce')
        if pd.isna(dt):
            return pd.NaT
        if dt.tzinfo is None:
            dt = dt.tz_localize('UTC')
        return dt.tz_convert('America/Sao_Paulo').tz_localize(None)
    except Exception:
        return pd.to_datetime(dt_str, errors='coerce')

def canonicalize_cativa_curso(cname):
    norm = normalize_text(cname)
    if 'CCIH' in norm:
        return 'POS-GRADUACAO EM PREVENCAO E CONTROLE DE INFECCAO HOSPITALAR (CCIH)'
    if 'IMUNO' in norm:
        return 'POS-GRADUACAO EM INFECTOLOGIA DO PACIENTE IMUNODEPRIMIDO'
    if 'ORTO' in norm or 'PELE' in norm or 'PARTES MOLES' in norm:
        return 'POS-GRADUACAO EM INFECCOES ORTOPEDICAS E DE PELE E PARTES MOLES'
    if 'PED' in norm:
        return 'POS-GRADUACAO EM INFECTOPEDIATRIA'
    if 'FUNGO' in norm or 'ANTIFUNGICO' in norm:
        return 'DO FUNGO AO ANTIFUNGICO'
    if 'MULTI-R' in norm or 'MULTIR' in norm or 'MULTI R' in norm:
        return 'JORNADA MULTI-R'
    if 'SOS' in norm or 'ANTIBIOTICO' in norm:
        return 'S.O.S ANTIBIOTICO'
    return norm

def fetch_cativa_courses_api():
    """Busca cursos cadastrados diretamente na API Cativa"""
    url = f"{BASE_URL}/course?pageNumber=1&pageSize=50"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('items', [])
    except Exception as e:
        print(f"[CATIVA API] Erro ao buscar cursos da API: {e}")
        return []

def fetch_cativa_course_modules(course_id):
    """Busca módulos de um curso diretamente na API Cativa"""
    url = f"{BASE_URL}/course/{course_id}/modules"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return []

def fetch_all_cativa_data(force_refresh=False):
    cached_data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
        except Exception:
            pass

    if not force_refresh and cached_data and cached_data.get('students'):
        st_count = len(cached_data.get('students', []))
        print(f"[CATIVA CACHE] Carregados {st_count} alunos da Cativa do cache local.")
        return cached_data

    print("[CATIVA API] Buscando relatorio completo de telemetria e aulas assistidas via API...")
    page_size = 25
    all_students_report = []

    def fetch_page(p):
        url = f"{BASE_URL}/course/lessons-watched-report?pageSize={page_size}&pageNumber={p}"
        req = urllib.request.Request(url, headers=HEADERS)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                    js = json.loads(resp.read().decode('utf-8'))
                    return p, js.get('items', []), js.get('total', 0)
            except Exception as e:
                if attempt == 2:
                    print(f"  [CATIVA API] Falha na pagina {p}: {e}")
                    return p, [], 0
                time.sleep(1)

    p1, items1, total = fetch_page(1)
    if items1:
        all_students_report.extend(items1)
        total_pages = (total + page_size - 1) // page_size
        print(f"  Pagina 1: {len(items1)}/{total} alunos (total paginas: {total_pages})")
        if total_pages > 1:
            with ThreadPoolExecutor(max_workers=5) as ex:
                results = list(ex.map(fetch_page, range(2, total_pages + 1)))
            for p, items, _ in sorted(results, key=lambda x: x[0]):
                all_students_report.extend(items)
        print(f"[CATIVA API] Total de {len(all_students_report)} alunos carregados com sucesso.")
    else:
        print("[CATIVA API] Aviso: Nao foi possivel carregar pagina 1 da API Cativa.")

    # Fallback if API returned fewer students than existing cache
    if len(all_students_report) < 100 and cached_data and len(cached_data.get('students', [])) > len(all_students_report):
        cached_count = len(cached_data['students'])
        print(f"[CATIVA API] Preservando {cached_count} alunos do cache anterior por seguranca.")
        all_students_report = cached_data['students']

    # Fetch users for phone numbers and last login
    print("[CATIVA API] Buscando cadastro de usuarios e ultimo login em tempo real...")
    users_dict = dict(cached_data.get('users_metadata', {}))
    users_page = 1
    while True:
        u_url = f"{BASE_URL}/user?pageNumber={users_page}&pageSize=100"
        req = urllib.request.Request(u_url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
                js = json.loads(resp.read().decode('utf-8'))
                items = js.get('items', [])
                for u in items:
                    em = str(u.get('email', '')).lower().strip()
                    if em:
                        users_dict[em] = {
                            'phone': u.get('phoneNumber'),
                            'created_at': u.get('createdAt'),
                            'last_login_at': u.get('lastLoginAt'),
                            'first_name': u.get('firstName'),
                            'last_name': u.get('lastName'),
                            'status': u.get('status')
                        }
                if not js.get('hasNextPage') or not items:
                    break
                users_page += 1
        except Exception as e:
            print(f"[CATIVA API] Erro carregando usuarios pagina {users_page}: {e}")
            break

    result = {
        'students': all_students_report,
        'users_metadata': users_dict
    }

    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False)
        print(f"[CATIVA API] Cache salvo com sucesso: {len(all_students_report)} alunos e {len(users_dict)} metadados cadastrais.")
    except Exception as e:
        print(f"[CATIVA API] Erro salvando cache: {e}")

    return result

def get_cativa_telemetry_logs():
    """
    Retorna todos os logs de telemetria de acesso e visualizações de aulas da Cativa Digital formatados para o DataFrame de logs.
    """
    data = fetch_all_cativa_data(force_refresh=False)
    students = data.get('students', [])
    users_meta = data.get('users_metadata', {})

    logs = []
    for s in students:
        em = str(s.get('email', '')).lower().strip()
        if not em or '@' not in em or em.endswith('@infectocast.com') or 'teste' in em:
            continue
            
        nome = str(s.get('fullName') or '').strip()
        meta = users_meta.get(em, {})
        if not nome:
            fn = meta.get('first_name', '')
            ln = meta.get('last_name', '')
            nome = f"{fn} {ln}".strip() or em

        # 1. Log de Último Login na Cativa
        last_login = meta.get('last_login_at')
        if last_login:
            logs.append({
                'Data log': parse_utc_to_brt(last_login),
                'Nome aluno': nome,
                'E-mail': em,
                'Ação / Local': 'Login Plataforma Cativa',
                'ID Item': 'LOGIN',
                'Desc. Item': 'Acesso à Plataforma Cativa Digital',
                'Modulo': 'Geral',
                'Curso': 'PLATAFORMA GERAL',
                'Plataforma': 'Cativa'
            })

        # 2. Telemetria de Cada Aula Assistida na Cativa
        for c in s.get('courses', []):
            c_name = canonicalize_cativa_curso(c.get('courseName', ''))
            for l in c.get('lessons', []):
                w_at = l.get('watchedAt')
                if w_at:
                    mod_name = str(l.get('moduleName') or 'Geral').strip()
                    les_name = str(l.get('lessonName') or 'Aula Cativa').strip()
                    les_id = str(l.get('lessonId') or '')
                    logs.append({
                        'Data log': parse_utc_to_brt(w_at),
                        'Nome aluno': nome,
                        'E-mail': em,
                        'Ação / Local': 'Assistiu Aula (Cativa)',
                        'ID Item': les_id,
                        'Desc. Item': les_name,
                        'Modulo': mod_name,
                        'Curso': c_name,
                        'Plataforma': 'Cativa'
                    })

    print(f"[CATIVA TELEMETRIA] Carregados {len(logs)} eventos de telemetria e aulas assistidas da Cativa Digital.")
    return logs

def get_cativa_curriculum():
    """
    Retorna a estrutura curricular completa de cursos, módulos e aulas hospedados na Cativa Digital.
    """
    data = fetch_all_cativa_data(force_refresh=False)
    students = data.get('students', [])

    curriculum = {}
    for s in students:
        for c in s.get('courses', []):
            c_raw = c.get('courseName', '')
            c_name = canonicalize_cativa_curso(c_raw)
            if not c_name: continue
            
            if c_name not in curriculum:
                curriculum[c_name] = {}
                
            for l in c.get('lessons', []):
                mod_name = str(l.get('moduleName') or 'Geral').strip()
                les_name = str(l.get('lessonName') or '').strip()
                les_id = l.get('lessonId')
                dur = l.get('duration', 0)
                
                if mod_name not in curriculum[c_name]:
                    curriculum[c_name][mod_name] = {}
                    
                if les_name and les_name not in curriculum[c_name][mod_name]:
                    curriculum[c_name][mod_name][les_name] = {
                        'id': les_id,
                        'duracao': dur
                    }

    formatted_curriculum = {}
    for c_name, mods in curriculum.items():
        formatted_curriculum[c_name] = []
        for m_idx, (m_name, aulas_dict) in enumerate(mods.items(), 1):
            aulas_list = []
            for a_idx, (a_name, a_info) in enumerate(aulas_dict.items(), 1):
                aulas_list.append({
                    'id': a_info.get('id'),
                    'nome': a_name,
                    'ordem': a_idx,
                    'duracao': a_info.get('duracao', 0),
                    'curriculo': True
                })
            formatted_curriculum[c_name].append({
                'id_modulo': f"CAT-MOD-{m_idx}",
                'modulo': m_name,
                'ordem': m_idx,
                'n_curric': len(aulas_list),
                'aulas': aulas_list
            })

    return formatted_curriculum

if __name__ == '__main__':
    logs = get_cativa_telemetry_logs()
    curric = get_cativa_curriculum()
    print(f"\nResumo Cativa:")
    print(f"Total Logs Telemetria: {len(logs)}")
    print(f"Total Cursos Curriculo Cativa: {len(curric)}")
    for c, mods in curric.items():
        print(f"  - {c}: {len(mods)} módulos")

