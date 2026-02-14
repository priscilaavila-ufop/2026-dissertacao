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
from time import perf_counter
import traceback
import inspect

INSTANCIAS = r"C:\Users\prisc\Workspace\VERSAO_OFICIAL\Instancias\Grupo2\Instancias_20v"
OUT_FOLDER = r"C:\Users\prisc\Workspace\VERSAO_OFICIAL\Instancias\Grupo2\Instancias_20v\Resultados - Heurística - 20260209"
N_SEMENTES = 30
NUM_REINICIOS = 5
MAX_SEM_MELHORA = 20
TIMEOUT = 300
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
CACHE_COMPATIBILIDADE = {}
VERBOSE = False
PROFILE = True
CTX = "NONE"

_prof = globals().get("_prof", {})
_prof.setdefault("viz",{})

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

_prof = {
    "t_delta": 0.0,
    "n_delta": 0,
    "t_alocar": 0.0,
    "n_alocar": 0,
}

def carregar_dados(caminho_arquivo):

    import re

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

    max_reg_idx = 0
    destinos_encontrados = set(um["destino"] for um in dados['ums'])

    for dest in destinos_encontrados:

        match = re.search(r'(\d+)', str(dest))
        if match:
            idx = int(match.group(1))
            if idx > max_reg_idx:
                max_reg_idx = idx

    if max_reg_idx > 0:
        regioes_ordenadas = [f"R{i}" for i in range(1, max_reg_idx + 1)]
    else:

        regioes_ordenadas = sorted(list(destinos_encontrados))

    dados['regioes'] = regioes_ordenadas

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

            tipos_ordenados = []
            seen = set()
            for v in dados['veiculos']:
                t = v['tipo']
                if t not in seen:
                    tipos_ordenados.append(t)
                    seen.add(t)

            for um in dados['ums']:
                if um['custo_str'] and ',' in um['custo_str']:
                    custos = [float(custo.strip()) for custo in um['custo_str'].split(',')]
                    um['custos_por_tipo'] = {}


                    for i, tipo in enumerate(tipos_ordenados):
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

    CACHE_COMPATIBILIDADE.clear()

    for um in dados['ums']:
        comp_str = um.get('compatibilidade', '')
        if not comp_str or not comp_str.strip():

            CACHE_COMPATIBILIDADE[um['id']] = set()
        else:

            tipos_permitidos = {t.strip().lower() for t in comp_str.split(',') if t.strip()}
            CACHE_COMPATIBILIDADE[um['id']] = tipos_permitidos

    return dados

def um_compatível_com_veiculo(um, veiculo):

    dest_veiculo = veiculo.get("destino")
    dest_um = um.get("destino")

    if dest_veiculo and dest_um and str(dest_veiculo) != str(dest_um):
        return False

    tipos_permitidos = CACHE_COMPATIBILIDADE.get(um['id'])

    if not tipos_permitidos:
        return True

    tipo_v = veiculo['tipo'].strip().lower()
    return tipo_v in tipos_permitidos

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

    if PROFILE:
        t0 = perf_counter()

    _prof.setdefault("alocar_por_ctx", {})
    _prof["alocar_por_ctx"][CTX] = _prof["alocar_por_ctx"].get(CTX, 0) + 1

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

    if PROFILE:
        _prof["t_alocar"] += perf_counter() - t0
        _prof["n_alocar"] += 1

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

def delta_insercao(sol, instancia, um, v):

    if PROFILE:
        t0 = perf_counter()

    vid = v['id']
    dados = sol['veiculo_dados'][vid]
    comp = sol.get('componentes_custo', {})
    beta = float(comp.get('beta', 1.0))





    val = um.get('custos_por_tipo', {}).get(v['tipo'], 0.0)


    if isinstance(val, (int, float)):
        custo_unit = float(val)


    elif isinstance(val, str):
        s = val.strip()


        if ',' in s:

            tipos = instancia.get('tipos_ordenados')
            if not tipos:
                tipos = []
                seen = set()
                for vv in instancia.get('veiculos', []):
                    t = vv.get('tipo')
                    if t is not None and t not in seen:
                        tipos.append(t)
                        seen.add(t)

            partes = [p.strip() for p in s.split(',') if p.strip()]
            try:
                idx = tipos.index(v['tipo'])
                custo_unit = float(partes[idx]) if idx < len(partes) else 0.0
            except ValueError:
                custo_unit = 0.0


        else:
            custo_unit = float(s) if s else 0.0

    else:
        custo_unit = 0.0







    penal_um = float(um.get('penalidade', 0.0))
    delta_nao_aloc = -penal_um if um['id'] in sol.get('nao_alocadas', set()) else 0.0













    delta_ativ = 0.0
    if not dados.get('ativo', False):
        reg = dados.get('regiao')
        if reg is None:
            reg = str(um.get('destino')) if um.get('destino') is not None else None

        if reg is not None:
            base = v.get('custos_por_regiao', {}).get(str(reg), v.get('custo', 0.0))
        else:
            base = v.get('custo', 0.0)


        if isinstance(base, str):
            s = base.strip()
            if ',' in s:
                base = s.split(',')[0].strip()
            base = float(base) if base else 0.0
        else:
            base = float(base)

        delta_ativ = base



    cap = float(v.get('capacidade_peso', 0.0))
    peso_antes = float(dados.get('peso_usado', 0.0))
    peso_depois = peso_antes + float(um.get('peso', 0.0))

    oci_antes = max(0.0, cap - peso_antes)
    oci_depois = max(0.0, cap - peso_depois)

    frete_antes = beta * oci_antes
    frete_depois = beta * oci_depois
    delta_frete = frete_depois - frete_antes

    out = (delta_ativ + custo_unit + delta_frete + delta_nao_aloc)

    if PROFILE:
        _prof["t_delta"] += perf_counter() - t0
        _prof["n_delta"] += 1

    return out

def gerar_solucao_gulosa(instancia, ordem=None):
    
    _prof["t_delta"] = 0.0
    _prof["n_delta"] = 0
    _prof["t_alocar"] = 0.0
    _prof["n_alocar"] = 0

    solucao = criar_estado_inicial(instancia)
    custo_total(solucao, instancia)

    veiculos = instancia['veiculos']
    ums_list = list(instancia['ums'])

    criterio = ordem
    seed_empate = None

    if isinstance(ordem, tuple) and len(ordem) == 2:
        criterio, seed_empate = ordem

    if criterio is None:
        criterio = 'penalidade'


    rnd = random.Random(seed_empate if seed_empate is not None else RANDOM_SEED)


    if criterio in ('penalidade', 'peso', 'volume'):
        if criterio == 'penalidade':
            ums_list.sort(key=lambda u: (-float(u.get('penalidade', 1.0)), rnd.random()))
        elif criterio == 'peso':
            ums_list.sort(key=lambda u: (-float(u.get('peso', 0.0)), rnd.random()))
        else:
            ums_list.sort(key=lambda u: (-float(u.get('volume', 0.0)), rnd.random()))

    elif isinstance(criterio, int):
        rnd = random.Random(criterio)
        rnd.shuffle(ums_list)

    else:

        rnd.shuffle(ums_list)


    ums_map = instancia.get('ums_id', None)
    veiculos_map = instancia.get('veiculos_id', None)
    if ums_map is None:
        ums_map = {u['id']: u for u in instancia['ums']}
    if veiculos_map is None:
        veiculos_map = {v['id']: v for v in instancia['veiculos']}



    rcl_k = int(instancia.get('gulosa_rcl_k', 3) or 3)
    if rcl_k < 1:
        rcl_k = 1


    for um in ums_list:

        destino_um = um.get('destino', None)
        destino_um_norm = str(destino_um) if destino_um is not None else None


        candidatos_fixos = [
            v for v in veiculos
            if v['id'] in solucao['veiculo_dados']
            and solucao['veiculo_dados'][v['id']]['ativo']
            and len(solucao['veiculo_dados'][v['id']]['ums']) > 0
        ]


        candidatos_ativos = []
        for v in candidatos_fixos:
            vid = v['id']

            reg_v = solucao['veiculo_dados'][vid].get('regiao', None)
            reg_v_norm = str(reg_v) if reg_v is not None else None
            if reg_v_norm != destino_um_norm:
                continue

            if not um_compatível_com_veiculo(um, v):
                continue

            if (solucao['veiculo_dados'][vid]['peso_usado'] + um.get('peso', 0.0) > v.get('capacidade_peso', 0.0) + 1e-9):
                continue
            if (solucao['veiculo_dados'][vid]['volume_usado'] + um.get('volume', 0.0) > v.get('capacidade_volume', 0.0) + 1e-9):
                continue

            candidatos_ativos.append(v)


        candidatos_vazios = []
        if not candidatos_ativos:
            for v in veiculos:
                vid = v['id']


                if solucao['veiculo_dados'][vid]['ativo'] and len(solucao['veiculo_dados'][vid]['ums']) > 0:
                    continue

                if not um_compatível_com_veiculo(um, v):
                    continue

                if (solucao['veiculo_dados'][vid]['peso_usado'] + um.get('peso', 0.0) > v.get('capacidade_peso', 0.0) + 1e-9):
                    continue
                if (solucao['veiculo_dados'][vid]['volume_usado'] + um.get('volume', 0.0) > v.get('capacidade_volume', 0.0) + 1e-9):
                    continue

                candidatos_vazios.append(v)

        candidatos = candidatos_ativos if candidatos_ativos else candidatos_vazios
        if not candidatos:
            continue


        rank = []
        for v in candidatos:
            vid = v['id']

            delta_custo_total = delta_insercao(solucao, instancia, um, v)


            peso_disp = v.get('capacidade_peso', 0.0) - solucao['veiculo_dados'][vid]['peso_usado']
            vol_disp  = v.get('capacidade_volume', 0.0) - solucao['veiculo_dados'][vid]['volume_usado']

            peso_rel = peso_disp / (v.get('capacidade_peso', 1.0) + 1e-9)
            vol_rel  = vol_disp / (v.get('capacidade_volume', 1.0) + 1e-9)
            folga_score = peso_rel + vol_rel

            chave = (delta_custo_total, -folga_score)
            rank.append((chave, v))


        rank.sort(key=lambda x: x[0])


        k = min(rcl_k, len(rank))
        escolhidos = [rank[i][1] for i in range(k)]
        escolhido = rnd.choice(escolhidos)


        sucesso = alocar_um(solucao, um['id'], escolhido['id'], instancia)

        if not sucesso:

            for _, v in rank:
                if v['id'] == escolhido['id']:
                    continue
                if alocar_um(solucao, um['id'], v['id'], instancia):
                    sucesso = True
                    break

    return solucao

