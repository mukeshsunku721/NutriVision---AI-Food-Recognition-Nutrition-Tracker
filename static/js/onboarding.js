const form = document.getElementById("onboarding-form");
const bmiBox = document.getElementById("bmi-result");

form.addEventListener("submit", async e => {
  e.preventDefault();
  const goal = document.querySelector('input[name="goal"]:checked')?.value || "maintain";
  const payload = {
    name: document.getElementById("name").value.trim(),
    age: parseInt(document.getElementById("age").value),
    gender: document.getElementById("gender").value,
    height_cm: parseFloat(document.getElementById("height").value),
    weight_kg: parseFloat(document.getElementById("weight").value),
    activity: document.getElementById("activity").value,
    goal,
  };
  const btn = form.querySelector("button[type=submit]");
  btn.disabled = true; btn.textContent = "Setting up…";
  try {
    const res  = await fetch("/api/users", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    localStorage.setItem("userId", data.id);
    localStorage.setItem("userName", data.name);
    const r = data.daily_requirements;
    bmiBox.innerHTML = `
      <h3>Profile created</h3>
      <p>BMI: <strong>${r.bmi}</strong> — ${r.bmi_category}</p>
      <p>Daily target: <strong>${r.calories} kcal</strong></p>
      <p>Protein ${r.protein}g &nbsp;·&nbsp; Carbs ${r.carbs}g &nbsp;·&nbsp; Fat ${r.fat}g</p>`;
    bmiBox.classList.remove("hidden");
    setTimeout(() => window.location.href = "/dashboard", 2000);

  } catch (err) {
    alert(err.message);
    btn.disabled = false; btn.textContent = "Calculate & Continue";
  }
});
