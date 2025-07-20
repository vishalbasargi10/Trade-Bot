import React from "react";
import { filterAtmStrikes } from "../../utils/optionCalculations";
import "./SentimentTable.css";

function SentimentTable({ rawData, atm, lastUpdated, rowHeight = 40 }) {
  // Calculate font size based on row height
  const fontSize = Math.max(10, rowHeight * 0.35);
  const badgeFontSize = Math.max(8, rowHeight * 0.25);
  const padding = Math.max(4, Math.round(rowHeight * 0.25));
  
  // Helper functions from IVTable
  const formatValue = (value) => {
    const num = parseFloat(value);
    return isNaN(num) ? "N/A" : num.toFixed(2);
  };

  const getIvStrengthClass = (ceIv, peIv) => {
    const avgIv = (parseFloat(ceIv) + parseFloat(peIv)) / 2;
    if (avgIv >= 15) return "high-iv";
    if (avgIv < 10) return "low-iv";
    return "moderate-iv";
  };

  const getIvStrengthLabel = (ceIv, peIv) => {
    const avgIv = (parseFloat(ceIv) + parseFloat(peIv)) / 2;
    if (avgIv >= 15) return "High (↑ Uncertainty)";
    if (avgIv < 10) return "Low (↓ Calm)";
    return "Moderate (Neutral)";
  };

  const data = React.useMemo(() => {
    return filterAtmStrikes(rawData, atm);
  }, [rawData, atm]);

  return (
    <div className="sentiment-table-outer-container">
    <div className="sentiment-wrapper">
      <div className="sentiment-table-container">
        <table style={{ fontSize: `${fontSize}px` }}>
          <thead>
            <tr>
              <th>Strike</th>
              <th>Put Sentiment</th>
              <th>Call Sentiment</th>
              <th>Skew</th>
            </tr>
          </thead>
          <tbody>
            {data.map((item, i) => {
              // Calculate skew and IV classes
              const skew = formatValue(item.ivSkew);
              const skewNum = parseFloat(skew);
              const skewClass = !isNaN(skewNum) 
                ? (skewNum > 0 ? "bullish" : skewNum < 0 ? "bearish" : "neutral")
                : "";
                
              const ivStrengthClass = getIvStrengthClass(item.ceIv, item.peIv);
              const ivStrengthLabel = getIvStrengthLabel(item.ceIv, item.peIv);

              return (
                <tr 
                  key={i} 
                  className={item.isAtm ? "atm-row" : ""}
                  style={{ height: rowHeight }}
                >
                  <td 
                    className="strike-cell"
                    style={{ padding: `${padding}px` }}
                  >
                    {item.strike}
                    {item.isAtm && (
                      <span 
                        className="atm-badge" 
                        style={{
                          fontSize: `${badgeFontSize}px`,
                          padding: `${Math.max(2, badgeFontSize * 0.25)}px ${Math.max(4, badgeFontSize * 0.5)}px`
                        }}
                      >
                        ATM
                      </span>
                    )}
                  </td>
                  <td style={{ padding: `${padding}px` }}>
                    <span 
                      className={`sentiment-label ${item.putSentiment.includes("Bullish") ? "bullish" : "bearish"}`}
                      style={{ padding: `${Math.max(2, padding * 0.5)}px ${Math.max(4, padding)}px` }}
                    >
                      {item.putSentiment}
                    </span>
                  </td>
                  <td style={{ padding: `${padding}px` }}>
                    <span 
                      className={`sentiment-label ${item.callSentiment.includes("Bullish") ? "bullish" : "bearish"}`}
                      style={{ padding: `${Math.max(2, padding * 0.5)}px ${Math.max(4, padding)}px` }}
                    >
                      {item.callSentiment}
                    </span>
                  </td>
                  <td 
                    className={`skew-cell ${skewClass}`}
                    style={{ padding: `${padding}px` }}
                  >
                    {skew}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend moved below the table */}
      <div className="sentiment-legend-below">
        <div className="legend-grid">
          <div><span className="legend-box bullish"></span> Bullish Sentiment</div>
          <div><span className="legend-box bearish"></span> Bearish Sentiment</div>
          <div><span className="legend-box" style={{ background: "#4CAF50" }}></span> LTP Increased</div>
          <div><span className="legend-box" style={{ background: "#F44336" }}></span> LTP Decreased</div>
          <div><span className="legend-box bullish"></span> Bullish Skew (CE IV &gt; PE IV)</div>
          <div><span className="legend-box bearish"></span> Bearish Skew (PE IV &gt; CE IV)</div>
        </div>
      </div>
    </div>
    </div>
  );
}

export default SentimentTable;