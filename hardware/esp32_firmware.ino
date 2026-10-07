// ESP32_FINAL_FIXED.ino - Complete Working Code with Fixed Door Control
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ============= CONFIGURATION =============
const char* ssid = "vivo Y29 5G";        // CHANGE THIS
const char* password = "87654321";       // CHANGE THIS
const char* serverUrl = "http://10.161.87.87:5000"; // CHANGE TO YOUR PC IP

// ============= PIN DEFINITIONS =============
#define LIGHT_RELAY    23    // Light relay (LOW = ON)
#define FAN_RELAY      22    // Fan ON/OFF relay (LOW = ON)
#define FAN_PWM        14    // Fan speed control (PWM)
#define DOOR_SOLENOID  21    // Door solenoid lock (HIGH = UNLOCK, LOW = LOCK)
#define STATUS_LED     2     // Built-in LED
#define EXTRA_RELAY    33    // Extra for future

// ============= GLOBAL VARIABLES =============
String lightState = "OFF";
String fanState = "OFF";
String fanSpeed = "0";
String doorState = "LOCKED";

unsigned long lastCheck = 0;
const unsigned long checkInterval = 2000; // Check every 2 seconds
bool connected = false;

// Add flag to track if door command is from auto ML
bool doorCommandFromAuto = false;
unsigned long lastDoorCommandTime = 0;

// PWM Settings
const int freq = 5000;
const int pwmChannel = 0;
const int resolution = 8;
int pwmValue = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n=================================");
  Serial.println("    ESP32 SMART HOME CONTROLLER");
  Serial.println("=================================\n");
  
  // Setup pins
  pinMode(LIGHT_RELAY, OUTPUT);
  pinMode(FAN_RELAY, OUTPUT);
  pinMode(DOOR_SOLENOID, OUTPUT);
  pinMode(STATUS_LED, OUTPUT);
  pinMode(EXTRA_RELAY, OUTPUT);
  
  // Setup PWM for fan speed
  ledcSetup(pwmChannel, freq, resolution);
  ledcAttachPin(FAN_PWM, pwmChannel);
  
  // Initialize to safe state
  digitalWrite(LIGHT_RELAY, HIGH);     // HIGH = OFF (relay active LOW)
  digitalWrite(FAN_RELAY, HIGH);       // HIGH = OFF
  ledcWrite(pwmChannel, 0);            // Fan speed 0
  digitalWrite(DOOR_SOLENOID, LOW);    // LOW = LOCKED
  digitalWrite(STATUS_LED, LOW);
  digitalWrite(EXTRA_RELAY, HIGH);
  
  // Connect to WiFi
  connectToWiFi();
  
  // Get initial status
  delay(2000);
  fetchDeviceStatus();
}

void loop() {
  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected. Reconnecting...");
    digitalWrite(STATUS_LED, LOW);
    connectToWiFi();
    delay(5000);
    return;
  }
  
  // Blink LED based on connection status
  static unsigned long lastBlink = 0;
  if (connected) {
    if (millis() - lastBlink > 2000) {
      digitalWrite(STATUS_LED, !digitalRead(STATUS_LED));
      lastBlink = millis();
    }
  } else {
    if (millis() - lastBlink > 500) {
      digitalWrite(STATUS_LED, !digitalRead(STATUS_LED));
      lastBlink = millis();
    }
  }
  
  // Check for new commands from server
  if (millis() - lastCheck > checkInterval) {
    fetchDeviceStatus();
    lastCheck = millis();
  }
  
  delay(100);
}

void connectToWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    digitalWrite(STATUS_LED, !digitalRead(STATUS_LED));
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi Connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    digitalWrite(STATUS_LED, HIGH);
    connected = true;
  } else {
    Serial.println("\n❌ WiFi Failed!");
    connected = false;
  }
}

void fetchDeviceStatus() {
  if (WiFi.status() != WL_CONNECTED) {
    connected = false;
    return;
  }
  
  HTTPClient http;
  String url = String(serverUrl) + "/api/devices";
  
  http.begin(url);
  http.setTimeout(3000);
  
  int httpCode = http.GET();
  
  if (httpCode == HTTP_CODE_OK) {
    connected = true;
    String payload = http.getString();
    
    // Parse JSON response
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, payload);
    
    if (!error && doc["success"] == true) {
      JsonArray devices = doc["devices"];
      
      for (JsonObject device : devices) {
        String deviceName = device["device_name"].as<String>();
        String status = device["status"].as<String>();
        
        // Check if this is an auto command (from ML)
        bool isAutoCommand = false;
        if (status.indexOf("_auto") > 0) {
          isAutoCommand = true;
          status = status.substring(0, status.indexOf("_"));
        } else if (status.indexOf("_") > 0) {
          status = status.substring(0, status.indexOf("_"));
        }
        
        // Handle each device
        if (deviceName == "light") {
          if (status != lightState) {
            controlLight(status);
            lightState = status;
          }
        }
        else if (deviceName == "fan") {
          if (status != fanState) {
            controlFan(status);
            fanState = status;
          }
        }
        else if (deviceName == "fan_speed") {
          if (status != fanSpeed) {
            controlFanSpeed(status.toInt());
            fanSpeed = status;
          }
        }
        else if (deviceName == "door") {
          // Only process door command if status changed
          if (status != doorState) {
            // Check if it's an auto command from ML
            if (isAutoCommand) {
              Serial.println("🤖 Auto ML command detected for door");
              doorCommandFromAuto = true;
              lastDoorCommandTime = millis();
              
              // Execute the command
              if (status == "UNLOCKED") {
                unlockDoor(true); // true = isAuto command
              } else if (status == "LOCKED") {
                lockDoor(true); // true = isAuto command
              }
            } else {
              // Manual command - no autolock
              Serial.println("👤 Manual command detected for door");
              doorCommandFromAuto = false;
              
              // Execute the command (manual)
              if (status == "UNLOCKED") {
                unlockDoor(false); // false = manual command
              } else if (status == "LOCKED") {
                lockDoor(false); // false = manual command
              }
            }
            doorState = status;
          }
        }
      }
    }
  } else {
    connected = false;
    Serial.print("HTTP Error: ");
    Serial.println(httpCode);
  }
  
  http.end();
}

