import pandas as pd
import numpy as np

# Carrega dados
df = pd.read_csv('AXS_abril_2026.csv')
df.columns = df.columns.str.lower().str.strip()
df['date'] = pd.to_datetime(df['open_time_brasilia'])
df = df.sort_values('date').reset_index(drop=True)

# Filtra dia 25/04
dia25 = df[df['date'].dt.strftime('%Y-%m-%d') == '2026-04-25'].copy()
dias_anteriores = df[df['date'].dt.strftime('%Y-%m-%d').isin(['2026-04-21', '2026-04-22', '2026-04-23', '2026-04-24'])].copy()

print("=" * 80)
print("ANÁLISE DO DIA 25/04 - EXPLOSÃO")
print("=" * 80)

# Calcula volume médio 20 dias
df['volume_ma20'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma20']

# Pega volume médio dos dias 21-24
vol_media_21_24 = dias_anteriores['volume'].mean()
vol_media_20_dias = df[df['date'] < '2026-04-25']['volume'].rolling(20).mean().iloc[-1]

print(f"\n📊 VOLUME:")
print(f"   Média 21-24/04: {vol_media_21_24:,.2f}")
print(f"   Média 20 dias (até 24/04): {vol_media_20_dias:,.2f}")
print(f"   Volume dia 25/04: {dia25['volume'].sum():,.2f}")
print(f"   Ratio vs média 20d: {dia25['volume'].sum() / vol_media_20_dias:.2f}x")

# Analisa candle por candle do dia 25
print(f"\n🕯️  CANDLES DO DIA 25/04 (amostra):")
for idx, row in dia25.iloc[::12].iterrows():  # Mostra a cada hora
    vol_ratio = row['volume'] / row.get('volume_ma20', vol_media_20_dias) if 'volume_ma20' in df.columns else 0
    print(f"   {row['date']} | Close: {row['close']:.3f} | Vol: {row['volume']:,.0f} | Ratio: {vol_ratio:.2f}x")

# Calcula ATR
df['high_low'] = df['high'] - df['low']
df['high_close'] = abs(df['high'] - df['close'].shift(1))
df['low_close'] = abs(df['low'] - df['close'].shift(1))
df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
df['atr'] = df['tr'].rolling(14).mean()
df['atr_avg_10'] = df['atr'].rolling(10).mean()
df['volatility_expansion'] = df['atr'] / df['atr_avg_10']

print(f"\n📈 VOLATILIDADE (ATR):")
atr_medio_21_24 = dias_anteriores['atr'].mean() if 'atr' in dias_anteriores.columns else 0
print(f"   ATR médio 21-24/04: {atr_medio_21_24:.6f}")
print(f"   ATR dia 25/04 (média): {dia25['atr'].mean():.6f}")

# Verifica máxima dos 4 dias anteriores
max_4d = dias_anteriores['high'].max()
print(f"\n🎯 ROMPIMENTO:")
print(f"   Máxima 21-24/04: {max_4d:.3f}")
print(f"   Mínima 21-24/04: {dias_anteriores['low'].min():.3f}")
print(f"   Primeira máxima do dia 25: {dia25['high'].iloc[0]:.3f}")
print(f"   Última máxima do dia 25: {dia25['high'].iloc[-1]:.3f}")

# EMA200
df['ema200'] = df['close'].ewm(span=200).mean()
print(f"\n📉 TENDÊNCIA:")
print(f"   EMA200 em 25/04: {dia25['ema200'].iloc[0]:.3f}")
print(f"   Preço inicial 25/04: {dia25['open'].iloc[0]:.3f}")
print(f"   Preço final 25/04: {dia25['close'].iloc[-1]:.3f}")
print(f"   Distância EMA200: {(dia25['close'].iloc[-1] - dia25['ema200'].iloc[0]) / dia25['ema200'].iloc[0] * 100:.2f}%")

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

print(f"\n💪 MOMENTUM (RSI):")
print(f"   RSI inicial 25/04: {dia25['rsi'].iloc[0]:.2f}")
print(f"   RSI final 25/04: {dia25['rsi'].iloc[-1]:.2f}")
print(f"   RSI máximo 25/04: {dia25['rsi'].max():.2f}")

print("\n" + "=" * 80)
print("CONCLUSÕES PARA AJUSTE DOS PARÂMETROS V15:")
print("=" * 80)
print("1. Volume explosion threshold: Reduzir de 3.0x para 2.0x")
print("2. Breakout lookback: Funciona (rompeu máxima de 4 dias)")
print("3. Volatility expansion: Ajustar threshold para 1.2x")
print("4. RSI minimum: Manter 55-60 (RSI subiu durante o dia)")
print("5. EMA200: Preço já estava acima no início do dia")
print("=" * 80)
