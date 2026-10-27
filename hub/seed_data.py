"""Seed content for ElectroLab. YouTube IDs point to real public tutorials."""

RED, BLK, GRN, YEL, BLU, ORG, WHT = "#ef4444", "#94a3b8", "#22c55e", "#facc15", "#38bdf8", "#fb923c", "#e2e8f0"

CATEGORIES = [
    ("iot", "IoT & Wi-Fi", "📡", "Connected devices, dashboards and web servers"),
    ("sensors", "Sensors", "🌡️", "Measure the physical world"),
    ("camera", "Camera & Vision", "📷", "Streaming, security and image projects"),
    ("automation", "Automation", "🏠", "Relays, pumps and smart control"),
    ("micropython", "MicroPython", "🐍", "Python on microcontrollers"),
]

# ------------------------------------------------------------------------------------------------
ESP32_DHT_INO = r'''#include <WiFi.h>
#include <WebServer.h>
#include <DHT.h>          // Library: "DHT sensor library" by Adafruit (+ Adafruit Unified Sensor)

#define DHTPIN  4         // DATA pin of the DHT22 -> GPIO4
#define DHTTYPE DHT22     // change to DHT11 if you have the blue sensor

const char* ssid     = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";

DHT dht(DHTPIN, DHTTYPE);
WebServer server(80);

float lastT = NAN, lastH = NAN;
unsigned long lastRead = 0;

void readSensor() {
  if (lastRead && millis() - lastRead < 2000) return;   // DHT22 max rate: 0.5 Hz
  lastRead = millis();
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (!isnan(h) && !isnan(t)) { lastT = t; lastH = h; }
}

void handleData() {
  readSensor();
  String json = "{\"temperature\":" + String(lastT, 1) + ",\"humidity\":" + String(lastH, 1) + "}";
  server.send(200, "application/json", json);
}

const char PAGE[] PROGMEM = R"rawliteral(
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32 Climate</title>
<style>body{font-family:system-ui;background:#0b1220;color:#e2e8f0;text-align:center;padding-top:40px}
.v{font-size:64px;font-weight:700;color:#22d3ee}.c{display:inline-block;margin:12px;padding:20px 36px;background:#131c30;border-radius:16px}</style></head>
<body><h1>ESP32 Climate Station</h1>
<div class="c"><div class="v" id="t">--</div>&deg;C</div>
<div class="c"><div class="v" id="h">--</div>% RH</div>
<script>
async function tick(){const d=await (await fetch('/data')).json();
t.textContent=d.temperature;h.textContent=d.humidity;}
tick();setInterval(tick,2000);
</script></body></html>
)rawliteral";

void setup() {
  Serial.begin(115200);
  dht.begin();
  WiFi.begin(ssid, password);
  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println();
  Serial.print("Open http://"); Serial.println(WiFi.localIP());

  server.on("/", []() { server.send_P(200, "text/html", PAGE); });
  server.on("/data", handleData);
  server.begin();
}

void loop() {
  server.handleClient();
}
'''

ESP32_DHT_PY = r'''"""Poll the ESP32 every 10 s and log readings to climate_log.csv.
Usage:  python logger.py 192.168.1.50
"""
import csv
import json
import sys
import time
import urllib.request
from datetime import datetime

ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.50"

with open("climate_log.csv", "a", newline="") as f:
    writer = csv.writer(f)
    while True:
        try:
            data = json.load(urllib.request.urlopen(f"http://{ip}/data", timeout=5))
            writer.writerow([datetime.now().isoformat(timespec="seconds"), data["temperature"], data["humidity"]])
            f.flush()
            print(data)
        except Exception as exc:
            print("read failed:", exc)
        time.sleep(10)
'''

ULTRA_INO = r'''// Arduino Ultrasonic Distance Meter with proximity buzzer
const int TRIG_PIN   = 9;
const int ECHO_PIN   = 10;
const int BUZZER_PIN = 8;

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
}

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);          // 10 microsecond trigger pulse
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);   // echo time in microseconds (30 ms timeout)
  if (duration == 0) return -1;          // nothing detected
  return duration * 0.0343 / 2.0;        // speed of sound = 343 m/s, there and back
}

void loop() {
  float cm = readDistanceCm();
  Serial.print("Distance: ");
  if (cm < 0) Serial.println("out of range");
  else { Serial.print(cm, 1); Serial.println(" cm"); }

  if (cm > 0 && cm < 30) {
    tone(BUZZER_PIN, 2000, 40);          // beep faster as you get closer
    delay(map((long)cm, 2, 30, 40, 400));
  } else {
    noTone(BUZZER_PIN);
    delay(100);
  }
}
'''

