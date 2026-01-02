import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import csv
from collections import defaultdict
from datetime import datetime
import os
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import PercentFormatter
import numpy as np
import networkx as nx
import matplotlib.colors as mcolors
import matplotlib.patches as patches

TIMEOUT = 3600 
INSTANCIAS = r"Instancias\Grupo2\Instancias_10v"



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
                    'custo': row['custo'],
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

    veiculos_por_tipo = {}
    for v in dados['veiculos']:
        if v['tipo'] not in veiculos_por_tipo:
            veiculos_por_tipo[v['tipo']] = []
        veiculos_por_tipo[v['tipo']].append(v)

    for um in dados['ums']:
        if um['custo_str'] and ',' in um['custo_str']:
            custos = [float(custo.strip()) for custo in um['custo_str'].split(',')]
            um['custos_por_tipo'] = {}
            for id_v, tipo in enumerate(veiculos_por_tipo.keys()):
                if id_v < len(custos):
                    um['custos_por_tipo'][tipo] = custos[id_v]
                else:
                    um['custos_por_tipo'][tipo] = 0.0
        else:
            custo_unico = float(um['custo_str']) if um['custo_str'] else 0.0
            um['custos_por_tipo'] = {tipo: custo_unico for tipo in veiculos_por_tipo.keys()}
    
    return dados


def criar_instancia(tipo_instancia):
    
    dados = carregar_dados(tipo_instancia) 
    
    return {
        "veiculos": dados['veiculos'],
        "ums": dados['ums'],
        "regioes": dados['regioes'],
        "parametros": dados['parametros']
    }



