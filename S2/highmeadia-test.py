from dotenv import load_dotenv
import os

dotenv_path = "/Users/hahahohohihing/bot/S2/.env"
load_dotenv(dotenv_path)

print("access =", os.getenv("UPBIT_ACCESS_KEY"))
print("secret =", os.getenv("UPBIT_SECRET_KEY"))

