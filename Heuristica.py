import os                            
import csv                           
import random                        
import copy                          
import time                          
import itertools                      
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import matplotlib.patches as patches
from matplotlib import rcParams
from datetime import datetime

INSTANCIAS = r"Instancias\Grupo2\Instancias_20v" 
NUM_REINICIOS = 5 
TIMEOUT = 3600  
RANDOM_SEED = 42 
random.seed(RANDOM_SEED)

CORES_PASTEL = {
    'azul_claro': '#AEC6CF',
    'azul_medio': '#9BB7D4', 
    'verde_claro': '#B5EAD7',
    'verde_medio': '#C1E1C1',
    'amarelo_claro': '#FDFD96',
    'laranja_claro': '#FFD8B1',
    'rosa_claro': '#FFB7B2',
    'roxo_claro': '#C9C9FF',
    'cinza_claro': '#E8E8E8',
    'salmao_claro': '#FF9AA2',
    'lavanda': '#C3B1E1',
    'menta': '#A2E4D2',
    'pessego': '#FFCC99',
    'lilas': '#D4B9DA',
    'azul_ceu': '#B2D4F0',
}

CORES_PASTEL_4 = [CORES_PASTEL['azul_claro'], CORES_PASTEL['verde_claro'], 
                  CORES_PASTEL['laranja_claro'], CORES_PASTEL['rosa_claro']]

CORES_PASTEL_6 = [CORES_PASTEL['azul_claro'], CORES_PASTEL['verde_claro'],
                  CORES_PASTEL['laranja_claro'], CORES_PASTEL['rosa_claro'],
                  CORES_PASTEL['roxo_claro'], CORES_PASTEL['amarelo_claro']]

CORES_PASTEL_8 = [CORES_PASTEL['azul_claro'], CORES_PASTEL['verde_claro'],
                  CORES_PASTEL['laranja_claro'], CORES_PASTEL['rosa_claro'],
                  CORES_PASTEL['roxo_claro'], CORES_PASTEL['amarelo_claro'],
                  CORES_PASTEL['lavanda'], CORES_PASTEL['menta']]


def carregar_dados(caminho_arquivo):

    dados = {
        'parametros': [],  
        'veiculos': [],   
        'ums': [],        
        'regioes': []
    }

    
    with open(caminho_arquivo, mode='r', encoding='utf-8-sig') as file: 
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:  
            tipo = row['tipo']

            if tipo == 'parametro':  
                dados['parametros'].append({
                    'descricao': row['descricao'],
                    'beta': float(row['valor'])
                })

            elif tipo == 'veiculo':

                dados['veiculos'].append({
                    'id': int(row['id']),
                    'tipo': row['descricao'].replace('Veiculo_', ''),
                    'capacidade_peso': float(row['capacidade_peso']),
                    'capacidade_volume': float(row['capacidade_vol']),
                    'custo': row['custo'] if row['custo'] not in (None, '') else 0.0,
                    'carga_minima': float(row['carga_minima']),
                    'destino': row['destino'] if 'destino' in row else None
                })

            elif tipo == 'um':
                
                compatibilidade = row['compatibilidade'].strip()
                if not compatibilidade:
                    compatibilidade = ",".join(str(v['tipo']) for v in dados['veiculos'])
                else:
                    compatibilidade = ",".join([tipo.strip() for tipo in compatibilidade.split(",")])

                dados['ums'].append({
                    'id': int(row['id']),
                    'tipo': row['descricao'],
                    'peso': float(row['peso']),
                    'volume': float(row['volume']),
                    'custo_str': row['custo'] if row.get('custo') not in (None, '') else '',
                    'destino': row['destino'],
                    'compatibilidade': compatibilidade,
                    'restricao': row['restricao'],
                    'penalidade': float(row['penalidade']) * 10000
                })

    dados['regioes'] = list(set(um["destino"] for um in dados['ums']))

    regioes_ordenadas = sorted(dados['regioes'])

    for v in dados['veiculos']:
        custos_por_regiao = {}

        if v.get('custo') and ',' in str(v['custo']):
            custos = [float(c.strip()) for c in str(v['custo']).split(',')]

            for i, reg in enumerate(regioes_ordenadas):
                if i < len(custos):
                    custos_por_regiao[reg] = custos[i]
                else:
                    custos_por_regiao[reg] = 0.0

        else:
            
            try:
                custo_unico = float(v.get('custo') or 0.0)
            except:
                custo_unico = 0.0

            for reg in regioes_ordenadas:
                custos_por_regiao[reg] = custo_unico

        v['custos_por_regiao'] = custos_por_regiao

    veiculos_por_tipo = {}
    for v in dados['veiculos']:
        if v['tipo'] not in veiculos_por_tipo:
            veiculos_por_tipo[v['tipo']] = []
        veiculos_por_tipo[v['tipo']].append(v)

    for um in dados['ums']:
        if um['custo_str'] and ',' in um['custo_str']:
            custos = [float(custo.strip()) for custo in um['custo_str'].split(',')]
            um['custos_por_tipo'] = {}

            
            
            for i, v in enumerate(dados['veiculos']):
                tipo = v['tipo']
                
                if tipo not in um['custos_por_tipo']:
                    if i < len(custos):
                        um['custos_por_tipo'][tipo] = custos[i]
                    else:
                        um['custos_por_tipo'][tipo] = 0.0
        else:
            custo_unico = float(um['custo_str']) if um['custo_str'] else 0.0
            um['custos_por_tipo'] = {
                v['tipo']: custo_unico for v in dados['veiculos']
            }
            
    
    dados['ums_id'] = {um['id']: um for um in dados['ums']}
    dados['veiculos_id'] = {v['id']: v for v in dados['veiculos']}

    return dados

def um_compatível_com_veiculo(um, veiculo):
    
    compatibilidade_str = um.get("compatibilidade") or ""
    lista_comp = [c.strip().lower() for c in compatibilidade_str.split(",") if c.strip() != ""] 
    tipo_veiculo = (veiculo.get("tipo") or "").strip().lower()
    if lista_comp and tipo_veiculo not in lista_comp:
        return False
    
    dest_veiculo = veiculo.get("destino", None)
    dest_um = um.get("destino", None)
    if dest_veiculo and (dest_um and str(dest_veiculo) != str(dest_um)):
        return False
    return True

def veiculo_tem_capacidade(sol_status_veiculo, veiculo, um):
    
    peso_disponivel = veiculo.get("capacidade_peso", 0.0) - sol_status_veiculo[veiculo['id']]['peso_usado']
    vol_disponivel = veiculo.get("capacidade_volume", 0.0) - sol_status_veiculo[veiculo['id']]['volume_usado']
    if um['peso'] <= (peso_disponivel + 1e-9) and um['volume'] <= (vol_disponivel + 1e-9): 
        return True
    return False

def criar_estado_inicial(instancia):
    
    solucao = {
        'alocacao_um': {},
        'nao_alocadas': set(),
        'veiculo_dados': {},
        'custo': None
    }

    
    for um in instancia['ums']:
        um_id = um['id']
        solucao['nao_alocadas'].add(um_id)

    
    for v in instancia['veiculos']:
        v_id = v['id']
        solucao['veiculo_dados'][v_id] = {
            'ums': set(),
            'peso_usado': 0.0,
            'volume_usado': 0.0,
            'ativo': False,
            'regiao': None  
        }

    return solucao

def determinar_regiao_do_veiculo(v, dados_alocacao, instancia):
    
    regioes = instancia.get('regioes', [])
    dest_veiculo = v.get('destino', None)

    if dest_veiculo and (not regioes or str(dest_veiculo) in regioes):
        return str(dest_veiculo)

    
    reg_cache = dados_alocacao.get('regiao', None)
    if reg_cache is not None:
        return str(reg_cache)

    ums_ids = list(dados_alocacao.get('ums', []))
    if ums_ids:
        
        ums_map = instancia.get('ums_id', None)
        if ums_map is None:
            ums_map = {u['id']: u for u in instancia['ums']}  

        primeira_um = ums_map.get(ums_ids[0], None)
        if primeira_um:
            return str(primeira_um.get('destino'))

    return None

def alocar_um(solucao, um_id, veiculo_id, instancia):
    
    ums_id = instancia.get('ums_id', None)
    veiculos_id = instancia.get('veiculos_id', None)
    if ums_id is None:
        ums_id = {u['id']: u for u in instancia['ums']}
    if veiculos_id is None:
        veiculos_id = {v['id']: v for v in instancia['veiculos']}

    um = ums_id.get(um_id)
    veiculo = veiculos_id.get(veiculo_id)

    if um is None or veiculo is None:
        return False

    
    v_atual = solucao.get('alocacao_um', {}).get(um_id, None)
    if v_atual is not None:
        
        if v_atual == veiculo_id:
            return True
        
        return False

    dados_alocacao = solucao['veiculo_dados'][veiculo_id]

    
    if 'componentes_custo' not in solucao or solucao.get('custo') is None or 'total' not in solucao.get('componentes_custo', {}):
        custo_total(solucao, instancia)

    comp = solucao['componentes_custo']
    comp.setdefault('frete_morto_por_veiculo', {})
    comp.setdefault('custo_ativacao_por_veiculo', {})
    comp.setdefault('transporte_por_veiculo', {})
    beta_valor = float(comp.get('beta', 1.0))
      
    destino_nova = um.get('destino', None)
    destino_nova_norm = str(destino_nova) if destino_nova is not None else None  

    if len(dados_alocacao['ums']) > 0:
        reg_atual = dados_alocacao.get('regiao', None)
        if reg_atual is None:
            reg_atual = determinar_regiao_do_veiculo(veiculo, dados_alocacao, instancia)
            dados_alocacao['regiao'] = reg_atual

        reg_atual_norm = str(reg_atual) if reg_atual is not None else None      

        if reg_atual_norm is not None and destino_nova_norm is not None and reg_atual_norm != destino_nova_norm:
            return False
    else:
        dados_alocacao['regiao'] = destino_nova_norm  

    if not um_compatível_com_veiculo(um, veiculo):
        return False

    if not veiculo_tem_capacidade(solucao['veiculo_dados'], veiculo, um):
        return False

    ativo_antes = bool(dados_alocacao.get('ativo', False))
    frete_antigo = float(comp['frete_morto_por_veiculo'].get(veiculo_id, 0.0))
    ativ_antiga = float(comp['custo_ativacao_por_veiculo'].get(veiculo_id, 0.0))
    transp_antigo = float(comp['transporte_por_veiculo'].get(veiculo_id, 0.0))

    try:
        custo_unit = float(um.get('custos_por_tipo', {}).get(veiculo['tipo'], 0.0))
    except:
        custo_unit = 0.0

    try:
        penal_um = float(um.get('penalidade', 0.0))
    except:
        penal_um = 0.0

    dados_alocacao['ums'].add(um_id)
    dados_alocacao['peso_usado'] += um['peso']
    dados_alocacao['volume_usado'] += um['volume']
    dados_alocacao['ativo'] = True

    solucao['alocacao_um'][um_id] = veiculo_id
    estava_nao_alocada = (um_id in solucao['nao_alocadas'])
    solucao['nao_alocadas'].discard(um_id)
    
    if estava_nao_alocada:  
        comp['nao_alocacao'] = float(comp.get('nao_alocacao', 0.0)) - penal_um

    comp['transporte'] = float(comp.get('transporte', 0.0)) + custo_unit
    comp['transporte_por_veiculo'][veiculo_id] = transp_antigo + custo_unit

    if not ativo_antes:
        regiao = dados_alocacao.get('regiao', None)
        custo_fix = 0.0
        if regiao is not None:
            if 'custos_por_regiao' in veiculo:
                custo_fix = float(veiculo['custos_por_regiao'].get(str(regiao), 0.0))
            else:
                custo_fix = float(veiculo.get('custo', 0.0))

        comp['alocacao'] = float(comp.get('alocacao', 0.0)) + custo_fix
        comp['custo_ativacao_por_veiculo'][veiculo_id] = custo_fix

    capacidade_peso = float(veiculo.get('capacidade_peso', 0.0))
    peso_usado = float(dados_alocacao.get('peso_usado', 0.0))

    ociosidade = capacidade_peso - peso_usado
    if ociosidade < 0:
        ociosidade = 0.0

    frete_novo = float(beta_valor) * float(ociosidade)

    comp['frete_morto'] = float(comp.get('frete_morto', 0.0)) + (frete_novo - frete_antigo)
    comp['frete_morto_por_veiculo'][veiculo_id] = frete_novo

    comp['total'] = float(comp.get('alocacao', 0.0)) + float(comp.get('transporte', 0.0)) + float(comp.get('frete_morto', 0.0)) + float(comp.get('nao_alocacao', 0.0))
    solucao['custo'] = comp['total']

    return True