def criar_modelo(instancia):

    model = gp.Model("AlocacaoCargas")

    ums = instancia["ums"]
    veiculos = instancia["veiculos"]
    regioes = instancia["regioes"]
    parametros = instancia["parametros"]
    beta_valor = next((p["beta"] for p in parametros if p["descricao"].lower() == "beta"), 1.0) 
    beta = {v["id"]: beta_valor for v in veiculos }

    regioes_ordenadas = sorted(instancia["regioes"])  

    c_vr = {}
    for v in veiculos:
        custos_por_regiao = [float(c.strip()) for c in str(v['custo']).split(',')]
        for id_r, r in enumerate(regioes_ordenadas):
            if id_r < len(custos_por_regiao):
                c_vr[(v["id"], r)] = custos_por_regiao[id_r]
            else:
                c_vr[(v["id"], r)] = 0.0

    h_iv = {}
    for i in ums:
        for v in veiculos:
            custo = i.get('custos_por_tipo', {}).get(v['tipo'], 0.0)
            h_iv[(i['id'], v['id'])] = custo

    
    try:
        
        valores_c_vr = list(c_vr.values()) if 'c_vr' in locals() else []
        
        valores_h_iv = list(h_iv.values()) if 'h_iv' in locals() else []
        
        valores_beta = list(beta.values()) if 'beta' in locals() else []
        
        valores_penalidade = [i.get('penalidade', 0.0) for i in ums]

        print("\n--- DIAGNÓSTICO DE SINAIS E FAIXAS ---")
        if valores_h_iv:
            print("Custo transporte (h_iv): min =", min(valores_h_iv), "max =", max(valores_h_iv))
        else:
            print("Custo transporte (h_iv): N/A")

        if valores_c_vr:
            print("Custo ativação veículo (c_vr): min =", min(valores_c_vr), "max =", max(valores_c_vr))
        else:
            print("Custo ativação veículo (c_vr): N/A")

        if valores_beta:
            print("Beta (frete morto): min =", min(valores_beta), "max =", max(valores_beta))
        else:
            print("Beta (frete morto): N/A")

        if valores_penalidade:
            print("Penalidade por não alocação: min =", min(valores_penalidade), "max =", max(valores_penalidade))
        else:
            print("Penalidade por não alocação: N/A")

        
        negs = []
        if any(v < 0 for v in valores_h_iv): negs.append("h_iv")
        if any(v < 0 for v in valores_c_vr): negs.append("c_vr")
        if any(v < 0 for v in valores_beta): negs.append("beta")
        if any(v < 0 for v in valores_penalidade): negs.append("penalidade")
        if negs:
            print("Atenção: valores negativos detectados em:", ", ".join(negs))
        else:
            print("Nenhum coeficiente negativo detectado entre h_iv, c_vr, beta e penalidades.")
        print("--- FIM DO DIAGNÓSTICO ---\n")
    except Exception as e:
        print("Erro no diagnóstico automático:", e)

    
    delta = {}
    for v in veiculos:
        for r in regioes:
            delta[(v['id'], r)] = 1 

    
    theta = {}
    for i in ums:
        for r in regioes:
            theta[(i['id'], r)] = 1 if i['destino'] == r else 0

    
    gamma = {}
    for i in ums:
        comp_strs = [s.strip() for s in str(i.get("compatibilidade","")).split(",")]
        for v in veiculos:
            gamma[(i["id"], v["id"])] = 1 if v["tipo"].strip() in comp_strs else 0

    
    alpha = {}  
    for v in veiculos:
        for r in regioes:
            alpha[v["id"], r] = model.addVar(vtype=GRB.BINARY, name=f"alpha_{v['id']}_{r}")

    
    
    x = {}
    x = model.addVars([(i["id"], v["id"]) for i in ums for v in veiculos], vtype=gp.GRB.BINARY, name="x")

    
    
    
    custo_nao_alocacao_var = model.addVar(vtype=GRB.CONTINUOUS, name="custo_nao_alocacao")
    custo_alocacao_var = model.addVar(vtype=GRB.CONTINUOUS, name="custo_alocacao")
    custo_frete_morto_var = model.addVar(vtype=GRB.CONTINUOUS, name="custo_frete_morto")
    custo_transporte_var = model.addVar(vtype=GRB.CONTINUOUS, name="custo_transporte")

    

    
    custo_nao_alocacao = gp.quicksum(i["penalidade"] * (1 - gp.quicksum(x[(i["id"], v["id"])] for v in veiculos)) for i in ums) 
    
    
    custo_alocacao = gp.quicksum(c_vr[(v["id"], r)] * alpha[(v["id"], r)] for v in veiculos for r in regioes)    
    
    
    custo_frete_morto = gp.quicksum(beta[v["id"]] * (gp.quicksum(alpha[(v["id"], r)] for r in regioes) * v["capacidade_peso"]
        - gp.quicksum(i["peso"] * x[(i["id"], v["id"])] for i in ums)) for v in veiculos)

    
    custo_transporte = gp.quicksum(h_iv[(i["id"], v["id"])] * x[(i["id"], v["id"])] for i in ums for v in veiculos)

    
    model.addConstr(custo_nao_alocacao_var == custo_nao_alocacao, name="constr_custo_nao_alocacao")
    model.addConstr(custo_alocacao_var == custo_alocacao, name="constr_custo_alocacao")
    model.addConstr(custo_frete_morto_var == custo_frete_morto, name="constr_custo_frete_morto")
    model.addConstr(custo_transporte_var == custo_transporte, name="constr_custo_transporte")

    
    model.setObjective(custo_alocacao + custo_transporte + custo_frete_morto + custo_nao_alocacao, GRB.MINIMIZE)
    
    

    
    for v in veiculos:
        model.addConstr(
            gp.quicksum(i["peso"] * x[(i["id"], v["id"])] for i in ums) <= v["capacidade_peso"], 
            name=f"cap_peso_{v['id']}")
        
        model.addConstr(
            gp.quicksum(i["volume"] * x[(i["id"], v["id"])] for i in ums ) <= v["capacidade_volume"], 
            name=f"cap_vol_{v['id']}")

    
    for v in veiculos:
        for r in regioes:
            model.addConstr(
                gp.quicksum(i["peso"] * x[(i["id"], v["id"])] for i in ums) >= alpha[(v["id"], r)] * v["carga_minima"], 
                name=f"frete_morto_{v['id']}_{r}")
            
    
    for i in ums:
        model.addConstr(
            gp.quicksum(x[(i["id"], v["id"])] for v in veiculos ) <= 1, 
            name=f"alocacao_unica_{i['id']}")

    
    for i in ums:
        for v in veiculos:
            model.addConstr(
                x[(i["id"], v["id"])] <= gamma[(i['id'], v['id'])], 
                name=f"compat_{i['id']}_{v['id']}")

    
    for i in ums:
        r_i = i['destino']   
        for v in veiculos:
            model.addConstr(
                    x[(i["id"], v["id"])] <= (delta[(v['id'], r_i)] * alpha[(v["id"], r_i)]),
                    name=f"atendimento_{i['id']}_{v['id']}")
   
    
    for v in veiculos:
            model.addConstr(gp.quicksum(alpha[(v["id"], r)] for r in regioes) <= 1,
            name=f"uma_regiao_por_veiculo_{v['id']}")

    
    
    

    
    for i in ums:
        r_i = i["destino"] 
        for v in veiculos:
            model.addConstr(x[(i["id"], v["id"])] <= theta[(i["id"], r_i)],
            name=f"associa_carga_uma_regiao_{i['id']}_{v['id']}")

    return model, x, alpha, h_iv, c_vr, beta, custo_nao_alocacao_var, custo_alocacao_var, custo_frete_morto_var, custo_transporte_var




