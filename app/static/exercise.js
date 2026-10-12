const form = document.getElementById('chat-form');
const input = document.getElementById('query');
const messages = document.getElementById('messages');
const hint = document.getElementById('hint');
const sendBtn = document.getElementById('send-btn');
const nameArea = document.getElementById('name-area');
const nameInput = document.getElementById('student-name');
const loginScreen = document.getElementById('login-screen');
const loginHint = document.getElementById('login-hint');
const appShell = document.getElementById('app-shell');
const exerciseTitle = document.getElementById('exercise-title');
const exerciseStatement = document.getElementById('exercise-statement');
const exerciseGraph = document.getElementById('exercise-graph');
const starterIdeas = document.getElementById('starter-ideas');
const exerciseStatus = document.getElementById('exercise-status');
const exerciseRetry = document.getElementById('exercise-retry');
const exerciseList = document.getElementById('exercise-list');
const historyBanner = document.getElementById('history-banner');
const checkpointPanel = document.getElementById('checkpoint-panel');
const checkpointProgress = document.getElementById('checkpoint-progress');
const checkpointPart = document.getElementById('checkpoint-part');
const progressBar = document.getElementById('progress-bar');
const checkpointPrompt = document.getElementById('checkpoint-prompt');
const checkpointOptions = document.getElementById('checkpoint-options');
const checkpointFeedback = document.getElementById('checkpoint-feedback');
const checkpointSubmit = document.getElementById('checkpoint-submit');
const checkpointHint = document.getElementById('checkpoint-hint');
const checkpointHelp = document.getElementById('checkpoint-help');
const exerciseReview = document.getElementById('exercise-review');
const exerciseReviewList = document.getElementById('exercise-review-list');
const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
const mobileMenuClose = document.getElementById('mobile-menu-close');
const sidebar = document.querySelector('.sidebar');

