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

const MAX_CHARS = 500;
const FALLBACK_ERROR = 'Ocurrió un error, intentá de nuevo';

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

function appendUserMessage(text) {
  const li = document.createElement('li');
  li.className = 'message user';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  li.appendChild(bubble);
  messages.appendChild(li);
  messages.scrollTop = messages.scrollHeight;
}

function appendAssistantPlaceholder() {
  const li = document.createElement('li');
  li.className = 'message assistant loading';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  li.appendChild(bubble);
  messages.appendChild(li);
  messages.scrollTop = messages.scrollHeight;
  return { li, bubble };
}

function processFrame(frame, elements) {
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
    elements.li.classList.remove('loading');
    elements.bubble.textContent = FALLBACK_ERROR;
    return;
  }

  if (dataValue === '[DONE]') {
    elements.li.classList.remove('loading');
    renderMathInBubble(elements.bubble);
    return;
  }

  if (dataValue !== null) {
    elements.li.classList.remove('loading');
    elements.bubble.textContent += dataValue;
  }
}

async function sendMessage(query) {
  setLoading(true);
  clearHint();
  appendUserMessage(query);
  const elements = appendAssistantPlaceholder();

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
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
        processFrame(frame, elements);
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
        processFrame(frame, elements);
      }
    }
  } catch (err) {
    elements.li.classList.remove('loading');
    elements.bubble.textContent = FALLBACK_ERROR;
  } finally {
    setLoading(false);
    input.focus();
  }
}

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
