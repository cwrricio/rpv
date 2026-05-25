import React from "react";

function polarToCartesian(cx, cy, r, angleDeg) {
  const a = ((angleDeg - 90) * Math.PI) / 180.0;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArcFlag = endAngle - startAngle > 180 ? "1" : "0";
  const d = [
    `M ${cx} ${cy}`,
    `L ${start.x} ${start.y}`,
    `A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`,
    "Z",
  ].join(" ");
  return d;
}

const COLORS = [
  "#60a5fa",
  "#34d399",
  "#f472b6",
  "#f59e0b",
  "#a78bfa",
  "#fb7185",
];

export default function PieChart({
  data = [],
  width = 300,
  height = 240,
  innerRadius = 0,
  colors = COLORS,
}) {
  const cx = width / 2;
  const cy = height / 2;
  const r = Math.min(width, height) / 2 - 20;
  const total = data.reduce((s, d) => s + (d.count || 0), 0) || 1;

  let acc = 0;
  const [tooltip, setTooltip] = React.useState(null);

  const onMove = (e, label, value) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      label,
      value,
    });
  };

  return (
    <div className="chart-wrapper">
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="Gráfico de distribuição"
      >
        {data.map((d, i) => {
          const startAngle = (acc / total) * 360;
          acc += d.count;
          const endAngle = (acc / total) * 360;
          const path = describeArc(cx, cy, r, startAngle, endAngle);
          const color = (colors || COLORS)[i % (colors || COLORS).length];
          // label position (centroid) in polar coords
          const midAngle = (startAngle + endAngle) / 2;
          const labelRadius = r * 0.6;
          const centroid = polarToCartesian(cx, cy, labelRadius, midAngle);
          const sliceAngle = endAngle - startAngle;

          let labelEl = null;
          if (sliceAngle > 10) {
            const name = String(d.name || "");
            if (sliceAngle < 24) {
              const initials = name
                .split(/\s+/)
                .filter(Boolean)
                .slice(0, 2)
                .map((s) => s[0]?.toUpperCase() || "")
                .join("");
              labelEl = (
                <text
                  x={centroid.x}
                  y={centroid.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={12}
                  fill="#fff"
                  stroke="#000"
                  strokeWidth={0.6}
                  paintOrder="stroke fill"
                  style={{ pointerEvents: "none", fontWeight: 700 }}
                >
                  {initials}
                </text>
              );
            } else {
              const maxLen = 18;
              let left = name;
              let right = "";
              if (name.length > maxLen) {
                const words = name.split(/\s+/);
                const half = Math.ceil(words.length / 2);
                left = words.slice(0, half).join(" ");
                right = words.slice(half).join(" ");
                if (left.length > maxLen)
                  left = left.slice(0, maxLen - 1) + "…";
                if (right.length > maxLen)
                  right = right.slice(0, maxLen - 1) + "…";
              }
              labelEl = (
                <text
                  x={centroid.x}
                  y={centroid.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={11}
                  fill="#fff"
                  stroke="#000"
                  strokeWidth={0.6}
                  paintOrder="stroke fill"
                  style={{ pointerEvents: "none", fontWeight: 600 }}
                >
                  <tspan x={centroid.x} dy={-6}>
                    {left}
                  </tspan>
                  {right ? (
                    <tspan x={centroid.x} dy={14}>
                      {right}
                    </tspan>
                  ) : null}
                </text>
              );
            }
          }

          return (
            <g key={d.id || d.name}>
              <path
                d={path}
                fill={color}
                stroke="#fff"
                strokeWidth={1}
                onMouseMove={(e) => onMove(e, d.name || d.id, d.count)}
                onMouseLeave={() => setTooltip(null)}
              />
              {labelEl}
            </g>
          );
        })}
        {/* center label with total */}
        <text
          x={cx}
          y={cy}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={14}
          fill="#0f172a"
        >
          {total}
        </text>
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
