// JARVIS Mobile Client PWA Application Logic
const state = {
  apiKey: localStorage.getItem('jarvis_api_key') || 'jarvis_secure_key_123',
  autoVoice: localStorage.getItem('jarvis_auto_voice') !== 'false',
  activeTab: 'talk',
  isRecording: false,
  mediaRecorder: null,
  audioChunks: [],
  telemetryTimer: null,
  chatHistory: []
};

// DOM Elements
const hostBadge = document.getElementById('host-badge');
const hostStatusText = document.getElementById('host-status-text');
const arcReactor = document.getElementById('arc-reactor');
const talkStatus = document.getElementById('talk-status');
const talkHint = document.getElementById('talk-hint');
const userSpeechEl = document.getElementById('user-speech');
const jarvisSpeechEl = document.getElementById('jarvis-speech');
const messagesList = document.getElementById('messages-list');
const chatInput = document.getElementById('chat-input');

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  initServiceWorker();
  initNavigation();
  initSettings();
  initChat();
  initVoice();
  initTelemetry();
  checkServerHealth();
});

// PWA Service Worker
function initServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js')
      .then(() => console.log('[PWA] Service Worker Active'))
      .catch(err => console.log('[PWA] Service Worker Error:', err));
  }
}

// Navigation Tabs
function initNavigation() {
  const navBtns = document.querySelectorAll('.nav-item');
  navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      switchTab(tab);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll('.nav-item').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tabId);
  });
  document.querySelectorAll('.screen').forEach(s => {
    s.classList.toggle('active', s.id === `screen-${tabId}`);
  });

  if (tabId === 'laptop') {
    fetchTelemetry();
  } else if (tabId === 'memory') {
    fetchTasks();
  }
}

// Settings
function initSettings() {
  const apiKeyInput = document.getElementById('setting-api-key');
  const autoVoiceToggle = document.getElementById('setting-auto-voice');
  const saveBtn = document.getElementById('btn-save-settings');
  const testStatus = document.getElementById('settings-test-status');

  if (apiKeyInput) apiKeyInput.value = state.apiKey;
  if (autoVoiceToggle) autoVoiceToggle.checked = state.autoVoice;

  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      state.apiKey = apiKeyInput.value.trim();
      state.autoVoice = autoVoiceToggle.checked;
      localStorage.setItem('jarvis_api_key', state.apiKey);
      localStorage.setItem('jarvis_auto_voice', state.autoVoice);

      testStatus.textContent = 'Verifying API Key...';
      testStatus.style.color = 'var(--cyan)';

      const ok = await checkServerHealth();
      testStatus.textContent = ok ? '✓ Connection Verified & Saved!' : '✗ Failed to connect. Check key.';
      testStatus.style.color = ok ? 'var(--emerald)' : 'var(--red)';
    });
  }
}

// API Helper
async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {})
  };
  if (state.apiKey) {
    headers['X-Jarvis-API-Key'] = state.apiKey;
  }
  return fetch(endpoint, { ...options, headers });
}

// Server Health
async function checkServerHealth() {
  try {
    const res = await apiFetch('/health');
    if (res.ok) {
      hostBadge.className = 'host-badge';
      hostStatusText.textContent = 'ONLINE';
      return true;
    }
  } catch (_) {}
  hostBadge.className = 'host-badge offline';
  hostStatusText.textContent = 'OFFLINE';
  return false;
}

