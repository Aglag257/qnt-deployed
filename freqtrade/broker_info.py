import ccxt
import pandas as pd

EXCHANGES = ['binance', 'coinbase', 'kraken', 'bitfinex', 'kucoin']
TOP_COINS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']

def load_exchanges():
    exchange_objects = {}
    for ex in EXCHANGES:
        try:
            exchange = getattr(ccxt, ex)()
            exchange.load_markets()
            exchange_objects[ex] = exchange
        except Exception as e:
            print(f"[ERROR] Could not load {ex}: {e}")
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
                print(f"[ERROR] {ex_name} - {coin}: {e}")
    return pd.DataFrame(records)

def print_arbitrage_summary(df, threshold_percent=0.5):
    print("\n=== Arbitrage Summary ===\n")
    grouped = df.groupby('Pair')

    found = False
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
            found = True
            print(f"{pair}:")
            print(f"  Buy @ {low:.2f} ({low_row['Exchange']})")
            print(f"  Sell @ {high:.2f} ({high_row['Exchange']})")
            print(f"  Spread: {spread:.2f}%\n")

    if not found:
        print("No arbitrage opportunities found.")

if __name__ == "__main__":
    print("[*] Loading exchanges...")
    exchanges = load_exchanges()

    print("[*] Fetching all available ticker metrics...")
    df = fetch_all_metrics(exchanges, TOP_COINS)

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print("\n=== Full Exchange Metrics ===\n")
    print(df.sort_values(by=['Pair', 'Exchange']).to_string(index=False))

    print_arbitrage_summary(df)
