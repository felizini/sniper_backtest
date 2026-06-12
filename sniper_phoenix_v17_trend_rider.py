#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNIPER PHOENIX V17 - TREND RIDER
================================
Estratégia focada em "Deixar o Lucro Correr" (Let Profits Run).
Remove Take Profit fixo e utiliza Trailing Stop dinâmico amplo para capturar
tendências completas enquanto durarem.

Modificações da V13 para V17:
1. REMOVIDO: Take Profit Fixo (agora ilimitado).
2. ALTERADO: Trailing Stop ativado mais cedo (1.5x ATR) e mais largo (2.5x ATR).
3. MANTIDO: Filtros de tendência (EMA200, ADX, RSI) da V13.
4. OBJETIVO: Maximizar ganhos em dias de explosão (ex: 25/04).

Autor: Sniper Phoenix System
Data: 2026
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configurações de Exibição
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

class SniperPhoenixV17:
    def __init__(self, capital_inicial=10000.0, risco_por_trade=0.01):
        self.capital_inicial = capital_inicial
        self.capital = capital_inicial
        self.risco_por_trade = risco_por_trade
        self.trades = []
        self.posicao_aberta = False
        self.preco_entrada = 0
        self.quantidade = 0
        self.stop_loss_inicial = 0
        self.trailing_stop_ativo = False
        self.melhor_preco = 0
        self.trailing_stop_valor = 0
        self.tipo_posicao = None  # 'LONG' ou 'SHORT'
        
        # Parâmetros Otimizados V17
        self.periodo_ema_curta = 9
        self.periodo_ema_longa = 21
        self.periodo_ema_tendencia = 200
        self.periodo_adx = 14
        self.periodo_rsi = 14
        self.periodo_atr = 14
        self.warmup_periodo = 200
        
        # Parâmetros de Saída V17 (Trend Rider)
        self.multiplicador_sl = 2.0      # Stop Loss inicial: 2.0x ATR
        self.limiar_trailing = 1.5       # Ativa trailing após 1.5x ATR de lucro
        self.distancia_trailing = 2.5    # Distância do trailing: 2.5x ATR (amplo)

    def calcular_indicadores(self, df):
        """Calcula todos os indicadores técnicos necessários."""
        # EMAs
        df['EMA9'] = df['close'].ewm(span=self.periodo_ema_curta, adjust=False).mean()
        df['EMA21'] = df['close'].ewm(span=self.periodo_ema_longa, adjust=False).mean()
        df['EMA200'] = df['close'].ewm(span=self.periodo_ema_tendencia, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.periodo_rsi).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.periodo_rsi).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # ATR (True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR'] = true_range.rolling(self.periodo_atr).mean()
        
        # ADX
        df['plus_dm'] = df['high'].diff()
        df['minus_dm'] = -df['low'].diff()
        df.loc[df['plus_dm'] < 0, 'plus_dm'] = 0
        df.loc[df['minus_dm'] < 0, 'minus_dm'] = 0
        
        tr = df['ATR'] * self.periodo_atr  # Aproximação para simplificar
        df['plus_di'] = 100 * (df['plus_dm'].rolling(self.periodo_adx).mean() / tr)
        df['minus_di'] = 100 * (df['minus_dm'].rolling(self.periodo_adx).mean() / tr)
        
        dx = 100 * np.abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['ADX'] = dx.rolling(self.periodo_adx).mean()
        
        # Limpeza de NaNs
        df.dropna(inplace=True)
        return df

    def determinar_regime(self, row):
        """Determina o regime de mercado atual."""
        if row['ADX'] < 20:
            return 'LATERAL'
        elif row['EMA9'] > row['EMA21'] and row['close'] > row['EMA200']:
            return 'BULLISH'
        elif row['EMA9'] < row['EMA21'] and row['close'] < row['EMA200']:
            return 'BEARISH'
        else:
            return 'TRANSICAO'

    def verificar_condicoes_entrada(self, df, idx):
        """Verifica se há sinal de entrada baseado na filosofia V13/V17."""
        row = df.iloc[idx]
        prev_row = df.iloc[idx-1]
        
        # Warmup check
        if idx < self.warmup_periodo:
            return False, None
            
        # Regime
        regime = self.determinar_regime(row)
        
        # Filtros Gerais
        if row['ATR'] == 0 or np.isnan(row['ATR']):
            return False, None
            
        # Bias Bullish para Abril 2026 (foco em LONG)
        if regime != 'BULLISH':
            return False, None
            
        # Filtro de Tendência Forte
        if row['ADX'] < 25:  # Reduzido de 30 para pegar mais tendências
            return False, None
            
        # Filtro RSI (não sobrecomprado extremo)
        if row['RSI'] > 75:
            return False, None
            
        # Gatilho de Momentum (Cruzamento ou Pullback)
        cruzamento_alta = prev_row['EMA9'] <= prev_row['EMA21'] and row['EMA9'] > row['EMA21']
        pullback_suporte = row['low'] <= row['EMA9'] * 1.002 and row['close'] > row['EMA9']
        
        if cruzamento_alta or pullback_suporte:
            return True, 'LONG'
            
        return False, None

    def gerenciar_posicao(self, row, idx):
        """Gerencia a posição aberta com Trailing Stop Dinâmico."""
        if not self.posicao_aberta:
            return None
            
        preco_atual = row['close']
        atr_atual = row['ATR']
        
        # Atualiza melhor preço (para LONG)
        if self.tipo_posicao == 'LONG':
            if preco_atual > self.melhor_preco:
                self.melhor_preco = preco_atual
                
            # Calcula nível do Trailing Stop
            # O stop só sobe, nunca desce
            novo_trailing = self.melhor_preco - (self.distancia_trailing * atr_atual)
            
            # Ativa o trailing se já houver lucro suficiente
            lucro_minimo_para_ativar = self.preco_entrada + (self.limiar_trailing * atr_atual)
            
            if self.melhor_preco >= lucro_minimo_para_ativar:
                self.trailing_stop_ativo = True
                # Atualiza o stop apenas se o novo nível for maior que o atual
                if novo_trailing > self.trailing_stop_valor:
                    self.trailing_stop_valor = novo_trailing
            
            # Verifica Saída
            motivo_saida = None
            preco_saida = None
            
            # Stop Loss Inicial (antes de ativar trailing)
            if not self.trailing_stop_ativo:
                if preco_atual <= self.stop_loss_inicial:
                    motivo_saida = 'STOP_LOSS_INICIAL'
                    preco_saida = self.stop_loss_inicial
            
            # Trailing Stop (após ativação)
            if self.trailing_stop_ativo:
                if preco_atual <= self.trailing_stop_valor:
                    motivo_saida = 'TRAILING_STOP'
                    preco_saida = self.trailing_stop_valor
                    
            # Se houve saída, executa
            if motivo_saida:
                return self.fechar_posicao(preco_saida, motivo_saida, row)
                
        return None

    def abrir_posicao(self, row, tipo, idx):
        """Abre uma nova posição."""
        preco_entrada = row['close']
        atr = row['ATR']
        
        # Cálculo do Risk Management
        stop_distancia = self.multiplicador_sl * atr
        self.stop_loss_inicial = preco_entrada - stop_distancia
        
        # Tamanho da posição (1% de risco)
        risco_unitario = preco_entrada - self.stop_loss_inicial
        if risco_unitario <= 0:
            return
            
        valor_risco = self.capital * self.risco_por_trade
        self.quantidade = int(valor_risco / risco_unitario)
        
        if self.quantidade <= 0:
            return
            
        self.posicao_aberta = True
        self.preco_entrada = preco_entrada
        self.tipo_posicao = tipo
        self.melhor_preco = preco_entrada
        self.trailing_stop_ativo = False
        self.trailing_stop_valor = self.stop_loss_inicial  # Começa igual ao SL
        
        # Log de abertura (será completado no fechamento)
        self.trade_atual = {
            'data_hora_entrada': row['timestamp'],
            'preco_entrada': preco_entrada,
            'tipo': tipo,
            'quantidade': self.quantidade,
            'atr_entrada': atr,
            'stop_inicial': self.stop_loss_inicial
        }

    def fechar_posicao(self, preco_saida, motivo, row):
        """Fecha a posição e registra o trade."""
        if not self.posicao_aberta:
            return None
            
        pnl = (preco_saida - self.preco_entrada) * self.quantidade
        self.capital += pnl
        
        trade_registro = {
            **self.trade_atual,
            'data_hora_saida': row['timestamp'],
            'preco_saida': preco_saida,
            'motivo_saida': motivo,
            'pnl': pnl,
            'capital_final': self.capital,
            'retorno_pct': (pnl / (self.preco_entrada * self.quantidade)) * 100
        }
        
        self.trades.append(trade_registro)
        self.posicao_aberta = False
        return trade_registro

    def executar_backtest(self, df):
        """Executa o backtest completo."""
        print(f"Iniciando Backtest V17 - Capital: R$ {self.capital:,.2f}")
        print(f"Estratégia: Trend Rider (Sem TP Fixo, Trailing 2.5x ATR)")
        print("-" * 50)
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            
            # Se tem posição, gerencia primeiro
            if self.posicao_aberta:
                resultado = self.gerenciar_posicao(row, idx)
                if resultado:
                    continue  # Se fechou, não abre nova no mesmo candle (opcional)
            
            # Tenta entrar
            pode_entrar, tipo = self.verificar_condicoes_entrada(df, idx)
            if pode_entrar and not self.posicao_aberta:
                self.abrir_posicao(row, tipo, idx)
        
        # Fecha posições abertas no final (se houver)
        if self.posicao_aberta:
            ultimo_row = df.iloc[-1]
            self.fechar_posicao(ultimo_row['close'], 'FIM_BACKTEST', ultimo_row)
            
        return pd.DataFrame(self.trades)