def realizar_troca_1x1(solucao, instancia):

    global CTX
    CTX = inspect.currentframe().f_code.co_name


    if PROFILE:
        _prof.setdefault("viz", {})
        _prof["viz"].setdefault(CTX, {"calls": 0, "t_total": 0.0, "alocar": 0, "t_alocar": 0.0})
        _prof["viz"][CTX]["calls"] += 1
        _t_ini = perf_counter()
        _n0 = _prof.get("n_alocar", 0)
        _t0 = _prof.get("t_alocar", 0.0)

    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, instancia)

    comp = solucao['componentes_custo']
    beta = float(comp.get('beta', 1.0))

    veiculos_map = instancia.get('veiculos_id', None)
    if veiculos_map is None:
        veiculos_map = {v['id']: v for v in instancia['veiculos']}

    ums_map = instancia.get('ums_id', None)
    if ums_map is None:
        ums_map = {u['id']: u for u in instancia['ums']}


    frete_por_v  = comp.get('frete_morto_por_veiculo', {})
    transp_por_v = comp.get('transporte_por_veiculo', {})

    def _norm(x):
        return str(x) if x is not None else None

    def _custo_unit(um_obj, tipo_veic):
        try:
            val = um_obj.get('custos_por_tipo', {}).get(tipo_veic, 0.0)
            if isinstance(val, str):
                s = val.strip()
                if ',' in s:
                    s = s.split(',')[0].strip()
                return float(s) if s else 0.0
            return float(val)
        except:
            return 0.0

    ativos = [vid for vid, dados in solucao['veiculo_dados'].items()
              if dados['ativo'] and len(dados['ums']) > 0]
    if len(ativos) < 2:

        return False

    melhor_mov = None
    melhor_delta = 0.0

    ativos_ordenados = sorted(ativos)

    for i in range(len(ativos_ordenados)):
        v1 = ativos_ordenados[i]
        d1 = solucao['veiculo_dados'][v1]
        ums_v1 = list(d1['ums'])
        if not ums_v1:
            continue

        v1_obj = veiculos_map[v1]
        tipo1 = v1_obj.get('tipo')
        cap_p1 = float(v1_obj.get('capacidade_peso', 0.0))
        cap_v1 = float(v1_obj.get('capacidade_volume', 0.0))
        min1 = float(v1_obj.get('carga_minima', 0.0))


        reg1 = _norm(d1.get('regiao'))
        if reg1 is None:
            reg1 = _norm(ums_map[ums_v1[0]].get('destino'))

        peso1_before = float(d1.get('peso_usado', 0.0))
        vol1_before  = float(d1.get('volume_usado', 0.0))
        transp1_before = float(transp_por_v.get(v1, 0.0))
        frete1_before  = float(frete_por_v.get(v1, 0.0))

        for j in range(i + 1, len(ativos_ordenados)):
            v2 = ativos_ordenados[j]
            d2 = solucao['veiculo_dados'][v2]
            ums_v2 = list(d2['ums'])
            if not ums_v2:
                continue

            v2_obj = veiculos_map[v2]
            tipo2 = v2_obj.get('tipo')
            cap_p2 = float(v2_obj.get('capacidade_peso', 0.0))
            cap_v2 = float(v2_obj.get('capacidade_volume', 0.0))
            min2 = float(v2_obj.get('carga_minima', 0.0))

            reg2 = _norm(d2.get('regiao'))
            if reg2 is None:
                reg2 = _norm(ums_map[ums_v2[0]].get('destino'))

            peso2_before = float(d2.get('peso_usado', 0.0))
            vol2_before  = float(d2.get('volume_usado', 0.0))
            transp2_before = float(transp_por_v.get(v2, 0.0))
            frete2_before  = float(frete_por_v.get(v2, 0.0))


            info1 = {}
            for uid in ums_v1:
                u = ums_map[uid]
                info1[uid] = (u, float(u.get('peso', 0.0)), float(u.get('volume', 0.0)), _norm(u.get('destino')))

            info2 = {}
            for uid in ums_v2:
                u = ums_map[uid]
                info2[uid] = (u, float(u.get('peso', 0.0)), float(u.get('volume', 0.0)), _norm(u.get('destino')))

            for um_a in ums_v1:
                uma_obj, peso_a, vol_a, dest_a = info1[um_a]


                if reg2 is not None and dest_a is not None and reg2 != dest_a:
                    continue


                if not um_compatível_com_veiculo(uma_obj, v2_obj):
                    continue


                c_a_em_v1 = _custo_unit(uma_obj, tipo1)
                c_a_em_v2 = _custo_unit(uma_obj, tipo2)

                for um_b in ums_v2:
                    umb_obj, peso_b, vol_b, dest_b = info2[um_b]


                    if reg1 is not None and dest_b is not None and reg1 != dest_b:
                        continue


                    if not um_compatível_com_veiculo(umb_obj, v1_obj):
                        continue


                    c_b_em_v2 = _custo_unit(umb_obj, tipo2)
                    c_b_em_v1 = _custo_unit(umb_obj, tipo1)


                    peso1_after = peso1_before - peso_a + peso_b
                    vol1_after  = vol1_before  - vol_a  + vol_b
                    if peso1_after > cap_p1 + 1e-9 or vol1_after > cap_v1 + 1e-9:
                        continue

                    peso2_after = peso2_before - peso_b + peso_a
                    vol2_after  = vol2_before  - vol_b  + vol_a
                    if peso2_after > cap_p2 + 1e-9 or vol2_after > cap_v2 + 1e-9:
                        continue


                    if min1 > 0.0 and peso1_after < min1 - 1e-9:
                        continue
                    if min2 > 0.0 and peso2_after < min2 - 1e-9:
                        continue


                    transp1_after = transp1_before - c_a_em_v1 + c_b_em_v1
                    transp2_after = transp2_before - c_b_em_v2 + c_a_em_v2


                    oci1_after = cap_p1 - peso1_after
                    if oci1_after < 0.0:
                        oci1_after = 0.0
                    frete1_after = beta * oci1_after

                    oci2_after = cap_p2 - peso2_after
                    if oci2_after < 0.0:
                        oci2_after = 0.0
                    frete2_after = beta * oci2_after


                    custo_old = transp1_before + frete1_before + transp2_before + frete2_before
                    custo_new = transp1_after  + frete1_after  + transp2_after  + frete2_after

                    delta = custo_old - custo_new
                    if delta > melhor_delta + 1e-9:
                        melhor_delta = delta
                        melhor_mov = (um_a, um_b, v1, v2)


    if melhor_mov is not None:
        um_a, um_b, v1, v2 = melhor_mov
        desalocar_um(solucao, um_a, v1, instancia)
        desalocar_um(solucao, um_b, v2, instancia)
        alocar_um(solucao, um_a, v2, instancia)
        alocar_um(solucao, um_b, v1, instancia)


        return True


    return False

def realizar_troca_1x2(solucao, instancia):

    global CTX
    CTX = inspect.currentframe().f_code.co_name


    if PROFILE:
        _prof.setdefault("viz", {})
        _prof["viz"].setdefault(CTX, {"calls": 0, "t_total": 0.0, "alocar": 0, "t_alocar": 0.0})
        _prof["viz"][CTX]["calls"] += 1
        _t_ini = perf_counter()
        _n0 = _prof.get("n_alocar", 0)
        _t0 = _prof.get("t_alocar", 0.0)

    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, instancia)

    comp = solucao['componentes_custo']
    beta = float(comp.get('beta', 1.0))


    veiculos_map = instancia.get('veiculos_id', None)
    if veiculos_map is None:
        veiculos_map = {v['id']: v for v in instancia['veiculos']}

    ums_map = instancia.get('ums_id', None)
    if ums_map is None:
        ums_map = {u['id']: u for u in instancia['ums']}


    frete_por_v  = comp.get('frete_morto_por_veiculo', {})
    ativ_por_v   = comp.get('custo_ativacao_por_veiculo', {})
    transp_por_v = comp.get('transporte_por_veiculo', {})

    def _norm(x):
        return str(x) if x is not None else None


    def _custo_fixo(v_obj, reg_norm):
        if reg_norm is not None:
            if 'custos_por_regiao' in v_obj:
                base = v_obj['custos_por_regiao'].get(str(reg_norm), 0.0)
            else:
                base = v_obj.get('custo', 0.0)
        else:
            base = v_obj.get('custo', 0.0)


        if isinstance(base, str):
            s = base.strip()
            if ',' in s:
                s = s.split(',')[0].strip()
            return float(s) if s else 0.0
        return float(base)

    def _custo_unit(um_obj, tipo_veic):
        try:
            val = um_obj.get('custos_por_tipo', {}).get(tipo_veic, 0.0)
            if isinstance(val, str):
                s = val.strip()
                if ',' in s:
                    s = s.split(',')[0].strip()
                return float(s) if s else 0.0
            return float(val)
        except:
            return 0.0

    ativos = [vid for vid, dados in solucao['veiculo_dados'].items()
              if dados['ativo'] and len(dados['ums']) > 0]
    if len(ativos) < 2:

        return False

    melhor_mov = None
    melhor_delta = 0.0

    ativos_ordenados = sorted(ativos)

    for i in range(len(ativos_ordenados)):
        v1 = ativos_ordenados[i]
        d1 = solucao['veiculo_dados'][v1]
        ums_v1 = list(d1['ums'])
        n1 = len(ums_v1)
        if n1 < 1:
            continue

        v1_obj = veiculos_map[v1]
        tipo1 = v1_obj.get('tipo')
        cap_p1 = float(v1_obj.get('capacidade_peso', 0.0))
        cap_v1 = float(v1_obj.get('capacidade_volume', 0.0))
        min1 = float(v1_obj.get('carga_minima', 0.0))

        reg1_before = _norm(d1.get('regiao'))
        if reg1_before is None and n1 > 0:

            reg1_before = _norm(ums_map[ums_v1[0]].get('destino'))

        peso1_before = float(d1.get('peso_usado', 0.0))
        vol1_before  = float(d1.get('volume_usado', 0.0))
        frete1_before = float(frete_por_v.get(v1, 0.0))
        ativ1_before  = float(ativ_por_v.get(v1, 0.0))
        transp1_before = float(transp_por_v.get(v1, 0.0))

        for j in range(i + 1, len(ativos_ordenados)):
            v2 = ativos_ordenados[j]
            d2 = solucao['veiculo_dados'][v2]
            ums_v2 = list(d2['ums'])
            n2 = len(ums_v2)
            if n2 < 2:
                continue

            v2_obj = veiculos_map[v2]
            tipo2 = v2_obj.get('tipo')
            cap_p2 = float(v2_obj.get('capacidade_peso', 0.0))
            cap_v2 = float(v2_obj.get('capacidade_volume', 0.0))
            min2 = float(v2_obj.get('carga_minima', 0.0))

            reg2_before = _norm(d2.get('regiao'))
            if reg2_before is None and n2 > 0:
                reg2_before = _norm(ums_map[ums_v2[0]].get('destino'))

            peso2_before = float(d2.get('peso_usado', 0.0))
            vol2_before  = float(d2.get('volume_usado', 0.0))
            frete2_before = float(frete_por_v.get(v2, 0.0))
            ativ2_before  = float(ativ_por_v.get(v2, 0.0))
            transp2_before = float(transp_por_v.get(v2, 0.0))


            info1 = {}
            for uid in ums_v1:
                u = ums_map[uid]
                info1[uid] = (u, float(u.get('peso', 0.0)), float(u.get('volume', 0.0)), _norm(u.get('destino')))

            info2 = {}
            for uid in ums_v2:
                u = ums_map[uid]
                info2[uid] = (u, float(u.get('peso', 0.0)), float(u.get('volume', 0.0)), _norm(u.get('destino')))

            for um_c in ums_v1:
                umc_obj, peso_c, vol_c, dest_c = info1[um_c]


                if not um_compatível_com_veiculo(umc_obj, v2_obj):
                    continue


                c_c_em_v1 = _custo_unit(umc_obj, tipo1)
                c_c_em_v2 = _custo_unit(umc_obj, tipo2)

                n1_mid = n1 - 1

                for (um_a, um_b) in itertools.combinations(ums_v2, 2):
                    uma_obj, peso_a, vol_a, dest_a = info2[um_a]
                    umb_obj, peso_b, vol_b, dest_b = info2[um_b]


                    if not um_compatível_com_veiculo(uma_obj, v1_obj):
                        continue
                    if not um_compatível_com_veiculo(umb_obj, v1_obj):
                        continue

                    n2_mid = n2 - 2



                    if n1_mid == 0:
                        reg1_after = dest_a

                        if reg1_after is not None and dest_b is not None and reg1_after != dest_b:
                            continue
                    else:
                        reg1_after = reg1_before
                        if reg1_after is not None:
                            if dest_a is not None and reg1_after != dest_a:
                                continue
                            if dest_b is not None and reg1_after != dest_b:
                                continue


                    if n2_mid == 0:
                        reg2_after = dest_c
                    else:
                        reg2_after = reg2_before
                        if reg2_after is not None and dest_c is not None and reg2_after != dest_c:
                            continue



                    peso1_after = peso1_before - peso_c + peso_a + peso_b
                    vol1_after  = vol1_before  - vol_c  + vol_a  + vol_b
                    if peso1_after > cap_p1 + 1e-9 or vol1_after > cap_v1 + 1e-9:
                        continue

                    peso2_after = peso2_before - peso_a - peso_b + peso_c
                    vol2_after  = vol2_before  - vol_a  - vol_b  + vol_c
                    if peso2_after > cap_p2 + 1e-9 or vol2_after > cap_v2 + 1e-9:
                        continue



                    if min1 > 0.0 and peso1_after < min1 - 1e-9:
                        continue
                    if min2 > 0.0 and peso2_after < min2 - 1e-9:
                        continue


                    c_a_em_v1 = _custo_unit(uma_obj, tipo1)
                    c_b_em_v1 = _custo_unit(umb_obj, tipo1)
                    c_a_em_v2 = _custo_unit(uma_obj, tipo2)
                    c_b_em_v2 = _custo_unit(umb_obj, tipo2)

                    transp1_after = transp1_before - c_c_em_v1 + c_a_em_v1 + c_b_em_v1
                    transp2_after = transp2_before - c_a_em_v2 - c_b_em_v2 + c_c_em_v2


                    oci1_after = cap_p1 - peso1_after
                    if oci1_after < 0.0:
                        oci1_after = 0.0
                    frete1_after = beta * oci1_after

                    oci2_after = cap_p2 - peso2_after
                    if oci2_after < 0.0:
                        oci2_after = 0.0
                    frete2_after = beta * oci2_after




                    if n1_mid == 0:

                        ativ1_after = _custo_fixo(v1_obj, reg1_after)
                    else:

                        ativ1_after = ativ1_before

                    if n2_mid == 0:

                        ativ2_after = _custo_fixo(v2_obj, reg2_after)
                    else:
                        ativ2_after = ativ2_before



                    custo_old = ativ1_before + transp1_before + frete1_before + ativ2_before + transp2_before + frete2_before
                    custo_new = activ1_after = ativ1_after
                    custo_new = ativ1_after + transp1_after + frete1_after + ativ2_after + transp2_after + frete2_after

                    delta = custo_old - custo_new
                    if delta > melhor_delta + 1e-9:
                        melhor_delta = delta
                        melhor_mov = (um_a, um_b, um_c, v1, v2)

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

