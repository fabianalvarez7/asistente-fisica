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
// Shown as a non-blocking banner above the messages list when the
// persistence layer is degraded. The SSE stream emits
// ``event: history_status\ndata: degraded`` and ``/history`` returns
// ``degraded: true`` to trigger it. The chat itself keeps responding
// normally; the banner only signals that the conversation will not
// survive a reload.
const HISTORY_BANNER_ID = 'history-banner';
let studentName = localStorage.getItem(STORAGE_KEY);

/**
 * Show or hide the history-degraded banner. Idempotent: calling it
 * multiple times with the same ``visible`` value has no extra effect.
 *
 * @param {boolean} visible true to reveal the banner, false to hide it.
 */
function setHistoryBannerVisible(visible) {
  const banner = document.getElementById(HISTORY_BANNER_ID);
  if (!banner) return;
  if (visible) {
    banner.hidden = false;
  } else {
    banner.hidden = true;
  }
}

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
  const content = document.createElement('span');
  content.className = 'bubble-content';
  bubble.appendChild(content);
  li.appendChild(bubble);
  return { li, bubble, content };
}

function renderMessage(msg, index = -1) {
  const { li, bubble, content } = createMessageElement(msg.role);

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
  const { li, bubble, content } = createMessageElement('assistant');
  li.classList.add('loading');
  messages.appendChild(li);
  messages.scrollTop = messages.scrollHeight;
  return { li, bubble, content };
}

function processFrame(frame, assistant) {
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

  if (eventName === 'history_status' && dataValue === 'degraded') {
    // The persistence layer failed at least once for this request. Show
    // the banner so the student knows the conversation won't survive a
    // reload — but the chat itself keeps responding.
    setHistoryBannerVisible(true);
    return;
  }

  if (eventName === 'user_message_id' || eventName === 'assistant_message_id') {
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
  appendUserMessage(query);
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
        processFrame(frame, assistant);
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
        processFrame(frame, assistant);
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
    setHistoryBannerVisible(Boolean(data.degraded));
    data.messages.forEach((msg, i) => renderMessage(msg, i));
  } catch (err) {
    showHint('No se pudo cargar el historial');
  }
}

const topicsContainer = document.getElementById('topics-container');

const DRAFT_PREFIX = /^\[BORRADOR[^\]]*\]\s*/;

/**
 * Strip the professor-review draft marker from a prompt string.
 *
 * Pure function: no side effects, only string manipulation. Used both when
 * rendering the prompt text (to decide the draft modifier class) and when
 * filling the chat input (so the student never sends the marker).
 */
function stripDraftPrefix(text) {
  return text.replace(DRAFT_PREFIX, '').trim();
}

async function loadTopics() {
  if (!topicsContainer) return;

  try {
    const resp = await fetch('/topics');
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    const data = await resp.json();

    const fragment = document.createDocumentFragment();
    (data.unidades || []).forEach((unidad) => {
      const group = document.createElement('div');
      group.className = 'topic-group';

      const heading = document.createElement('h3');
      heading.className = 'topic-group-title';

      const headerBtn = document.createElement('button');
      headerBtn.type = 'button';
      headerBtn.className = 'topic-group-header';
      headerBtn.setAttribute('aria-expanded', 'false');
      headerBtn.setAttribute('aria-controls', `prompts-${unidad.numero}`);
      headerBtn.textContent = `UNIDAD ${unidad.numero} — ${unidad.titulo}`;

      heading.appendChild(headerBtn);
      group.appendChild(heading);

      const body = document.createElement('div');
      body.id = `prompts-${unidad.numero}`;
      body.className = 'topic-prompts';
      body.setAttribute('role', 'region');
      body.setAttribute('aria-live', 'polite');
      body.hidden = true;

      const preguntas = unidad.preguntas || [];
      if (preguntas.length === 0) {
        const emptyMsg = document.createElement('p');
        emptyMsg.textContent = 'Sin preguntas por ahora';
        body.appendChild(emptyMsg);
      } else {
        preguntas.forEach((raw) => {
          const promptBtn = document.createElement('button');
          promptBtn.type = 'button';
          promptBtn.className = 'topic-prompt';
          promptBtn.dataset.question = raw;

          if (raw.startsWith('[BORRADOR')) {
            promptBtn.classList.add('topic-prompt--draft');
            const badge = document.createElement('span');
            badge.className = 'draft-badge';
            badge.textContent = 'Borrador';
            promptBtn.appendChild(badge);
          }

          promptBtn.appendChild(document.createTextNode(stripDraftPrefix(raw)));
          body.appendChild(promptBtn);
        });
      }

      group.appendChild(body);
      fragment.appendChild(group);
    });

    topicsContainer.innerHTML = '';
    topicsContainer.appendChild(fragment);

    // Desktop default: first unit open; mobile stays fully collapsed.
    if (window.matchMedia('(min-width: 769px)').matches) {
      const firstHeader = topicsContainer.querySelector('.topic-group-header');
      const firstBody = topicsContainer.querySelector('.topic-prompts');
      if (firstHeader && firstBody) {
        firstHeader.setAttribute('aria-expanded', 'true');
        firstBody.hidden = false;
      }
    }
  } catch (err) {
    // El sidebar es decorativo: si falla, ocultamos el contenedor sin
    // interrumpir la experiencia de chat.
    topicsContainer.style.display = 'none';
  }
}

if (topicsContainer) {
  topicsContainer.addEventListener('click', (event) => {
    const headerBtn = event.target.closest('.topic-group-header');
    if (headerBtn) {
      const bodyId = headerBtn.getAttribute('aria-controls');
      const targetBody = document.getElementById(bodyId);
      if (!targetBody) return;

      // Close any currently open unit so only one is expanded at a time.
      const openHeader = topicsContainer.querySelector('.topic-group-header[aria-expanded="true"]');
      if (openHeader && openHeader !== headerBtn) {
        const openBody = document.getElementById(openHeader.getAttribute('aria-controls'));
        if (openBody) {
          openBody.hidden = true;
        }
        openHeader.setAttribute('aria-expanded', 'false');
      }

      const willOpen = targetBody.hidden;
      targetBody.hidden = !willOpen;
      headerBtn.setAttribute('aria-expanded', String(willOpen));
      return;
    }

    const promptBtn = event.target.closest('.topic-prompt');
    if (promptBtn) {
      input.value = stripDraftPrefix(promptBtn.dataset.question);
      if (!input.disabled) {
        input.focus();
      }
    }
  });
}

nameSubmit.addEventListener('click', handleNameSubmit);
nameInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    handleNameSubmit();
  }
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

loadTopics();
