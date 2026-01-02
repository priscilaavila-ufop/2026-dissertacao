import pandas as pd
import random
import os
import warnings
import csv

warnings.simplefilter(action='ignore', category=FutureWarning)


TAMANHO_GRID = 100
NUM_REGIOES = 4
PASTA_SAIDA = os.path.join(os.path.dirname(__file__), 'Instancias_PRINT')


CONFIGURACOES = [
    {'num_veiculos': 2, 'num_ums': 5}
]


NUM_VARIACOES = {
    2:10
}


VEICULOS_BASE = [
    {'tipo': 'Bi-trem Carga Seca', 'capacidade_peso': 57000, 'capacidade_vol': 90, 'custo_base': 1500},
    {'tipo': 'Bi-trem Especializado', 'capacidade_peso': 57000, 'capacidade_vol': 80, 'custo_base': 1800},
    {'tipo': 'Bi-truck', 'capacidade_peso': 33000, 'capacidade_vol': 50, 'custo_base': 1200},
    {'tipo': 'Carreta L', 'capacidade_peso': 33000, 'capacidade_vol': 70, 'custo_base': 1350},
    {'tipo': 'Carreta trucada (LS)', 'capacidade_peso': 45000, 'capacidade_vol': 85, 'custo_base': 1600},
    {'tipo': 'Rodotrem Carga seca', 'capacidade_peso': 74000, 'capacidade_vol': 110, 'custo_base': 2000},
    {'tipo': 'Rodotrem Especializado', 'capacidade_peso': 74000, 'capacidade_vol': 100, 'custo_base': 2200},
    {'tipo': 'Truck', 'capacidade_peso': 23000, 'capacidade_vol': 40, 'custo_base': 1000},
    {'tipo': 'Vanderléia', 'capacidade_peso': 41000, 'capacidade_vol': 75, 'custo_base': 1700}
]


TIPOS_UM = ['chapa', 'tira', 'perfil', 'tubo']



def criar_pasta(caminho):
    os.makedirs(caminho, exist_ok=True)

def definir_regioes(num_regioes):
    
    return [f"R{i}" for i in range(1, num_regioes+1)]

def formatar_lista_com_virgula(lista):
    
    return ",".join(f"{float(x):.1f}" if (float(x) % 1) != 0 else f"{int(x)}.0" for x in lista)

def determinar_penalidade_e_criterio(peso, volume, restricao):
    
    rand_val = random.random()
    
    
    if rand_val < 0.05:
        penalidade = round(random.uniform(5.0, 10.0), 2)
        criterio = "Estratégica - impacto operacional grave, peça única ou projeto com multa por atraso"
    
    
    elif rand_val < 0.15:
        penalidade = round(random.uniform(2.0, 5.0), 2)
        criterio = "Cliente importante - risco de multas ou perda de contrato"
    
    
    elif peso > 4000 or volume > 100:
        penalidade = round(random.uniform(2.0, 5.0), 2)
        criterio = "Carga grande - ocupa muito espaço e pode exigir veículo extra"
    
    
    
    elif peso >= 1200:
        penalidade = round(random.uniform(0.8, 1.5), 2)
        criterio = "Prioridade normal - carga média ou cliente regular"
    else:
        penalidade = round(random.uniform(0.3, 0.5), 2)
        criterio = "Carga comum - baixa prioridade"
    
    return penalidade, criterio

def determinar_compatibilidade_um(tipo_um, peso, volume):
    
    nivel = definir_nivel_compatibilidade(tipo_um, peso, volume)
    
    
    veiculos_compatíveis = gerar_compatibilidade(tipo_um, peso, volume, nivel)
    
    return veiculos_compatíveis

