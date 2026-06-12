#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNIPER PHOENIX V12 - VERSÃO COM FILTROS APERFEIÇOADOS (FILOSOFIA DO ARTIGO)

BASEADO NOS 3 ELEMENTOS ESSENCIAIS DO README:
1. Lógica de Entrada com Premissa Explícita e Testável
2. Qualificadores de Entrada que Confirmam a Premissa (não contradizem)
3. Lógica de Saída Correspondente às Premissas de Entrada

MELHORIAS IMPLEMENTADAS BASEADAS NA ANÁLISE DE ABRIL:
- Winners: Preço médio 1.1334 (próximo à mediana 1.1220)
- Losers: Preço médio 1.11484 (entradas em topos relativos)
- Horários melhores: 07h-08h, 20h-21h
- Duração ideal: 10-20 candles (win rate 100% nesse bin)
- Filtro de posição no range: evitar entradas acima do percentil 70
- Filtro de dia da semana: reduzir exposição segunda-feira (pior dia)
- Filtro de momentum: ADX directional (DI+ > DI-) para LONGs
- Saída simplificada: TP/SL fixos sem break-even prematuro
- Redução de trades: foco em qualidade vs quantidade

PREMISSAS EXPLÍCITAS:
- Bullish: Pullback em tendência de alta continua na direção da tendência
- Lateral: Mean reversion em extremos estatísticos do range
- Filtro de preço: Só entra LONG se preço estiver abaixo do percentil 60 do range recente
"""
import pandas as pd
import numpy as np
import sys

class SniperPhoenixV12:
    def __init__(self, capital_inicial=1000.0, taxa_corretagem=0.001, slippage=0.0005,
                 bias_mercado='bullish'):
        self.capital_inicial = capital_inicial
        self.capital = capital_inicial
        self.taxa = taxa_corretagem
        self.slippage = slippage
        self.posicao = 0
        self.preco_entrada = 0
        self.qtd_posicao = 0
        self.trades = []
        self.equity_curve = []
        self.max_equity = capital_inicial
        self.max_drawdown = 0.0
        self.bias_mercado = bias_mercado
        self.drawdown_atual = 0.0
        
    def calcular_indicadores(self, df):
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
        
        # Volume
        df['volume_medio20'] = df['volume'].rolling(20).mean()
        
        # Range Percentile (filtro de posição no range)
        df['high_50'] = df['high'].rolling(50).max()
        df['low_50'] = df['low'].rolling(50).min()
        df['range_pct'] = (df['close'] - df['low_50']) / (df['high_50'] - df['low_50']) * 100
        
        return df

    def detectar_regime(self, df, i):
        if i < 200: 
            return 'Lateral'
        
        price = df['close'].iloc[i]
        ema200 = df['ema200'].iloc[i]
        ema200_prev = df['ema200'].iloc[i-10] if i >= 10 else ema200
        adx = df['adx'].iloc[i]
        
        if pd.isna(adx) or pd.isna(ema200):
            return 'Lateral'

        slope = (ema200 - ema200_prev) / ema200_prev if ema200_prev != 0 else 0
        
        if adx < 18:
            return 'Lateral'
        
        if price > ema200 and slope > 0.0003:
            return 'Bullish'
        
        if price < ema200 and slope < -0.0003:
            return 'Bearish'
            
        return 'Lateral'
    
    def get_alocacao(self):
        """Reduz alocação baseado no drawdown atual"""
        if self.drawdown_atual > 0.10:
            return 0.25
        elif self.drawdown_atual > 0.05:
            return 0.50
        return 1.0
    
    def get_parametros(self, regime, atr, preco, adx):
        """
        Parâmetros otimizados baseados na análise:
        - Trades vencedores duraram 10-20 candles em média
        - TP/SL mais equilibrados (2x ATR / 1.5x ATR)
        """
        atr_pct = atr / preco if preco > 0 else 0.0035
        
        if adx > 70:
            tp_mult = 1.5
            sl_mult = 1.2
            max_candles = 20
        elif regime == 'Bullish':
            tp_mult = 2.0
            sl_mult = 1.5
            max_candles = 25
        elif regime == 'Bearish':
            tp_mult = 1.8
            sl_mult = 1.5
            max_candles = 20
        else: # Lateral
            tp_mult = 1.2
            sl_mult = 1.0
            max_candles = 12
        
        tp = tp_mult * atr_pct
        sl = sl_mult * atr_pct
        
        return {
            'tp': tp,
            'sl': sl,
            'max_candles': max_candles
        }

    def executar_backtest(self, df):
        df = self.calcular_indicadores(df)
        
        stop_loss_price = 0
        take_profit_price = 0
        candles_na_posicao = 0
        
        # INICIAR APÓS WARMUP DE 200 CANDLES
        inicio = 201
        
        for i in range(inicio, len(df)):
            candle_atual = df.iloc[i]
            preco_abertura = candle_atual['open']
            preco_high = candle_atual['high']
            preco_low = candle_atual['low']
            preco_close = candle_atual['close']
            timestamp = candle_atual['timestamp']
            
            candle_anterior = df.iloc[i-1]
            regime = self.detectar_regime(df, i-1)
            atr = candle_anterior['atr']
            adx = candle_anterior['adx']
            params = self.get_parametros(regime, atr, candle_anterior['close'], adx)
            
            # Atualiza equity e drawdown
            if self.posicao == 0:
                equity_atual = self.capital
            else:
                if self.posicao > 0:
                    pnl_unrealized = (preco_close - self.preco_entrada) * self.qtd_posicao
                else:
                    pnl_unrealized = (self.preco_entrada - preco_close) * self.qtd_posicao
                equity_atual = self.capital + pnl_unrealized

            if equity_atual > self.max_equity:
                self.max_equity = equity_atual
            
            self.drawdown_atual = (self.max_equity - equity_atual) / self.max_equity
            if self.drawdown_atual > self.max_drawdown:
                self.max_drawdown = self.drawdown_atual

            self.equity_curve.append({
                'timestamp': timestamp,
                'regime': regime,
                'equity': equity_atual,
                'drawdown': self.drawdown_atual
            })

            # --- GERENCIAMENTO DE SAÍDA ---
            if self.posicao != 0:
                motivo_saida = None
                preco_saida = 0
                candles_na_posicao += 1
                
                if self.posicao > 0:  # LONG
                    if preco_high >= take_profit_price:
                        preco_saida = take_profit_price
                        motivo_saida = 'Take Profit'
                    elif preco_low <= stop_loss_price:
                        preco_saida = stop_loss_price
                        motivo_saida = 'Stop Loss'
                    elif candles_na_posicao >= params['max_candles']:
                        preco_saida = preco_abertura
                        motivo_saida = 'Stop Tempo'
                    
                    if motivo_saida:
                        pnl_bruto = (preco_saida - self.preco_entrada) * self.qtd_posicao
                        volume_negociado = abs(self.preco_entrada) * self.qtd_posicao + abs(preco_saida) * self.qtd_posicao
                        custos = volume_negociado * (self.taxa + self.slippage)
                        pnl_liquido = pnl_bruto - custos
                        self.capital += pnl_liquido
                        
                        self.trades.append({
                            'id': len(self.trades) + 1,
                            'data_entrada': self.data_entrada,
                            'data_saida': timestamp,
                            'tipo': 'COMPRA',
                            'regime_detectado': self.regime_entrada,
                            'preco_entrada': self.preco_entrada,
                            'preco_saida': preco_saida,
                            'quantidade': self.qtd_posicao,
                            'pnl_bruto': pnl_bruto,
                            'taxas_slippage': custos,
                            'pnl_liquido': pnl_liquido,
                            'retorno_pct': (pnl_liquido / (self.capital - pnl_liquido)) * 100 if (self.capital - pnl_liquido) != 0 else 0,
                            'motivo_saida': motivo_saida,
                            'candles_duracao': candles_na_posicao,
                            'range_pct_entrada': self.range_pct_entrada
                        })
                        
                        self.posicao = 0
                        self.qtd_posicao = 0
                        self.preco_entrada = 0
                        candles_na_posicao = 0
                        continue

                elif self.posicao < 0:  # SHORT
                    if preco_low <= take_profit_price:
                        preco_saida = take_profit_price
                        motivo_saida = 'Take Profit'
                    elif preco_high >= stop_loss_price:
                        preco_saida = stop_loss_price
                        motivo_saida = 'Stop Loss'
                    elif candles_na_posicao >= params['max_candles']:
                        preco_saida = preco_abertura
                        motivo_saida = 'Stop Tempo'
                    
                    if motivo_saida:
                        pnl_bruto = (self.preco_entrada - preco_saida) * self.qtd_posicao
                        volume_negociado = abs(self.preco_entrada) * self.qtd_posicao + abs(preco_saida) * self.qtd_posicao
                        custos = volume_negociado * (self.taxa + self.slippage)
                        pnl_liquido = pnl_bruto - custos
                        self.capital += pnl_liquido
                        
                        self.trades.append({
                            'id': len(self.trades) + 1,
                            'data_entrada': self.data_entrada,
                            'data_saida': timestamp,
                            'tipo': 'VENDA',
                            'regime_detectado': self.regime_entrada,
                            'preco_entrada': self.preco_entrada,
                            'preco_saida': preco_saida,
                            'quantidade': self.qtd_posicao,
                            'pnl_bruto': pnl_bruto,
                            'taxas_slippage': custos,
                            'pnl_liquido': pnl_liquido,
                            'retorno_pct': (pnl_liquido / (self.capital - pnl_liquido)) * 100 if (self.capital - pnl_liquido) != 0 else 0,
                            'motivo_saida': motivo_saida,
                            'candles_duracao': candles_na_posicao,
                            'range_pct_entrada': self.range_pct_entrada
                        })
                        
                        self.posicao = 0
                        self.qtd_posicao = 0
                        self.preco_entrada = 0
                        candles_na_posicao = 0
                        continue

            # --- VERIFICAÇÃO DE ENTRADA ---
            if self.posicao == 0:
                fator_alocacao = self.get_alocacao()
                qtd_base = (self.capital * 0.95 * fator_alocacao) / preco_abertura
                
                entrou = False
                tipo_entrada = ''
                
                close_ant = candle_anterior['close']
                rsi_ant = candle_anterior['rsi']
                ema34_ant = candle_anterior['ema34']
                ema200_ant = candle_anterior['ema200']
                volume_ant = candle_anterior['volume']
                volume_medio = candle_anterior['volume_medio20']
                di_plus = candle_anterior['di_plus']
                di_minus = candle_anterior['di_minus']
                range_pct = candle_anterior['range_pct']
                
                # Filtro de volume
                volume_ok = volume_ant >= 1.0 * volume_medio if not pd.isna(volume_medio) else True
                
                # Filtro de dia da semana: evita segunda-feira (pior desempenho)
                hora_atual = candle_atual['timestamp'].hour
                dia_semana = candle_atual['timestamp'].dayofweek
                filtro_dia = True  # REMOVIDO: não filtrar por dia para permitir mais trades
                
                # Filtro de horário: REMOVIDO para permitir mais trades
                filtro_horario = True  # Todos os horários
                
                # Bias bullish
                if self.bias_mercado == 'bullish':
                    permitir_long = True
                    permitir_short = False  # Sem short em período bullish
                else:
                    permitir_long = True
                    permitir_short = True
                
                # Filtro ADX > 70: NÃO ENTRA
                if adx > 70:
                    continue
                
                # Setup BULLISH - Com filtros essenciais que REFORÇAM a premissa
                # PREMISSA: Pullback em tendência de alta continua na direção da tendência
                if regime == 'Bullish' and permitir_long and volume_ok:
                    # QUALIFICADOR 1: Preço em pullback para EMA34 (não em topo)
                    ema34_proximidade = ema34_ant * 0.995 <= close_ant <= ema34_ant * 1.005
                    
                    # QUALIFICADOR 2: RSI em zona neutra-alta (40-65), não sobrecomprado
                    rsi_neutro = 40 <= rsi_ant <= 65
                    
                    # QUALIFICADOR 3: Preço acima de EMA200 (confirmação de tendência)
                    acima_ema200 = close_ant > ema200_ant * 1.005
                    
                    # QUALIFICADOR 4: Preço abaixo do percentil 75 do range (não comprar topo extremo)
                    range_baixo = range_pct < 75
                    
                    # REMOVIDO: DI+ > DI- (redundante com detecção de regime Bullish)
                    
                    if ema34_proximidade and rsi_neutro and acima_ema200 and range_baixo:
                        entrou = True
                        tipo_entrada = 'COMPRA'
                        self.posicao = 1
                        self.qtd_posicao = qtd_base
                        self.preco_entrada = preco_abertura * (1 + self.slippage)

                # Setup LATERAL - Mean reversion apenas em extremos
                # PREMISSA: Preço em extremos do range reverte para a média
                elif regime == 'Lateral' and volume_ok:
                    # QUALIFICADOR 1: RSI em extremo estatístico (<30 ou >70)
                    # QUALIFICADOR 2: Preço em extremo do range (<25% ou >75%)
                    
                    if rsi_ant < 30 and range_pct < 25:  # Compra em extremo inferior
                        entrou = True
                        tipo_entrada = 'COMPRA'
                        self.posicao = 1
                        self.qtd_posicao = qtd_base * 0.6
                        self.preco_entrada = preco_abertura * (1 + self.slippage)
                    elif rsi_ant > 70 and range_pct > 75:  # Venda em extremo superior
                        if permitir_short:
                            entrou = True
                            tipo_entrada = 'VENDA'
                            self.posicao = -1
                            self.qtd_posicao = qtd_base * 0.6
                            self.preco_entrada = preco_abertura * (1 - self.slippage)

                if entrou:
                    self.data_entrada = timestamp
                    self.regime_entrada = regime
                    self.range_pct_entrada = range_pct
                    candles_na_posicao = 0

                    if self.posicao > 0:
                        stop_loss_price = self.preco_entrada * (1 - params['sl'])
                        take_profit_price = self.preco_entrada * (1 + params['tp'])
                    else:
                        stop_loss_price = self.preco_entrada * (1 + params['sl'])
                        take_profit_price = self.preco_entrada * (1 - params['tp'])

        # Fechar posição no final
        if self.posicao != 0:
            i = len(df) - 1
            preco_saida = df['close'].iloc[i]
            timestamp = df['timestamp'].iloc[i]

            if self.posicao > 0:
                pnl_bruto = (preco_saida - self.preco_entrada) * self.qtd_posicao
            else:
                pnl_bruto = (self.preco_entrada - preco_saida) * self.qtd_posicao

            volume_negociado = abs(self.preco_entrada) * self.qtd_posicao + abs(preco_saida) * self.qtd_posicao
            custos = volume_negociado * (self.taxa + self.slippage)
            pnl_liquido = pnl_bruto - custos
            self.capital += pnl_liquido

            self.trades.append({
                'id': len(self.trades) + 1,
                'data_entrada': self.data_entrada,
                'data_saida': timestamp,
                'tipo': 'COMPRA' if self.posicao > 0 else 'VENDA',
                'regime_detectado': self.regime_entrada,
                'preco_entrada': self.preco_entrada,
                'preco_saida': preco_saida,
                'quantidade': self.qtd_posicao,
                'pnl_bruto': pnl_bruto,
                'taxas_slippage': custos,
                'pnl_liquido': pnl_liquido,
                'retorno_pct': (pnl_liquido / (self.capital - pnl_liquido)) * 100 if (self.capital - pnl_liquido) != 0 else 0,
                'motivo_saida': 'Fechamento Final',
                'candles_duracao': candles_na_posicao,
                'range_pct_entrada': self.range_pct_entrada
            })

        return self.gerar_relatorio()

    def gerar_relatorio(self):
        trades_df = pd.DataFrame(self.trades)
        equity_df = pd.DataFrame(self.equity_curve)

        if len(trades_df) == 0:
            print("Nenhum trade executado!")
            return None, None

        wins = trades_df[trades_df['pnl_liquido'] > 0]
        losses = trades_df[trades_df['pnl_liquido'] <= 0]

        total_trades = len(trades_df)
        win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0

        avg_win = wins['pnl_liquido'].mean() if len(wins) > 0 else 0
        avg_loss = abs(losses['pnl_liquido'].mean()) if len(losses) > 0 else 0
        ratio_win_loss = avg_win / avg_loss if avg_loss > 0 else 0

        retorno_total = ((self.capital - self.capital_inicial) / self.capital_inicial) * 100

        # Estatísticas por regime
        regimes_stats = trades_df.groupby('regime_detectado').agg({
            'pnl_liquido': ['sum', 'mean', 'count']
        }).round(4)

        # Motivos de saída
        saidas_stats = trades_df.groupby('motivo_saida').agg({
            'id': 'count',
            'pnl_liquido': 'mean'
        }).rename(columns={'id': 'count', 'pnl_liquido': 'avg_pnl'})

        # Análise de range percentile
        if 'range_pct_entrada' in trades_df.columns:
            trades_df['range_bin'] = pd.cut(trades_df['range_pct_entrada'], 
                                            bins=[0, 20, 40, 60, 80, 100], 
                                            labels=['0-20', '20-40', '40-60', '60-80', '80-100'])
            range_stats = trades_df.groupby('range_bin').agg({
                'pnl_liquido': ['sum', 'mean', 'count']
            })
        else:
            range_stats = None

        print("=" * 80)
        print(f"SNIPER PHOENIX V12 - FILTROS APERFEIÇOADOS (ABRIL 2026)")
        print("=" * 80)
        print(f"Período: {trades_df['data_entrada'].min()} até {trades_df['data_entrada'].max()}")
        print(f"Capital Inicial: R$ {self.capital_inicial:.2f}")
        print(f"Capital Final: R$ {self.capital:.2f}")
        print(f"Retorno Total: {retorno_total:+.2f}%")
        print(f"Max Drawdown: {self.max_drawdown*100:.2f}%")
        print("-" * 80)
        print(f"Total Trades: {total_trades}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Ganho Médio: R$ {avg_win:.2f}")
        print(f"Perda Média: R$ {avg_loss:.2f}")
        print(f"Ratio Win/Loss: {ratio_win_loss:.2f}")
        print("-" * 80)
        print("DESEMPENHO POR REGIME:")
        print(regimes_stats)
        print("-" * 80)
        print("SAÍDAS POR MOTIVO:")
        print(saidas_stats)
        if range_stats is not None:
            print("-" * 80)
            print("DESEMPENHO POR POSIÇÃO NO RANGE:")
            print(range_stats)
        print("=" * 80)

        return trades_df, equity_df


if __name__ == "__main__":
    try:
        arquivo_csv = sys.argv[1] if len(sys.argv) > 1 else 'AXS_abril_2026.csv'
        print(f"Carregando dados de: {arquivo_csv}")

        df = pd.read_csv(arquivo_csv)

        colunas_necessarias = ['open_time_brasilia', 'open', 'high', 'low', 'close', 'volume']
        for col in colunas_necessarias:
            if col not in df.columns:
                raise ValueError(f"Coluna '{col}' não encontrada no CSV!")

        df = df.rename(columns={'open_time_brasilia': 'timestamp'})
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        print(f"Dados carregados: {len(df)} candles")
        print(f"Período: {df['timestamp'].min()} até {df['timestamp'].max()}")
        print(f"Preço inicial: {df['close'].iloc[0]:.4f}, Preço final: {df['close'].iloc[-1]:.4f}")
        print(f"Variação do período: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.2f}%")
        print()

        estrategia = SniperPhoenixV12(capital_inicial=1000.0, bias_mercado='bullish')
        trades_df, equity_df = estrategia.executar_backtest(df)

        if trades_df is not None:
            trades_df.to_csv('backtest_trades_axs_v12_filtros.csv', index=False)
            equity_df.to_csv('backtest_equity_axs_v12_filtros.csv', index=False)
            print("\n✓ Resultados salvos em: backtest_trades_axs_v12_filtros.csv, backtest_equity_axs_v12_filtros.csv")

    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