def calcular_relaxacao_linear(instancia):
    
    try:
        print("\n--- CALCULANDO RELAXAÇÃO LINEAR ---")
        
        ums = instancia["ums"]
        veiculos = instancia["veiculos"]
        regioes = instancia["regioes"]
        parametros = instancia["parametros"]
        
        
        beta_valor = next((p["beta"] for p in parametros if p["descricao"].lower() == "beta"), 1.0)
        beta = {v["id"]: beta_valor for v in veiculos}
        
        
        regioes_ordenadas = sorted(regioes)
        
        
        c_vr = {}
        for v in veiculos:
            custos_por_regiao = [float(c.strip()) for c in str(v['custo']).split(',')]
            for id_r, r in enumerate(regioes_ordenadas):
                if id_r < len(custos_por_regiao):
                    c_vr[(v["id"], r)] = custos_por_regiao[id_r]
                else:
                    c_vr[(v["id"], r)] = 0.0
        
        
        h_iv = {}
        veiculos_por_tipo = {}
        for v in veiculos:
            if v['tipo'] not in veiculos_por_tipo:
                veiculos_por_tipo[v['tipo']] = []
            veiculos_por_tipo[v['tipo']].append(v)
            
        for i in ums:
            for v in veiculos:
                custo = i.get('custos_por_tipo', {}).get(v['tipo'], 0.0)
                h_iv[(i['id'], v['id'])] = custo
        
        
        delta = {}
        for v in veiculos:
            for r in regioes:
                delta[(v['id'], r)] = 1
        
        theta = {}
        for i in ums:
            for r in regioes:
                theta[(i['id'], r)] = 1 if i['destino'] == r else 0
        
        gamma = {}
        for i in ums:
            comp_strs = [s.strip() for s in str(i.get("compatibilidade","")).split(",")]
            for v in veiculos:
                gamma[(i["id"], v["id"])] = 1 if v["tipo"].strip() in comp_strs else 0
        
        
        modelo_relaxado = gp.Model("RelaxacaoLinear")
        
        
        alpha_relax = {}
        for v in veiculos:
            for r in regioes:
                alpha_relax[v["id"], r] = modelo_relaxado.addVar(
                    vtype=GRB.CONTINUOUS, lb=0, ub=1, 
                    name=f"alpha_{v['id']}_{r}"
                )
        
        x_relax = {}
        for i in ums:
            for v in veiculos:
                x_relax[i["id"], v["id"]] = modelo_relaxado.addVar(
                    vtype=GRB.CONTINUOUS, lb=0, ub=1,
                    name=f"x_{i['id']}_{v['id']}"
                )
        
        
        
        for v in veiculos:
            modelo_relaxado.addConstr(
                gp.quicksum(i["peso"] * x_relax[(i["id"], v["id"])] for i in ums) <= v["capacidade_peso"], 
                name=f"cap_peso_{v['id']}"
            )
            modelo_relaxado.addConstr(
                gp.quicksum(i["volume"] * x_relax[(i["id"], v["id"])] for i in ums) <= v["capacidade_volume"], 
                name=f"cap_vol_{v['id']}"
            )
        
        
        for v in veiculos:
            for r in regioes:
                modelo_relaxado.addConstr(
                    gp.quicksum(i["peso"] * x_relax[(i["id"], v["id"])] for i in ums) >= alpha_relax[(v["id"], r)] * v["carga_minima"], 
                    name=f"frete_morto_{v['id']}_{r}"
                )
        
        
        for i in ums:
            modelo_relaxado.addConstr(
                gp.quicksum(x_relax[(i["id"], v["id"])] for v in veiculos) <= 1, 
                name=f"alocacao_unica_{i['id']}"
            )
        
        
        for i in ums:
            for v in veiculos:
                modelo_relaxado.addConstr(
                    x_relax[(i["id"], v["id"])] <= gamma[(i['id'], v['id'])], 
                    name=f"compat_{i['id']}_{v['id']}"
                )
        
        
        for i in ums:
            r_i = i['destino']   
            for v in veiculos:
                modelo_relaxado.addConstr(
                    x_relax[(i["id"], v["id"])] <= (delta[(v['id'], r_i)] * alpha_relax[(v["id"], r_i)]),
                    name=f"atendimento_{i['id']}_{v['id']}"
                )
        
        
        for v in veiculos:
            modelo_relaxado.addConstr(
                gp.quicksum(alpha_relax[(v["id"], r)] for r in regioes) <= 1,
                name=f"uma_regiao_por_veiculo_{v['id']}"
            )
        
        
        for i in ums:
            r_i = i["destino"]  
            for v in veiculos:
                modelo_relaxado.addConstr(
                    x_relax[(i["id"], v["id"])] <= theta[(i["id"], r_i)],
                    name=f"associa_carga_uma_regiao_{i['id']}_{v['id']}"
                )
        
        
        custo_nao_alocacao_relax = gp.quicksum(
            i["penalidade"] * (1 - gp.quicksum(x_relax[(i["id"], v["id"])] for v in veiculos)) 
            for i in ums
        )
        
        custo_alocacao_relax = gp.quicksum(
            c_vr[(v["id"], r)] * alpha_relax[(v["id"], r)] 
            for v in veiculos for r in regioes
        )
        
        
        frete_morto_aux = {}
        for v in veiculos:
            frete_morto_aux[v["id"]] = modelo_relaxado.addVar(
                vtype=GRB.CONTINUOUS, lb=0, name=f"frete_morto_aux_{v['id']}"
            )
            
            capacidade_utilizada = gp.quicksum(alpha_relax[(v["id"], r)] for r in regioes) * v["capacidade_peso"]
            carga_real = gp.quicksum(i["peso"] * x_relax[(i["id"], v["id"])] for i in ums)
            
            modelo_relaxado.addConstr(
                frete_morto_aux[v["id"]] >= 0,
                name=f"frete_morto_nonneg_{v['id']}"
            )
            modelo_relaxado.addConstr(
                frete_morto_aux[v["id"]] >= capacidade_utilizada - carga_real,
                name=f"frete_morto_calc_{v['id']}"
            )
        
        custo_frete_morto_relax = gp.quicksum(
            beta[v["id"]] * frete_morto_aux[v["id"]] for v in veiculos
        )
        
        custo_transporte_relax = gp.quicksum(
            h_iv[(i["id"], v["id"])] * x_relax[(i["id"], v["id"])] 
            for i in ums for v in veiculos
        )
        
        modelo_relaxado.setObjective(
            custo_alocacao_relax + custo_transporte_relax + custo_frete_morto_relax + custo_nao_alocacao_relax, 
            GRB.MINIMIZE
        )
        
        
        modelo_relaxado.setParam('OutputFlag', 0)  
        modelo_relaxado.optimize()
        
        if modelo_relaxado.status == GRB.OPTIMAL:
            print(f"Relaxação linear resolvida: {modelo_relaxado.ObjVal:.2f}")
            return modelo_relaxado.ObjVal
        else:
            print("Falha na relaxação linear")
            return None
            
    except Exception as e:
        print(f"Erro no cálculo da relaxação linear: {repr(e)}")
        import traceback
        traceback.print_exc()
        return None





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
    plt.figure(figsize=(10, 6))
    plt.bar(nome_base, resultados['tempo_execucao'], 
            color=CORES_PASTEL['azul_claro'], alpha=0.8)
    plt.axhline(y=TIMEOUT, color=CORES_PASTEL['rosa_claro'], 
                linestyle='--', label='Timeout', linewidth=2)
    plt.ylabel('Tempo (segundos)')
    plt.title('Tempo de Execução')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_tempo_execucao.png"), dpi=300)
    plt.close()

