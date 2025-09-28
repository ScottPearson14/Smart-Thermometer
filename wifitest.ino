//This is wifitest file that goes on the arduino

#include <WiFi.h>
#include <HTTPClient.h>

// WiFi credentials
const char* ssid = "Hotspot";        // WiFi network name
const char* password = "NajeebNajeeb";              // WiFi password

// Python server details
const char* serverURL = "http://172.20.10.11:8080/data"; // Replace with your Mac's IP address

void setup() {
  Serial.begin(9600);
  delay(1000);
  
  Serial.println("Starting WiFi connection...");
  Serial.println("SSID: " + String(ssid));
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(1000);
    attempts++;
    Serial.println("Connecting to WiFi... Attempt " + String(attempts));
    Serial.println("Status: " + String(WiFi.status()));
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected!");
    Serial.print("ESP32 IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi connection failed!");
    Serial.println("Final status: " + String(WiFi.status()));
  }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");
    
    // Create test JSON data
    String jsonData = "{\"test_temp1\": 23.45, \"test_temp2\": 24.67, \"timestamp\": ";
    jsonData += millis();
    jsonData += "}";
    
    Serial.println("Sending data: " + jsonData);
    
    int httpResponseCode = http.POST(jsonData);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("HTTP Response code: " + String(httpResponseCode));
      Serial.println("Response: " + response);
    } else {
      Serial.println("Error on HTTP request: " + String(httpResponseCode));
    }
    
    http.end();
  } else {
    Serial.println("WiFi disconnected!");
  }
  
  delay(5000); // Send data every 5 seconds
}
