import { useMemo, useState } from "react";
import type { Notification } from "../types";
import { shortId } from "../utils/format";
import "./NotificationFeed.css";

interface Props {
  notifications: Notification[];
  onOpenPlan: (planId: string) => void;
}

type Filter = "all" | "approver" | "requester";

export default function NotificationFeed({ notifications, onOpenPlan }: Props) {
  const [filter, setFilter] = useState<Filter>("all");

  const filtered = useMemo(() => {
    if (filter === "approver") {
      return notifications.filter((n) => n.event_type === "NOTIFY_APPROVER");
    }
    if (filter === "requester") {
      return notifications.filter((n) => n.event_type !== "NOTIFY_APPROVER");
    }
    return notifications;
  }, [notifications, filter]);

  if (notifications.length === 0) {
    return (
      <div className="empty-state">
        No alerts yet. Blocked apply requests notify approvers here.
      </div>
    );
  }

  return (
    <div className="notification-feed-wrap">
      <div className="notification-filters">
        <button
          type="button"
          className={filter === "all" ? "active" : ""}
          onClick={() => setFilter("all")}
        >
          All
        </button>
        <button
          type="button"
          className={filter === "approver" ? "active" : ""}
          onClick={() => setFilter("approver")}
        >
          Approver
        </button>
        <button
          type="button"
          className={filter === "requester" ? "active" : ""}
          onClick={() => setFilter("requester")}
        >
          Requester
        </button>
      </div>

      <div className="notification-feed">
        {filtered.map((n) => (
          <div key={n.id} className="notification-item">
            <div className="notification-body">
              <div className="notification-meta">
                <span
                  className={`event-tag ${
                    n.event_type === "NOTIFY_APPROVER" ? "approver" : "requester"
                  }`}
                >
                  {n.event_type === "NOTIFY_APPROVER" ? "Approver" : "Requester"}
                </span>
                <span className="notification-recipient">{n.recipient}</span>
                <span className="notification-channel">{n.channel}</span>
                <span>{new Date(n.timestamp).toLocaleString()}</span>
              </div>
              <p className="notification-message">{n.message}</p>
              <button
                type="button"
                className="plan-link"
                onClick={() => onOpenPlan(n.plan_id)}
              >
                View plan {shortId(n.plan_id)}…
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
