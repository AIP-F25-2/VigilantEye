// JavaScript for VIGILANTEye

document.addEventListener('DOMContentLoaded', function() {
    // Initialize form validation
    initFormValidation();
    
    // Initialize real-time validation
    initRealTimeValidation();

    // Initialize password toggles
    initPasswordToggles();

    // Initialize password strength meter
    initPasswordStrengthMeter();
    
    // Initialize camera functionality
    initCamera();
});

function initFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            console.log('Form submission attempted');
            // Only prevent submission if there are actual validation errors
            const requiredFields = form.querySelectorAll('[required]');
            let hasErrors = false;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    hasErrors = true;
                    field.classList.add('is-invalid');
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            
            if (hasErrors) {
                console.log('Form has validation errors, preventing submission');
                event.preventDefault();
                event.stopPropagation();
            } else {
                console.log('Form validation passed, submitting...');
            }
            form.classList.add('was-validated');
        });
    });
}

function initPasswordToggles() {
    const toggleButtons = document.querySelectorAll('.toggle-password');
    toggleButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const input = document.getElementById(targetId);
            const icon = this.querySelector('i');
            if (!input) return;
            const isPassword = input.getAttribute('type') === 'password';
            input.setAttribute('type', isPassword ? 'text' : 'password');
            if (icon) {
                icon.classList.toggle('bi-eye');
                icon.classList.toggle('bi-eye-slash');
            }
        });
    });
}

function initPasswordStrengthMeter() {
    const passwordInput = document.getElementById('password');
    const barContainer = document.querySelector('.password-strength');
    if (!passwordInput || !barContainer) return;
    const update = () => {
        const value = passwordInput.value || '';
        const score = scorePassword(value);
        barContainer.classList.remove('password-weak','password-fair','password-good','password-strong');
        if (score >= 80) barContainer.classList.add('password-strong');
        else if (score >= 60) barContainer.classList.add('password-good');
        else if (score >= 40) barContainer.classList.add('password-fair');
        else barContainer.classList.add('password-weak');
    };
    passwordInput.addEventListener('input', update);
    update();
}

function scorePassword(password) {
    let score = 0;
    if (!password) return score;
    const letters = {};
    for (let i = 0; i < password.length; i++) {
        letters[password[i]] = (letters[password[i]] || 0) + 1;
        score += 5.0 / letters[password[i]];
    }
    const variations = {
        digits: /\d/.test(password),
        lower: /[a-z]/.test(password),
        upper: /[A-Z]/.test(password),
        nonWords: /[^\w]/.test(password),
        length8: password.length >= 8
    };
    let variationCount = 0;
    for (const check in variations) variationCount += variations[check] ? 1 : 0;
    score += (variationCount - 1) * 10;
    return parseInt(score);
}

function initRealTimeValidation() {
    // Username validation
    const usernameInput = document.getElementById('username');
    if (usernameInput) {
        let usernameTimeout;
        usernameInput.addEventListener('input', function() {
            clearTimeout(usernameTimeout);
            const username = this.value.trim();
            
            if (username.length < 3) {
                showFieldError('username', 'Username must be at least 3 characters');
                return;
            }
            
            usernameTimeout = setTimeout(() => {
                checkUsernameAvailability(username);
            }, 500);
        });
    }
    
    // Email validation
    const emailInput = document.getElementById('email');
    if (emailInput) {
        let emailTimeout;
        emailInput.addEventListener('input', function() {
            clearTimeout(emailTimeout);
            const email = this.value.trim();
            
            if (!isValidEmail(email)) {
                showFieldError('email', 'Please enter a valid email address');
                return;
            }
            
            emailTimeout = setTimeout(() => {
                checkEmailAvailability(email);
            }, 500);
        });
    }
    
    // Password confirmation validation
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    
    if (passwordInput && confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            const password = passwordInput.value;
            const confirmPassword = this.value;
            
            if (confirmPassword && password !== confirmPassword) {
                showFieldError('confirm_password', 'Passwords do not match');
            } else if (confirmPassword && password === confirmPassword) {
                showFieldSuccess('confirm_password', 'Passwords match');
            }
        });
    }
}

function checkUsernameAvailability(username) {
    if (username.length < 3) return;
    
    fetch(`/api/check-username?username=${encodeURIComponent(username)}`)
        .then(response => response.json())
        .then(data => {
            if (data.available) {
                showFieldSuccess('username', data.message);
            } else {
                showFieldError('username', data.message);
            }
        })
        .catch(error => {
            console.error('Error checking username:', error);
        });
}