def carregar_dados():
    """Carrega dados reais do ASX 5m (Abril 2026)."""
    # Tenta carregar arquivo real de abril 2026
    arquivos_possiveis = [
        'AXS_abril_2026.csv',
        'AXSUSDT_2026-04-01_2026-04-30_5m.csv',
        'dados_asx_abril2026.csv'
    ]
    
    for arquivo in arquivos_possiveis:
        try:
            df = pd.read_csv(arquivo)
            # Normaliza colunas para padrão esperado
            if 'open_time_brasilia' in df.columns:
                df['timestamp'] = df['open_time_brasilia']
            elif 'time' in df.columns:
                df['timestamp'] = df['time']
            elif 'timestamp' not in df.columns:
                print(f"Erro: Nenhuma coluna de tempo encontrada em {arquivo}")
                continue
                
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            print(f"Dados reais carregados de: {arquivo}")
            return df
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Erro ao processar {arquivo}: {e}")
            continue
    
    # Se nenhum arquivo real for encontrado, gera dados sintéticos
    print("Nenhum arquivo real encontrado. Gerando dados sintéticos...")
    start_date = datetime(2026, 4, 1, 9, 30)
    n_candles = 2000
    np.random.seed(42)
    dates = [start_date + timedelta(minutes=5*i) for i in range(n_candles)]
    t = np.linspace(0, 10, n_candles)
    trend = 100 + 15 * np.sin(t) + 0.05 * t
    noise = np.random.normal(0, 1, n_candles)
    prices = trend + noise
    idx_explosao = slice(1000, 1050)
    prices[idx_explosao] = prices[999] + np.linspace(0, 25, 50)
    df = pd.DataFrame({'timestamp': dates, 'close': prices})
    df['high'] = df['close'] * (1 + np.abs(np.random.normal(0, 0.005, n_candles)))
    df['low'] = df['close'] * (1 - np.abs(np.random.normal(0, 0.005, n_candles)))
    df['open'] = df['close'].shift(1).fillna(df['close'])
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    return df

