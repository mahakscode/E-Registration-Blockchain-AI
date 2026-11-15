import { useEffect, useState } from "react";
import { useT } from "../i18n.js";
import { getRegistration, listRegistrations } from "../api.js";
import { fmtDate, fmtDateTime, money } from "../format.js";
import ResultPanel, { Detail } from "../components/ResultPanel.jsx";

function OwnershipHistory({ rows }) {
  const { t, lang } = useT();
  if (rows.length === 0) return <p className="muted">{t("d.noHistory")}</p>;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>{t("d.owner")}</th>
            <th>{t("d.ownerId")}</th>
            <th>{t("d.from")}</th>
            <th>{t("d.until")}</th>
            <th>{t("d.how")}</th>
            <th>{t("d.price")}</th>
            <th>{t("d.mutation")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((h) => (
            <tr key={h.id} className={h.ceased_on ? "" : "row-current"}>
              <td>{h.owner_name}</td>
              <td className="mono">{h.owner_id}</td>
              <td>{h.acquired_on.length > 10 ? fmtDateTime(h.acquired_on, lang) : fmtDate(h.acquired_on, lang)}</td>
              <td>
                {h.ceased_on
                  ? h.ceased_on.length > 10 ? fmtDateTime(h.ceased_on, lang) : fmtDate(h.ceased_on, lang)
                  : <span className="pill pill-green">{t("d.present")}</span>}
              </td>
              <td>{t(`tt.${h.transfer_type}`)}</td>
              <td>{h.sale_price ? money(h.sale_price) : "—"}</td>
              <td className="mono">{h.mutation_id || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SubmittedDetails({ r }) {
  const { t, lang } = useT();
  const unit = t(`unit.${r.unit}`);
  const items = [
    ["property_id", r.property_id], ["property_name", r.property_name], ["khasra_no", r.khasra_no],
    ["khata_no", r.khata_no], ["survey_no", r.survey_no], ["address", r.address, true],
    ["state", r.state], ["district", r.district], ["tehsil", r.tehsil],
    ["area", `${r.area} ${unit}`], ["property_type", t(`type.${r.property_type}`)],
    ["land_category", t(`cat.${r.land_category}`)], ["circle_rate", money(r.circle_rate)],
    ["declared_price", money(r.declared_price)], ["seller_name", r.seller_name], ["seller_id", r.seller_id],
    ["seller_contact", r.seller_contact], ["existing_ownership", r.existing_ownership, true],
    ["buyer_name", r.buyer_name], ["buyer_id", r.buyer_id], ["buyer_contact", r.buyer_contact],
    ["registration_date", fmtDate(r.registration_date, lang)], ["sale_deed_ref", r.sale_deed_ref],
    ["transaction_details", r.transaction_details, true],
  ];
  return (
    <section className="panel">
      <h3>{t("d.submitted")}</h3>
      <dl className="details">
        {items.map(([name, value, wide]) => (
          <Detail key={name} label={t(`f.${name}`)} value={value} wide={wide} />
        ))}
      </dl>
    </section>
  );
}

function RegistrationDetail({ reference, go }) {
  const { t } = useT();
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setData(null);
    getRegistration(reference).then(setData).catch(() => setFailed(true));
  }, [reference]);

  return (
    <>
      <button className="link back" onClick={() => go("history")}>← {t("btn.back")}</button>
      {failed && <p className="notice notice-red">{t("err.generic")}</p>}
      {!data && !failed && <p className="muted">{t("loading")}</p>}
      {data && (
        <>
          <ResultPanel data={data} />
          <SubmittedDetails r={data.registration} />
          <section className="panel">
            <h3>{t("d.ownershipHistory")}</h3>
            <OwnershipHistory rows={data.ownership_history} />
          </section>
        </>
      )}
    </>
  );
}

export default function History({ detailRef, go }) {
  const { t, lang } = useT();
  const [rows, setRows] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (detailRef) return;
    listRegistrations().then(setRows).catch(() => setFailed(true));
  }, [detailRef]);

  if (detailRef) return <RegistrationDetail reference={detailRef} go={go} />;

  return (
    <>
      <h1 className="page-title">{t("h.title")}</h1>
      <p className="lead">{t("h.intro")}</p>
      {failed && <p className="notice notice-red">{t("err.network")}</p>}
      {rows && rows.length === 0 && <p className="muted">{t("h.empty")}</p>}
      {rows && rows.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>{t("h.reference")}</th>
                <th>{t("f.property_id")}</th>
                <th>{t("f.property_name")}</th>
                <th>{t("conf.buyer")}</th>
                <th>{t("conf.seller")}</th>
                <th>{t("h.registration_date")}</th>
                <th>{t("h.verification")}</th>
                <th>{t("h.mutation")}</th>
                <th><span className="sr-only">{t("btn.view")}</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const ref = r.registration_id || r.case_id;
                return (
                  <tr key={ref}>
                    <td className="mono">{ref}</td>
                    <td>{r.property_id}</td>
                    <td>{r.property_name}</td>
                    <td>{r.buyer_name}</td>
                    <td>{r.seller_name}</td>
                    <td>{fmtDate(r.registration_date, lang)}</td>
                    <td><span className={`pill pill-${r.verification_status === "Verified" ? "green" : "red"}`}>{t(`vs.${r.verification_status}`)}</span></td>
                    <td><span className={`pill pill-${r.mutation_status === "Completed" ? "green" : "grey"}`}>{t(`ms.${r.mutation_status}`)}</span></td>
                    <td><button className="btn btn-small" onClick={() => go("history", ref)}>{t("btn.view")}</button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
