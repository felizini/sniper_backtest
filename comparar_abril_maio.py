#!/usr/bin/env python3
"""
Comparação de simulações entre ABRIL e MAIO-JUNHO 2026 para o bot sniper_phoenix_v17_trend_rider.py
"""
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
pd.set_option('display.max_columns', None)

def calcular_indicadores(df):
    """Calcula todos os indicadores necessários"""
    # EMAs
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - 100/(1 + gain/loss)
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    true_range = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1)
    df['ATR'] = true_range.rolling(14).mean()
    
    # ADX
    periodo = 14
    plus_dm = df['high'].diff().clip(lower=0)
    minus_dm = (-df['low'].diff()).clip(lower=0)
    tr_roll = df['ATR'] * periodo
    plus_di = 100 * plus_dm.rolling(periodo).mean() / tr_roll
    minus_di = 100 * minus_dm.rolling(periodo).mean() / tr_roll
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    df['ADX'] = dx.rolling(periodo).mean()
    
    return df

def backtest_v17(df, sl_mult=2.0, trail_dist=2.5, trail_limiar=1.5, adx_min=25, rsi_max=75, bias='BULLISH'):
    """
    Simula o comportamento do sniper_phoenix_v17_trend_rider.py
    """
    capital = 10000
    trades = []
    pos = False
    entry = 0
    qty = 0
    sl = 0
    trailing = False
    best = 0
    trail_val = 0
    
    df = df.copy()
    df = calcular_indicadores(df)
    df.dropna(inplace=True)
    
    for i in range(200, len(df)):
        row = df.iloc[i]
        
        if pos:
            close = row['close']
            atr_val = max(row['ATR'], 0.001)
            
            if bias == 'BULLISH':
                # LONG trade
                if close < best:
                    pass  # Não atualiza best
                else:
                    best = close
                
                # Ativa trailing
                if best >= entry + trail_limiar * atr_val:
                    trailing = True
                    new_trail = best - trail_dist * atr_val
                    if new_trail > trail_val:
                        trail_val = new_trail
                
                # Saiu?
                exit_price = None
                if not trailing and close <= sl:
                    exit_price = sl
                elif trailing and close <= trail_val:
                    exit_price = trail_val
                
                if exit_price:
                    pnl = (exit_price - entry) * qty
                    capital += pnl
                    trades.append(pnl)
                    pos = False
            else:
                # SHORT trade
                if close < best:
                    best = close
                
                # Ativa trailing
                if best <= entry - trail_limiar * atr_val:
                    trailing = True
                    new_trail = best + trail_dist * atr_val
                    if new_trail < trail_val or trail_val == 0:
                        trail_val = new_trail
                
                # Saiu?
                exit_price = None
                if not trailing and close >= sl:
                    exit_price = sl
                elif trailing and close >= trail_val:
                    exit_price = trail_val
                
                if exit_price:
                    pnl = (entry - exit_price) * qty
                    capital += pnl
                    trades.append(pnl)
                    pos = False
        
        if not pos:
            # Regime
            bullish = row['EMA9'] > row['EMA21'] and row['close'] > row['EMA200']
            bearish = row['EMA9'] < row['EMA21'] and row['close'] < row['EMA200']
            
            if row['ATR'] <= 0 or row['ADX'] < adx_min or row['RSI'] > rsi_max:
                continue
            
            prev = df.iloc[i-1]
            
            if bias == 'BULLISH' and bullish:
                # Sinal LONG
                cross_up = prev['EMA9'] <= prev['EMA21'] and row['EMA9'] > row['EMA21']
                pullback = row['low'] <= row['EMA9'] * 1.002 and row['close'] > row['EMA9']
                
                if cross_up or pullback:
                    entry = row['close']
                    atr_val = row['ATR']
                    sl = entry - sl_mult * atr_val
                    risk = entry - sl
                    qty = int(capital * 0.01 / risk) if risk > 0 else 0
                    if qty > 0:
                        pos = True
                        best = entry
                        trailing = False
                        trail_val = sl
            elif bias == 'BEARISH' and bearish:
                # Sinal SHORT
                cross_down = prev['EMA9'] >= prev['EMA21'] and row['EMA9'] < row['EMA21']
                pullback = row['high'] >= row['EMA9'] * 0.998 and row['close'] < row['EMA9']
                
                if cross_down or pullback:
                    entry = row['close']
                    atr_val = row['ATR']
                    sl = entry + sl_mult * atr_val
                    risk = sl - entry
                    qty = int(capital * 0.01 / risk) if risk > 0 else 0
                    if qty > 0:
                        pos = True
                        best = entry
                        trailing = False
                        trail_val = sl
    
    if trades:
        retorno = sum(trades) / 10000 * 100
        win_rate = len([t for t in trades if t > 0]) / len(trades) * 100
        return {
            'retorno': retorno, 
            'win_rate': win_rate, 
            'trades': len(trades), 
            'pnl': sum(trades),
            'capital_final': capital
        }
    return {'retorno': 0, 'win_rate': 0, 'trades': 0, 'pnl': 0, 'capital_final': capital}

