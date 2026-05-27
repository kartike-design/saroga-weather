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
        "temp":        m.get("temp"),
        "feels_like":  m.get("windChill") or m.get("heatIndex") or m.get("temp"),
        "humidity":    obs.get("humidity"),
        "wind_kph":    m.get("windSpeed"),
        "wind_dir":    obs.get("winddir"),
        "pressure":    m.get("pressure"),
        "precip_today":m.get("precipTotal"),
        "uv":          obs.get("uv"),
        "condition":   "",
        "updated":     obs.get("obsTimeLocal", "")
    }

def wind_direction(deg):
    if deg is None:
        return ""
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[round(deg / 22.5) % 16]

def wu_history_day(date_str):
    url = (
        f"https://api.weather.com/v1/pwshistory/daily/7day"
        f"?stationId={STATION_ID}&format=json&units=m&apiKey={API_KEY}"
        f"&startDate={date_str}&endDate={date_str}"
    )
    try:
        data = fetch(url)
        obs = data.get("observations", [])
        if not obs:
            return None
        o = obs[0]
        m = o.get("metric", {})
        return {
            "date":      date_str,
            "temp_avg":  m.get("tempAvg"),
            "temp_high": m.get("tempHigh"),
            "temp_low":  m.get("tempLow"),
            "precip":    m.get("precipTotal")
        }
    except Exception:
        return None

def wu_today_minmax():
    url = (
        f"https://api.weather.com/v2/pws/observations/all/1day"
        f"?stationId={STATION_ID}&format=json&units=m&apiKey={API_KEY}"
    )
    try:
        data = fetch(url)
        obs = data.get("observations", [])
        if not obs:
            return None, None, None
        temps = [o["metric"]["temp"] for o in obs if o.get("metric", {}).get("temp") is not None]
        precips = [o["metric"].get("precipTotal", 0) or 0 for o in obs]
        return min(temps), max(temps), max(precips)
    except Exception:
        return None, None, None

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
            "date":    d["time"][i],
            "code":    d["weathercode"][i],
            "high":    d["temperature_2m_max"][i],
            "low":     d["temperature_2m_min"][i],
            "precip":  d["precipitation_sum"][i]
        })
    return days

def history_week(year_offset):
    today = datetime.now(timezone.utc)
    target = today.replace(year=today.year - year_offset)
    days = []
    for i in range(-3, 4):
        d = target + timedelta(days=i)
        result = wu_history_day(d.strftime("%Y%m%d"))
        if result:
            days.append(result)
    if not days:
        return None
    temps = [d["temp_avg"] for d in days if d["temp_avg"] is not None]
    highs = [d["temp_high"] for d in days if d["temp_high"] is not None]
    lows  = [d["temp_low"] for d in days if d["temp_low"] is not None]
    precips = [d["precip"] for d in days if d["precip"] is not None]
    return {
        "year":      today.year - year_offset,
        "temp_avg":  round(sum(temps)/len(temps), 1) if temps else None,
        "temp_high": round(max(highs), 1) if highs else None,
        "temp_low":  round(min(lows), 1) if lows else None,
        "precip":    round(sum(precips), 1) if precips else None
    }

def main():
    os.makedirs("docs", exist_ok=True)
    result = {}

    try:
        current = wu_current()
        current["wind_dir_label"] = wind_direction(current.get("wind_dir"))
        t_low, t_high, precip_today = wu_today_minmax()
        current["today_low"]   = t_low
        current["today_high"]  = t_high
        if precip_today is not None:
            current["precip_today"] = precip_today
        result["current"] = current
    except Exception as e:
        result["current_error"] = str(e)

    try:
        result["forecast"] = open_meteo_forecast()
    except Exception as e:
        result["forecast_error"] = str(e)

    try:
        result["history_1y"] = history_week(1)
    except Exception as e:
        result["history_1y"] = None

    try:
        result["history_2y"] = history_week(2)
    except Exception as e:
        result["history_2y"] = None

    result["generated"] = datetime.now(timezone.utc).isoformat()

    with open(OUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Done — {OUT_FILE} written at {result['generated']}")

if __name__ == "__main__":
    main()
