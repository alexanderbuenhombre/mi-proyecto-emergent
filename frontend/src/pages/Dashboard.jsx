import { useEffect, useState } from "react";
import {
  fetchPrice, fetchSessions, fetchMultiTF, fetchStrength,
  fetchActiveSignal, fetchHistory, fetchBinary, fetchStats,
} from "../lib/signalsApi";
import { usePolling } from "../lib/usePolling";
import { loadVoiceSettings } from "../lib/voice";
import { useVoiceAlerts } from "../lib/useVoiceAlerts";
import PriceHeader from "../components/dashboard/PriceHeader";
import ActiveSignalCard from "../components/dashboard/ActiveSignalCard";
import BullsBearsGauge from "../components/dashboard/BullsBearsGauge";
import MultiTimeframe from "../components/dashboard/MultiTimeframe";
import StrengthBars from "../components/dashboard/StrengthBars";
import MarketSessions from "../components/dashboard/MarketSessions";
import SignalHistory from "../components/dashboard/SignalHistory";
import NextCandleBinary from "../components/dashboard/NextCandleBinary";
import SystemStats from "../components/dashboard/SystemStats";
import SourceSelector from "../components/dashboard/SourceSelector";
import ConfluencePanel from "../components/dashboard/ConfluencePanel";
import VoiceSettings from "../components/dashboard/VoiceSettings";
import { saveVoiceSettings } from "../lib/voice";

export default function Dashboard() {
  const [source, setSource] = useState("swissquote");
  const [tf, setTf] = useState("5m");
  const [voiceSettings, setVoiceSettings] = useState(() => loadVoiceSettings());

  const toggleVoice = () => {
    setVoiceSettings((s) => {
      const next = { ...s, enabled: !s.enabled };
      saveVoiceSettings(next);
      return next;
    });
  };

  // Live tick polling: 1s for Swissquote (sub-second feed), 2s for others
  const priceIntervalMs = source === "swissquote" ? 1000 : 2000;
  const price = usePolling(() => fetchPrice(source), priceIntervalMs, [source]);
  const sessions = usePolling(fetchSessions, 30000);
  const multi = usePolling(fetchMultiTF, 10000);
  const strength = usePolling(fetchStrength, 8000);
  // Signal polling every 3s (was 6s) → señales aparecen con más anticipación
  const activeSig = usePolling(() => fetchActiveSignal(tf), 3000, [tf]);
  const history = usePolling(fetchHistory, 15000);
  const binary = usePolling(fetchBinary, 3000);
  const stats = usePolling(fetchStats, 15000);

  const tfAnalysis = activeSig.data?.analysis || multi.data?.timeframes?.[tf];
  const recommendation = activeSig.data?.recommendation;
  const confluence = activeSig.data?.confluence;

  useVoiceAlerts({
    signal: activeSig.data?.signal,
    recommendation,
    settings: voiceSettings,
    timeframe: tf,
  });

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-3 sm:p-5 lg:p-6" data-testid="dashboard-root">
      <div className="max-w-[1600px] mx-auto space-y-4">
        <PriceHeader price={price.data} sessions={sessions.data} />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* LEFT */}
          <div className="lg:col-span-3 flex flex-col gap-4">
            <BullsBearsGauge analysis={tfAnalysis} timeframe={tf} />
            <ConfluencePanel data={confluence} />
            <SourceSelector value={source} onChange={setSource} />
            <VoiceSettings onChange={setVoiceSettings} />
            <SystemStats data={stats.data} />
          </div>

          {/* CENTER */}
          <div className="lg:col-span-6 flex flex-col gap-4">
            <ActiveSignalCard
              payload={activeSig.data}
              livePrice={price.data?.price}
              timeframe={tf}
              voiceEnabled={voiceSettings.enabled}
              onToggleVoice={toggleVoice}
            />
            <SignalHistory data={history.data} />
          </div>

          {/* RIGHT */}
          <div className="lg:col-span-3 flex flex-col gap-4">
            <NextCandleBinary data={binary.data} />
            <MultiTimeframe data={multi.data} selected={tf} onSelect={setTf} />
            <StrengthBars data={strength.data} />
            <MarketSessions data={sessions.data} />
          </div>
        </div>

        <footer className="text-center text-[11px] text-zinc-600 pt-4 pb-2">
          XAU/USD Real-Time Signals · TradingView OANDA spot + Gold-API LBMA · Educacional, no es asesoría financiera.
        </footer>
      </div>
    </div>
  );
}
