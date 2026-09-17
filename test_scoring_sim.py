
import pandas as pd

path = r'C:/Users/DELL/Desktop/Acompanhamento de acessos/BD/LogRD.csv'
df_rd = pd.read_csv(path, encoding='utf-8', low_memory=False)

hoje = pd.Timestamp.now()
dt_p_col = [c for c in df_rd.columns if 'primeira' in c.lower()][0]
dt_u_col = [c for c in df_rd.columns if 'ltima' in c.lower() and 'convers' in c.lower()][0]
ev_col_name = [c for c in df_rd.columns if 'eventos' in c.lower()][0]
conv_col = [c for c in df_rd.columns if 'convers' in c.lower() and 'total' in c.lower()][0]
score_col = [c for c in df_rd.columns if 'scoring - interesse' in c.lower()][0]

df_rd['dt_primeira'] = pd.to_datetime(df_rd[dt_p_col].str[:19], errors='coerce')
df_rd['dt_ultima'] = pd.to_datetime(df_rd[dt_u_col].str[:19], errors='coerce')

prof_cols_found = [c for c in df_rd.columns if any(k in c.lower() for k in ['profis', 'especial', 'cargo', 'sou:'])]

keywords_pos = ['pos-graduacao', 'pós', 'pos', 'ccih', 'infectoped', 'pediatria', 'ortoped', 'imuno', 'multi-r', 'biofilme', 'pga', 'enfermagem', 'especializacao', 'diploma', 'grade_pos']
icp_profs = ['enferm', 'medic', 'médic', 'farmac', 'infecto', 'biomed', 'bioméd', 'fisio', 'nutri', 'biolog', 'biólog']

results = []

for _, row in df_rd.iterrows():
    conversoes = row[conv_col] if pd.notna(row[conv_col]) else 0
    scoring_rd = row[score_col] if pd.notna(row[score_col]) else 0
    
    dias_desde = 0
    if pd.notna(row['dt_primeira']):
        dias_desde = (hoje - row['dt_primeira']).days
        
    dias_ultima = 9999
    if pd.notna(row['dt_ultima']):
        dias_ultima = (hoje - row['dt_ultima']).days

    evs_str = str(row[ev_col_name]) if ev_col_name else ''
    ev_list_raw = [e.strip() for e in evs_str.split('/') if e.strip()] if evs_str != 'nan' else []
    ev_list = []
    for e in ev_list_raw:
        e_low = e.lower().strip()
        if e_low == '26': continue
        if not any(x in e_low for x in ['pago', 'pendente', 'recorrencia', 'marco', '[pós]', '[pos]', 'aluno']):
            ev_list.append(e)
    ev_list = list(dict.fromkeys(ev_list))

    tags_lower = str(row.get('Tags', '')).lower()
    evs_text = ' '.join(ev_list).lower() + ' ' + tags_lower

    tem_pos = any(k in evs_text for k in keywords_pos)
    tem_lista_espera = any('lista-espera' in e.lower() or 'espera' in e.lower() for e in ev_list)

    profs = []
    for col in prof_cols_found:
        if col in row and pd.notna(row[col]):
            val = str(row[col]).strip()
            if val and val.lower() not in [p.lower() for p in profs] and val.lower() not in ['outro', 'outros', 'nenhuma', 'nd', 'n/a', 'nenhum']:
                profs.append(val)
    profissao_str = ' | '.join(profs) if profs else '-'
    tem_icp_prof = any(p in profissao_str.lower() for p in icp_profs)

    score = 0
    # 1. Volume de conversões (máx 30 pts)
    score += min(30, (conversoes / 8) * 30)

    # 2. Maturidade / Recência (máx 20 pts)
    if (dias_desde > 180 and (dias_ultima <= 120 or conversoes >= 4)) or (30 <= dias_desde <= 180):
        score += 20
    else:
        score += 10

    # 3. Interesse temático / Pós / Cursos (máx 25 pts)
    if tem_pos:
        score += 25

    # 4. Lista de Espera (máx 10 pts)
    if tem_lista_espera:
        score += 10

    # 5. Profissão / Perfil ICP (máx 15 pts)
    if tem_icp_prof:
        score += 15

    # 6. Scoring RD (bônus máx 5 pts)
    score += min(5, (scoring_rd / 100) * 5)

    score = min(100, round(score))

    if score >= 70:
        maturidade = 'Pronto'
    elif score >= 50:
        maturidade = 'Quente'
    elif score >= 25:
        maturidade = 'Morno'
    else:
        maturidade = 'Frio'

    results.append({
        'email': str(row['Email']),
        'nome': str(row['Nome']),
        'conversoes': conversoes,
        'profissao': profissao_str,
        'tem_pos': tem_pos,
        'score': score,
        'maturidade': maturidade
    })

res_df = pd.DataFrame(results)
print('Distribuicao de Maturidade:')
print(res_df['maturidade'].value_counts())

vivian_res = res_df[res_df['email'].str.lower() == 'vivianvidal01@gmail.com']
print('
=== Vivian Vidal com nova regra ===')
print(vivian_res.to_dict(orient='records'))
