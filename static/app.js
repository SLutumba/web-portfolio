const $ = (selector, parent = document) => parent.querySelector(selector);
const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];
const themeToggle = $('#theme-toggle');
const themeMedia = matchMedia('(prefers-color-scheme: dark)');

function updateThemeButton() {
  const dark = document.documentElement.dataset.theme === 'dark';
  themeToggle.setAttribute('aria-label', `Switch to ${dark ? 'light' : 'dark'} theme`);
  $('use', themeToggle).setAttribute('href', dark ? '#i-sun' : '#i-moon');
  $('meta[name="theme-color"]').content = dark ? '#111a22' : '#f8fafb';
}
themeToggle.addEventListener('click', () => {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('sl-theme', next); } catch { /* Theme still works without storage. */ }
  updateThemeButton();
});
themeMedia.addEventListener('change', () => {
  let saved;
  try { saved = localStorage.getItem('sl-theme'); } catch { /* Use system preference. */ }
  if (!saved) {
    document.documentElement.dataset.theme = themeMedia.matches ? 'dark' : 'light';
    updateThemeButton();
  }
});
updateThemeButton();
$('#year').textContent = new Date().getFullYear();

const menuToggle = $('#menu-toggle');
const navLinks = $('#nav-links');
function closeMenu() {
  navLinks.classList.remove('is-open');
  menuToggle.setAttribute('aria-expanded', 'false');
  menuToggle.setAttribute('aria-label', 'Open navigation');
}
menuToggle.addEventListener('click', () => {
  const opened = navLinks.classList.toggle('is-open');
  menuToggle.setAttribute('aria-expanded', String(opened));
  menuToggle.setAttribute('aria-label', opened ? 'Close navigation' : 'Open navigation');
});
$$('a', navLinks).forEach(link => link.addEventListener('click', closeMenu));
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && navLinks.classList.contains('is-open')) { closeMenu(); menuToggle.focus(); }
});
document.addEventListener('click', event => {
  if (!event.target.closest('.nav')) closeMenu();
});
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        $$('.nav-links a').forEach(link => {
          const active = link.hash === `#${entry.target.id}`;
          link.classList.toggle('active', active);
          if (active) link.setAttribute('aria-current', 'location'); else link.removeAttribute('aria-current');
        });
      }
    });
  }, {rootMargin: '-15% 0px -65% 0px'});
  $$('main > section[id]').forEach(section => observer.observe(section));
}

const dialog = $('#demo-dialog');
const demoContent = $('#demo-content');
const editor = $('#task-editor');
const loading = $('#demo-loading');
const errorPanel = $('#demo-error');
const form = $('#task-form');
let session = null;
let tasks = [];
let filter = 'all';
let editingId = null;
let busy = false;
let toastTimer;
let editorReturnTarget = null;
let demoReturnTarget = null;

try {
  const stored = JSON.parse(sessionStorage.getItem('sl-demo') || 'null');
  if (stored && typeof stored.access_token === 'string' && Date.parse(stored.expires_at) > Date.now()) session = stored;
} catch { /* Start fresh when saved state is unavailable. */ }

function rememberSession(value) {
  session = value;
  try {
    if (value) sessionStorage.setItem('sl-demo', JSON.stringify(value));
    else sessionStorage.removeItem('sl-demo');
  } catch { /* The current page keeps the session in memory. */ }
}

function announce(message) {
  const toast = $('#toast');
  if (dialog.open) $('.demo-shell').append(toast); else document.body.append(toast);
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 4500);
}

function showError(message) {
  loading.hidden = true;
  demoContent.hidden = true;
  editor.hidden = true;
  errorPanel.hidden = false;
  $('#demo-error-text').textContent = message;
}

function showResponse(method, path, status, payload) {
  $('#request-method').textContent = method;
  $('#request-path').textContent = path;
  $('#response-code').textContent = String(status);
  $('#api-output').textContent = payload === null ? 'No content — the task was deleted.' : JSON.stringify(payload, null, 2);
}

