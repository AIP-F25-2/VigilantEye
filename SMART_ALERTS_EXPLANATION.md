# Smart Alerts System - How It Works

## Overview
The Smart Alerts system is a real-time notification system that monitors camera feeds for motion and object detection events, triggering alerts when configured thresholds are exceeded.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Camera Feed (Video Stream)                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │   Detection Systems            │
        │  ┌──────────┐  ┌──────────┐  │
        │  │  Motion  │  │  Object  │  │
        │  │Detection │  │Detection │  │
        │  └────┬──────┘  └────┬──────┘  │
        └──────┼──────────────┼──────────┘
               │              │
               ▼              ▼
        ┌───────────────────────────────┐
        │   Alert Trigger Logic         │
        │  • Check threshold            │
        │  • Check cooldown             │
        │  • Check if enabled           │
        └──────────────┬────────────────┘
                       │
                       ▼
        ┌───────────────────────────────┐
        │   Alert Creation              │
        │  • Create alert object        │
        │  • Store in memory             │
        │  • Save to localStorage       │
        └──────────────┬────────────────┘
                       │
                       ▼
        ┌───────────────────────────────┐
        │   Alert Display               │
        │  • Show in UI panel            │
        │  • Play sound (optional)      │
        │  • Send Telegram (optional)   │
        └───────────────────────────────┘
```

## Alert Flow

### 1. Detection Phase

#### Motion Detection Alerts
```javascript
// Location: app/static/js/script.js (lines 756-765)

if (motion.detected) {
    updateMotionStatus(`Motion detected (${motion.intensity.toFixed(0)}%)`, 'danger');
    
    // Check if motion alert should be triggered
    if (motion.intensity >= smartAlertsConfig.motionThreshold) {
        createAlert('motion', `Motion detected: ${motion.intensity.toFixed(0)}% intensity`, {
            intensity: motion.intensity,
            regions: motion.regions.length
        });
    }
}
```

**How it works:**
- Motion detection runs continuously (every ~100ms)
- Compares current frame with previous frame
- Calculates motion intensity (0-100%)
- If intensity ≥ configured threshold → triggers alert

#### Object Detection Alerts
```javascript
// Location: app/static/js/script.js (lines 960-970)

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
```

**How it works:**
- Object detection runs every 500ms
- Uses edge detection and blob detection algorithms
- Counts detected objects
- If count ≥ configured minimum → triggers alert

### 2. Alert Creation Phase

```javascript
// Location: app/static/js/script.js (lines 1239-1288)

function createAlert(type, message, data = {}) {
    const now = Date.now();
    
    // Step 1: Check cooldown period
    if (now - lastAlertTime < smartAlertsConfig.cooldown * 1000) {
        return; // Skip alert due to cooldown
    }
    
    // Step 2: Check if alert type is enabled
    if (type === 'motion' && !smartAlertsConfig.motionAlertsEnabled) {
        return;
    }
    if (type === 'object' && !smartAlertsConfig.objectAlertsEnabled) {
        return;
    }
    
    // Step 3: Update last alert time
    lastAlertTime = now;
    
    // Step 4: Create alert object
    const alert = {
        id: Date.now(),
        type: type,              // 'motion' or 'object'
        message: message,         // Human-readable message
        timestamp: new Date().toISOString(),
        data: data               // Additional data (intensity, objectCount, etc.)
    };
    
    // Step 5: Store alert (keep last 50)
    alerts.unshift(alert);
    if (alerts.length > 50) {
        alerts = alerts.slice(0, 50);
    }
    
    // Step 6: Save to localStorage for persistence
    localStorage.setItem('dashboardAlerts', JSON.stringify(alerts));
    
    // Step 7: Display alert in UI
    displayAlert(alert);
    
    // Step 8: Play sound if enabled
    if (smartAlertsConfig.soundAlertsEnabled) {
        playAlertSound();
    }
    
    // Step 9: Send Telegram notification if enabled
    if (smartAlertsConfig.telegramAlertsEnabled) {
        sendTelegramAlert(alert);
    }
}
```

**Key Features:**
- **Cooldown System**: Prevents alert spam by enforcing minimum time between alerts
- **Type Filtering**: Only triggers alerts for enabled types
- **Persistence**: Alerts are saved to localStorage and persist across page refreshes
- **Limit Management**: Keeps only the last 50 alerts in memory

### 3. Alert Display Phase

```javascript
// Location: app/static/js/script.js (lines 1290-1347)

