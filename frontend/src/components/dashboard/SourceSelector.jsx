import { CandlestickChart, Activity, Zap, Coins } from "lucide-react";

const SOURCES = [
  { id: "tradingview", label: "TradingView · OANDA", badge: "SPOT BROKER", note: "Spot vía broker OANDA — coincide con Exness MT4, XM, IC Markets", Icon: Activity },
  { id: "swissquote", label: "Swissquote · Live Tick", badge: "LIVE TICK", note: "Tick bancario en vivo (bid/ask) — máxima frecuencia · sub-segundo", Icon: Zap },
  { id: "goldapi", label: "Gold-API · LBMA", badge: "SPOT LBMA", note: "Spot LBMA agregado de bancos — referencia internacional", Icon: Coins },
];

export default function SourceSelector({ value, onChange }) {
  return (
    <div className="card" data-testid="source-selector">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <CandlestickChart className="w-4 h-4 text-amber-500" />
          <span className="font-semibold">Fuente de Precio</span>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full border border-zinc-700 text-zinc-300 font-semibold">EN VIVO</span>
      </div>
      <div className="card-body space-y-2">
        {SOURCES.map((s) => {
          const sel = value === s.id;
          const Icon = s.Icon;
          return (
            <button
              key={s.id}
              onClick={() => onChange(s.id)}
              data-testid={`source-${s.id}`}
              className={`w-full text-left rounded-lg border px-3 py-2.5 transition-all ${sel ? "border-amber-500/70 bg-amber-500/95 text-zinc-950 ring-1 ring-amber-400" : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700"}`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Icon className={`w-4 h-4 ${sel ? "text-zinc-950" : "text-zinc-300"}`} />
                  <span className={`text-sm font-bold ${sel ? "text-zinc-950" : "text-zinc-200"}`}>{s.label}</span>
                </div>
                <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold tracking-wider ${sel ? "bg-zinc-950/15 text-zinc-950" : "bg-zinc-800 text-zinc-400"}`}>
                  {s.badge}
                </span>
              </div>
              <div className={`text-[11px] mt-1 ${sel ? "text-zinc-900/80" : "text-zinc-500"}`}>{s.note}</div>
            </button>
          );
        })}
        <div className="rounded-md bg-zinc-900/50 border border-zinc-800 p-2 text-[11px] text-zinc-400 leading-relaxed mt-2">
          💡 <span className="text-amber-400 font-semibold">Swissquote · Live Tick</span> es la fuente más rápida (sub-segundo). Las demás quedan como referencia.
        </div>
      </div>
    </div>
  );
}
