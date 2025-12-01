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

function buildPayload(eventType, target, extra = {}) {
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
    value_preview: sanitizeValue(target),
    ...extra
  };
}

function sendBrowserEvent(eventType, target, extra = {}) {
  const payload = buildPayload(eventType, target, extra);

  try {
    RT.runtime.sendMessage(
      {
        type: "browser-event",
        payload
      },
      () => {
        // Antwort ignorieren – Fehler landen im Background/Service Worker
        void 0;
      }
    );
  } catch (e) {
    console.warn("Local Activity Tracker – sendMessage failed", e);
  }
}

/* ---------------- Basis-Events (schon vorhanden) ---------------- */

// Klicks loggen
document.addEventListener(
  "click",
  (e) => {
    sendBrowserEvent("click", e.target);
  },
  true
);

// Eingaben loggen (während der Eingabe)
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

/* ---------------- Erweiterungen für Task-Mining ---------------- */

// Änderungen (Select, Checkbox, Radio etc.)
document.addEventListener(
  "change",
  (e) => {
    const target = e.target;
    const tag = (target.tagName || "").toLowerCase();
    const type = (target.type || "").toLowerCase();

    const extra = {
      change_kind: type || tag || null,
      checked: typeof target.checked === "boolean" ? target.checked : null
    };

    sendBrowserEvent("change", target, extra);
  },
  true
);

// Fokus / Blur von Feldern
document.addEventListener(
  "focus",
  (e) => {
    sendBrowserEvent("focus", e.target);
  },
  true
);

document.addEventListener(
  "blur",
  (e) => {
    sendBrowserEvent("blur", e.target);
  },
  true
);

// Copy / Paste / Cut – ohne Inhalte zu loggen
document.addEventListener(
  "copy",
  (e) => {
    sendBrowserEvent("copy", e.target, { clipboard_operation: "copy" });
  },
  true
);

document.addEventListener(
  "paste",
  (e) => {
    sendBrowserEvent("paste", e.target, { clipboard_operation: "paste" });
  },
  true
);

document.addEventListener(
  "cut",
  (e) => {
    sendBrowserEvent("cut", e.target, { clipboard_operation: "cut" });
  },
  true
);

// Scroll-Events (gedrosselt, damit nicht tausende Events entstehen)
let lastScrollSent = 0;
function handleScroll() {
  const now = Date.now();
  if (now - lastScrollSent < 1000) {
    return; // max. 1 Event / Sekunde
  }
  lastScrollSent = now;

  const target = document.scrollingElement || document.documentElement || document.body;
  const extra = {
    scroll_x: window.scrollX,
    scroll_y: window.scrollY,
    viewport_height: window.innerHeight,
    viewport_width: window.innerWidth,
    document_height: document.documentElement?.scrollHeight || null
  };

  sendBrowserEvent("scroll", target, extra);
}

window.addEventListener("scroll", handleScroll, { capture: true, passive: true });

// Sichtbarkeitswechsel (Tab aktiv / im Hintergrund)
document.addEventListener("visibilitychange", () => {
  sendBrowserEvent("visibilitychange", document, {
    visibility: document.visibilityState
  });
});

// Seite wird verlassen / neu geladen
window.addEventListener("beforeunload", () => {
  sendBrowserEvent("before_unload", document);
});
