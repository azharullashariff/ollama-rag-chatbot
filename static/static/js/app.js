/* ── app.js — RAG Chatbot Frontend Logic ──────────────────────────────────── */

// ── State ──────────────────────────────────────────────────────────────────────
const state = {
  isStreaming: false,
  messageCount: 0,
  currentModel: document.getElementById('modelSelect')?.value || 'llama3',
};

// ── DOM Refs ───────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const messagesEl    = $('messages');
const queryInput    = $('queryInput');
const sendBtn       = $('sendBtn');
const welcomeScreen = $('welcomeScreen');
const modelSelect   = $('modelSelect');
const modelBadge    = $('modelBadge');
const ragToggle     = $('ragToggle');
const chunkCount    = $('chunkCount');
const fileInput     = $('fileInput');
const uploadZone    = $('uploadZone');
const uploadBtn     = $('uploadBtn');
const uploadStatus  = $('uploadStatus');
const filesList     = $('filesList');
const clearDocsBtn  = $('clearDocsBtn');
const newChatBtn    = $('newChatBtn');
const sidebar       = $('sidebar');
const menuBtn       = $('menuBtn');
const sidebarToggle = $('sidebarToggle');
const modalOverlay  = $('modalOverlay');
const modalClose    = $('modalClose');
const modalBody     = $('modalBody');

// ── Helpers ────────────────────────────────────────────────────────────────────

function formatTime(date = new Date()) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function scrollToBottom() {
  messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: 'smooth' });
}

function setInputEnabled(enabled) {
  queryInput.disabled = !enabled;
  sendBtn.disabled    = !enabled || !queryInput.value.trim();
  state.isStreaming   = !enabled;
}

function showUploadStatus(message, type = '') {
  uploadStatus.textContent = message;
  uploadStatus.className   = `upload-status ${type}`;
  uploadStatus.classList.remove('hidden');
  if (type === 'success' || type === 'error') {
    setTimeout(() => uploadStatus.classList.add('hidden'), 4000);
  }
}

// ── Markdown-lite renderer ─────────────────────────────────────────────────────
function renderMarkdown(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
      `<pre><code class="lang-${lang}">${code.trim()}</code></pre>`)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^#{3}\s(.+)$/gm, '<h3>$1</h3>')
    .replace(/^#{2}\s(.+)$/gm, '<h2>$1</h2>')
    .replace(/^#{1}\s(.+)$/gm, '<h1>$1</h1>')
    .replace(/^[-*]\s(.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>');
}

// ── Message Rendering ──────────────────────────────────────────────────────────

function createMessage(role, content = '', sources = []) {
  state.messageCount++;

  // Hide welcome screen on first message
  if (welcomeScreen && state.messageCount === 1) {
    welcomeScreen.style.display = 'none';
  }

  const msgId    = `msg-${Date.now()}`;
  const avatar   = role === 'user' ? '👤' : '🤖';
  const timeStr  = formatTime();

  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;
  wrapper.id = msgId;

  wrapper.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-content">
      <div class="message-bubble" id="${msgId}-bubble">
        ${role === 'ai' && !content ? '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>' : ''}
      </div>
      <div class="message-meta">
        <span class="message-time">${timeStr}</span>
        ${sources.length ? `<button class="sources-btn" data-sources='${JSON.stringify(sources)}'>📚 ${sources.length} source${sources.length > 1 ? 's' : ''}</button>` : ''}
      </div>
    </div>
  `;

  messagesEl.appendChild(wrapper);
  scrollToBottom();

  if (content) {
    const bubble = wrapper.querySelector(`#${msgId}-bubble`);
    bubble.innerHTML = `<p>${renderMarkdown(content)}</p>`;
  }

  // Bind sources button
  const sourcesBtn = wrapper.querySelector('.sources-btn');
  if (sourcesBtn) {
    sourcesBtn.addEventListener('click', () => {
      const srcs = JSON.parse(sourcesBtn.dataset.sources);
      showSourcesModal(srcs);
    });
  }

  return msgId;
}

function updateMessageBubble(msgId, fullText) {
  const bubble = $(`${msgId}-bubble`);
  if (bubble) {
    bubble.innerHTML = `<p>${renderMarkdown(fullText)}</p>`;
    scrollToBottom();
  }
}

function finalizeMessage(msgId, sources = []) {
  const meta = document.querySelector(`#${msgId} .message-meta`);
  if (meta && sources.length) {
    const btn = document.createElement('button');
    btn.className = 'sources-btn';
    btn.textContent = `📚 ${sources.length} source${sources.length > 1 ? 's' : ''}`;
    btn.dataset.sources = JSON.stringify(sources);
    btn.addEventListener('click', () => showSourcesModal(sources));
    meta.appendChild(btn);
  }
}

// ── Chat Send ──────────────────────────────────────────────────────────────────

async function sendMessage() {
  const query = queryInput.value.trim();
  if (!query || state.isStreaming) return;

  // Render user bubble
  createMessage('user', query);
  queryInput.value = '';
  queryInput.style.height = 'auto';
  sendBtn.disabled = true;

  // Render AI placeholder (typing indicator)
  const aiMsgId = createMessage('ai');
  setInputEnabled(false);

  let fullText = '';

  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        model: modelSelect.value,
        use_rag: ragToggle.checked,
      }),
    });

    if (!res.ok) throw new Error(`Server error: ${res.status}`);

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.token) {
            fullText += data.token;
            updateMessageBubble(aiMsgId, fullText);
          }
          if (data.done) break;
          if (data.error) throw new Error(data.error);
        } catch (_) { /* skip malformed chunks */ }
      }
    }

  } catch (err) {
    updateMessageBubble(aiMsgId, `⚠️ Error: ${err.message}`);
  } finally {
    setInputEnabled(true);
    queryInput.focus();
  }
}