// --- 🎙️ VOICE & ARC REACTOR ---
function initVoice() {
  if (!arcReactor) return;

  const micModal = document.getElementById('mic-help-modal');
  const btnCloseModal = document.getElementById('btn-close-mic-modal');
  const btnSwitchChat = document.getElementById('btn-switch-to-chat');

  if (btnCloseModal && micModal) {
    btnCloseModal.addEventListener('click', () => {
      micModal.style.display = 'none';
    });
  }

  if (btnSwitchChat && micModal) {
    btnSwitchChat.addEventListener('click', () => {
      micModal.style.display = 'none';
      switchTab('chat');
    });
  }

  if (talkHint) {
    talkHint.addEventListener('click', () => {
      if (talkStatus.textContent.includes('MIC') && micModal) {
        micModal.style.display = 'flex';
      }
    });
  }

  arcReactor.addEventListener('click', async () => {
    if (talkStatus.textContent.includes('MIC') && micModal && !state.isRecording) {
      micModal.style.display = 'flex';
      return;
    }

    if (state.isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  });
}

async function startRecording() {
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Insecure origin or unsupported browser');
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.mediaRecorder = new MediaRecorder(stream);
    state.audioChunks = [];

    state.mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) state.audioChunks.push(e.data);
    };

    state.mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(state.audioChunks, { type: 'audio/wav' });
      await processVoiceInput(audioBlob);
    };

    state.mediaRecorder.start();
    state.isRecording = true;
    arcReactor.className = 'arc-reactor-wrapper listening';
    talkStatus.textContent = 'LISTENING...';
    talkStatus.style.color = 'var(--red)';
    talkHint.textContent = 'Tap Arc Reactor again when done speaking';
  } catch (err) {
    console.error('Microphone error:', err);
    talkStatus.textContent = 'MIC ACCESS REQUIRED';
    talkStatus.style.color = 'var(--red)';
    talkHint.textContent = 'Tap here to see how to enable mic in Mobile Chrome';
    const micModal = document.getElementById('mic-help-modal');
    if (micModal) micModal.style.display = 'flex';
  }
}

function stopRecording() {
  if (state.mediaRecorder && state.isRecording) {
    state.mediaRecorder.stop();
    state.isRecording = false;
    arcReactor.className = 'arc-reactor-wrapper';
    talkStatus.textContent = 'PROCESSING AUDIO...';
    talkStatus.style.color = 'var(--gold)';
    talkHint.textContent = 'Querying Groq AI & Edge-TTS...';
    
    // Stop all audio tracks
    state.mediaRecorder.stream.getTracks().forEach(t => t.stop());
  }
}

async function processVoiceInput(blob) {
  const formData = new FormData();
  formData.append('file', blob, 'user_voice.wav');

  try {
    const res = await apiFetch('/api/voice', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Voice processing failed');
    }

    const data = await res.json();
    userSpeechEl.textContent = `"${data.transcribed_text}"`;
    jarvisSpeechEl.textContent = data.llm_response;

    // Add to chat history
    addMessageToChat('user', data.transcribed_text);
    addMessageToChat('assistant', data.llm_response);

    if (data.audio_base64 && state.autoVoice) {
      playAudioResponse(data.audio_base64);
    } else {
      talkStatus.textContent = 'IDLE';
      talkStatus.style.color = 'var(--cyan)';
      talkHint.textContent = 'Tap Arc Reactor to start speaking';
    }
  } catch (err) {
    talkStatus.textContent = 'ERROR';
    talkStatus.style.color = 'var(--red)';
    talkHint.textContent = err.message;
  }
}

function playAudioResponse(base64Mp3) {
  arcReactor.className = 'arc-reactor-wrapper speaking';
  talkStatus.textContent = 'SPEAKING...';
  talkStatus.style.color = 'var(--emerald)';

  const audio = new Audio('data:audio/mp3;base64,' + base64Mp3);
  audio.onended = () => {
    arcReactor.className = 'arc-reactor-wrapper';
    talkStatus.textContent = 'IDLE';
    talkStatus.style.color = 'var(--cyan)';
    talkHint.textContent = 'Tap Arc Reactor to speak again';
  };
  audio.play().catch(e => {
    console.warn('Audio autoplay blocked:', e);
    arcReactor.className = 'arc-reactor-wrapper';
    talkStatus.textContent = 'IDLE';
    talkStatus.style.color = 'var(--cyan)';
    talkHint.textContent = 'Tap Arc Reactor to speak';
  });
}

// --- 💬 CHAT ---
function initChat() {
  const sendBtn = document.getElementById('btn-send-chat');
  
  if (sendBtn && chatInput) {
    sendBtn.addEventListener('click', sendUserMessage);
    chatInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendUserMessage();
      }
    });
  }

  // Quick Chips
  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (chatInput) {
        chatInput.value = btn.textContent;
        sendUserMessage();
      }
    });
  });
}

