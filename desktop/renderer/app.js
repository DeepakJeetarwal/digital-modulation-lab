
const $ = (id) => document.getElementById(id);

const schemeControl = $("scheme");
const snrControl = $("snr");
const bitsControl = $("bits");
const runButton = $("runButton");

let latestResult = null;
let running = false;
let resizeFrame = null;

const palette = {
  "BPSK": "#71866B",
  "QPSK": "#7895A5",
  "8-PSK": "#B98159",
  "16-QAM": "#A18CB7",
};

const COLORS = {
  background: "#FCFBF8",
  grid: "#EAE6DE",
  axis: "#77796F",
  text: "#45483F",
  muted: "#858479",
  error: "#B4533C",
  theory: "#45483F",
};

function updateLabels() {
  $("snrValue").textContent = `${snrControl.value} dB`;
  $("metricSnr").textContent = `${snrControl.value} dB`;
  $("metricScheme").textContent = schemeControl.value;
  $("constellationSubtitle").textContent =
    `Transmitted and received I/Q symbols · ${snrControl.value} dB`;
}

function showMessage(element, message, isError = false) {
  element.replaceChildren();

  const p = document.createElement("p");
  p.textContent = message;
  p.style.color = isError ? COLORS.error : COLORS.muted;
  p.style.padding = "20px";
  element.appendChild(p);
}

function createCanvas(element, height) {
  element.replaceChildren();

  const canvas = document.createElement("canvas");
  canvas.style.width = "100%";
  canvas.style.height = `${height}px`;
  canvas.style.display = "block";
  canvas.style.minWidth = "0";

  element.appendChild(canvas);

  const width = Math.max(element.clientWidth - 4, 320);
  const ratio = Math.min(window.devicePixelRatio || 1, 2);

  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);

  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);

  return { canvas, ctx, width, height };
}

// Abramowitz-Stegun approximation for the complementary error function.
// Accuracy is sufficient for a visual theoretical BER reference.
function erfc(x) {
  const z = Math.abs(x);
  const t = 1 / (1 + 0.5 * z);

  const answer = t * Math.exp(
    -z * z - 1.26551223 +
    t * (
      1.00002368 +
      t * (
        0.37409196 +
        t * (
          0.09678418 +
          t * (
            -0.18628806 +
            t * (
              0.27886807 +
              t * (
                -1.13520398 +
                t * (
                  1.48851587 +
                  t * (
                    -0.82215223 +
                    t * 0.17087277
                  )
                )
              )
            )
          )
        )
      )
    )
  );

  return x >= 0 ? answer : 2 - answer;
}

function qFunction(x) {
  return 0.5 * erfc(x / Math.SQRT2);
}

function theoreticalBER(scheme, ebn0Db) {
  const gamma = Math.pow(10, ebn0Db / 10);

  if (scheme === "BPSK" || scheme === "QPSK") {
    return qFunction(Math.sqrt(2 * gamma));
  }

  if (scheme === "8-PSK") {
    // Standard nearest-neighbour approximation for Gray-coded M-PSK.
    const k = 3;
    const m = 8;
    return Math.min(
      0.5,
      (2 / k) *
        qFunction(
          Math.sqrt(2 * k * gamma) * Math.sin(Math.PI / m)
        )
    );
  }

  if (scheme === "16-QAM") {
    // Standard Gray-coded square M-QAM BER approximation.
    const m = 16;
    const k = 4;
    return Math.min(
      0.5,
      (4 / k) *
        (1 - 1 / Math.sqrt(m)) *
        qFunction(
          Math.sqrt((3 * k * gamma) / (m - 1))
        )
    );
  }

  return null;
}

