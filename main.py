import os
import sys
import requests

# 1. 環境變數讀取與安全檢查
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("錯誤：未設定 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID 環境變數！")
    sys.exit(1)

# 2. 取得天氣資料 (Open-Meteo API - 預設桃園經緯度 24.993, 121.301)
def get_weather_data(lat=24.993, lon=121.301):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,precipitation_probability_max&timezone=Asia%2FTaipei"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        max_temp = data["daily"]["temperature_2m_max"][0]
        max_pop = data["daily"]["precipitation_probability_max"][0]
        return max_temp, max_pop
    except requests.RequestException as e:
        print(f"取得天氣 API 失敗: {e}")
        return None, None

# 3. 取得空氣品質資料 (環境部 Open API)
def get_aqi_data():
    url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?language=zh&limit=1000&api_key=e8dd42e6-9b8b-43f8-991e-b3dee723a588"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        records = response.json().get("records", [])

        target_site = next((item for item in records if item.get("sitename") == "桃園"), None)
        if not target_site and records:
            target_site = records[0]

        aqi_value = int(target_site.get("aqi", 0)) if target_site else 0
        return aqi_value
    except Exception as e:
        print(f"取得 AQI API 失敗: {e}")
        return None

# 4. 判斷通勤風險與生成建議
def evaluate_commute_risk(max_temp, max_pop, aqi):
    suggestions = []

    if max_pop is not None and max_pop >= 60:
        suggestions.append("🌧️ 降雨機率達 60% 以上，請記得攜帶雨傘！")

    if max_temp is not None and max_temp >= 33:
        suggestions.append("☀️ 最高溫達 33°C 以上，請注意防曬並多補充水分！")

    if aqi is not None and aqi >= 100:
        suggestions.append("😷 空氣品質 AQI 達 100 以上，建議配戴口罩！")

    if not suggestions:
        suggestions.append("✅ 今日各項指標皆正常，非常適合外出通勤！")

    return suggestions

# 5. 發送 Telegram 訊息
def send_telegram_message(max_temp, max_pop, aqi, suggestions):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    msg_lines = [
        "🚨 <b>【智慧通勤風險通知】</b>",
        "----------------------------------",
        f"🌡️ 預測最高溫：{max_temp if max_temp is not None else 'N/A'} °C",
        f"🌧️ 最高降雨機率：{max_pop if max_pop is not None else 'N/A'} %",
        f"🌬️ 空氣品質 AQI：{aqi if aqi is not None else 'N/A'}",
        "----------------------------------",
        "💡 <b>通勤建議：</b>"
    ]

    for s in suggestions:
        msg_lines.append(f"• {s}")

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": "\n".join(msg_lines),
        "parse_mode": "HTML"
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
        print("Telegram 訊息傳送成功！")
    except requests.RequestException as e:
        print(f"Telegram 訊息傳送失敗: {e}")
        sys.exit(1)

def main():
    print("開始執行通勤風險評估...")
    max_temp, max_pop = get_weather_data()
    aqi = get_aqi_data()

    print(f"數據取得結果 - 溫: {max_temp}°C, 雨: {max_pop}%, AQI: {aqi}")

    suggestions = evaluate_commute_risk(max_temp, max_pop, aqi)
    send_telegram_message(max_temp, max_pop, aqi, suggestions)

if __name__ == "__main__":
    main()
