import type { ReactNode } from "react";
import "./Badge.css";

interface Props {
  children: ReactNode;
  variant?: string;
  className?: string;
}

export default function Badge({ children, variant = "neutral", className = "" }: Props) {
  return <span className={`ui-badge ${variant} ${className}`.trim()}>{children}</span>;
}
