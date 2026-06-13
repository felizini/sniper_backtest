#!/usr/bin/env python3
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
pd.set_option('display.max_columns', None)

# Carregar dados
df = pd.read_csv('AXSUSDT_2026-05-11_2026-06-12_5m.csv')
df['timestamp'] = pd.to_datetime(df['open_time_brasilia'])
print(f"Dados: {len(df)} candles, {df['timestamp'].min()} a {df['timestamp'].max()}")

# Estatisticas basicas
print("\n=== ANALISE ESTATISTICA MAIO-JUNHO 2026 ===")
variacao = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
print(f"Variacao total: {variacao:+.2f}%")
print(f"Preco: {df['close'].iloc[0]:.4f} -> {df['close'].iloc[-1]:.4f}")

# ATR
high_low = df['high'] - df['low']
high_close = np.abs(df['high'] - df['close'].shift())
low_close = np.abs(df['low'] - df['close'].shift())
true_range = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1)
atr = true_range.rolling(14).mean()
print(f"ATR medio: {atr.mean():.6f} ({atr.mean()/df['close'].mean()*100:.3f}%)")

# EMAs
df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
pct_bearish = (df['close'] < df['EMA200']).sum() / len(df) * 100
print(f"% Bearish (abaixo EMA200): {pct_bearish:.1f}%")

# RSI
delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rsi = 100 - 100/(1 + gain/loss)
print(f"RSI medio: {rsi.mean():.2f}")

# Backtest simplificado
def backtest(df, sl_mult, trail_dist, trail_limiar, adx_min, bias='BEARISH'):
    capital = 10000
    trades = []
    pos = False
    entry = 0
    qty = 0
    sl = 0
    trailing = False
    best = 0
    trail_val = 0
    
    # Indicadores
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - 100/(1 + gain/loss)
    
    tr = np.max(pd.concat([df['high']-df['low'], 
                           np.abs(df['high']-df['close'].shift()),
                           np.abs(df['low']-df['close'].shift())], axis=1), axis=1)
    df['ATR'] = tr.rolling(14).mean()
    
    # ADX simplificado
    periodo = 14
    plus_dm = df['high'].diff().clip(lower=0)
    minus_dm = (-df['low'].diff()).clip(lower=0)
    tr_roll = df['ATR'] * periodo
    plus_di = 100 * plus_dm.rolling(periodo).mean() / tr_roll
    minus_di = 100 * minus_dm.rolling(periodo).mean() / tr_roll
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    df['ADX'] = dx.rolling(periodo).mean()
    
    df.dropna(inplace=True)
    
    for i in range(200, len(df)):
        row = df.iloc[i]
        
        if pos:
            close = row['close']
            atr_val = max(row['ATR'], 0.001)
            
            if close > best:
                best = close
            
            # Ativa trailing
            if best >= entry + trail_limiar * atr_val:
                trailing = True
                new_trail = best - trail_dist * atr_val
                if new_trail > trail_val:
                    trail_val = new_trail
            
            # Saiu?
            exit_price = None
            if not trailing and close <= sl:
                exit_price = sl
            elif trailing and close <= trail_val:
                exit_price = trail_val
            
            if exit_price:
                pnl = (exit_price - entry) * qty
                capital += pnl
                trades.append(pnl)
                pos = False
        
        if not pos:
            # Regime
            bullish = row['EMA9'] > row['EMA21'] and row['close'] > row['EMA200']
            bearish = row['EMA9'] < row['EMA21'] and row['close'] < row['EMA200']
            
            if row['ATR'] <= 0 or row['ADX'] < adx_min or row['RSI'] > 75:
                continue
            
            prev = df.iloc[i-1]
            
            # Sinal SHORT
            if bias == 'BEARISH' and bearish:
                cross_down = prev['EMA9'] >= prev['EMA21'] and row['EMA9'] < row['EMA21']
                pullback = row['high'] >= row['EMA9'] * 0.998 and row['close'] < row['EMA9']
                
                if cross_down or pullback:
                    entry = row['close']
                    atr_val = row['ATR']
                    sl = entry + sl_mult * atr_val
                    qty = int(capital * 0.01 / (sl - entry)) if sl > entry else 0
                    if qty > 0:
                        pos = True
                        best = entry
                        trailing = False
                        trail_val = sl
    
    if trades:
        retorno = sum(trades) / 10000 * 100
        win_rate = len([t for t in trades if t > 0]) / len(trades) * 100
        return {'retorno': retorno, 'win_rate': win_rate, 'trades': len(trades), 'pnl': sum(trades)}
    return {'retorno': 0, 'win_rate': 0, 'trades': 0, 'pnl': 0}

