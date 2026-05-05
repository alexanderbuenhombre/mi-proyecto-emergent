import { CandlestickChart } from "lucide-react";

const SOURCES = [
  { id: "tradingview", label: "TradingView (OANDA)", note: "Spot · coincide con Exness/XM/IC Markets MT4" },
  { id: "goldapi", label: "Gold-API.com (LBMA)", note: "Spot LBMA agregado · cross-check independiente" },
];

export default function SourceSelector({ value, onChange }) {
  return (
    <div className="card" data-testid="source-selector">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <CandlestickChart className="w-4 h-4 text-amber-500" />
          <span className="font-semibold">Fuente de Precio</span>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-semibold">EN VIVO</span>
      </div>
      <div className="card-body space-y-2">
        {SOURCES.map((s) => {
          const sel = value === s.id;
          return (
            <button
              key={s.id}
              onClick={() => onChange(s.id)}
              data-testid={`source-${s.id}`}
              className={`w-full text-left rounded-lg border px-3 py-2.5 transition-all ${sel ? "border-amber-500/60 bg-amber-500/10 ring-1 ring-amber-500/30" : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700"}`}
            >
              <div className="flex items-center justify-between">
                <span className={`text-sm font-semibold ${sel ? "text-amber-400" : "text-zinc-200"}`}>{s.label}</span>
                {sel && <span className="text-[10px] font-bold text-amber-400">SELECCIONADO</span>}
              </div>
              <div className="text-[11px] text-zinc-500 mt-0.5">{s.note}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
