import type { Plan } from "../types";
import "./PilotAgentPanel.css";

interface Props {
  plan: Plan;
}

export default function PilotAgentPanel({ plan }: Props) {
  const guidance = plan.pilot_guidance;
  const isAiGuidance =
    plan.scan_model !== "none" &&
    plan.scan_model !== "rule_engine_only" &&
    plan.scan_model !== "ai_unavailable";

  if (!guidance.message && !guidance.developer_hint) {
    return null;
  }

  return (
    <div className="pilot-panel">
      <div className="pilot-panel-header">
        <h4>
          Pilot agent
          {isAiGuidance && <span className="ai-badge">Grok</span>}
        </h4>
      </div>
      {guidance.message && <p>{guidance.message}</p>}
      {guidance.suggestion && <p className="suggestion">{guidance.suggestion}</p>}
      {guidance.developer_hint && (
        <div className="developer-hint">
          <strong>Developer coach</strong>
          <pre>{guidance.developer_hint}</pre>
        </div>
      )}
    </div>
  );
}
