// Number and date helpers. Names, IDs and addresses typed by the user are never translated.
export const money = (n) => "₹" + new Intl.NumberFormat("en-IN").format(Math.round(Number(n)));
export const num = (n) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 }).format(Number(n));

function toDate(value) {
  return new Date(String(value).replace(" ", "T"));
}
export function fmtDate(value, lang) {
  if (!value) return "—";
  return toDate(value).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", {
    day: "2-digit", month: "short", year: "numeric",
  });
}
export function fmtDateTime(value, lang) {
  if (!value) return "—";
  return toDate(value).toLocaleString(lang === "hi" ? "hi-IN" : "en-IN", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}
export const todayISO = () => {
  const d = new Date();
  const pad = (x) => String(x).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};
