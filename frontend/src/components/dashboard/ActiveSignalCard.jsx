import { TrendingUp, TrendingDown, Target, ShieldAlert, Clock } from "lucide-react";

export default function ActiveSignalCard({ payload, timeframe }) {
  const signal = payload?.signal;
  const price = payload?.price;
  if (!signal) {
    return (
      <div className="card" data-testid="active-signal-card">
        <div className="card-header">
          <div className="flex items-center gap-2">
            <Target className="w-4 h-4 text-amber-500" />
            <span className="font-semibold">Señales Activas</span>
          </div>
          <span className="text-xs text-zinc-500 font-mono-num">{timeframe.toUpperCase()}</span>
        </div>
        <div className="card-body text-center py-12 text-zinc-400">
          <div className="text-zinc-300 font-semibold mb-1">Mercado neutral</div>
          <div className="text-xs">Esperando confirmación de tendencia para emitir señal…</div>
        </div>
      </div>
    );
  }

  const isBuy = signal.direction === "BUY";
  const Icon = isBuy ? TrendingUp : TrendingDown;
  const livePnl = signal.pnl_pct ?? 0;

  // Static class maps (Tailwind needs full literal class names)
  const styles = isBuy
    ? {
        cardShadow: "inset 0 0 0 1px rgba(16,185,129,0.25)",
        text: "text-emerald-400",
        textSoft: "text-emerald-300",
        badgeBg: "bg-emerald-500/15 text-emerald-400",
        priceBox: "bg-emerald-500/5 border-emerald-500/20",
        tpBox: "bg-emerald-500/10 border-emerald-500/25",
        tpLabel: "text-emerald-400",
        tpValue: "text-emerald-300",
        cta: "bg-emerald-500 hover:bg-emerald-400",
      }
    : {
        cardShadow: "inset 0 0 0 1px rgba(244,63,94,0.25)",
        text: "text-rose-400",
        textSoft: "text-rose-300",
        badgeBg: "bg-rose-500/15 text-rose-400",
        priceBox: "bg-rose-500/5 border-rose-500/20",
        tpBox: "bg-rose-500/10 border-rose-500/25",
        tpLabel: "text-rose-400",
        tpValue: "text-rose-300",
        cta: "bg-rose-500 hover:bg-rose-400",
      };

  return (
    <div
      className="card"
      style={{ boxShadow: styles.cardShadow }}
      data-testid="active-signal-card"
    >
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-amber-500" />
          <span className="font-semibold">Señal Activa</span>
        </div>
        <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono-num">
          {timeframe.toUpperCase()} · Generada {new Date(signal.created_at).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
      <div className="p-5">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div
              className={`w-11 h-11 rounded-xl flex items-center justify-center ${styles.badgeBg}`}
              data-testid={isBuy ? "signal-buy-badge" : "signal-sell-badge"}
            >
              <Icon className="w-6 h-6" />
            </div>
            <div>
              <div className={`text-xl font-bold tracking-tight ${styles.text}`}>
                {isBuy ? "COMPRA" : "VENTA"} XAU/USD
              </div>
              <div className="text-xs text-zinc-500 flex items-center gap-2 mt-0.5">
                <Clock className="w-3 h-3" />
                Expira: {new Date(signal.expires_at).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Confianza</div>
            <div className={`text-3xl font-bold font-mono-num ${styles.text}`}>{signal.confidence}%</div>
            <div className="text-[10px] text-amber-500 font-semibold">ALTA</div>
          </div>
        </div>

        <div className={`border ${styles.priceBox} rounded-lg px-4 py-3 mb-4 flex items-center justify-between`}>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Precio en vivo</div>
            <div className="font-mono-num text-lg font-semibold">${price?.price?.toFixed(2) ?? "—"}</div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">P&amp;L</div>
            <div className={`font-mono-num text-lg font-semibold ${livePnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {livePnl >= 0 ? "+" : ""}{livePnl.toFixed(3)}%
            </div>
          </div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg px-4 py-3 mb-3 text-center">
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">Entrada</div>
          <div className="font-mono-num text-2xl font-bold">${signal.entry.toFixed(2)}</div>
        </div>

        <div className="grid grid-cols-3 gap-2 mb-3">
          {[1, 2, 3].map((n) => (
            <div key={n} className={`border ${styles.tpBox} rounded-lg p-3 text-center`} data-testid={`tp-${n}`}>
              <div className={`text-[10px] uppercase tracking-wider ${styles.tpLabel}`}>TP{n} {isBuy ? "↑" : "↓"}</div>
              <div className={`font-mono-num text-base font-semibold ${styles.tpValue}`}>
                ${signal[`tp${n}`].toFixed(2)}
              </div>
            </div>
          ))}
        </div>

        <div className="bg-rose-500/10 border border-rose-500/25 rounded-lg p-3 text-center mb-4">
          <div className="text-[10px] uppercase tracking-wider text-rose-400">Stop Loss {isBuy ? "↓" : "↑"}</div>
          <div className="font-mono-num text-lg font-semibold text-rose-300">${signal.stop_loss.toFixed(2)}</div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3 mb-4">
          <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">Análisis</div>
          <div className="text-sm text-zinc-200">{signal.analysis}</div>
        </div>

        <button
          className={`w-full ${styles.cta} text-zinc-950 font-bold py-3 rounded-lg transition-colors flex items-center justify-center gap-2`}
          data-testid="take-signal-btn"
        >
          <ShieldAlert className="w-4 h-4" />
          TOMAR SEÑAL AHORA · {isBuy ? "COMPRA" : "VENTA"} {signal.confidence}%
        </button>
        <div className="text-center text-[11px] text-zinc-500 mt-2">
          Riesgo: {((Math.abs(signal.entry - signal.stop_loss) / signal.entry) * 100).toFixed(2)}%
        </div>
      </div>
    </div>
  );
}
