/* Shared deterministic visual components. No timers or network assets are used. */
(function () {
  "use strict";

  const PALETTE = Object.freeze({
    space: "#070B14", panel: "#0D1424", card: "#111A2E",
    cyan: "#00E5FF", purple: "#8B5CF6", text: "#E6EDF7", muted: "#8A97B0",
    red: "#FF4D5E", yellow: "#FFB830", green: "#2EE6A8"
  });
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const easeOut = v => 1 - Math.pow(1 - clamp(v), 3);
  const easeInOut = v => v < .5 ? 4 * v * v * v : 1 - Math.pow(-2 * v + 2, 3) / 2;

  function seededRandom(seed) {
    let s = seed >>> 0;
    return function () {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }

  class SpaceField {
    constructor(canvas, options = {}) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.width = options.width || 1920;
      this.height = options.height || 1080;
      this.count = options.count || 105;
      this.speed = options.speed || 1;
      this.seed = options.seed || 20261109;
      canvas.width = this.width;
      canvas.height = this.height;
      const rnd = seededRandom(this.seed);
      this.particles = Array.from({ length: this.count }, (_, i) => ({
        x: rnd() * this.width,
        y: rnd() * this.height,
        r: 1.2 + rnd() * 3.6,
        phase: rnd() * Math.PI * 2,
        drift: 8 + rnd() * 22,
        color: i % 7 === 0 ? PALETTE.purple : (i % 3 === 0 ? PALETTE.cyan : PALETTE.muted),
        alpha: .12 + rnd() * .36
      }));
    }
    render(t) {
      const c = this.ctx;
      c.clearRect(0, 0, this.width, this.height);
      for (const p of this.particles) {
        const x = p.x + Math.sin(t * .17 * this.speed + p.phase) * p.drift;
        const y = p.y + Math.cos(t * .12 * this.speed + p.phase) * p.drift * .65;
        const breathe = .72 + .28 * Math.sin(t * .48 + p.phase);
        c.globalAlpha = p.alpha * breathe;
        c.fillStyle = p.color;
        c.shadowColor = p.color;
        c.shadowBlur = p.r > 3 ? 13 : 5;
        c.beginPath();
        c.arc(x, y, p.r, 0, Math.PI * 2);
        c.fill();
      }
      c.globalAlpha = 1;
      c.shadowBlur = 0;
    }
  }

  function neonText(text, options = {}) {
    const span = document.createElement("span");
    span.className = options.className || "neon-text";
    span.setAttribute("aria-label", text);
    Array.from(text).forEach((char, i) => {
      const item = document.createElement("span");
      item.className = "neon-char";
      item.textContent = char === " " ? "\u00A0" : char;
      item.dataset.index = i;
      span.appendChild(item);
    });
    return span;
  }

  function revealText(element, t, options = {}) {
    const start = options.start || 0;
    const perChar = options.perChar || .09;
    const duration = options.duration || .52;
    const distance = options.distance === undefined ? 28 : options.distance;
    const chars = element.querySelectorAll(".neon-char");
    chars.forEach((char, i) => {
      const p = easeOut((t - start - i * perChar) / duration);
      char.style.opacity = p.toFixed(3);
      char.style.transform = `translate3d(0, ${((1 - p) * distance).toFixed(2)}px, 0)`;
    });
  }

  function dataCard(options = {}) {
    const card = document.createElement("section");
    card.className = "data-card";
    card.style.setProperty("--card-accent", options.accent || PALETTE.cyan);
    if (options.className) card.classList.add(...options.className.split(/\s+/));
    if (options.label) {
      const label = document.createElement("div");
      label.className = "data-card-label text-secondary";
      label.textContent = options.label;
      card.appendChild(label);
    }
    if (options.value !== undefined) {
      const value = document.createElement("div");
      value.className = "data-card-value neon-number";
      value.textContent = options.value;
      card.appendChild(value);
    }
    if (options.unit) {
      const unit = document.createElement("div");
      unit.className = "data-card-unit";
      unit.textContent = options.unit;
      card.appendChild(unit);
    }
    return card;
  }

  function comparisonBars(items = []) {
    const root = document.createElement("div");
    root.className = "comparison-bars";
    items.forEach(item => {
      const row = document.createElement("div");
      row.className = "comparison-row";
      row.style.setProperty("--bar-color", item.color || PALETTE.cyan);
      const dot = document.createElement("span");
      dot.className = "comparison-dot";
      const track = document.createElement("span");
      track.className = "comparison-track";
      const fill = document.createElement("span");
      fill.className = "comparison-fill";
      fill.style.transform = `scaleX(${clamp(item.value === undefined ? .7 : item.value)})`;
      track.appendChild(fill);
      row.append(dot, track);
      root.appendChild(row);
    });
    return root;
  }

  function riskLegend() {
    const root = document.createElement("div");
    root.className = "risk-legend";
    root.setAttribute("aria-label", "风险分级：红、黄、绿");
    [PALETTE.red, PALETTE.yellow, PALETTE.green].forEach(color => {
      const swatch = document.createElement("span");
      swatch.className = "risk-swatch";
      swatch.style.setProperty("--swatch", color);
      root.appendChild(swatch);
    });
    return root;
  }

  class TransitionFX {
    constructor(root) {
      this.root = root;
      this.scan = root.querySelector(".transition-scan");
      this.flash = root.querySelector(".transition-flash");
    }
    static create(parent) {
      const root = document.createElement("div");
      root.className = "transition-fx";
      root.innerHTML = '<div class="transition-scan"></div><div class="transition-flash"></div>';
      parent.appendChild(root);
      return new TransitionFX(root);
    }
    render(t, start, duration = .3) {
      duration = Math.min(.3, duration);
      const p = clamp((t - start) / duration);
      const active = t >= start && t <= start + duration;
      const envelope = active ? Math.sin(Math.PI * p) : 0;
      this.scan.style.opacity = active ? (.58 * envelope).toFixed(3) : "0";
      this.scan.style.transform = `translateY(${(p * 1090 - 12).toFixed(1)}px)`;
      /* One soft luminance pulse only; maximum opacity is deliberately restrained. */
      this.flash.style.opacity = active ? (.17 * Math.sin(Math.PI * clamp(p * 1.25))).toFixed(3) : "0";
    }
  }

  class SubtitleTrack {
    constructor(element, cues) {
      this.element = element;
      this.cues = cues;
      this.last = "";
    }
    render(t) {
      const cue = this.cues.find(item => t >= item.start && t < item.end);
      const value = cue ? cue.text : "";
      if (value !== this.last) {
        this.element.textContent = value;
        this.last = value;
      }
    }
  }

  function fitStage(stage, viewportWidth, viewportHeight) {
    const scale = Math.min(viewportWidth / 1920, viewportHeight / 1080);
    stage.style.transform = `scale(${scale})`;
    stage.style.left = `${(viewportWidth - 1920 * scale) / 2}px`;
    stage.style.top = `${(viewportHeight - 1080 * scale) / 2}px`;
  }

  window.NeonUI = {
    PALETTE, clamp, easeOut, easeInOut, seededRandom,
    SpaceField, neonText, revealText, dataCard, comparisonBars, riskLegend,
    TransitionFX, SubtitleTrack, fitStage
  };
})();