def realizar_insercao_nao_alocadas(solucao, instancia):
    global CTX
    CTX = inspect.currentframe().f_code.co_name


    if PROFILE:
        _prof.setdefault("viz", {})
        _prof["viz"].setdefault(CTX, {"calls": 0, "t_total": 0.0, "alocar": 0, "t_alocar": 0.0})
        _prof["viz"][CTX]["calls"] += 1
        _t_ini = perf_counter()
        _n0 = _prof.get("n_alocar", 0)
        _t0 = _prof.get("t_alocar", 0.0)

    if not solucao.get('nao_alocadas'):

        return False


    ums_map = instancia.get('ums_id', None)
    if ums_map is None:
        ums_map = {u['id']: u for u in instancia['ums']}

    veiculos = instancia.get('veiculos', [])
    veiculos_map = instancia.get('veiculos_id', None)
    if veiculos_map is None:
        veiculos_map = {v['id']: v for v in veiculos}


    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, instancia)

    def _norm(x):
        return str(x) if x is not None else None


    nao_alocadas_ordenadas = sorted(
        list(solucao['nao_alocadas']),
        key=lambda uid: (-float(ums_map[uid].get('penalidade', 0.0)), str(uid))
    )

    melhor_delta = 0.0
    melhor_mov = None

    for um_id in nao_alocadas_ordenadas:
        um = ums_map.get(um_id, None)
        if um is None:
            continue

        destino_um = _norm(um.get('destino'))
        peso_um = float(um.get('peso', 0.0))
        vol_um  = float(um.get('volume', 0.0))

        for v in veiculos:
            v_id = v['id']
            dados = solucao['veiculo_dados'][v_id]



            if len(dados['ums']) > 0:
                reg_atual = dados.get('regiao', None)
                if reg_atual is None:

                    try:
                        any_uid = next(iter(dados['ums']))
                        reg_atual = _norm(ums_map[any_uid].get('destino'))
                    except:
                        reg_atual = None
                reg_atual = _norm(reg_atual)

                if reg_atual is not None and destino_um is not None and reg_atual != destino_um:
                    continue



            if not um_compatível_com_veiculo(um, v):
                continue


            cap_p = float(v.get('capacidade_peso', 0.0))
            cap_v = float(v.get('capacidade_volume', 0.0))

            peso_after = float(dados.get('peso_usado', 0.0)) + peso_um
            vol_after  = float(dados.get('volume_usado', 0.0)) + vol_um

            if peso_after > cap_p + 1e-9 or vol_after > cap_v + 1e-9:
                continue



            carga_min = float(v.get('carga_minima', 0.0) or 0.0)
            if carga_min > 0.0 and (len(dados['ums']) == 0 or not dados.get('ativo', False)):
                if peso_after + 1e-9 < carga_min:
                    continue



            delta = delta_insercao(solucao, instancia, um, v)


            if delta < melhor_delta - 1e-9:
                melhor_delta = delta
                melhor_mov = (um_id, v_id)

    if melhor_mov is not None:
        um_id, v_id = melhor_mov
        ok = alocar_um(solucao, um_id, v_id, instancia)
        if ok:
            return True


    return False

def realizar_troca_alocada_por_nao_alocada(solucao, instancia):

    global CTX
    CTX = inspect.currentframe().f_code.co_name


    if PROFILE:
        _prof.setdefault("viz", {})
        _prof["viz"].setdefault(CTX, {"calls": 0, "t_total": 0.0, "alocar": 0, "t_alocar": 0.0})
        _prof["viz"][CTX]["calls"] += 1
        _t_ini = perf_counter()
        _n0 = _prof.get("n_alocar", 0)
        _t0 = _prof.get("t_alocar", 0.0)

    if not solucao.get('nao_alocadas'):

        return False

    ums_id = instancia.get('ums_id', None)
    veiculos_id = instancia.get('veiculos_id', None)
    if ums_id is None:
        ums_id = {u['id']: u for u in instancia['ums']}
        instancia['ums_id'] = ums_id
    if veiculos_id is None:
        veiculos_id = {v['id']: v for v in instancia['veiculos']}
        instancia['veiculos_id'] = veiculos_id

    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, instancia)

    EPS = 1e-9

    def _norm(x):
        return str(x) if x is not None else None


    top_k_nao = 25
    top_k_out = 8


    nao_alocadas_ordenadas = sorted(
        list(solucao['nao_alocadas']),
        key=lambda uid: (-float(ums_id.get(uid, {}).get('penalidade', 0.0) or 0.0), str(uid))
    )[:top_k_nao]

    for um_in_id in nao_alocadas_ordenadas:
        um_in = ums_id.get(um_in_id)
        if um_in is None:
            continue

        penal_in = float(um_in.get('penalidade', 0.0) or 0.0)
        destino_in_norm = _norm(um_in.get('destino', None))

        peso_in = float(um_in.get('peso', 0.0) or 0.0)
        vol_in  = float(um_in.get('volume', 0.0) or 0.0)


        for v_id, dados_v in solucao['veiculo_dados'].items():
            if not dados_v.get('ativo', False):
                continue
            if len(dados_v.get('ums', [])) == 0:
                continue


            reg_v_norm = _norm(dados_v.get('regiao', None))
            if reg_v_norm is not None and destino_in_norm is not None and reg_v_norm != destino_in_norm:
                continue

            veic = veiculos_id.get(v_id)
            if veic is None:
                continue


            if not um_compatível_com_veiculo(um_in, veic):
                continue


            cap_p = float(veic.get('capacidade_peso', 0.0) or 0.0)
            cap_v = float(veic.get('capacidade_volume', 0.0) or 0.0)
            peso_us = float(dados_v.get('peso_usado', 0.0) or 0.0)
            vol_us  = float(dados_v.get('volume_usado', 0.0) or 0.0)

            falta_p = (peso_us + peso_in) - cap_p
            falta_v = (vol_us  + vol_in)  - cap_v


            if falta_p <= 1e-6 and falta_v <= 1e-6:
                continue


            ums_no_veiculo = list(dados_v.get('ums', set()))
            ums_no_veiculo_ordenadas = sorted(
                ums_no_veiculo,
                key=lambda uid: (float(ums_id.get(uid, {}).get('penalidade', 0.0) or 0.0), str(uid))
            )[:top_k_out]


            melhor_out = None
            melhor_penal = float("inf")

            for um_out_id in ums_no_veiculo_ordenadas:
                um_out = ums_id.get(um_out_id)
                if um_out is None:
                    continue

                penal_out = float(um_out.get('penalidade', 0.0) or 0.0)


                if penal_in <= penal_out + EPS:
                    continue

                peso_out = float(um_out.get('peso', 0.0) or 0.0)
                vol_out  = float(um_out.get('volume', 0.0) or 0.0)


                if peso_out + 1e-9 < falta_p and vol_out + 1e-9 < falta_v:
                    continue

                if penal_out < melhor_penal:
                    melhor_penal = penal_out
                    melhor_out = um_out_id

            if melhor_out is None:
                continue


            custo_base = float(solucao.get('custo', 0.0))

            if not desalocar_um(solucao, melhor_out, v_id, instancia):
                continue

            ok = alocar_um(solucao, um_in_id, v_id, instancia)

            if ok:
                if float(solucao.get('custo', custo_base)) < custo_base - 1e-9:
                    return True

                desalocar_um(solucao, um_in_id, v_id, instancia)


            alocar_um(solucao, melhor_out, v_id, instancia)


    return False

def realoca_entre_veiculos(solucao, instancia):

    global CTX
    CTX = inspect.currentframe().f_code.co_name


    if PROFILE:
        _prof.setdefault("viz", {})
        _prof["viz"].setdefault(CTX, {"calls": 0, "t_total": 0.0, "alocar": 0, "t_alocar": 0.0})
        _prof["viz"][CTX]["calls"] += 1
        _t_ini = perf_counter()
        _n0 = _prof.get("n_alocar", 0)
        _t0 = _prof.get("t_alocar", 0.0)

    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, instancia)

    comp = solucao['componentes_custo']
    beta = float(comp.get('beta', 1.0))

    ums_id = instancia.get('ums_id', None)
    veiculos_map = instancia.get('veiculos_id', None)
    veiculos = instancia.get('veiculos', [])

    if ums_id is None:
        ums_id = {u['id']: u for u in instancia['ums']}
    if veiculos_map is None:
        veiculos_map = {v['id']: v for v in instancia['veiculos']}

    frete_por_v  = comp.get('frete_morto_por_veiculo', {})
    ativ_por_v   = comp.get('custo_ativacao_por_veiculo', {})
    transp_por_v = comp.get('transporte_por_veiculo', {})

    def _norm(x):
        return str(x) if x is not None else None

    def _custo_unit(um_obj, tipo_veic):
        try:
            val = um_obj.get('custos_por_tipo', {}).get(tipo_veic, 0.0)
            if isinstance(val, str):
                s = val.strip()
                if ',' in s:
                    s = s.split(',')[0].strip()
                return float(s) if s else 0.0
            return float(val)
        except:
            return 0.0

    def _custo_fixo(veic_obj, reg_norm):

        if reg_norm is not None:
            if 'custos_por_regiao' in veic_obj:
                base = veic_obj['custos_por_regiao'].get(str(reg_norm), 0.0)
            else:
                base = veic_obj.get('custo', 0.0)
        else:
            base = veic_obj.get('custo', 0.0)

        if isinstance(base, str):
            s = base.strip()
            if ',' in s:
                s = s.split(',')[0].strip()
            return float(s) if s else 0.0
        return float(base)

    custo_base = float(solucao['custo'])

    melhor_movimento = None
    melhor_delta = 0.0


    for um_id, v_origem_id in list(solucao['alocacao_um'].items()):
        um = ums_id[um_id]
        peso_u = float(um.get('peso', 0.0))
        vol_u  = float(um.get('volume', 0.0))
        dest_u = _norm(um.get('destino'))

        dO = solucao['veiculo_dados'][v_origem_id]
        veicO = veiculos_map[v_origem_id]
        tipoO = veicO.get('tipo')

        nO = len(dO['ums'])
        regO_before = _norm(dO.get('regiao'))
        if regO_before is None and nO > 0:

            any_uid = next(iter(dO['ums']))
            regO_before = _norm(ums_id[any_uid].get('destino'))

        pesoO_before = float(dO.get('peso_usado', 0.0))
        volO_before  = float(dO.get('volume_usado', 0.0))
        transpO_before = float(transp_por_v.get(v_origem_id, 0.0))
        freteO_before  = float(frete_por_v.get(v_origem_id, 0.0))
        ativO_before   = float(ativ_por_v.get(v_origem_id, 0.0))

        cap_pO = float(veicO.get('capacidade_peso', 0.0))
        cap_vO = float(veicO.get('capacidade_volume', 0.0))
        minO   = float(veicO.get('carga_minima', 0.0) or 0.0)


        c_u_em_O = _custo_unit(um, tipoO)


        nO_mid = nO - 1
        pesoO_after = pesoO_before - peso_u
        volO_after  = volO_before  - vol_u
        transpO_after = transpO_before - c_u_em_O

        if nO_mid == 0:

            ativO_after = 0.0
            freteO_after = 0.0
            regO_after = None
            ativoO_after = False
        else:
            ativO_after = ativO_before
            regO_after = regO_before
            ativoO_after = True
            ociO = cap_pO - pesoO_after
            if ociO < 0.0:
                ociO = 0.0
            freteO_after = beta * ociO


        if ativoO_after and (pesoO_after + 1e-9 < minO):

            continue


        custoO_old = ativO_before + transpO_before + freteO_before
        custoO_new = ativO_after  + transpO_after  + freteO_after


        for v_dest in veiculos:
            v_dest_id = v_dest['id']
            if v_dest_id == v_origem_id:
                continue


            if not um_compatível_com_veiculo(um, v_dest):
                continue

            dD = solucao['veiculo_dados'][v_dest_id]
            veicD = veiculos_map[v_dest_id]
            tipoD = veicD.get('tipo')

            nD = len(dD['ums'])
            regD_before = _norm(dD.get('regiao'))
            if regD_before is None and nD > 0:
                any_uid = next(iter(dD['ums']))
                regD_before = _norm(ums_id[any_uid].get('destino'))

            pesoD_before = float(dD.get('peso_usado', 0.0))
            volD_before  = float(dD.get('volume_usado', 0.0))
            transpD_before = float(transp_por_v.get(v_dest_id, 0.0))
            freteD_before  = float(frete_por_v.get(v_dest_id, 0.0))
            ativD_before   = float(ativ_por_v.get(v_dest_id, 0.0))
            ativoD_before  = bool(dD.get('ativo', False))

            cap_pD = float(veicD.get('capacidade_peso', 0.0))
            cap_vD = float(veicD.get('capacidade_volume', 0.0))
            minD   = float(veicD.get('carga_minima', 0.0) or 0.0)


            if nD == 0:
                regD_after = dest_u
            else:
                regD_after = regD_before
                if regD_after is not None and dest_u is not None and regD_after != dest_u:
                    continue


            pesoD_after = pesoD_before + peso_u
            volD_after  = volD_before  + vol_u
            if pesoD_after > cap_pD + 1e-9 or volD_after > cap_vD + 1e-9:
                continue


            c_u_em_D = _custo_unit(um, tipoD)
            transpD_after = transpD_before + c_u_em_D


            ociD = cap_pD - pesoD_after
            if ociD < 0.0:
                ociD = 0.0
            freteD_after = beta * ociD


            if (not ativoD_before) or (nD == 0):
                ativD_after = _custo_fixo(veicD, regD_after)
            else:
                ativD_after = ativD_before


            if pesoD_after + 1e-9 < minD:
                continue

            custoD_old = ativD_before + transpD_before + freteD_before
            custoD_new = ativD_after  + transpD_after  + freteD_after


            delta_total = (custoO_new + custoD_new) - (custoO_old + custoD_old)

            if delta_total < melhor_delta - 1e-9:
                melhor_delta = delta_total
                melhor_movimento = (um_id, v_origem_id, v_dest_id)


    if melhor_movimento is not None:
        um_id, v_origem_id, v_dest_id = melhor_movimento
        desalocar_um(solucao, um_id, v_origem_id, instancia)
        alocar_um(solucao, um_id, v_dest_id, instancia)
        return True


    return False

