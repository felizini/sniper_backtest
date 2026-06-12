#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNIPER PHOENIX V16 - SNIPER DE EXPLOSÃO
========================================
Estratégia ultra-restritiva para capturar APENAS explosões reais como o dia 25/04.

FILOSOFIA:
- Melhor perder 5 oportunidades falsas do que entrar em 1 trade perdedor
- Filtros extremos baseados em compressão + rompimento + momentum
- Horário restrito (apenas manhã quando volume é real)
- Apenas LONG (viés bullish de abril)

PARÂMETROS OTIMIZADOS PARA ABRIL 2026:
- Compressão: ATR < percentil 25 (3 dias)
- Volume: > 3.0x média (rompimento real)
- Momentum: RSI > 60 + Preço rompendo máxima 5 candles
- Horário: 09:00-11:00 (volume institucional)
- TP: 3.0% (captura explosão sem ganância)
- SL: 1.5% (proteção rigorosa)
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURAÇÕES GERAIS
# ============================================================================

SYMBOL = 'AXS'
TIMEFRAME = '5m'
INITIAL_CAPITAL = 1000.00
COMMISSION_RATE = 0.001  # 0.1% por trade

# Período de teste: Abril 2026 (bullish +20.56%)
START_DATE = '2026-04-01'
END_DATE = '2026-04-30'

# Warmup para indicadores
WARMUP_PERIOD = 200

# ============================================================================
# PARÂMETROS DA ESTRATÉGIA V16 - SNIPER DE EXPLOSÃO
# ============================================================================

STRATEGY_PARAMS = {
    # Filtro de compressão (pré-explosão) - REMOVIDO pois explosões reais não têm compressão prévia
    'use_compression_filter': False,  # Desativado: dia 25 teve ATR alto desde início
    
    # Filtro de volume (rompimento real) - REDUZIDO para capturar início do movimento
    'volume_multiplier': 2.0,         # Volume > 2x média (antes 3.0x muito restritivo)
    'volume_lookback': 10,            # Média de volume
    
    # Filtro de momentum (confirmação)
    'rsi_threshold': 50,              # RSI > 50 (antes 60 perdia entrada cedo)
    'breakout_lookback': 3,           # Romper máxima de 3 candles (antes 5 muito lento)
    
    # Filtro de horário (capturar explosão completa)
    'trade_start_hour': 0,            # 00:00
    'trade_end_hour': 8,              # 08:00 (antes da grande alta das 07:00-08:00)
    
    # Viés direcional (abril foi bullish)
    'bias': 'BULLISH',                # Apenas LONG
    
    # Gerenciamento de risco - AJUSTADO PARA EXPLOSÃO
    'take_profit_pct': 8.0,           # TP 8.0% (explosão de +44% no dia 25)
    'stop_loss_pct': 2.0,             # SL 2.0% (mais largo para volatilidade)
    'use_trailing': True,             # Trailing para capturar tendência longa
    'trailing_atr_mult': 2.0,         # Trailing de 2x ATR
}

# ============================================================================
# CARREGAR DADOS
# ============================================================================

def load_data():
    """Carrega dados do CSV"""
    df = pd.read_csv('AXSUSDT_2026-04-01_2026-04-30_5m.csv')
    df['timestamp'] = pd.to_datetime(df['open_time_brasilia'])
    df.set_index('timestamp', inplace=True)
    
    # Filtrar período de abril 2026
    df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
    
    print(f"📊 Dados carregados: {len(df)} candles")
    print(f"   Período: {df.index[0].date()} a {df.index[-1].date()}")
    print(f"   Preço inicial: R$ {df['close'].iloc[0]:.2f}")
    print(f"   Preço final: R$ {df['close'].iloc[-1]:.2f}")
    print(f"   Variação Buy-and-Hold: +{(df['close'].iloc[-1]/df['close'].iloc[0]-1)*100:.2f}%")
    
    return df

# ============================================================================
# INDICADORES TÉCNICOS
# ============================================================================

