#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNIPER PHOENIX V14 - ANTECIPAÇÃO DE PICOS DE ALTA (SQUEEZE DETECTION)
VERSÃO CORRIGIDA E SIMPLIFICADA

ESTRATÉGIA: Detectar compressão de volatilidade seguida de explosão direcional
para capturar movimentos parabólicos antecipadamente.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("SNIPER PHOENIX V14 - ANTECIPAÇÃO DE PICOS DE ALTA (SQUEEZE DETECTION)")
print("=" * 80)

# ============================================================================
# CARREGAMENTO DE DADOS
# ============================================================================

df = pd.read_csv('AXSUSDT_2026-04-01_2026-04-30_5m.csv', parse_dates=['open_time_brasilia'])
df.set_index('open_time_brasilia', inplace=True)
df.index = pd.to_datetime(df.index)

print(f"\n📊 PERÍODO: Abril 2026")
print(f"📈 Candles: {len(df)}")
print(f"📉 Variação do período: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.2f}%")

# ============================================================================
# INDICADORES TÉCNICOS
# ============================================================================

# EMAs para tendência
df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

# ATR para volatilidade
def calculate_atr(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    
    return atr

df['atr'] = calculate_atr(df, 14)
df['atr_pct'] = (df['atr'] / df['close']) * 100

# Bandas de Bollinger para squeeze detection
df['bb_middle'] = df['close'].rolling(window=20).mean()
df['bb_std'] = df['close'].rolling(window=20).std()
df['bb_upper'] = df['bb_middle'] + (2 * df['bb_std'])
df['bb_lower'] = df['bb_middle'] - (2 * df['bb_std'])
df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_middle']) * 100

# RSI para momentum
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

df['rsi'] = calculate_rsi(df['close'], 14)

# Volume
df['volume_ma'] = df['volume'].rolling(window=20).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma']

# Suporte e Resistência dinâmicos
df['highest_5'] = df['high'].rolling(window=5).max()
df['lowest_5'] = df['low'].rolling(window=5).min()

# ============================================================================
# SISTEMA DE PONTUAÇÃO DE PROBABILIDADE (SIMPLIFICADO)
# ============================================================================

df['score'] = 0

# Pontos por tendência (preço acima das EMAs)
df.loc[df['close'] > df['ema200'], 'score'] += 15
df.loc[(df['ema9'] > df['ema21']) & (df['ema21'] > df['ema50']), 'score'] += 20

# Pontos por RSI em zona ideal (45-65, espaço para subir)
df.loc[(df['rsi'] >= 45) & (df['rsi'] <= 65), 'score'] += 20

# Pontos por volume acima da média
df.loc[df['volume_ratio'] > 1.0, 'score'] += 15
df.loc[df['volume_ratio'] > 1.5, 'score'] += 10

# Pontos por ATR baixo (compressão de volatilidade)
df['atr_percentile'] = df['atr_pct'].rolling(window=50).apply(
    lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
)
df.loc[df['atr_percentile'] < 0.5, 'score'] += 20

# Pontos por Bandas de Bollinger estreitas
df['bb_percentile'] = df['bb_width'].rolling(window=50).apply(
    lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
)
df.loc[df['bb_percentile'] < 0.5, 'score'] += 20

# ============================================================================
# REGRAS DE ENTRADA (LONG APENAS - BIAS BULLISH)
# ============================================================================

# Condições principais - FILTROS MÍNIMOS
entry_condition = (
    (df['score'] >= 40) &  # Pontuação mínima
    (df['close'] > df['ema200']) &  # Tendência de longo prazo bullish
    (df['rsi'] < 70)  # Não sobrecomprado
)

# Gatilho de entrada: rompimento da máxima dos últimos 5 candles
entry_trigger = (
    entry_condition &
    (df['close'] > df['highest_5'].shift(1))
)

# Marcar entradas
df['entry_signal'] = entry_trigger.astype(int)

print(f"\n🔍 SINAIS GERADOS:")
print(f"   Entradas potenciais: {df['entry_signal'].sum()}")

# ============================================================================
# PARÂMETROS DE SAÍDA OTIMIZADOS
# ============================================================================

CAPITAL_INICIAL = 1000
RISCO_POR_TRADE = 0.02  # 2% do capital

# Parâmetros dinâmicos baseados em ATR
TP_MULT = 2.5  # Take Profit = 2.5x ATR
SL_MULT = 1.5  # Stop Loss = 1.5x ATR
TRAILING_MULT = 2.0  # Trailing Stop = 2x ATR
BREAK_EVEN_MULT = 1.5  # Ativa break-even após 1.5x ATR a favor

# ============================================================================
# EXECUÇÃO DO BACKTEST
# ============================================================================

trades = []
capital = CAPITAL_INICIAL
posicao = None
stop_loss = None
take_profit = None
trailing_stop = None
break_even_ativado = False

for i in range(200, len(df)):  # Warmup de 200 candles
    candle_atual = df.iloc[i]
    
    # Verificar entrada
    if df['entry_signal'].iloc[i] == 1 and posicao is None:
        # Calcular tamanho da posição
        preco_entrada = candle_atual['close']
        atr_atual = candle_atual['atr']
        
        stop_loss = preco_entrada * (1 - (SL_MULT * atr_atual / preco_entrada))
        take_profit = preco_entrada * (1 + (TP_MULT * atr_atual / preco_entrada))
        trailing_stop = stop_loss
        
        risco_unitario = preco_entrada - stop_loss
        tamanho_posicao = (capital * RISCO_POR_TRADE) / risco_unitario
        
        posicao = {
            'tipo': 'LONG',
            'entrada': preco_entrada,
            'candle_entrada': i,
            'tamanho': tamanho_posicao,
            'atr_entrada': atr_atual,
            'score': candle_atual['score']
        }
        break_even_ativado = False
    
    # Gerenciar posição aberta
    if posicao is not None:
        preco_atual = candle_atual['close']
        minimo_candle = candle_atual['low']
        maximo_candle = candle_atual['high']
        
        # Atualizar trailing stop
        novo_trailing = preco_atual - (TRAILING_MULT * posicao['atr_entrada'])
        if novo_trailing > trailing_stop:
            trailing_stop = novo_trailing
        
        # Ativar break-even
        unrealized = (preco_atual - posicao['entrada']) / posicao['entrada']
        if not break_even_ativado and unrealized >= (BREAK_EVEN_MULT * posicao['atr_entrada'] / posicao['entrada']):
            if trailing_stop > posicao['entrada']:
                stop_loss = trailing_stop
                break_even_ativado = True
        
        # Verificar saída por Stop Loss
        if minimo_candle <= stop_loss:
            preco_saida = stop_loss
            pnl = (preco_saida - posicao['entrada']) * posicao['tamanho']
            capital += pnl
            
            trades.append({
                'data_entrada': df.index[posicao['candle_entrada']],
                'data_saida': df.index[i],
                'tipo': posicao['tipo'],
                'entrada': posicao['entrada'],
                'saida': preco_saida,
                'tamanho': posicao['tamanho'],
                'pnl': pnl,
                'capital_final': capital,
                'motivo_saida': 'STOP_LOSS',
                'score': posicao['score'],
                'atr_entrada': posicao['atr_entrada']
            })
            
            posicao = None
            continue
        
        # Verificar saída por Take Profit
        if maximo_candle >= take_profit:
            preco_saida = take_profit
            pnl = (preco_saida - posicao['entrada']) * posicao['tamanho']
            capital += pnl
            
            trades.append({
                'data_entrada': df.index[posicao['candle_entrada']],
                'data_saida': df.index[i],
                'tipo': posicao['tipo'],
                'entrada': posicao['entrada'],
                'saida': preco_saida,
                'tamanho': posicao['tamanho'],
                'pnl': pnl,
                'capital_final': capital,
                'motivo_saida': 'TAKE_PROFIT',
                'score': posicao['score'],
                'atr_entrada': posicao['atr_entrada']
            })
            
            posicao = None
            continue
        
        # Verificar saída por Trailing Stop
        if minimo_candle <= trailing_stop and break_even_ativado:
            preco_saida = trailing_stop
            pnl = (preco_saida - posicao['entrada']) * posicao['tamanho']
            capital += pnl
            
            trades.append({
                'data_entrada': df.index[posicao['candle_entrada']],
                'data_saida': df.index[i],
                'tipo': posicao['tipo'],
                'entrada': posicao['entrada'],
                'saida': preco_saida,
                'tamanho': posicao['tamanho'],
                'pnl': pnl,
                'capital_final': capital,
                'motivo_saida': 'TRAILING_STOP',
                'score': posicao['score'],
                'atr_entrada': posicao['atr_entrada']
            })
            
            posicao = None
            continue

# Fechar posição aberta no final
if posicao is not None:
    preco_saida = df.iloc[-1]['close']
    pnl = (preco_saida - posicao['entrada']) * posicao['tamanho']
    capital += pnl
    
    trades.append({
        'data_entrada': df.index[posicao['candle_entrada']],
        'data_saida': df.index[-1],
        'tipo': posicao['tipo'],
        'entrada': posicao['entrada'],
        'saida': preco_saida,
        'tamanho': posicao['tamanho'],
        'pnl': pnl,
        'capital_final': capital,
        'motivo_saida': 'FIM_PERIODO',
        'score': posicao['score'],
        'atr_entrada': posicao['atr_entrada']
    })

# ============================================================================
# RESULTADOS E ESTATÍSTICAS
# ============================================================================

trades_df = pd.DataFrame(trades)

print("\n" + "=" * 80)
print("📊 RESULTADOS DO BACKTEST - V14 SQUEEZE DETECTION")
print("=" * 80)

if len(trades_df) > 0:
    total_trades = len(trades_df)
    wins = len(trades_df[trades_df['pnl'] > 0])
    losses = len(trades_df[trades_df['pnl'] <= 0])
    win_rate = (wins / total_trades) * 100
    
    pnl_total = trades_df['pnl'].sum()
    pnl_medio = trades_df['pnl'].mean()
    maior_gain = trades_df['pnl'].max()
    maior_loss = trades_df['pnl'].min()
    
    retorno_total = ((capital - CAPITAL_INICIAL) / CAPITAL_INICIAL) * 100
    
    print(f"\n💰 CAPITAL INICIAL: R$ {CAPITAL_INICIAL:,.2f}")
    print(f"💰 CAPITAL FINAL: R$ {capital:,.2f}")
    print(f"📈 RETORNO TOTAL: {retorno_total:.2f}%")
    print(f"📊 LUCRO/PREJUÍZO: R$ {pnl_total:,.2f}")
    
    print(f"\n📋 ESTATÍSTICAS DE TRADES:")
    print(f"   Total de Trades: {total_trades}")
    print(f"   Wins: {wins} ({win_rate:.1f}%)")
    print(f"   Losses: {losses} ({100-win_rate:.1f}%)")
    print(f"   PnL Médio: R$ {pnl_medio:,.2f}")
    print(f"   Maior Gain: R$ {maior_gain:,.2f}")
    print(f"   Maior Loss: R$ {maior_loss:,.2f}")
    
    print(f"\n🎯 SAÍDAS POR MOTIVO:")
    for motivo in trades_df['motivo_saida'].unique():
        subset = trades_df[trades_df['motivo_saida'] == motivo]
        print(f"   {motivo}: {len(subset)} trades, "
              f"Win Rate: {(len(subset[subset['pnl']>0])/len(subset)*100):.1f}%, "
              f"PnL Médio: R$ {subset['pnl'].mean():,.2f}")
    
    # Salvar trades
    trades_df.to_csv('backtest_trades_axs_v14_squeeze.csv', index=False)
    print(f"\n✅ Trades salvos em: backtest_trades_axs_v14_squeeze.csv")
else:
    print("\n❌ NENHUM TRADE REALIZADO!")

print("\n" + "=" * 80)
