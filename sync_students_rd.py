import urllib.request
import urllib.error
import json
import os
import time
import pandas as pd
import sys

sys.path.append(r'C:\Users\DELL\Desktop\Dash_InfectoCast')
from rd_service import get_access_token

CACHE_FILE = r'C:\Users\DELL\Desktop\Dash_InfectoCast\rd_students_cache.json'

def sync_students_rd():
    token = get_access_token()
    df_insc = pd.read_excel(r'C:\Users\DELL\Desktop\Acompanhamento de acessos\BD\Inscrições.xlsx')
    
    # Mapear data de inscrição por email
    insc_map = {}
    for _, row in df_insc.dropna(subset=['E-mail']).iterrows():
        em = str(row['E-mail']).lower().strip()
        dt = row.get('Data Inscrição')
        if pd.notna(dt):
            insc_map[em] = pd.to_datetime(dt, dayfirst=True)

    unique_emails = list(insc_map.keys())
    print(f"Total de {len(unique_emails)} alunos a verificar.")
    
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    results = dict(cache)
    total = len(unique_emails)
    
    for i, em in enumerate(unique_emails, 1):
        # Se já tiver obtido com sucesso anteriormente, não precisa bater na API de novo
        if em in results and results[em].get('encontrado_rd') is True:
            continue
            
        print(f"[{i}/{total}] Consultando {em}...", end=' ', flush=True)
        
        attempts = 0
        success = False
        while attempts < 3 and not success:
            attempts += 1
            url_contact = f'https://api.rd.services/platform/contacts/email:{em}'
            req = urllib.request.Request(url_contact, headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
            
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    contact = json.loads(resp.read().decode('utf-8'))
                    uuid = contact.get('uuid')
                    
                    time.sleep(0.3)
                    # Funil
                    funnel = {}
                    try:
                        f_url = f'https://api.rd.services/platform/contacts/{uuid}/funnels/default'
                        f_req = urllib.request.Request(f_url, headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
                        with urllib.request.urlopen(f_req, timeout=10) as f_resp:
                            funnel = json.loads(f_resp.read().decode('utf-8'))
                    except Exception:
                        pass
                    
                    time.sleep(0.3)
                    # Conversões
                    events = []
                    try:
                        e_url = f'https://api.rd.services/platform/contacts/{uuid}/events?event_type=CONVERSION'
                        e_req = urllib.request.Request(e_url, headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
                        with urllib.request.urlopen(e_req, timeout=10) as e_resp:
                            events = json.loads(e_resp.read().decode('utf-8'))
                    except Exception:
                        pass
                    
                    # Processar eventos
                    insc_date = insc_map.get(em)
                    conversoes_antes = []
                    todas_conversoes = []
                    
                    events.sort(key=lambda x: x.get('event_timestamp', ''))
                    
                    for ev in events:
                        ts_str = ev.get('event_timestamp', '')
                        ident = ev.get('event_identifier', '')
                        payload = ev.get('payload', {})
                        ev_date = pd.to_datetime(ts_str[:19]) if ts_str else None
                        
                        item = {
                            'timestamp': ts_str[:19],
                            'data_formatada': ev_date.strftime('%d/%m/%Y %H:%M') if ev_date else '',
                            'evento': ident,
                            'origem': payload.get('conversion_origin', {}).get('source', '') if isinstance(payload.get('conversion_origin'), dict) else ''
                        }
                        todas_conversoes.append(item)
                        
                        # Conversões que antecederam a inscrição
                        if insc_date and ev_date and ev_date <= insc_date:
                            conversoes_antes.append(item)
                        elif not insc_date:
                            conversoes_antes.append(item)
                            
                    results[em] = {
                        'encontrado_rd': True,
                        'uuid': uuid,
                        'nome_rd': contact.get('name'),
                        'telefone_rd': contact.get('mobile_phone'),
                        'tags': contact.get('tags', []),
                        'origem_funil': funnel.get('origin', 'Desconhecido'),
                        'estagio': funnel.get('lifecycle_stage', 'Lead'),
                        'score_interesse': funnel.get('interest', 0),
                        'score_perfil': funnel.get('fit', 0),
                        'total_conversoes': len(events),
                        'dt_primeira': todas_conversoes[0]['data_formatada'] if todas_conversoes else '—',
                        'dt_ultima': todas_conversoes[-1]['data_formatada'] if todas_conversoes else '—',
                        'conversoes_todas': todas_conversoes,
                        'conversoes_antes_matricula': conversoes_antes
                    }
                    print(f"OK ({len(events)} conversões, {len(conversoes_antes)} antes da matrícula)")
                    success = True
                    
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print("Não encontrado no RD")
                    results[em] = {'encontrado_rd': False}
                    success = True
                elif e.code == 429:
                    print("Rate limit (429), aguardando 6s...")
                    time.sleep(6)
                elif e.code == 401:
                    print("Token expirado, renovando...")
                    token = get_access_token()
                    time.sleep(2)
                else:
                    print(f"Erro {e.code}")
                    results[em] = {'encontrado_rd': False, 'error': e.code}
                    success = True
            except Exception as e:
                print(f"Erro: {e}")
                results[em] = {'encontrado_rd': False, 'error': str(e)}
                success = True
                
            time.sleep(0.3)
            
    # Salvar cache atualizado
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    found_total = sum(1 for v in results.values() if v.get('encontrado_rd') is True)
    print(f"\nFinalizado! {found_total} de {total} alunos identificados no RD Station.")
    return results

if __name__ == '__main__':
    sync_students_rd()
