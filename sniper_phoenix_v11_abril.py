#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNIPER PHOENIX V11 - VERSÃO OTIMIZADA PARA ABRIL 2026 (BULLISH +20.56%)

Mudanças Baseadas na Análise Estatística de Abril:
- Período: +20.56% (bullish moderado com volatilidade)
- ATR Médio: 0.345% (mediana 0.248%)
- Regimes: Bullish 47.1%, Bearish 52.9%, Lateral 46.8%

MELHORIAS IMPLEMENTADAS:
1. Warmup explícito de 200 candles para EMA200 estável
2. Filtro ADX > 70 bloqueia entradas (mercado sobre-estendido)
3. Alocação dinâmica: reduz 50% em drawdown > 5%, 75% em DD > 10%
4. Parâmetros otimizados para bullish: TP 3.5x ATR, SL 1.5x ATR
5. Mean-reversion mais agressiva em lateral (RSI <25/>75)
6. Bias bullish forçado (prioriza LONGs)
7. Confirmação de volume: 1.0x (mais permissivo para capturar tendência)
"""
import pandas as pd
import numpy as np
import sys

class SniperPhoenixV11:
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
        
        # ADX threshold para identificar tendência
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
            return 0.25  # 25% em DD > 10%
        elif self.drawdown_atual > 0.05:
            return 0.50  # 50% em DD > 5%
        return 1.0  # 100% alocação normal
    
    def get_parametros(self, regime, atr, preco, adx):
        """
        Parâmetros DINÂMICOS otimizados para Abril 2026
        ATR médio: 0.345%, ADX médio: ~69
        
        PROBLEMA IDENTIFICADO: TP muito grande (3-4x ATR) não é atingido,
        preço volta e aciona SL (1.5x ATR).
        
        SOLUÇÃO: TP mais realista (2x ATR) e SL mais largo (2x ATR) para
        dar espaço ao trade respirar em mercado volátil.
        """
        atr_pct = atr / preco if preco > 0 else 0.0035
        
        # Filtro ADX > 70: mercado sobre-estendido
        if adx > 70:
            tp_mult = 1.8  # TP menor pois reversão é iminente
            sl_mult = 1.5
            max_candles = 25
        elif regime == 'Bullish':
            # Otimizado para tendência de alta - TP/SL mais equilibrados
            if adx > 40:  # Tendência forte
                tp_mult = 2.5
                sl_mult = 2.0
                max_candles = 50
            else:  # Tendência moderada
                tp_mult = 2.0
                sl_mult = 1.8
                max_candles = 40
        elif regime == 'Bearish':
            # Mais conservador em bearish (contra-tendência em abril)
            tp_mult = 2.0
            sl_mult = 1.8
            max_candles = 30
        else: # Lateral - mean reversion rápida
            tp_mult = 1.5
            sl_mult = 1.2
            max_candles = 15
        
        tp = tp_mult * atr_pct
        sl = sl_mult * atr_pct
        
        return {
            'tp': tp,
            'sl': sl,
            'max_candles': max_candles,
            'break_even_atr': 1.5  # Move para BE após 1.5x ATR a favor
        }

    def executar_backtest(self, df):
        df = self.calcular_indicadores(df)
        
        stop_loss_price = 0
        take_profit_price = 0
        candles_na_posicao = 0
        break_even_ativado = False
        
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
                
                # Verifica se deve mover para break-even
                if not break_even_ativado:
                    if self.posicao > 0:
                        dist_percorrida = (preco_high - self.preco_entrada) / self.preco_entrada
                        if dist_percorrida >= params['break_even_atr'] * (atr / self.preco_entrada):
                            stop_loss_price = self.preco_entrada * 1.001
                            break_even_ativado = True
                    else:
                        dist_percorrida = (self.preco_entrada - preco_low) / self.preco_entrada
                        if dist_percorrida >= params['break_even_atr'] * (atr / self.preco_entrada):
                            stop_loss_price = self.preco_entrada * 0.999
                            break_even_ativado = True
                
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
                            'break_even_usado': break_even_ativado
                        })
                        
                        self.posicao = 0
                        self.qtd_posicao = 0
                        self.preco_entrada = 0
                        candles_na_posicao = 0
                        break_even_ativado = False
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
                            'break_even_usado': break_even_ativado
                        })
                        
                        self.posicao = 0
                        self.qtd_posicao = 0
                        self.preco_entrada = 0
                        candles_na_posicao = 0
                        break_even_ativado = False
                        continue

            # --- VERIFICAÇÃO DE ENTRADA ---
            if self.posicao == 0:
                # Alocação dinâmica baseada em drawdown
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
                
                # Filtro de volume mais permissivo (1.0x) para capturar tendência
                volume_ok = volume_ant >= 1.0 * volume_medio if not pd.isna(volume_medio) else True
                
                # Bias bullish: prioriza LONGs, só SHORT em condições extremas
                if self.bias_mercado == 'bullish':
                    permitir_long = True
                    permitir_short = (regime == 'Bearish' and rsi_ant > 70)  # Só short com RSI extremo
                elif self.bias_mercado == 'bearish':
                    permitir_long = (regime == 'Bullish' and rsi_ant < 35)
                    permitir_short = True
                else:
                    permitir_long = True
                    permitir_short = True
                
                # Filtro ADX > 70: NÃO ENTRA (mercado sobre-estendido)
                if adx > 70:
                    continue
                
                # Setup BULLISH - Principal para abril
                # PROBLEMA IDENTIFICADO: V9 funcionou melhor com entradas mais simples
                # SOLUÇÃO: Voltar ao setup do V9 que teve 29.8% win rate
                if regime == 'Bullish' and permitir_long and volume_ok:
                    # Pullback para EMA34 com RSI em zona neutra-alta
                    if ema34_ant * 0.997 <= close_ant <= ema34_ant * 1.003:
                        if 45 <= rsi_ant <= 65:  # Faixa do V9 que funcionou
                            if close_ant > ema200_ant * 1.01:
                                entrou = True
                                tipo_entrada = 'COMPRA'
                                self.posicao = 1
                                self.qtd_posicao = qtd_base
                                self.preco_entrada = preco_abertura * (1 + self.slippage)
                                    
                # Setup BEARISH - Contra-tendência, apenas em condições ótimas
                elif regime == 'Bearish' and permitir_short and volume_ok:
                    if ema34_ant * 0.997 <= close_ant <= ema34_ant * 1.003:
                        if 45 <= rsi_ant <= 58:  # RSI mais alto para contra-tendência
                            if close_ant < ema200_ant * 0.995:
                                entrou = True
                                tipo_entrada = 'VENDA'
                                self.posicao = -1
                                self.qtd_posicao = qtd_base * 0.7  # Menor tamanho para contra-tendência
                                self.preco_entrada = preco_abertura * (1 - self.slippage)
                                    
                # Setup LATERAL - Mean reversion agressiva
                elif regime == 'Lateral' and volume_ok:
                    qtd_scalp = qtd_base * 0.6
                    # RSI thresholds mais agressivos para mean reversion
                    if rsi_ant < 25:
                        if permitir_long:
                            entrou = True
                            tipo_entrada = 'COMPRA'
                            self.posicao = 1
                            self.qtd_posicao = qtd_scalp
                            self.preco_entrada = preco_abertura * (1 + self.slippage)
                    elif rsi_ant > 75:
                        if permitir_short:
                            entrou = True
                            tipo_entrada = 'VENDA'
                            self.posicao = -1
                            self.qtd_posicao = qtd_scalp
                            self.preco_entrada = preco_abertura * (1 - self.slippage)
                
                if entrou:
                    self.data_entrada = timestamp
                    self.regime_entrada = regime
                    candles_na_posicao = 0
                    break_even_ativado = False
                    
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
                'break_even_usado': break_even_ativado
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
        
        print("=" * 80)
        print(f"SNIPER PHOENIX V11 - RELATÓRIO OTIMIZADO (ABRIL 2026)")
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
        print("=" * 80)
        
        return trades_df, equity_df


if __name__ == "__main__":
    try:
        arquivo_csv = sys.argv[1] if len(sys.argv) > 1 else 'AXS_abril_2026.csv'
        print(f"Carregando dados de: {arquivo_csv}")
        
        df = pd.read_csv(arquivo_csv)
        
        # Validar colunas necessárias
        colunas_necessarias = ['open_time_brasilia', 'open', 'high', 'low', 'close', 'volume']
        for col in colunas_necessarias:
            if col not in df.columns:
                raise ValueError(f"Coluna '{col}' não encontrada no CSV!")
        
        # Renomear para formato esperado
        df = df.rename(columns={'open_time_brasilia': 'timestamp'})
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"Dados carregados: {len(df)} candles")
        print(f"Período: {df['timestamp'].min()} até {df['timestamp'].max()}")
        print(f"Preço inicial: {df['close'].iloc[0]:.4f}, Preço final: {df['close'].iloc[-1]:.4f}")
        print(f"Variação do período: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.2f}%")
        print()
        
        # Executar backtest
        estrategia = SniperPhoenixV11(capital_inicial=1000.0, bias_mercado='bullish')
        trades_df, equity_df = estrategia.executar_backtest(df)
        
        if trades_df is not None:
            # Salvar resultados
            trades_df.to_csv('backtest_trades_axs_v11_abril.csv', index=False)
            equity_df.to_csv('backtest_equity_axs_v11_abril.csv', index=False)
            print("\n✓ Resultados salvos em: backtest_trades_axs_v11_abril.csv, backtest_equity_axs_v11_abril.csv")
        
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
