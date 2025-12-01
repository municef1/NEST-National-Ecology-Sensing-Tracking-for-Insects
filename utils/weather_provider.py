"""
날씨 정보 제공 모듈
위치(위도, 경도)와 시간 정보를 기반으로 날씨 데이터를 가져옵니다.
Open-Meteo API를 사용합니다 (무료, API 키 불필요)
"""

import requests
from datetime import datetime
from typing import Dict, Optional


def get_weather_info(lat: float, lon: float, datetime_str: str = None) -> Optional[Dict]:
    """
    위치와 시간 정보를 기반으로 날씨 정보 가져오기
    
    Args:
        lat: 위도
        lon: 경도
        datetime_str: 촬영 일시 (YYYY-MM-DD HH:MM:SS 형식), None이면 현재 날씨
    
    Returns:
        dict: 날씨 정보 {
            'temperature': 온도 (℃),
            'weather_description': 날씨 설명,
            'weather_code': 날씨 코드,
            'humidity': 습도 (%),
            'wind_speed': 풍속 (km/h),
            'datetime': 날씨 시간
        } 또는 None
    """
    if lat is None or lon is None:
        return None
    
    try:
        # datetime_str 파싱
        target_date = None
        if datetime_str:
            try:
                target_date = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    target_date = datetime.strptime(datetime_str.split()[0], "%Y-%m-%d")
                except:
                    pass
        
        # 과거 날씨 데이터가 필요한 경우 (촬영 시간이 과거인 경우)
        if target_date and target_date < datetime.now():
            # Open-Meteo Historical Weather API 사용
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": target_date.strftime("%Y-%m-%d"),
                "end_date": target_date.strftime("%Y-%m-%d"),
                "hourly": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "Asia/Seoul"
            }
        else:
            # 현재 날씨 데이터
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "Asia/Seoul"
            }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if target_date and target_date < datetime.now():
            # 과거 날씨 데이터 처리
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            temperatures = hourly.get("temperature_2m", [])
            humidities = hourly.get("relative_humidity_2m", [])
            weather_codes = hourly.get("weather_code", [])
            wind_speeds = hourly.get("wind_speed_10m", [])
            
            if not times:
                return None
            
            # 촬영 시간에 가장 가까운 시간 찾기
            target_hour = target_date.hour
            closest_idx = 0
            min_diff = abs(int(times[0].split("T")[1].split(":")[0]) - target_hour) if "T" in times[0] else 24
            
            for i, time_str in enumerate(times):
                if "T" in time_str:
                    hour = int(time_str.split("T")[1].split(":")[0])
                    diff = abs(hour - target_hour)
                    if diff < min_diff:
                        min_diff = diff
                        closest_idx = i
            
            temperature = temperatures[closest_idx] if closest_idx < len(temperatures) else None
            humidity = humidities[closest_idx] if closest_idx < len(humidities) else None
            weather_code = weather_codes[closest_idx] if closest_idx < len(weather_codes) else None
            wind_speed = wind_speeds[closest_idx] if closest_idx < len(wind_speeds) else None
            weather_time = times[closest_idx] if closest_idx < len(times) else None
        else:
            # 현재 날씨 데이터 처리
            current = data.get("current", {})
            temperature = current.get("temperature_2m")
            humidity = current.get("relative_humidity_2m")
            weather_code = current.get("weather_code")
            wind_speed = current.get("wind_speed_10m")
            weather_time = current.get("time")
        
        if temperature is None:
            return None
        
        # 날씨 코드를 설명으로 변환
        weather_description = get_weather_description(weather_code)
        
        return {
            'temperature': round(temperature, 1),
            'weather_description': weather_description,
            'weather_code': weather_code,
            'humidity': round(humidity, 1) if humidity else None,
            'wind_speed': round(wind_speed * 3.6, 1) if wind_speed else None,  # m/s -> km/h 변환
            'datetime': weather_time
        }
    except Exception as e:
        print(f"날씨 정보 가져오기 오류: {str(e)}")
        return None


def get_weather_description(weather_code: int) -> str:
    """
    WMO Weather Interpretation Codes (WW)를 한국어 설명으로 변환
    
    Args:
        weather_code: WMO 날씨 코드
    
    Returns:
        str: 날씨 설명
    """
    if weather_code is None:
        return "정보 없음"
    
    weather_map = {
        0: "맑음",
        1: "대체로 맑음",
        2: "부분적으로 흐림",
        3: "흐림",
        45: "안개",
        48: "서리 안개",
        51: "약한 이슬비",
        53: "보통 이슬비",
        55: "강한 이슬비",
        56: "약한 얼음 이슬비",
        57: "강한 얼음 이슬비",
        61: "약한 비",
        63: "보통 비",
        65: "강한 비",
        66: "약한 얼음 비",
        67: "강한 얼음 비",
        71: "약한 눈",
        73: "보통 눈",
        75: "강한 눈",
        77: "눈알갱이",
        80: "약한 소나기",
        81: "보통 소나기",
        82: "강한 소나기",
        85: "약한 눈 소나기",
        86: "강한 눈 소나기",
        95: "천둥번개",
        96: "천둥번개와 우박",
        99: "강한 천둥번개와 우박"
    }
    
    return weather_map.get(weather_code, f"날씨 코드 {weather_code}")


def get_weather_icon(weather_code: int) -> str:
    """
    날씨 코드에 따른 이모지 아이콘 반환
    
    Args:
        weather_code: WMO 날씨 코드
    
    Returns:
        str: 날씨 이모지
    """
    if weather_code is None:
        return "❓"
    
    # 날씨 코드 범위별 아이콘
    if weather_code == 0:
        return "☀️"  # 맑음
    elif weather_code == 1:
        return "🌤️"  # 대체로 맑음
    elif weather_code in [2, 3]:
        return "☁️"  # 흐림
    elif weather_code in [45, 48]:
        return "🌫️"  # 안개
    elif weather_code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67]:
        return "🌧️"  # 비
    elif weather_code in [71, 73, 75, 77, 85, 86]:
        return "❄️"  # 눈
    elif weather_code in [80, 81, 82]:
        return "🌦️"  # 소나기
    elif weather_code in [95, 96, 99]:
        return "⛈️"  # 천둥번개
    else:
        return "🌤️"  # 기본값

