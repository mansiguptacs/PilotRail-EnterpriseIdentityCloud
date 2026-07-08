import type { PolicyFinding } from "../types";
import "./SecurityAlert.css";

interface Props {
  findings: PolicyFinding[];
}

const CATEGORY_LABELS: Record<string, string> = {
  network_exposure: "Network",
  data_exposure: "Data",
  identity_access: "IAM",
  encryption: "Encryption",
  compliance: "Compliance",
};

export default function SecurityAlert({ findings }: Props) {
  if (findings.length === 0) return null;

  const ruleCount = findings.filter((f) => f.source === "rule_engine").length;
  const aiCount = findings.filter((f) => f.source === "ai_reviewer").length;

  return (
    <div className="security-alert">
      <h3>
        Policy Gap Report — {findings.length} finding(s)
        <span className="finding-sources">
          {ruleCount > 0 && <span className="source-tag rule">Rule Engine: {ruleCount}</span>}
          {aiCount > 0 && <span className="source-tag ai">AI Reviewer: {aiCount}</span>}
        </span>
      </h3>
      <ul>
        {findings.map((f, i) => (
          <li key={i}>
            <div className="finding-header">
              <span className={`finding-severity ${f.severity}`}>{f.severity}</span>
              <span className="finding-policy">{f.policy_id}</span>
              <span className="finding-category">
                {CATEGORY_LABELS[f.category] ?? f.category}
              </span>
              {f.source === "ai_reviewer" && <span className="source-tag ai">AI</span>}
            </div>
            <strong>{f.term}</strong> — {f.message}
            {f.matched_text && (
              <code className="finding-match">{f.matched_text}</code>
            )}
            {f.remediation && (
              <div className="finding-remediation">Fix: {f.remediation}</div>
            )}
            <div className="finding-line">Line {f.line_number}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
