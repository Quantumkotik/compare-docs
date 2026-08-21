const form = document.getElementById('upload-form');
const submitBtn = document.getElementById('submit');
const resetBtn = document.getElementById('reset');
const statusEl = document.getElementById('status');
const errorEl = document.getElementById('error');
const resultsEl = document.getElementById('results');

const slots = {};

document.querySelectorAll('.drop').forEach((drop) => {
  const name = drop.dataset.slot;
  const input = drop.querySelector('input[type=file]');
  const fileEl = drop.querySelector('.drop__file');
  const clearBtn = drop.querySelector('.drop__clear');

  slots[name] = { drop, input, fileEl, clearBtn, file: null };

  input.addEventListener('change', () => setFile(name, input.files[0] || null));

  drop.addEventListener('dragover', (e) => {
    e.preventDefault();
    drop.classList.add('is-over');
  });

  drop.addEventListener('dragleave', () => drop.classList.remove('is-over'));

  drop.addEventListener('drop', (e) => {
    e.preventDefault();
    drop.classList.remove('is-over');
    setFile(name, e.dataTransfer.files[0] || null);
  });

  clearBtn.addEventListener('click', (e) => {
    e.preventDefault();
    setFile(name, null);
  });
});

function setFile(name, file) {
  const slot = slots[name];

  if (file && !file.name.toLowerCase().endsWith('.docx')) {
    showError(`«${file.name}»: поддерживаются только файлы .docx`);
    return;
  }

  slot.file = file;
  slot.input.value = '';
  slot.fileEl.textContent = file ? `${file.name} · ${formatSize(file.size)}` : '';
  slot.drop.classList.toggle('is-filled', Boolean(file));
  slot.clearBtn.hidden = !file;

  hideError();
  submitBtn.disabled = !(slots.first.file && slots.second.file);
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`;
}

function showError(message) {
  errorEl.textContent = message;
  errorEl.hidden = false;
}

function hideError() {
  errorEl.hidden = true;
  errorEl.textContent = '';
}

submitBtn.addEventListener('click', async (e) => {
  e.preventDefault();
  if (!slots.first.file || !slots.second.file) return;

  const data = new FormData();
  data.append('first', slots.first.file);
  data.append('second', slots.second.file);

  submitBtn.disabled = true;
  statusEl.textContent = 'Загрузка…';
  hideError();

  try {
    const response = await fetch('/api/upload', { method: 'POST', body: data });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || 'Не удалось обработать документы');
    }

    render(payload.documents);
    statusEl.textContent = 'Готово';
  } catch (err) {
    resultsEl.hidden = true;
    statusEl.textContent = '';
    showError(err.message);
  } finally {
    submitBtn.disabled = false;
  }
});

resetBtn.addEventListener('click', () => {
  setFile('first', null);
  setFile('second', null);
  resultsEl.hidden = true;
  resultsEl.innerHTML = '';
  statusEl.textContent = '';
  hideError();
});

function render(documents) {
  resultsEl.innerHTML = '';

  documents.forEach((doc, index) => {
    const card = document.createElement('article');
    card.className = 'doc';

    const title = document.createElement('h2');
    title.textContent = doc.filename;
    card.append(title);

    const meta = document.createElement('p');
    meta.className = 'doc__meta';
    meta.textContent = [
      `Документ ${index + 1}`,
      formatSize(doc.size_bytes),
      doc.author ? `автор: ${doc.author}` : null,
      doc.modified ? `изменён: ${doc.modified.slice(0, 10)}` : null,
    ].filter(Boolean).join(' · ');
    card.append(meta);

    const stats = document.createElement('div');
    stats.className = 'stats';
    [
      [doc.word_count, 'слов'],
      [doc.char_count, 'символов'],
      [doc.paragraph_count, 'абзацев'],
      [doc.table_count, 'таблиц'],
      [doc.image_count, 'изображений'],
      [doc.headings.length, 'заголовков'],
    ].forEach(([value, label]) => {
      const stat = document.createElement('div');
      stat.className = 'stat';

      const v = document.createElement('div');
      v.className = 'stat__value';
      v.textContent = value.toLocaleString('ru-RU');

      const l = document.createElement('div');
      l.className = 'stat__label';
      l.textContent = label;

      stat.append(v, l);
      stats.append(stat);
    });
    card.append(stats);

    if (doc.headings.length) {
      const heading = document.createElement('h3');
      heading.textContent = 'Заголовки';
      const list = document.createElement('ul');
      list.className = 'headings';
      doc.headings.forEach((text) => {
        const li = document.createElement('li');
        li.textContent = text;
        list.append(li);
      });
      card.append(heading, list);
    }

    const previewTitle = document.createElement('h3');
    previewTitle.textContent = 'Текст документа';
    const preview = document.createElement('div');
    preview.className = 'preview';
    preview.textContent = doc.paragraphs.join('\n\n') || '(документ не содержит текста)';
    card.append(previewTitle, preview);

    resultsEl.append(card);
  });

  resultsEl.hidden = false;
}

form.addEventListener('submit', (e) => e.preventDefault());