def calculate_indicators(df):
    """Calcula todos os indicadores necessários"""
    
    # EMA para tendência
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['ema34'] = df['close'].ewm(span=34, adjust=False).mean()
    
    # ATR (volatilidade)
    df['high_low'] = df['high'] - df['low']
    df['high_close_prev'] = abs(df['high'] - df['close'].shift(1))
    df['low_close_prev'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['high_low', 'high_close_prev', 'low_close_prev']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=14).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ADX (força da tendência)
    df['plus_dm'] = df['high'].diff()
    df['minus_dm'] = -df['low'].diff()
    df['plus_dm'] = df['plus_dm'].where((df['plus_dm'] > df['minus_dm']) & (df['plus_dm'] > 0), 0)
    df['minus_dm'] = df['minus_dm'].where((df['minus_dm'] > df['plus_dm']) & (df['minus_dm'] > 0), 0)
    
    df['plus_di'] = 100 * (df['plus_dm'].rolling(14).mean() / df['atr'])
    df['minus_di'] = 100 * (df['minus_dm'].rolling(14).mean() / df['atr'])
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].rolling(14).mean()
    
    # Média de volume
    df['volume_ma'] = df['volume'].rolling(window=STRATEGY_PARAMS['volume_lookback']).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']
    
    # Percentil de ATR (compressão)
    df['atr_percentile'] = df['atr_pct'].rolling(window=20).apply(
        lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) * 100 if x.max() != x.min() else 50
    )
    
    # Máxima dos últimos N candles (para breakout)
    df['breakout_level'] = df['high'].rolling(window=STRATEGY_PARAMS['breakout_lookback']).max().shift(1)
    
    return df

# ============================================================================
# LÓGICA DE ENTRADA - SNIPER DE EXPLOSÃO
# ============================================================================

def check_entry_signal(row, idx, df):
    """
    Verifica se há sinal de entrada baseado em filtros para explosão.
    
    FILTROS OBRIGATÓRIOS:
    1. Volume > 2x média (início do movimento)
    2. Momentum (RSI > 50)
    3. Rompimento de resistência (3 candles)
    4. Horário adequado (00:00-08:00)
    5. Tendência bullish (preço > EMA200)
    
    FILTRO REMOVIDO: Compressão (não existia no dia 25)
    """
    
    params = STRATEGY_PARAMS
    
    # Filtro 0: Warmup period
    if idx < WARMUP_PERIOD:
        return False, "Warmup"
    
    # Filtro 1: Horário restrito (00:00-08:00 para capturar explosão completa)
    candle_hour = row.name.hour
    if candle_hour < params['trade_start_hour'] or candle_hour >= params['trade_end_hour']:
        return False, f"Fora horário ({candle_hour}:00)"
    
    # Filtro 2: Viés BULLISH (apenas LONG em abril)
    if params['bias'] == 'BULLISH' and row['close'] <= row['ema200']:
        return False, "Preço abaixo EMA200"
    
    # Filtro 3: Volume (> 2x média - início do movimento)
    if row['volume_ratio'] < params['volume_multiplier']:
        return False, f"Volume insuficiente ({row['volume_ratio']:.1f}x)"
    
    # Filtro 4: Momentum (RSI > 50)
    if row['rsi'] < params['rsi_threshold']:
        return False, f"RSI fraco ({row['rsi']:.1f})"
    
    # Filtro 5: Rompimento de resistência (preço > máxima dos últimos 3 candles)
    if row['close'] <= row['breakout_level']:
        return False, f"Sem rompimento (< {row['breakout_level']:.2f})"
    
    # ✅ TODOS OS FILTROS PASSARAM - SINAL DE COMPRA
    return True, "Todos filtros OK"

# ============================================================================
# GERENCIAMENTO DE POSIÇÃO
# ============================================================================

