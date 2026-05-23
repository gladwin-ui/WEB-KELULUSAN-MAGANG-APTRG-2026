/* ============================================================
   Pengumuman Kelulusan Magang APTRG Laboratory 2026
   script.js — NIM lookup logic & UI state management
   ============================================================ */

/* ------------------------------------------------------------
   MOCK DATABASE
   Update this array to add / modify participant records.

   Logic mapping:
     isLulus: true,  isBersyarat: false  →  Lulus
     isLulus: true,  isBersyarat: true   →  Lulus Bersyarat
     isLulus: false, isBersyarat: false  →  Tidak Lulus

   Optional field:
     catatan  →  Custom notes shown on "Lulus Bersyarat" panel
                (falls back to default notes in HTML if omitted)
   ------------------------------------------------------------ */
const pesertaMagang = [
  { nim: "102022300082", isLulus: true,  isBersyarat: false },
  { nim: "102022300083", isLulus: true,  isBersyarat: true,
    catatan: [
      "Melengkapi laporan akhir magang sebelum 30 Juni 2026.",
      "Menghadiri sesi remedial evaluasi praktik (jadwal via email).",
    ]
  },
  { nim: "102022300084", isLulus: false, isBersyarat: false },
  { nim: "102022300085", isLulus: true,  isBersyarat: false },
  { nim: "102022300086", isLulus: true,  isBersyarat: true },
];

/* ------------------------------------------------------------
   DOM REFERENCES
   ------------------------------------------------------------ */
const nimForm        = document.getElementById("nim-form");
const nimInput       = document.getElementById("nim-input");
const inputError     = document.getElementById("input-error");
const btnCek         = document.getElementById("btn-cek");
const confettiContainer = document.getElementById("confetti-container");

const panels = {
  input:       document.getElementById("state-input"),
  lulus:       document.getElementById("state-lulus"),
  bersyarat:   document.getElementById("state-bersyarat"),
  tidakLulus:  document.getElementById("state-tidak-lulus"),
  error:       document.getElementById("state-error"),
};

const nimDisplays = {
  lulus:      document.getElementById("lulus-nim"),
  bersyarat:  document.getElementById("bersyarat-nim"),
  tidakLulus: document.getElementById("tidaklulus-nim"),
};

const bersyaratNotesEl = document.getElementById("bersyarat-notes");

/* Media paths — ganti file di folder assets/ bila punya asli */
const MEDIA = {
  video: "assets/victory-dance.mp4",
  audio: "assets/celebration-sound.mp3",
  audioFallback: "assets/celebration-sound.wav",
  lulusReveal: "assets/celebration-sound1.mp3",
  lulusRevealFallback: "assets/celebration-sound1.wav",
};

const victoryOverlay = document.getElementById("victory-overlay");
const victoryVideos = document.querySelectorAll(".victory-video");
const celebrationAudio = document.getElementById("celebration-audio");
const lulusRevealAudio = document.getElementById("lulus-reveal-audio");
const countdownOverlay = document.getElementById("countdown-overlay");
const countdownNumberEl = document.getElementById("countdown-number");

/* Panel yang pakai countdown 10→1 sebelum pengumuman */
const RESULT_WITH_COUNTDOWN = new Set(["lulus", "bersyarat", "tidakLulus"]);
const COUNTDOWN_START =8;
const COUNTDOWN_TICK_MS = 1000;
const COUNTDOWN_HOLD_ON_ONE_MS = 1000;

let countdownIntervalId = null;
let countdownRevealTimeoutId = null;

/* Track the currently visible panel id */
let activePanelId = "input";

/* ------------------------------------------------------------
   LOOKUP
   ------------------------------------------------------------ */

/**
 * Find a participant by NIM (case-insensitive, trimmed).
 * @param {string} nim
 * @returns {object|undefined}
 */
function findPeserta(nim) {
  const normalized = nim.trim();
  return pesertaMagang.find(
    (p) => p.nim.trim() === normalized
  );
}

/**
 * Determine which result state to show.
 * @param {object} peserta
 * @returns {"lulus"|"bersyarat"|"tidakLulus"}
 */
function resolveResultType(peserta) {
  if (!peserta.isLulus) return "tidakLulus";
  if (peserta.isBersyarat) return "bersyarat";
  return "lulus";
}

/* ------------------------------------------------------------
   UI STATE MANAGEMENT
   ------------------------------------------------------------ */

/**
 * Switch visible panel with fade transition.
 * @param {string} targetId  — key in `panels` object
 * @param {object} [options]
 * @param {string} [options.nim]
 * @param {string[]} [options.catatan]
 */
