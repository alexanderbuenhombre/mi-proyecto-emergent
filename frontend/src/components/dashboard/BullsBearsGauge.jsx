import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

export default function BullsBearsGauge({ analysis }) {
  const score = analysis?.score ?? 0;
  // map -100..100 -> 0..180 deg pointer
  const norm = (score + 100) / 200; // 0..1
  const angle = norm * 180;
  const data = [
    { name: "sell-strong", value: 25, color: "#dc2626" },
    { name: "sell", value: 25, color: "#f97316" },
    { name: "buy", value: 25, color: "#84cc16" },
    { name: "buy-strong", value: 25, color: "#10b981" },
  ];
  let label = "Neutral";
  let labelColor = "text-zinc-300";
  if (score >= 50) { label = "Compra Fuerte"; labelColor = "text-emerald-400"; }
  else if (score >= 20) { label = "Compra"; labelColor = "text-emerald-300"; }
  else if (score <= -50) { label = "Venta Fuerte"; labelColor = "text-rose-400"; }
  else if (score <= -20) { label = "Venta"; labelColor = "text-rose-300"; }

  const rsi = analysis?.rsi ?? 50;
  const cci = analysis?.cci ?? 0;
  const trendArrow = score > 0 ? "↗" : score < 0 ? "↘" : "→";

  return (
    <div className="card" data-testid="bulls-bears-gauge">
      <div className="card-body">
        <div className="text-center text-xs text-zinc-500 mb-1">XAUUSD</div>
        <div className="text-center text-xs text-zinc-400 mb-3 font-medium">Bulls &amp; Bears</div>

        <div className="relative h-32">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="100%"
                startAngle={180}
                endAngle={0}
                innerRadius="65%"
                outerRadius="100%"
                paddingAngle={1}
                dataKey="value"
                stroke="none"
              >
                {data.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          {/* Pointer */}
          <div
            className="absolute left-1/2 bottom-0 origin-bottom"
            style={{
              width: "2px",
              height: "70%",
              background: "#fafafa",
              transform: `translateX(-50%) rotate(${angle - 90}deg)`,
              transition: "transform 800ms cubic-bezier(.2,.8,.2,1)",
              boxShadow: "0 0 6px rgba(255,255,255,0.4)",
            }}
          />
          <div className="absolute left-1/2 bottom-0 -translate-x-1/2 w-3 h-3 rounded-full bg-zinc-200" />
        </div>

        <div className="text-center mt-2">
          <div className={`text-base font-bold ${labelColor}`}>{label}</div>
          <div className="text-xs text-zinc-500 font-mono-num">{trendArrow} score {score}</div>
        </div>

        <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-zinc-800 text-center">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">RSI</div>
            <div className={`font-mono-num text-base ${rsi > 70 ? "text-rose-400" : rsi < 30 ? "text-emerald-400" : "text-zinc-200"}`}>
              {rsi.toFixed(2)}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">CCI</div>
            <div className={`font-mono-num text-base ${cci > 100 ? "text-emerald-400" : cci < -100 ? "text-rose-400" : "text-zinc-200"}`}>
              {cci.toFixed(0)}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Trend</div>
            <div className={`font-mono-num text-base ${score > 0 ? "text-emerald-400" : score < 0 ? "text-rose-400" : "text-zinc-200"}`}>
              {trendArrow}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
