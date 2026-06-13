# 📊 ANÁLISE COMPARATIVA: ABRIL vs MAIO-JUNHO 2026

## Resumo Executivo

Esta análise compara o desempenho do trading bot `sniper_phoenix_v17_trend_rider.py` 
em dois períodos distintos de 2026, revelando a importância crítica da adaptação 
ao regime de mercado.

---

## 📈 Estatísticas dos Períodos

| Métrica | Abril 2026 | Maio-Junho 2026 |
|---------|------------|-----------------|
| **Variação Total** | +20.56% | -32.70% |
| **ATR Médio** | 0.371% | 0.292% |
| **% Bearish** | 52.8% | 57.7% |
| **RSI Médio** | 49.97 | 49.53 |
| **Candles** | 8640 | 12097 |

---

## 🧪 Resultados da Simulação V17 Original

### Abril 2026 (Bias BULLISH)
- Retorno: 109.26%
- Win Rate: 50.0%
- Trades: 108
- PnL: R$ 10925.59

### Maio-Junho 2026 (Bias BULLISH - inadequado)
- Retorno: -1.86%
- Win Rate: 35.3%
- Trades: 173
- PnL: R$ -185.95

### Maio-Junho 2026 (Bias BEARISH - otimizado)
- Retorno: 489.03%
- Win Rate: 45.5%
- Trades: 358
- PnL: R$ 48902.60

---

## 🏆 Melhores Configurações Encontradas

### Para Abril 2026 (BULLISH)
| Parâmetro | Valor |
|-----------|-------|
| Stop Loss | 2.0x ATR |
| Trailing Stop | 3.5x ATR |
| Limiar Trailing | 2.0x ATR |
| ADX Mínimo | 20 |
| RSI Máximo | 75 |
| **Retorno** | **136.73%** |
| Win Rate | 36.3% |

### Para Maio-Junho 2026 (BEARISH)
| Parâmetro | Valor |
|-----------|-------|
| Stop Loss | 1.2x ATR |
| Trailing Stop | 1.5x ATR |
| Limiar Trailing | 0.6x ATR |
| ADX Mínimo | 15 |
| RSI Máximo | 60 |
| **Retorno** | **823.68%** |
| Win Rate | 45.8% |

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

*Relatório gerado em 2026-06-13 16:06*
*Dados: AXSUSDT_2026-04-01_2026-04-30_5m.csv e AXSUSDT_2026-05-11_2026-06-12_5m.csv*
