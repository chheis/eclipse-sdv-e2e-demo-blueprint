#define ZENOH_ARDUINO_UNO_R4_WIFI 1

#include <WiFiS3.h>
#include <zenoh-pico.h>
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;    // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)
int status = WL_IDLE_STATUS;  // the WiFi radio's status

WiFiClient wifiClient;

const char zenohMode[] = "client";
const char zenohLocator[] = "tcp/192.168.0.100:7447";
const char zenohKeyexpr[] = "Vehicle/Body/Lights/Signals";

const int xPin = A0;  // VRX attach
const int swPin = 8;  // SW attach (pressed = LOW)

const int joystickCenter = 512;
const int joystickDeadzone = 120;

bool leftIsSignaling = false;
bool rightIsSignaling = false;
bool brakeIsActive = false;

z_owned_session_t zenohSession;
z_owned_publisher_t zenohPublisher;
bool zenohReady = false;
unsigned long lastZenohKeepAliveMs = 0;
const unsigned long zenohKeepAliveIntervalMs = 1000;

void setup() {
  // set PINs for Joystick
  pinMode(swPin, INPUT_PULLUP);
  Serial.begin(115200);
  while(!Serial) { }

  // check for the WiFi module:
  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
    // don't continue
    while (true)
      ;
  }

  String fv = WiFi.firmwareVersion();
  if (fv < WIFI_FIRMWARE_LATEST_VERSION) {
    Serial.println("Please upgrade the firmware");
  }

  // attempt to connect to WiFi network:
  while (status != WL_CONNECTED) {
    Serial.print("Attempting to connect to WPA SSID: ");
    Serial.println(ssid);
    // Connect to WPA/WPA2 network. Change this line if using open or WEP network:
    status = WiFi.begin(ssid, pass);

    // wait 5 seconds for connection:
    delay(5000);
  }

  // you're connected now, so print out the data:
  Serial.print("You're connected to the network");
  printCurrentNet();
  printWifiData();

  initZenoh();
}

void loop() {
  int xValue = analogRead(xPin);
  bool swPressed = (digitalRead(swPin) == LOW);

  if (zenohReady) {
    zp_read(z_session_loan(&zenohSession), NULL);
    unsigned long now = millis();
    if (now - lastZenohKeepAliveMs >= zenohKeepAliveIntervalMs) {
      zp_send_keep_alive(z_session_loan(&zenohSession), NULL);
      lastZenohKeepAliveMs = now;
    }
  }

  bool newLeft = xValue < (joystickCenter - joystickDeadzone);
  bool newRight = xValue > (joystickCenter + joystickDeadzone);
  bool newBrake = swPressed;

  if (newLeft != leftIsSignaling || newRight != rightIsSignaling || newBrake != brakeIsActive) {
    leftIsSignaling = newLeft;
    rightIsSignaling = newRight;
    brakeIsActive = newBrake;
    sendZenohUpdate(leftIsSignaling, rightIsSignaling, brakeIsActive);
  }

  delay(50);
}

void printWifiData() {
  // print your board's IP address:
  IPAddress ip = WiFi.localIP();
  Serial.print("IP Address: ");

  Serial.println(ip);

  // print your MAC address:
  byte mac[6];
  WiFi.macAddress(mac);
  Serial.print("MAC address: ");
  printMacAddress(mac);
}

void printCurrentNet() {
  // print the SSID of the network you're attached to:
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());

  // print the MAC address of the router you're attached to:
  byte bssid[6];
  WiFi.BSSID(bssid);
  Serial.print("BSSID: ");
  printMacAddress(bssid);

  // print the received signal strength:
  long rssi = WiFi.RSSI();
  Serial.print("signal strength (RSSI):");
  Serial.println(rssi);

  // print the encryption type:
  byte encryption = WiFi.encryptionType();
  Serial.print("Encryption Type:");
  Serial.println(encryption, HEX);
  Serial.println();
}

void printMacAddress(byte mac[]) {
  for (int i = 5; i >= 0; i--) {
    if (mac[i] < 16) {
      Serial.print("0");
    }
    Serial.print(mac[i], HEX);
    if (i > 0) {
      Serial.print(":");
    }
  }
  Serial.println();
}


void initZenoh() {
#if Z_FEATURE_PUBLICATION == 1
  z_owned_config_t config;
  z_config_default(&config);
  zp_config_insert(z_config_loan_mut(&config), Z_CONFIG_MODE_KEY, zenohMode);
  if (strlen(zenohLocator) > 0) {
    zp_config_insert(z_config_loan_mut(&config), Z_CONFIG_CONNECT_KEY, zenohLocator);
  }

  Serial.print("Opening Zenoh session...");
  if (z_open(&zenohSession, z_config_move(&config), NULL) < 0) {
    Serial.println("failed");
    return;
  }
  Serial.println("ok");

  z_view_keyexpr_t ke;
  z_view_keyexpr_from_str_unchecked(&ke, zenohKeyexpr);
  Serial.print("Declaring Zenoh publisher: ");
  Serial.println(zenohKeyexpr);
  if (z_declare_publisher(z_session_loan(&zenohSession), &zenohPublisher, z_view_keyexpr_loan(&ke), NULL) < 0) {
    Serial.println("Unable to declare Zenoh publisher");
    z_session_drop(z_session_move(&zenohSession));
    return;
  }

  zenohReady = true;
#else
  Serial.println("Zenoh publication feature disabled at build time.");
#endif
}

void sendZenohUpdate(bool left, bool right, bool brake) {
  if (!zenohReady) {
    return;
  }

  String payload = "{";
  payload += "\"Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling\":";
  payload += (left ? "true" : "false");
  payload += ",";
  payload += "\"Vehicle.Body.Lights.DirectionIndicator.Right.IsSignaling\":";
  payload += (right ? "true" : "false");
  payload += ",";
  payload += "\"Vehicle.Body.Lights.Brake.IsActive\":";
  payload += (brake ? "true" : "false");
  payload += "}";

  Serial.println("Publishing to Zenoh:");
  Serial.println(payload);

  z_owned_bytes_t bytes;
  z_bytes_copy_from_str(&bytes, payload.c_str());
  if (z_publisher_put(z_publisher_loan(&zenohPublisher), z_bytes_move(&bytes), NULL) < 0) {
    Serial.println("Zenoh publish failed");
  }
}
