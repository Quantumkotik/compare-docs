const form = document.getElementById("upload-form");
const submitBtn = document.getElementById("submit-btn");
const resetBtn = document.getElementById("reset-btn");
const errorBox = document.getElementById("error");
const results = document.getElementById("results");
const dropzones = [...document.querySelectorAll(".dropzone")];

// Перетаскивание файла в зону
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

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.hidden = true;
  results.hidden = true;
  submitBtn.disabled = true;
  submitBtn.textContent = "Загрузка…";

  try {
    const response = await fetch("/api/upload", {
      method: "POST",
      body: new FormData(form),
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || "Не удалось загрузить документы");
    }

    render("left", payload.left);
    render("right", payload.right);
    results.hidden = false;
  } catch (err) {
    showError(err.message);
  } finally {
    submitBtn.textContent = "Загрузить";
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
  updateSubmitState();
});

function render(slot, doc) {
  const panel = results.querySelector(`.result[data-slot="${slot}"]`);
  panel.replaceChildren();

  const title = document.createElement("h2");
  title.textContent = doc.filename;
  panel.append(title);

  const stats = document.createElement("div");
  stats.className = "stats";
  const items = [
    [doc.paragraphs, "абзацев"],
    [doc.words, "слов"],
    [doc.chars, "символов"],
    [doc.tables, "таблиц"],
  ];
  for (const [value, label] of items) {
    const stat = document.createElement("div");
    stat.className = "stat";
    const v = document.createElement("div");
    v.className = "stat__value";
    v.textContent = value.toLocaleString("ru-RU");
    const l = document.createElement("div");
    l.className = "stat__label";
    l.textContent = label;
    stat.append(v, l);
    stats.append(stat);
  }
  panel.append(stats);

  const preview = document.createElement("div");
  preview.className = "preview";
  for (const text of doc.preview) {
    const p = document.createElement("p");
    p.textContent = text;
    preview.append(p);
  }
  if (doc.truncated) {
    const more = document.createElement("p");
    more.className = "more";
    more.textContent = `…ещё ${doc.paragraphs - doc.preview.length} абз.`;
    preview.append(more);
  }
  if (!doc.preview.length) {
    const empty = document.createElement("p");
    empty.textContent = "Документ не содержит текста.";
    preview.append(empty);
  }
  panel.append(preview);
}
