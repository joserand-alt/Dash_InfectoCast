import urllib.request
import ssl
import json
import os
import unicodedata

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb3NlcmFuZGNvc3RhIiwianRpIjoiYTdiMzg2Y2MtYTYwYi00NGRmLWQ0NWYtMDhkZTEwYmRmODVkIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9yb2xlIjoiQWRtaW4iLCJodHRwOi8vcGxhaC5zb2NpYWwvY2xhaW1zL2N1c3RvbWVyL2lkIjoiZjA5NGYxZTctZWY5MC00Mzc3LTlkYjYtMDhkY2E3NjQ4Y2IzIiwiaHR0cDovL3BsYWguc29jaWFsL2NsYWltcy9jdXN0b21lci9uYW1lIjoiaW5mZWN0b3hwZXJ0IiwiaHR0cDovL3BsYWguc29jaWFsL2NsYWltcy91c2VyL2VtYWlsQ29uZmlybWVkIjoidHJ1ZSIsImh0dHA6Ly9wbGFoLnNvY2lhbC9jbGFpbXMvYXBpL2tleSI6ImYzOWExMTU5LTM3NDMtNGEwMi1hNmI1LTBmMzU1OWU4NGE5MSIsImh0dHBzOi8vY2F0aXZhLmRpZ2l0YWwvY2xhaW1zL3VzZXIvYmFkZ2UiOiI1ZTM4YTI5YS01M2I3LTQyNTEtOWM1ZS0wOGRlMjc1ODg0OGMiLCJleHAiOjIxMDQ0MTc3NjIsImlzcyI6InBsYWgtYXBpIiwiYXVkIjoicGxhaC1hcGkifQ.FuDmRu_dzMZfw6bmeJlhm53FqJuZkipJP_z77Dwy0qI"
CUSTOMER = "infectoxpert"
BASE_URL = "https://backoffice.cativalab.digital/api"
CACHE_FILE = r"C:\Users\DELL\Desktop\Dash_InfectoCast\cativa_cache.json"

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

def fetch_all_cativa_data(force_refresh=False):
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[CATIVA CACHE] Carregados {len(data.get('students', []))} alunos da Cativa do cache local.")
                return data
        except Exception as e:
            print(f"[CATIVA CACHE] Erro lendo cache: {e}. Requisitando API...")

    print("[CATIVA API] Buscando relatório completo de aulas assistidas...")
    page_size = 100
    page_num = 1
    all_students_report = []

    while True:
        url = f"{BASE_URL}/course/lessons-watched-report?pageSize={page_size}&pageNumber={page_num}"
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
                js = json.loads(resp.read().decode('utf-8'))
                items = js.get('items', [])
                all_students_report.extend(items)
                total = js.get('total', 0)
                print(f"  Página {page_num}: {len(items)} alunos carregados (total acumulado: {len(all_students_report)}/{total})")
                if len(all_students_report) >= total or not items:
                    break
                page_num += 1
        except Exception as e:
            print(f"[CATIVA API] Erro na página {page_num}: {e}")
            break

    # Also fetch users for phone numbers and last login
    print("[CATIVA API] Buscando cadastro de usuários...")
    users_page = 1
    users_dict = {}
    while True:
        u_url = f"{BASE_URL}/user?pageNumber={users_page}&pageSize=100"
        req = urllib.request.Request(u_url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
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
            print(f"[CATIVA API] Erro carregando usuários página {users_page}: {e}")
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

if __name__ == '__main__':
    data = fetch_all_cativa_data(force_refresh=True)
    print(f"\nResumo:")
    print(f"Total alunos com aulas na Cativa: {len(data['students'])}")
    print(f"Total cadastros com metadados: {len(data['users_metadata'])}")
