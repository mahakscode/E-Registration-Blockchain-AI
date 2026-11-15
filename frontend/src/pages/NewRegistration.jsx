import { useEffect, useRef, useState } from "react";
import { useT } from "../i18n.js";
import { getDemoCases, submitRegistration } from "../api.js";
import { todayISO } from "../format.js";
import ResultPanel from "../components/ResultPanel.jsx";

const UNITS = ["sqm", "sqft", "acre", "hectare"];
const TYPES = ["Residential", "Commercial", "Agricultural"];
const CATEGORIES = ["Abadi", "Irrigated", "Unirrigated", "NonAgricultural", "CommercialPlot"];

// The whole form is described by these lists, so adding a field is a one-line change.
const SECTIONS = [
  {
    title: "section.property",
    fields: [
      { name: "property_id", placeholder: "PROP1001" },
      { name: "property_name" },
      { name: "khasra_no", placeholder: "245/1" },
      { name: "khata_no", placeholder: "KH-3001" },
      { name: "survey_no", placeholder: "SVY-501" },
      { name: "address", wide: true },
      { name: "state" },
      { name: "district" },
      { name: "tehsil" },
      { name: "area", type: "number" },
      { name: "unit", options: UNITS, optionKey: "unit" },
      { name: "property_type", options: TYPES, optionKey: "type" },
      { name: "land_category", options: CATEGORIES, optionKey: "cat" },
      { name: "circle_rate", type: "number" },
      { name: "declared_price", type: "number" },
    ],
  },
  {
    title: "section.seller",
    fields: [
      { name: "seller_name" },
      { name: "seller_id", placeholder: "OWN100001" },
      { name: "seller_contact", type: "tel", placeholder: "9876543210" },
      { name: "existing_ownership", wide: true, multiline: true },
    ],
  },
  {
    title: "section.buyer",
    fields: [
      { name: "buyer_name" },
      { name: "buyer_id", placeholder: "OWN900001" },
      { name: "buyer_contact", type: "tel", placeholder: "9876543210" },
    ],
  },
  {
    title: "section.registration",
    fields: [
      { name: "registration_date", type: "date" },
      { name: "sale_deed_ref", placeholder: "SD/2026/12345" },
      { name: "transaction_details", wide: true, multiline: true },
    ],
  },
];

const ALL_FIELDS = SECTIONS.flatMap((s) => s.fields);
const POSITIVE = ["area", "circle_rate", "declared_price"];
const PHONES = ["seller_contact", "buyer_contact"];

const emptyForm = () => ({
  ...Object.fromEntries(ALL_FIELDS.map((f) => [f.name, ""])),
  unit: "sqm",
  property_type: "Residential",
  land_category: "Abadi",
  registration_date: todayISO(),
});

