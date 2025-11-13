// VIGILANTEye JavaScript

// Initialize tooltips and setup
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Initialize auth page features
    initPasswordToggles();
    initPasswordStrength();
    initFormValidation();
});

// API Helper Functions
const API_BASE_URL = '/api/v2';

// Get auth token from localStorage
function getAuthToken() {
    return localStorage.getItem('access_token');
}

// Set auth token
function setAuthToken(token) {
    localStorage.setItem('access_token', token);
}

// Remove auth token
function removeAuthToken() {
    localStorage.removeItem('access_token');
}

// Make authenticated API request
async function apiRequest(endpoint, options = {}) {
    const token = getAuthToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
        const response = await fetch(API_BASE_URL + endpoint, {
            ...options,
            headers
        });
        
        if (response.status === 401) {
            // Unauthorized - redirect to login
            removeAuthToken();
            window.location.href = '/login';
            return null;
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

// Format duration
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// Show loading spinner
function showLoading(element) {
    element.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
}

// Show error message
function showError(message, container) {
    const alert = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="bi bi-exclamation-triangle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    container.innerHTML = alert;
}

// Show success message
function showSuccess(message, container) {
    const alert = `
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <i class="bi bi-check-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    container.innerHTML = alert;
}

// Confirm dialog
function confirmAction(message) {
    return confirm(message);
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!');
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// Show toast notification
function showToast(message, type = 'info') {
    const toastHtml = `
        <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(container);
    }
    
    const toastElement = document.createElement('div');
    toastElement.innerHTML = toastHtml;
    document.getElementById('toastContainer').appendChild(toastElement.firstElementChild);
    
    const toast = new bootstrap.Toast(toastElement.firstElementChild);
    toast.show();
}

// ========== Auth Page Functions ==========

// Initialize password visibility toggles
function initPasswordToggles() {
    const toggleButtons = document.querySelectorAll('.toggle-password');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const input = document.getElementById(targetId);
            const icon = this.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            }
        });
    });
}

// Initialize password strength indicator
function initPasswordStrength() {
    const passwordInput = document.getElementById('password');
    const strengthBar = document.getElementById('passwordStrengthBar');
    
    if (!passwordInput || !strengthBar) return;
    
    passwordInput.addEventListener('input', function() {
        const password = this.value;
        const strength = calculatePasswordStrength(password);
        
        // Update progress bar
        strengthBar.style.width = strength.percentage + '%';
        strengthBar.className = 'progress-bar';
        
        if (strength.score === 0) {
            strengthBar.classList.add('bg-secondary');
        } else if (strength.score === 1) {
            strengthBar.classList.add('bg-danger');
        } else if (strength.score === 2) {
            strengthBar.classList.add('bg-warning');
        } else if (strength.score === 3) {
            strengthBar.classList.add('bg-info');
        } else {
            strengthBar.classList.add('bg-success');
        }
    });
}

// Calculate password strength
function calculatePasswordStrength(password) {
    let score = 0;
    
    if (!password) return { score: 0, percentage: 0 };
    
    // Length check
    if (password.length >= 6) score++;
    if (password.length >= 10) score++;
    
    // Character type checks
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;
    
    // Calculate percentage (max score is 7)
    const percentage = Math.min(100, (score / 7) * 100);
    
    return {
        score: Math.min(4, Math.floor(score / 2)),
        percentage: percentage
    };
}

// Initialize form validation
function initFormValidation() {
    const signupForm = document.getElementById('signupForm');
    const loginForm = document.getElementById('loginForm');
    
    if (signupForm) {
        initSignupValidation(signupForm);
    }
    
    if (loginForm) {
        initLoginValidation(loginForm);
    }
}