def definir_nivel_compatibilidade(tipo_um, peso, volume):
    
    
    if (peso > 6500 or 
        volume > 90 or 
        (tipo_um == 'tubo' and peso > 5000) or
        (tipo_um == 'chapa' and volume > 8.5)):
        return 1  
    
    
    elif (peso > 40000 or 
          volume > 80 or
          (tipo_um == 'perfil' and peso > 3500)):
        return random.randint(2, 3)
    
    
    elif (peso > 2000 or 
          volume > 60 or
          tipo_um in ['chapa', 'perfil']):
        return random.randint(3, 4)
    
    
    elif peso > 1000 or volume > 40:
        return random.randint(4, 5)
    
    
    else:
        return random.randint(5, 7)

def gerar_compatibilidade(tipo_um, peso, volume, nivel):
    
    veiculos_por_capacidade = {
        'MAXIMA_CAPACIDADE': ['Rodotrem Carga seca', 'Rodotrem Especializado', 'Bi-trem Carga Seca', 'Bi-trem Especializado'],
        'ALTA_CAPACIDADE': ['Carreta trucada (LS)', 'Vanderléia', 'Bi-trem Carga Seca'],
        'MEDIA_CAPACIDADE': ['Carreta L', 'Bi-truck', 'Vanderléia'],
        'BAIXA_CAPACIDADE': ['Truck', 'Bi-truck', 'Carreta L']
    }
    
    if nivel == 1:  
        
        if peso > 6500:
            return "Rodotrem Carga seca"  
        elif volume > 95:
            return "Rodotrem Especializado"  
        elif tipo_um == 'tubo' and peso > 5000:
            return "Bi-trem Especializado"  
        elif tipo_um == 'chapa' and volume > 8.5:
            return "Carreta trucada (LS)"  
        else:
            
            return random.choice(veiculos_por_capacidade['MAXIMA_CAPACIDADE'])
    
    elif nivel == 2:  
        if peso > 4500:
            compatíveis = random.sample(veiculos_por_capacidade['MAXIMA_CAPACIDADE'], 2)
        elif volume > 85:
            compatíveis = ['Rodotrem Carga seca', 'Bi-trem Carga Seca']
            if random.random() < 0.5:
                compatíveis.append('Rodotrem Especializado')
        else:
            compatíveis = random.sample(veiculos_por_capacidade['ALTA_CAPACIDADE'], 2)
        return ",".join(compatíveis)
    
    elif nivel == 3:  
        compatíveis = random.sample(veiculos_por_capacidade['ALTA_CAPACIDADE'] + 
                                  veiculos_por_capacidade['MEDIA_CAPACIDADE'], 
                                  random.randint(3, 4))
        return ",".join(compatíveis)
    
    elif nivel == 4:  
        compatíveis = random.sample(veiculos_por_capacidade['MEDIA_CAPACIDADE'] + 
                                  veiculos_por_capacidade['ALTA_CAPACIDADE'], 
                                  random.randint(4, 5))
        return ",".join(compatíveis)
    
    else:  
        todos = (veiculos_por_capacidade['BAIXA_CAPACIDADE'] + 
                veiculos_por_capacidade['MEDIA_CAPACIDADE'] + 
                veiculos_por_capacidade['ALTA_CAPACIDADE'])
        return ",".join(random.sample(todos, nivel))

def gerar_frota(num_veiculos, regioes):
    
    frota = []
    vid = 1
    
    
    for r_idx, r in enumerate(regioes):
        if vid > num_veiculos:
            break
        base = random.choice(VEICULOS_BASE)
        
        custos = []
        for _ in regioes:
            var = random.uniform(0.85, 1.25)
            custos.append(round(base['custo_base'] * var, 2))
        custo_str = formatar_lista_com_virgula(custos)
        frota.append({
            'id': vid,
            'tipo': base['tipo'],
            'descricao': base['tipo'],
            'capacidade_peso': base['capacidade_peso'],
            'capacidade_vol': base['capacidade_vol'],
            'custo': custo_str,
            'carga_minima': max(1, int(base['capacidade_peso'] * 0.3))
        })
        vid += 1

    
    while vid <= num_veiculos:
        base = random.choice(VEICULOS_BASE)
        custos = []
        for _ in regioes:
            var = random.uniform(0.85, 1.25)
            custos.append(round(base['custo_base'] * var, 2))
        custo_str = formatar_lista_com_virgula(custos)
        frota.append({
            'id': vid,
            'tipo': base['tipo'],
            'descricao': base['tipo'],
            'capacidade_peso': base['capacidade_peso'],
            'capacidade_vol': base['capacidade_vol'],
            'custo': custo_str,
            'carga_minima': max(1, int(base['capacidade_peso'] * 0.3))
        })
        vid += 1

    return frota



