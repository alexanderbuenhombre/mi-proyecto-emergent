import { Activity, Zap, BarChart3, Volume2, Target } from "lucide-react";

const ROWS = [
  { key: "trend", label: "Fuerza Tendencia", Icon: Activity, hue: "emerald" },
  { key: "momentum", label: "Momentum", Icon: Zap, hue: "amber" },
  { key: "volatility", label: "Volatilidad", Icon: BarChart3, hue: "amber" },
  { key: "volume", label: "Volumen", Icon: Volume2, hue: "emerald" },
  { key: "confidence", label: "Confianza General", Icon: Target, hue: "amber" },
];

export default function StrengthBars({ data }) {
  return (
    <div className="card" data-testid="strength-bars">
      <div className="card-header">
        <span className="font-semibold">Indicadores de Fuerza</span>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-semibold tracking-wider">
          MULTI-SOURCE
        </span>
      </div>
      <div className="card-body space-y-3">
        {ROWS.map(({ key, label, Icon }) => {
          const v = data?.[key] ?? 0;
          const tone =
            v >= 75 ? "text-emerald-400 bg-emerald-500/15"
            : v >= 50 ? "text-amber-400 bg-amber-500/15"
            : "text-rose-400 bg-rose-500/15";
          return (
            <div key={key} data-testid={`strength-${key}`}>
              <div className="flex items-center justify-between text-xs mb-1.5">
                <div className="flex items-center gap-2 text-zinc-300">
                  <Icon className="w-3.5 h-3.5 text-zinc-400" />
                  <span>{label}</span>
                </div>
                <span className={`font-mono-num text-[11px] px-1.5 py-0.5 rounded-md ${tone}`}>{v}%</span>
              </div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${v}%` }} />
              </div>
            </div>
          );
        })}
        <div className="text-[11px] text-zinc-500 pt-1">
          Basado en señales reales de multi-fuente
        </div>
      </div>
    </div>
  );
}
