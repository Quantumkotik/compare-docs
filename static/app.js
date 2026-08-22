// Версия фронтенда. Видна в консоли браузера — по ней сразу понятно,
// выполняется свежий файл или старый из кеша.
const APP_VERSION = 2;
const API_URL = '/api/compare';

const log = (...args) => console.log(`[compare-docs v${APP_VERSION}]`, ...args);

log('скрипт загружен, эндпоинт:', API_URL);

const form = document.getElementById('upload-form');
const submit = document.getElementById('submit');
const errorBox = document.getElementById('error');
const results = document.getElementById('results');
const diffBody = document.getElementById('diff-body');
const drops = Array.from(document.querySelectorAll('.drop'));

function refreshSubmit() {
    submit.disabled = drops.some((drop) => !drop.querySelector('input').files.length);
}

function showFile(drop, file) {
    log('выбран файл:', file ? `${file.name} (${file.size} байт)` : 'нет');
    drop.classList.toggle('is-filled', Boolean(file));
    drop.querySelector('.drop__file').textContent = file ? file.name : '';
    refreshSubmit();
}

drops.forEach((drop) => {
    const input = drop.querySelector('input');

    input.addEventListener('change', () => showFile(drop, input.files[0]));

    ['dragenter', 'dragover'].forEach((type) => {
        drop.addEventListener(type, (event) => {
            event.preventDefault();
            drop.classList.add('is-dragover');
        });
    });

    ['dragleave', 'drop'].forEach((type) => {
        drop.addEventListener(type, () => drop.classList.remove('is-dragover'));
    });

    drop.addEventListener('drop', (event) => {
        event.preventDefault();
        const file = event.dataTransfer.files[0];
        if (!file) return;
        if (!file.name.toLowerCase().endsWith('.docx')) {
            showError(`Файл «${file.name}» не является документом .docx`);
            return;
        }
        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;
        showFile(drop, file);
    });
});

function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
}

function hideError() {
    errorBox.hidden = true;
}

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} Б`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
    return `${(bytes / 1024 / 1024).toFixed(1)} МБ`;
}

/** Строит ячейку одной стороны diff: номер строки и подсвеченный текст. */
function buildCell(side, column) {
    const cell = document.createElement('div');
    cell.className = `cell cell--${column}`;

    if (!side) {
        cell.classList.add('cell--empty');
        return cell;
    }

    // Строку красим только если на этой стороне действительно что-то изменилось:
    // при чистой вставке слева нечему быть красным, и наоборот.
    const hasChanges = side.parts.some((part) => part.changed);
    cell.classList.add(`cell--${hasChanges ? side.type : 'equal'}`);

    const number = document.createElement('span');
    number.className = 'cell__number';
    number.textContent = side.number;

    const text = document.createElement('span');
    text.className = 'cell__text';
    side.parts.forEach((part) => {
        if (!part.changed) {
            text.append(document.createTextNode(part.text));
            return;
        }
        const mark = document.createElement('span');
        mark.className = column === 'old' ? 'word--removed' : 'word--added';
        mark.textContent = part.text;
        text.append(mark);
    });

    cell.append(number, text);
    return cell;
}

function renderDiff(data) {
    document.getElementById('old-name').textContent = data.old.filename;
    document.getElementById('old-stats').textContent =
        `${formatSize(data.old.size)} · строк: ${data.old.lines} · слов: ${data.old.words}`;
    document.getElementById('new-name').textContent = data.new.filename;
    document.getElementById('new-stats').textContent =
        `${formatSize(data.new.size)} · строк: ${data.new.lines} · слов: ${data.new.words}`;

    document.getElementById('count-removed').textContent = data.summary.removed;
    document.getElementById('count-added').textContent = data.summary.added;
    document.getElementById('count-changed').textContent = data.summary.changed;
    document.getElementById('count-unchanged').textContent = data.summary.unchanged;

    diffBody.innerHTML = '';
    const fragment = document.createDocumentFragment();
    data.rows.forEach((row) => {
        fragment.append(buildCell(row.old, 'old'), buildCell(row.new, 'new'));
    });
    diffBody.append(fragment);

    results.hidden = false;
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    hideError();
    results.hidden = true;
    submit.disabled = true;
    submit.textContent = 'Сравниваю…';

    const started = performance.now();
    try {
        log('шаг 1: отправляю файлы на', API_URL);
        const response = await fetch(API_URL, {
            method: 'POST',
            body: new FormData(form),
        });
        log('шаг 2: ответ', response.status, response.statusText,
            `за ${(performance.now() - started).toFixed(0)} мс`);

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Не удалось сравнить документы');
        }

        log('шаг 3: получено строк diff:', data.rows.length, 'сводка:', data.summary);
        renderDiff(data);
        log('шаг 4: результат отрисован');
    } catch (err) {
        console.error(`[compare-docs v${APP_VERSION}] ошибка:`, err);
        showError(err.message);
    } finally {
        submit.textContent = 'Сравнить';
        refreshSubmit();
    }
});

refreshSubmit();