def analisar_periodo(df, nome_periodo):
    """Analisa estatísticas de um período"""
    print(f"\n{'='*60}")
    print(f"📊 {nome_periodo.upper()}")
    print(f"{'='*60}")
    
    variacao = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
    print(f"Período: {df['timestamp'].min()} a {df['timestamp'].max()}")
    print(f"Candles: {len(df)}")
    print(f"Preço: {df['close'].iloc[0]:.4f} -> {df['close'].iloc[-1]:.4f}")
    print(f"Variação total: {variacao:+.2f}%")
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    true_range = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1)
    atr = true_range.rolling(14).mean()
    print(f"ATR médio: {atr.mean():.6f} ({atr.mean()/df['close'].mean()*100:.3f}%)")
    
    # EMAs
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    pct_bearish = (df['close'] < df['EMA200']).sum() / len(df) * 100
    print(f"% Bearish (abaixo EMA200): {pct_bearish:.1f}%")
    
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = 100 - 100/(1 + gain/loss)
    print(f"RSI médio: {rsi.mean():.2f}")
    
    return {
        'variacao': variacao,
        'atr_medio': atr.mean(),
        'pct_bearish': pct_bearish,
        'rsi_medio': rsi.mean()
    }

# Carregar dados
print("="*60)
print("CARREGANDO DADOS...")
print("="*60)

df_abril = pd.read_csv('AXSUSDT_2026-04-01_2026-04-30_5m.csv')
df_maio = pd.read_csv('AXSUSDT_2026-05-11_2026-06-12_5m.csv')

df_abril['timestamp'] = pd.to_datetime(df_abril['timestamp'])
df_maio['timestamp'] = pd.to_datetime(df_maio['timestamp'])

# Analisar períodos
stats_abril = analisar_periodo(df_abril, "ABRIL 2026")
stats_maio = analisar_periodo(df_maio, "MAIO-JUNHO 2026")

# Comparação lado a lado
print("\n\n" + "="*60)
print("📋 COMPARAÇÃO ESTATÍSTICA: ABRIL vs MAIO-JUNHO")
print("="*60)

comparacao = pd.DataFrame({
    'Métrica': ['Variação Total', 'ATR Médio (%)', '% Bearish', 'RSI Médio', 'Candles'],
    'Abril 2026': [
        f"{stats_abril['variacao']:+.2f}%",
        f"{stats_abril['atr_medio']/df_abril['close'].mean()*100:.3f}%",
        f"{stats_abril['pct_bearish']:.1f}%",
        f"{stats_abril['rsi_medio']:.2f}",
        f"{len(df_abril)}"
    ],
    'Maio-Junho 2026': [
        f"{stats_maio['variacao']:+.2f}%",
        f"{stats_maio['atr_medio']/df_maio['close'].mean()*100:.3f}%",
        f"{stats_maio['pct_bearish']:.1f}%",
        f"{stats_maio['rsi_medio']:.2f}",
        f"{len(df_maio)}"
    ]
})

print(comparacao.to_string(index=False))

# Testar parâmetros V17 originais em ambos períodos
print("\n\n" + "="*60)
print("🧪 SIMULAÇÃO COM PARÂMETROS V17 ORIGINAIS")
print("="*60)
print("\nParâmetros: SL=2.0x, Trail=2.5x, Limiar=1.5x, ADX>25, RSI<75")

# Abril com bias BULLISH (original)
print("\n--- ABRIL 2026 (Bias BULLISH) ---")
res_abril_bull = backtest_v17(df_abril, sl_mult=2.0, trail_dist=2.5, trail_limiar=1.5, adx_min=25, rsi_max=75, bias='BULLISH')
print(f"Retorno: {res_abril_bull['retorno']:.2f}%")
print(f"Win Rate: {res_abril_bull['win_rate']:.1f}%")
print(f"Trades: {res_abril_bull['trades']}")
print(f"PnL: R$ {res_abril_bull['pnl']:.2f}")
print(f"Capital Final: R$ {res_abril_bull['capital_final']:.2f}")

