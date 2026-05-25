import React from "react";

export default function Histogram({
  data = [],
  width = 320,
  height = 160,
  bins = 8,
  onBarClick,
}) {
  // data: [{name, value}] where value = h-index
  const values = data.map((d) => Number(d.value) || 0);
  const max = Math.max(1, ...values);
  const min = Math.min(0, ...values);
  const binSize = Math.max(1, Math.ceil((max - min) / bins));
  const counts = new Array(bins).fill(0);
  const labels = new Array(bins)
    .fill(0)
    .map((_, i) => `${min + i * binSize}-${min + (i + 1) * binSize - 1}`);
  data.forEach((d) => {
    const v = Number(d.value) || 0;
    let idx = Math.floor((v - min) / binSize);
    if (idx < 0) idx = 0;
    if (idx >= bins) idx = bins - 1;
    counts[idx] += 1;
  });
  const padding = { top: 12, right: 12, bottom: 30, left: 24 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;
  const maxCount = Math.max(1, ...counts);
  const barW = innerW / bins;
  const [tooltip, setTooltip] = React.useState(null);

  const onMove = (e, info) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      label: info.label,
      value: info.count,
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
        <g transform={`translate(${padding.left},${padding.top})`}>
          {counts.map((c, i) => {
            const h = (c / maxCount) * innerH;
            const x = i * barW;
            const y = innerH - h;
            return (
              <g key={i}>
                <rect
                  x={x + 4}
                  y={y}
                  width={barW - 8}
                  height={h}
                  fill="#60a5fa"
                  rx={4}
                  style={{ cursor: onBarClick ? "pointer" : "default" }}
                  onMouseMove={(e) => onMove(e, { label: labels[i], count: c })}
                  onMouseLeave={() => setTooltip(null)}
                  onClick={() =>
                    onBarClick && onBarClick({ binIndex: i, label: labels[i] })
                  }
                />
                <text
                  x={x + barW / 2}
                  y={innerH + 14}
                  textAnchor="middle"
                  style={{ fontSize: 11, fill: "#0f1724" }}
                >
                  {labels[i]}
                </text>
                <text
                  x={x + barW / 2}
                  y={y - 6}
                  textAnchor="middle"
                  style={{ fontSize: 11, fill: "#0f1724" }}
                >
                  {c}
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
