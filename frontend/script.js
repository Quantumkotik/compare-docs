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

    renderDiff(data.diff);
    resultEl.classList.remove("hidden");
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove("hidden");
  } finally {
    loadingEl.classList.add("hidden");
    submitBtn.disabled = false;
  }
});

function renderDiff(diff) {
  diffOutput.innerHTML = "";

  if (diff.length === 0) {
    diffOutput.innerHTML = '<div class="diff-line empty">Документы идентичны</div>';
    return;
  }

  for (const item of diff) {
    const line = document.createElement("div");
    const isEmpty = item.text.trim() === "";
    line.className = `diff-line ${item.type}${isEmpty ? " empty" : ""}`;
    line.textContent = isEmpty ? "(пустой абзац)" : item.text;
    diffOutput.appendChild(line);
  }
}
