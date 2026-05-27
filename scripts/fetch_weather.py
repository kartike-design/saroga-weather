import urllib.request
import urllib.error
import json
import os
from datetime import datetime, timedelta, timezone

API_KEY = "c481811673aa4a0c81811673aa9a0ccd"
STATION_ID = "IKUMHA3"
LAT = 31.3167
LON = 77.1833
OUT_FILE = "docs/weather.json"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SarogaWeather/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def wu_current():
    url = (
        f"https://api.weather.com/v2/pws/observations/current"
        f"?stationId={STATION_ID}&format=json&units=m&apiKey={API_KEY}"
    )
    data = fetch(url)
    obs = data["observations"][0]
    m = obs.get("metric", {})
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

def wind_direction(deg):
    if deg is None:
        return ""
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(deg / 22.5) % 16]

def open_meteo_forecast():
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&timezone=Asia%2FKolkata&forecast_days=7"
    )
    data = fetch(url)
    d = data["daily"]
    days = []
    for i in range(7):
        days.append({
            "date":   d["time"][i],
            "code":   d["weathercode"][i],
            "high":   d["temperature_2m_max"][i],
            "low":    d["temperature_2m_min"][i],
            "precip": d["precipitation_sum"][i]
        })
    return days

def open_meteo_today_minmax():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        f"&daily=temperature_2m_max,temperature_2m_min"
        f"&timezone=Asia%2FKolkata&forecast_days=1"
    )
    try:
        data = fetch(url)
        d = data["daily"]
        return d["temperature_2m_min"][0], d["temperature_2m_max"][0]
    except Exception:
        return None, None

def open_meteo_history_week(year_offset):
    today = datetime.now(timezone.utc)
    target = today.replace(year=today.year - year_offset)
    start = (target - timedelta(days=3)).strftime("%Y-%m-%d")
    end   = (target + timedelta(days=3)).strftime("%Y-%m-%d")
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LAT}&longitude={LON}"
        f"&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum"
        f"&timezone=Asia%2FKolkata"
        f"&start_date={start}&end_date={end}"
    )
    try:
        data = fetch(url)
        d = data["daily"]
        means  = [v for v in d["temperature_2m_mean"] if v is not None]
        highs  = [v for v in d["temperature_2m_max"]  if v is not None]
        lows   = [v for v in d["temperature_2m_min"]  if v is not None]
        precips= [v for v in d["precipitation_sum"]   if v is not None]
        return {
            "year":      today.year - year_offset,
            "temp_avg":  round(sum(means)/len(means), 1) if means else None,
            "temp_high": round(max(highs), 1)            if highs else None,
            "temp_low":  round(min(lows), 1)             if lows  else None,
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
        t_low, t_high = open_meteo_today_minmax()
        current["today_low"]  = t_low
        current["today_high"] = t_high
        result["current"] = current
        print(f"Current: {current['temp']}°C, low {t_low}, high {t_high}")
    except Exception as e:
        print(f"Current error: {e}")
        result["current_error"] = str(e)

    try:
        result["forecast"] = open_meteo_forecast()
        print(f"Forecast: {len(result['forecast'])} days")
    except Exception as e:
        print(f"Forecast error: {e}")
        result["forecast_error"] = str(e)

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
