/**
 * NEST - Toss Style Web Application
 * Advanced Interactions and Animations
 */

// ==================== Loading Overlay ====================
class LoadingOverlay {
  constructor() {
    this.overlay = null;
    this.init();
  }
  
  init() {
    // Create overlay element
    this.overlay = document.createElement('div');
    this.overlay.className = 'loading-overlay';
    this.overlay.innerHTML = `
      <div class="loading-content">
        <div class="loading-spinner-large"></div>
        <div class="loading-text">분석 중...</div>
        <div class="loading-progress">
          <div class="loading-progress-bar"></div>
        </div>
      </div>
    `;
    document.body.appendChild(this.overlay);
  }
  
  show(message = '분석 중...') {
    const textEl = this.overlay.querySelector('.loading-text');
    if (textEl) textEl.textContent = message;
    this.overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    
    // Simulate progress
    this.animateProgress();
  }
  
  hide() {
    this.overlay.classList.remove('active');
    document.body.style.overflow = '';
    
    // Reset progress
    const progressBar = this.overlay.querySelector('.loading-progress-bar');
    if (progressBar) progressBar.style.width = '0%';
  }
  
  animateProgress() {
    const progressBar = this.overlay.querySelector('.loading-progress-bar');
    if (!progressBar) return;
    
    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 15;
      if (progress >= 90) {
        progress = 90;
        clearInterval(interval);
      }
      progressBar.style.width = progress + '%';
    }, 300);
  }
}

