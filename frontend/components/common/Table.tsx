"use client";

import React from "react";

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  render?: (row: T, index: number) => React.ReactNode;
  align?: "left" | "center" | "right";
  width?: string;
  className?: string;
}

export interface ResponsiveTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T, index: number) => string | number;
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
  renderMobileCard?: (item: T, index: number) => React.ReactNode;
  className?: string;
}

export function ResponsiveTable<T>({
  columns,
  data,
  keyExtractor,
  emptyMessage = "No records found.",
  onRowClick,
  renderMobileCard,
  className = "",
}: ResponsiveTableProps<T>) {
  if (data.length === 0) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-[#CFDDCE] text-xs text-[#677766]">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`}>
      {/* Mobile view if renderMobileCard provided */}
      {renderMobileCard && (
        <div className="block md:hidden space-y-3">
          {data.map((item, idx) => (
            <div
              key={keyExtractor(item, idx)}
              onClick={() => onRowClick && onRowClick(item)}
              className={onRowClick ? "cursor-pointer" : ""}
            >
              {renderMobileCard(item, idx)}
            </div>
          ))}
        </div>
      )}

      {/* Desktop / Default Table */}
      <div
        className={`${
          renderMobileCard ? "hidden md:block" : "block"
        } overflow-x-auto rounded-xl border border-[#CFDDCE] bg-white shadow-sm`}
      >
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-[#FAF9F5] border-b border-[#CFDDCE] text-[#3B4B3A] font-semibold uppercase tracking-wider">
              {columns.map((col) => (
                <th
                  key={col.key}
                  style={{ width: col.width }}
                  className={`py-3 px-4 ${
                    col.align === "center"
                      ? "text-center"
                      : col.align === "right"
                      ? "text-right"
                      : "text-left"
                  } ${col.className || ""}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E4ECE3] text-[#182417]">
            {data.map((item, rowIdx) => (
              <tr
                key={keyExtractor(item, rowIdx)}
                onClick={() => onRowClick && onRowClick(item)}
                className={`transition-colors ${
                  onRowClick
                    ? "cursor-pointer hover:bg-[#F6F7F3]"
                    : "hover:bg-[#FAF9F5]"
                }`}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`py-3 px-4 ${
                      col.align === "center"
                        ? "text-center"
                        : col.align === "right"
                        ? "text-right"
                        : "text-left"
                    } ${col.className || ""}`}
                  >
                    {col.render
                      ? col.render(item, rowIdx)
                      : (item as any)[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
