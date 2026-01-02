// ===============================
// Advanced Drowsiness Dashboard
// Real-time Updates with Animations
// ===============================

// Global state
let pitchData = [];
let gyroData = [];
let labels = [];
let lastUpdateTime = Date.now();
let isConnected = true;

const MAX_POINTS = 50;
const UPDATE_INTERVAL = 2000; // 2 seconds

// ===============================
// Smooth Number Animation
// ===============================
function animateValue(element, start, end, duration = 500) {
    if (!element) return;
    
    const startTime = performance.now();
    const isNumber = !isNaN(start) && !isNaN(end);
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out)
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        
        if (isNumber) {
            const current = start + (end - start) * easeProgress;
            element.textContent = Math.round(current * 10) / 10;
        } else {
            element.textContent = end;
        }
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// ===============================
// Update UI Indicators with Animation
// ===============================
function updateIndicators(live) {
    // Pitch
    const pitchEl = document.getElementById('pitchValue');
    if (pitchEl) {
        const current = parseFloat(pitchEl.textContent.replace('°', '')) || 0;
        const newValue = live.pitch ?? 0;
        if (Math.abs(current - newValue) > 0.1) {
            animateValue(pitchEl, current, newValue);
            pitchEl.textContent = Math.round(newValue * 10) / 10 + '°';
        }
    }

    // Gyro Y
    const gyroEl = document.getElementById('gyroValue');
    if (gyroEl) {
        const current = parseFloat(gyroEl.textContent) || 0;
        const newValue = live.gyroY ?? 0;
        if (Math.abs(current - newValue) > 0.1) {
            animateValue(gyroEl, current, newValue);
            gyroEl.textContent = Math.round(newValue);
        }
    }

    // Temperature
    const tempEl = document.getElementById('tempValue');
    if (tempEl) {
        const current = parseFloat(tempEl.textContent.replace('°C', '')) || 0;
        const newValue = live.bodyTemp ?? 0;
        if (Math.abs(current - newValue) > 0.1) {
            animateValue(tempEl, current, newValue);
            tempEl.textContent = Math.round(newValue * 10) / 10 + '°C';
            
            // Add visual feedback for high temperature
            const card = tempEl.closest('.metric-card');
            if (card) {
                if (newValue > 38) {
                    card.style.borderColor = 'rgba(239, 68, 68, 0.6)';
                    card.style.boxShadow = '0 0 20px rgba(239, 68, 68, 0.4)';
                } else {
                    card.style.borderColor = '';
                    card.style.boxShadow = '';
                }
            }
        }
    }

    // Heart Rate
    const heartRateEl = document.getElementById('heartRateValue');
    if (heartRateEl) {
        const current = parseFloat(heartRateEl.textContent) || 0;
        const newValue = live.heartRate ?? 0;
        if (Math.abs(current - newValue) > 1) {
            animateValue(heartRateEl, current, newValue);
            heartRateEl.innerHTML = Math.round(newValue) + ' <small style="font-size: 0.6em">bpm</small>';
            
            // Pulse animation for heart rate
            const card = heartRateEl.closest('.metric-card');
            if (card) {
                card.style.animation = 'pulse 1s ease-in-out';
                setTimeout(() => {
                    card.style.animation = '';
                }, 1000);
            }
        }
    }

    // Drowsy State
    const drowsyEl = document.getElementById('drowsyState');
    if (drowsyEl) {
        const isDrowsy = live.isDrowsy || false;
        const currentText = drowsyEl.textContent.trim();
        const newText = isDrowsy ? 'DROWSY' : 'NORMAL';
        
        if (currentText !== newText) {
            // Animate state change
            drowsyEl.style.transform = 'scale(0.8)';
            drowsyEl.style.opacity = '0.5';
            
            setTimeout(() => {
                drowsyEl.innerHTML = isDrowsy 
                    ? '<span class="status-indicator danger"></span>DROWSY'
                    : '<span class="status-indicator active"></span>NORMAL';
                drowsyEl.className = isDrowsy
                    ? 'metric status-bad'
                    : 'metric status-ok';
                
                drowsyEl.style.transform = 'scale(1)';
                drowsyEl.style.opacity = '1';
                drowsyEl.style.transition = 'all 0.3s ease';
                
                // Show alert for drowsiness
                if (isDrowsy) {
                    showDrowsinessAlert();
                }
            }, 200);
        }
    }
}

