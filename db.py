from pymongo import MongoClient
import csv


def convert_str_price_float(price: str) -> float:
    return float((price[1:-3]).replace(',', ''))


def load_dataset_from_kaggle(csv_path: str, db):
    records = []

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                records.append({
                    "channel"        : row['Channel_Used'],
                    "roi"            : float(row['ROI']),
                    "conversion_rate": float(row['Conversion_Rate']),
                    "budget"         : convert_str_price_float(row['Acquisition_Cost']),
                    "revenue"        : float(row['ROI']) * convert_str_price_float(row['Acquisition_Cost'])
                })
            except (ValueError, KeyError):
                continue

    db.campaigns.drop()
    db.campaigns.insert_many(records)
    db.campaigns.create_index("channel")
    print(f'✅  {len(records)} records loaded into MongoDB (marketing_ai.campaigns)')


client = MongoClient('mongodb://localhost:27017/')
db = client['marketing_ai']


# ── Run this file ONCE to load the dataset ────────────────────────────────
# After loading, you can run main.py directly.

if __name__ == "__main__":
    load_dataset_from_kaggle('marketing_campaign_dataset.csv', db)
    print("Done! You can now run main.py")
