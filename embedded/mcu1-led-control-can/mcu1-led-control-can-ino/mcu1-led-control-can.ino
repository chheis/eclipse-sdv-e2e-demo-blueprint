#include <FastLED.h>  // Include FastLED library
#include <SPI.h>
#include <107-Arduino-MCP2515.h>
#undef max
#undef min
#include <algorithm>

/**Globals for LED Stripe**/
#define NUM_LEDS 8    // Number of LEDs in the chain
#define DATA_PIN 6    // Data pin for LED control

CRGB leds[NUM_LEDS];  // Array to hold LED color data
/**END Globals for LED Stripe**/

/*Globals for CAN MCP2515 */
static int const MKRCAN_MCP2515_CS_PIN  = 10;
static int const MKRCAN_MCP2515_INT_PIN = 2;
static SPISettings const MCP2515x_SPI_SETTING{1000000, MSBFIRST, SPI_MODE0};

/**************************************************************************************
 * FUNCTION DECLARATION
 **************************************************************************************/

void onReceiveBufferFull(uint32_t const, uint32_t const, uint8_t const *, uint8_t const);

/**************************************************************************************
 * TYPEDEF
 **************************************************************************************/

typedef struct
{
  uint32_t id;
  uint8_t  data[8];
  uint8_t  len;
} sCanTestFrame;

bool canRxPending = false;

typedef struct {
  uint32_t ts;
  uint32_t id;
  uint8_t  len;
  uint8_t  data[8];
} CanRxFrame;

CanRxFrame rxFrame;

/**************************************************************************************
 * GLOBAL CONSTANTS
 **************************************************************************************/

static sCanTestFrame const test_frame_1 = { 0x00000001, {0}, 0 };                                              /* Minimum (no) payload */
static sCanTestFrame const test_frame_2 = { 0x00000002, {0xCA, 0xFE, 0xCA, 0xFE, 0, 0, 0, 0}, 4 };             /* Between minimum and maximum payload */
static sCanTestFrame const test_frame_3 = { 0x00000003, {0xCA, 0xFE, 0xCA, 0xFE, 0xCA, 0xFE, 0xCA, 0xFE}, 8 }; /* Maximum payload */
static sCanTestFrame const test_frame_4 = { 0x40000004, {0}, 0 };                                              /* RTR frame */
static sCanTestFrame const test_frame_5 = { 0x000007FF, {0}, 0 };                                              /* Highest standard 11 bit CAN address */
static sCanTestFrame const test_frame_6 = { 0x80000000, {0}, 0 };                                              /* Lowest extended 29 bit CAN address */
static sCanTestFrame const test_frame_7 = { 0x9FFFFFFF, {0}, 0 };                                              /* Highest extended 29 bit CAN address */

static std::array<sCanTestFrame, 7> const CAN_TEST_FRAME_ARRAY =
{
  test_frame_1,
  test_frame_2,
  test_frame_3,
  test_frame_4,
  test_frame_5,
  test_frame_6,
  test_frame_7
};
/*END Globals for CAN MCP2515 */

// void onReceiveBufferFull(uint32_t const timestamp_us, uint32_t const id, uint8_t const * data, uint8_t const len)
// {
//   Serial.println(id, HEX);
// }
void onTransmitBufferEmpty(ArduinoMCP2515 * this_ptr)
{
  /* You can use this callback to refill the transmit buffer via this_ptr->transmit(...) */
}
/*CAN MCP2515 */
ArduinoMCP2515 mcp2515([]() { digitalWrite(MKRCAN_MCP2515_CS_PIN, LOW); },
                       []() { digitalWrite(MKRCAN_MCP2515_CS_PIN, HIGH); },
                       [](uint8_t const d) { return SPI.transfer(d); },
                       micros,
                       millis,
                       onReceiveBufferFull,
                       nullptr);
/*CAN MCP2515 */

void setup() {
  Serial.begin(115200);
  while(!Serial) { }

  SPI.begin();
  //SPI.beginTransaction(MCP2515x_SPI_SETTING);
  pinMode(MKRCAN_MCP2515_CS_PIN, OUTPUT);
  digitalWrite(MKRCAN_MCP2515_CS_PIN, HIGH);

  /* Attach interrupt handler to register MCP2515 signaled by taking INT low */
  pinMode(MKRCAN_MCP2515_INT_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(MKRCAN_MCP2515_INT_PIN), [](){ mcp2515.onExternalEventHandler(); }, FALLING);


  mcp2515.begin();
  mcp2515.setBitRate(CanBitRate::BR_500kBPS_8MHZ); // CAN bitrate and clock speed of MCP2515
  mcp2515.setNormalMode();
  /**Init LED Stripe**/
  FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_LEDS);  // Initialize LEDs
}

