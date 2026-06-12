"""
SNIPER PHOENIX V15B - ESTRATÉGIA DE ACELERAÇÃO INICIAL
Foco: Capturar o INÍCIO da explosão (candles 00:00-01:00 do dia 25/04)

Ajustes Baseados na Análise do Dia 25/04:
1. Volume threshold reduzido: 2.0x (não 3.0x)
2. Entrada precoce: Primeiro candle com volume >2x E preço subindo
3. Sem filtro de breakout imediato (rompimento acontece depois)
4. Volatility expansion: 1.2x (não 1.5x)
5. RSI mínimo: 50 (não 60) - RSI sobe DURANTE o movimento

Parâmetros Otimizados:
- TP: 15% (movimento de +43% no dia 25)
- SL: 4% (stop mais largo para volatilidade extrema)
- Trailing: Ativo após 8%, offset 5%
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

class SniperPhoenixV15B:
    def __init__(self, capital_inicial=1000.0):
        self.capital_inicial = capital_inicial
        self.capital = capital_inicial
        self.posicao = 0
        self.preco_entrada = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trailing_ativo = False
        self.trailing_reference = 0
        self.trades_log = []
        
        # Parâmetros ajustados para captura precoce
        self.volume_explosion_threshold = 2.0  # Reduzido de 3.0
        self.volatility_expansion_threshold = 1.2  # Reduzido de 1.5
        self.rsi_min = 50  # Reduzido de 60
        self.ema_period = 200
        
        # Saídas
        self.tp_percent = 0.15  # Aumentado de 0.10
        self.sl_percent = 0.04  # Aumentado de 0.03
        self.trailing_trigger = 0.08  # Aumentado de 0.05
        self.trailing_offset = 0.05  # Aumentado de 0.03
        
        self.warmup_period = 200
        
    def calculate_indicators(self, df):
        df = df.copy()
        
        # EMAs
        df['ema200'] = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        
        # ATR
        df['high_low'] = df['high'] - df['low']
        df['high_close'] = abs(df['high'] - df['close'].shift(1))
        df['low_close'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()
        df['atr_avg_10'] = df['atr'].rolling(window=10).mean()
        
        # Volume
        df['volume_ma20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Momentum (preço subindo)
        df['price_change'] = df['close'].pct_change()
        df['highest_4d'] = df['high'].rolling(window=4).max().shift(1)
        
        # Volatilidade relativa
        df['volatility_expansion'] = df['atr'] / df['atr_avg_10']
        
        return df
    
    def detect_acceleration_signal(self, df, idx):
        """Detecta aceleração inicial - filtros mais flexíveis"""
        if idx < self.warmup_period:
            return False, "Warmup"
            
        row = df.iloc[idx]
        
        # 1. Volume acelerando (>= 2x média)
        if row['volume_ratio'] < self.volume_explosion_threshold:
            return False, f"Volume {row['volume_ratio']:.2f}x < {self.volume_explosion_threshold}x"
        
        # 2. Preço subindo no candle
        if row['price_change'] <= 0.01:  # Pelo menos 1% de alta
            return False, f"Preço não subindo: {row['price_change']*100:.2f}%"
        
        # 3. RSI neutro ou subindo (>= 50)
        if pd.isna(row['rsi']) or row['rsi'] < self.rsi_min:
            return False, f"RSI {row['rsi']:.2f} < {self.rsi_min}"
        
        # 4. Preço acima EMA200 (tendência bullish)
        if row['close'] <= row['ema200']:
            dist = (row['close'] - row['ema200']) / row['ema200'] * 100
            return False, f"Abaixo EMA200: {dist:.2f}%"
        
        # 5. Volatilidade expandindo (>= 1.2x)
        if row['volatility_expansion'] < self.volatility_expansion_threshold:
            return False, f"Vol {row['volatility_expansion']:.2f}x < {self.volatility_expansion_threshold}x"
        
        return True, "ACELERAÇÃO DETECTADA"
    
    def check_exit_conditions(self, df, idx, current_price):
        if self.posicao == 0:
            return None, "Sem posição"
        
        pnl_percent = (current_price - self.preco_entrada) / self.preco_entrada
        
        # Trailing stop
        if not self.trailing_ativo and pnl_percent >= self.trailing_trigger:
            self.trailing_ativo = True
            self.trailing_reference = current_price
            return None, f"Trailing ativado {pnl_percent*100:.2f}%"
        
        if self.trailing_ativo:
            if current_price > self.trailing_reference:
                self.trailing_reference = current_price
            trailing_stop = self.trailing_reference * (1 - self.trailing_offset)
            if current_price <= trailing_stop:
                return 'SELL', f"Trailing {pnl_percent*100:.2f}%"
        
        # TP/SL
        if current_price >= self.take_profit:
            return 'SELL', f"TP {pnl_percent*100:.2f}%"
        if current_price <= self.stop_loss:
            return 'SELL', f"SL {pnl_percent*100:.2f}%"
        
        # Saída fim do dia
        hour = (idx % 78) // 12
        if hour >= 23 and self.posicao > 0:
            return 'SELL', f"Fim dia {pnl_percent*100:.2f}%"
        
        return None, f"Holding {pnl_percent*100:.2f}%"
    
    def execute_backtest(self, df):
        print("=" * 80)
        print("SNIPER PHOENIX V15B - ACELERAÇÃO INICIAL")
        print("=" * 80)
        print(f"Período: {df['date'].min()} até {df['date'].max()}")
        print(f"Candles: {len(df)} | Capital: R$ {self.capital_inicial:,.2f}")
        print(f"Parâmetros: Vol>{self.volume_explosion_threshold}x, RSI>{self.rsi_min}, TP={self.tp_percent*100:.0f}%, SL={self.sl_percent*100:.0f}%")
        print("=" * 80)
        
        df = self.calculate_indicators(df)
        
        for idx in range(len(df)):
            if idx < self.warmup_period:
                continue
            
            row = df.iloc[idx]
            current_price = row['close']
            timestamp = row['date']
            
            # Verifica saídas
            if self.posicao > 0:
                action, reason = self.check_exit_conditions(df, idx, current_price)
                
                if action == 'SELL':
                    valor_saida = self.posicao * current_price
                    pnl = valor_saida - (self.posicao * self.preco_entrada)
                    pnl_percent = (current_price - self.preco_entrada) / self.preco_entrada
                    
                    self.capital += valor_saida
                    self.trades_log.append({
                        'trade_id': len(self.trades_log) // 2 + 1,
                        'timestamp': timestamp,
                        'type': 'EXIT',
                        'price': current_price,
                        'quantity': self.posicao,
                        'pnl': pnl,
                        'pnl_percent': pnl_percent,
                        'reason': reason,
                        'capital_after': self.capital,
                        'entry_price': self.preco_entrada,
                        'exit_price': current_price,
                        'volume': row['volume'],
                        'volume_ratio': row['volume_ratio'],
                        'rsi': row['rsi']
                    })
                    
                    self.posicao = 0
                    self.trailing_ativo = False
                    continue
            
            # Procura entrada
            if self.posicao == 0:
                is_signal, reason = self.detect_acceleration_signal(df, idx)
                
                if is_signal:
                    # Usa 100% do capital disponível
                    capital_disponivel = self.capital
                    quantidade = capital_disponivel / current_price
                    valor_alocado = quantidade * current_price
                    
                    self.posicao = quantidade
                    self.preco_entrada = current_price
                    self.take_profit = current_price * (1 + self.tp_percent)
                    self.stop_loss = current_price * (1 - self.sl_percent)
                    self.trailing_ativo = False
                    
                    # Deduz o capital alocado
                    self.capital -= valor_alocado
                    
                    self.trades_log.append({
                        'trade_id': len(self.trades_log) // 2 + 1,
                        'timestamp': timestamp,
                        'type': 'ENTRY',
                        'price': current_price,
                        'quantity': quantidade,
                        'pnl': 0,
                        'pnl_percent': 0,
                        'reason': reason,
                        'capital_after': self.capital,
                        'entry_price': current_price,
                        'exit_price': None,
                        'volume': row['volume'],
                        'volume_ratio': row['volume_ratio'],
                        'rsi': row['rsi'],
                        'volatility_expansion': row['volatility_expansion']
                    })
        
        return self.generate_report(df)
    
    def generate_report(self, df):
        print("\n" + "=" * 80)
        print("RELATÓRIO V15B")
        print("=" * 80)
        
        if not self.trades_log:
            print("Nenhum trade!")
            return {}
        
        trades_df = pd.DataFrame(self.trades_log)
        entries = trades_df[trades_df['type'] == 'ENTRY']
        exits = trades_df[trades_df['type'] == 'EXIT']
        
        total_trades = len(exits)
        if total_trades == 0:
            return {}
        
        winning = exits[exits['pnl'] > 0]
        losing = exits[exits['pnl'] <= 0]
        
        win_rate = len(winning) / total_trades * 100
        total_pnl = exits['pnl'].sum()
        total_return = (self.capital - self.capital_inicial) / self.capital_inicial * 100
        
        avg_win = winning['pnl'].mean() if len(winning) > 0 else 0
        avg_loss = abs(losing['pnl'].mean()) if len(losing) > 0 else 0
        
        tp_hits = len(exits[exits['reason'].str.contains('TP', na=False)])
        trail_hits = len(exits[exits['reason'].str.contains('Trailing', na=False)])
        
        print(f"\n📊 MÉTRICAS:")
        print(f"   Trades: {total_trades}")
        print(f"   Win Rate: {win_rate:.2f}%")
        print(f"   PnL Total: R$ {total_pnl:,.2f}")
        print(f"   Retorno: {total_return:.2f}%")
        print(f"   Capital Final: R$ {self.capital:,.2f}")
        
        print(f"\n💰 ANÁLISE:")
        print(f"   Vitórias: {len(winning)} (média R$ {avg_win:,.2f})")
        print(f"   Derrotas: {len(losing)} (média R$ {avg_loss:,.2f})")
        
        print(f"\n🎯 SAÍDAS:")
        print(f"   TP: {tp_hits} ({tp_hits/total_trades*100:.1f}%)")
        print(f"   Trailing: {trail_hits} ({trail_hits/total_trades*100:.1f}%)")
        
        print(f"\n📈 ENTRADAS:")
        print(f"   Volume Ratio Médio: {entries['volume_ratio'].mean():.2f}x")
        print(f"   RSI Médio: {entries['rsi'].mean():.2f}")
        
        print(f"\n📝 TRADES:")
        for _, trade in exits.iterrows():
            status = "✅" if trade['pnl'] > 0 else "❌"
            print(f"   #{trade['trade_id']} {trade['timestamp'].strftime('%Y-%m-%d %H:%M')} | {status} | "
                  f"R$ {trade['pnl']:,.2f} ({trade['pnl_percent']*100:.1f}%) | {trade['reason'][:35]}")
        
        print("\n" + "=" * 80)
        
        trades_df.to_csv('backtest_trades_axs_v15b_aceleracao.csv', index=False)
        print(f"✅ Salvo: backtest_trades_axs_v15b_aceleracao.csv")
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'capital_final': self.capital
        }

def load_data(filepath='AXS_abril_2026.csv'):
    print(f"Carregando {filepath}...")
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.lower().str.strip()
    
    column_mapping = {'open_time_brasilia': 'date'}
    for old, new in column_mapping.items():
        if old in df.columns:
            df[new] = df[old]
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    print(f"Dados: {len(df)} candles | {df['date'].min()} até {df['date'].max()}")
    return df

if __name__ == "__main__":
    import sys
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'AXS_abril_2026.csv'
    df = load_data(filepath)
    
    estrategia = SniperPhoenixV15B(capital_inicial=1000.0)
    resultados = estrategia.execute_backtest(df)
    
    print("\n" + "=" * 80)
    print("COMPARAÇÃO")
    print("=" * 80)
    print("V13 (Trend-Following): 28 trades, 57.1% WR, +3.26%")
    print("V15 (Explosão Tardia): 0 trades (filtros restritivos)")
    if resultados:
        print(f"V15B (Aceleração): {resultados['total_trades']} trades, {resultados['win_rate']:.2f}% WR, {resultados['total_return']:.2f}%")
    print("=" * 80)
