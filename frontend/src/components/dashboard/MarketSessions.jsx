import { Globe } from "lucide-react";

export default function MarketSessions({ data }) {
  const sessions = data?.sessions || [];
  return (
    <div className="card" data-testid="market-sessions-panel">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-amber-500" />
          <span className="font-semibold">Horarios de Mercado</span>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-semibold">
          {data?.active_count ?? 0} ACTIVOS
        </span>
      </div>
      <div className="card-body space-y-2">
        {sessions.map((s) => (
          <div
            key={s.name}
            className={`flex items-center justify-between rounded-lg px-3 py-2 border ${s.active ? "bg-emerald-500/5 border-emerald-500/25" : "bg-zinc-900/40 border-zinc-800"}`}
            data-testid={`session-${s.name.replace(/\s+/g, "-").toLowerCase()}`}
          >
            <div className="flex items-center gap-2">
              <span className={`pulse-dot ${s.active ? "" : "red"}`} style={{ background: s.active ? "#10b981" : "#52525b", animation: s.active ? undefined : "none" }} />
              <span className="text-sm font-medium">{s.name}</span>
            </div>
            <div className="text-right">
              <div className={`text-[10px] uppercase tracking-wider font-bold ${s.active ? "text-emerald-400" : "text-zinc-500"}`}>
                {s.active ? "ABIERTO" : "CERRADO"}
              </div>
              <div className="text-[10px] font-mono-num text-zinc-500">
                {String(s.open).padStart(2, "0")}:00 - {String(s.close).padStart(2, "0")}:00 {s.tz}
              </div>
            </div>
          </div>
        ))}
        {data?.active_count >= 2 && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 mt-2">
            <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold">
              <span className="pulse-dot" style={{ background: "#f59e0b" }} />
              Mercados superpuestos · Máxima liquidez
            </div>
            <div className="text-[11px] text-zinc-400 mt-1">
              Las mejores oportunidades suelen ocurrir durante las superposiciones.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
