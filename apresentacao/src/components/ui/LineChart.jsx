import React from "react";

// Simple line chart for series of {x, y}
export default function LineChart({ data = [], width = 520, height = 200 }) {
  if (!data || data.length === 0)
    return (
      <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} />
    );
  const xs = data.map((d) => d.x);
  const ys = data.map((d) => d.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const mapX = (v) => ((v - minX) / (maxX - minX || 1)) * (width - 40) + 20;
  const mapY = (v) =>
    height - 20 - ((v - minY) / (maxY - minY || 1)) * (height - 40);
  const path = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${mapX(d.x)} ${mapY(d.y)}`)
    .join(" ");

  const [tooltip, setTooltip] = React.useState(null);
  const onMove = (e, d) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      label: d.x,
      value: d.y,
    });
  };

  return (
    <div className="chart-wrapper">
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMidYMid meet"
      >
        <path d={path} fill="none" stroke="#34d399" strokeWidth={2} />
        {data.map((d, i) => (
          <circle
            key={i}
            cx={mapX(d.x)}
            cy={mapY(d.y)}
            r={4}
            fill="#10b981"
            onMouseMove={(e) => onMove(e, d)}
            onMouseLeave={() => setTooltip(null)}
          />
        ))}
        {/* x labels */}
        {data.map((d, i) => (
          <text
            key={`x-${i}`}
            x={mapX(d.x)}
            y={height - 2}
            fontSize={10}
            textAnchor="middle"
          >
            {d.x}
          </text>
        ))}
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
