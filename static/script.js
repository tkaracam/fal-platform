const uiLang = document.body?.dataset?.uiLang || "tr";

const uiText = {
  tr: {
    closed: "Kapalı Kart",
    selected: "Seçilen kart",
    next: "Sıradaki",
    done: "Tamamlandı",
    chosen: "Seçildi",
    chooseWarn: "Lütfen önce {count} kart seçin.",
    positions: {
      katina: ["Sen", "Partner", "İlişki Enerjisi", "Engel", "Yakın Gelecek", "Tavsiye", "Olası Sonuç"],
      tarot: [
        "Mevcut Durum",
        "Engel / Karşı Etki",
        "Temel Etki",
        "Yakın Geçmiş",
        "Olası Gelişme",
        "Yakın Gelecek",
        "Sen",
        "Çevre",
        "Umutlar / Korkular",
        "Sonuç",
      ],
    },
  },
  en: {
    closed: "Closed Card",
    selected: "Selected cards",
    next: "Next",
    done: "Done",
    chosen: "Chosen",
    chooseWarn: "Please select {count} cards first.",
    positions: {
      katina: ["You", "Partner", "Relationship Energy", "Obstacle", "Near Future", "Advice", "Outcome"],
      tarot: [
        "Current Situation",
        "Challenge / Crossing Energy",
        "Root Influence",
        "Recent Past",
        "Potential Development",
        "Near Future",
        "Self",
        "Environment",
        "Hopes / Fears",
        "Outcome",
      ],
    },
  },
  de: {
    closed: "Verdeckte Karte",
    selected: "Gewählte Karten",
    next: "Nächste",
    done: "Fertig",
    chosen: "Gewählt",
    chooseWarn: "Bitte zuerst {count} Karten auswählen.",
    positions: {
      katina: ["Du", "Partner", "Beziehungsenergie", "Hindernis", "Nächste Phase", "Rat", "Ergebnis"],
      tarot: [
        "Aktuelle Situation",
        "Hindernis / Gegenenergie",
        "Grundenergie",
        "Jüngste Vergangenheit",
        "Mögliche Entwicklung",
        "Nahe Zukunft",
        "Du selbst",
        "Umfeld",
        "Hoffnungen / Ängste",
        "Ergebnis",
      ],
    },
  },
};

const readingConfigs = {
  katina: { deckSize: 65, picksRequired: 7 },
  tarot: { deckSize: 78, picksRequired: 10 },
};

const currentText = uiText[uiLang] || uiText.tr;

function fmt(template, value) {
  return template.replace("{count}", String(value));
}

function initNavbar() {
  const toggle = document.querySelector("[data-nav-toggle]");
  const links = document.querySelector("[data-nav-links]");
  if (!toggle || !links) {
    return;
  }
  const body = document.body;
  const langGroup = links.querySelector("[data-lang-group]");
  const langToggle = links.querySelector("[data-lang-toggle]");
  const langList = links.querySelector("[data-lang-list]");

  function setLangMenuState(isOpen) {
    if (!langGroup || !langToggle || !langList) {
      return;
    }
    langGroup.classList.toggle("is-open", isOpen);
    langToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    langList.hidden = !isOpen;
  }

  function setMenuState(isOpen) {
    links.classList.toggle("is-open", isOpen);
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    if (body) {
      body.classList.toggle("nav-open", isOpen);
    }
    if (!isOpen) {
      setLangMenuState(false);
    }
  }

  setMenuState(false);
  setLangMenuState(false);

  toggle.addEventListener("click", () => {
    const isOpen = !links.classList.contains("is-open");
    setMenuState(isOpen);
  });

  if (langToggle) {
    langToggle.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const isOpen = !langGroup.classList.contains("is-open");
      setLangMenuState(isOpen);
    });
  }

  links.addEventListener("click", (event) => {
    const target = event.target;
    if (target instanceof HTMLElement && (target.tagName === "A" || target.closest("a"))) {
      setMenuState(false);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && links.classList.contains("is-open")) {
      setMenuState(false);
    }
  });
}

function initPhotoGrid() {
  const slots = document.querySelectorAll(".photo-slot input[type='file']");
  if (!slots.length) {
    return;
  }
  slots.forEach((input) => {
    input.addEventListener("change", () => {
      const slot = input.closest(".photo-slot");
      if (!slot) {
        return;
      }
      const file = input.files && input.files[0];
      if (!file) {
        slot.style.backgroundImage = "";
        slot.classList.remove("has-image");
        return;
      }
      const objectUrl = URL.createObjectURL(file);
      slot.style.backgroundImage = `linear-gradient(to top, rgba(0,0,0,.55), rgba(0,0,0,.08)), url('${objectUrl}')`;
      slot.style.backgroundSize = "cover";
      slot.style.backgroundPosition = "center";
      slot.classList.add("has-image");
    });
  });
}

