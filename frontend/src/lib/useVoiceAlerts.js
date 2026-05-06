import { useEffect, useRef } from "react";
import { speak } from "./voice";

/**
 * Trigger voice alerts when:
 *  - new signal id appears
 *  - recommendation action changes (and not within cooldown)
 * De-dup strategy: composite key (signal.id + recommendation.label) tracked,
 *                  + 8s cooldown between any two utterances.
 */
const COOLDOWN_MS = 8000;

export function useVoiceAlerts({ signal, recommendation, settings, timeframe }) {
  const lastKey = useRef(null);
  const lastSpokenAt = useRef(0);
  const initialized = useRef(false);

  // Reset on timeframe change so a new TF can speak its first signal once
  useEffect(() => {
    lastKey.current = null;
    initialized.current = false;
  }, [timeframe]);

  useEffect(() => {
    if (!settings?.enabled || !recommendation) return;

    const sigId = signal?.id || "none";
    const action = recommendation.action;
    const label = recommendation.label;
    const key = `${sigId}|${label}`;

    // Skip the very first render (avoid speaking on initial mount or TF switch)
    if (!initialized.current) {
      lastKey.current = key;
      initialized.current = true;
      return;
    }

    // Same composite as last time → no speech
    if (key === lastKey.current) return;

    // Cooldown
    const now = Date.now();
    if (now - lastSpokenAt.current < COOLDOWN_MS) {
      lastKey.current = key;
      return;
    }

    // Build phrase based on action
    const map = {
      TOMAR: settings.alertTypes.take_now,
      TOMAR_GANANCIAS: settings.alertTypes.take_profit,
      STOP_LOSS_HIT: settings.alertTypes.stop_loss,
      CERRAR_REVERSO: settings.alertTypes.reversal,
      ESPERAR: settings.alertTypes.wait,
      MANTENER: false,
    };

    // New signal arrived → use the "new_signal" alert toggle
    const isNewSignal = signal && signal.id !== (lastKey.current?.split("|")[0] || null);
    const shouldSpeakNewSig = isNewSignal && settings.alertTypes.new_signal;

    let phrase = null;
    if (shouldSpeakNewSig) {
      const dir = signal.direction === "BUY" ? "compra" : "venta";
      const takeText = recommendation.take ? "Recomendable tomar la señal." : "No es recomendable tomar la señal.";
      phrase = `Nueva señal de ${dir} XAU dólar. Confianza ${Math.round(signal.confidence)} por ciento. ${takeText}`;
    } else if (map[action]) {
      const takeText = recommendation.take ? "Recomendable tomar." : "No es recomendable tomar.";
      const phrases = {
        TOMAR: `Tomar señal ahora. ${recommendation.headline}. ${takeText}`,
        TOMAR_GANANCIAS: `${recommendation.headline}. ${recommendation.message}`,
        STOP_LOSS_HIT: "Atención. Stop loss alcanzado. Cierra la posición ahora.",
        CERRAR_REVERSO: "Reverso brusco detectado. Considera cerrar la posición.",
        ESPERAR: `Esperar. ${recommendation.headline}. ${takeText}`,
      };
      phrase = phrases[action];
    }

    if (phrase) {
      speak(phrase, settings);
      lastSpokenAt.current = now;
    }
    lastKey.current = key;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signal?.id, recommendation?.label, recommendation?.action, settings?.enabled]);
}
