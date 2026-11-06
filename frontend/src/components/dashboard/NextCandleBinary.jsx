import { Flame, ArrowUp, ArrowDown, Minus, Clock } from "lucide-react";

function fmt(s) {
  if (s == null) return "0s";
  const m = Math.floor(s / 60);
  const sec = Math.max(0, Math.floor(s % 60));
  return m > 0 ? `${m}m ${sec.toString().padStart(2, "0")}s` : `${sec}s`;
}

function Row({ tf, item }) {
  const dir = item?.direction || "NEUTRAL";
  const conf = item?.confidence ?? 50;
  const isCall = dir === "CALL";
  const isPut = dir === "PUT";
  const tone = isCall ? "border-emerald-500/30 bg-emerald-500/5" : isPut ? "border-rose-500/30 bg-rose-500/5" : "border-zinc-700 bg-zinc-900/40";
  const dirCls = isCall ? "text-emerald-400" : isPut ? "text-rose-400" : "text-zinc-400";
  const Icon = isCall ? ArrowUp : isPut ? ArrowDown : Minus;
  return (
    <div className={`rounded-lg border ${tone} px-3 py-3 flex items-center justify-between`}>
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono-num font-bold text-zinc-200">{tf}</span>
        <Icon className={`w-4 h-4 ${dirCls}`} />
        <span className={`font-bold ${dirCls}`} data-testid={`binary-${tf.replace(" ", "").toLowerCase()}-direction`}>{dir}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className={`text-[11px] px-2 py-0.5 rounded-md font-mono-num ${conf >= 70 ? "bg-emerald-500/15 text-emerald-400" : conf >= 55 ? "bg-amber-500/15 text-amber-400" : "bg-zinc-700/40 text-zinc-300"}`}>
          {conf}%
        </span>
        <span className="text-xs text-zinc-400 flex items-center gap-1 font-mono-num">
          <Clock className="w-3 h-3" /> {fmt(item?.seconds_left)}
        </span>
      </div>
    </div>
  );
}

export default function NextCandleBinary({ data }) {
  return (
    <div className="card" data-testid="binary-next-candle">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <Flame className="w-4 h-4 text-amber-500" />
          <span className="font-semibold">Próxima Vela · Binarias</span>
        </div>
        <span className="pulse-dot" style={{ background: "#f59e0b" }} />
      </div>
      <div className="card-body space-y-2">
        <Row tf="1 MIN" item={data?.one_min} />
        <Row tf="5 MIN" item={data?.five_min} />
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 text-[11px] text-zinc-400 leading-relaxed mt-2">
          <div className="font-semibold text-zinc-200 mb-1">¿Cómo operar?</div>
          <div>
            La predicción indica la dirección de la próxima vela. Cuando el temporizador llegue a <span className="font-mono-num text-amber-400">00:00</span>, entra la operación:
          </div>
          <div className="mt-1.5">
            <span className="text-emerald-400 font-bold">CALL</span> = la vela subirá ·
            <span className="text-rose-400 font-bold"> PUT</span> = la vela bajará
          </div>
          <div className="mt-1.5">Solo se muestra CALL/PUT con alta probabilidad (confianza ≥75% y temporalidad superior en la misma dirección). Si ves <span className="text-zinc-200 font-bold">ESPERAR</span>, no operes.</div>
        </div>
      </div>
    </div>
  );
}
