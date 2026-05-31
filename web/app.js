const canvas = document.getElementById("boardCanvas");
const ctx = canvas.getContext("2d");
const SQRT3 = Math.sqrt(3);

const els = {
  setupOverlay: document.getElementById("setupOverlay"),
  setupForm: document.getElementById("setupForm"),
  setupMode: document.getElementById("setupMode"),
  setupHumanColor: document.getElementById("setupHumanColor"),
  setupFirstColor: document.getElementById("setupFirstColor"),
  humanSideField: document.getElementById("humanSideField"),
  ponderRow: document.getElementById("ponderRow"),
  setupPonderToggle: document.getElementById("setupPonderToggle"),
  setupAutoAiToggle: document.getElementById("setupAutoAiToggle"),
  blueDepthInput: document.getElementById("blueDepthInput"),
  orangeDepthInput: document.getElementById("orangeDepthInput"),
  blueDepthValue: document.getElementById("blueDepthValue"),
  orangeDepthValue: document.getElementById("orangeDepthValue"),
  blueTimeInput: document.getElementById("blueTimeInput"),
  orangeTimeInput: document.getElementById("orangeTimeInput"),
  turnDot: document.getElementById("turnDot"),
  turnText: document.getElementById("turnText"),
  bannerTitle: document.getElementById("bannerTitle"),
  bannerSub: document.getElementById("bannerSub"),
  modeLabel: document.getElementById("modeLabel"),
  statusTitle: document.getElementById("statusTitle"),
  cellsStat: document.getElementById("cellsStat"),
  turnStat: document.getElementById("turnStat"),
  scoreStat: document.getElementById("scoreStat"),
  selectedCells: document.getElementById("selectedCells"),
  coordReadout: document.getElementById("coordReadout"),
  toast: document.getElementById("toast"),
  engineStatus: document.getElementById("engineStatus"),
  engineSide: document.getElementById("engineSide"),
  engineDepth: document.getElementById("engineDepth"),
  engineTime: document.getElementById("engineTime"),
  engineNodes: document.getElementById("engineNodes"),
  enginePv: document.getElementById("enginePv"),
  engineDepths: document.getElementById("engineDepths"),
  undoButton: document.getElementById("undoButton"),
  redoButton: document.getElementById("redoButton"),
  undoRoundButton: document.getElementById("undoRoundButton"),
  botButton: document.getElementById("botButton"),
  analyzeButton: document.getElementById("analyzeButton"),
  newGameButton: document.getElementById("newGameButton"),
  commitButton: document.getElementById("commitButton"),
  clearSelectionButton: document.getElementById("clearSelectionButton"),
  autoSubmitToggle: document.getElementById("autoSubmitToggle"),
  autoAiToggle: document.getElementById("autoAiToggle"),
  sizeSlider: document.getElementById("sizeSlider"),
  sizeValue: document.getElementById("sizeValue"),
  coordsToggle: document.getElementById("coordsToggle"),
  frontierToggle: document.getElementById("frontierToggle"),
  heatToggle: document.getElementById("heatToggle"),
  latestToggle: document.getElementById("latestToggle"),
  resetViewButton: document.getElementById("resetViewButton"),
  centerPiecesButton: document.getElementById("centerPiecesButton"),
  historyList: document.getElementById("historyList")
};

let state = null;
let cellMap = new Map();
let selected = [];
let hoverCell = null;
let searchBusy = false;
let gameStarted = false;
let toastTimer = null;
let searchPollTimer = null;
let automationTimer = null;

const settings = {
  hexSize: 34,
  showCoords: false,
  showFrontier: true,
  showHeat: false,
  showLatest: true,
  autoSubmit: true,
  autoAi: true
};

const view = {
  panX: 0,
  panY: 0,
  scale: 1,
  down: false,
  moved: false,
  lastX: 0,
  lastY: 0,
  totalMove: 0
};

function coordKey(x, y) {
  return `${x},${y}`;
}

