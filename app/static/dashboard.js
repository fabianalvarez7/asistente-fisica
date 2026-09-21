const totalQuestions = document.getElementById('total-questions');
const studentsRepresented = document.getElementById('students-represented');
const latestActivity = document.getElementById('latest-activity');
const topicCounts = document.getElementById('topic-counts');
const dashboardError = document.getElementById('dashboard-error');

function formatNumber(value) {
  return new Intl.NumberFormat('es-AR').format(value);
}

function renderTopicCounts(items) {
  topicCounts.replaceChildren();

  if (!items.length) {
    const empty = document.createElement('p');
    empty.className = 'empty-state';
    empty.textContent = 'Todavía no hay preguntas registradas.';
    topicCounts.appendChild(empty);
    return;
  }

  const maxCount = Math.max(...items.map((item) => item.count), 0);
  items.forEach((item) => {
    const row = document.createElement('div');
    row.className = 'topic-row';

    const name = document.createElement('span');
    name.className = 'topic-name';
    name.textContent = `Unidad ${item.number} — ${item.title}`;

    const bar = document.createElement('div');
    bar.className = 'topic-bar';
    bar.setAttribute('aria-hidden', 'true');
    const fill = document.createElement('div');
    fill.className = 'topic-bar-fill';
    fill.style.width = maxCount ? `${(item.count / maxCount) * 100}%` : '0%';
    bar.appendChild(fill);

    const value = document.createElement('span');
    value.className = 'topic-value';
    value.textContent = formatNumber(item.count);
    value.setAttribute('aria-label', `${formatNumber(item.count)} preguntas`);

    row.append(name, bar, value);
    topicCounts.appendChild(row);
  });
}

function renderDashboard(data) {
  totalQuestions.textContent = formatNumber(data.total_questions);
  studentsRepresented.textContent = formatNumber(data.students_represented);
  latestActivity.textContent = data.latest_activity;
  renderTopicCounts(data.topic_counts || []);
}

async function loadDashboard() {
  try {
    const response = await fetch('/api/dashboard');
    if (!response.ok) {
      throw new Error('dashboard request failed');
    }
    renderDashboard(await response.json());
  } catch (_error) {
    dashboardError.hidden = false;
    topicCounts.replaceChildren();
    const empty = document.createElement('p');
    empty.className = 'empty-state';
    empty.textContent = 'Las métricas no están disponibles por ahora.';
    topicCounts.appendChild(empty);
  }
}

loadDashboard();
