/*
 * PulseSure: ESP32-C3 Super Mini + MAX30102 + MPU6050
 *
 * Flow:
 *   1. Read MAX30102 IR at 100 Hz for one 10-second window.
 *   2. Read MPU6050 directly through I2C registers (no MPU library).
 *   3. Send normalized PPG plus a compact motion summary to the Go backend.
 *
 * Required library: SparkFun MAX3010x Pulse and Proximity Sensor Library.
 * MPU6050 requires no external library.
 *
 * Wiring (both sensors share the I2C bus):
 *   ESP32-C3 3V3 -> MAX30102 VIN, MPU6050 VCC
 *   ESP32-C3 GND -> MAX30102 GND, MPU6050 GND
 *   ESP32-C3 GPIO8 -> MAX30102 SDA, MPU6050 SDA
 *   ESP32-C3 GPIO9 -> MAX30102 SCL, MPU6050 SCL
 *   MPU6050 AD0 -> GND (address 0x68); 0x69 is detected too.
 */
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include "MAX30105.h"   // SparkFun library, compatible with MAX30102

// ---------- network and backend ----------
const char* WIFI_SSID  = "jennjest";
const char* WIFI_PASS  = "13572468";
const char* API_URL    = "http://10.34.0.213:8080/api/measurements";
const char* SESSION_ID = "esp32c3-supermini-01";

const uint16_t FS             = 100;
const uint16_t WINDOW_SAMPLES = 1000;
const uint32_t FINGER_MIN     = 30000;
const uint32_t COLLECTION_TIMEOUT_MS = 20000;

const int PIN_SDA = 8;
const int PIN_SCL = 9;

// MPU6050 registers used directly over I2C.
const uint8_t MPU_ADDRESS_LOW  = 0x68;
const uint8_t MPU_ADDRESS_HIGH = 0x69;
const uint8_t MPU_REG_SMPLRT_DIV   = 0x19;
const uint8_t MPU_REG_CONFIG       = 0x1A;
const uint8_t MPU_REG_GYRO_CONFIG  = 0x1B;
const uint8_t MPU_REG_ACCEL_CONFIG = 0x1C;
const uint8_t MPU_REG_ACCEL_XOUT_H = 0x3B;
const uint8_t MPU_REG_PWR_MGMT_1   = 0x6B;
const uint8_t MPU_REG_WHO_AM_I     = 0x75;

const float MPU_ACCEL_LSB_PER_G = 16384.0f;  // +/- 2 g
const float MPU_GYRO_LSB_PER_DPS = 131.0f;   // +/- 250 deg/s
const float LOCAL_MOTION_GYRO_DPS = 12.0f;
const float LOCAL_MOTION_ACCEL_STEP_G = 0.035f;

// ---------- state ----------
MAX30105 sensor;
WiFiClient wifiClient;
uint32_t rawIR[WINDOW_SAMPLES];
uint32_t windowID = 0;
uint8_t mpuAddress = 0;
bool mpuReady = false;

struct MPUReading {
  int16_t ax;
  int16_t ay;
  int16_t az;
  int16_t gx;
  int16_t gy;
  int16_t gz;
};

struct MotionSummary {
  bool available;
  uint16_t samples;
  float accelStdG;
  float gyroRmsDPS;
  float accelPeakDeltaG;
  float motionFraction;
};

struct MotionAccumulator {
  uint16_t validSamples;
  uint16_t motionSamples;
  double accelSum;
  double accelSquareSum;
  double gyroSquareSum;
  float accelPeakDeltaG;
  float previousAccelMagnitude;
  bool hasPreviousAccel;
};

bool writeMPURegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(mpuAddress);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission(true) == 0;
}

bool readI2CBytes(uint8_t address, uint8_t reg, uint8_t* data, size_t length) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(address, (uint8_t)length, (uint8_t)true) != length) return false;
  for (size_t i = 0; i < length; i++) data[i] = Wire.read();
  return true;
}