def liberar_veiculo_para_um_cara(sol, instancia, top_k_ums=5, max_veiculos_testados=5):

    global CTX
    CTX = inspect.currentframe().f_code.co_name
    n0 = _prof["n_alocar"]
    t0 = _prof["t_alocar"]


    ums_id = instancia.get('ums_id', None)
    veiculos_id = instancia.get('veiculos_id', None)
    if ums_id is None:
        ums_id = {u['id']: u for u in instancia['ums']}
        instancia['ums_id'] = ums_id
    if veiculos_id is None:
        veiculos_id = {v['id']: v for v in instancia['veiculos']}
        instancia['veiculos_id'] = veiculos_id


    if sol.get('custo') is None or 'componentes_custo' not in sol:
        custo_total(sol, instancia)

    def _norm(x):
        return str(x) if x is not None else None

    nao_aloc = list(sol.get('nao_alocadas', set()))
    if not nao_aloc:

        return False


    nao_aloc.sort(
        key=lambda u: float(ums_id.get(u, {}).get('penalidade', 0.0) or 0.0),
        reverse=True
    )
    ums_candidatas = nao_aloc[:top_k_ums]

    todos_veiculos_ids = list(sol['veiculo_dados'].keys())


    max_remocoes = 10
    max_destinos_por_um = 12

    for um_id in ums_candidatas:
        um = ums_id.get(um_id)
        if um is None:
            continue

        destino_um = _norm(um.get('destino', None))
        custo_inicial = float(sol.get('custo', 0.0))


        veiculos_possiveis = []
        for v_id, dados in sol['veiculo_dados'].items():
            if len(dados.get('ums', [])) == 0:
                veiculos_possiveis.append(v_id)
            else:
                reg = _norm(dados.get('regiao', None))
                if reg == destino_um:
                    veiculos_possiveis.append(v_id)

        random.shuffle(veiculos_possiveis)
        veiculos_possiveis = veiculos_possiveis[:max_veiculos_testados]

        for v_alvo_id in veiculos_possiveis:
            veic_alvo = veiculos_id[v_alvo_id]
            dados_alvo = sol['veiculo_dados'][v_alvo_id]



            if len(dados_alvo.get('ums', [])) > 0:
                reg = _norm(dados_alvo.get('regiao', None))
                if reg is not None and destino_um is not None and reg != destino_um:
                    continue


            if not um_compatível_com_veiculo(um, veic_alvo):
                continue

            cap_p = float(veic_alvo.get('capacidade_peso', 0.0))
            cap_v = float(veic_alvo.get('capacidade_volume', 0.0))
            carga_min = float(veic_alvo.get('carga_minima', 0.0) or 0.0)

            peso_u = float(um.get('peso', 0.0))
            vol_u  = float(um.get('volume', 0.0))


            peso_disp = cap_p - float(dados_alvo.get('peso_usado', 0.0))
            vol_disp  = cap_v - float(dados_alvo.get('volume_usado', 0.0))
            falta_p = peso_u - peso_disp
            falta_v = vol_u  - vol_disp


            if falta_p <= 1e-6 and falta_v <= 1e-6:
                delta_um_cara = delta_insercao(sol, instancia, um, veic_alvo)
                if delta_um_cara < -1e-6:
                    if alocar_um(sol, um_id, v_alvo_id, instancia):
                        if float(sol.get('custo', 0.0)) < custo_inicial - 1e-6:
                            return True
                        desalocar_um(sol, um_id, v_alvo_id, instancia)
                continue


            if peso_u > cap_p + 1e-9 or vol_u > cap_v + 1e-9:
                continue


            ums_orig = list(dados_alvo.get('ums', []))
            if not ums_orig:
                continue


            ums_orig.sort(key=lambda uid: float(ums_id[uid].get('penalidade', 0.0) or 0.0))

            removidos = []
            ok = True



            for u in ums_orig:
                if (falta_p <= 1e-6 and falta_v <= 1e-6) or len(removidos) >= max_remocoes:
                    break

                if desalocar_um(sol, u, v_alvo_id, instancia):
                    removidos.append(u)
                    falta_p -= float(ums_id[u].get('peso', 0.0) or 0.0)
                    falta_v -= float(ums_id[u].get('volume', 0.0) or 0.0)
                else:
                    ok = False
                    break

            if not ok or (falta_p > 1e-6 or falta_v > 1e-6):

                for u in removidos:
                    alocar_um(sol, u, v_alvo_id, instancia)
                continue



            removidos.sort(key=lambda uid: -float(ums_id[uid].get('peso', 0.0) or 0.0))

            relocados = []
            for u in removidos:
                um_old = ums_id.get(u)
                if um_old is None:
                    ok = False
                    break

                destino_old = _norm(um_old.get('destino', None))
                peso_old = float(um_old.get('peso', 0.0))
                vol_old  = float(um_old.get('volume', 0.0))


                vazios = []
                mesma_reg = []
                for v_dest_id in todos_veiculos_ids:
                    if v_dest_id == v_alvo_id:
                        continue
                    d = sol['veiculo_dados'][v_dest_id]
                    if len(d.get('ums', [])) == 0:
                        vazios.append(v_dest_id)
                    else:
                        reg = _norm(d.get('regiao', None))
                        if reg is not None and destino_old is not None and reg == destino_old:
                            mesma_reg.append(v_dest_id)

                random.shuffle(vazios)
                random.shuffle(mesma_reg)
                candidatos = (vazios + mesma_reg)[:max_destinos_por_um]

                melhor_dest = None
                melhor_delta = float("inf")

                for v_dest_id in candidatos:
                    d = sol['veiculo_dados'][v_dest_id]
                    veic_dest = veiculos_id[v_dest_id]

                    if not um_compatível_com_veiculo(um_old, veic_dest):
                        continue


                    cap_p2 = float(veic_dest.get('capacidade_peso', 0.0))
                    cap_v2 = float(veic_dest.get('capacidade_volume', 0.0))
                    peso_after = float(d.get('peso_usado', 0.0)) + peso_old
                    vol_after  = float(d.get('volume_usado', 0.0)) + vol_old
                    if peso_after > cap_p2 + 1e-9 or vol_after > cap_v2 + 1e-9:
                        continue


                    carga_min2 = float(veic_dest.get('carga_minima', 0.0) or 0.0)
                    if carga_min2 > 0.0 and (len(d.get('ums', [])) == 0 or not d.get('ativo', False)):
                        if peso_after + 1e-9 < carga_min2:
                            continue

                    delta = delta_insercao(sol, instancia, um_old, veic_dest)
                    if delta < melhor_delta:
                        melhor_delta = delta
                        melhor_dest = v_dest_id

                if melhor_dest is None:
                    ok = False
                    break

                if not alocar_um(sol, u, melhor_dest, instancia):
                    ok = False
                    break

                relocados.append((u, melhor_dest))

            if not ok:

                for (u, v_dest) in relocados:
                    desalocar_um(sol, u, v_dest, instancia)
                for u in removidos:
                    alocar_um(sol, u, v_alvo_id, instancia)
                continue


            delta_um_cara = delta_insercao(sol, instancia, um, veic_alvo)
            if delta_um_cara < -1e-6:
                if alocar_um(sol, um_id, v_alvo_id, instancia):
                    if float(sol.get('custo', 0.0)) < custo_inicial - 1e-6:
                        return True
                    desalocar_um(sol, um_id, v_alvo_id, instancia)


            for (u, v_dest) in relocados:
                desalocar_um(sol, u, v_dest, instancia)
            for u in removidos:
                alocar_um(sol, u, v_alvo_id, instancia)


    return False

def abrir_veiculo_formar_minimo_e_inserir_um(
    sol,
    instancia,
    top_k_ums=3,
    max_veiculos_vazios=4,
    max_doadores=8,
    max_transferencias=4,
    penalidade_minima_para_rodar=1000.0,
    exigir_um_muito_restrita=False,
):

    global CTX
    CTX = inspect.currentframe().f_code.co_name


    if sol.get("custo") is None or "componentes_custo" not in sol:
        custo_total(sol, instancia)

    nao_alocadas = list(sol.get("nao_alocadas", set()))
    if not nao_alocadas:
        return False


    ums_id = instancia.get("ums_id")
    veiculos_id = instancia.get("veiculos_id")
    if ums_id is None:
        ums_id = {u["id"]: u for u in instancia["ums"]}
        instancia["ums_id"] = ums_id
    if veiculos_id is None:
        veiculos_id = {v["id"]: v for v in instancia["veiculos"]}
        instancia["veiculos_id"] = veiculos_id

    def _norm(x):
        return str(x) if x is not None else None




    penal_max = 0.0
    for uid in nao_alocadas:
        um = ums_id.get(uid, {})
        penal_max = max(penal_max, float(um.get("penalidade", 0.0) or 0.0))

    if penal_max + 1e-9 < float(penalidade_minima_para_rodar):
        return False





    if exigir_um_muito_restrita:
        achou_restrita = False
        for uid in nao_alocadas:
            tipos = CACHE_COMPATIBILIDADE.get(uid)
            if tipos and len(tipos) <= 1:
                achou_restrita = True
                break
        if not achou_restrita:
            return False

    custo_inicial = float(sol.get("custo", 0.0))




    def score_um(uid):
        um = ums_id.get(uid, {})
        pen = float(um.get("penalidade", 0.0) or 0.0)
        tipos = CACHE_COMPATIBILIDADE.get(uid)
        if not tipos:
            restr = 999
        else:
            restr = len(tipos)
        return (restr, -pen)

    nao_alocadas.sort(key=score_um)
    ums_alvo = nao_alocadas[:max(1, int(top_k_ums))]




    veic_ids = list(sol["veiculo_dados"].keys())
    vazios = []
    ativos_por_reg = {}

    for vid in veic_ids:
        d = sol["veiculo_dados"][vid]
        if len(d.get("ums", [])) == 0:
            vazios.append(vid)
        else:
            reg = _norm(d.get("regiao", None))
            if reg is not None:
                ativos_por_reg.setdefault(reg, []).append(vid)

    def custo_fixo_regiao(veic, reg):
        cpr = veic.get("custos_por_regiao", {})
        try:
            return float(cpr.get(reg, 0.0))
        except:
            return 0.0

    def cabe_no(vid, veic, uid):
        d = sol["veiculo_dados"][vid]
        um = ums_id[uid]
        cap_p = float(veic.get("capacidade_peso", 0.0))
        cap_v = float(veic.get("capacidade_volume", 0.0))
        p_after = float(d.get("peso_usado", 0.0)) + float(um.get("peso", 0.0) or 0.0)
        v_after = float(d.get("volume_usado", 0.0)) + float(um.get("volume", 0.0) or 0.0)
        if p_after > cap_p + 1e-9:
            return False
        if v_after > cap_v + 1e-9:
            return False
        return True




    for um_alvo_id in ums_alvo:
        um_alvo = ums_id.get(um_alvo_id)
        if um_alvo is None:
            continue

        reg = _norm(um_alvo.get("destino", None))
        if reg is None:
            continue


        vazios_comp = []
        for vid in vazios:
            veic = veiculos_id[vid]
            if not um_compatível_com_veiculo(um_alvo, veic):
                continue
            if not cabe_no(vid, veic, um_alvo_id):
                continue
            vazios_comp.append(vid)

        if not vazios_comp:
            continue


        vazios_comp.sort(key=lambda vid: custo_fixo_regiao(veiculos_id[vid], reg))
        vazios_comp = vazios_comp[:max(1, int(max_veiculos_vazios))]


        doadores_veic = ativos_por_reg.get(reg, [])

        for v_alvo_id in vazios_comp:
            veic_alvo = veiculos_id[v_alvo_id]
            carga_min = float(veic_alvo.get("carga_minima", 0.0) or 0.0)

            if VERBOSE:
                print(f"[{CTX}] Tentando abrir veic {v_alvo_id} (tipo={veic_alvo.get('tipo')}) em reg={reg} "
                      f"para UM={um_alvo_id} (pen={float(um_alvo.get('penalidade',0.0) or 0.0):.2f})")


            if not alocar_um(sol, um_alvo_id, v_alvo_id, instancia):
                continue

            movidos = []


            if carga_min <= 1e-9:
                if float(sol.get("custo", 0.0)) < custo_inicial - 1e-6:
                    if VERBOSE:
                        print(f"[{CTX}] Aceitou: abriu {v_alvo_id} e inseriu UM={um_alvo_id}. "
                              f"custo {custo_inicial:.2f} -> {float(sol.get('custo',0.0)):.2f}")
                    return True

                desalocar_um(sol, um_alvo_id, v_alvo_id, instancia)
                continue


            d_alvo = sol["veiculo_dados"][v_alvo_id]
            peso_atual = float(d_alvo.get("peso_usado", 0.0))

            ok = True
            if peso_atual + 1e-9 < carga_min:
                falta = carga_min - peso_atual


                cand = []
                for vid_origem in doadores_veic:
                    if vid_origem == v_alvo_id:
                        continue

                    d_or = sol["veiculo_dados"][vid_origem]
                    veic_or = veiculos_id[vid_origem]
                    min_or = float(veic_or.get("carga_minima", 0.0) or 0.0)

                    for uid in list(d_or.get("ums", [])):
                        um_d = ums_id[uid]
                        if not um_compatível_com_veiculo(um_d, veic_alvo):
                            continue
                        if not cabe_no(v_alvo_id, veic_alvo, uid):
                            continue

                        peso_uid = float(um_d.get("peso", 0.0) or 0.0)


                        if len(d_or.get("ums", [])) > 1 and min_or > 1e-9:
                            if (float(d_or.get("peso_usado", 0.0)) - peso_uid) + 1e-9 < min_or:
                                continue

                        pen = float(um_d.get("penalidade", 0.0) or 0.0)
                        cand.append((pen, -peso_uid, uid, vid_origem))

                if not cand:
                    ok = False
                else:
                    cand.sort()
                    cand = cand[:max(1, int(max_doadores))]

                    transf = 0
                    for _, _, uid, vid_origem in cand:
                        if falta <= 1e-6 or transf >= max(1, int(max_transferencias)):
                            break


                        if not desalocar_um(sol, uid, vid_origem, instancia):
                            continue
                        if not alocar_um(sol, uid, v_alvo_id, instancia):

                            alocar_um(sol, uid, vid_origem, instancia)
                            continue

                        movidos.append((uid, vid_origem))
                        falta -= float(ums_id[uid].get("peso", 0.0) or 0.0)
                        transf += 1

                    if falta > 1e-6:
                        ok = False

            if ok:
                if float(sol.get("custo", 0.0)) < custo_inicial - 1e-6:
                    if VERBOSE:
                        print(f"[{CTX}] Aceitou: abriu {v_alvo_id}, inseriu UM={um_alvo_id}, "
                              f"movidos={len(movidos)}. custo {custo_inicial:.2f} -> {float(sol.get('custo',0.0)):.2f}")
                    return True


            for uid, vid_origem in reversed(movidos):
                desalocar_um(sol, uid, v_alvo_id, instancia)
                alocar_um(sol, uid, vid_origem, instancia)

            desalocar_um(sol, um_alvo_id, v_alvo_id, instancia)


    return False