function showPanel(targetId, options = {}) {
  const currentPanel = panels[activePanelId];
  const nextPanel    = panels[targetId];

  if (!nextPanel || targetId === activePanelId) return;

  // Populate NIM on result panels
  if (options.nim) {
    if (targetId === "lulus")      nimDisplays.lulus.textContent      = options.nim;
    if (targetId === "bersyarat")  nimDisplays.bersyarat.textContent  = options.nim;
    if (targetId === "tidakLulus") nimDisplays.tidakLulus.textContent = options.nim;
  }

  // Custom catatan for Lulus Bersyarat
  if (targetId === "bersyarat" && options.catatan?.length) {
    renderCatatan(options.catatan);
  }

  // Exit current panel
  currentPanel.classList.remove("is-active");
  currentPanel.classList.add("is-exiting");

  const transitionMs = 450;

  setTimeout(() => {
    currentPanel.classList.remove("is-exiting");
    currentPanel.hidden = true;

    nextPanel.hidden = false;
    // Force reflow so the enter animation triggers
    void nextPanel.offsetWidth;
    nextPanel.classList.add("is-active");

    activePanelId = targetId;

    // Celebratory effects for Lulus
    if (targetId === "lulus") {
      launchConfetti();
      startLulusCelebration();
    } else {
      clearConfetti();
      stopLulusCelebration();
    }

    // Scroll to top of card on mobile
    nextPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, transitionMs);
}

/** Reset to the input / landing panel */
function showInputPanel() {
  cancelCountdown();
  clearConfetti();
  stopLulusCelebration();
  nimInput.value = "";
  setFormDisabled(false);
  nimInput.classList.remove("is-invalid");
  hideInputError();
  showPanel("input");
  nimInput.focus();
}

/* ------------------------------------------------------------
   FORM VALIDATION & SUBMIT
   ------------------------------------------------------------ */

function showInputError(message) {
  inputError.textContent = message;
  inputError.hidden = false;
  nimInput.classList.add("is-invalid");
  nimInput.setAttribute("aria-invalid", "true");
}

function hideInputError() {
  inputError.textContent = "";
  inputError.hidden = true;
  nimInput.classList.remove("is-invalid");
  nimInput.removeAttribute("aria-invalid");
}

function setLoading(isLoading) {
  btnCek.disabled = isLoading;
  btnCek.querySelector(".btn-text").hidden = isLoading;
  btnCek.querySelector(".btn-spinner").hidden = !isLoading;
}

nimForm.addEventListener("submit", (e) => {
  e.preventDefault();
  hideInputError();

  const nim = nimInput.value.trim();

  if (!nim) {
    showInputError("NIM wajib diisi.");
    nimInput.focus();
    return;
  }

  if (!/^\d+$/.test(nim)) {
    showInputError("NIM hanya boleh berisi angka.");
    nimInput.focus();
    return;
  }

  setLoading(true);

  // Brief delay simulates a server lookup & lets the spinner show
  setTimeout(() => {
    setLoading(false);

    const peserta = findPeserta(nim);

    if (!peserta) {
      showPanel("error");
      return;
    }

    const resultType = resolveResultType(peserta);

    startCountdownThenReveal(resultType, {
      nim: peserta.nim,
      catatan: peserta.catatan,
    });
  }, 600);
});

/* Clear inline error as user types */
nimInput.addEventListener("input", () => {
  if (!inputError.hidden) hideInputError();
});

/* ------------------------------------------------------------
   BACK BUTTONS
   ------------------------------------------------------------ */
document.querySelectorAll('[data-action="back"]').forEach((btn) => {
  btn.addEventListener("click", showInputPanel);
});

/* ------------------------------------------------------------
   CATATAN (Lulus Bersyarat notes)
   ------------------------------------------------------------ */

/** Re-render the notes list inside the bersyarat panel */
function renderCatatan(items) {
  const list = bersyaratNotesEl.querySelector(".notes-list");
  if (!list) return;
  list.innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

/** Prevent XSS when injecting custom catatan strings */
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/* ------------------------------------------------------------
   CONFETTI ANIMATION (Lulus celebration)
   ------------------------------------------------------------ */

/* Warna confetti mengikuti palet logo APTRG */
const CONFETTI_COLORS = ["#00b4d8", "#33c4e0", "#e85d5d", "#b8b8b8", "#0d9b6e", "#0d1f2d"];

function launchConfetti() {
  clearConfetti();
  const count = 60;

  for (let i = 0; i < count; i++) {
    const piece = document.createElement("div");
    piece.className = "confetti-piece";
    piece.style.left = `${Math.random() * 100}%`;
    piece.style.backgroundColor = CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)];
    piece.style.animationDuration = `${1.8 + Math.random() * 2}s`;
    piece.style.animationDelay = `${Math.random() * 0.8}s`;
    piece.style.width  = `${6 + Math.random() * 8}px`;
    piece.style.height = `${6 + Math.random() * 8}px`;
    piece.style.borderRadius = Math.random() > 0.5 ? "50%" : "2px";
    confettiContainer.appendChild(piece);
  }

  // Auto-remove after animation completes
  setTimeout(clearConfetti, 4500);
}

function clearConfetti() {
  confettiContainer.innerHTML = "";
}

/* ------------------------------------------------------------
   COUNTDOWN (10 → 1) + audio, lalu tampilkan hasil
   ------------------------------------------------------------ */

function setFormDisabled(disabled) {
  nimInput.disabled = disabled;
  btnCek.disabled = disabled;
}