def desalocar_um(solucao, um_id, veiculo_id, instancia):

    ums_id = instancia.get('ums_id', None)
    veiculos_id = instancia.get('veiculos_id', None)
    if ums_id is None:
        ums_id = {u['id']: u for u in instancia['ums']}
    if veiculos_id is None:
        veiculos_id = {v['id']: v for v in instancia['veiculos']}

    um = ums_id.get(um_id)
    veiculo = veiculos_id.get(veiculo_id)

    if um is None or veiculo is None:
        return False
    
    v_atual = solucao.get('alocacao_um', {}).get(um_id, None)
    if v_atual != veiculo_id:
        return False

    dados_alocacao = solucao['veiculo_dados'][veiculo_id]
    
    if 'componentes_custo' not in solucao or solucao.get('custo') is None or 'total' not in solucao.get('componentes_custo', {}):
        custo_total(solucao, instancia)

    comp = solucao['componentes_custo']
    comp.setdefault('frete_morto_por_veiculo', {})
    comp.setdefault('custo_ativacao_por_veiculo', {})
    comp.setdefault('transporte_por_veiculo', {})
    beta_valor = float(comp.get('beta', 1.0))

    frete_antigo = float(comp['frete_morto_por_veiculo'].get(veiculo_id, 0.0))
    ativ_antiga = float(comp['custo_ativacao_por_veiculo'].get(veiculo_id, 0.0))
    transp_antigo = float(comp['transporte_por_veiculo'].get(veiculo_id, 0.0))

    try:
        custo_unit = float(um.get('custos_por_tipo', {}).get(veiculo['tipo'], 0.0))
    except:
        custo_unit = 0.0

    try:
        penal_um = float(um.get('penalidade', 0.0))
    except:
        penal_um = 0.0
        
    dados_alocacao['ums'].remove(um_id)
    dados_alocacao['peso_usado'] -= um['peso']
    dados_alocacao['volume_usado'] -= um['volume']

    solucao['alocacao_um'].pop(um_id, None)
    estava_nao_alocada = (um_id in solucao['nao_alocadas'])
    solucao['nao_alocadas'].add(um_id)

    if not estava_nao_alocada:  
        comp['nao_alocacao'] = float(comp.get('nao_alocacao', 0.0)) + penal_um
    
    comp['transporte'] = float(comp.get('transporte', 0.0)) - custo_unit
    comp['transporte_por_veiculo'][veiculo_id] = transp_antigo - custo_unit
    
    if len(dados_alocacao['ums']) == 0:
        
        dados_alocacao['ativo'] = False
        comp['alocacao'] = float(comp.get('alocacao', 0.0)) - ativ_antiga
        comp['custo_ativacao_por_veiculo'][veiculo_id] = 0.0
        comp['frete_morto'] = float(comp.get('frete_morto', 0.0)) - frete_antigo
        comp['frete_morto_por_veiculo'][veiculo_id] = 0.0
        
        dados_alocacao['regiao'] = None
    else:
        
        capacidade_peso = float(veiculo.get('capacidade_peso', 0.0))
        peso_usado = float(dados_alocacao.get('peso_usado', 0.0))

        ociosidade = capacidade_peso - peso_usado
        if ociosidade < 0:
            ociosidade = 0.0

        frete_novo = float(beta_valor) * float(ociosidade)

        comp['frete_morto'] = float(comp.get('frete_morto', 0.0)) + (frete_novo - frete_antigo)
        comp['frete_morto_por_veiculo'][veiculo_id] = frete_novo

    
    comp['total'] = float(comp.get('alocacao', 0.0)) + float(comp.get('transporte', 0.0)) + float(comp.get('frete_morto', 0.0)) + float(comp.get('nao_alocacao', 0.0))
    solucao['custo'] = comp['total']

    return True

def custo_total(solucao, instancia):
    
    if solucao.get('custo') is not None and 'componentes_custo' in solucao:
        comp = solucao.get('componentes_custo', {})
        try:
            a = float(comp.get('alocacao', 0.0))
            t = float(comp.get('transporte', 0.0))
            f = float(comp.get('frete_morto', 0.0))
            n = float(comp.get('nao_alocacao', 0.0))
            tot = float(comp.get('total', solucao.get('custo', 0.0)))

            ok_nao_neg = (a >= 0.0 and t >= 0.0 and f >= 0.0 and n >= 0.0 and tot >= 0.0)
            ok_soma = abs((a + t + f + n) - tot) <= 1e-6

            if ok_nao_neg and ok_soma:
                return solucao
        except:
            pass

        solucao['custo'] = None
        solucao.pop('componentes_custo', None)

    ums_id = instancia.get('ums_id', None)
    veiculos_id = instancia.get('veiculos_id', None)

    if ums_id is None:
        ums_id = {u['id']: u for u in instancia['ums']}  
    if veiculos_id is None:
        veiculos_id = {v['id']: v for v in instancia['veiculos']}  

    custo_ativacao = 0.0
    custo_transporte = 0.0
    custo_frete_morto = 0.0
    custo_nao_alocacao = 0.0

    beta_valor = 1.0
    try:
        beta_valor = next(
            (p["beta"] for p in instancia.get("parametros", [])
             if str(p.get("descricao", "")).strip().lower() == "beta"),
            1.0
        )
    except:
        beta_valor = 1.0

    solucao.setdefault('componentes_custo', {})
    solucao['componentes_custo'].setdefault('frete_morto_por_veiculo', {})
    solucao['componentes_custo'].setdefault('custo_ativacao_por_veiculo', {})
    solucao['componentes_custo'].setdefault('transporte_por_veiculo', {})
    solucao['componentes_custo']['beta'] = float(beta_valor)
    solucao['componentes_custo']['frete_morto_por_veiculo'].clear()
    solucao['componentes_custo']['custo_ativacao_por_veiculo'].clear()
    solucao['componentes_custo']['transporte_por_veiculo'].clear()
    
    for um_id in solucao['nao_alocadas']:
        um = ums_id.get(um_id)
        if um is not None:
            custo_nao_alocacao += float(um.get('penalidade', 0.0))

    for v_id, v_dados in solucao['veiculo_dados'].items():
        if not v_dados['ativo']:
            continue

        v = veiculos_id[v_id]

        regiao = determinar_regiao_do_veiculo(v, v_dados, instancia)

        custo_fixo = 0.0
        if regiao is not None:
            if 'custos_por_regiao' in v and regiao is not None:
                custo_fixo = float(v['custos_por_regiao'].get(regiao, 0.0))
            else:
                custo_fixo = float(v.get('custo', 0.0))

        custo_ativacao += custo_fixo
        solucao['componentes_custo']['custo_ativacao_por_veiculo'][v_id] = custo_fixo

        peso_usado = float(v_dados.get('peso_usado', 0.0))
        capacidade_peso = float(v.get('capacidade_peso', 0.0))

        ociosidade = capacidade_peso - peso_usado
        if ociosidade < 0:
            ociosidade = 0.0  

        penal_frete_morto = float(beta_valor) * float(ociosidade)

        custo_frete_morto += penal_frete_morto
        solucao['componentes_custo']['frete_morto_por_veiculo'][v_id] = penal_frete_morto

        transp_v = 0.0
        for um_id in v_dados['ums']:
            um = ums_id.get(um_id)
            if um is None:
                continue
            custos_tipo = um.get('custos_por_tipo', {})
            custo_unit = float(custos_tipo.get(v['tipo'], 0.0))

            custo_transporte += custo_unit
            transp_v += custo_unit

        solucao['componentes_custo']['transporte_por_veiculo'][v_id] = transp_v

    total = custo_ativacao + custo_transporte + custo_frete_morto + custo_nao_alocacao

    solucao['componentes_custo']['alocacao'] = float(custo_ativacao)
    solucao['componentes_custo']['transporte'] = float(custo_transporte)
    solucao['componentes_custo']['frete_morto'] = float(custo_frete_morto)
    solucao['componentes_custo']['nao_alocacao'] = float(custo_nao_alocacao)
    solucao['componentes_custo']['total'] = float(total)

    solucao['custo'] = float(total)

    return solucao

def gerar_solucao_gulosa(instancia, ordem=None):

    solucao = criar_estado_inicial(instancia)

    custo_total(solucao, instancia)

    veiculos = instancia['veiculos']
    ums_list = list(instancia['ums'])

    if ordem is None:
        ums_list.sort(key=lambda u: u.get('penalidade', 1.0), reverse=True)
    elif ordem == 'peso':
        ums_list.sort(key=lambda u: u.get('peso', 0.0), reverse=True)
    elif ordem == 'volume':
        ums_list.sort(key=lambda u: u.get('volume', 0.0), reverse=True)
    elif isinstance(ordem, int):
        rnd = random.Random(ordem)
        rnd.shuffle(ums_list)
    else:
        rnd = random.Random(RANDOM_SEED)
        rnd.shuffle(ums_list)

    ums_map = instancia.get('ums_id', None)
    veiculos_map = instancia.get('veiculos_id', None)
    if ums_map is None:
        ums_map = {u['id']: u for u in instancia['ums']}
    if veiculos_map is None:
        veiculos_map = {v['id']: v for v in instancia['veiculos']}

    for um in ums_list:

        destino_um = um.get('destino', None)
        destino_um_norm = str(destino_um) if destino_um is not None else None

        candidatos_fixos = []      
        candidatos_vazios = []     

        for v in veiculos:
            vid = v['id']
            v_dados = solucao['veiculo_dados'][vid]

            reg_v = determinar_regiao_do_veiculo(v, v_dados, instancia)
            
            reg_v_norm = str(reg_v) if reg_v is not None else None

            if reg_v_norm is not None and destino_um_norm is not None and reg_v_norm != destino_um_norm:
                continue
            if not um_compatível_com_veiculo(um, v):
                continue
            if not veiculo_tem_capacidade(solucao['veiculo_dados'], v, um):
                continue
            if v_dados.get('ativo', False) and reg_v_norm is not None and reg_v_norm == destino_um_norm:
                candidatos_fixos.append(v)
            else:
                if len(v_dados['ums']) == 0:
                    candidatos_vazios.append(v)
        if candidatos_fixos:
            candidatos = candidatos_fixos
        else:
            candidatos = candidatos_vazios
        if not candidatos:
            continue  
        melhor_chave = None
        melhores = []

        for v in candidatos:
            vid = v['id']

            
            try:
                custo_marginal = float(um.get('custos_por_tipo', {}).get(v['tipo'], 0.0))
            except:
                custo_marginal = 0.0

            
            peso_disp = v.get('capacidade_peso', 0.0) - solucao['veiculo_dados'][vid]['peso_usado']
            vol_disp  = v.get('capacidade_volume', 0.0) - solucao['veiculo_dados'][vid]['volume_usado']

            peso_rel = peso_disp / (v.get('capacidade_peso', 1.0) + 1e-9)
            vol_rel  = vol_disp / (v.get('capacidade_volume', 1.0) + 1e-9)

            folga_score = peso_rel + vol_rel

            chave = (custo_marginal, -folga_score)

            if melhor_chave is None or chave < melhor_chave:
                melhor_chave = chave
                melhores = [v]
            elif chave == melhor_chave:
                melhores.append(v)

        escolhido = melhores[0]

        
        
        
        sucesso = alocar_um(solucao, um['id'], escolhido['id'], instancia)

        if not sucesso:
            
            for v in candidatos:
                if v == escolhido:
                    continue
                if alocar_um(solucao, um['id'], v['id'], instancia):
                    sucesso = True
                    break

    return solucao