# Maio com bias BULLISH (original)
print("\n--- MAIO-JUNHO 2026 (Bias BULLISH) ---")
res_maio_bull = backtest_v17(df_maio, sl_mult=2.0, trail_dist=2.5, trail_limiar=1.5, adx_min=25, rsi_max=75, bias='BULLISH')
print(f"Retorno: {res_maio_bull['retorno']:.2f}%")
print(f"Win Rate: {res_maio_bull['win_rate']:.1f}%")
print(f"Trades: {res_maio_bull['trades']}")
print(f"PnL: R$ {res_maio_bull['pnl']:.2f}")
print(f"Capital Final: R$ {res_maio_bull['capital_final']:.2f}")

# Maio com bias BEARISH (otimizado)
print("\n--- MAIO-JUNHO 2026 (Bias BEARISH - Otimizado) ---")
res_maio_bear = backtest_v17(df_maio, sl_mult=1.3, trail_dist=1.8, trail_limiar=0.8, adx_min=18, rsi_max=65, bias='BEARISH')
print(f"Retorno: {res_maio_bear['retorno']:.2f}%")
print(f"Win Rate: {res_maio_bear['win_rate']:.1f}%")
print(f"Trades: {res_maio_bear['trades']}")
print(f"PnL: R$ {res_maio_bear['pnl']:.2f}")
print(f"Capital Final: R$ {res_maio_bear['capital_final']:.2f}")

# Grid search otimizada para ABRIL
print("\n\n" + "="*60)
print("🔬 OTIMIZAÇÃO DE PARÂMETROS PARA ABRIL 2026")
print("="*60)

configs_abril = [
    (2.0, 2.5, 1.5, 25, 75),  # Original V17
    (2.5, 3.0, 1.5, 25, 75),  # Mais amplo
    (2.0, 3.5, 2.0, 20, 75),  # TP maior
    (1.8, 2.5, 1.2, 20, 70),  # Mais agressivo
    (2.2, 3.0, 1.5, 22, 72),  # Balanceado
    (2.5, 3.5, 1.8, 20, 75),  # Conservador
]

print("\nTestando configurações para ABRIL (Bias BULLISH):")
resultados_abril = []
for sl, td, tl, adx, rsi in configs_abril:
    res = backtest_v17(df_abril, sl_mult=sl, trail_dist=td, trail_limiar=tl, adx_min=adx, rsi_max=rsi, bias='BULLISH')
    res['params'] = (sl, td, tl, adx, rsi)
    resultados_abril.append(res)
    print(f"SL={sl}x Trail={td}x Lim={tl} ADX>{adx} RSI<{rsi}: Trades={res['trades']}, WR={res['win_rate']:.1f}%, Ret={res['retorno']:.2f}%")

resultados_abril.sort(key=lambda x: x['retorno'], reverse=True)
melhor_abril = resultados_abril[0]

print(f"\n=== MELHOR CONFIGURAÇÃO PARA ABRIL ===")
print(f"SL={melhor_abril['params'][0]}x, Trail={melhor_abril['params'][1]}x, Limiar={melhor_abril['params'][2]}, ADX>{melhor_abril['params'][3]}, RSI<{melhor_abril['params'][4]}")
print(f"Retorno: {melhor_abril['retorno']:.2f}%, Win Rate: {melhor_abril['win_rate']:.1f}%, Trades: {melhor_abril['trades']}")

# Grid search otimizada para MAIO
print("\n\n" + "="*60)
print("🔬 OTIMIZAÇÃO DE PARÂMETROS PARA MAIO-JUNHO 2026")
print("="*60)

configs_maio = [
    (1.3, 1.8, 0.8, 18, 65),  # Otimizado anterior
    (1.5, 2.0, 1.0, 20, 65),  # Mais conservador
    (1.2, 1.5, 0.6, 15, 60),  # Mais agressivo
    (1.4, 1.8, 0.8, 18, 65),  # Balanceado
    (1.5, 2.2, 1.0, 18, 65),  # Trailing maior
    (1.3, 2.0, 0.8, 20, 65),  # ADX maior
]

print("\nTestando configurações para MAIO-JUNHO (Bias BEARISH):")
resultados_maio = []
for sl, td, tl, adx, rsi in configs_maio:
    res = backtest_v17(df_maio, sl_mult=sl, trail_dist=td, trail_limiar=tl, adx_min=adx, rsi_max=rsi, bias='BEARISH')
    res['params'] = (sl, td, tl, adx, rsi)
    resultados_maio.append(res)
    print(f"SL={sl}x Trail={td}x Lim={tl} ADX>{adx} RSI<{rsi}: Trades={res['trades']}, WR={res['win_rate']:.1f}%, Ret={res['retorno']:.2f}%")