const STORAGE_KEY = 'student_name';
const MAX_CHARS = 500;
const FALLBACK_ERROR = 'Ocurrió un error, intentá de nuevo';
const EXERCISE_PROGRESS_ERROR = 'No se pudo leer tu progreso. No se generó una nueva guía. Reintentá.';
const EXERCISE_COMPLETED_CODE = 'exercise_completed';
let studentName = localStorage.getItem(STORAGE_KEY);
let exercise = null;
let exerciseCatalog = [];
let historyReady = false;
let progressState = null;
let exerciseHistory = [];
let selectedOptionIds = new Set();
let checkpointBusy = false;
let selectionToken = 0;

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return text.replace(/[&<>"']/g, (match) => map[match]);
}

function renderAssistantMarkdown(text) {
  return escapeHtml(text).replace(/\*\*([^*\n]+?)\*\*/g, '<strong>$1</strong>');
}

function setHistoryBannerVisible(visible) {
  if (historyBanner) historyBanner.hidden = !visible;
}

function showHint(text) {
  if (hint) hint.textContent = text;
  if (loginHint) loginHint.textContent = text;
}

function clearHint() {
  if (hint) hint.textContent = '';
  if (loginHint) loginHint.textContent = '';
}

function setChatEnabled(enabled) {
  historyReady = enabled;
  const canChat = enabled
    && Boolean(studentName)
    && Boolean(exercise)
    && Boolean(progressState)
    && !progressState.complete;
  if (input) input.disabled = !canChat;
  if (sendBtn) sendBtn.disabled = !canChat;
}

function setExerciseProgressError(message = EXERCISE_PROGRESS_ERROR) {
  progressState = null;
  if (checkpointPanel) checkpointPanel.hidden = true;
  if (exerciseStatus) exerciseStatus.textContent = message;
  if (exerciseRetry) exerciseRetry.hidden = false;
  setChatEnabled(false);
}

function clearExerciseProgressError() {
  if (exerciseStatus) exerciseStatus.textContent = '';
  if (exerciseRetry) exerciseRetry.hidden = true;
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

function renderMessage(message) {
  if (!messages) return;
  const { li, content } = createMessageElement(message.role);
  content.innerHTML = message.role === 'assistant'
    ? renderAssistantMarkdown(message.content)
    : escapeHtml(message.content);
  messages.appendChild(li);
  messages.scrollTop = messages.scrollHeight;
}

function appendUserMessage(text) {
  if (!messages) return;
  renderMessage({ role: 'user', content: text });
}

function appendAssistantPlaceholder() {
  if (!messages) return null;
  const { li, content } = createMessageElement('assistant');
  li.classList.add('loading');
  content.rawText = '';
  content.hasError = false;
  messages.appendChild(li);
  messages.scrollTop = messages.scrollHeight;
  return { li, content };
}

function processFrame(frame, assistant, token = selectionToken) {
  if (!isCurrentSelection(token)) return;
  const lines = frame.split('\n');
  let eventName = null;
  let dataValue = null;
  lines.forEach((line) => {
    if (line.startsWith('event: ')) eventName = line.slice(7);
    if (line.startsWith('data: ')) dataValue = line.slice(6);
  });

  if (eventName === 'history_status' && dataValue === 'degraded') {
    setHistoryBannerVisible(true);
    return;
  }
  if (eventName === 'error') {
    assistant.li.classList.remove('loading');
    assistant.content.hasError = true;
    assistant.content.textContent = dataValue || FALLBACK_ERROR;
    if (dataValue === EXERCISE_PROGRESS_ERROR) setExerciseProgressError();
    return;
  }
  if (eventName === 'user_message_id' || eventName === 'assistant_message_id') return;
  if (dataValue === '[DONE]') {
    assistant.li.classList.remove('loading');
    if (assistant.content.hasError) return;
    assistant.content.innerHTML = renderAssistantMarkdown(assistant.content.rawText);
    return;
  }
  if (assistant.content.hasError) return;
  if (dataValue !== null) {
    assistant.li.classList.remove('loading');
    assistant.content.rawText += dataValue;
    assistant.content.textContent += dataValue;
  }
}

async function sendMessage(query) {
  const token = selectionToken;
  let completedRejected = false;
  setChatEnabled(false);
  clearHint();
  appendUserMessage(query);
  const assistant = appendAssistantPlaceholder();
  if (!assistant) return;

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, student_name: studentName, exercise_id: exercise.id }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const detail = data.detail;
      if (
        response.status === 409
        && detail?.code === EXERCISE_COMPLETED_CODE
        && detail.retryable === false
      ) {
        completedRejected = true;
        assistant.li.classList.remove('loading');
        assistant.content.hasError = true;
        assistant.content.textContent = detail.message;
        setChatEnabled(false);
        await loadProgress(token);
        return;
      }
      throw new Error(detail?.message || detail || `HTTP ${response.status}`);
    }
    const reader = response.body?.getReader();
    if (!reader) throw new Error('Response body is null');

    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        processFrame(buffer.slice(0, boundary), assistant, token);
        buffer = buffer.slice(boundary + 2);
      }
    }
    buffer += decoder.decode();
    if (buffer) processFrame(buffer, assistant, token);
  } catch (error) {
    if (isCurrentSelection(token)) {
      assistant.li.classList.remove('loading');
      if (!assistant.content.hasError) assistant.content.textContent = FALLBACK_ERROR;
    }
  } finally {
    if (isCurrentSelection(token)) {
      if (!completedRejected) setChatEnabled(true);
      input.focus();
    }
  }
}

function showCheckpointFeedback(result, feedback) {
  if (!checkpointFeedback) return;
  checkpointFeedback.hidden = false;
  checkpointFeedback.className = `checkpoint-feedback checkpoint-feedback--${result}`;
  checkpointFeedback.textContent = feedback;
}

const SVG_NS = 'http://www.w3.org/2000/svg';

function createSvgElement(tag, attributes = {}) {
  const element = document.createElementNS(SVG_NS, tag);
  Object.entries(attributes).forEach(([name, value]) => {
    element.setAttribute(name, String(value));
  });
  return element;
}

function appendSvgText(svg, text, attributes) {
  const element = createSvgElement('text', attributes);
  element.textContent = text;
  svg.appendChild(element);
}

