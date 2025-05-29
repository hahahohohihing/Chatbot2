import pyupbit
import os
from dotenv import load_dotenv

load_dotenv()

access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")
upbit = pyupbit.Upbit(access, secret)

try:
    result = upbit.buy_market_order("KRW-DOGE", 5000)
    print("🛒 매수 결과:", result)
except Exception as e:
    print("❌ 매수 실패:", e)
