// background.js

// Browser-Kompatibilität (Chrome/Edge: chrome, Firefox: browser)
const RT = typeof browser !== "undefined" ? browser : chrome;

function sendToBackend(payload) {
  // Falls dein Backend unter anderer Adresse läuft, hier anpassen
  const url = "http://127.0.0.1:8000/browser-events/";

  fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  }).catch(() => {
    // Backend nicht erreichbar → stillschweigend ignorieren
  });
}

// Nachrichten vom Content-Script verarbeiten
RT.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message && message.type === "browser-event") {
    sendToBackend(message.payload);
  }

  // Keine Antwort nötig
  return false;
});