CAM_INO = r'''// ESP32-CAM (AI-Thinker) live MJPEG stream + PIR motion flag
// Board: "AI Thinker ESP32-CAM", PSRAM: Enabled.  Stream: http://<ip>:81/stream   Status: http://<ip>/motion
#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"

const char* ssid     = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";

#define PIR_PIN    13
#define FLASH_LED   4

// AI-Thinker pin map
#define PWDN_GPIO_NUM  32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM   0
#define SIOD_GPIO_NUM  26
#define SIOC_GPIO_NUM  27
#define Y9_GPIO_NUM    35
#define Y8_GPIO_NUM    34
#define Y7_GPIO_NUM    39
#define Y6_GPIO_NUM    36
#define Y5_GPIO_NUM    21
#define Y4_GPIO_NUM    19
#define Y3_GPIO_NUM    18
#define Y2_GPIO_NUM     5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM  23
#define PCLK_GPIO_NUM  22

httpd_handle_t web_httpd = NULL;
httpd_handle_t stream_httpd = NULL;
volatile unsigned long lastMotion = 0;

static esp_err_t stream_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
  char part[64];
  while (true) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) return ESP_FAIL;
    size_t hlen = snprintf(part, sizeof(part), "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len);
    esp_err_t res = httpd_resp_send_chunk(req, "\r\n--frame\r\n", 11);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, part, hlen);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    if (res != ESP_OK) break;            // client disconnected
  }
  return ESP_OK;
}

static esp_err_t motion_handler(httpd_req_t *req) {
  char buf[64];
  bool recent = lastMotion && (millis() - lastMotion < 5000);
  snprintf(buf, sizeof(buf), "{\"motion\":%s}", recent ? "true" : "false");
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_sendstr(req, buf);
}

void IRAM_ATTR onMotion() { lastMotion = millis(); }

void startServers() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  httpd_uri_t motion_uri = { "/motion", HTTP_GET, motion_handler, NULL };
  if (httpd_start(&web_httpd, &config) == ESP_OK) httpd_register_uri_handler(web_httpd, &motion_uri);

  config.server_port = 81;
  config.ctrl_port += 1;
  httpd_uri_t stream_uri = { "/stream", HTTP_GET, stream_handler, NULL };
  if (httpd_start(&stream_httpd, &config) == ESP_OK) httpd_register_uri_handler(stream_httpd, &stream_uri);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIR_PIN, INPUT);
  pinMode(FLASH_LED, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(PIR_PIN), onMotion, RISING);

  camera_config_t c;
  c.ledc_channel = LEDC_CHANNEL_0;  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM; c.pin_d1 = Y3_GPIO_NUM; c.pin_d2 = Y4_GPIO_NUM; c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM; c.pin_d5 = Y7_GPIO_NUM; c.pin_d6 = Y8_GPIO_NUM; c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM; c.pin_pclk = PCLK_GPIO_NUM; c.pin_vsync = VSYNC_GPIO_NUM;
  c.pin_href = HREF_GPIO_NUM; c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM; c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_VGA; c.jpeg_quality = 12; c.fb_count = 2;
  c.grab_mode = CAMERA_GRAB_LATEST; c.fb_location = CAMERA_FB_IN_PSRAM;

  if (esp_camera_init(&c) != ESP_OK) { Serial.println("Camera init failed"); return; }

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  startServers();
  Serial.printf("\nStream: http://%s:81/stream\n", WiFi.localIP().toString().c_str());
}

void loop() {
  // Light the on-board flash LED briefly after motion
  digitalWrite(FLASH_LED, (lastMotion && millis() - lastMotion < 1500) ? HIGH : LOW);
  delay(50);
}
'''