def reconfigurar_frota_para_penalidade(
    sol,
    instancia,
    tipo_apoio="Carreta L",
    top_k_regioes=2,
    top_k_ums_por_regiao=3,
    max_veiculos_candidatos=6,
    max_mover_do_veiculo=14,
    max_destinos_realocar=10,
    max_puxar_para_min=6,
    max_doadores_considerados=16,
    max_veiculos_apoio_testados=4,
):
    global CTX
    CTX = inspect.currentframe().f_code.co_name

    if not sol.get("nao_alocadas"):
        return False

    if sol.get("custo") is None or "componentes_custo" not in sol:
        custo_total(sol, instancia)

    ums_id = instancia.get("ums_id")
    veiculos_id = instancia.get("veiculos_id")
    if ums_id is None:
        ums_id = {u["id"]: u for u in instancia["ums"]}
        instancia["ums_id"] = ums_id
    if veiculos_id is None:
        veiculos_id = {v["id"]: v for v in instancia["veiculos"]}
        instancia["veiculos_id"] = veiculos_id

    def _norm(x):
        return str(x) if x is not None else None

    def _peso(uid):
        return float(ums_id[uid].get("peso", 0.0) or 0.0)

    def _vol(uid):
        return float(ums_id[uid].get("volume", 0.0) or 0.0)

    def _pen(uid):
        return float(ums_id[uid].get("penalidade", 0.0) or 0.0)


    def _snapshot_veic(d):
        ums = d.get("ums", set())
        if isinstance(ums, list):
            ums = set(ums)
        return {
            "ativo": bool(d.get("ativo", False)),
            "regiao": d.get("regiao", None),
            "peso_usado": float(d.get("peso_usado", 0.0) or 0.0),
            "volume_usado": float(d.get("volume_usado", 0.0) or 0.0),
            "ums": list(ums),
        }

    def _restore_veic(d, snap):
        d["ativo"] = bool(snap.get("ativo", False))
        d["regiao"] = snap.get("regiao", None)
        d["peso_usado"] = float(snap.get("peso_usado", 0.0) or 0.0)
        d["volume_usado"] = float(snap.get("volume_usado", 0.0) or 0.0)
        d["ums"] = set(snap.get("ums", []))

    def _zerar_veic_para_migrar(d):
        d["ums"] = set()
        d["peso_usado"] = 0.0
        d["volume_usado"] = 0.0
        d["regiao"] = None
        d["ativo"] = False


    todos_vids = list(sol["veiculo_dados"].keys())

    def tipo_veiculo(vid):
        v = veiculos_id[vid]
        return str(v.get("tipo") or v.get("descricao") or v.get("nome") or "")


    def rebuild_ativos_por_reg():
        m = {}
        for vid in todos_vids:
            d = sol["veiculo_dados"][vid]
            ums = d.get("ums", set())
            if isinstance(ums, list):
                d["ums"] = set(ums)
                ums = d["ums"]
            if len(ums) == 0:
                continue
            reg = _norm(d.get("regiao", None))
            if reg is not None:
                m.setdefault(reg, []).append(vid)
        return m

    ativos_por_reg = rebuild_ativos_por_reg()


    def cabe_em(um_id, vid):
        um = ums_id[um_id]
        veic = veiculos_id[vid]
        d = sol["veiculo_dados"][vid]
        cap_p = float(veic.get("capacidade_peso", 0.0))
        cap_v = float(veic.get("capacidade_volume", 0.0))
        if float(d.get("peso_usado", 0.0)) + float(um.get("peso", 0.0) or 0.0) > cap_p + 1e-9:
            return False
        if float(d.get("volume_usado", 0.0)) + float(um.get("volume", 0.0) or 0.0) > cap_v + 1e-9:
            return False
        return True


    def ok_cmin_apos_remover(vid, um_id):
        veic = veiculos_id[vid]
        cmin = float(veic.get("carga_minima", 0.0) or 0.0)
        if cmin <= 1e-9:
            return True
        d = sol["veiculo_dados"][vid]
        ums = d.get("ums", set())
        if isinstance(ums, list):
            d["ums"] = set(ums)
            ums = d["ums"]
        if um_id not in ums:
            return True
        if len(ums) <= 1:
            return True
        peso_depois = float(d.get("peso_usado", 0.0)) - _peso(um_id)
        return (peso_depois + 1e-9 >= cmin)


    def melhor_destino_mesma_regiao(um_id, reg, vid_bloqueado):
        cand = []
        for vdest in ativos_por_reg.get(reg, []):
            if vdest == vid_bloqueado:
                continue
            if not um_compatível_com_veiculo(ums_id[um_id], veiculos_id[vdest]):
                continue
            if not cabe_em(um_id, vdest):
                continue
            delta = delta_insercao(sol, instancia, ums_id[um_id], veiculos_id[vdest])
            cand.append((delta, vdest))
        if not cand:
            return None
        cand.sort(key=lambda x: x[0])
        return cand[0][1]

    def rollback_reloc(reloc, vid_origem):

        for uid, vdest in reversed(reloc):
            desalocar_um(sol, uid, vdest, instancia)
            alocar_um(sol, uid, vid_origem, instancia)


    def tentar_esvaziar_veiculo(vid):
        d = sol["veiculo_dados"][vid]
        reg = _norm(d.get("regiao", None))
        if reg is None:
            return False, [], []

        ums = d.get("ums", set())
        if isinstance(ums, list):
            d["ums"] = set(ums)
            ums = d["ums"]

        reloc = []
        travadas = []

        ums_no = list(ums)
        ums_no.sort(key=lambda uid: -_peso(uid))


        if len(ums_no) > max_mover_do_veiculo:
            return False, [], ["LIMITE_MAX_MOVER"]

        for uid in ums_no:
            if not ok_cmin_apos_remover(vid, uid):
                travadas.append(uid)
                return False, reloc, travadas

            vdest = melhor_destino_mesma_regiao(uid, reg, vid)
            if vdest is None:
                travadas.append(uid)
                return False, reloc, travadas

            if not desalocar_um(sol, uid, vid, instancia):
                travadas.append(uid)
                return False, reloc, travadas

            if not alocar_um(sol, uid, vdest, instancia):
                alocar_um(sol, uid, vid, instancia)
                travadas.append(uid)
                return False, reloc, travadas

            reloc.append((uid, vdest))


        d2 = sol["veiculo_dados"][vid]
        ums2 = d2.get("ums", set())
        if isinstance(ums2, list):
            d2["ums"] = set(ums2)
            ums2 = d2["ums"]
        if len(ums2) != 0:
            return False, reloc, ["NAO_ESVAZIOU"]

        return True, reloc, []


    penal_por_reg = {}
    nao = list(sol["nao_alocadas"])
    for uid in nao:
        um = ums_id.get(uid)
        if um is None:
            continue
        reg = _norm(um.get("destino", None))
        if reg is None:
            continue
        penal_por_reg[reg] = penal_por_reg.get(reg, 0.0) + _pen(uid)

    if not penal_por_reg:
        return False

    regioes_criticas = sorted(penal_por_reg.items(), key=lambda x: x[1], reverse=True)
    regioes_criticas = [r for r, _ in regioes_criticas[:max(1, int(top_k_regioes))]]


    for reg_alvo in regioes_criticas:

        ums_na_reg = [uid for uid in nao if _norm(ums_id[uid].get("destino", None)) == reg_alvo]
        if not ums_na_reg:
            continue
        ums_na_reg.sort(key=lambda uid: _pen(uid), reverse=True)
        ums_na_reg = ums_na_reg[:max(1, int(top_k_ums_por_regiao))]

        for um_alvo_id in ums_na_reg:
            um_alvo = ums_id.get(um_alvo_id)
            if um_alvo is None:
                continue


            cand_migrar = []
            for vid in todos_vids:
                d = sol["veiculo_dados"][vid]
                ums_v = d.get("ums", set())
                if isinstance(ums_v, list):
                    d["ums"] = set(ums_v)
                    ums_v = d["ums"]
                if not d.get("ativo", False) or len(ums_v) == 0:
                    continue

                reg_vid = _norm(d.get("regiao", None))
                if reg_vid is None or reg_vid == reg_alvo:
                    continue

                if not um_compatível_com_veiculo(um_alvo, veiculos_id[vid]):
                    continue

                cand_migrar.append((len(ums_v), vid))

            if not cand_migrar:
                continue

            cand_migrar.sort()
            cand_migrar = [vid for _, vid in cand_migrar[:max(1, int(max_veiculos_candidatos))]]

            for v_migrar in cand_migrar:
                d_m = sol["veiculo_dados"][v_migrar]
                reg_origem = _norm(d_m.get("regiao", None))
                if reg_origem is None:
                    continue

                custo_antes = float(sol.get("custo", 0.0))


                snap_migrar = _snapshot_veic(d_m)


                ok, reloc, travadas = tentar_esvaziar_veiculo(v_migrar)


                v_apoio = None
                snap_apoio = None
                reloc_apoio = []
                travadas_movidas = []


                if (not ok) and travadas and travadas not in (["LIMITE_MAX_MOVER"], ["NAO_ESVAZIOU"]):

                    cand_apoio = []
                    for vid2 in todos_vids:
                        d2 = sol["veiculo_dados"][vid2]
                        ums2 = d2.get("ums", set())
                        if isinstance(ums2, list):
                            d2["ums"] = set(ums2)
                            ums2 = d2["ums"]
                        if not d2.get("ativo", False) or len(ums2) == 0:
                            continue

                        reg2 = _norm(d2.get("regiao", None))
                        if reg2 is None or reg2 == reg_origem:
                            continue

                        if tipo_veiculo(vid2) != tipo_apoio:
                            continue

                        cand_apoio.append((len(ums2), vid2))

                    cand_apoio.sort()
                    cand_apoio = [vid for _, vid in cand_apoio[:max(1, int(max_veiculos_apoio_testados))]]

                    for v2 in cand_apoio:
                        d2 = sol["veiculo_dados"][v2]
                        snap2 = _snapshot_veic(d2)

                        ok2, reloc2, trav2 = tentar_esvaziar_veiculo(v2)
                        if not ok2:
                            rollback_reloc(reloc2, v2)
                            _restore_veic(d2, snap2)
                            continue


                        _zerar_veic_para_migrar(sol["veiculo_dados"][v2])


                        moveu = []
                        ok_put = True
                        for uid_trava in travadas[:3]:
                            if not um_compatível_com_veiculo(ums_id[uid_trava], veiculos_id[v2]):
                                ok_put = False
                                break
                            if not cabe_em(uid_trava, v2):
                                ok_put = False
                                break
                            if not desalocar_um(sol, uid_trava, v_migrar, instancia):
                                ok_put = False
                                break
                            if not alocar_um(sol, uid_trava, v2, instancia):
                                alocar_um(sol, uid_trava, v_migrar, instancia)
                                ok_put = False
                                break
                            moveu.append(uid_trava)

                        if not ok_put:

                            for uid_trava in reversed(moveu):
                                desalocar_um(sol, uid_trava, v2, instancia)
                                alocar_um(sol, uid_trava, v_migrar, instancia)

                            rollback_reloc(reloc2, v2)
                            _restore_veic(sol["veiculo_dados"][v2], snap2)
                            continue


                        v_apoio = v2
                        snap_apoio = snap2
                        reloc_apoio = reloc2
                        travadas_movidas = moveu
                        break


                    if v_apoio is not None:
                        ok, reloc, travadas = tentar_esvaziar_veiculo(v_migrar)

                if not ok:

                    if v_apoio is not None:
                        for uid_trava in reversed(travadas_movidas):
                            desalocar_um(sol, uid_trava, v_apoio, instancia)
                            alocar_um(sol, uid_trava, v_migrar, instancia)

                        rollback_reloc(reloc_apoio, v_apoio)
                        _restore_veic(sol["veiculo_dados"][v_apoio], snap_apoio)

                    rollback_reloc(reloc, v_migrar)
                    _restore_veic(sol["veiculo_dados"][v_migrar], snap_migrar)

                    ativos_por_reg = rebuild_ativos_por_reg()
                    continue


                _zerar_veic_para_migrar(sol["veiculo_dados"][v_migrar])


                if (not um_compatível_com_veiculo(um_alvo, veiculos_id[v_migrar])) or (not cabe_em(um_alvo_id, v_migrar)):

                    _restore_veic(sol["veiculo_dados"][v_migrar], snap_migrar)
                    rollback_reloc(reloc, v_migrar)

                    if v_apoio is not None:
                        for uid_trava in reversed(travadas_movidas):
                            desalocar_um(sol, uid_trava, v_apoio, instancia)
                            alocar_um(sol, uid_trava, v_migrar, instancia)
                        rollback_reloc(reloc_apoio, v_apoio)
                        _restore_veic(sol["veiculo_dados"][v_apoio], snap_apoio)

                    ativos_por_reg = rebuild_ativos_por_reg()
                    continue

                if not alocar_um(sol, um_alvo_id, v_migrar, instancia):

                    _restore_veic(sol["veiculo_dados"][v_migrar], snap_migrar)
                    rollback_reloc(reloc, v_migrar)

                    if v_apoio is not None:
                        for uid_trava in reversed(travadas_movidas):
                            desalocar_um(sol, uid_trava, v_apoio, instancia)
                            alocar_um(sol, uid_trava, v_migrar, instancia)
                        rollback_reloc(reloc_apoio, v_apoio)
                        _restore_veic(sol["veiculo_dados"][v_apoio], snap_apoio)

                    ativos_por_reg = rebuild_ativos_por_reg()
                    continue


                movidos_min = []
                veic_new = veiculos_id[v_migrar]
                cmin = float(veic_new.get("carga_minima", 0.0) or 0.0)
                okmin = True

                ativos_por_reg = rebuild_ativos_por_reg()

                if cmin > 1e-9:
                    dnew = sol["veiculo_dados"][v_migrar]
                    falta = cmin - float(dnew.get("peso_usado", 0.0))
                    if falta > 1e-6:
                        cand = []
                        for vdoa in ativos_por_reg.get(reg_alvo, []):
                            if vdoa == v_migrar:
                                continue
                            ddoa = sol["veiculo_dados"][vdoa]
                            ums_doa = ddoa.get("ums", set())
                            if isinstance(ums_doa, list):
                                ddoa["ums"] = set(ums_doa)
                                ums_doa = ddoa["ums"]

                            veic_doa = veiculos_id[vdoa]
                            cmin_doa = float(veic_doa.get("carga_minima", 0.0) or 0.0)

                            for uid in list(ums_doa):
                                if not um_compatível_com_veiculo(ums_id[uid], veic_new):
                                    continue
                                if not cabe_em(uid, v_migrar):
                                    continue
                                if len(ums_doa) > 1 and cmin_doa > 1e-9:
                                    if float(ddoa.get("peso_usado", 0.0)) - _peso(uid) + 1e-9 < cmin_doa:
                                        continue
                                cand.append((_pen(uid), -_peso(uid), uid, vdoa))

                        cand.sort()
                        cand = cand[:max(1, int(max_doadores_considerados))]

                        transf = 0
                        for _, __, uid, vdoa in cand:
                            if falta <= 1e-6 or transf >= max(1, int(max_puxar_para_min)):
                                break
                            if not desalocar_um(sol, uid, vdoa, instancia):
                                continue
                            if not alocar_um(sol, uid, v_migrar, instancia):
                                alocar_um(sol, uid, vdoa, instancia)
                                continue
                            movidos_min.append((uid, vdoa))
                            falta -= _peso(uid)
                            transf += 1

                        if falta > 1e-6:
                            okmin = False

                if okmin and float(sol.get("custo", 0.0)) < custo_antes - 1e-6:
                    return True


                for uid, vdoa in reversed(movidos_min):
                    desalocar_um(sol, uid, v_migrar, instancia)
                    alocar_um(sol, uid, vdoa, instancia)

                desalocar_um(sol, um_alvo_id, v_migrar, instancia)

                rollback_reloc(reloc, v_migrar)
                _restore_veic(sol["veiculo_dados"][v_migrar], snap_migrar)

                if v_apoio is not None:
                    for uid_trava in reversed(travadas_movidas):
                        desalocar_um(sol, uid_trava, v_apoio, instancia)
                        alocar_um(sol, uid_trava, v_migrar, instancia)

                    rollback_reloc(reloc_apoio, v_apoio)
                    _restore_veic(sol["veiculo_dados"][v_apoio], snap_apoio)

                ativos_por_reg = rebuild_ativos_por_reg()

    return False

