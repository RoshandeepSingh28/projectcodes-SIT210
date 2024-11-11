#include <Wire.h>
#include <MPU6050.h>
#include <ArduinoMqttClient.h>
#include <WiFiNINA.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "oplus_co_apdmkd";
const char* password = "tohm3279";

// MQTT settings
const char* mqtt_broker = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* topic = "health/data";

// Sensor pins
const int PULSE_SENSOR_PIN = A0;
const int LM35_PIN = A1;
const int BUTTON_PIN = 6; // Button pin

// Constants
const float weight = 70.0;
const int numReadings = 10;
const float MIN_VALID_TEMP = 35.0; // Minimum valid temperature in °C
const float MAX_VALID_TEMP = 42.0; // Maximum valid temperature in °C
const int MIN_VALID_HEART_RATE = 40; // Minimum valid heart rate in BPM
const int MAX_VALID_HEART_RATE = 180; // Maximum valid heart rate in BPM

// Objects
MPU6050 mpu;
WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

// Variables
float temperature = 0.0;
int heartRate = 0;
float calories = 0.0;
bool beatDetected = false;
unsigned long lastBeatTime = 0;
int BPM = 0;
float tempReadings[10];
int readIndex = 0;
float tempTotal = 0;
unsigned long lastSendTime = 0;
const long interval = 1000;
bool sendDataEnabled = false; // Track whether data should be sent
bool lastButtonState = HIGH; // Last button state to detect changes
bool buttonPressed = false; // To debounce the button

void setup() {
    Serial.begin(9600);
    while (!Serial) {
        ; // Wait for serial port to connect
    }
    Serial.println("Smart Health Monitoring System Started");
    
    // Initialize WiFi
    connectWiFi();
    
    // Initialize MQTT
    connectMQTT();
    
    // Initialize MPU6050
    Wire.begin();
    mpu.initialize();
    
    // Initialize temperature readings array
    for (int i = 0; i < numReadings; i++) {
        tempReadings[i] = 0;
    }
    
    // Initialize pins
    pinMode(PULSE_SENSOR_PIN, INPUT);
    pinMode(LM35_PIN, INPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP); // Initialize button pin with pull-up resistor
}

void loop() {
    if (!mqttClient.connected()) {
        connectMQTT();
    }
    mqttClient.poll();

    // Read button state
    int buttonState = digitalRead(BUTTON_PIN);
    
    // Check for a button press (with debounce)
    if (buttonState == LOW && lastButtonState == HIGH) {
        delay(50); // Debounce delay
        buttonPressed = true;
    } else {
        buttonPressed = false;
    }
    
    // If the button was pressed, toggle the sendDataEnabled flag
    if (buttonPressed) {
        sendDataEnabled = !sendDataEnabled; // Toggle the flag
        Serial.print("Send data enabled: ");
        Serial.println(sendDataEnabled ? "ON" : "OFF");
    }

    lastButtonState = buttonState; // Update the last button state

    // If sending data is enabled, read and send data
    if (sendDataEnabled) {
        // Regular sensor readings
        readHeartRate();
        readTemperature();
        readMPU6050();

        // Send sensor data
        unsigned long currentMillis = millis();
        if (currentMillis - lastSendTime >= interval) {
            sendData();
            lastSendTime = currentMillis;
        }
    }
}

void connectWiFi() {
    Serial.print("Connecting to WiFi...");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nConnected to WiFi");
}

void connectMQTT() {
    Serial.print("Connecting to MQTT broker...");
    while (!mqttClient.connect(mqtt_broker, mqtt_port)) {
        delay(1000);
        Serial.print("...");
    }
    Serial.println("\nConnected to MQTT broker");
}

void readHeartRate() {
    int pulseValue = analogRead(PULSE_SENSOR_PIN);

    if (pulseValue > 550) { // Adjust threshold based on your sensor sensitivity
        unsigned long currentTime = millis();
        unsigned long elapsedTime = currentTime - lastBeatTime;

        if (elapsedTime > 250) { // Minimum time between beats to avoid double-counting
            BPM = 60000 / elapsedTime;
            if (BPM >= MIN_VALID_HEART_RATE && BPM <= MAX_VALID_HEART_RATE) {
                heartRate = BPM;
            }
            lastBeatTime = currentTime;
        }
    }
}

void readTemperature() {
    tempTotal -= tempReadings[readIndex];
    int reading = analogRead(LM35_PIN);
    float voltage = reading * (5.0 / 1023.0);
    float tempC = voltage * 100; // Convert voltage to Celsius (10 mV per °C)

    if (tempC >= MIN_VALID_TEMP && tempC <= MAX_VALID_TEMP) {
        tempReadings[readIndex] = tempC;
        tempTotal += tempReadings[readIndex];
        readIndex = (readIndex + 1) % numReadings;
        temperature = tempTotal / numReadings;
    } else {
        Serial.println("Temperature reading out of range. Discarded.");
    }
}

void readMPU6050() {
    int16_t ax, ay, az;
    mpu.getAcceleration(&ax, &ay, &az);
    
    float totalAccel = sqrt(ax * ax + ay * ay + az * az);
    float MET = 3.5;
    
    if (totalAccel > 2.0) {
        MET = 6.0;
    } else if (totalAccel > 1.0) {
        MET = 4.5;
    }
    
    calories = MET * weight * (1.0 / 3600.0);
}

void sendData() {
    StaticJsonDocument<200> doc;
    doc["heart_rate"] = heartRate;
    doc["temperature"] = temperature;
    doc["calories"] = calories;
    
    String jsonString;
    serializeJson(doc, jsonString);
    mqttClient.beginMessage(topic);
    mqttClient.print(jsonString);
    mqttClient.endMessage();
    
    Serial.println("Data sent: " + jsonString);
}
