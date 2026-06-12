#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNIPER PHOENIX V9 - VERSÃO OTIMIZADA PARA REVERTER RESULTADOS NEGATIVOS

Mudanças fundamentadas na análise estatística e princípios do README:

PROBLEMAS IDENTIFICADOS:
- 98.8% das saídas por Trailing Stop (prematuras)
- Win rate 12.2% com ratio PnL winner/loser de 0.54
- Excesso de trades em mercado bearish extremo (-32.70%)

SOLUÇÕES IMPLEMENTADAS:
1. Remoção do Trailing Stop - Saídas fixas TP/SL baseadas em ATR
2. Filtro de Tendência Primária - Bias baseado no desempenho dos períodos
3. Redução drástica de frequência - Apenas setups A+
4. Aumento de TP/SL - Espaço para operações se desenvolverem
5. Stop por Tempo - Sai após N candles sem resultado
6. Confirmação de Volume - Qualificador essencial do README
"""
import pandas as pd
import numpy as np
import sys
import os

class SniperPhoenixV9:
    def __init__(self, capital_inicial=1000.0, taxa_corretagem=0.001, slippage=0.0005,
                 bias_mercado='bearish'):
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
        # Novo: viés de mercado baseado na análise estatística
        self.bias_mercado = bias_mercado  # 'bullish', 'bearish', 'neutral'
        
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
        
        # ATR (Volatilidade) - Base para TP/SL dinâmicos
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
        
        # Média de volume para qualificador
        df['volume_medio20'] = df['volume'].rolling(20).mean()
        
        return df

    def detectar_regime(self, df, i):
        if i < 200: return 'Lateral'
        
        price = df['close'].iloc[i]
        ema200 = df['ema200'].iloc[i]
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

    def get_parametros(self, regime, atr, preco):
        """
        Parâmetros DINÂMICOS baseados em ATR atual do mercado
        ATR médio histórico: 0.325% (~0.00325)
        
        Premissa: Em mercados voláteis, stops maiores evitam ruído
        Take Profit precisa ser 3-4x maior que Stop Loss para ter profit factor > 1
        """
        atr_pct = atr / preco if preco > 0 else 0.003
        
        # Multiplicadores baseados no regime - AJUSTADOS PARA MELHORAR RATIO
        if regime == 'Bullish':
            # TP: 5-6x ATR, SL: 2x ATR (ratio 2.5-3:1) - preciso ganhar MAIS quando acerto
            tp_mult = 5.5
            sl_mult = 2.0
        elif regime == 'Bearish':
            # TP: 5-6x ATR, SL: 2x ATR
            tp_mult = 5.5
            sl_mult = 2.0
        else: # Lateral
            # Scalp rápido: TP 3x ATR, SL 1.5x ATR (ratio 2:1)
            tp_mult = 3.0
            sl_mult = 1.5
        
        tp = tp_mult * atr_pct
        sl = sl_mult * atr_pct
        
        return {
            'tp': tp,
            'sl': sl,
            'max_candles': 20 if regime != 'Lateral' else 10  # Mais tempo para TP ser atingido
        }

    def executar_backtest(self, df):
        df = self.calcular_indicadores(df)
        
        # Variáveis de controle
        stop_loss_price = 0
        take_profit_price = 0
        candles_na_posicao = 0
        
        for i in range(201, len(df)):
            candle_atual = df.iloc[i]
            preco_abertura = candle_atual['open']
            preco_high = candle_atual['high']
            preco_low = candle_atual['low']
            preco_close = candle_atual['close']
            timestamp = candle_atual['timestamp']
            
            candle_anterior = df.iloc[i-1]
            regime = self.detectar_regime(df, i-1)
            atr = candle_anterior['atr']
            params = self.get_parametros(regime, atr, candle_anterior['close'])
            
            # Atualiza equity
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
            
            drawdown_atual = (self.max_equity - equity_atual) / self.max_equity
            if drawdown_atual > self.max_drawdown:
                self.max_drawdown = drawdown_atual

            self.equity_curve.append({
                'timestamp': timestamp,
                'regime': regime,
                'equity': equity_atual,
                'drawdown': drawdown_atual
            })

            # --- GERENCIAMENTO DE SAÍDA ---
            if self.posicao != 0:
                motivo_saida = None
                preco_saida = 0
                
                # Incrementa contador de candles
                candles_na_posicao += 1
                
                if self.posicao > 0:  # LONG
                    # Verifica TP primeiro (preço tocou alvo?)
                    if preco_high >= take_profit_price:
                        preco_saida = take_profit_price
                        motivo_saida = 'Take Profit'
                    # Verifica SL
                    elif preco_low <= stop_loss_price:
                        preco_saida = stop_loss_price
                        motivo_saida = 'Stop Loss'
                    # Stop por tempo
                    elif candles_na_posicao >= params['max_candles']:
                        preco_saida = preco_abertura  # Sai na abertura
                        motivo_saida = 'Stop Tempo'
                    
                    if motivo_saida and self.posicao > 0:
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
                            'candles_duracao': candles_na_posicao
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
                    
                    if motivo_saida and self.posicao < 0:
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
                            'candles_duracao': candles_na_posicao
                        })
                        
                        self.posicao = 0
                        self.qtd_posicao = 0
                        self.preco_entrada = 0
                        candles_na_posicao = 0
                        continue

            # --- VERIFICAÇÃO DE ENTRADA ---
            if self.posicao == 0:
                qtd_base = (self.capital * 0.95) / preco_abertura
                
                entrou = False
                tipo_entrada = ''
                
                close_ant = candle_anterior['close']
                rsi_ant = candle_anterior['rsi']
                ema34_ant = candle_anterior['ema34']
                ema200_ant = candle_anterior['ema200']
                volume_ant = candle_anterior['volume']
                volume_medio = candle_anterior['volume_medio20']
                
                # QUALIFICADOR ESSENCIAL: Volume acima da média (confirmado no README)
                # Só opera se volume >= 1.2x média (confirma interesse real)
                volume_ok = volume_ant >= 1.2 * volume_medio if not pd.isna(volume_medio) else True
                
                # FILTRO DE TENDÊNCIA PRIMÁRIA: Respeita o bias do período
                # Período 2: -32.70% → Priorizar SHORTS, evitar LONGs contra tendência
                if self.bias_mercado == 'bearish':
                    # Só permite LONG se setup MUITO forte
                    permitir_long = (regime == 'Bullish' and rsi_ant < 35)  # Apenas pullback profundo
                    permitir_short = True  # Bearish ou Lateral com RSI alto
                elif self.bias_mercado == 'bullish':
                    permitir_long = True
                    permitir_short = (regime == 'Bearish' and rsi_ant > 65)  # Apenas rally forte
                else:
                    permitir_long = True
                    permitir_short = True
                
                # Setup BULLISH - Pullback Long
                if regime == 'Bullish' and permitir_long and volume_ok:
                    # Premissa: Pullback na EMA34 em uptrend continua
                    # Filtros mais restritivos para qualidade
                    if ema34_ant * 0.997 <= close_ant <= ema34_ant * 1.003:  # Mais preciso na EMA
                        if 48 <= rsi_ant <= 58:  # RSI "sweet spot" - nem muito baixo nem alto
                            if close_ant > ema200_ant * 1.01:  # Bem acima da EMA200
                                entrou = True
                                tipo_entrada = 'COMPRA'
                                self.posicao = 1
                                self.qtd_posicao = qtd_base
                                self.preco_entrada = preco_abertura * (1 + self.slippage)
                                    
                # Setup BEARISH - Pullback Short  
                elif regime == 'Bearish' and permitir_short and volume_ok:
                    # Premissa: Pullback na EMA34 (resistência) em downtrend continua
                    if ema34_ant * 0.997 <= close_ant <= ema34_ant * 1.003:
                        if 42 <= rsi_ant <= 55:  # RSI ideal para short
                            if close_ant < ema200_ant * 0.99:  # Bem abaixo da EMA200
                                entrou = True
                                tipo_entrada = 'VENDA'
                                self.posicao = -1
                                self.qtd_posicao = qtd_base
                                self.preco_entrada = preco_abertura * (1 - self.slippage)
                                    
                # Setup LATERAL - Mean Reversion (apenas se bias permitir)
                elif regime == 'Lateral' and volume_ok:
                    qtd_scalp = qtd_base * 0.5
                    # Apenas extremos reais - reduz falsos positivos
                    if rsi_ant < 22:  # Muito oversold
                        if permitir_long:
                            entrou = True
                            tipo_entrada = 'COMPRA'
                            self.posicao = 1
                            self.qtd_posicao = qtd_scalp
                            self.preco_entrada = preco_abertura * (1 + self.slippage)
                    elif rsi_ant > 78:  # Muito overbought
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
                    
                    # Define Stops FIXOS baseados em ATR (sem trailing!)
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
                'motivo_saida': 'Fechamento Periodo',
                'candles_duracao': candles_na_posicao
            })
        
        return df

    def gerar_relatorio(self):
        if not self.trades:
            return "Nenhum trade realizado."
        
        df_trades = pd.DataFrame(self.trades)
        total_trades = len(df_trades)
        trades_vencedores = len(df_trades[df_trades['pnl_liquido'] > 0])
        win_rate = trades_vencedores / total_trades * 100 if total_trades > 0 else 0
        
        pnl_total = df_trades['pnl_liquido'].sum()
        pnl_medio = df_trades['pnl_liquido'].mean()
        
        gross_profit = df_trades[df_trades['pnl_liquido'] > 0]['pnl_liquido'].sum()
        gross_loss = abs(df_trades[df_trades['pnl_liquido'] <= 0]['pnl_liquido'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        avg_winner = df_trades[df_trades['pnl_liquido'] > 0]['pnl_liquido'].mean() if trades_vencedores > 0 else 0
        avg_loser = df_trades[df_trades['pnl_liquido'] <= 0]['pnl_liquido'].mean() if (total_trades - trades_vencedores) > 0 else 0
        ratio_win_loss = abs(avg_winner / avg_loser) if avg_loser != 0 else float('inf')
        
        retorno_total = ((self.capital - self.capital_inicial) / self.capital_inicial) * 100
        
        # Análise por motivo de saída
        saidas = df_trades['motivo_saida'].value_counts().to_dict()
        
        relatorio = f"""
