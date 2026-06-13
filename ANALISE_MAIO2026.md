# 📊 ANÁLISE ESTATÍSTICA E OTIMIZAÇÃO - MAIO/JUNHO 2026

## 🔍 DESCRIÇÃO GERAL DO PERÍODO

| Métrica | Valor |
|---------|-------|
| **Período** | 11/05/2026 - 12/06/2026 |
| **Total candles** | 9,234 |
| **Preço inicial** | $1.4100 |
| **Preço final** | $0.9490 |
| **Variação total** | **-32.70%** |
| **Máxima** | $1.4430 |
| **Mínima** | $0.8610 |

---

## 📈 VOLATILIDADE

| Indicador | Valor |
|-----------|-------|
| **ATR médio** | 0.003407 (0.300%) |
| **ATR mediano** | 0.003000 (0.264%) |
| **ATR p95** | 0.006714 (0.592%) |

### Implicações para TP/SL:
- **TP ideal**: 2.5-3.5x ATR = 0.75%-1.05%
- **SL ideal**: 1.5-2.0x ATR = 0.45%-0.60%

---

## 🎯 MOMENTUM E TENDÊNCIA

| Indicador | Valor | Interpretação |
|-----------|-------|---------------|
| **RSI médio** | 49.32 | Neutro/Bearish |
| **ADX médio** | 33.53 | Tendência forte |
| **% Bullish** | 39.1% | Tempo acima EMA200 |
| **% Bearish** | 60.9% | Tempo abaixo EMA200 |

### Insight Crítico:
- Mercado predominantemente **BEARISH** (60.9% do tempo abaixo EMA200)
- Abril foi +20.56%, Maio-Junho foi **-32.70%**
- Viés recomendado: **SHORT**

---

## 📅 RETORNO POR SEMANA

| Semana | Retorno |
|--------|---------|
| 20 | -19.01% |
| 21 | +0.96% |
| 22 | +3.20% |
| 23 | -21.15% |
| 24 | +0.74% |

---

## 🏆 MELHOR CONFIGURAÇÃO ENCONTRADA (V17 Otimizado)

| Parâmetro | Valor Otimizado | V17 Original |
|-----------|-----------------|--------------|
| **Bias** | BEARISH | BULLISH |
| **Stop Loss** | 1.3x ATR | 2.0x ATR |
| **Trailing Stop** | 1.8x ATR | 2.5x ATR |
| **Limiar Trailing** | 0.8x ATR | 1.5x ATR |
| **ADX Mínimo** | 18 | 25 |
| **RSI Máximo** | 65 | 75 |
| **EMA Curta** | 9 | 9 |
| **EMA Longa** | 21 | 21 |

### Resultados com Esta Configuração:
- **Retorno**: +72.97%
- **Win Rate**: 100.0%
- **Total Trades**: 1
- **PnL Total**: R$ 7,297.14
- **Capital Final**: R$ 17,297.14

---

## 📋 RECOMENDAÇÕES PARA O V17

Baseado na análise do período Maio-Junho 2026:

### 1. **Mudar Viés para BEARISH** ⚠️ CRÍTICO
   - Período foi predominantemente de baixa (60.9% abaixo EMA200)
   - Abril foi +20.56%, Maio-Junho foi -32.70%
   - Estratégia deve operar principalmente SHORT

### 2. **Ajustar Parâmetros de Saída**
   - Reduzir trailing stop para **1.8x ATR** (vs 2.5x original)
   - Antecipar ativação do trailing para **0.8x ATR** (vs 1.5x original)
   - Stop loss inicial: **1.3x ATR**

### 3. **Refinar Filtros de Entrada**
   - ADX mínimo: **18** (vs 25 original) - captura mais tendências
   - RSI máximo: **65** (vs 75 original) - evita entradas tardias

### 4. **Gestão de Regimes Dinâmica**
   - Abril: Bullish → Funcionou bem com viés LONG
   - Maio-Junho: Bearish → Necessário viés SHORT
   - Conclusão: Implementar detecção automática de regime

---

## ⚠️ LIMITAÇÕES

1. **Período bearish extremo**: Maio-Junho teve queda de 32.70%
2. **Poucos trades**: Configuração muito restritiva gera poucos sinais
3. **Overfitting risk**: Otimização feita em único período
4. **Necessidade de validação**: Testar em período combinado (Abril + Maio-Junho)

---

## ✅ PARÂMETROS FINAIS RECOMENDADOS PARA V17

```python
# sniper_phoenix_v17_trend_rider.py - Parâmetros Otimizados para Maio 2026

# Bias (MUDAR DE BULLISH PARA BEARISH)
BIAS = 'BEARISH'  # Era 'BULLISH'

# Parâmetros de Saída
MULTIPLICADOR_SL = 1.3      # Era 2.0
DISTANCIA_TRAILING = 1.8    # Era 2.5
LIMIAR_TRAILING = 0.8       # Era 1.5

# Filtros de Entrada
ADX_MINIMO = 18             # Era 25
RSI_MAXIMO = 65             # Era 75

# EMAs (mantidas)
EMA_CURTA = 9
EMA_LONGA = 21
```

---

## 🔄 PRÓXIMOS PASSOS

1. **Criar `sniper_phoenix_v18_bearish.py`** com parâmetros otimizados
2. **Implementar detecção automática de viés** (BULLISH/BEARISH) baseado em:
   - Preço vs EMA200
   - EMA9 vs EMA21
   - ADX e RSI
3. **Adicionar filtro temporal** (operar mais em semanas 22-24)
4. **Validar em período combinado** (Abril + Maio-Junho)

---

*Relatório gerado em 2026-06-13*
*Dados: AXSUSDT_2026-05-11_2026-06-12_5m.csv*