function renderGraphCard(option) {
  const descriptor = option.graph;
  if (!descriptor || !['polyline', 'curve'].includes(descriptor.kind)) return null;
  const bounds = [
    descriptor.x_min,
    descriptor.x_max,
    descriptor.y_min,
    descriptor.y_max,
  ];
  if (
    bounds.some((value) => !Number.isFinite(value))
    || descriptor.x_max <= descriptor.x_min
    || descriptor.y_max <= descriptor.y_min
    || !Array.isArray(descriptor.points)
    || descriptor.points.length < 2
  ) return null;

  const points = descriptor.points.map((point) => {
    if (!Array.isArray(point) || point.length !== 2) return null;
    const [x, y] = point;
    return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null;
  });
  if (points.some((point) => point === null)) return null;

  const width = 240;
  const height = 160;
  const left = 32;
  const right = 228;
  const top = 12;
  const bottom = 130;
  const xFor = (value) => left + ((value - descriptor.x_min) / (descriptor.x_max - descriptor.x_min)) * (right - left);
  const yFor = (value) => bottom - ((value - descriptor.y_min) / (descriptor.y_max - descriptor.y_min)) * (bottom - top);
  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const svg = createSvgElement('svg', {
    viewBox: `0 0 ${width} ${height}`,
    role: 'img',
    'aria-label': `${option.label}: ${descriptor.y_label} en función de ${descriptor.x_label}`,
  });
  svg.classList.add('checkpoint-graph-svg');

  const grid = createSvgElement('g', { class: 'checkpoint-graph-grid' });
  [descriptor.x_min, (descriptor.x_min + descriptor.x_max) / 2, descriptor.x_max].forEach((value) => {
    grid.appendChild(createSvgElement('line', {
      x1: xFor(value), y1: top, x2: xFor(value), y2: bottom,
    }));
  });
  [descriptor.y_min, (descriptor.y_min + descriptor.y_max) / 2, descriptor.y_max].forEach((value) => {
    grid.appendChild(createSvgElement('line', {
      x1: left, y1: yFor(value), x2: right, y2: yFor(value),
    }));
  });
  svg.appendChild(grid);

  const axes = createSvgElement('g', { class: 'checkpoint-graph-axes' });
  const xAxisY = yFor(clamp(0, descriptor.y_min, descriptor.y_max));
  const yAxisX = xFor(clamp(0, descriptor.x_min, descriptor.x_max));
  axes.appendChild(createSvgElement('line', { x1: left, y1: xAxisY, x2: right, y2: xAxisY }));
  axes.appendChild(createSvgElement('line', { x1: yAxisX, y1: top, x2: yAxisX, y2: bottom }));
  svg.appendChild(axes);

  const coordinates = points.map((point) => ({ x: xFor(point.x), y: yFor(point.y) }));
  if (descriptor.kind === 'curve' && coordinates.length >= 4) {
    let pathData = `M ${coordinates[0].x} ${coordinates[0].y}`;
    let index = 1;
    for (; index + 2 < coordinates.length; index += 3) {
      pathData += ` C ${coordinates[index].x} ${coordinates[index].y}, ${coordinates[index + 1].x} ${coordinates[index + 1].y}, ${coordinates[index + 2].x} ${coordinates[index + 2].y}`;
    }
    for (; index < coordinates.length; index += 1) {
      pathData += ` L ${coordinates[index].x} ${coordinates[index].y}`;
    }
    svg.appendChild(createSvgElement('path', { d: pathData, class: 'checkpoint-graph-line' }));
  } else {
    svg.appendChild(createSvgElement('polyline', {
      points: coordinates.map((point) => `${point.x},${point.y}`).join(' '),
      class: 'checkpoint-graph-line',
    }));
  }

  [descriptor.x_min, (descriptor.x_min + descriptor.x_max) / 2, descriptor.x_max].forEach((value) => {
    appendSvgText(svg, String(value), { x: xFor(value), y: bottom + 17, class: 'checkpoint-graph-label', 'text-anchor': 'middle' });
  });
  appendSvgText(svg, descriptor.x_label, { x: right, y: height - 2, class: 'checkpoint-graph-axis-label', 'text-anchor': 'end' });
  appendSvgText(svg, descriptor.y_label, { x: 4, y: top + 2, class: 'checkpoint-graph-axis-label' });
  return svg;
}

function updateCheckpointButtons() {
  if (!checkpointOptions) return;
  checkpointOptions.querySelectorAll('button').forEach((button) => {
    const selected = selectedOptionIds.has(button.dataset.optionId);
    button.classList.toggle('is-selected', selected);
    button.setAttribute('aria-pressed', String(selected));
    button.disabled = checkpointBusy;
  });
  if (checkpointSubmit) {
    checkpointSubmit.disabled = checkpointBusy || selectedOptionIds.size === 0;
  }
  if (checkpointHint) checkpointHint.disabled = checkpointBusy;
  if (checkpointHelp) checkpointHelp.disabled = checkpointBusy;
}