async function api(path, { method = 'GET', data, inspect = true } = {}) {
  const headers = {'Content-Type': 'application/json'};
  if (session && path !== '/api/demo/session') headers.Authorization = `Bearer ${session.access_token}`;
  let response;
  try {
    response = await fetch(path, {method, headers, body: data === undefined ? undefined : JSON.stringify(data), signal: AbortSignal.timeout(15000)});
  } catch (error) {
    throw new Error(error.name === 'TimeoutError' ? 'The API took too long to respond. Please try again.' : 'Could not reach the API. Check your connection and try again.');
  }
  const payload = response.status === 204 ? null : await response.json().catch(() => ({error: 'The API returned an unexpected response.'}));
  if (inspect) showResponse(method, path, response.status, payload);
  if (!response.ok) {
    const message = payload?.details || payload?.error || payload?.msg || 'Something went wrong. Please try again.';
    if ([401, 422].includes(response.status) && path !== '/api/demo/session') {
      rememberSession(null);
      showError('Your demo session has ended. Start a fresh workspace to keep exploring.');
    }
    throw new Error(message);
  }
  return payload;
}

function makeIcon(id) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.classList.add('icon');
  svg.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', `#i-${id}`);
  svg.append(use);
  return svg;
}

function renderTasks() {
  const list = $('#task-list');
  list.replaceChildren();
  const visibleTasks = tasks.filter(task => filter === 'all' || (filter === 'complete' ? task.status === 'Complete' : task.status !== 'Complete'));
  for (const task of visibleTasks) {
    const row = document.createElement('div');
    row.className = `task-row${task.status === 'Complete' ? ' complete' : ''}`;
    const checkbox = document.createElement('button');
    checkbox.className = 'task-check';
    checkbox.setAttribute('aria-label', `${task.status === 'Complete' ? 'Reopen' : 'Complete'} ${task.title}`);
    checkbox.setAttribute('aria-pressed', String(task.status === 'Complete'));
    checkbox.disabled = busy;
    if (task.status === 'Complete') checkbox.append(makeIcon('check'));
    checkbox.addEventListener('click', () => changeTask(task));
    const info = document.createElement('button');
    info.className = 'task-info';
    info.setAttribute('aria-label', `Edit ${task.title}`);
    info.disabled = busy;
    const title = document.createElement('strong');
    title.textContent = task.title;
    info.append(title);
    if (task.description) { const description = document.createElement('small'); description.textContent = task.description; info.append(description); }
    const state = document.createElement('span');
    state.className = 'task-state';
    state.textContent = task.status;
    info.append(state);
    info.addEventListener('click', () => openEditor(task, info));
    const priority = document.createElement('span');
    priority.className = `priority ${['Low','Medium','High'].includes(task.priority) ? task.priority.toLowerCase() : 'medium'}`;
    priority.textContent = task.priority;
    const remove = document.createElement('button');
    remove.className = 'icon-button task-delete';
    remove.setAttribute('aria-label', `Delete ${task.title}`);
    remove.disabled = busy;
    remove.append(makeIcon('trash'));
    remove.addEventListener('click', () => removeTask(task));
    row.append(checkbox, info, priority, remove);
    list.append(row);
  }
  $('#count-all').textContent = tasks.length;
  $('#task-empty').hidden = visibleTasks.length > 0;
  $('#tasks-status').textContent = `${visibleTasks.length} ${filter === 'all' ? '' : filter + ' '}task${visibleTasks.length === 1 ? '' : 's'} shown.`;
  $('#add-task').disabled = busy;
  $('#reset-demo').disabled = busy;
}

async function loadTasks(inspect = true) {
  const response = await api('/api/tasks/', {inspect});
  if (!Array.isArray(response)) throw new Error('The API returned an unexpected task list. Please retry.');
  tasks = response;
  renderTasks();
}

async function initialiseDemo(fresh = false) {
  if (busy) return;
  busy = true;
  loading.hidden = false;
  errorPanel.hidden = true;
  demoContent.hidden = true;
  editor.hidden = true;
  try {
    if (fresh || !session || Date.parse(session.expires_at) <= Date.now()) {
      const newSession = await api('/api/demo/session', {method: 'POST', data: {}, inspect: false});
      rememberSession(newSession);
    }
    await loadTasks();
    demoContent.hidden = false;
  } catch (error) {
    showError(error.message);
  } finally {
    loading.hidden = true;
    busy = false;
    renderTasks();
  }
}