function prettyColor(color) {
  return color ? color.charAt(0).toUpperCase() + color.slice(1) : "-";
}

function modeLabel(mode) {
  return {
    "human-ai": "Human vs AI",
    "human-human": "Human vs Human",
    "ai-ai": "AI vs AI"
  }[mode] || "Setup";
}

function activeSize() {
  return settings.hexSize * view.scale;
}

function cellToUnit(x, y) {
  return {
    x: 1.5 * x,
    y: SQRT3 * (y - x / 2)
  };
}

function cellToScreen(cell) {
  const unit = cellToUnit(cell.x, cell.y);
  const size = activeSize();
  return {
    x: canvas.clientWidth / 2 + view.panX + unit.x * size,
    y: canvas.clientHeight / 2 + view.panY + unit.y * size
  };
}

function localToCell(sx, sy) {
  const size = activeSize();
  const ux = (sx - canvas.clientWidth / 2 - view.panX) / size;
  const uy = (sy - canvas.clientHeight / 2 - view.panY) / size;
  const q = (2 / 3) * ux;
  const r = (-1 / 3) * ux + (SQRT3 / 3) * uy;
  const rounded = roundAxial(q, r);
  return { x: rounded.q, y: rounded.r + rounded.q };
}

function eventToCell(event) {
  const rect = canvas.getBoundingClientRect();
  return localToCell(event.clientX - rect.left, event.clientY - rect.top);
}

function roundAxial(q, r) {
  let x = q;
  let z = r;
  let y = -x - z;
  let rx = Math.round(x);
  let ry = Math.round(y);
  let rz = Math.round(z);
  const xDiff = Math.abs(rx - x);
  const yDiff = Math.abs(ry - y);
  const zDiff = Math.abs(rz - z);

  if (xDiff > yDiff && xDiff > zDiff) {
    rx = -ry - rz;
  } else if (yDiff > zDiff) {
    ry = -rx - rz;
  } else {
    rz = -rx - ry;
  }
  return { q: rx, r: rz };
}

function isSelected(cell) {
  return selected.some((item) => item.x === cell.x && item.y === cell.y);
}

function isLatest(cell) {
  if (!state || !settings.showLatest || !state.history.length) {
    return false;
  }
  const latest = state.history[state.history.length - 1];
  return latest.cells.some((item) => item.x === cell.x && item.y === cell.y);
}

