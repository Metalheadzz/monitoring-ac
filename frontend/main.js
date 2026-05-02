// --- Auth Check ---
if (!localStorage.getItem('auth_token')) {
    window.location.href = '/login.html';
}

import Chart from 'chart.js/auto';

// --- UI Elements ---
const statusDot = document.getElementById('connection-status');
const statusText = document.getElementById('connection-text');
const currentTempEl = document.getElementById('current-temp');
const acStateEl = document.getElementById('ac-state');
const gaugePath = document.getElementById('gauge-path');
const btnOn = document.getElementById('btn-on');
const btnOff = document.getElementById('btn-off');
const feedbackEl = document.getElementById('control-feedback');
const historyRange = document.getElementById('history-range');
const historyDate = document.getElementById('history-date');
const roomSelector = document.getElementById('room-selector');
const btnLogout = document.getElementById('btn-logout');

let currentRoom = "Ruang Utama";

// --- Fetch Rooms ---
async function fetchRooms() {
    try {
        const res = await fetch('/api/rooms');
        const data = await res.json();
        if (data.rooms && data.rooms.length > 0) {
            roomSelector.innerHTML = '';
            data.rooms.forEach(room => {
                const option = document.createElement('option');
                option.value = room;
                option.textContent = room;
                roomSelector.appendChild(option);
            });
            roomSelector.style.display = 'block';
            currentRoom = roomSelector.value;
        }
    } catch (e) {
        console.error('Failed to fetch rooms', e);
    }
}

roomSelector.addEventListener('change', (e) => {
    currentRoom = e.target.value;
    // Clear realtime chart
    realtimeChart.data.labels = [];
    realtimeChart.data.datasets[0].data = [];
    realtimeChart.update();
    
    // Clear current temp display
    currentTempEl.textContent = '--';
    acStateEl.textContent = 'UNKNOWN';
    acStateEl.className = '';
    
    fetchHistory();
});

// Logout Logic
btnLogout.addEventListener('click', () => {
    localStorage.removeItem('auth_token');
    window.location.href = '/login.html';
});

// --- Charts Setup ---
const ctxRealtime = document.getElementById('realtimeChart').getContext('2d');
const ctxHistory = document.getElementById('historyChart').getContext('2d');

// Chart Defaults for dark theme
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(255,255,255,0.1)';

const realtimeChart = new Chart(ctxRealtime, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Suhu Realtime (°C)',
            data: [],
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.2)',
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.4
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 0 },
        scales: {
            x: { display: false },
            y: { min: 15, max: 45 }
        },
        plugins: { legend: { display: false } }
    }
});

const historyChart = new Chart(ctxHistory, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Rata-rata Suhu (°C)',
            data: [],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            borderWidth: 2,
            pointRadius: 2,
            fill: true,
            tension: 0.3
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { 
                ticks: { maxTicksLimit: 10 }
            },
            y: { suggestedMin: 15, suggestedMax: 40 }
        }
    }
});

// --- Gauge Logic ---
// Circle path length is ~125. 125 = empty, 0 = full
function updateGauge(temp) {
    const minTemp = 15;
    const maxTemp = 45;
    let percentage = (temp - minTemp) / (maxTemp - minTemp);
    percentage = Math.max(0, Math.min(1, percentage));
    
    const offset = 125 - (percentage * 125);
    gaugePath.style.strokeDashoffset = offset;
    
    // Color change
    if (temp >= 30) {
        gaugePath.style.stroke = '#ef4444'; // Red
    } else if (temp >= 24) {
        gaugePath.style.stroke = '#f59e0b'; // Yellow
    } else {
        gaugePath.style.stroke = '#3b82f6'; // Blue
    }
}

// --- SSE Connection (Realtime via Flask) ---
const maxDataPoints = 50;
let eventSource = null;