function drawBERChart(data) {
  const container = $("berChart");
  const { ctx, width, height } = createCanvas(container, 390);

  const margin = { left: 70, right: 20, top: 28, bottom: 100 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;

  const minLog = -6;
  const maxLog = 0;

  const x = (value) => margin.left + (value / 20) * plotW;
  const y = (ber) => {
    const safe = Math.max(1e-6, Math.min(1, ber));
    const logValue = Math.log10(safe);
    return margin.top +
      ((maxLog - logValue) / (maxLog - minLog)) * plotH;
  };

  ctx.fillStyle = COLORS.background;
  ctx.fillRect(0, 0, width, height);
  ctx.font = "11px Segoe UI, sans-serif";
  ctx.lineWidth = 1;

  // Horizontal logarithmic grid.
  for (let decade = 0; decade <= 6; decade++) {
    const value = Math.pow(10, -decade);
    const yy = y(value);

    ctx.strokeStyle = COLORS.grid;
    ctx.beginPath();
    ctx.moveTo(margin.left, yy);
    ctx.lineTo(width - margin.right, yy);
    ctx.stroke();

    ctx.fillStyle = COLORS.axis;
    ctx.textAlign = "right";
    ctx.fillText(`10⁻${decade}`, margin.left - 10, yy + 4);
  }

  // Vertical SNR grid.
  for (let snr = 0; snr <= 20; snr += 2) {
    const xx = x(snr);

    ctx.strokeStyle = "#F0EDE6";
    ctx.beginPath();
    ctx.moveTo(xx, margin.top);
    ctx.lineTo(xx, margin.top + plotH);
    ctx.stroke();

    ctx.fillStyle = COLORS.axis;
    ctx.textAlign = "center";
    ctx.fillText(String(snr), xx, margin.top + plotH + 18);
  }

  // Axis labels.
  ctx.fillStyle = COLORS.text;
  ctx.font = "12px Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Eb/N0 (dB)", margin.left + plotW / 2, height - 60);

  ctx.save();
  ctx.translate(17, margin.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Bit Error Rate (BER)", 0, 0);
  ctx.restore();

  // Draw measured curves. Zero BER points are shown at the chart floor.
  // A floor marker means "below 10^-6 / zero observed errors", not true BER.
  for (const [scheme, result] of Object.entries(data.curves)) {
    const color = palette[scheme] || COLORS.text;

    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 2.2;
    ctx.setLineDash([]);

    ctx.beginPath();

    result.snr.forEach((snr, i) => {
      const raw = result.ber[i];
      const ber = raw === null || raw === undefined ? 0 : raw;
      const xx = x(snr);
      const yy = y(ber > 0 ? ber : 1e-6);

      if (i === 0) {
        ctx.moveTo(xx, yy);
      } else {
        ctx.lineTo(xx, yy);
      }
    });

    ctx.stroke();

    result.snr.forEach((snr, i) => {
      const raw = result.ber[i];
      const ber = raw === null || raw === undefined ? 0 : raw;
      const xx = x(snr);
      const yy = y(ber > 0 ? ber : 1e-6);

      ctx.beginPath();

      if (ber === 0) {
        // Downward triangle denotes zero observed errors.
        ctx.moveTo(xx, yy + 4);
        ctx.lineTo(xx - 4, yy - 3);
        ctx.lineTo(xx + 4, yy - 3);
        ctx.closePath();
      } else {
        ctx.arc(xx, yy, 3, 0, Math.PI * 2);
      }

      ctx.fill();
    });
  }

  // Theoretical reference for the currently selected scheme.
  const selected = data.selected_scheme;
  const theorySnr = Array.from(
    { length: 41 },
    (_, i) => i * 0.5
  );

  ctx.strokeStyle = COLORS.theory;
  ctx.lineWidth = 1.8;
  ctx.setLineDash([6, 4]);
  ctx.beginPath();

  theorySnr.forEach((snr, i) => {
    const ber = theoreticalBER(selected, snr);
    const xx = x(snr);
    const yy = y(ber);

    if (i === 0) {
      ctx.moveTo(xx, yy);
    } else {
      ctx.lineTo(xx, yy);
    }
  });

  ctx.stroke();
  ctx.setLineDash([]);

  // Compact legend below the chart.
  const legendItems = [
    ...Object.keys(data.curves).map((scheme) => ({
      label: scheme,
      color: palette[scheme],
      dashed: false,
    })),
    {
      label: `${selected} theory`,
      color: COLORS.theory,
      dashed: true,
    },
  ];

  const itemWidths = legendItems.map(
    (item) => 25 + item.label.length * 6.4
  );
  const totalWidth = itemWidths.reduce((a, b) => a + b, 0) + 12;
  let legendX = Math.max(12, (width - totalWidth) / 2);
  const legendY = height - 36;

  ctx.font = "10px Segoe UI, sans-serif";
  ctx.textAlign = "left";

  legendItems.forEach((item, index) => {
    ctx.strokeStyle = item.color;
    ctx.fillStyle = item.color;
    ctx.lineWidth = 2;
    ctx.setLineDash(item.dashed ? [4, 3] : []);

    ctx.beginPath();
    ctx.moveTo(legendX, legendY - 3);
    ctx.lineTo(legendX + 14, legendY - 3);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = COLORS.text;
    ctx.fillText(item.label, legendX + 18, legendY);

    legendX += itemWidths[index];
  });

  // Small explanatory note.
  ctx.fillStyle = COLORS.muted;
  ctx.font = "10px Segoe UI, sans-serif";
  ctx.textAlign = "left";
  ctx.fillText(
    "Triangles at 10⁻⁶ indicate zero observed errors.",
    margin.left,
    height - 8
  );
}

function drawConstellation(data) {
  const container = $("constellationChart");
  const { ctx, width, height } = createCanvas(container, 330);

  const margin = 36;
  const plotSize = Math.max(
    100,
    Math.min(width - margin * 2, height - margin * 2 - 15)
  );

  const left = (width - plotSize) / 2;
  const top = (height - plotSize) / 2 - 5;

  const constellation = data.constellation;
  const allValues = [
    ...constellation.rx_i,
    ...constellation.rx_q,
    ...constellation.tx_i,
    ...constellation.tx_q,
  ];

  const maxAbs = Math.max(
    1.5,
    ...allValues.map((v) => Math.abs(v))
  ) * 1.08;

  const px = (v) =>
    left + ((v + maxAbs) / (2 * maxAbs)) * plotSize;

  const py = (v) =>
    top + ((maxAbs - v) / (2 * maxAbs)) * plotSize;

  ctx.fillStyle = COLORS.background;
  ctx.fillRect(0, 0, width, height);

  // Grid.
  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;

  for (let i = 0; i <= 4; i++) {
    const pos = left + (i / 4) * plotSize;
    const ypos = top + (i / 4) * plotSize;

    ctx.beginPath();
    ctx.moveTo(pos, top);
    ctx.lineTo(pos, top + plotSize);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(left, ypos);
    ctx.lineTo(left + plotSize, ypos);
    ctx.stroke();
  }

  // I and Q axes.
  ctx.strokeStyle = "#A8A69B";
  ctx.lineWidth = 1.3;
  ctx.beginPath();
  ctx.moveTo(px(0), top);
  ctx.lineTo(px(0), top + plotSize);
  ctx.moveTo(left, py(0));
  ctx.lineTo(left + plotSize, py(0));
  ctx.stroke();

  // Received symbols.
  ctx.fillStyle = palette[data.selected_scheme] || COLORS.text;
  ctx.globalAlpha = 0.52;

  constellation.rx_i.forEach((value, i) => {
    ctx.beginPath();
    ctx.arc(
      px(value),
      py(constellation.rx_q[i]),
      2,
      0,
      Math.PI * 2
    );
    ctx.fill();
  });

  ctx.globalAlpha = 1;

  // Ideal transmitted symbols.
  ctx.fillStyle = "#B98159";

  constellation.tx_i.forEach((value, i) => {
    ctx.beginPath();
    ctx.arc(
      px(value),
      py(constellation.tx_q[i]),
      3.5,
      0,
      Math.PI * 2
    );
    ctx.fill();
  });

  // Axis labels.
  ctx.fillStyle = COLORS.text;
  ctx.font = "10px Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("In-phase (I)", left + plotSize / 2, height - 5);

  ctx.save();
  ctx.translate(12, top + plotSize / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Quadrature (Q)", 0, 0);
  ctx.restore();

  // Legend.
  const legendY = 15;
  ctx.fillStyle = "#B98159";
  ctx.beginPath();
  ctx.arc(width / 2 - 66, legendY, 3.5, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = COLORS.text;
  ctx.textAlign = "left";
  ctx.fillText("Ideal", width / 2 - 58, legendY + 4);

  ctx.fillStyle = palette[data.selected_scheme] || COLORS.text;
  ctx.beginPath();
  ctx.arc(width / 2 + 5, legendY, 3.5, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = COLORS.text;
  ctx.fillText("Received", width / 2 + 13, legendY + 4);
}

function drawBits(data) {
  const container = $("bitResults");
  container.replaceChildren();

  const tx = data.bits.tx;
  const rx = data.bits.rx;

  const heading = document.createElement("div");
  heading.className = "bit-grid";

  const txLabel = document.createElement("strong");
  txLabel.textContent = "TX";

  const rxLabel = document.createElement("strong");
  rxLabel.textContent = "RX";

  heading.append(txLabel, rxLabel);

  const values = document.createElement("div");
  values.className = "bit-values";

  let shownErrors = 0;

  for (let i = 0; i < tx.length; i++) {
    const txCell = document.createElement("span");
    txCell.textContent = tx[i];
    txCell.className = "bit-cell";

    const rxCell = document.createElement("span");
    rxCell.textContent = rx[i];
    rxCell.className = "bit-cell";

    if (tx[i] !== rx[i]) {
      rxCell.classList.add("bit-error");
      shownErrors++;
    }

    values.append(txCell, rxCell);
  }

  const legend = document.createElement("p");
  legend.className = "bit-legend";
  legend.textContent =
    `Red cells indicate errors · ${shownErrors} errors in the displayed ${tx.length} bits`;

  container.append(heading, values, legend);
}

async function runSimulation() {
  if (running) return;

  running = true;
  runButton.disabled = true;
  runButton.textContent = "Running simulation…";

  showMessage($("berChart"), "Calculating BER curves…");
  showMessage($("constellationChart"), "Generating received symbols…");
  showMessage($("bitResults"), "Comparing transmitted and received bits…");

  try {
    const response = await window.simulationAPI.run({
      schemes: ["BPSK", "QPSK", "8-PSK", "16-QAM"],
      scheme: schemeControl.value,
      snr: Number(snrControl.value),
      num_bits: Number(bitsControl.value),
      seed: 42,
    });

    if (!response.ok) {
      throw new Error(response.error || "Simulation failed.");
    }

    latestResult = response;

    $("metricSnr").textContent = `${response.snr} dB`;
    $("metricScheme").textContent = response.selected_scheme;
    $("metricBer").textContent = response.ber.toExponential(3);
    $("metricErrors").textContent =
      `${response.errors.toLocaleString()} / ${response.num_bits.toLocaleString()}`;

    updateLabels();
    drawBERChart(response);
    drawConstellation(response);
    drawBits(response);
  } catch (error) {
    showMessage(
      $("berChart"),
      error.message || "Simulation failed.",
      true
    );
    showMessage(
      $("constellationChart"),
      "Unable to draw constellation.",
      true
    );
    showMessage(
      $("bitResults"),
      "Unable to display bit comparison.",
      true
    );
  } finally {
    running = false;
    runButton.disabled = false;
    runButton.textContent = "Run simulation ↗";
  }
}

schemeControl.addEventListener("change", updateLabels);

snrControl.addEventListener("input", updateLabels);

document.querySelectorAll("[data-snr]").forEach((button) => {
  button.addEventListener("click", () => {
    snrControl.value = button.dataset.snr;
    updateLabels();
  });
});

runButton.addEventListener("click", runSimulation);

window.addEventListener("resize", () => {
  if (!latestResult) return;

  if (resizeFrame !== null) {
    cancelAnimationFrame(resizeFrame);
  }

  resizeFrame = requestAnimationFrame(() => {
    if (latestResult) {
      drawBERChart(latestResult);
      drawConstellation(latestResult);
    }
    resizeFrame = null;
  });
});

updateLabels();
