import json
import time
import threading
import math
from datetime import datetime
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dhanhq import dhanhq
from openai import OpenAI
import os
import pandas as pd

app = FastAPI()
# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Dhan API
dhan = dhanhq(
    "1101685567",
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU0OTE1NzU0LCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwMTY4NTU2NyJ9.4HYRy2XOmkDRtvVgI_G9DWuD4cIEPI7kVlehGbDjowOCWZaLLxzCh_ZdLf4gpQ9ge2FsPS1bGWqas5GE-h8Qrw"
)

# ====================== Shared Option Chain Cache ======================
# Option chain cache
last_called_time = 0
last_valid_response = None
previous_chain = None  # For tracking historical values
option_chain_lock = threading.Lock()

# LLM analysis cache
llm_analysis_cache = None
llm_analysis_time = 0
llm_cache_lock = threading.Lock()

# API key rotation
API_KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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"
]
USED_KEY_INDEX = -1
key_lock = threading.Lock()
def update_llm_analysis():
    """Fetch new data and update LLM analysis cache"""
    global llm_analysis_cache, llm_analysis_time
    
    try:
        option_data = get_cached_option_chain()
        precomputed_metrics = compute_metrics(
            option_data["option_chain"],
            option_data["spot_price"],
            option_data["expiry"]
        )
        #print(precomputed_metrics)
        llm_output = call_llm(option_data, precomputed_metrics,first_expiry)
        if llm_output:
            with llm_cache_lock:
                llm_analysis_cache = llm_output
                llm_analysis_time = time.time()
    except Exception as e:
        print(f"⚠️ LLM update failed: {str(e)}")

def scheduled_llm_updater():
    """Background task that updates LLM analysis every 15 minutes"""
    while True:
        try:
            update_llm_analysis()
            print(f"✅ LLM analysis updated at {datetime.now()}")
        except Exception as e:
            print(f"❌ Scheduled LLM update failed: {str(e)}")
        
        # Wait 15 minutes (900 seconds)
        time.sleep(900)

# ====================== Startup Event Update ======================
@app.on_event("startup")
def startup_event():
    # Step 1: Pre-fetch option chain
    try:
        print("⏳ Pre-fetching option chain...")
        get_cached_option_chain()  # Populate initial cache
        print("✅ Option chain pre-fetched")
    except Exception as e:
        print(f"❌ Option chain pre-fetch failed: {e}")

    # Step 2: Pre-cache security list
    def pre_cache_security():
        try:
            # Create empty CSV if it doesn't exist
            if not os.path.exists("security_list.csv"):
                pd.DataFrame(columns=['SEM_CUSTOM_SYMBOL', 'SEM_SMST_SECURITY_ID']).to_csv("security_list.csv", index=False)
                    
            get_security_map()
            print("✅ Security list pre-cached")
        except Exception as e:
            print(f"❌ Security list pre-cache failed: {e}")
    
    # Run in background thread
    threading.Thread(target=pre_cache_security, daemon=True).start()

    # Step 3: Start background tasks
    def background_init():
        # --- LLM Analysis Init ---
        try:
            print("⏳ Starting initial LLM update...")
            update_llm_analysis()
            print("✅ Initial LLM update completed")
        except Exception as e:
            print(f"❌ Initial LLM update failed: {e}")

        # Start periodic LLM updates
        scheduler_thread = threading.Thread(target=scheduled_llm_updater, daemon=True)
        scheduler_thread.start()
        print("🚀 LLM scheduler started")

        # --- Trade Execution Init ---
        # Start trade scheduler after 1 minute
        time.sleep(60)
        trade_thread = threading.Thread(target=trade_execution_scheduler, daemon=True)
        trade_thread.start()
        print("🚀 Trade execution scheduler started")

    # Start everything in background
    init_thread = threading.Thread(target=background_init, daemon=True)
    init_thread.start()