async function sendUserMessage() {
  const text = chatInput.value.trim();
  if (!text) return;

  chatInput.value = '';
  addMessageToChat('user', text);

  // Show typing indicator
  const typingBubble = document.createElement('div');
  typingBubble.className = 'message-bubble assistant';
  typingBubble.id = 'typing-indicator';
  typingBubble.innerHTML = '<span class="status-dot"></span> JARVIS is thinking...';
  messagesList.appendChild(typingBubble);
  messagesList.scrollTop = messagesList.scrollHeight;

  try {
    const payload = {
      messages: state.chatHistory.map(m => ({ role: m.role, content: m.content })),
      session_id: 'mobile_web_session'
    };

    const res = await apiFetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();

    if (!res.ok) {
      const err = await res.json();
      addMessageToChat('assistant', `⚠️ Error: ${err.detail || 'Failed to get response'}`);
      return;
    }

    const data = await res.json();
    addMessageToChat('assistant', data.response);
  } catch (err) {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
    addMessageToChat('assistant', `⚠️ Network Error: ${err.message}`);
  }
}

function addMessageToChat(role, content) {
  state.chatHistory.push({ role, content });

  const bubble = document.createElement('div');
  bubble.className = `message-bubble ${role}`;
  
  const header = document.createElement('div');
  header.className = 'message-header';
  header.textContent = role === 'user' ? 'YOU' : '⚡ JARVIS';

  const body = document.createElement('div');
  // Simple markdown conversion for bold & linebreaks
  let formatted = content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code style="background:rgba(0,240,255,0.15);padding:1px 4px;border-radius:3px;">$1</code>')
    .replace(/\n/g, '<br/>');

  body.innerHTML = formatted;

  bubble.appendChild(header);
  bubble.appendChild(body);
  messagesList.appendChild(bubble);
  messagesList.scrollTop = messagesList.scrollHeight;
}

// --- 💻 TELEMETRY ---
function initTelemetry() {
  // Poll telemetry every 3.5 seconds
  setInterval(() => {
    if (state.activeTab === 'laptop') {
      fetchTelemetry();
    }
  }, 3500);
}

async function fetchTelemetry() {
  try {
    const res = await apiFetch('/api/system/status');
    if (!res.ok) return;
    const data = await res.json();

    // CPU
    document.getElementById('stat-cpu').textContent = `${data.cpu.percent}%`;
    document.getElementById('stat-cpu-cores').textContent = `${data.cpu.cores} Physical/Logical Cores`;
    const cpuBar = document.getElementById('bar-cpu');
    cpuBar.style.width = `${data.cpu.percent}%`;
    cpuBar.className = data.cpu.percent > 85 ? 'stat-bar-fill danger' : data.cpu.percent > 60 ? 'stat-bar-fill warn' : 'stat-bar-fill';

    // RAM
    document.getElementById('stat-ram').textContent = `${data.ram.percent}%`;
    document.getElementById('stat-ram-detail').textContent = `${data.ram.used_gb} GB / ${data.ram.total_gb} GB`;
    const ramBar = document.getElementById('bar-ram');
    ramBar.style.width = `${data.ram.percent}%`;
    ramBar.className = data.ram.percent > 85 ? 'stat-bar-fill danger' : data.ram.percent > 70 ? 'stat-bar-fill warn' : 'stat-bar-fill';

    // Battery
    document.getElementById('stat-battery').textContent = `${data.battery.percent}%`;
    document.getElementById('stat-battery-state').textContent = data.battery.status;
    const battBar = document.getElementById('bar-battery');
    battBar.style.width = `${data.battery.percent}%`;
    battBar.className = data.battery.percent < 20 ? 'stat-bar-fill danger' : data.battery.percent < 40 ? 'stat-bar-fill warn' : 'stat-bar-fill';

    // Disk
    document.getElementById('stat-disk').textContent = `${data.disk.percent}%`;
    document.getElementById('stat-disk-detail').textContent = `${data.disk.free_gb} GB Free / ${data.disk.total_gb} GB`;
    document.getElementById('bar-disk').style.width = `${data.disk.percent}%`;

    // OS info
    document.getElementById('stat-os').textContent = `${data.os.system} ${data.os.release} (${data.os.arch})`;
    document.getElementById('stat-time').textContent = `Last sync: ${data.timestamp}`;
  } catch (err) {
    console.warn('Telemetry poll error:', err);
  }
}

