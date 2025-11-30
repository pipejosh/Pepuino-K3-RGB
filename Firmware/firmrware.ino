
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>
#include "USBKeyboard.h"

// ------------ OLED SETTINGS -------------
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 32
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// ------------ PINS -----------------------
#define BTN1 1  // 'z'
#define BTN2 2  // 'x'
#define BTN3 3  // 'w'

int r = 0;
int rMax = 14;
bool growing = true;
unsigned long lastAnim = 0;

void setup() {
  pinMode(BTN1, INPUT_PULLUP);
  pinMode(BTN2, INPUT_PULLUP);
  pinMode(BTN3, INPUT_PULLUP);

  USBKeyboard.begin();

  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();
  display.display();
}

void loop() {

  // ---------- KEYBOARD INPUT ----------
  if (!digitalRead(BTN1)) { USBKeyboard.print("z"); delay(150); }
  if (!digitalRead(BTN2)) { USBKeyboard.print("x"); delay(150); }
  if (!digitalRead(BTN3)) { USBKeyboard.print("w"); delay(150); }

  // ---------- PULSE ANIMATION ----------
  if (millis() - lastAnim > 40) {   // animation speed
    lastAnim = millis();

    if (growing) {
      r++;
      if (r >= rMax) growing = false;
    } else {
      r--;
      if (r <= 1) growing = true;
    }
  }

  // ---------- DRAW ----------
  display.clearDisplay();

  int cx = SCREEN_WIDTH / 2;
  int cy = SCREEN_HEIGHT / 2;

  // Outer circle pulse
  display.drawCircle(cx, cy, r, SSD1306_WHITE);

  // Optional: inner core
  display.fillCircle(cx, cy, 2, SSD1306_WHITE);

  display.display();
}
