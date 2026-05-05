import { LineChart } from "lucide-react";

function Stat({ label, value, tone = "default" }) {
  const cls = {
    default: "text-zinc-200",
    pos: "text-emerald-400",
    neg: "text-rose-400",
    warn: "text-amber-400",
  }[tone];
  return (
    <div className="flex items-center justify-between text-sm py-1">
      <span className="text-zinc-400">{label}</span>
      <span className={`font-mono-num font-semibold ${cls}`}>{value}</span>
    </div>
  );
}

export default function SystemStats({ data }) {
  if (!data) return null;
  return (
    <div className="card" data-testid="system-stats">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <LineChart className="w-4 h-4 text-amber-500" />
          <span className="font-semibold">Estadísticas del Sistema</span>
        </div>
      </div>
      <div className="card-body">
        <Stat label="Señales activas" value={data.active_signals} tone="default" />
        <Stat label="Señales totales" value={data.total_signals} />
        <Stat label="Precisión promedio" value={`${data.avg_confidence}%`} tone="pos" />
        <Stat label="Exitosas" value={data.wins} tone="pos" />
        <Stat label="Fallidas" value={data.losses} tone={data.losses > 0 ? "neg" : "default"} />
        <div className="border-t border-zinc-800 my-2" />
        <Stat label="Win Rate" value={`${data.win_rate}%`} tone="pos" />
      </div>
    </div>
  );
}