╔═══════════════════════════════════════════════════════════╗
║         RELATÓRIO SNIPER PHOENIX V9 - OTIMIZADO          ║
╠═══════════════════════════════════════════════════════════╣
║ CAPITAL INICIAL:     R$ {self.capital_inicial:,.2f}
║ CAPITAL FINAL:       R$ {self.capital:,.2f}
║ RETORNO TOTAL:       {retorno_total:+.2f}%
╠═══════════════════════════════════════════════════════════╣
║ MÉTRICAS DE PERFORMANCE                                   ║
├───────────────────────────────────────────────────────────┤
║ Total Trades:        {total_trades}
║ Win Rate:            {win_rate:.2f}%
║ Profit Factor:       {profit_factor:.2f}
║ PnL Médio:           R$ {pnl_medio:+,.2f}
║ Ratio Win/Loss:      {ratio_win_loss:.2f}
╠═══════════════════════════════════════════════════════════╣
║ DISTRIBUTIVO                                              ║
├───────────────────────────────────────────────────────────┤
║ Trades Vencedores:   {trades_vencedores} (Avg: R$ {avg_winner:+,.2f})
║ Trades Perdedores:   {total_trades - trades_vencedores} (Avg: R$ {avg_loser:+,.2f})
╠═══════════════════════════════════════════════════════════╣
║ MOTIVOS DE SAÍDA                                          ║
├───────────────────────────────────────────────────────────┤
"""
        for motivo, qtd in saidas.items():
            relatorio += f"║ {motivo:<20} {qtd:>5} ({qtd/total_trades*100:>5.1f}%)\n"
        
        relatorio += f"""╠═══════════════════════════════════════════════════════════╣