def atende_carga_minima(solucao, veiculos_map, vid):

    dados_v = solucao['veiculo_dados'][vid]
    if not dados_v['ativo']:
        return True
    carga_min = float(veiculos_map[vid].get('carga_minima', 0.0) or 0.0)
    return (dados_v['peso_usado'] + 1e-9) >= carga_min

def realizar_troca_1x1(solucao, instancia):
    
    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, instancia)

    
    custo_base = float(solucao['custo'])

    
    veiculos_map = instancia.get('veiculos_id', None)
    if veiculos_map is None:
        veiculos_map = {v['id']: v for v in instancia['veiculos']}

    
    ativos = [vid for vid, dados in solucao['veiculo_dados'].items() if dados['ativo'] and len(dados['ums']) > 0]
    if len(ativos) < 2:
        return False

    melhor_mov = None
    melhor_delta = 0.0

    
    ativos_ordenados = sorted(ativos)

    for i in range(len(ativos_ordenados)):
        v1 = ativos_ordenados[i]
        ums_v1 = list(solucao['veiculo_dados'][v1]['ums'])

        for j in range(i + 1, len(ativos_ordenados)):
            v2 = ativos_ordenados[j]
            ums_v2 = list(solucao['veiculo_dados'][v2]['ums'])

            for um_a in ums_v1:
                for um_b in ums_v2:

                    
                    desalocar_um(solucao, um_a, v1, instancia)
                    desalocar_um(solucao, um_b, v2, instancia)

                    ok = True
                    if not alocar_um(solucao, um_a, v2, instancia):
                        ok = False
                    else:
                        if not alocar_um(solucao, um_b, v1, instancia):
                            ok = False

                    
                    if ok:
                        if not atende_carga_minima(solucao, veiculos_map, v1):
                            ok = False
                        elif not atende_carga_minima(solucao, veiculos_map, v2):
                            ok = False

                    if ok:
                        
                        custo_novo = float(solucao['custo'])
                        delta = custo_base - custo_novo
                        if delta > melhor_delta + 1e-9:
                            melhor_delta = delta
                            melhor_mov = (um_a, um_b, v1, v2)

                    
                    
                    if solucao['alocacao_um'].get(um_a) == v2:
                        desalocar_um(solucao, um_a, v2, instancia)
                    if solucao['alocacao_um'].get(um_b) == v1:
                        desalocar_um(solucao, um_b, v1, instancia)

                    
                    alocar_um(solucao, um_a, v1, instancia)
                    alocar_um(solucao, um_b, v2, instancia)

    
    if melhor_mov is not None:
        um_a, um_b, v1, v2 = melhor_mov
        desalocar_um(solucao, um_a, v1, instancia)
        desalocar_um(solucao, um_b, v2, instancia)
        alocar_um(solucao, um_a, v2, instancia)
        alocar_um(solucao, um_b, v1, instancia)
        return True

    return False

def realizar_troca_2x1(solucao, instancia):
    
    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, instancia)

    
    custo_base = float(solucao['custo'])

    
    veiculos_map = instancia.get('veiculos_id', None)
    if veiculos_map is None:
        veiculos_map = {v['id']: v for v in instancia['veiculos']}

    ativos = [vid for vid, dados in solucao['veiculo_dados'].items() if dados['ativo'] and len(dados['ums']) > 0]
    if len(ativos) < 2:
        return False

    melhor_mov = None
    melhor_delta = 0.0

    ativos_ordenados = sorted(ativos)

    for i in range(len(ativos_ordenados)):
        v1 = ativos_ordenados[i]
        ums_v1 = list(solucao['veiculo_dados'][v1]['ums'])
        if len(ums_v1) < 2:
            continue

        for j in range(i + 1, len(ativos_ordenados)):
            v2 = ativos_ordenados[j]
            ums_v2 = list(solucao['veiculo_dados'][v2]['ums'])
            if len(ums_v2) < 1:
                continue

            for (um_a, um_b) in itertools.combinations(ums_v1, 2):
                for um_c in ums_v2:

                    
                    desalocar_um(solucao, um_a, v1, instancia)
                    desalocar_um(solucao, um_b, v1, instancia)
                    desalocar_um(solucao, um_c, v2, instancia)

                    ok = True

                    
                    if not alocar_um(solucao, um_c, v1, instancia):
                        ok = False
                    else:
                        
                        if not alocar_um(solucao, um_a, v2, instancia):
                            ok = False
                        else:
                            if not alocar_um(solucao, um_b, v2, instancia):
                                ok = False

                    if ok:
                        if not atende_carga_minima(solucao, veiculos_map, v1):
                            ok = False
                        elif not atende_carga_minima(solucao, veiculos_map, v2):
                            ok = False

                    if ok:
                        
                        custo_novo = float(solucao['custo'])
                        delta = custo_base - custo_novo
                        if delta > melhor_delta + 1e-9:
                            melhor_delta = delta
                            melhor_mov = (um_a, um_b, um_c, v1, v2)

                    
                    
                    if solucao['alocacao_um'].get(um_c) == v1:
                        desalocar_um(solucao, um_c, v1, instancia)
                    if solucao['alocacao_um'].get(um_a) == v2:
                        desalocar_um(solucao, um_a, v2, instancia)
                    if solucao['alocacao_um'].get(um_b) == v2:
                        desalocar_um(solucao, um_b, v2, instancia)

                    
                    alocar_um(solucao, um_a, v1, instancia)
                    alocar_um(solucao, um_b, v1, instancia)
                    alocar_um(solucao, um_c, v2, instancia)

    if melhor_mov is not None:
        um_a, um_b, um_c, v1, v2 = melhor_mov
        desalocar_um(solucao, um_a, v1, instancia)
        desalocar_um(solucao, um_b, v1, instancia)
        desalocar_um(solucao, um_c, v2, instancia)
        alocar_um(solucao, um_c, v1, instancia)
        alocar_um(solucao, um_a, v2, instancia)
        alocar_um(solucao, um_b, v2, instancia)
        return True

    return False


def realizar_troca_1x2(solucao, instancia):
    
    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, instancia)

    
    custo_base = float(solucao['custo'])

    
    veiculos_map = instancia.get('veiculos_id', None)
    if veiculos_map is None:
        veiculos_map = {v['id']: v for v in instancia['veiculos']}

    ativos = [vid for vid, dados in solucao['veiculo_dados'].items() if dados['ativo'] and len(dados['ums']) > 0]
    if len(ativos) < 2:
        return False

    melhor_mov = None
    melhor_delta = 0.0

    ativos_ordenados = sorted(ativos)

    for i in range(len(ativos_ordenados)):
        v1 = ativos_ordenados[i]
        ums_v1 = list(solucao['veiculo_dados'][v1]['ums'])
        if len(ums_v1) < 1:
            continue

        for j in range(i + 1, len(ativos_ordenados)):
            v2 = ativos_ordenados[j]
            ums_v2 = list(solucao['veiculo_dados'][v2]['ums'])
            if len(ums_v2) < 2:
                continue

            for um_c in ums_v1:
                for (um_a, um_b) in itertools.combinations(ums_v2, 2):

                    
                    desalocar_um(solucao, um_c, v1, instancia)
                    desalocar_um(solucao, um_a, v2, instancia)
                    desalocar_um(solucao, um_b, v2, instancia)

                    ok = True

                    
                    if not alocar_um(solucao, um_a, v1, instancia):
                        ok = False
                    else:
                        if not alocar_um(solucao, um_b, v1, instancia):
                            ok = False
                        else:
                            
                            if not alocar_um(solucao, um_c, v2, instancia):
                                ok = False

                    if ok:
                        if not atende_carga_minima(solucao, veiculos_map, v1):
                            ok = False
                        elif not atende_carga_minima(solucao, veiculos_map, v2):
                            ok = False

                    if ok:
                        
                        custo_novo = float(solucao['custo'])
                        delta = custo_base - custo_novo
                        if delta > melhor_delta + 1e-9:
                            melhor_delta = delta
                            melhor_mov = (um_a, um_b, um_c, v1, v2)

                    
                    if solucao['alocacao_um'].get(um_a) == v1:
                        desalocar_um(solucao, um_a, v1, instancia)
                    if solucao['alocacao_um'].get(um_b) == v1:
                        desalocar_um(solucao, um_b, v1, instancia)
                    if solucao['alocacao_um'].get(um_c) == v2:
                        desalocar_um(solucao, um_c, v2, instancia)

                    alocar_um(solucao, um_c, v1, instancia)
                    alocar_um(solucao, um_a, v2, instancia)
                    alocar_um(solucao, um_b, v2, instancia)

    if melhor_mov is not None:
        um_a, um_b, um_c, v1, v2 = melhor_mov
        desalocar_um(solucao, um_c, v1, instancia)
        desalocar_um(solucao, um_a, v2, instancia)
        desalocar_um(solucao, um_b, v2, instancia)
        alocar_um(solucao, um_a, v1, instancia)
        alocar_um(solucao, um_b, v1, instancia)
        alocar_um(solucao, um_c, v2, instancia)
        return True

    return False

def realizar_desalocacao(solucao, instancia):
    
    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, instancia)

    
    custo_base = float(solucao['custo'])

    
    veiculos_map = instancia.get('veiculos_id', None)
    if veiculos_map is None:
        veiculos_map = {v['id']: v for v in instancia['veiculos']}

    melhor_mov = None
    melhor_delta = 0.0

    
    for um_id, v_origem_id in list(solucao['alocacao_um'].items()):

        
        desalocar_um(solucao, um_id, v_origem_id, instancia)

        ok = True
        if not atende_carga_minima(solucao, veiculos_map, v_origem_id):
            ok = False

        if ok:
            
            custo_novo = float(solucao['custo'])
            delta = custo_base - custo_novo
            if delta > melhor_delta + 1e-9:
                melhor_delta = delta
                melhor_mov = (um_id, v_origem_id)

        
        alocar_um(solucao, um_id, v_origem_id, instancia)

    if melhor_mov is not None:
        um_id, v_origem_id = melhor_mov
        desalocar_um(solucao, um_id, v_origem_id, instancia)
        return True

    return False

def realoca_entre_veiculos(solucao, instancia):

    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, instancia)

    
    ums_id = instancia.get('ums_id', None)
    veiculos_map = instancia.get('veiculos_id', None)
    veiculos = instancia.get('veiculos', [])

    if ums_id is None:
        ums_id = {u['id']: u for u in instancia['ums']}
    if veiculos_map is None:
        veiculos_map = {v['id']: v for v in instancia['veiculos']}

    
    custo_base = float(solucao['custo'])

    melhor_movimento = None  
    melhor_delta = 0.0

    for um_id, v_origem_id in list(solucao['alocacao_um'].items()):
        um = ums_id[um_id]

        for v_dest in veiculos:
            v_dest_id = v_dest['id']
            if v_dest_id == v_origem_id:
                continue

            
            if not um_compatível_com_veiculo(um, v_dest):
                continue
            if not veiculo_tem_capacidade(solucao['veiculo_dados'], v_dest, um):
                continue

            
            if not desalocar_um(solucao, um_id, v_origem_id, instancia):
                continue
            if not alocar_um(solucao, um_id, v_dest_id, instancia):
                
                alocar_um(solucao, um_id, v_origem_id, instancia)
                continue

            
            ok = True
            for vid in (v_origem_id, v_dest_id):
                dados_v = solucao['veiculo_dados'][vid]
                veic = veiculos_map[vid]
                carga_min = float(veic.get('carga_minima', 0.0) or 0.0)
                if dados_v['ativo'] and dados_v['peso_usado'] + 1e-9 < carga_min:
                    ok = False
                    break

            if ok:
                
                novo_custo = float(solucao['custo'])
                delta = novo_custo - custo_base
                if delta < melhor_delta - 1e-9:
                    melhor_delta = delta
                    melhor_movimento = (um_id, v_origem_id, v_dest_id)

            
            desalocar_um(solucao, um_id, v_dest_id, instancia)
            alocar_um(solucao, um_id, v_origem_id, instancia)

    
    if melhor_movimento is not None:
        um_id, v_origem_id, v_dest_id = melhor_movimento
        desalocar_um(solucao, um_id, v_origem_id, instancia)
        alocar_um(solucao, um_id, v_dest_id, instancia)
        
        return True

    return False
