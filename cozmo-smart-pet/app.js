const state = {
  energy: 78,
  mood: "neugierig",
  timer: null,
};

const moodCopy = {
  neugierig: "Er erkundet gerne seine Umgebung. Vielleicht gibt es heute etwas Neues zu entdecken?",
  verspielt: "Cozmo hat gerade richtig Lust auf gemeinsame Zeit mit dir.",
  zufrieden: "Ein schöner Moment für Cozmo. Er fühlt sich wohl und geborgen.",
  müde: "Auch kleine Roboter brauchen Pausen. Eine Ladung gibt ihm neue Energie.",
};

const toast = document.querySelector("#toast");
let toastTimer;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2600);
}

function updateEnergy(value) {
  state.energy = Math.max(0, Math.min(100, value));
  document.querySelector("#energy-value").textContent = state.energy;
  document.querySelector("#energy-meter").style.width = `${state.energy}%`;
  const caption = state.energy < 20 ? "Zeit für eine Ladepause" : state.energy < 45 ? "Eine kleine Pause tut gut" : "Gute Laune, viel Energie";
  document.querySelector("#energy-caption").textContent = caption;
  if (state.energy < 20) setMood("müde");
}

function setMood(mood) {
  state.mood = mood;
  document.querySelector("#mood-word").textContent = mood;
  document.querySelector("#mood-description").textContent = moodCopy[mood];
}

function addMemory(title, detail, icon = "✦") {
  const item = document.createElement("div");
  item.className = "memory-item";
  const symbol = document.createElement("span");
  symbol.className = "memory-icon memory-heart";
  symbol.setAttribute("aria-hidden", "true");
  symbol.textContent = icon;
  const content = document.createElement("div");
  const heading = document.createElement("strong");
  heading.textContent = title;
  const caption = document.createElement("span");
  caption.textContent = `${new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit" }).format(new Date())} · ${detail}`;
  content.append(heading, caption);
  const star = document.createElement("span");
  star.className = "memory-star";
  star.setAttribute("aria-hidden", "true");
  star.textContent = "✧";
  item.append(symbol, content, star);
  document.querySelector("#memory-list").prepend(item);
  while (document.querySelectorAll("#memory-list .memory-item").length > 4) {
    document.querySelector("#memory-list .memory-item:last-child").remove();
  }
}

function runAction(action) {
  if (action === "play") {
    if (state.energy < 10) {
      showToast("Cozmo ist müde – eine Ladepause wäre gut.");
      return;
    }
    updateEnergy(state.energy - 8);
    setMood("verspielt");
    addMemory("Mit dir gespielt", "Spielzeit", "♡");
    showToast("Cozmo freut sich über die gemeinsame Spielzeit!");
  } else if (action === "explore") {
    if (state.energy < 15) {
      showToast("Cozmo braucht erst etwas Energie zum Erkunden.");
      return;
    }
    updateEnergy(state.energy - 12);
    setMood("neugierig");
    addMemory("Eine neue Runde gedreht", "Erkundung", "⌖");
    showToast("Cozmo hat seine Umgebung erkundet. (Simulation)");
  } else if (action === "charge") {
    updateEnergy(100);
    setMood("zufrieden");
    addMemory("Energie wieder aufgeladen", "Ladepause", "ϟ");
    showToast("In der Demo ist Cozmos Akku wieder voll.");
  }
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => runAction(button.dataset.action));
});

state.timer = window.setInterval(() => {
  if (state.energy > 0) updateEnergy(state.energy - 1);
}, 45000);