// Signup form validation
function initSignupValidation(form) {
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    
    // Real-time username validation
    if (usernameInput) {
        usernameInput.addEventListener('blur', function() {
            const username = this.value.trim();
            const feedback = document.getElementById('username-feedback');
            const validFeedback = document.getElementById('username-valid');
            
            if (username.length < 3) {
                feedback.textContent = 'Username must be at least 3 characters';
                feedback.style.display = 'block';
                validFeedback.style.display = 'none';
                this.classList.add('is-invalid');
                this.classList.remove('is-valid');
            } else {
                feedback.style.display = 'none';
                validFeedback.textContent = 'Username looks good!';
                validFeedback.style.display = 'block';
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        });
    }
    
    // Real-time email validation
    if (emailInput) {
        emailInput.addEventListener('blur', function() {
            const email = this.value.trim();
            const feedback = document.getElementById('email-feedback');
            const validFeedback = document.getElementById('email-valid');
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            
            if (!emailRegex.test(email)) {
                feedback.textContent = 'Please enter a valid email address';
                feedback.style.display = 'block';
                validFeedback.style.display = 'none';
                this.classList.add('is-invalid');
                this.classList.remove('is-valid');
            } else {
                feedback.style.display = 'none';
                validFeedback.textContent = 'Email looks good!';
                validFeedback.style.display = 'block';
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        });
    }
    
    // Confirm password validation
    if (confirmPasswordInput && passwordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            const password = passwordInput.value;
            const confirmPassword = this.value;
            const feedback = document.getElementById('confirm-password-feedback');
            
            if (confirmPassword && confirmPassword !== password) {
                feedback.textContent = 'Passwords do not match';
                feedback.style.display = 'block';
                this.classList.add('is-invalid');
                this.classList.remove('is-valid');
            } else if (confirmPassword && confirmPassword === password) {
                feedback.style.display = 'none';
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        });
    }
    
    // Form submission
    form.addEventListener('submit', function(e) {
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        if (password !== confirmPassword) {
            e.preventDefault();
            const feedback = document.getElementById('confirm-password-feedback');
            feedback.textContent = 'Passwords do not match';
            feedback.style.display = 'block';
            confirmPasswordInput.classList.add('is-invalid');
        }
    });
}

// Login form validation
function initLoginValidation(form) {
    form.addEventListener('submit', function(e) {
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        
        if (!email || !password) {
            e.preventDefault();
            alert('Please fill in all fields');
        }
    });
}

// ========== Camera Functions ==========

// Camera state
let cameraStream = null;
let isRecording = false;
let recordingTimer = null;
let recordingStartTime = null;
let mediaRecorder = null;
let recordedChunks = [];

// Motion and Object Detection state
let motionDetectionEnabled = false;
let objectDetectionEnabled = false;
let motionDetectionInterval = null;
let objectDetectionInterval = null;
let previousFrame = null;
let motionSensitivity = 0.3;
let detectionCanvas = null;
let detectionCtx = null;

// Smart Alerts Configuration (moved here for global access)
let smartAlertsConfig = {
    motionAlertsEnabled: true,
    objectAlertsEnabled: true,
    soundAlertsEnabled: false,
    telegramAlertsEnabled: false,
    telegramChannelId: '',  // Telegram channel/chat ID
    motionThreshold: 30,
    objectCount: 1,
    cooldown: 10
};

// Alerts storage
let alerts = [];
let lastAlertTime = 0;

// Initialize camera functionality
function initCamera() {
    const startBtn = document.getElementById('startCamera');
    const stopBtn = document.getElementById('stopCamera');
    const recordBtn = document.getElementById('recordBtn');
    const stopRecordBtn = document.getElementById('stopRecordBtn');
    const screenshotBtn = document.getElementById('screenshotBtn');
    
    if (startBtn) {
        startBtn.addEventListener('click', startCamera);
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', stopCamera);
    }
    
    if (recordBtn) {
        recordBtn.addEventListener('click', startRecording);
    }
    
    if (stopRecordBtn) {
        stopRecordBtn.addEventListener('click', stopRecording);
    }
    
    if (screenshotBtn) {
        screenshotBtn.addEventListener('click', takeScreenshot);
    }
}

// Start camera
async function startCamera() {
    try {
        const video = document.getElementById('cameraFeed');
        const canvas = document.getElementById('cameraCanvas');
        const placeholder = document.getElementById('cameraPlaceholder');
        const startBtn = document.getElementById('startCamera');
        const stopBtn = document.getElementById('stopCamera');
        const recordBtn = document.getElementById('recordBtn');
        const screenshotBtn = document.getElementById('screenshotBtn');
        
        // Request camera access
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: document.getElementById('cameraSelect')?.value || 'user',
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: false
        });
        
        cameraStream = stream;
        video.srcObject = stream;
        
        // Show video, hide placeholder
        placeholder.style.display = 'none';
        video.style.display = 'block';
        canvas.style.display = 'none';
        
        // Update UI
        startBtn.disabled = true;
        stopBtn.disabled = false;
        recordBtn.disabled = false;
        screenshotBtn.disabled = false;
        
        updateCameraStatus('Connected', 'success');
        updateCameraResolution(video.videoWidth, video.videoHeight);
        
        // Update FPS (simplified)
        let frameCount = 0;
        let lastTime = Date.now();
        setInterval(() => {
            frameCount++;
            const currentTime = Date.now();
            if (currentTime - lastTime >= 1000) {
                document.getElementById('cameraFPS').textContent = frameCount + ' fps';
                frameCount = 0;
                lastTime = currentTime;
            }
        }, 100);
        
        // Handle video loaded
        video.onloadedmetadata = () => {
            updateCameraResolution(video.videoWidth, video.videoHeight);
        };
        
        // Start motion/object detection if enabled
        if (motionDetectionEnabled) {
            startMotionDetection();
        }
        if (objectDetectionEnabled) {
            startObjectDetection();
        }
        
    } catch (error) {
        console.error('Error accessing camera:', error);
        updateCameraStatus('Error: ' + error.message, 'danger');
        alert('Could not access camera. Please check permissions and try again.');
    }
}