bool readMPURegisterAt(uint8_t address, uint8_t reg, uint8_t& value) {
  return readI2CBytes(address, reg, &value, 1);
}

bool detectAndInitializeMPU6050() {
  uint8_t whoAmI = 0;
  const uint8_t addresses[2] = {MPU_ADDRESS_LOW, MPU_ADDRESS_HIGH};
  for (uint8_t index = 0; index < 2; index++) {
    const uint8_t address = addresses[index];
    if (readMPURegisterAt(address, MPU_REG_WHO_AM_I, whoAmI) && whoAmI == 0x68) {
      mpuAddress = address;
      break;
    }
  }
  if (mpuAddress == 0) return false;

  // Reset, select the X gyro PLL clock, then configure 100 Hz sampling,
  // DLPF=3, accelerometer +/-2 g, and gyroscope +/-250 deg/s.
  if (!writeMPURegister(MPU_REG_PWR_MGMT_1, 0x80)) return false;
  delay(100);
  if (!writeMPURegister(MPU_REG_PWR_MGMT_1, 0x01)) return false;
  if (!writeMPURegister(MPU_REG_CONFIG, 0x03)) return false;
  if (!writeMPURegister(MPU_REG_SMPLRT_DIV, 9)) return false;
  if (!writeMPURegister(MPU_REG_GYRO_CONFIG, 0x00)) return false;
  if (!writeMPURegister(MPU_REG_ACCEL_CONFIG, 0x00)) return false;
  delay(20);
  return true;
}

int16_t signedWord(const uint8_t* bytes) {
  return (int16_t)(((uint16_t)bytes[0] << 8) | bytes[1]);
}

bool readMPU6050(MPUReading& reading) {
  uint8_t data[14];
  if (!mpuReady || !readI2CBytes(mpuAddress, MPU_REG_ACCEL_XOUT_H, data, sizeof(data))) {
    return false;
  }
  reading.ax = signedWord(&data[0]);
  reading.ay = signedWord(&data[2]);
  reading.az = signedWord(&data[4]);
  // data[6..7] is temperature and is intentionally skipped.
  reading.gx = signedWord(&data[8]);
  reading.gy = signedWord(&data[10]);
  reading.gz = signedWord(&data[12]);
  return true;
}

void resetMotionAccumulator(MotionAccumulator& accumulator) {
  memset(&accumulator, 0, sizeof(accumulator));
}

void addMotionSample(MotionAccumulator& accumulator, const MPUReading& reading) {
  const float ax = reading.ax / MPU_ACCEL_LSB_PER_G;
  const float ay = reading.ay / MPU_ACCEL_LSB_PER_G;
  const float az = reading.az / MPU_ACCEL_LSB_PER_G;
  const float gx = reading.gx / MPU_GYRO_LSB_PER_DPS;
  const float gy = reading.gy / MPU_GYRO_LSB_PER_DPS;
  const float gz = reading.gz / MPU_GYRO_LSB_PER_DPS;

  const float accelMagnitude = sqrtf(ax * ax + ay * ay + az * az);
  const float gyroMagnitude = sqrtf(gx * gx + gy * gy + gz * gz);
  const float peakDelta = fabsf(accelMagnitude - 1.0f);

  accumulator.validSamples++;
  accumulator.accelSum += accelMagnitude;
  accumulator.accelSquareSum += accelMagnitude * accelMagnitude;
  accumulator.gyroSquareSum += gyroMagnitude * gyroMagnitude;
  accumulator.accelPeakDeltaG = max(accumulator.accelPeakDeltaG, peakDelta);

  const bool accelerationStep = accumulator.hasPreviousAccel &&
      fabsf(accelMagnitude - accumulator.previousAccelMagnitude) >= LOCAL_MOTION_ACCEL_STEP_G;
  if (accelerationStep || gyroMagnitude >= LOCAL_MOTION_GYRO_DPS) {
    accumulator.motionSamples++;
  }
  accumulator.previousAccelMagnitude = accelMagnitude;
  accumulator.hasPreviousAccel = true;
}