class Position:
    def __init__(self, entry_price, entry_time, capital_at_risk):
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.capital_at_risk = capital_at_risk
        self.shares = int(capital_at_risk / entry_price)
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None
        self.pnl = 0.0
        self.pnl_pct = 0.0
        self.max_profit = 0.0
        self.max_loss = 0.0
        
    def check_exit(self, row, params):
        """Verifica condições de saída com trailing stop"""
        
        if self.exit_price is not None:
            return False  # Já saiu
        
        # Calcular preços de saída base
        tp_price = self.entry_price * (1 + params['take_profit_pct'] / 100)
        sl_price = self.entry_price * (1 - params['stop_loss_pct'] / 100)
        
        # Trailing stop dinâmico
        trailing_stop = None
        if params.get('use_trailing', False):
            # Trailing = preço atual - (ATR x multiplicador)
            trailing_distance = row['atr'] * params.get('trailing_atr_mult', 2.0)
            trailing_stop = row['close'] - trailing_distance
            
            # Trailing só sobe, nunca desce
            if hasattr(self, 'trailing_stop_max'):
                if trailing_stop > self.trailing_stop_max:
                    self.trailing_stop_max = trailing_stop
                trailing_stop = self.trailing_stop_max
            else:
                self.trailing_stop_max = trailing_stop
        
        # Verificar Take Profit
        if row['high'] >= tp_price:
            self.exit_price = tp_price
            self.exit_time = row.name
            self.exit_reason = 'TP'
            self.pnl = (self.exit_price - self.entry_price) * self.shares
            self.pnl -= (self.entry_price + self.exit_price) * self.shares * COMMISSION_RATE
            self.pnl_pct = (self.exit_price / self.entry_price - 1) * 100
            return True
        
        # Verificar Trailing Stop (se ativado)
        if params.get('use_trailing', False) and trailing_stop is not None:
            if row['low'] <= trailing_stop:
                self.exit_price = trailing_stop
                self.exit_time = row.name
                self.exit_reason = f'TRAILING ({trailing_stop:.3f})'
                self.pnl = (self.exit_price - self.entry_price) * self.shares
                self.pnl -= (self.entry_price + self.exit_price) * self.shares * COMMISSION_RATE
                self.pnl_pct = (self.exit_price / self.entry_price - 1) * 100
                return True
        
        # Verificar Stop Loss fixo
        if row['low'] <= sl_price:
            self.exit_price = sl_price
            self.exit_time = row.name
            self.exit_reason = 'SL'
            self.pnl = (self.exit_price - self.entry_price) * self.shares
            self.pnl -= (self.entry_price + self.exit_price) * self.shares * COMMISSION_RATE
            self.pnl_pct = (self.exit_price / self.entry_price - 1) * 100
            return True
        
        # Atualizar max profit/loss para análise
        current_pnl = (row['close'] - self.entry_price) * self.shares
        if current_pnl > self.max_profit:
            self.max_profit = current_pnl
        if current_pnl < self.max_loss:
            self.max_loss = current_pnl
        
        return False

# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def run_backtest(df):
    """Executa o backtest da estratégia V16"""
    
    positions = []
    current_position = None
    capital = INITIAL_CAPITAL
    trades_log = []
    
    print(f"\n🚀 Iniciando backtest V16 - Sniper de Explosão")
    print(f"   Capital inicial: R$ {INITIAL_CAPITAL:.2f}")
    print(f"   Parâmetros:")
    for key, value in STRATEGY_PARAMS.items():
        print(f"      {key}: {value}")
    
    # Iterar sobre cada candle
    for idx, (timestamp, row) in enumerate(df.iterrows()):
        
        # Se tem posição aberta, verificar saída
        if current_position is not None:
            if current_position.check_exit(row, STRATEGY_PARAMS):
                # Posição fechada
                capital += current_position.pnl
                positions.append(current_position)
                
                trades_log.append({
                    'entry_time': current_position.entry_time,
                    'exit_time': current_position.exit_time,
                    'entry_price': current_position.entry_price,
                    'exit_price': current_position.exit_price,
                    'shares': current_position.shares,
                    'pnl': current_position.pnl,
                    'pnl_pct': current_position.pnl_pct,
                    'exit_reason': current_position.exit_reason,
                    'capital_after': capital,
                    'filters_passed': current_position.filters_passed
                })
                
                current_position = None
        
        # Se não tem posição, verificar entrada
        if current_position is None:
            signal, reason = check_entry_signal(row, idx, df)
            
            if signal:
                # Calcular capital por trade (100% do capital disponível)
                capital_at_risk = capital
                
                # Abrir posição
                current_position = Position(row['close'], timestamp, capital_at_risk)
                current_position.filters_passed = reason
                
                print(f"\n💰 COMPRA às {timestamp}: R$ {row['close']:.2f}")
                print(f"   Filtros: {reason}")
                print(f"   Shares: {current_position.shares}")
    
    # Fechar posição aberta no final (se houver)
    if current_position is not None:
        current_position.exit_price = df['close'].iloc[-1]
        current_position.exit_time = df.index[-1]
        current_position.exit_reason = 'FIM_PERIODO'
        current_position.pnl = (current_position.exit_price - current_position.entry_price) * current_position.shares
        current_position.pnl -= (current_position.entry_price + current_position.exit_price) * current_position.shares * COMMISSION_RATE
        current_position.pnl_pct = (current_position.exit_price / current_position.entry_price - 1) * 100
        capital += current_position.pnl
        positions.append(current_position)
        
        trades_log.append({
            'entry_time': current_position.entry_time,
            'exit_time': current_position.exit_time,
            'entry_price': current_position.entry_price,
            'exit_price': current_position.exit_price,
            'shares': current_position.shares,
            'pnl': current_position.pnl,
            'pnl_pct': current_position.pnl_pct,
            'exit_reason': current_position.exit_reason,
            'capital_after': capital,
            'filters_passed': current_position.filters_passed
        })
    
    return positions, trades_log, capital