// Stop camera
function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    
    const video = document.getElementById('cameraFeed');
    const placeholder = document.getElementById('cameraPlaceholder');
    const startBtn = document.getElementById('startCamera');
    const stopBtn = document.getElementById('stopCamera');
    const recordBtn = document.getElementById('recordBtn');
    const stopRecordBtn = document.getElementById('stopRecordBtn');
    const screenshotBtn = document.getElementById('screenshotBtn');
    
    if (video) {
        video.srcObject = null;
        video.style.display = 'none';
    }
    
    if (placeholder) {
        placeholder.style.display = 'flex';
    }
    
    // Update UI
    if (startBtn) startBtn.disabled = false;
    if (stopBtn) stopBtn.disabled = true;
    if (recordBtn) recordBtn.disabled = true;
    if (stopRecordBtn) stopRecordBtn.disabled = true;
    if (screenshotBtn) screenshotBtn.disabled = true;
    
    updateCameraStatus('Disconnected', 'secondary');
    document.getElementById('cameraResolution').textContent = '-';
    document.getElementById('cameraFPS').textContent = '-';
    
    // Stop recording if active
    if (isRecording) {
        stopRecording();
    }
    
    // Stop motion and object detection
    stopMotionDetection();
    stopObjectDetection();
    
    // Clear canvas overlay
    const canvas = document.getElementById('cameraCanvas');
    if (canvas) {
        canvas.style.display = 'none';
    }
}

// Start recording
function startRecording() {
    if (!cameraStream) {
        alert('Please start camera first');
        return;
    }
    
    try {
        recordedChunks = [];
        mediaRecorder = new MediaRecorder(cameraStream, {
            mimeType: 'video/webm;codecs=vp8'
        });
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = () => {
            const blob = new Blob(recordedChunks, { type: 'video/webm' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `recording-${Date.now()}.webm`;
            a.click();
            URL.revokeObjectURL(url);
        };
        
        mediaRecorder.start();
        isRecording = true;
        recordingStartTime = Date.now();
        
        const recordBtn = document.getElementById('recordBtn');
        const stopRecordBtn = document.getElementById('stopRecordBtn');
        if (recordBtn) recordBtn.disabled = true;
        if (stopRecordBtn) stopRecordBtn.disabled = false;
        
        document.getElementById('recordingStatus').textContent = 'Recording...';
        document.getElementById('recordingStatus').className = 'fw-semibold text-danger';
        
        // Start timer
        recordingTimer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            document.getElementById('recordingTimer').textContent = 
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
        
    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Could not start recording: ' + error.message);
    }
}

// Stop recording
function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        const recordBtn = document.getElementById('recordBtn');
        const stopRecordBtn = document.getElementById('stopRecordBtn');
        if (recordBtn) recordBtn.disabled = false;
        if (stopRecordBtn) stopRecordBtn.disabled = true;
        
        document.getElementById('recordingStatus').textContent = 'Ready';
        document.getElementById('recordingStatus').className = 'fw-semibold text-secondary';
        document.getElementById('recordingTimer').textContent = '00:00';
        
        if (recordingTimer) {
            clearInterval(recordingTimer);
            recordingTimer = null;
        }
    }
}

// Take screenshot
function takeScreenshot() {
    const video = document.getElementById('cameraFeed');
    const canvas = document.getElementById('cameraCanvas');
    
    if (!video || !video.srcObject) {
        alert('Please start camera first');
        return;
    }
    
    try {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);
        
        canvas.toBlob((blob) => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `screenshot-${Date.now()}.png`;
            a.click();
            URL.revokeObjectURL(url);
            
            document.getElementById('screenshotStatus').textContent = 'Saved!';
            setTimeout(() => {
                document.getElementById('screenshotStatus').textContent = 'Ready';
            }, 2000);
        }, 'image/png');
        
    } catch (error) {
        console.error('Error taking screenshot:', error);
        alert('Could not take screenshot: ' + error.message);
    }
}

// Update camera status
function updateCameraStatus(status, type = 'secondary') {
    const statusEl = document.getElementById('cameraStatus');
    if (statusEl) {
        statusEl.textContent = status;
        statusEl.className = `fw-semibold text-${type}`;
    }
}

// Update camera resolution
function updateCameraResolution(width, height) {
    const resolutionEl = document.getElementById('cameraResolution');
    if (resolutionEl && width && height) {
        resolutionEl.textContent = `${width}x${height}`;
    }
}

// ========== Motion Detection Functions ==========

// Initialize motion detection
function initMotionDetection() {
    const toggle = document.getElementById('motionDetectionToggle');
    const sensitivitySlider = document.getElementById('motionSensitivity');
    const sensitivityValue = document.getElementById('sensitivityValue');
    
    if (toggle) {
        toggle.addEventListener('change', function() {
            motionDetectionEnabled = this.checked;
            if (motionDetectionEnabled && cameraStream) {
                startMotionDetection();
            } else {
                stopMotionDetection();
            }
        });
    }
    
    if (sensitivitySlider && sensitivityValue) {
        sensitivitySlider.addEventListener('input', function() {
            motionSensitivity = parseFloat(this.value);
            sensitivityValue.textContent = motionSensitivity.toFixed(1);
        });
    }
}

