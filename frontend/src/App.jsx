import { useEffect, useState } from "react";
import { LangContext, useT } from "./i18n.js";
import Dashboard from "./pages/Dashboard.jsx";
import NewRegistration from "./pages/NewRegistration.jsx";
import History from "./pages/History.jsx";

function Seal() {
  // A simple neutral seal (document + shield). Not the national emblem.
  return (
    <svg className="seal" viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="20" cy="20" r="19" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M20 7l9 3.5v8.5c0 6-4 10.5-9 13-5-2.5-9-7-9-13v-8.5z" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M15.5 17h9M15.5 21h9M15.5 25h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function Shell() {
  const { t, lang, setLang } = useT();
  const [page, setPage] = useState("home");
  const [detailRef, setDetailRef] = useState(null);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const go = (target, ref = null) => {
    setPage(target);
    setDetailRef(ref);
    window.scrollTo({ top: 0 });
  };

  const nav = [
    ["home", t("nav.home")],
    ["new", t("nav.new")],
    ["history", t("nav.history")],
  ];

  return (
    <>
      <header className="site-header">
        <div className="flag-strip" aria-hidden="true" />
        <div className="wrap header-row">
          <button className="brand" onClick={() => go("home")}>
            <Seal />
            <span>
              <span className="brand-title">{t("app.title")}</span>
              <span className="brand-tag">{t("app.tagline")}</span>
            </span>
          </button>
          <div className="lang" role="group" aria-label={t("lang.label")}>
            <button aria-pressed={lang === "en"} onClick={() => setLang("en")}>English</button>
            <button aria-pressed={lang === "hi"} onClick={() => setLang("hi")}>हिंदी</button>
          </div>
        </div>
        <nav className="wrap nav" aria-label="Main">
          {nav.map(([key, label]) => (
            <button key={key} className={page === key ? "active" : ""} aria-current={page === key ? "page" : undefined}
              onClick={() => go(key)}>
              {label}
            </button>
          ))}
        </nav>
      </header>

      <div className="academic-banner" role="note">
        <div className="wrap">{t("banner.academic")}</div>
      </div>

      <main className="wrap main">
        {page === "home" && <Dashboard go={go} />}
        {page === "new" && <NewRegistration go={go} />}
        {page === "history" && <History detailRef={detailRef} go={go} />}
      </main>

      <footer className="site-footer">
        <div className="wrap">
          <p>{t("banner.academic")}</p>
          <p>{t("footer.future")}</p>
        </div>
      </footer>
    </>
  );
}

export default function App() {
  const [lang, setLangState] = useState(() => localStorage.getItem("lang") || "en");
  const setLang = (value) => {
    localStorage.setItem("lang", value);
    setLangState(value);
  };
  return (
    <LangContext.Provider value={{ lang, setLang }}>
      <Shell />
    </LangContext.Provider>
  );
}
