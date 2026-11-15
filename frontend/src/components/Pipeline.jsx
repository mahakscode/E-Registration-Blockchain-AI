import { useT } from "../i18n.js";

const STAGES = ["verify", "fraud", "register", "mutate"];
const ICON = { pass: "✓", warn: "!", fail: "✕", skip: "–", idle: "" };

// Four connected steps. In "explain" mode (home page) it describes each step.
// In result mode it shows what actually happened: pass, warn, fail or skip.
export default function Pipeline({ states, explain = false }) {
  const { t } = useT();
  return (
    <ol className={`pipeline ${explain ? "pipeline-explain" : ""}`}>
      {STAGES.map((stage, index) => {
        const state = explain ? "idle" : states[stage];
        return (
          <li key={stage} className={`pipe-step pipe-${state}`}>
            <span className="pipe-dot" aria-hidden="true">{explain ? index + 1 : ICON[state]}</span>
            <span className="pipe-name">{t(`stage.${stage}`)}</span>
            {explain && <span className="pipe-text">{t(`stage.${stage}.text`)}</span>}
          </li>
        );
      })}
    </ol>
  );
}