function hexPath(cx, cy, radius) {
  ctx.beginPath();
  for (let i = 0; i < 6; i += 1) {
    const angle = (Math.PI / 180) * (60 * i);
    const x = cx + radius * Math.cos(angle);
    const y = cy + radius * Math.sin(angle);
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.closePath();
}

function drawHex(cell, options = {}) {
  const center = cellToScreen(cell);
  const radius = activeSize() * (options.scale || 0.92);
  if (
    center.x < -radius * 2 ||
    center.y < -radius * 2 ||
    center.x > canvas.clientWidth + radius * 2 ||
    center.y > canvas.clientHeight + radius * 2
  ) {
    return;
  }

  hexPath(center.x, center.y, radius);
  if (options.fill) {
    ctx.fillStyle = options.fill;
    ctx.fill();
  }
  if (options.stroke) {
    ctx.lineWidth = options.lineWidth || 1;
    ctx.strokeStyle = options.stroke;
    ctx.stroke();
  }
  if (options.label) {
    ctx.fillStyle = "rgba(214, 225, 237, 0.58)";
    ctx.font = `${Math.max(10, Math.floor(activeSize() * 0.32))}px Cascadia Mono, Consolas, monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(options.label, center.x, center.y);
  }
}

function drawPiece(cell) {
  const center = cellToScreen(cell);
  const radius = activeSize() * 0.8;
  if (
    center.x < -radius * 2 ||
    center.y < -radius * 2 ||
    center.x > canvas.clientWidth + radius * 2 ||
    center.y > canvas.clientHeight + radius * 2
  ) {
    return;
  }

  const blue = cell.color === "blue";
  hexPath(center.x, center.y, radius);
  ctx.fillStyle = blue ? "#47c8ff" : "#ffc23d";
  ctx.fill();
  ctx.lineWidth = Math.max(2, activeSize() * 0.08);
  ctx.strokeStyle = blue ? "#d9f5ff" : "#fff2bf";
  ctx.stroke();

  if (settings.showHeat && (cell.threatcount > 0 || cell.line >= 4)) {
    hexPath(center.x, center.y, radius + 4);
    ctx.lineWidth = 3;
    ctx.strokeStyle = cell.threatcount > 1 ? "rgba(255, 109, 109, 0.9)" : "rgba(98, 240, 189, 0.8)";
    ctx.stroke();
  }

  if (settings.showCoords && activeSize() >= 24) {
    ctx.fillStyle = blue ? "#052432" : "#4a2b00";
    ctx.font = `${Math.max(10, Math.floor(activeSize() * 0.3))}px Cascadia Mono, Consolas, monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(`${cell.x},${cell.y}`, center.x, center.y);
  }
}

function draw() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  ctx.clearRect(0, 0, width, height);

  const background = ctx.createLinearGradient(0, 0, width, height);
  background.addColorStop(0, "#0d1118");
  background.addColorStop(0.55, "#111827");
  background.addColorStop(1, "#0b1018");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, width, height);

  if (!state) {
    return;
  }

  if (settings.showFrontier) {
    for (const cell of state.frontier || []) {
      const selectedHere = isSelected(cell);
      const hoverHere = hoverCell && hoverCell.x === cell.x && hoverCell.y === cell.y;
      drawHex(cell, {
        fill: selectedHere
          ? "rgba(98, 240, 189, 0.16)"
          : hoverHere
            ? "rgba(255, 255, 255, 0.06)"
            : "rgba(16, 24, 38, 0.54)",
        stroke: selectedHere
          ? "rgba(98, 240, 189, 0.95)"
          : "rgba(132, 153, 184, 0.18)",
        lineWidth: selectedHere ? 2.5 : 1,
        label: settings.showCoords && activeSize() >= 30 ? `${cell.x},${cell.y}` : null
      });
    }
  }

  for (const cell of state.cells) {
    drawPiece(cell);
  }

  if (settings.showLatest && state.history.length) {
    for (const cell of state.history[state.history.length - 1].cells) {
      drawHex(cell, {
        stroke: "rgba(255, 255, 255, 0.85)",
        lineWidth: 3,
        scale: 0.98
      });
    }
  }

  for (const cell of selected) {
    drawHex(cell, {
      stroke: "rgba(98, 240, 189, 0.95)",
      lineWidth: 3,
      scale: 0.98
    });
  }

  for (const cell of state.cells) {
    if (cell.sixinarow) {
      drawHex(cell, {
        stroke: "rgba(255, 255, 255, 0.96)",
        lineWidth: 4,
        scale: 1.04
      });
    }
  }
}

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  draw();
}

async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

