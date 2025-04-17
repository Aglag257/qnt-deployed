import ccxt
import pandas as pd
import streamlit as st
from datetime import datetime
import time

EXCHANGES = ['binance', 'coinbase', 'kraken', 'bitfinex', 'kucoin']
TOP_COINS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']

error_messages = []

@st.cache_resource
def load_exchanges():
    exchange_objects = {}
    for ex in EXCHANGES:
        try:
            exchange = getattr(ccxt, ex)()
            exchange.load_markets()
            exchange_objects[ex] = exchange
        except Exception as e:
            error_messages.append(f"[ERROR] Could not load {ex}: {e}")
    return exchange_objects

def fetch_all_metrics(exchanges, coins):
    records = []
    for coin in coins:
        for ex_name, ex in exchanges.items():
            try:
                ticker = ex.fetch_ticker(coin)
                data = {
                    'Exchange': ex_name,
                    'Pair': coin,
                    'Price': ticker.get('last'),
                    'Bid': ticker.get('bid'),
                    'Ask': ticker.get('ask'),
                    'High (24h)': ticker.get('high'),
                    'Low (24h)': ticker.get('low'),
                    'Volume (24h)': ticker.get('baseVolume'),
                    'Quote Volume (24h)': ticker.get('quoteVolume'),
                    '% Change': ticker.get('percentage'),
                    'Change': ticker.get('change'),
                    'Previous Close': ticker.get('previousClose'),
                    'Open': ticker.get('open'),
                    'Timestamp': pd.to_datetime(ticker.get('timestamp'), unit='ms') if ticker.get('timestamp') else None,
                }
                records.append(data)
            except Exception as e:
                error_messages.append(f"[ERROR] {ex_name} - {coin}: {e}")
    return pd.DataFrame(records)

def get_arbitrage_summary(df, threshold_percent=0.5):
    summary = []
    grouped = df.groupby('Pair')
    for pair, group in grouped:
        prices = group.dropna(subset=['Price'])
        if len(prices) < 2:
            continue

        low_row = prices.loc[prices['Price'].idxmin()]
        high_row = prices.loc[prices['Price'].idxmax()]

        low = low_row['Price']
        high = high_row['Price']
        spread = ((high - low) / low) * 100 if low else 0

        if spread > threshold_percent:
            summary.append({
                "Pair": pair,
                "Buy @": f"{low:.2f} ({low_row['Exchange']})",
                "Sell @": f"{high:.2f} ({high_row['Exchange']})",
                "Spread (%)": f"{spread:.2f}"
            })
    return pd.DataFrame(summary)

def main():
    st.set_page_config(page_title="Crypto Broker Arbitrage Dashboard", layout="wide")
    st.title("📈 Crypto Broker Arbitrage Dashboard")
    st.caption("Live metrics and arbitrage detection across top exchanges.")
    st.sidebar.header("Settings")
    
    autorefresh = st.sidebar.toggle("Auto-refresh every 60 seconds", value=True)
    threshold = st.sidebar.slider("Arbitrage threshold (%)", 0.1, 5.0, 0.5, 0.1)

    exchanges = load_exchanges()
    
    placeholder = st.empty()

    while True:
        error_messages.clear()

        with placeholder.container():
            st.markdown(f"#### Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            df = fetch_all_metrics(exchanges, TOP_COINS)

            if error_messages:
                with st.expander("⚠️ View Error Log", expanded=False):
                    for msg in error_messages:
                        st.warning(msg)

            st.subheader("🔍 Full Exchange Metrics")
            st.dataframe(df.sort_values(by=['Pair', 'Exchange']), use_container_width=True)

            arb_df = get_arbitrage_summary(df, threshold)
            st.subheader("💰 Arbitrage Opportunities")
            if arb_df.empty:
                st.info("No arbitrage opportunities found above threshold.")
            else:
                st.dataframe(arb_df, use_container_width=True)

        if not autorefresh:
            break
        time.sleep(60)

if __name__ == "__main__":
    main()
