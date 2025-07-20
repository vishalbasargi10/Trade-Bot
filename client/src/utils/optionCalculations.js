export const processStrikeData = (strikeStr, values, atm) => {
  const strike = parseFloat(strikeStr);
  const ce = values.ce || {};
  const pe = values.pe || {};

  // Extract values with defaults
  const callOi = ce.oi || 0;
  const callPrevOi = ce.previous_oi || 0;
  const callLtp = ce.last_price || 0;
  const callPrevLtp = ce.previous_close_price || 0;
  const ceIv = ce.implied_volatility || 0;
  
  const putOi = pe.oi || 0;
  const putPrevOi = pe.previous_oi || 0;
  const putLtp = pe.last_price || 0;
  const putPrevLtp = pe.previous_close_price || 0;
  const peIv = pe.implied_volatility || 0;

  // Calculate percentage changes
  const callLtpChange = callPrevLtp 
    ? ((callLtp - callPrevLtp) / callPrevLtp) * 100 
    : 0;
  
  const putLtpChange = putPrevLtp 
    ? ((putLtp - putPrevLtp) / putPrevLtp) * 100 
    : 0;

  // Determine sentiment
  const callSentiment = callOi > callPrevOi
    ? callLtpChange > 0 ? "Bullish (OI↑ + LTP↑)" : "Bearish (OI↑ + LTP↓)"
    : callLtpChange > 0 ? "Bullish (OI↓ + LTP↑)" : "Bearish (OI↓ + LTP↓)";

  const putSentiment = putOi > putPrevOi
    ? putLtpChange > 0 ? "Bullish (OI↑ + LTP↑)" : "Bearish (OI↑ + LTP↓)"
    : putLtpChange > 0 ? "Bearish (OI↓ + LTP↑)" : "Bullish (OI↓ + LTP↓)";

  return {
    strike: strike.toString(),
    put_base: Math.min(putOi, putPrevOi),
    put_diff: Math.abs(putOi - putPrevOi),
    put_increase: putOi >= putPrevOi,
    call_base: Math.min(callOi, callPrevOi),
    call_diff: Math.abs(callOi - callPrevOi),
    call_increase: callOi >= callPrevOi,
    putLtpChange: putLtpChange.toFixed(2),
    callLtpChange: callLtpChange.toFixed(2),
    callSentiment,
    putSentiment,
    ceIv: ceIv.toFixed(2),
    peIv: peIv.toFixed(2),
    ivSkew: (ceIv - peIv).toFixed(2),
    isAtm: Math.abs(strike - atm) < 0.01
  };
};

export const filterAtmStrikes = (rawData, atm) => {
  if (!rawData) return [];
  
  const processed = Object.entries(rawData).map(([strike, values]) => 
    processStrikeData(strike, values, atm)
  );

  const sorted = [...processed].sort((a, b) => 
    parseFloat(a.strike) - parseFloat(b.strike)
  );
  
  const atmIndex = sorted.findIndex(d => d.isAtm);
  
  if (atmIndex === -1) return sorted.slice(0, 15);
  
  return sorted
    .slice(Math.max(0, atmIndex - 7), Math.min(sorted.length, atmIndex + 8))
    .sort((a, b) => parseFloat(b.strike) - parseFloat(a.strike));
};