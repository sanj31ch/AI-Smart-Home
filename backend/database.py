# database.py - COMPLETE FIX for "Unread result found" error
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import time

class Database:
    def __init__(self):
        self.host = "localhost"
        self.user = "root"
        self.password = "WU02@urmila"  # Your MySQL password
        self.database = "smart_home"
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establish database connection with retry logic"""
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                print(f"📡 Connecting to database (attempt {attempt + 1}/{max_retries})...")
                
                # First connect without database
                connection = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    connection_timeout=10,
                    buffered=True  # Important: Add buffered=True
                )
                
                cursor = connection.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                cursor.close()
                connection.close()
                
                # Connect to the database with buffered=True
                self.connection = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    autocommit=True,
                    buffered=True,  # Critical for preventing "Unread result found"
                    connection_timeout=10
                )
                
                print("✅ Database connected successfully")
                return True
                
            except Error as e:
                print(f"❌ Database connection error (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt == max_retries - 1:
                    print("❌ Failed to connect to database after all retries")
                    return False
                
                print(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
        
        return False
    
    def ensure_tables(self):
        """Create all required tables"""
        try:
            if not self.connection:
                print("❌ No database connection")
                return False
                
            cursor = self.connection.cursor()
            
            # Devices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    device_name VARCHAR(50) UNIQUE NOT NULL,
                    status VARCHAR(50) DEFAULT 'OFF',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Voice commands table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS voice_commands (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    command_text TEXT NOT NULL,
                    language VARCHAR(20),
                    recognized_device VARCHAR(50),
                    recognized_action VARCHAR(50),
                    confidence FLOAT,
                    executed BOOLEAN DEFAULT FALSE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Device logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    device_name VARCHAR(50) NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    source VARCHAR(20) DEFAULT 'manual',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User habits table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_habits (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    device_name VARCHAR(50) NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    hour_of_day INT NOT NULL,
                    day_of_week INT NOT NULL,
                    frequency INT DEFAULT 1,
                    last_triggered TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_habit (device_name, action, hour_of_day, day_of_week)
                )
            """)
            
            # ML predictions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ml_predictions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    device_name VARCHAR(50) NOT NULL,
                    predicted_action VARCHAR(50) NOT NULL,
                    confidence FLOAT NOT NULL,
                    scheduled_time TIME,
                    executed BOOLEAN DEFAULT FALSE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ESP32 devices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS esp_devices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    mac_address VARCHAR(17) UNIQUE NOT NULL,
                    ip_address VARCHAR(15),
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'offline',
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.close()
            self.init_default_devices()
            
            print("✅ All tables created successfully")
            return True
            
        except Error as e:
            print(f"❌ Table creation error: {e}")
            return False
    
    def init_default_devices(self):
        """Initialize default devices"""
        try:
            if not self.connection:
                return False
                
            default_devices = [
                ('light', 'OFF'),
                ('fan', 'OFF'),
                ('fan_speed', '0'),
                ('door', 'LOCKED')  # Changed from door_lock to door for consistency
            ]
            
            cursor = self.connection.cursor()
            
            for device_name, status in default_devices:
                cursor.execute("""
                    INSERT IGNORE INTO devices (device_name, status) 
                    VALUES (%s, %s)
                """, (device_name, status))
            
            cursor.close()
            self.connection.commit()
            print("✅ Default devices initialized")
            return True
            
        except Error as e:
            print(f"❌ Device initialization error: {e}")
            return False
    
    def get_device_status(self, device_name=None):
        """Get device status - FIXED for 'Unread result found' error"""
        try:
            if not self.connection:
                print("❌ No database connection")
                return []
            
            # Always create a new cursor for each query
            cursor = self.connection.cursor(dictionary=True, buffered=True)
            
            if device_name:
                cursor.execute("SELECT * FROM devices WHERE device_name = %s", (device_name,))
            else:
                cursor.execute("SELECT * FROM devices ORDER BY id")
            
            # Fetch all results immediately
            result = cursor.fetchall()
            
            # Close cursor to free resources
            cursor.close()
            
            return result
            
        except Error as e:
            print(f"❌ Error getting device status: {e}")
            return []
    
    def update_device_status(self, device_name, status, source='manual'):
        """Update device status - FIXED"""
        try:
            if not self.connection:
                print("❌ No database connection")
                return False
            
            # Clean status - remove any underscores for display
            clean_status = status.split('_')[0] if '_' in status else status
            
            # Use separate cursors for each operation
            cursor1 = self.connection.cursor(buffered=True)
            cursor2 = self.connection.cursor(buffered=True)
            
            # Update device status
            cursor1.execute("""
                UPDATE devices 
                SET status = %s, last_updated = NOW() 
                WHERE device_name = %s
            """, (clean_status, device_name))
            
            # Log the action
            cursor2.execute("""
                INSERT INTO device_logs (device_name, action, source, timestamp)
                VALUES (%s, %s, %s, NOW())
            """, (device_name, status, source))
            
            # Close cursors
            cursor1.close()
            cursor2.close()
            
            self.connection.commit()
            
            print(f"✅ Device updated: {device_name} = {clean_status} (source: {source})")
            return True
            
        except Error as e:
            print(f"❌ Error updating device: {e}")
            return False
    
    def store_voice_command(self, command_text, language, device, action, confidence, executed):
        """Store voice command - FIXED"""
        try:
            if not self.connection:
                return False
            
            cursor = self.connection.cursor(buffered=True)
            
            cursor.execute("""
                INSERT INTO voice_commands 
                (command_text, language, recognized_device, recognized_action, confidence, executed, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (command_text, language, device, action, confidence, executed))
            
            cursor.close()
            self.connection.commit()
            
            return True
            
        except Error as e:
            print(f"❌ Error storing voice command: {e}")
            return False
    
    def record_habit(self, device_name, action):
        """Record user habit for ML - FIXED"""
        try:
            if not self.connection:
                return False
            
            now = datetime.now()
            hour = now.hour
            day = now.weekday()
            
            cursor = self.connection.cursor(buffered=True)
            
            cursor.execute("""
                INSERT INTO user_habits (device_name, action, hour_of_day, day_of_week, frequency)
                VALUES (%s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                frequency = frequency + 1,
                last_triggered = NOW()
            """, (device_name, action, hour, day))
            
            cursor.close()
            self.connection.commit()
            
            return True
            
        except Error as e:
            print(f"❌ Error recording habit: {e}")
            return False
    
    def get_habits_for_ml(self):
        """Get all habits for ML processing - FIXED"""
        try:
            if not self.connection:
                return []
            
            cursor = self.connection.cursor(dictionary=True, buffered=True)
            
            cursor.execute("""
                SELECT device_name, action, hour_of_day, day_of_week, 
                       SUM(frequency) as total_frequency
                FROM user_habits 
                GROUP BY device_name, action, hour_of_day, day_of_week
                ORDER BY total_frequency DESC
            """)
            
            result = cursor.fetchall()
            cursor.close()
            
            return result
            
        except Error as e:
            print(f"❌ Error getting habits: {e}")
            return []
    
    def save_prediction(self, device, action, confidence, scheduled_time):
        """Save ML prediction - FIXED"""
        try:
            if not self.connection:
                return False
            
            cursor = self.connection.cursor(buffered=True)
            
            cursor.execute("""
                INSERT INTO ml_predictions (device_name, predicted_action, confidence, scheduled_time, timestamp)
                VALUES (%s, %s, %s, %s, NOW())
            """, (device, action, confidence, scheduled_time))
            
            cursor.close()
            self.connection.commit()
            
            return True
            
        except Error as e:
            print(f"❌ Error saving prediction: {e}")
            return False
    
    def register_esp(self, mac_address, ip_address):
        """Register ESP32 device - FIXED"""
        try:
            if not self.connection:
                return False
            
            cursor = self.connection.cursor(buffered=True)
            
            cursor.execute("""
                INSERT INTO esp_devices (mac_address, ip_address, status, last_seen)
                VALUES (%s, %s, 'online', NOW())
                ON DUPLICATE KEY UPDATE
                ip_address = %s,
                status = 'online',
                last_seen = NOW()
            """, (mac_address, ip_address, ip_address))
            
            cursor.close()
            self.connection.commit()
            
            return True
            
        except Error as e:
            print(f"❌ Error registering ESP: {e}")
            return False
    
    def test_connection(self):
        """Test database connection"""
        try:
            if not self.connection:
                return False
            
            cursor = self.connection.cursor(buffered=True)
            cursor.execute("SELECT 1")
            cursor.fetchone()  # Important: fetch the result
            cursor.close()
            
            return True
        except:
            return False
    
    def close(self):
        """Close database connection"""
        try:
            if self.connection and self.connection.is_connected():
                self.connection.close()
                print("✅ Database connection closed")
        except:
            pass