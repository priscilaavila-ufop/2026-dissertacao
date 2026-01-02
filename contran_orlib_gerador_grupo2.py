import math
import pandas as pd
import random
import os
import warnings
import csv
import re

warnings.simplefilter(action='ignore', category=FutureWarning)


TAMANHO_GRID = 100
NUM_REGIOES = 4
FATOR_PESO = 10
FATOR_VOLUME = 30
FATOR_LINEAR = FATOR_VOLUME ** (1.0/3.0)   
PASTA_SAIDA = os.path.join(os.path.dirname(__file__), 'Instancias_20v_1p')
PASTA_ORLIB = os.path.join(os.path.dirname(__file__), 'wtpacks')


ARQUIVOS_ORLIB = ['wtpack1.txt', 'wtpack2.txt', 'wtpack3.txt', 'wtpack4.txt', 'wtpack5.txt', 'wtpack6.txt', 'wtpack7.txt']


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
        compatíveis = random.sample(
            veiculos_por_capacidade['ALTA_CAPACIDADE'] + veiculos_por_capacidade['MEDIA_CAPACIDADE'],
            random.randint(3, 4)
        )
        return ",".join(compatíveis)

    elif nivel == 4:  
        compatíveis = random.sample(
            veiculos_por_capacidade['ALTA_CAPACIDADE'] +
            veiculos_por_capacidade['MEDIA_CAPACIDADE'] +
            veiculos_por_capacidade['BAIXA_CAPACIDADE'],
            random.randint(4, 5)
        )
        return ",".join(compatíveis)

    else:  
        todos = (veiculos_por_capacidade['MAXIMA_CAPACIDADE'] +
                 veiculos_por_capacidade['ALTA_CAPACIDADE'] +
                 veiculos_por_capacidade['MEDIA_CAPACIDADE'] +
                 veiculos_por_capacidade['BAIXA_CAPACIDADE'])
        
        nivel_ajustado = min(int(nivel), len(set(todos)))
        return ",".join(random.sample(sorted(set(todos)), nivel_ajustado))
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

def ler_arquivo_wtpack(caminho_arquivo):
    
    problemas = []
    
    with open(caminho_arquivo, 'r') as f:
        linhas = f.readlines()
    
    i = 0
    while i < len(linhas):
        linha = linhas[i].strip()
        
        if re.match(r'^\d+\s+\d+\s+\d+$', linha):
            l, w, h = map(int, linha.split())
            
            i += 1
            if i >= len(linhas):
                break
                
            partes = linhas[i].strip().split()
            num_tipos = int(partes[0])
            volume_total = float(partes[1])
            
            caixas = []
            for j in range(num_tipos):
                i += 1
                if i >= len(linhas):
                    break
                partes = linhas[i].strip().split()
                if len(partes) >= 11:
                    caixa = {
                        'comprimento': int(partes[0]) * FATOR_LINEAR,
                        'orientacao_comprimento': int(partes[1]),
                        'largura': int(partes[2]) * FATOR_LINEAR,
                        'orientacao_largura': int(partes[3]),
                        'altura': int(partes[4]) * FATOR_LINEAR,
                        'orientacao_altura': int(partes[5]),
                        'quantidade': int(partes[6]),
                        'peso': float(partes[7]) * FATOR_PESO,
                        'capacidade_carga_comprimento': float(partes[8]),
                        'capacidade_carga_largura': float(partes[9]),
                        'capacidade_carga_altura': float(partes[10])
                    }
                    caixas.append(caixa)
            
            problema = {
                'container': {'comprimento': l, 'largura': w, 'altura': h},
                'num_tipos': num_tipos,
                'volume_total': (int(partes[0]) * FATOR_LINEAR) * (int(partes[2]) * FATOR_LINEAR) * (int(partes[4]) * FATOR_LINEAR) / 1000000,
                'caixas': caixas
            }
            problemas.append(problema)
        
        i += 1
    
    return problemas

def determinar_tipo_um_por_caixa(caixa, idx):
    
    volume_caixa = (caixa['comprimento'] * caixa['largura'] * caixa['altura']) / 1000000
    
    if volume_caixa > 5.0:
        return 'chapa'  
    elif caixa['peso'] > 5000:
        return 'viga'   
    elif caixa['comprimento'] > 150:
        return 'barra'  
    else:
        
        return random.choice(TIPOS_UM)

def determinar_restricao_por_caixa(caixa):
    
    volume_caixa = (caixa['comprimento'] * caixa['largura'] * caixa['altura']) / 1000000
    
    if caixa['peso'] > 3000:
        return 'Pesado'
    elif volume_caixa > 3.0:
        return 'Não empilhar'
    elif min(caixa['comprimento'], caixa['largura'], caixa['altura']) < 20:
        return 'Frágil'
    else:
        return ''



