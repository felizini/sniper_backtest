#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Análise dos Períodos AXSUSDT 5m
Analisa dois meses de dados para identificar padrões e parâmetros ideais
"""
import pandas as pd
import numpy as np
from datetime import datetime

def carregar_dados(arquivo):
    """Carrega e prepara os dados do CSV"""
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

def calcular_indicadores(df):
    """Calcula indicadores técnicos para análise"""
    # EMAs
    for span in [9, 20, 34, 50, 200]:
        df[f'ema{span}'] = df['close'].ewm(span=span, adjust=False).mean()
    
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
    
    # ADX
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
    
    # Volatilidade (desvio padrão móvel)
    df['volatility'] = df['close'].rolling(20).std()
    df['volatility_pct'] = (df['volatility'] / df['close']) * 100
    
    # Máximas e mínimas recentes
    df['high_20'] = df['high'].rolling(20).max()
    df['low_20'] = df['low'].rolling(20).min()
    
    return df

def detectar_regime(df):
    """Detecta regime de mercado para cada candle"""
    regimes = []
    for i in range(len(df)):
        if i < 200:
            regimes.append('Insufficient Data')
            continue
        
        price = df['close'].iloc[i]
        ema200 = df['ema200'].iloc[i]
        ema200_prev = df['ema200'].iloc[i-10] if i >= 10 else ema200
        adx = df['adx'].iloc[i]
        
        if pd.isna(adx) or pd.isna(ema200):
            regimes.append('Unknown')
            continue
        
        slope = (ema200 - ema200_prev) / ema200_prev if ema200_prev != 0 else 0
        
        if adx < 20:
            regimes.append('Lateral')
        elif price > ema200 and slope > 0.0005:
            regimes.append('Bullish')
        elif price < ema200 and slope < -0.0005:
            regimes.append('Bearish')
        else:
            regimes.append('Lateral')
    
    df['regime'] = regimes
    return df

def analisar_pullbacks(df, regime_filtro='Bullish'):
    """Analisa pullbacks na EMA34 para identificar parâmetros ideais"""
    df_regime = df[df['regime'] == regime_filtro].copy()
    
    if len(df_regime) == 0:
        return None
    
    pullbacks = []
    for i in range(1, len(df_regime)):
        idx = df_regime.index[i]
        prev_idx = df_regime.index[i-1]
        
        ema34 = df_regime.loc[prev_idx, 'ema34']
        close = df_regime.loc[prev_idx, 'close']
        rsi = df_regime.loc[prev_idx, 'rsi']
        
        # Verifica se está em pullback na EMA34 (dentro de 0.5%)
        if ema34 * 0.995 <= close <= ema34 * 1.005:
            # Analisa movimento subsequente
            max_move = 0
            min_move = 0
            
            for j in range(i, min(i+100, len(df_regime))):
                curr_idx = df_regime.index[j]
                move_pct = (df_regime.loc[curr_idx, 'close'] - close) / close * 100
                max_move = max(max_move, move_pct)
                min_move = min(min_move, move_pct)
            
            pullbacks.append({
                'timestamp': df_regime.loc[prev_idx, 'timestamp'],
                'price': close,
                'rsi': rsi,
                'max_gain_pct': max_move,
                'max_loss_pct': min_move,
                'atr_pct': df_regime.loc[prev_idx, 'atr_pct']
            })
    
    if len(pullbacks) == 0:
        return None
    
    return pd.DataFrame(pullbacks)

def analisar_mean_reversion(df):
    """Analisa oportunidades de reversão à média (RSI extremo)"""
    oversold = df[(df['rsi'] < 30) & (df['regime'] == 'Lateral')].copy()
    overbought = df[(df['rsi'] > 70) & (df['regime'] == 'Lateral')].copy()
    
    results = {'oversold': [], 'overbought': []}
    
    for data, direction in [(oversold, 'oversold'), (overbought, 'overbought')]:
        for idx in data.index:
            i = df.index.get_loc(idx)
            close = df.loc[idx, 'close']
            rsi = df.loc[idx, 'rsi']
            
            max_move = 0
            min_move = 0
            
            for j in range(i, min(i+100, len(df))):
                curr_idx = df.index[j]
                if direction == 'oversold':
                    move_pct = (df.loc[curr_idx, 'close'] - close) / close * 100
                else:
                    move_pct = (close - df.loc[curr_idx, 'close']) / close * 100
                    
                max_move = max(max_move, move_pct)
                min_move = min(min_move, move_pct)
            
            results[direction].append({
                'timestamp': df.loc[idx, 'timestamp'],
                'price': close,
                'rsi': rsi,
                'max_gain_pct': max_move,
                'max_loss_pct': min_move,
                'atr_pct': df.loc[idx, 'atr_pct']
            })
    
    return results

def testar_parametros_stop_tp(df, sl_pct, tp_pct, regime='Bullish', side='long'):
    """Testa combinações de stop loss e take profit"""
    wins = 0
    losses = 0
    total_pnl = 0
    trades = []
    
    df_regime = df[df['regime'] == regime].copy()
    
    for i in range(1, len(df_regime)-10):
        idx = df_regime.index[i]
        prev_idx = df_regime.index[i-1]
        
        if side == 'long':
            ema34 = df_regime.loc[prev_idx, 'ema34']
            close = df_regime.loc[prev_idx, 'close']
            rsi = df_regime.loc[prev_idx, 'rsi']
            
            if not (ema34 * 0.995 <= close <= ema34 * 1.005):
                continue
            if not (40 <= rsi <= 65):
                continue
            
            entry_price = df_regime.loc[idx, 'open']
            sl_price = entry_price * (1 - sl_pct)
            tp_price = entry_price * (1 + tp_pct)
            
            # Simula movimento
            outcome = None
            exit_price = None
            for j in range(i, min(i+50, len(df_regime))):
                curr_idx = df_regime.index[j]
                high = df_regime.loc[curr_idx, 'high']
                low = df_regime.loc[curr_idx, 'low']
                
                if low <= sl_price:
                    outcome = 'loss'
                    exit_price = sl_price
                    break
                elif high >= tp_price:
                    outcome = 'win'
                    exit_price = tp_price
                    break
            
            if outcome:
                pnl = (exit_price - entry_price) / entry_price if side == 'long' else (entry_price - exit_price) / entry_price
                total_pnl += pnl
                trades.append(pnl)
                if outcome == 'win':
                    wins += 1
                else:
                    losses += 1
        else:  # short
            ema34 = df_regime.loc[prev_idx, 'ema34']
            close = df_regime.loc[prev_idx, 'close']
            rsi = df_regime.loc[prev_idx, 'rsi']
            
            if not (ema34 * 0.995 <= close <= ema34 * 1.005):
                continue
            if not (35 <= rsi <= 60):
                continue
            
            entry_price = df_regime.loc[idx, 'open']
            sl_price = entry_price * (1 + sl_pct)
            tp_price = entry_price * (1 - tp_pct)
            
            outcome = None
            exit_price = None
            for j in range(i, min(i+50, len(df_regime))):
                curr_idx = df_regime.index[j]
                high = df_regime.loc[curr_idx, 'high']
                low = df_regime.loc[curr_idx, 'low']
                
                if high >= sl_price:
                    outcome = 'loss'
                    exit_price = sl_price
                    break
                elif low <= tp_price:
                    outcome = 'win'
                    exit_price = tp_price
                    break
            
            if outcome:
                pnl = (entry_price - exit_price) / entry_price
                total_pnl += pnl
                trades.append(pnl)
                if outcome == 'win':
                    wins += 1
                else:
                    losses += 1
    
    total_trades = wins + losses
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0
    avg_win = np.mean([t for t in trades if t > 0]) if any(t > 0 for t in trades) else 0
    avg_loss = np.mean([t for t in trades if t < 0]) if any(t < 0 for t in trades) else 0
    
    return {
        'sl': sl_pct,
        'tp': tp_pct,
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': abs(avg_loss),
        'profit_factor': abs(total_pnl / sum(t for t in trades if t < 0)) if sum(t for t in trades if t < 0) != 0 else 0
    }

def otimizar_parametros(df, regime='Bullish', side='long'):
    """Otimiza parâmetros de SL e TP"""
    resultados = []
    
    sl_values = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03]
    tp_values = [0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05]
    
    for sl in sl_values:
        for tp in tp_values:
            resultado = testar_parametros_stop_tp(df, sl, tp, regime, side)
            if resultado['total_trades'] >= 10:  # Mínimo de trades para significância
                resultados.append(resultado)
    
    if len(resultados) == 0:
        return None
    
    # Ordena por profit factor
    resultados_df = pd.DataFrame(resultados)
    melhores = resultados_df.sort_values('profit_factor', ascending=False)
    
    return melhores.head(10)

def analisar_periodo_completo(arquivo, nome_periodo):
    """Análise completa de um período"""
    print(f"\n{'='*80}")
    print(f"ANÁLISE DO PERÍODO: {nome_periodo}")
    print(f"{'='*80}")
    
    df = carregar_dados(arquivo)
    print(f"\nDados carregados: {len(df)} candles")
    print(f"Período: {df['timestamp'].iloc[0]} a {df['timestamp'].iloc[-1]}")
    
    df = calcular_indicadores(df)
    df = detectar_regime(df)
    
    # Estatísticas de regimes
    regime_counts = df['regime'].value_counts()
    print(f"\n--- DISTRIBUIÇÃO DE REGIMES ---")
    for regime, count in regime_counts.items():
        pct = count / len(df) * 100
        print(f"{regime}: {count} ({pct:.1f}%)")
    
    # Estatísticas de volatilidade
    print(f"\n--- VOLATILIDADE (ATR %) ---")
    print(f"Média: {df['atr_pct'].mean():.3f}%")
    print(f"Mediana: {df['atr_pct'].median():.3f}%")
    print(f"Desvio Padrão: {df['atr_pct'].std():.3f}%")
    print(f"Mínimo: {df['atr_pct'].min():.3f}%")
    print(f"Máximo: {df['atr_pct'].max():.3f}%")
    
    # Movimentos médios
    df['return_1'] = df['close'].pct_change() * 100
    df['return_5'] = df['close'].pct_change(5) * 100
    df['return_10'] = df['close'].pct_change(10) * 100
    df['return_20'] = df['close'].pct_change(20) * 100
    
    print(f"\n--- MOVIMENTOS DE PREÇO (%) ---")
    print(f"Retorno médio (1 candle): {df['return_1'].mean():.4f}% (std: {df['return_1'].std():.4f}%)")
    print(f"Retorno médio (5 candles): {df['return_5'].mean():.4f}% (std: {df['return_5'].std():.4f}%)")
    print(f"Retorno médio (10 candles): {df['return_10'].mean():.4f}% (std: {df['return_10'].std():.4f}%)")
    print(f"Retorno médio (20 candles): {df['return_20'].mean():.4f}% (std: {df['return_20'].std():.4f}%)")
    
    # Pullbacks em regime Bullish
    print(f"\n--- ANÁLISE DE PULLBACKS (REGIME BULLISH) ---")
    pullbacks_bull = analisar_pullbacks(df, 'Bullish')
    if pullbacks_bull is not None and len(pullbacks_bull) > 0:
        print(f"Total de pullbacks identificados: {len(pullbacks_bull)}")
        print(f"Ganho máximo médio: {pullbacks_bull['max_gain_pct'].mean():.2f}%")
        print(f"Perda máxima média: {pullbacks_bull['max_loss_pct'].mean():.2f}%")
        print(f"RSI médio nos pullbacks: {pullbacks_bull['rsi'].mean():.1f}")
        print(f"ATR% médio: {pullbacks_bull['atr_pct'].mean():.3f}%")
        
        # Qual % atinge +2%, +3%, +4% antes de -1%, -1.5%, -2%?
        for tp in [0.02, 0.03, 0.04, 0.05]:
            for sl in [0.01, 0.015, 0.02]:
                wins = len(pullbacks_bull[pullbacks_bull['max_gain_pct'] >= tp*100])
                losses = len(pullbacks_bull[pullbacks_bull['max_loss_pct'] <= -sl*100])
                total = len(pullbacks_bull)
                print(f"TP {tp*100:.0f}% / SL {sl*100:.0f}%: {wins} ganhariam ({wins/total*100:.1f}%), {losses} perderiam ({losses/total*100:.1f}%)")
    else:
        print("Poucos ou nenhum pullback identificado em regime Bullish")
    
    # Pullbacks em regime Bearish
    print(f"\n--- ANÁLISE DE PULLBACKS (REGIME BEARISH) ---")
    pullbacks_bear = analisar_pullbacks(df, 'Bearish')
    if pullbacks_bear is not None and len(pullbacks_bear) > 0:
        print(f"Total de pullbacks identificados: {len(pullbacks_bear)}")
        print(f"Ganho máximo médio (short): {pullbacks_bear['max_gain_pct'].mean():.2f}%")
        print(f"Perda máxima média (short): {pullbacks_bear['max_loss_pct'].mean():.2f}%")
        print(f"RSI médio nos pullbacks: {pullbacks_bear['rsi'].mean():.1f}")
    else:
        print("Poucos ou nenhum pullback identificado em regime Bearish")
    
    # Mean reversion
    print(f"\n--- ANÁLISE DE REVERSÃO À MÉDIA (RSI EXTREMOS) ---")
    mr_results = analisar_mean_reversion(df)
    
    if len(mr_results['oversold']) > 0:
        df_oversold = pd.DataFrame(mr_results['oversold'])
        print(f"RSI < 30 em regime lateral: {len(df_oversold)} ocorrências")
        print(f"Ganho máximo médio: {df_oversold['max_gain_pct'].mean():.2f}%")
        print(f"Perda máxima média: {df_oversold['max_loss_pct'].mean():.2f}%")
    
    if len(mr_results['overbought']) > 0:
        df_overbought = pd.DataFrame(mr_results['overbought'])
        print(f"RSI > 70 em regime lateral: {len(df_overbought)} ocorrências")
        print(f"Ganho máximo médio (short): {df_overbought['max_gain_pct'].mean():.2f}%")
        print(f"Perda máxima média (short): {df_overbought['max_loss_pct'].mean():.2f}%")
    
    # Otimização de parâmetros
    print(f"\n--- OTIMIZAÇÃO DE PARÂMETROS (STOP/TP) ---")
    
    print("\nRegime BULLISH (Long):")
    opt_bull = otimizar_parametros(df, 'Bullish', 'long')
    if opt_bull is not None:
        print(opt_bull[['sl', 'tp', 'total_trades', 'win_rate', 'profit_factor']].to_string(index=False))
    else:
        print("Dados insuficientes para otimização")
    
    print("\nRegime BEARISH (Short):")
    opt_bear = otimizar_parametros(df, 'Bearish', 'short')
    if opt_bear is not None:
        print(opt_bear[['sl', 'tp', 'total_trades', 'win_rate', 'profit_factor']].to_string(index=False))
    else:
        print("Dados insuficientes para otimização")
    
    # Recomendações baseadas na análise
    print(f"\n--- RECOMENDAÇÕES DE PARÂMETROS ---")
    
    # Baseado no ATR médio
    atr_medio = df['atr_pct'].mean() / 100
    print(f"ATR Médio: {atr_medio*100:.2f}%")
    
    # Sugere stops baseados em múltiplos do ATR
    print(f"\nStops sugeridos (baseados em ATR):")
    print(f"  Stop Loss: {1.5 * atr_medio*100:.2f}% a {2.0 * atr_medio*100:.2f}%")
    print(f"  Take Profit: {3.0 * atr_medio*100:.2f}% a {4.0 * atr_medio*100:.2f}%")
    
    return df

def main():
    print("="*80)
    print("ANÁLISE ESTATÍSTICA - AXSUSDT 5min")
    print("Períodos: Abril 2026 e Maio-Junho 2026")
    print("="*80)
    
    # Analisar ambos os períodos
    df_abril = analisar_periodo_completo(
        '/workspace/AXSUSDT_2026-04-01_2026-04-30_5m.csv',
        'ABRIL 2026 (01-30)'
    )
    
    df_maijun = analisar_periodo_completo(
        '/workspace/AXSUSDT_2026-05-11_2026-06-12_5m.csv',
        'MAIO-JUNHO 2026 (11/05 - 12/06)'
    )
    
    # Comparação entre períodos
    print(f"\n{'='*80}")
    print("COMPARAÇÃO ENTRE PERÍODOS")
    print(f"{'='*80}")
    
    comparacao = {
        'Métrica': ['Candles', 'Preço Inicial', 'Preço Final', 'Variação Total %', 
                   'ATR Média %', 'ADX Médio', 'Regime Bullish %', 'Regime Bearish %', 'Regime Lateral %'],
        'Abril 2026': [
            len(df_abril),
            f"{df_abril['close'].iloc[0]:.4f}",
            f"{df_abril['close'].iloc[-1]:.4f}",
            f"{(df_abril['close'].iloc[-1] / df_abril['close'].iloc[0] - 1) * 100:.2f}%",
            f"{df_abril['atr_pct'].mean():.3f}",
            f"{df_abril['adx'].mean():.1f}",
            f"{(df_abril['regime'] == 'Bullish').sum() / len(df_abril) * 100:.1f}%",
            f"{(df_abril['regime'] == 'Bearish').sum() / len(df_abril) * 100:.1f}%",
            f"{(df_abril['regime'] == 'Lateral').sum() / len(df_abril) * 100:.1f}%"
        ],
        'Mai-Jun 2026': [
            len(df_maijun),
            f"{df_maijun['close'].iloc[0]:.4f}",
            f"{df_maijun['close'].iloc[-1]:.4f}",
            f"{(df_maijun['close'].iloc[-1] / df_maijun['close'].iloc[0] - 1) * 100:.2f}%",
            f"{df_maijun['atr_pct'].mean():.3f}",
            f"{df_maijun['adx'].mean():.1f}",
            f"{(df_maijun['regime'] == 'Bullish').sum() / len(df_maijun) * 100:.1f}%",
            f"{(df_maijun['regime'] == 'Bearish').sum() / len(df_maijun) * 100:.1f}%",
            f"{(df_maijun['regime'] == 'Lateral').sum() / len(df_maijun) * 100:.1f}%"
        ]
    }
    
    df_comp = pd.DataFrame(comparacao)
    print(df_comp.to_string(index=False))
    
    # Salvar recomendações
    print(f"\n{'='*80}")
    print("RECOMENDAÇÕES FINAIS PARA PARÂMETROS DO BACKTEST")
    print(f"{'='*80}")
    
    atr_global = (df_abril['atr_pct'].mean() + df_maijun['atr_pct'].mean()) / 2
    print(f"\nATR Médio Combinado: {atr_global:.3f}%")
    
    print("\n>>> PARÂMETROS SUGERIDOS PARA O CÓDIGO <<<")
    print("\nPara regime BULLISH (Pullback Long):")
    print(f"  - TP: 3.5% a 4.5%")
    print(f"  - SL: 1.2% a 1.8%")
    print(f"  - Trailing Stop: 1.0x a 1.5x ATR")
    print(f"  - Filtro RSI: 40-65")
    
    print("\nPara regime BEARISH (Pullback Short):")
    print(f"  - TP: 3.0% a 4.0%")
    print(f"  - SL: 1.2% a 1.8%")
    print(f"  - Trailing Stop: 1.0x a 1.5x ATR")
    print(f"  - Filtro RSI: 35-60")
    
    print("\nPara regime LATERAL (Mean Reversion):")
    print(f"  - TP: 1.5% a 2.5%")
    print(f"  - SL: 0.8% a 1.2%")
    print(f"  - RSI Oversold: < 30")
    print(f"  - RSI Overbought: > 70")
    
    print("\nFiltros de Tendência:")
    print(f"  - EMA200 slope threshold: 0.0005 (0.05%)")
    print(f"  - ADX threshold: 20")
    print(f"  - Distância da EMA34 para pullback: ±0.5%")
    
    # Salvar dados para referência
    df_abril.to_csv('/workspace/analise_abril_completa.csv', index=False)
    df_maijun.to_csv('/workspace/analise_maijun_completa.csv', index=False)
    print(f"\nDados completos salvos em:")
    print(f"  - /workspace/analise_abril_completa.csv")
    print(f"  - /workspace/analise_maijun_completa.csv")

if __name__ == "__main__":
    main()