// Start motion detection
function startMotionDetection() {
    if (motionDetectionInterval) {
        clearInterval(motionDetectionInterval);
    }
    
    const video = document.getElementById('cameraFeed');
    const canvas = document.getElementById('cameraCanvas');
    
    if (!video || !video.srcObject) {
        return;
    }
    
    // Create detection canvas if it doesn't exist
    if (!detectionCanvas) {
        detectionCanvas = document.createElement('canvas');
        detectionCtx = detectionCanvas.getContext('2d');
    }
    
    // Initialize previous frame
    previousFrame = null;
    
    motionDetectionInterval = setInterval(() => {
        if (!motionDetectionEnabled || !video.srcObject) {
            return;
        }
        
        try {
            // Set canvas dimensions
            detectionCanvas.width = video.videoWidth;
            detectionCanvas.height = video.videoHeight;
            
            // Draw current frame
            detectionCtx.drawImage(video, 0, 0);
            const currentFrame = detectionCtx.getImageData(0, 0, detectionCanvas.width, detectionCanvas.height);
            
            if (previousFrame) {
                // Compare frames
                const motion = detectMotion(previousFrame, currentFrame, motionSensitivity);
                
                if (motion.detected) {
                    updateMotionStatus(`Motion detected (${motion.intensity.toFixed(0)}%)`, 'danger');
                    
                    // Check if motion alert should be triggered
                    if (motion.intensity >= smartAlertsConfig.motionThreshold) {
                        createAlert('motion', `Motion detected: ${motion.intensity.toFixed(0)}% intensity`, {
                            intensity: motion.intensity,
                            regions: motion.regions.length
                        });
                    }
                    
                    // Draw motion regions on canvas overlay (only if object detection is not active)
                    if (!objectDetectionEnabled) {
                        drawMotionRegions(motion.regions);
                    }
                } else {
                    updateMotionStatus('No motion', 'success');
                    // Clear canvas if only motion detection is active
                    if (!objectDetectionEnabled) {
                        const canvas = document.getElementById('cameraCanvas');
                        if (canvas) {
                            canvas.style.display = 'none';
                        }
                    }
                }
            }
            
            // Store current frame as previous
            previousFrame = currentFrame;
        } catch (error) {
            console.error('Motion detection error:', error);
        }
    }, 100); // Check every 100ms
}

// Stop motion detection
function stopMotionDetection() {
    if (motionDetectionInterval) {
        clearInterval(motionDetectionInterval);
        motionDetectionInterval = null;
    }
    previousFrame = null;
    updateMotionStatus('Disabled', 'secondary');
}

// Detect motion between two frames
function detectMotion(frame1, frame2, sensitivity) {
    const data1 = frame1.data;
    const data2 = frame2.data;
    const width = frame1.width;
    const height = frame1.height;
    
    let totalDiff = 0;
    let motionPixels = 0;
    const threshold = sensitivity * 255;
    const regions = [];
    
    // Sample every 4th pixel for performance
    for (let i = 0; i < data1.length; i += 16) {
        const r1 = data1[i];
        const g1 = data1[i + 1];
        const b1 = data1[i + 2];
        const r2 = data2[i];
        const g2 = data2[i + 1];
        const b2 = data2[i + 2];
        
        // Calculate difference
        const diff = Math.abs(r1 - r2) + Math.abs(g1 - g2) + Math.abs(b1 - b2);
        totalDiff += diff;
        
        if (diff > threshold) {
            motionPixels++;
            const pixelIndex = i / 4;
            const x = (pixelIndex % width);
            const y = Math.floor(pixelIndex / width);
            regions.push({ x, y });
        }
    }
    
    const intensity = (motionPixels / (data1.length / 16)) * 100;
    const detected = intensity > (sensitivity * 10);
    
    return {
        detected,
        intensity,
        regions: detected ? regions : []
    };
}

// Draw motion regions on canvas
function drawMotionRegions(regions) {
    const canvas = document.getElementById('cameraCanvas');
    const video = document.getElementById('cameraFeed');
    
    if (!canvas || !video || !video.srcObject) {
        return;
    }
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.style.display = 'block';
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    // Draw motion regions
    if (regions.length > 0) {
        ctx.strokeStyle = 'rgba(255, 0, 0, 0.5)';
        ctx.fillStyle = 'rgba(255, 0, 0, 0.2)';
        ctx.lineWidth = 2;
        
        // Group nearby regions
        const groupedRegions = groupRegions(regions);
        
        groupedRegions.forEach(region => {
            ctx.fillRect(region.x - 10, region.y - 10, 20, 20);
            ctx.strokeRect(region.x - 10, region.y - 10, 20, 20);
        });
    }
}

