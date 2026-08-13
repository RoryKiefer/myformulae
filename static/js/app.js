(function () {
  const form = document.getElementById("solve-form");
  const input = document.getElementById("expression");
  const modeButtons = Array.from(document.querySelectorAll(".mode-btn"));
  const submitBtn = form.querySelector(".submit-btn");

  const errorBox = document.getElementById("error");
  const resultBox = document.getElementById("result");
  const inputDisplay = document.getElementById("input-display");
  const finalDisplay = document.getElementById("final-display");
  const stepsBlock = document.getElementById("steps-block");
  const stepsList = document.getElementById("steps-list");
  const noteBox = document.getElementById("note");

  let mode = "auto";

  function setMode(next) {
    mode = next;
    modeButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.mode === next));
  }
  setMode("auto");

  modeButtons.forEach((btn) => {
    btn.addEventListener("click", () => setMode(btn.dataset.mode));
  });

  function renderMath(el, latex) {
    el.textContent = "";
    if (window.katex) {
      window.katex.render(latex, el, { throwOnError: false, displayMode: true });
    } else {
      el.textContent = latex;
    }
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
    resultBox.hidden = true;
  }

  function clearError() {
    errorBox.hidden = true;
    errorBox.textContent = "";
  }

  function showResult(data) {
    resultBox.hidden = false;
    renderMath(inputDisplay, data.input_display);
    renderMath(finalDisplay, data.final);

    stepsList.innerHTML = "";
    if (data.steps && data.steps.length) {
      stepsBlock.hidden = false;
      data.steps.forEach((step) => {
        const li = document.createElement("li");
        renderMath(li, step);
        stepsList.appendChild(li);
      });
    } else {
      stepsBlock.hidden = true;
    }

    if (data.note) {
      noteBox.hidden = false;
      noteBox.textContent = data.note;
    } else {
      noteBox.hidden = true;
      noteBox.textContent = "";
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const expression = input.value.trim();
    clearError();
    resultBox.hidden = true;

    if (!expression) {
      showError("Please enter an expression.");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Solving…";

    try {
      const res = await fetch("/api/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expression, mode }),
      });
      const data = await res.json();

      if (!res.ok) {
        showError(data.error || "Something went wrong.");
        return;
      }
      showResult(data);
    } catch (err) {
      showError("Could not reach the server. Please try again.");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit";
    }
  });
})();