function checkEmailAvailability(email) {
    if (!isValidEmail(email)) return;
    
    fetch(`/api/check-email?email=${encodeURIComponent(email)}`)
        .then(response => response.json())
        .then(data => {
            if (data.available) {
                showFieldSuccess('email', data.message);
            } else {
                showFieldError('email', data.message);
            }
        })
        .catch(error => {
            console.error('Error checking email:', error);
        });
}

function showFieldError(fieldName, message) {
    const field = document.getElementById(fieldName);
    const feedback = document.getElementById(`${fieldName}-feedback`);
    
    if (field && feedback) {
        field.classList.remove('is-valid');
        field.classList.add('is-invalid');
        feedback.textContent = message;
        feedback.style.display = 'block';
    }
    
    // Hide success message if exists
    const successFeedback = document.getElementById(`${fieldName}-valid`);
    if (successFeedback) {
        successFeedback.style.display = 'none';
    }
}

function showFieldSuccess(fieldName, message) {
    const field = document.getElementById(fieldName);
    const feedback = document.getElementById(`${fieldName}-valid`);
    
    if (field && feedback) {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
        feedback.textContent = message;
        feedback.style.display = 'block';
    }
    
    // Hide error message if exists
    const errorFeedback = document.getElementById(`${fieldName}-feedback`);
    if (errorFeedback) {
        errorFeedback.style.display = 'none';
    }
}

function isValidEmail(email) {
    const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return pattern.test(email);
}

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Add loading state to submit buttons
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Processing...';
                submitBtn.disabled = true;
            }
        });
    });
});

// Camera functionality
let cameraStream = null;
let cameraActive = false;
let fpsCounter = 0;
let fpsStartTime = Date.now();

// Recording functionality
let mediaRecorder = null;
let recordedChunks = [];
let isRecording = false;
let recordingStartTime = null;

// Session history
let sessionHistory = [];
let currentSession = null;

// AI Features
let motionDetection = {
    enabled: false,
    sensitivity: 0.3,
    lastFrame: null,
    motionCount: 0,
    motionThreshold: 10
};
let objectDetection = {
    enabled: false,
    detectedObjects: []
};

function initCamera() {
    const startBtn = document.getElementById('startCamera');
    const stopBtn = document.getElementById('stopCamera');
    const recordBtn = document.getElementById('recordBtn');
    const stopRecordBtn = document.getElementById('stopRecordBtn');
    const screenshotBtn = document.getElementById('screenshotBtn');
    
    if (!startBtn || !stopBtn) return; // Only initialize on dashboard page
    
    startBtn.addEventListener('click', startCamera);
    stopBtn.addEventListener('click', stopCamera);
    
    if (recordBtn) recordBtn.addEventListener('click', startRecording);
    if (stopRecordBtn) stopRecordBtn.addEventListener('click', stopRecording);
    if (screenshotBtn) screenshotBtn.addEventListener('click', takeScreenshot);
    
    // Settings functionality
    const applySettingsBtn = document.getElementById('applySettings');
    if (applySettingsBtn) applySettingsBtn.addEventListener('click', applyCameraSettings);
    
    // Session history functionality
    const clearHistoryBtn = document.getElementById('clearHistory');
    if (clearHistoryBtn) clearHistoryBtn.addEventListener('click', clearSessionHistory);
    
    // AI functionality
    const motionToggle = document.getElementById('motionDetectionToggle');
    const objectToggle = document.getElementById('objectDetectionToggle');
    const sensitivitySlider = document.getElementById('motionSensitivity');
    
    if (motionToggle) motionToggle.addEventListener('change', toggleMotionDetection);
    if (objectToggle) objectToggle.addEventListener('change', toggleObjectDetection);
    if (sensitivitySlider) {
        sensitivitySlider.addEventListener('input', updateMotionSensitivity);
        updateSensitivityDisplay();
    }
    
    // Load saved settings
    loadCameraSettings();
    
    // Load session history
    loadSessionHistory();
    
    // Update FPS counter every second
    setInterval(updateFPS, 1000);
}

