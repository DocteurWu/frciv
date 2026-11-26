export function compact(n) {
  if (n == null || Number.isNaN(n)) return "–";
  const a = Math.abs(n);
  const fr = (v, d) => v.toFixed(d).replace(".", ",").replace(/,0$/, "");
  if (a >= 1e12) return fr(n / 1e12, a >= 1e13 ? 1 : 2) + " Md";
  if (a >= 1e9) return fr(n / 1e9, a >= 1e11 ? 0 : 1) + " Md";
  if (a >= 1e6) return fr(n / 1e6, a >= 1e8 ? 0 : 1) + " M";
  if (a >= 1e3) return fr(n / 1e3, a >= 1e5 ? 0 : 1) + " k";
  return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, "\u202f");
}

export const money = (n) => (n == null ? "–" : compact(n) + " €");
export const dollars = (n) => (n == null ? "–" : Math.round(n).toLocaleString("fr-FR") + " €");
export const int = (n) => (n == null ? "–" : Math.round(n).toLocaleString("fr-FR"));
export const pct = (x, d = 1) => (x == null ? "–" : (x * 100).toFixed(d).replace(".", ",") + "%");

export function yieldValue(y, v) {
  return (y.unit === "usd" || y.unit === "eur") ? money(v) : compact(v);
}

export function popShort(n) {
  if (n >= 1e7) return Math.round(n / 1e6) + "M";
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  return Math.round(n / 1e3) + "K";
}

export const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
