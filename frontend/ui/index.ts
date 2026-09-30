/**
 * PRAHARI Unified UI & Design System
 * 
 * Single authoritative folder containing all visual components, layouts, charts,
 * widgets, and theme tokens that govern the presentation across all screens.
 */

// ─── Theme & Design Tokens ──────────────────────────────────────────
export * from "./theme";
export { default as PRAHARI_THEME } from "./theme";

// ─── Layout & Navigation ────────────────────────────────────────────
export * from "./layout/Header";
export * from "./layout/Sidebar";
export * from "./layout/Shell";

// ─── Visual Primitives & Widgets ────────────────────────────────────
export * from "./widgets/StatCard";
export * from "./widgets/RiskBadge";
export * from "./widgets/Modal";
export * from "./widgets/Toast";
export * from "./widgets/EmptyState";
export * from "./widgets/Skeleton";

// ─── Data Visualization & Charts ────────────────────────────────────
export * from "./charts/RiskDistributionChart";
export * from "./charts/WorkloadTrendChart";

// ─── Authentication & Route Protection ──────────────────────────────
export * from "./auth/RoleGuard";