def ativar_ou_migrar_tipo_por_score_tipo_regiao(
    sol,
    instancia,
    top_k_regioes=4,
    top_k_pares=6,
    top_k_ums_regiao=25,
    max_veiculos_candidatos=8,
    max_insercoes=10,
    max_doadores_min=18,
    max_puxar_min=6,
    max_ums_para_esvaziar=22,
    max_destinos_por_um=14,
    preferir_migracao=True,
):

    global CTX
    CTX = inspect.currentframe().f_code.co_name

    if not sol.get("nao_alocadas"):
        return False

    if sol.get("custo") is None or "componentes_custo" not in sol:
        custo_total(sol, instancia)

    ums_id = instancia.get("ums_id")
    veiculos_id = instancia.get("veiculos_id")
    if ums_id is None:
        ums_id = {u["id"]: u for u in instancia["ums"]}
        instancia["ums_id"] = ums_id
    if veiculos_id is None:
        veiculos_id = {v["id"]: v for v in instancia["veiculos"]}
        instancia["veiculos_id"] = veiculos_id

    def _norm(x):
        return str(x) if x is not None else None

    def _ensure_set(d):
        if "ums" not in d or d["ums"] is None:
            d["ums"] = set()
        elif isinstance(d["ums"], list):
            d["ums"] = set(d["ums"])

    def _pen(uid):
        return float(ums_id[uid].get("penalidade", 0.0) or 0.0)

    def _peso(uid):
        return float(ums_id[uid].get("peso", 0.0) or 0.0)

    def _tipo(vid):
        v = veiculos_id[vid]
        return str(v.get("tipo") or v.get("descricao") or v.get("nome") or "")

    todos_vids = list(sol["veiculo_dados"].keys())
    nao = list(sol["nao_alocadas"])


    veic_exemplo_por_tipo = {}
    for vid in todos_vids:
        t = _tipo(vid)
        if t not in veic_exemplo_por_tipo:
            veic_exemplo_por_tipo[t] = vid

    def _tipos_compativeis(uid):
        um = ums_id[uid]
        comp = []
        for t, vid_ex in veic_exemplo_por_tipo.items():
            if um_compatível_com_veiculo(um, veiculos_id[vid_ex]):
                comp.append(t)
        return comp


    def _ativos_por_regiao_e_tipos_e_vazios():
        ativos = {}
        tipos = {}
        vazios = []
        for vid in todos_vids:
            d = sol["veiculo_dados"][vid]
            _ensure_set(d)
            if len(d["ums"]) == 0:
                vazios.append(vid)
                continue
            reg = _norm(d.get("regiao", None))
            if reg is None:
                continue
            ativos.setdefault(reg, []).append(vid)
            tipos.setdefault(reg, set()).add(_tipo(vid))
        return ativos, tipos, vazios

    ativos_reg, tipos_reg, vazios_globais = _ativos_por_regiao_e_tipos_e_vazios()


    score = {}
    penal_reg = {}
    cand_ums_por_reg = {}

    por_reg_tmp = {}
    for uid in nao:
        reg = _norm(ums_id[uid].get("destino", None))
        if reg is None:
            continue
        por_reg_tmp.setdefault(reg, []).append(uid)

    for reg, lista in por_reg_tmp.items():
        lista.sort(key=lambda u: _pen(u), reverse=True)
        lista = lista[:max(1, int(top_k_ums_regiao))]
        cand_ums_por_reg[reg] = lista
        penal_reg[reg] = sum(_pen(u) for u in lista)

        tipos_ativos = tipos_reg.get(reg, set())

        for uid in lista:
            comp = _tipos_compativeis(uid)
            k = len(comp)
            if k == 0:
                continue
            w = _pen(uid) / float(k)
            for t in comp:
                if t in tipos_ativos:
                    continue
                score[(reg, t)] = score.get((reg, t), 0.0) + w

    if not score:
        return False


    regioes_criticas = sorted(penal_reg.items(), key=lambda x: x[1], reverse=True)
    regioes_criticas = {r for r, _ in regioes_criticas[:max(1, int(top_k_regioes))]}

    pares = [(v, reg, t) for (reg, t), v in score.items() if reg in regioes_criticas]
    if not pares:
        return False

    pares.sort(reverse=True)
    pares = pares[:max(1, int(top_k_pares))]


    def _completar_minimo(vid, reg_alvo):
        veic = veiculos_id[vid]
        cmin = float(veic.get("carga_minima", 0.0) or 0.0)
        if cmin <= 1e-9:
            return True, []

        d = sol["veiculo_dados"][vid]
        falta = cmin - float(d.get("peso_usado", 0.0))
        if falta <= 1e-6:
            return True, []

        ativos2, _, _ = _ativos_por_regiao_e_tipos_e_vazios()

        cand = []
        for vdoa in ativos2.get(reg_alvo, []):
            if vdoa == vid:
                continue
            ddoa = sol["veiculo_dados"][vdoa]
            _ensure_set(ddoa)
            veic_doa = veiculos_id[vdoa]
            cmin_doa = float(veic_doa.get("carga_minima", 0.0) or 0.0)

            for uid in list(ddoa["ums"]):
                if not um_compatível_com_veiculo(ums_id[uid], veic):
                    continue

                if len(ddoa["ums"]) > 1 and cmin_doa > 1e-9:
                    peso_depois = float(ddoa.get("peso_usado", 0.0)) - _peso(uid)
                    if peso_depois + 1e-9 < cmin_doa:
                        continue
                cand.append((_pen(uid), -_peso(uid), uid, vdoa))

        cand.sort()
        cand = cand[:max(1, int(max_doadores_min))]

        mov = []
        puxou = 0
        for _, __, uid, vdoa in cand:
            if falta <= 1e-6 or puxou >= max(1, int(max_puxar_min)):
                break
            if not desalocar_um(sol, uid, vdoa, instancia):
                continue
            if not alocar_um(sol, uid, vid, instancia):
                alocar_um(sol, uid, vdoa, instancia)
                continue
            mov.append((uid, vdoa))
            falta -= _peso(uid)
            puxou += 1

        if falta > 1e-6:
            for uid, vdoa in reversed(mov):
                desalocar_um(sol, uid, vid, instancia)
                alocar_um(sol, uid, vdoa, instancia)
            return False, []

        return True, mov



    def _melhor_dest_origem(uid, reg_origem, vid_bloq):
        ativos2, _, vazios2 = _ativos_por_regiao_e_tipos_e_vazios()
        candidatos = []


        for vdest in ativos2.get(reg_origem, []):
            if vdest != vid_bloq:
                candidatos.append(vdest)


        candidatos.extend(vazios2)


        seen = set()
        cand = []
        for v in candidatos:
            if v == vid_bloq:
                continue
            if v in seen:
                continue
            seen.add(v)
            cand.append(v)

        random.shuffle(cand)
        cand = cand[:max(1, int(max_destinos_por_um))]

        melhor = None
        melhor_delta = float("inf")
        um = ums_id[uid]

        for vdest in cand:
            veic2 = veiculos_id[vdest]
            d2 = sol["veiculo_dados"][vdest]
            _ensure_set(d2)


            if len(d2["ums"]) > 0:
                reg2 = _norm(d2.get("regiao", None))
                if reg2 is not None and reg2 != reg_origem:
                    continue

            if not um_compatível_com_veiculo(um, veic2):
                continue


            cap_p = float(veic2.get("capacidade_peso", 0.0))
            cap_v = float(veic2.get("capacidade_volume", 0.0))
            if float(d2.get("peso_usado", 0.0)) + float(um.get("peso", 0.0) or 0.0) > cap_p + 1e-9:
                continue
            if float(d2.get("volume_usado", 0.0)) + float(um.get("volume", 0.0) or 0.0) > cap_v + 1e-9:
                continue

            delta = delta_insercao(sol, instancia, um, veic2)
            if delta < melhor_delta:
                melhor_delta = delta
                melhor = vdest

        return melhor

    def _rollback_reloc(reloc, vid_origem):
        for uid, vdest in reversed(reloc):
            desalocar_um(sol, uid, vdest, instancia)
            alocar_um(sol, uid, vid_origem, instancia)

    def _tentar_esvaziar_para_migrar(vid_migrar, reg_origem):
        d = sol["veiculo_dados"][vid_migrar]
        _ensure_set(d)
        ums_no = list(d["ums"])

        if len(ums_no) > max(1, int(max_ums_para_esvaziar)):
            return False, []

        ums_no.sort(key=lambda u: -_peso(u))
        reloc = []

        for uid in ums_no:
            vdest = _melhor_dest_origem(uid, reg_origem, vid_migrar)
            if vdest is None:
                _rollback_reloc(reloc, vid_migrar)
                return False, []

            if not desalocar_um(sol, uid, vid_migrar, instancia):
                _rollback_reloc(reloc, vid_migrar)
                return False, []

            if not alocar_um(sol, uid, vdest, instancia):
                alocar_um(sol, uid, vid_migrar, instancia)
                _rollback_reloc(reloc, vid_migrar)
                return False, []

            reloc.append((uid, vdest))

        _ensure_set(sol["veiculo_dados"][vid_migrar])
        if len(sol["veiculo_dados"][vid_migrar]["ums"]) != 0:
            _rollback_reloc(reloc, vid_migrar)
            return False, []

        return True, reloc


    def _tentar_abrir_e_inserir(vid, reg_alvo, tipo_alvo, lista_ums):
        custo_antes = float(sol.get("custo", 0.0))
        inseridas = []

        for uid in lista_ums:
            if len(inseridas) >= max(1, int(max_insercoes)):
                break
            if uid not in sol.get("nao_alocadas", set()):
                continue
            if not um_compatível_com_veiculo(ums_id[uid], veiculos_id[vid]):
                continue
            if not alocar_um(sol, uid, vid, instancia):
                continue
            inseridas.append(uid)

        if not inseridas:
            return False, [], []

        okmin, mov_min = _completar_minimo(vid, reg_alvo)

        if okmin and float(sol.get("custo", 0.0)) < custo_antes - 1e-6:
            return True, inseridas, mov_min


        for uid, vdoa in reversed(mov_min):
            desalocar_um(sol, uid, vid, instancia)
            alocar_um(sol, uid, vdoa, instancia)
        for uid in reversed(inseridas):
            desalocar_um(sol, uid, vid, instancia)

        return False, [], []


    for _, reg_alvo, tipo_alvo in pares:


        lista = list(cand_ums_por_reg.get(reg_alvo, []))
        if not lista:
            continue

        def _key_um(uid):
            comp = _tipos_compativeis(uid)
            k = len(comp) if comp else 99
            return (k, -_pen(uid), -_peso(uid))

        lista.sort(key=_key_um)


        if preferir_migracao:
            candidatos_migrar = []
            for vid in todos_vids:
                if _tipo(vid) != tipo_alvo:
                    continue
                d = sol["veiculo_dados"][vid]
                _ensure_set(d)
                if not d.get("ativo", False) or len(d["ums"]) == 0:
                    continue
                reg_origem = _norm(d.get("regiao", None))
                if reg_origem is None or reg_origem == reg_alvo:
                    continue
                candidatos_migrar.append((len(d["ums"]), vid))

            candidatos_migrar.sort()
            candidatos_migrar = [vid for _, vid in candidatos_migrar[:max(1, int(max_veiculos_candidatos))]]

            for vid_migrar in candidatos_migrar:
                d_m = sol["veiculo_dados"][vid_migrar]
                _ensure_set(d_m)
                reg_origem = _norm(d_m.get("regiao", None))
                if reg_origem is None:
                    continue

                custo_global_antes = float(sol.get("custo", 0.0))

                ok, reloc = _tentar_esvaziar_para_migrar(vid_migrar, reg_origem)
                if not ok:
                    continue


                d0 = sol["veiculo_dados"][vid_migrar]
                _ensure_set(d0)
                d0["ativo"] = False
                d0["regiao"] = None
                d0["peso_usado"] = 0.0
                d0["volume_usado"] = 0.0

                ok2, inseridas, mov_min = _tentar_abrir_e_inserir(vid_migrar, reg_alvo, tipo_alvo, lista)
                if ok2:

                    return True


                _rollback_reloc(reloc, vid_migrar)


                if float(sol.get("custo", 0.0)) > custo_global_antes + 1e-6:
                    custo_total(sol, instancia)


        vazios_tipo = []
        for vid in todos_vids:
            if _tipo(vid) != tipo_alvo:
                continue
            d = sol["veiculo_dados"][vid]
            _ensure_set(d)
            if len(d["ums"]) == 0:
                vazios_tipo.append(vid)

        random.shuffle(vazios_tipo)
        vazios_tipo = vazios_tipo[:max(1, int(max_veiculos_candidatos))]

        for vid_novo in vazios_tipo:
            ok2, _, _ = _tentar_abrir_e_inserir(vid_novo, reg_alvo, tipo_alvo, lista)
            if ok2:
                return True

    return False