def busca_local(solucao, instancia, max_iter=200, time_limit=TIMEOUT):
        
    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, instancia)

    start_time = time.time()
    iteracoes = 0

    while iteracoes < max_iter:
        if (time.time() - start_time) > time_limit:
            break

        melhorou = False

        if realoca_entre_veiculos(solucao, instancia):
            melhorou = True
        elif realizar_troca_1x1(solucao, instancia):
            melhorou = True
        elif realizar_troca_2x1(solucao, instancia):
            melhorou = True
        elif realizar_troca_1x2(solucao, instancia):
            melhorou = True
        elif realizar_desalocacao(solucao, instancia):
            melhorou = True

        if not melhorou:
            
            break

        iteracoes += 1

    return solucao


def aplicar_restricao_carga_minima(solucao, instancia):

    
    veiculos_id = instancia.get('veiculos_id', None)
    if veiculos_id is None:
        veiculos_id = {v['id']: v for v in instancia['veiculos']}  

    
    if 'componentes_custo' not in solucao or solucao.get('custo') is None or 'total' not in solucao.get('componentes_custo', {}):
        custo_total(solucao, instancia)

    for v_id, dados_v in solucao['veiculo_dados'].items():
        if not dados_v['ativo']:
            continue

        veiculo = veiculos_id[v_id]

        if dados_v['peso_usado'] + 1e-9 < veiculo['carga_minima']:

            
            for um_id in list(dados_v['ums']):
                desalocar_um(solucao, um_id, v_id, instancia)

    
    


def executar_instancia_heuristica(caminho, num_reinicios=NUM_REINICIOS, time_limit=TIMEOUT):
    
    instancia = carregar_dados(caminho)
    melhor_sol = None
    melhor_custo = float("inf")
    solucao_inicial = None  

    tempo_total = time.time()
    ordens = [None, 'peso', 'volume'] + list(range(max(0, num_reinicios-3)))
    ordens = ordens[:num_reinicios] 

    for restart_id, ordm in enumerate(ordens): 

        t0 = time.time() 
        if (time.time() - tempo_total) > time_limit: 
            break

        
        solucao = gerar_solucao_gulosa(instancia, ordem=ordm) 
        aplicar_restricao_carga_minima(solucao, instancia)

        
        if restart_id == 0:
            solucao_inicial = copy.deepcopy(solucao)  

        
        solucao = busca_local(solucao, instancia, max_iter=200, time_limit=time_limit - (time.time() - tempo_total))
        aplicar_restricao_carga_minima(solucao, instancia)

        custo = custo_total(solucao, instancia)['componentes_custo']['total'] 
        print(f"  Restart {restart_id+1}/{len(ordens)} ordem={ordm} custo={custo:.2f} tempo={(time.time()-t0):.1f}s")

        if custo < melhor_custo: 
            melhor_custo = custo
            melhor_sol = copy.deepcopy(solucao) 

    tempo_total = time.time() - tempo_total
    nome_instancia = os.path.basename(caminho).replace('.csv', '') 

    return {
        "solucao": melhor_sol,
        "custo": melhor_custo,
        "tempo_exec": tempo_total,
        "instancia": instancia,
        "nome_instancia": nome_instancia,  
        "solucao_inicial": solucao_inicial  
    }

def estruturar_resultados_heuristica(resultado, solucao_inicial=None):
    
    solucao = resultado['solucao']
    instancia = resultado['instancia']

    if solucao is None:
        return None

    
    custo_total(solucao, instancia)  

    ums_id = {u['id']: u for u in instancia['ums']}
    veiculos_id = {v['id']: v for v in instancia['veiculos']}

    custo_total_valor = resultado['custo']  

    
    sol_inicial_dados = None
    if solucao_inicial:
        custo_total(solucao_inicial, instancia)  
        sol_inicial_dados = {
            'custo_total': solucao_inicial['componentes_custo']['total'],  
            'veiculos_ativos': sum(1 for v in solucao_inicial['veiculo_dados'].values() if v['ativo']),
            'ums_alocadas': len(solucao_inicial['alocacao_um']),
            'ums_nao_alocadas': len(solucao_inicial['nao_alocadas']),
            'custo_alocacao': solucao_inicial['componentes_custo']['alocacao'],  
            'custo_transporte': solucao_inicial['componentes_custo']['transporte'],  
            'frete_morto_total': solucao_inicial['componentes_custo']['frete_morto'],  
            'custo_nao_alocacao': solucao_inicial['componentes_custo']['nao_alocacao']  
        }

    alocacoes = []
    veiculos_ativos = 0
    ums_alocadas = 0
    ums_nao_alocadas = 0
    peso_nao_alocado = 0.0
    volume_nao_alocado = 0.0

    
    termos = solucao.get('componentes_custo', {})
    custo_alocacao = termos.get('alocacao', 0.0)
    custo_transporte = termos.get('transporte', 0.0)
    custo_frete_morto = termos.get('frete_morto', 0.0)
    custo_nao_alocacao = termos.get('nao_alocacao', 0.0)

    
    for um_id in solucao['nao_alocadas']:
        um = ums_id.get(um_id)
        if um is not None:
            ums_nao_alocadas += 1
            peso_nao_alocado += um.get('peso', 0.0)
            volume_nao_alocado += um.get('volume', 0.0)

    
    ums_alocadas = len(solucao['alocacao_um'])

    for veiculo_id, veiculo_dados in solucao['veiculo_dados'].items():
        if veiculo_dados['ativo']: 
            veiculos_ativos += 1
            v = veiculos_id[veiculo_id] 
            cargas = list(veiculo_dados['ums']) 
            tipos_um = [ums_id[um_id].get('tipo', 'Desconhecido') for um_id in cargas]

            peso_total = veiculo_dados['peso_usado']
            volume_total = veiculo_dados['volume_usado']

            taxa_utilizacao_peso = (peso_total / v['capacidade_peso'] * 100) if v['capacidade_peso'] > 0 else 0
            taxa_utilizacao_volume = (volume_total / v['capacidade_volume'] * 100) if v['capacidade_volume'] > 0 else 0

            destino = None
            if cargas:
                primeira_um = ums_id[cargas[0]] 
                destino = primeira_um.get('destino', 'N/A')
            else:
                destino = v.get('destino', 'N/A')

            frete_morto_por_veic = solucao.get('componentes_custo', {}).get('frete_morto_por_veiculo', {})
            custo_ativacao_por_veic = solucao.get('componentes_custo', {}).get('custo_ativacao_por_veiculo', {})

            alocacoes.append({
                'veiculo_id': veiculo_id,
                'veiculo_tipo': v.get('tipo', 'N/A'),
                'destino': destino,
                'cargas': cargas,
                'tipos_um': tipos_um,
                'peso_total': peso_total,
                'peso_minimo': v.get('carga_minima', 0.0),
                'capacidade_peso': v['capacidade_peso'],
                'volume_total': volume_total,
                'capacidade_volume': v['capacidade_volume'],
                'taxa_utilizacao_peso': taxa_utilizacao_peso,
                'taxa_utilizacao_volume': taxa_utilizacao_volume,
                'custo_veiculo': float(custo_ativacao_por_veic.get(veiculo_id, 0.0)),
                'frete_morto': {'valor': float(frete_morto_por_veic.get(veiculo_id, 0.0))}
            })

    return {
        'tipo_instancia': resultado.get('nome_instancia', 'N/A'),
        'custo_total': custo_total_valor,
        'custo_alocacao': custo_alocacao,
        'custo_transporte': custo_transporte,
        'frete_morto_total': custo_frete_morto,
        'custo_nao_alocacao': custo_nao_alocacao,
        'veiculos_ativos': veiculos_ativos,
        'veiculos_inativos': len(instancia.get('veiculos', [])) - veiculos_ativos,
        'ums_alocadas': ums_alocadas,
        'ums_nao_alocadas': ums_nao_alocadas,
        'peso_nao_alocado': peso_nao_alocado,
        'volume_nao_alocado': volume_nao_alocado,
        'alocacoes': alocacoes,
        'tempo_execucao': resultado.get('tempo_exec', 0.0),  
        'gap_otimizacao': 0.0,  
        'status': 'Heurística',  
        'melhor_solucao': custo_total_valor ,  
        'solucao_relaxada': None,  
        'relaxacao_linear': None,  
        'gap_relaxacao': None,  
        'tempo_para_otimo': resultado.get('tempo_exec', 0.0)  
    }

def imprimir_resultados_detalhados_heuristica(resultados):
    
    if not resultados:
        print("Nenhum resultado para imprimir.")
        return

    print("\n" + "="*80)
    print(f"Resumo da heurística — Instância: {resultados.get('tipo_instancia', 'N/A')}")
    print("="*80)
    print(f"Custo total: {resultados.get('custo_total', 0.0):.2f}")
    print(f"  - Custo ativação: {resultados.get('custo_alocacao', 0.0):.2f}")
    print(f"  - Custo transporte: {resultados.get('custo_transporte', 0.0):.2f}")
    print(f"  - Frete morto total: {resultados.get('frete_morto_total', 0.0):.2f}")
    print(f"  - Custo não alocação: {resultados.get('custo_nao_alocacao', 0.0):.2f}")
    print()
    print(f"Veículos ativos: {resultados.get('veiculos_ativos', 0)}")
    print(f"Veículos inativos: {resultados.get('veiculos_inativos', 0)}")
    print(f"UMs alocadas: {resultados.get('ums_alocadas', 0)}")
    print(f"UMs não alocadas: {resultados.get('ums_nao_alocadas', 0)}")
    print(f"Peso não alocado (kg): {resultados.get('peso_nao_alocado', 0.0):.2f}")
    print(f"Volume não alocado (m³): {resultados.get('volume_nao_alocado', 0.0):.2f}")
    print("\nDetalhe por veículo:")
    for a in resultados.get('alocacoes', []):
        print("-"*60)
        print(f"Veículo ID: {a.get('veiculo_id')}  Tipo: {a.get('veiculo_tipo')}  Destino: {a.get('destino')}")
        print(f" Cargas: {a.get('cargas')}")
        print(f" Peso total: {a.get('peso_total', 0.0):.2f}  / Capacidade: {a.get('capacidade_peso', 0.0)}  (mín.: {a.get('peso_minimo', 0.0)})")
        print(f" Utilização peso: {a.get('taxa_utilizacao_peso', 0.0):.1f}%")
        print(f" Volume total: {a.get('volume_total', 0.0):.2f} / Capacidade vol.: {a.get('capacidade_volume', 0.0)}")
        print(f" Utilização volume: {a.get('taxa_utilizacao_volume', 0.0):.1f}%")
        print(f" Custo ativação veículo: {a.get('custo_veiculo', 0.0):.2f}")
        print(f" Frete morto veículo: {a.get('frete_morto', {}).get('valor', 0.0):.2f}")
    print("\n" + "="*80 + "\n")

