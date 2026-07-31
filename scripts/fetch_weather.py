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
    highs   = data.get("calendarDayTemperatureMax") or data.get("temperatureMax") or []
    lows    = data.get("calendarDayTemperatureMin") or data.get("temperatureMin") or []
    dow     = data.get("dayOfWeek", [])
    valid   = data.get("validTimeLocal", [])
    # qpf is a top-level array with one value per day — not inside daypart
    precip  = data.get("qpf") or []
    daypart = data.get("daypart", [{}])
    dp      = daypart[0] if daypart else {}
    icons   = dp.get("iconCode") or []
    phrases = dp.get("wxPhraseLong") or dp.get("wxPhraseShort") or []

    days = []
    for i in range(min(5, len(highs))):
        date_str  = valid[i][:10] if valid and i < len(valid) else ""
        dow_str   = dow[i] if dow and i < len(dow) else ""
        # daypart array has 2 entries per day: [day0, night0, day1, night1, ...]
        day_idx   = i * 2
        night_idx = i * 2 + 1

        # Icon: prefer daytime, fall back to night
        icon_code = None
        if icons:
            if day_idx < len(icons) and icons[day_idx] is not None:
                icon_code = icons[day_idx]
            elif night_idx < len(icons) and icons[night_idx] is not None:
                icon_code = icons[night_idx]

        # Phrase: prefer daytime, fall back to night
        phrase = ""
        if phrases:
            if day_idx < len(phrases) and phrases[day_idx]:
                phrase = phrases[day_idx]
            elif night_idx < len(phrases) and phrases[night_idx]:
                phrase = phrases[night_idx]

        # qpf is top-level per day, not per daypart
        day_precip = precip[i] if precip and i < len(precip) and precip[i] is not None else 0

        days.append({
            "date":    date_str,
            "dow":     dow_str,
            "high":    highs[i],
            "low":     lows[i],
            "desc":    phrase,
            "icon_wu": icon_code,
            "precip":  round(day_precip, 1)
        })
        print(f"  Day {i} ({dow_str}): high={highs[i]}, low={lows[i]}, precip={day_precip}mm, icon={icon_code}, desc={phrase}")
    return days

def wu_history_week(year_offset):
    today  = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    target = today.replace(year=today.year - year_offset)
    monday = target - timedelta(days=target.weekday())
    sunday = monday + timedelta(days=6)
    start  = monday.strftime("%Y%m%d")
    end    = sunday.strftime("%Y%m%d")
    url = (
        f"https://api.weather.com/v2/pws/history/daily"
        f"?stationId={STATION_ID}&format=json&units=m&apiKey={API_KEY}"
        f"&startDate={start}&endDate={end}"
    )
    try:
        data = fetch(url)
        obs  = data.get("observations", [])
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

def wu_month_facts(month):
    ist = timezone(timedelta(hours=5, minutes=30))
    current_year = datetime.now(ist).year
    coldest_temp = None
    coldest_date = None
    wettest_mm   = None
    wettest_date = None
    for yr in [current_year, current_year - 1, current_year - 2]:
        if month == 12:
            last_day = 31
        else:
            next_month_first = datetime(yr, month + 1, 1, tzinfo=ist)
            last_day = (next_month_first - timedelta(days=1)).day
        start = f"{yr}{month:02d}01"
        end   = f"{yr}{month:02d}{last_day:02d}"
        url = (
            f"https://api.weather.com/v2/pws/history/daily"
            f"?stationId={STATION_ID}&format=json&units=m&apiKey={API_KEY}"
            f"&startDate={start}&endDate={end}"
        )
        try:
            data = fetch(url)
            for obs in data.get("observations", []):
                m    = obs.get("metric", {})
                date = obs.get("obsTimeLocal", "")[:10]
                low  = m.get("tempLow")
                rain = m.get("precipTotal")
                if low is not None and (coldest_temp is None or low < coldest_temp):
                    coldest_temp = low
                    coldest_date = date
                if rain is not None and rain > 0 and (wettest_mm is None or rain > wettest_mm):
                    wettest_mm   = rain
                    wettest_date = date
        except Exception as e:
            print(f"Month facts {yr}-{month:02d} error: {e}")
    return {
        "month":        month,
        "coldest_temp": coldest_temp,
        "coldest_date": coldest_date,
        "wettest_mm":   wettest_mm,
        "wettest_date": wettest_date
    }

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
        print(f"Current
