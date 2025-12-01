const BACKEND_URL = "http://127.0.0.1:8000/events";

function sendBrowserEvent(type, details) {
  const payload = {
    timestamp: new Date().toISOString(),
    source: "browser",
    type: type,
    payload: {
      url: details.url || null,
      title: details.title || null,
      tab_id: details.tabId || null,
      window_id: details.windowId || null,
    },
  };

  fetch(BACKEND_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  }).catch((err) => {
    console.warn("Local Activity Tracker – sendBrowserEvent failed", err);
  });
}

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (!tab.url || tab.url.startsWith("chrome://")) return;

    sendBrowserEvent("tab_activated", {
      url: tab.url,
      title: tab.title,
      tabId: tab.id,
      windowId: tab.windowId,
    });
  } catch (e) {
    console.warn("Local Activity Tracker – onActivated error", e);
  }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status !== "complete") return;
  if (!tab.url || tab.url.startsWith("chrome://")) return;

  sendBrowserEvent("page_loaded", {
    url: tab.url,
    title: tab.title,
    tabId: tab.id,
    windowId: tab.windowId,
  });
});

// Events aus dem Content Script verarbeiten
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  try {
    if (!message || message.type !== "browser-event") {
      return; // andere Messages ignorieren
    }

    const payload = message.payload || {};
    const tabId = sender.tab?.id || null;
    const windowId = sender.tab?.windowId || null;

    // Wir verwenden denselben Backend-Endpunkt wie für tab_activated / page_loaded
    sendBrowserEvent("browser_dom_event", {
      url: payload.url,
      title: payload.title,
      tabId,
      windowId
    });

    // Du könntest hier auch mehr Details aus payload nach hinten durchreichen
    // z. B. event_type, element_tag, value_preview etc.
    // sendBrowserEvent("browser_dom_event", { ...payload, tabId, windowId });

    sendResponse({ ok: true });
  } catch (e) {
    console.warn("Local Activity Tracker – onMessage error", e);
    sendResponse({ ok: false, error: e?.message || String(e) });
  }

  // Kein asynchrones sendResponse → false zurückgeben
  return false;
});

// background.js – Manifest V3 Service Worker

const BACKEND_URL = "http://127.0.0.1:8000/events";

async function sendBrowserEvent(type, details) {
  const payload = {
    timestamp: new Date().toISOString(),
    source: "browser",
    type: type,
    payload: {
      url: details.url || null,
      title: details.title || null,
      tab_id: details.tabId || null,
      window_id: details.windowId || null,
      dom_event: details.domEvent || null,  // für Content-Script-Details
    },
  };

  try {
    await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn("Local Activity Tracker – sendBrowserEvent failed:", err);
  }
}

// ----------------------------------------
// TAB ACTIVATED
// ----------------------------------------
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (!tab.url || tab.url.startsWith("chrome://")) return;

    sendBrowserEvent("tab_activated", {
      url: tab.url,
      title: tab.title,
      tabId: tab.id,
      windowId: tab.windowId,
    });
  } catch (e) {
    console.warn("Local Activity Tracker – onActivated error", e);
  }
});

// ----------------------------------------
// PAGE LOADED
// ----------------------------------------
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status !== "complete") return;
  if (!tab.url || tab.url.startsWith("chrome://")) return;

  sendBrowserEvent("page_loaded", {
    url: tab.url,
    title: tab.title,
    tabId: tab.id,
    windowId: tab.windowId,
  });
});

// ----------------------------------------
// DOM-/Input-Events aus content.js
// ----------------------------------------
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  try {
    if (!message || message.type !== "browser-event") {
      return;
    }

    const payload = message.payload || {};
    const tabId = sender.tab?.id || null;
    const windowId = sender.tab?.windowId || null;

    const domEvent = { ...payload };

    sendBrowserEvent(payload.event_type || "browser_dom_event", {
      url: payload.url,
      title: payload.title,
      tabId,
      windowId,
      domEvent,
    });

    sendResponse({ ok: true });
  } catch (e) {
    console.warn("Local Activity Tracker – onMessage error", e);
    sendResponse({ ok: false, error: e?.message || String(e) });
  }

  // keine asynchrone Antwort
  return false;
});

// ----------------------------------------
// Heartbeat – prüft, ob Extension noch „lebt“
// ----------------------------------------
function sendHeartbeat() {
  sendBrowserEvent("browser_heartbeat", {
    url: null,
    title: null,
    tabId: null,
    windowId: null,
    domEvent: null,
  });
}

// alle 30 Sekunden ein Lebenszeichen
setInterval(sendHeartbeat, 30_000);

