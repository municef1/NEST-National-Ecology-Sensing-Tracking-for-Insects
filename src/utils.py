"""
공통 유틸리티 함수
"""

import os
import platform
from pathlib import Path
import uuid
from datetime import datetime

PLATFORM = platform.system()


def get_platform_path(path_str):
    """
    플랫폼에 맞는 경로 반환
    
    Args:
        path_str: 경로 문자열
    
    Returns:
        Path: 플랫폼에 맞게 변환된 경로
    """
    return Path(path_str)


def generate_unique_filename(original_filename):
    """
    고유한 파일명 생성
    
    Args:
        original_filename: 원본 파일명
    
    Returns:
        str: 고유한 파일명
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    ext = Path(original_filename).suffix
    return f"{timestamp}_{unique_id}{ext}"


def ensure_dir(directory):
    """
    디렉토리가 존재하지 않으면 생성
    
    Args:
        directory: 디렉토리 경로
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_file_size(file_path):
    """
    파일 크기 반환 (MB)
    
    Args:
        file_path: 파일 경로
    
    Returns:
        float: 파일 크기 (MB)
    """
    return Path(file_path).stat().st_size / (1024 * 1024)


def allowed_file(filename, allowed_extensions={'jpg', 'jpeg', 'png', 'gif', 'bmp'}):
    """
    허용된 파일 확장자인지 확인
    
    Args:
        filename: 파일명
        allowed_extensions: 허용된 확장자 집합
    
    Returns:
        bool: 허용 여부
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def format_confidence(confidence):
    """
    신뢰도를 퍼센트로 포맷팅
    
    Args:
        confidence: 신뢰도 (0-1)
    
    Returns:
        str: 포맷팅된 문자열
    """
    return f"{confidence * 100:.2f}%"


def get_base_dir():
    """
    프로젝트 루트 디렉토리 반환
    
    Returns:
        Path: 루트 디렉토리
    """
    return Path(__file__).parent.parent

