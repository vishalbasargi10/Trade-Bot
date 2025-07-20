import React, { useEffect, useState, useRef, useCallback } from "react";
import axios from "axios";
import OIChart from "./components/OIChart/OIChart";
import SentimentTable from "./components/SentimentTable/SentimentTable";
import MetricsBiasComponent from "./components/MetricsBiasComponent/MetricsBiasComponent";
import "./App.css";

function App() {
  const [rawData, setRawData] = useState(null);
  const [atmStrike, setAtmStrike] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [activeTab, setActiveTab] = useState("combined");
  const [llmData, setLlmData] = useState(null);
  const [llmLastUpdated, setLlmLastUpdated] = useState(null);
  const [rowHeight, setRowHeight] = useState(40);
  const isMountedRef = useRef(true);

  // Create refs for intervals
  const optionIntervalRef = useRef(null);
  const llmIntervalRef = useRef(null);

  const fetchOptionData = useCallback(async () => {
    try {
      const res = await axios.get("http://127.0.0.1:8000/option-chain");
      if (!isMountedRef.current) return;

      setRawData(res.data.option_chain);
      setAtmStrike(parseFloat(res.data.atm_strike));
      setLastUpdated(new Date());
      setError(null);
      setLoading(false);
    } catch (err) {
      if (isMountedRef.current) {
        setError("⚠️ Failed to fetch option data. Showing cached data.");
        setLoading(false);
      }
      console.error("Option data fetch failed:", err);
    }
  }, []);

  const fetchLLMData = useCallback(async () => {
    try {
      const llmRes = await axios.get("http://127.0.0.1:8000/analyze");
      if (isMountedRef.current) {
        // Only update if we actually get new data
        setLlmData(llmRes.data.llm_analysis);
        setLlmLastUpdated(new Date());
      }
      console.log("LLM analysis updated at", new Date());
    } catch (err) {
      console.error("LLM analysis fetch failed:", err);
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;

    // Fetch initial data
    fetchOptionData();
    fetchLLMData();

    // Set up intervals
    optionIntervalRef.current = setInterval(fetchOptionData, 15000);
    llmIntervalRef.current = setInterval(fetchLLMData, 15 * 60 * 1000);

    return () => {
      isMountedRef.current = false;
      clearInterval(optionIntervalRef.current);
      clearInterval(llmIntervalRef.current);
    };
  }, [fetchOptionData, fetchLLMData]);

  return (
    <div className="app-container">
      <div className="header-container">
        <div className="navbar">
          <button
            className={`nav-btn ${activeTab === "combined" ? "active" : ""}`}
            onClick={() => setActiveTab("combined")}
          >
            Visualization - Updates Every 15 seconds
          </button>
          <button
            className={`nav-btn ${activeTab === "llm" ? "active" : ""}`}
            onClick={() => setActiveTab("llm")}
          >
            Metrics Bias
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {rawData && atmStrike ? (
        <div
          className="content-container"
          style={{ opacity: loading ? 0.4 : 1, transition: "opacity 0.5s ease" }}
        >
          {activeTab === "combined" && (
            <div className="combined-view">
              <div className="chart-section">
                <OIChart
                  rawData={rawData}
                  atm={atmStrike}
                  lastUpdated={lastUpdated}
                  rowHeight={rowHeight}
                />
              </div>
              <div className="table-section">
                <SentimentTable
                  rawData={rawData}
                  atm={atmStrike}
                  lastUpdated={lastUpdated}
                  rowHeight={rowHeight}
                />
              </div>
            </div>
          )}

          {activeTab === "llm" && (
            <MetricsBiasComponent
              key={llmLastUpdated?.getTime()} // Reset on new LLM data
              data={llmData}
              lastUpdated={llmLastUpdated}
              loading={!llmData} // Show loading state
            />
          )}
        </div>
      ) : (
        <div className="loading">Loading initial data...</div>
      )}
    </div>
  );
}

export default App;