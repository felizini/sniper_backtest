#!/usr/bin/env python3
"""Análise detalhada do dia 25/04 para entender por que V16 não capturou"""

import pandas as pd
from datetime import datetime

# Carregar dados
df = pd.read_csv('AXSUSDT_2026-04-01_2026-04-30_5m.csv')
df['timestamp'] = pd.to_datetime(df['open_time_brasilia'])
df.set_index('timestamp', inplace=True)

# Calcular indicadores
df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
df['volume_ma'] = df['volume'].rolling(10).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma']

# Breakout level (máxima 5 candles)
df['breakout_level'] = df['high'].rolling(5).max().shift(1)

# ATR percentile
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df['atr_pct'] = df['atr'] / df['close'] * 100
df['atr_percentile'] = df['atr_pct'].rolling(20).apply(
    lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) * 100 if x.max() != x.min() else 50
)

# RSI
delta = df['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Filtrar dia 25
dia25 = df[df.index.date == datetime(2026, 4, 25).date()]

print('='*70)
print('DIA 25/04 - ANÁLISE DETALHADA DOS FILTROS V16')
print('='*70)

print(f'\nTotal candles: {len(dia25)}')
print(f'Volume total: {dia25["volume"].sum():,.0f}')

print('\n=== PRIMEIROS 20 CANDLES (00:00-01:40) ===')
for idx, row in dia25.head(20).iterrows():
    atr_pctl = row['atr_percentile']
    vol_ratio = row['volume_ratio']
    rsi = row['rsi']
    breakout = row['breakout_level']
    ema200 = row['ema200']
    
    # Verificar filtros
    f_horario = idx.hour >= 0 and idx.hour < 12
    f_ema200 = row['close'] > ema200
    f_compressao = atr_pctl <= 25
    f_volume = vol_ratio >= 3.0
    f_rsi = rsi >= 60
    f_breakout = row['close'] > breakout
    
    todos_ok = all([f_horario, f_ema200, f_compressao, f_volume, f_rsi, f_breakout])
    
    status = "✅ ENTRADA" if todos_ok else ""
    
    print(f'{idx} | Close: {row["close"]:.3f} | Vol: {vol_ratio:.1f}x | RSI: {rsi:.0f} | ATR%: {atr_pctl:.0f} | Breakout: {breakout:.3f} {status}')

print('\n=== VERIFICAÇÃO DOS FILTROS POR HORÁRIO ===')
for hour in range(0, 12):
    hora_candles = dia25[dia25.index.hour == hour]
    if len(hora_candles) == 0:
        continue
    
    for idx, row in hora_candles.iterrows():
        atr_pctl = row['atr_percentile']
        vol_ratio = row['volume_ratio']
        rsi = row['rsi']
        breakout = row['breakout_level']
        ema200 = row['ema200']
        
        filtros = {
            'Horário': idx.hour >= 0 and idx.hour < 12,
            'EMA200': row['close'] > ema200,
            'Compressão': atr_pctl <= 25,
            'Volume': vol_ratio >= 3.0,
            'RSI': rsi >= 60,
            'Breakout': row['close'] > breakout
        }
        
        falhas = [k for k, v in filtros.items() if not v]
        
        if len(falhas) <= 2:  # Mostrar apenas candles próximos de entrar
            print(f'{idx} | Close: {row["close"]:.3f}')
            for k, v in filtros.items():
                status = "✅" if v else "❌"
                print(f'   {status} {k}: {v}')
            print()
