import { useEffect, useRef, useState } from "react";
import { Volume2, VolumeX, Play, Settings as SettingsIcon } from "lucide-react";
import {
  loadVoiceSettings, saveVoiceSettings, listSpanishVoices, onVoicesChanged, speak, stopSpeaking,
} from "../../lib/voice";

export default function VoiceSettings({ onChange }) {
  const [settings, setSettings] = useState(() => loadVoiceSettings());
  const [voices, setVoices] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const refresh = () => setVoices(listSpanishVoices());
    refresh();
    const off = onVoicesChanged(refresh);
    return off;
  }, []);

  useEffect(() => {
    saveVoiceSettings(settings);
    onChange?.(settings);
  }, [settings]); // eslint-disable-line

  const update = (patch) => setSettings((s) => ({ ...s, ...patch }));
  const updateAlert = (key, value) =>
    setSettings((s) => ({ ...s, alertTypes: { ...s.alertTypes, [key]: value } }));

  const test = () => speak("Señal de compra XAU/USD. Confianza alta. Toma señal ahora.", settings);

  return (
    <div className="card" data-testid="voice-settings">
      <div className="card-header">
        <div className="flex items-center gap-2">
          {settings.enabled
            ? <Volume2 className="w-4 h-4 text-amber-500" />
            : <VolumeX className="w-4 h-4 text-zinc-500" />}
          <span className="font-semibold">Alertas de Voz</span>
        </div>
        <button
          onClick={() => update({ enabled: !settings.enabled })}
          data-testid="voice-toggle"
          className={`text-[10px] px-2.5 py-1 rounded-full font-bold tracking-wider ${settings.enabled ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-800 text-zinc-400"}`}
        >
          {settings.enabled ? "ACTIVADAS" : "DESACTIVADAS"}
        </button>
      </div>
      <div className="card-body space-y-3">
        {/* Voice selector */}
        <div>
          <label className="text-[11px] uppercase tracking-wider text-zinc-500 block mb-1">Tipo de voz</label>
          <select
            value={settings.voiceURI}
            onChange={(e) => update({ voiceURI: e.target.value })}
            disabled={!settings.enabled}
            data-testid="voice-selector"
            className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-2 py-2 text-sm focus:outline-none focus:border-amber-500 disabled:opacity-50"
          >
            <option value="">Auto (mejor voz en español)</option>
            {voices.map((v) => (
              <option key={v.voiceURI} value={v.voiceURI}>
                {v.name} · {v.lang}
              </option>
            ))}
          </select>
          {voices.length === 0 && (
            <div className="text-[11px] text-amber-400 mt-1">
              Cargando voces del navegador… (refresca si no aparecen)
            </div>
          )}
        </div>

        {/* Rate */}
        <div>
          <div className="flex items-center justify-between text-[11px] text-zinc-400 mb-1">
            <span>Velocidad</span>
            <span className="font-mono-num text-zinc-200">{settings.rate.toFixed(1)}x</span>
          </div>
          <input
            type="range" min="0.6" max="1.6" step="0.1"
            value={settings.rate}
            onChange={(e) => update({ rate: parseFloat(e.target.value) })}
            disabled={!settings.enabled}
            className="w-full accent-amber-500"
            data-testid="voice-rate"
          />
        </div>

        {/* Volume */}
        <div>
          <div className="flex items-center justify-between text-[11px] text-zinc-400 mb-1">
            <span>Volumen</span>
            <span className="font-mono-num text-zinc-200">{Math.round(settings.volume * 100)}%</span>
          </div>
          <input
            type="range" min="0" max="1" step="0.05"
            value={settings.volume}
            onChange={(e) => update({ volume: parseFloat(e.target.value) })}
            disabled={!settings.enabled}
            className="w-full accent-amber-500"
            data-testid="voice-volume"
          />
        </div>

        {/* Test + open alerts */}
        <div className="flex items-center gap-2">
          <button
            onClick={test}
            disabled={!settings.enabled}
            data-testid="voice-test"
            className="flex-1 bg-amber-500/15 border border-amber-500/30 hover:bg-amber-500/25 text-amber-400 font-semibold px-3 py-2 rounded-md transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" /> Probar voz
          </button>
          <button
            onClick={() => setOpen((o) => !o)}
            className="bg-zinc-900 border border-zinc-800 hover:border-zinc-700 px-3 py-2 rounded-md text-sm flex items-center gap-1 text-zinc-300"
            data-testid="voice-alerts-open"
          >
            <SettingsIcon className="w-3.5 h-3.5" />
          </button>
        </div>

        {open && (
          <div className="border-t border-zinc-800 pt-3 space-y-1.5">
            <div className="text-[11px] uppercase tracking-wider text-zinc-500 mb-1">Cuándo hablar</div>
            {[
              ["new_signal", "Nueva señal generada"],
              ["take_now", "Recomendación TOMAR AHORA"],
              ["take_profit", "TP alcanzado"],
              ["stop_loss", "Stop Loss alcanzado"],
              ["reversal", "Reverso brusco / cerrar"],
              ["wait", "ESPERAR (silencioso por defecto)"],
            ].map(([k, label]) => (
              <label key={k} className="flex items-center justify-between text-xs text-zinc-300 cursor-pointer">
                <span>{label}</span>
                <input
                  type="checkbox"
                  checked={!!settings.alertTypes[k]}
                  onChange={(e) => updateAlert(k, e.target.checked)}
                  className="accent-amber-500"
                  data-testid={`voice-alert-${k}`}
                />
              </label>
            ))}
            <button
              onClick={stopSpeaking}
              className="w-full mt-2 text-[11px] text-zinc-400 hover:text-zinc-200 underline"
            >
              Detener voz
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