// Group nearby regions
function groupRegions(regions) {
    if (regions.length === 0) return [];
    
    const grouped = [];
    const processed = new Set();
    
    regions.forEach(region => {
        if (processed.has(`${region.x},${region.y}`)) return;
        
        const nearby = regions.filter(r => 
            Math.abs(r.x - region.x) < 30 && Math.abs(r.y - region.y) < 30
        );
        
        const avgX = Math.round(nearby.reduce((sum, r) => sum + r.x, 0) / nearby.length);
        const avgY = Math.round(nearby.reduce((sum, r) => sum + r.y, 0) / nearby.length);
        
        grouped.push({ x: avgX, y: avgY });
        nearby.forEach(r => processed.add(`${r.x},${r.y}`));
    });
    
    return grouped;
}

// Update motion status
function updateMotionStatus(status, type = 'secondary') {
    const statusEl = document.getElementById('motionStatus');
    if (statusEl) {
        statusEl.textContent = status;
        statusEl.className = `fw-semibold text-${type}`;
    }
}

// ========== Object Detection Functions ==========

// Initialize object detection
function initObjectDetection() {
    const toggle = document.getElementById('objectDetectionToggle');
    
    if (toggle) {
        toggle.addEventListener('change', function() {
            objectDetectionEnabled = this.checked;
            if (objectDetectionEnabled && cameraStream) {
                startObjectDetection();
            } else {
                stopObjectDetection();
            }
        });
    }
}

// Start object detection
function startObjectDetection() {
    if (objectDetectionInterval) {
        clearInterval(objectDetectionInterval);
    }
    
    const video = document.getElementById('cameraFeed');
    
    if (!video || !video.srcObject) {
        return;
    }
    
    // Create detection canvas if it doesn't exist
    if (!detectionCanvas) {
        detectionCanvas = document.createElement('canvas');
        detectionCtx = detectionCanvas.getContext('2d');
    }
    
    objectDetectionInterval = setInterval(() => {
        if (!objectDetectionEnabled || !video.srcObject) {
            return;
        }
        
        try {
            // Set canvas dimensions
            detectionCanvas.width = video.videoWidth;
            detectionCanvas.height = video.videoHeight;
            
            // Draw current frame
            detectionCtx.drawImage(video, 0, 0);
            const frameData = detectionCtx.getImageData(0, 0, detectionCanvas.width, detectionCanvas.height);
            
            // Detect objects
            const objects = detectObjects(frameData);
            
            // Update status
            updateObjectStatus(objects.length);
            
            // Check if object alert should be triggered
            if (objects.length >= smartAlertsConfig.objectCount) {
                createAlert('object', `${objects.length} object(s) detected`, {
                    objectCount: objects.length,
                    objects: objects.map(obj => obj.type)
                });
            }
            
            // Draw detected objects (this will also show video frame)
            drawDetectedObjects(objects);
        } catch (error) {
            console.error('Object detection error:', error);
        }
    }, 500); // Check every 500ms
}

// Stop object detection
function stopObjectDetection() {
    if (objectDetectionInterval) {
        clearInterval(objectDetectionInterval);
        objectDetectionInterval = null;
    }
    updateObjectStatus(0);
    
    // Clear canvas if motion detection is also not active
    if (!motionDetectionEnabled) {
        const canvas = document.getElementById('cameraCanvas');
        if (canvas) {
            canvas.style.display = 'none';
        }
    }
}

// Detect objects in frame (basic blob detection)
function detectObjects(frameData) {
    const data = frameData.data;
    const width = frameData.width;
    const height = frameData.height;
    const objects = [];
    
    // Simple edge detection and blob detection
    const edges = detectEdges(data, width, height);
    const blobs = findBlobs(edges, width, height);
    
    // Filter blobs by size (remove noise)
    const significantBlobs = blobs.filter(blob => blob.size > 100);
    
    return significantBlobs.map(blob => ({
        x: blob.centerX,
        y: blob.centerY,
        width: blob.width,
        height: blob.height,
        type: classifyObject(blob)
    }));
}

// Detect edges using Sobel operator
function detectEdges(data, width, height) {
    const edges = new Uint8Array(width * height);
    
    for (let y = 1; y < height - 1; y++) {
        for (let x = 1; x < width - 1; x++) {
            // Get grayscale values for Sobel operator
            const getGray = (px, py) => {
                const idx = (py * width + px) * 4;
                return (data[idx] + data[idx + 1] + data[idx + 2]) / 3;
            };
            
            // Sobel operator
            const gx = -getGray(x - 1, y - 1) + getGray(x + 1, y - 1)
                      - 2 * getGray(x - 1, y) + 2 * getGray(x + 1, y)
                      - getGray(x - 1, y + 1) + getGray(x + 1, y + 1);
            
            const gy = -getGray(x - 1, y - 1) - 2 * getGray(x, y - 1) - getGray(x + 1, y - 1)
                      + getGray(x - 1, y + 1) + 2 * getGray(x, y + 1) + getGray(x + 1, y + 1);
            
            const magnitude = Math.sqrt(gx * gx + gy * gy);
            edges[y * width + x] = magnitude > 50 ? 255 : 0;
        }
    }
    
    return edges;
}

