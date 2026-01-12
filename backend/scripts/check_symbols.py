import requests


def check_cop_pairs():
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url)
        data = response.json()

        cop_pairs = [s['symbol']
                     for s in data['symbols'] if 'COP' in s['symbol']]

        print(f"Found {len(cop_pairs)} pairs involving COP.")
        for pair in cop_pairs:
            print(pair)

        if not cop_pairs:
            print("No direct spot trading pairs found for COP.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_cop_pairs()