def plot_gap_otimizacao(resultados, pasta_saida, nome_base):
    if resultados['gap_otimizacao'] is not None:
        plt.figure(figsize=(8, 5))
        plt.bar(nome_base, resultados['gap_otimizacao'], 
                color=CORES_PASTEL['laranja_claro'], alpha=0.8)
        plt.ylabel('GAP (%)')
        plt.title('GAP de Otimização')
        plt.tight_layout()
        plt.savefig(os.path.join(pasta_saida, f"{nome_base}_gap_otimizacao.png"), dpi=300)
        plt.close()

def plot_status_solucao(resultados, pasta_saida, nome_base):
    status_map = {
        GRB.OPTIMAL: "Ótimo",
        GRB.TIME_LIMIT: "Timeout",
        GRB.INFEASIBLE: "Inviável",
        GRB.INF_OR_UNBD: "Infinito/Ilimitado",
        GRB.UNBOUNDED: "Ilimitado"
    }
    status = status_map.get(resultados['status'], "Desconhecido")

    cor_status = {
        "Ótimo": CORES_PASTEL['verde_claro'],
        "Timeout": CORES_PASTEL['laranja_claro'],
        "Inviável": CORES_PASTEL['rosa_claro'],
        "Infinito/Ilimitado": CORES_PASTEL['roxo_claro'],
        "Ilimitado": CORES_PASTEL['amarelo_claro'],
        "Desconhecido": CORES_PASTEL['cinza_claro']
    }

    plt.figure(figsize=(6, 6))
    plt.pie([1], labels=[status], autopct='%1.0f%%', 
            colors=[cor_status.get(status, CORES_PASTEL['cinza_claro'])])
    plt.title('Status da Solução')
    plt.tight_layout()
    plt.savefig(os.path.join(pasta_saida, f"{nome_base}_status_solucao.png"), dpi=300)
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
        
        print(f"Erro na paleta: {e}. Usando paleta padrão.")
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
    plot_status_solucao(resultados, pasta_saida, nome_base)

    
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