def determinar_tipo_um_por_caracteristicas(peso, volume, idx):
    
    if volume > 5.0:
        return 'chapa'  
    elif peso > 5000:
        return 'viga'   
    elif random.random() > 0.7:  
        return 'barra'  
    else:
        
        return random.choice(TIPOS_UM)

def determinar_restricao_por_caracteristicas(peso, volume, comprimento, largura, altura):
    
    if peso > 3000:
        return 'Pesado'
    elif volume > 3.0:
        return 'Não empilhar'
    elif min(comprimento, largura, altura) < 20:
        return 'Frágil'
    else:
        return ''

def gerar_dimensoes_um(tipo_um):
    
    if tipo_um == 'chapa':
        comprimento = random.randint(200, 600)
        largura = random.randint(100, 300)
        altura = random.randint(5, 30)
    elif tipo_um == 'tira':
        comprimento = random.randint(150, 400)
        largura = random.randint(30, 80)
        altura = random.randint(10, 50)
    elif tipo_um == 'perfil':
        comprimento = random.randint(300, 800)
        largura = random.randint(40, 100)
        altura = random.randint(40, 100)
    elif tipo_um == 'tubo':
        comprimento = random.randint(200, 500)
        largura = random.randint(50, 150)
        altura = random.randint(50, 150)
    else:  
        comprimento = random.randint(400, 1000)
        largura = random.randint(30, 80)
        altura = random.randint(30, 80)
    
    return comprimento, largura, altura



