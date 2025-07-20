import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from "recharts";
import { filterAtmStrikes } from "../../utils/optionCalculations";
import "./OIChart.css";

function OIChart({ rawData, atm, lastUpdated, rowHeight = 40 }) {
  const data = React.useMemo(() => {
    return filterAtmStrikes(rawData, atm);
  }, [rawData, atm]);

  const getPercentageChange = (base, diff) => {
    return base > 0 ? ((diff / base) * 100).toFixed(2) : "0.00";
  };

  // Calculate chart height based on number of rows and row height
  const chartHeight = data.length * rowHeight + rowHeight;
  const barSize = Math.max(10, rowHeight * 0.8); // Ensure bars have minimum height

  return (
    <div className="chart-container">
      <div className="chart-header">Open Interest (OI) Change Chart</div>

      <div className="chart-content-wrapper striped-bg">
        <ResponsiveContainer width="100%" height={chartHeight}>
          <BarChart
            layout="vertical"
            data={data}
            margin={{ top: 20, right: 30, left: 80, bottom: 20 }}
            barSize={barSize}
          >
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="strike"
              tick={{ fill: "#555", fontSize: 13, fontWeight: "bold" }}
              tickLine={false}
              axisLine={false}
              width={60}
              tickMargin={5}
              interval={0}
            />
            <Tooltip
              content={({ payload, label }) => {
                if (!payload || payload.length === 0) return null;
                const d = payload[0].payload;
                const callPct = getPercentageChange(d.call_base, d.call_diff);
                const putPct = getPercentageChange(d.put_base, d.put_diff);
                return (
                  <div
                    style={{
                      background: "#fff",
                      padding: "10px",
                      border: "1px solid #ccc",
                      borderRadius: "6px",
                      fontSize: "13px",
                      color: "#333",
                      boxShadow: "0 0 8px rgba(0,0,0,0.1)",
                    }}
                  >
                    <div><strong>Strike:</strong> {label}</div>
                    <div style={{ color: "#B71C1C" }}>
                      <strong>Put OI Change:</strong> {(d.put_increase ? "+" : "-") + putPct + "%"}
                    </div>
                    <div style={{ color: "#2E7D32" }}>
                      <strong>Call OI Change:</strong> {(d.call_increase ? "+" : "-") + callPct + "%"}
                    </div>
                  </div>
                );
              }}
            />

            <Bar dataKey="put_base" stackId="put" fill="#E57373" />
            <Bar
              dataKey="put_diff"
              stackId="put"
              shape={({ x, y, width, height, payload }) =>
                payload.put_increase ? (
                  <rect x={x} y={y} width={width} height={height} fill="#B71C1C" />
                ) : (
                  <rect
                    x={x + 1}
                    y={y + 1}
                    width={Math.max(0, width - 2)}
                    height={Math.max(0, height - 2)}
                    fill="#909894ff"
                    stroke="#B71C1C"
                    strokeWidth={2}
                  />
                )
              }
            />

            <Bar dataKey="call_base" stackId="call" fill="#81C784" />
            <Bar
              dataKey="call_diff"
              stackId="call"
              shape={({ x, y, width, height, payload }) =>
                payload.call_increase ? (
                  <rect x={x} y={y} width={width} height={height} fill="#2E7D32" />
                ) : (
                  <rect
                    x={x + 1}
                    y={y + 1}
                    width={Math.max(0, width - 2)}
                    height={Math.max(0, height - 2)}
                    fill="#969e9aff"
                    stroke="#2E7D32"
                    strokeWidth={2}
                  />
                )
              }
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="legend-and-updated">
        <div className="oi-legend-bottom">
          <div className="legend-row">
            <div><span className="legend-box" style={{ background: "#2E7D32" }}></span> Call OI ↑</div>
            <div><span className="legend-box" style={{ background: "#B71C1C" }}></span> Put OI ↑</div>
            <div><span className="legend-box" style={{ background: "#81C784" }}></span> Call Base</div>
          </div>
          <div className="legend-row">
            <div><span className="legend-box" style={{ border: "2px solid #2E7D32", background: "#556B5F" }}></span> Call OI ↓</div>
            <div><span className="legend-box" style={{ border: "2px solid #B71C1C", background: "#556B5F" }}></span> Put OI ↓</div>
            <div><span className="legend-box" style={{ background: "#E57373" }}></span> Put Base</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default OIChart;