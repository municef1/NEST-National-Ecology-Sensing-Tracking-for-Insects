// 곤충 탐지 및 분류 시스템 - 프론트엔드 로직

// DOM 요소
const detectionUploadArea = document.getElementById('detection-upload-area');
const detectionFileInput = document.getElementById('detection-file-input');
const detectionResult = document.getElementById('detection-result');
const detectionImage = document.getElementById('detection-image');
const detectionInfo = document.getElementById('detection-info');
const detectionLoading = document.getElementById('detection-loading');
const proceedBtn = document.getElementById('proceed-to-classification');

const classificationSection = document.getElementById('classification-section');
const classificationUploadArea = document.getElementById('classification-upload-area');
const classificationFileInput = document.getElementById('classification-file-input');
const classificationResult = document.getElementById('classification-result');
const classificationImage = document.getElementById('classification-image');
const classificationLoading = document.getElementById('classification-loading');
const restartBtn = document.getElementById('restart');

const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');

// 전역 변수
let detectionData = null;

// 초기화
function init() {
    setupEventListeners();
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 1단계: 탐지
    detectionUploadArea.addEventListener('click', () => {
        detectionFileInput.click();
    });

    detectionFileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleDetectionUpload(e.target.files[0]);
        }
    });

    detectionUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        detectionUploadArea.style.borderColor = 'var(--primary-color)';
    });

    detectionUploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        detectionUploadArea.style.borderColor = 'var(--border-color)';
    });

    detectionUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        detectionUploadArea.style.borderColor = 'var(--border-color)';
        if (e.dataTransfer.files.length > 0) {
            handleDetectionUpload(e.dataTransfer.files[0]);
        }
    });

    proceedBtn.addEventListener('click', () => {
        showClassificationSection();
    });

    // 2단계: 분류
    classificationUploadArea.addEventListener('click', () => {
        classificationFileInput.click();
    });

    classificationFileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleClassificationUpload(e.target.files[0]);
        }
    });

    classificationUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        classificationUploadArea.style.borderColor = 'var(--primary-color)';
    });

    classificationUploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        classificationUploadArea.style.borderColor = 'var(--border-color)';
    });

    classificationUploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        classificationUploadArea.style.borderColor = 'var(--border-color)';
        if (e.dataTransfer.files.length > 0) {
            handleClassificationUpload(e.dataTransfer.files[0]);
        }
    });

    restartBtn.addEventListener('click', () => {
        location.reload();
    });
    
    // 다시 분류 버튼
    const retryClassificationBtn = document.getElementById('retry-classification');
    retryClassificationBtn.addEventListener('click', () => {
        resetClassification();
    });
}

// 1단계: 탐지 업로드 처리
async function handleDetectionUpload(file) {
    // 파일 검증
    if (!validateFile(file)) {
        return;
    }

    // UI 업데이트
    detectionUploadArea.style.display = 'none';
    detectionResult.style.display = 'none';
    detectionLoading.style.display = 'block';

    // FormData 생성
    const formData = new FormData();
    formData.append('image', file);

    try {
        // API 호출
        const response = await fetch('/api/detect', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || '탐지에 실패했습니다.');
        }

        // 결과 표시
        detectionData = data;
        displayDetectionResult(data);

    } catch (error) {
        console.error('Error:', error);
        alert(`오류: ${error.message}`);
        detectionUploadArea.style.display = 'block';
    } finally {
        detectionLoading.style.display = 'none';
    }
}

// 탐지 결과 표시
function displayDetectionResult(data) {
    detectionImage.src = data.result_image;
    
    let infoHTML = '<h3>탐지 결과</h3>';
    
    if (data.count === 0) {
        infoHTML += '<p>곤충이 탐지되지 않았습니다. 다른 이미지를 시도해보세요.</p>';
        proceedBtn.style.display = 'none';
    } else {
        infoHTML += `<p><strong>${data.count}개</strong>의 곤충이 탐지되었습니다.</p>`;
        
        data.detections.forEach((det, idx) => {
            infoHTML += `
                <p>
                    객체 ${idx + 1}: 
                    신뢰도 <strong>${(det.confidence * 100).toFixed(2)}%</strong>
                </p>
            `;
        });
        
        infoHTML += '<p style="margin-top: 16px; color: var(--text-tertiary);">다음 단계에서 곤충의 세부 사진을 업로드하여 종을 확인하세요.</p>';
        proceedBtn.style.display = 'block';
    }
    
    // 다시 업로드 버튼 추가
    infoHTML += '<button class="btn btn-secondary" onclick="resetDetection()" style="margin-top: 10px;">다른 이미지로 다시 탐지</button>';
    
    detectionInfo.innerHTML = infoHTML;
    detectionResult.style.display = 'block';
}

