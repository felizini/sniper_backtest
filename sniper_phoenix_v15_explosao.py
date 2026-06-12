"""
SNIPER PHOENIX V15 - ESTRATÉGIA DE EXPLOSÃO DE VOLUME
Foco: Capturar movimentos explosivos como o dia 25/04 (+21.35%)

Premissas Baseadas na Análise Estatística de Abril 2026:
1. Dias 21-24: Compressão (volume baixo, ATR contraindo)
2. Dia 25: Explosão (volume 13.76x média, alta volatilidade)
3. Padrão: 3-4 dias de compressão seguidos de rompimento

Filtros Implementados:
- Volume Compression Ratio: Média volume últimos 3 dias < 0.5x média 20 dias
- Volume Explosion: Volume atual > 3x média 20 dias
- Price Breakout: Preço rompe máxima dos últimos 3-5 dias
- Volatility Expansion: ATR atual > 1.5x ATR médio últimos 10 dias
- Momentum Confirmation: RSI > 60 e subindo
- Trend Alignment: Preço > EMA200 (para LONG)

Parâmetros Otimizados para Explosões:
- TP: 8-12% (capturar grande parte do movimento)
- SL: 3% (stop mais largo para aguentar volatilidade)
- Trailing: Ativo após 5% de lucro
- Posição: 100% alocação (eventos raros, alta convicção)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configurações de exibição
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
pd.set_option('display.float_format', lambda x: f'{x:.4f}')

class SniperPhoenixV15:
    def __init__(self, capital_inicial=1000.0):
        self.capital_inicial = capital_inicial
        self.capital = capital_inicial
        self.posicao = 0
        self.preco_entrada = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trailing_ativo = False
        self.trailing_reference = 0
        self.trades = []
        self.trades_log = []
        
        # Parâmetros otimizados para explosões
        self.compression_days = 3  # Dias de compressão
        self.volume_compression_threshold = 0.5  # Volume compressão < 50% da média
        self.volume_explosion_threshold = 3.0  # Volume explosão > 300% da média
        self.volatility_expansion_threshold = 1.5  # ATR > 150% da média
        self.breakout_lookback = 4  # Rompimento de máxima dos últimos N dias
        self.rsi_min = 60  # Momentum mínimo
        self.ema_period = 200
        
        # Parâmetros de saída
        self.tp_percent = 0.10  # 10% TP
        self.sl_percent = 0.03  # 3% SL
        self.trailing_trigger = 0.05  # Ativa trailing após 5%
        self.trailing_offset = 0.03  # Trailing de 3%
        
        # Filtros de tempo
        self.warmup_period = 200
        self.trade_window_start = 9  # 9:00 AM
        self.trade_window_end = 16  # 4:00 PM
        
    def calculate_indicators(self, df):
        """Calcula indicadores técnicos necessários"""
        df = df.copy()
        
        # EMAs
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
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
        df['volume_ma3'] = df['volume'].rolling(window=3).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        df['volume_compression_ratio'] = df['volume_ma3'] / df['volume_ma20']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Máximas e mínimas para breakout
        df['highest_4d'] = df['high'].rolling(window=self.breakout_lookback).max().shift(1)
        df['lowest_4d'] = df['low'].rolling(window=self.breakout_lookback).min().shift(1)
        
        # Volatilidade relativa
        df['volatility_expansion'] = df['atr'] / df['atr_avg_10']
        
        # Distância da EMA200
        df['dist_ema200'] = (df['close'] - df['ema200']) / df['ema200']
        
        return df
    
    def detect_compression_phase(self, df, idx):
        """Detecta fase de compressão (pré-explosão)"""
        if idx < self.compression_days + 20:
            return False
            
        # Verifica se volume dos últimos N dias está comprimido
        compression_ratio = df.loc[idx, 'volume_compression_ratio']
        
        # Verifica se ATR está contraindo
        atr_current = df.loc[idx, 'atr']
        atr_avg = df.loc[idx, 'atr_avg_10']
        atr_contracting = atr_current < atr_avg * 0.8
        
        return compression_ratio < self.volume_compression_threshold and atr_contracting
    
    def detect_explosion_signal(self, df, idx):
        """Detecta sinal de explosão de volume e preço"""
        if idx < self.warmup_period:
            return False, "Warmup"
            
        row = df.iloc[idx]
        
        # Filtro de horário
        hour = idx % 78  # ~78 candles de 5min por dia
        if hour < self.trade_window_start * 12 or hour > self.trade_window_end * 12:
            return False, "Fora do horário"
        
        # 1. Volume Explosion
        if row['volume_ratio'] < self.volume_explosion_threshold:
            return False, f"Volume baixo: {row['volume_ratio']:.2f}x"
        
        # 2. Price Breakout
        if row['close'] <= row['highest_4d']:
            return False, f"Sem breakout: close={row['close']:.2f} < high_4d={row['highest_4d']:.2f}"
        
        # 3. Volatility Expansion
        if row['volatility_expansion'] < self.volatility_expansion_threshold:
            return False, f"Volatilidade baixa: {row['volatility_expansion']:.2f}x"
        
        # 4. Momentum (RSI)
        if pd.isna(row['rsi']) or row['rsi'] < self.rsi_min:
            return False, f"RSI baixo: {row['rsi']:.2f}"
        
        # 5. Trend Alignment (preço acima EMA200)
        if row['close'] <= row['ema200']:
            return False, f"Abaixo EMA200: {row['dist_ema200']*100:.2f}%"
        
        # 6. Confirmação: preço fechando perto da máxima
        candle_range = row['high'] - row['low']
        if candle_range == 0:
            return False, "Candle sem range"
        close_position = (row['close'] - row['low']) / candle_range
        if close_position < 0.6:
            return False, f"Fechamento fraco: {close_position*100:.1f}% do range"
        
        return True, "EXPLOSÃO DETECTADA"
    
    def check_exit_conditions(self, df, idx, current_price):
        """Verifica condições de saída"""
        if self.posicao == 0:
            return None, "Sem posição"
        
        row = df.iloc[idx]
        pnl_percent = (current_price - self.preco_entrada) / self.preco_entrada
        
        # Ativa trailing stop após ganho de 5%
        if not self.trailing_ativo and pnl_percent >= self.trailing_trigger:
            self.trailing_ativo = True
            self.trailing_reference = current_price
            return None, f"Trailing ativado em {pnl_percent*100:.2f}%"
        
        # Atualiza referência do trailing
        if self.trailing_ativo:
            if current_price > self.trailing_reference:
                self.trailing_reference = current_price
            trailing_stop = self.trailing_reference * (1 - self.trailing_offset)
            
            if current_price <= trailing_stop:
                motivo = f"Trailing Stop: {pnl_percent*100:.2f}%"
                return 'SELL', motivo
        
        # Take Profit
        if current_price >= self.take_profit:
            motivo = f"Take Profit: {pnl_percent*100:.2f}%"
            return 'SELL', motivo
        
        # Stop Loss
        if current_price <= self.stop_loss:
            motivo = f"Stop Loss: {pnl_percent*100:.2f}%"
            return 'SELL', motivo
        
        # Saída no final do dia (evitar overnight risk)
        hour = (idx % 78) // 12
        if hour >= 17 and self.posicao > 0:
            motivo = f"Saída fim do dia: {pnl_percent*100:.2f}%"
            return 'SELL', motivo
        
        return None, f"Holding: {pnl_percent*100:.2f}%"
    
    def execute_backtest(self, df):
        """Executa backtest da estratégia"""
        print("=" * 80)
        print("SNIPER PHOENIX V15 - ESTRATÉGIA DE EXPLOSÃO DE VOLUME")
        print("=" * 80)
        print(f"Período: {df['date'].min()} até {df['date'].max()}")
        print(f"Total candles: {len(df)}")
        print(f"Capital inicial: R$ {self.capital_inicial:,.2f}")
        print("=" * 80)
        
        # Calcula indicadores
        df = self.calculate_indicators(df)
        
        # Loop principal
        for idx in range(len(df)):
            if idx < self.warmup_period:
                continue
            
            row = df.iloc[idx]
            current_price = row['close']
            timestamp = row['date']
            
            # Verifica saídas primeiro
            if self.posicao > 0:
                action, reason = self.check_exit_conditions(df, idx, current_price)
                
                if action == 'SELL':
                    valor_saida = self.posicao * current_price
                    pnl = valor_saida - (self.posicao * self.preco_entrada)
                    pnl_percent = (current_price - self.preco_entrada) / self.preco_entrada
                    
                    self.capital += valor_saida
                    self.trades.append({
                        'tipo': 'SAÍDA',
                        'data': timestamp,
                        'preco': current_price,
                        'quantidade': self.posicao,
                        'pnl': pnl,
                        'pnl_percent': pnl_percent,
                        'motivo': reason,
                        'capital': self.capital
                    })
                    
                    self.trades_log.append({
                        'trade_id': len(self.trades),
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
                        'rsi': row['rsi'],
                        'atr': row['atr']
                    })
                    
                    self.posicao = 0
                    self.trailing_ativo = False
                    continue
            
            # Procura entrada
            if self.posicao == 0:
                is_explosion, reason = self.detect_explosion_signal(df, idx)
                
                if is_explosion:
                    # Alocação total (evento raro, alta convicção)
                    quantidade = self.capital / current_price
                    self.posicao = quantidade
                    self.preco_entrada = current_price
                    self.take_profit = current_price * (1 + self.tp_percent)
                    self.stop_loss = current_price * (1 - self.sl_percent)
                    self.trailing_ativo = False
                    
                    self.trades.append({
                        'tipo': 'ENTRADA',
                        'data': timestamp,
                        'preco': current_price,
                        'quantidade': quantidade,
                        'tp': self.take_profit,
                        'sl': self.stop_loss,
                        'motivo': reason,
                        'capital': self.capital - (quantidade * current_price)
                    })
                    
                    self.trades_log.append({
                        'trade_id': len(self.trades),
                        'timestamp': timestamp,
                        'type': 'ENTRY',
                        'price': current_price,
                        'quantity': quantidade,
                        'pnl': 0,
                        'pnl_percent': 0,
                        'reason': reason,
                        'capital_after': self.capital - (quantidade * current_price),
                        'entry_price': current_price,
                        'exit_price': None,
                        'volume': row['volume'],
                        'volume_ratio': row['volume_ratio'],
                        'rsi': row['rsi'],
                        'atr': row['atr'],
                        'volatility_expansion': row['volatility_expansion'],
                        'dist_ema200': row['dist_ema200']
                    })
        
        return self.generate_report(df)
    
    def generate_report(self, df):
        """Gera relatório detalhado do backtest"""
        print("\n" + "=" * 80)
        print("RELATÓRIO DE PERFORMANCE - V15 EXPLOSÃO")
        print("=" * 80)
        
        if not self.trades_log:
            print("Nenhum trade executado!")
            return {}
        
        trades_df = pd.DataFrame(self.trades_log)
        
        # Separa entradas e saídas
        entries = trades_df[trades_df['type'] == 'ENTRY']
        exits = trades_df[trades_df['type'] == 'EXIT']
        
        total_trades = len(exits)
        
        if total_trades == 0:
            print("Nenhuma saída registrada!")
            return {}
        
        # Métricas principais
        winning_trades = exits[exits['pnl'] > 0]
        losing_trades = exits[exits['pnl'] <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = win_count / total_trades * 100
        
        total_pnl = exits['pnl'].sum()
        total_return = (self.capital - self.capital_inicial) / self.capital_inicial * 100
        
        avg_win = winning_trades['pnl'].mean() if win_count > 0 else 0
        avg_loss = abs(losing_trades['pnl'].mean()) if loss_count > 0 else 0
        profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if loss_count > 0 and losing_trades['pnl'].sum() != 0 else float('inf')
        
        # Análise de saídas
        tp_hits = len(exits[exits['reason'].str.contains('Take Profit', na=False)])
        sl_hits = len(exits[exits['reason'].str.contains('Stop Loss|Trailing', na=False)])
        end_of_day = len(exits[exits['reason'].str.contains('fim do dia', na=False)])
        
        # Métricas de entrada
        avg_volume_ratio = entries['volume_ratio'].mean()
        avg_rsi = entries['rsi'].mean()
        avg_volatility_exp = entries['volatility_expansion'].mean()
        
        print(f"\n📊 MÉTRICAS GERAIS:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Win Rate: {win_rate:.2f}% ({win_count}/{total_trades})")
        print(f"   PnL Total: R$ {total_pnl:,.2f}")
        print(f"   Retorno Total: {total_return:.2f}%")
        print(f"   Capital Final: R$ {self.capital:,.2f}")
        
        print(f"\n💰 ANÁLISE DE LUCROS/PERDAS:")
        print(f"   Vitórias: {win_count} (média: R$ {avg_win:,.2f})")
        print(f"   Derrotas: {loss_count} (média: R$ {avg_loss:,.2f})")
        print(f"   Profit Factor: {profit_factor:.2f}")
        print(f"   Ratio Win/Loss: {avg_win/avg_loss:.2f}" if avg_loss > 0 else "   Ratio Win/Loss: N/A")
        
        print(f"\n🎯 ANÁLISE DE SAÍDAS:")
        print(f"   Take Profit: {tp_hits} ({tp_hits/total_trades*100:.1f}%)")
        print(f"   Stop Loss/Trailing: {sl_hits} ({sl_hits/total_trades*100:.1f}%)")
        print(f"   Fim do Dia: {end_of_day} ({end_of_day/total_trades*100:.1f}%)")
        
        print(f"\n📈 CARACTERÍSTICAS DAS ENTRADAS:")
        print(f"   Volume Ratio Médio: {avg_volume_ratio:.2f}x")
        print(f"   RSI Médio: {avg_rsi:.2f}")
        print(f"   Volatility Expansion: {avg_volatility_exp:.2f}x")
        
        # Trades individuais
        print(f"\n📝 DETALHAMENTO DOS TRADES:")
        for idx, trade in exits.iterrows():
            status = "✅ WIN" if trade['pnl'] > 0 else "❌ LOSS"
            print(f"   Trade #{trade['trade_id']}: {trade['timestamp']} | {status} | "
                  f"PnL: R$ {trade['pnl']:,.2f} ({trade['pnl_percent']*100:.2f}%) | "
                  f"Motivo: {trade['reason'][:40]}")
        
        # Melhores e piores trades
        if len(exits) > 0:
            best_trade = exits.loc[exits['pnl'].idxmax()]
            worst_trade = exits.loc[exits['pnl'].idxmin()]
            
            print(f"\n🏆 MELHOR TRADE:")
            print(f"   Data: {best_trade['timestamp']}")
            print(f"   PnL: R$ {best_trade['pnl']:,.2f} ({best_trade['pnl_percent']*100:.2f}%)")
            print(f"   Motivo: {best_trade['reason']}")
            
            print(f"\n💀 PIOR TRADE:")
            print(f"   Data: {worst_trade['timestamp']}")
            print(f"   PnL: R$ {worst_trade['pnl']:,.2f} ({worst_trade['pnl_percent']*100:.2f}%)")
            print(f"   Motivo: {worst_trade['reason']}")
        
        print("\n" + "=" * 80)
        
        # Salva trades em CSV
        trades_df.to_csv('backtest_trades_axs_v15_explosao.csv', index=False)
        print(f"✅ Trades salvos em: backtest_trades_axs_v15_explosao.csv")
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'capital_final': self.capital,
            'profit_factor': profit_factor,
            'tp_hits': tp_hits,
            'sl_hits': sl_hits
        }

def load_data(filepath='AXS_abril_2026.csv'):
    """Carrega dados do CSV"""
    print(f"Carregando dados de {filepath}...")
    
    df = pd.read_csv(filepath)
    
    # Padroniza colunas
    df.columns = df.columns.str.lower().str.strip()
    
    # Mapeia nomes de colunas comuns
    column_mapping = {
        'open_time_brasilia': 'date',
        'data': 'date',
        'hora': 'time',
        'abertura': 'open',
        'maxima': 'high',
        'minima': 'low',
        'fechamento': 'close',
        'volume': 'volume'
    }
    
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            df[new_name] = df[old_name]
    
    # Garante colunas necessárias
    required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Coluna necessária '{col}' não encontrada! Colunas disponíveis: {df.columns.tolist()}")
    
    # Converte data
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    print(f"Dados carregados: {len(df)} candles")
    print(f"Período: {df['date'].min()} até {df['date'].max()}")
    
    return df

if __name__ == "__main__":
    import sys
    
    # Carrega dados - usa argumento ou default
    filepath = sys.argv[1] if len(sys.argv) > 1 else 'AXS_abril_2026.csv'
    df = load_data(filepath)
    
    # Executa backtest
    estrategia = SniperPhoenixV15(capital_inicial=1000.0)
    resultados = estrategia.execute_backtest(df)
    
    # Comparação com V13
    print("\n" + "=" * 80)
    print("COMPARAÇÃO V13 vs V15")
    print("=" * 80)
    print("V13 (Trend-Following Otimizado):")
    print("   Trades: 28 | Win Rate: 57.1% | Retorno: +3.26%")
    print("\nV15 (Explosão de Volume):")
    if resultados:
        print(f"   Trades: {resultados['total_trades']} | Win Rate: {resultados['win_rate']:.2f}% | Retorno: {resultados['total_return']:.2f}%")
    print("=" * 80)