function renderExerciseReview(review) {
  if (!exerciseReview || !exerciseReviewList) return;
  exerciseReviewList.replaceChildren();
  const entries = Array.isArray(review) ? review : [];
  entries.forEach((entry) => {
    const item = document.createElement('li');
    item.className = 'exercise-review-item';
    const question = document.createElement('p');
    question.className = 'exercise-review-question';
    question.textContent = entry.question;
    item.appendChild(question);
    const label = document.createElement('span');
    label.className = 'exercise-review-role';
    label.textContent = 'Respuesta correcta';
    item.appendChild(label);
    const answers = document.createElement('ul');
    answers.className = 'exercise-review-answers';
    (Array.isArray(entry.correct_answers) ? entry.correct_answers : []).forEach((answer) => {
      const answerItem = document.createElement('li');
      answerItem.textContent = answer.label;
      answers.appendChild(answerItem);
    });
    item.appendChild(answers);
    exerciseReviewList.appendChild(item);
  });
  if (entries.length === 0) {
    const empty = document.createElement('li');
    empty.className = 'exercise-review-empty';
    empty.textContent = 'No hay respuestas para repasar.';
    exerciseReviewList.appendChild(empty);
  }
  exerciseReview.hidden = false;
}

function renderCheckpoint(state) {
  if (!checkpointPanel || !state) return;
  progressState = state;
  selectedOptionIds = new Set();
  checkpointPanel.hidden = false;
  const current = state.current_checkpoint;
  const completed = Boolean(state.complete);
  checkpointProgress.textContent = completed
    ? 'Ejercicio completo'
    : `Checkpoint ${state.current_index + 1} de ${state.total}`;
  if (checkpointPart) {
    checkpointPart.hidden = completed;
    checkpointPart.textContent = completed ? '' : `Parte ${current.part}`;
  }
  progressBar.style.width = `${(state.completed_count / state.total) * 100}%`;
  checkpointPrompt.textContent = completed
    ? '¡Muy bien! Completaste el ejercicio.'
    : current.prompt;
  checkpointOptions.replaceChildren();
  if (completed) {
    renderExerciseReview(state.completed_review);
    checkpointFeedback.hidden = false;
    checkpointFeedback.className = 'checkpoint-feedback checkpoint-feedback--correct';
    checkpointFeedback.textContent = 'Verificá tus resultados en los apuntes de la cátedra.';
    checkpointSubmit.hidden = true;
    checkpointHint.hidden = true;
    checkpointHelp.hidden = true;
    setChatEnabled(false);
    return;
  }

  if (exerciseReview) exerciseReview.hidden = true;
  if (exerciseReviewList) exerciseReviewList.replaceChildren();

  checkpointSubmit.hidden = false;
  checkpointHint.hidden = false;
  checkpointHelp.hidden = false;
   current.options.forEach((option) => {
     const button = document.createElement('button');
     button.type = 'button';
     button.className = 'checkpoint-option';
     const graph = current.presentation === 'graph' ? renderGraphCard(option) : null;
     if (graph) {
       button.classList.add('checkpoint-option--graph');
       button.setAttribute('aria-label', option.label);
       const graphWrapper = document.createElement('span');
       graphWrapper.className = 'checkpoint-graph';
       graphWrapper.appendChild(graph);
       button.appendChild(graphWrapper);
       const graphLabel = document.createElement('span');
       graphLabel.className = 'checkpoint-graph-option-label';
       graphLabel.textContent = option.label;
       button.appendChild(graphLabel);
     } else {
       button.textContent = option.label;
     }
     button.dataset.optionId = option.id;
    button.setAttribute('aria-pressed', 'false');
    button.addEventListener('click', () => {
      if (current.input_type === 'single_choice') selectedOptionIds.clear();
      if (selectedOptionIds.has(option.id)) selectedOptionIds.delete(option.id);
      else selectedOptionIds.add(option.id);
      updateCheckpointButtons();
    });
    checkpointOptions.appendChild(button);
  });
  updateCheckpointButtons();
}

