#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Análise Rápida dos Períodos AXSUSDT 5m
Versão otimizada para identificar parâmetros ideais
"""
import pandas as pd
import numpy as np

def carregar_dados(arquivo):
    df = pd.read_csv(arquivo)
    col_map = {
        'open_time_brasilia': 'timestamp',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    }
    existing_cols = {k: v for k, v in col_map.items() if k in df.columns}
    df.rename(columns=existing_cols, inplace=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def calcular_indicadores_rapido(df):
    # EMAs
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema34'] = df['close'].ewm(span=34, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()
    df['atr_pct'] = (df['atr'] / df['close']) * 100
    
    # ADX simplificado
    df['dm_plus'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']), 
                             np.maximum(0, df['high'] - df['high'].shift()), 0)
    df['dm_minus'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()), 
                              np.maximum(0, df['low'].shift() - df['low']), 0)
    df['tr'] = true_range
    df['atr_adx'] = df['tr'].rolling(14).mean()
    df['di_plus'] = np.where(df['atr_adx'] != 0, 100 * (df['dm_plus'] / df['atr_adx']), 0)
    df['di_minus'] = np.where(df['atr_adx'] != 0, 100 * (df['dm_minus'] / df['atr_adx']), 0)
    df['dx'] = np.where((df['di_plus'] + df['di_minus']) != 0, 
                        100 * np.abs(df['di_plus'] - df['di_minus']) / (df['di_plus'] + df['di_minus']), 0)
    df['adx'] = df['dx'].rolling(14).mean()
    
    return df

def detectar_regime_vectorized(df):
    regimes = ['Insufficient Data'] * len(df)
    
    for i in range(200, len(df)):
        price = df['close'].iloc[i]
        ema200 = df['ema200'].iloc[i]
        ema200_prev = df['ema200'].iloc[i-10]
        adx = df['adx'].iloc[i]
        
        if pd.isna(adx) or pd.isna(ema200):
            continue
        
        slope = (ema200 - ema200_prev) / ema200_prev if ema200_prev != 0 else 0
        
        if adx < 20:
            regimes[i] = 'Lateral'
        elif price > ema200 and slope > 0.0005:
            regimes[i] = 'Bullish'
        elif price < ema200 and slope < -0.0005:
            regimes[i] = 'Bearish'
        else:
            regimes[i] = 'Lateral'
    
    df['regime'] = regimes
    return df

def analisar_movimentos_futuros(df, indices, lookforward=50):
    """Analisa movimentos máximos após cada ponto"""
    resultados = []
    for idx in indices:
        i = df.index.get_loc(idx) if idx in df.index else idx
        close = df['close'].iloc[i]
        
        max_gain = 0
        max_loss = 0
        
        for j in range(i+1, min(i+lookforward, len(df))):
            move = (df['close'].iloc[j] - close) / close * 100
            max_gain = max(max_gain, move)
            max_loss = min(max_loss, move)
        
        resultados.append({
            'max_gain': max_gain,
            'max_loss': max_loss
        })
    
    return resultados

def main():
    print("="*80)
    print("ANÁLISE ESTATÍSTICA RÁPIDA - AXSUSDT 5min")
    print("="*80)
    
    arquivos = [
        ('/workspace/AXSUSDT_2026-04-01_2026-04-30_5m.csv', 'ABRIL 2026'),
        ('/workspace/AXSUSDT_2026-05-11_2026-06-12_5m.csv', 'MAIO-JUN 2026')
    ]
    
    all_stats = []
    
    for arquivo, nome in arquivos:
        print(f"\n{'='*80}")
        print(f"ANÁLISE: {nome}")
        print(f"{'='*80}")
        
        df = carregar_dados(arquivo)
        print(f"Candles: {len(df)}")
        print(f"Período: {df['timestamp'].iloc[0]} a {df['timestamp'].iloc[-1]}")
        
        df = calcular_indicadores_rapido(df)
        df = detectar_regime_vectorized(df)
        
        # Estatísticas básicas
        print(f"\n--- PREÇO ---")
        print(f"Início: ${df['close'].iloc[0]:.4f}")
        print(f"Fim: ${df['close'].iloc[-1]:.4f}")
        print(f"Variação: {(df['close'].iloc[-1]/df['close'].iloc[0]-1)*100:.2f}%")
        print(f"Máximo: ${df['high'].max():.4f}")
        print(f"Mínimo: ${df['low'].min():.4f}")
        
        # Volatilidade
        print(f"\n--- VOLATILIDADE (ATR%) ---")
        atr_med = df['atr_pct'].mean()
        atr_mediana = df['atr_pct'].median()
        atr_std = df['atr_pct'].std()
        print(f"Média: {atr_med:.3f}%")
        print(f"Mediana: {atr_mediana:.3f}%")
        print(f"Std: {atr_std:.3f}%")
        print(f"P25: {df['atr_pct'].quantile(0.25):.3f}%")
        print(f"P75: {df['atr_pct'].quantile(0.75):.3f}%")
        
        # Regimes
        print(f"\n--- REGIMES DE MERCADO ---")
        regime_counts = df['regime'].value_counts()
        for regime, count in regime_counts.items():
            pct = count / len(df) * 100
            print(f"{regime}: {count} ({pct:.1f}%)")
        
        # RSI stats
        print(f"\n--- RSI ---")
        print(f"Média: {df['rsi'].mean():.1f}")
        print(f"RSI < 30: {(df['rsi'] < 30).sum()} ({(df['rsi'] < 30).sum()/len(df)*100:.1f}%)")
        print(f"RSI > 70: {(df['rsi'] > 70).sum()} ({(df['rsi'] > 70).sum()/len(df)*100:.1f}%)")
        print(f"RSI 40-65: {((df['rsi'] >= 40) & (df['rsi'] <= 65)).sum()} ({((df['rsi'] >= 40) & (df['rsi'] <= 65)).sum()/len(df)*100:.1f}%)")
        
        # ADX
        print(f"\n--- ADX (Força Tendência) ---")
        print(f"Média: {df['adx'].mean():.1f}")
        print(f"ADX < 20 (lateral): {(df['adx'] < 20).sum()} ({(df['adx'] < 20).sum()/len(df)*100:.1f}%)")
        print(f"ADX >= 20 (tendência): {(df['adx'] >= 20).sum()} ({(df['adx'] >= 20).sum()/len(df)*100:.1f}%)")
        
        # Análise de Pullbacks na EMA34
        print(f"\n--- PULLBACKS NA EMA34 (REGIME BULLISH) ---")
        df_bull = df[df['regime'] == 'Bullish'].copy()
        if len(df_bull) > 0:
            pullback_mask = (
                (df_bull['close'] >= df_bull['ema34'] * 0.995) & 
                (df_bull['close'] <= df_bull['ema34'] * 1.005) &
                (df_bull['rsi'] >= 40) & (df_bull['rsi'] <= 65)
            )
            pullbacks = df_bull[pullback_mask]
            print(f"Pullbacks identificados: {len(pullbacks)}")
            
            if len(pullbacks) > 0:
                # Analisar movimento futuro (amostra)
                sample_indices = pullbacks.index[::max(1, len(pullbacks)//20)]  # Amostra de 20
                moves = analisar_movimentos_futuros(df, sample_indices, lookforward=30)
                
                if moves:
                    gains = [m['max_gain'] for m in moves]
                    losses = [abs(m['max_loss']) for m in moves]
                    print(f"Ganho máximo médio (amostra): {np.mean(gains):.2f}%")
                    print(f"Perda máxima média (amostra): {np.mean(losses):.2f}%")
                    
                    # Taxa de sucesso para diferentes TP/SL
                    for tp in [2, 3, 4, 5]:
                        for sl in [1, 1.5, 2]:
                            wins = sum(1 for m in moves if m['max_gain'] >= tp)
                            loss_hits = sum(1 for m in moves if m['max_loss'] <= -sl)
                            print(f"TP {tp}% / SL {sl}%: {wins} ganhos, {loss_hits} stops")
        
        # Pullbacks Bearish
        print(f"\n--- PULLBACKS NA EMA34 (REGIME BEARISH) ---")
        df_bear = df[df['regime'] == 'Bearish'].copy()
        if len(df_bear) > 0:
            pullback_mask = (
                (df_bear['close'] >= df_bear['ema34'] * 0.995) & 
                (df_bear['close'] <= df_bear['ema34'] * 1.005) &
                (df_bear['rsi'] >= 35) & (df_bear['rsi'] <= 60)
            )
            pullbacks = df_bear[pullback_mask]
            print(f"Pullbacks identificados: {len(pullbacks)}")
        
        # Mean Reversion
        print(f"\n--- MEAN REVERSION (RSI EXTREMOS + LATERAL) ---")
        df_lat = df[df['regime'] == 'Lateral']
        oversold = df_lat[df_lat['rsi'] < 30]
        overbought = df_lat[df_lat['rsi'] > 70]
        print(f"RSI < 30 em lateral: {len(oversold)}")
        print(f"RSI > 70 em lateral: {len(overbought)}")
        
        # Movimentos típicos
        print(f"\n--- MOVIMENTOS TÍPICOS ---")
        df['ret_1'] = df['close'].pct_change() * 100
        df['ret_5'] = df['close'].pct_change(5) * 100
        df['ret_10'] = df['close'].pct_change(10) * 100
        print(f"Retorno 1 candle: média {df['ret_1'].mean():.4f}%, std {df['ret_1'].std():.3f}%")
        print(f"Retorno 5 candles: média {df['ret_5'].mean():.4f}%, std {df['ret_5'].std():.3f}%")
        print(f"Retorno 10 candles: média {df['ret_10'].mean():.4f}%, std {df['ret_10'].std():.3f}%")
        
        all_stats.append({
            'nome': nome,
            'candles': len(df),
            'atr_medio': atr_med,
            'adx_medio': df['adx'].mean(),
            'bullish_pct': (df['regime'] == 'Bullish').sum() / len(df) * 100,
            'bearish_pct': (df['regime'] == 'Bearish').sum() / len(df) * 100,
            'lateral_pct': (df['regime'] == 'Lateral').sum() / len(df) * 100,
            'variacao_total': (df['close'].iloc[-1]/df['close'].iloc[0]-1)*100
        })
    
    # Resumo comparativo
    print(f"\n{'='*80}")
    print("RESUMO COMPARATIVO")
    print(f"{'='*80}")
    
    for stat in all_stats:
        print(f"\n{stat['nome']}:")
        print(f"  Candles: {stat['candles']}")
        print(f"  Variação total: {stat['variacao_total']:.2f}%")
        print(f"  ATR médio: {stat['atr_medio']:.3f}%")
        print(f"  ADX médio: {stat['adx_medio']:.1f}")
        print(f"  Bullish: {stat['bullish_pct']:.1f}%")
        print(f"  Bearish: {stat['bearish_pct']:.1f}%")
        print(f"  Lateral: {stat['lateral_pct']:.1f}%")
    
    # Recomendações finais
    print(f"\n{'='*80}")
    print("RECOMENDAÇÕES DE PARÂMETROS PARA O BACKTEST")
    print(f"{'='*80}")
    
    atr_global = np.mean([s['atr_medio'] for s in all_stats])
    print(f"\nATR Médio Global: {atr_global:.3f}%")
    
    print("\n>>> PARÂMETROS OTIMIZADOS <<<")
    print("\nRegime BULLISH (Pullback Long):")
    print(f"  Take Profit: {3.5:.1f}% a {4.5:.1f}%")
    print(f"  Stop Loss: {max(1.2, 1.5*atr_global):.1f}% a {max(1.8, 2.0*atr_global):.1f}%")
    print(f"  Trailing Stop: 1.0x a 1.5x ATR")
    print(f"  Filtro RSI: 40-65")
    print(f"  Distância EMA34: ±0.5%")
    
    print("\nRegime BEARISH (Pullback Short):")
    print(f"  Take Profit: {3.0:.1f}% a {4.0:.1f}%")
    print(f"  Stop Loss: {max(1.2, 1.5*atr_global):.1f}% a {max(1.8, 2.0*atr_global):.1f}%")
    print(f"  Trailing Stop: 1.0x a 1.5x ATR")
    print(f"  Filtro RSI: 35-60")
    print(f"  Distância EMA34: ±0.5%")
    
    print("\nRegime LATERAL (Mean Reversion):")
    print(f"  Take Profit: {1.5:.1f}% a {2.5:.1f}%")
    print(f"  Stop Loss: {0.8:.1f}% a {1.2:.1f}%")
    print(f"  RSI Oversold: < 30")
    print(f"  RSI Overbought: > 70")
    
    print("\nFiltros de Tendência:")
    print(f"  ADX Threshold: 20")
    print(f"  EMA200 Slope: 0.0005 (0.05%)")
    
    print(f"\n{'='*80}")
    print("Análise concluída!")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
