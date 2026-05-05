import { useEffect, useRef, useState } from "react";
import { Activity, Zap, Wifi } from "lucide-react";

export default function PriceHeader({ price, sessions }) {
  const [tickClass, setTickClass] = useState("");
  const prev = useRef(null);

  useEffect(() => {
    if (!price) return;
    if (prev.current != null && price.price !== prev.current) {
      setTickClass(price.price > prev.current ? "tick-up" : "tick-down");
      const t = setTimeout(() => setTickClass(""), 700);
      prev.current = price.price;
      return () => clearTimeout(t);
    }
    prev.current = price.price;
  }, [price]);

  if (!price) {
    return (
      <div className="card" data-testid="live-price-ticker">
        <div className="card-body text-zinc-400">Cargando precio…</div>
      </div>
    );
  }

  const up = price.change >= 0;
  const sessionLabel = sessions?.label || "—";
  const activeCount = sessions?.active_count ?? 0;

  return (
    <div className={`card ${tickClass}`} data-testid="live-price-ticker">
      <div className="px-5 py-4 flex flex-wrap items-center gap-4 lg:gap-8">
        <div className="flex items-center gap-3">
          <div className="text-amber-500 font-bold tracking-tight text-2xl">XAU/USD</div>
          <div className="flex items-center gap-1 text-xs text-emerald-500 font-semibold">
            <Activity className="w-3 h-3" />
            <Zap className="w-3 h-3" />
            REAL-TIME
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <div className={`font-mono-num text-3xl lg:text-4xl font-bold ${up ? "text-emerald-400" : "text-rose-400"}`}>
            ${price.price.toFixed(2)}
          </div>
          <div className={`font-mono-num text-sm ${up ? "text-emerald-400" : "text-rose-400"}`}>
            {up ? "+" : ""}{price.change.toFixed(2)} ({up ? "+" : ""}{price.change_pct.toFixed(2)}%)
          </div>
        </div>
        <div className="hidden md:flex items-center gap-5 text-xs text-zinc-400 ml-auto">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Spread</div>
            <div className="font-mono-num text-zinc-200">${price.spread.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Sesión</div>
            <div className="font-semibold text-zinc-200">{sessionLabel}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Sesiones</div>
            <div className="font-mono-num text-zinc-200">{activeCount}/4 activas</div>
          </div>
          <div className="flex items-center gap-1 text-emerald-500">
            <Wifi className="w-3 h-3" />
            <span className="font-medium">EN VIVO</span>
          </div>
        </div>
      </div>
      <div className="px-5 pb-3 text-[11px] text-zinc-500 font-mono-num flex flex-wrap gap-3 items-center">
        <span>Fuente: {price.source}</span>
        <span>· Actualizado: {new Date(price.timestamp).toLocaleTimeString("es-ES")}</span>
        <span className={`px-1.5 py-0.5 rounded ${price.fresh_seconds <= 5 ? "bg-emerald-500/15 text-emerald-400" : price.fresh_seconds <= 15 ? "bg-amber-500/15 text-amber-400" : "bg-rose-500/15 text-rose-400"}`}>
          tick {price.fresh_seconds}s
        </span>
      </div>
    </div>
  );
}