function getUsernameCheckTexts(lang) {
  const map = {
    tr: {
      checking: "Kontrol ediliyor...",
      available: "Kullanıcı adı uygun.",
      taken: "Kullanıcı adı zaten var.",
      tooShort: "Kullanıcı adı en az 3 karakter olmalı.",
    },
    en: {
      checking: "Checking...",
      available: "Username is available.",
      taken: "This username already exists.",
      tooShort: "Username must be at least 3 characters.",
    },
    de: {
      checking: "Wird geprüft...",
      available: "Benutzername ist verfügbar.",
      taken: "Dieser Benutzername existiert bereits.",
      tooShort: "Benutzername muss mindestens 3 Zeichen lang sein.",
    },
  };
  return map[lang] || map.en;
}

function initRegisterUsernameCheck() {
  const form = document.querySelector("form[data-register-form]");
  if (!form) {
    return;
  }
  const usernameInput = form.querySelector("[data-username-input]");
  const statusEl = form.querySelector("[data-username-status]");
  const checkUrl = form.getAttribute("data-username-check-url") || "";
  if (!usernameInput || !statusEl || !checkUrl) {
    return;
  }

  const texts = getUsernameCheckTexts(uiLang);
  let timer = null;
  let requestSeq = 0;
  let availableState = null;

  function setState(kind, msg) {
    statusEl.classList.remove("ok", "bad", "checking");
    usernameInput.classList.remove("username-ok", "username-bad");
    statusEl.textContent = msg || "";
    if (kind) {
      statusEl.classList.add(kind);
    }
    if (kind === "ok") {
      usernameInput.classList.add("username-ok");
    }
    if (kind === "bad") {
      usernameInput.classList.add("username-bad");
    }
  }

  async function checkUsernameNow() {
    const raw = String(usernameInput.value || "").trim().toLowerCase();
    if (raw.length < 3) {
      availableState = false;
      setState("bad", texts.tooShort);
      return;
    }
    setState("checking", texts.checking);
    const current = ++requestSeq;
    try {
      const resp = await fetch(`${checkUrl}?username=${encodeURIComponent(raw)}`, { credentials: "same-origin" });
      if (!resp.ok) {
        return;
      }
      const payload = await resp.json();
      if (current !== requestSeq) {
        return;
      }
      const isAvailable = Boolean(payload && payload.available);
      availableState = isAvailable;
      if (isAvailable) {
        setState("ok", texts.available);
      } else {
        setState("bad", texts.taken);
      }
    } catch (_) {
      // Keep silent on temporary network issues.
    }
  }

  function scheduleCheck() {
    if (timer) {
      clearTimeout(timer);
    }
    timer = setTimeout(checkUsernameNow, 250);
  }

  usernameInput.addEventListener("input", scheduleCheck);
  usernameInput.addEventListener("blur", checkUsernameNow);

  form.addEventListener("submit", async (event) => {
    const raw = String(usernameInput.value || "").trim().toLowerCase();
    usernameInput.value = raw;
    if (raw.length < 3) {
      event.preventDefault();
      availableState = false;
      setState("bad", texts.tooShort);
      usernameInput.focus();
      return;
    }
    if (availableState !== true) {
      event.preventDefault();
      await checkUsernameNow();
      if (availableState !== true) {
        usernameInput.focus();
      } else {
        form.submit();
      }
    }
  });

  if (String(usernameInput.value || "").trim()) {
    checkUsernameNow();
  }
}

function getPasswordMatchTexts(lang) {
  const map = {
    tr: { mismatch: "Şifreler uyuşmuyor." },
    en: { mismatch: "Passwords do not match." },
    de: { mismatch: "Passwörter stimmen nicht überein." },
  };
  return map[lang] || map.en;
}

function initRegisterPasswordConfirm() {
  const form = document.querySelector("form[data-register-form]");
  if (!form) {
    return;
  }
  const passwordInput = form.querySelector("[data-register-password]");
  const confirmInput = form.querySelector("[data-register-password-confirm]");
  const statusEl = form.querySelector("[data-password-status]");
  if (!passwordInput || !confirmInput || !statusEl) {
    return;
  }

  const texts = getPasswordMatchTexts(uiLang);

  function validateMatch() {
    const password = String(passwordInput.value || "");
    const confirm = String(confirmInput.value || "");
    statusEl.classList.remove("bad");
    confirmInput.classList.remove("password-bad");

    if (!confirm) {
      statusEl.textContent = "";
      return true;
    }
    if (password !== confirm) {
      statusEl.textContent = texts.mismatch;
      statusEl.classList.add("bad");
      confirmInput.classList.add("password-bad");
      return false;
    }
    statusEl.textContent = "";
    return true;
  }

  passwordInput.addEventListener("input", validateMatch);
  confirmInput.addEventListener("input", validateMatch);
  confirmInput.addEventListener("blur", validateMatch);

  form.addEventListener("submit", (event) => {
    if (!validateMatch()) {
      event.preventDefault();
      confirmInput.focus();
    }
  });
}

