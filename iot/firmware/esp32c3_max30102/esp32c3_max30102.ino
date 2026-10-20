/*
 * PULSESURE: ESP32-C3 + MAX30102 (PPG sensor) firmware
 *
 * Flow:
 *   1. Read the IR channel from the MAX30102 at 100 Hz.
 *   2. Collect one 10-second window (1000 samples).
 *   3. Normalize to 0..1 and send it to the Go backend:
 *        POST http://<SERVER_IP>/api/measurements
 *
 * Library: "SparkFun MAX3010x Pulse and Proximity Sensor Library" (Arduino Library Manager).
 * Board:   ESP32-C3 (ESP32 Arduino core 2.x / 3.x).
 */
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include "MAX30105.h"   // SparkFun library, compatible with MAX30102

// ---------- configuration (change for your environment) ----------
const char* WIFI_SSID   = "YOUR_WIFI_NAME";
const char* WIFI_PASS   = "YOUR_WIFI_PASSWORD";
const char* API_URL     = "http://192.168.1.50/api/measurements";  // server IP or domain
const char* SESSION_ID  = "demo";   // must exist in backend/data (session_demo.json)

const uint16_t FS          = 100;     // Hz, must match the sensor setup() below
const uint16_t WINDOW      = 1000;    // 1000 samples / 100 Hz = 10 seconds
const uint32_t FINGER_MIN  = 30000;   // below this mean IR value, the finger is treated as absent

// I2C pins for ESP32-C3 (same as the CATTLEYE firmware). Change for your board.
const int PIN_SDA = 8;
const int PIN_SCL = 9;

// ---------- state ----------
MAX30105 sensor;
WiFiClient wifiClient;
uint32_t rawIR[WINDOW];
uint32_t windowID = 0;

void connectWiFi() {
  Serial.print("WiFi connecting");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(WiFi.status() == WL_CONNECTED ? " OK" : " FAILED (will retry in loop)");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());
  }
}

// Fill rawIR with exactly WINDOW samples from the sensor FIFO.
void collectWindow() {
  uint16_t n = 0;
  while (n < WINDOW) {
    sensor.check();                       // read the sensor FIFO
    while (sensor.available() && n < WINDOW) {
      rawIR[n++] = sensor.getFIFOIR();
      sensor.nextSample();
    }
  }
}

void sendWindow() {
  // 1. Compute the mean and min/max for finger detection and normalization.
  uint64_t sum = 0;
  uint32_t vmin = UINT32_MAX, vmax = 0;
  for (uint16_t i = 0; i < WINDOW; i++) {
    sum += rawIR[i];
    if (rawIR[i] < vmin) vmin = rawIR[i];
    if (rawIR[i] > vmax) vmax = rawIR[i];
  }
  uint32_t mean = sum / WINDOW;
  bool sensorOK = mean >= FINGER_MIN && vmax > vmin;

  // 2. Build the JSON body. If the sensor is not OK, send an empty samples array (backend rejects it).
  String body;
  body.reserve(WINDOW * 7 + 200);
  body += "{\"session_id\":\"";
  body += SESSION_ID;
  body += "\",\"window_id\":";
  body += String(windowID);
  body += ",\"fs\":";
  body += String(FS);
  body += ",\"source\":\"sensor\",\"sensor_ok\":";
  body += sensorOK ? "true" : "false";
  body += ",\"samples\":[";
  if (sensorOK) {
    float range = (float)(vmax - vmin);
    for (uint16_t i = 0; i < WINDOW; i++) {
      if (i) body += ',';
      body += String((float)(rawIR[i] - vmin) / range, 4);
    }
  }
  body += "]}";

  // 3. Send to the backend.
  HTTPClient http;
  http.begin(wifiClient, API_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(10000);
  int code = http.POST(body);
  Serial.printf("window %lu sensor_ok=%d -> HTTP %d\n",
                (unsigned long)windowID, sensorOK ? 1 : 0, code);
  if (code > 0) Serial.println(http.getString().substring(0, 200));
  http.end();
  windowID++;
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== PULSESURE ESP32-C3 + MAX30102 ===");

  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setTimeOut(50);

  if (!sensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30102 NOT DETECTED: check the I2C wiring and 3.3V power");
    while (true) delay(1000);
  }
  // ledPower, sampleAverage, ledMode (2 = red + IR), sampleRate, pulseWidth, adcRange
  sensor.setup(60, 4, 2, FS, 411, 4096);
  Serial.println("MAX30102 OK");

  connectWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    return;
  }
  collectWindow();
  sendWindow();
}