resultados_maio.sort(key=lambda x: x['retorno'], reverse=True)
melhor_maio = resultados_maio[0]

print(f"\n=== MELHOR CONFIGURAÇÃO PARA MAIO-JUNHO ===")
print(f"SL={melhor_maio['params'][0]}x, Trail={melhor_maio['params'][1]}x, Limiar={melhor_maio['params'][2]}, ADX>{melhor_maio['params'][3]}, RSI<{melhor_maio['params'][4]}")
print(f"Retorno: {melhor_maio['retorno']:.2f}%, Win Rate: {melhor_maio['win_rate']:.1f}%, Trades: {melhor_maio['trades']}")

# Comparação final
print("\n\n" + "="*60)
print("📊 RESUMO COMPARATIVO FINAL")
print("="*60)

resumo = pd.DataFrame({
    'Período': ['Abril 2026', 'Maio-Junho 2026'],
    'Tendência': ['BULLISH (+20.56%)', 'BEARISH (-32.70%)'],
    'Melhor Bias': ['BULLISH', 'BEARISH'],
    'Melhor Retorno': [f"{melhor_abril['retorno']:.2f}%", f"{melhor_maio['retorno']:.2f}%"],
    'Win Rate': [f"{melhor_abril['win_rate']:.1f}%", f"{melhor_maio['win_rate']:.1f}%"],
    'Total Trades': [f"{melhor_abril['trades']}", f"{melhor_maio['trades']}"],
    'PnL Total': [f"R$ {melhor_abril['pnl']:.2f}", f"R$ {melhor_maio['pnl']:.2f}"]
})

print(resumo.to_string(index=False))

# Conclusões
print("\n\n" + "="*60)
print("💡 CONCLUSÕES E RECOMENDAÇÕES")
print("="*60)

print("""
1. MUDANÇA DE REGIME CRÍTICA:
   - Abril: +20.56% → Bias BULLISH funcionou bem
   - Maio-Junho: -32.70% → Necessário bias BEARISH

2. PARÂMETROS ÓTIMOS POR PERÍODO:
   
   ABRIL (BULLISH):
   - SL: {abril_sl}x ATR
   - Trailing: {abril_td}x ATR
   - Limiar: {abril_tl}x ATR
   - ADX Mínimo: {abril_adx}
   - RSI Máximo: {abril_rsi}
   
   MAIO-JUNHO (BEARISH):
   - SL: {maio_sl}x ATR
   - Trailing: {maio_td}x ATR
   - Limiar: {maio_tl}x ATR
   - ADX Mínimo: {maio_adx}
   - RSI Máximo: {maio_rsi}

3. RECOMENDAÇÃO PRINCIPAL:
   Implementar detecção AUTOMÁTICA de regime baseada em:
   - Preço vs EMA200
   - EMA9 vs EMA21
   - ADX e RSI
   
   Isso permitiria ao bot alternar entre bias BULLISH/BEARISH
   automaticamente conforme as condições de mercado.

4. LIÇÃO APRENDIDA:
   Parâmetros fixos não funcionam em todos os regimes de mercado.
   É necessário adaptar o viés operacional à tendência predominante.
""".format(
    abril_sl=melhor_abril['params'][0],
    abril_td=melhor_abril['params'][1],
    abril_tl=melhor_abril['params'][2],
    abril_adx=melhor_abril['params'][3],
    abril_rsi=melhor_abril['params'][4],
    maio_sl=melhor_maio['params'][0],
    maio_td=melhor_maio['params'][1],
    maio_tl=melhor_maio['params'][2],
    maio_adx=melhor_maio['params'][3],
    maio_rsi=melhor_maio['params'][4]
))