def aplicar_restricao_carga_minima(solucao, dados):

    global CTX
    CTX = inspect.currentframe().f_code.co_name

    ids_veiculos = list(solucao['veiculo_dados'].keys())

    ums_id = dados.get('ums_id', None)
    veiculos_id = dados.get('veiculos_id', None)
    if ums_id is None:
        ums_id = {u['id']: u for u in dados['ums']}
        dados['ums_id'] = ums_id
    if veiculos_id is None:
        veiculos_id = {v['id']: v for v in dados['veiculos']}
        dados['veiculos_id'] = veiculos_id

    if solucao.get('custo') is None or 'componentes_custo' not in solucao:
        custo_total(solucao, dados)

    def _norm(x):
        return str(x) if x is not None else None

    for v_id in ids_veiculos:
        v_dados = solucao['veiculo_dados'][v_id]

        if not v_dados.get('ativo', False):
            continue

        veiculo_info = veiculos_id[v_id]
        carga_minima = float(veiculo_info.get('carga_minima', 0.0) or 0.0)

        if float(v_dados.get('peso_usado', 0.0)) + 1e-9 >= carga_minima:
            continue




        candidatos = list(solucao.get('nao_alocadas', set()))
        if candidatos:
            candidatos.sort(key=lambda uid: float(ums_id[uid].get('peso', 0.0) or 0.0), reverse=True)

            reg_v = _norm(v_dados.get('regiao', None))
            if reg_v is not None:
                mesmos = [uid for uid in candidatos if _norm(ums_id[uid].get('destino', None)) == reg_v]
                outros = [uid for uid in candidatos if uid not in set(mesmos)]
                candidatos = mesmos + outros

            cap_p = float(veiculo_info.get('capacidade_peso', 0.0) or 0.0)
            cap_v = float(veiculo_info.get('capacidade_volume', 0.0) or 0.0)

            for um_id in candidatos:
                um = ums_id[um_id]

                peso_after = float(v_dados.get('peso_usado', 0.0)) + float(um.get('peso', 0.0) or 0.0)
                vol_after  = float(v_dados.get('volume_usado', 0.0)) + float(um.get('volume', 0.0) or 0.0)
                if peso_after > cap_p + 1e-9 or vol_after > cap_v + 1e-9:
                    continue

                if alocar_um(solucao, um_id, v_id, dados):
                    if float(v_dados.get('peso_usado', 0.0)) + 1e-9 >= carga_minima:
                        break

        if float(v_dados.get('peso_usado', 0.0)) + 1e-9 >= carga_minima:
            continue





        ums_para_mover = list(v_dados.get('ums', set()))
        if ums_para_mover:
            ums_para_mover.sort(key=lambda uid: float(ums_id[uid].get('peso', 0.0) or 0.0), reverse=True)

            for um_id in ums_para_mover:
                if float(v_dados.get('peso_usado', 0.0)) + 1e-9 >= carga_minima:
                    break

                um = ums_id.get(um_id, None)
                if um is None:
                    continue

                destino_um = _norm(um.get('destino', None))
                peso_u = float(um.get('peso', 0.0) or 0.0)
                vol_u  = float(um.get('volume', 0.0) or 0.0)


                mesma_reg = []
                outras_reg = []

                for v_dest_id in ids_veiculos:
                    if v_dest_id == v_id:
                        continue

                    d2 = solucao['veiculo_dados'][v_dest_id]
                    if not d2.get('ativo', False):
                        continue


                    if len(d2.get('ums', [])) > 0:
                        reg2 = _norm(d2.get('regiao', None))
                        if destino_um is not None and reg2 == destino_um:
                            mesma_reg.append(v_dest_id)
                        else:
                            outras_reg.append(v_dest_id)
                    else:

                        outras_reg.append(v_dest_id)


                def _folga(v_dest_id):
                    d2 = solucao['veiculo_dados'][v_dest_id]
                    veic2 = veiculos_id[v_dest_id]
                    cap_p2 = float(veic2.get('capacidade_peso', 0.0) or 0.0)
                    cap_v2 = float(veic2.get('capacidade_volume', 0.0) or 0.0)
                    folga_p = cap_p2 - float(d2.get('peso_usado', 0.0))
                    folga_v = cap_v2 - float(d2.get('volume_usado', 0.0))
                    return (folga_p + folga_v)

                mesma_reg.sort(key=_folga, reverse=True)
                outras_reg.sort(key=_folga, reverse=True)


                melhor_dest = None
                melhor_delta = float("inf")

                def _avaliar_lista(lista_ids):
                    nonlocal melhor_dest, melhor_delta

                    for v_dest_id in lista_ids:
                        d2 = solucao['veiculo_dados'][v_dest_id]
                        veic2 = veiculos_id[v_dest_id]


                        if len(d2.get('ums', [])) > 0:
                            reg2 = _norm(d2.get('regiao', None))
                            if reg2 is not None and destino_um is not None and reg2 != destino_um:
                                continue


                        if not um_compatível_com_veiculo(um, veic2):
                            continue


                        cap_p2 = float(veic2.get('capacidade_peso', 0.0) or 0.0)
                        cap_v2 = float(veic2.get('capacidade_volume', 0.0) or 0.0)
                        peso_after = float(d2.get('peso_usado', 0.0)) + peso_u
                        vol_after  = float(d2.get('volume_usado', 0.0)) + vol_u
                        if peso_after > cap_p2 + 1e-9 or vol_after > cap_v2 + 1e-9:
                            continue


                        carga_min_dest = float(veic2.get('carga_minima', 0.0) or 0.0)
                        if carga_min_dest > 0.0 and (len(d2.get('ums', [])) == 0 or not d2.get('ativo', False)):
                            if peso_after + 1e-9 < carga_min_dest:
                                continue

                        delta = delta_insercao(solucao, dados, um, veic2)
                        if delta < melhor_delta:
                            melhor_delta = delta
                            melhor_dest = v_dest_id

                _avaliar_lista(mesma_reg)

                if melhor_dest is None:
                    _avaliar_lista(outras_reg)

                if melhor_dest is None:
                    continue


                if not desalocar_um(solucao, um_id, v_id, dados):
                    continue
                if not alocar_um(solucao, um_id, melhor_dest, dados):
                    alocar_um(solucao, um_id, v_id, dados)




        if v_dados.get('ativo', False) and float(v_dados.get('peso_usado', 0.0)) + 1e-9 < carga_minima:
            ums_no_veiculo = list(v_dados.get('ums', set()))
            for um_id in ums_no_veiculo:
                desalocar_um(solucao, um_id, v_id, dados)

    return solucao

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
        'nome_instancia': resultado.get('nome_instancia', 'N/A'),
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

    caminho_saida = os.path.join(os.path.dirname(__file__), OUT_FOLDER, 'Resultados - Heurística')
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

                _valor_ou_na(sol_inicial.get('peso_nao_alocado', 0.0),2), _valor_ou_na(resultados.get('peso_nao_alocado', 0.0),2),
                _valor_ou_na(sol_inicial.get('volume_nao_alocado', 0.0),2), _valor_ou_na(resultados.get('volume_nao_alocado', 0.0),2)
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

                "N/A", _valor_ou_na(resultados.get('peso_nao_alocado', 0.0),2),
                "N/A", _valor_ou_na(resultados.get('volume_nao_alocado', 0.0),2)
            ])

    print(f"✅ Resumo geral (append) salvo em: {caminho_completo_resumo}")

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

        print(f" Erro na paleta: {e}. Usando paleta padrão.")
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

