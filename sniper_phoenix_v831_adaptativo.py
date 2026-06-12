#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import sys
import os

class SniperPhoenixAdaptativo:
    def __init__(self, capital_inicial=1000.0, taxa_corretagem=0.001, slippage=0.0005):
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
        
        # ATR (Volatilidade)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # ADX (Força da Tendência)
        df['dm_plus'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']), 
                                 np.maximum(0, df['high'] - df['high'].shift()), 0)
        df['dm_minus'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()), 
                                  np.maximum(0, df['low'].shift() - df['low']), 0)
        df['tr'] = true_range
        df['atr_adx'] = df['tr'].rolling(14).mean()
        
        # Evitar divisão por zero
        df['di_plus'] = np.where(df['atr_adx'] != 0, 100 * (df['dm_plus'] / df['atr_adx']), 0)
        df['di_minus'] = np.where(df['atr_adx'] != 0, 100 * (df['dm_minus'] / df['atr_adx']), 0)
        
        df['dx'] = np.where((df['di_plus'] + df['di_minus']) != 0, 
                            100 * np.abs(df['di_plus'] - df['di_minus']) / (df['di_plus'] + df['di_minus']), 0)
        df['adx'] = df['dx'].rolling(14).mean()
        
        return df

    def detectar_regime(self, df, i):
        if i < 200: return 'Lateral'
        
        price = df['close'].iloc[i]
        ema200 = df['ema200'].iloc[i]
        # Comparação com 10 períodos atrás para inclinação
        ema200_prev = df['ema200'].iloc[i-10]
        adx = df['adx'].iloc[i]
        
        if pd.isna(adx) or pd.isna(ema200):
            return 'Lateral'

        slope = (ema200 - ema200_prev) / ema200_prev if ema200_prev != 0 else 0
        
        if adx < 20:
            return 'Lateral'
        
        if price > ema200 and slope > 0.0005:
            return 'Bullish'
        
        if price < ema200 and slope < -0.0005:
            return 'Bearish'
            
        return 'Lateral'

    def get_parametros(self, regime):
        if regime == 'Bullish':
            return {'tp': 0.045, 'sl': 0.015, 'trail_atr_mult': 1.0, 'strat': 'pullback_long'}
        elif regime == 'Bearish':
            return {'tp': 0.035, 'sl': 0.015, 'trail_atr_mult': 1.0, 'strat': 'pullback_short'}
        else: # Lateral
            return {'tp': 0.020, 'sl': 0.010, 'trail_atr_mult': 0.8, 'strat': 'mean_rev'}

    def executar_backtest(self, df):
        df = self.calcular_indicadores(df)
        
        # Variáveis de controle de posição
        stop_loss_price = 0
        take_profit_price = 0
        trailing_stop_price = 0
        max_price_since_entry = 0
        min_price_since_entry = float('inf')
        
        # Loop começa em 201 para garantir indicadores calculados e evitar lookahead
        # A lógica é: Analisa o fechamento do candle i-1, Entra na abertura do candle i
        for i in range(201, len(df)):
            # Dados do candle ATUAL (onde vamos entrar ou gerenciar)
            candle_atual = df.iloc[i]
            preco_abertura = candle_atual['open']
            preco_high = candle_atual['high']
            preco_low = candle_atual['low']
            preco_close = candle_atual['close']
            timestamp = candle_atual['timestamp']
            
            # Dados do candle ANTERIOR (onde o sinal foi gerado)
            candle_anterior = df.iloc[i-1]
            regime = self.detectar_regime(df, i-1) # Detecta regime no fechamento anterior
            params = self.get_parametros(regime)
            atr = candle_anterior['atr'] # Usa ATR do fechamento anterior para definir stops
            
            # Atualiza Equity antes de qualquer ação
            valor_mercado = 0
            if self.posicao > 0:
                valor_mercado = self.qtd_posicao * preco_close
            elif self.posicao < 0:
                valor_mercado = self.capital + (self.qtd_posicao * (self.preco_entrada - preco_close)) # Simplificação para short
            
            if self.posicao == 0:
                equity_atual = self.capital
            else:
                # Calculo PnL não realizado simples
                if self.posicao > 0:
                    pnl_unrealized = (preco_close - self.preco_entrada) * self.qtd_posicao
                else:
                    pnl_unrealized = (self.preco_entrada - preco_close) * self.qtd_posicao
                equity_atual = self.capital + pnl_unrealized

            if equity_atual > self.max_equity:
                self.max_equity = equity_atual
            
            drawdown_atual = (self.max_equity - equity_atual) / self.max_equity
            if drawdown_atual > self.max_drawdown:
                self.max_drawdown = drawdown_atual

            self.equity_curve.append({
                'timestamp': timestamp,
                'regime': regime,
                'equity': equity_atual,
                'drawdown': drawdown_atual
            })

            # --- GERENCIAMENTO DE SAÍDA (Se estiver posicionado) ---
            if self.posicao != 0:
                motivo_saida = None
                preco_saida = 0
                
                # Atualiza extremos para Trailing Stop
                if self.posicao > 0:
                    if preco_high > max_price_since_entry:
                        max_price_since_entry = preco_high
                        # Recalcula Trailing Stop para Long
                        trailing_stop_price = max_price_since_entry * (1 - params['trail_atr_mult'] * (atr / max_price_since_entry))
                    
                    # Verifica Stops
                    if preco_low <= stop_loss_price:
                        preco_saida = stop_loss_price
                        motivo_saida = 'Stop Loss'
                    elif preco_high >= take_profit_price:
                        preco_saida = take_profit_price
                        motivo_saida = 'Take Profit'
                    elif preco_low <= trailing_stop_price:
                        preco_saida = trailing_stop_price
                        motivo_saida = 'Trailing Stop'

                elif self.posicao < 0: # Short
                    if preco_low < min_price_since_entry:
                        min_price_since_entry = preco_low
                        # Recalcula Trailing Stop para Short
                        trailing_stop_price = min_price_since_entry * (1 + params['trail_atr_mult'] * (atr / min_price_since_entry))
                    
                    if preco_high >= stop_loss_price:
                        preco_saida = stop_loss_price
                        motivo_saida = 'Stop Loss'
                    elif preco_low <= take_profit_price:
                        preco_saida = take_profit_price
                        motivo_saida = 'Take Profit'
                    elif preco_high >= trailing_stop_price:
                        preco_saida = trailing_stop_price
                        motivo_saida = 'Trailing Stop'

                if motivo_saida:
                    # Executa Saída
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
                        'motivo_saida': motivo_saida
                    })
                    
                    # Reseta posição
                    self.posicao = 0
                    self.qtd_posicao = 0
                    self.preco_entrada = 0
                    max_price_since_entry = 0
                    min_price_since_entry = float('inf')
                    continue # Pula a entrada neste candle se saiu

            # --- VERIFICAÇÃO DE ENTRADA (Se estiver zerado) ---
            if self.posicao == 0:
                # Usa 95% do capital para margem de segurança
                qtd_base = (self.capital * 0.95) / preco_abertura 
                
                entrou = False
                tipo_entrada = ''
                
                # Condições baseadas no fechamento ANTERIOR (i-1)
                close_ant = candle_anterior['close']
                rsi_ant = candle_anterior['rsi']
                ema34_ant = candle_anterior['ema34']
                
                if regime == 'Bullish' and params['strat'] == 'pullback_long':
                    # Pullback na EMA34 + RSI saudável no fechamento anterior
                    if ema34_ant * 0.995 <= close_ant <= ema34_ant * 1.005:
                        if 40 <= rsi_ant <= 65:
                            entrou = True
                            tipo_entrada = 'COMPRA'
                            self.posicao = 1
                            self.qtd_posicao = qtd_base
                            # Entrada na ABERTURA do candle atual
                            self.preco_entrada = preco_abertura * (1 + self.slippage)
                            
                elif regime == 'Bearish' and params['strat'] == 'pullback_short':
                    # Pullback na EMA34 (resistência) + RSI
                    if ema34_ant * 0.995 <= close_ant <= ema34_ant * 1.005:
                        if 35 <= rsi_ant <= 60:
                            entrou = True
                            tipo_entrada = 'VENDA'
                            self.posicao = -1
                            self.qtd_posicao = qtd_base
                            self.preco_entrada = preco_abertura * (1 - self.slippage)
                            
                elif regime == 'Lateral' and params['strat'] == 'mean_rev':
                    qtd_scalp = qtd_base * 0.5
                    if rsi_ant < 30:
                        entrou = True
                        tipo_entrada = 'COMPRA'
                        self.posicao = 1
                        self.qtd_posicao = qtd_scalp
                        self.preco_entrada = preco_abertura * (1 + self.slippage)
                    elif rsi_ant > 70:
                        entrou = True
                        tipo_entrada = 'VENDA'
                        self.posicao = -1
                        self.qtd_posicao = qtd_scalp
                        self.preco_entrada = preco_abertura * (1 - self.slippage)
                
                if entrou:
                    self.data_entrada = timestamp
                    self.regime_entrada = regime
                    
                    # Define Stops Iniciais baseados na abertura + ATR anterior
                    if self.posicao > 0:
                        stop_loss_price = self.preco_entrada * (1 - params['sl'])
                        take_profit_price = self.preco_entrada * (1 + params['tp'])
                        max_price_since_entry = self.preco_entrada
                        trailing_stop_price = self.preco_entrada * (1 - params['trail_atr_mult'] * (atr / self.preco_entrada))
                    else:
                        stop_loss_price = self.preco_entrada * (1 + params['sl'])
                        take_profit_price = self.preco_entrada * (1 - params['tp'])
                        min_price_since_entry = self.preco_entrada
                        trailing_stop_price = self.preco_entrada * (1 + params['trail_atr_mult'] * (atr / self.preco_entrada))

        # Fechar posição aberta no final do período
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
                'retorno_pct': 0,
                'motivo_saida': 'Fim Periodo'
            })

        return df

