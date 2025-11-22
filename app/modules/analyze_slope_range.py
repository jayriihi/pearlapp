from datetime import datetime, timedelta
from tidal_data_retrieval import get_detailed_tide_predictions
import pandas as pd

def analyze_annual_slope_stats(station_id=2695540):
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()

    print("Fetching 1 year of tide data...")
    df = get_detailed_tide_predictions(station_id, start_date, end_date)

    print("Calculating slopes...")
    df['slope'] = df['v'].diff() / (15 * 60) * 3600  # m/hr
    df = df.dropna()

    print("Slope stats:")
    print("  Max slope:", df['slope'].max())
    print("  Min slope:", df['slope'].min())
    print("  Mean absolute slope:", df['slope'].abs().mean())
    print("  90th percentile:", df['slope'].abs().quantile(0.9))
    print("  95th percentile:", df['slope'].abs().quantile(0.95))

    # Optionally save to CSV if you want to explore further
    df[['t', 'v', 'slope']].to_csv("tide_slope_year.csv", index=False)
    print("Saved slope data to tide_slope_year.csv")

if __name__ == "__main__":
    analyze_annual_slope_stats()
