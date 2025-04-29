import ccxt
import pandas as pd
import streamlit as st
from datetime import datetime, timezone
import time

st.set_option('server.headless', True)
st.set_option('server.enableCORS', False)
st.set_option('server.enableXsrfProtection', False)


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

        if not autorefresh:
            break
        time.sleep(60)

if __name__ == "__main__":
    main()
