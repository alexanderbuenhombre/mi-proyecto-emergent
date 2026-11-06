import { TrendingUp, TrendingDown, Minus } from "lucide-react";

const TF_LIST = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];

export default function MultiTimeframe({ data, selected, onSelect }) {
  const tfs = data?.timeframes || {};
  return (
    <div className="card" data-testid="multi-timeframe-panel">
      <div className="card-header">
        <span className="font-semibold">Temporalidades</span>
        <span className="text-[10px] uppercase tracking-wider text-zinc-500">Selección activa</span>
      </div>
      <div className="card-body">
        <div className="grid grid-cols-7 gap-1">
          {TF_LIST.map((tf) => {
            const a = tfs[tf];
            const dir = a?.high_prob ? a.direction : "NEUTRAL";
            const isSel = selected === tf;
            const cls = dir === "BUY"
              ? "text-emerald-400 border-emerald-500/30"
              : dir === "SELL"
                ? "text-rose-400 border-rose-500/30"
                : "text-amber-400 border-zinc-700";
            return (
              <button
                key={tf}
                onClick={() => onSelect?.(tf)}
                data-testid={`tf-${tf}`}
                className={`rounded-lg border ${cls} ${isSel ? "bg-amber-500/15 ring-1 ring-amber-500/40" : "bg-zinc-900/40"} px-1.5 py-2 transition-all`}
              >
                <div className="text-[11px] font-mono-num font-bold uppercase">{tf}</div>
                <div className="flex items-center justify-center mt-0.5">
                  {dir === "BUY" && <TrendingUp className="w-3.5 h-3.5" />}
                  {dir === "SELL" && <TrendingDown className="w-3.5 h-3.5" />}
                  {dir === "NEUTRAL" && <Minus className="w-3.5 h-3.5" />}
                </div>
                <div className="text-[8px] font-bold tracking-wider mt-0.5" data-testid={`tf-${tf}-status`}>
                  {a?.high_prob ? a.probability : "ESPERAR"}
                </div>
              </button>
            );
          })}
        </div>
        <div className="mt-3 text-xs text-zinc-500">
          Actual: <span className="text-zinc-200 font-medium">{labelFor(selected)}</span>
        </div>
        <div className="mt-3 flex items-center gap-3 text-[11px] text-zinc-500">
          <span className="flex items-center gap-1"><TrendingUp className="w-3 h-3 text-emerald-400" /> Alta prob. alcista</span>
          <span className="flex items-center gap-1"><TrendingDown className="w-3 h-3 text-rose-400" /> Alta prob. bajista</span>
          <span className="flex items-center gap-1"><Minus className="w-3 h-3 text-amber-400" /> Esperar</span>
        </div>
      </div>
    </div>
  );
}

function labelFor(tf) {
  const map = {
    "1m": "Scalping ultra-rápido",
    "5m": "Scalping rápido",
    "15m": "Intradía corto",
    "30m": "Intradía medio",
    "1h": "Swing corto",
    "4h": "Swing medio",
    "1d": "Posicional",
  };
  return map[tf] || tf;
}
