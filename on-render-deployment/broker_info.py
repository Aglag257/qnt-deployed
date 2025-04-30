import ccxt
import pandas as pd
import streamlit as st
from datetime import datetime, timezone
import time
import plotly.express as px
import uuid  

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
                    'Open': ticker.get('open'),
                    'Timestamp': pd.to_datetime(ticker.get('timestamp'), unit='ms') if ticker.get('timestamp') else None,
                }
                data['Timestamp (UTC+3)'] = data['Timestamp'] + pd.Timedelta(hours=3)
                records.append(data)
            except Exception as e:
                error_messages.append(f"[ERROR] {ex_name} - {coin}: {e}")
    return pd.DataFrame(records)

def display_charts_grid(df_subset, y_col, title_prefix, y_label, color_col="Exchange", log_y=False):
    coins = df_subset["Pair"].unique()
    num_cols = 3
    unique_id = str(uuid.uuid4())

    for i in range(0, len(coins), num_cols):
        cols = st.columns(num_cols)
        for j, coin in enumerate(coins[i:i + num_cols]):
            with cols[j]:
                fig = px.bar(
                    df_subset[df_subset["Pair"] == coin],
                    x="Exchange",
                    y=y_col,
                    color=color_col,
                    title=f"{coin}",
                    labels={y_col: y_label},
                    log_y=log_y,
                )
                st.plotly_chart(fig, use_container_width=True, key=f"{unique_id}-{y_col}-{coin}")

def main():
    st.set_page_config(page_title="Crypto Broker Information Dashboard", layout="wide")
    st.title("📈 Crypto Broker Information Dashboard")
    st.caption("Live metrics across top exchanges.")
    st.sidebar.header("Settings")
    
    autorefresh = st.sidebar.toggle("Auto-refresh every 60 seconds", value=True)

    exchanges = load_exchanges()
    
    placeholder = st.empty()

    while True:
        error_messages.clear()

        with placeholder.container():
            now_utc3 = datetime.utcnow() + pd.Timedelta(hours=3)
            st.markdown(f"#### Last updated: {now_utc3.strftime('%Y-%m-%d %H:%M:%S')} UTC+03:00")
            df = fetch_all_metrics(exchanges, TOP_COINS)

            if error_messages:
                with st.expander("⚠️ View Error Log", expanded=False):
                    for msg in error_messages:
                        st.warning(msg)

            st.subheader("🔍 Full Exchange Metrics")
            st.dataframe(df.sort_values(by=['Pair', 'Exchange']), use_container_width=True)
            price_df = df.dropna(subset=['Price'])

            volume_df = df.dropna(subset=["Volume (24h)"])
            change_df = df.dropna(subset=["% Change"])
            spread_df = df.copy()
            spread_df["Spread"] = spread_df["Ask"] - spread_df["Bid"]
            spread_df = spread_df.dropna(subset=["Spread"])

            st.subheader("💸 Price Per Coin")
            display_charts_grid(price_df, "Price", "Price", "Last Price")

            st.subheader("📊 24h Trading Volume")
            display_charts_grid(volume_df, "Volume (24h)", "24h Volume", "Volume", log_y=True)

            st.subheader("📈 24h % Change")
            display_charts_grid(change_df, "% Change", "% Change", "% Change")

            st.subheader("🔎 Bid-Ask Spread")
            display_charts_grid(spread_df, "Spread", "Spread", "Ask - Bid")

            st.subheader("⏱ Data Freshness (Age in Seconds)")
            fresh_df = df.copy()
            fresh_df["Data Age (sec)"] = (datetime.utcnow() - fresh_df["Timestamp"]).dt.total_seconds().round()
            fresh_df = fresh_df.dropna(subset=["Data Age (sec)"])

            fig_fresh = px.density_heatmap(
                fresh_df,
                x="Exchange",
                y="Pair",
                z="Data Age (sec)",
                color_continuous_scale="reds",
                title="Freshness of Broker Data (lower is better)",
                labels={"Data Age (sec)": "Age (s)"},
            )
            st.plotly_chart(fig_fresh, use_container_width=True)

        if not autorefresh:
            break
        time.sleep(60)

if __name__ == "__main__":
    main()
