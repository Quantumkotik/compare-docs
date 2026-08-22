const form = document.getElementById("upload-form");
const submitBtn = document.getElementById("submit-btn");
const resetBtn = document.getElementById("reset-btn");
const errorBox = document.getElementById("error");
const results = document.getElementById("results");
const summaryStats = document.getElementById("summary-stats");
const onlyChanges = document.getElementById("only-changes");
const diff = document.getElementById("diff");
const dropzones = [...document.querySelectorAll(".dropzone")];

// ---------- Выбор файлов ----------

dropzones.forEach((zone) => {
  const input = zone.querySelector("input[type=file]");

  ["dragenter", "dragover"].forEach((type) =>
    zone.addEventListener(type, (e) => {
      e.preventDefault();
      zone.classList.add("dragover");
    })
  );

  ["dragleave", "drop"].forEach((type) =>
    zone.addEventListener(type, (e) => {
      e.preventDefault();
      zone.classList.remove("dragover");
    })
  );

  zone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (!file) return;
    // DataTransfer -> input.files, чтобы форма отправилась обычным способом
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    input.dispatchEvent(new Event("change"));
  });

  input.addEventListener("change", () => {
    const file = input.files[0];
    zone.classList.toggle("filled", Boolean(file));
    zone.querySelector(".dropzone__file").textContent = file
      ? `${file.name} · ${formatSize(file.size)}`
      : "";
    updateSubmitState();
  });
});

function updateSubmitState() {
  const ready = dropzones.every((z) => z.querySelector("input").files.length > 0);
  submitBtn.disabled = !ready;
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`;
}

// ---------- Отправка ----------

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.hidden = true;
  results.hidden = true;
  submitBtn.disabled = true;
  submitBtn.textContent = "Сравниваем…";

  try {
    const response = await fetch("/api/compare", {
      method: "POST",
      body: new FormData(form),
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || "Не удалось сравнить документы");
    }

    render(payload);
    results.hidden = false;
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.hidden = false;
  } finally {
    submitBtn.textContent = "Сравнить";
    updateSubmitState();
  }
});

resetBtn.addEventListener("click", () => {
  form.reset();
  dropzones.forEach((zone) => {
    zone.classList.remove("filled");
    zone.querySelector(".dropzone__file").textContent = "";
  });
  errorBox.hidden = true;
  results.hidden = true;
  onlyChanges.checked = false;
  updateSubmitState();
});

onlyChanges.addEventListener("change", applyFilter);

function applyFilter() {
  const hide = onlyChanges.checked;
  diff.querySelectorAll(".row").forEach((row) => {
    row.classList.toggle("hidden", hide && row.dataset.pair === "equal");
  });
}

// ---------- Отрисовка ----------

function render(data) {
  renderSummary(data);
  diff.replaceChildren(
    makeHead("left", "Старая версия", data.left),
    makeHead("right", "Новая версия", data.right)
  );

  for (const pair of data.rows) {
    // Пара считается неизменной, только если обе стороны без правок
    const pairKind =
      pair.left.kind === "equal" && pair.right.kind === "equal" ? "equal" : "changed";
    diff.append(makeRow(pair.left, pairKind), makeRow(pair.right, pairKind));
  }

  if (!data.rows.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Оба документа не содержат текста.";
    diff.append(empty);
  }

  applyFilter();
}

function renderSummary({ summary, left, right }) {
  const chips = [
    ["chip--del", summary.removed, "удалено абзацев"],
    ["chip--ins", summary.added, "добавлено абзацев"],
    ["", summary.changed, "изменено абзацев"],
    ["", summary.equal, "без изменений"],
  ];

  summaryStats.replaceChildren();

  if (summary.identical) {
    summaryStats.append(makeChip("chip--identical", null, "Документы идентичны"));
  }

  for (const [cls, value, label] of chips) {
    summaryStats.append(makeChip(cls, value, label));
  }

  summaryStats.append(
    makeChip("", null, `${left.words.toLocaleString("ru-RU")} → ${right.words.toLocaleString("ru-RU")} слов`)
  );
}

function makeChip(cls, value, label) {
  const chip = document.createElement("div");
  chip.className = `chip ${cls}`.trim();
  if (value !== null) {
    const b = document.createElement("b");
    b.textContent = value.toLocaleString("ru-RU");
    chip.append(b);
  }
  chip.append(document.createTextNode(label));
  return chip;
}

function makeHead(side, title, doc) {
  const head = document.createElement("div");
  head.className = `diff__head diff__head--${side}`;
  const label = document.createElement("span");
  label.textContent = title;
  head.append(label, document.createTextNode(doc.filename));
  return head;
}

function makeRow(row, pairKind) {
  const el = document.createElement("div");
  el.className = `row row--${row.kind}`;
  el.dataset.pair = pairKind;

  for (const span of row.spans) {
    if (span.mark === "none") {
      el.append(document.createTextNode(span.text));
    } else {
      const mark = document.createElement("mark");
      mark.className = span.mark;
      mark.textContent = span.text;
      el.append(mark);
    }
  }

  // Пустая строка всё равно должна занимать высоту в сетке
  if (!row.spans.length) {
    el.append(document.createTextNode(" "));
  }

  return el;
}