def exportar_resultados_csv_heuristica(resultados_lista, instancias_originais, solucoes_iniciais, resultado_estruturado):
    
    import os
    import csv
    from datetime import datetime

    caminho_saida = os.path.join(os.path.dirname(__file__), INSTANCIAS, 'Resultados - Heuristica')
    os.makedirs(caminho_saida, exist_ok=True)
    
    if not resultados_lista or not instancias_originais:
        raise ValueError("Listas de resultados e instâncias originais vazias.")

    idx_atual = len(resultados_lista) - 1
    resultados = resultados_lista[idx_atual]
    instancia_atual = instancias_originais[idx_atual]

    
    sol_inicial = None
    if solucoes_iniciais and len(solucoes_iniciais) > idx_atual:
        sol_inicial = solucoes_iniciais[idx_atual]

    
    
    
    def _valor_ou_na(v, casas=None):
        if v is None:
            return "N/A"
        try:
            if casas is None:
                return str(v)
            return f"{float(v):.{casas}f}"
        except:
            return str(v)

    def _beta_da_instancia(inst):
        beta_valor = 1.0
        try:
            for p in inst.get("parametros", []):
                if str(p.get("descricao", "")).strip().lower() == "beta":
                    beta_valor = float(p.get("beta", 1.0))
                    break
        except:
            beta_valor = 1.0
        return beta_valor

    def _ids_alocados_do_resultado(res):
        
        ids = set()
        for a in res.get("alocacoes", []) or []:
            for um_id in a.get("cargas", []) or []:
                ids.add(int(um_id))
        return ids

    def _frete_morto_por_veiculo(beta_valor, capacidade_peso, peso_usado):
        try:
            ociosidade = float(capacidade_peso) - float(peso_usado)
            if ociosidade < 0:
                ociosidade = 0.0
            return float(beta_valor) * float(ociosidade)
        except:
            return 0.0

    def _motivo_nao_alocada(um, veiculos):
        
        try:
            peso = float(um.get("peso", 0.0))
            volume = float(um.get("volume", 0.0))
        except:
            peso, volume = 0.0, 0.0

        existe_viavel = False
        for v in veiculos:
            try:
                
                if not um_compatível_com_veiculo(um, v):
                    continue
                
                if peso <= float(v.get("capacidade_peso", 0.0)) + 1e-9 and volume <= float(v.get("capacidade_volume", 0.0)) + 1e-9:
                    existe_viavel = True
                    break
            except:
                continue

        if not existe_viavel:
            return "Incompatibilidade"
        return "Decisão da heurística"
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_arquivo = f"resultados_heuristica_{resultado_estruturado['nome_instancia']}_{timestamp}.csv"
    caminho_completo = os.path.join(caminho_saida, nome_arquivo)

    beta_valor = _beta_da_instancia(instancia_atual)
    ums_id = {u["id"]: u for u in instancia_atual.get("ums", [])}
    veiculos = instancia_atual.get("veiculos", [])
    veiculos_id = {v["id"]: v for v in veiculos}

    
    ids_alocados_melhor = _ids_alocados_do_resultado(resultados)
    todos_ums = set(int(u["id"]) for u in instancia_atual.get("ums", []))
    ids_nao_alocados_melhor = sorted(list(todos_ums - ids_alocados_melhor), key=lambda i: (str(ums_id.get(i, {}).get("tipo", "")), int(i)))

    
    ids_nao_alocados_inicial = []
    if sol_inicial:
        ids_alocados_inicial = _ids_alocados_do_resultado(sol_inicial)
        ids_nao_alocados_inicial = sorted(list(todos_ums - ids_alocados_inicial), key=lambda i: (str(ums_id.get(i, {}).get("tipo", "")), int(i)))

    with open(caminho_completo, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file, delimiter=';')

        writer.writerow(["RELATÓRIO DE HEURÍSTICA"])
        writer.writerow(["Gerado em:", datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
        writer.writerow([])

        writer.writerow([f"INSTÂNCIA: {resultados.get('tipo_instancia', 'N/A')}"])
        writer.writerow([])
        
        writer.writerow(["Status", _valor_ou_na(resultados.get("status", "Heurística"))])
        writer.writerow(["Tempo Total (s)", _valor_ou_na(resultados.get("tempo_execucao", 0.0), 2)])
        writer.writerow(["Tempo para Ótimo (s)", _valor_ou_na(resultados.get("tempo_para_otimo", resultados.get("tempo_execucao", 0.0)), 2)])

        writer.writerow(["Melhor Solução", _valor_ou_na(resultados.get("melhor_solucao", resultados.get("custo_total", 0.0)), 2)])
        writer.writerow(["Solução Relaxada", _valor_ou_na(resultados.get("solucao_relaxada", None), 2)])
        writer.writerow(["GAP (%)", _valor_ou_na(resultados.get("gap_otimizacao", 0.0), 2)])

        writer.writerow(["Relaxação Linear", _valor_ou_na(resultados.get("relaxacao_linear", None), 2)])
        writer.writerow(["GAP Relaxação (%)", _valor_ou_na(resultados.get("gap_relaxacao", None), 2)])

        writer.writerow(["Custo Total", _valor_ou_na(resultados.get("custo_total", 0.0), 2)])
        writer.writerow(["Custo Atendimento", _valor_ou_na(resultados.get("custo_alocacao", 0.0), 2)])
        writer.writerow(["Custo Transporte", _valor_ou_na(resultados.get("custo_transporte", 0.0), 2)])
        writer.writerow(["Frete Morto", _valor_ou_na(resultados.get("frete_morto_total", 0.0), 2)])
        writer.writerow(["Custo Não Alocação", _valor_ou_na(resultados.get("custo_nao_alocacao", 0.0), 2)])

        writer.writerow(["Peso Não Alocado", _valor_ou_na(resultados.get("peso_nao_alocado", 0.0))])
        writer.writerow(["Volume Não Alocado", _valor_ou_na(resultados.get("volume_nao_alocado", 0.0))])

        writer.writerow(["Veículos Ativos", _valor_ou_na(resultados.get("veiculos_ativos", 0))])
        writer.writerow(["Veículos Inativos", _valor_ou_na(resultados.get("veiculos_inativos", 0))])
        writer.writerow(["UMs Alocadas", _valor_ou_na(resultados.get("ums_alocadas", 0))])
        writer.writerow(["UMs Não Alocadas", _valor_ou_na(resultados.get("ums_nao_alocadas", 0))])

        writer.writerow([])
        writer.writerow(["VEÍCULOS ATIVOS"])
        writer.writerow([
            "ID", "Tipo", "Destino", "Cargas",
            "Peso Total (kg)", "Capacidade (kg)", "Utilização (%)",
            "Volume Total", "Capacidade (m3)", "Utilização (%)",
            "Frete Morto (R$)"
        ])

        
        alocacoes_melhor = resultados.get("alocacoes", []) or []
        alocacoes_melhor = sorted(alocacoes_melhor, key=lambda a: int(a.get("veiculo_id", 0)))

        for a in alocacoes_melhor:
            v_id = a.get("veiculo_id", "")
            v = veiculos_id.get(v_id, {})
            peso_total = a.get("peso_total", 0.0)
            cap_peso = a.get("capacidade_peso", v.get("capacidade_peso", 0.0))
            vol_total = a.get("volume_total", 0.0)
            cap_vol = a.get("capacidade_volume", v.get("capacidade_volume", 0.0))

            frete_v = _frete_morto_por_veiculo(beta_valor, cap_peso, peso_total)

            writer.writerow([
                v_id,
                a.get("veiculo_tipo", ""),
                a.get("destino", ""),
                ";".join(map(str, a.get("cargas", []) or [])),
                _valor_ou_na(peso_total),
                _valor_ou_na(cap_peso),
                _valor_ou_na(a.get("taxa_utilizacao_peso", 0.0), 1),
                _valor_ou_na(vol_total),
                _valor_ou_na(cap_vol),
                _valor_ou_na(a.get("taxa_utilizacao_volume", 0.0), 1),
                _valor_ou_na(frete_v, 2)
            ])

        writer.writerow([])
        writer.writerow(["UNIDADES METÁLICAS NÃO ALOCADAS"])
        writer.writerow(["ID", "Tipo", "Peso (kg)", "Volume (m³)", "Destino", "Compatibilidade", "Motivo"])

        for um_id in ids_nao_alocados_melhor:
            um = ums_id.get(um_id, {})
            writer.writerow([
                um_id,
                um.get("tipo", ""),
                _valor_ou_na(um.get("peso", "")),
                _valor_ou_na(um.get("volume", "")),
                um.get("destino", ""),
                um.get("compatibilidade", ""),
                _motivo_nao_alocada(um, veiculos)
            ])
            
        if sol_inicial is not None:
            writer.writerow([])
            writer.writerow(["SOLUÇÃO INICIAL (GULOSA)"])
            writer.writerow(["Status", _valor_ou_na(sol_inicial.get("status", "Heurística"))])
            writer.writerow(["Tempo Total (s)", _valor_ou_na(sol_inicial.get("tempo_execucao", resultados.get("tempo_execucao", 0.0)), 2)])
            writer.writerow(["Tempo para Ótimo (s)", _valor_ou_na(sol_inicial.get("tempo_para_otimo", sol_inicial.get("tempo_execucao", resultados.get("tempo_execucao", 0.0))), 2)])

            writer.writerow(["Melhor Solução", _valor_ou_na(sol_inicial.get("melhor_solucao", sol_inicial.get("custo_total", 0.0)), 2)])
            writer.writerow(["Solução Relaxada", _valor_ou_na(sol_inicial.get("solucao_relaxada", None), 2)])
            writer.writerow(["GAP (%)", _valor_ou_na(sol_inicial.get("gap_otimizacao", 0.0), 2)])

            writer.writerow(["Relaxação Linear", _valor_ou_na(sol_inicial.get("relaxacao_linear", None), 2)])
            writer.writerow(["GAP Relaxação (%)", _valor_ou_na(sol_inicial.get("gap_relaxacao", None), 2)])

            writer.writerow(["Custo Total", _valor_ou_na(sol_inicial.get("custo_total", 0.0), 2)])
            writer.writerow(["Custo Atendimento", _valor_ou_na(sol_inicial.get("custo_alocacao", 0.0), 2)])
            writer.writerow(["Custo Transporte", _valor_ou_na(sol_inicial.get("custo_transporte", 0.0), 2)])
            writer.writerow(["Frete Morto", _valor_ou_na(sol_inicial.get("frete_morto_total", 0.0), 2)])
            writer.writerow(["Custo Não Alocação", _valor_ou_na(sol_inicial.get("custo_nao_alocacao", 0.0), 2)])

            writer.writerow(["Peso Não Alocado", _valor_ou_na(sol_inicial.get("peso_nao_alocado", 0.0))])
            writer.writerow(["Volume Não Alocado", _valor_ou_na(sol_inicial.get("volume_nao_alocado", 0.0))])

            writer.writerow(["Veículos Ativos", _valor_ou_na(sol_inicial.get("veiculos_ativos", 0))])
            writer.writerow(["Veículos Inativos", _valor_ou_na(sol_inicial.get("veiculos_inativos", 0))])
            writer.writerow(["UMs Alocadas", _valor_ou_na(sol_inicial.get("ums_alocadas", 0))])
            writer.writerow(["UMs Não Alocadas", _valor_ou_na(sol_inicial.get("ums_nao_alocadas", 0))])

            writer.writerow([])
            writer.writerow(["VEÍCULOS ATIVOS (SOLUÇÃO INICIAL)"])
            writer.writerow([
                "ID", "Tipo", "Destino", "Cargas",
                "Peso Total (kg)", "Capacidade (kg)", "Utilização (%)",
                "Volume Total", "Capacidade (m3)", "Utilização (%)",
                "Frete Morto (R$)"
            ])

            alocacoes_ini = sol_inicial.get("alocacoes", []) or []
            alocacoes_ini = sorted(alocacoes_ini, key=lambda a: int(a.get("veiculo_id", 0)))

            for a in alocacoes_ini:
                v_id = a.get("veiculo_id", "")
                v = veiculos_id.get(v_id, {})
                peso_total = a.get("peso_total", 0.0)
                cap_peso = a.get("capacidade_peso", v.get("capacidade_peso", 0.0))
                vol_total = a.get("volume_total", 0.0)
                cap_vol = a.get("capacidade_volume", v.get("capacidade_volume", 0.0))

                frete_v = _frete_morto_por_veiculo(beta_valor, cap_peso, peso_total)

                writer.writerow([
                    v_id,
                    a.get("veiculo_tipo", ""),
                    a.get("destino", ""),
                    ";".join(map(str, a.get("cargas", []) or [])),
                    _valor_ou_na(peso_total),
                    _valor_ou_na(cap_peso),
                    _valor_ou_na(a.get("taxa_utilizacao_peso", 0.0), 1),
                    _valor_ou_na(vol_total),
                    _valor_ou_na(cap_vol),
                    _valor_ou_na(a.get("taxa_utilizacao_volume", 0.0), 1),
                    _valor_ou_na(frete_v, 2)
                ])

            writer.writerow([])
            writer.writerow(["UNIDADES METÁLICAS NÃO ALOCADAS (SOLUÇÃO INICIAL)"])
            writer.writerow(["ID", "Tipo", "Peso (kg)", "Volume (m³)", "Destino", "Compatibilidade", "Motivo"])

            for um_id in ids_nao_alocados_inicial:
                um = ums_id.get(um_id, {})
                writer.writerow([
                    um_id,
                    um.get("tipo", ""),
                    _valor_ou_na(um.get("peso", "")),
                    _valor_ou_na(um.get("volume", "")),
                    um.get("destino", ""),
                    um.get("compatibilidade", ""),
                    _motivo_nao_alocada(um, veiculos)
                ])

    print(f"\n✅ Relatório de heurística salvo em: {caminho_completo}")

    
    
    
    nome_arquivo_resumo = "resumo_geral_heuristica.csv"
    caminho_completo_resumo = os.path.join(caminho_saida, nome_arquivo_resumo)

    arquivo_existe = os.path.exists(caminho_completo_resumo)

    with open(caminho_completo_resumo, mode='a', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file, delimiter=';')

        
        if not arquivo_existe:
            writer.writerow([
                "Instância",
                "Tempo (s)",
                "Custo Total (Inicial)", "Custo Total (Final)",
                "Custo Ativação (Inicial)", "Custo Ativação (Final)",
                "Custo Transporte (Inicial)", "Custo Transporte (Final)",
                "Frete Morto (Inicial)", "Frete Morto (Final)",
                "Custo Não Alocação (Inicial)", "Custo Não Alocação (Final)",
                "Veículos Ativos (Inicial)", "Veículos Ativos (Final)",
                "Veículos Inativos (Inicial)", "Veículos Inativos (Final)",
                "UMs Alocadas (Inicial)", "UMs Alocadas (Final)",
                "UMs Não Alocadas (Inicial)", "UMs Não Alocadas (Final)",
                "Peso Não Alocado (Inicial)", "Peso Não Alocado (Final)",
                "Volume Não Alocado (Inicial)", "Volume Não Alocado (Final)"
            ])

        
        if sol_inicial:
            writer.writerow([
                resultados.get('tipo_instancia'),
                _valor_ou_na(resultados.get('tempo_execucao', 0.0), 2),

                _valor_ou_na(sol_inicial.get('custo_total', 0.0), 2), _valor_ou_na(resultados.get('custo_total', 0.0), 2),
                _valor_ou_na(sol_inicial.get('custo_alocacao', 0.0), 2), _valor_ou_na(resultados.get('custo_alocacao', 0.0), 2),
                _valor_ou_na(sol_inicial.get('custo_transporte', 0.0), 2), _valor_ou_na(resultados.get('custo_transporte', 0.0), 2),
                _valor_ou_na(sol_inicial.get('frete_morto_total', 0.0), 2), _valor_ou_na(resultados.get('frete_morto_total', 0.0), 2),
                _valor_ou_na(sol_inicial.get('custo_nao_alocacao', 0.0), 2), _valor_ou_na(resultados.get('custo_nao_alocacao', 0.0), 2),

                sol_inicial.get('veiculos_ativos', 0), resultados.get('veiculos_ativos', 0),
                sol_inicial.get('veiculos_inativos', 0), resultados.get('veiculos_inativos', 0),

                sol_inicial.get('ums_alocadas', 0), resultados.get('ums_alocadas', 0),
                sol_inicial.get('ums_nao_alocadas', 0), resultados.get('ums_nao_alocadas', 0),

                _valor_ou_na(sol_inicial.get('peso_nao_alocado', 0.0)), _valor_ou_na(resultados.get('peso_nao_alocado', 0.0)),
                _valor_ou_na(sol_inicial.get('volume_nao_alocado', 0.0)), _valor_ou_na(resultados.get('volume_nao_alocado', 0.0))
            ])
        else:
            
            writer.writerow([
                resultados.get('tipo_instancia'),
                _valor_ou_na(resultados.get('tempo_execucao', 0.0), 2),

                "N/A", _valor_ou_na(resultados.get('custo_total', 0.0), 2),
                "N/A", _valor_ou_na(resultados.get('custo_alocacao', 0.0), 2),
                "N/A", _valor_ou_na(resultados.get('custo_transporte', 0.0), 2),
                "N/A", _valor_ou_na(resultados.get('frete_morto_total', 0.0), 2),
                "N/A", _valor_ou_na(resultados.get('custo_nao_alocacao', 0.0), 2),

                "N/A", resultados.get('veiculos_ativos', 0),
                "N/A", resultados.get('veiculos_inativos', 0),

                "N/A", resultados.get('ums_alocadas', 0),
                "N/A", resultados.get('ums_nao_alocadas', 0),

                "N/A", _valor_ou_na(resultados.get('peso_nao_alocado', 0.0)),
                "N/A", _valor_ou_na(resultados.get('volume_nao_alocado', 0.0))
            ])

    print(f"✅ Resumo geral (append) salvo em: {caminho_completo_resumo}")


def executar_todas_instancias_na_pasta(pasta=INSTANCIAS, out_folder="Resultados - Heuristica"):
    
    pasta_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), pasta)
    if not os.path.isdir(pasta_abs):
        print(f"❌ Pasta de instâncias não encontrada: {pasta_abs}")
        return
    
    arquivos = [f for f in os.listdir(pasta_abs) if f.endswith('.csv') and not f.startswith('00_')]
    if not arquivos:
        print("❌ Nenhuma instância CSV encontrada na pasta.")
        return
    
    os.makedirs(out_folder, exist_ok=True)
    resultados_totais = []
    instancias_originais = []
    solucoes_iniciais = []  

    for a in arquivos:
        caminho = os.path.join(pasta_abs, a)
        print("\n" + "="*60)
        print(f"Executando heurística na instância: {a}")
        print("="*60)
        start = time.time()

        resultado = executar_instancia_heuristica(caminho, num_reinicios=NUM_REINICIOS, time_limit=TIMEOUT)
        dur = time.time() - start
        print(f"Resultado: custo={resultado['custo']:.2f} tempo_total_exec={dur:.1f}s")

        
        resultado_estruturado = estruturar_resultados_heuristica(resultado)
        
        
        sol_inicial_estruturada = None
        
        
        sol_inicial = resultado.get('solucao_inicial', None)
        instancia = resultado['instancia']

        if sol_inicial is not None:
            
            sol_inicial_estruturada = estruturar_resultados_heuristica(
                {
                    'solucao': sol_inicial,
                    'instancia': instancia,
                    'nome_instancia': resultado['nome_instancia'],
                    'tempo_exec': resultado['tempo_exec'],
                    'custo': custo_total(sol_inicial, instancia)['componentes_custo']['total']
                }
            )
        else:
            sol_inicial_estruturada = None  

        
        solucoes_iniciais.append(sol_inicial_estruturada)

        if resultado_estruturado:
            resultado_estruturado['nome_instancia'] = a.replace('.csv', '')
            resultados_totais.append(resultado_estruturado)
            instancias_originais.append(resultado['instancia'])

            
            pasta_vis = os.path.join(os.path.dirname(__file__), INSTANCIAS, 'Resultados - Heuristica', 'Visualizacoes', resultado_estruturado['nome_instancia'])
            gerar_visualizacoes(resultado_estruturado, resultado['instancia'], pasta_vis)
            print(f"✅ Visualizações salvas em: {pasta_vis}")

            
            imprimir_resultados_detalhados_heuristica(resultado_estruturado)
        else:
            print("❌ Não foi possível estruturar os resultados.")

        
        if resultados_totais:
            
            if len(solucoes_iniciais) < len(resultados_totais):
                
                solucoes_iniciais.extend([None] * (len(resultados_totais) - len(solucoes_iniciais)))
            
            exportar_resultados_csv_heuristica(resultados_totais, instancias_originais, solucoes_iniciais, resultado_estruturado)
            print(f"\n✅ Relatórios e visualizações salvos em: {out_folder}")