def main():
    arquivo_dados = 'AXSUSDT_2026-05-11_2026-06-12_5m.csv'
    
    if not os.path.exists(arquivo_dados):
        print(f"Erro: Arquivo '{arquivo_dados}' não encontrado.")
        print("Por favor, baixe o arquivo do GitHub e coloque na mesma pasta deste script.")
        return

    print(f"Carregando dados de {arquivo_dados}...")
    try:
        df = pd.read_csv(arquivo_dados)
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return
    
    # Mapeamento correto das colunas do seu CSV específico
    col_map = {
        'open_time_brasilia': 'timestamp',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'volume'
    }
    
    # Renomeia apenas as colunas que existem
    existing_cols = {k: v for k, v in col_map.items() if k in df.columns}
    df.rename(columns=existing_cols, inplace=True)
    
    cols_necessarias = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in cols_necessarias):
        print(f"Erro: O CSV não contém as colunas necessárias. Encontradas: {df.columns.tolist()}")
        return

    print(f"Dados carregados: {len(df)} candles.")
    print(f"Período: {df['timestamp'].iloc[0]} a {df['timestamp'].iloc[-1]}")

    bot = SniperPhoenixAdaptativo(capital_inicial=1000.0)
    df_resultado = bot.executar_backtest(df)
    
    if len(bot.trades) == 0:
        print("Nenhum trade realizado. Verifique os parâmetros ou o período.")
        return

    trades_df = pd.DataFrame(bot.trades)
    trades_df.to_csv('backtest_trades_axs_adaptativo_v2.csv', index=False)
    print(f"Trades salvos em 'backtest_trades_axs_adaptativo_v2.csv' ({len(trades_df)} trades)")
    
    equity_df = pd.DataFrame(bot.equity_curve)
    equity_df.to_csv('backtest_equity_axs_adaptativo_v2.csv', index=False)
    print(f"Equity curve salva em 'backtest_equity_axs_adaptativo_v2.csv'")
    
    capital_final = bot.capital
    retorno_total = ((capital_final - 1000) / 1000) * 100
    wins = len(trades_df[trades_df['pnl_liquido'] > 0])
    win_rate = (wins / len(trades_df)) * 100
    
    print("\n" + "="*60)
    print("SIMULAÇÃO CONCLUÍDA - VERSÃO CORRIGIDA (SEM LOOKAHEAD)")
    print("="*60)
    print(f"Capital Inicial:    $1.000,00")
    print(f"Capital Final:      ${capital_final:.2f}")
    print(f"Retorno Total:      {retorno_total:.2f}%")
    print(f"Total de Trades:    {len(trades_df)}")
    print(f"Win Rate:           {win_rate:.2f}% ({wins} vitórias)")
    print(f"Max Drawdown:       {bot.max_drawdown:.2%}")
    print("="*60)

if __name__ == "__main__":
    main()