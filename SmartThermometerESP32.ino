// SmartThermometerESP32.ino
//
//   ESP32-based smart thermometer system with dual DS18B20 sensors, OLED 
//   display, and WiFi connectivity. Local buttons allow toggling sensors, 
//   while a hardware switch controls the display. Sensor data is read, 
//   displayed, and periodically sent to a Flask server in JSON format. 
//   The server can also send back remote state overrides.
//
// Dependencies:
//   Adafruit GFX & SSD1306 libraries
//   OneWire & DallasTemperature libraries
//   ArduinoJson library
//
// Group 11: Braden Miller, Kent Zdan, Scott Pearson, Xavier Uhrmacher
// Due: 10/03/2025

#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// =========================
// OLED DISPLAY
// =========================
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 32
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// =========================
// BUTTONS & SWITCH
// =========================
#define BUTTON1_PIN 35
#define BUTTON2_PIN 34
#define SWITCH_PIN 13

// =========================
// TEMPERATURE SENSORS
// =========================
#define TEMP_SENSOR1_PIN 2
#define TEMP_SENSOR2_PIN 4
OneWire oneWire1(TEMP_SENSOR1_PIN);
OneWire oneWire2(TEMP_SENSOR2_PIN);
DallasTemperature tempSensor1(&oneWire1);
DallasTemperature tempSensor2(&oneWire2);

// =========================
// SENSOR STATES
// =========================
bool sensor1_enabled = false;
bool sensor2_enabled = false;
bool display_on = false;
bool sensor1_disconnected = false;
bool sensor2_disconnected = false;

// =========================
// TEMPERATURE DATA
// =========================
float temp1 = 0.0;
float temp2 = 0.0;
unsigned long lastTempRead = 0;
const unsigned long tempReadInterval = 1000; // 1 sec

// =========================
// BUTTON DEBOUNCE
// =========================
bool button1_last_state = LOW;
bool button2_last_state = LOW;
unsigned long last_button1_time = 0;
unsigned long last_button2_time = 0;
const unsigned long debounce_delay = 200;

// =========================
// WIFI CONFIG
// =========================
const char* ssid = "Hotspot";       // <-- your SSID
const char* password = "NajeebNajeeb"; // <-- your password
const char* serverURL = "http://172.20.10.11:8080/data"; // <-- update to Flask IP

// =========================
// SETUP
// =========================
void setup() {
 Serial.begin(115200);

 // Button/switch setup
 pinMode(BUTTON1_PIN, INPUT);
 pinMode(BUTTON2_PIN, INPUT);
 pinMode(SWITCH_PIN, INPUT_PULLDOWN);

 // Init temp sensors
 tempSensor1.begin();
 tempSensor2.begin();
 Serial.println("Temperature sensors initialized");

 // Init display
 if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
   Serial.println(F("SSD1306 allocation failed"));
   for (;;) {}
 }
 updateDisplay();

 // Connect WiFi
 Serial.println("Connecting to WiFi...");
 WiFi.begin(ssid, password);
 int attempts = 0;
 while (WiFi.status() != WL_CONNECTED && attempts < 20) {
   delay(1000);
   attempts++;
   Serial.println("Connecting... attempt " + String(attempts));
 }
 if (WiFi.status() == WL_CONNECTED) {
   Serial.println("WiFi connected!");
   Serial.print("ESP32 IP: ");
   Serial.println(WiFi.localIP());
 } else {
   Serial.println("WiFi connection failed!");
 }
}

// =========================
// LOOP
// =========================
void loop() {
 unsigned long currentMillis = millis();

 // --- Check display switch immediately ---
 bool switch_current = digitalRead(SWITCH_PIN);
 if (switch_current != display_on) {
   display_on = switch_current;
   updateDisplay();
   Serial.print("Display switch: ");
   Serial.println(display_on ? "ON" : "OFF");
 }

 // --- Handle buttons quickly ---
 if (display_on) {
   bool button1_current = digitalRead(BUTTON1_PIN);
   if (button1_current == HIGH && button1_last_state == LOW) {
     if (millis() - last_button1_time > debounce_delay) {
       sensor1_enabled = !sensor1_enabled; // local physical toggle
       updateDisplay();
       last_button1_time = millis();
       Serial.println("Button 1 pressed - Sensor 1 toggled");
     }
   }
   button1_last_state = button1_current;

   bool button2_current = digitalRead(BUTTON2_PIN);
   if (button2_current == HIGH && button2_last_state == LOW) {
     if (millis() - last_button2_time > debounce_delay) {
       sensor2_enabled = !sensor2_enabled; // local physical toggle
       updateDisplay();
       last_button2_time = millis();
       Serial.println("Button 2 pressed - Sensor 2 toggled");
     }
   }
   button2_last_state = button2_current;
 }

 // --- Read temps + send data only once per second ---
 if (currentMillis - lastTempRead >= tempReadInterval) {
   readTemperatures();
   if (display_on) {   // only send if switch is ON
        sendData();
    }
   lastTempRead = currentMillis;
 }


 delay(5); // very small delay to avoid hogging CPU
}