# Grid search
print("\n=== OTIMIZACAO DE PARAMETROS ===")
configs = [
    (1.3, 1.8, 0.8, 18), (1.4, 1.8, 0.8, 18), (1.5, 1.8, 0.8, 18),
    (1.5, 2.0, 1.0, 20), (1.5, 2.2, 1.0, 20), (1.5, 2.5, 1.0, 20),
    (1.6, 2.0, 1.0, 20), (1.4, 2.0, 0.8, 18), (1.5, 1.5, 1.0, 20),
    (1.5, 3.0, 1.0, 20), (1.2, 2.0, 1.0, 20), (1.8, 2.0, 1.0, 20),
]

resultados = []
for sl, td, tl, adx in configs:
    res = backtest(df.copy(), sl, td, tl, adx, 'BEARISH')
    res['params'] = (sl, td, tl, adx)
    resultados.append(res)
    print(f"SL={sl}x Trail={td}x Limiar={tl} ADX>{adx}: Trades={res['trades']}, WinRate={res['win_rate']:.1f}%, Retorno={res['retorno']:.2f}%")

# Top configs
resultados.sort(key=lambda x: x['retorno'], reverse=True)
print("\n=== TOP 5 CONFIGURACOES ===")
for i, r in enumerate(resultados[:5]):
    p = r['params']
    print(f"#{i+1}: SL={p[0]}x, Trail={p[1]}x, Limiar={p[2]}, ADX>{p[3]} => Retorno={r['retorno']:.2f}%, Trades={r['trades']}, WinRate={r['win_rate']:.1f}%")

melhor = resultados[0]
print(f"\n=== MELHOR CONFIGURACAO ===")
print(f"SL={melhor['params'][0]}x ATR, Trailing={melhor['params'][1]}x ATR, Limiar={melhor['params'][2]}x, ADX>{melhor['params'][3]}")
print(f"Retorno: {melhor['retorno']:.2f}%, Win Rate: {melhor['win_rate']:.1f}%, Trades: {melhor['trades']}")

# Salvar relatorio
relatorio = f"""# ANALISE ESTATISTICA E OTIMIZACAO - MAIO/JUNHO 2026

## DADOS GERAIS
- Periodo: 11/05/2026 - 12/06/2026
- Candles: {len(df)}
- Variacao: {variacao:+.2f}%
- ATR medio: {atr.mean():.6f} ({atr.mean()/df['close'].mean()*100:.3f}%)
- % Bearish: {pct_bearish:.1f}%

## MELHORES PARAMETROS ENCONTRADOS
- Stop Loss: {melhor['params'][0]}x ATR
- Trailing Stop: {melhor['params'][1]}x ATR
- Limiar Trailing: {melhor['params'][2]}x ATR
- ADX minimo: {melhor['params'][3]}
- Bias: BEARISH

## RESULTADOS
- Retorno: {melhor['retorno']:.2f}%
- Win Rate: {melhor['win_rate']:.1f}%
- Total Trades: {melhor['trades']}
- PnL Total: R$ {melhor['pnl']:.2f}

## RECOMENDACOES PARA V17
1. Mudar bias para BEARISH (mercado em queda de {variacao:.2f}%)
2. Reduzir trailing para {melhor['params'][1]}x ATR
3. Antecipar ativacao para {melhor['params'][2]}x ATR
4. Usar ADX > {melhor['params'][3]} como filtro
"""

with open('ANALISE_MAIO2026.md', 'w') as f:
    f.write(relatorio)
print("\nRelatorio salvo em ANALISE_MAIO2026.md")