/**************************************************************************************
 * FUNCTION DEFINITION
 **************************************************************************************/
void onReceiveBufferFull(uint32_t const timestamp_us,
                         uint32_t const id,
                         uint8_t const * data,
                         uint8_t const len)
{
  if (canRxPending) return; // drop frame if not processed yet

  rxFrame.ts  = timestamp_us;
  rxFrame.id  = id;
  rxFrame.len = len;

  for (uint8_t i = 0; i < len; i++) {
    rxFrame.data[i] = data[i];
  }

  canRxPending = true;
}

// void onReceiveBufferFull(uint32_t const timestamp_us, uint32_t const id, uint8_t const * data, uint8_t const len)
// {
//   Serial.print("[ ");
//   Serial.print(timestamp_us);
//   Serial.print("] ");

//   Serial.print("ID");
//   if(id & MCP2515::CAN_EFF_BITMASK) Serial.print("(EXT)");
//   if(id & MCP2515::CAN_RTR_BITMASK) Serial.print("(RTR)");
//   Serial.print(" ");
//   Serial.print(id, HEX);

//   Serial.print(" DATA[");
//   Serial.print(len);
//   Serial.print("] ");
//   std::for_each(data,
//                 data+len,
//                 [](uint8_t const elem) {
//                   Serial.print(elem, HEX);
//                   Serial.print(" ");
//                 });
//   Serial.println();
// }

void loop() {
  static uint32_t lastLedUpdate = 0;
  static uint32_t lastCanTx     = 0;
  static uint8_t  ledIndex     = 0;
  static bool     ledOn        = false;

  uint32_t now = millis();

  /* ---------- LED animation (non-blocking) ---------- */
  if (now - lastLedUpdate >= 30) {
    lastLedUpdate = now;

    fill_solid(leds, NUM_LEDS, CRGB::Black);

    if (ledOn) {
      leds[ledIndex] = CRGB::Blue;
      ledIndex = (ledIndex + 1) % NUM_LEDS;
    }

    ledOn = !ledOn;
    FastLED.show();
  }

  /* ---------- CAN transmit (rate limited) ----------- */
  if (now - lastCanTx >= 100) {
    lastCanTx = now;

    uint8_t data[8] = {
      0xDE, 0xAD, 0xBE, 0xEF,
      0xDE, 0xAD, 0xBE, 0xEF
    };

    mcp2515.transmit(0x01, data, 8);
    Serial.println("Send Frame");
  }
  if (canRxPending) {
    noInterrupts();
    CanRxFrame f = rxFrame;
    canRxPending = false;
    interrupts();

    Serial.print("[ ");
    Serial.print(f.ts);
    Serial.print(" ] ID ");

    if (f.id & MCP2515::CAN_EFF_BITMASK) Serial.print("(EXT)");
    if (f.id & MCP2515::CAN_RTR_BITMASK) Serial.print("(RTR)");

    Serial.print(" ");
    Serial.print(f.id, HEX);
    Serial.print(" DATA[");

    Serial.print(f.len);
    Serial.print("] ");

    for (uint8_t i = 0; i < f.len; i++) {
      Serial.print(f.data[i], HEX);
      Serial.print(" ");
    }
    Serial.println();
  }
  
  // // Loop through each LED and set it to blue
  // for (int dot = 0; dot < NUM_LEDS; dot++) {
  //   leds[dot] = CRGB::Blue;   // Set the current LED to blue
  //   //FastLED.show();           // Update LEDs
  //   leds[dot] = CRGB::Black;  // Clear the current LED
  //   delay(30);                // Wait for a short period before moving to the next LED
  // }

  // fill_solid(leds, NUM_LEDS, CRGB::Blue);
  // FastLED.show();
  // delay(240);
  // fill_solid(leds, NUM_LEDS, CRGB::Black);
  // FastLED.show();

  // uint8_t const data[8] = {0xDE, 0xAD, 0xBE, 0xEF, 0xDE, 0xAD, 0xBE, 0xEF};
  // mcp2515.transmit(1 /* id */, data, 8 /* len */);
  // Serial.println("Send Frame");



  //delay(100);
  
}