// =========================
// DISPLAY
// =========================
void updateDisplay() {
  display.clearDisplay();

  if (!display_on) {
    display.display();
    return;
  }

  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  // --- Sensor 1 ---
  display.setCursor(0, 2);
  if (sensor1_enabled) {
    display.print(F("Sensor 1: "));
    if (sensor1_disconnected) {
      display.print(F("DISCONNECT"));
    } else {
      display.print(temp1, 2);
      display.write(247);
      display.print(F("C"));
    }
  } else {
    display.print(F("Sensor 1: OFF"));
  }

  display.drawLine(0, 16, SCREEN_WIDTH - 1, 16, SSD1306_WHITE);

  // --- Sensor 2 ---
  display.setCursor(0, 20);
  if (sensor2_enabled) {
    display.print(F("Sensor 2: "));
    if (sensor2_disconnected) {
      display.print(F("DISCONNECT"));
    } else {
      display.print(temp2, 2);
      display.write(247);
      display.print(F("C"));
    }
  } else {
    display.print(F("Sensor 2: OFF"));
  }

  display.display();
}

// =========================
// TEMPERATURE READ
// =========================
void readTemperatures() {
  tempSensor1.requestTemperatures();
  tempSensor2.requestTemperatures();

  float newTemp1 = tempSensor1.getTempCByIndex(0);
  float newTemp2 = tempSensor2.getTempCByIndex(0);

  if (newTemp1 != DEVICE_DISCONNECTED_C) {
    temp1 = newTemp1;
    sensor1_disconnected = false;
  } else {
    sensor1_disconnected = true;
  }

  if (newTemp2 != DEVICE_DISCONNECTED_C) {
    temp2 = newTemp2;
    sensor2_disconnected = false;
  } else {
    sensor2_disconnected = true;
  }

  if (display_on && (sensor1_enabled || sensor2_enabled)) {
    updateDisplay();
  }

  Serial.print("Temp1: ");
  if (sensor1_disconnected) Serial.print("DISCONNECT");
  else Serial.print(temp1);

  Serial.print("°C, Temp2: ");
  if (sensor2_disconnected) Serial.print("DISCONNECT");
  else Serial.print(temp2);

  Serial.println("°C");
}

// =========================
// SEND TO SERVER
// =========================
void sendData() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");

    // Build JSON string safely
    String jsonData = "{";

    if (sensor1_enabled && !sensor1_disconnected) {
      jsonData += "\"temp1\": " + String(temp1, 2) + ",";
    } else {
      jsonData += "\"temp1\": null,";
    }

    if (sensor2_enabled && !sensor2_disconnected) {
      jsonData += "\"temp2\": " + String(temp2, 2) + ",";
    } else {
      jsonData += "\"temp2\": null,";
    }

    jsonData += "\"sensor1\": " + String(sensor1_enabled ? "true" : "false") + ",";
    jsonData += "\"sensor2\": " + String(sensor2_enabled ? "true" : "false") + ",";

    jsonData += "\"timestamp\": " + String(millis());
    jsonData += "}";

    Serial.println("Sending data: " + jsonData);
    int httpResponseCode = http.POST(jsonData);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Response: " + response);

      // Parse server response JSON
      StaticJsonDocument<256> doc;
      DeserializationError err = deserializeJson(doc, response);
      if (!err) {
        bool desiredSensor1 = doc.containsKey("sensor1") ? doc["sensor1"].as<bool>() : sensor1_enabled;
        bool desiredSensor2 = doc.containsKey("sensor2") ? doc["sensor2"].as<bool>() : sensor2_enabled;
        bool desiredDisplayOn = doc.containsKey("display_on") ? doc["display_on"].as<bool>() : display_on;

        // Only apply remote states if display_on switch is ON
        if (display_on) {
          if (sensor1_enabled != desiredSensor1) {
            sensor1_enabled = desiredSensor1;
            Serial.print("Remote set sensor1_enabled -> ");
            Serial.println(sensor1_enabled ? "ON" : "OFF");
            updateDisplay();
          }
          if (sensor2_enabled != desiredSensor2) {
            sensor2_enabled = desiredSensor2;
            Serial.print("Remote set sensor2_enabled -> ");
            Serial.println(sensor2_enabled ? "ON" : "OFF");
            updateDisplay();
          }
        }

        if (desiredDisplayOn != display_on) {
          Serial.print("Server desired display_on = ");
          Serial.println(desiredDisplayOn ? "ON" : "OFF");
        }
      } else {
        Serial.print("JSON parse error: ");
        Serial.println(err.c_str());
      }
    } else {
      Serial.println("HTTP Error: " + String(httpResponseCode));
    }
    http.end();
  }
}
