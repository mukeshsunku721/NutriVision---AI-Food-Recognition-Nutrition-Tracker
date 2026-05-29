/* Dashboard — detection, annotation display, meal logging, live tracker */

const userId   = localStorage.getItem("userId");
const userName = localStorage.getItem("userName") || "User";
if (!userId) window.location.href = "/";


// TO PREVIEW LOCALLY:
//const userId   = "1"; // Hardcode a fake ID
//const userName = "Demo User"; 

// if (!userId) window.location.href = "/"; // Comment this out!


document.getElementById("nav-user").textContent = userName;
document.getElementById("nav-date").textContent = new Date().toLocaleDateString("en-IN",
  {weekday:"long", day:"numeric", month:"short"});

const datePicker = document.getElementById("date-picker");
datePicker.value = new Date().toISOString().split("T")[0];
datePicker.addEventListener("change", () => loadSummary(datePicker.value));

// ── State ─────────────────────────────────────────────────────────────────
let lastDetection = null;   // stores full /api/detect response

// ── Upload zone ───────────────────────────────────────────────────────────
const uploadZone = document.getElementById("upload-zone");
const fileInput  = document.getElementById("file-input");
const previewImg = document.getElementById("preview-img");
const detectBtn  = document.getElementById("detect-btn");

uploadZone.addEventListener("click", () => fileInput.click());
uploadZone.addEventListener("dragover", e => { e.preventDefault(); uploadZone.classList.add("drag-over"); });
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("drag-over"));
uploadZone.addEventListener("drop", e => {
  e.preventDefault(); uploadZone.classList.remove("drag-over");
  if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => fileInput.files[0] && handleFile(fileInput.files[0]));

function handleFile(file) {
  previewImg.src = URL.createObjectURL(file);
  previewImg.classList.remove("hidden");
  detectBtn.disabled = false;
  detectBtn._file = file;
  document.getElementById("detection-result").classList.add("hidden");
  lastDetection = null;
}

// ── Detect ────────────────────────────────────────────────────────────────
detectBtn.addEventListener("click", async () => {
  const file = detectBtn._file;
  if (!file) return;
  detectBtn.disabled = true;
  detectBtn.textContent = "Detecting…";

  const formData = new FormData();
  formData.append("image", file);
  formData.append("quantity_g", document.getElementById("quantity").value);

  try {
    const res  = await fetch("/api/detect", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    lastDetection = data;
    renderDetection(data);
  } catch (err) {
    alert("Detection failed: " + err.message);
  } finally {
    detectBtn.disabled = false;
    detectBtn.textContent = "Detect Food Items";
  }
});

// ── Render detection results ──────────────────────────────────────────────
function renderDetection(data) {
  const { detections, plate_total, annotated_url, count } = data;

  // Annotated image
  document.getElementById("annotated-img").src = annotated_url + "?t=" + Date.now();
  document.getElementById("detect-caption").textContent =
    `${count} food item${count !== 1 ? "s" : ""} detected`;

  // Per-item cards
  const itemCards = document.getElementById("item-cards");
  itemCards.innerHTML = detections.map(item => {
    const [r, g, b] = item.color_rgb;
    const hex = `rgb(${r},${g},${b})`;
    const n = item.nutrition;
    return `
      <div class="item-card" style="border-left-color:${hex}">
        <div class="item-badge" style="background:${hex}">${item.index}</div>
        <div class="item-info">
          <div class="item-name">${item.label}</div>
          <div class="item-conf">${item.confidence}% confidence &nbsp;·&nbsp; ${n.quantity}g</div>
          <div class="item-macros">
            ${n.calories} kcal &nbsp;·&nbsp;
            P: ${n.protein}g &nbsp;·&nbsp;
            C: ${n.carbs}g &nbsp;·&nbsp;
            F: ${n.fat}g
          </div>
        </div>
      </div>`;
  }).join("");

  // Plate totals
  const t = plate_total;
  document.getElementById("pt-cal").textContent = t.calories;
  document.getElementById("pt-pro").textContent = t.protein + "g";
  document.getElementById("pt-car").textContent = t.carbs + "g";
  document.getElementById("pt-fat").textContent = t.fat + "g";
  document.getElementById("pt-fib").textContent = t.fiber + "g";

  document.getElementById("detection-result").classList.remove("hidden");
}

// ── Log all detected items ────────────────────────────────────────────────
document.getElementById("log-all-btn").addEventListener("click", async () => {
  if (!lastDetection) return;

  const payload = {
    meal_name: document.getElementById("meal-select").value,
    log_date:  datePicker.value,
    items: lastDetection.detections.map(d => ({
      food_name:  d.food_name,
      quantity_g: d.nutrition.quantity,
      confidence: d.confidence,
      image_path: lastDetection.annotated_url,
    })),
  };

  try {
    const res = await fetch(`/api/users/${userId}/meals`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error((await res.json()).error);

    document.getElementById("detection-result").classList.add("hidden");
    previewImg.classList.add("hidden");
    detectBtn.disabled = true;
    lastDetection = null;
    await loadSummary(datePicker.value);
  } catch (err) {
    alert("Failed to log: " + err.message);
  }
});

// ── Load summary ──────────────────────────────────────────────────────────

async function loadSummary(dateStr) {
  const [sumRes, mealRes] = await Promise.all([
    fetch(`/api/users/${userId}/summary?date=${dateStr}`),
    fetch(`/api/users/${userId}/meals?date=${dateStr}`),
  ]);
  const sum   = await sumRes.json();
  const meals = await mealRes.json();
  updateRing(sum);
  updateBars(sum);
  updateAdvice(sum.advice);
  renderLog(meals.meals);
}







function updateRing(s) {
  const consumed = s.intake.calories;
  const target   = s.targets.calories;
  const circ     = 314;
  const offset   = circ - Math.min(consumed / target, 1) * circ;
  document.getElementById("ring-consumed").textContent = Math.round(consumed);
  document.getElementById("ring-target").textContent   = target;
  document.getElementById("ring-arc").setAttribute("stroke-dashoffset", offset);
}

function updateBars(s) {
  const keys = [["protein","bp","lp"],["carbs","bc","lc"],["fat","bf","lf"],["fiber","bfi","lfi"]];
  for (const [key,barId,lblId] of keys) {
    const consumed = s.intake[key] || 0;
    const target   = s.targets[key] || 1;
    document.getElementById(barId).style.width =
      Math.min((consumed/target)*100,100).toFixed(1)+"%";
    document.getElementById(lblId).textContent = `${Math.round(consumed)}/${target}g`;
  }
}

function updateAdvice(advice) {
  document.getElementById("advice-box").innerHTML =
    advice.map(a => `<div class="advice-item">${a}</div>`).join("");
}

function renderLog(meals) {
  const el = document.getElementById("meal-log");
  if (!meals || !Object.keys(meals).length) {
    el.innerHTML = `<p class="empty-state">No meals logged yet today.</p>`; return;
  }
  const ORDER = ["Breakfast","Lunch","Dinner","Snack"];
  const sorted = Object.entries(meals).sort(([a],[b])=>ORDER.indexOf(a)-ORDER.indexOf(b));
  el.innerHTML = sorted.map(([meal, items]) => `
    <div class="meal-group">
      <div class="meal-group-title">${meal}</div>
      ${items.map(i=>`
        <div class="log-item">
          <span class="log-item-name">${i.label}</span>
          <span class="log-item-right">${i.quantity_g}g · ${i.calories} kcal</span>
        </div>`).join("")}
    </div>`).join("");
}

// ── Init ──────────────────────────────────────────────────────────────────
loadSummary(datePicker.value);
