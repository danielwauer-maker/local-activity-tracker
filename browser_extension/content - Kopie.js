// content.js

// Browser-Kompatibilität (Manifest V3, Chrome/Edge/Firefox)
const RT = typeof chrome !== "undefined" ? chrome : browser;

function sanitizeValue(target) {
  try {
    if (!target) return null;

    const tag = (target.tagName || "").toLowerCase();
    const type = (target.type || "").toLowerCase();

    // Niemals Passwörter loggen
    if (type === "password") {
      return null;
    }

    // Klassische Textfelder → nur Vorschau (z. B. 30 Zeichen)
    if (
      type === "text" ||
      type === "email" ||
      type === "search" ||
      type === "url" ||
      tag === "textarea"
    ) {
      const val = target.value || "";
      if (!val) return null;
      return val.substring(0, 30);
    }

    // Buttons oder Links → sichtbarer Text
    if (tag === "button" || tag === "a" || type === "submit") {
      const text = target.innerText || target.textContent || "";
      if (!text) return null;
      return text.substring(0, 80);
    }

    return null;
  } catch (e) {
    return null;
  }
}

function getLabelFor(target) {
  try {
    if (!target || !target.id) return null;
    const lbl = document.querySelector(`label[for="${target.id}"]`);
    if (lbl) {
      const text = lbl.innerText || lbl.textContent || "";
      return text.substring(0, 80);
    }
    return null;
  } catch (e) {
    return null;
  }
}

function buildPayload(eventType, target) {
  return {
    timestamp: new Date().toISOString(),
    url: window.location.href,
    title: document.title,
    event_type: eventType,
    element_tag: target?.tagName || null,
    element_type: target?.type || null,
    element_id: target?.id || null,
    element_name: target?.name || null,
    element_label: getLabelFor(target),
    value_preview: sanitizeValue(target)
  };
}

function sendBrowserEvent(eventType, target) {
  const payload = buildPayload(eventType, target);

  try {
    RT.runtime.sendMessage(
      {
        type: "browser-event",
        payload
      },
      () => {
        // Antwort ignorieren – Fehler landen im Background/Service Worker
        // Optional: RT.runtime.lastError auslesen, wenn du Debug willst
      }
    );
  } catch (e) {
    // Falls auf speziellen internen Seiten kein Messaging möglich ist
    // (meist laufen dort ohnehin keine Content Scripts)
    console.warn("Local Activity Tracker – sendMessage failed", e);
  }
}

// Klicks loggen
document.addEventListener(
  "click",
  (e) => {
    sendBrowserEvent("click", e.target);
  },
  true
);

// Eingaben loggen
document.addEventListener(
  "input",
  (e) => {
    sendBrowserEvent("input", e.target);
  },
  true
);

// Formular-Submits loggen
document.addEventListener(
  "submit",
  (e) => {
    sendBrowserEvent("submit", e.target);
  },
  true
);