def gerar_instancia(num_veiculos, num_ums, num_regioes, nome_saida):
    
    regioes = definir_regioes(num_regioes)
    regioes_ord = regioes[:]  

    
    colunas = [
        'tipo', 'id', 'descricao', 'valor', 'peso', 'volume', 'destino',
        'x', 'y', 'compatibilidade', 'restricao', 'capacidade_peso',
        'capacidade_vol', 'custo', 'carga_minima', 'penalidade', 'Criterio Penalidade'
    ]
    df = pd.DataFrame(columns=colunas)

    
    df = pd.concat([df, pd.DataFrame([{
        'tipo': 'parametro',
        'id': 1,
        'descricao': 'Beta',
        'valor': 0.1
    }])], ignore_index=True, sort=False)

    
    frota = gerar_frota(num_veiculos, regioes_ord)

    
    tipos_ord = []
    for v in frota:
        if v['tipo'] not in tipos_ord:
            tipos_ord.append(v['tipo'])

    
    for v in frota:
        df = pd.concat([df, pd.DataFrame([{
            'tipo': 'veiculo',
            'id': v['id'],
            'descricao': f"Veiculo_{v['descricao']}",
            'capacidade_peso': v['capacidade_peso'],
            'capacidade_vol': v['capacidade_vol'],
            'custo': f'"{v["custo"]}"',   
            'carga_minima': v['carga_minima']
        }])], ignore_index=True, sort=False)

    
    um_id = 1
    for idx in range(num_ums):
        
        peso = random.randint(250, 7000)
        
        
        
        tipo_um = determinar_tipo_um_por_caracteristicas(peso, 0, idx)  
        comprimento, largura, altura = gerar_dimensoes_um(tipo_um)
        volume_m3 = (comprimento * largura * altura) / 1000000
        volume = round(volume_m3, 4)
        
        
        restricao_base = determinar_restricao_por_caracteristicas(peso, volume_m3, comprimento, largura, altura)
        
        
        penalidade, criterio = determinar_penalidade_e_criterio(peso, volume_m3, restricao_base)
        
        
        orientacoes = []
        if random.random() > 0.3:  
            orientacoes.append("L")
        if random.random() > 0.3:  
            orientacoes.append("W")
        if random.random() > 0.5:  
            orientacoes.append("H")
        
        
        
        compatibilidade = determinar_compatibilidade_um(tipo_um, peso, volume)
        
        
        orientacoes_str = ",".join(orientacoes) if orientacoes else "FIXA"
        restricao_completa = f"{orientacoes_str}_L{random.uniform(0.5, 2.0):.1f}_W{random.uniform(0.5, 2.0):.1f}_H{random.uniform(0.5, 2.0):.1f}"
        
        
        min_por_regiao = max(1, num_ums // len(regioes_ord))
        
        if idx < len(regioes_ord) * min_por_regiao:
            
            destino = regioes_ord[(idx // min_por_regiao) % len(regioes_ord)]
        else:
            
            destino = random.choice(regioes_ord)

        
        custos_por_tipo = []
        for tipo in tipos_ord:
            base_val = 5.0 + random.uniform(0.0, 12.0)
            custos_por_tipo.append(round(base_val, 2))
        custo_str_um = formatar_lista_com_virgula(custos_por_tipo)

        df = pd.concat([df, pd.DataFrame([{
            'tipo': 'um',
            'id': um_id,
            'descricao': tipo_um,
            'peso': peso,
            'volume': volume,
            'compatibilidade': compatibilidade,
            'restricao': restricao_completa,
            'penalidade': penalidade,
            'Criterio Penalidade': criterio,
            'destino': destino,
            'custo': f'"{custo_str_um}"'
        }])], ignore_index=True, sort=False)

        um_id += 1

    
    criar_pasta(PASTA_SAIDA)
    caminho = os.path.join(PASTA_SAIDA, f"{nome_saida}.csv")
    
    df.to_csv(caminho, sep=';', decimal='.', index=False, encoding='utf-8-sig', quoting=csv.QUOTE_NONE)
    print(f"Instância gerada: {caminho}  (veículos={num_veiculos}, ums={num_ums}, regioes={num_regioes})")

    
    return {'Veículos': num_veiculos, 'Clientes': 0, 'UMs': num_ums, 'Arquivo': f"{nome_saida}.csv"}

def gerar_todas_instancias():
    criar_pasta(PASTA_SAIDA)
    resumo_lista = []

    for cfg in CONFIGURACOES:
        nv = cfg['num_veiculos']
        num_vari = NUM_VARIACOES.get(nv, 1)
        for v in range(1, num_vari + 1):
            nome_base = f"{nv}v_{cfg['num_ums']}c_var{v}"
            info = gerar_instancia(nv, cfg['num_ums'], NUM_REGIOES, nome_base)
            resumo_lista.append(info)

    
    resumo = pd.DataFrame(resumo_lista)
    resumo.to_csv(os.path.join(PASTA_SAIDA, '00_RESUMO_COMPLETO.csv'), index=False)

    
    resumo_consolidado = resumo.groupby(['Veículos', 'UMs']).size().reset_index()
    resumo_consolidado.columns = ['Veículos', 'UMs', 'Qtd Instâncias']
    resumo_consolidado.to_csv(os.path.join(PASTA_SAIDA, '00_RESUMO.csv'), index=False)

    print("\nGeração finalizada. Relatórios:")
    print(f" - {os.path.join(PASTA_SAIDA, '00_RESUMO_COMPLETO.csv')}")
    print(f" - {os.path.join(PASTA_SAIDA, '00_RESUMO.csv')}")


if __name__ == "__main__":
    gerar_todas_instancias()