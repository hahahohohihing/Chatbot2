import pyupbit
import os
from dotenv import load_dotenv

load_dotenv()
access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")

upbit = pyupbit.Upbit(access, secret)

try:
    krw = upbit.get_balance("KRW")
    if krw is not None:
        print("✅ 연결 성공, KRW 잔고:", krw)
    else:
        print("❌ 연결 실패: None 반환 (IP 또는 키 문제)")
except Exception as e:
    print("❗ 예외 발생:", e)
