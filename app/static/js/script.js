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
