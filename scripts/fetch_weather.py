import urllib.request
import urllib.error
import json
import os
from datetime import datetime, timedelta, timezone

API_KEY    = "c481811673aa4a0c81811673aa9a0ccd"
STATION_ID = "IKUMHA3"
LAT        = 31.3167
LON        = 77.1833
OUT_FILE   = "docs/weather.json"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SarogaWeather/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def wind_direction(deg):
    if deg is None:
        return ""
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(deg / 22.5) % 16]

def wu_current():
    url = (
        f"https://api.weather.com/v2/pws/observations/current"
        f"?stationId={STATION_ID}&format=json&units=m&apiKey={API_KEY}"
    )
    data = fetch(url)
    obs  = data["observations"][0]
    m    = obs.get("metric", {})
    return {
        "temp":         m.get("temp"),
        "feels_like":   m.get("windChill") or m.get("heatIndex") or m.get("temp"),
        "humidity":     obs.get("humidity"),
        "wind_kph":     m.get("windSpeed"),
        "wind_dir":     obs.get("winddir"),
        "pressure":     m.get("pressure"),
        "precip_today": m.get("precipTotal"),
        "uv":           obs.get("uv"),
        "condition":    "",
        "updated":      obs.get("obsTimeLocal", "")
    }

def wu_today_minmax():
    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y%m%d")
    url = (
        f"https://api.weather.com/v1/pwshistory/daily/7day"
        f"?stationId={STATION_ID}&format=json&units=m&apiKey={API_KEY}"
        f"&startDate={today}&endDate={today}"
    )
    try:
        data = fetch(url)
        obs  = data.get("observations", [])
        if not obs:
            print("Today minmax: no observations returned")
            return None, None
        m = obs[0].get("metric", {})
        return m.get("tempLow"), m.get("tempHigh")
    except Exception as e:
        print(f"Today minmax error: {e}")
        return None, None

def wu_forecast():
    url = (
        f"https://api.weather.com/v3/wx/forecast/daily/7day"
        f"?geocode={LAT},{LON}&format=json&units=m&language=en-IN&apiKey={API_KEY}"
    )
    data = fetch(url)
    print(f"WU forecast keys: {list(data.keys())}")

    highs   = data.get("temperatureMax") or data.get("calendarDayTemperatureMax") or []
    lows    = data.get("temperatureMin") or data.get("calendarDayTemperatureMin") or []
    dow     = data.get("dayOfWeek", [])
    valid   = data.get("validTimeLocal", [])
    precip  = data.get("qpf", [])
    daypart = data.get("daypart", [{}])
    dp      = daypart[0] if daypart else {}
    icons   = dp.get("iconCode") or []
    phrases = dp.get("wxPhraseLong") or dp.get("wxPhraseShort") or []

    print(f"WU highs: {highs[:4]}")
    print(f"WU lows:  {lows[:4]}")
    print(f"WU dow:   {dow[:4]}")
    print(f"WU icons (first 8): {icons[:8]}")
    print(f"WU phrases (first 4): {phrases[:4]}")

    days = []
    for i in range(min(7, len(highs))):
        date_str  = valid[i][:10] if valid and i < len(valid) else ""
        dow_str   = dow[i] if dow and i < len(dow) else ""
        icon_idx  = i * 2
        icon_code = icons[icon_idx] if icons and icon_idx < len(icons) else None
        phrase    = phrases[icon_idx] if phrases and icon_idx < len(phrases) else ""
        days.append({
            "date":    date_str,
            "dow":     dow_str,
            "high":    highs[i],
            "low":     lows[i],
            "desc":    phrase or "",
            "icon_wu": icon_code,
            "precip":  precip[i] if precip and i < len(precip) else 0
        })
    return days

def open_meteo_history_week(year_offset):
    today  = datetime.now(timezone.utc)
    target = today.replace(year=today.year - year_offset)
    start  = (target - timedelta(days=3)).strftime("%Y-%m-%d")
    end    = (target + timedelta(days=3)).strftime("%Y-%m-%d")
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LAT}&longitude={LON}"
        f"&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum"
        f"&timezone=Asia%2FKolkata"
        f"&start_date={start}&end_date={end}"
    )
    try:
        data    = fetch(url)
        d       = data["daily"]
        means   = [v for v in d["temperature_2m_mean"] if v is not None]
        highs   = [v for v in d["temperature_2m_max"]  if v is not None]
        lows    = [v for v in d["temperature_2m_min"]  if v is not None]
        precips = [v for v in d["precipitation_sum"]   if v is not None]
        return {
            "year":      today.year - year_offset,
            "temp_avg":  round(sum(means)/len(means), 1) if means  else None,
            "temp_high": round(max(highs), 1)            if highs  else None,
            "temp_low":  round(min(lows), 1)             if lows   else None,
            "precip":    round(sum(precips), 1)          if precips else None
        }
    except Exception as e:
        print(f"History {year_offset}y error: {e}")
        return None

def main():
    os.makedirs("docs", exist_ok=True)
    result = {}

    try:
        current = wu_current()
        current["wind_dir_label"] = wind_direction(current.get("wind_dir"))
        t_low, t_high = wu_today_minmax()
        current["today_low"]  = t_low
        current["today_high"] = t_high
        result["current"] = current
        print(f"Current: {current['temp']}°C, low {t_low}, high {t_high}")
    except Exception as e:
        print(f"Current error: {e}")
        result["current_error"] = str(e)

    try:
        result["forecast"] = wu_forecast()
        print(f"Forecast: {len(result['forecast'])} days from WU")
    except Exception as e:
        print(f"WU Forecast error: {e}")
        result["forecast_error"] = str(e)
        result["forecast"] = []

    result["history_1y"] = open_meteo_history_week(1)
    print(f"History 1y: {result['history_1y']}")

    result["history_2y"] = open_meteo_history_week(2)
    print(f"History 2y: {result['history_2y']}")

    result["generated"] = datetime.now(timezone.utc).isoformat()

    with open(OUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Done — {OUT_FILE} written at {result['generated']}")

if __name__ == "__main__":
    main()
