#!/usr/bin/env python3
"""
Check stress data values in the database
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
    """Check stress data values"""
    try:
        # Try to get connection string from environment first
        connection_string = os.environ.get('DATABASE_URL')
        if not connection_string:
            connection_string = get_connection_string()
        
        print(f"Connecting to database...")
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # Check stress data
            print("\nStress Data Analysis:")
            print("=" * 60)
            
            # Get sample stress records
            query = text("""
                SELECT 
                    date,
                    stress_high_minutes,
                    recovery_high_minutes,
                    stress_recovery_ratio,
                    day_summary
                FROM oura_stress
                ORDER BY date DESC
                LIMIT 10
            """)
            
            results = conn.execute(query).fetchall()
            
            if results:
                print("\nRecent stress records:")
                for row in results:
                    print(f"\nDate: {row[0]}")
                    print(f"  Stress minutes: {row[1]}")
                    print(f"  Recovery minutes: {row[2]}")
                    print(f"  Stress/Recovery ratio: {row[3]}")
                    print(f"  Day summary: {row[4][:50] if row[4] else 'None'}...")
                    
                    # Check if values seem reasonable
                    if row[1] and row[1] > 1440:  # More than 24 hours
                        print(f"  ⚠️  WARNING: Stress minutes ({row[1]}) exceeds 24 hours!")
                    if row[2] and row[2] > 1440:  # More than 24 hours
                        print(f"  ⚠️  WARNING: Recovery minutes ({row[2]}) exceeds 24 hours!")
            else:
                print("No stress data found")
            
            # Get statistics
            query_stats = text("""
                SELECT 
                    MIN(stress_high_minutes) as min_stress,
                    MAX(stress_high_minutes) as max_stress,
                    AVG(stress_high_minutes) as avg_stress,
                    MIN(recovery_high_minutes) as min_recovery,
                    MAX(recovery_high_minutes) as max_recovery,
                    AVG(recovery_high_minutes) as avg_recovery
                FROM oura_stress
                WHERE stress_high_minutes IS NOT NULL
            """)
            
            stats = conn.execute(query_stats).fetchone()
            if stats:
                print("\n" + "=" * 60)
                print("Stress Data Statistics:")
                print(f"Stress minutes - Min: {stats[0]}, Max: {stats[1]}, Avg: {stats[2]:.1f}")
                print(f"Recovery minutes - Min: {stats[3]}, Max: {stats[4]}, Avg: {stats[5]:.1f}")
                
                if stats[1] > 1440:
                    print(f"\n⚠️  ISSUE FOUND: Maximum stress minutes ({stats[1]}) exceeds 24 hours (1440 minutes)")
                    print("This suggests the data might be in seconds instead of minutes!")
            
            # Check raw data
            query_raw = text("""
                SELECT 
                    date,
                    raw_data
                FROM oura_stress
                ORDER BY date DESC
                LIMIT 1
            """)
            
            raw_result = conn.execute(query_raw).fetchone()
            if raw_result and raw_result[1]:
                print("\n" + "=" * 60)
                print(f"Raw data sample for {raw_result[0]}:")
                import json
                raw_data = raw_result[1] if isinstance(raw_result[1], dict) else json.loads(raw_result[1])
                print(json.dumps(raw_data, indent=2))
        
        engine.dispose()
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
