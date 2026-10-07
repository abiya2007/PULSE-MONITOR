/**
 * Clinical Pulse Monitor & Health Analyzer - Laptop Dashboard JavaScript
 * Connects to Python FastAPI backend via WebSockets & REST APIs.
 * Renders high-end glowing oscilloscope PPG trace, HR zone gauge, & diagnostic reference cards.
 */

document.addEventListener('DOMContentLoaded', () => {

    // DOM Elements
    const valBPM = document.getElementById('valBPM');
    const valIBI = document.getElementById('valIBI');
    const valHRV = document.getElementById('valHRV');
    const badgeCategory = document.getElementById('badgeCategory');
    const connectionBadge = document.getElementById('connectionBadge');
    const hrZoneIndicator = document.getElementById('hrZoneIndicator');

    const portSelect = document.getElementById('portSelect');
    const btnConnect = document.getElementById('btnConnect');
    const btnRefreshPorts = document.getElementById('btnRefreshPorts');

    const alertSummary = document.getElementById('alertSummary');
    const iconStatus = document.getElementById('iconStatus');
    const lblStatusTitle = document.getElementById('lblStatusTitle');
    const lblStatusDesc = document.getElementById('lblStatusDesc');
    const containerSymptoms = document.getElementById('containerSymptoms');
    const containerDiseases = document.getElementById('containerDiseases');
    const lblAdvice = document.getElementById('lblAdvice');

    const btnStartSession = document.getElementById('btnStartSession');
    const btnEndSession = document.getElementById('btnEndSession');
    const lblSessionId = document.getElementById('lblSessionId');
    const tableSessionsBody = document.getElementById('tableSessionsBody');
    const btnRefreshHistory = document.getElementById('btnRefreshHistory');

    const canvas = document.getElementById('ppgCanvas');
    const ctx = canvas.getContext('2d');

    // Canvas buffer & Oscilloscope Sweep
    const ppgHistory = [];
    const MAX_PPG_POINTS = 220;
    let sweepX = 0;

    let ws = null;
    let isHardwareConnected = false;
    let activeSessionId = null;

    // Set canvas dimensions dynamically
    function resizeCanvas() {
        if (!canvas.parentElement) return;
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = 220;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Initialize WebSocket Connection
    function initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log("WebSocket connected to Python server.");
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            } catch (err) {
                console.error("Error parsing WebSocket payload:", err);
            }
        };

        ws.onclose = () => {
            console.log("WebSocket connection closed. Retrying in 2 seconds...");
            setTimeout(initWebSocket, 2000);
        };

        ws.onerror = (err) => {
            console.error("WebSocket error:", err);
        };
    }

    // Update Dashboard UI with real-time telemetry and analysis
    function updateDashboard(data) {
        const telemetry = data.telemetry;
        const analysis = data.analysis;

        activeSessionId = data.active_session_id;
        if (lblSessionId) lblSessionId.textContent = activeSessionId ? `#${activeSessionId}` : '#None';

        // Update Numerical Metrics & Emoji Display
        const currentBpm = telemetry.bpm;
        valBPM.textContent = currentBpm.toFixed(0);
        valIBI.textContent = telemetry.ibi_ms.toFixed(0);
        valHRV.textContent = analysis.hrv_sdnn.toFixed(1);

        const valEmoji = document.getElementById('valEmoji');
        if (valEmoji) valEmoji.textContent = analysis.emoji || '😊';

        // Update Dedicated Featured Emoji & State Dialogue Card (Mockup Match)
        const lblEmojiAvatar = document.getElementById('lblEmojiAvatar');
        const lblEmojiStateTitle = document.getElementById('lblEmojiStateTitle');
        const lblEmojiDialogue = document.getElementById('lblEmojiDialogue');
        const cardEmojiDialogue = document.getElementById('cardEmojiDialogue');

        if (lblEmojiAvatar) lblEmojiAvatar.textContent = analysis.emoji || '😊';
        if (lblEmojiStateTitle) lblEmojiStateTitle.textContent = (analysis.status_title || analysis.status).toUpperCase();
        if (lblEmojiDialogue) lblEmojiDialogue.textContent = analysis.dialogue || '';

        if (cardEmojiDialogue) {
            if (analysis.severity === 'success') {
                cardEmojiDialogue.style.borderColor = 'rgba(16, 185, 129, 0.6)';
                cardEmojiDialogue.style.boxShadow = '0 0 35px rgba(16, 185, 129, 0.25)';
            } else if (analysis.severity === 'info') {
                cardEmojiDialogue.style.borderColor = 'rgba(56, 189, 248, 0.6)';
                cardEmojiDialogue.style.boxShadow = '0 0 35px rgba(56, 189, 248, 0.25)';
            } else if (analysis.severity === 'warning') {
                cardEmojiDialogue.style.borderColor = 'rgba(245, 158, 11, 0.6)';
                cardEmojiDialogue.style.boxShadow = '0 0 35px rgba(245, 158, 11, 0.25)';
            } else {
                cardEmojiDialogue.style.borderColor = 'rgba(239, 68, 68, 0.6)';
                cardEmojiDialogue.style.boxShadow = '0 0 35px rgba(239, 68, 68, 0.25)';
            }
        }

        // Calculate 7-Zone Indicator Bar Percentage
        let zonePercent = 40;
        if (currentBpm < 50) {
            zonePercent = Math.max(5, (currentBpm / 50) * 14);
        } else if (currentBpm <= 65) {
            zonePercent = 14 + ((currentBpm - 50) / 15) * 14;
        } else if (currentBpm <= 85) {
            zonePercent = 28 + ((currentBpm - 65) / 20) * 15;
        } else if (currentBpm <= 110) {
            zonePercent = 43 + ((currentBpm - 85) / 25) * 14;
        } else if (currentBpm <= 130) {
            zonePercent = 57 + ((currentBpm - 110) / 20) * 14;
        } else if (currentBpm <= 160) {
            zonePercent = 71 + ((currentBpm - 130) / 30) * 14;
        } else {
            zonePercent = Math.min(95, 85 + ((currentBpm - 160) / 40) * 10);
        }
        if (hrZoneIndicator) hrZoneIndicator.style.left = `${zonePercent}%`;

        // Update Category Badge & Severity Styles
        badgeCategory.textContent = analysis.status.toUpperCase();
        applySeverityBadgeStyle(badgeCategory, analysis.severity);

        // Update Hardware Connection Status Badge
        if (data.connected_port && data.connected_port !== "Simulator Mode") {
            isHardwareConnected = true;
            connectionBadge.className = "mode-badge mode-hardware d-flex align-items-center gap-2 px-3 py-1-5 rounded-pill";
            connectionBadge.innerHTML = `<span class="pulse-dot"></span><span class="font-mono text-uppercase fs-7 fw-semibold">HARDWARE: ${data.connected_port}</span>`;
            btnConnect.textContent = "Disconnect";
            btnConnect.className = "btn btn-outline-crimson btn-sm fw-semibold";
        } else {
            isHardwareConnected = false;
            connectionBadge.className = "mode-badge mode-simulated d-flex align-items-center gap-2 px-3 py-1-5 rounded-pill";
            connectionBadge.innerHTML = `<span class="pulse-dot"></span><span class="font-mono text-uppercase fs-7 fw-semibold">MODE: SIMULATED (${telemetry.mode || 'RESTING'})</span>`;
            btnConnect.textContent = "Connect";
            btnConnect.className = "btn btn-cyan btn-sm fw-semibold";
        }

        // Add Raw PPG Signal to Canvas Buffer
        ppgHistory.push(telemetry.raw);
        if (ppgHistory.length > MAX_PPG_POINTS) {
            ppgHistory.shift();
        }
        drawPPGWaveform(analysis.severity);

        // Update Medical Diagnostics Card
        lblStatusTitle.textContent = analysis.status;
        lblStatusDesc.textContent = analysis.summary;
        lblAdvice.textContent = analysis.advice;

        // Apply Alert Style
        applyAlertStyle(alertSummary, iconStatus, analysis.severity);

        // Populate Symptoms List as Badges
        containerSymptoms.innerHTML = '';
        if (analysis.symptoms && analysis.symptoms.length > 0) {
            analysis.symptoms.forEach(sym => {
                const badge = document.createElement('span');
                badge.className = 'badge bg-dark-subtle text-amber-light border border-warning-subtle px-3 py-2 font-mono fs-8 text-wrap text-start';
                badge.innerHTML = `<i class="bi bi-caret-right-fill me-1 text-amber"></i> ${sym}`;
                containerSymptoms.appendChild(badge);
            });
        }

        // Populate Diseases / Physiological References as Badges
        containerDiseases.innerHTML = '';
        if (analysis.potential_diseases && analysis.potential_diseases.length > 0) {
            analysis.potential_diseases.forEach(dis => {
                const badge = document.createElement('span');
                badge.className = 'badge bg-dark-subtle text-light border border-danger-subtle px-3 py-2 font-mono fs-8 text-wrap text-start';
                badge.innerHTML = `<i class="bi bi-activity me-1 text-crimson"></i> ${dis}`;
                containerDiseases.appendChild(badge);
            });
        }
    }

    // Severity to Bootstrap Badge Styling
    function applySeverityBadgeStyle(element, severity) {
        element.className = "badge font-mono px-3 py-2 rounded-pill fs-7 fw-bold mt-2 ";
        if (severity === 'success') element.classList.add('bg-emerald', 'text-dark');
        else if (severity === 'info') element.classList.add('bg-info', 'text-dark');
        else if (severity === 'warning') element.classList.add('bg-warning', 'text-dark');
        else if (severity === 'alert') element.classList.add('bg-danger', 'text-white');
        else if (severity === 'danger') element.classList.add('bg-purple', 'text-white');
        else element.classList.add('bg-secondary', 'text-white');
    }

    // Severity to Alert Box Styling
    function applyAlertStyle(alertEl, iconEl, severity) {
        alertEl.className = "alert border-0 rounded-3 p-3 mb-4 d-flex align-items-start gap-3 ";
        iconEl.className = "bi fs-3 ";

        if (severity === 'success') {
            alertEl.classList.add('alert-emerald');
            iconEl.classList.add('bi-check-circle-fill', 'text-emerald');
        } else if (severity === 'info') {
            alertEl.classList.add('alert-sky');
            iconEl.classList.add('bi-info-circle-fill', 'text-sky');
        } else if (severity === 'warning') {
            alertEl.classList.add('alert-amber');
            iconEl.classList.add('bi-exclamation-triangle-fill', 'text-amber');
        } else if (severity === 'danger') {
            alertEl.classList.add('alert-violet');
            iconEl.classList.add('bi-lightning-fill', 'text-violet');
        } else {
            alertEl.classList.add('alert-crimson');
            iconEl.classList.add('bi-exclamation-octagon-fill', 'text-crimson');
        }
    }

    // High-End Glowing Oscilloscope Waveform Renderer
    function drawPPGWaveform(severity) {
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        if (ppgHistory.length < 2) return;

        // Auto-scale waveform to canvas bounds
        const minVal = Math.min(...ppgHistory);
        const maxVal = Math.max(...ppgHistory);
        const range = maxVal - minVal || 1;

        // Determine line glow color based on severity
        let traceColor = '#00f2fe'; // Default Cyan
        let gradientTop = 'rgba(0, 242, 254, 0.35)';
        if (severity === 'success') {
            traceColor = '#10b981';
            gradientTop = 'rgba(16, 185, 129, 0.35)';
        } else if (severity === 'warning') {
            traceColor = '#f59e0b';
            gradientTop = 'rgba(245, 158, 11, 0.35)';
        } else if (severity === 'alert') {
            traceColor = '#ef4444';
            gradientTop = 'rgba(239, 68, 68, 0.35)';
        } else if (severity === 'danger') {
            traceColor = '#c084fc';
            gradientTop = 'rgba(192, 132, 252, 0.35)';
        }

        // Create Gradient Fill Under Trace Curve
        const gradFill = ctx.createLinearGradient(0, 0, 0, h);
        gradFill.addColorStop(0, gradientTop);
        gradFill.addColorStop(1, 'rgba(0, 0, 0, 0.0)');

        const step = w / MAX_PPG_POINTS;

        // Path for Fill
        ctx.beginPath();
        ctx.moveTo(0, h);
        for (let i = 0; i < ppgHistory.length; i++) {
            const x = i * step;
            const normY = (ppgHistory[i] - minVal) / range;
            const y = h - (normY * (h - 40) + 20);
            if (i === 0) ctx.lineTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.lineTo((ppgHistory.length - 1) * step, h);
        ctx.closePath();
        ctx.fillStyle = gradFill;
        ctx.fill();

        // Path for Glowing Stroke Line
        ctx.save();
        ctx.shadowColor = traceColor;
        ctx.shadowBlur = 12;
        ctx.strokeStyle = traceColor;
        ctx.lineWidth = 2.8;

        ctx.beginPath();
        for (let i = 0; i < ppgHistory.length; i++) {
            const x = i * step;
            const normY = (ppgHistory[i] - minVal) / range;
            const y = h - (normY * (h - 40) + 20);

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Draw Pulsing Beat Dot on Latest Peak Point
        const lastX = (ppgHistory.length - 1) * step;
        const lastNormY = (ppgHistory[ppgHistory.length - 1] - minVal) / range;
        const lastY = h - (lastNormY * (h - 40) + 20);

        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    // Fetch Available COM Serial Ports
    async function loadSerialPorts() {
        try {
            const res = await fetch('/api/ports');
            const data = await res.json();
            portSelect.innerHTML = '<option value="">Select Microchip COM Port...</option>';
            data.ports.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.port;
                opt.textContent = `${p.port} (${p.description})`;
                portSelect.appendChild(opt);
            });
        } catch (e) {
            console.error("Failed to load serial ports:", e);
        }
    }

    // Connect / Disconnect Serial Port Event Listener
    btnConnect.addEventListener('click', async () => {
        if (isHardwareConnected) {
            await fetch('/api/disconnect', { method: 'POST' });
            loadSerialPorts();
        } else {
            const selectedPort = portSelect.value;
            if (!selectedPort) {
                alert("Please select a valid microchip serial COM port from the dropdown.");
                return;
            }
            const res = await fetch('/api/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ port: selectedPort, baud_rate: 115200 })
            });
            const result = await res.json();
            if (result.status !== 'success') {
                alert("Connection failed: " + result.detail);
            }
        }
    });

    btnRefreshPorts.addEventListener('click', loadSerialPorts);

    // Simulation Profile Mode Switcher Buttons
    document.querySelectorAll('.sim-mode-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            document.querySelectorAll('.sim-mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const mode = btn.getAttribute('data-mode');
            await fetch('/api/simulator/mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: mode })
            });
        });
    });

    // Session Recording Controls
    btnStartSession.addEventListener('click', async () => {
        const sessionName = prompt("Enter a name for this pulse monitoring session:", "Live Pulse Monitor Session");
        if (!sessionName) return;

        const res = await fetch('/api/session/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: sessionName })
        });
        const data = await res.json();
        alert(`New recording session started (ID: #${data.session_id})`);
        loadSessionHistory();
    });

    btnEndSession.addEventListener('click', async () => {
        if (!activeSessionId) {
            alert("No active session is currently running.");
            return;
        }
        const res = await fetch('/api/session/end', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            alert(`Session #${data.summary.session_id} saved!\nTotal Readings: ${data.summary.total_readings}\nMin BPM: ${data.summary.min_bpm}\nMax BPM: ${data.summary.max_bpm}\nAvg BPM: ${data.summary.avg_bpm}`);
            loadSessionHistory();
        }
    });

    // Load Recorded Session History Table
    async function loadSessionHistory() {
        try {
            const res = await fetch('/api/sessions');
            const data = await res.json();
            tableSessionsBody.innerHTML = '';

            if (!data.sessions || data.sessions.length === 0) {
                tableSessionsBody.innerHTML = '<tr><td colspan="9" class="text-center text-secondary py-4">No recorded sessions found.</td></tr>';
                return;
            }

            data.sessions.forEach(s => {
                const tr = document.createElement('tr');
                const startTime = new Date(s.start_time).toLocaleTimeString();
                const endTime = s.end_time ? new Date(s.end_time).toLocaleTimeString() : '<span class="badge bg-emerald text-dark">ACTIVE</span>';

                tr.innerHTML = `
                    <td class="fw-bold text-cyan">#${s.id}</td>
                    <td>${s.name}</td>
                    <td>${startTime}</td>
                    <td>${endTime}</td>
                    <td>${s.total_readings || 0}</td>
                    <td class="text-sky font-mono">${s.min_bpm || '--'}</td>
                    <td class="text-crimson font-mono">${s.max_bpm || '--'}</td>
                    <td class="fw-bold text-emerald font-mono">${s.avg_bpm || '--'}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-secondary py-0 px-2 btn-view-session font-mono fs-8" data-id="${s.id}">
                            <i class="bi bi-eye me-1"></i> Timeline
                        </button>
                    </td>
                `;
                tableSessionsBody.appendChild(tr);
            });

            // Attach Click Listeners
            document.querySelectorAll('.btn-view-session').forEach(btn => {
                btn.addEventListener('click', () => viewSessionTimeline(btn.getAttribute('data-id')));
            });

        } catch (e) {
            console.error("Failed to load session history:", e);
        }
    }

    // View Session Timeline Modal ("When and How")
    async function viewSessionTimeline(sessionId) {
        try {
            const res = await fetch(`/api/session/${sessionId}`);
            const data = await res.json();

            const info = data.session_info;
            document.getElementById('modalTitle').textContent = `Timeline Report - Session #${info.id}: ${info.name}`;
            document.getElementById('modalSummaryHeader').innerHTML = `
                <div class="col-4">
                    <div class="p-2 border border-secondary-subtle rounded bg-dark-subtle">
                        <span class="small text-secondary font-mono d-block">MIN BPM</span>
                        <strong class="text-sky fs-5 font-mono">${info.min_bpm}</strong>
                    </div>
                </div>
                <div class="col-4">
                    <div class="p-2 border border-secondary-subtle rounded bg-dark-subtle">
                        <span class="small text-secondary font-mono d-block">AVERAGE BPM</span>
                        <strong class="text-emerald fs-5 font-mono">${info.avg_bpm}</strong>
                    </div>
                </div>
                <div class="col-4">
                    <div class="p-2 border border-secondary-subtle rounded bg-dark-subtle">
                        <span class="small text-secondary font-mono d-block">MAX BPM</span>
                        <strong class="text-crimson fs-5 font-mono">${info.max_bpm}</strong>
                    </div>
                </div>
            `;

            const eventsBody = document.getElementById('modalEventsBody');
            eventsBody.innerHTML = '';

            if (!data.events_timeline || data.events_timeline.length === 0) {
                eventsBody.innerHTML = '<tr><td colspan="4" class="text-center text-secondary py-3">No abnormal pulse events flagged during this session (All Normal).</td></tr>';
            } else {
                data.events_timeline.forEach(ev => {
                    const timeStr = new Date(ev.time).toLocaleTimeString();
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${timeStr}</td>
                        <td class="fw-bold font-mono text-cyan">${ev.bpm} BPM</td>
                        <td><span class="badge bg-warning text-dark font-mono">${ev.category}</span></td>
                        <td>${ev.status}</td>
                    `;
                    eventsBody.appendChild(tr);
                });
            }

            const modal = new bootstrap.Modal(document.getElementById('timelineModal'));
            modal.show();

        } catch (e) {
            alert("Failed to load session details: " + e);
        }
    }

    btnRefreshHistory.addEventListener('click', loadSessionHistory);

    // Initial load calls
    loadSerialPorts();
    loadSessionHistory();
    initWebSocket();
});