// --- 🧠 MEMORY & TASKS ---
async function fetchTasks() {
  try {
    const res = await apiFetch('/api/memory/tasks');
    if (!res.ok) return;
    const data = await res.json();
    const listEl = document.getElementById('tasks-list');
    listEl.innerHTML = '';

    if (!data.tasks || data.tasks.length === 0) {
      listEl.innerHTML = '<div style="color:var(--text-muted);font-size:0.85rem;padding:8px;">No pending tasks recorded.</div>';
      return;
    }

    data.tasks.forEach(t => {
      const item = document.createElement('div');
      item.className = `task-item ${t.status === 'completed' ? 'done' : ''}`;
      item.innerHTML = `
        <div>
          <div class="task-title">${t.title}</div>
          <div style="font-size:0.75rem;color:var(--text-muted);">${t.project} • ${t.priority}</div>
        </div>
        <span class="task-tag">${t.status}</span>
      `;
      listEl.appendChild(item);
    });
  } catch (err) {
    console.warn('Tasks fetch error:', err);
  }
}

// --- ⚡ VERSION 7: REMOTE CONTROL DECK ---
async function executeRemote(action, payload = {}) {
  const feedbackEl = document.getElementById('remote-action-feedback');
  if (feedbackEl) {
    feedbackEl.textContent = `Executing ${action}...`;
    feedbackEl.style.color = 'var(--gold)';
  }

  try {
    const res = await apiFetch('/api/remote/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, ...payload })
    });

    const data = await res.json();
    if (feedbackEl) {
      if (data.status === 'success' && data.result.success) {
        feedbackEl.textContent = `✓ ${data.result.message || 'Action executed successfully!'}`;
        feedbackEl.style.color = 'var(--emerald)';
      } else {
        feedbackEl.textContent = `✗ ${data.result.error || 'Action failed'}`;
        feedbackEl.style.color = 'var(--red)';
      }
      setTimeout(() => { feedbackEl.textContent = ''; }, 4000);
    }
  } catch (err) {
    if (feedbackEl) {
      feedbackEl.textContent = `✗ Error: ${err.message}`;
      feedbackEl.style.color = 'var(--red)';
      setTimeout(() => { feedbackEl.textContent = ''; }, 4000);
    }
  }
}

async function requestScreenshot() {
  const card = document.getElementById('screenshot-card');
  const img = document.getElementById('screenshot-img');
  const feedbackEl = document.getElementById('remote-action-feedback');

  if (feedbackEl) {
    feedbackEl.textContent = '📸 Capturing laptop screen snapshot...';
    feedbackEl.style.color = 'var(--cyan)';
  }

  try {
    const res = await apiFetch('/api/remote/screenshot');
    const data = await res.json();

    if (data.success && data.image_base64) {
      img.src = `data:${data.mime_type || 'image/jpeg'};base64,${data.image_base64}`;
      card.style.display = 'block';
      if (feedbackEl) {
        feedbackEl.textContent = '✓ Screen snapshot captured!';
        feedbackEl.style.color = 'var(--emerald)';
        setTimeout(() => { feedbackEl.textContent = ''; }, 3000);
      }
    } else {
      if (feedbackEl) {
        feedbackEl.textContent = `✗ Capture failed: ${data.error || 'Unknown error'}`;
        feedbackEl.style.color = 'var(--red)';
      }
    }
  } catch (err) {
    if (feedbackEl) {
      feedbackEl.textContent = `✗ Error: ${err.message}`;
      feedbackEl.style.color = 'var(--red)';
    }
  }
}

// Attach globally to window
window.executeRemote = executeRemote;
window.requestScreenshot = requestScreenshot;


