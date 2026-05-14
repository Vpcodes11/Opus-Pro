/**
 * Opus Pro — Frontend Logic
 * Premium Opus Pro alternative UI
 */

// ============ DOM ============
const $ = id => document.getElementById(id);
const dropZone = $('drop-zone');
const fileInput = $('file-input');
const fileInfo = $('file-info');
const fileName = $('file-name');
const fileSize = $('file-size');
const removeFileBtn = $('remove-file-btn');
const urlInput = $('url-input');
const startBtn = $('start-btn');
const presetSelect = $('preset-select');
const captionSelect = $('caption-select');
const heroSection = $('hero-section');
const processingSection = $('processing-section');
const progressFill = $('progress-fill');
const progressMessage = $('progress-message');
const progressPercent = $('progress-percent');
const processingSource = $('processing-source');
const resultsSection = $('results-section');
const resultsSummary = $('results-summary');
const clipsGrid = $('clips-grid');
const errorSection = $('error-section');
const errorMessage = $('error-message');
const retryBtn = $('retry-btn');
const transcriptPreview = $('transcript-preview');
const transcriptBody = $('transcript-body');
const transcriptStats = $('transcript-stats');
const fullTranscript = $('full-transcript');
const fullTranscriptBody = $('full-transcript-body');
const downloadAllBtn = $('download-all-btn');
const newProjectBtn = $('new-project-btn');
const toggleTranscriptBtn = $('toggle-transcript-btn');

let selectedFile = null;
let currentJobId = null;
let ws = null;
let pollTimer = null;
let activeTab = 'upload';

// ============ Init ============

// ============ Tabs ============
document.querySelectorAll('.input-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.input-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        activeTab = tab.dataset.tab;
        $('content-' + activeTab).classList.add('active');
        updateStartBtn();
    });
});

// ============ File Upload ============
dropZone.addEventListener('click', e => {
    if (e.target.closest('.btn-icon-sm')) return;
    fileInput.click();
});
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
    e.preventDefault(); dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFile(fileInput.files[0]); });
removeFileBtn.addEventListener('click', e => { e.stopPropagation(); clearFile(); });