export default function NewRegistration({ go }) {
  const { t } = useT();
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [problem, setProblem] = useState("");
  const [demos, setDemos] = useState([]);
  const resultRef = useRef(null);

  useEffect(() => {
    getDemoCases().then(setDemos).catch(() => {});
  }, []);

  useEffect(() => {
    if (result && resultRef.current) {
      const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      resultRef.current.scrollIntoView({ behavior: calm ? "auto" : "smooth", block: "start" });
    }
  }, [result]);

  const change = (event) => {
    const { name, value } = event.target;
    setForm((f) => ({ ...f, [name]: value }));
    setErrors((e) => ({ ...e, [name]: undefined }));
  };

  const fillDemo = (event) => {
    const chosen = demos.find((d) => d.key === event.target.value);
    if (!chosen) return;
    const next = { ...emptyForm() };
    for (const [key, value] of Object.entries(chosen.form)) next[key] = String(value);
    setForm(next);
    setErrors({});
    setResult(null);
    setProblem("");
  };

  const validate = () => {
    const found = {};
    for (const { name } of ALL_FIELDS) {
      const value = String(form[name]).trim();
      if (!value) found[name] = t("v.required");
      else if (POSITIVE.includes(name) && !(Number(value) > 0)) found[name] = t("v.positive");
      else if (PHONES.includes(name) && !/^[6-9]\d{9}$/.test(value)) found[name] = t("v.phone");
      else if (name === "registration_date" && value > todayISO()) found[name] = t("v.future");
    }
    return found;
  };

  const submit = async (event) => {
    event.preventDefault();
    const found = validate();
    setErrors(found);
    setProblem("");
    if (Object.keys(found).length) {
      setProblem(t("v.summary"));
      return;
    }
    const payload = { ...form };
    for (const name of POSITIVE) payload[name] = Number(form[name]);

    setBusy(true);
    try {
      setResult(await submitRegistration(payload));
    } catch (err) {
      if (err.network) setProblem(t("err.network"));
      else if (err.status === 422 && Array.isArray(err.detail)) {
        const serverErrors = {};
        for (const item of err.detail) serverErrors[item.loc[item.loc.length - 1]] = t("v.invalid");
        setErrors(serverErrors);
        setProblem(t("v.summary"));
      } else setProblem(t("err.generic"));
    } finally {
      setBusy(false);
    }
  };

  const registered = result && result.registration.registration_status === "Registered";

  const startAgain = () => {
    setForm(emptyForm());
    setResult(null);
    setErrors({});
    window.scrollTo({ top: 0 });
  };

  return (
    <>
      <h1 className="page-title">{t("form.title")}</h1>

      {result && (
        <div ref={resultRef} className="result-anchor">
          <ResultPanel data={result}>
            {registered ? (
              <div className="actions">
                <button className="btn btn-primary" onClick={startAgain}>{t("btn.another")}</button>
                <button className="btn" onClick={() => go("history", result.registration.registration_id)}>
                  {t("btn.history")}
                </button>
              </div>
            ) : (
              <p className="muted retry">{t("form.retry")}</p>
            )}
          </ResultPanel>
        </div>
      )}

      {!registered && (
        <form className="form" onSubmit={submit} noValidate>
          <p className="lead">{t("form.intro")}</p>

          <div className="demo-picker">
            <label htmlFor="demo">{t("demo.label")}</label>
            <select id="demo" onChange={fillDemo} value="" disabled={demos.length === 0}>
              <option value="">{t("demo.choose")}</option>
              {demos.map((d) => (
                <option key={d.key} value={d.key}>{t(`demo.${d.key}`)}</option>
              ))}
            </select>
            <span className="muted">{t("demo.hint")}</span>
          </div>

          {SECTIONS.map((section) => (
            <fieldset key={section.title} className="fieldset">
              <legend>{t(section.title)}</legend>
              <div className="grid">
                {section.fields.map((field) => (
                  <div key={field.name} className={`field ${field.wide ? "field-wide" : ""}`}>
                    <label htmlFor={field.name}>{t(`f.${field.name}`)}</label>
                    {field.options ? (
                      <select id={field.name} name={field.name} value={form[field.name]} onChange={change}>
                        {field.options.map((o) => (
                          <option key={o} value={o}>{t(`${field.optionKey}.${o}`)}</option>
                        ))}
                      </select>
                    ) : field.multiline ? (
                      <textarea id={field.name} name={field.name} rows={2} value={form[field.name]}
                        onChange={change} aria-invalid={!!errors[field.name]} />
                    ) : (
                      <input id={field.name} name={field.name} type={field.type || "text"}
                        value={form[field.name]} onChange={change} placeholder={field.placeholder}
                        step={field.type === "number" ? "any" : undefined}
                        max={field.type === "date" ? todayISO() : undefined}
                        inputMode={field.type === "tel" ? "numeric" : undefined}
                        maxLength={field.type === "tel" ? 10 : undefined}
                        aria-invalid={!!errors[field.name]} />
                    )}
                    {errors[field.name] && <span className="field-error">{errors[field.name]}</span>}
                  </div>
                ))}
              </div>
            </fieldset>
          ))}

          {problem && <p className="notice notice-red" role="alert">{problem}</p>}
          <div className="actions">
            <button className="btn btn-primary btn-large" type="submit" disabled={busy}>
              {busy ? t("btn.submitting") : t("btn.submit")}
            </button>
            <button className="btn" type="button" onClick={startAgain}>{t("btn.clear")}</button>
          </div>
        </form>
      )}
    </>
  );
}
