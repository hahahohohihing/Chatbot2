import requests
import time
import pandas as pd
# import time
import pyupbit
import os
from dotenv import load_dotenv


# .env 파일에서 키 불러오기
load_dotenv()
access = os.getenv('UPBIT_ACCESS_KEY')
secret = os.getenv('UPBIT_SECRET_KEY')

upbit = pyupbit.Upbit(access, secret)

#시장가 매수 함수
def buy_market(symbol='KRW-DOGE', krw_amount=1000):
    try:
        res = upbit.buy_market_order(symbol, krw_amount)
        print('매수 주문 전송 완료', res)
        return res
    except Exception as e:
        print ('매수 주문 실패:', e)
        return None

if price < lower_band and current_rsi < 30 and current_volume > avg_volume:
    now = time.time()
    last_alert_time = 0
    if now - last_alert_time > alert_cooldown:
        # 알림 + 자동 매수!
        send_telegram(f'DOGE 조건 충족!\n 자동 매수 시도!\n가격: {price}\nRSI: {current_rsi:.2f}\n거래량: {current_volume:.2f}')
        # 1,000원어치 시장가 매수
        buy_market('KRW-DOGE', 1000)
        last_alert_time = now