def executar_instancia_com_timeout(tipo_instancia, instancia):
    try:
        print(f"\n{'='*80}")
        print(f"INICIANDO INSTÂNCIA: {tipo_instancia.upper()}")
        print(f"{'='*80}")

        
        modelo, x, alpha, h_iv, c_vr, beta, custo_nao_alocacao_var, custo_alocacao_var, custo_frete_morto_var, custo_transporte_var = criar_modelo(instancia)

        
        relaxacao_linear = calcular_relaxacao_linear(instancia)

        
        print("\n--- RESOLVENDO MODELO INTEIRO ---")
        modelo.Params.TimeLimit = TIMEOUT
        log_path = os.path.join(os.path.dirname(__file__), INSTANCIAS, 'Resultados - Modelo Exato', f"gurobi_log_{tipo_instancia}.log")
        modelo.Params.LogFile = log_path
        modelo.Params.OutputFlag = 1
        
        modelo.optimize()

        
        gap_relaxacao = None
        
        
        if modelo.SolCount > 0 and relaxacao_linear is not None:
            melhor_solucao = modelo.ObjVal
            if melhor_solucao is not None and melhor_solucao > 0:
                gap_relaxacao = ((melhor_solucao - relaxacao_linear) / melhor_solucao) * 100

        
        resultados = {
            'tipo_instancia': tipo_instancia,
            'status': modelo.status,
            'tempo_execucao': modelo.Runtime,
            'custo_total': None,
            'veiculos_ativos': 0,
            'veiculos_inativos': len(instancia["veiculos"]),
            'ums_alocadas': 0,
            'ums_nao_alocadas': len(instancia["ums"]),
            'peso_nao_alocado': 0,
            'volume_nao_alocado': 0,
            'frete_morto_total': 0,
            'custo_transporte': 0,
            'custo_nao_alocacao': 0,
            'custo_alocacao': 0,
            'alocacoes': [],
            'tempo_para_otimo': modelo.RunTime if modelo.status == GRB.OPTIMAL else None,
            'melhor_solucao': modelo.ObjVal if modelo.SolCount > 0 else None,
            'solucao_relaxada': modelo.ObjBound if modelo.SolCount > 0 else None,
            'gap_otimizacao': modelo.MIPGap * 100 if hasattr(modelo, 'MIPGap') and modelo.SolCount > 0 else None,
            'relaxacao_linear': relaxacao_linear,
            'gap_relaxacao': gap_relaxacao
        }

        if modelo.SolCount > 0:
            
            x_val = {}
            for i in instancia["ums"]:
                for v in instancia["veiculos"]:
                    var = x.get((i["id"], v["id"]))
                    if var is not None:
                        x_val[(i["id"], v["id"])] = var.X
                    else:
                        x_val[(i["id"], v["id"])] = 0.0

            
            
            
            
            custo_alocacao = 0.0
            for v in instancia["veiculos"]:
                for r in instancia["regioes"]:
                    if alpha.get((v["id"], r)) is not None and alpha[(v["id"], r)].X > 0.5:
                        custo_alocacao += c_vr[(v["id"], r)]

            
            
            

            custo_transporte = 0.0
            for i in instancia["ums"]:
                for v in instancia["veiculos"]:
                    if x_val.get((i["id"], v["id"]), 0.0) > 0.5:
                        custo_unit = i.get('custos_por_tipo', {}).get(v['tipo'], 0.0)
                        custo_transporte += custo_unit
  
            
            
            

            frete_morto = {}
            carga_total_por_veiculo = {} 
            for v in instancia["veiculos"]:
                carga_total_por_veiculo[v["id"]] = sum(i["peso"] * x_val.get((i["id"], v["id"]), 0.0) for i in instancia["ums"])

            for v in instancia["veiculos"]: 
                for r in instancia["regioes"]:
                    if alpha.get((v["id"], r)) is not None and alpha[(v["id"], r)].X > 0.5:
                        fm = (max(0.0, v["capacidade_peso"] - carga_total_por_veiculo.get(v["id"], 0.0))) * beta[v["id"]] 
                        frete_morto[(v["id"], r)] = fm
                    else:
                        frete_morto[(v["id"], r)] = 0.0

            frete_morto_total = sum(frete_morto.values())

            
            
            

            custo_nao_alocacao = 0.0
            for i in instancia["ums"]:
                soma_alocacao = sum(x_val.get((i["id"], v["id"]), 0.0) for v in instancia["veiculos"])
                custo_nao_alocacao += i["penalidade"] * (1.0 - min(1.0, soma_alocacao)) 

            
            
            

            veiculos_ativos = 0
            for v in instancia["veiculos"]: 
                existe_x = any(x_val.get((i["id"], v["id"]), 0.0) > 0.9 for i in instancia["ums"])
                existe_alpha = any(alpha.get((v["id"], r)) is not None and alpha[(v["id"], r)].X > 0.5 for r in instancia["regioes"])
                if existe_x or existe_alpha:
                    veiculos_ativos += 1

            
            
            
            nao_alocadas = [i["id"] for i in instancia["ums"]
                            if all(x_val.get((i["id"], v["id"]), 0.0) < 0.1 for v in instancia["veiculos"])]
            
            
            
            

            resultados['custo_total'] = modelo.ObjVal
            resultados['veiculos_ativos'] = veiculos_ativos
            resultados['veiculos_inativos'] = len(instancia["veiculos"]) - veiculos_ativos
            resultados['ums_nao_alocadas'] = len(nao_alocadas)
            resultados['ums_alocadas'] = len(instancia["ums"]) - len(nao_alocadas)
            resultados['peso_nao_alocado'] = sum(i["peso"] for i in instancia["ums"] if i["id"] in nao_alocadas)
            resultados['volume_nao_alocado'] = sum(i["volume"] for i in instancia["ums"] if i["id"] in nao_alocadas)
            resultados['frete_morto_total'] = frete_morto_total
            resultados['custo_transporte'] = custo_transporte
            resultados['custo_alocacao'] = custo_alocacao
            resultados['custo_nao_alocacao'] = custo_nao_alocacao
            
            

            for v in instancia["veiculos"]:
                cargas = [i["id"] for i in instancia["ums"] if x_val.get((i["id"], v["id"]), 0.0) > 0.9]
                if cargas:
                    tipo_carga = [next((um["tipo"] for um in instancia["ums"] if um["id"] == um_id), "Desconhecido")
                                  for um_id in cargas]
                    peso_total = sum(i["peso"] for i in instancia["ums"] if i["id"] in cargas)
                    volume_total = round(sum(i["volume"] for i in instancia["ums"] if i["id"] in cargas),1)

                    frete_morto_por_veiculo = { (v_id, r): fm for (v_id, r), fm in frete_morto.items() if v_id == v["id"] }

                    custo_veic = 0.0
                    for r in instancia["regioes"]:
                        if alpha.get((v["id"], r)) is not None and alpha[(v["id"], r)].X > 0.5:
                            custo_veic = c_vr[(v["id"], r)]
                            break

                    regiao_por_veiculo = {}
                    for r in instancia["regioes"]:
                        if alpha.get((v["id"], r)) is not None and alpha[(v["id"], r)].X > 0.5:
                            regiao_por_veiculo[v["id"]] = r
                            break
                    else:
                        regiao_por_veiculo[v["id"]] = "Nenhuma"

                    resultados['alocacoes'].append({
                        'veiculo_id': v["id"],
                        'veiculo_tipo': v["tipo"],
                        'destino': regiao_por_veiculo.get(v["id"], "N/A"),
                        'cargas': cargas,
                        'tipos_um': tipo_carga,
                        'peso_total': peso_total,
                        'peso_minimo': v["carga_minima"],
                        'capacidade_peso': v["capacidade_peso"],
                        'volume_total': volume_total,
                        'capacidade_volume': v["capacidade_volume"],
                        'custo_veiculo': custo_veic,
                        'frete_morto': frete_morto_por_veiculo,
                        'taxa_utilizacao_peso': (peso_total / v["capacidade_peso"]) * 100 if v["capacidade_peso"] > 0 else 0.0,
                        'taxa_utilizacao_volume': (volume_total / v["capacidade_volume"]) * 100 if v["capacidade_volume"] > 0 else 0.0
                    })

        
        if resultados and modelo.SolCount > 0:
            pasta_visualizacoes = os.path.join(os.path.dirname(__file__), INSTANCIAS, 'Visualizacoes')
            gerar_visualizacoes(resultados, instancia, pasta_visualizacoes)
        return resultados
    
    except Exception as e:
        import traceback
        print(f"Erro ao processar instância {tipo_instancia}: {repr(e)}")
        traceback.print_exc()
        return None

