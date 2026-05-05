import { CheckCircle2, AlertTriangle, Clock, TrendingUp, TrendingDown, ShieldAlert, Zap } from "lucide-react";

const TONES = {
  buy: { ring: "ring-emerald-500/40", bg: "bg-emerald-500/10", border: "border-emerald-500/40", text: "text-emerald-400", Icon: TrendingUp },
  sell: { ring: "ring-rose-500/40", bg: "bg-rose-500/10", border: "border-rose-500/40", text: "text-rose-400", Icon: TrendingDown },
  success: { ring: "ring-emerald-500/40", bg: "bg-emerald-500/10", border: "border-emerald-500/40", text: "text-emerald-400", Icon: CheckCircle2 },
  danger: { ring: "ring-rose-500/40", bg: "bg-rose-500/10", border: "border-rose-500/40", text: "text-rose-400", Icon: ShieldAlert },
  neutral: { ring: "ring-zinc-700", bg: "bg-zinc-900/40", border: "border-zinc-700", text: "text-zinc-300", Icon: Clock },
};

export default function RecommendationBanner({ rec }) {
  if (!rec) return null;
  const t = TONES[rec.tone] || TONES.neutral;
  const { Icon } = t;
  const high = rec.urgency === "high";

  return (
    <div
      className={`rounded-xl border ${t.border} ${t.bg} ${high ? `ring-2 ${t.ring}` : ""} px-4 py-3 flex items-center gap-3 transition-all ${high ? "animate-pulse-slow" : ""}`}
      data-testid="recommendation-banner"
      style={high ? { boxShadow: `0 0 24px -6px var(--${rec.tone === "danger" ? "sell" : "buy"})` } : {}}
    >
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${t.bg} ${t.border} border`}>
        <Icon className={`w-5 h-5 ${t.text}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold tracking-wider ${t.text}`} data-testid="rec-label">
            {rec.label}
          </span>
          {high && (
            <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 bg-amber-500 text-zinc-950 rounded font-bold flex items-center gap-0.5">
              <Zap className="w-2.5 h-2.5" /> URGENTE
            </span>
          )}
        </div>
        <div className="text-sm text-zinc-200 font-medium leading-tight mt-0.5" data-testid="rec-headline">{rec.headline}</div>
        <div className="text-[11px] text-zinc-400 mt-0.5">{rec.message}</div>
      </div>
    </div>
  );
}