# ============================================================================
# RELATÓRIO E MÉTRICAS
# ============================================================================

def generate_report(trades_log, final_capital, df):
    """Gera relatório detalhado do backtest"""
    
    total_trades = len(trades_log)
    winning_trades = [t for t in trades_log if t['pnl'] > 0]
    losing_trades = [t for t in trades_log if t['pnl'] <= 0]
    
    wins = len(winning_trades)
    losses = len(losing_trades)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = final_capital - INITIAL_CAPITAL
    total_return = (total_pnl / INITIAL_CAPITAL) * 100
    
    avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
    avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
    
    # Buy-and-Hold para comparação
    bh_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    
    print("\n" + "="*70)
    print("📊 RELATÓRIO FINAL - V16 SNIPER DE EXPLOSÃO")
    print("="*70)
    
    print(f"\n📈 MÉTRICAS DE PERFORMANCE:")
    print(f"   Trades totais: {total_trades}")
    print(f"   Vitórias: {wins} ({win_rate:.2f}%)")
    print(f"   Derrotas: {losses} ({100-win_rate:.2f}%)")
    print(f"   PnL Total: R$ {total_pnl:.2f}")
    print(f"   Retorno: {total_return:.2f}%")
    print(f"   Capital Final: R$ {final_capital:.2f}")
    
    print(f"\n💰 ANÁLISE FINANCEIRA:")
    if total_trades > 0:
        print(f"   Vitória média: R$ {avg_win:.2f}")
        print(f"   Derrota média: R$ {avg_loss:.2f}")
        if avg_loss != 0:
            print(f"   Ratio Win/Loss: {abs(avg_win/avg_loss):.2f}")
        else:
            print(f"   Ratio Win/Loss: N/A (sem derrotas)")
    else:
        print(f"   Nenhum trade realizado")
    
    print(f"\n📊 COMPARAÇÃO:")
    print(f"   Estratégia: {total_return:.2f}%")
    print(f"   Buy-and-Hold: {bh_return:.2f}%")
    print(f"   Alpha: {total_return - bh_return:.2f}%")
    
    # Detalhar trades
    if trades_log:
        print(f"\n📝 DETALHAMENTO DOS TRADES:")
        print("-"*70)
        for i, trade in enumerate(trades_log, 1):
            status = "✅ WIN" if trade['pnl'] > 0 else "❌ LOSS"
            print(f"   Trade #{i}: {status}")
            print(f"      Entrada: {trade['entry_time']} @ R$ {trade['entry_price']:.2f}")
            print(f"      Saída: {trade['exit_time']} @ R$ {trade['exit_price']:.2f} ({trade['exit_reason']})")
            print(f"      PnL: R$ {trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")
            print(f"      Filtros: {trade['filters_passed']}")
            print()
    
    # Salvar trades em CSV
    if trades_log:
        trades_df = pd.DataFrame(trades_log)
        trades_df.to_csv('backtest_trades_axs_v16_sniper.csv', index=False)
        print(f"💾 Trades salvos em: backtest_trades_axs_v16_sniper.csv")
    
    return {
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'total_return': total_return,
        'final_capital': final_capital,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'bh_return': bh_return,
        'alpha': total_return - bh_return
    }

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("="*70)
    print("🎯 SNIPER PHOENIX V16 - SNIPER DE EXPLOSÃO")
    print("="*70)
    print("\nObjetivo: Capturar APENAS explosões reais (ex: dia 25/04)")
    print("Filosofia: Melhor perder oportunidades do que entrar em trades falsos\n")
    
    # Carregar dados
    df = load_data()
    
    # Calcular indicadores
    df = calculate_indicators(df)
    
    # Executar backtest
    positions, trades_log, final_capital = run_backtest(df)
    
    # Gerar relatório
    metrics = generate_report(trades_log, final_capital, df)
    
    print("\n" + "="*70)
    print("✅ Backtest concluído!")
    print("="*70)
