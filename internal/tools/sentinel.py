import os
import sys
import time
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to sys.path to allow imports if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

def get_db_url():
    # Attempt to pull from environment or default to common dev path
    # In a real scenario, this would pull from the .env file
    return "postgresql://scentrix:scentrix_password@localhost:5432/scentrix"

def monitor():
    url = get_db_url()
    try:
        engine = create_engine(url)
        Session = sessionmaker(bind=engine)
        session = Session()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sentinel Active. Monitoring Scentrix Pulsometry...")
        print("-" * 80)
        print(f"{'Timestamp':<20} | {'User ID':<8} | {'Event':<15} | {'Value':<10} | {'Fragrance':<20}")
        print("-" * 80)
    except Exception as e:
        print(f"Database Connection Error: {e}")
        return

    last_id = 0
    
    # First run: get the last ID to only show new events
    try:
        res = session.execute(text("SELECT MAX(id) FROM user_interaction_events")).fetchone()
        last_id = res[0] if res[0] else 0
    except:
        pass

    while True:
        try:
            query = text("SELECT id, created_at, user_id, interaction_type, interaction_value, fragrance_neo4j_id FROM user_interaction_events WHERE id > :last_id ORDER BY id ASC")
            events = session.execute(query, {"last_id": last_id}).fetchall()
            
            for event in events:
                ts = event[1].strftime('%Y-%m-%d %H:%M:%S')
                uid = event[2]
                etype = event[3]
                val = event[4] if event[4] else "N/A"
                fid = event[5]
                print(f"{ts:<20} | {uid:<8} | {etype:<15} | {val:<10} | {fid:<20}")
                last_id = event[0]
            
            # Check for new users too
            user_query = text("SELECT id, email_hash, created_at FROM users WHERE id > (SELECT COALESCE(MAX(id)-5, 0) FROM users) ORDER BY id DESC LIMIT 5")
            # (Optional: display recent signups)
            
            time.sleep(2)
        except KeyboardInterrupt:
            print("\nSentinel Disengaged.")
            break
        except Exception as e:
            print(f"Monitoring Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor()