PICO_PY = r'''# Raspberry Pi Pico - Traffic light with pedestrian button (MicroPython)
from machine import Pin
import time

red = Pin(15, Pin.OUT)
amber = Pin(14, Pin.OUT)
green = Pin(13, Pin.OUT)
button = Pin(12, Pin.IN, Pin.PULL_DOWN)
buzzer = Pin(11, Pin.OUT)

walk_requested = False


def on_button(pin):
    global walk_requested
    walk_requested = True


button.irq(trigger=Pin.IRQ_RISING, handler=on_button)


def lights(r=0, a=0, g=0):
    red.value(r)
    amber.value(a)
    green.value(g)


def beep(times, ms=100):
    for _ in range(times):
        buzzer.value(1)
        time.sleep_ms(ms)
        buzzer.value(0)
        time.sleep_ms(ms)


while True:
    # Cars: GO
    lights(g=1)
    for _ in range(50):                  # 5 s, but react to the button
        if walk_requested:
            break
        time.sleep_ms(100)

    # Cars: prepare to stop
    lights(a=1)
    time.sleep(2)

    # Cars: STOP
    lights(r=1)
    if walk_requested:
        beep(8, 150)                     # pedestrians cross
        walk_requested = False
    else:
        time.sleep(4)

    # Red + amber: prepare to go
    lights(r=1, a=1)
    time.sleep(1.5)
'''

PICO_PWM_PY = r'''# Bonus: smooth "breathing" amber light using PWM
from machine import Pin, PWM
import time

amber = PWM(Pin(14))
amber.freq(1000)

while True:
    for duty in range(0, 65535, 1024):
        amber.duty_u16(duty)
        time.sleep_ms(15)
    for duty in range(65535, 0, -1024):
        amber.duty_u16(duty)
        time.sleep_ms(15)
'''

PLANT_INO = r'''// Automatic Plant Watering - Arduino Uno + soil moisture sensor + relay + pump
const int SOIL_PIN  = A0;
const int RELAY_PIN = 7;            // relay module is ACTIVE-LOW (LOW = pump ON)

const int DRY_VALUE = 620;          // calibrate: reading with sensor in dry air
const int WET_VALUE = 280;          // calibrate: reading with sensor in a glass of water
const int WATER_BELOW_PERCENT = 35; // start watering under this moisture %
const unsigned long PUMP_MS   = 4000;     // water for 4 s
const unsigned long COOLDOWN  = 600000UL; // wait 10 min to let water soak in

unsigned long lastWatered = 0;

int moisturePercent() {
  int raw = analogRead(SOIL_PIN);
  return constrain(map(raw, DRY_VALUE, WET_VALUE, 0, 100), 0, 100);
}

void setup() {
  Serial.begin(9600);
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH);    // pump OFF at boot
}

void loop() {
  int pct = moisturePercent();
  Serial.print("Soil moisture: "); Serial.print(pct); Serial.println(" %");

  bool ready = (lastWatered == 0) || (millis() - lastWatered > COOLDOWN);
  if (pct < WATER_BELOW_PERCENT && ready) {
    Serial.println("Dry soil -> watering");
    digitalWrite(RELAY_PIN, LOW);
    delay(PUMP_MS);
    digitalWrite(RELAY_PIN, HIGH);
    lastWatered = millis();
  }
  delay(2000);
}
'''

RELAY_INO = r'''// ESP32 Wi-Fi relay controller (4 channels)  -  http://<ip>/  toggles each channel
#include <WiFi.h>
#include <WebServer.h>

const char* ssid     = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";

const int RELAY_PINS[4] = {26, 27, 14, 12};
bool state[4] = {false, false, false, false};
const bool ACTIVE_LOW = true;       // most relay boards: LOW = ON

WebServer server(80);

void apply(int i) { digitalWrite(RELAY_PINS[i], (state[i] ^ ACTIVE_LOW) ? HIGH : LOW); }

String page() {
  String h = "<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'>"
             "<style>body{font-family:system-ui;background:#0b1220;color:#e2e8f0;text-align:center}"
             "a{display:block;margin:14px auto;max-width:320px;padding:18px;border-radius:14px;"
             "text-decoration:none;color:#fff;font-weight:700}.on{background:#16a34a}.off{background:#475569}</style>"
             "<h1>Relay Control</h1>";
  for (int i = 0; i < 4; i++) {
    h += "<a class='" + String(state[i] ? "on" : "off") + "' href='/toggle?ch=" + String(i) + "'>Channel " +
         String(i + 1) + ": " + (state[i] ? "ON" : "OFF") + "</a>";
  }
  return h;
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) { pinMode(RELAY_PINS[i], OUTPUT); apply(i); }
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println(WiFi.localIP());

  server.on("/", []() { server.send(200, "text/html", page()); });
  server.on("/toggle", []() {
    int ch = server.arg("ch").toInt();
    if (ch >= 0 && ch < 4) { state[ch] = !state[ch]; apply(ch); }
    server.sendHeader("Location", "/");
    server.send(303);
  });
  server.begin();
}

void loop() { server.handleClient(); }
'''

