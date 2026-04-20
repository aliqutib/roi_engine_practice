from pymongo import MongoClient
import csv


def convert_str_price_float (price:str):
    return float(((price)[1:-3]).replace(',', ''))

def load_dataset_from_kaggle(csv_path:str, db) :

    records = []

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row  in reader:
            records.append({
                "channel": row['Channel_Used'],
                "roi": float(row['ROI']),
                "conversion_rate": float(row['Conversion_Rate']),
                "budget": convert_str_price_float(row['Acquisition_Cost']),
                "revenue": float(row['ROI']) * convert_str_price_float(row['Acquisition_Cost'])
            })

    db.campaigns.insert_many(records)
    db.campaigns.create_index("channel")
    print(f'{len(records)} added to the database')
    

client = MongoClient('mongodb://localhost:27017/')
db = client['marketing_ai']

#load_dataset_from_kaggle('marketing_campaign_dataset.csv', db) # <- uncomment once to load kaggle dataset into your mongo db
