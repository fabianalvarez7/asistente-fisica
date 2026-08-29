/**
 * SSE client for the Física 1 chat assistant.
 *
 * Uses fetch() + ReadableStream reader instead of EventSource because
 * EventSource only supports GET requests. Implements the hand-parser contract
 * defined in the design doc:
 *   1. Streaming via fetch POST + ReadableStream reader.
 *   2. Per-stream string buffer.
 *   3. Frame splitting on "\n\n", preserving mid-frame chunks.
 *   4. Frame dispatch for event: error, data: [DONE], data: <token>.
 *   5. Input re-enabled on terminal frame, error event, or network failure.
 *   6. Null response.body treated as a network error.
 *   7. Pre-send validation with Spanish hints; no request on invalid input.
 */

const form = document.getElementById('chat-form');
const input = document.getElementById('query');
const messages = document.getElementById('messages');
const hint = document.getElementById('hint');
const sendBtn = document.getElementById('send-btn');
const nameArea = document.getElementById('name-area');
const nameInput = document.getElementById('student-name');
const nameSubmit = document.getElementById('name-submit');

const MAX_CHARS = 500;
const STORAGE_KEY = 'student_name';
const FALLBACK_ERROR = 'Ocurrió un error, intentá de nuevo';
let studentName = localStorage.getItem(STORAGE_KEY);

/**
 * HTML-escape user-provided text before injecting it into innerHTML. The
 * welcome greeting is the only place we render raw HTML, and only the
 * student's own name (from localStorage) ever lands inside the injected
 * span. Escaping is still required because typed names are arbitrary.
 */
function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

/**
 * Escape regex metacharacters in user-provided text. Used to build a safe
 * pattern that matches the student's name literally inside the welcome
 * message content.
 */
function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Render LaTeX math in an element using KaTeX auto-render.
 *
 * Supports $...$ (inline) and $$...$$ (display) delimiters. The LLM emits
 * these naturally for physics formulas (e.g. $F = ma$). throwOnError:false
 * keeps the page rendering even if the model produces malformed LaTeX.
 *
 * Safe to call repeatedly: renderMathInElement is idempotent on already-
 * rendered nodes, and we only call it once per assistant message on [DONE].
 *
 * Guarded by typeof because KaTeX loads from a CDN and may not be ready
 * in unusual load orders (e.g. if the CDN is blocked).
 */
function renderMathInBubble(element) {
  if (typeof window.renderMathInElement !== 'function') return;
  window.renderMathInElement(element, {
    delimiters: [
      { left: '$$', right: '$$', display: true },
      { left: '$', right: '$', display: false },
      { left: '\\(', right: '\\)', display: false },
      { left: '\\[', right: '\\]', display: true },
    ],
    throwOnError: false,
  });
}

function setLoading(isLoading) {
  input.disabled = isLoading;
  sendBtn.disabled = isLoading;
}

function showHint(text) {
  hint.textContent = text;
}

function clearHint() {
  hint.textContent = '';
}

function createMessageElement(role) {
  const li = document.createElement('li');
  li.className = `message ${role}`;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  const deleteBtn = document.createElement('button');
  deleteBtn.type = 'button';
  deleteBtn.className = 'delete-btn';
  deleteBtn.setAttribute('aria-label', 'Eliminar mensaje');
  deleteBtn.textContent = '×';
  const content = document.createElement('span');
  content.className = 'bubble-content';
  bubble.appendChild(deleteBtn);
  bubble.appendChild(content);
  li.appendChild(bubble);
  return { li, bubble, content, deleteBtn };
}

function renderMessage(msg, index = -1) {
  const { li, bubble, content, deleteBtn } = createMessageElement(msg.role);
  if (msg.id != null) {
    deleteBtn.dataset.messageId = msg.id;
  } else {
    deleteBtn.disabled = true;
  }

  // Welcome greeting: the first assistant turn the student sees after
  // identifying. We recognize it by position (index 0), role, and the fact
  // that it contains the student's name. Render with the dedicated
  // greeting styles and wrap the name in a serif-italic span so the brand
  // wordmark tone carries over to the chat column.
  const isWelcome = (
    index === 0 &&
    msg.role === 'assistant' &&
    studentName &&
    msg.content.includes(studentName)
  );

  if (isWelcome) {
    bubble.classList.add('bubble-greeting');
    const pattern = new RegExp(escapeRegex(studentName), '');
    content.innerHTML = msg.content.replace(
      pattern,
      `<span class="greeting-name">${escapeHtml(studentName)}</span>`
    );
  } else {
    content.textContent = msg.content;
  }

  messages.appendChild(li);
  if (msg.role === 'assistant') {
    renderMathInBubble(bubble);
  }
  messages.scrollTop = messages.scrollHeight;
  return li;
}

