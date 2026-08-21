const form = document.getElementById("compare-form");
const file1Input = document.getElementById("file1");
const file2Input = document.getElementById("file2");
const file1Name = document.getElementById("file1-name");
const file2Name = document.getElementById("file2-name");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const resultSummaryEl = document.getElementById("result-summary");
const diffContainer = document.getElementById("diff-container");

file1Input.addEventListener("change", () => {
  file1Name.textContent = file1Input.files[0]?.name ?? "Файл не выбран";
});

file2Input.addEventListener("change", () => {
  file2Name.textContent = file2Input.files[0]?.name ?? "Файл не выбран";
});

function showStatus(message, isError) {
  statusEl.textContent = message;
  statusEl.hidden = false;
  statusEl.classList.toggle("error", Boolean(isError));
}

function hideStatus() {
  statusEl.hidden = true;
  statusEl.classList.remove("error");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file1 = file1Input.files[0];
  const file2 = file2Input.files[0];

  if (!file1 || !file2) {
    showStatus("Выберите оба файла", true);
    return;
  }

  const formData = new FormData();
  formData.append("file1", file1);
  formData.append("file2", file2);

  submitBtn.disabled = true;
  resultEl.hidden = true;
  showStatus("Сравниваем документы...");

  try {
    const response = await fetch("/api/compare", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Не удалось сравнить документы");
    }

    hideStatus();
    resultSummaryEl.textContent = data.identical
      ? "Документы идентичны"
      : `Найдены различия между "${data.filename1}" и "${data.filename2}"`;
    diffContainer.innerHTML = data.diff_html;
    resultEl.hidden = false;
  } catch (err) {
    showStatus(err.message, true);
  } finally {
    submitBtn.disabled = false;
  }
});
