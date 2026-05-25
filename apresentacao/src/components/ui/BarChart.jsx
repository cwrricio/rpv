import React, { useState } from "react";

// Simple horizontal bar chart. Expects data = [{name, value}]
export default function BarChart({
  data = [],
  width = 400,
  height = 300,
  onBarClick,
  highlightId,
}) {
  const [hover, setHover] = useState(null);
  const padding = { top: 8, right: 12, bottom: 24, left: 120 };
  const w = Math.max(120, width);
  const h = Math.max(80, height);
  const innerW = w - padding.left - padding.right;
  const innerH = h - padding.top - padding.bottom;
  const max = Math.max(1, ...data.map((d) => d.value || 0));
  const barH = Math.max(18, innerH / Math.max(1, data.length));
  const [tooltip, setTooltip] = useState(null);
  const onMove = (e, info) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      label: info.label,
      value: info.value,
    });
  };

  return (
    <div className="chart-wrapper">
      <svg
        width="100%"
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        preserveAspectRatio="xMidYMid meet"
      >
        <g transform={`translate(${padding.left},${padding.top})`}>
          {data.map((d, i) => {
            const val = d.value || 0;
            const barWidth = (val / max) * innerW;
            const y = i * barH;
            const isHover = hover === i;
            const isActive = highlightId && highlightId === d.id;
            return (
              <g key={d.name || i} transform={`translate(0,${y})`}>
                <rect
                  x={0}
                  y={2}
                  width={barWidth}
                  height={barH - 6}
                  fill={isActive ? "#2563eb" : isHover ? "#60a5fa" : "#93c5fd"}
                  rx={6}
                  style={{ cursor: onBarClick ? "pointer" : "default" }}
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                  onMouseMove={(e) =>
                    onMove(e, { label: d.name, value: d.value })
                  }
                  onClick={() => onBarClick && onBarClick(d)}
                />
                <text
                  x={-8}
                  y={barH / 2}
                  textAnchor="end"
                  alignmentBaseline="middle"
                  style={{ fontSize: 12, fill: "#0f1724" }}
                >
                  {d.name}
                </text>
                <text
                  x={barWidth + 8}
                  y={barH / 2}
                  alignmentBaseline="middle"
                  style={{ fontSize: 12, fill: "#0f1724" }}
                >
                  {val}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      {tooltip && (
        <div
          className="chart-tooltip"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <div style={{ fontWeight: 700 }}>{tooltip.label}</div>
          <div style={{ opacity: 0.9, fontSize: 12 }}>{tooltip.value}</div>
        </div>
      )}
    </div>
  );
}