# ------------------------------------------------------------------------------------------------
PROJECTS = [
    dict(
        slug="esp32-dht22-web-monitor", category="iot", board="ESP32", featured=True,
        title="ESP32 Temperature & Humidity Web Monitor",
        summary="Serve a live climate dashboard from an ESP32 and read it from any phone on your Wi-Fi.",
        description=("Build a self-hosted weather station: an ESP32 reads a DHT22 sensor and serves both a live web "
                     "dashboard and a JSON endpoint. A Python logger then records the data to CSV — a perfect first "
                     "step into IoT, HTTP servers and data logging."),
        difficulty="beginner", build_minutes=30, cost_usd=14,
        tags="esp32, dht22, wifi, web server, temperature, humidity, iot, json",
        youtube_id="JXCcmZUmzy8", video_credit="Measure Temperature and Humidity over WiFi with ESP32 + DHT11/DHT22 (Robojax)",
        safety_note="",
        components=[("ESP32 DevKit V1", 1, "any 30-pin ESP32 board"), ("DHT22 (AM2302) sensor", 1, "or DHT11"),
                    ("10 kΩ resistor", 1, "pull-up on the data line"), ("Breadboard", 1, ""),
                    ("Jumper wires", 5, "male-to-male"), ("Micro-USB cable", 1, "data-capable")],
        connections=[("ESP32", "3V3", "DHT22", "VCC (pin 1)", RED, "Power, 3.3 V"),
                     ("ESP32", "GPIO4", "DHT22", "DATA (pin 2)", GRN, "Single-wire data"),
                     ("ESP32", "GND", "DHT22", "GND (pin 4)", BLK, "Common ground"),
                     ("ESP32", "3V3", "10k Resistor", "Leg A", RED, "Pull-up to 3V3"),
                     ("ESP32", "GPIO4", "10k Resistor", "Leg B", GRN, "Pull-up joins data line")],
        steps=[("Install the toolchain", "Install the Arduino IDE, then add ESP32 support via Boards Manager (Espressif Systems)."),
               ("Install libraries", "Library Manager → install “DHT sensor library” and “Adafruit Unified Sensor”."),
               ("Wire the sensor", "Follow the Connections tab. Place the 10 kΩ resistor between DATA and 3V3."),
               ("Edit credentials", "Replace YOUR_WIFI_NAME and YOUR_WIFI_PASSWORD in the sketch (2.4 GHz network)."),
               ("Upload & open", "Select “ESP32 Dev Module”, upload, open Serial Monitor at 115200 and browse to the printed IP."),
               ("Log to CSV (optional)", "Run `python logger.py <esp32-ip>` on any computer to save readings every 10 s.")],
        code=[("esp32_dht22_server.ino", "cpp", "Arduino sketch: Wi-Fi web server, dashboard and /data JSON API", ESP32_DHT_INO),
              ("logger.py", "python", "Python client that logs the readings to climate_log.csv", ESP32_DHT_PY)],
    ),
    dict(
        slug="arduino-ultrasonic-distance-meter", category="sensors", board="Arduino Uno",
        title="Arduino Ultrasonic Distance Meter + Parking Beeper",
        summary="Measure distance with an HC-SR04 and beep faster as an object gets closer.",
        description=("Learn how time-of-flight works: the HC-SR04 sends a 40 kHz burst and times the echo. "
                     "This project converts echo time to centimetres, prints it to the Serial Monitor and drives a "
                     "buzzer like a car parking sensor."),
        difficulty="beginner", build_minutes=20, cost_usd=8,
        tags="arduino, hc-sr04, ultrasonic, distance, sensor, buzzer, parking",
        youtube_id="nkSUFV7gCNU", video_credit="Ultrasonic Distance Sensor HC-SR04 – Arduino tutorial #7",
        components=[("Arduino Uno R3", 1, "or Nano"), ("HC-SR04 ultrasonic sensor", 1, ""),
                    ("Active buzzer", 1, "5 V"), ("Breadboard", 1, ""), ("Jumper wires", 6, "")],
        connections=[("Arduino Uno", "5V", "HC-SR04", "VCC", RED, "Sensor needs 5 V"),
                     ("Arduino Uno", "D9", "HC-SR04", "TRIG", YEL, "Trigger pulse out"),
                     ("Arduino Uno", "D10", "HC-SR04", "ECHO", BLU, "Echo time in"),
                     ("Arduino Uno", "GND", "HC-SR04", "GND", BLK, ""),
                     ("Arduino Uno", "D8", "Buzzer", "+", ORG, "Tone output"),
                     ("Arduino Uno", "GND", "Buzzer", "−", BLK, "")],
        steps=[("Understand the sensor", "Trigger = 10 µs pulse. Echo stays HIGH for the round-trip time. Distance = time × 0.0343 / 2 cm."),
               ("Wire the circuit", "Connect VCC/GND, then TRIG→D9 and ECHO→D10. Add the buzzer on D8."),
               ("Upload the sketch", "Select Arduino Uno + the right COM port, then upload."),
               ("Test", "Open Serial Monitor (9600). Move your hand toward the sensor — beeps get faster below 30 cm."),
               ("Improve", "Average 5 readings to reduce jitter or add an LCD/OLED for display.")],
        code=[("ultrasonic_meter.ino", "cpp", "Distance measurement with proximity buzzer", ULTRA_INO)],
    ),
    dict(
        slug="esp32-cam-security-camera", category="camera", board="ESP32-CAM", featured=True,
        title="ESP32-CAM Security Camera with Motion Sensor",
        summary="Live MJPEG video stream plus a PIR motion flag — a tiny Wi-Fi security camera.",
        description=("Turn a $8 ESP32-CAM into a Wi-Fi security camera. It streams VGA video over HTTP, exposes a "
                     "/motion JSON endpoint driven by a PIR sensor, and flashes the on-board LED on movement. "
                     "Pair it with the AI Lab troubleshooter if your camera won't initialise."),
        difficulty="intermediate", build_minutes=60, cost_usd=22,
        tags="esp32-cam, camera, streaming, mjpeg, security, pir, motion, wifi, surveillance, iot",
        youtube_id="mdaM53qIYgk", video_credit="ESP32-CAM Security System: Motion Detection + Phone Alerts Tutorial",
        safety_note="Use only on your own property and respect privacy laws. Power with a stable 5 V ≥1 A supply.",
        components=[("ESP32-CAM (AI-Thinker)", 1, "with OV2640 camera"), ("FTDI USB-to-serial adapter", 1, "3.3 V logic, for flashing"),
                    ("HC-SR501 PIR sensor", 1, ""), ("5 V 1 A power supply", 1, ""), ("Jumper wires", 8, "female-to-female")],
        connections=[("FTDI", "TX", "ESP32-CAM", "U0R", GRN, "Flashing only"),
                     ("FTDI", "RX", "ESP32-CAM", "U0T", BLU, "Flashing only"),
                     ("FTDI", "5V", "ESP32-CAM", "5V", RED, ""),
                     ("FTDI", "GND", "ESP32-CAM", "GND", BLK, ""),
                     ("ESP32-CAM", "GPIO0", "ESP32-CAM", "GND", ORG, "Bridge to GND to enter flash mode"),
                     ("PIR HC-SR501", "OUT", "ESP32-CAM", "GPIO13", YEL, "Motion signal"),
                     ("PIR HC-SR501", "VCC", "ESP32-CAM", "5V", RED, ""),
                     ("PIR HC-SR501", "GND", "ESP32-CAM", "GND", BLK, "")],
        steps=[("Prepare the IDE", "Install ESP32 boards; choose “AI Thinker ESP32-CAM” and enable PSRAM."),
               ("Enter flash mode", "Wire the FTDI adapter as shown and bridge GPIO0 to GND, then press RESET."),
               ("Upload", "Enter your Wi-Fi credentials and upload the sketch."),
               ("Run", "Remove the GPIO0–GND jumper, press RESET and read the IP in the Serial Monitor."),
               ("Watch", "Open http://<ip>:81/stream for video and http://<ip>/motion for the PIR status."),
               ("Mount", "Power from a dedicated 5 V supply; weak USB ports cause brown-outs.")],
        code=[("esp32cam_security.ino", "cpp", "MJPEG streaming server with PIR motion endpoint", CAM_INO)],
    ),
    dict(
        slug="pico-traffic-light-controller", category="micropython", board="Raspberry Pi Pico",
        title="Raspberry Pi Pico Traffic Light with Pedestrian Button",
        summary="A complete traffic-light state machine in MicroPython with interrupt-driven crossing request.",
        description=("Three LEDs, one button and a buzzer teach you GPIO, timing, interrupts and PWM in MicroPython. "
                     "Press the button and the lights finish their cycle, stop traffic and beep for pedestrians."),
        difficulty="beginner", build_minutes=25, cost_usd=10,
        tags="raspberry pi pico, micropython, traffic light, led, button, interrupt, pwm, python",
        youtube_id="nDpi5tqEYd0", video_credit="Raspberry Pi Pico MicroPython Crash Course: LED, Button & Analog",
        components=[("Raspberry Pi Pico", 1, "or Pico W"), ("Red LED", 1, ""), ("Amber/yellow LED", 1, ""), ("Green LED", 1, ""),
                    ("220 Ω resistor", 3, "one per LED"), ("Push button", 1, ""), ("Active buzzer", 1, "3.3 V OK"),
                    ("Breadboard", 1, ""), ("Jumper wires", 10, "")],
        connections=[("Pico", "GP15", "Red LED", "Anode (via 220Ω)", RED, ""),
                     ("Pico", "GP14", "Amber LED", "Anode (via 220Ω)", YEL, ""),
                     ("Pico", "GP13", "Green LED", "Anode (via 220Ω)", GRN, ""),
                     ("Pico", "GP12", "Button", "Pin A", BLU, "Other leg to 3V3"),
                     ("Pico", "3V3(OUT)", "Button", "Pin B", RED, "Pull-down in code"),
                     ("Pico", "GP11", "Buzzer", "+", ORG, ""),
                     ("Pico", "GND", "LED cathodes + Buzzer −", "Common GND", BLK, "")],
        steps=[("Flash MicroPython", "Hold BOOTSEL, plug in the Pico, drag the MicroPython .uf2 onto the RPI-RP2 drive."),
               ("Install Thonny", "Select the “MicroPython (Raspberry Pi Pico)” interpreter."),
               ("Build the circuit", "LED long leg → resistor → GPIO, short leg → GND. Button between GP12 and 3V3."),
               ("Run main.py", "Save the file to the Pico as main.py so it starts on power-up."),
               ("Try the bonus", "Run pwm_breathe.py to see smooth fading using duty_u16().")],
        code=[("main.py", "python", "Traffic-light state machine with button interrupt", PICO_PY),
              ("pwm_breathe.py", "python", "PWM breathing amber LED", PICO_PWM_PY)],
    ),
    dict(
        slug="arduino-auto-plant-watering", category="automation", board="Arduino Uno", featured=True,
        title="Automatic Plant Watering System",
        summary="Soil-moisture sensing with a relay-driven pump — your plants water themselves.",
        description=("A calibrated soil-moisture sensor decides when to switch a small pump through a relay. "
                     "Includes a cool-down timer so the soil can absorb water and the pump never floods the pot."),
        difficulty="beginner", build_minutes=45, cost_usd=18,
        tags="arduino, soil moisture, relay, pump, plant, irrigation, automation, garden",
        youtube_id="8g8oiIa98xc", video_credit="Automatic Plant Watering System using Arduino & Soil Moisture Sensor",
        safety_note="Keep all electronics away from water. Power the pump from its own supply — never from the Arduino pin.",
        components=[("Arduino Uno R3", 1, ""), ("Capacitive soil moisture sensor", 1, "more durable than resistive"),
                    ("1-channel 5 V relay module", 1, "active-low"), ("5 V mini submersible pump", 1, ""),
                    ("Silicone tubing", 1, "1 m"), ("External 5 V supply", 1, "for the pump"), ("Jumper wires", 8, "")],
        connections=[("Arduino Uno", "5V", "Soil Sensor", "VCC", RED, ""),
                     ("Arduino Uno", "A0", "Soil Sensor", "AOUT", GRN, "Analog reading"),
                     ("Arduino Uno", "GND", "Soil Sensor", "GND", BLK, ""),
                     ("Arduino Uno", "5V", "Relay", "VCC", RED, ""),
                     ("Arduino Uno", "D7", "Relay", "IN", YEL, "LOW = pump ON"),
                     ("Arduino Uno", "GND", "Relay", "GND", BLK, ""),
                     ("Pump supply +", "5V", "Relay", "COM / NO", ORG, "Relay switches pump power")],
        steps=[("Calibrate", "Print analogRead(A0) in dry air and in water; put those numbers in DRY_VALUE and WET_VALUE."),
               ("Wire sensor & relay", "Follow the Connections tab. Route pump power through COM and NO."),
               ("Upload & watch", "Open Serial Monitor to see moisture %."),
               ("Tune", "Adjust WATER_BELOW_PERCENT, PUMP_MS and COOLDOWN for your plant."),
               ("Deploy", "Place the sensor near the roots, the hose outlet at the soil surface.")],
        code=[("plant_watering.ino", "cpp", "Moisture-controlled pump with cooldown", PLANT_INO)],
    ),
    dict(
        slug="esp32-wifi-relay-controller", category="automation", board="ESP32",
        title="ESP32 Wi-Fi 4-Channel Relay Controller",
        summary="Toggle lamps, fans or pumps from a phone-friendly web page served by the ESP32.",
        description=("A mobile-friendly control panel with four toggles served straight from the ESP32. "
                     "Learn about active-low relay logic, HTTP routes and safe load switching. Test with low-voltage "
                     "loads (LEDs, 12 V fan) before ever attempting mains."),
        difficulty="intermediate", build_minutes=40, cost_usd=16,
        tags="esp32, relay, home automation, smart home, web server, wifi, iot, switch",
        youtube_id="giACxpN0cGc", video_credit="ESP32/ESP8266 Relay Module – Control AC Appliances (Web Server)",
        safety_note="⚠ MAINS VOLTAGE CAN KILL. Start with low-voltage loads. Use a rated, enclosed relay board, proper fusing and never touch live wiring.",
        components=[("ESP32 DevKit V1", 1, ""), ("4-channel relay module (5 V)", 1, "opto-isolated"),
                    ("5 V power supply", 1, "≥1 A"), ("Low-voltage test loads", 4, "LEDs / 12 V fan"), ("Jumper wires", 8, "")],
        connections=[("ESP32", "GPIO26", "Relay board", "IN1", GRN, ""),
                     ("ESP32", "GPIO27", "Relay board", "IN2", BLU, ""),
                     ("ESP32", "GPIO14", "Relay board", "IN3", YEL, ""),
                     ("ESP32", "GPIO12", "Relay board", "IN4", ORG, "Avoid pulling high at boot"),
                     ("ESP32", "VIN (5V)", "Relay board", "VCC", RED, ""),
                     ("ESP32", "GND", "Relay board", "GND", BLK, "")],
        steps=[("Wire the board", "Connect IN1–IN4 to GPIO 26/27/14/12, power the module from 5 V and share ground."),
               ("Check the logic", "Most boards are active-low; the sketch handles this with ACTIVE_LOW."),
               ("Upload", "Add your Wi-Fi credentials, upload and read the IP address."),
               ("Control", "Browse to the IP on your phone and tap a channel to toggle it."),
               ("Go further", "Add authentication, MQTT or schedules before exposing it beyond your home network.")],
        code=[("esp32_relay_panel.ino", "cpp", "Four-channel web relay controller", RELAY_INO)],
    ),
]