MotionSummary finishMotionSummary(const MotionAccumulator& accumulator) {
  MotionSummary summary = {};
  summary.available = mpuReady && accumulator.validSamples > 0;
  summary.samples = accumulator.validSamples;
  if (!summary.available) return summary;

  const double count = accumulator.validSamples;
  const double accelMean = accumulator.accelSum / count;
  const double accelVariance = max(0.0, accumulator.accelSquareSum / count - accelMean * accelMean);
  summary.accelStdG = sqrt(accelVariance);
  summary.gyroRmsDPS = sqrt(accumulator.gyroSquareSum / count);
  summary.accelPeakDeltaG = accumulator.accelPeakDeltaG;
  summary.motionFraction = (float)accumulator.motionSamples / accumulator.validSamples;
  return summary;
}

void scanI2CBus() {
  Serial.println("I2C scan:");
  for (uint8_t address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  found 0x%02X\n", address);
    }
  }
}

void WiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
  switch (event) {
    case ARDUINO_EVENT_WIFI_STA_CONNECTED:
      Serial.println("[EVENT] Connected to access point");
      break;
    case ARDUINO_EVENT_WIFI_STA_GOT_IP:
      Serial.print("[EVENT] Got IP: ");
      Serial.println(WiFi.localIP());
      break;
    case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
      Serial.print("[EVENT] Disconnected! Reason code: ");
      Serial.println(info.wifi_sta_disconnected.reason);
      break;
    default:
      break;
  }
}

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("Connecting to %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  const uint32_t startedAt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startedAt < 20000) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf(" OK, RSSI=%d dBm\n", WiFi.RSSI());
    Serial.print("Backend: ");
    Serial.println(API_URL);
  } else {
    Serial.println(" FAILED; retrying after the next loop.");
  }
}

// Collect one synchronized 10-second PPG and motion window.
bool collectWindow(MotionSummary& motion) {
  uint16_t ppgSamples = 0;
  uint16_t imuTicks = 0;
  MotionAccumulator accumulator;
  resetMotionAccumulator(accumulator);

  const uint32_t startedAt = millis();
  uint32_t nextIMUAt = micros();
  const uint32_t imuPeriodUs = 1000000UL / FS;

  while (ppgSamples < WINDOW_SAMPLES || (mpuReady && imuTicks < WINDOW_SAMPLES)) {
    if (ppgSamples < WINDOW_SAMPLES) {
      sensor.check();
      while (sensor.available() && ppgSamples < WINDOW_SAMPLES) {
        rawIR[ppgSamples++] = sensor.getFIFOIR();
        sensor.nextSample();
      }
    }

    const uint32_t now = micros();
    if (mpuReady && imuTicks < WINDOW_SAMPLES && (int32_t)(now - nextIMUAt) >= 0) {
      MPUReading reading;
      if (readMPU6050(reading)) addMotionSample(accumulator, reading);
      imuTicks++;
      nextIMUAt += imuPeriodUs;
      if ((int32_t)(now - nextIMUAt) > (int32_t)(2 * imuPeriodUs)) {
        nextIMUAt = now + imuPeriodUs;
      }
    }

    if (millis() - startedAt >= COLLECTION_TIMEOUT_MS) {
      Serial.println("Collection timeout: incomplete MAX30102 window");
      break;
    }
    delay(1);
  }

  motion = finishMotionSummary(accumulator);
  Serial.printf("Collected PPG=%u/%u, MPU=%u, elapsed=%lu ms\n",
                ppgSamples, WINDOW_SAMPLES, motion.samples,
                (unsigned long)(millis() - startedAt));
  return ppgSamples == WINDOW_SAMPLES;
}

