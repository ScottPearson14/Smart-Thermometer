#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <OneWire.h>
#include <DallasTemperature.h>


#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 32 // OLED display height, in pixels
#define OLED_RESET     -1 // Reset pin # (or -1 if sharing Arduino reset pin)
#define SCREEN_ADDRESS 0x3C ///< See datasheet for Address; 0x3D for 128x64, 0x3C for 128x32
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);


// Button and switch pins
#define BUTTON1_PIN 34 // GPIO34 (D34)
#define BUTTON2_PIN 35 // GPIO35 (D35)
#define SWITCH_PIN 13  // GPIO13 (D13) - Display on/off switch


// Temperature sensor pins
#define TEMP_SENSOR1_PIN 2 // GPIO2 (D2)
#define TEMP_SENSOR2_PIN 4 // GPIO4 (D4)


// Setup OneWire instances for temperature sensors
OneWire oneWire1(TEMP_SENSOR1_PIN);
OneWire oneWire2(TEMP_SENSOR2_PIN);


// Pass OneWire references to Dallas Temperature sensors
DallasTemperature tempSensor1(&oneWire1);
DallasTemperature tempSensor2(&oneWire2);


// Sensor states
bool sensor1_enabled = false;
bool sensor2_enabled = false;
bool display_on = false; // Display on/off state


// Temperature variables
float temp1 = 0.0;
float temp2 = 0.0;
unsigned long lastTempRead = 0;
const unsigned long tempReadInterval = 1000; // Read temperature every 1 second


// Button state tracking for debouncing
bool button1_last_state = LOW;  // Changed to LOW since no internal pullup
bool button2_last_state = LOW;  // Changed to LOW since no internal pullup
unsigned long last_button1_time = 0;
unsigned long last_button2_time = 0;
const unsigned long debounce_delay = 200; // 200ms debounce


void setup() {
 Serial.begin(9600);


 // Initialize button pins as inputs (no pullup - GPIO34/35 are input-only pins)
 pinMode(BUTTON1_PIN, INPUT);
 pinMode(BUTTON2_PIN, INPUT);
  // Initialize switch pin with internal pull-down
 pinMode(SWITCH_PIN, INPUT_PULLDOWN);
  // Initialize temperature sensors
 tempSensor1.begin();
 tempSensor2.begin();
  Serial.println("Temperature sensors initialized");


 // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
 if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
   Serial.println(F("SSD1306 allocation failed"));
   for(;;); // Don't proceed, loop forever
 }


 // Initialize display
 updateDisplay();
}


void loop() {
 // Read temperature sensors periodically
 if (millis() - lastTempRead >= tempReadInterval) {
   readTemperatures();
   lastTempRead = millis();
 }
  // Check display switch state
 bool switch_current = digitalRead(SWITCH_PIN);
 if (switch_current != display_on) {
   display_on = switch_current;
   updateDisplay();
   Serial.print("Display switch: ");
   Serial.println(display_on ? "ON" : "OFF");
 }
  // Only check buttons if display is on
 if (display_on) {
   // Check button 1
   bool button1_current = digitalRead(BUTTON1_PIN);
   if (button1_current == HIGH && button1_last_state == LOW) {
     if (millis() - last_button1_time > debounce_delay) {
       sensor1_enabled = !sensor1_enabled; // Toggle sensor 1
       updateDisplay();
       last_button1_time = millis();
       Serial.println("Button 1 pressed - Sensor 1 toggled");
     }
   }
   button1_last_state = button1_current;
  
   // Check button 2
   bool button2_current = digitalRead(BUTTON2_PIN);
   if (button2_current == HIGH && button2_last_state == LOW) {
     if (millis() - last_button2_time > debounce_delay) {
       sensor2_enabled = !sensor2_enabled; // Toggle sensor 2
       updateDisplay();
       last_button2_time = millis();
       Serial.println("Button 2 pressed - Sensor 2 toggled");
     }
   }
   button2_last_state = button2_current;
 }
  delay(10); // Small delay to prevent excessive polling
}


void updateDisplay() {
 display.clearDisplay();
  // If display is off, just show a blank screen
 if (!display_on) {
   display.display();
   return;
 }
  // Set text properties
 display.setTextSize(1);
 display.setTextColor(SSD1306_WHITE);
  // Display sensor 1 in top half
 display.setCursor(0, 2);
 if (sensor1_enabled) {
   display.print(F("Sensor 1: "));
   display.print(temp1, 2); // 2 decimal places
   display.write(247); // Degree symbol (°)
   display.print(F("C"));
 } else {
   display.print(F("Sensor 1: OFF"));
 }
  // Draw horizontal line in the middle
 display.drawLine(0, 16, SCREEN_WIDTH-1, 16, SSD1306_WHITE);
  // Display sensor 2 in bottom half
 display.setCursor(0, 20);
 if (sensor2_enabled) {
   display.print(F("Sensor 2: "));
   display.print(temp2, 2); // 2 decimal places
   display.write(247); // Degree symbol (°)
   display.print(F("C"));
 } else {
   display.print(F("Sensor 2: OFF"));
 }
  // Update the display
 display.display();
}


void readTemperatures() {
 // Request temperatures from both sensors
 tempSensor1.requestTemperatures();
 tempSensor2.requestTemperatures();
  // Read temperatures (index 0 = first sensor on each bus)
 float newTemp1 = tempSensor1.getTempCByIndex(0);
 float newTemp2 = tempSensor2.getTempCByIndex(0);
  // Check for valid readings (-127 indicates error)
 if (newTemp1 != DEVICE_DISCONNECTED_C) {
   temp1 = newTemp1;
 }
 if (newTemp2 != DEVICE_DISCONNECTED_C) {
   temp2 = newTemp2;
 }
  // Update display if any sensor values changed and display is on
 if (display_on && (sensor1_enabled || sensor2_enabled)) {
   updateDisplay();
 }
  // Print to serial for debugging
 Serial.print("Temp1: ");
 Serial.print(temp1);
 Serial.print("°C, Temp2: ");
 Serial.print(temp2);
 Serial.println("°C");
}