function displayAlert(alert) {
    const alertsList = document.getElementById('alertsList');
    const noAlertsPlaceholder = document.getElementById('noAlertsPlaceholder');
    
    // Hide "No alerts" placeholder
    if (noAlertsPlaceholder) {
        noAlertsPlaceholder.style.display = 'none';
    }
    
    // Create alert HTML element
    const alertItem = document.createElement('div');
    alertItem.className = 'list-group-item d-flex align-items-start';
    alertItem.id = `alert-${alert.id}`;
    
    // Determine icon and color based on type
    let icon = 'bi-exclamation-triangle';
    let color = 'warning';
    if (alert.type === 'motion') {
        icon = 'bi-activity';      // Activity icon for motion
        color = 'danger';          // Red color
    } else if (alert.type === 'object') {
        icon = 'bi-shield-check';  // Shield icon for objects
        color = 'info';            // Blue color
    }
    
    // Build alert HTML
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
    
    // Add to top of list (newest first)
    alertsList.insertBefore(alertItem, alertsList.firstChild);
    
    // Animate appearance
    alertItem.style.opacity = '0';
    alertItem.style.transform = 'translateY(-10px)';
    setTimeout(() => {
        alertItem.style.transition = 'all 0.3s ease';
        alertItem.style.opacity = '1';
        alertItem.style.transform = 'translateY(0)';
    }, 10);
}
```

**Display Features:**
- **Visual Indicators**: Different icons and colors for motion vs object alerts
- **Rich Information**: Shows timestamp, intensity, object count
- **Animation**: Smooth fade-in and slide-down effect
- **Dismissible**: Each alert has a dismiss button

### 4. Configuration System

```javascript
// Location: app/static/js/script.js (lines 1180-1237)

// Configuration stored in localStorage
let smartAlertsConfig = {
    motionAlertsEnabled: true,      // Enable/disable motion alerts
    objectAlertsEnabled: true,      // Enable/disable object alerts
    soundAlertsEnabled: false,      // Play sound on alert
    telegramAlertsEnabled: false,   // Send to Telegram
    motionThreshold: 30,             // Motion intensity threshold (%)
    objectCount: 1,                  // Minimum objects to trigger
    cooldown: 10                     // Cooldown period (seconds)
};
```

**Configuration Options:**
- **Motion Alerts**: Toggle on/off, set intensity threshold (10-100%)
- **Object Alerts**: Toggle on/off, set minimum object count (1-10)
- **Sound Alerts**: Optional audio notification
- **Telegram Alerts**: Optional Telegram notification (requires backend setup)
- **Cooldown**: Minimum time between alerts (0-300 seconds)

## Alert Types

### Motion Alert
- **Trigger**: Motion intensity ≥ threshold
- **Icon**: Activity icon (bi-activity)
- **Color**: Red (danger)
- **Data**: Intensity percentage, number of motion regions

### Object Alert
- **Trigger**: Object count ≥ minimum
- **Icon**: Shield icon (bi-shield-check)
- **Color**: Blue (info)
- **Data**: Object count, object types

## Alert Lifecycle

```
1. Detection Event
   ↓
2. Check Threshold
   ↓
3. Check Cooldown
   ↓
4. Check if Enabled
   ↓
5. Create Alert Object
   ↓
6. Store in Memory
   ↓
7. Save to localStorage
   ↓
8. Display in UI
   ↓
9. Play Sound (if enabled)
   ↓
10. Send Telegram (if enabled)
```

## User Interactions

### Viewing Alerts
- Alerts appear in the "Recent Alerts" panel on the dashboard
- Newest alerts appear at the top
- Scrollable list (max 50 alerts)

### Dismissing Alerts
- Click the "X" button on any alert
- Alert is removed from UI and localStorage
- Animation: slides out to the left

### Clearing All Alerts
- Click the "Clear" button in the alerts panel header
- Confirmation dialog appears
- All alerts are removed

### Configuring Alerts
- Click "Configure" button in Smart Alerts section
- Modal opens with all configuration options
- Changes are saved to localStorage
- Status badge updates automatically

## Persistence

Alerts are stored in browser localStorage:
- **Key**: `dashboardAlerts`
- **Format**: JSON array of alert objects
- **Limit**: Last 50 alerts
- **Survival**: Persists across page refreshes and browser sessions

Configuration is also stored:
- **Key**: `smartAlertsConfig`
- **Format**: JSON object with all settings
- **Survival**: Persists across sessions

## Testing the Alert System

### Test Motion Alerts:
1. Start camera
2. Enable motion detection
3. Move in front of camera
4. If motion intensity exceeds threshold → alert appears

### Test Object Alerts:
1. Start camera
2. Enable object detection
3. Place objects in camera view
4. If object count ≥ minimum → alert appears

### Test Cooldown:
1. Trigger an alert
2. Immediately trigger another
3. Second alert should be blocked until cooldown expires

## Troubleshooting

### Alerts Not Appearing:
- Check if alert type is enabled in configuration
- Check if threshold is set correctly
- Check if cooldown period has expired
- Check browser console for errors

### Too Many Alerts:
- Increase cooldown period
- Increase motion threshold
- Increase minimum object count

### Alerts Not Persisting:
- Check browser localStorage is enabled
- Check browser console for storage errors
- Clear browser cache and try again

## Future Enhancements

Potential improvements:
- [ ] Alert filtering by type
- [ ] Alert search functionality
- [ ] Alert export to CSV/JSON
- [ ] Email notifications
- [ ] SMS notifications
- [ ] Alert severity levels
- [ ] Alert grouping by time
- [ ] Alert statistics dashboard

