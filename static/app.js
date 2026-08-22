const form = document.getElementById('upload-form');
const submitBtn = document.getElementById('submit');
const resetBtn = document.getElementById('reset');
const statusEl = document.getElementById('status');
const errorEl = document.getElementById('error');
const summaryEl = document.getElementById('summary');
const resultsEl = document.getElementById('results');

const ЦВЕТА = {
  equal: '#9aa3b5',
  changed: '#e8a33d',
  removed: '#e05a4e',
  added: '#3aa76d',
  old: '#e05a4e',
  new: '#3aa76d',
};

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

function число(значение) {
  return значение.toLocaleString('ru-RU');
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
  statusEl.textContent = 'Сравнение…';
  hideError();

  try {
    const response = await fetch('/api/upload', { method: 'POST', body: data });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || 'Не удалось обработать документы');
    }

    render(payload.documents, payload.diff);
    statusEl.textContent = 'Готово';
  } catch (err) {
    summaryEl.hidden = true;
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
  summaryEl.hidden = true;
  summaryEl.innerHTML = '';
  resultsEl.hidden = true;
  resultsEl.innerHTML = '';
  statusEl.textContent = '';
  hideError();
});

// --- отрисовка ------------------------------------------------------

function render(documents, diff) {
  renderSummary(documents, diff);
  renderPanes(documents, diff);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function svg(tag, attrs) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs).forEach(([ключ, значение]) => node.setAttribute(ключ, значение));
  return node;
}

function svgТекст(attrs, текст) {
  const node = svg('text', attrs);
  node.textContent = текст;
  return node;
}

function renderSummary(documents, diff) {
  const [старый, новый] = documents;
  const s = diff.stats;

  summaryEl.innerHTML = '';

  const шапка = el('div', 'summary__head');
  шапка.append(el('h2', null, 'Что изменилось'));
  шапка.append(el('span', 'similarity', `совпадение ${Math.round(s.similarity * 100)}%`));
  summaryEl.append(шапка);

  const метки = el('div', 'chips');
  [
    ['equal', s.equal, 'без изменений'],
    ['changed', s.changed, 'изменено'],
    ['removed', s.removed, 'удалено'],
    ['added', s.added, 'добавлено'],
  ].forEach(([вид, значение, подпись]) => {
    const метка = el('span', `chip chip--${вид}`);
    метка.append(el('b', null, число(значение)));
    метка.append(document.createTextNode(` ${подпись}`));
    метки.append(метка);
  });

  метки.append(el('span', 'chip chip--words',
    `слов: −${число(s.words_removed)} / +${число(s.words_added)}`));
  summaryEl.append(метки);

  const диаграммы = el('div', 'charts');
  диаграммы.append(диаграммаСостава(s));
  диаграммы.append(диаграммаМетрик(старый, новый));
  summaryEl.append(диаграммы);

  summaryEl.hidden = false;
}

/** Полоса: из чего состоит документ после сравнения. */
function диаграммаСостава(s) {
  const карточка = el('figure', 'chart');
  карточка.append(el('figcaption', 'chart__title', 'Состав абзацев'));

  const данные = [
    ['equal', s.equal, 'без изменений'],
    ['changed', s.changed, 'изменено'],
    ['removed', s.removed, 'удалено'],
    ['added', s.added, 'добавлено'],
  ];

  const всего = данные.reduce((сумма, [, значение]) => сумма + значение, 0);

  const Ш = 560;
  const рисунок = svg('svg', { viewBox: `0 0 ${Ш} 124`, class: 'chart__svg', role: 'img' });

  if (!всего) {
    рисунок.append(svgТекст(
      { x: Ш / 2, y: 40, 'text-anchor': 'middle', fill: '#6b7387', 'font-size': 14 },
      'нет абзацев для сравнения',
    ));
    карточка.append(рисунок);
    return карточка;
  }

  let x = 0;
  данные.filter(([, значение]) => значение > 0).forEach(([вид, значение]) => {
    const ширина = (значение / всего) * Ш;

    рисунок.append(svg('rect', {
      x, y: 8, width: Math.max(ширина, 2), height: 42, fill: ЦВЕТА[вид], rx: 3,
    }));

    if (ширина > 34) {
      рисунок.append(svgТекст({
        x: x + ширина / 2, y: 35, 'text-anchor': 'middle',
        fill: '#ffffff', 'font-size': 14, 'font-weight': 600,
      }, число(значение)));
    }

    x += ширина;
  });

  данные.forEach(([вид, значение, подпись], индекс) => {
    const y = 78 + Math.floor(индекс / 2) * 24;
    const x0 = (индекс % 2) * 285;

    рисунок.append(svg('rect', { x: x0, y: y - 11, width: 12, height: 12, fill: ЦВЕТА[вид], rx: 3 }));
    рисунок.append(svgТекст(
      { x: x0 + 20, y, fill: '#4a5265', 'font-size': 13 },
      `${подпись} — ${число(значение)}`,
    ));
  });

  карточка.append(рисунок);
  return карточка;
}