def plot_distribuicao_alocacao(resultados, instancia, pasta_saida, nome_base):
    plt.figure(figsize=(16, 10))
    ax = plt.gca()

    um_width = 0.7
    um_height = 0.8
    espacamento_vertical = 1.5
    margin_left = 3.0
    ums_por_linha = 10

    
    tipos_um = sorted(set(um['tipo'] for um in instancia['ums']))
    cores_ums = [CORES_PASTEL['azul_claro'], CORES_PASTEL['verde_claro'], 
                 CORES_PASTEL['laranja_claro'], CORES_PASTEL['rosa_claro'],
                 CORES_PASTEL['roxo_claro'], CORES_PASTEL['amarelo_claro'],
                 CORES_PASTEL['lavanda'], CORES_PASTEL['menta'],
                 CORES_PASTEL['pessego'], CORES_PASTEL['lilas'],
                 CORES_PASTEL['azul_ceu'], CORES_PASTEL['salmao_claro']]
    cor_um = {tipo: cores_ums[i % len(cores_ums)] 
              for i, tipo in enumerate(tipos_um)}

    
    tipos_veiculos = sorted(set(v['tipo'] for v in instancia['veiculos']))
    cores_veiculos = [CORES_PASTEL['azul_medio'], CORES_PASTEL['verde_medio'],
                      CORES_PASTEL['lavanda'], CORES_PASTEL['pessego'],
                      CORES_PASTEL['menta'], CORES_PASTEL['lilas']]
    cor_veiculo = {tipo: cores_veiculos[i % len(cores_veiculos)] 
                   for i, tipo in enumerate(tipos_veiculos)}

    
    cor_regiao = CORES_PASTEL['cinza_claro']

    y_pos = 0
    ums_alocadas = set()

    
    alocacoes_por_regiao = {}
    for aloc in resultados['alocacoes']:
        regiao = aloc['destino']
        if regiao not in alocacoes_por_regiao:
            alocacoes_por_regiao[regiao] = []
        alocacoes_por_regiao[regiao].append(aloc)

    
    regioes = sorted(alocacoes_por_regiao.keys())  

    
    for regiao in regioes:
        if regiao not in alocacoes_por_regiao:
            continue
            
        
        ax.text(margin_left - 2, y_pos, f'Região: {regiao}', 
                ha='left', va='center', fontsize=12, weight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor=cor_regiao, alpha=0.5))
        
        y_pos -= 1.5

        
        for aloc in alocacoes_por_regiao[regiao]:
            veic_id = aloc['veiculo_id']
            veic_tipo = aloc['veiculo_tipo']
            ums = aloc['cargas']
            tipos_um_veiculo = aloc['tipos_um']  
            
            
            num_linhas = (len(ums) + ums_por_linha - 1) // ums_por_linha
            altura_veiculo = 1.0 + num_linhas * 1.0

            
            ax.add_patch(patches.Rectangle(
                (margin_left, y_pos - altura_veiculo/2),
                width=ums_por_linha,
                height=altura_veiculo,
                facecolor=cor_veiculo[veic_tipo],
                alpha=0.3,
                edgecolor='gray',
                linewidth=1.0
            ))

            
            ax.text(margin_left - 0.5, y_pos,
                   f'V{veic_id} ({veic_tipo})\n{len(ums)} UMs\n{aloc["taxa_utilizacao_peso"]:.1f}%',
                   ha='right', va='center', fontsize=9)

            
            for i, (um_id, um_tipo) in enumerate(zip(ums, tipos_um_veiculo)):
                linha = i // ums_por_linha
                coluna = i % ums_por_linha
                
                x_pos = margin_left + coluna
                y_um = y_pos - altura_veiculo/2 + (linha + 0.6)
                
                ax.add_patch(patches.Rectangle(
                    (x_pos, y_um), um_width, um_height,
                    facecolor=cor_um[um_tipo],  
                    edgecolor='gray', linewidth=0.6, alpha=0.9
                ))
                ax.text(x_pos + um_width/2, y_um + um_height/2,
                       f'UM{um_id}', ha='center', va='center', fontsize=6)

                ums_alocadas.add(um_id)

            y_pos -= (altura_veiculo + espacamento_vertical)

        y_pos -= 1.0

    
    ums_nao_alocadas = [um for um in instancia['ums'] if um['id'] not in ums_alocadas]
    if ums_nao_alocadas:
        y_pos -= 1.0
        ax.text(margin_left - 2, y_pos, 'UMs Não Alocadas:', 
                ha='left', va='center', fontsize=11, weight='bold', color='red')
        
        y_pos -= 1.0
        for i, um in enumerate(ums_nao_alocadas):
            linha = i // ums_por_linha
            coluna = i % ums_por_linha
            
            x_pos = margin_left + coluna
            y_um = y_pos - linha * 1.2
            
            ax.add_patch(patches.Rectangle(
                (x_pos, y_um), um_width, um_height,
                facecolor=cor_um[um['tipo']],  
                edgecolor='red', linestyle='dashed', linewidth=1.0, alpha=0.8
            ))
            ax.text(x_pos + um_width/2, y_um + um_height/2,
                   f'UM{um["id"]}', ha='center', va='center', fontsize=6)

    
    ax.set_xlim(0, margin_left + ums_por_linha + 2)
    ax.set_ylim(y_pos - 2, 2)
    ax.axis('off')

    
    legend_elements = []
    
    
    for tipo, cor in cor_um.items():
        legend_elements.append(patches.Patch(facecolor=cor, label=f'UM {tipo}'))
    
    
    for tipo, cor in cor_veiculo.items():
        legend_elements.append(patches.Patch(facecolor=cor, alpha=0.3, label=f'Veículo {tipo}'))

    ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.02, 0.5),
              fontsize=8, ncol=2)

    plt.title(f'Distribuição de Cargas - Cores por Tipo de UM - {nome_base}', fontsize=14)
    plt.tight_layout()
    
    caminho = os.path.join(pasta_saida, f"{nome_base}_alocacao_por_regiao.png")
    plt.savefig(caminho, dpi=300, bbox_inches='tight')
    plt.close()

