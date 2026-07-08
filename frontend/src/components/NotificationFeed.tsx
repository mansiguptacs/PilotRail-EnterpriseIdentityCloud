import type { Notification } from "../types";
import "./NotificationFeed.css";

interface Props {
  notifications: Notification[];
}

export default function NotificationFeed({ notifications }: Props) {
  if (notifications.length === 0) {
    return (
      <div className="empty-state">
        No notifications yet. Blocked apply requests will alert approvers here.
      </div>
    );
  }

  return (
    <div className="notification-feed">
      {notifications.map((n) => (
        <div key={n.id} className="notification-item">
          <span className="notification-icon">
            {n.event_type === "NOTIFY_APPROVER" ? "🔔" : "📬"}
          </span>
          <div className="notification-body">
            <div className="notification-meta">
              <span
                className={`event-tag ${
                  n.event_type === "NOTIFY_APPROVER" ? "approver" : "requester"
                }`}
              >
                {n.event_type === "NOTIFY_APPROVER" ? "Approver alert" : "Requester update"}
              </span>
              <span className="notification-channel">{n.channel}</span>
              <span>{new Date(n.timestamp).toLocaleString()}</span>
            </div>
            <p className="notification-message">{n.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