// Find blobs (connected components)
function findBlobs(edges, width, height) {
    const visited = new Set();
    const blobs = [];
    
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const idx = y * width + x;
            if (edges[idx] === 255 && !visited.has(idx)) {
                const blob = floodFill(edges, width, height, x, y, visited);
                if (blob.pixels.length > 50) {
                    blobs.push(blob);
                }
            }
        }
    }
    
    return blobs;
}

// Flood fill to find connected components
function floodFill(edges, width, height, startX, startY, visited) {
    const pixels = [];
    const stack = [[startX, startY]];
    
    let minX = startX, maxX = startX;
    let minY = startY, maxY = startY;
    
    while (stack.length > 0) {
        const [x, y] = stack.pop();
        const idx = y * width + x;
        
        if (x < 0 || x >= width || y < 0 || y >= height || visited.has(idx) || edges[idx] !== 255) {
            continue;
        }
        
        visited.add(idx);
        pixels.push([x, y]);
        
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
        
        // Check neighbors
        stack.push([x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]);
    }
    
    const centerX = Math.round((minX + maxX) / 2);
    const centerY = Math.round((minY + maxY) / 2);
    
    return {
        pixels,
        centerX,
        centerY,
        width: maxX - minX,
        height: maxY - minY,
        size: pixels.length
    };
}

// Classify object (simple heuristic)
function classifyObject(blob) {
    const aspectRatio = blob.width / blob.height;
    const area = blob.width * blob.height;
    
    if (aspectRatio > 1.5) {
        return 'Horizontal Object';
    } else if (aspectRatio < 0.7) {
        return 'Vertical Object';
    } else if (area > 5000) {
        return 'Large Object';
    } else {
        return 'Small Object';
    }
}

// Draw detected objects
function drawDetectedObjects(objects) {
    const canvas = document.getElementById('cameraCanvas');
    const video = document.getElementById('cameraFeed');
    
    if (!canvas || !video || !video.srcObject) {
        return;
    }
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.style.display = 'block';
    
    const ctx = canvas.getContext('2d');
    
    // Clear canvas and draw video frame
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Draw bounding boxes
    objects.forEach(obj => {
        ctx.strokeStyle = 'rgba(0, 255, 0, 0.8)';
        ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
        ctx.lineWidth = 2;
        
        const x = obj.x - obj.width / 2;
        const y = obj.y - obj.height / 2;
        
        ctx.fillRect(x, y, obj.width, obj.height);
        ctx.strokeRect(x, y, obj.width, obj.height);
        
        // Draw label background
        ctx.fillStyle = 'rgba(0, 255, 0, 0.9)';
        ctx.fillRect(x, y - 20, obj.type.length * 7, 18);
        
        // Draw label text
        ctx.fillStyle = 'rgba(0, 0, 0, 0.9)';
        ctx.font = '12px Arial';
        ctx.fillText(obj.type, x + 2, y - 5);
    });
}

// Update object status
function updateObjectStatus(count) {
    const statusEl = document.getElementById('objectStatus');
    if (statusEl) {
        statusEl.textContent = `${count} detected`;
        statusEl.className = count > 0 ? 'fw-semibold text-success' : 'fw-semibold text-secondary';
    }
}

// ========== Smart Alerts Functions ==========

// Open smart alerts configuration modal
function openSmartAlertsConfig() {
    // Load current config
    const savedConfig = localStorage.getItem('smartAlertsConfig');
    if (savedConfig) {
        smartAlertsConfig = JSON.parse(savedConfig);
    }
    
    // Update modal with current values
    document.getElementById('enableMotionAlerts').checked = smartAlertsConfig.motionAlertsEnabled;
    document.getElementById('enableObjectAlerts').checked = smartAlertsConfig.objectAlertsEnabled;
    document.getElementById('enableSoundAlerts').checked = smartAlertsConfig.soundAlertsEnabled;
    document.getElementById('enableTelegramAlerts').checked = smartAlertsConfig.telegramAlertsEnabled;
    document.getElementById('telegramChannelId').value = smartAlertsConfig.telegramChannelId || '';
    document.getElementById('motionAlertThreshold').value = smartAlertsConfig.motionThreshold;
    document.getElementById('motionThresholdValue').textContent = smartAlertsConfig.motionThreshold;
    document.getElementById('objectAlertCount').value = smartAlertsConfig.objectCount;
    document.getElementById('alertCooldown').value = smartAlertsConfig.cooldown;
    
    // Update threshold display on slider change
    document.getElementById('motionAlertThreshold').addEventListener('input', function() {
        document.getElementById('motionThresholdValue').textContent = this.value;
    });
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('smartAlertsModal'));
    modal.show();
}

