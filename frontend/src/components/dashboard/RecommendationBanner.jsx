import { CheckCircle2, AlertTriangle, Clock, TrendingUp, TrendingDown, ShieldAlert, Zap, XCircle } from "lucide-react";

const TONES = {
  buy: { bg: "bg-emerald-500/10", border: "border-emerald-500/40", text: "text-emerald-400", Icon: TrendingUp },
  sell: { bg: "bg-rose-500/10", border: "border-rose-500/40", text: "text-rose-400", Icon: TrendingDown },
  success: { bg: "bg-emerald-500/10", border: "border-emerald-500/40", text: "text-emerald-400", Icon: CheckCircle2 },
  danger: { bg: "bg-rose-500/10", border: "border-rose-500/40", text: "text-rose-400", Icon: ShieldAlert },
  neutral: { bg: "bg-zinc-900/50", border: "border-zinc-700", text: "text-zinc-300", Icon: Clock },
};

const PROB_TONES = {
  ULTRA: "bg-emerald-500 text-zinc-950",
  ALTA: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40",
  MEDIA: "bg-amber-500/20 text-amber-400 border border-amber-500/40",
  BAJA: "bg-rose-500/20 text-rose-400 border border-rose-500/40",
};

export default function RecommendationBanner({ rec }) {
  if (!rec) return null;
  const t = TONES[rec.tone] || TONES.neutral;
  const { Icon } = t;
  const high = rec.urgency === "high";
  const take = !!rec.take;
  const probLabel = rec.probability || "BAJA";

  return (
    <div
      className={`rounded-xl border ${t.border} ${t.bg} px-4 py-3 transition-all ${high ? "ring-2 ring-amber-500/30" : ""}`}
      data-testid="recommendation-banner"
    >
      <div className="flex items-center gap-3">
        <div className={`w-11 h-11 rounded-lg flex items-center justify-center ${t.bg} ${t.border} border`}>
          <Icon className={`w-5 h-5 ${t.text}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-sm font-bold tracking-wider ${t.text}`} data-testid="rec-label">
              {rec.label}
            </span>
            {high && (
              <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 bg-amber-500 text-zinc-950 rounded font-bold flex items-center gap-0.5">
                <Zap className="w-2.5 h-2.5" /> URGENTE
              </span>
            )}
            <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded font-bold ${PROB_TONES[probLabel] || PROB_TONES.MEDIA}`}
                  data-testid="rec-probability">
              Prob. {probLabel}
            </span>
          </div>
          <div className="text-sm text-zinc-200 font-medium leading-tight mt-0.5" data-testid="rec-headline">{rec.headline}</div>
          <div className="text-[11px] text-zinc-400 mt-0.5">{rec.message}</div>
        </div>
      </div>

      {/* Take recommendation strip */}
      <div className={`mt-3 rounded-lg border ${take ? "bg-emerald-500/10 border-emerald-500/35" : "bg-rose-500/8 border-rose-500/35"} px-3 py-2 flex items-center gap-2`}
           data-testid="take-recommendation">
        {take ? (
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
        ) : (
          <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-bold tracking-wider ${take ? "text-emerald-400" : "text-rose-400"}`} data-testid="take-label">
              {rec.take_label || (take ? "RECOMENDABLE" : "NO RECOMENDABLE")}
            </span>
          </div>
          <div className="text-[11px] text-zinc-400 mt-0.5" data-testid="take-reason">
            {rec.take_reason}
          </div>
        </div>
      </div>
    </div>
  );
}
