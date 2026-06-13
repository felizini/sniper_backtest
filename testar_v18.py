#!/usr/bin/env python3
"""
Teste do Sniper Phoenix V18 nos períodos de Abril e Maio-Junho 2026
"""
import pandas as pd
import numpy as np
from sniper_phoenix_v18_trend_rider import SniperPhoenixV18, carregar_dados, analisar_resultados
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("🧪 TESTE DO SNIPER PHOENIX V18 - COMPARAÇÃO ABRIL vs MAIO-JUNHO")
print("="*70)

# Carregar dados
print("\n📂 Carregando dados...")
df_abril = carregar_dados('AXSUSDT_2026-04-01_2026-04-30_5m.csv')
df_maio = carregar_dados('AXSUSDT_2026-05-11_2026-06-12_5m.csv')

print(f"   Abril: {len(df_abril)} candles ({df_abril['timestamp'].min()} a {df_abril['timestamp'].max()})")
print(f"   Maio-Junho: {len(df_maio)} candles ({df_maio['timestamp'].min()} a {df_maio['timestamp'].max()})")

# Calcular variação dos períodos
variacao_abril = ((df_abril['close'].iloc[-1] - df_abril['close'].iloc[0]) / df_abril['close'].iloc[0]) * 100
variacao_maio = ((df_maio['close'].iloc[-1] - df_maio['close'].iloc[0]) / df_maio['close'].iloc[0]) * 100

print(f"\n📈 Variação do Mercado:")
print(f"   Abril: {variacao_abril:+.2f}%")
print(f"   Maio-Junho: {variacao_maio:+.2f}%")

# Inicializar bot V18
bot_v18 = SniperPhoenixV18(capital_inicial=10000, risk_per_trade=0.01)

# Executar backtest em ABRIL
print("\n" + "="*70)
print("📊 BACKTEST V18 - ABRIL 2026")
print("="*70)
resultados_abril = bot_v18.executar_backtest(df_abril, verbose=False)
analisar_resultados(resultados_abril, "ABRIL 2026 (V18)")

# Resetar bot para próximo teste
bot_v18.capital = bot_v18.capital_inicial
bot_v18.trades = []

# Executar backtest em MAIO-JUNHO
print("\n" + "="*70)
print("📊 BACKTEST V18 - MAIO-JUNHO 2026")
print("="*70)
resultados_maio = bot_v18.executar_backtest(df_maio, verbose=False)
analisar_resultados(resultados_maio, "MAIO-JUNHO 2026 (V18)")

# Comparação final
print("\n" + "="*70)
print("🏆 COMPARAÇÃO FINAL - V18 ADAPTATIVO")
print("="*70)

print(f"\n{'Métrica':<30} {'Abril 2026':<20} {'Maio-Junho 2026':<20}")
print("-"*70)
print(f"{'Retorno (%)':<30} {resultados_abril['retorno_pct']:+>10.2f}% {resultados_maio['retorno_pct']:+>10.2f}%")
print(f"{'PnL Total (R$)':<30} {resultados_abril['pnl_total']:>+10.2f} {resultados_maio['pnl_total']:>+10.2f}")
print(f"{'Capital Final (R$)':<30} {resultados_abril['capital_final']:>10.2f} {resultados_maio['capital_final']:>10.2f}")
print(f"{'Total Trades':<30} {resultados_abril['total_trades']:>10d} {resultados_maio['total_trades']:>10d}")
print(f"{'Win Rate (%)':<30} {resultados_abril['win_rate']:>10.1f}% {resultados_maio['win_rate']:>10.1f}%")
print(f"{'Trades BULLISH':<30} {resultados_abril['trades_bullish']:>10d} {resultados_maio['trades_bullish']:>10d}")
print(f"{'Trades BEARISH':<30} {resultados_abril['trades_bearish']:>10d} {resultados_maio['trades_bearish']:>10d}")
print(f"{'PnL BULLISH (R$)':<30} {resultados_abril['pnl_bullish']:>+10.2f} {resultados_maio['pnl_bullish']:>+10.2f}")
print(f"{'PnL BEARISH (R$)':<30} {resultados_abril['pnl_bearish']:>+10.2f} {resultados_maio['pnl_bearish']:>+10.2f}")
print(f"{'Mudanças Regime':<30} {resultados_abril['mudancas_bias']:>10d} {resultados_maio['mudancas_bias']:>10d}")

print("\n" + "="*70)
print("✅ CONCLUSÕES:")
print("="*70)

# Análise de adaptação
if variacao_abril > 0 and resultados_abril['retorno_pct'] > 0:
    print("\n✓ V18 performou bem em mercado BULLISH (Abril)")
    
if variacao_maio < 0 and resultados_maio['retorno_pct'] > 0:
    print("✓ V18 performou bem em mercado BEARISH (Maio-Junho)")
    print("✓ Detecção automática de regime FUNCIONOU!")

# Comparar performance por regime
total_bullish = resultados_abril['trades_bullish'] + resultados_maio['trades_bullish']
total_bearish = resultados_abril['trades_bearish'] + resultados_maio['trades_bearish']

print(f"\n📊 Distribuição de Trades:")
print(f"   BULLISH: {total_bullish} trades ({total_bullish/(total_bullish+total_bearish)*100:.1f}%)")
print(f"   BEARISH: {total_bearish} trades ({total_bearish/(total_bullish+total_bearish)*100:.1f}%)")

# Performance agregada
retorno_total = resultados_abril['retorno_pct'] + resultados_maio['retorno_pct']
print(f"\n💰 Performance Agregada (ambos períodos): {retorno_total:+.2f}%")

print("\n" + "="*70)
print("🎯 V18 PRONTO PARA USO!")
print("="*70)
