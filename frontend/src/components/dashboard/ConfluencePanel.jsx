import { Layers, ArrowRight } from "lucide-react";

export default function ConfluencePanel({ data }) {
  if (!data) return null;
  const { timeframes = [], details = [], aligned_count = 0, total_count = 0, direction } = data;
  const dirCls = direction === "BUY" ? "text-emerald-400 border-emerald-500/30" :
                 direction === "SELL" ? "text-rose-400 border-rose-500/30" :
                 "text-zinc-300 border-zinc-700";
  const strong = aligned_count >= 3;
  return (
    <div className="card" data-testid="confluence-panel">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-amber-500" />
          <span className="font-semibold">Confluencia Multi-TF</span>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${strong ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/15 text-amber-400"}`}>
          {aligned_count}/{total_count}
        </span>
      </div>
      <div className="card-body">
        <div className="flex items-center justify-center gap-2 mb-3">
          {details.map((d, i) => (
            <div key={d.tf} className="flex items-center gap-1">
              <div className={`px-2 py-1 rounded-md text-[11px] font-mono-num font-bold border ${
                d.dir === "BUY" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" :
                d.dir === "SELL" ? "border-rose-500/30 bg-rose-500/10 text-rose-400" :
                "border-zinc-700 bg-zinc-900/40 text-zinc-400"
              }`}>
                {d.tf} {d.dir === "BUY" ? "↑" : d.dir === "SELL" ? "↓" : "—"}
              </div>
              {i < details.length - 1 && <ArrowRight className="w-3 h-3 text-zinc-600" />}
            </div>
          ))}
        </div>
        <div className={`rounded-md text-center text-xs font-bold py-1.5 border ${dirCls}`}>
          Veredicto: {direction === "BUY" ? "COMPRA" : direction === "SELL" ? "VENTA" : "NEUTRAL"}
        </div>
        <div className="text-[11px] text-zinc-500 mt-2 text-center">
          {strong
            ? "Confluencia fuerte · TFs alineados"
            : aligned_count >= 2
              ? "Confluencia moderada · espera confirmación"
              : "Sin confluencia · NO operes"}
        </div>
      </div>
    </div>
  );
}
