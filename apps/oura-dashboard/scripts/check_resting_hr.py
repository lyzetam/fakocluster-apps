#!/usr/bin/env python3
"""
Check resting heart rate data in the database
"""
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text

# Build connection string from environment variables
def get_connection_string():
    """Build PostgreSQL connection string from environment variables"""
    host = os.environ.get('DATABASE_HOST', 'localhost')
    port = os.environ.get('DATABASE_PORT', '5432')
    database = os.environ.get('DATABASE_NAME', 'oura_health')
    user = os.environ.get('DATABASE_USER', 'postgres')
    password = os.environ.get('DATABASE_PASSWORD', '')
    
    if password:
        from urllib.parse import quote_plus
        password = quote_plus(password)
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    else:
        return f"postgresql://{user}@{host}:{port}/{database}"

def main():
    """Check resting heart rate data"""
    try:
        # Try to get connection string from environment first
        connection_string = os.environ.get('DATABASE_URL')
        if not connection_string:
            connection_string = get_connection_string()
        
        print(f"Connecting to database...")
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # Check readiness table for resting heart rate
            print("\nChecking Resting Heart Rate Data:")
            print("=" * 60)
            
            # Get sample readiness records
            query = text("""
                SELECT 
                    date,
                    readiness_score,
                    resting_heart_rate,
                    hrv_balance,
                    temperature_deviation
                FROM oura_readiness
                ORDER BY date DESC
                LIMIT 10
            """)
            
            results = conn.execute(query).fetchall()
            
            if results:
                print("\nRecent readiness records:")
                for row in results:
                    print(f"\nDate: {row[0]}")
                    print(f"  Readiness score: {row[1]}")
                    print(f"  Resting HR: {row[2]} {'⚠️ MISSING' if row[2] is None else 'bpm'}")
                    print(f"  HRV balance: {row[3]}")
                    print(f"  Temperature deviation: {row[4]}")
            else:
                print("No readiness data found")
            
            # Get statistics
            query_stats = text("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(resting_heart_rate) as records_with_hr,
                    MIN(resting_heart_rate) as min_hr,
                    MAX(resting_heart_rate) as max_hr,
                    AVG(resting_heart_rate) as avg_hr
                FROM oura_readiness
            """)
            
            stats = conn.execute(query_stats).fetchone()
            if stats:
                print("\n" + "=" * 60)
                print("Resting Heart Rate Statistics:")
                print(f"Total readiness records: {stats[0]}")
                print(f"Records with resting HR: {stats[1]}")
                print(f"Missing resting HR: {stats[0] - stats[1]} ({(stats[0] - stats[1]) / stats[0] * 100:.1f}%)")
                if stats[1] > 0:
                    print(f"Min HR: {stats[2]} bpm")
                    print(f"Max HR: {stats[3]} bpm")
                    print(f"Avg HR: {stats[4]:.1f} bpm")
            
            # Check raw data structure
            query_raw = text("""
                SELECT 
                    date,
                    raw_data
                FROM oura_readiness
                WHERE resting_heart_rate IS NULL
                ORDER BY date DESC
                LIMIT 1
            """)
            
            raw_result = conn.execute(query_raw).fetchone()
            if raw_result and raw_result[1]:
                print("\n" + "=" * 60)
                print(f"Sample raw data for record without resting HR ({raw_result[0]}):")
                import json
                raw_data = raw_result[1] if isinstance(raw_result[1], dict) else json.loads(raw_result[1])
                print(json.dumps(raw_data, indent=2))
                
                # Check if resting_heart_rate exists in raw data
                if 'resting_heart_rate' in raw_data:
                    print(f"\n⚠️ ISSUE: resting_heart_rate exists in raw data ({raw_data['resting_heart_rate']}) but not in column!")
            
            # Check sleep periods for heart rate data
            print("\n" + "=" * 60)
            print("Checking Sleep Periods Heart Rate Data:")
            
            query_sleep = text("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(heart_rate_avg) as records_with_avg_hr,
                    COUNT(heart_rate_min) as records_with_min_hr,
                    AVG(heart_rate_avg) as avg_sleep_hr,
                    AVG(heart_rate_min) as avg_min_hr
                FROM oura_sleep_periods
                WHERE type = 'long_sleep'
            """)
            
            sleep_stats = conn.execute(query_sleep).fetchone()
            if sleep_stats:
                print(f"Total sleep records: {sleep_stats[0]}")
                print(f"Records with avg HR: {sleep_stats[1]}")
                print(f"Records with min HR: {sleep_stats[2]}")
                if sleep_stats[1] > 0:
                    print(f"Avg sleep HR: {sleep_stats[3]:.1f} bpm")
                    print(f"Avg min HR: {sleep_stats[4]:.1f} bpm")
        
        engine.dispose()
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