# ====================== Option Chain Processing ======================
first_expiry=''
def get_cached_option_chain():
    global last_called_time, last_valid_response, previous_chain
    
    with option_chain_lock:
        current_time = time.time()
        # Return cached response if within 5-second window
        if current_time - last_called_time < 5 and last_valid_response:
            return last_valid_response

        try:
            expiry_list = dhan.expiry_list(under_security_id=13, under_exchange_segment="IDX_I")
            first_expiry = expiry_list['data']['data'][0]
            print(first_expiry)

            option_chain_data = dhan.option_chain(
                under_security_id=13,
                under_exchange_segment="IDX_I",
                expiry=first_expiry
            )

            # Validate and process option chain
            oc_data = option_chain_data["data"]["data"]
            if "oc" not in oc_data or not isinstance(oc_data["oc"], dict):
                raise ValueError("Invalid Option Chain Data")

            spot_price = oc_data.get("last_price", 0)
            atm_strike = round(spot_price / 50) * 50
            all_strikes = sorted([float(k) for k in oc_data["oc"].keys()])
            atm_index = all_strikes.index(min(all_strikes, key=lambda x: abs(x - atm_strike)))
            selected_strikes = all_strikes[max(0, atm_index - 10): atm_index + 11]

            # Prepare new option chain with historical data
            filtered_oc = {}
            for strike in selected_strikes:
                strike_key = f"{strike:.6f}"
                strike_data = oc_data["oc"][strike_key]
                
                # Add historical data if available
                if last_valid_response and strike_key in last_valid_response["option_chain"]:
                    prev_data = last_valid_response["option_chain"][strike_key]
                    for opt_type in ['ce', 'pe']:
                        if opt_type in strike_data and opt_type in prev_data:
                            strike_data[opt_type]['previous_oi'] = prev_data[opt_type].get('oi', 0)
                            strike_data[opt_type]['previous_close_price'] = prev_data[opt_type].get('last_price', 0)
                
                filtered_oc[strike_key] = strike_data

            result = {
                "spot_price": spot_price,
                "atm_strike": atm_strike,
                "option_chain": filtered_oc,
                "expiry": first_expiry
            }

            # Update cache
            previous_chain = last_valid_response  # Save for next comparison
            last_valid_response = result
            last_called_time = current_time
            return result

        except Exception as e:
            print(f"Error fetching option chain: {e}")
            if last_valid_response:
                return last_valid_response
            raise

# ====================== Option Chain Endpoint ======================
@app.get("/option-chain")
async def get_option_chain(request: Request):
    # Return immediately if we have cached data
    with option_chain_lock:
        if last_valid_response:
            return last_valid_response
    
    try:
        data = get_cached_option_chain()
        return data
    except Exception as e:
        return {"error": str(e)}

