import { useEffect, useRef } from "react";

/**
 * Bulls & Bears half-circle gauge matching reference screenshot.
 * Score range: -100..+100  →  pointer angle 180..0 degrees.
 *
 *  Sectors:
 *    -100..-50  Venta Fuerte (deep red)
 *    -50..-20   Venta (orange)
 *    -20..+20   Neutral (gray)
 *    +20..+50   Compra (green)
 *    +50..+100  Compra Fuerte (deep green)
 */
export default function BullsBearsGauge({ analysis, timeframe = "5m" }) {
  const score = analysis?.score ?? 0;
  const rsi = analysis?.rsi ?? 50;
  const cci = analysis?.cci ?? 0;

  // map -100..100 -> 0..1 -> 180..0 deg (left=red, right=green)
  const norm = Math.max(0, Math.min(1, (score + 100) / 200));
  const angle = 180 - norm * 180; // pointer from -90 to +90 (left to right)
  const targetRotation = angle - 90; // for CSS rotate at bottom origin

  // Label mapping
  let label = "Neutral";
  let labelClass = "text-zinc-300";
  if (score >= 50) { label = "Compra Fuerte"; labelClass = "text-emerald-400"; }
  else if (score >= 20) { label = "Compra"; labelClass = "text-emerald-300"; }
  else if (score <= -50) { label = "Venta Fuerte"; labelClass = "text-rose-400"; }
  else if (score <= -20) { label = "Venta"; labelClass = "text-rose-300"; }

  const trendUp = score > 5;
  const trendDown = score < -5;

  // Generate small histogram of recent score-pulses (visual accent only, derived from score)
  const bars = useRef(null);
  if (!bars.current) {
    bars.current = Array.from({ length: 36 }, (_, i) => {
      // pseudo-random heights based on index, weighted by score sign
      const base = 14 + ((i * 7919) % 28);
      const sign = (i + Math.round(score / 25)) % 4 === 0 ? "neutral" : score >= 0 ? (i % 3 === 0 ? "down" : "up") : (i % 3 === 0 ? "up" : "down");
      return { h: base, sign };
    });
  }

  // Re-shuffle bars when score sign changes
  useEffect(() => {
    bars.current = Array.from({ length: 36 }, (_, i) => {
      const base = 12 + ((i * 9587 + Math.abs(score) * 13) % 30);
      const r = (i * 31 + Math.abs(score)) % 5;
      const sign = r === 0 ? "neutral" : score > 5 ? (r === 1 ? "down" : "up") : score < -5 ? (r === 1 ? "up" : "down") : (i % 2 === 0 ? "up" : "down");
      return { h: base, sign };
    });
  }, [Math.sign(score), Math.round(Math.abs(score) / 10)]);

  return (
    <div className="card" data-testid="bulls-bears-gauge">
      <div className="card-body pb-3">
        {/* Gauge SVG */}
        <div className="relative w-full" style={{ aspectRatio: "2 / 1.1" }}>
          <svg viewBox="0 0 200 110" className="w-full h-full">
            <defs>
              <linearGradient id="bb-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#dc2626" />
                <stop offset="22%" stopColor="#ef4444" />
                <stop offset="38%" stopColor="#f59e0b" />
                <stop offset="50%" stopColor="#71717a" />
                <stop offset="62%" stopColor="#22c55e" />
                <stop offset="78%" stopColor="#16a34a" />
                <stop offset="100%" stopColor="#10b981" />
              </linearGradient>
            </defs>
            {/* arc */}
            <path
              d="M 14 96 A 86 86 0 0 1 186 96"
              fill="none"
              stroke="url(#bb-grad)"
              strokeWidth="14"
              strokeLinecap="round"
            />
            {/* sector labels along the arc */}
            <text x="14" y="60" fill="#f87171" fontSize="7" fontWeight="700" textAnchor="start">Venta</text>
            <text x="14" y="68" fill="#f87171" fontSize="7" fontWeight="700" textAnchor="start">Fuerte</text>
            <text x="55" y="30" fill="#fb923c" fontSize="7.5" fontWeight="600">Venta</text>
            <text x="92" y="16" fill="#a1a1aa" fontSize="7.5" fontWeight="600">Neutral</text>
            <text x="135" y="30" fill="#86efac" fontSize="7.5" fontWeight="600">Compra</text>
            <text x="170" y="60" fill="#34d399" fontSize="7" fontWeight="700" textAnchor="start">Compra</text>
            <text x="170" y="68" fill="#34d399" fontSize="7" fontWeight="700" textAnchor="start">Fuerte</text>
            {/* Pivot circle */}
            <circle cx="100" cy="96" r="5" fill="#52525b" stroke="#a1a1aa" strokeWidth="0.5" />
            {/* Needle */}
            <line
              x1="100" y1="96"
              x2="100" y2="34"
              stroke="#fafafa"
              strokeWidth="2.4"
              strokeLinecap="round"
              style={{
                transformOrigin: "100px 96px",
                transform: `rotate(${targetRotation}deg)`,
                transition: "transform 900ms cubic-bezier(.2,.8,.2,1)",
              }}
            />
          </svg>
        </div>

        {/* Symbol & subtitle */}
        <div className="text-center -mt-2">
          <div className="text-xl font-bold tracking-tight">XAUUSD</div>
          <div className="text-xs text-zinc-400 mt-0.5">Bulls &amp; Bears</div>
        </div>

        {/* Histogram bars + arrow */}
        <div className="mt-3 flex items-end gap-3">
          {trendDown && <div className="text-rose-400 text-xs">▼</div>}
          {trendUp && <div className="text-emerald-400 text-xs">▲</div>}
          {!trendUp && !trendDown && <div className="text-zinc-500 text-xs">—</div>}
          <div className="flex-1 flex items-end gap-[2px] h-12">
            {bars.current?.map((b, i) => (
              <div
                key={i}
                className="flex-1 rounded-sm"
                style={{
                  height: `${b.h}px`,
                  background:
                    b.sign === "up" ? "#10b981" :
                    b.sign === "down" ? "#f43f5e" : "#52525b",
                  opacity: 0.85,
                }}
              />
            ))}
          </div>
        </div>
        <div className="flex justify-between text-[10px] text-zinc-500 mt-1 px-1">
          <span>high</span>
          <span>low</span>
          <span>high</span>
        </div>

        {/* Indicators row */}
        <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-zinc-800 text-center">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">RSI</div>
            <div className={`font-mono-num text-xl font-bold ${rsi > 70 ? "text-rose-400" : rsi < 30 ? "text-emerald-400" : "text-zinc-100"}`}>
              {rsi.toFixed(2)}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">CCI</div>
            <div className={`font-mono-num text-xl font-bold ${cci > 100 ? "text-emerald-400" : cci < -100 ? "text-rose-400" : "text-zinc-100"}`}>
              {Math.round(cci)}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Trends</div>
            <div className={`text-xl font-mono-num ${trendUp ? "text-emerald-400" : trendDown ? "text-rose-400" : "text-zinc-300"}`}>
              {trendUp ? "↗" : trendDown ? "↘" : "→"}
            </div>
          </div>
        </div>

        {/* Bottom verdict */}
        <div className="text-center mt-3">
          <span className={`font-bold text-base ${labelClass}`} data-testid="bb-label">{label}</span>
          <span className="text-zinc-500 text-xs ml-1.5 font-mono-num">({timeframe})</span>
        </div>
      </div>
    </div>
  );
}