// ── Sources Modal ──────────────────────────────────────────────────────────────

function showSourcesModal(sources) {
  modalBody.innerHTML = sources.map((src, i) => `
    <div class="source-item">
      <div class="source-file">📄 Source ${i + 1}: ${src.source || 'Unknown'} ${src.chunk_index !== undefined ? `(chunk ${src.chunk_index})` : ''}</div>
    </div>
  `).join('');
  modalOverlay.classList.remove('hidden');
}

function closeModal() {
  modalOverlay.classList.add('hidden');
}

// ── File Upload ────────────────────────────────────────────────────────────────

async function uploadFile(file) {
  showUploadStatus(`Uploading ${file.name}...`);

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res  = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) throw new Error(data.error);

    showUploadStatus(data.message, 'success');
    chunkCount.textContent = data.total_docs;
    await loadFilesList();
  } catch (err) {
    showUploadStatus(`❌ ${err.message}`, 'error');
  }
}

async function loadFilesList() {
  try {
    const res  = await fetch('/api/documents');
    const data = await res.json();

    chunkCount.textContent = data.total_chunks;

    if (!data.files.length) {
      filesList.innerHTML = '<span style="color:var(--text-muted);font-size:12px">No files indexed yet</span>';
      return;
    }

    filesList.innerHTML = data.files.map(f => `
      <div class="file-item">
        <span class="file-type">${f.type}</span>
        <span class="file-name" title="${f.name}">${f.name}</span>
        <span class="file-size">${formatFileSize(f.size)}</span>
      </div>
    `).join('');
  } catch (_) {
    filesList.innerHTML = '<span style="color:var(--text-muted);font-size:12px">Could not load files</span>';
  }
}

// ── Clear Documents ────────────────────────────────────────────────────────────

async function clearDocuments() {
  if (!confirm('Clear all indexed documents from the vector store?')) return;
  try {
    const res  = await fetch('/api/documents/clear', { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    chunkCount.textContent = 0;
    await loadFilesList();
    alert(data.message);
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

// ── Sidebar Toggle ─────────────────────────────────────────────────────────────

function toggleSidebar() {
  const isMobile = window.innerWidth <= 768;
  if (isMobile) {
    sidebar.classList.toggle('open');
  } else {
    sidebar.classList.toggle('hidden');
    document.querySelector('.main').classList.toggle('full');
  }
}

// ── Event Listeners ────────────────────────────────────────────────────────────

// Send on button click
sendBtn.addEventListener('click', sendMessage);

// Enter to send (Shift+Enter for newline)
queryInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Enable/disable send button
queryInput.addEventListener('input', () => {
  sendBtn.disabled = !queryInput.value.trim() || state.isStreaming;
  // Auto-resize textarea
  queryInput.style.height = 'auto';
  queryInput.style.height = Math.min(queryInput.scrollHeight, 160) + 'px';
});

// Model selector
modelSelect?.addEventListener('change', () => {
  state.currentModel = modelSelect.value;
  modelBadge.textContent = modelSelect.value;
});

// Upload triggers
uploadBtn.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
  Array.from(fileInput.files).forEach(uploadFile);
  fileInput.value = '';
});

// Drag & drop
uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('dragover');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('dragover');
  Array.from(e.dataTransfer.files).forEach(uploadFile);
});

// Clear docs
clearDocsBtn.addEventListener('click', clearDocuments);

// New chat
newChatBtn.addEventListener('click', () => {
  messagesEl.innerHTML = '';
  if (welcomeScreen) {
    messagesEl.appendChild(welcomeScreen);
    welcomeScreen.style.display = '';
  }
  state.messageCount = 0;
});

// Sidebar
menuBtn?.addEventListener('click', toggleSidebar);
sidebarToggle?.addEventListener('click', toggleSidebar);

// Modal
modalClose.addEventListener('click', closeModal);
modalOverlay.addEventListener('click', (e) => {
  if (e.target === modalOverlay) closeModal();
});

// Suggestion cards
document.querySelectorAll('.suggestion-card').forEach(card => {
  card.addEventListener('click', () => {
    queryInput.value = card.dataset.query;
    sendMessage();
  });
});

// ── Init ───────────────────────────────────────────────────────────────────────
loadFilesList();