$$('[data-open-demo]').forEach(button => button.addEventListener('click', () => {
  demoReturnTarget = button;
  dialog.showModal();
  $('#close-demo').focus();
  initialiseDemo();
}));
$('#close-demo').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => {
  const rect = dialog.getBoundingClientRect();
  if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
});
dialog.addEventListener('close', () => {
  editor.hidden = true;
  $('#toast').hidden = true;
  document.body.append($('#toast'));
  demoReturnTarget?.focus();
});
$('#retry-demo').addEventListener('click', () => initialiseDemo(true));
$('#reset-demo').addEventListener('click', async () => {
  filter = 'all';
  updateFilters();
  await initialiseDemo(true);
  if (errorPanel.hidden) announce('A fresh workspace, ready to explore.');
});

function updateFilters() {
  $$('[data-filter]').forEach(button => {
    const active = button.dataset.filter === filter;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  renderTasks();
}
$$('[data-filter]').forEach(button => button.addEventListener('click', () => { filter = button.dataset.filter; updateFilters(); }));

function openEditor(task = null, target = $('#add-task')) {
  if (busy) return;
  editingId = task?.id ?? null;
  editorReturnTarget = target;
  form.reset();
  $('#editor-title').textContent = task ? 'A little fine-tuning' : 'A new task';
  $('#task-title').value = task?.title ?? '';
  $('#task-description').value = task?.description ?? '';
  $('#task-status').value = task?.status ?? 'To-Do';
  $('#task-priority').value = task?.priority ?? 'Medium';
  $('#form-error').textContent = '';
  demoContent.hidden = true;
  editor.hidden = false;
  $('#task-title').focus();
}
function closeEditor() {
  if (busy) return;
  editor.hidden = true;
  demoContent.hidden = false;
  if (editorReturnTarget?.isConnected) editorReturnTarget.focus(); else $('#add-task').focus();
}
$('#add-task').addEventListener('click', () => openEditor());
$('#cancel-editor').addEventListener('click', closeEditor);
$('#cancel-task').addEventListener('click', closeEditor);

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (busy) return;
  const title = $('#task-title').value.trim();
  if (title.length < 3) {
    $('#form-error').textContent = 'Please use at least three characters for the title.';
    $('#task-title').focus();
    return;
  }
  const payload = {title, description: $('#task-description').value.trim() || null, status: $('#task-status').value, priority: $('#task-priority').value};
  busy = true;
  $('#save-task').disabled = true;
  $('#cancel-task').disabled = true;
  $('#cancel-editor').disabled = true;
  $('#form-error').textContent = '';
  const isNew = editingId === null;
  try {
    const result = await api(isNew ? '/api/tasks/create' : `/api/tasks/${editingId}`, {method: isNew ? 'POST' : 'PATCH', data: payload});
    if (isNew) tasks.push(result); else tasks = tasks.map(task => task.id === editingId ? result : task);
    // Show the saved task even when its new state leaves the current filter.
    filter = 'all';
    busy = false;
    updateFilters();
    closeEditor();
    announce(isNew ? 'Task created.' : 'Changes saved.');
  } catch (error) {
    $('#form-error').textContent = error.message;
  } finally {
    busy = false;
    $('#save-task').disabled = false;
    $('#cancel-task').disabled = false;
    $('#cancel-editor').disabled = false;
  }
});

async function changeTask(task) {
  if (busy) return;
  busy = true;
  renderTasks();
  try {
    const updated = await api(`/api/tasks/${task.id}`, {method: 'PATCH', data: {status: task.status === 'Complete' ? 'To-Do' : 'Complete'}});
    tasks = tasks.map(item => item.id === updated.id ? updated : item);
    announce(updated.status === 'Complete' ? 'One more thing done.' : 'Task reopened.');
  } catch (error) { announce(error.message); }
  finally {
    busy = false;
    renderTasks();
    const updatedButton = $$('.task-check').find(button => button.getAttribute('aria-label').endsWith(task.title));
    (updatedButton || $('#add-task')).focus();
  }
}

async function removeTask(task) {
  if (busy) return;
  busy = true;
  renderTasks();
  try {
    await api(`/api/tasks/${task.id}`, {method: 'DELETE', data: {}});
    tasks = tasks.filter(item => item.id !== task.id);
    announce('Task deleted.');
  } catch (error) { announce(error.message); }
  finally { busy = false; renderTasks(); $('#add-task').focus(); }
}