// 탐지 초기화 함수
function resetDetection() {
    detectionResult.style.display = 'none';
    detectionUploadArea.style.display = 'block';
    detectionFileInput.value = '';
    detectionData = null;
    classificationSection.style.display = 'none';
    step2.classList.remove('active');
}

// 2단계 섹션 표시
function showClassificationSection() {
    classificationSection.style.display = 'block';
    step2.classList.add('active');
    
    // 스크롤
    classificationSection.scrollIntoView({ behavior: 'smooth' });
}

// 2단계: 분류 업로드 처리
async function handleClassificationUpload(file) {
    // 파일 검증
    if (!validateFile(file)) {
        return;
    }

    // UI 업데이트
    classificationUploadArea.style.display = 'none';
    classificationResult.style.display = 'none';
    classificationLoading.style.display = 'block';

    // FormData 생성
    const formData = new FormData();
    formData.append('image', file);

    try {
        // API 호출
        const response = await fetch('/api/classify', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || '분류에 실패했습니다.');
        }

        // 결과 표시
        displayClassificationResult(data);

    } catch (error) {
        console.error('Error:', error);
        alert(`오류: ${error.message}`);
        classificationUploadArea.style.display = 'block';
    } finally {
        classificationLoading.style.display = 'none';
    }
}

// 분류 결과 표시
function displayClassificationResult(data) {
    classificationImage.src = data.image_url;
    
    // 목 분류 결과 표시
    document.getElementById('species-name').textContent = data.order || '알 수 없음';
    document.getElementById('species-scientific').textContent = `${data.order} (목)`;
    
    // 신뢰도 바
    const confidenceFill = document.getElementById('confidence-fill');
    const confidenceText = document.getElementById('confidence-text');
    
    confidenceFill.style.width = `${data.confidence * 100}%`;
    confidenceText.textContent = data.confidence_formatted;
    
    // 목 분류 정보
    const speciesInfoDiv = document.getElementById('species-info');
    let infoHTML = '<h4>목 분류 정보</h4>';
    infoHTML += `<p><strong>분류된 목:</strong> ${data.order}</p>`;
    infoHTML += `<p><strong>신뢰도:</strong> ${data.confidence_formatted}</p>`;
    
    speciesInfoDiv.innerHTML = infoHTML;
    
    // Top 예측 (목 분류)
    const topPredictionsDiv = document.getElementById('top-predictions');
    let topHTML = '<h4>다른 가능성</h4>';
    
    if (data.top_predictions && data.top_predictions.length > 1) {
        data.top_predictions.slice(1, 5).forEach((pred, idx) => {
            topHTML += `
                <div class="prediction-item">
                    <span class="prediction-rank">${idx + 2}</span>
                    <span class="prediction-name">${pred.order}</span>
                    <span class="prediction-confidence">${(pred.confidence * 100).toFixed(2)}%</span>
                </div>
            `;
        });
    }
    
    topPredictionsDiv.innerHTML = topHTML;
    
    classificationResult.style.display = 'block';
}

// 파일 검증
function validateFile(file) {
    const maxSize = 16 * 1024 * 1024; // 16MB
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp'];
    
    if (!allowedTypes.includes(file.type)) {
        alert('지원하지 않는 파일 형식입니다. JPG, PNG, GIF, BMP 파일만 업로드 가능합니다.');
        return false;
    }
    
    if (file.size > maxSize) {
        alert('파일 크기가 너무 큽니다. 최대 16MB까지 업로드 가능합니다.');
        return false;
    }
    
    return true;
}

// 분류 초기화 함수
function resetClassification() {
    classificationResult.style.display = 'none';
    classificationUploadArea.style.display = 'block';
    classificationFileInput.value = '';
}

// 초기화 실행
document.addEventListener('DOMContentLoaded', init);