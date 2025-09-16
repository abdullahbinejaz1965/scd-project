from config import Config

conn = Config.get_db_connection()
if conn:
    print("✅ Database connected successfully!")
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES;")
    for table in cursor.fetchall():
        print("Table:", table[0])
    conn.close()
else:
    print("❌ Database connection failed!")
