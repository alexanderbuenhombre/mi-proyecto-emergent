import { useEffect, useRef } from "react";
import { speak } from "./voice";

/**
 * Trigger voice alerts when:
 *  - new signal id appears
 *  - recommendation action changes
 *  - TP1/TP2/TP3, Stop Loss, Reversal events
 */
export function useVoiceAlerts({ signal, recommendation, settings }) {
  const lastSignalId = useRef(null);
  const lastAction = useRef(null);
  const lastLabel = useRef(null);
  const initial = useRef(true);

  useEffect(() => {
    if (!settings?.enabled || !recommendation) return;

    const sigId = signal?.id || null;
    const action = recommendation.action;
    const label = recommendation.label;

    // Skip the very first render to avoid speaking on page load
    if (initial.current) {
      lastSignalId.current = sigId;
      lastAction.current = action;
      lastLabel.current = label;
      initial.current = false;
      return;
    }

    // 1) New signal
    if (sigId && sigId !== lastSignalId.current && settings.alertTypes.new_signal) {
      const dir = signal.direction === "BUY" ? "compra" : "venta";
      speak(
        `Nueva señal de ${dir} XAU dólar. Confianza ${Math.round(signal.confidence)} por ciento. Entrada en ${signal.entry.toFixed(2)}.`,
        settings
      );
      lastSignalId.current = sigId;
      lastAction.current = action;
      lastLabel.current = label;
      return; // avoid double-speak
    }
    lastSignalId.current = sigId;

    // 2) Recommendation action/label changed
    if (label !== lastLabel.current) {
      const map = {
        TOMAR: settings.alertTypes.take_now,
        TOMAR_GANANCIAS: settings.alertTypes.take_profit,
        STOP_LOSS_HIT: settings.alertTypes.stop_loss,
        CERRAR_REVERSO: settings.alertTypes.reversal,
        ESPERAR: settings.alertTypes.wait,
        MANTENER: false,
      };
      if (map[action]) {
        const phrases = {
          TOMAR: "Tomar señal ahora. " + recommendation.headline,
          TOMAR_GANANCIAS: recommendation.headline + ". " + recommendation.message,
          STOP_LOSS_HIT: "¡Atención! Stop loss alcanzado. Cierra la posición ahora.",
          CERRAR_REVERSO: "Reverso brusco detectado. Considera cerrar la posición.",
          ESPERAR: "Esperar. " + recommendation.headline,
        };
        speak(phrases[action] || recommendation.headline, settings);
      }
      lastLabel.current = label;
      lastAction.current = action;
    }
  }, [signal?.id, recommendation?.label, recommendation?.action, settings]); // eslint-disable-line
}