def imprimir_resultados_detalhados(resultados):
    print(f"\n{'='*80}")
    print(f" RESULTADOS PARA INSTÂNCIA: {resultados['tipo_instancia'].upper()}")
    print(f"{'='*80}")

    
    status_map = {
        GRB.OPTIMAL: "Ótimo encontrado",
        GRB.TIME_LIMIT: "Tempo limite atingido",
        GRB.INFEASIBLE: "Problema inviável",
        GRB.INF_OR_UNBD: "Infinito ou ilimitado",
        GRB.UNBOUNDED: "Ilimitado"
    }

    
    

    
    

    
    
    

    if resultados['status'] == GRB.OPTIMAL or resultados['status'] == GRB.TIME_LIMIT:        
        def safe_format(value, fmt=".2f", prefix=""): 
            return f"{prefix}{value:{fmt}}" if value is not None else "N/A"

        print(f"\nCUSTOS:")
        print(f"  Total: {safe_format(resultados.get('custo_total'), '.2f', 'R$')}")
        print(f"  - Custo Atendimento: R$ {resultados['custo_alocacao']:.2f}")
        print(f"  - Transporte: {safe_format(resultados.get('custo_transporte'), '.2f', 'R$')}")
        print(f"  - Frete morto: {safe_format(resultados.get('frete_morto_total'), '.2f', 'R$')}")
        print(f"  - Não alocação: {safe_format(resultados.get('custo_nao_alocacao'), '.2f', 'R$')}")

        print(f"\nVEÍCULOS:")
        print(f"  Ativos: {resultados.get('veiculos_ativos', 'N/A')}")
        print(f"  Inativos: {resultados.get('veiculos_inativos', 'N/A')}")

        
        for aloc in resultados.get('alocacoes', []):
            print(f"\n  Veículo {aloc.get('veiculo_id', 'N/A')} ({aloc.get('veiculo_tipo', 'N/A')} para {aloc.get('destino', 'N/A')}):")
            print(f"    Cargas: {aloc.get('cargas', 'N/A')}")
            print(f"    Peso: {safe_format(aloc.get('peso_total'), '.2f', '')}kg (min: {safe_format(aloc.get('peso_minimo'), '.2f', '')}kg, cap: {safe_format(aloc.get('capacidade_peso'), '.2f', '')}kg)")
            print(f"    Volume: {safe_format(aloc.get('volume_total'), '.2f', '')}m³ (cap: {safe_format(aloc.get('capacidade_volume'), '.2f', '')}m³)")
            print(f"    Utilização: {safe_format(aloc.get('taxa_utilizacao_peso'), '.1f', '')}% (peso), {safe_format(aloc.get('taxa_utilizacao_volume'), '.1f', '')}% (volume)")
            print(f"    Custo: {safe_format(aloc.get('custo_veiculo'), '.2f', 'R$')}")
            if aloc.get('frete_morto', {}).get("valor", 0) > 0:
                print(f"    Frete morto: {safe_format(aloc['frete_morto']['valor'], '.2f', 'R$')}")

        
        print(f"\nCARGAS NÃO ALOCADAS:")
        print(f"  Quantidade: {resultados.get('ums_nao_alocadas', 'N/A')} de {resultados.get('ums_alocadas', 0) + resultados.get('ums_nao_alocadas', 0)}")
        print(f"  Peso total: {safe_format(resultados.get('peso_nao_alocado'), '.2f', '')}kg")
        print(f"  Volume total: {safe_format(resultados.get('volume_nao_alocado'), '.2f', '')}m³")

        
        print(f"\nANÁLISE DE DECISÕES:")
        if resultados.get('frete_morto_total', 0) > 0:
            print("Há fretes mortos - veículos operando abaixo da capacidade mínima")
        else:
            print("  Nenhum frete morto - todos veículos atendem carga mínima")

        if resultados.get('ums_nao_alocadas', 0) > 0:
            print(f"{resultados.get('ums_nao_alocadas', 0)} UMs não alocadas - verifique se é por restrições ou decisão ótima")
        else:
            print("  Todas UMs alocadas")

        if resultados.get('veiculos_inativos', 0) > 0:
            print(f"{resultados.get('veiculos_inativos', 0)} veículos inativos - verifique se é esperado")

    print(f"\n{'='*80}")


