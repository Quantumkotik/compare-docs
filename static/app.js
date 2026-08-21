const form = document.getElementById('upload-form');
const submit = document.getElementById('submit');
const errorBox = document.getElementById('error');
const results = document.getElementById('results');
const drops = Array.from(document.querySelectorAll('.drop'));

function refreshSubmit() {
    submit.disabled = drops.some((drop) => !drop.querySelector('input').files.length);
}

function showFile(drop, file) {
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

function renderResults(documents) {
    results.innerHTML = '';
    documents.forEach((doc, index) => {
        const card = document.createElement('article');
        card.className = 'card';

        const title = document.createElement('h2');
        title.textContent = `Документ ${index + 1}: ${doc.filename}`;
        card.append(title);

        const dl = document.createElement('dl');
        const rows = [
            ['Размер', formatSize(doc.size)],
            ['Абзацев', doc.paragraphs],
            ['Таблиц', doc.tables],
            ['Слов', doc.words],
            ['Символов', doc.characters],
        ];
        rows.forEach(([label, value]) => {
            const dt = document.createElement('dt');
            dt.textContent = label;
            const dd = document.createElement('dd');
            dd.textContent = value;
            dl.append(dt, dd);
        });
        card.append(dl);

        const preview = document.createElement('pre');
        preview.className = 'preview';
        preview.textContent = doc.preview || 'Документ не содержит текста';
        card.append(preview);

        results.append(card);
    });
    results.hidden = false;
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    hideError();
    results.hidden = true;
    submit.disabled = true;
    submit.textContent = 'Загрузка…';

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: new FormData(form),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Не удалось загрузить документы');
        }
        renderResults(data.documents);
    } catch (err) {
        showError(err.message);
    } finally {
        submit.textContent = 'Загрузить';
        refreshSubmit();
    }
});

refreshSubmit();
