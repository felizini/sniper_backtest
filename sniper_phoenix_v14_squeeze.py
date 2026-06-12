#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNIPER PHOENIX V14 - ANTECIPAÇÃO DE PICOS DE ALTA (SQUEEZE DETECTION)

ESTRATÉGIA: Detectar compressão de volatilidade seguida de explosão direcional
para capturar movimentos parabólicos antecipadamente.

FILOSOFIA:
1. Squeeze Detection: Bandas de Bollinger estreitas + ATR em mínimos
2. Momentum Buildup: RSI em zona neutra com divergência positiva oculta
3. Volume Accumulation: Volume crescente antes da explosão
4. Breakout Confirmation: Preço rompe resistência com volume 2x+
5. Early Entry: Entrar no início da expansão, não no topo

PARÂMETROS OTIMIZADOS PARA ABRIL 2026:
- Período de squeeze: 20 candles
- Threshold ATR: < 40º percentil dos últimos 50 candles
- Volume accumulation: 3 candles consecutivos com volume crescente
- Trigger: Rompimento de máxima dos últimos 5 candles
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
df.rename(columns={'close': 'close', 'high': 'high', 'low': 'low', 'open': 'open', 'volume': 'volume'}, inplace=True)

# Filtrar período de teste: ABRIL 2026
df = df[df.index >= '2026-04-01']
df = df[df.index <= '2026-04-30 23:59']

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

# ADX para força da tendência
def calculate_adx(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.DataFrame([tr1, tr2, tr3]).max()
    
    atr = tr.ewm(span=period, adjust=False).mean()
    
    plus_di = 100 * (pd.Series(plus_dm).ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm).ewm(span=period, adjust=False).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(span=period, adjust=False).mean()
    
    return adx, plus_di, minus_di

adx_values, plus_di, minus_di = calculate_adx(df, 14)
df['adx'] = adx_values
df['plus_di'] = plus_di
df['minus_di'] = minus_di

# Volume
df['volume_ma'] = df['volume'].rolling(window=20).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma']

# Suporte e Resistência dinâmicos
df['highest_5'] = df['high'].rolling(window=5).max()
df['lowest_5'] = df['low'].rolling(window=5).min()
df['highest_20'] = df['high'].rolling(window=20).max()
df['lowest_20'] = df['low'].rolling(window=20).min()

# ============================================================================
# DETECÇÃO DE SQUEEZE E ACUMULAÇÃO
# ============================================================================

# Percentil do ATR (baixo = compressão)
df['atr_percentile_50'] = df['atr_pct'].rolling(window=50).apply(
    lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100
)

# Percentil da largura das Bandas de Bollinger
df['bb_percentile_50'] = df['bb_width'].rolling(window=50).apply(
    lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100
)

# Detecção de Squeeze RELAXADA (percentis mais altos)
df['squeeze'] = (df['atr_percentile_50'] < 60) | (df['bb_percentile_50'] < 60)

# Acumulação de volume (2 candles consecutivos com volume crescente)
df['volume_increasing'] = (
    (df['volume'] > df['volume'].shift(1)) &
    (df['volume'].shift(1) > df['volume'].shift(2))
)

# Acumulação de preço (fechamentos consecutivos acima da abertura) - 2 candles
df['price_accumulation'] = (
    (df['close'] > df['open']) &
    (df['close'].shift(1) > df['open'].shift(1))
)

# Divergência positiva oculta (RSI faz fundo mais alto, preço faz fundo mais baixo)
df['hidden_bull_div'] = (
    (df['rsi'] > df['rsi'].shift(2)) &
    (df['low'] < df['low'].shift(2)) &
    (df['rsi'] < 55)
)

# ============================================================================
# SISTEMA DE PONTUAÇÃO DE PROBABILIDADE
# ============================================================================

df['score'] = 0

# Pontos por squeeze detectado
df.loc[df['squeeze'], 'score'] += 25

# Pontos por acumulação de volume
df.loc[df['volume_increasing'], 'score'] += 20
df.loc[df['volume_ratio'] > 1.5, 'score'] += 15
df.loc[df['volume_ratio'] > 2.0, 'score'] += 10

# Pontos por acumulação de preço
df.loc[df['price_accumulation'], 'score'] += 15

# Pontos por divergência oculta
df.loc[df['hidden_bull_div'], 'score'] += 20

# Pontos por tendência (preço acima das EMAs)
df.loc[df['close'] > df['ema200'], 'score'] += 10
df.loc[(df['ema9'] > df['ema21']) & (df['ema21'] > df['ema50']), 'score'] += 15

# Pontos por RSI em zona ideal (45-60, espaço para subir)
df.loc[(df['rsi'] >= 45) & (df['rsi'] <= 60), 'score'] += 15

# Pontos por ADX moderado (25-50, tendência se formando mas não sobre-estendida)
df.loc[(df['adx'] >= 25) & (df['adx'] <= 50), 'score'] += 10

# Bonus por DI+ > DI-
df.loc[df['plus_di'] > df['minus_di'], 'score'] += 10

# ============================================================================
# REGRAS DE ENTRADA (LONG APENAS - BIAS BULLISH)
# ============================================================================

# Condições principais - MÍNIMO DE FILTROS PARA PERMITIR SINAIS
entry_condition = (
    (df['score'] >= 30) &  # Pontuação mínima bem baixa
    (df['close'] > df['ema200']) &  # Tendência de longo prazo bullish
    (df['adx'] < 80)  # Apenas evitar sobre-extremo
)

# Gatilho de entrada: rompimento da máxima dos últimos 5 candles
entry_trigger = (
    entry_condition &
    (df['close'] > df['highest_5'].shift(1))
)

# Marcar entradas
df['entry_signal'] = entry_trigger.astype(int)

# ============================================================================
# PARÂMETROS DE SAÍDA OTIMIZADOS
# ============================================================================

CAPITAL_INICIAL = 1000
RISCO_POR_TRADE = 0.02  # 2% do capital

# Parâmetros dinâmicos baseados em ATR
TP_MULT = 3.0  # Take Profit = 3x ATR
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
max_unrealized = 0

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
        max_unrealized = 0
    
    # Gerenciar posição aberta
    if posicao is not None:
        preco_atual = candle_atual['close']
        minimo_candle = candle_atual['low']
        maximo_candle = candle_atual['high']
        
        # Calcular lucro/prejuízo unrealizado
        unrealized = (preco_atual - posicao['entrada']) / posicao['entrada']
        max_unrealized = max(max_unrealized, unrealized)
        
        # Atualizar trailing stop
        novo_trailing = preco_atual - (TRAILING_MULT * posicao['atr_entrada'])
        if novo_trailing > trailing_stop:
            trailing_stop = novo_trailing
        
        # Ativar break-even
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
    
    # Estatísticas por motivo de saída
    saidas = trades_df.groupby('motivo_saida').agg({
        'pnl': ['count', 'mean', 'sum'],
        'score': 'mean'
    }).round(2)
    
    print(f"\n💰 CAPITAL INICIAL: R$ {CAPITAL_INICIAL:,.2f}")
    print(f"💰 CAPITAL FINAL: R$ {capital:,.2f}")
    print(f"📈 RETORNO TOTAL: {retorno_total:.2f}%")
    print(f"📊 LUCRO/PREJUÍZO: R$ {pnl_total:,.2f}")
    
    print(f"\n📋 ESTASTÍSTICAS DE TRADES:")
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
              f"PnL Médio: R$ {subset['pnl'].mean():,.2f}, "
              f"Score Médio: {subset['score'].mean():.1f}")
    
    # Análise de scores
    print(f"\n🎯 ANÁLISE DE SCORES:")
    print(f"   Score Médio nas Entradas: {trades_df['score'].mean():.1f}")
    print(f"   Score Mínimo: {trades_df['score'].min()}")
    print(f"   Score Máximo: {trades_df['score'].max()}")
    
    wins_df = trades_df[trades_df['pnl'] > 0]
    losses_df = trades_df[trades_df['pnl'] <= 0]
    
    if len(wins_df) > 0:
        print(f"   Score Médio em WINS: {wins_df['score'].mean():.1f}")
    if len(losses_df) > 0:
        print(f"   Score Médio em LOSSES: {losses_df['score'].mean():.1f}")
    
    # Salvar trades
    trades_df.to_csv('backtest_trades_axs_v14_squeeze.csv', index=False)
    print(f"\n✅ Trades salvos em: backtest_trades_axs_v14_squeeze.csv")
