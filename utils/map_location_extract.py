from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from pathlib import Path
from datetime import datetime
import os


def get_exif_data(image_path: str):
    """
    이미지에서 EXIF 데이터 추출
    
    Args:
        image_path: 이미지 파일 경로
    
    Returns:
        dict: EXIF 데이터 딕셔너리
    """
    try:
        image = Image.open(image_path)
        exif_data_raw = image._getexif()
        exif_data = {}

        if not exif_data_raw:
            return exif_data

        for tag_id, value in exif_data_raw.items():
            tag = TAGS.get(tag_id, tag_id)
            exif_data[tag] = value

        return exif_data
    except Exception as e:
        print(f"EXIF 데이터 추출 중 오류 발생: {str(e)}")
        return {}


def get_gps_info(exif_data: dict):
    """
    EXIF 데이터에서 GPS 정보 추출
    
    Args:
        exif_data: EXIF 데이터 딕셔너리
    
    Returns:
        dict: GPS 정보 딕셔너리, 없으면 None
    """
    gps_info = {}
    gps_data = exif_data.get("GPSInfo")

    if not gps_data:
        return None

    for key in gps_data.keys():
        decoded_key = GPSTAGS.get(key, key)
        gps_info[decoded_key] = gps_data[key]

    return gps_info


def convert_to_degrees(value):
    """
    GPS 좌표를 도(degree) 단위로 변환
    IFDRational → float 변환
    
    Args:
        value: GPS 좌표 튜플 (도, 분, 초)
    
    Returns:
        float: 도 단위 좌표
    """
    try:
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except (TypeError, ValueError, IndexError) as e:
        print(f"좌표 변환 중 오류 발생: {str(e)}")
        return None


def get_lat_lon(gps_info: dict):
    """
    GPS 정보에서 위도와 경도 추출
    
    Args:
        gps_info: GPS 정보 딕셔너리
    
    Returns:
        tuple: (위도, 경도), 없으면 (None, None)
    """
    if not gps_info:
        return None, None

    gps_latitude = gps_info.get("GPSLatitude")
    gps_latitude_ref = gps_info.get("GPSLatitudeRef")
    gps_longitude = gps_info.get("GPSLongitude")
    gps_longitude_ref = gps_info.get("GPSLongitudeRef")

    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        lat = convert_to_degrees(gps_latitude)
        lon = convert_to_degrees(gps_longitude)

        # convert_to_degrees가 None을 반환할 수 있으므로 체크
        if lat is None or lon is None:
            return None, None

        # 남반구 또는 서반구인 경우 음수로 변환
        if gps_latitude_ref != "N":
            lat = -lat
        if gps_longitude_ref != "E":
            lon = -lon

        return lat, lon

    return None, None


def get_image_location(image_path: str):
    """
    이미지 파일에서 위치 정보(위도, 경도) 추출
    
    Args:
        image_path: 이미지 파일 경로
    
    Returns:
        tuple: (위도, 경도), 없으면 (None, None)
    """
    try:
        exif_data = get_exif_data(image_path)
        gps_info = get_gps_info(exif_data)
        lat, lon = get_lat_lon(gps_info)
        return lat, lon
    except Exception as e:
        print(f"위치 정보 추출 중 오류 발생: {str(e)}")
        return None, None


def get_google_maps_url(lat: float, lon: float):
    """
    위도, 경도로 Google Maps URL 생성
    
    Args:
        lat: 위도
        lon: 경도
    
    Returns:
        str: Google Maps URL
    """
    if lat is None or lon is None:
        return None
    return f"https://www.google.com/maps?q={lat},{lon}"


def get_datetime_taken(exif_data: dict):
    """
    EXIF 데이터에서 촬영 일시 추출
    
    Args:
        exif_data: EXIF 데이터 딕셔너리
    
    Returns:
        str: 촬영 일시 문자열 (YYYY-MM-DD HH:MM:SS 형식), 없으면 None
    """
    try:
        # DateTimeOriginal (원본 촬영 시간) 우선
        datetime_str = exif_data.get("DateTimeOriginal")
        if not datetime_str:
            # DateTime (파일 수정 시간) 사용
            datetime_str = exif_data.get("DateTime")
        
        if datetime_str:
            # EXIF 형식: "YYYY:MM:DD HH:MM:SS" -> "YYYY-MM-DD HH:MM:SS"
            if isinstance(datetime_str, str):
                datetime_str = datetime_str.replace(":", "-", 2)  # 첫 두 개의 :만 -로 변경
                try:
                    # 파싱하여 형식 검증
                    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return datetime_str
        return None
    except Exception as e:
        print(f"촬영 일시 추출 중 오류 발생: {str(e)}")
        return None


def extract_locations_from_folder(upload_folder: str):
    """
    업로드 폴더의 모든 이미지에서 위치 정보 추출
    
    Args:
        upload_folder: 업로드 폴더 경로
    
    Returns:
        list: 위치 정보가 있는 이미지들의 리스트
            각 항목은 {
                'filename': 파일명,
                'path': 파일 경로,
                'lat': 위도,
                'lon': 경도,
                'maps_url': Google Maps URL
            }
    """
    locations = []
    upload_path = Path(upload_folder)
    
    if not upload_path.exists():
        print(f"업로드 폴더가 존재하지 않습니다: {upload_folder}")
        return locations
    
    # 지원하는 이미지 확장자
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
    
    # 폴더 내 모든 이미지 파일 검색
    for image_file in upload_path.iterdir():
        if image_file.is_file() and image_file.suffix.lower() in image_extensions:
            try:
                lat, lon = get_image_location(str(image_file))
                
                if lat is not None and lon is not None:
                    # EXIF 데이터에서 촬영 일시 추출
                    exif_data = get_exif_data(str(image_file))
                    datetime_taken = get_datetime_taken(exif_data)
                    
                    # 촬영 일시가 없으면 파일 수정 시간 사용
                    if not datetime_taken:
                        file_mtime = datetime.fromtimestamp(image_file.stat().st_mtime)
                        datetime_taken = file_mtime.strftime("%Y-%m-%d %H:%M:%S")
                    
                    maps_url = get_google_maps_url(lat, lon)
                    locations.append({
                        'filename': image_file.name,
                        'path': str(image_file),
                        'lat': lat,
                        'lon': lon,
                        'maps_url': maps_url,
                        'datetime_taken': datetime_taken
                    })
            except Exception as e:
                continue
    
    return locations
