import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, timeout: 15000 });

export const fetchPrice = (source = "tradingview") =>
  api.get(`/price`, { params: { source } }).then((r) => r.data);
export const fetchMultiTF = () => api.get(`/multi-timeframe`).then((r) => r.data);
export const fetchStrength = () => api.get(`/strength`).then((r) => r.data);
export const fetchSessions = () => api.get(`/sessions`).then((r) => r.data);
export const fetchActiveSignal = (timeframe = "5m") =>
  api.get(`/signal/active`, { params: { timeframe } }).then((r) => r.data);
export const fetchHistory = () => api.get(`/signal/history`).then((r) => r.data);
export const fetchBinary = () => api.get(`/binary/next-candle`).then((r) => r.data);
export const fetchStats = () => api.get(`/stats`).then((r) => r.data);