/** Hitung mundur 10→1; musik saat countdown; berhenti di 1 lalu pengumuman */
function startCountdownThenReveal(targetId, options = {}) {
  if (!RESULT_WITH_COUNTDOWN.has(targetId)) {
    showPanel(targetId, options);
    return;
  }

  cancelCountdown();
  setFormDisabled(true);

  let remaining = COUNTDOWN_START;
  countdownNumberEl.textContent = String(remaining);
  countdownNumberEl.classList.remove("countdown-pop");

  countdownOverlay.hidden = false;
  countdownOverlay.setAttribute("aria-hidden", "false");

  playCelebrationAudio();

  countdownIntervalId = setInterval(() => {
    remaining -= 1;
    countdownNumberEl.textContent = String(remaining);
    pulseCountdownNumber();

    if (remaining <= 1) {
      clearInterval(countdownIntervalId);
      countdownIntervalId = null;
      stopCelebrationAudio();

      countdownRevealTimeoutId = setTimeout(() => {
        countdownOverlay.hidden = true;
        countdownOverlay.setAttribute("aria-hidden", "true");
        setFormDisabled(false);
        showPanel(targetId, options);
        countdownRevealTimeoutId = null;
      }, COUNTDOWN_HOLD_ON_ONE_MS);
    }
  }, COUNTDOWN_TICK_MS);
}

function pulseCountdownNumber() {
  countdownNumberEl.classList.remove("countdown-pop");
  void countdownNumberEl.offsetWidth;
  countdownNumberEl.classList.add("countdown-pop");
}

function cancelCountdown() {
  if (countdownIntervalId) {
    clearInterval(countdownIntervalId);
    countdownIntervalId = null;
  }
  if (countdownRevealTimeoutId) {
    clearTimeout(countdownRevealTimeoutId);
    countdownRevealTimeoutId = null;
  }
  if (countdownOverlay) {
    countdownOverlay.hidden = true;
    countdownOverlay.setAttribute("aria-hidden", "true");
  }
  stopCelebrationAudio();
  setFormDisabled(false);
}

/* ------------------------------------------------------------
   LULUS — Video overlay + celebration-sound1 saat popup
   ------------------------------------------------------------ */

/** Tampilkan overlay video & putar celebration-sound1 */
function startLulusCelebration() {
  if (victoryOverlay) {
    victoryOverlay.hidden = false;
    victoryOverlay.setAttribute("aria-hidden", "false");
    victoryOverlay.classList.add("is-active");

    victoryVideos.forEach((video) => {
      video.currentTime = 0;
      const playPromise = video.play();
      if (playPromise?.catch) {
        playPromise.catch(() => { /* autoplay blocked */ });
      }
    });
  }

  playLulusRevealAudio();
}

/** Sembunyikan overlay & hentikan media Lulus */
function stopLulusCelebration() {
  if (victoryOverlay) {
    victoryOverlay.hidden = true;
    victoryOverlay.setAttribute("aria-hidden", "true");
    victoryOverlay.classList.remove("is-active");

    victoryVideos.forEach((video) => {
      video.pause();
      video.currentTime = 0;
    });
  }

  stopCelebrationAudio();
  stopLulusRevealAudio();
}

/** Suara khusus saat pengumuman Lulus muncul */
function playLulusRevealAudio() {
  if (!lulusRevealAudio) return;

  lulusRevealAudio.src = MEDIA.lulusReveal;
  lulusRevealAudio.loop = false;
  lulusRevealAudio.currentTime = 0;

  const tryPlay = () => {
    const p = lulusRevealAudio.play();
    if (p?.catch) {
      p.catch(() => {
        lulusRevealAudio.src = MEDIA.lulusRevealFallback;
        lulusRevealAudio.play().catch(() => {});
      });
    }
  };

  tryPlay();
}

function stopLulusRevealAudio() {
  if (!lulusRevealAudio) return;
  lulusRevealAudio.pause();
  lulusRevealAudio.currentTime = 0;
}

/** Putar audio; fallback ke .wav jika .mp3 tidak ada */
function playCelebrationAudio() {
  if (!celebrationAudio) return;

  celebrationAudio.src = MEDIA.audio;
  celebrationAudio.currentTime = 0;
  celebrationAudio.loop = true;

  const tryPlay = () => {
    const p = celebrationAudio.play();
    if (p?.catch) {
      p.catch(() => {
        celebrationAudio.src = MEDIA.audioFallback;
        celebrationAudio.play().catch(() => { /* user belum berinteraksi */ });
      });
    }
  };

  tryPlay();
}

function stopCelebrationAudio() {
  if (!celebrationAudio) return;
  celebrationAudio.pause();
  celebrationAudio.currentTime = 0;
}

/* ------------------------------------------------------------
   INIT
   ------------------------------------------------------------ */
// Ensure only the input panel is visible on load
Object.entries(panels).forEach(([id, el]) => {
  if (id === "input") {
    el.hidden = false;
    el.classList.add("is-active");
  } else {
    el.hidden = true;
    el.classList.remove("is-active");
  }
});