function connectSSE() {
    console.log('[SSE] Connecting to /api/stream...');
    statusText.textContent = 'Connecting...';
    
    eventSource = new EventSource('/api/stream');
    
    eventSource.onopen = () => {
        console.log('[SSE] Connected!');
        statusDot.className = 'status-dot connected';
        statusText.textContent = 'Connected (Real-time)';
    };
    
    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            // Only process data for the currently selected room
            if (data.ruangan && data.ruangan !== currentRoom) return;

            const temp = parseFloat(data.suhu).toFixed(1);
            const acState = data.status_ac;

            // Update UI Texts
            currentTempEl.textContent = temp;
            acStateEl.textContent = acState;
            acStateEl.className = acState === 'ON' ? 'on' : 'off';
            
            // Update Gauge
            updateGauge(parseFloat(temp));

            // Update Realtime Chart
            const timeStr = new Date(data.timestamp).toLocaleTimeString();
            realtimeChart.data.labels.push(timeStr);
            realtimeChart.data.datasets[0].data.push(parseFloat(temp));

            if (realtimeChart.data.labels.length > maxDataPoints) {
                realtimeChart.data.labels.shift();
                realtimeChart.data.datasets[0].data.shift();
            }
            realtimeChart.update();

        } catch (e) {
            console.error('[SSE] Error parsing message', e);
        }
    };
    
    eventSource.onerror = (err) => {
        console.error('[SSE] Connection error, reconnecting...', err);
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = 'Reconnecting...';
        eventSource.close();
        // Reconnect after 3 seconds
        setTimeout(connectSSE, 3000);
    };
}

// Start SSE connection
connectSSE();

// --- Controls (via Flask API) ---
async function sendCommand(state) {
    try {
        feedbackEl.textContent = `Sending: AC ${state}...`;
        feedbackEl.style.opacity = 1;
        feedbackEl.style.color = '#94a3b8';
        
        const res = await fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: state, ruangan: currentRoom })
        });
        
        const data = await res.json();
        
        if (data.success) {
            feedbackEl.textContent = `✓ Command Sent: AC ${state}`;
            feedbackEl.style.color = '#10b981';
        } else {
            feedbackEl.textContent = `✗ Error: ${data.error}`;
            feedbackEl.style.color = '#ef4444';
        }
        
        feedbackEl.style.opacity = 1;
        setTimeout(() => { feedbackEl.style.opacity = 0; }, 3000);
        
    } catch (e) {
        feedbackEl.textContent = 'Error: Could not send command';
        feedbackEl.style.color = '#ef4444';
        feedbackEl.style.opacity = 1;
    }
}

btnOn.addEventListener('click', () => sendCommand('ON'));
btnOff.addEventListener('click', () => sendCommand('OFF'));

// --- History API Fetching ---
async function fetchHistory() {
    try {
        const range = historyRange.value;
        const date = historyDate.value;
        
        let url = `/api/history?ruangan=${encodeURIComponent(currentRoom)}`;
        if (date) {
            url += `&date=${date}`;
        } else {
            url += `&range=${range}`;
        }

        const res = await fetch(url);
        if (!res.ok) throw new Error('API Error');
        const data = await res.json();
        
        const labels = [];
        const values = [];
        
        if (data.length > 0) {
            data.forEach(d => {
                const dateObj = new Date(d.time);
                let labelStr = '';
                if (date || range === '1h' || range === '24h') {
                    labelStr = dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                } else {
                    labelStr = dateObj.toLocaleDateString();
                }
                labels.push(labelStr);
                values.push(d.suhu);
            });
        } else {
            labels.push('No Data');
            values.push(0);
        }

        historyChart.data.labels = labels;
        historyChart.data.datasets[0].data = values;
        historyChart.update();

    } catch (e) {
        console.error('Failed to fetch history', e);
    }
}

historyRange.addEventListener('change', fetchHistory);

historyDate.addEventListener('change', () => {
    // If a specific date is selected, disable the range dropdown temporarily or just let it be overridden
    if (historyDate.value) {
        historyRange.disabled = true;
    } else {
        historyRange.disabled = false;
    }
    fetchHistory();
});

// Initialize
async function init() {
    await fetchRooms();
    fetchHistory();
}

init();
