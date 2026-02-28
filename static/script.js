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
      tarot: ["Geçmiş", "Şimdi", "Gelecek"],
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
      tarot: ["Past", "Present", "Future"],
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
      tarot: ["Vergangenheit", "Gegenwart", "Zukunft"],
    },
  },
};

const readingConfigs = {
  katina: { deckSize: 65, picksRequired: 7 },
  tarot: { deckSize: 78, picksRequired: 3 },
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
  toggle.setAttribute("aria-expanded", "false");
  toggle.addEventListener("click", () => {
    const isOpen = links.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
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
  selectionElement.textContent = `${currentText.selected}: 0/${config.picksRequired}`;

  shuffled.forEach((cardName) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `card-back ${backClass}`;
    button.textContent = "";
    button.setAttribute("aria-label", currentText.closed);

    button.addEventListener("click", () => {
      if (picked.length >= config.picksRequired || button.classList.contains("picked")) {
        return;
      }

      const step = picked.length;
      button.classList.add("picked");
      button.textContent = `${currentText.chosen} ${step + 1}`;
      picked.push({ position: positions[step], card: cardName });

      selectionElement.textContent = `${currentText.selected}: ${picked.length}/${config.picksRequired} - ${currentText.next}: ${positions[picked.length] || currentText.done}`;
      hiddenInput.value = JSON.stringify(picked);
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
