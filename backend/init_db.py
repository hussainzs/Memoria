#!/usr/bin/env python3
"""
Database initialization script
"""
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

def wait_for_db():
    """Wait for database to be ready"""
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = psycopg2.connect(
                host="db",
                port="5432",
                user="memoria",
                password="memoria",
                database="memoria"
            )
            conn.close()
            print("Database is ready")
            return True
        except psycopg2.OperationalError:
            retry_count += 1
            print(f"Waiting for database... ({retry_count}/{max_retries})")
            time.sleep(2)
    
    print("Database not ready after maximum retries")
    return False

def init_database():
    """Initialize database with schema"""
    if not wait_for_db():
        return False
    
    try:
        conn = psycopg2.connect(
            host="db",
            port="5432",
            user="memoria",
            password="memoria",
            database="memoria"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        with open('/app/app/db/schema.sql', 'r') as f:
            schema_sql = f.read()
        
        cursor.execute(schema_sql)
        print("Database schema created successfully")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    exit(0 if success else 1)