// Save smart alerts configuration
function saveSmartAlertsConfig() {
    const telegramChannelId = document.getElementById('telegramChannelId').value.trim();
    const telegramEnabled = document.getElementById('enableTelegramAlerts').checked;
    
    // Validate Telegram configuration
    if (telegramEnabled && !telegramChannelId) {
        alert('Please enter a Telegram Channel/Chat ID to enable Telegram notifications.');
        return;
    }
    
    smartAlertsConfig = {
        motionAlertsEnabled: document.getElementById('enableMotionAlerts').checked,
        objectAlertsEnabled: document.getElementById('enableObjectAlerts').checked,
        soundAlertsEnabled: document.getElementById('enableSoundAlerts').checked,
        telegramAlertsEnabled: telegramEnabled,
        telegramChannelId: telegramChannelId,
        motionThreshold: parseInt(document.getElementById('motionAlertThreshold').value),
        objectCount: parseInt(document.getElementById('objectAlertCount').value),
        cooldown: parseInt(document.getElementById('alertCooldown').value)
    };
    
    // Save to localStorage
    localStorage.setItem('smartAlertsConfig', JSON.stringify(smartAlertsConfig));
    
    // Update status badge
    const statusBadge = document.getElementById('smartAlertsStatus');
    if (statusBadge) {
        const isActive = smartAlertsConfig.motionAlertsEnabled || smartAlertsConfig.objectAlertsEnabled;
        statusBadge.textContent = isActive ? 'Active' : 'Inactive';
        statusBadge.className = isActive ? 'badge bg-success align-self-center' : 'badge bg-secondary align-self-center';
    }
    
    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('smartAlertsModal'));
    modal.hide();
    
    // Show success message
    showAlert('Smart Alerts configuration saved!', 'success');
}

// Create and display alert
function createAlert(type, message, data = {}) {
    const now = Date.now();
    
    // Check cooldown
    if (now - lastAlertTime < smartAlertsConfig.cooldown * 1000) {
        return; // Skip alert due to cooldown
    }
    
    // Check if alert type is enabled
    if (type === 'motion' && !smartAlertsConfig.motionAlertsEnabled) {
        return;
    }
    if (type === 'object' && !smartAlertsConfig.objectAlertsEnabled) {
        return;
    }
    
    lastAlertTime = now;
    
    // Create alert object
    const alert = {
        id: Date.now(),
        type: type,
        message: message,
        timestamp: new Date().toISOString(),
        data: data
    };
    
    // Add to alerts array (keep last 50)
    alerts.unshift(alert);
    if (alerts.length > 50) {
        alerts = alerts.slice(0, 50);
    }
    
    // Save to localStorage
    localStorage.setItem('dashboardAlerts', JSON.stringify(alerts));
    
    // Display alert
    displayAlert(alert);
    
    // Play sound if enabled
    if (smartAlertsConfig.soundAlertsEnabled) {
        playAlertSound();
    }
    
    // Send Telegram notification if enabled
    if (smartAlertsConfig.telegramAlertsEnabled) {
        sendTelegramAlert(alert);
    }
}

// Display alert in UI
function displayAlert(alert) {
    const alertsList = document.getElementById('alertsList');
    const noAlertsPlaceholder = document.getElementById('noAlertsPlaceholder');
    
    if (!alertsList) return;
    
    // Hide placeholder
    if (noAlertsPlaceholder) {
        noAlertsPlaceholder.style.display = 'none';
    }
    
    // Create alert element
    const alertItem = document.createElement('div');
    alertItem.className = 'list-group-item d-flex align-items-start';
    alertItem.id = `alert-${alert.id}`;
    
    // Determine icon and color based on type
    let icon = 'bi-exclamation-triangle';
    let color = 'warning';
    if (alert.type === 'motion') {
        icon = 'bi-activity';
        color = 'danger';
    } else if (alert.type === 'object') {
        icon = 'bi-shield-check';
        color = 'info';
    }
    
    const time = new Date(alert.timestamp).toLocaleTimeString();
    
    alertItem.innerHTML = `
        <i class="bi ${icon} text-${color} me-2 mt-1"></i>
        <div class="flex-grow-1">
            <div class="fw-semibold">${alert.message}</div>
            <div class="text-muted small">${time}</div>
            ${alert.data.intensity ? `<div class="text-muted small">Intensity: ${alert.data.intensity.toFixed(0)}%</div>` : ''}
            ${alert.data.objectCount ? `<div class="text-muted small">Objects: ${alert.data.objectCount}</div>` : ''}
        </div>
        <button class="btn btn-sm btn-outline-secondary" onclick="dismissAlert(${alert.id})" title="Dismiss">
            <i class="bi bi-x"></i>
        </button>
    `;
    
    // Add to top of list
    alertsList.insertBefore(alertItem, alertsList.firstChild);
    
    // Add animation
    alertItem.style.opacity = '0';
    alertItem.style.transform = 'translateY(-10px)';
    setTimeout(() => {
        alertItem.style.transition = 'all 0.3s ease';
        alertItem.style.opacity = '1';
        alertItem.style.transform = 'translateY(0)';
    }, 10);
}