function initHomeHeroSlider() {
  const slider = document.querySelector("[data-home-slider]");
  if (!slider) {
    return;
  }
  const slides = Array.from(slider.querySelectorAll("[data-home-slide]"));
  const prevBtn = slider.querySelector("[data-home-prev]");
  const nextBtn = slider.querySelector("[data-home-next]");
  if (slides.length < 2) {
    return;
  }

  const ANIM_MS = 1080;
  const AUTO_MS = 6000;
  let currentIndex = slides.findIndex((slide) => slide.classList.contains("is-active"));
  if (currentIndex < 0) {
    currentIndex = 0;
    slides[0].classList.add("is-active");
  }
  let animating = false;
  let autoTimer = null;

  function clearMotionClasses(slide) {
    slide.classList.remove(
      "is-entering",
      "is-leaving-to-right",
      "is-leaving-to-left",
      "from-right",
      "from-left",
    );
  }

  function goTo(targetIndex, direction) {
    if (animating || targetIndex === currentIndex) {
      return;
    }
    animating = true;

    const current = slides[currentIndex];
    const next = slides[targetIndex];
    const leaveClass = direction === "left" ? "is-leaving-to-left" : "is-leaving-to-right";
    const fromClass = direction === "left" ? "from-right" : "from-left";

    clearMotionClasses(current);
    clearMotionClasses(next);

    next.classList.remove("is-active");
    next.classList.add(fromClass);

    void next.offsetWidth;
    next.classList.add("is-entering");
    current.classList.add(leaveClass);

    window.setTimeout(() => {
      current.classList.remove("is-active", leaveClass);
      clearMotionClasses(current);
      clearMotionClasses(next);
      next.classList.add("is-active");
      currentIndex = targetIndex;
      animating = false;
    }, ANIM_MS);
  }

  function stepNextAuto() {
    const nextIndex = (currentIndex + 1) % slides.length;
    // Opposite direction: slide to left (new slide enters from right).
    goTo(nextIndex, "left");
  }

  function restartAuto() {
    if (autoTimer) {
      clearInterval(autoTimer);
    }
    autoTimer = window.setInterval(stepNextAuto, AUTO_MS);
  }

  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      const prevIndex = (currentIndex - 1 + slides.length) % slides.length;
      goTo(prevIndex, "right");
      restartAuto();
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      const nextIndex = (currentIndex + 1) % slides.length;
      goTo(nextIndex, "left");
      restartAuto();
    });
  }

  restartAuto();
}

function shuffle(array) {
  const copy = [...array];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function createDeck(readingType) {
  const config = readingConfigs[readingType];
  const deckElement = document.querySelector(`.deck[data-reading="${readingType}"]`);
  const selectionElement = document.querySelector(`.selection[data-selection="${readingType}"]`);
  const form = document.querySelector(`form[data-form="${readingType}"]`);
  const backClass = readingType === "katina" ? "katina-back" : "tarot-back";

  if (!deckElement || !selectionElement || !form || !config) {
    return;
  }
  const positions = currentText.positions[readingType];
  const hiddenInput = form.querySelector("input[name='selected_cards']");

  const deckCards = Array.from({ length: config.deckSize }, (_, index) => `${readingType}-kart-${index + 1}`);
  const shuffled = shuffle(deckCards);
  const picked = [];
  const cardButtons = new Map();
  selectionElement.textContent = `${currentText.selected}: 0/${config.picksRequired}`;

  function syncSelectionState() {
    selectionElement.textContent = `${currentText.selected}: ${picked.length}/${config.picksRequired}${picked.length ? ` - ${currentText.next}: ${positions[picked.length] || currentText.done}` : ""}`;
    if (hiddenInput) {
      hiddenInput.value = JSON.stringify(picked);
    }
  }

  function redrawPickedLabels() {
    picked.forEach((entry, index) => {
      entry.position = positions[index];
      const pickedButton = cardButtons.get(entry.card);
      if (pickedButton) {
        pickedButton.classList.add("picked");
        pickedButton.textContent = "";
      }
    });
  }

  syncSelectionState();

  shuffled.forEach((cardName) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `card-back ${backClass}`;
    button.textContent = "";
    button.setAttribute("aria-label", currentText.closed);
    cardButtons.set(cardName, button);

    button.addEventListener("click", () => {
      if (button.classList.contains("picked")) {
        const removeIndex = picked.findIndex((entry) => entry.card === cardName);
        if (removeIndex === -1) {
          return;
        }
        picked.splice(removeIndex, 1);
        button.classList.remove("picked");
        button.textContent = "";
        redrawPickedLabels();
        syncSelectionState();
        return;
      }
      if (picked.length >= config.picksRequired) {
        return;
      }

      const step = picked.length;
      button.classList.add("picked");
      button.textContent = "";
      picked.push({ position: positions[step], card: cardName });
      syncSelectionState();
    });

    deckElement.appendChild(button);
  });

  form.addEventListener("submit", (event) => {
    if (picked.length !== config.picksRequired) {
      event.preventDefault();
      alert(fmt(currentText.chooseWarn, config.picksRequired));
    }
  });
}

createDeck("katina");
createDeck("tarot");
initNavbar();
initPhotoGrid();
initRegisterUsernameCheck();
initRegisterPasswordConfirm();
initHomeHeroSlider();