function handleFile(file) {
    if (!file.type.startsWith('video/') && !/\.(mp4|mkv|mov|avi|webm)$/i.test(file.name)) {
        alert('Please select a video file'); return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatSize(file.size);
    $('drop-zone-inner').classList.add('hidden');
    fileInfo.classList.remove('hidden');
    updateStartBtn();
}

function clearFile() {
    selectedFile = null; fileInput.value = '';
    $('drop-zone-inner').classList.remove('hidden');
    fileInfo.classList.add('hidden');
    updateStartBtn();
}

urlInput.addEventListener('input', updateStartBtn);

function updateStartBtn() {
    const hasSource = activeTab === 'upload' ? !!selectedFile : urlInput.value.trim().length > 5;
    startBtn.disabled = !hasSource;
}

function formatSize(bytes) {
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

// ============ Start Processing ============
startBtn.addEventListener('click', async () => {
    if (startBtn.disabled) return;
    startBtn.disabled = true;
    startBtn.innerHTML = '<span class="btn-spinner"></span> Uploading...';
    errorSection.classList.add('hidden');
    resultsSection.classList.add('hidden');

    try {
        const formData = new FormData();
        formData.append('preset', presetSelect.value);
        formData.append('caption_style', captionSelect.value);

        if (activeTab === 'upload' && selectedFile) {
            formData.append('file', selectedFile);
            processingSource.textContent = selectedFile.name;
        } else {
            formData.append('url', urlInput.value.trim());
            processingSource.textContent = urlInput.value.trim();
        }

        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);

        const data = await res.json();
        if (data.error) throw new Error(data.error);
        currentJobId = data.job_id;

        // Show processing UI
        heroSection.classList.add('hidden');
        processingSection.classList.remove('hidden');

        // Handle download step visibility
        const dlStep = $('step-download');
        if (activeTab === 'url') { dlStep.style.display = 'flex'; }
        else { dlStep.style.display = 'none'; }

        connectWebSocket(currentJobId);
        startPolling(currentJobId);

    } catch (err) {
        showError(err.message);
        startBtn.disabled = false;
        startBtn.innerHTML = svgPlay + '<span>Extract Viral Clips</span>';
    }
});

const svgPlay = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>';

// ============ WebSocket ============
function connectWebSocket(jobId) {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws/${jobId}`);
    ws.onmessage = e => handleUpdate(JSON.parse(e.data));
    ws.onerror = () => console.log('WS error, polling active');
    ws.onclose = () => { ws = null; };
}

// ============ Polling ============
function startPolling(jobId) {
    pollTimer = setInterval(async () => {
        try {
            const res = await fetch(`/api/status/${jobId}`);
            const data = await res.json();
            updateProgress(data.message, data.progress);
            updatePipeline(data.progress);
            if (data.transcript && !transcriptPreview.classList.contains('shown')) {
                showTranscriptPreview(data.transcript);
            }
            if (data.status === 'complete') {
                stopPolling();
                handleUpdate({ type: 'complete', clips: data.clips, message: data.message, transcript: data.transcript });
            } else if (data.status === 'error') {
                stopPolling();
                handleUpdate({ type: 'error', message: data.message });
            }
        } catch (e) { console.error('Poll error:', e); }
    }, 2000);
}

function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

// ============ Update Handlers ============
function handleUpdate(data) {
    if (data.type === 'progress') {
        updateProgress(data.message, data.progress);
        updatePipeline(data.progress);
    } else if (data.type === 'transcript') {
        showTranscriptPreview(data.transcript);
    } else if (data.type === 'complete') {
        stopPolling();
        if (ws) ws.close();
        processingSection.classList.add('hidden');
        showResults(data.clips, data.message, data.transcript);
    } else if (data.type === 'error') {
        stopPolling();
        if (ws) ws.close();
        processingSection.classList.add('hidden');
        showError(data.message);
    }
}

function updateProgress(message, percent) {
    progressFill.style.width = percent + '%';
    progressMessage.textContent = message;
    progressPercent.textContent = percent + '%';
}

function updatePipeline(progress) {
    const steps = [
        { id: 'step-download', min: 0, max: 4 },
        { id: 'step-extract', min: 5, max: 14 },
        { id: 'step-transcribe', min: 15, max: 55 },
        { id: 'step-analyze', min: 56, max: 70 },
        { id: 'step-render', min: 71, max: 100 },
    ];
    steps.forEach(s => {
        const el = $(s.id);
        if (!el || el.style.display === 'none') return;
        if (progress >= s.max) el.className = 'pipe-step done';
        else if (progress >= s.min) el.className = 'pipe-step active';
        else el.className = 'pipe-step';
    });
}

// ============ Transcript Preview ============
function showTranscriptPreview(transcript) {
    if (!transcript) return;
    transcriptPreview.classList.remove('hidden');
    transcriptPreview.classList.add('shown');
    transcriptStats.textContent = `${transcript.word_count || 0} words • ${formatDuration(transcript.duration || 0)}`;
    transcriptBody.innerHTML = '';
    (transcript.segments || []).slice(0, 20).forEach(seg => {
        const div = document.createElement('div');
        div.className = 'transcript-segment';
        div.innerHTML = `<span class="transcript-time">${formatTimestamp(seg.start)}</span>${escapeHtml(seg.text)}`;
        transcriptBody.appendChild(div);
    });
}

// ============ Results ============
function showResults(clips, message, transcript) {
    resultsSection.classList.remove('hidden');
    resultsSummary.textContent = message || `${clips.length} clips ready`;
    clipsGrid.innerHTML = '';

    clips.forEach((clip, i) => {
        const card = document.createElement('div');
        card.className = 'clip-card';
        card.style.animationDelay = `${i * 0.12}s`;

        const previewUrl = `/api/preview/${currentJobId}/${clip.filename}`;
        const downloadUrl = `/api/download/${currentJobId}/${clip.filename}`;
        const hashtags = (clip.hashtags || []).join(' ');

        card.innerHTML = `
            <div class="clip-preview">
                <video controls preload="metadata" src="${previewUrl}" poster="/api/preview/${currentJobId}/${clip.thumbnail}"></video>
                <div class="clip-overlay">
                    <span class="clip-badge score">🔥 ${clip.virality_score}/10</span>
                    <span class="clip-badge category">${clip.category || ''}</span>
                </div>
                <span class="clip-duration-badge">${Math.round(clip.duration)}s</span>
            </div>
            <div class="clip-body">
                <h3 class="clip-title">${escapeHtml(clip.title)}</h3>
                <p class="clip-caption">${escapeHtml(clip.hook_caption)}</p>
                <p class="clip-reason">${escapeHtml(clip.reason)}</p>
                ${hashtags ? `<p class="clip-hashtags">${escapeHtml(hashtags)}</p>` : ''}
                <div class="clip-footer">
                    <a href="${downloadUrl}" class="btn-download" download>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                            <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                        Download
                    </a>
                    <button class="btn-copy" onclick="copyText(\`${escapeJs(clip.hook_caption + (hashtags ? '\n' + hashtags : ''))}\`)">📋 Copy</button>
                </div>
            </div>
        `;
        clipsGrid.appendChild(card);
    });

    // Full transcript
    if (transcript && transcript.segments) {
        fullTranscript.classList.remove('hidden');
        fullTranscriptBody.innerHTML = '';
        transcript.segments.forEach(seg => {
            const div = document.createElement('div');
            div.className = 'transcript-segment';
            div.innerHTML = `<span class="transcript-time">${formatTimestamp(seg.start)}</span>${escapeHtml(seg.text)}`;
            fullTranscriptBody.appendChild(div);
        });
    }
}

// ============ Download All ============
downloadAllBtn?.addEventListener('click', () => {
    const links = document.querySelectorAll('.btn-download[download]');
    links.forEach((link, i) => {
        setTimeout(() => { const a = document.createElement('a'); a.href = link.href; a.download = ''; document.body.appendChild(a); a.click(); a.remove(); }, i * 500);
    });
});

// ============ New Project ============
newProjectBtn?.addEventListener('click', () => {
    resultsSection.classList.add('hidden');
    heroSection.classList.remove('hidden');
    clearFile();
    urlInput.value = '';
    startBtn.disabled = false;
    startBtn.innerHTML = svgPlay + '<span>Extract Viral Clips</span>';
    transcriptPreview.classList.add('hidden');
    transcriptPreview.classList.remove('shown');
    fullTranscript.classList.add('hidden');
    currentJobId = null;
    updateStartBtn();
});

// ============ Toggle Transcript ============
toggleTranscriptBtn?.addEventListener('click', () => {
    fullTranscriptBody.classList.toggle('collapsed');
    const isCollapsed = fullTranscriptBody.classList.contains('collapsed');
    toggleTranscriptBtn.innerHTML = isCollapsed
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>';
});

// ============ Error ============
function showError(message) {
    errorSection.classList.remove('hidden');
    errorMessage.textContent = message;
    heroSection.classList.remove('hidden');
    processingSection.classList.add('hidden');
    startBtn.disabled = false;
    startBtn.innerHTML = svgPlay + '<span>Extract Viral Clips</span>';
}

retryBtn.addEventListener('click', () => {
    errorSection.classList.add('hidden');
    updateStartBtn();
});

// ============ Utilities ============
function escapeHtml(str) {
    if (!str) return '';
    const d = document.createElement('div'); d.textContent = str; return d.innerHTML;
}

function escapeJs(str) {
    if (!str) return '';
    return str.replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');
}

function copyText(text) {
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target.closest('.btn-copy');
        if (btn) { const orig = btn.textContent; btn.textContent = '✓ Copied!'; setTimeout(() => btn.textContent = orig, 1500); }
    });
}

function formatTimestamp(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatDuration(seconds) {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    if (m < 60) return `${m}m ${s}s`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
}

// Init
updateStartBtn();