/** Парные столбцы: старая версия против новой по основным показателям. */
function диаграммаМетрик(старый, новый) {
  const карточка = el('figure', 'chart');
  карточка.append(el('figcaption', 'chart__title', 'Старая и новая версия в цифрах'));

  const метрики = [
    ['слова', старый.word_count, новый.word_count],
    ['символы', старый.char_count, новый.char_count],
    ['абзацы', старый.paragraph_count, новый.paragraph_count],
    ['таблицы', старый.table_count, новый.table_count],
  ];

  const Ш = 560;
  const низ = 124;
  const максВысота = 92;
  const шаг = Ш / метрики.length;

  const рисунок = svg('svg', { viewBox: `0 0 ${Ш} 180`, class: 'chart__svg', role: 'img' });
  рисунок.append(svg('line', { x1: 0, y1: низ, x2: Ш, y2: низ, stroke: '#dfe3ea' }));

  метрики.forEach(([подпись, было, стало], индекс) => {
    const максимум = Math.max(было, стало, 1);
    const центр = индекс * шаг + шаг / 2;

    [[было, ЦВЕТА.old, -30], [стало, ЦВЕТА.new, 4]].forEach(([значение, цвет, сдвиг]) => {
      const высота = значение > 0 ? Math.max((значение / максимум) * максВысота, 2) : 0;
      const x = центр + сдвиг;

      if (высота) {
        рисунок.append(svg('rect', {
          x, y: низ - высота, width: 26, height: высота, fill: цвет, rx: 3,
        }));
      }

      рисунок.append(svgТекст(
        { x: x + 13, y: низ - высота - 6, 'text-anchor': 'middle', fill: '#4a5265', 'font-size': 12 },
        число(значение),
      ));
    });

    рисунок.append(svgТекст(
      { x: центр, y: низ + 18, 'text-anchor': 'middle', fill: '#4a5265', 'font-size': 13 },
      подпись,
    ));
  });

  [['старая версия', ЦВЕТА.old, 140], ['новая версия', ЦВЕТА.new, 310]].forEach(([подпись, цвет, x]) => {
    рисунок.append(svg('rect', { x, y: низ + 34, width: 12, height: 12, fill: цвет, rx: 3 }));
    рисунок.append(svgТекст({ x: x + 20, y: низ + 45, fill: '#4a5265', 'font-size': 13 }, подпись));
  });

  карточка.append(рисунок);
  return карточка;
}

function renderPanes(documents, diff) {
  const [старый, новый] = documents;

  resultsEl.innerHTML = '';

  const сетка = el('div', 'diff');
  сетка.append(заголовокПанели(старый, 'old', 'Старая версия', 'красным — то, чего нет в новой версии'));
  сетка.append(заголовокПанели(новый, 'new', 'Новая версия', 'зелёным — то, что появилось или изменилось'));

  if (!diff.rows.length) {
    const пусто = el('p', 'diff__empty', 'Оба документа не содержат текста');
    сетка.append(пусто);
  }

  diff.rows.forEach((строка) => {
    сетка.append(ячейка(строка.left, 'old'));
    сетка.append(ячейка(строка.right, 'new'));
  });

  resultsEl.append(сетка);
  resultsEl.hidden = false;
}

function заголовокПанели(документ, сторона, титул, пояснение) {
  const шапка = el('header', `pane__head pane__head--${сторона}`);
  шапка.append(el('span', 'pane__badge', титул));
  шапка.append(el('h2', null, документ.filename));

  const мета = [
    formatSize(документ.size_bytes),
    `${число(документ.word_count)} слов`,
    документ.author ? `автор: ${документ.author}` : null,
    документ.modified ? `изменён: ${документ.modified.slice(0, 10)}` : null,
  ].filter(Boolean).join(' · ');

  шапка.append(el('p', 'pane__meta', мета));
  шапка.append(el('p', 'pane__hint', пояснение));
  return шапка;
}

function ячейка(блок, сторона) {
  if (!блок) {
    return el('div', `row row--${сторона} row--empty`);
  }

  const узел = el('div', `row row--${сторона} row--${блок.kind}`);

  блок.parts.forEach((часть) => {
    if (часть.changed) {
      узел.append(el('mark', `mark mark--${сторона}`, часть.text));
    } else {
      узел.append(document.createTextNode(часть.text));
    }
  });

  return узел;
}

form.addEventListener('submit', (e) => e.preventDefault());