// ===============================
// Update Chart with Smooth Animation
// ===============================
function updateChart(pitch, gyroY) {
    if (typeof motionChart === 'undefined') {
        console.warn('Chart not initialized');
        return;
    }

    // Add new data point
    if (labels.length >= MAX_POINTS) {
        labels.shift();
        pitchData.shift();
        gyroData.shift();
    }

    labels.push('');
    pitchData.push(pitch);
    gyroData.push(gyroY);

    // Update chart with animation
    motionChart.data.labels = labels;
    motionChart.data.datasets[0].data = pitchData;
    motionChart.data.datasets[1].data = gyroData;
    
    // Use 'none' mode for smoother updates
    motionChart.update('none');
}

// ===============================
// Fetch Live Telemetry
// ===============================
async function fetchLiveData() {
    try {
        const startTime = performance.now();
        const res = await fetch('/api/live', {
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache'
            }
        });
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        
        const json = await res.json();
        const fetchTime = performance.now() - startTime;

        if (!json.live) {
            console.warn('No live data received');
            return;
        }

        const pitch = json.live.pitch ?? 0;
        const gyroY = json.live.gyroY ?? 0;

        // Update chart
        updateChart(pitch, gyroY);
        
        // Update indicators with animation
        updateIndicators(json.live);

        // Update connection status
        updateConnectionStatus(true);
        lastUpdateTime = Date.now();

        // Log performance (optional)
        if (fetchTime > 500) {
            console.warn(`Slow API response: ${fetchTime.toFixed(2)}ms`);
        }

    } catch (err) {
        console.error('Live fetch error:', err);
        updateConnectionStatus(false);
        
        // Show connection error toast
        if (isConnected) {
            showToast('danger', 'Connection lost. Retrying...');
            isConnected = false;
        }
    }
}

// ===============================
// Update Connection Status
// ===============================
function updateConnectionStatus(connected) {
    const liveBadge = document.querySelector('.live-badge');
    const liveDot = document.querySelector('.live-dot');
    
    if (liveBadge && liveDot) {
        if (connected) {
            liveBadge.style.opacity = '1';
            liveDot.style.background = '#22c55e';
            liveDot.style.boxShadow = '0 0 10px rgba(34, 197, 94, 0.8)';
            isConnected = true;
        } else {
            liveBadge.style.opacity = '0.5';
            liveDot.style.background = '#ef4444';
            liveDot.style.boxShadow = '0 0 10px rgba(239, 68, 68, 0.8)';
        }
    }
}

// ===============================
// Show Drowsiness Alert
// ===============================
function showDrowsinessAlert() {
    const alertsContainer = document.getElementById('alertsContainer');
    if (!alertsContainer) return;

    const alertItem = document.createElement('div');
    alertItem.className = 'alert-item danger';
    alertItem.innerHTML = `
        <div class="d-flex justify-content-between align-items-start mb-1">
            <strong class="text-white">
                <i class="bi bi-exclamation-triangle-fill"></i> DROWSINESS_DETECTED
            </strong>
            <small class="text-muted">${new Date().toLocaleTimeString()}</small>
        </div>
        <small class="text-muted">Driver drowsiness detected. Motor stopped automatically.</small>
    `;
    
    alertsContainer.insertBefore(alertItem, alertsContainer.firstChild);
    
    // Remove old alerts if too many
    const alerts = alertsContainer.querySelectorAll('.alert-item');
    if (alerts.length > 10) {
        alerts[alerts.length - 1].remove();
    }
    
    // Animate in
    alertItem.style.animation = 'slideInRight 0.5s ease-out';
    
    // Show browser notification if permitted
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Drowsiness Detected!', {
            body: 'Driver drowsiness has been detected. Motor stopped.',
            icon: '/static/favicon.ico',
            tag: 'drowsiness-alert'
        });
    }
}