function appendUserMessage(text) {
  return renderMessage({ role: 'user', content: text });
}

function appendAssistantPlaceholder() {
  const { li, bubble, content, deleteBtn } = createMessageElement('assistant');
  li.classList.add('loading');
  deleteBtn.disabled = true;
  messages.appendChild(li);
  messages.scrollTop = messages.scrollHeight;
  return { li, bubble, content, deleteBtn };
}

function processFrame(frame, assistant, userLi) {
  const lines = frame.split('\n');
  let eventName = null;
  let dataValue = null;

  for (const line of lines) {
    if (line.startsWith('event: ')) {
      eventName = line.slice(7);
    } else if (line.startsWith('data: ')) {
      dataValue = line.slice(6);
    }
  }

  if (eventName === 'error') {
    assistant.li.classList.remove('loading');
    // Show whatever the backend sent. In dev this is the real exception
    // (rate limits, timeouts, etc.); in prod it's the generic fallback.
    assistant.content.textContent = dataValue || FALLBACK_ERROR;
    return;
  }

  if (eventName === 'user_message_id' && userLi) {
    const deleteBtn = userLi.querySelector('.delete-btn');
    if (deleteBtn) {
      deleteBtn.dataset.messageId = dataValue;
      deleteBtn.disabled = false;
    }
    return;
  }

  if (eventName === 'assistant_message_id' && assistant) {
    assistant.deleteBtn.dataset.messageId = dataValue;
    assistant.deleteBtn.disabled = false;
    return;
  }

  if (dataValue === '[DONE]') {
    assistant.li.classList.remove('loading');
    renderMathInBubble(assistant.bubble);
    return;
  }

  if (dataValue !== null) {
    assistant.li.classList.remove('loading');
    assistant.content.textContent += dataValue;
  }
}

async function sendMessage(query) {
  setLoading(true);
  clearHint();
  const userLi = appendUserMessage(query);
  const assistant = appendAssistantPlaceholder();

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, student_name: studentName }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is null');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        processFrame(frame, assistant, userLi);
      }
    }

    // Flush any remaining bytes in the decoder.
    const remaining = decoder.decode();
    if (remaining) {
      buffer += remaining;
      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        processFrame(frame, assistant, userLi);
      }
    }
  } catch (err) {
    assistant.li.classList.remove('loading');
    assistant.content.textContent = FALLBACK_ERROR;
  } finally {
    setLoading(false);
    input.focus();
  }
}

function setChatEnabled(enabled) {
  input.disabled = !enabled;
  sendBtn.disabled = !enabled;
}

function startChat(name) {
  studentName = name;
  localStorage.setItem(STORAGE_KEY, name);
  nameArea.style.display = 'none';
  setChatEnabled(true);
  loadHistory();
}

function handleNameSubmit() {
  const name = nameInput.value.trim();
  if (!name) {
    showHint('Escribí tu nombre para empezar');
    return;
  }
  clearHint();
  startChat(name);
}

async function loadHistory() {
  if (!studentName) return;
  messages.innerHTML = '';
  try {
    const resp = await fetch(`/history?student_name=${encodeURIComponent(studentName)}`);
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    const data = await resp.json();
    data.messages.forEach((msg, i) => renderMessage(msg, i));
  } catch (err) {
    showHint('No se pudo cargar el historial');
  }
}

nameSubmit.addEventListener('click', handleNameSubmit);
nameInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    handleNameSubmit();
  }
});

messages.addEventListener('click', async (event) => {
  const deleteBtn = event.target.closest('.delete-btn');
  if (!deleteBtn) return;
  const messageId = deleteBtn.dataset.messageId;
  if (!messageId || !studentName) return;
  const resp = await fetch(
    `/messages/${messageId}?student_name=${encodeURIComponent(studentName)}`,
    { method: 'DELETE' }
  );
  if (resp.ok) {
    deleteBtn.closest('.message').remove();
  }
  // 403/404 are silently ignored so the UI stays consistent.
});

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const query = input.value.trim();

  if (query.length === 0) {
    showHint('Escribí una pregunta');
    return;
  }

  if (query.length > MAX_CHARS) {
    showHint('Máximo 500 caracteres');
    return;
  }

  input.value = '';
  sendMessage(query);
});

if (studentName) {
  nameArea.style.display = 'none';
  setChatEnabled(true);
  loadHistory();
} else {
  setChatEnabled(false);
}
