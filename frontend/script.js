const form = document.getElementById("compare-form");
const file1Input = document.getElementById("file1");
const file2Input = document.getElementById("file2");
const filename1 = document.getElementById("filename1");
const filename2 = document.getElementById("filename2");
const submitBtn = document.getElementById("submit-btn");
const errorEl = document.getElementById("error");
const loadingEl = document.getElementById("loading");
const resultEl = document.getElementById("result");
const diffOutput = document.getElementById("diff-output");
const headerLeft = document.getElementById("header-left");
const headerRight = document.getElementById("header-right");

file1Input.addEventListener("change", () => {
  filename1.textContent = file1Input.files[0]?.name ?? "Файл не выбран";
});

file2Input.addEventListener("change", () => {
  filename2.textContent = file2Input.files[0]?.name ?? "Файл не выбран";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  errorEl.classList.add("hidden");
  resultEl.classList.add("hidden");
  loadingEl.classList.remove("hidden");
  submitBtn.disabled = true;

  const formData = new FormData();
  formData.append("file1", file1Input.files[0]);
  formData.append("file2", file2Input.files[0]);

  try {
    const response = await fetch("/api/compare", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось сравнить документы");
    }

    headerLeft.textContent = `Старая версия — ${data.file1}`;
    headerRight.textContent = `Новая версия — ${data.file2}`;
    renderDiff(data.rows);
    resultEl.classList.remove("hidden");
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  } finally {
    loadingEl.classList.add("hidden");
    submitBtn.disabled = false;
  }
});

function renderDiff(rows) {
  diffOutput.innerHTML = "";

  if (rows.length === 0) {
    diffOutput.innerHTML = '<div class="diff-cell empty">Документы идентичны</div>';
    return;
  }

  for (const row of rows) {
    diffOutput.appendChild(buildCell(row.left));
    diffOutput.appendChild(buildCell(row.right));
  }
}

function buildCell(cell) {
  const div = document.createElement("div");

  if (!cell) {
    div.className = "diff-cell blank";
    return div;
  }

  const isEmpty = cell.text.trim() === "";
  div.className = `diff-cell ${cell.type}${isEmpty ? " empty" : ""}`;
  div.textContent = isEmpty ? "(пустой абзац)" : cell.text;
  return div;
}