void sendWindow(const MotionSummary& motion, bool ppgComplete) {
  // 1. Compute the mean and min/max for finger detection and normalization.
  uint64_t sum = 0;
  uint32_t vmin = UINT32_MAX, vmax = 0;
  for (uint16_t i = 0; i < WINDOW_SAMPLES; i++) {
    sum += rawIR[i];
    if (rawIR[i] < vmin) vmin = rawIR[i];
    if (rawIR[i] > vmax) vmax = rawIR[i];
  }
  uint32_t mean = sum / WINDOW_SAMPLES;
  bool sensorOK = ppgComplete && mean >= FINGER_MIN && vmax > vmin;

  // 2. Build the JSON body. If the sensor is not OK, send an empty samples array (backend rejects it).
  String body;
  body.reserve(WINDOW_SAMPLES * 8 + 600);
  body += "{\"session_id\":\"";
  body += SESSION_ID;
  body += "\",\"window_id\":";
  body += String(windowID);
  body += ",\"fs\":";
  body += String(FS);
  body += ",\"source\":\"sensor\",\"sensor_ok\":";
  body += sensorOK ? "true" : "false";
  body += ",\"motion\":{\"available\":";
  body += motion.available ? "true" : "false";
  body += ",\"sample_rate_hz\":";
  body += String(FS);
  body += ",\"samples\":";
  body += String(motion.samples);
  body += ",\"accel_std_g\":";
  body += String(motion.accelStdG, 5);
  body += ",\"gyro_rms_dps\":";
  body += String(motion.gyroRmsDPS, 3);
  body += ",\"accel_peak_delta_g\":";
  body += String(motion.accelPeakDeltaG, 5);
  body += ",\"motion_fraction\":";
  body += String(motion.motionFraction, 5);
  body += "},\"samples\":[";
  if (sensorOK) {
    float range = (float)(vmax - vmin);
    for (uint16_t i = 0; i < WINDOW_SAMPLES; i++) {
      if (i) body += ',';
      body += String((float)(rawIR[i] - vmin) / range, 4);
    }
  }
  body += "]}";

  // 3. Send to the backend.
  HTTPClient http;
  if (!http.begin(wifiClient, API_URL)) {
    Serial.println("HTTP begin failed");
    windowID++;
    return;
  }
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(30000);
  int code = http.POST(body);
  Serial.printf("window=%lu sensor_ok=%d motion=%d heap=%lu -> HTTP %d\n",
                (unsigned long)windowID, sensorOK ? 1 : 0,
                motion.motionFraction >= 0.10f ? 1 : 0,
                (unsigned long)ESP.getFreeHeap(), code);
  if (code > 0) {
    Serial.println(http.getString().substring(0, 500));
  } else {
    Serial.printf("HTTP error: %s\n", http.errorToString(code).c_str());
  }
  http.end();
  windowID++;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== PulseSure ESP32-C3 + MAX30102 + MPU6050 ===");

  WiFi.onEvent(WiFiEvent);

  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(400000);
  Wire.setTimeOut(50);
  scanI2CBus();

  if (!sensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println("MAX30102 NOT DETECTED: check the I2C wiring and 3.3V power");
    while (true) delay(1000);
  }
  // sampleAverage=1 is required so the FIFO really supplies 100 records/s.
  // ledPower, sampleAverage, ledMode (2=red+IR), rate, width, ADC range.
  sensor.setup(60, 1, 2, FS, 411, 4096);
  sensor.clearFIFO();
  Serial.println("MAX30102 OK at address 0x57, 100 Hz");

  mpuReady = detectAndInitializeMPU6050();
  if (mpuReady) {
    Serial.printf("MPU6050 OK at address 0x%02X, manual register mode\n", mpuAddress);
  } else {
    Serial.println("MPU6050 NOT DETECTED; PPG will continue without motion context");
  }

  connectWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    return;
  }
  MotionSummary motion;
  const bool ppgComplete = collectWindow(motion);
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
  if (WiFi.status() == WL_CONNECTED) {
    sendWindow(motion, ppgComplete);
  } else {
    Serial.println("Window dropped because WiFi is disconnected");
    windowID++;
  }
}