void controlLight(String status) {
  Serial.print("💡 Light: ");
  Serial.println(status);
  
  if (status == "ON") {
    digitalWrite(LIGHT_RELAY, LOW);   // Relay ON
  } else {
    digitalWrite(LIGHT_RELAY, HIGH);  // Relay OFF
  }
  
  blinkLED(2, 200);
  sendFeedback("light", status, false);
}

void controlFan(String status) {
  Serial.print("🌀 Fan: ");
  Serial.println(status);
  
  if (status == "ON") {
    digitalWrite(FAN_RELAY, LOW);     // Relay ON
    ledcWrite(pwmChannel, pwmValue);  // Restore speed
  } else {
    digitalWrite(FAN_RELAY, HIGH);    // Relay OFF
    ledcWrite(pwmChannel, 0);         // Speed 0
  }
  
  blinkLED(2, 200);
  sendFeedback("fan", status, false);
}

void controlFanSpeed(int speed) {
  Serial.print("🌀 Fan Speed: ");
  Serial.print(speed);
  Serial.println("%");
  
  // Convert percentage to PWM value (0-255)
  pwmValue = map(speed, 0, 100, 0, 255);
  
  // Only apply if fan is ON
  if (fanState == "ON") {
    ledcWrite(pwmChannel, pwmValue);
  }
  
  blinkLED(1, 100);
  sendFeedback("fan_speed", String(speed), false);
}

void unlockDoor(bool isAuto) {
  Serial.println("🚪 Door: UNLOCKING (Solenoid HIGH)");
  if (isAuto) {
    Serial.println("🤖 Auto ML UNLOCK command - will auto-lock after 5 seconds");
  } else {
    Serial.println("👤 Manual UNLOCK command - will stay unlocked until manually locked");
  }
  
  // Activate solenoid to unlock (HIGH = UNLOCK)
  digitalWrite(DOOR_SOLENOID, HIGH);
  
  // Update state immediately
  doorState = "UNLOCKED";
  
  blinkLED(3, 100);
  sendFeedback("door", "UNLOCKED", isAuto);
  
  Serial.println("✅ Door UNLOCKED - Solenoid Activated");
  
  // If this is an auto command, schedule auto-lock after 5 seconds
  if (isAuto) {
    Serial.println("⏰ Auto-lock scheduled in 5 seconds for ML command");
    delay(5000); // Wait 5 seconds
    lockDoor(true); // Auto-lock after delay
  }
}

void lockDoor(bool isAuto) {
  Serial.println("🚪 Door: LOCKING (Solenoid LOW)");
  if (isAuto) {
    Serial.println("🤖 Auto ML LOCK command");
  } else {
    Serial.println("👤 Manual LOCK command");
  }
  
  // Deactivate solenoid to lock (LOW = LOCK)
  digitalWrite(DOOR_SOLENOID, LOW);
  
  // Update state immediately
  doorState = "LOCKED";
  
  blinkLED(2, 100);
  sendFeedback("door", "LOCKED", isAuto);
  
  Serial.println("✅ Door LOCKED - Solenoid Deactivated");
}

void sendFeedback(String device, String status, bool isAuto) {
  if (WiFi.status() != WL_CONNECTED) return;
  
  HTTPClient http;
  String url = String(serverUrl) + "/api/device-feedback";
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  DynamicJsonDocument doc(256);
  doc["device"] = device;
  doc["status"] = status;
  doc["esp_id"] = WiFi.macAddress();
  doc["is_auto"] = isAuto;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  int httpCode = http.POST(jsonString);
  
  if (httpCode == HTTP_CODE_OK) {
    Serial.println("✅ Feedback sent to server");
  } else {
    Serial.print("❌ Feedback failed: ");
    Serial.println(httpCode);
  }
  
  http.end();
}

void blinkLED(int count, int delayTime) {
  for (int i = 0; i < count; i++) {
    digitalWrite(STATUS_LED, HIGH);
    delay(delayTime);
    digitalWrite(STATUS_LED, LOW);
    delay(delayTime);
  }
  digitalWrite(STATUS_LED, connected ? HIGH : LOW);
}