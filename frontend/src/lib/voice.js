/**
 * Voice alerts using browser Web Speech API.
 * Stored settings in localStorage. No external API keys.
 */

const KEY = "xauusd.voice.settings.v1";

const defaultSettings = {
  enabled: true,
  voiceURI: "",        // browser voice URI; empty = first ES voice
  rate: 1.0,
  pitch: 1.0,
  volume: 1.0,
  lang: "es",          // prefer Spanish voices
  alertTypes: {
    new_signal: true,
    take_now: true,
    take_profit: true,
    stop_loss: true,
    reversal: true,
    wait: false,       // off by default; less critical
  },
};

export function loadVoiceSettings() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...defaultSettings };
    return { ...defaultSettings, ...JSON.parse(raw) };
  } catch {
    return { ...defaultSettings };
  }
}

export function saveVoiceSettings(s) {
  localStorage.setItem(KEY, JSON.stringify(s));
}

export function getVoices() {
  if (typeof window === "undefined" || !window.speechSynthesis) return [];
  return window.speechSynthesis.getVoices();
}

export function listSpanishVoices() {
  const all = getVoices();
  // Spanish first, then others
  const es = all.filter((v) => (v.lang || "").toLowerCase().startsWith("es"));
  const others = all.filter((v) => !(v.lang || "").toLowerCase().startsWith("es"));
  return [...es, ...others];
}

let initialized = false;
const listeners = new Set();
export function onVoicesChanged(cb) {
  if (typeof window === "undefined" || !window.speechSynthesis) return () => {};
  listeners.add(cb);
  if (!initialized) {
    initialized = true;
    window.speechSynthesis.onvoiceschanged = () => {
      listeners.forEach((fn) => fn(getVoices()));
    };
    // Trigger initial load
    setTimeout(() => listeners.forEach((fn) => fn(getVoices())), 50);
  }
  return () => listeners.delete(cb);
}

export function speak(text, settings) {
  if (!settings?.enabled) return;
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    const voices = getVoices();
    if (settings.voiceURI) {
      const found = voices.find((v) => v.voiceURI === settings.voiceURI);
      if (found) u.voice = found;
    } else {
      const es = voices.find((v) => (v.lang || "").toLowerCase().startsWith("es"));
      if (es) u.voice = es;
    }
    u.rate = settings.rate ?? 1.0;
    u.pitch = settings.pitch ?? 1.0;
    u.volume = settings.volume ?? 1.0;
    u.lang = u.voice?.lang || "es-ES";
    window.speechSynthesis.speak(u);
  } catch (e) {
    console.warn("speak error", e);
  }
}

export function stopSpeaking() {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
}