METRIC_TEMPLATE = {
  "metrics": [
    {
      "metric": "Put/Call Volume Ratio",
      "importance": 9,
      "ease": 5,
      "purpose": "Short-term sentiment gauge",
      "interpretation": {
        "high_ratio": "Panic-driven downside hedging",
        "low_ratio": "Bullish speculation"
      },
      "output_format": {
        "total_put_volume": "int",
        "total_call_volume": "int",
        "put_call_volume_ratio": "float",
        "intraday_bias": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Open Interest Concentration",
      "importance": 9,
      "ease": 4,
      "purpose": "Identifies dominant strikes and support/resistance walls",
      "interpretation": {
        "high_call_oi": "Resistance zone",
        "high_put_oi": "Support zone",
        "breach_risk": "Gamma-driven selloff if support broken"
      },
      "output_format": {
        "top_call_oi_strikes": {"strike1": "int", "strike2": "int", "strike3": "int"},
        "top_put_oi_strikes": {"strike1": "int", "strike2": "int", "strike3": "int"},
        "cumulative_put_oi_pct": "float",
        "key_support_zone": "string",
        "key_resistance_zone": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Gamma Exposure (GEX)",
      "importance": 8,
      "ease": 3,
      "purpose": "Measures sensitivity of dealer hedging to market moves",
      "interpretation": {
        "negative": "Dealers short gamma → Hedging amplifies volatility",
        "positive": "Dealers long gamma → Suppresses volatility"
      },
      "output_format": {
        "total_call_gex": "float",
        "total_put_gex": "float",
        "net_gex": "float",
        "volatility_impact": "string",
        "amplification_zone": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Volume/OI Ratio",
      "importance": 8,
      "ease": 5,
      "purpose": "Distinguishes new vs. closing positions",
      "interpretation": {
        "ratio >1": "New positions opening",
        "ratio <1": "Existing positions closing"
      },
      "output_format": {
        "call_volume": "int",
        "call_oi": "int",
        "call_ratio": "float",
        "put_volume": "int",
        "put_oi": "int",
        "put_ratio": "float",
        "call_activity": "string",
        "put_activity": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Risk Reversal",
      "importance": 7,
      "ease": 4,
      "purpose": "Measures directional sentiment bias",
      "interpretation": {
        "positive": "Bearish bias (downside fear)",
        "negative": "Bullish bias (upside optimism)"
      },
      "output_format": {
        "otm_put_iv": "float",
        "otm_call_iv": "float",
        "risk_reversal_skew": "float",
        "sentiment_bias": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Price Expectations - Expected Move",
      "importance": 7,
      "ease": 4,
      "purpose": "Market's implied price range",
      "output_format": {
        "spot_price": "float",
        "atm_iv": "float",
        "days_to_expiry": "int",
        "expected_move": "float",
        "price_range_low": "float",
        "price_range_high": "float",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "IV Percentile/Rank",
      "importance": 7,
      "ease": 4,
      "purpose": "Gauges relative volatility",
      "interpretation": {
        ">70%": "High relative volatility",
        "<30%": "Low relative volatility"
      },
      "output_format": {
        "atm_iv": "float",
        "min_chain_iv": "float",
        "max_chain_iv": "float",
        "iv_percentile": "float",
        "volatility_context": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Delta Weighted OI",
      "importance": 6,
      "ease": 3,
      "purpose": "Measures effective directional exposure",
      "interpretation": {
        "positive": "Bullish directional exposure",
        "negative": "Bearish directional exposure"
      },
      "output_format": {
        "total_call_effective_oi": "float",
        "total_put_effective_oi": "float",
        "net_effective_oi": "float",
        "directional_bias": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Max Pain Calculation",
      "importance": 6,
      "ease": 2,
      "purpose": "Strike where option sellers maximize profits",
      "output_format": {
        "max_pain_strike": "float",
        "pain_value": "float",
        "interpretation": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Bid-Ask Spread % (Critical Strikes)",
      "importance": 5,
      "ease": 5,
      "purpose": "Liquidity quality at key OI strikes",
      "interpretation": {
        "<1%": "Excellent liquidity",
        "1-5%": "Moderate liquidity",
        ">5%": "Poor liquidity/dealer reluctance"
      },
      "output_format": {
        "critical_strikes": [
          {
            "strike": "float",
            "spread_pct": "float",
            "liquidity_quality": "string"
          }
        ],
        "avg_spread_top_oi": "float",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Volatility Smile/Smirk",
      "importance": 5,
      "ease": 3,
      "purpose": "Identifies crash risk or normal conditions",
      "pattern_detection": [
        "Smirk: Put_IV > ATM_IV > Call_IV → Crash fear",
        "Smile: Put_IV ≈ Call_IV > ATM_IV → Normal",
        "Reverse: Call_IV > ATM_IV > Put_IV → Bullish"
      ],
      "output_format": {
        "low_put_iv": "float",
        "atm_iv": "float",
        "high_call_iv": "float",
        "pattern": "string",
        "sentiment_implication": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Sentiment Synthesis Framework",
      "importance": 5,
      "ease": 4,
      "purpose": "Cross-verify metrics through 3-lens approach",
      "framework": [
        "Fear Gauge: IV skew + Put/Call ratios",
        "Flow Truth: Volume/OI changes + block trades",
        "Dealer Impact: GEX + Max Pain"
      ],
      "output_format": {
        "fear_gauge": "string",
        "flow_truth": "string",
        "dealer_impact": "string",
        "composite_sentiment": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Theta Decay Burden (Enhanced)",
      "importance": 4,
      "ease": 3,
      "purpose": "Daily cost to hold positions",
      "enhanced_features": [
        "Put/Call theta ratio",
        "Daily cost in millions"
      ],
      "interpretation": {
        "high_put_ratio": "Bearish positions expensive → Unwind risk"
      },
      "output_format": {
        "total_call_theta": "float",
        "total_put_theta": "float",
        "total_theta_burden": "float",
        "put_call_theta_ratio": "float",
        "daily_cost_millions": "float",
        "decay_pressure": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Implied Volatility (IV) Slope",
      "importance": 4,
      "ease": 2,
      "purpose": "Measures steepness of volatility skew",
      "interpretation": {
        "negative_slope": "Steeper put IV slope → Crash fear"
      },
      "output_format": {
        "low_strike_iv": "float",
        "high_strike_iv": "float",
        "iv_slope_per_100pts": "float",
        "slope_direction": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Block Trade Detection",
      "importance": 3,
      "ease": 2,
      "purpose": "Identifies institutional activity",
      "triggers": [
        "Volume > 5x strike's average volume",
        "|Last - Mark| > 10% of Mark"
      ],
      "output_format": {
        "block_trades": [
          {
            "strike": "float",
            "option_type": "string",
            "volume": "int",
            "avg_volume": "float",
            "premium_deviation_pct": "float"
          }
        ],
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Gamma-Vega Ratio",
      "importance": 3,
      "ease": 1,
      "purpose": "Spot vs. vol move sensitivity",
      "interpretation": {
        "high_ratio": "More sensitive to spot moves",
        "low_ratio": "More sensitive to vol moves"
      },
      "output_format": {
        "atm_strike": "float",
        "call_gamma_vega_ratio": "float",
        "put_gamma_vega_ratio": "float",
        "sensitivity_profile": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Gamma Neutral Zone",
      "importance": 2,
      "ease": 1,
      "purpose": "Price with minimal gamma exposure impact",
      "output_format": {
        "gamma_neutral_strike": "float",
        "net_gamma_at_strike": "float",
        "distance_from_spot": "float",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Call-Put Skew Deviation",
      "importance": 2,
      "ease": 1,
      "purpose": "Quantifies IV disparity between equidistant OTM strikes",
      "interpretation": {
        "positive_deviation": "Fat tail risk pricing"
      },
      "output_format": {
        "call_skew_component": "float",
        "put_skew_component": "float",
        "skew_deviation": "float",
        "risk_implication": "string",
        "sentiment_score": "int"
      }
    },
    {
      "metric": "VWAP Strike Levels",
      "importance": 2,
      "ease": 3,
      "purpose": "Volume-weighted premium at key strikes",
      "output_format": {
        "key_strikes": [
          {
            "strike": "float",
            "vwap_premium": "float"
          }
        ],
        "sentiment_score": "int"
      }
    },
    {
      "metric": "Call-Put Parity Arbitrage",
      "importance": 1,
      "ease": 1,
      "purpose": "Identify mispricing opportunities",
      "output_format": {
        "arbitrage_opportunities": [
          {
            "strike": "float",
            "call_put_diff": "float",
            "spot_strike_diff": "float",
            "deviation_pct": "float"
          }
        ],
        "sentiment_score": "int"
      }
    },
  ],
  "tactical_idea": {
    "structure": "Put Ratio Spread",
    "reason": "Smart money accumulating 25000 puts with low IV",
    "execution": "Buy 1x 25000P, Sell 2x 24800P",
    "theta_profile": "Positive decay in range"
  },
  "bias_analysis": {
    "sentiment_score": 4,
    "bias_label": "Moderately Bearish",
    "supporting_metrics": ["Put/Call Volume Ratio", "Gamma Exposure", "Open Interest Concentration"],
    "reasoning": "Increasing put volume and negative GEX indicate growing bearish sentiment. OI concentration shows strong resistance at 25,000 level.",
    "llm_gut_call": "Market likely to test support at 24,500 before any rebound. Downside volatility risk remains elevated.",
    "confidence_score": 7.5,
    "suggested_strategies": [
        {
            "name": "Protective Put",
            "legs": ["Buy 1x 24500P"],
            "reason": "Direct hedge against downside risk with defined risk",
            "strike":"int",
            "strike_type":"PUT or CALL"
        },
        {
            "name": "Bear Put Spread",
            "legs": ["Buy 1x 24500P", "Sell 1x 24300P"],
            "reason": "Cost-efficient bearish play with limited risk"
        },
        {
            "name": "Short Call",
            "legs": ["Sell 1x 24800C"],
            "reason": "Capitalize on resistance with positive theta"
        },
        {
            "name": "Put Ratio Spread",
            "legs": ["Buy 1x 24500P", "Sell 2x 24300P"],
            "reason": "High-probability play for range-bound downside"
        }
    ]
}
}



def compute_metrics(option_chain, spot_price, expiry_date):
    # Calculate days to expiry
    expiry_dt = datetime.strptime(expiry_date, "%Y-%m-%d")
    days_to_expiry = (expiry_dt - datetime.now()).days
    
    metrics = {}
    oi_dict = defaultdict(lambda: {'ce': 0, 'pe': 0})
    all_iv = []
    strikes = sorted(map(float, option_chain.keys()))
    
    # Initialize totals
    total_put_volume = total_call_volume = 0
    total_put_oi = total_call_oi = 0
    call_gex = put_gex = 0
    call_effective = put_effective = 0
    call_theta = put_theta = 0
    
    # First pass: collect totals and OI information
    for strike, data in option_chain.items():
        strike_val = float(strike)
        
        if 'ce' in data:
            ce = data['ce']
            total_call_volume += ce['volume']
            total_call_oi += ce['oi']
            oi_dict[strike_val]['ce'] = ce['oi']
            
            # Greeks calculations
            if 'greeks' in ce:
                greeks = ce['greeks']
                gamma = greeks.get('gamma', 0)
                delta = greeks.get('delta', 0)
                theta_val = greeks.get('theta', 0)
                
                call_gex += gamma * ce['oi'] * 100
                call_effective += ce['oi'] * abs(delta)
                call_theta += ce['oi'] * abs(theta_val) * 100
            
            all_iv.append(ce['implied_volatility'])
        
        if 'pe' in data:
            pe = data['pe']
            total_put_volume += pe['volume']
            total_put_oi += pe['oi']
            oi_dict[strike_val]['pe'] = pe['oi']
            
            if 'greeks' in pe:
                greeks = pe['greeks']
                gamma = greeks.get('gamma', 0)
                delta = greeks.get('delta', 0)
                theta_val = greeks.get('theta', 0)
                
                put_gex += gamma * pe['oi'] * 100
                put_effective += pe['oi'] * abs(delta)
                put_theta += pe['oi'] * abs(theta_val) * 100
            
            all_iv.append(pe['implied_volatility'])
    
    # 1. Put/Call Volume Ratio
    metrics['Put/Call Volume Ratio'] = {
        'total_put_volume': total_put_volume,
        'total_call_volume': total_call_volume,
        'put_call_volume_ratio': total_put_volume / total_call_volume if total_call_volume else 0
    }
    
    # 2. Open Interest Concentration
    sorted_call_oi = sorted(oi_dict.items(), key=lambda x: x[1]['ce'], reverse=True)
    sorted_put_oi = sorted(oi_dict.items(), key=lambda x: x[1]['pe'], reverse=True)
    
    metrics['Open Interest Concentration'] = {
        'top_call_oi_strikes': [k for k, v in sorted_call_oi[:3]],
        'top_put_oi_strikes': [k for k, v in sorted_put_oi[:3]],
        'cumulative_put_oi_pct': sum(v['pe'] for k, v in sorted_put_oi[:3]) / total_put_oi * 100 if total_put_oi else 0
    }
    
    # 3. Gamma Exposure (GEX)
    metrics['Gamma Exposure (GEX)'] = {
        'total_call_gex': call_gex,
        'total_put_gex': put_gex,
        'net_gex': -1 * (call_gex + put_gex)
    }
    
    # 4. Volume/OI Ratio
    metrics['Volume/OI Ratio'] = {
        'call_ratio': total_call_volume / total_call_oi if total_call_oi else 0,
        'put_ratio': total_put_volume / total_put_oi if total_put_oi else 0
    }
    
    # 5. Risk Reversal
    otm_put_iv = option_chain[f"{min(strikes):.6f}"]['pe']['implied_volatility']
    otm_call_iv = option_chain[f"{max(strikes):.6f}"]['ce']['implied_volatility']
    
    metrics['Risk Reversal'] = {
        'otm_put_iv': otm_put_iv,
        'otm_call_iv': otm_call_iv,
        'risk_reversal_skew': otm_put_iv - otm_call_iv
    }
    
    # 6. Expected Move
    atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
    atm_data = option_chain[f"{atm_strike:.6f}"]
    atm_iv = atm_data['ce']['implied_volatility']
    expected_move = spot_price * (atm_iv/100) * math.sqrt(days_to_expiry/365)
    
    metrics['Price Expectations - Expected Move'] = {
        'spot_price': spot_price,
        'atm_iv': atm_iv,
        'days_to_expiry': days_to_expiry,
        'expected_move': expected_move,
        'price_range_low': spot_price - expected_move,
        'price_range_high': spot_price + expected_move
    }
    
    # 7. IV Percentile
    min_iv, max_iv = min(all_iv), max(all_iv)
    metrics['IV Percentile/Rank'] = {
        'atm_iv': atm_iv,
        'min_chain_iv': min_iv,
        'max_chain_iv': max_iv,
        'iv_percentile': (atm_iv - min_iv) / (max_iv - min_iv) * 100 if max_iv > min_iv else 0
    }
    
    # 8. Delta Weighted OI
    metrics['Delta Weighted OI'] = {
        'total_call_effective_oi': call_effective,
        'total_put_effective_oi': put_effective,
        'net_effective_oi': call_effective - put_effective
    }
    
    # 9. Max Pain Calculation
    # Fixed price range calculation
    low_bound = min(strikes) - 500
    high_bound = max(strikes) + 500
    price_range = [low_bound + i * 50 for i in range(int((high_bound - low_bound) // 50 + 1))]
    
    pain_values = {}
    for price in price_range:
        pain = 0.0
        for strike, oi in oi_dict.items():
            # For call options
            if oi['ce'] > 0:
                pain += oi['ce'] * max(0, price - strike)
            # For put options
            if oi['pe'] > 0:
                pain += oi['pe'] * max(0, strike - price)
        pain_values[price] = pain
    
    min_pain_price = min(pain_values, key=pain_values.get)
    metrics['Max Pain Calculation'] = {
        'max_pain_strike': min_pain_price,
        'pain_value': pain_values[min_pain_price]
    }
    
    # 10. Theta Decay
    metrics['Theta Decay Burden (Enhanced)'] = {
        'total_call_theta': call_theta,
        'total_put_theta': put_theta,
        'total_theta_burden': call_theta + put_theta,
        'put_call_theta_ratio': put_theta / call_theta if call_theta else 0,
        'daily_cost_millions': (call_theta + put_theta) / 1000000
    }
    
    # 11. Volatility Smile
    metrics['Volatility Smile/Smirk'] = {
        'low_put_iv': otm_put_iv,
        'atm_iv': atm_iv,
        'high_call_iv': otm_call_iv
    }
    
    return metrics


def get_next_api_key():
    global USED_KEY_INDEX
    with key_lock:
        next_index = (USED_KEY_INDEX + 1) % len(API_KEYS)
        USED_KEY_INDEX = next_index
        return API_KEYS[next_index]


response_text=''
def call_llm(option_chain_data, precomputed_metrics,first_expiry):
    # Construct optimized prompt
    prompt = f"""
          ROLE: Professional Options Market Analyst
          TASK: Analyze NIFTY option chain data and provide trade recommendations(expiry date={first_expiry})
          INSTRUCTIONS:
          1. Use precomputed metrics for quantitative values
          2. Add qualitative interpretations and sentiment scores
          3. Generate tactical ideas based on metrics
          4. Provide comprehensive bias analysis
          5. OUTPUT strict JSON format matching template
          6. Sentiment scoring:
             - 1: Highly bullish
             - 2: Moderately bullish
             - 3: Neutral
             - 4: Moderately bearish
             - 5: Highly bearish
          7. For each metric interpretation, select ONLY ONE relevant interpretation
          8. Suggested strategies:
             - FIRST strategy: Single option trade (buy 1 call OR 1 put)
             - Additional: Up to 3 more complex strategies
          9. Remmeber i need all my metrics to  be there as given in output template(dont even miss one)

          PRE-COMPUTED METRICS:
          {json.dumps(precomputed_metrics, indent=2)}

          OPTION CHAIN DATA (reference only):
          {json.dumps(option_chain_data['option_chain'])}

          OUTPUT TEMPLATE (use same structure and field names):
          {json.dumps(METRIC_TEMPLATE, indent=2)}
          10. CRITICAL: Output json should have all metrics
          """

    for _ in range(len(API_KEYS)):
        api_key = get_next_api_key()
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        try:
            completion = client.chat.completions.create(
                #model="deepseek/deepseek-r1-0528:free",
                model="deepseek/deepseek-chat-v3-0324:free",                
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
                extra_headers={
                    "HTTP-Referer": "https://yourdomain.com",
                    "X-Title": "OptionChainAnalyzer"
                }
            )

            response_text = completion.choices[0].message.content.strip()
            return json.loads(response_text)
        except Exception as e:
            # Handle insufficient balance error specifically
            if "Insufficient" in str(e) or "402" in str(e):
                print(f"❌ Key {api_key[-6:]} has insufficient balance. Rotating...")
            else:
                print(f"❌ LLM failed — {e}")
    return None

@app.get("/analyze")
def get_llm_analysis():
    """Returns the latest scheduled LLM analysis"""
    with llm_cache_lock:
        if llm_analysis_cache is None:
            raise HTTPException(status_code=503, detail="Analysis not available yet")
        return {"llm_analysis": llm_analysis_cache}


# ====================== Strike String Endpoint ======================
@app.get("/strike_string")
def get_strike_string_endpoint():
    """Endpoint to get current strike string in security list format"""
    try:
        # Get current expiry from option chain cache
        option_data = get_cached_option_chain()
        expiry_date = option_data["expiry"]
        
        # Get cached LLM analysis
        with llm_cache_lock:
            if not llm_analysis_cache:
                return {"strike_string": "ANALYSIS_UNAVAILABLE"}
            analysis = llm_analysis_cache
        
        # Extract first strategy details
        strategy = analysis["bias_analysis"]["suggested_strategies"][0]
        strike = strategy.get("strike", 0)
        option_type = strategy.get("strike_type", "PUT").upper()
        
        # Format date components
        expiry_dt = datetime.strptime(expiry_date, '%Y-%m-%d')
        year_2digit = expiry_dt.strftime('%y')
        month_abbr = expiry_dt.strftime('%b').upper()
        day_2digit = expiry_dt.strftime('%d')
        
        # Generate proper strike string format based on security list format
        strike_string = f"NIFTY {day_2digit} {month_abbr} {strike} {'CALL' if option_type == 'CALL' else 'PUT'}"
        
        return {"strike_string": strike_string}
    
    except Exception as e:
        return {"error": f"Strike string generation failed: {str(e)}"}



 
# ====================== Trade Scheduler ======================
def trade_execution_scheduler():
    """Background task that executes trades based on LLM analysis"""
    print("🚀 Starting trade execution scheduler")
    while True:
        try:
            print("\n" + "="*50)
            print(f"🔄 Running trade check at {datetime.now()}")
            execute_llm_trade()
            print(f"✅ Trade execution check completed")
            print("="*50 + "\n")
        except Exception as e:
            print(f"❌ Trade execution scheduler failed: {str(e)}")
        
        # Wait 15 minutes between checks
        time.sleep(900)
   
# ====================== Security List Caching ======================
SECURITY_MAP_CACHE = None
SECURITY_CACHE_TIME = 0
SECURITY_CACHE_LOCK = threading.Lock()
SECURITY_CACHE_TTL = 24 * 60 * 60  # Refresh every 24 hours

def get_security_map():
    """Get security map with DataFrame handling"""
    global SECURITY_MAP_CACHE, SECURITY_CACHE_TIME
    
    with SECURITY_CACHE_LOCK:
        current_time = time.time()
        
        # Return cache if valid
        if SECURITY_MAP_CACHE and (current_time - SECURITY_CACHE_TIME) < SECURITY_CACHE_TTL:
            return SECURITY_MAP_CACHE
        
        try:
            print("🔁 Refreshing security list cache...")
            # Fetch security list as DataFrame
            security_df = dhan.fetch_security_list("compact")
            
            # Save to CSV for debugging
            security_df.to_csv("security_list.csv", index=False)
            print("💾 Saved security list to security_list.csv")
            
            # Create symbol->ID mapping
            security_map = {}
            for _, row in security_df.iterrows():
                symbol = row.get('SEM_CUSTOM_SYMBOL')
                if pd.notna(symbol):  # Check for NaN values
                    # Clean up symbol name
                    clean_symbol = ' '.join(str(symbol).strip().split())
                    security_id = row['SEM_SMST_SECURITY_ID']
                    security_map[clean_symbol] = security_id
            
            # Update cache
            SECURITY_MAP_CACHE = security_map
            SECURITY_CACHE_TIME = current_time
            print(f"✅ Security list refreshed with {len(security_map)} symbols")
            return security_map
            
        except Exception as e:
            print(f"❌ Failed to refresh security list: {e}")
            # Try to load from CSV if available
            try:
                if os.path.exists("security_list.csv"):
                    security_df = pd.read_csv("security_list.csv")
                    print("♻️ Using cached security list from CSV file")
                    
                    security_map = {}
                    for _, row in security_df.iterrows():
                        symbol = row.get('SEM_CUSTOM_SYMBOL')
                        if pd.notna(symbol):
                            clean_symbol = ' '.join(str(symbol).strip().split())
                            security_id = row['SEM_SMST_SECURITY_ID']
                            security_map[clean_symbol] = security_id
                    return security_map
            except Exception as file_error:
                print(f"❌ Failed to load from CSV: {file_error}")
            
            return SECURITY_MAP_CACHE or {}
# ====================== Trade Execution Logic ======================
def execute_llm_trade():
    """Execute trade based on latest LLM analysis"""
    try:
        # Get the latest LLM analysis
        with llm_cache_lock:
            if not llm_analysis_cache:
                print("⚠️ LLM analysis not available for trade execution")
                return
            analysis = llm_analysis_cache
        
        # Get current expiry from option chain
        option_data = get_cached_option_chain()
        expiry_date = option_data["expiry"]
        
        # Extract first strategy details
        strategy = analysis["bias_analysis"]["suggested_strategies"][0]
        strike = strategy.get("strike")
        option_type = strategy.get("strike_type", "PUT").upper()  # Default to PUT
        
        # Format date components
        expiry_dt = datetime.strptime(expiry_date, '%Y-%m-%d')
        year_2digit = expiry_dt.strftime('%y')
        month_abbr = expiry_dt.strftime('%b').upper()
        day_2digit = expiry_dt.strftime('%d')
        
        # Generate proper strike string format based on security list format
        # Format: "NIFTY 24 JUN 25000 CE" or "NIFTY 24 JUN 25000 PE"
        strike_string = f"NIFTY {day_2digit} {month_abbr} {strike} {'CALL' if option_type == 'CALL' else 'PUT'}"        
        print(f"🔍 Generated strike string: {strike_string}")
        
        # Check existing positions
        positions = dhan.get_positions()
        if positions and positions.get('status') == 'success' and positions.get('data'):
            print("⏩ Positions already exist. Skipping trade execution.")
            return
        
        # Get security ID from cache
        security_map = get_security_map()
        security_id = security_map.get(strike_string)
        
        if not security_id:
            # Try alternative formatting if exact match not found
            alt_strike_string = f"NIFTY{year_2digit}{month_abbr}{strike}{'CE' if option_type == 'CALL' else 'PE'}"
            security_id = security_map.get(alt_strike_string)
            
            if not security_id:
                print(f"❌ Symbol '{strike_string}' not found in security list")
                # Print some similar symbols for debugging
                similar = [sym for sym in security_map.keys() if 'NIFTY' in sym][:5]
                print(f"ℹ️ Sample NIFTY symbols: {similar}")
                return
        
        print(f"✅ Found Security ID: {security_id} for {strike_string}")
        
        order_response = dhan.place_order(
        security_id=security_id,
        exchange_segment=dhan.NSE_FNO,
        transaction_type=dhan.BUY,
        quantity=75,
        order_type=dhan.MARKET,
        product_type=dhan.INTRA,
        price=0
        )

        print(f"📊 Order Response: {order_response}")

        # Check if order was successful
        if order_response.get('status') != 'success':
            # Try to extract meaningful error message
            remarks = order_response.get('remarks', {})
            data = order_response.get('data', {})

            error_message = (
                remarks.get('error_message') or
                data.get('errorMessage') or
                order_response.get('message') or
                "Unknown error"
            )

            print(f"❌ Order failed: {error_message}")
        else:
            print("🎉 Trade executed successfully!")

        print("✅ Trade execution check completed")

    except Exception as e:
        print(f"🔥 Trade execution failed: {str(e)}")


# Run with: uvicorn analysis:app --reload