// Dismiss alert
function dismissAlert(alertId) {
    // Remove from array
    alerts = alerts.filter(a => a.id !== alertId);
    localStorage.setItem('dashboardAlerts', JSON.stringify(alerts));
    
    // Remove from UI
    const alertElement = document.getElementById(`alert-${alertId}`);
    if (alertElement) {
        alertElement.style.transition = 'all 0.3s ease';
        alertElement.style.opacity = '0';
        alertElement.style.transform = 'translateX(-20px)';
        setTimeout(() => {
            alertElement.remove();
            checkNoAlerts();
        }, 300);
    }
}

// Clear all alerts
function clearAlerts() {
    if (confirm('Clear all alerts?')) {
        alerts = [];
        localStorage.setItem('dashboardAlerts', JSON.stringify(alerts));
        const alertsList = document.getElementById('alertsList');
        if (alertsList) {
            alertsList.innerHTML = `
                <div class="list-group-item d-flex align-items-start" id="noAlertsPlaceholder">
                    <i class="bi bi-exclamation-triangle text-warning me-2"></i>
                    <div>
                        <div class="fw-semibold">No alerts yet</div>
                        <div class="text-muted small">Alerts will appear here with snapshots and timestamps.</div>
                    </div>
                </div>
            `;
        }
    }
}

// Check if no alerts and show placeholder
function checkNoAlerts() {
    const alertsList = document.getElementById('alertsList');
    if (alertsList && alertsList.children.length === 0) {
        alertsList.innerHTML = `
            <div class="list-group-item d-flex align-items-start" id="noAlertsPlaceholder">
                <i class="bi bi-exclamation-triangle text-warning me-2"></i>
                <div>
                    <div class="fw-semibold">No alerts yet</div>
                    <div class="text-muted small">Alerts will appear here with snapshots and timestamps.</div>
                </div>
            </div>
        `;
    }
}

// Load saved alerts
function loadSavedAlerts() {
    const savedAlerts = localStorage.getItem('dashboardAlerts');
    if (savedAlerts) {
        alerts = JSON.parse(savedAlerts);
        alerts.forEach(alert => displayAlert(alert));
    }
}

// Play alert sound
function playAlertSound() {
    // Create audio context for beep sound
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.3);
    } catch (e) {
        console.warn('Could not play alert sound:', e);
    }
}

// Send Telegram alert (if configured)
function sendTelegramAlert(alert) {
    if (!smartAlertsConfig.telegramAlertsEnabled || !smartAlertsConfig.telegramChannelId) {
        console.warn('Telegram alerts not properly configured');
        return;
    }
    
    // Format alert message
    const emoji = alert.type === 'motion' ? '🔴' : '🔵';
    const alertType = alert.type === 'motion' ? 'Motion Detection' : 'Object Detection';
    const timestamp = new Date(alert.timestamp).toLocaleString();
    
    let message = `${emoji} <b>${alertType} Alert</b>\n\n`;
    message += `${alert.message}\n\n`;
    message += `⏰ <b>Time:</b> ${timestamp}\n`;
    
    if (alert.data.intensity) {
        message += `📊 <b>Intensity:</b> ${alert.data.intensity.toFixed(0)}%\n`;
        message += `📍 <b>Regions:</b> ${alert.data.regions || 0}\n`;
    }
    
    if (alert.data.objectCount) {
        message += `🔍 <b>Objects Detected:</b> ${alert.data.objectCount}\n`;
        if (alert.data.objects && alert.data.objects.length > 0) {
            message += `📦 <b>Types:</b> ${alert.data.objects.join(', ')}\n`;
        }
    }
    
    message += `\n🔔 <i>VigilantEye Smart Alert System</i>`;
    
    // Send to Telegram API
    fetch('/api/telegram/ingest', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            type: 'text',
            content: message,
            channel_id: smartAlertsConfig.telegramChannelId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error('Telegram alert failed:', data.error);
        } else {
            console.log('Telegram alert sent successfully:', data);
        }
    })
    .catch(error => {
        console.error('Error sending Telegram alert:', error);
    });
}

// Show Telegram setup help
function showTelegramSetupHelp() {
    const modal = new bootstrap.Modal(document.getElementById('telegramHelpModal'));
    modal.show();
}

// Show temporary alert message
function showAlert(message, type = 'info') {
    // Create toast-like notification
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

// Initialize smart alerts on dashboard load
function initSmartAlerts() {
    // Load saved configuration
    const savedConfig = localStorage.getItem('smartAlertsConfig');
    if (savedConfig) {
        smartAlertsConfig = JSON.parse(savedConfig);
    }
    
    // Update status badge
    const statusBadge = document.getElementById('smartAlertsStatus');
    if (statusBadge) {
        const isActive = smartAlertsConfig.motionAlertsEnabled || smartAlertsConfig.objectAlertsEnabled;
        statusBadge.textContent = isActive ? 'Active' : 'Inactive';
        statusBadge.className = isActive ? 'badge bg-success align-self-center' : 'badge bg-secondary align-self-center';
    }
    
    // Load saved alerts
    loadSavedAlerts();
}

// Initialize camera on dashboard load
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('startCamera')) {
        initCamera();
        initMotionDetection();
        initObjectDetection();
        initSmartAlerts();
    }
});