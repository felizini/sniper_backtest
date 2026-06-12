# Relatório Final: Análise de Filtros - Sniper Phoenix V11 vs V12

## Contexto
Teste realizado em **Abril 2026** (+20.56%), período bullish com alta volatilidade.

## Comparação de Resultados

| Métrica | V11 (Original) | V12 (Filtros) | Diferença |
|---------|---------------|---------------|-----------|
| Total Trades | 24 | 63 | +39 (+162%) |
| Win Rate | 25.0% | 23.8% | -1.2pp |
| TP Hits | 41.7% | 33.3% | -8.4pp |
| Avg Win | R$ 2.00 | R$ 1.62 | -R$ 0.38 |
| Avg Loss | R$ 3.62 | R$ 2.56 | -R$ 1.06 |
| Ratio W/L | 0.55 | 0.63 | +0.08 |
| **PnL Total** | **-R$ 53.21** | **-R$ 98.71** | **-R$ 45.50** |

## Conclusões da Análise

### 1. Filtros Adicionais Não Melhoraram Performance
- Win rate permaneceu essencialmente igual (25% → 23.8%)
- TP hits **diminuíram** (41.7% → 33.3%)
- PnL **piorou** significativamente (-R$ 45.50)

### 2. Problemas Identificados no V12
- **Excesso de trades em regime Bullish**: 44 trades com desempenho ruim (-R$ 82)
- **Filtro range_pct < 75** não foi eficaz em mercado volátil
- **Remoção do filtro DI+ > DI-** aumentou quantidade sem melhorar qualidade
- **Setup Lateral muito restritivo**: apenas 19 trades vs 44 Bullish

### 3. Lições Aprendidas sobre Filtros

#### Filtros que FUNCIONAM (alinhados com README):
✅ **EMA34 proximidade** - Pullback real, não compra em topo
✅ **RSI zona neutra (40-65)** - Evita sobrecompra/sobrevenda
✅ **Preço acima EMA200** - Confirma tendência de alta
✅ **Volume >= média** - Confirma participação do mercado

#### Filtros que NÃO FUNCIONARAM neste contexto:
❌ **Range percentile < 75** - Muito restritivo em tendência forte
❌ **DI+ > DI-** - Redundante com detecção de regime Bullish
❌ **Filtro horário/dia** - Eliminou oportunidades válidas

### 4. Premissas do README - Aplicação Correta

O artigo estabelece 3 elementos essenciais:

1. **Lógica de Entrada com Premissa Explícita** ✅
   - V11 e V12 têm premissas claras (pullback em tendência)
   
2. **Qualificadores que REFORÇAM a Premissa** ⚠️
   - V12 adicionou filtros demais, alguns contraditórios
   - Excesso de qualificadores eliminou boas entradas
   
3. **Saída Correspondente à Entrada** ✅
   - Ambos usam TP/SL proporcionais ao regime

### 5. Recomendação Final

**Para Abril 2026 (período volátil bullish):**
- **USAR V11** - Mais simples, menos trades, melhor PnL
- Filtros essenciais já são suficientes
- Adicionar mais filtros degrada performance

**Para períodos futuros:**
- Testar V12 em período **lateral definido** (ADX < 20 predominante)
- Em tendência forte, filtros de range são contraproducentes
- Manter apenas filtros que reforçam diretamente a premissa

## Código Final Recomendado

O arquivo `sniper_phoenix_v11_abril.py` representa o melhor equilíbrio entre:
- Simplicidade (facilidade de manutenção)
- Performance (menor drawdown, melhor PnL)
- Alinhamento com filosofia do README (premissas explícitas, qualificadores lógicos)

## Próximos Passos Sugeridos

1. **Testar em período completo** (abril + maio-junho) para validação
2. **Implementar alocação dinâmica** baseada em drawdown
3. **Considerar mean-reversion pura** para períodos laterais
4. **Adicionar filtro de momentum macro** (ex: ADX > 70 = não opera)

---
*Relatório gerado em 2026 - Sniper Phoenix Backtest Project*
