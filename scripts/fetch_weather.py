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
    url = (
        f"https://api.weather.com/v2/pws/dailysummary/7day"
        f"?stationId={STATION_ID}&format=json&units=m&apiKey={API_KEY}"
    )
    try:
        data = fetch(url)
        summaries = data.get("summaries", [])
        if not summaries:
            return None, None
        today_str = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
        for s in summaries:
            if s.get("obsTimeLocal", "").startswith(today_str):
                m = s.get("metric", {})
                return m.get("tempLow"), m.get("tempHigh")
        m = summaries[-1].get("metric", {})
        return m.get("tempLow"), m.get("tempHigh")
    except Exception as e:
        print(f"Today minmax error: {e}")
        return None, None

def wu_forecast():
    url = (
        f"https://api.weather.com/v3/wx/forecast/daily/5day"
        f"?geocode={LAT},{LON}&format=json&units=m&language=en-IN&apiKey={API_KEY}"
    )
    data = fetch(url)
    highs   = data.get("temperatureMax") or data.get("calendarDayTemperatureMax") or []
    lows    = data.get("temperatureMin") or data.get("calendarDayTemperatureMin") or []
    dow     = data.get("dayOfWeek", [])
    valid   = data.get("validTimeLocal", [])
    precip  = data.get("qpf", [])
    daypart = data.get("daypart", [{}])
    dp      = daypart[0] if daypart else {}
    icons   = dp.get("iconCode") or []
    phrases = dp.get("wxPhraseLong") or dp.get("wxPhraseShort") or []
    days = []
    for i in range(min(5, len(highs))):
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

def wu_history_week(year_offset):
    today  = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    target = today.replace(year=today.year - year_offset)
    start  = (target - timedelta(days=3)).strftime("%Y%m%d")
    end    = (target + timedelta(days=3)).strftime("%Y%m%d")
    url = (
        f"https://api.weather.com/v2/pws/history/daily"
        f"?stationId={STATION_ID}&format=json&units=m&apiKey={API_KEY}"
        f"&startDate={start}&endDate={end}"
    )
    try:
        data = fetch(url)
        print(f"PWS history {year_offset}y keys: {list(data.keys())}")
        obs = data.get("observations", [])
        print(f"PWS history {year_offset}y entries: {len(obs)}")
        if not obs:
            return None
        temps_high = [o["metric"]["tempHigh"]    for o in obs if o.get("metric", {}).get("tempHigh")    is not None]
        temps_low  = [o["metric"]["tempLow"]     for o in obs if o.get("metric", {}).get("tempLow")     is not None]
        temps_avg  = [o["metric"]["tempAvg"]     for o in obs if o.get("metric", {}).get("tempAvg")     is not None]
        precips    = [o["metric"]["precipTotal"] for o in obs if o.get("metric", {}).get("precipTotal") is not None]
        return {
            "year":      today.year - year_offset,
            "temp_avg":  round(sum(temps_avg)/len(temps_avg), 1) if temps_avg  else None,
            "temp_high": round(max(temps_high), 1)               if temps_high else None,
            "temp_low":  round(min(temps_low), 1)                if temps_low  else None,
            "precip":    round(sum(precips), 1)                  if precips    else None
        }
    except Exception as e:
        print(f"PWS history {year_offset}y error: {e}")
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

    result["history_1y"] = wu_history_week(1)
    print(f"History 1y: {result['history_1y']}")

    result["history_2y"] = wu_history_week(2)
    print(f"History 2y: {result['history_2y']}")

    result["generated"] = datetime.now(timezone.utc).isoformat()

    with open(OUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Done — {OUT_FILE} written at {result['generated']}")

if __name__ == "__main__":
    main()
