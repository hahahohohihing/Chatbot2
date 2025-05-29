import requests

# 현재 가격 조회

url = 'https://api.upbit.com/v1/ticker?markets=KRW-DOGE'
response = requests.get(url)
price = response.json()[0]['trade_price']

print('현재 DOGE 가격 =', price)




import pandas as pd
import numpy as np

# 예시 가격

prices = [300, 310, 320, 330, 340, 350, 360, 370, 380, 390, 210, 220, 230, 240, 250, 260, 270, 280, 290]
df = pd.DataFrame(prices, columns=['close'])

df["MA20"] = df["close"].rolling(window=20).mean()
df["STD"] = df["close"].rolling(window=20).std()
df["lower_band"] = df["MA20"] - 2 * df["STD"]

# 조건 검사

if prices[-1] < df['lower_band'].iloc[-1]:
  print('볼린저 하단')
else:
  print('아직 돌파 아님')
