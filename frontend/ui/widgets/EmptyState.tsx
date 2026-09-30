import React from "react";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  message?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  message,
  action,
  className,
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center py-12 px-6 text-center rounded-xl ${className || ""}`}
      style={{ border: "1.5px dashed #CDE0CB", background: "#F8FAF7" }}
    >
      {icon && (
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
          style={{ background: "#EFF5EE", border: "1px solid #CDE0CB", color: "#385E31" }}
        >
          {icon}
        </div>
      )}
      <h3 className="text-sm font-semibold" style={{ color: "#1C281A" }}>
        {title}
      </h3>
      {message && (
        <p className="text-xs mt-1.5 max-w-sm leading-relaxed" style={{ color: "#728070" }}>
          {message}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
};