async function startCamera() {
    const startBtn = document.getElementById('startCamera');
    const stopBtn = document.getElementById('stopCamera');
    const video = document.getElementById('cameraFeed');
    const canvas = document.getElementById('cameraCanvas');
    const placeholder = document.getElementById('cameraPlaceholder');
    const status = document.getElementById('cameraStatus');
    const resolution = document.getElementById('cameraResolution');
    
    try {
        // Load saved settings
        const resolution = localStorage.getItem('cameraResolution') || '1280x720';
        const fps = parseInt(localStorage.getItem('cameraFPS')) || 30;
        const facingMode = localStorage.getItem('cameraFacingMode') || 'user';
        
        // Parse resolution
        const [width, height] = resolution.split('x').map(Number);
        
        // Request camera access with settings
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: width },
                height: { ideal: height },
                frameRate: { ideal: fps },
                facingMode: facingMode
            },
            audio: false
        });
        
        // Set up video element
        video.srcObject = cameraStream;
        video.style.display = 'block';
        canvas.style.display = 'none';
        placeholder.style.display = 'none';
        
        // Wait for video to load
        video.onloadedmetadata = function() {
            video.play();
            cameraActive = true;
            
            // Update UI
            startBtn.disabled = true;
            stopBtn.disabled = false;
            
            // Enable recording and screenshot buttons
            const recordBtn = document.getElementById('recordBtn');
            const screenshotBtn = document.getElementById('screenshotBtn');
            if (recordBtn) recordBtn.disabled = false;
            if (screenshotBtn) screenshotBtn.disabled = false;
            
            status.textContent = 'Connected';
            status.className = 'fw-semibold text-success';
            resolution.textContent = `${video.videoWidth}x${video.videoHeight}`;
            
            // Start frame processing for FPS calculation
            processFrame();
            
            // Start new session
            startNewSession();
        };
        
    } catch (error) {
        console.error('Error accessing camera:', error);
        updateCameraStatus('Error: ' + getErrorMessage(error), 'text-danger');
    }
}

function stopCamera() {
    const startBtn = document.getElementById('startCamera');
    const stopBtn = document.getElementById('stopCamera');
    const video = document.getElementById('cameraFeed');
    const canvas = document.getElementById('cameraCanvas');
    const placeholder = document.getElementById('cameraPlaceholder');
    
    // Stop camera stream
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    
    // Reset UI
    video.style.display = 'none';
    canvas.style.display = 'none';
    placeholder.style.display = 'flex';
    startBtn.disabled = false;
    stopBtn.disabled = true;
    
    // Disable recording and screenshot buttons
    const recordBtn = document.getElementById('recordBtn');
    const stopRecordBtn = document.getElementById('stopRecordBtn');
    const screenshotBtn = document.getElementById('screenshotBtn');
    if (recordBtn) recordBtn.disabled = true;
    if (stopRecordBtn) stopRecordBtn.disabled = true;
    if (screenshotBtn) screenshotBtn.disabled = true;
    
    cameraActive = false;
    updateCameraStatus('Disconnected', 'text-secondary');
    document.getElementById('cameraResolution').textContent = '-';
    document.getElementById('cameraFPS').textContent = '-';
    
    // Reset recording status
    const recordingStatus = document.getElementById('recordingStatus');
    if (recordingStatus) {
        recordingStatus.textContent = 'Ready';
        recordingStatus.className = 'fw-semibold text-secondary';
    }
    stopRecordingTimer();
    
    // End current session
    endCurrentSession();
}

function processFrame() {
    if (!cameraActive) return;
    
    const video = document.getElementById('cameraFeed');
    const canvas = document.getElementById('cameraCanvas');
    const ctx = canvas.getContext('2d');
    
    if (video.videoWidth > 0 && video.videoHeight > 0) {
        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Draw video frame to canvas (for potential image processing)
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // AI Processing
        if (motionDetection.enabled || objectDetection.enabled) {
            processAIFeatures(canvas, ctx);
        }
        
        // Increment FPS counter
        fpsCounter++;
    }
    
    // Continue processing frames
    requestAnimationFrame(processFrame);
}

function updateFPS() {
    if (cameraActive) {
        const fps = fpsCounter;
        document.getElementById('cameraFPS').textContent = fps + ' FPS';
        fpsCounter = 0; // Reset counter
    }
}

function updateCameraStatus(message, className) {
    const status = document.getElementById('cameraStatus');
    status.textContent = message;
    status.className = 'fw-semibold ' + className;
}

function getErrorMessage(error) {
    switch (error.name) {
        case 'NotAllowedError':
            return 'Camera access denied. Please allow camera access and try again.';
        case 'NotFoundError':
            return 'No camera found. Please connect a camera and try again.';
        case 'NotReadableError':
            return 'Camera is being used by another application.';
        case 'OverconstrainedError':
            return 'Camera constraints cannot be satisfied.';
        default:
            return 'Unable to access camera. Please check your camera settings.';
    }
}

