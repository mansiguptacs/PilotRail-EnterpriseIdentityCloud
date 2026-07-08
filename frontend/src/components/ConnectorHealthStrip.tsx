import type { ConnectorHealth } from "../types";
import "./ConnectorHealthStrip.css";

interface Props {
  connectors: ConnectorHealth[];
}

export default function ConnectorHealthStrip({ connectors }: Props) {
  return (
    <div className="connector-strip">
      {connectors.map((c) => (
        <div key={c.name} className="connector-item" title={c.message}>
          <span className={`connector-dot ${c.status}`} />
          <span className="connector-name">{c.name}</span>
          <span className="connector-message">{c.status}</span>
        </div>
      ))}
    </div>
  );
}