// ===============================
// Toast Notification Helper
// ===============================
function showToast(type, message) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: 'check-circle',
        danger: 'exclamation-triangle',
        warning: 'exclamation-circle',
        info: 'info-circle'
    };
    
    toast.innerHTML = `
        <i class="bi bi-${icons[type] || 'info-circle'}-fill" style="font-size: 1.5rem; color: var(--${type === 'success' ? 'success' : type === 'danger' ? 'danger' : type === 'warning' ? 'warning' : 'info'});"></i>
        <div>
            <strong>${type.charAt(0).toUpperCase() + type.slice(1)}</strong><br>
            <small>${message}</small>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.5s ease-out';
    }, 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.5s ease-out reverse';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

// ===============================
// Request Notification Permission
// ===============================
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
            console.log('Notification permission granted');
        }
    });
}

// ===============================
// Motor Control Functions
// ===============================
async function setMotor(state) {
    try {
        const response = await fetch('/control/motor', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({state})
        });
        
        const data = await response.json();
        
        if (data.status === 'OK') {
            showToast('success', `Motor turned ${state}`);
            updateMotorStatus(state);
        } else {
            showToast('danger', 'Failed to control motor');
        }
    } catch (err) {
        console.error('Motor control error:', err);
        showToast('danger', 'Network error. Please try again.');
    }
}

async function emergencyStop() {
    if (!confirm('🚨 Are you sure you want to activate emergency stop?')) {
        return;
    }
    
    try {
        const response = await fetch('/control/emergency-stop', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'EMERGENCY_STOP_ACTIVATED') {
            showToast('danger', '🚨 Emergency stop activated!');
            updateMotorStatus('OFF');
            
            // Visual feedback
            document.body.style.animation = 'pulse 0.5s';
            setTimeout(() => {
                document.body.style.animation = '';
            }, 500);
        }
    } catch (err) {
        console.error('Emergency stop error:', err);
        showToast('danger', 'Failed to activate emergency stop');
    }
}

async function updateMotorStatus(forcedState = null) {
    try {
        if (forcedState) {
            const statusEl = document.getElementById('motorStatus');
            if (statusEl) {
                statusEl.textContent = forcedState;
                statusEl.className = 'badge ' + (forcedState === 'ON' ? 'bg-success' : 'bg-danger');
            }
            return;
        }
        
        const response = await fetch('/api/motor');
        const data = await response.json();
        
        const statusEl = document.getElementById('motorStatus');
        if (statusEl) {
            const motorState = data.motor || 'UNKNOWN';
            statusEl.textContent = motorState;
            statusEl.className = 'badge ' + (motorState === 'ON' ? 'bg-success' : 'bg-danger');
        }
    } catch (err) {
        console.error('Motor status error:', err);
    }
}

// ===============================
// Initialize and Start Updates
// ===============================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Drowsiness Dashboard initialized');
    
    // Initial data fetch
    fetchLiveData();
    
    // Update motor status
    updateMotorStatus();
    
    // Set up periodic updates
    setInterval(fetchLiveData, UPDATE_INTERVAL);
    setInterval(updateMotorStatus, 10000); // Update motor status every 10s
    
    // Check for inactivity
    setInterval(() => {
        const timeSinceUpdate = Date.now() - lastUpdateTime;
        if (timeSinceUpdate > UPDATE_INTERVAL * 3) {
            updateConnectionStatus(false);
        }
    }, 5000);
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + E for emergency stop
        if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
            e.preventDefault();
            emergencyStop();
        }
    });
});

// ===============================
// Export functions for global use
// ===============================
if (typeof window !== 'undefined') {
    window.setMotor = setMotor;
    window.emergencyStop = emergencyStop;
    window.updateChart = updateChart;
    window.showToast = showToast;
}
