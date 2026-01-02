import pandas as pd
import os
import re


PASTA_SAIDA = os.path.join(os.path.dirname(__file__), 'Instancias_ORLibrary')
PASTA_ORLIB = os.path.join(os.path.dirname(__file__), 'ORLibrary')  



def criar_pasta(caminho):
    os.makedirs(caminho, exist_ok=True)

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
                        'comprimento': int(partes[0]),
                        'orientacao_comprimento': int(partes[1]),
                        'largura': int(partes[2]),
                        'orientacao_largura': int(partes[3]),
                        'altura': int(partes[4]),
                        'orientacao_altura': int(partes[5]),
                        'quantidade': int(partes[6]),
                        'peso': float(partes[7]),
                        'capacidade_carga_comprimento': float(partes[8]),
                        'capacidade_carga_largura': float(partes[9]),
                        'capacidade_carga_altura': float(partes[10])
                    }
                    caixas.append(caixa)
            
            problema = {
                'container': {'comprimento': l, 'largura': w, 'altura': h},
                'num_tipos': num_tipos,
                'volume_total': volume_total,
                'caixas': caixas
            }
            problemas.append(problema)
        
        i += 1
    
    return problemas

def gerar_instancia_orlibrary(problema, num_arquivo, num_problema):
    
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
    }])], ignore_index=True)
    
    
    capacidade_peso = sum(caixa['peso'] * caixa['quantidade'] for caixa in problema['caixas']) * 1.1  

    df = pd.concat([df, pd.DataFrame([{
        'tipo': 'veiculo',
        'id': 1,
        'descricao': 'Veiculo_ORLibrary',
        'capacidade_peso': round(capacidade_peso, 2),
        'capacidade_vol': problema['volume_total'] * 1.1,  
        'custo': '1000',
        'carga_minima': 0
    }])], ignore_index=True)
    
    
    um_id = 1
    for idx, caixa in enumerate(problema['caixas']):
        
        orientacoes = []
        if caixa['orientacao_comprimento'] == 1:
            orientacoes.append("L")
        if caixa['orientacao_largura'] == 1:
            orientacoes.append("W")
        if caixa['orientacao_altura'] == 1:
            orientacoes.append("H")
        
        compatibilidade = "ORLibrary"  
        
        
        orientacoes_str = ",".join(orientacoes) if orientacoes else "FIXA"
        restricao = f"{orientacoes_str}_L{caixa['capacidade_carga_comprimento']}_W{caixa['capacidade_carga_largura']}_H{caixa['capacidade_carga_altura']}"
        
        
        for qtd_idx in range(caixa['quantidade']):
            
            volume_m3 = (caixa['comprimento'] * caixa['largura'] * caixa['altura']) / 1000000
            
            df = pd.concat([df, pd.DataFrame([{
                'tipo': 'um',
                'id': um_id,
                'descricao': f"Caixa_{idx+1}",
                'peso': caixa['peso'],
                'volume': round(volume_m3, 4),
                'compatibilidade': compatibilidade,  
                'restricao': restricao,  
                'penalidade': 0.5,
                'Criterio Penalidade': 'Prioridade normal - dados ORLibrary',
                'destino': 'R1',
                'custo': '10.0'
            }])], ignore_index=True)
            
            um_id += 1
    
    return df

def processar_todos_arquivos_orlibrary():
    
    criar_pasta(PASTA_SAIDA)
    resumo_lista = []
    
    
    for num_arquivo in range(1, 8):
        nome_arquivo = f"wtpack{num_arquivo}.txt"
        caminho_arquivo = os.path.join(PASTA_ORLIB, nome_arquivo)
        
        if not os.path.exists(caminho_arquivo):
            print(f"Arquivo não encontrado: {caminho_arquivo}")
            continue
        
        print(f"Processando {nome_arquivo}...")
        
        try:
            problemas = ler_arquivo_wtpack(caminho_arquivo)
            print(f"   Encontrados {len(problemas)} problemas")
            
            for idx, problema in enumerate(problemas):
                nome_saida = f"orlib_wtpack{num_arquivo}_prob{idx+1:03d}"
                df = gerar_instancia_orlibrary(problema, num_arquivo, idx+1)
                
                
                caminho_saida = os.path.join(PASTA_SAIDA, f"{nome_saida}.csv")
                df.to_csv(caminho_saida, sep=';', decimal='.', index=False, encoding='utf-8-sig')
                
                
                num_ums = sum(caixa['quantidade'] for caixa in problema['caixas'])
                resumo_lista.append({
                    'Arquivo_Original': nome_arquivo,
                    'Problema': idx+1,
                    'Tipos_Caixas': problema['num_tipos'],
                    'UMs': num_ums,
                    'Container_Dims': f"{problema['container']['comprimento']}x{problema['container']['largura']}x{problema['container']['altura']}",
                    'Volume_Total': problema['volume_total'],
                    'Arquivo_CSV': f"{nome_saida}.csv"
                })
                
            print(f"✅ {nome_arquivo} processado: {len(problemas)} instâncias geradas")
            
        except Exception as e:
            print(f"Erro ao processar {nome_arquivo}: {e}")
    
    
    if resumo_lista:
        resumo = pd.DataFrame(resumo_lista)
        resumo.to_csv(os.path.join(PASTA_SAIDA, '00_RESUMO_ORLIBRARY.csv'), index=False)
        
        print(f"\nConversão finalizada!")
        print(f"Total de instâncias convertidas: {len(resumo_lista)}")
        print(f"Pasta de saída: {PASTA_SAIDA}")
        print(f"Relatório: {os.path.join(PASTA_SAIDA, '00_RESUMO_ORLIBRARY.csv')}")
    else:
        print("Nenhuma instância foi convertida.")


if __name__ == "__main__":
    
    criar_pasta(PASTA_ORLIB)
    
    print("=" * 60)
    print("CONVERSOR OR-Library wtpack* para CSV")
    print("=" * 60)
    print(f"Coloque os arquivos wtpack1.txt a wtpack7.txt em: {PASTA_ORLIB}")
    print("Processando...")
    
    processar_todos_arquivos_orlibrary()