async function postJson(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

function secondsToMs(value) {
  const seconds = Number(value || 0);
  return Math.max(0, Math.floor(seconds * 1000));
}

function msToSeconds(ms) {
  return Math.floor(Number(ms || 0) / 1000);
}

function setupPayload() {
  return {
    mode: els.setupMode.value,
    humanColor: els.setupHumanColor.value,
    firstColor: els.setupFirstColor.value,
    blueDepth: Number(els.blueDepthInput.value),
    orangeDepth: Number(els.orangeDepthInput.value),
    blueTimeMs: secondsToMs(els.blueTimeInput.value),
    orangeTimeMs: secondsToMs(els.orangeTimeInput.value),
    ponder: els.setupPonderToggle.checked
  };
}

function syncSetupFields() {
  const mode = els.setupMode.value;
  els.humanSideField.style.display = mode === "ai-ai" ? "none" : "grid";
  els.setupHumanColor.disabled = mode !== "human-ai";
  els.setupPonderToggle.disabled = mode !== "human-human";
  els.ponderRow.style.opacity = mode === "human-human" ? "1" : "0.45";
}

function applyState(nextState) {
  state = nextState;
  cellMap = new Map(state.cells.map((cell) => [coordKey(cell.x, cell.y), cell]));
  selected = selected.filter((cell) => !cellMap.has(coordKey(cell.x, cell.y)));
  syncControls();
  draw();
  scheduleAutomation();
}

async function loadState() {
  try {
    applyState(await getJson("/api/state"));
    centerPieces(false);
  } catch (error) {
    showToast(error.message);
  }
}

function showToast(message) {
  window.clearTimeout(toastTimer);
  els.toast.textContent = message;
  els.toast.hidden = false;
  toastTimer = window.setTimeout(() => {
    els.toast.hidden = true;
  }, 2600);
}

function formatScore(score) {
  if (score === null || score === undefined) {
    return "-";
  }
  if (Math.abs(score) >= 1000000) {
    return score > 0 ? "Win" : "Loss";
  }
  return Number(score).toFixed(1);
}

function formatMs(ms) {
  if (!ms) {
    return "0 ms";
  }
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(2)} s`;
  }
  return `${ms} ms`;
}

function renderSearchStats(search = {}) {
  const depths = search.depths || [];
  const latestDepth = depths.length ? depths[depths.length - 1] : null;
  const pv = (search.pv && search.pv.length ? search.pv : latestDepth && latestDepth.pv) || [];
  const running = search.running || search.threadRunning;

  els.engineStatus.textContent = running ? (search.kind === "analysis" ? "Analyzing" : "Thinking") : "Idle";
  els.engineSide.textContent = prettyColor(search.side);
  els.engineDepth.textContent = latestDepth ? `D${latestDepth.depth}` : "D0";
  els.engineTime.textContent = formatMs(search.elapsedMs);
  els.engineNodes.textContent = Number(search.nodes || 0).toLocaleString();
  els.enginePv.textContent = pv.length ? pv.join("  ") : "-";
  els.scoreStat.textContent = formatScore(latestDepth ? latestDepth.score : state && state.lastScore);

  if (depths.length === 0) {
    els.engineDepths.innerHTML = '<div class="engine-empty">No search yet.</div>';
    return;
  }

  els.engineDepths.innerHTML = depths
    .slice()
    .reverse()
    .slice(0, 10)
    .map((item) => `
      <div class="engine-depth-row">
        <span>D${item.depth}</span>
        <strong>${formatScore(item.score)}</strong>
        <span>${formatMs(item.timeMs)}</span>
        <span>${Number(item.nodes || 0).toLocaleString()} n</span>
      </div>
    `)
    .join("");
}

function syncSetupFromState() {
  if (!state) {
    return;
  }
  els.setupMode.value = state.mode || "human-ai";
  els.setupHumanColor.value = state.humanColor || "blue";
  els.setupFirstColor.value = state.firstColor || "blue";
  els.blueDepthInput.value = state.sideSettings?.blue?.depth || 3;
  els.orangeDepthInput.value = state.sideSettings?.orange?.depth || 3;
  els.blueDepthValue.textContent = els.blueDepthInput.value;
  els.orangeDepthValue.textContent = els.orangeDepthInput.value;
  els.blueTimeInput.value = msToSeconds(state.sideSettings?.blue?.timeMs || 0);
  els.orangeTimeInput.value = msToSeconds(state.sideSettings?.orange?.timeMs || 0);
  els.setupPonderToggle.checked = Boolean(state.ponder);
  syncSetupFields();
}

function syncControls() {
  if (!state) {
    return;
  }

  const activeColor = state.winner || state.nextColor;
  els.turnDot.className = `dot ${activeColor}`;
  els.turnText.textContent = state.gameOver
    ? `${prettyColor(state.winner)} wins`
    : `${prettyColor(state.nextColor)} to move`;

  els.modeLabel.textContent = modeLabel(state.mode);
  els.statusTitle.textContent = state.gameOver
    ? `${prettyColor(state.winner)} wins`
    : state.botPending
      ? `${prettyColor(state.nextColor)} AI to move`
      : `${prettyColor(state.nextColor)} to move`;

  if (!gameStarted) {
    els.bannerTitle.textContent = "Setup";
    els.bannerSub.textContent = "Choose a mode and press Play.";
  } else if (state.gameOver) {
    els.bannerTitle.textContent = `${prettyColor(state.winner)} wins`;
    els.bannerSub.textContent = "Start a new game or undo.";
  } else if (searchBusy) {
    els.bannerTitle.textContent = state.search?.kind === "analysis" ? "Analysis running" : "AI thinking";
    els.bannerSub.textContent = "Engine output is updating in the side panel.";
  } else if (state.botPending) {
    els.bannerTitle.textContent = `${prettyColor(state.nextColor)} AI to move`;
    els.bannerSub.textContent = "Use AI Move or enable Auto-play AI turns.";
  } else {
    els.bannerTitle.textContent = `${prettyColor(state.nextColor)} to move`;
    els.bannerSub.textContent = `${2 - selected.length} placements left this turn.`;
  }

  els.cellsStat.textContent = state.occupied;
  els.turnStat.textContent = state.turn;
  els.sizeValue.textContent = settings.hexSize;
  renderSearchStats(state.search || {});

  const canHumanMove = gameStarted && !searchBusy && !state.gameOver && !state.botPending;
  els.commitButton.disabled = !canHumanMove || selected.length !== 2;
  els.clearSelectionButton.disabled = searchBusy || selected.length === 0;
  els.botButton.disabled = !gameStarted || searchBusy || !state.botPending;
  els.analyzeButton.disabled = !gameStarted || searchBusy || state.gameOver;
  els.undoButton.disabled = searchBusy || !state.canUndo;
  els.undoRoundButton.disabled = searchBusy || !state.canUndo;
  els.redoButton.disabled = searchBusy || !state.canRedo;
  els.newGameButton.disabled = searchBusy;

  if (selected.length === 0) {
    els.selectedCells.innerHTML = '<span class="empty-selection">No cells selected</span>';
  } else {
    els.selectedCells.innerHTML = selected
      .map((cell) => `<span class="coord-chip">${cell.x}, ${cell.y}</span>`)
      .join("");
  }

  if (state.history.length === 0) {
    els.historyList.innerHTML = '<div class="history-empty">No moves yet.</div>';
  } else {
    els.historyList.innerHTML = state.history
      .slice()
      .reverse()
      .slice(0, 14)
      .map((move) => {
        const title = `${move.ply}. ${move.actor} placed ${prettyColor(move.color)}`;
        const coords = move.cells.map((cell) => `(${cell.x}, ${cell.y})`).join("  ");
        return `
          <div class="history-item">
            <span class="dot ${move.color}"></span>
            <span class="history-title">${title}</span>
            <span class="history-coords">${coords}</span>
          </div>
        `;
      })
      .join("");
  }
}

function selectCell(cell) {
  if (!state || !gameStarted || searchBusy) {
    return;
  }
  if (state.gameOver) {
    showToast("The game is already over.");
    return;
  }
  if (state.botPending) {
    showToast("It is an AI turn.");
    return;
  }
  if (cellMap.has(coordKey(cell.x, cell.y))) {
    showToast(`Cell (${cell.x}, ${cell.y}) is occupied.`);
    return;
  }
  const frontier = new Set((state.frontier || []).map((item) => coordKey(item.x, item.y)));
  if (!frontier.has(coordKey(cell.x, cell.y))) {
    showToast(`Place within ${state.placementRange || 8} hexes of the current position.`);
    return;
  }

  const index = selected.findIndex((item) => item.x === cell.x && item.y === cell.y);
  if (index >= 0) {
    selected.splice(index, 1);
  } else {
    if (selected.length === 2) {
      selected.shift();
    }
    selected.push(cell);
  }
  syncControls();
  draw();

  if (settings.autoSubmit && selected.length === 2) {
    submitMove();
  }
}

async function submitMove() {
  if (selected.length !== 2 || searchBusy) {
    return;
  }

  const cells = selected.map((cell) => ({ x: cell.x, y: cell.y }));
  selected = [];
  syncControls();
  draw();

  try {
    applyState(await postJson("/api/move", { cells }));
  } catch (error) {
    showToast(error.message);
  }
}

async function startSearch(kind) {
  if (searchBusy) {
    return;
  }
  window.clearTimeout(searchPollTimer);
  searchBusy = true;
  syncControls();

  try {
    const search = await postJson(kind === "move" ? "/api/bot/start" : "/api/analyze/start");
    renderSearchStats(search);
    await pollSearchUntilDone();
    applyState(await getJson("/api/state"));
  } catch (error) {
    showToast(error.message);
  } finally {
    searchBusy = false;
    syncControls();
  }
}

function wait(ms) {
  return new Promise((resolve) => {
    searchPollTimer = window.setTimeout(resolve, ms);
  });
}

async function pollSearchUntilDone() {
  while (true) {
    const search = await getJson("/api/search");
    renderSearchStats(search);
    if (!search.running && !search.threadRunning) {
      return;
    }
    await wait(140);
  }
}

function scheduleAutomation() {
  window.clearTimeout(automationTimer);
  if (!gameStarted || searchBusy || !state || state.gameOver) {
    return;
  }
  if (state.botPending && settings.autoAi) {
    automationTimer = window.setTimeout(() => startSearch("move"), 180);
    return;
  }
  if (state.mode === "human-human" && state.ponder && !state.search?.running) {
    automationTimer = window.setTimeout(() => startSearch("analysis"), 260);
  }
}

async function startNewGame(event) {
  if (event) {
    event.preventDefault();
  }
  if (searchBusy) {
    return;
  }

  selected = [];
  gameStarted = true;
  settings.autoAi = els.setupAutoAiToggle.checked;
  els.autoAiToggle.checked = settings.autoAi;
  try {
    const nextState = await postJson("/api/new", setupPayload());
    els.setupOverlay.classList.add("hidden");
    applyState(nextState);
    centerPieces(false);
  } catch (error) {
    showToast(error.message);
  }
}

async function applyOptions() {
  if (searchBusy) {
    return;
  }
  try {
    applyState(await postJson("/api/options", setupPayload()));
  } catch (error) {
    showToast(error.message);
  }
}

async function undo(steps) {
  if (searchBusy) {
    return;
  }
  try {
    selected = [];
    applyState(await postJson("/api/undo", { steps }));
  } catch (error) {
    showToast(error.message);
  }
}

async function redo() {
  if (searchBusy) {
    return;
  }
  try {
    selected = [];
    applyState(await postJson("/api/redo"));
  } catch (error) {
    showToast(error.message);
  }
}

function resetView() {
  view.panX = 0;
  view.panY = 0;
  view.scale = 1;
  draw();
}

function centerPieces(animateToast = true) {
  if (!state || state.cells.length === 0) {
    resetView();
    return;
  }
  let totalX = 0;
  let totalY = 0;
  for (const cell of state.cells) {
    const unit = cellToUnit(cell.x, cell.y);
    totalX += unit.x;
    totalY += unit.y;
  }
  const size = activeSize();
  view.panX = -(totalX / state.cells.length) * size;
  view.panY = -(totalY / state.cells.length) * size;
  if (animateToast) {
    showToast("Centered on pieces.");
  }
  draw();
}

canvas.addEventListener("pointerdown", (event) => {
  view.down = true;
  view.moved = false;
  view.totalMove = 0;
  view.lastX = event.clientX;
  view.lastY = event.clientY;
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener("pointermove", (event) => {
  const cell = eventToCell(event);
  hoverCell = cell;
  els.coordReadout.textContent = `${cell.x}, ${cell.y}`;

  if (view.down) {
    const dx = event.clientX - view.lastX;
    const dy = event.clientY - view.lastY;
    view.totalMove += Math.abs(dx) + Math.abs(dy);
    if (view.totalMove > 4) {
      view.moved = true;
      view.panX += dx;
      view.panY += dy;
    }
    view.lastX = event.clientX;
    view.lastY = event.clientY;
  }
  draw();
});

canvas.addEventListener("pointerup", (event) => {
  canvas.releasePointerCapture(event.pointerId);
  if (!view.moved) {
    selectCell(eventToCell(event));
  }
  view.down = false;
});

canvas.addEventListener("pointerleave", () => {
  hoverCell = null;
  draw();
});

canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const sx = event.clientX - rect.left;
  const sy = event.clientY - rect.top;
  const oldSize = settings.hexSize * view.scale;
  const worldX = (sx - canvas.clientWidth / 2 - view.panX) / oldSize;
  const worldY = (sy - canvas.clientHeight / 2 - view.panY) / oldSize;

  const factor = event.deltaY < 0 ? 1.08 : 0.92;
  view.scale = Math.max(0.55, Math.min(1.9, view.scale * factor));
  const newSize = settings.hexSize * view.scale;
  view.panX = sx - canvas.clientWidth / 2 - worldX * newSize;
  view.panY = sy - canvas.clientHeight / 2 - worldY * newSize;
  draw();
}, { passive: false });

canvas.addEventListener("contextmenu", (event) => event.preventDefault());

els.setupForm.addEventListener("submit", startNewGame);
els.setupMode.addEventListener("change", syncSetupFields);
els.newGameButton.addEventListener("click", () => {
  syncSetupFromState();
  els.setupOverlay.classList.remove("hidden");
});
els.botButton.addEventListener("click", () => startSearch("move"));
els.analyzeButton.addEventListener("click", () => startSearch("analysis"));
els.commitButton.addEventListener("click", submitMove);
els.clearSelectionButton.addEventListener("click", () => {
  selected = [];
  syncControls();
  draw();
});
els.undoButton.addEventListener("click", () => undo(1));
els.undoRoundButton.addEventListener("click", () => undo(state && state.mode === "human-ai" ? 2 : 1));
els.redoButton.addEventListener("click", redo);
els.resetViewButton.addEventListener("click", resetView);
els.centerPiecesButton.addEventListener("click", () => centerPieces(true));

els.blueDepthInput.addEventListener("input", () => {
  els.blueDepthValue.textContent = els.blueDepthInput.value;
});
els.orangeDepthInput.addEventListener("input", () => {
  els.orangeDepthValue.textContent = els.orangeDepthInput.value;
});
els.sizeSlider.addEventListener("input", () => {
  settings.hexSize = Number(els.sizeSlider.value);
  els.sizeValue.textContent = settings.hexSize;
  draw();
});
els.coordsToggle.addEventListener("change", () => {
  settings.showCoords = els.coordsToggle.checked;
  draw();
});
els.frontierToggle.addEventListener("change", () => {
  settings.showFrontier = els.frontierToggle.checked;
  draw();
});
els.heatToggle.addEventListener("change", () => {
  settings.showHeat = els.heatToggle.checked;
  draw();
});
els.latestToggle.addEventListener("change", () => {
  settings.showLatest = els.latestToggle.checked;
  draw();
});
els.autoSubmitToggle.addEventListener("change", () => {
  settings.autoSubmit = els.autoSubmitToggle.checked;
});
els.autoAiToggle.addEventListener("change", () => {
  settings.autoAi = els.autoAiToggle.checked;
  els.setupAutoAiToggle.checked = settings.autoAi;
  scheduleAutomation();
});

window.addEventListener("resize", resizeCanvas);
syncSetupFields();
resizeCanvas();
loadState().then(syncSetupFromState);