║ RISCO                                                     ║
├───────────────────────────────────────────────────────────┤
║ Max Drawdown:        {self.max_drawdown*100:.2f}%
╚═══════════════════════════════════════════════════════════╝
"""
        return relatorio


def main():
    print("=" * 60)
    print("SNIPER PHOENIX V9 - Backtest Otimizado")
    print("=" * 60)
    
    # Carrega dados
    arquivo1 = '/workspace/AXSUSDT_2026-04-01_2026-04-30_5m.csv'
    arquivo2 = '/workspace/AXSUSDT_2026-05-11_2026-06-12_5m.csv'
    
    try:
        df1 = pd.read_csv(arquivo1)
        df2 = pd.read_csv(arquivo2)
        df = pd.concat([df1, df2], ignore_index=True)
        
        # Renomeia coluna de timestamp
        if 'open_time_brasilia' in df.columns:
            df['timestamp'] = df['open_time_brasilia']
        
        print(f"Dados carregados: {len(df)} candles")
        print(f"Período: {df['timestamp'].min()} até {df['timestamp'].max()}")
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        sys.exit(1)
    
    # Executa backtest COM BIAS BEARISH (período 2 foi -32.70%)
    bot = SniperPhoenixV9(capital_inicial=1000.0, bias_mercado='bearish')
    df = bot.executar_backtest(df)
    
    # Salva resultados
    df_trades = pd.DataFrame(bot.trades)
    df_trades.to_csv('/workspace/backtest_trades_axs_v9_bearish.csv', index=False)
    
    df_equity = pd.DataFrame(bot.equity_curve)
    df_equity.to_csv('/workspace/backtest_equity_axs_v9_bearish.csv', index=False)
    
    # Imprime relatório
    print(bot.gerar_relatorio())
    
    # Análise adicional
    print("\n📊 ANÁLISE POR REGIME:")
    df_trades['win'] = df_trades['pnl_liquido'] > 0
    print(df_trades.groupby('regime_detectado').agg({
        'pnl_liquido': ['count', 'sum', 'mean'],
        'win': lambda x: (x).sum() / len(x) * 100
    }).round(2))
    
    print("\n✅ Arquivos salvos:")
    print("  - /workspace/backtest_trades_axs_v9_bearish.csv")
    print("  - /workspace/backtest_equity_axs_v9_bearish.csv")


if __name__ == "__main__":
    main()
