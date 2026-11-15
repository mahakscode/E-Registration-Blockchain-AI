import { useEffect, useState } from "react";
import { useT } from "../i18n.js";
import { getStats, listRegistrations } from "../api.js";
import { fmtDate } from "../format.js";
import Pipeline from "../components/Pipeline.jsx";

export default function Dashboard({ go }) {
  const { t, lang } = useT();
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    getStats().then(setStats).catch(() => setOffline(true));
    listRegistrations().then((rows) => setRecent(rows.slice(0, 5))).catch(() => setOffline(true));
  }, []);

  return (
    <>
      {offline && <p className="notice notice-red">{t("err.network")}</p>}

      <section className="hero">
        <div className="hero-text">
          <h1>{t("hero.title")}</h1>
          <p>{t("hero.text")}</p>
          <button className="btn btn-primary btn-large" onClick={() => go("new")}>{t("hero.cta")}</button>
        </div>

        <div className="delay" role="group" aria-label={t("delay.title")}>
          <h2>{t("delay.title")}</h2>
          <div className="delay-row">
            <span className="delay-label">{t("delay.existing")}</span>
            <div className="delay-track"><div className="delay-bar delay-bar-old" /></div>
            <span className="delay-value">{t("delay.existingValue")}</span>
          </div>
          <div className="delay-row">
            <span className="delay-label">{t("delay.proposed")}</span>
            <div className="delay-track"><div className="delay-bar delay-bar-new" /></div>
            <span className="delay-value delay-value-new">{t("delay.proposedValue")}</span>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>{t("flow.title")}</h2>
        <Pipeline explain />
      </section>

      <section className="section">
        <dl className="stats">
          <div>
            <dt>{t("stats.records")}</dt>
            <dd>{stats ? stats.records : "—"}</dd>
          </div>
          <div>
            <dt>{t("stats.registered")}</dt>
            <dd>{stats ? stats.registered : "—"}</dd>
          </div>
          <div>
            <dt>{t("stats.held")}</dt>
            <dd>{stats ? stats.held : "—"}</dd>
          </div>
          <div>
            <dt>{t("stats.avg")}</dt>
            <dd>{stats && stats.avg_mutation_ms != null ? `${stats.avg_mutation_ms} ${t("stats.ms")}` : "—"}</dd>
          </div>
        </dl>
      </section>

      <section className="section">
        <div className="section-head">
          <h2>{t("recent.title")}</h2>
          <button className="link" onClick={() => go("history")}>{t("recent.all")}</button>
        </div>
        {recent && recent.length === 0 && <p className="muted">{t("recent.empty")}</p>}
        {recent && recent.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("h.reference")}</th>
                  <th>{t("f.property_id")}</th>
                  <th>{t("conf.buyer")}</th>
                  <th>{t("h.registration_date")}</th>
                  <th>{t("h.verification")}</th>
                  <th>{t("h.mutation")}</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((r) => {
                  const ref = r.registration_id || r.case_id;
                  return (
                    <tr key={ref}>
                      <td><button className="link mono" onClick={() => go("history", ref)}>{ref}</button></td>
                      <td>{r.property_id}</td>
                      <td>{r.buyer_name}</td>
                      <td>{fmtDate(r.registration_date, lang)}</td>
                      <td><span className={`pill pill-${r.verification_status === "Verified" ? "green" : "red"}`}>{t(`vs.${r.verification_status}`)}</span></td>
                      <td><span className={`pill pill-${r.mutation_status === "Completed" ? "green" : "grey"}`}>{t(`ms.${r.mutation_status}`)}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
