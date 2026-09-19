import time
import json
import random
from datetime import datetime, timezone
from azure.eventhub import EventHubProducerClient, EventData

# PASTE YOUR COPIED FABRIC CONNECTION STRING HERE
EVENTSTREAM_CONNECTION_STRING = ""

SITE_CODES = ["STORE_101", "STORE_102", "STORE_103", "STORE_104"]
SKU_LIST = [
    {"sku": "SKU-MILK-001", "base_price": 3.99, "category": "Dairy"},
    {"sku": "SKU-BREAD-002", "base_price": 2.49, "category": "Bakery"},
    {"sku": "SKU-EGG-003", "base_price": 4.19, "category": "Dairy"},
    {"sku": "SKU-JUICE-004", "base_price": 5.99, "category": "Beverages"}
]

def generate_competitor_signal():
    """Generates real-time competitor pricing intelligence signals."""
    site = random.choice(SITE_CODES)
    item = random.choice(SKU_LIST)
    price_factor = round(random.uniform(0.85, 1.10), 2)
    
    return {
        "signal_id": f"SIG-{int(time.time() * 1000)}",
        "signal_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "site_code": site,
        "item_sku": item["sku"],
        "competitor_price": round(item["base_price"] * price_factor, 2),
        "signal_type": "WEB_SCRAPE_REALTIME"
    }

if __name__ == "__main__":
    print("Connecting to Fabric Eventstream...")
    producer = EventHubProducerClient.from_connection_string(conn_str=EVENTSTREAM_CONNECTION_STRING)
    print("Streaming live telemetry to Fabric... Press CTRL+C to stop.")
    
    try:
        with producer:
            while True:
                competitor_data = generate_competitor_signal()
                batch = producer.create_batch()
                batch.add(EventData(json.dumps(competitor_data)))
                producer.send_batch(batch)
                
                print(f"[SENT TO FABRIC KQL]: {competitor_data['signal_id']} | Site: {competitor_data['site_code']} | Price: ${competitor_data['competitor_price']}")
                time.sleep(2)
    except KeyboardInterrupt:
        print("\nTelemetry generation stopped.")