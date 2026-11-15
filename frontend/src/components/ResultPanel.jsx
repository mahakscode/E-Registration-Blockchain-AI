import { useT } from "../i18n.js";
import { fmtDateTime, money, num } from "../format.js";
import Pipeline from "./Pipeline.jsx";

function CheckRow({ check }) {
  const { t } = useT();
  const show = (value) =>
    check.fmt === "area"
      ? `${num(value)} ${t("unit.short")}`
      : check.key === "ownership_status"
      ? t(`os.${value}`)
      : check.key === "property_type"
      ? t(`type.${value}`)
      : value;

  return (
    <li className={`check ${check.ok ? "check-ok" : "check-bad"}`}>
      <span className="check-icon" aria-hidden="true">{check.ok ? "✓" : "✕"}</span>
      <span className="check-label">{t(`chk.${check.key}`)}</span>
      <span className="check-values">
        {check.ok ? (
          <span>{show(check.entered ?? check.recorded)}</span>
        ) : (
          <>
            {check.entered != null && (
              <span>{t("chk.entered")}: <b>{show(check.entered)}</b></span>
            )}
            {check.recorded != null && (
              <span>{t("chk.recorded")}: <b>{show(check.recorded)}</b></span>
            )}
            {check.key === "property_id" && <em>{t("chk.idHint")}</em>}
            {check.masked && <em>{t("chk.masked")}</em>}
          </>
        )}
      </span>
    </li>
  );
}

function Verification({ verification }) {
  const { t } = useT();
  const { status, checks } = verification;
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>{t("verify.title")}</h3>
        <span className={`pill pill-${status === "Verified" ? "green" : "red"}`}>{t(`vs.${status}`)}</span>
      </div>
      {status === "Not Found" ? (
        <p className="alert-text">{t("verify.notFound")}</p>
      ) : (
        <>
          {status === "Mismatch" && <p className="alert-text">{t("verify.mismatchNote")}</p>}
          <ul className="checks">
            {/* failed checks first, so the problem is the first thing seen */}
            {[...checks].sort((a, b) => Number(a.ok) - Number(b.ok)).map((c) => (
              <CheckRow key={c.key} check={c} />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function Fraud({ fraud }) {
  const { t } = useT();
  const tone = { Low: "green", Medium: "amber", High: "red" }[fraud.level];
  const decisionTone = fraud.decision === "blocked" ? "red" : fraud.decision === "warning" ? "amber" : "green";

  // Money values are formatted here; the sentence itself comes from the language file.
  const describe = (finding) => {
    const values = { ...finding.params };
    for (const key of ["price", "circle", "previous"]) {
      if (values[key] != null) values[key] = money(values[key]);
    }
    return t(`fr.${finding.code}`, values);
  };

  return (
    <section className="panel">
      <div className="panel-head">
        <h3>{t("fraud.title")}</h3>
        <span className={`pill pill-${decisionTone}`}>{t(`fs.${fraud.decision}`)}</span>
      </div>
      <div className="risk">
        <div className="risk-number">
          <span className={`risk-score tone-${tone}`}>{fraud.score}</span>
          <span className="risk-of">/ 100</span>
        </div>
        <div className="risk-meter">
          <div className="risk-track" role="img" aria-label={`${t("fraud.score")}: ${fraud.score} / 100`}>
            <div className={`risk-fill fill-${tone}`} style={{ width: `${Math.max(fraud.score, 2)}%` }} />
            <span className="risk-tick" style={{ left: "30%" }} />
            <span className="risk-tick" style={{ left: "60%" }} />
          </div>
          <p>{t("fraud.level")}: <b className={`tone-${tone}`}>{t(`level.${fraud.level}`)}</b></p>
        </div>
      </div>
      {fraud.findings.length === 0 ? (
        <p className="muted">{t("fraud.none")}</p>
      ) : (
        <>
          <h4>{t("fraud.reasons")}</h4>
          <ul className="findings">
            {fraud.findings.map((f, i) => (
              <li key={i}>
                <span className={`pill pill-${f.severity === "high" ? "red" : "amber"}`}>
                  {t(f.severity === "high" ? "level.High" : "level.Medium")}
                </span>
                <span>{describe(f)}</span>
                <span className="points">+{f.points}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

export function Detail({ label, value, wide }) {
  return (
    <div className={wide ? "detail wide" : "detail"}>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

// Shows the outcome of one submission. Used right after submitting AND on the history detail page.
export default function ResultPanel({ data, children }) {
  const { t, lang } = useT();
  const { registration: r, verification, fraud, stages } = data;
  const done = r.registration_status === "Registered";

  return (
    <div className="result" aria-live="polite">
      <div className={`result-banner ${done ? "banner-ok" : "banner-hold"}`}>
        <span className="banner-icon" aria-hidden="true">{done ? "✓" : "!"}</span>
        <div>
          <h2>{done ? t("result.registered") : t("result.held")}</h2>
          {done ? (
            <p>
              <b>{t("result.mutated")}</b>
              {r.mutation_ms != null && <> {t("result.mutatedIn", { ms: r.mutation_ms })}</>}
            </p>
          ) : (
            <p>{t("result.heldNote", { id: r.case_id })}</p>
          )}
        </div>
      </div>

      <Pipeline states={stages} />

      {done && (
        <section className="panel">
          <h3>{t("result.confirmation")}</h3>
          <dl className="details">
            <Detail label={t("conf.registration_id")} value={<b className="mono">{r.registration_id}</b>} />
            <Detail label={t("conf.property_id")} value={r.matched_property_id || r.property_id} />
            <Detail label={t("conf.buyer")} value={r.buyer_name} />
            <Detail label={t("conf.seller")} value={r.seller_name} />
            <Detail label={t("conf.khasra")} value={r.khasra_no} />
            <Detail label={t("conf.verification")} value={t(`vs.${r.verification_status}`)} />
            <Detail
              label={t("conf.fraud")}
              value={`${t(`fs.${r.fraud_status}`)} (${t(`level.${r.risk_level}`)}, ${r.risk_score}/100)`}
            />
            <Detail label={t("conf.mutation_id")} value={<b className="mono">{r.mutation_id}</b>} />
            <Detail label={t("conf.mutation_status")} value={t(`ms.${r.mutation_status}`)} />
            <Detail label={t("conf.submitted")} value={fmtDateTime(r.submitted_at, lang)} />
            <Detail label={t("conf.mutation_at")} value={fmtDateTime(r.mutation_at, lang)} />
          </dl>
          <div className="owner-change" aria-label={t("result.ownership")}>
            <div>
              <span className="muted">{t("own.previous")}</span>
              <strong>{r.previous_owner}</strong>
            </div>
            <span className="owner-arrow" aria-hidden="true">→</span>
            <div>
              <span className="muted">{t("own.new")}</span>
              <strong>{r.buyer_name}</strong>
            </div>
          </div>
        </section>
      )}

      <div className="result-grid">
        <Verification verification={verification} />
        <Fraud fraud={fraud} />
      </div>

      {!done && (
        <dl className="details held-meta">
          <Detail label={t("conf.case_id")} value={<b className="mono">{r.case_id}</b>} />
          <Detail label={t("conf.submitted")} value={fmtDateTime(r.submitted_at, lang)} />
          <Detail label={t("conf.mutation_status")} value={t(`ms.${r.mutation_status}`)} />
        </dl>
      )}
      {children}
    </div>
  );
}
