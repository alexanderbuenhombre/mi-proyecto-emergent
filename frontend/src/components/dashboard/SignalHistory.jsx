import { History, TrendingUp, TrendingDown } from "lucide-react";

export default function SignalHistory({ data }) {
  const list = data?.history || [];
  return (
    <div className="card" data-testid="signal-history-list">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-amber-500" />
          <span className="font-semibold">Historial de Señales</span>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-mono-num font-semibold">
          {list.length} HOY
        </span>
      </div>
      <div className="card-body max-h-[420px] overflow-y-auto scrollbar-thin">
        {list.length === 0 && (
          <div className="text-sm text-zinc-500 text-center py-6">Aún sin señales generadas hoy.</div>
        )}
        <div className="space-y-2">
          {list.map((s) => {
            const isBuy = s.direction === "BUY";
            const Icon = isBuy ? TrendingUp : TrendingDown;
            const stTone = {
              active: "bg-amber-500/15 text-amber-400",
              won: "bg-emerald-500/15 text-emerald-400",
              lost: "bg-rose-500/15 text-rose-400",
              expired: "bg-zinc-500/15 text-zinc-400",
            }[s.status];
            const stLabel = { active: "Activa", won: "Ganada", lost: "Perdida", expired: "Expirada" }[s.status];
            return (
              <div key={s.id} className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2 flex items-center gap-3">
                <div className={`w-8 h-8 rounded-md flex items-center justify-center ${isBuy ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/15 text-rose-400"}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-xs">
                    <span className={`font-bold ${isBuy ? "text-emerald-400" : "text-rose-400"}`}>{isBuy ? "COMPRA" : "VENTA"}</span>
                    <span className="font-mono-num text-zinc-300">${s.entry.toFixed(2)}</span>
                    <span className="font-mono-num text-amber-400">{s.confidence}%</span>
                  </div>
                  <div className="text-[11px] text-zinc-500 truncate">{s.analysis}</div>
                </div>
                <div className="text-right">
                  <div className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${stTone}`}>{stLabel}</div>
                  <div className="text-[10px] text-zinc-500 font-mono-num mt-0.5">{s.timeframe.toUpperCase()}</div>
                  {s.pnl_pct != null && (
                    <div className={`text-[11px] font-mono-num font-semibold ${s.pnl_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      {s.pnl_pct >= 0 ? "+" : ""}{s.pnl_pct.toFixed(2)}%
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