def exportar_resultados_csv(resultados_lista, instancias_originais, nome_instancia):
    
    caminho_saida = os.path.join(os.path.dirname(__file__), INSTANCIAS, 'Resultados - Modelo Exato')

    
    if (not resultados_lista or not instancias_originais or
        len(resultados_lista) != len(instancias_originais)):
        raise ValueError("Listas de resultados e instâncias originais não correspondem")

    os.makedirs(caminho_saida, exist_ok=True)

    
    
    
    idx_atual = len(resultados_lista) - 1
    resultados = resultados_lista[idx_atual]
    instancia = instancias_originais[idx_atual]

    if not resultados or not instancia:
        print("Resultado/instância inválido(s).")
        return

    if 'ums' not in instancia:
        print(f"Estrutura inválida na instância {resultados.get('tipo_instancia', 'desconhecida')}")
        return

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    nome_arquivo = f"resultados_{nome_instancia}_{timestamp}.csv"
    caminho_completo = os.path.join(caminho_saida, nome_arquivo)

    with open(caminho_completo, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file, delimiter=';')

        writer.writerow(["RELATÓRIO DE OTIMIZAÇÃO"])
        writer.writerow(["Gerado em:", datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
        writer.writerow([])

        
        writer.writerow([f"INSTÂNCIA: {resultados.get('tipo_instancia', 'N/A')}"])
        writer.writerow([])

        writer.writerow(["Status", "Ótimo" if resultados.get('status') == GRB.OPTIMAL else "Timeout"])
        writer.writerow(["Tempo Total (s)", f"{resultados.get('tempo_execucao', 0):.2f}"])
        writer.writerow(["Tempo para Ótimo (s)", f"{resultados.get('tempo_para_otimo', 0):.2f}" if resultados.get('tempo_para_otimo') is not None else "N/A"])
        writer.writerow(["Melhor Solução", f"{resultados.get('melhor_solucao', 0):.2f}" if resultados.get('melhor_solucao') is not None else "N/A"])
        writer.writerow(["Solução Relaxada", f"{resultados.get('solucao_relaxada', 0):.2f}" if resultados.get('solucao_relaxada') is not None else "N/A"])
        writer.writerow(["GAP (%)", f"{resultados.get('gap_otimizacao', 0):.2f}" if resultados.get('gap_otimizacao') is not None else "N/A"])
        writer.writerow(["Relaxação Linear", f"{resultados.get('relaxacao_linear', 0):.2f}" if resultados.get('relaxacao_linear') is not None else "N/A"])
        writer.writerow(["GAP Relaxação (%)", f"{resultados.get('gap_relaxacao', 0):.2f}" if resultados.get('gap_relaxacao') is not None else "N/A"])
        writer.writerow(["Custo Total", f"{resultados.get('custo_total', 0):.2f}" if resultados.get('custo_total') is not None else "N/A"])
        writer.writerow(["Custo Atendimento", f"{resultados.get('custo_alocacao', 0):.2f}"])
        writer.writerow(["Custo Transporte", f"{resultados.get('custo_transporte', 0):.2f}"])
        writer.writerow(["Frete Morto", f"{resultados.get('frete_morto_total', 0):.2f}"])
        writer.writerow(["Custo Não Alocação", f"{resultados.get('custo_nao_alocacao', 0):.2f}"])
        writer.writerow(["Peso Não Alocado", f"{resultados.get('peso_nao_alocado', 0):.2f}"])
        writer.writerow(["Volume Não Alocado", f"{resultados.get('volume_nao_alocado', 0):.2f}"])
        writer.writerow(["Veículos Ativos", resultados.get('veiculos_ativos', 0)])
        writer.writerow(["Veículos Inativos", resultados.get('veiculos_inativos', 0)])
        writer.writerow(["UMs Alocadas", resultados.get('ums_alocadas', 0)])
        writer.writerow(["UMs Não Alocadas", resultados.get('ums_nao_alocadas', 0)])
        writer.writerow([])

        
        writer.writerow(["VEÍCULOS ATIVOS"])
        writer.writerow([
            "ID", "Tipo", "Destino", "Cargas", "Peso Total (kg)", "Capacidade (kg)",
            "Utilização (%)", "Volume Total", "Capacidade (m3)", "Utilização (%)", "Frete Morto (R$)"
        ])

        for aloc in resultados.get('alocacoes', []):
            
            beta_valor = next(
                (p["beta"] for p in instancia.get('parametros', [])
                 if p.get("descricao", "").lower() == "beta"),
                1.0
            )

            capacidade_utilizada = aloc.get('capacidade_peso', 0)
            carga_real = aloc.get('peso_total', 0)

            capacidade_ociosa = max(0, capacidade_utilizada - carga_real)
            frete_morto_veiculo = capacidade_ociosa * beta_valor

            writer.writerow([
                aloc.get('veiculo_id', ''),
                aloc.get('veiculo_tipo', ''),
                aloc.get('destino', ''),
                ";".join(map(str, aloc.get('cargas', []))),
                f"{aloc.get('peso_total', 0):.1f}",
                f"{aloc.get('capacidade_peso', 0):.1f}",
                f"{aloc.get('taxa_utilizacao_peso', 0):.1f}",
                f"{aloc.get('volume_total', 0):.1f}",
                f"{aloc.get('capacidade_volume', 0):.1f}",
                f"{aloc.get('taxa_utilizacao_volume', 0):.1f}",
                f"{frete_morto_veiculo:.2f}"
            ])
        writer.writerow([])

        
        writer.writerow(["UNIDADES METÁLICAS NÃO ALOCADAS"])
        writer.writerow(["ID", "Tipo", "Peso (kg)", "Volume (m³)", "Destino", "Compatibilidade", "Motivo"])

        
        alocados_ids = set()
        for aloc in resultados.get('alocacoes', []):
            alocados_ids.update(aloc.get('cargas', []))

        for um in instancia.get('ums', []):
            if um.get('id') not in alocados_ids:
                motivo = "Decisão ótima"
                if not any(
                    v.get('tipo', '') in um.get('compatibilidade', '').split(',')
                    for v in instancia.get('veiculos', [])
                ):
                    motivo = "Incompatibilidade"

                writer.writerow([
                    um.get('id', ''),
                    um.get('tipo', ''),
                    um.get('peso', ''),
                    um.get('volume', ''),
                    um.get('destino', ''),
                    um.get('compatibilidade', ''),
                    motivo
                ])

        writer.writerow([])
        writer.writerow(["-" * 50])
        writer.writerow([])

    print(f"\nRelatório salvo em: {caminho_completo}")

    
    
    
    nome_arquivo_resumo = f"resumo_resultados_{nome_instancia}.csv"  
    caminho_completo_resumo = os.path.join(caminho_saida, nome_arquivo_resumo)

    arquivo_existe = os.path.exists(caminho_completo_resumo)

    with open(caminho_completo_resumo, mode='a', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file, delimiter=';')

        if not arquivo_existe:
            writer.writerow([
                "Instância", "Status", "Tempo para Ótimo (s)",
                "Solução Inteira", "Solução Relaxada", "GAP (%)",
                "Relaxação Linear", "GAP Relaxação (%)", "Custo Total",
                "Custo Atendimento", "Custo Transporte", "Frete Morto", "Custo Não Alocação",
                "Peso Não Alocado", "Volume Não Alocado", "Veículos Ativos", "Veículos Inativos",
                "UMs Alocadas", "UMs Não Alocadas"
            ])

        writer.writerow([
            resultados.get('tipo_instancia', 'N/A'),
            "Ótimo" if resultados.get('status') == GRB.OPTIMAL else "Timeout",
            f"{resultados.get('tempo_para_otimo', 0):.2f}" if resultados.get('tempo_para_otimo') is not None else "N/A",
            f"{resultados.get('melhor_solucao', 0):.2f}" if resultados.get('melhor_solucao') is not None else "N/A",
            f"{resultados.get('solucao_relaxada', 0):.2f}" if resultados.get('solucao_relaxada') is not None else "N/A",
            f"{resultados.get('gap_otimizacao', 0):.2f}" if resultados.get('gap_otimizacao') is not None else "N/A",
            f"{resultados.get('relaxacao_linear', 0):.2f}" if resultados.get('relaxacao_linear') is not None else "N/A",
            f"{resultados.get('gap_relaxacao', 0):.2f}" if resultados.get('gap_relaxacao') is not None else "N/A",
            f"{resultados.get('custo_total', 0):.2f}" if resultados.get('custo_total') is not None else "N/A",
            f"{resultados.get('custo_alocacao', 0):.2f}",
            f"{resultados.get('custo_transporte', 0):.2f}",
            f"{resultados.get('frete_morto_total', 0):.2f}",
            f"{resultados.get('custo_nao_alocacao', 0):.2f}",
            f"{resultados.get('peso_nao_alocado', 0):.2f}",
            f"{resultados.get('volume_nao_alocado', 0):.2f}",
            resultados.get('veiculos_ativos', 0),
            resultados.get('veiculos_inativos', 0),
            resultados.get('ums_alocadas', 0),
            resultados.get('ums_nao_alocadas', 0)
        ])


def executar_todas_instancias_geradas():
    
    PASTA_INSTANCIAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), INSTANCIAS)
    PASTA_RESULTADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), INSTANCIAS, 'Resultados - Modelo Exato')
    os.makedirs(PASTA_RESULTADOS, exist_ok=True)

    arquivos_instancias = [f for f in os.listdir(PASTA_INSTANCIAS) if f.endswith('.csv') and not f.startswith('00_')]

    if not arquivos_instancias:
        print("Nenhuma instância encontrada na pasta!")
        return

    print(f"Encontradas {len(arquivos_instancias)} instâncias para executar")

    resultados_totais = []
    instancias_originais = []

    for arquivo in arquivos_instancias:
        try:
            nome_instancia = arquivo.replace('.csv', '')
            print(f"\n{'='*80}")
            print(f"🚀 PROCESSANDO INSTÂNCIA: {nome_instancia}")
            print(f"{'='*80}")

            caminho_completo = os.path.join(PASTA_INSTANCIAS, arquivo)
            dados = carregar_dados(caminho_completo)
            instancia = {
                "veiculos": dados['veiculos'],
                "ums": dados['ums'],
                "parametros": dados['parametros'],
                "regioes": dados['regioes']
            }

            instancias_originais.append(instancia)
            resultados = executar_instancia_com_timeout(nome_instancia, instancia)

            if resultados:
                resultados_totais.append(resultados)
                imprimir_resultados_detalhados(resultados)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                nome_arquivo = f"resultados_consolidados_{timestamp}.csv"
                exportar_resultados_csv(resultados_totais, instancias_originais, nome_instancia)
                print(f"\nTodas instâncias processadas! Resultados em: {nome_arquivo}")
            else:
                print(f"Falha ao executar instância {nome_instancia}")

        except Exception as e:
            import traceback
            print(f"Erro crítico ao processar {arquivo}: {repr(e)}")
            traceback.print_exc()
            continue

if __name__ == "__main__":

    executar_todas_instancias_geradas()