// Recording functionality
function startRecording() {
    if (!cameraActive || !cameraStream) {
        alert('Please start the camera first');
        return;
    }
    
    try {
        recordedChunks = [];
        mediaRecorder = new MediaRecorder(cameraStream, {
            mimeType: 'video/webm;codecs=vp9'
        });
        
        mediaRecorder.ondataavailable = function(event) {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = function() {
            const blob = new Blob(recordedChunks, { type: 'video/webm' });
            downloadRecording(blob);
        };
        
        mediaRecorder.start();
        isRecording = true;
        recordingStartTime = new Date();
        
        // Update UI
        const recordBtn = document.getElementById('recordBtn');
        const stopRecordBtn = document.getElementById('stopRecordBtn');
        const recordingStatus = document.getElementById('recordingStatus');
        
        if (recordBtn) recordBtn.disabled = true;
        if (stopRecordBtn) stopRecordBtn.disabled = false;
        if (recordingStatus) {
            recordingStatus.textContent = 'Recording...';
            recordingStatus.className = 'fw-semibold text-danger';
        }
        
        // Start recording timer
        startRecordingTimer();
        
        // Add to session history
        addRecordingToSession({
            id: 'rec_' + Date.now(),
            startTime: new Date(),
            duration: 0,
            status: 'recording'
        });
        
    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Error starting recording: ' + error.message);
    }
}

function stopRecording() {
    if (!isRecording || !mediaRecorder) return;
    
    mediaRecorder.stop();
    isRecording = false;
    
    // Update UI
    const recordBtn = document.getElementById('recordBtn');
    const stopRecordBtn = document.getElementById('stopRecordBtn');
    const recordingStatus = document.getElementById('recordingStatus');
    
    if (recordBtn) recordBtn.disabled = false;
    if (stopRecordBtn) stopRecordBtn.disabled = true;
    if (recordingStatus) {
        recordingStatus.textContent = 'Stopped';
        recordingStatus.className = 'fw-semibold text-secondary';
    }
    
    // Stop recording timer
    stopRecordingTimer();
}

function downloadRecording(blob) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `vigilanteye_recording_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.webm`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function startRecordingTimer() {
    const recordingTimer = document.getElementById('recordingTimer');
    if (!recordingTimer) return;
    
    const timerInterval = setInterval(() => {
        if (!isRecording) {
            clearInterval(timerInterval);
            return;
        }
        
        const now = new Date();
        const elapsed = Math.floor((now - recordingStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        recordingTimer.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);
}

function stopRecordingTimer() {
    const recordingTimer = document.getElementById('recordingTimer');
    if (recordingTimer) {
        recordingTimer.textContent = '00:00';
    }
}

// Screenshot functionality
function takeScreenshot() {
    if (!cameraActive) {
        alert('Please start the camera first');
        return;
    }
    
    const video = document.getElementById('cameraFeed');
    const canvas = document.getElementById('cameraCanvas');
    const ctx = canvas.getContext('2d');
    
    // Set canvas dimensions to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw current video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert to blob and download
    canvas.toBlob(function(blob) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `vigilanteye_screenshot_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, 'image/png', 0.9);
    
    // Add to session history
    addScreenshotToSession({
        id: 'screenshot_' + Date.now(),
        timestamp: new Date(),
        filename: `vigilanteye_screenshot_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.png`
    });
    
    // Show feedback
    const screenshotStatus = document.getElementById('screenshotStatus');
    if (screenshotStatus) {
        screenshotStatus.textContent = 'Screenshot saved!';
        screenshotStatus.className = 'fw-semibold text-success';
        setTimeout(() => {
            screenshotStatus.textContent = 'Ready';
            screenshotStatus.className = 'fw-semibold text-secondary';
        }, 2000);
    }
}

// Settings functionality
function applyCameraSettings() {
    if (cameraActive) {
        alert('Please stop the camera first to apply new settings');
        return;
    }
    
    const resolutionSelect = document.getElementById('resolutionSelect');
    const fpsSelect = document.getElementById('fpsSelect');
    const cameraSelect = document.getElementById('cameraSelect');
    
    if (resolutionSelect && fpsSelect && cameraSelect) {
        const resolution = resolutionSelect.value;
        const fps = parseInt(fpsSelect.value);
        const facingMode = cameraSelect.value;
        
        // Store settings for next camera start
        localStorage.setItem('cameraResolution', resolution);
        localStorage.setItem('cameraFPS', fps);
        localStorage.setItem('cameraFacingMode', facingMode);
        
        // Show confirmation
        const applyBtn = document.getElementById('applySettings');
        if (applyBtn) {
            applyBtn.innerHTML = '<i class="bi bi-check"></i> Settings Saved';
            applyBtn.className = 'btn btn-sm btn-success w-100';
            setTimeout(() => {
                applyBtn.innerHTML = '<i class="bi bi-gear"></i> Apply Settings';
                applyBtn.className = 'btn btn-sm btn-outline-primary w-100';
            }, 2000);
        }
    }
}

// Load saved settings
function loadCameraSettings() {
    const resolution = localStorage.getItem('cameraResolution') || '1280x720';
    const fps = localStorage.getItem('cameraFPS') || '30';
    const facingMode = localStorage.getItem('cameraFacingMode') || 'user';
    
    const resolutionSelect = document.getElementById('resolutionSelect');
    const fpsSelect = document.getElementById('fpsSelect');
    const cameraSelect = document.getElementById('cameraSelect');
    
    if (resolutionSelect) resolutionSelect.value = resolution;
    if (fpsSelect) fpsSelect.value = fps;
    if (cameraSelect) cameraSelect.value = facingMode;
}

// Session History Management
function startNewSession() {
    currentSession = {
        id: generateSessionId(),
        startTime: new Date(),
        endTime: null,
        recordings: [],
        screenshots: [],
        settings: {
            resolution: localStorage.getItem('cameraResolution') || '1280x720',
            fps: parseInt(localStorage.getItem('cameraFPS')) || 30,
            facingMode: localStorage.getItem('cameraFacingMode') || 'user'
        },
        status: 'active'
    };
    
    addToSessionHistory(currentSession);
    updateSessionHistoryDisplay();
}

function endCurrentSession() {
    if (currentSession) {
        currentSession.endTime = new Date();
        currentSession.status = 'completed';
        currentSession.duration = Math.floor((currentSession.endTime - currentSession.startTime) / 1000);
        updateSessionInHistory(currentSession);
        updateSessionHistoryDisplay();
        currentSession = null;
    }
}

function addRecordingToSession(recordingData) {
    if (currentSession) {
        currentSession.recordings.push(recordingData);
        updateSessionInHistory(currentSession);
        updateSessionHistoryDisplay();
    }
}

function addScreenshotToSession(screenshotData) {
    if (currentSession) {
        currentSession.screenshots.push(screenshotData);
        updateSessionInHistory(currentSession);
        updateSessionHistoryDisplay();
    }
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function addToSessionHistory(session) {
    sessionHistory.unshift(session); // Add to beginning
    if (sessionHistory.length > 50) { // Keep only last 50 sessions
        sessionHistory = sessionHistory.slice(0, 50);
    }
    saveSessionHistory();
}

function updateSessionInHistory(session) {
    const index = sessionHistory.findIndex(s => s.id === session.id);
    if (index !== -1) {
        sessionHistory[index] = session;
        saveSessionHistory();
    }
}

function saveSessionHistory() {
    localStorage.setItem('vigilanteye_session_history', JSON.stringify(sessionHistory));
}

function loadSessionHistory() {
    const saved = localStorage.getItem('vigilanteye_session_history');
    if (saved) {
        sessionHistory = JSON.parse(saved);
    }
    updateSessionHistoryDisplay();
}

function updateSessionHistoryDisplay() {
    const historyContainer = document.getElementById('sessionHistory');
    if (!historyContainer) return;
    
    if (sessionHistory.length === 0) {
        historyContainer.innerHTML = '<div class="text-muted small">No sessions yet</div>';
        return;
    }
    
    let html = '';
    sessionHistory.slice(0, 10).forEach(session => {
        const duration = session.duration ? formatDuration(session.duration) : 'Active';
        const statusClass = session.status === 'active' ? 'text-success' : 'text-secondary';
        const recordingsCount = session.recordings ? session.recordings.length : 0;
        const screenshotsCount = session.screenshots ? session.screenshots.length : 0;
        
        html += `
            <div class="session-item mb-2 p-2 border rounded">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="fw-semibold small">Session ${session.id.substring(0, 8)}...</div>
                        <div class="text-muted small">${formatDateTime(session.startTime)}</div>
                        <div class="small">
                            <span class="badge bg-primary me-1">${recordingsCount} recordings</span>
                            <span class="badge bg-warning">${screenshotsCount} screenshots</span>
                        </div>
                    </div>
                    <div class="text-end">
                        <div class="small ${statusClass}">${duration}</div>
                        <div class="small text-muted">${session.settings.resolution} @ ${session.settings.fps}fps</div>
                    </div>
                </div>
            </div>
        `;
    });
    
    historyContainer.innerHTML = html;
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

function formatDateTime(date) {
    return new Date(date).toLocaleString();
}

function clearSessionHistory() {
    if (confirm('Are you sure you want to clear all session history? This cannot be undone.')) {
        sessionHistory = [];
        saveSessionHistory();
        updateSessionHistoryDisplay();
    }
}

// AI Features
function processAIFeatures(canvas, ctx) {
    if (motionDetection.enabled) {
        detectMotion(canvas, ctx);
    }
    
    if (objectDetection.enabled) {
        detectObjects(canvas, ctx);
    }
}

function detectMotion(canvas, ctx) {
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;
    
    if (motionDetection.lastFrame === null) {
        motionDetection.lastFrame = new Uint8ClampedArray(data);
        return;
    }
    
    let motionPixels = 0;
    const threshold = motionDetection.sensitivity * 255;
    
    for (let i = 0; i < data.length; i += 4) {
        const r = Math.abs(data[i] - motionDetection.lastFrame[i]);
        const g = Math.abs(data[i + 1] - motionDetection.lastFrame[i + 1]);
        const b = Math.abs(data[i + 2] - motionDetection.lastFrame[i + 2]);
        
        if (r > threshold || g > threshold || b > threshold) {
            motionPixels++;
        }
    }
    
    motionDetection.lastFrame = new Uint8ClampedArray(data);
    
    if (motionPixels > motionDetection.motionThreshold) {
        motionDetection.motionCount++;
        updateMotionStatus('Motion Detected', 'text-danger');
        
        // Add motion event to session
        if (currentSession) {
            addMotionEventToSession({
                timestamp: new Date(),
                motionPixels: motionPixels,
                confidence: Math.min(motionPixels / 1000, 1)
            });
        }
    } else {
        updateMotionStatus('Monitoring', 'text-success');
    }
}

function detectObjects(canvas, ctx) {
    // Simplified object detection - in a real implementation, you'd use a proper ML model
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;
    
    // Basic edge detection for demonstration
    let edgePixels = 0;
    for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        
        // Simple edge detection based on color intensity
        if (r < 100 || g < 100 || b < 100) {
            edgePixels++;
        }
    }
    
    // Estimate number of objects based on edge density
    const objectCount = Math.floor(edgePixels / 1000);
    objectDetection.detectedObjects = Array(objectCount).fill().map((_, i) => ({
        id: i,
        type: 'object',
        confidence: 0.7
    }));
    
    updateObjectStatus(`${objectCount} detected`);
}

function toggleMotionDetection() {
    const toggle = document.getElementById('motionDetectionToggle');
    motionDetection.enabled = toggle.checked;
    
    if (motionDetection.enabled) {
        updateMotionStatus('Enabled', 'text-success');
        motionDetection.lastFrame = null; // Reset for new detection
    } else {
        updateMotionStatus('Disabled', 'text-secondary');
    }
}

function toggleObjectDetection() {
    const toggle = document.getElementById('objectDetectionToggle');
    objectDetection.enabled = toggle.checked;
    
    if (objectDetection.enabled) {
        updateObjectStatus('Enabled');
    } else {
        updateObjectStatus('0 detected');
        objectDetection.detectedObjects = [];
    }
}

function updateMotionSensitivity() {
    const slider = document.getElementById('motionSensitivity');
    motionDetection.sensitivity = parseFloat(slider.value);
    updateSensitivityDisplay();
}

function updateSensitivityDisplay() {
    const display = document.getElementById('sensitivityValue');
    if (display) {
        display.textContent = motionDetection.sensitivity.toFixed(1);
    }
}

function updateMotionStatus(message, className) {
    const status = document.getElementById('motionStatus');
    if (status) {
        status.textContent = message;
        status.className = `fw-semibold ${className}`;
    }
}

function updateObjectStatus(message) {
    const status = document.getElementById('objectStatus');
    if (status) {
        status.textContent = message;
        status.className = 'fw-semibold text-info';
    }
}

function addMotionEventToSession(eventData) {
    if (currentSession) {
        if (!currentSession.motionEvents) {
            currentSession.motionEvents = [];
        }
        currentSession.motionEvents.push(eventData);
        updateSessionInHistory(currentSession);
        updateSessionHistoryDisplay();
    }
}

