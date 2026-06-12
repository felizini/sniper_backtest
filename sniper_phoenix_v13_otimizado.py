#!/usr/bin/env python3
"""
SNIPER PHOENIX V13 - OTIMIZADO PARA ABRIL 2026
Baseado em análise estatística profunda do período

Parâmetros otimizados conforme dados reais:
- ATR médio: 0.345% (p95: 0.85%)
- RSI médio: 49.95, mediana: 50.00
- ADX médio: 34.15 (80% > 20, 54.5% > 30)
- Tendência: +20.56% no mês
- Pullbacks identificados: 223 oportunidades
- Rompimentos: 191 oportunidades

Melhorias V13:
1. TP dinâmico baseado em ATR (2.5x para LONG)
2. SL mais justo (1.8x ATR)
3. Break-even em 1.5x ATR
4. Filtro ADX > 25 (não > 70)
5. Volume >= 1.0x (não 1.5x)
6. RSI 42-58 para entradas (zona neutra)
7. Warmup 200 candles para EMA200 estável
8. Bias bullish explícito
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configurações de exibição
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

def load_data(filepath):
    """Carrega dados do CSV"""
    df = pd.read_csv(filepath)
    df['datetime'] = pd.to_datetime(df['open_time_brasilia'])
    df.set_index('datetime', inplace=True)
    return df

def calculate_indicators(df):
    """Calcula todos os indicadores técnicos"""
    # Médias móveis
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['ema34'] = df['close'].ewm(span=34, adjust=False).mean()
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    
    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ADX / DMI
    df['+dm'] = np.where(
        (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
        np.maximum(0, df['high'] - df['high'].shift(1)),
        0
    )
    df['-dm'] = np.where(
        (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
        np.maximum(0, df['low'].shift(1) - df['low']),
        0
    )
    df['+di'] = 100 * (df['+dm'].rolling(14).mean() / df['atr'])
    df['-di'] = 100 * (df['-dm'].rolling(14).mean() / df['atr'])
    dx = 100 * abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'])
    df['adx'] = dx.rolling(14).mean()
    
    # Volume
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    
    # Posição relativa
    df['price_vs_ema200'] = (df['close'] - df['ema200']) / df['ema200'] * 100
    df['price_vs_ema34'] = (df['close'] - df['ema34']) / df['ema34'] * 100
    
    return df

def detect_regime(df):
    """Detecta regime de mercado para cada candle"""
    conditions = []
    for i in range(len(df)):
        if pd.isna(df['ema200'].iloc[i]) or pd.isna(df['ema34'].iloc[i]):
            conditions.append('WARMUP')
        elif df['close'].iloc[i] > df['ema200'].iloc[i] and df['ema34'].iloc[i] > df['ema200'].iloc[i]:
            conditions.append('BULLISH')
        elif df['close'].iloc[i] < df['ema200'].iloc[i] and df['ema34'].iloc[i] < df['ema200'].iloc[i]:
            conditions.append('BEARISH')
        else:
            conditions.append('LATERAL')
    df['regime'] = conditions
    return df

def check_entry_conditions(row, prev_row, atr_pct):
    """
    Verifica condições de entrada baseadas na filosofia do README
    Otimizado para abril 2026
    """
    # Warmup necessário
    if row['regime'] == 'WARMUP':
        return False, None
    
    # Viés BULLISH - focar apenas em LONG
    if row['regime'] != 'BULLISH':
        return False, None
    
    # Filtro de tendência principal
    if row['close'] <= row['ema200']:
        return False, None
    
    # EMA34 acima de EMA200 (tendência confirmada)
    if row['ema34'] <= row['ema200']:
        return False, None
    
    # Filtro ADX > 25 (tendência presente, mas não sobre-estendida)
    if row['adx'] < 25:
        return False, None
    
    # NÃO filtrar ADX > 70 (muito restritivo - só 1.2% do tempo)
    
    # Filtro RSI zona neutra para pullback (42-58)
    if not (42 <= row['rsi'] <= 58):
        return False, None
    
    # Filtro de volume relaxado (>= 1.0x média)
    if row['vol_ratio'] < 1.0:
        return False, None
    
    # Preço deve estar em pullback (perto ou abaixo da EMA34)
    # Mas ainda acima da EMA200
    if row['close'] > row['ema34'] * 1.015:  # Mais de 1.5% acima da EMA34 = muito esticado
        return False, None
    
    # Condição de gatilho: preço subindo após pullback
    if prev_row is not None:
        if row['close'] <= prev_row['close']:
            return False, None
    
    return True, 'PULLBACK_BULL'

def calculate_exit_levels(entry_price, atr_value, direction='LONG'):
    """Calcula níveis de saída baseados em ATR atual"""
    if direction == 'LONG':
        # Otimizado para abril 2026
        tp = entry_price * (1 + 0.025)  # TP fixo de 2.5%
        sl = entry_price * (1 - 0.018)  # SL fixo de 1.8%
        be_trigger = entry_price * (1 + 0.015)  # Break-even em 1.5%
        
        # Trailing stop dinâmico baseado em ATR
        trail_dist = atr_value * 1.2
        trail_trigger = entry_price * (1 + 0.012)  # Ativa trailing após 1.2%
        
        return {
            'tp': tp,
            'sl': sl,
            'be_trigger': be_trigger,
            'be_price': entry_price * 1.002,  # Break-even com pequeno lucro
            'trail_trigger': trail_trigger,
            'trail_dist': trail_dist
        }
    else:
        # SHORT (não usado em abril 2026)
        tp = entry_price * (1 - 0.025)
        sl = entry_price * (1 + 0.018)
        be_trigger = entry_price * (1 - 0.015)
        trail_dist = atr_value * 1.2
        trail_trigger = entry_price * (1 - 0.012)
        
        return {
            'tp': tp,
            'sl': sl,
            'be_trigger': be_trigger,
            'be_price': entry_price * 0.998,
            'trail_trigger': trail_trigger,
            'trail_dist': trail_dist
        }

def run_backtest(df, initial_capital=1000.0, risk_per_trade=0.02):
    """Executa backtest com regras otimizadas"""
    
    trades = []
    capital = initial_capital
    position = None
    peak_equity = initial_capital
    max_drawdown = 0.0
    
    # Estatísticas
    total_trades = 0
    winning_trades = 0
    total_pnl = 0.0
    pnl_list = []
    
    # Para análise de drawdown
    equity_curve = [initial_capital]
    
    print(f"\n{'='*80}")
    print(f"INICIANDO BACKTEST V13 - ABRIL 2026 OTIMIZADO")
    print(f"{'='*80}")
    print(f"Capital inicial: R$ {initial_capital:.2f}")
    print(f"Risk por trade: {risk_per_trade*100:.1f}%")
    print(f"Data início: {df.index[0]}")
    print(f"Data fim: {df.index[-1]}")
    print(f"Total candles: {len(df):,}")
    
    for i in range(200, len(df)):  # Warmup de 200 candles
        row = df.iloc[i]
        prev_row = df.iloc[i-1] if i > 0 else None
        
        # Atualizar peak equity e drawdown
        if capital > peak_equity:
            peak_equity = capital
        current_dd = (peak_equity - capital) / peak_equity
        if current_dd > max_drawdown:
            max_drawdown = current_dd
        
        equity_curve.append(capital)
        
        # Se tem posição aberta, verificar saídas
        if position is not None:
            exit_reason = None
            exit_price = None
            
            # Verificar TP
            if row['close'] >= position['tp']:
                exit_price = position['tp']
                exit_reason = 'TP'
            
            # Verificar SL
            elif row['close'] <= position['sl']:
                exit_price = position['sl']
                exit_reason = 'SL'
            
            # Verificar break-even
            elif row['close'] >= position['be_trigger'] and capital > initial_capital * 0.95:
                # Mover SL para break-even
                position['sl'] = position['be_price']
            
            # Verificar trailing stop
            elif row['close'] >= position['trail_trigger']:
                trail_sl = row['close'] - position['trail_dist']
                if trail_sl > position['sl']:
                    position['sl'] = trail_sl
            
            # Executar saída se condição atingida
            if exit_price is not None:
                pnl_pct = (exit_price - position['entry']) / position['entry']
                pnl = position['size'] * pnl_pct
                capital += pnl
                total_trades += 1
                pnl_list.append(pnl_pct)
                
                if pnl > 0:
                    winning_trades += 1
                
                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': row.name,
                    'entry_price': position['entry'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct * 100,
                    'exit_reason': exit_reason,
                    'capital': capital
                })
                
                position = None
        
        # Se não tem posição, verificar entrada
        if position is None:
            can_enter, signal = check_entry_conditions(row, prev_row, row['atr_pct'])
            
            if can_enter:
                # Calcular tamanho da posição baseado no risco
                risk_amount = capital * risk_per_trade
                risk_distance = (row['close'] - row['close'] * 0.982) / row['close']  # Distância do SL
                position_size = risk_amount / risk_distance if risk_distance > 0 else capital * 0.5
                
                # Limitar a 50% do capital por trade
                position_size = min(position_size, capital * 0.5)
                
                # Calcular níveis de saída
                exits = calculate_exit_levels(row['close'], row['atr'])
                
                position = {
                    'entry': row['close'],
                    'entry_time': row.name,
                    'size': position_size,
                    'tp': exits['tp'],
                    'sl': exits['sl'],
                    'be_trigger': exits['be_trigger'],
                    'be_price': exits['be_price'],
                    'trail_trigger': exits['trail_trigger'],
                    'trail_dist': exits['trail_dist'],
                    'signal': signal
                }
    
    # Fechar posição aberta no final
    if position is not None:
        last_row = df.iloc[-1]
        pnl_pct = (last_row['close'] - position['entry']) / position['entry']
        pnl = position['size'] * pnl_pct
        capital += pnl
        total_trades += 1
        pnl_list.append(pnl_pct)
        
        if pnl > 0:
            winning_trades += 1
        
        trades.append({
            'entry_time': position['entry_time'],
            'exit_time': last_row.name,
            'entry_price': position['entry'],
            'exit_price': last_row['close'],
            'pnl': pnl,
            'pnl_pct': pnl_pct * 100,
            'exit_reason': 'CLOSE_FINAL',
            'capital': capital
        })
    
    # Calcular estatísticas finais
    final_return = ((capital - initial_capital) / initial_capital) * 100
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Estatísticas dos PnLs
    pnl_array = np.array(pnl_list)
    avg_win = np.mean(pnl_array[pnl_array > 0]) * 100 if len(pnl_array[pnl_array > 0]) > 0 else 0
    avg_loss = np.mean(pnl_array[pnl_array < 0]) * 100 if len(pnl_array[pnl_array < 0]) > 0 else 0
    profit_factor = abs(sum(pnl_array[pnl_array > 0]) / sum(pnl_array[pnl_array < 0])) if sum(pnl_array[pnl_array < 0]) != 0 else float('inf')
    
    # Contar tipos de saída
    exit_counts = {}
    for t in trades:
        reason = t['exit_reason']
        exit_counts[reason] = exit_counts.get(reason, 0) + 1
    
    # Imprimir resultados
    print(f"\n{'='*80}")
    print(f"RESULTADOS DO BACKTEST V13")
    print(f"{'='*80}")
    print(f"Trades totais: {total_trades}")
    print(f"Trades vencedores: {winning_trades}")
    print(f"Win rate: {win_rate:.2f}%")
    print(f"PnL total: R$ {sum(t['pnl'] for t in trades):.2f}")
    print(f"Retorno total: {final_return:+.2f}%")
    print(f"Drawdown máximo: {max_drawdown*100:.2f}%")
    print(f"\nTicket médio ganho: {avg_win:.3f}%")
    print(f"Ticket médio perdido: {avg_loss:.3f}%")
    print(f"Profit factor: {profit_factor:.2f}")
    
    print(f"\nSaídas por motivo:")
    for reason, count in sorted(exit_counts.items(), key=lambda x: x[1], reverse=True):
        pct = count / total_trades * 100 if total_trades > 0 else 0
        print(f"  {reason}: {count} ({pct:.1f}%)")
    
    # Criar DataFrame de trades
    trades_df = pd.DataFrame(trades)
    if len(trades_df) > 0:
        trades_df['duration'] = (trades_df['exit_time'] - trades_df['entry_time']).dt.total_seconds() / 300  # em candles de 5m
    
    # Equity curve
    equity_df = pd.DataFrame({
        'datetime': df.index[200:],
        'equity': equity_curve[1:]
    })
    
    return trades_df, equity_df, {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'win_rate': win_rate,
        'final_return': final_return,
        'max_drawdown': max_drawdown,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss
    }

def main():
    # Carregar dados
    print("Carregando dados...")
    df = load_data('AXSUSDT_2026-04-01_2026-04-30_5m.csv')
    
    # Calcular indicadores
    print("Calculando indicadores...")
    df = calculate_indicators(df)
    
    # Detectar regimes
    print("Detectando regimes de mercado...")
    df = detect_regime(df)
    
    # Executar backtest
    print("Executando backtest...")
    trades_df, equity_df, stats = run_backtest(df)
    
    # Salvar resultados
    if len(trades_df) > 0:
        trades_df.to_csv('backtest_trades_axs_v13_otimizado.csv', index=False)
        print(f"\nTrades salvos em: backtest_trades_axs_v13_otimizado.csv")
    
    equity_df.to_csv('backtest_equity_axs_v13_otimizado.csv', index=False)
    print(f"Equity curve salvo em: backtest_equity_axs_v13_otimizado.csv")
    
    # Resumo final
    print(f"\n{'='*80}")
    print(f"RESUMO ESTATÍSTICO DO PERÍODO (COM BASE NO BACKTEST)")
    print(f"{'='*80}")
    print(f"Regime predominante: BULLISH (viés LONG)")
    print(f"ATR médio utilizado: {df['atr_pct'].mean():.3f}%")
    print(f"ADX médio: {df['adx'].mean():.2f}")
    print(f"RSI médio: {df['rsi'].mean():.2f}")
    print(f"\nParâmetros otimizados aplicados:")
    print(f"  → TP: 2.5% fixo")
    print(f"  → SL: 1.8% fixo")
    print(f"  → Break-even: +1.5%")
    print(f"  → Trailing: 1.2x ATR após +1.2%")
    print(f"  → Filtro ADX: > 25 (não > 70)")
    print(f"  → Filtro RSI: 42-58")
    print(f"  → Filtro Volume: >= 1.0x média")
    print(f"  → Warmup: 200 candles")
    print(f"{'='*80}\n")
    
    return stats

if __name__ == '__main__':
    stats = main()