// ==================== Toast Notification ====================
class Toast {
  static show(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = {
      success: '✓',
      error: '✗',
      warning: '⚠',
      info: 'ℹ'
    }[type] || 'ℹ';
    
    toast.innerHTML = `
      <span class="toast-icon">${icon}</span>
      <span class="toast-message">${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Auto remove
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }
}

// ==================== Image Upload Handler ====================
class ImageUploadHandler {
  constructor(inputId, areaId, previewId, placeholderId, formId) {
    this.input = document.getElementById(inputId);
    this.area = document.getElementById(areaId);
    this.preview = document.getElementById(previewId);
    this.placeholder = document.getElementById(placeholderId);
    this.form = document.getElementById(formId);
    this.loading = new LoadingOverlay();
    
    if (this.input && this.area) {
      this.init();
    }
  }
  
  init() {
    // Click to upload
    this.area.addEventListener('click', (e) => {
      if (e.target !== this.input) {
        this.input.click();
      }
    });
    
    // File input change
    this.input.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        this.handleFile(file);
      }
    });
    
    // Drag and drop
    this.area.addEventListener('dragover', (e) => {
      e.preventDefault();
      this.area.classList.add('dragover');
    });
    
    this.area.addEventListener('dragleave', (e) => {
      e.preventDefault();
      this.area.classList.remove('dragover');
    });
    
    this.area.addEventListener('drop', (e) => {
      e.preventDefault();
      this.area.classList.remove('dragover');
      
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        this.input.files = files;
        this.handleFile(files[0]);
      }
    });
  }
  
  handleFile(file) {
    // Validate file size
    if (file.size > 16 * 1024 * 1024) {
      Toast.show('파일 크기는 16MB를 초과할 수 없습니다.', 'error');
      return;
    }
    
    // Validate file type
    const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      Toast.show('지원하지 않는 파일 형식입니다.', 'error');
      return;
    }
    
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
      if (this.preview) {
        this.preview.src = e.target.result;
        this.preview.classList.remove('hidden');
      }
      if (this.placeholder) {
        this.placeholder.classList.add('hidden');
      }
      if (this.area) {
        this.area.classList.add('has-image');
      }
      
      // Submit form with loading
      this.submitWithLoading();
    };
    reader.readAsDataURL(file);
  }
  
  submitWithLoading() {
    if (!this.form) return;
    
    // 중복 제출 방지
    if (this.form.dataset.submitting === 'true') {
      return;
    }
    
    this.form.dataset.submitting = 'true';
    this.loading.show('이미지 업로드 중...');
    
    setTimeout(() => {
      this.form.submit();
    }, 500);
  }
}

// ==================== Classification Handler ====================
class ClassificationHandler {
  constructor() {
    this.loading = new LoadingOverlay();
  }
  
  async proceed() {
    this.loading.show('곤충 분류 중...');
    
    try {
      const response = await fetch('/classify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      
      if (data.success) {
        Toast.show('분류가 완료되었습니다!', 'success');
        setTimeout(() => {
          window.location.href = '/?show_result=true';
        }, 500);
      } else {
        this.loading.hide();
        Toast.show('분류 중 오류가 발생했습니다.', 'error');
      }
    } catch (error) {
      console.error('Classification error:', error);
      this.loading.hide();
      Toast.show('분류 중 오류가 발생했습니다.', 'error');
    }
  }
}

// ==================== Accordion Handler ====================
function toggleAccordion(header) {
  const content = header.nextElementSibling;
  const isActive = header.classList.contains('active');
  
  // Close all accordions in the same group
  const group = header.closest('.info-card');
  if (group) {
    group.querySelectorAll('.accordion-header').forEach(h => {
      if (h !== header) {
        h.classList.remove('active');
        h.nextElementSibling.classList.remove('active');
      }
    });
  }
  
  // Toggle current accordion
  header.classList.toggle('active');
  content.classList.toggle('active');
  
  // Haptic feedback (if supported)
  if (navigator.vibrate) {
    navigator.vibrate(10);
  }
}

// ==================== Scroll Animations ====================
class ScrollAnimations {
  constructor() {
    this.init();
  }
  
  init() {
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }
      });
    }, observerOptions);
    
    // Observe all cards
    document.querySelectorAll('.card, .risk-card, .info-card').forEach(element => {
      element.style.opacity = '0';
      element.style.transform = 'translateY(20px)';
      element.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      observer.observe(element);
    });
  }
}

// ==================== Smooth Scroll ====================
function smoothScrollTo(targetId) {
  const target = document.getElementById(targetId);
  if (target) {
    target.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
  }
}

// ==================== Button Ripple Effect ====================
function addRippleEffect() {
  document.querySelectorAll('.btn').forEach(button => {
    button.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      ripple.className = 'ripple';
      
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;
      
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';
      
      this.appendChild(ripple);
      
      setTimeout(() => ripple.remove(), 600);
    });
  });
}

// ==================== Initialize ====================
document.addEventListener('DOMContentLoaded', function() {
  // Initialize upload handler (only on upload page and if not already initialized)
  const imageInput = document.getElementById('imageInput');
  const uploadArea = document.getElementById('uploadArea');
  
  // index.html에서 이미 이벤트를 처리하고 있으므로 app.js의 초기화는 스킵
  // 단, 다른 페이지에서 필요할 수 있으므로 조건부로만 초기화
  if (imageInput && uploadArea && !uploadArea.dataset.initialized) {
    uploadArea.dataset.initialized = 'true';
    const uploadHandler = new ImageUploadHandler(
      'imageInput',
      'uploadArea',
      'previewImage',
      'uploadPlaceholder',
      'uploadForm'
    );
  }
  
  // Initialize scroll animations
  new ScrollAnimations();
  
  // Add ripple effect to buttons
  addRippleEffect();
  
  // Global classification handler
  window.classificationHandler = new ClassificationHandler();
  
  // Global function for classification button
  window.proceedToClassification = function() {
    window.classificationHandler.proceed();
  };
  
  // Show success toast if redirected after upload
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('show_result') === 'true') {
    setTimeout(() => {
      Toast.show('탐지가 완료되었습니다!', 'success');
    }, 500);
  }
  
  // Prevent double form submission
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    let submitted = false;
    form.addEventListener('submit', function(e) {
      if (submitted) {
        e.preventDefault();
        return false;
      }
      submitted = true;
    });
  });
  
  // Add keyboard shortcuts
  document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + U: Upload image
    if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
      e.preventDefault();
      const imageInput = document.getElementById('imageInput');
      if (imageInput) imageInput.click();
    }
    
    // Escape: Close modals/overlays
    if (e.key === 'Escape') {
      const overlay = document.querySelector('.loading-overlay.active');
      if (overlay) overlay.classList.remove('active');
    }
  });
  
  // Add touch feedback for mobile
  if ('ontouchstart' in window) {
    document.querySelectorAll('.btn, .step-chip, .accordion-header').forEach(element => {
      element.addEventListener('touchstart', function() {
        this.style.transform = 'scale(0.95)';
      });
      
      element.addEventListener('touchend', function() {
        this.style.transform = '';
      });
    });
  }
  
  // Performance monitoring
  if (window.performance && window.performance.timing) {
    window.addEventListener('load', function() {
      const loadTime = window.performance.timing.domContentLoadedEventEnd - 
                      window.performance.timing.navigationStart;
      console.log('Page load time:', loadTime + 'ms');
    });
  }
  
  // Service Worker registration (PWA support)
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
      // Uncomment when service worker is ready
      // navigator.serviceWorker.register('/sw.js');
    });
  }
});

// ==================== Export for global use ====================
window.Toast = Toast;
window.toggleAccordion = toggleAccordion;
window.smoothScrollTo = smoothScrollTo;