async function submitCheckpoint(action = 'answer') {
  if (!progressState?.current_checkpoint || checkpointBusy) return;
  const token = selectionToken;
  checkpointBusy = true;
  updateCheckpointButtons();
  try {
    const response = await fetch(`/api/exercises/${encodeURIComponent(exercise.id)}/checkpoint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_name: studentName,
        checkpoint_id: progressState.current_checkpoint.id,
        answer_ids: action === 'answer' ? Array.from(selectedOptionIds) : [],
        action,
      }),
    });
    const data = await response.json();
    if (!isCurrentSelection(token)) return;
    if (!response.ok) {
      if (data.detail?.progress) renderCheckpoint(data.detail.progress);
      if (response.status === 503 && data.detail?.retryable) {
        setExerciseProgressError(data.detail.message || EXERCISE_PROGRESS_ERROR);
        return;
      }
      throw new Error(data.detail?.message || data.detail || `HTTP ${response.status}`);
    }
    showCheckpointFeedback(data.result, data.feedback);
    if (data.progress) renderCheckpoint(data.progress);
  } catch (error) {
    if (isCurrentSelection(token)) showHint(error.message || FALLBACK_ERROR);
  } finally {
    if (isCurrentSelection(token)) {
      checkpointBusy = false;
      updateCheckpointButtons();
    }
  }
}

async function loadExercise() {
  if (exerciseCatalog.length > 0) return exercise;
  try {
    const response = await fetch('/api/exercises');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const exercises = await response.json();
    if (!Array.isArray(exercises) || exercises.length === 0) throw new Error('No exercises found');
    exerciseCatalog = exercises;
    renderExerciseCatalog();
    await selectExercise(exerciseCatalog[0], { loadState: false });
    return exercise;
  } catch (error) {
    exerciseStatus.textContent = 'No se pudo cargar el ejercicio.';
    throw error;
  }
}

function renderExerciseCatalog() {
  if (!exerciseList) return;
  exerciseList.replaceChildren();
  exerciseCatalog.forEach((item) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'exercise-list-item';
    button.dataset.exerciseId = item.id;
    button.textContent = item.title;
    button.setAttribute('aria-pressed', String(item.id === exercise?.id));
    button.addEventListener('click', () => { void selectExercise(item); });
    exerciseList.appendChild(button);
  });
}

function renderExerciseDetails(selectedExercise) {
  exerciseTitle.textContent = selectedExercise.title;
  exerciseStatement.textContent = selectedExercise.statement;
  exerciseGraph.src = selectedExercise.graph_asset;
  exerciseGraph.hidden = false;
  starterIdeas.replaceChildren();
  selectedExercise.starter_ideas.forEach((idea) => {
    const item = document.createElement('li');
    item.textContent = idea;
    starterIdeas.appendChild(item);
  });
  exerciseStatus.textContent = '';
}

function resetSelectedExerciseState() {
  progressState = null;
  exerciseHistory = [];
  selectedOptionIds = new Set();
  checkpointBusy = false;
  if (messages) messages.replaceChildren();
  if (checkpointPanel) checkpointPanel.hidden = true;
  if (checkpointOptions) checkpointOptions.replaceChildren();
  if (checkpointFeedback) {
    checkpointFeedback.hidden = true;
    checkpointFeedback.textContent = '';
  }
  if (exerciseReview) exerciseReview.hidden = true;
  if (exerciseReviewList) exerciseReviewList.replaceChildren();
  setHistoryBannerVisible(false);
}

function isCurrentSelection(token) {
  return token === selectionToken;
}

async function selectExercise(selectedExercise, { loadState = true } = {}) {
  if (!selectedExercise) return;
  selectionToken += 1;
  const token = selectionToken;
  exercise = selectedExercise;
  resetSelectedExerciseState();
  renderExerciseCatalog();
  renderExerciseDetails(selectedExercise);
  setChatEnabled(false);
  closeMobileMenu(false);
  if (loadState && studentName) await loadSelectedStudentState(token);
}

async function loadProgress(token = selectionToken) {
  if (!exercise || !checkpointPanel) return;
  const params = new URLSearchParams({ student_name: studentName });
  const response = await fetch(`/api/exercises/${encodeURIComponent(exercise.id)}/progress?${params}`);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  if (!isCurrentSelection(token)) return;
  clearExerciseProgressError();
  renderCheckpoint(data);
}

async function loadHistory(token = selectionToken) {
  if (messages) messages.replaceChildren();
  try {
    const params = new URLSearchParams({ student_name: studentName, exercise_id: exercise.id });
    const response = await fetch(`/history?${params}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!isCurrentSelection(token)) return;
    setHistoryBannerVisible(Boolean(data.degraded));
    exerciseHistory = Array.isArray(data.messages) ? data.messages : [];
  } catch (error) {
    if (!isCurrentSelection(token)) return;
    exerciseHistory = [];
    showHint('No se pudo cargar el historial');
  }
}

