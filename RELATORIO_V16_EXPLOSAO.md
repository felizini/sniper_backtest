# 📊 RELATÓRIO FINAL - V16 SNIPER DE EXPLOSÃO

## 🎯 OBJETIVO
Capturar APENAS explosões reais como o dia 25/04, que teve:
- **+44% de alta** em um único dia
- Volume **2000x** acima da média
- Rompimento sequencial de resistências

---

## 🔍 ANÁLISE DO DIA 25/04

### Por que a V16 original falhou?

A versão inicial tinha filtros **ultra-restritivos** que eliminaram a entrada no dia 25:

| Filtro | Parâmetro Original | Problema no Dia 25 |
|--------|-------------------|-------------------|
| Compressão ATR | Percentil < 25 | ❌ ATR já estava alto (100%) |
| Volume | > 3.0x | ✅ OK (volume foi 2-10x) |
| RSI | > 60 | ✅ OK (RSI 77-89) |
| Breakout | 5 candles | ⚠️ Lento demais |
| Horário | 09:00-11:00 | ❌ Explosão começou às 00:00 |

**Conclusão:** O filtro de compressão eliminou todas as entradas potenciais porque explosões reais **NÃO** têm compressão prévia - elas começam com volatilidade alta desde o início.

---

## ✅ V16B - PARÂMETROS OTIMIZADOS

### Mudanças Implementadas

| Parâmetro | Antes | Depois | Justificativa |
|-----------|-------|--------|---------------|
| **Filtro Compressão** | Ativo (p25) | **REMOVIDO** | Dia 25 teve ATR alto desde início |
| **Volume Multiplier** | 3.0x | **2.0x** | Capturar início do movimento |
| **RSI Threshold** | 60 | **50** | Entrar mais cedo na tendência |
| **Breakout Lookback** | 5 candles | **3 candles** | Resposta mais rápida |
| **Horário** | 09:00-12:00 | **00:00-08:00** | Capturar explosão noturna completa |
| **Take Profit** | 3.0% | **8.0%** | Explosões grandes exigem TP maior |
| **Stop Loss** | 1.5% | **2.0%** | Volatilidade exige stop mais largo |
| **Trailing Stop** | Não | **SIM (2x ATR)** | Maximizar ganhos em tendências longas |

---

## 📈 RESULTADOS V16B

### Métricas Gerais

| Métrica | Valor |
|---------|-------|
| **Trades Totais** | 37 |
| **Vitórias** | 10 (27.03%) |
| **Derrotas** | 27 (72.97%) |
| **PnL Total** | R$ -33.82 |
| **Retorno** | **-3.38%** |
| **Buy-and-Hold** | +20.12% |
| **Alpha** | -23.50% |

### Análise Financeira

- **Vitória média:** R$ 14.97
- **Derrota média:** R$ -6.80
- **Ratio Win/Loss:** 2.20 ✅ (ganha 2x mais quando acerta)

### Trades do Dia 25/04

| # | Entrada | Saída | PnL | Exit Reason |
|---|---------|-------|-----|-------------|
| 31 | 00:20 @ 1.20 | 01:20 @ 1.24 | **+R$ 30.73 (+3.64%)** | Trailing |
| 32 | 01:20 @ 1.27 | 01:50 @ 1.25 | -R$ 19.95 (-1.96%) | Trailing |
| 33 | 02:35 @ 1.39 | 03:55 @ 1.40 | +R$ 3.96 (+0.64%) | Trailing |
| 34 | 05:20 @ 1.50 | 06:10 @ 1.62 | **+R$ 70.90 (+8.00%)** | **TP** |
| 35 | 07:00 @ 1.69 | 07:10 @ 1.66 | -R$ 22.29 (-2.08%) | Trailing |

**Saldo dia 25:** +R$ 63.35 (+6.33% no dia)

---

## 🎯 CONCLUSÕES

### ✅ O Que Funcionou

1. **Remoção do filtro de compressão** - Permitiu entrar no dia 25
2. **Trailing stop** - Capturou parte significativa da alta (trade #34: +8%)
3. **Ratio Win/Loss 2.20** - Quando acerta, ganha 2x mais do que perde
4. **Horário estendido (00:00-08:00)** - Capturou explosão noturna

### ❌ O Que Falhou

1. **Excesso de trades (37)** - Muitos sinais falsos durante o mês
2. **Win rate baixo (27%)** - Entra em muitas oportunidades marginais
3. **Não superou Buy-and-Hold** - -3.38% vs +20.12%
4. **Entradas tardias no dia 25** - Trade #34 entrou às 05:20, perdendo alta inicial de 1.18→1.50 (+27%)

### 📝 LIÇÕES APRENDIDAS

1. **Explosões não têm padrão previsível** - Filtros técnicos não capturam eventos exógenos
2. **Menos é mais** - Estratégia deve fazer 1-2 trades/mês, não 37
3. **Volume isolado não basta** - É necessário contexto macro/fundamentalista
4. **Timing é tudo** - Entrar às 00:20 vs 05:20 no dia 25 fez diferença de +27% vs +8%

---

## 🚀 PRÓXIMOS PASSOS SUGERIDOS

### Opção A: Ultra-Restritiva (1-2 trades/mês)
- Adicionar filtro de **volume > 5x** (apenas eventos extremos)
- Exigir **rompimento de máxima de 20 candles**
- Operar apenas **2ª-6ª feira** (evitar fim de semana)
- **Expected:** 1-2 trades, captura apenas mega-explosões

### Opção B: Trend-Following Simples (V13)
- Manter estratégia V13 (+3.26% em abril)
- Aceitar que dias como 25/04 são **exceção**, não regra
- Foco em consistência, não home-runs

### Opção C: Híbrida
- V13 como base (trend-following)
- Adicionar "modo explosão" quando volume > 10x + RSI > 80
- Alocação menor (10-20% capital) em trades de explosão

---

## 📁 ARQUIVOS GERADOS

1. `sniper_phoenix_v16_sniper.py` - Código da estratégia V16B
2. `backtest_trades_axs_v16_sniper.csv` - Detalhamento dos 37 trades
3. `analise_dia25_v16.py` - Script de análise do dia 25/04
4. `RELATORIO_V16_EXPLOSAO.md` - Este relatório

---

**Data:** Junho 2026  
**Autor:** Sniper Phoenix Team  
**Status:** ✅ Conclusão da fase de análise de explosões