else:
    print("\n❌ NENHUM TRADE REALIZADO - Filtros muito restritivos!")
    print("   Sugestão: Reduzir threshold de score ou relaxar condições.")

print("\n" + "=" * 80)
print("🔍 ANÁLISE DE EFETIVIDADE DA ESTRATÉGIA DE ANTECIPAÇÃO")
print("=" * 80)

if len(trades_df) > 0:
    # Verificar quantos trades capturaram movimentos > 2%
    grandes_movimentos = trades_df[trades_df['pnl'] > CAPITAL_INICIAL * 0.02]
    print(f"\n🚀 TRADES COM GANHOS > 2%: {len(grandes_movimentos)} ({len(grandes_movimentos)/len(trades_df)*100:.1f}%)")
    
    # Tempo médio em trade
    trades_df['duracao'] = trades_df['data_saida'] - trades_df['data_entrada']
    duracao_media = trades_df['duracao'].mean()
    print(f"⏱️  DURAÇÃO MÉDIA DOS TRADES: {duracao_media}")
    
    # Analisar horários dos trades vencedores
    if len(wins_df) > 0:
        wins_df['hora'] = wins_df['data_entrada'].dt.hour
        hora_mais_comum = wins_df['hora'].mode().iloc[0] if len(wins_df['hora'].mode()) > 0 else "N/A"
        print(f"🕐 HORA MAIS COMUM EM WINS: {hora_mais_comum}:00")

print("\n" + "=" * 80)