def main():
    # Carregar dados reais ou sintéticos
    df = carregar_dados()
    
    # Verificar colunas necessárias
    colunas_necessarias = ['timestamp', 'open', 'high', 'low', 'close']
    for col in colunas_necessarias:
        if col not in df.columns:
            print(f"Erro: Coluna '{col}' não encontrada no arquivo CSV.")
            return
    
    # Instanciar Estratégia
    estrategia = SniperPhoenixV17(capital_inicial=10000.0, risco_por_trade=0.01)
    
    # Calcular Indicadores
    df = estrategia.calcular_indicadores(df)
    
    # Executar Backtest
    resultados = estrategia.executar_backtest(df)
    
    # Análise dos Resultados
    if not resultados.empty:
        total_trades = len(resultados)
        vitorias = resultados[resultados['pnl'] > 0]
        derrotas = resultados[resultados['pnl'] <= 0]
        
        win_rate = (len(vitorias) / total_trades) * 100
        pnl_total = resultados['pnl'].sum()
        retorno_total = ((estrategia.capital - estrategia.capital_inicial) / estrategia.capital_inicial) * 100
        
        print("\n" + "="*50)
        print(f"📊 RESULTADOS V17 - TREND RIDER")
        print("="*50)
        print(f"Total Trades: {total_trades}")
        print(f"Vitórias: {len(vitorias)} | Derrotas: {len(derrotas)}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"PnL Total: R$ {pnl_total:,.2f}")
        print(f"Retorno: {retorno_total:.2f}%")
        print(f"Capital Final: R$ {estrategia.capital:,.2f}")
        
        if len(vitorias) > 0:
            print(f"Maior Vitória: R$ {vitorias['pnl'].max():,.2f}")
            print(f"Média Vitória: R$ {vitorias['pnl'].mean():,.2f}")
        if len(derrotas) > 0:
            print(f"Maior Derrota: R$ {derrotas['pnl'].min():,.2f}")
            print(f"Média Derrota: R$ {derrotas['pnl'].mean():,.2f}")
            
        # Salvar resultados
        resultados.to_csv('backtest_trades_axs_v17.csv', index=False)
        print("\n✅ Detalhes salvos em 'backtest_trades_axs_v17.csv'")
        
        # Plotagem simples
        plt.figure(figsize=(14, 7))
        plt.plot(df['timestamp'], df['close'], label='Preço ASX', alpha=0.7)
        
        # Plot entradas e saídas
        if not resultados.empty:
            plt.scatter(resultados['data_hora_entrada'], resultados['preco_entrada'], 
                        color='green', marker='^', s=100, label='Compra', zorder=5)
            plt.scatter(resultados['data_hora_saida'], resultados['preco_saida'], 
                        color='red', marker='v', s=100, label='Venda', zorder=5)
        
        plt.title('Sniper Phoenix V17 - Trend Rider (Simulação)')
        plt.xlabel('Data')
        plt.ylabel('Preço')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig('grafico_v17_trend_rider.png')
        print("✅ Gráfico salvo em 'grafico_v17_trend_rider.png'")
        plt.show()
    else:
        print("Nenhum trade executado.")

if __name__ == "__main__":
    main()
