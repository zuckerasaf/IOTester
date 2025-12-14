/*
 * Controllino Serial Command Interface
 * 
 * Simple protocol for controlling Controllino pins via serial commands.
 * Commands:
 *   W,pin,value  - Write digital (W,2,1 = set pin 2 HIGH, W,2,0 = set pin 2 LOW)
 *   R,pin        - Read analog (R,54 = read analog from pin 54)
 *   ?            - Ping/alive check (responds with "OK")
 * 
 * Baud rate: 115200
 */

#include <Controllino.h>

const unsigned long BAUD_RATE = 115200;
String inputString = "";
boolean stringComplete = false;

void setup() {
  Serial.begin(BAUD_RATE);
  inputString.reserve(50);
  
  // Send ready signal
  delay(100);
  Serial.println("READY");
}

void loop() {
  // Process serial commands
  if (stringComplete) {
    processCommand(inputString);
    inputString = "";
    stringComplete = false;
  }
}

// Serial event handler - called automatically when data arrives
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n' || inChar == '\r') {
      if (inputString.length() > 0) {
        stringComplete = true;
      }
    } else {
      inputString += inChar;
    }
  }
}

void processCommand(String cmd) {
  cmd.trim();
  
  if (cmd.length() == 0) {
    return;
  }
  
  // Ping command
  if (cmd == "?") {
    Serial.println("OK");
    return;
  }
  
  // Parse command: W,pin,value or R,pin
  int firstComma = cmd.indexOf(',');
  if (firstComma == -1) {
    Serial.println("ERROR:Invalid command format");
    return;
  }
  
  char command = cmd.charAt(0);
  String pinStr = cmd.substring(firstComma + 1);
  
  if (command == 'W') {
    // Digital write: W,pin,value
    int secondComma = pinStr.indexOf(',');
    if (secondComma == -1) {
      Serial.println("ERROR:Missing value for write");
      return;
    }
    
    int pin = pinStr.substring(0, secondComma).toInt();
    int value = pinStr.substring(secondComma + 1).toInt();
    
    pinMode(pin, OUTPUT);
    digitalWrite(pin, value);
    Serial.print("OK:W,");
    Serial.print(pin);
    Serial.print(",");
    Serial.println(value);
    
  } else if (command == 'R') {
    // Analog read: R,pin
    int pin = pinStr.toInt();
    pinMode(pin, INPUT);
    int reading = analogRead(pin);
    
    // Convert to voltage (0-5V range, 10-bit ADC)
    float voltage = (reading / 1023.0) * 5.0;
    
    Serial.print("OK:R,");
    Serial.print(pin);
    Serial.print(",");
    Serial.println(voltage, 3);  // 3 decimal places
    
  } else {
    Serial.println("ERROR:Unknown command");
  }
}
