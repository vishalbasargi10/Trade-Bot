import React from 'react';
import './MetricsBiasComponent.css';

const MetricsBiasComponent = ({ data }) => {
  if (!data) return <div className="loading">Loading LLM analysis...</div>;

  const { metrics, tactical_idea, bias_analysis } = data;

  // Sentiment color mapping
  const sentimentColors = {
    1: '#66BB6A',      // Vibrant Green - Bullish
    2: '#43A047',      // Medium Green - Highly Bullish
    3: '#9E9E9E',      // Grey - Neutral
    4: '#EF5350',      // Coral Red - Bearish
    5: '#E53935'       // Vibrant Red - Highly Bearish
  };

  const sentimentLightColors = {
    1: 'rgba(102, 187, 106, 0.18)',
    2: 'rgba(67, 160, 71, 0.18)',
    3: 'rgba(120, 120, 120, 0.18)',
    4: 'rgba(239, 83, 80, 0.18)',
    5: 'rgba(211, 47, 47, 0.18)'
  };

  const getTextColor = (sentiment) => {
    return sentiment === 3 ? '#212121' : 'white';
  };

  const renderMetricValue = (metric, value) => {
    if (typeof value === 'number') {
      return value.toLocaleString(undefined, {
        maximumFractionDigits: 4
      });
    }

    if (Array.isArray(value)) {
      return (
        <ul className="nested-list">
          {value.map((item, idx) => (
            <li key={idx}>
              {Object.entries(item).map(([k, v]) => (
                <div key={k} className="key-value">
                  <span className="key">{k}:</span>
                  <span className="value">{v}</span>
                </div>
              ))}
            </li>
          ))}
        </ul>
      );
    }

    if (typeof value === 'object' && value !== null) {
      return (
        <div className="nested-object">
          {Object.entries(value).map(([k, v]) => (
            <div key={k} className="key-value">
              <span className="key">{k}:</span>
              <span className="value">{renderMetricValue(metric, v)}</span>
            </div>
          ))}
        </div>
      );
    }

    return value;
  };

  return (
    <div className="dashboard">

      <div className="dashboard-columns">
        {/* Left Column - 65% for Metrics */}
        <div className="metrics-column">
          {/* Key Metrics Section */}
          <section className="key-metrics">
            <h2>Core Market Indicators</h2>
            <div className="metrics-grid">
              {metrics.slice(0, 5).map(metric => (
                <div
                  key={metric.metric}
                  className="metric-card"
                  style={{
                    backgroundColor: sentimentLightColors[metric.output_format.sentiment_score],
                    borderLeft: `4px solid ${sentimentColors[metric.output_format.sentiment_score]}`
                  }}
                >
                  <div className="metric-header">
                    <h3>{metric.metric}</h3>
                    <div className="metric-meta">
                      <div className="sentiment-badge" style={{
                        backgroundColor: sentimentColors[metric.output_format.sentiment_score],
                        color: getTextColor(metric.output_format.sentiment_score)
                      }}>
                        Sentiment: {metric.output_format.sentiment_score}
                      </div>
                      <div className="importance-badge">
                        Importance: {metric.importance}/10
                      </div>
                      <div className="ease-badge">
                        Ease: {metric.ease}/5
                      </div>
                    </div>
                  </div>

                  <p className="purpose">{metric.purpose}</p>

                  {metric.interpretation && (
                    <div className="interpretation">
                      <h4>Interpretation:</h4>
                      <div className="interpretation-grid">
                        {Object.entries(metric.interpretation).map(([key, val]) => (
                          <React.Fragment key={key}>
                            <div className="interpretation-key">{key}:</div>
                            <div className="interpretation-value">{val}</div>
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="output-data">
                    <h4>Analysis:</h4>
                    <div className="data-grid">
                      {Object.entries(metric.output_format).map(([key, value]) => (
                        key !== 'sentiment_score' && (
                          <React.Fragment key={key}>
                            <div className="data-label">{key}:</div>
                            <div className="data-value">
                              {renderMetricValue(metric, value)}
                            </div>
                          </React.Fragment>
                        )
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Additional Metrics */}
          <section className="additional-metrics">
            <h2>Advanced Metrics</h2>
            <div className="metrics-grid">
              {metrics.slice(5).map(metric => (
                <div
                  key={metric.metric}
                  className="metric-card"
                  style={{
                    backgroundColor: sentimentLightColors[metric.output_format.sentiment_score],
                    borderLeft: `4px solid ${sentimentColors[metric.output_format.sentiment_score]}`
                  }}
                >
                  <div className="metric-header">
                    <h3>{metric.metric}</h3>
                    <div className="metric-meta">
                      <div className="sentiment-badge" style={{
                        backgroundColor: sentimentColors[metric.output_format.sentiment_score],
                        color: getTextColor(metric.output_format.sentiment_score)
                      }}>
                        Sentiment: {metric.output_format.sentiment_score}
                      </div>
                      <div className="importance-badge">
                        Importance: {metric.importance}/10
                      </div>
                      <div className="ease-badge">
                        Ease: {metric.ease}/5
                      </div>
                    </div>
                  </div>

                  <p className="purpose">{metric.purpose}</p>

                  <div className="output-data">
                    <div className="data-grid">
                      {Object.entries(metric.output_format).map(([key, value]) => (
                        key !== 'sentiment_score' && (
                          <React.Fragment key={key}>
                            <div className="data-label">{key}:</div>
                            <div className="data-value">
                              {renderMetricValue(metric, value)}
                            </div>
                          </React.Fragment>
                        )
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Right Column - 35% for Bias & Tactical - Enhanced Design */}
        <div className="bias-tactical-column">
          {/* Market Sentiment Section */}
          {/* Market Sentiment Section */}
          <section className="sentiment-section">
            <div className="section-header">
              <h2>Market Sentiment</h2>
              <div className="confidence-indicator">
                Confidence: <span className="confidence-value">{bias_analysis.confidence_score}/10</span>
              </div>
            </div>

            <div
              className="sentiment-card"
              style={{
                backgroundColor: sentimentColors[bias_analysis.sentiment_score],
                color: getTextColor(bias_analysis.sentiment_score)
              }}
            >
              <div className="sentiment-label">OVERALL BIAS</div>
              <div className="sentiment-value">{bias_analysis.bias_label}</div>
            </div>
          </section>

          {/* Bias Analysis Details */}
          <section className="bias-analysis">
            <h2>Bias Analysis Details</h2>
            <div className="bias-details">
              <div className="bias-card">
                <h3><i className="icon-chart"></i> Supporting Metrics</h3>
                <ul className="metric-list">
                  {bias_analysis.supporting_metrics.map((metric, idx) => (
                    <li key={idx} className="metric-item">
                      <span className="metric-bullet"></span>
                      <span className="metric-text">{metric}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="bias-card">
                <h3><i className="icon-reasoning"></i> Reasoning</h3>
                <p className="reasoning-text">{bias_analysis.reasoning}</p>
              </div>

              <div className="bias-card">
                <h3><i className="icon-prediction"></i> LLM Prediction</h3>
                <p className="prediction-text">{bias_analysis.llm_gut_call}</p>
              </div>
            </div>
          </section>

          {/* Suggested Strategies */}
          <section className="strategies-section">
            <h2>Suggested Strategies</h2>
            <div className="strategies-grid">
              {bias_analysis.suggested_strategies.map((strategy, idx) => (
                <div key={idx} className="strategy-card">
                  <div className="strategy-header">
                    <h3>{strategy.name}</h3>
                    <div className="strategy-tag">Strategy {idx + 1}</div>
                  </div>

                  <div className="strategy-details">
                    <div className="strategy-row">
                      <span className="label">Legs:</span>
                      <span className="value">{strategy.legs.join(' + ')}</span>
                    </div>
                    <div className="strategy-row">
                      <span className="label">Risk Profile:</span>
                      <span className="value">{strategy.risk_profile || 'Moderate'}</span>
                    </div>
                    <div className="strategy-row">
                      <span className="label">Theta:</span>
                      <span className="value">{strategy.theta || 'Positive'}</span>
                    </div>
                  </div>

                  <div className="strategy-reason">
                    <span className="label">Reason:</span>
                    <p>{strategy.reason}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Tactical Idea */}
          <section className="tactical-idea">
            <h2>Tactical Trading Idea</h2>
            <div className="tactical-card">
              <div className="tactical-header">
                <h3>{tactical_idea.structure}</h3>
                <div className="timeframe-tag">{tactical_idea.timeframe || 'Short-term'}</div>
              </div>

              <div className="tactical-details">
                <div className="tactical-row">
                  <i className="icon-idea"></i>
                  <div>
                    <div className="label">Idea Rationale</div>
                    <p>{tactical_idea.reason}</p>
                  </div>
                </div>

                <div className="tactical-row">
                  <i className="icon-execute"></i>
                  <div>
                    <div className="label">Execution Plan</div>
                    <p>{tactical_idea.execution}</p>
                  </div>
                </div>

                <div className="tactical-row">
                  <i className="icon-theta"></i>
                  <div>
                    <div className="label">Theta Profile</div>
                    <p>{tactical_idea.theta_profile}</p>
                  </div>
                </div>

                <div className="tactical-row">
                  <i className="icon-profit"></i>
                  <div>
                    <div className="label">Profit Target</div>
                    <p>{tactical_idea.profit_target || '15-20%'}</p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default MetricsBiasComponent;