# Salvar relatório
relatorio = f"""# 📊 ANÁLISE COMPARATIVA: ABRIL vs MAIO-JUNHO 2026

## Resumo Executivo

Esta análise compara o desempenho do trading bot `sniper_phoenix_v17_trend_rider.py` 
em dois períodos distintos de 2026, revelando a importância crítica da adaptação 
ao regime de mercado.

---

## 📈 Estatísticas dos Períodos

| Métrica | Abril 2026 | Maio-Junho 2026 |
|---------|------------|-----------------|
| **Variação Total** | +20.56% | -32.70% |
| **ATR Médio** | {stats_abril['atr_medio']/df_abril['close'].mean()*100:.3f}% | {stats_maio['atr_medio']/df_maio['close'].mean()*100:.3f}% |
| **% Bearish** | {stats_abril['pct_bearish']:.1f}% | {stats_maio['pct_bearish']:.1f}% |
| **RSI Médio** | {stats_abril['rsi_medio']:.2f} | {stats_maio['rsi_medio']:.2f} |
| **Candles** | {len(df_abril)} | {len(df_maio)} |

---

## 🧪 Resultados da Simulação V17 Original

### Abril 2026 (Bias BULLISH)
- Retorno: {res_abril_bull['retorno']:.2f}%
- Win Rate: {res_abril_bull['win_rate']:.1f}%
- Trades: {res_abril_bull['trades']}
- PnL: R$ {res_abril_bull['pnl']:.2f}

### Maio-Junho 2026 (Bias BULLISH - inadequado)
- Retorno: {res_maio_bull['retorno']:.2f}%
- Win Rate: {res_maio_bull['win_rate']:.1f}%
- Trades: {res_maio_bull['trades']}
- PnL: R$ {res_maio_bull['pnl']:.2f}

### Maio-Junho 2026 (Bias BEARISH - otimizado)
- Retorno: {res_maio_bear['retorno']:.2f}%
- Win Rate: {res_maio_bear['win_rate']:.1f}%
- Trades: {res_maio_bear['trades']}
- PnL: R$ {res_maio_bear['pnl']:.2f}

---

## 🏆 Melhores Configurações Encontradas

### Para Abril 2026 (BULLISH)
| Parâmetro | Valor |
|-----------|-------|
| Stop Loss | {melhor_abril['params'][0]}x ATR |
| Trailing Stop | {melhor_abril['params'][1]}x ATR |
| Limiar Trailing | {melhor_abril['params'][2]}x ATR |
| ADX Mínimo | {melhor_abril['params'][3]} |
| RSI Máximo | {melhor_abril['params'][4]} |
| **Retorno** | **{melhor_abril['retorno']:.2f}%** |
| Win Rate | {melhor_abril['win_rate']:.1f}% |

### Para Maio-Junho 2026 (BEARISH)
| Parâmetro | Valor |
|-----------|-------|
| Stop Loss | {melhor_maio['params'][0]}x ATR |
| Trailing Stop | {melhor_maio['params'][1]}x ATR |
| Limiar Trailing | {melhor_maio['params'][2]}x ATR |
| ADX Mínimo | {melhor_maio['params'][3]} |
| RSI Máximo | {melhor_maio['params'][4]} |
| **Retorno** | **{melhor_maio['retorno']:.2f}%** |
| Win Rate | {melhor_maio['win_rate']:.1f}% |

---

## 💡 Conclusões Principais

1. **Mudança de Regime é Crítica**: 
   - Abril teve tendência de alta (+20.56%) → Bias BULLISH ideal
   - Maio-Junho teve tendência de baixa (-32.70%) → Bias BEARISH necessário

2. **Parâmetros V17 Originais**:
   - Funcionaram bem em Abril (regime favorável)
   - Falharam em Maio-Junho quando mantidos com bias BULLISH

3. **Necessidade de Adaptação Dinâmica**:
   - Implementar detecção automática de regime
   - Alternar bias baseado em preço vs EMA200 e EMA9 vs EMA21

4. **Lições para Futuras Versões**:
   - Criar sistema de detecção de tendência automática
   - Ajustar parâmetros conforme volatilidade (ATR)
   - Considerar filtros temporais/semanais

---

## ✅ Recomendações para V18

```python
# Detecção automática de regime
def detectar_regime(df):
    preco_vs_ema200 = df['close'].iloc[-1] > df['EMA200'].iloc[-1]
    ema9_vs_ema21 = df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1]
    
    if preco_vs_ema200 and ema9_vs_ema21:
        return 'BULLISH'
    elif not preco_vs_ema200 and not ema9_vs_ema21:
        return 'BEARISH'
    else:
        return 'NEUTRO'

# Ajuste dinâmico de parâmetros
if regime == 'BULLISH':
    bias = 'BULLISH'
    sl_mult = 2.0
    trail_dist = 2.5
else:
    bias = 'BEARISH'
    sl_mult = 1.3
    trail_dist = 1.8
```

---

*Relatório gerado em {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*Dados: AXSUSDT_2026-04-01_2026-04-30_5m.csv e AXSUSDT_2026-05-11_2026-06-12_5m.csv*
"""

with open('ANALISE_COMPARATIVA_ABRIL_MAIO2026.md', 'w') as f:
    f.write(relatorio)

print("\n✅ Relatório salvo em ANALISE_COMPARATIVA_ABRIL_MAIO2026.md")
