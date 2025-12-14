#include <Controllino.h>

// List of all pins we want to test
const int digitalPins[] = {
  CONTROLLINO_D0,  CONTROLLINO_D1,  CONTROLLINO_D2,  CONTROLLINO_D3,
  CONTROLLINO_D4,  CONTROLLINO_D5,  CONTROLLINO_D6,  CONTROLLINO_D7,
  CONTROLLINO_D8,  CONTROLLINO_D9,  CONTROLLINO_D10, CONTROLLINO_D11,
  CONTROLLINO_D12, CONTROLLINO_D13, CONTROLLINO_D14, CONTROLLINO_D15,
  CONTROLLINO_D16, CONTROLLINO_D17, CONTROLLINO_D18, CONTROLLINO_D19,
  CONTROLLINO_D20, CONTROLLINO_D21, CONTROLLINO_D22, CONTROLLINO_D23
};

const int analogPins[] = {
  CONTROLLINO_A0,  CONTROLLINO_A1,  CONTROLLINO_A2,  CONTROLLINO_A3,
  CONTROLLINO_A4,  CONTROLLINO_A5,  CONTROLLINO_A6,  CONTROLLINO_A7,
  CONTROLLINO_A8,  CONTROLLINO_A9,  CONTROLLINO_A10, CONTROLLINO_A11,
  CONTROLLINO_A12, CONTROLLINO_A13, CONTROLLINO_A14, CONTROLLINO_A15
};

const int numDigital = sizeof(digitalPins) / sizeof(digitalPins[0]);
const int numAnalog  = sizeof(analogPins)  / sizeof(analogPins[0]);

const unsigned long onTime = 500;  // ms each channel stays ON

void setup() {
  // Set all pins as OUTPUT and start them LOW
  for (int i = 0; i < numDigital; i++) {
    pinMode(digitalPins[i], OUTPUT);
    digitalWrite(digitalPins[i], LOW);
  }
  for (int i = 0; i < numAnalog; i++) {
    pinMode(analogPins[i], OUTPUT);
    digitalWrite(analogPins[i], LOW);
  }
}

void loop() {
  // Scan all digital outputs (including relays)
  for (int i = 0; i < numDigital; i++) {
    digitalWrite(digitalPins[i], HIGH);  // this LED/relay ON
    delay(onTime);
    digitalWrite(digitalPins[i], LOW);   // back OFF
  }

  // Scan all “analog” channels as digital outputs
  for (int i = 0; i < numAnalog; i++) {
    digitalWrite(analogPins[i], HIGH);
    delay(onTime);
    digitalWrite(analogPins[i], LOW);
  }
}
