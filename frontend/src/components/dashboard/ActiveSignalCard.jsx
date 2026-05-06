import { TrendingUp, TrendingDown, Target, ShieldAlert, Clock, CheckCircle2, XCircle, AlertTriangle, Volume2, VolumeX } from "lucide-react";

const PROB_BADGE = {
  ULTRA: "bg-emerald-500 text-zinc-950",
  ALTA: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40",
  MEDIA: "bg-amber-500/20 text-amber-400 border border-amber-500/40",
  BAJA: "bg-rose-500/20 text-rose-400 border border-rose-500/40",
};

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}

function minutesLeft(iso) {
  const ms = new Date(iso) - new Date();
  return Math.max(0, Math.round(ms / 60000));
}

export default function ActiveSignalCard({ payload, timeframe, voiceEnabled, onToggleVoice }) {
  const signal = payload?.signal;
  const price = payload?.price;
  const recommendation = payload?.recommendation;

  // Empty state — embed recommendation inside same shell
  if (!signal) {
    const rec = recommendation;
    return (
      <div className="card border-zinc-700" data-testid="active-signal-card">
        <div className="card-header">
          <div className="flex items-center gap-2">
            <Target className="w-4 h-4 text-amber-500" />
            <span className="font-semibold">Señales Activas</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={onToggleVoice} className="p-1 rounded hover:bg-zinc-800" data-testid="voice-quick-toggle">
              {voiceEnabled ? <Volume2 className="w-3.5 h-3.5 text-amber-400" /> : <VolumeX className="w-3.5 h-3.5 text-zinc-500" />}
            </button>
            <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono-num">{timeframe.toUpperCase()}</span>
          </div>
        </div>
        <div className="card-body">
          <div className="text-center py-6 mb-3">
            <div className="text-zinc-300 font-semibold mb-1">Mercado neutral</div>
            <div className="text-xs text-zinc-500">Esperando confirmación de tendencia para emitir señal…</div>
          </div>
          {rec && (
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <Clock className="w-4 h-4 text-zinc-400" />
                <span className="text-sm font-bold tracking-wider text-zinc-200" data-testid="rec-label">{rec.label}</span>
                <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded font-bold ${PROB_BADGE[rec.probability] || PROB_BADGE.BAJA}`} data-testid="rec-probability">
                  Prob. {rec.probability}
                </span>
              </div>
              <div className="text-xs text-zinc-300" data-testid="rec-headline">{rec.headline}</div>
              <div className="rounded-md border border-rose-500/30 bg-rose-500/8 px-2.5 py-2 flex items-start gap-2" data-testid="take-recommendation">
                <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] font-bold tracking-wider text-rose-400" data-testid="take-label">{rec.take_label || "NO TOMAR"}</div>
                  <div className="text-[11px] text-zinc-400" data-testid="take-reason">{rec.take_reason}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  const isBuy = signal.direction === "BUY";
  const Icon = isBuy ? TrendingUp : TrendingDown;
  const livePnl = signal.pnl_pct ?? 0;
  const tpHits = signal.tp_hits || { tp1: false, tp2: false, tp3: false };
  const slHit = !!signal.sl_hit;
  const minLeft = minutesLeft(signal.expires_at);

  const styles = isBuy
    ? {
        cardShadow: "inset 0 0 0 1px rgba(16,185,129,0.45)",
        text: "text-emerald-400",
        textSoft: "text-emerald-300",
        badgeBg: "bg-emerald-500/15 text-emerald-400",
        priceBox: "bg-emerald-500/5 border-emerald-500/25",
        cta: "bg-emerald-500 hover:bg-emerald-400",
      }
    : {
        cardShadow: "inset 0 0 0 1px rgba(244,63,94,0.45)",
        text: "text-rose-400",
        textSoft: "text-rose-300",
        badgeBg: "bg-rose-500/15 text-rose-400",
        priceBox: "bg-rose-500/5 border-rose-500/25",
        cta: "bg-rose-500 hover:bg-rose-400",
      };

  const TpBox = ({ n }) => {
    const hit = !!tpHits[`tp${n}`];
    const value = signal[`tp${n}`];
    // Static class maps (Tailwind needs literal class strings)
    const variants = {
      buy: {
        idle: "bg-emerald-500/10 border-emerald-500/25",
        hit:  "bg-emerald-500/30 border-emerald-500/70 ring-1 ring-emerald-500/50",
        labelIdle: "text-emerald-400",
        valueIdle: "text-emerald-300",
      },
      sell: {
        idle: "bg-rose-500/10 border-rose-500/25",
        hit:  "bg-rose-500/30 border-rose-500/70 ring-1 ring-rose-500/50",
        labelIdle: "text-rose-400",
        valueIdle: "text-rose-300",
      },
    };
    const v = isBuy ? variants.buy : variants.sell;
    return (
      <div className={`relative border rounded-lg p-3 text-center ${hit ? v.hit : v.idle}`} data-testid={`tp-${n}`}>
        {hit && (
          <div className="absolute top-1 right-1 flex items-center gap-0.5 text-[9px] font-bold text-emerald-200 bg-emerald-500/40 px-1.5 py-0.5 rounded-full">
            <CheckCircle2 className="w-2.5 h-2.5" /> ALCANZADO
          </div>
        )}
        <div className={`text-[10px] uppercase tracking-wider ${hit ? "text-emerald-200" : v.labelIdle}`}>
          TP{n} {isBuy ? "↑" : "↓"}
        </div>
        <div className={`font-mono-num text-base font-semibold ${hit ? "text-emerald-100 line-through decoration-emerald-200/60" : v.valueIdle}`}>
          ${value.toFixed(2)}
        </div>
      </div>
    );
  };

  // Recommendation badge tone
  const recTone = recommendation?.tone || "neutral";
  const recHigh = recommendation?.urgency === "high";
  const recBg = recTone === "danger" ? "border-rose-500/40 bg-rose-500/8"
    : recTone === "success" ? "border-emerald-500/40 bg-emerald-500/8"
    : recTone === "buy" ? "border-emerald-500/40 bg-emerald-500/8"
    : recTone === "sell" ? "border-rose-500/40 bg-rose-500/8"
    : "border-zinc-700 bg-zinc-900/50";
  const RecIcon = recTone === "danger" ? ShieldAlert
    : recTone === "success" ? CheckCircle2
    : recTone === "buy" || recTone === "sell" ? Target
    : Clock;
  const recIconColor = recTone === "danger" ? "text-rose-400"
    : recTone === "success" ? "text-emerald-400"
    : recTone === "buy" ? "text-emerald-400"
    : recTone === "sell" ? "text-rose-400"
    : "text-zinc-300";

  return (
    <div
      className="card"
      style={{ boxShadow: styles.cardShadow }}
      data-testid="active-signal-card"
    >
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-amber-500" />
          <span className="font-semibold">Señales Activas</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onToggleVoice} className="p-1 rounded hover:bg-zinc-800" data-testid="voice-quick-toggle">
            {voiceEnabled ? <Volume2 className="w-3.5 h-3.5 text-amber-400" /> : <VolumeX className="w-3.5 h-3.5 text-zinc-500" />}
          </button>
          <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono-num">{timeframe.toUpperCase()}</span>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* Header: title + confianza */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${styles.badgeBg}`} data-testid={isBuy ? "signal-buy-badge" : "signal-sell-badge"}>
              <Icon className="w-6 h-6" />
            </div>
            <div>
              <div className={`text-xl font-bold tracking-tight ${styles.text}`}>
                {isBuy ? "COMPRA" : "VENTA"} XAU/USD
              </div>
              <div className="text-xs text-zinc-500 flex items-center gap-2 mt-0.5">
                <Clock className="w-3 h-3" />
                {timeframe} · Generada {formatTime(signal.created_at)} · Expira en {minLeft}m
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Confianza</div>
            <div className={`text-3xl font-bold font-mono-num ${styles.text}`}>{Math.round(signal.confidence)}%</div>
            <div className="text-[10px] text-amber-500 font-semibold">PROB. {recommendation?.probability || "MEDIA"}</div>
          </div>
        </div>

        {/* Live price + pnl */}
        <div className={`border ${styles.priceBox} rounded-lg px-4 py-3 flex items-center justify-between`}>
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

        {/* Entrada */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg px-4 py-3 text-center">
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">Entrada</div>
          <div className="font-mono-num text-2xl font-bold">${signal.entry.toFixed(2)}</div>
        </div>

        {/* TPs (with hit markers) */}
        <div className="grid grid-cols-3 gap-2">
          <TpBox n={1} />
          <TpBox n={2} />
          <TpBox n={3} />
        </div>

        {/* Stop Loss */}
        <div className={`border rounded-lg p-3 text-center ${slHit ? "bg-rose-500/30 border-rose-500/70 ring-1 ring-rose-500/40" : "bg-rose-500/10 border-rose-500/25"}`} data-testid="stop-loss-box">
          {slHit && (
            <div className="text-[10px] uppercase tracking-wider font-bold text-rose-200 mb-0.5 flex items-center justify-center gap-1">
              <AlertTriangle className="w-3 h-3" /> SL ALCANZADO
            </div>
          )}
          <div className="text-[10px] uppercase tracking-wider text-rose-400">Stop Loss {isBuy ? "↓" : "↑"}</div>
          <div className={`font-mono-num text-lg font-semibold ${slHit ? "text-rose-200 line-through" : "text-rose-300"}`}>
            ${signal.stop_loss.toFixed(2)}
          </div>
        </div>

        {/* Análisis */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">Análisis</div>
          <div className="text-sm text-zinc-200">{signal.analysis}</div>
        </div>

        {/* RECOMMENDATION INLINE (matches model image style) */}
        {recommendation && (
          <div className={`rounded-lg border p-3 space-y-2 ${recBg} ${recHigh ? "ring-1 ring-amber-500/40" : ""}`} data-testid="recommendation-inline">
            <div className="flex items-center gap-2 flex-wrap">
              <RecIcon className={`w-4 h-4 ${recIconColor}`} />
              <span className={`text-sm font-bold tracking-wider ${recIconColor}`} data-testid="rec-label">
                {recommendation.label}
              </span>
              <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded font-bold ${PROB_BADGE[recommendation.probability] || PROB_BADGE.MEDIA}`} data-testid="rec-probability">
                Prob. {recommendation.probability}
              </span>
              {recHigh && (
                <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 bg-amber-500 text-zinc-950 rounded font-bold">URGENTE</span>
              )}
            </div>
            <div className="text-sm text-zinc-200" data-testid="rec-headline">{recommendation.headline}</div>
            <div className="text-[11px] text-zinc-400">{recommendation.message}</div>
            <div className={`rounded-md border ${recommendation.take ? "border-emerald-500/30 bg-emerald-500/10" : "border-rose-500/30 bg-rose-500/10"} px-2.5 py-2 flex items-start gap-2`} data-testid="take-recommendation">
              {recommendation.take
                ? <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                : <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />}
              <div className="flex-1 min-w-0">
                <div className={`text-[11px] font-bold tracking-wider ${recommendation.take ? "text-emerald-400" : "text-rose-400"}`} data-testid="take-label">
                  {recommendation.take_label || (recommendation.take ? "RECOMENDABLE" : "NO RECOMENDABLE")}
                </div>
                <div className="text-[11px] text-zinc-400" data-testid="take-reason">{recommendation.take_reason}</div>
              </div>
            </div>
          </div>
        )}

        {/* CTA */}
        <button
          className={`w-full ${styles.cta} text-zinc-950 font-bold py-3 rounded-lg transition-colors flex items-center justify-center gap-2 ${!recommendation?.take ? "opacity-60" : ""}`}
          data-testid="take-signal-btn"
          disabled={!recommendation?.take}
        >
          <ShieldAlert className="w-4 h-4" />
          {recommendation?.take ? "TOMAR SEÑAL AHORA" : "ESPERAR"} · {isBuy ? "COMPRA" : "VENTA"} {Math.round(signal.confidence)}%
        </button>
        <div className="text-center text-[11px] text-zinc-500 -mt-2">
          Riesgo: {((Math.abs(signal.entry - signal.stop_loss) / signal.entry) * 100).toFixed(2)}% · Válida {minLeft}min más
        </div>
      </div>
    </div>
  );
}
