#include <WiFiS3.h>
#include <ArduinoMqttClient.h>
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;    // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)
int status = WL_IDLE_STATUS;  // the WiFi radio's status

WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

const char broker[] = "broker.hivemq.com";
int port = 1883;
const char topic[] = "SunFounder MQTT Test";

//init buttons & states
const int buttonPins[4] = { 2, 3, 4, 5 };
bool previousButtonStates[4] = { false, false, false, false };

const int xPin = A0;  //the VRX attach to
const int yPin = A1;  //the VRY attach to
const int swPin = 8;  //the SW attach to

void setup() {
  pinMode(swPin, INPUT_PULLUP);
  Serial.begin(115200);
  while(!Serial) { }
  
}

void loop() {
  Serial.print("X: ");
  Serial.print(analogRead(xPin), DEC);  // print the value of VRX in DEC
  Serial.print("|Y: ");
  Serial.print(analogRead(yPin), DEC);  // print the value of VRX in DEC
  Serial.print("|Z: ");
  Serial.println(digitalRead(swPin));  // print the value of SW
  delay(50);
}