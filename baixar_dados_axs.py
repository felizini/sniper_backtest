#!/usr/bin/env python3
"""
Script para baixar dados históricos da AXSUSDT e comparar simulações de Abril vs Maio-Junho 2026
"""
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

def baixar_dados(symbol='AXS/USDT', timeframe='5m', start_date=None, end_date=None):
    """Baixa dados históricos da Binance"""
    exchange = ccxt.binance()
    
    if start_date is None:
        start_date = datetime(2026, 4, 1)
    if end_date is None:
        end_date = datetime(2026, 6, 12)
    
    print(f"Baixando dados de {symbol}...")
    print(f"Período: {start_date} a {end_date}")
    
    all_ohlcv = []
    current_time = int(start_date.timestamp() * 1000)
    end_time = int(end_date.timestamp() * 1000)
    
    while current_time < end_time:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_time, limit=1000)
            if not ohlcv:
                break
            
            all_ohlcv.extend(ohlcv)
            current_time = ohlcv[-1][0] + 1
            print(f"Progresso: {len(all_ohlcv)} candles baixados...")
            time.sleep(0.1)  # Rate limiting
            
        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(1)
    
    if not all_ohlcv:
        raise Exception("Nenhum dado baixado!")
    
    # Criar DataFrame
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Filtrar período exato
    df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
    
    # Adicionar coluna open_time_brasilia
    df['open_time_brasilia'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('America/Sao_Paulo').astype(str)
    
    # Salvar CSVs separados por mês
    abril = df[df['timestamp'].dt.month == 4].copy()
    maio_junho = df[df['timestamp'].dt.month >= 5].copy()
    
    if len(abril) > 0:
        arquivo_abril = 'AXSUSDT_2026-04-01_2026-04-30_5m.csv'
        abril.to_csv(arquivo_abril, index=False)
        print(f"\nDados de Abril salvos em {arquivo_abril} ({len(abril)} candles)")
    
    if len(maio_junho) > 0:
        arquivo_maio = 'AXSUSDT_2026-05-11_2026-06-12_5m.csv'
        maio_junho.to_csv(arquivo_maio, index=False)
        print(f"Dados de Maio-Junho salvos em {arquivo_maio} ({len(maio_junho)} candles)")
    
    # Salvar completo também
    arquivo_completo = 'AXSUSDT_2026-04-01_2026-06-12_5m.csv'
    df.to_csv(arquivo_completo, index=False)
    print(f"Dados completos salvos em {arquivo_completo} ({len(df)} candles)")
    
    return df, abril, maio_junho

if __name__ == '__main__':
    df, abril, maio_junho = baixar_dados()
    print("\n=== Resumo ===")
    print(f"Total: {len(df)} candles")
    print(f"Abril: {len(abril)} candles")
    print(f"Maio-Junho: {len(maio_junho)} candles")
