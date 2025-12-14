/*
 * Controllino Pin Mapper
 * 
 * This sketch prints out the actual Arduino pin numbers for all Controllino pins.
 * Upload this to your Controllino, open Serial Monitor at 115200 baud,
 * and copy the output to update your pin_map.json file.
 */

#include <Controllino.h>

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ; // wait for serial port to connect
  }
  
  delay(2000);
  
  Serial.println("========================================");
  Serial.println("CONTROLLINO PIN MAPPING");
  Serial.println("========================================");
  Serial.println();
  
  // Digital pins
  Serial.println("Digital Pins (D):");
  Serial.println("------------------");
  Serial.print("CONTROLLINO_D0  = "); Serial.println(CONTROLLINO_D0);
  Serial.print("CONTROLLINO_D1  = "); Serial.println(CONTROLLINO_D1);
  Serial.print("CONTROLLINO_D2  = "); Serial.println(CONTROLLINO_D2);
  Serial.print("CONTROLLINO_D3  = "); Serial.println(CONTROLLINO_D3);
  Serial.print("CONTROLLINO_D4  = "); Serial.println(CONTROLLINO_D4);
  Serial.print("CONTROLLINO_D5  = "); Serial.println(CONTROLLINO_D5);
  Serial.print("CONTROLLINO_D6  = "); Serial.println(CONTROLLINO_D6);
  Serial.print("CONTROLLINO_D7  = "); Serial.println(CONTROLLINO_D7);
  Serial.print("CONTROLLINO_D8  = "); Serial.println(CONTROLLINO_D8);
  Serial.print("CONTROLLINO_D9  = "); Serial.println(CONTROLLINO_D9);
  Serial.print("CONTROLLINO_D10 = "); Serial.println(CONTROLLINO_D10);
  Serial.print("CONTROLLINO_D11 = "); Serial.println(CONTROLLINO_D11);
  Serial.print("CONTROLLINO_D12 = "); Serial.println(CONTROLLINO_D12);
  Serial.print("CONTROLLINO_D13 = "); Serial.println(CONTROLLINO_D13);
  Serial.print("CONTROLLINO_D14 = "); Serial.println(CONTROLLINO_D14);
  Serial.print("CONTROLLINO_D15 = "); Serial.println(CONTROLLINO_D15);
  Serial.print("CONTROLLINO_D16 = "); Serial.println(CONTROLLINO_D16);
  Serial.print("CONTROLLINO_D17 = "); Serial.println(CONTROLLINO_D17);
  Serial.print("CONTROLLINO_D18 = "); Serial.println(CONTROLLINO_D18);
  Serial.print("CONTROLLINO_D19 = "); Serial.println(CONTROLLINO_D19);
  Serial.print("CONTROLLINO_D20 = "); Serial.println(CONTROLLINO_D20);
  Serial.print("CONTROLLINO_D21 = "); Serial.println(CONTROLLINO_D21);
  Serial.print("CONTROLLINO_D22 = "); Serial.println(CONTROLLINO_D22);
  Serial.print("CONTROLLINO_D23 = "); Serial.println(CONTROLLINO_D23);
  
  Serial.println();
  Serial.println("Relay Pins (R):");
  Serial.println("------------------");
  Serial.print("CONTROLLINO_R0  = "); Serial.println(CONTROLLINO_R0);
  Serial.print("CONTROLLINO_R1  = "); Serial.println(CONTROLLINO_R1);
  Serial.print("CONTROLLINO_R2  = "); Serial.println(CONTROLLINO_R2);
  Serial.print("CONTROLLINO_R3  = "); Serial.println(CONTROLLINO_R3);
  Serial.print("CONTROLLINO_R4  = "); Serial.println(CONTROLLINO_R4);
  Serial.print("CONTROLLINO_R5  = "); Serial.println(CONTROLLINO_R5);
  Serial.print("CONTROLLINO_R6  = "); Serial.println(CONTROLLINO_R6);
  Serial.print("CONTROLLINO_R7  = "); Serial.println(CONTROLLINO_R7);
  Serial.print("CONTROLLINO_R8  = "); Serial.println(CONTROLLINO_R8);
  Serial.print("CONTROLLINO_R9  = "); Serial.println(CONTROLLINO_R9);
  Serial.print("CONTROLLINO_R10 = "); Serial.println(CONTROLLINO_R10);
  Serial.print("CONTROLLINO_R11 = "); Serial.println(CONTROLLINO_R11);
  Serial.print("CONTROLLINO_R12 = "); Serial.println(CONTROLLINO_R12);
  Serial.print("CONTROLLINO_R13 = "); Serial.println(CONTROLLINO_R13);
  Serial.print("CONTROLLINO_R14 = "); Serial.println(CONTROLLINO_R14);
  Serial.print("CONTROLLINO_R15 = "); Serial.println(CONTROLLINO_R15);
  
  Serial.println();
  Serial.println("Analog Pins (A):");
  Serial.println("------------------");
  Serial.print("CONTROLLINO_A0  = "); Serial.println(CONTROLLINO_A0);
  Serial.print("CONTROLLINO_A1  = "); Serial.println(CONTROLLINO_A1);
  Serial.print("CONTROLLINO_A2  = "); Serial.println(CONTROLLINO_A2);
  Serial.print("CONTROLLINO_A3  = "); Serial.println(CONTROLLINO_A3);
  Serial.print("CONTROLLINO_A4  = "); Serial.println(CONTROLLINO_A4);
  Serial.print("CONTROLLINO_A5  = "); Serial.println(CONTROLLINO_A5);
  Serial.print("CONTROLLINO_A6  = "); Serial.println(CONTROLLINO_A6);
  Serial.print("CONTROLLINO_A7  = "); Serial.println(CONTROLLINO_A7);
  Serial.print("CONTROLLINO_A8  = "); Serial.println(CONTROLLINO_A8);
  Serial.print("CONTROLLINO_A9  = "); Serial.println(CONTROLLINO_A9);
  Serial.print("CONTROLLINO_A10 = "); Serial.println(CONTROLLINO_A10);
  Serial.print("CONTROLLINO_A11 = "); Serial.println(CONTROLLINO_A11);
  Serial.print("CONTROLLINO_A12 = "); Serial.println(CONTROLLINO_A12);
  Serial.print("CONTROLLINO_A13 = "); Serial.println(CONTROLLINO_A13);
  Serial.print("CONTROLLINO_A14 = "); Serial.println(CONTROLLINO_A14);
  Serial.print("CONTROLLINO_A15 = "); Serial.println(CONTROLLINO_A15);
  
  Serial.println();
  Serial.println("========================================");
  Serial.println("Copy this output to verify pin_map.json");
  Serial.println("========================================");
}

void loop() {
  // Nothing to do
}