async function loadSelectedStudentState(token = selectionToken) {
  await loadHistory(token);
  if (!isCurrentSelection(token)) return false;
  try {
    await loadProgress(token);
  } catch (error) {
    if (!isCurrentSelection(token)) return false;
    setExerciseProgressError(error.message || EXERCISE_PROGRESS_ERROR);
    return false;
  }
  if (!isCurrentSelection(token)) return false;
  setChatEnabled(true);
  return true;
}

async function startChat(name) {
  studentName = name;
  localStorage.setItem(STORAGE_KEY, name);
  loginScreen.hidden = true;
  appShell.hidden = false;
  clearHint();
  setChatEnabled(false);
  await loadExercise();
  const progressLoaded = await loadSelectedStudentState(selectionToken);
  if (progressLoaded) input.focus();
}

async function retryProgress() {
  if (!exercise || !studentName) return;
  if (exerciseStatus) exerciseStatus.textContent = 'Reintentando cargar tu progreso...';
  if (exerciseRetry) exerciseRetry.hidden = true;
  setChatEnabled(false);
  try {
    await loadProgress(selectionToken);
    if (!progressState) return;
    setChatEnabled(true);
    input.focus();
  } catch (error) {
    setExerciseProgressError(error.message || EXERCISE_PROGRESS_ERROR);
  }
}

function setSidebarInteractive(isOpen) {
  const isMobile = window.matchMedia?.('(max-width: 768px)').matches ?? false;
  sidebar.inert = isMobile && !isOpen;
}

function closeMobileMenu(restoreFocus = true) {
  const wasOpen = sidebar.classList.contains('is-open');
  sidebar.classList.remove('is-open');
  mobileMenuToggle.setAttribute('aria-expanded', 'false');
  mobileMenuToggle.setAttribute('aria-label', 'Abrir menú');
  setSidebarInteractive(false);
  if (restoreFocus && wasOpen) mobileMenuToggle.focus();
}

function toggleMobileMenu() {
  if (sidebar.classList.contains('is-open')) {
    closeMobileMenu();
    return;
  }
  sidebar.classList.add('is-open');
  sidebar.inert = false;
  mobileMenuToggle.setAttribute('aria-expanded', 'true');
  mobileMenuToggle.setAttribute('aria-label', 'Cerrar menú');
  mobileMenuClose.focus();
}

nameArea.addEventListener('submit', (event) => {
  event.preventDefault();
  const name = nameInput.value.trim();
  if (!name) {
    showHint('Escribí tu nombre para empezar');
    return;
  }
  startChat(name);
});

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const query = input.value.trim();
  if (!query) {
    showHint('Escribí una observación si querés usar este campo');
    return;
  }
  if (query.length > MAX_CHARS) {
    showHint('Máximo 500 caracteres');
    return;
  }
  input.value = '';
  sendMessage(query);
});

if (checkpointSubmit) checkpointSubmit.addEventListener('click', () => submitCheckpoint());
if (checkpointHint) checkpointHint.addEventListener('click', () => submitCheckpoint('hint'));
if (checkpointHelp) checkpointHelp.addEventListener('click', () => submitCheckpoint('help'));
if (exerciseRetry) exerciseRetry.addEventListener('click', retryProgress);
mobileMenuToggle.addEventListener('click', toggleMobileMenu);
mobileMenuClose.addEventListener('click', () => closeMobileMenu());
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && sidebar.classList.contains('is-open')) closeMobileMenu();
});
window.addEventListener('resize', () => setSidebarInteractive(sidebar.classList.contains('is-open')));

setSidebarInteractive(false);
async function initializeExercisePage() {
  try {
    await loadExercise();
    if (studentName) await startChat(studentName);
    else setChatEnabled(false);
  } catch (error) {
    setChatEnabled(false);
  }
}

initializeExercisePage();
