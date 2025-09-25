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
});

function initFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
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