def gerar_instancia_orlibrary_contran(arquivo_orlib, num_problema, problema, num_veiculos, num_regioes, nome_saida):
    
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
    for idx, caixa in enumerate(problema['caixas']):
        
        volume_m3 = (caixa['comprimento'] * caixa['largura'] * caixa['altura']) / 1000000
        
        
        tipo_um = determinar_tipo_um_por_caixa(caixa, idx)
        
        
        restricao_um = determinar_restricao_por_caixa(caixa)
        
        
        penalidade, criterio = determinar_penalidade_e_criterio(caixa['peso'], volume_m3, restricao_um)
        
        
        orientacoes = []
        if caixa['orientacao_comprimento'] == 1:
            orientacoes.append("L")
        if caixa['orientacao_largura'] == 1:
            orientacoes.append("W")
        if caixa['orientacao_altura'] == 1:
            orientacoes.append("H")
        
        orientacoes_str = ",".join(orientacoes) if orientacoes else "FIXA"
        restricao_completa = f"{orientacoes_str}_L{caixa['capacidade_carga_comprimento']}_W{caixa['capacidade_carga_largura']}_H{caixa['capacidade_carga_altura']}"
                
        custos_por_tipo = []
        for tipo in tipos_ord:
            base_val = 5.0 + random.uniform(0.0, 12.0)
            custos_por_tipo.append(round(base_val, 2))
        custo_str_um = formatar_lista_com_virgula(custos_por_tipo)

        for qtd_idx in range(caixa['quantidade']):
            min_por_regiao = max(1, caixa['quantidade'] // len(regioes_ord))

            if qtd_idx < len(regioes_ord) * min_por_regiao:
                
                destino = regioes_ord[(qtd_idx // min_por_regiao) % len(regioes_ord)]
            else:
                
                destino = random.choice(regioes_ord)
            
            compatibilidade = determinar_compatibilidade_um(tipo_um, caixa['peso'], volume_m3)

            df = pd.concat([df, pd.DataFrame([{
                'tipo': 'um',
                'id': um_id,
                'descricao': tipo_um,  
                'peso': caixa['peso'],
                'volume': round(volume_m3, 4),
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
    print(f"Instância gerada: {caminho}  (veículos={num_veiculos}, ums={um_id-1}, regioes={num_regioes})")

    return {'Veículos': num_veiculos, 'Clientes': 0, 'UMs': um_id-1, 'Arquivo': f"{nome_saida}.csv"}

def gerar_todas_instancias_orlibrary_contran():
    
    criar_pasta(PASTA_SAIDA)
    criar_pasta(PASTA_ORLIB)
    resumo_lista = []

    
    NUM_VEICULOS = 20
    NUM_PROBLEMAS_POR_ARQUIVO = 1  

    for arquivo_orlib in ARQUIVOS_ORLIB:
        caminho_arquivo = os.path.join(PASTA_ORLIB, arquivo_orlib)
        
        if not os.path.exists(caminho_arquivo):
            print(f"⚠️ Arquivo não encontrado: {caminho_arquivo}")
            continue

        print(f"📖 Processando {arquivo_orlib}...")
        
        try:
            problemas = ler_arquivo_wtpack(caminho_arquivo)
            print(f"   Encontrados {len(problemas)} problemas")

            
            num_instancias = len(problemas) // NUM_PROBLEMAS_POR_ARQUIVO
            if len(problemas) % NUM_PROBLEMAS_POR_ARQUIVO != 0:
                num_instancias += 1

            print(f"   Gerando {num_instancias} instâncias com {NUM_PROBLEMAS_POR_ARQUIVO} problemas cada")
            
            for i in range(num_instancias):
                inicio = i * NUM_PROBLEMAS_POR_ARQUIVO
                fim = min((i + 1) * NUM_PROBLEMAS_POR_ARQUIVO, len(problemas))
                
                problemas_lote = problemas[inicio:fim]
                
                
                nome_base = f"orlib_contran_{arquivo_orlib.replace('.txt', '')}_lote{i+1:02d}"
                
                
                problema_combinado = {
                    'container': problemas_lote[0]['container'],  
                    'num_tipos': sum(p['num_tipos'] for p in problemas_lote),
                    'volume_total': sum(p['volume_total'] for p in problemas_lote),
                    'caixas': []
                }
                
                
                for problema in problemas_lote:
                    problema_combinado['caixas'].extend(problema['caixas'])
                
                info = gerar_instancia_orlibrary_contran(arquivo_orlib, i+1, problema_combinado, NUM_VEICULOS, NUM_REGIOES, nome_base)
                resumo_lista.append(info)
                
                print(f"✅ Lote {i+1} processado: 1 instância gerada com {info['UMs']} UMs")
            
        except Exception as e:
            print(f"❌ Erro ao processar {arquivo_orlib}: {e}")

    resumo = pd.DataFrame(resumo_lista)
    resumo.to_csv(os.path.join(PASTA_SAIDA, '00_RESUMO_COMPLETO.csv'), index=False)

    resumo_consolidado = resumo.groupby(['Veículos', 'Clientes', 'UMs']).size().reset_index()
    resumo_consolidado.columns = ['Veículos', 'Clientes', 'UMs', 'Qtd Instâncias']
    resumo_consolidado.to_csv(os.path.join(PASTA_SAIDA, '00_RESUMO.csv'), index=False)

    print("\n✅ Geração finalizada. Relatórios:")
    print(f" - {os.path.join(PASTA_SAIDA, '00_RESUMO_COMPLETO.csv')}")
    print(f" - {os.path.join(PASTA_SAIDA, '00_RESUMO.csv')}")


if __name__ == "__main__":
    gerar_todas_instancias_orlibrary_contran()