def plot_tempo_execucao(resultados, pasta_saida, nome_base):
    rcParams.update({'font.size': 12})
    plt.figure(figsize=(10, 6))
    plt.bar(nome_base, resultados['tempo_execucao'], 
            color='#AEC6CF', alpha=0.8)
    plt.axhline(y=TIMEOUT, color='#FFB7B2',
                linestyle='--', label='Timeout', linewidth=2)
    plt.ylabel('Tempo (segundos)', fontsize=12)
    plt.title('Tempo de Execução da Heurística', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.tight_layout()
    
    caminho = os.path.join(pasta_saida, f"{nome_base}_tempo_execucao.png")
    plt.savefig(caminho, dpi=300, bbox_inches='tight')
    plt.close()

def plot_gap_otimizacao(resultados, pasta_saida, nome_base):
    
    if resultados['gap_otimizacao'] is not None:
        import matplotlib.pyplot as plt
        from matplotlib import rcParams
        rcParams.update({'font.size': 12})
        
        plt.figure(figsize=(8, 5))
        plt.bar(nome_base, resultados['gap_otimizacao'], 
                color='#FFD8B1', alpha=0.8)
        plt.ylabel('GAP (%)', fontsize=12)
        plt.title('GAP de Otimização (Heurística = 0%)', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        caminho = os.path.join(pasta_saida, f"{nome_base}_gap_otimizacao.png")
        plt.savefig(caminho, dpi=300, bbox_inches='tight')
        plt.close()

def plot_utilizacao_veiculos(resultados, pasta_saida, nome_base):
    if not resultados['alocacoes']:
        return

    df = pd.DataFrame(resultados['alocacoes'])
    df = df.sort_values('veiculo_id')

    fig, ax = plt.subplots(figsize=(14, 7))
    bar_width = 0.25
    x = np.arange(len(df))

    bars1 = ax.bar(x - bar_width, df['peso_total'], bar_width, 
                   label='Peso Real', color=CORES_PASTEL['azul_claro'], alpha=0.8)
    bars2 = ax.bar(x, df['peso_minimo'], bar_width, 
                   label='Peso Mínimo', color=CORES_PASTEL['laranja_claro'], alpha=0.8)
    bars3 = ax.bar(x + bar_width, df['capacidade_peso'], bar_width, 
                   label='Capacidade', color=CORES_PASTEL['verde_claro'], alpha=0.8)

    for i, cap in enumerate(df['capacidade_peso']):
        ax.axhline(y=cap, xmin=(i - 0.4)/len(x), xmax=(i + 0.4)/len(x),
                  color=CORES_PASTEL['roxo_claro'], linestyle=':', alpha=0.7)

    ax.set_xlabel('Veículos (ID - Tipo - Região)')
    ax.set_ylabel('Peso (kg)')
    ax.set_title('Utilização de Capacidade dos Veículos')
    
    labels = [f"V{vID}\n{tipo}\n{reg}" 
              for vID, tipo, reg in zip(df['veiculo_id'], df['veiculo_tipo'], df['destino'])]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.legend()

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + max(df['capacidade_peso'])*0.01,
                       f'{height:.0f}', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_utilizacao_veiculos.png"), dpi=300)
    plt.close()

def plot_distribuicao_utilizacao(resultados, pasta_saida, nome_base):
    if not resultados['alocacoes']:
        return

    df = pd.DataFrame(resultados['alocacoes'])

    plt.figure(figsize=(12, 6))
    sns.histplot(data=df, x='taxa_utilizacao_peso', bins=10, kde=True, 
                 color=CORES_PASTEL['azul_claro'], alpha=0.7)
    plt.xlabel('Taxa de Utilização de Peso (%)')
    plt.ylabel('Número de Veículos')
    plt.title('Distribuição das Taxas de Utilização de Peso')
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_distribuicao_utilizacao.png"), dpi=300)
    plt.close()

def plot_ums_por_veiculo(resultados, pasta_saida, nome_base):
    if not resultados['alocacoes']:
        return

    df = pd.DataFrame(resultados['alocacoes'])
    df['num_cargas'] = df['cargas'].apply(len)

    tipos_unicos = df['veiculo_tipo'].unique()
    
    
    cores_tipos = CORES_PASTEL_8 + [CORES_PASTEL['azul_ceu'], CORES_PASTEL['salmao_claro'], 
                                   CORES_PASTEL['pessego'], CORES_PASTEL['lilas']]
    
    
    if len(tipos_unicos) > len(cores_tipos):
        
        import matplotlib.colors as mcolors
        cores_adicionais = list(mcolors.TABLEAU_COLORS.values())[:len(tipos_unicos) - len(cores_tipos)]
        cores_tipos.extend(cores_adicionais)
    
    
    cores_tipos = cores_tipos[:len(tipos_unicos)]
    paleta_pastel = dict(zip(tipos_unicos, cores_tipos))

    plt.figure(figsize=(12, 6))
    
    try:
        sns.barplot(data=df, x='veiculo_id', y='num_cargas',
                    hue='veiculo_tipo', dodge=False, palette=paleta_pastel, alpha=0.8)
    except ValueError as e:
        
        print(f"⚠️ Erro na paleta: {e}. Usando paleta padrão.")
        sns.barplot(data=df, x='veiculo_id', y='num_cargas',
                    hue='veiculo_tipo', dodge=False, alpha=0.8)
    
    plt.xlabel('ID do Veículo', fontsize=12)
    plt.ylabel('Número de UMs Transportadas', fontsize=12)
    plt.title('Distribuição de UMs por Veículo', fontsize=14, fontweight='bold')
    
    
    plt.legend(title='Tipos de Veículos', title_fontsize=11, fontsize=10,
               loc='upper right', framealpha=0.9)
    
    
    for i, (idx, row) in enumerate(df.iterrows()):
        plt.text(i, row['num_cargas'] + 0.1, str(row['num_cargas']),
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_ums_por_veiculo.png"), dpi=300)
    plt.close()

def plot_composicao_custos(resultados, pasta_saida, nome_base):
    componentes = ['Ativação Veículos', 'Transporte', 'Frete Morto', 'Não Alocação']
    valores = [
        resultados['custo_alocacao'],
        resultados['custo_transporte'],
        resultados['frete_morto_total'],
        resultados['custo_nao_alocacao']
    ]

    
    cores = [CORES_PASTEL['azul_medio'], CORES_PASTEL['azul_claro'], 
             CORES_PASTEL['laranja_claro'], CORES_PASTEL['verde_claro']]

    plt.figure(figsize=(10, 8))
    
    
    plt.pie(valores, labels=componentes, autopct='%1.1f%%', colors=cores,
            startangle=90, textprops={'fontsize': 10})
    plt.title('Composição do Custo Total', fontsize=12, fontweight='bold')
    
    
    total = sum(valores)
    plt.text(0.9, -1.2, f'Total: R$ {total:,.2f}', 
             ha='center', va='center', fontsize=11, fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.3", facecolor=CORES_PASTEL['cinza_claro'], alpha=0.7))
    
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_composicao_custos.png"), dpi=300)
    plt.close()

def plot_custo_por_componente(resultados, pasta_saida, nome_base):
    componentes = ['Ativação Veículos', 'Transporte', 'Frete Morto', 'Não Alocação']
    valores = [
        resultados['custo_alocacao'],
        resultados['custo_transporte'],
        resultados['frete_morto_total'],
        resultados['custo_nao_alocacao']
    ]

    cores = [CORES_PASTEL['azul_medio'], CORES_PASTEL['azul_claro'], 
             CORES_PASTEL['laranja_claro'], CORES_PASTEL['verde_claro']]

    plt.figure(figsize=(12, 7))
    bars = plt.bar(componentes, valores, color=cores, alpha=0.8, edgecolor='gray', linewidth=0.5)
    plt.ylabel('Custo (R$)', fontsize=12)
    plt.title('Custo por Componente', fontsize=14, fontweight='bold')
    
    
    for bar in bars:
        height = bar.get_height()
        if height > 0:  
            plt.text(bar.get_x() + bar.get_width()/2., height + max(valores)*0.01,
                    f'R$ {height:,.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    
    total = sum(valores)
    plt.axhline(y=total, color=CORES_PASTEL['rosa_claro'], linestyle='--', alpha=0.7, linewidth=2)
    plt.text(len(componentes) - 0.5, total + max(valores)*0.02, f'Total: R$ {total:,.2f}', 
             ha='right', va='bottom', fontsize=11, fontweight='bold',
             bbox=dict(boxstyle="round,pad=0.3", facecolor=CORES_PASTEL['cinza_claro'], alpha=0.7))

    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_custo_por_componente.png"), dpi=300)
    plt.close()

def plot_penalidades_nao_alocacao(resultados, pasta_saida, nome_base):
    if resultados['ums_nao_alocadas'] == 0:
        return

    dados = {
        'Peso Não Alocado': resultados['peso_nao_alocado'],
        'Volume Não Alocado': resultados['volume_nao_alocado']
    }

    cores = [CORES_PASTEL['laranja_claro'], CORES_PASTEL['roxo_claro']]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(dados.keys(), dados.values(), color=cores, alpha=0.8)
    plt.ylabel('Valor Total')
    plt.title('Recursos Não Alocados')

    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + max(dados.values())*0.01,
                f'{height:,.2f}', ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_penalidades_nao_alocacao.png"), dpi=300)
    plt.close()

def plot_heatmap_compatibilidade(instancia, pasta_saida, nome_base):
    ums_por_tipo = {}
    for um in instancia['ums']:
        tipo = um['tipo']
        if tipo not in ums_por_tipo:
            ums_por_tipo[tipo] = []
        ums_por_tipo[tipo].append(um)

    compat_data = []
    tipos_um = sorted(ums_por_tipo.keys())
    tipos_veiculo = sorted(set(v['tipo'] for v in instancia['veiculos']))

    for tipo_um in tipos_um:
        compat_por_tipo = []
        for tipo_veic in tipos_veiculo:
            compats = []
            for um in ums_por_tipo[tipo_um]:
                compat = 1 if tipo_veic in um['compatibilidade'].split(',') else 0
                compats.append(compat)
            taxa = sum(compats) / len(compats) if compats else 0
            compat_por_tipo.append(taxa)
        compat_data.append(compat_por_tipo)

    df = pd.DataFrame(
        compat_data,
        index=[f"{tipo}\n({len(ums_por_tipo[tipo])} UMs)" for tipo in tipos_um],
        columns=[f"{tipo}" for tipo in tipos_veiculo]
    )

    plt.figure(figsize=(12, 8))
    sns.heatmap(df, annot=True, fmt='.2f', cmap="YlGnBu_r", 
                cbar_kws={'label': 'Taxa de Compatibilidade'},
                vmin=0, vmax=1)
    plt.title('Matriz de Compatibilidade: Tipos de UM x Tipos de Veículo')
    plt.xlabel('Tipos de Veículo')
    plt.ylabel('Tipos de UM (quantidade)')
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_heatmap_compatibilidade.png"), dpi=300)
    plt.close()

def plot_distribuicao_ums_nao_alocadas(instancia, resultados, pasta_saida, nome_base):
    alocados_ids = set()
    for aloc in resultados['alocacoes']:
        alocados_ids.update(aloc['cargas'])

    ums_nao_alocadas = [um for um in instancia['ums'] if um['id'] not in alocados_ids]

    if not ums_nao_alocadas:
        return

    df = pd.DataFrame(ums_nao_alocadas)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    sns.boxplot(data=df, y='peso', ax=axes[0], color=CORES_PASTEL['azul_claro'])
    axes[0].set_title('Distribuição de Peso das UMs Não Alocadas')

    sns.boxplot(data=df, y='volume', ax=axes[1], color=CORES_PASTEL['verde_claro'])
    axes[1].set_title('Distribuição de Volume das UMs Não Alocadas')

    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_distribuicao_ums_nao_alocadas.png"), dpi=300)
    plt.close()

def plot_distribuicao_por_regiao(resultados, instancia, pasta_saida, nome_base):
    if not resultados['alocacoes']:
        return

    
    regioes_ordenadas = sorted(instancia['regioes'], key=lambda x: int(x[1:]) if x[1:].isdigit() else x)
    
    ums_por_regiao = {}
    veiculos_por_regiao = {}
    
    for aloc in resultados['alocacoes']:
        regiao = aloc['destino']
        if regiao not in ums_por_regiao:
            ums_por_regiao[regiao] = 0
            veiculos_por_regiao[regiao] = 0
        ums_por_regiao[regiao] += len(aloc['cargas'])
        veiculos_por_regiao[regiao] += 1

    ums_alocadas_ids = set()
    for aloc in resultados['alocacoes']:
        ums_alocadas_ids.update(aloc['cargas'])
    
    ums_nao_alocadas_por_regiao = {}
    for um in instancia['ums']:
        if um['id'] not in ums_alocadas_ids:
            regiao = um['destino']
            if regiao not in ums_nao_alocadas_por_regiao:
                ums_nao_alocadas_por_regiao[regiao] = 0
            ums_nao_alocadas_por_regiao[regiao] += 1

    
    ums_alocadas = [ums_por_regiao.get(r, 0) for r in regioes_ordenadas]
    ums_nao_alocadas = [ums_nao_alocadas_por_regiao.get(r, 0) for r in regioes_ordenadas]
    veiculos_counts = [veiculos_por_regiao.get(r, 0) for r in regioes_ordenadas]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    
    x = np.arange(len(regioes_ordenadas))
    bar_width = 0.35
    
    bars1 = ax1.bar(x - bar_width/2, ums_alocadas, bar_width, 
                    label='UMs Alocadas', color=CORES_PASTEL['verde_claro'], alpha=0.8)
    bars2 = ax1.bar(x + bar_width/2, ums_nao_alocadas, bar_width, 
                    label='UMs Não Alocadas', color=CORES_PASTEL['rosa_claro'], alpha=0.8)
    
    ax1.set_xlabel('Regiões', fontsize=12)
    ax1.set_ylabel('Quantidade de UMs', fontsize=12)
    ax1.set_title('Distribuição de UMs por Região', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(regioes_ordenadas, fontsize=11)
    ax1.legend(fontsize=10)
    ax1.grid(axis='y', alpha=0.3)
    
    
    max_ums = max(ums_alocadas + ums_nao_alocadas) if (ums_alocadas + ums_nao_alocadas) else 1
    offset = max_ums * 0.05  
    
    for i, (a, n) in enumerate(zip(ums_alocadas, ums_nao_alocadas)):
        if a > 0:
            
            ax1.text(i - bar_width/2, a + offset, str(a), 
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
        if n > 0:
            ax1.text(i + bar_width/2, n + offset, str(n), 
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    
    ax1.set_ylim(0, max_ums + offset * 3)

    
    bars3 = ax2.bar(regioes_ordenadas, veiculos_counts, 
                    color=CORES_PASTEL['azul_claro'], alpha=0.8)
    ax2.set_xlabel('Regiões', fontsize=12)
    ax2.set_ylabel('Quantidade de Veículos', fontsize=12)
    ax2.set_title('Veículos Ativos por Região', fontsize=14, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    
    
    max_veiculos = max(veiculos_counts) if veiculos_counts else 1
    offset_veic = max_veiculos * 0.1  
    
    for i, v in enumerate(veiculos_counts):
        if v > 0:
            ax2.text(i, v + offset_veic, str(v), 
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    
    ax2.set_ylim(0, max_veiculos + offset_veic * 2)

    
    total_ums_alocadas = sum(ums_alocadas)
    total_ums_nao_alocadas = sum(ums_nao_alocadas)
    total_veiculos = sum(veiculos_counts)
    
    
    info_text = f"Totais:\nUMs Alocadas: {total_ums_alocadas}\nUMs Não Alocadas: {total_ums_nao_alocadas}\nVeículos: {total_veiculos}"
    fig.text(0.02, 0.02, info_text, fontsize=10, 
             bbox=dict(boxstyle="round,pad=0.3", facecolor=CORES_PASTEL['cinza_claro'], alpha=0.7))

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)  
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_distribuicao_regioes.png"), 
                dpi=300, bbox_inches='tight')
    plt.close()

def plot_analise_frete_morto(resultados, pasta_saida, nome_base):
    if not resultados['alocacoes']:
        return

    df = pd.DataFrame(resultados['alocacoes'])
    df['frete_morto_kg'] = df['capacidade_peso'] - df['peso_total']
    df['frete_morto_percentual'] = (df['frete_morto_kg'] / df['capacidade_peso']) * 100
    df['frete_morto_percentual'] = df['frete_morto_percentual'].clip(lower=0)

    
    tipos_veiculos = sorted(df['veiculo_tipo'].unique())
    cores_tipos = CORES_PASTEL_8[:len(tipos_veiculos)]
    cor_por_tipo = dict(zip(tipos_veiculos, cores_tipos))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    
    bars1 = []
    labels1 = []
    for i, (idx, row) in enumerate(df.iterrows()):
        cor = cor_por_tipo.get(row['veiculo_tipo'], CORES_PASTEL['cinza_claro'])
        
        
        if i == df[df['veiculo_tipo'] == row['veiculo_tipo']].index[0]:
            label = row['veiculo_tipo']
        else:
            label = ""
            
        bar = ax1.bar(i, row['frete_morto_kg'], 
                      color=cor, alpha=0.8, label=label)
        bars1.append(bar)

    ax1.set_xlabel('Veículos')
    ax1.set_ylabel('Frete Morto (kg)')
    ax1.set_title('Frete Morto por Veículo (kg)')
    ax1.set_xticks(range(len(df)))
    ax1.set_xticklabels([f"V{id}" for id in df['veiculo_id']], rotation=45, ha='right')
    
    
    bars2 = []
    for i, (idx, row) in enumerate(df.iterrows()):
        cor = cor_por_tipo.get(row['veiculo_tipo'], CORES_PASTEL['cinza_claro'])
        
        bar = ax2.bar(i, row['frete_morto_percentual'],
                      color=cor, alpha=0.8)
        bars2.append(bar)

    ax2.set_xlabel('Veículos')
    ax2.set_ylabel('Frete Morto (%)')
    ax2.set_title('Frete Morto por Veículo (% da Capacidade)')
    ax2.set_xticks(range(len(df)))
    ax2.set_xticklabels([f"V{id}" for id in df['veiculo_id']], rotation=45, ha='right')

    
    for ax, is_kg in [(ax1, True), (ax2, False)]:
        for i, (idx, row) in enumerate(df.iterrows()):
            height = row['frete_morto_kg'] if is_kg else row['frete_morto_percentual']
            if height > 0:
                max_val = max(df['frete_morto_kg']) if is_kg else max(df['frete_morto_percentual'])
                offset = max_val * 0.02
                ax.text(i, height + offset,
                       f'{height:.1f}{"kg" if is_kg else "%"}', 
                       ha='center', va='bottom', fontsize=8)

    
    handles, labels = ax1.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))  
    if by_label:
        fig.legend(by_label.values(), by_label.keys(), 
                   loc='center right', bbox_to_anchor=(1.15, 0.5),
                   title='Tipos de Veículo')

    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_analise_frete_morto.png"), 
                dpi=300, bbox_inches='tight')
    plt.close()

def gerar_visualizacoes(resultados, instancia, pasta_saida):
    os.makedirs(pasta_saida, exist_ok=True)
    nome_base = resultados['tipo_instancia']

    
    plot_tempo_execucao(resultados, pasta_saida, nome_base)
    plot_gap_otimizacao(resultados, pasta_saida, nome_base)

    
    plot_utilizacao_veiculos(resultados, pasta_saida, nome_base)
    plot_distribuicao_utilizacao(resultados, pasta_saida, nome_base)
    plot_ums_por_veiculo(resultados, pasta_saida, nome_base)
    plot_distribuicao_alocacao(resultados, instancia, pasta_saida, nome_base)
    plot_distribuicao_por_regiao(resultados, instancia, pasta_saida, nome_base)

    
    plot_composicao_custos(resultados, pasta_saida, nome_base)
    plot_custo_por_componente(resultados, pasta_saida, nome_base)
    plot_penalidades_nao_alocacao(resultados, pasta_saida, nome_base)
    plot_analise_frete_morto(resultados, pasta_saida, nome_base)

    
    if resultados['ums_nao_alocadas'] > 0:
        plot_heatmap_compatibilidade(instancia, pasta_saida, nome_base)
        plot_distribuicao_ums_nao_alocadas(instancia, resultados, pasta_saida, nome_base)

if __name__ == "__main__":
    executar_todas_instancias_na_pasta()