def executar_heuristica_na_pasta(pasta_instancias=INSTANCIAS,
                              ordem_vnd = [
                            "insercao_nao_alocada",
                            "troca_alocada_nao_alocada",
                            "realocacao_simples",
                            "troca_1x1",
                            "troca_1x2",
                            "ativar_ou_migrar_tipo_por_score_tipo_regiao",
                            "abrir_veiculo_formar_minimo_e_inserir_um",
                            "reconfigurar_frota_para_penalidade",
                            "liberar_veiculo_para_um_cara"
                            ],
                              n_sementes=N_SEMENTES, out_folder=OUT_FOLDER):

    if not os.path.exists(out_folder):
        os.makedirs(out_folder)


    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


    arquivo_resumo = os.path.join(out_folder, f'metodo2_resultados_{timestamp}.csv')


    arquivo_detalhado = os.path.join(out_folder, f'metodo2_detalhado_{timestamp}.csv')

    arquivos = [f for f in os.listdir(pasta_instancias) if f.endswith('.csv')]

    arquivos.sort()

    resultados_totais_estruturados = []
    instancias_originais = []
    solucoes_iniciais_estruturadas = []

    print(f"Iniciando Método 2 (VND) em {len(arquivos)} instâncias...")
    print(f"Saída Resumo: {arquivo_resumo}")
    print(f"Saída Detalhada: {arquivo_detalhado}")


    with open(arquivo_resumo, mode='w', newline='', encoding='utf-8-sig') as f_res, \
         open(arquivo_detalhado, mode='w', newline='', encoding='utf-8-sig') as f_det:


        writer_res = csv.writer(f_res, delimiter=';')
        writer_det = csv.writer(f_det, delimiter=';')


        writer_res.writerow([
            'Instancia',
            'Melhor Custo',
            'Media Custo',
            'Pior Custo',
            'Tempo Medio (s)',
            'Qtd Melhores',
            'N Sementes',
            'Ordem VND'
        ])


        writer_det.writerow([
            'Instancia',
            'Semente',
            'Custo',
            'Tempo Total (s)',
            'Iteracoes'
        ])

        for nome_arq in arquivos:
            caminho_completo = os.path.join(pasta_instancias, nome_arq)

            try:
                resultado = executar_heuristica_por_instancia(
                    caminho=caminho_completo,
                    ordem_vnd=ordem_vnd,
                    n_sementes=n_sementes
                )

                if resultado['solucao_global'] is not None:


                    dados_final = {
                        'solucao': resultado['solucao_global'],
                        'instancia': resultado['instancia_obj'],
                        'custo': resultado['melhor'],
                        'nome_instancia': resultado['instancia'],
                        'tempo_exec': resultado['tempo_medio']
                    }
                    resultado_estruturado = estruturar_resultados_heuristica(dados_final)


                    sol_ini_estruturada = None
                    if resultado.get('solucao_inicial_global') is not None:
                        dados_inicial = {
                            'solucao': resultado['solucao_inicial_global'],
                            'instancia': resultado['instancia_obj'],
                            'custo': resultado['solucao_inicial_global'].get('custo', 0.0),
                            'nome_instancia': resultado['instancia'],
                            'tempo_exec': 0.0
                        }
                        sol_ini_estruturada = estruturar_resultados_heuristica(dados_inicial)


                    resultados_totais_estruturados.append(resultado_estruturado)
                    instancias_originais.append(resultado['instancia_obj'])
                    solucoes_iniciais_estruturadas.append(sol_ini_estruturada)


                    exportar_resultados_csv_heuristica(
                        resultados_totais_estruturados,
                        instancias_originais,
                        solucoes_iniciais_estruturadas,
                        resultado_estruturado
                    )
                    print("  -> CSV detalhado (Metodo 2) exportado.")


                writer_res.writerow([
                    resultado['instancia'],
                    f"{resultado['melhor']:.2f}",
                    f"{resultado['media']:.2f}",
                    f"{resultado['pior']:.2f}",
                    f"{resultado['tempo_medio']:.4f}",
                    resultado['qtd_melhores'],
                    resultado['n_sementes']

                ])


                for semente_data in resultado['por_semente']:
                    writer_det.writerow([
                        resultado['instancia'],
                        semente_data['semente'] if 'semente' in semente_data else '',
                        f"{semente_data['best_custo']:.2f}",
                        f"{semente_data['tempo_total_execucao']:.4f}",
                        semente_data.get('iteracoes_executadas', 0)
                    ])


                f_res.flush()
                f_det.flush()

                print(f"> Processado: {nome_arq} | Melhor: {resultado['melhor']:.2f} | T.Medio: {resultado['tempo_medio']:.2f}s")

            except Exception as e:
                print(f"ERRO ao processar {nome_arq}: {e}")
                traceback.print_exc()

    print("\nExecução Finalizada com Sucesso!")

def vnd(sol, instancia, ordem_vnd, vizinhancas, max_passos_busca=100000, time_limit_busca=TIMEOUT):
    
    t0 = time.time()

    passos = 0

    while passos < max_passos_busca:
        if (time.time() - t0) > time_limit_busca:
            break

        melhorou_nessa_rodada = False

        for nome_viz in ordem_vnd:
            if (time.time() - t0) > time_limit_busca:
                break

            func_mov = vizinhancas[nome_viz]
            melhorou = func_mov(sol, instancia)

            if melhorou:
                passos += 1
                melhorou_nessa_rodada = True
                break

        if not melhorou_nessa_rodada:
            break

    return passos

def executar_heuristica_por_instancia(
    caminho,
    ordem_vnd,
    n_sementes=N_SEMENTES,
    n_iteracoes=100,
    criterio='penalidade',
    max_sem_melhora=MAX_SEM_MELHORA,
    max_passos_busca=100000,
    time_limit_busca=TIMEOUT
):
    instancia = carregar_dados(caminho)
    nome_instancia = os.path.basename(caminho).replace('.csv', '')

    vizinhancas = {
        'insercao_nao_alocada': realizar_insercao_nao_alocadas,
        'troca_alocada_nao_alocada': realizar_troca_alocada_por_nao_alocada,
        'realocacao_simples': realoca_entre_veiculos,
        'troca_1x1': realizar_troca_1x1,
        'troca_1x2': realizar_troca_1x2,
        'ativar_ou_migrar_tipo_por_score_tipo_regiao': ativar_ou_migrar_tipo_por_score_tipo_regiao,
        'abrir_veiculo_formar_minimo_e_inserir_um': abrir_veiculo_formar_minimo_e_inserir_um,
        'reconfigurar_frota_para_penalidade': reconfigurar_frota_para_penalidade,
        'liberar_veiculo_para_um_cara': liberar_veiculo_para_um_cara
    }

    resultados_por_semente = []
    custos_finais_por_semente = []
    tempos_totais_por_semente = []

    melhor_sol_global = None
    melhor_sol_inicial_global = None
    melhor_custo_global = float('inf')

    for semente in range(1, n_sementes + 1):

        t0_semente = time.time()
        melhor_custo_s = float('inf')
        melhor_sol_inicial_s = None

        sem_melhora = 0
        tempos_iter = []
        iteracoes_executadas = 0

        if VERBOSE:
            print(f"\n  --- Semente {semente}/{n_sementes} | VND ordem={ordem_vnd} ---")

        for rep in range(1, n_iteracoes + 1):

            tempo_decorrido = time.time() - t0_semente
            tempo_restante = time_limit_busca - tempo_decorrido
            if tempo_restante <= 0:
                break

            seed_rep = 1000 * semente + rep
            t0_iteracao = time.time()

            sol = gerar_solucao_gulosa(instancia, ordem=(criterio, seed_rep))
            aplicar_restricao_carga_minima(sol, instancia)
            custo_total(sol, instancia)

            sol_inicial_atual = copy.deepcopy(sol)

            _ = vnd(
                sol, instancia,
                ordem_vnd=ordem_vnd,
                vizinhancas=vizinhancas,
                max_passos_busca=max_passos_busca,
                time_limit_busca=tempo_restante
            )

            aplicar_restricao_carga_minima(sol, instancia)
            custo_total(sol, instancia)

            dt = time.time() - t0_iteracao
            tempos_iter.append(dt)
            iteracoes_executadas += 1

            custo_final = sol['custo']

            if custo_final < melhor_custo_s:
                melhor_custo_s = custo_final
                melhor_sol_s = copy.deepcopy(sol)
                melhor_sol_inicial_s = sol_inicial_atual
                sem_melhora = 0
                melhorou_global = True
            else:
                sem_melhora += 1

            if VERBOSE:
                print(
                    f"    Iter {rep}: seed={seed_rep} "
                    f"Custo={custo_final:.2f} MelhorCusto={melhor_custo_s:.2f} Tempo={dt:.1f}s "
                    f"Sem_melhora={sem_melhora}/{max_sem_melhora}"
                    + (" *" if melhorou_global else "")
                )

            if sem_melhora >= max_sem_melhora:
                if VERBOSE:
                    print(f"    Parou por sem_melhora={sem_melhora}/{max_sem_melhora}.")
                break

        tempo_total_semente = time.time() - t0_semente

        resultados_por_semente.append({
            'semente': semente,
            'best_custo': melhor_custo_s,
            'tempo_total_execucao': tempo_total_semente,
            'iteracoes_executadas': iteracoes_executadas
        })

        custos_finais_por_semente.append(melhor_custo_s)
        tempos_totais_por_semente.append(tempo_total_semente)



        if melhor_custo_s < melhor_custo_global - 1e-6:
            melhor_custo_global = melhor_custo_s
            melhor_sol_global = copy.deepcopy(melhor_sol_s)
            melhor_sol_inicial_global = melhor_sol_inicial_s

        if VERBOSE:
            print("alocar_por_ctx:", _prof.get("alocar_por_ctx", {}))
            print(f"  >> Semente {semente}: Best={melhor_custo_s:.2f} | TempoTotal={tempo_total_semente:.2f}s | it={iteracoes_executadas}")

        melhor_val = min(custos_finais_por_semente) if custos_finais_por_semente else 0.0
        pior_val = max(custos_finais_por_semente) if custos_finais_por_semente else 0.0
        media_val = sum(custos_finais_por_semente) / len(custos_finais_por_semente) if custos_finais_por_semente else 0.0
        tempo_medio = sum(tempos_totais_por_semente) / len(tempos_totais_por_semente) if tempos_totais_por_semente else 0.0

        qtd_melhores = sum(1 for c in custos_finais_por_semente if abs(c - melhor_val) < 1e-5)

    return {
        'instancia': nome_instancia,
        'instancia_obj': instancia,
        'solucao_global': melhor_sol_global,
        'solucao_inicial_global': melhor_sol_inicial_global,
        'metodo': 'Metodo 2',
        'criterio_gsi': criterio,
        'ordem_vnd': ordem_vnd,
        'n_sementes': n_sementes,
        'n_iteracoes': n_iteracoes,
        'max_sem_melhora': max_sem_melhora,
        'melhor': melhor_val,
        'media': media_val,
        'pior': pior_val,
        'tempo_medio': tempo_medio,
        'qtd_melhores': qtd_melhores,
        'por_semente': resultados_por_semente
    }

if __name__ == "__main__":
    executar_heuristica_na_pasta()


