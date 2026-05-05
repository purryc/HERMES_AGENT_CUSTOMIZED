#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <M5GFX.h>
#include <M5Unified.h>
#include <SPIFFS.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include <algorithm>
#include <cmath>
#include <memory>
#include <vector>

#include "pet_config.h"

namespace {

constexpr uint32_t kSampleRate = 16000;
constexpr size_t kRecordChunkSamples = 512;
constexpr size_t kMinSpeechSamples = kSampleRate / 4;
constexpr size_t kMaxRecordSamples = (kSampleRate * PET_MAX_RECORD_MS) / 1000;
constexpr uint32_t kHttpTimeoutMs = 15000;
constexpr uint32_t kShakeSampleMs = 60;
constexpr uint32_t kShakeDizzyMs = 2600;
constexpr uint32_t kShakeCooldownMs = 1200;
constexpr float kShakeDeltaThreshold = 1.35f;
constexpr float kShakeMagnitudeThreshold = 2.8f;
constexpr char kPendingIndexPath[] = "/pending_queue.json";

enum class DeviceState {
  Boot,
  Idle,
  Recording,
  Uploading,
  Thinking,
  Speaking,
  Error,
};

struct PendingUpload {
  String id;
  String wavPath;
  String sessionId;
  int batteryLevel = -1;
};

struct WavInfo {
  uint32_t dataOffset = 44;
  uint32_t sampleRate = kSampleRate;
  uint16_t channels = 1;
  uint16_t bitsPerSample = 16;
};

DeviceState gState = DeviceState::Boot;
String gBubbleText = "Booting...";
String gExpression = "idle";
String gEmotion = "neutral";
String gActiveTurnId;
String gCurrentAudioUrl;
String gCurrentReplyText;
String gLastUploadError = "Offline, saved for retry";
int16_t gRecordedSamples[kMaxRecordSamples] = {};
size_t gRecordedSampleCount = 0;
std::vector<uint8_t> gSpeakingAudio;
uint32_t gPlaybackExpectedUntil = 0;
uint32_t gStateChangedAt = 0;
uint32_t gLastUiRefreshAt = 0;
uint32_t gLastPollAt = 0;
uint32_t gLastWifiAttemptAt = 0;
uint32_t gRecordStartedAt = 0;
uint32_t gLastShakeSampleAt = 0;
uint32_t gLastShakeTriggerAt = 0;
uint32_t gDizzyUntil = 0;
float gLastAccelX = 0.0f;
float gLastAccelY = 0.0f;
float gLastAccelZ = 0.0f;
bool gWifiConnected = false;
bool gBtnAWasDown = false;
bool gHasLastAccel = false;
M5Canvas gUiCanvas(&M5.Display);
bool gUiCanvasReady = false;
String gLastScrollText;
uint32_t gTextScrollStartedAt = 0;

String stateLabel(DeviceState state);

void setState(DeviceState state, const String& bubble, const String& expression) {
  gState = state;
  gBubbleText = bubble;
  gExpression = expression;
  gStateChangedAt = millis();
  gLastUiRefreshAt = 0;
  Serial.printf("[pet] state=%s bubble=%s expression=%s\n", stateLabel(state).c_str(), bubble.c_str(), expression.c_str());
}

String stateLabel(DeviceState state) {
  switch (state) {
    case DeviceState::Boot:
      return "BOOT";
    case DeviceState::Idle:
      return "IDLE";
    case DeviceState::Recording:
      return "REC";
    case DeviceState::Uploading:
      return "SEND";
    case DeviceState::Thinking:
      return "THINK";
    case DeviceState::Speaking:
      return "SPEAK";
    case DeviceState::Error:
      return "ERR";
  }
  return "UNK";
}

uint16_t emotionColor(const String& emotion) {
  if (emotion == "happy") {
    return TFT_YELLOW;
  }
  if (emotion == "curious") {
    return TFT_CYAN;
  }
  if (emotion == "excited") {
    return TFT_ORANGE;
  }
  if (emotion == "sad") {
    return TFT_RED;
  }
  if (emotion == "sleepy") {
    return TFT_DARKGREY;
  }
  return TFT_WHITE;
}

int batteryLevel() {
  return M5.Power.getBatteryLevel();
}

lgfx::LovyanGFX& uiTarget() {
  return gUiCanvasReady ? static_cast<lgfx::LovyanGFX&>(gUiCanvas) : static_cast<lgfx::LovyanGFX&>(M5.Display);
}

void ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    gWifiConnected = true;
    return;
  }
  gWifiConnected = false;
  if (millis() - gLastWifiAttemptAt < PET_WIFI_RETRY_MS) {
    return;
  }
  gLastWifiAttemptAt = millis();
  WiFi.mode(WIFI_STA);
  WiFi.begin(PET_WIFI_SSID, PET_WIFI_PASSWORD);
}

bool isDizzy() {
  return gDizzyUntil != 0 && static_cast<int32_t>(gDizzyUntil - millis()) > 0;
}

void updateShakeGesture() {
  if (!M5.Imu.isEnabled()) {
    return;
  }

  const uint32_t now = millis();
  if (now - gLastShakeSampleAt < kShakeSampleMs) {
    return;
  }
  gLastShakeSampleAt = now;

  if (!M5.Imu.update()) {
    return;
  }

  float accelX = 0.0f;
  float accelY = 0.0f;
  float accelZ = 0.0f;
  if (!M5.Imu.getAccel(&accelX, &accelY, &accelZ)) {
    return;
  }

  if (!gHasLastAccel) {
    gLastAccelX = accelX;
    gLastAccelY = accelY;
    gLastAccelZ = accelZ;
    gHasLastAccel = true;
    return;
  }

  const float delta = fabsf(accelX - gLastAccelX) + fabsf(accelY - gLastAccelY) + fabsf(accelZ - gLastAccelZ);
  const float magnitude = fabsf(accelX) + fabsf(accelY) + fabsf(accelZ);
  gLastAccelX = accelX;
  gLastAccelY = accelY;
  gLastAccelZ = accelZ;

  if (now - gLastShakeTriggerAt < kShakeCooldownMs) {
    return;
  }

  if (delta >= kShakeDeltaThreshold || magnitude >= kShakeMagnitudeThreshold) {
    gLastShakeTriggerAt = now;
    gDizzyUntil = now + kShakeDizzyMs;
    gLastUiRefreshAt = 0;
    Serial.printf("[pet] shake detected delta=%.2f magnitude=%.2f\n", delta, magnitude);
  }
}

void drawPetFace(lgfx::LovyanGFX& gfx, int centerX, int centerY, int width, int height) {
  const bool dizzy = isDizzy();
  const uint16_t accent = dizzy ? TFT_MAGENTA : emotionColor(gEmotion);
  const uint16_t skin = 0xF5D7;
  const uint16_t skinShade = 0xCCB1;
  const uint16_t hair = 0x2945;
  const uint16_t hairLight = 0x8BD1;
  const uint16_t panel = 0x0108;
  const uint32_t now = millis();
  const int pulse = static_cast<int>((now / 120) % 6);
  const int wobble = dizzy ? static_cast<int>((now / 70) % 5) - 2 : 0;
  centerX += wobble;
  const bool blink = !dizzy && ((now / 1800) % 7) == 0 && gState != DeviceState::Recording && gState != DeviceState::Speaking;
  const bool speakingOpen = !dizzy && gState == DeviceState::Speaking && ((now / 150) % 2 == 0);

  const int left = centerX - width / 2;
  const int top = centerY - height / 2;
  const int right = left + width;
  const int bottom = top + height;
  const int haloR = std::min(width, height) / 2 - 2;
  gfx.fillRoundRect(left, top, width, height, 12, TFT_BLACK);
  gfx.drawCircle(centerX, centerY - 7, haloR, 0x035F);
  gfx.drawCircle(centerX, centerY - 7, haloR - 10 + (pulse % 3), accent);
  gfx.drawFastVLine(left + 2, top + 10, height - 20, 0x035F);
  gfx.drawFastVLine(right - 3, top + 10, height - 20, 0x035F);

  const int faceW = width * 44 / 80;
  const int faceH = height * 54 / 96;
  const int faceX = centerX - faceW / 2 + 2;
  const int faceY = top + height * 24 / 100;
  gfx.fillTriangle(faceX - 16, faceY + 8, centerX - 4, top + 8, faceX + faceW + 10, faceY + 6, hair);
  gfx.fillRoundRect(faceX - 12, faceY - 12, faceW + 22, faceH + 22, 20, hair);
  gfx.fillTriangle(faceX - 14, faceY + 6, faceX - 22, bottom - 8, faceX + 2, bottom - 12, hair);
  gfx.fillTriangle(faceX + faceW + 7, faceY + 4, faceX + faceW + 22, bottom - 4, faceX + faceW - 5, bottom - 12, hair);
  gfx.drawLine(faceX - 7, faceY - 6, faceX - 17, bottom - 11, hairLight);
  gfx.drawLine(faceX + faceW + 5, faceY - 4, faceX + faceW + 16, bottom - 10, 0x5A69);
  if (dizzy) {
    const int spin = static_cast<int>((now / 110) % 4);
    const int starY = faceY - 15;
    for (int i = 0; i < 3; ++i) {
      const int starX = centerX - 18 + i * 18;
      const int starBob = ((spin + i) % 2) * 3;
      gfx.drawFastHLine(starX - 3, starY + starBob, 7, accent);
      gfx.drawFastVLine(starX, starY - 3 + starBob, 7, accent);
    }
  }

  gfx.fillEllipse(centerX + 2, faceY + faceH / 2, faceW / 2, faceH / 2, skin);
  gfx.fillTriangle(centerX - faceW / 2 + 4, faceY + faceH / 2, centerX + faceW / 2, faceY + faceH / 2,
                          centerX + 1, faceY + faceH + 10, skin);
  gfx.drawLine(centerX + faceW / 3, faceY + 10, centerX + faceW / 3 + 4, faceY + faceH - 6, skinShade);
  gfx.fillCircle(centerX - faceW / 2 - 3, faceY + faceH / 2, 4, skin);
  gfx.drawLine(centerX - faceW / 2 - 5, faceY + faceH / 2 + 5, centerX - faceW / 2 - 3, faceY + faceH / 2 + 16, accent);

  const int eyeY = faceY + faceH / 2 - 4;
  const int leftEyeX = centerX - faceW / 4;
  const int rightEyeX = centerX + faceW / 5;
  if (dizzy) {
    const int spin = static_cast<int>((now / 90) % 4);
    const int dotX[4] = {0, 4, 0, -4};
    const int dotY[4] = {-4, 0, 4, 0};
    auto drawSpiralEye = [&](int x, int y, int offset) {
      const int index = (spin + offset) % 4;
      gfx.drawCircle(x, y, 7, accent);
      gfx.drawCircle(x, y, 4, accent);
      gfx.fillCircle(x + dotX[index], y + dotY[index], 2, TFT_WHITE);
      gfx.drawLine(x - 5, y + 5, x + 5, y - 5, accent);
    };
    drawSpiralEye(leftEyeX, eyeY, 0);
    drawSpiralEye(rightEyeX, eyeY, 2);
  } else if (gState == DeviceState::Thinking || gExpression == "thinking") {
    gfx.drawCircle(leftEyeX, eyeY, 5 + (pulse % 2), accent);
    gfx.drawCircle(rightEyeX, eyeY, 5 + ((pulse + 1) % 2), accent);
    gfx.fillCircle(leftEyeX, eyeY, 2, TFT_WHITE);
    gfx.fillCircle(rightEyeX, eyeY, 2, TFT_WHITE);
  } else if (gEmotion == "sleepy") {
    gfx.drawFastHLine(leftEyeX - 5, eyeY, 10, accent);
    gfx.drawFastHLine(rightEyeX - 5, eyeY, 10, accent);
  } else if (gState == DeviceState::Error || gExpression == "error" || gEmotion == "sad") {
    gfx.drawLine(leftEyeX - 5, eyeY - 3, leftEyeX + 5, eyeY + 2, accent);
    gfx.drawLine(rightEyeX - 5, eyeY + 2, rightEyeX + 5, eyeY - 3, accent);
  } else if (blink) {
    gfx.drawFastHLine(leftEyeX - 5, eyeY, 10, accent);
    gfx.drawFastHLine(rightEyeX - 5, eyeY, 10, accent);
  } else {
    const int curiousOffset = gEmotion == "curious" || gState == DeviceState::Recording ? 1 : 0;
    gfx.fillEllipse(leftEyeX, eyeY, 4, 5 + curiousOffset, TFT_BLACK);
    gfx.fillEllipse(rightEyeX, eyeY - curiousOffset, 4, 5, TFT_BLACK);
    gfx.fillCircle(leftEyeX + 1, eyeY - 1, 2, accent);
    gfx.fillCircle(rightEyeX + 1, eyeY - 1, 2, accent);
  }
  gfx.drawLine(leftEyeX - 8, eyeY - 8, leftEyeX + 5, eyeY - 10, hair);
  gfx.drawLine(rightEyeX - 6, eyeY - 10, rightEyeX + 8, eyeY - 8, hair);

  const int mouthY = faceY + faceH - 8;
  if (dizzy) {
    gfx.fillEllipse(centerX, mouthY + 1, 6, 3, 0x7800);
    gfx.drawLine(centerX - 7, mouthY - 2, centerX + 7, mouthY + 4, 0xE986);
  } else if (gState == DeviceState::Recording) {
    gfx.fillCircle(centerX, mouthY, 4 + (pulse % 2), TFT_RED);
    gfx.drawCircle(centerX, bottom - 16, 5 + pulse, TFT_RED);
  } else if (speakingOpen) {
    gfx.fillEllipse(centerX, mouthY, 6, 4, 0x7800);
  } else if (gEmotion == "happy" || gEmotion == "excited") {
    gfx.drawArc(centerX, mouthY - 2, 10, 6, 200, 340, 0xE986);
  } else if (gState == DeviceState::Error || gEmotion == "sad") {
    gfx.drawArc(centerX, mouthY + 4, 9, 5, 20, 160, 0xE986);
  } else {
    gfx.drawFastHLine(centerX - 5, mouthY, 10, 0xE986);
  }

  gfx.fillRoundRect(centerX - 18, bottom - 16, 36, 16, 6, panel);
  gfx.drawLine(centerX - 10, bottom - 12, centerX - 2, bottom - 5, accent);
  gfx.drawLine(centerX - 2, bottom - 5, centerX + 10, bottom - 14, accent);
}

String normalizeBubbleText(const String& text) {
  String compact = text;
  compact.replace("\r", " ");
  compact.replace("\n", " ");
  while (compact.indexOf("  ") >= 0) {
    compact.replace("  ", " ");
  }
  compact.trim();
  return compact.length() ? compact : String(" ");
}

size_t utf8CharSize(const String& text, size_t index) {
  const uint8_t lead = static_cast<uint8_t>(text[index]);
  size_t count = 1;
  if ((lead & 0xE0) == 0xC0) {
    count = 2;
  } else if ((lead & 0xF0) == 0xE0) {
    count = 3;
  } else if ((lead & 0xF8) == 0xF0) {
    count = 4;
  }
  return std::min(count, static_cast<size_t>(text.length()) - index);
}

void wrapUtf8Text(lgfx::LovyanGFX& gfx, const String& text, int width, std::vector<String>& lines) {
  lines.clear();
  const String compact = normalizeBubbleText(text);
  String line;
  for (size_t i = 0; i < static_cast<size_t>(compact.length());) {
    const size_t charSize = utf8CharSize(compact, i);
    String glyph = compact.substring(static_cast<int>(i), static_cast<int>(i + charSize));
    i += charSize;

    if (line.isEmpty() && glyph == " ") {
      continue;
    }

    String candidate = line + glyph;
    if (!line.isEmpty() && gfx.textWidth(candidate) > width) {
      line.trim();
      lines.push_back(line);
      line = glyph == " " ? String("") : glyph;
    } else {
      line = candidate;
    }
  }
  line.trim();
  if (!line.isEmpty()) {
    lines.push_back(line);
  }
  if (lines.empty()) {
    lines.push_back(String(" "));
  }
}

void drawVerticalScrollText(lgfx::LovyanGFX& gfx, const String& text, int x, int y, int width, int height, uint16_t fg, uint16_t bg) {
  const String compact = normalizeBubbleText(text);
  if (compact != gLastScrollText) {
    gLastScrollText = compact;
    gTextScrollStartedAt = millis();
  }

  std::vector<String> lines;
  wrapUtf8Text(gfx, compact, width, lines);

  const int lineStep = std::max(12, height / 2);
  const int textY = y + std::max(0, (lineStep - gfx.fontHeight()) / 2);
  int firstLine = 0;
  int offsetY = 0;

  if (lines.size() > 2) {
    const uint32_t holdMs = 1500;
    const uint32_t scrollMs = 520;
    const uint32_t cycleMs = holdMs + scrollMs;
    const uint32_t elapsed = millis() - gTextScrollStartedAt;
    firstLine = static_cast<int>((elapsed / cycleMs) % lines.size());
    const uint32_t phase = elapsed % cycleMs;
    if (phase > holdMs) {
      offsetY = static_cast<int>(((phase - holdMs) * lineStep) / scrollMs);
      offsetY = std::min(offsetY, lineStep);
    }
  }

  gfx.setTextDatum(top_left);
  gfx.setTextColor(fg, bg);
  gfx.setClipRect(x, y, width, height);
  for (int row = 0; row < 3; ++row) {
    const int lineIndex = lines.size() > 2 ? (firstLine + row) % lines.size() : row;
    if (lineIndex >= static_cast<int>(lines.size())) {
      break;
    }
    gfx.setCursor(x, textY + row * lineStep - offsetY);
    gfx.print(lines[lineIndex]);
  }
  gfx.clearClipRect();
}

void drawHudFrame(lgfx::LovyanGFX& gfx, int x, int y, int width, int height, uint16_t color) {
  gfx.drawRoundRect(x, y, width, height, 6, color);
  gfx.drawFastHLine(x + 4, y + 4, 12, color);
  gfx.drawFastHLine(x + width - 16, y + 4, 12, color);
  gfx.drawFastHLine(x + 4, y + height - 5, 12, color);
  gfx.drawFastHLine(x + width - 16, y + height - 5, 12, color);
}

void drawUi() {
  if (millis() - gLastUiRefreshAt < PET_UI_REFRESH_MS) {
    return;
  }
  gLastUiRefreshAt = millis();

  lgfx::LovyanGFX& gfx = uiTarget();
  const int screenW = gfx.width();
  const int screenH = gfx.height();
  const bool dizzy = isDizzy();
  const uint16_t accent = dizzy ? TFT_MAGENTA : emotionColor(gEmotion);
  const uint16_t dimCyan = 0x035F;
  const uint16_t panelFill = 0x0108;
  const uint32_t now = millis();
  const int panelH = 50;
  const int panelY = screenH - panelH - 4;
  const int avatarTop = 20;
  const int avatarBottom = panelY - 4;
  const int avatarH = std::max(76, avatarBottom - avatarTop);

  gfx.startWrite();
  gfx.fillScreen(TFT_BLACK);
  drawHudFrame(gfx, 2, 2, screenW - 4, screenH - 4, dimCyan);

  gfx.setTextColor(TFT_WHITE, TFT_BLACK);
  gfx.setTextDatum(top_left);
  gfx.setTextSize(1);
  gfx.setCursor(6, 6);
  gfx.printf("%s", gWifiConnected ? "WIFI" : "OFF");
  gfx.setTextColor(accent, TFT_BLACK);
  gfx.setCursor(screenW / 2 - 10, 6);
  String displayState = dizzy ? String("DIZ") : stateLabel(gState);
  gfx.printf("%s", displayState.c_str());
  gfx.setTextColor(TFT_WHITE, TFT_BLACK);
  gfx.setCursor(screenW - 28, 6);
  gfx.printf("%d%%", batteryLevel());

  drawPetFace(gfx, screenW / 2, avatarTop + avatarH / 2, screenW - 10, avatarH);

  gfx.fillRoundRect(5, panelY, screenW - 10, panelH, 7, panelFill);
  gfx.drawRoundRect(5, panelY, screenW - 10, panelH, 7, accent);
  gfx.drawFastHLine(12, panelY + 5, screenW - 24, dimCyan);
  gfx.fillCircle(12 + ((now / 90) % std::max(1, screenW - 24)), panelY + 5, 2, accent);
  String displayText = dizzy ? String("Dizzy...") : gBubbleText;
  drawVerticalScrollText(gfx, displayText, 10, panelY + 13, screenW - 20, 32, TFT_WHITE, panelFill);
  gfx.endWrite();
  if (gUiCanvasReady) {
    M5.Display.startWrite();
    gUiCanvas.pushSprite(&M5.Display, 0, 0);
    M5.Display.endWrite();
  }
}

void enableMicMode() {
  M5.Speaker.end();
  if (!M5.Mic.isEnabled()) {
    M5.Mic.begin();
  }
  Serial.printf("[pet] mic enabled=%d\n", M5.Mic.isEnabled() ? 1 : 0);
}

void enableSpeakerMode() {
  if (M5.Mic.isEnabled()) {
    M5.Mic.end();
  }
  if (!M5.Speaker.isEnabled()) {
    M5.Speaker.begin();
  }
  M5.Speaker.setVolume(PET_SPEAKER_VOLUME);
  Serial.printf("[pet] speaker enabled=%d volume=%u\n", M5.Speaker.isEnabled() ? 1 : 0, PET_SPEAKER_VOLUME);
}

void playDebugBeep(uint16_t frequency = 1200, uint16_t durationMs = 120) {
  enableSpeakerMode();
  const bool started = M5.Speaker.tone(static_cast<float>(frequency), durationMs, 0, true);
  Serial.printf("[pet] debug beep start=%d freq=%u duration=%u\n",
                started ? 1 : 0,
                static_cast<unsigned>(frequency),
                static_cast<unsigned>(durationMs));
  delay(durationMs + 40);
}

std::vector<uint8_t> buildWav(const int16_t* samples, size_t sampleCount) {
  const uint32_t dataSize = static_cast<uint32_t>(sampleCount * sizeof(int16_t));
  std::vector<uint8_t> wav;
  wav.reserve(dataSize + 44);

  auto appendString = [&](const char* value) {
    while (*value) {
      wav.push_back(static_cast<uint8_t>(*value));
      ++value;
    }
  };
  auto append32 = [&](uint32_t value) {
    wav.push_back(static_cast<uint8_t>(value & 0xFF));
    wav.push_back(static_cast<uint8_t>((value >> 8) & 0xFF));
    wav.push_back(static_cast<uint8_t>((value >> 16) & 0xFF));
    wav.push_back(static_cast<uint8_t>((value >> 24) & 0xFF));
  };
  auto append16 = [&](uint16_t value) {
    wav.push_back(static_cast<uint8_t>(value & 0xFF));
    wav.push_back(static_cast<uint8_t>((value >> 8) & 0xFF));
  };

  appendString("RIFF");
  append32(dataSize + 36);
  appendString("WAVEfmt ");
  append32(16);
  append16(1);
  append16(1);
  append32(kSampleRate);
  append32(kSampleRate * 2);
  append16(2);
  append16(16);
  appendString("data");
  append32(dataSize);

  const uint8_t* raw = reinterpret_cast<const uint8_t*>(samples);
  wav.insert(wav.end(), raw, raw + dataSize);
  return wav;
}

bool loadPendingQueue(DynamicJsonDocument& doc) {
  if (!SPIFFS.exists(kPendingIndexPath)) {
    doc.to<JsonArray>();
    return true;
  }
  File file = SPIFFS.open(kPendingIndexPath, FILE_READ);
  if (!file) {
    return false;
  }
  DeserializationError error = deserializeJson(doc, file);
  file.close();
  if (error) {
    doc.to<JsonArray>();
    return false;
  }
  return true;
}

bool savePendingQueue(const DynamicJsonDocument& doc) {
  File file = SPIFFS.open(kPendingIndexPath, FILE_WRITE);
  if (!file) {
    return false;
  }
  serializeJson(doc, file);
  file.close();
  return true;
}

bool enqueuePendingUpload(const std::vector<uint8_t>& wavBytes) {
  const String itemId = String(millis());
  const String wavPath = "/" + itemId + ".wav";

  File wavFile = SPIFFS.open(wavPath, FILE_WRITE);
  if (!wavFile) {
    return false;
  }
  wavFile.write(wavBytes.data(), wavBytes.size());
  wavFile.close();

  DynamicJsonDocument doc(2048);
  loadPendingQueue(doc);
  JsonArray queue = doc.as<JsonArray>();
  JsonObject item = queue.add<JsonObject>();
  item["id"] = itemId;
  item["wav_path"] = wavPath;
  item["session_id"] = PET_SESSION_ID;
  item["battery_level"] = batteryLevel();
  return savePendingQueue(doc);
}

bool popPendingUpload(PendingUpload& upload) {
  DynamicJsonDocument doc(2048);
  loadPendingQueue(doc);
  JsonArray queue = doc.as<JsonArray>();
  if (queue.isNull() || queue.size() == 0) {
    return false;
  }
  JsonObject first = queue[0];
  upload.id = first["id"] | "";
  upload.wavPath = first["wav_path"] | "";
  upload.sessionId = first["session_id"] | PET_SESSION_ID;
  upload.batteryLevel = first["battery_level"] | -1;

  queue.remove(0);
  savePendingQueue(doc);
  return true;
}

void pushFrontPendingUpload(const PendingUpload& upload) {
  DynamicJsonDocument existing(2048);
  loadPendingQueue(existing);

  DynamicJsonDocument reordered(2048);
  JsonArray target = reordered.to<JsonArray>();
  JsonObject first = target.add<JsonObject>();
  first["id"] = upload.id;
  first["wav_path"] = upload.wavPath;
  first["session_id"] = upload.sessionId;
  first["battery_level"] = upload.batteryLevel;

  for (JsonObject item : existing.as<JsonArray>()) {
    JsonObject copy = target.add<JsonObject>();
    copy["id"] = item["id"] | "";
    copy["wav_path"] = item["wav_path"] | "";
    copy["session_id"] = item["session_id"] | PET_SESSION_ID;
    copy["battery_level"] = item["battery_level"] | -1;
  }
  savePendingQueue(reordered);
}

bool readFileBytes(const String& path, std::vector<uint8_t>& bytes) {
  File file = SPIFFS.open(path, FILE_READ);
  if (!file) {
    return false;
  }
  bytes.clear();
  bytes.reserve(file.size());
  while (file.available()) {
    bytes.push_back(static_cast<uint8_t>(file.read()));
  }
  file.close();
  return true;
}

void deleteFileIfExists(const String& path) {
  if (SPIFFS.exists(path)) {
    SPIFFS.remove(path);
  }
}

class MultipartBodyStream : public Stream {
 public:
  MultipartBodyStream(String prefix, const std::vector<uint8_t>& payload, String suffix)
      : prefix_(std::move(prefix)), payload_(payload), suffix_(std::move(suffix)) {}

  size_t size() const {
    return prefix_.length() + payload_.size() + suffix_.length();
  }

  int available() override {
    const size_t remaining = size() - position_;
    return remaining > static_cast<size_t>(INT32_MAX) ? INT32_MAX : static_cast<int>(remaining);
  }

  int read() override {
    if (position_ >= size()) {
      return -1;
    }
    return readByteAt(position_++);
  }

  int peek() override {
    if (position_ >= size()) {
      return -1;
    }
    return readByteAt(position_);
  }

  size_t readBytes(uint8_t* buffer, size_t length) override {
    size_t copied = 0;
    while (copied < length && position_ < size()) {
      buffer[copied++] = static_cast<uint8_t>(readByteAt(position_++));
    }
    return copied;
  }

  void flush() override {}

  size_t write(uint8_t) override {
    return 0;
  }

 private:
  int readByteAt(size_t index) const {
    if (index < prefix_.length()) {
      return static_cast<uint8_t>(prefix_[index]);
    }
    index -= prefix_.length();
    if (index < payload_.size()) {
      return payload_[index];
    }
    index -= payload_.size();
    return static_cast<uint8_t>(suffix_[index]);
  }

  String prefix_;
  const std::vector<uint8_t>& payload_;
  String suffix_;
  size_t position_ = 0;
};

struct HttpEndpoint {
  bool secure = false;
  String host;
  uint16_t port = 80;
  String basePath;
};

bool parseHttpEndpoint(const String& baseUrl, HttpEndpoint& endpoint) {
  String value = baseUrl;
  endpoint.secure = false;
  if (value.startsWith("https://")) {
    endpoint.secure = true;
    value.remove(0, 8);
  } else if (value.startsWith("http://")) {
    value.remove(0, 7);
  } else {
    return false;
  }
  int slash = value.indexOf('/');
  String hostPort = slash >= 0 ? value.substring(0, slash) : value;
  endpoint.basePath = slash >= 0 ? value.substring(slash) : "";

  int colon = hostPort.indexOf(':');
  if (colon >= 0) {
    endpoint.host = hostPort.substring(0, colon);
    endpoint.port = static_cast<uint16_t>(hostPort.substring(colon + 1).toInt());
  } else {
    endpoint.host = hostPort;
    endpoint.port = endpoint.secure ? 443 : 80;
  }
  endpoint.host.trim();
  return endpoint.host.length() > 0 && endpoint.port > 0;
}

std::unique_ptr<Client> connectHttpClient(const HttpEndpoint& endpoint) {
  if (endpoint.secure) {
    std::unique_ptr<WiFiClientSecure> client(new WiFiClientSecure());
    client->setInsecure();
    if (!client->connect(endpoint.host.c_str(), endpoint.port)) {
      return nullptr;
    }
    return client;
  }

  std::unique_ptr<WiFiClient> client(new WiFiClient());
  if (!client->connect(endpoint.host.c_str(), endpoint.port)) {
    return nullptr;
  }
  return client;
}

bool readHttpResponse(Client& client, int& statusCode, String& body) {
  const uint32_t start = millis();
  while (!client.available() && client.connected() && millis() - start < kHttpTimeoutMs) {
    delay(10);
  }
  if (!client.available()) {
    return false;
  }

  String statusLine = client.readStringUntil('\n');
  statusLine.trim();
  const int firstSpace = statusLine.indexOf(' ');
  const int secondSpace = statusLine.indexOf(' ', firstSpace + 1);
  if (firstSpace < 0) {
    return false;
  }
  statusCode = statusLine.substring(firstSpace + 1, secondSpace > 0 ? secondSpace : statusLine.length()).toInt();

  int contentLength = -1;
  while (client.connected()) {
    String header = client.readStringUntil('\n');
    header.trim();
    if (header.isEmpty()) {
      break;
    }
    String lower = header;
    lower.toLowerCase();
    if (lower.startsWith("content-length:")) {
      contentLength = header.substring(header.indexOf(':') + 1).toInt();
    }
  }

  body = "";
  const uint32_t bodyStart = millis();
  while ((client.connected() || client.available()) && millis() - bodyStart < kHttpTimeoutMs) {
    while (client.available()) {
      body += static_cast<char>(client.read());
      if (contentLength >= 0 && body.length() >= contentLength) {
        return true;
      }
    }
    delay(5);
  }
  return true;
}

bool sendHttpGet(const String& url, int& statusCode, String& responseText) {
  HttpEndpoint endpoint;
  if (!parseHttpEndpoint(url, endpoint)) {
    return false;
  }

  auto client = connectHttpClient(endpoint);
  if (!client) {
    return false;
  }

  const String path = endpoint.basePath.length() ? endpoint.basePath : "/";
  client->printf("GET %s HTTP/1.1\r\n", path.c_str());
  client->printf("Host: %s:%u\r\n", endpoint.host.c_str(), endpoint.port);
  client->print("Connection: close\r\n\r\n");
  const bool ok = readHttpResponse(*client, statusCode, responseText);
  client->stop();
  return ok;
}

bool sendHttpGetBinary(const String& url, int& statusCode, std::vector<uint8_t>& responseBytes) {
  HttpEndpoint endpoint;
  if (!parseHttpEndpoint(url, endpoint)) {
    return false;
  }

  auto client = connectHttpClient(endpoint);
  if (!client) {
    return false;
  }

  const String path = endpoint.basePath.length() ? endpoint.basePath : "/";
  client->printf("GET %s HTTP/1.1\r\n", path.c_str());
  client->printf("Host: %s:%u\r\n", endpoint.host.c_str(), endpoint.port);
  client->print("Connection: close\r\n\r\n");

  const uint32_t start = millis();
  while (!client->available() && client->connected() && millis() - start < kHttpTimeoutMs) {
    delay(10);
  }
  if (!client->available()) {
    client->stop();
    return false;
  }

  String statusLine = client->readStringUntil('\n');
  statusLine.trim();
  const int firstSpace = statusLine.indexOf(' ');
  const int secondSpace = statusLine.indexOf(' ', firstSpace + 1);
  if (firstSpace < 0) {
    client->stop();
    return false;
  }
  statusCode = statusLine.substring(firstSpace + 1, secondSpace > 0 ? secondSpace : statusLine.length()).toInt();

  int contentLength = -1;
  while (client->connected()) {
    String header = client->readStringUntil('\n');
    header.trim();
    if (header.isEmpty()) {
      break;
    }
    String lower = header;
    lower.toLowerCase();
    if (lower.startsWith("content-length:")) {
      contentLength = header.substring(header.indexOf(':') + 1).toInt();
    }
  }

  responseBytes.clear();
  if (contentLength > 0) {
    responseBytes.reserve(contentLength);
  }

  uint8_t buffer[512];
  const uint32_t bodyStart = millis();
  while ((client->connected() || client->available()) && millis() - bodyStart < kHttpTimeoutMs) {
    const int available = client->available();
    if (available <= 0) {
      delay(5);
      continue;
    }
    const size_t toRead = std::min(static_cast<size_t>(available), sizeof(buffer));
    const int readCount = client->read(buffer, toRead);
    if (readCount <= 0) {
      break;
    }
    responseBytes.insert(responseBytes.end(), buffer, buffer + readCount);
    if (contentLength >= 0 && static_cast<int>(responseBytes.size()) >= contentLength) {
      break;
    }
  }

  client->stop();
  return true;
}

String absoluteUrl(const String& maybeRelative) {
  if (maybeRelative.startsWith("http://") || maybeRelative.startsWith("https://")) {
    return maybeRelative;
  }
  String base = PET_API_BASE_URL;
  if (maybeRelative.startsWith("/")) {
    return base + maybeRelative;
  }
  return base + "/" + maybeRelative;
}

bool uploadVoiceTurn(const std::vector<uint8_t>& wavBytes, const String& sessionId, int currentBatteryLevel, String& turnId) {
  if (WiFi.status() != WL_CONNECTED) {
    gLastUploadError = "WiFi disconnected";
    Serial.println("[pet] upload skipped: wifi disconnected");
    return false;
  }

  Serial.printf("[pet] upload start wav_bytes=%u session=%s battery=%d free_heap=%u\n",
                static_cast<unsigned>(wavBytes.size()),
                sessionId.c_str(),
                currentBatteryLevel,
                static_cast<unsigned>(ESP.getFreeHeap()));

  const String boundary = "----M5PetBoundary";
  const String prefix = "--" + boundary + "\r\nContent-Disposition: form-data; name=\"device_id\"\r\n\r\n" +
                        String(PET_DEVICE_ID) + "\r\n" +
                        "--" + boundary + "\r\nContent-Disposition: form-data; name=\"session_id\"\r\n\r\n" + sessionId +
                        "\r\n" +
                        "--" + boundary + "\r\nContent-Disposition: form-data; name=\"battery_level\"\r\n\r\n" +
                        String(currentBatteryLevel) + "\r\n" +
                        "--" + boundary + "\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"turn.wav\"\r\n"
                        "Content-Type: audio/wav\r\n\r\n";
  const String suffix = "\r\n--" + boundary + "--\r\n";
  MultipartBodyStream bodyStream(prefix, wavBytes, suffix);
  HttpEndpoint endpoint;
  if (!parseHttpEndpoint(String(PET_API_BASE_URL), endpoint)) {
    gLastUploadError = "Bad API URL";
    Serial.println("[pet] upload failed: invalid api base url");
    return false;
  }

  auto client = connectHttpClient(endpoint);
  if (!client) {
    gLastUploadError = "Connect failed";
    Serial.println("[pet] upload failed: connect failed");
    return false;
  }

  const String path = (endpoint.basePath.length() ? endpoint.basePath : "") + "/api/companion/voice-turns";
  client->printf("POST %s HTTP/1.1\r\n", path.c_str());
  client->printf("Host: %s:%u\r\n", endpoint.host.c_str(), endpoint.port);
  client->print("Connection: close\r\n");
  client->printf("Content-Type: multipart/form-data; boundary=%s\r\n", boundary.c_str());
  client->printf("Content-Length: %u\r\n\r\n", static_cast<unsigned>(bodyStream.size()));

  uint8_t chunk[512];
  while (bodyStream.available() > 0) {
    const size_t count = bodyStream.readBytes(chunk, sizeof(chunk));
    if (!count) {
      break;
    }
    const size_t written = client->write(chunk, count);
    if (written != count) {
      gLastUploadError = "Socket write failed";
      Serial.printf("[pet] upload failed: short write %u/%u\n", static_cast<unsigned>(written), static_cast<unsigned>(count));
      client->stop();
      return false;
    }
  }
  client->flush();

  int statusCode = 0;
  String responseText;
  if (!readHttpResponse(*client, statusCode, responseText)) {
    gLastUploadError = "No HTTP response";
    Serial.println("[pet] upload failed: no http response");
    client->stop();
    return false;
  }
  client->stop();

  Serial.printf("[pet] upload response status=%d body_bytes=%u free_heap=%u\n",
                statusCode,
                static_cast<unsigned>(bodyStream.size()),
                static_cast<unsigned>(ESP.getFreeHeap()));
  if (statusCode != 201) {
    gLastUploadError = "HTTP " + String(statusCode);
    Serial.printf("[pet] upload failed body=%s\n", responseText.c_str());
    return false;
  }

  DynamicJsonDocument doc(1024);
  Serial.printf("[pet] upload ok raw=%s\n", responseText.c_str());
  DeserializationError error = deserializeJson(doc, responseText);
  if (error) {
    gLastUploadError = "Bad JSON response";
    Serial.println("[pet] upload response parse failed");
    return false;
  }
  turnId = doc["turn_id"] | "";
  gEmotion = doc["emotion"] | "neutral";
  gExpression = doc["expression"] | "thinking";
  gLastUploadError = "";
  return turnId.length() > 0;
}

bool parseWavInfo(const std::vector<uint8_t>& wavBytes, WavInfo& info) {
  if (wavBytes.size() < 44) {
    return false;
  }
  auto read16 = [&](size_t offset) -> uint16_t {
    return static_cast<uint16_t>(wavBytes[offset] | (wavBytes[offset + 1] << 8));
  };
  auto read32 = [&](size_t offset) -> uint32_t {
    return static_cast<uint32_t>(wavBytes[offset] | (wavBytes[offset + 1] << 8) | (wavBytes[offset + 2] << 16) |
                                 (wavBytes[offset + 3] << 24));
  };

  info.channels = read16(22);
  info.sampleRate = read32(24);
  info.bitsPerSample = read16(34);

  for (size_t offset = 12; offset + 8 <= wavBytes.size();) {
    const uint32_t chunkSize = read32(offset + 4);
    if (wavBytes[offset] == 'd' && wavBytes[offset + 1] == 'a' && wavBytes[offset + 2] == 't' && wavBytes[offset + 3] == 'a') {
      info.dataOffset = offset + 8;
      return true;
    }
    offset += 8 + chunkSize;
  }
  return false;
}

bool downloadBinary(const String& url, std::vector<uint8_t>& bytes) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }
  int statusCode = 0;
  if (!sendHttpGetBinary(absoluteUrl(url), statusCode, bytes) || statusCode != 200) {
    return false;
  }
  return !bytes.empty();
}

bool startPlayback(const std::vector<uint8_t>& wavBytes) {
  WavInfo info;
  if (!parseWavInfo(wavBytes, info) || info.channels != 1 || info.bitsPerSample != 16 || info.dataOffset >= wavBytes.size()) {
    Serial.println("[pet] playback rejected: invalid wav");
    return false;
  }
  enableSpeakerMode();
  playDebugBeep(1600, 120);
  gSpeakingAudio = wavBytes;
  const size_t bytesPerFrame = static_cast<size_t>(info.channels) * static_cast<size_t>(info.bitsPerSample / 8);
  const size_t pcmBytes = gSpeakingAudio.size() - info.dataOffset;
  const uint32_t frameCount = bytesPerFrame == 0 ? 0 : static_cast<uint32_t>(pcmBytes / bytesPerFrame);
  const uint32_t durationMs = info.sampleRate == 0 ? 0 : static_cast<uint32_t>((1000ULL * frameCount) / info.sampleRate);
  gPlaybackExpectedUntil = millis() + durationMs + 180;
  Serial.printf("[pet] playback prestart heap=%u psram=%u size=%u\n",
                static_cast<unsigned>(ESP.getFreeHeap()),
                static_cast<unsigned>(ESP.getFreePsram()),
                static_cast<unsigned>(gSpeakingAudio.size()));
  const bool started = M5.Speaker.playWav(gSpeakingAudio.data(), gSpeakingAudio.size(), 1, 0, true);
  Serial.printf("[pet] playback start=%d wav_bytes=%u sample_rate=%u\n",
                started ? 1 : 0,
                static_cast<unsigned>(gSpeakingAudio.size()),
                static_cast<unsigned>(info.sampleRate));
  Serial.printf("[pet] playback duration_ms=%u expected_until=%u\n",
                static_cast<unsigned>(durationMs),
                static_cast<unsigned>(gPlaybackExpectedUntil));
  if (!started) {
    gPlaybackExpectedUntil = 0;
    return false;
  }
  setState(DeviceState::Speaking, gBubbleText, "speaking");
  return true;
}

void stopPlayback() {
  M5.Speaker.end();
  gSpeakingAudio.clear();
  gPlaybackExpectedUntil = 0;
  enableMicMode();
}

bool pollVoiceTurn() {
  if (WiFi.status() != WL_CONNECTED || gActiveTurnId.isEmpty()) {
    return false;
  }
  int statusCode = 0;
  String responseText;
  if (!sendHttpGet(absoluteUrl("/api/companion/voice-turns/" + gActiveTurnId), statusCode, responseText) || statusCode != 200) {
    return false;
  }
  DynamicJsonDocument doc(2048);
  DeserializationError error = deserializeJson(doc, responseText);
  if (error) {
    return false;
  }

  const String status = doc["status"] | "";
  gEmotion = doc["emotion"] | "neutral";
  gExpression = doc["expression"] | "thinking";
  gCurrentReplyText = doc["display_text"] | doc["reply_text"] | "";

  if (status == "processing") {
    setState(DeviceState::Thinking, "Thinking...", "thinking");
    return true;
  }

  if (status == "failed") {
    const String errorText = doc["error"] | "Voice turn failed";
    gActiveTurnId = "";
    gCurrentAudioUrl = "";
    gEmotion = "sad";
    setState(DeviceState::Error, errorText, "error");
    return true;
  }

  gCurrentAudioUrl = doc["audio_url"] | "";
  gBubbleText = gCurrentReplyText.isEmpty() ? String("I am here.") : gCurrentReplyText;
  std::vector<uint8_t> audioBytes;
  if (!gCurrentAudioUrl.isEmpty() && downloadBinary(gCurrentAudioUrl, audioBytes) && startPlayback(audioBytes)) {
    return true;
  }

  gActiveTurnId = "";
  setState(DeviceState::Idle, gBubbleText, "idle");
  return true;
}

void startRecording() {
  stopPlayback();
  enableMicMode();
  gRecordedSampleCount = 0;
  gRecordStartedAt = millis();
  gEmotion = "curious";
  setState(DeviceState::Recording, "Listening... release to send", "listening");
  drawUi();
}

void finishRecording() {
  Serial.printf("[pet] finish recording samples=%u\n", static_cast<unsigned>(gRecordedSampleCount));
  if (gRecordedSampleCount < kMinSpeechSamples) {
    enableMicMode();
    setState(DeviceState::Idle, "Too short, try again", "idle");
    return;
  }

  std::vector<uint8_t> wavBytes = buildWav(gRecordedSamples, gRecordedSampleCount);
  gRecordedSampleCount = 0;
  setState(DeviceState::Uploading, "Uploading voice...", "thinking");
  String turnId;
  if (uploadVoiceTurn(wavBytes, PET_SESSION_ID, batteryLevel(), turnId)) {
    gActiveTurnId = turnId;
    Serial.printf("[pet] upload ok turn=%s\n", turnId.c_str());
    setState(DeviceState::Thinking, "Thinking...", "thinking");
    return;
  }

  Serial.println("[pet] upload failed, queueing");
  enqueuePendingUpload(wavBytes);
  gEmotion = "sleepy";
  setState(DeviceState::Error, gLastUploadError.isEmpty() ? String("Offline, saved for retry") : gLastUploadError, "error");
}

void captureRecording() {
  static int16_t chunk[kRecordChunkSamples];
  if (!M5.Mic.isEnabled()) {
    gEmotion = "sad";
    setState(DeviceState::Error, "Mic unavailable", "error");
    return;
  }
  if (M5.Mic.record(chunk, kRecordChunkSamples, kSampleRate)) {
    const size_t remaining = kMaxRecordSamples > gRecordedSampleCount ? kMaxRecordSamples - gRecordedSampleCount : 0;
    const size_t copyCount = std::min(remaining, kRecordChunkSamples);
    if (copyCount > 0) {
      memcpy(&gRecordedSamples[gRecordedSampleCount], chunk, copyCount * sizeof(int16_t));
      gRecordedSampleCount += copyCount;
    }
  }
  if (millis() - gRecordStartedAt >= PET_MAX_RECORD_MS) {
    finishRecording();
  }
}

void flushPendingUploads() {
  if (gState != DeviceState::Idle || WiFi.status() != WL_CONNECTED) {
    return;
  }
  PendingUpload upload;
  if (!popPendingUpload(upload)) {
    return;
  }

  std::vector<uint8_t> wavBytes;
  if (!readFileBytes(upload.wavPath, wavBytes)) {
    deleteFileIfExists(upload.wavPath);
    return;
  }

  String turnId;
  if (!uploadVoiceTurn(wavBytes, upload.sessionId, upload.batteryLevel, turnId)) {
    pushFrontPendingUpload(upload);
    return;
  }

  deleteFileIfExists(upload.wavPath);
  gActiveTurnId = turnId;
  setState(DeviceState::Thinking, "Queued voice sent", "thinking");
}

void updateStateMachine() {
  if (gState == DeviceState::Speaking && gPlaybackExpectedUntil != 0 && millis() >= gPlaybackExpectedUntil) {
    Serial.printf("[pet] playback finished isPlaying=%d now=%u expected_until=%u\n",
                  M5.Speaker.isPlaying() ? 1 : 0,
                  static_cast<unsigned>(millis()),
                  static_cast<unsigned>(gPlaybackExpectedUntil));
    gActiveTurnId = "";
    gCurrentAudioUrl = "";
    gExpression = "idle";
    enableMicMode();
    setState(DeviceState::Idle, gBubbleText, "idle");
  }

  if (gState == DeviceState::Error && millis() - gStateChangedAt > 2500) {
    setState(DeviceState::Idle, "Hold BtnA to talk", "idle");
  }

  if (gState == DeviceState::Thinking && millis() - gLastPollAt >= PET_POLL_INTERVAL_MS) {
    gLastPollAt = millis();
    pollVoiceTurn();
  }

  flushPendingUploads();
}

}  // namespace

void setup() {
  auto cfg = M5.config();
  cfg.clear_display = true;
  cfg.internal_spk = true;
  cfg.internal_mic = true;
  cfg.internal_imu = true;
  cfg.serial_baudrate = 115200;
  M5.begin(cfg);
  Serial.begin(115200);
  delay(150);
  M5.Display.setRotation(0);
  M5.Display.setFont(&fonts::efontCN_14);
  M5.Display.setTextColor(TFT_WHITE);
  M5.Display.setTextSize(1);
  gUiCanvas.setColorDepth(16);
  gUiCanvasReady = gUiCanvas.createSprite(M5.Display.width(), M5.Display.height()) != nullptr;
  if (gUiCanvasReady) {
    gUiCanvas.setFont(&fonts::efontCN_14);
    gUiCanvas.setTextColor(TFT_WHITE);
    gUiCanvas.setTextSize(1);
    Serial.printf("[pet] ui canvas ready width=%d height=%d\n", gUiCanvas.width(), gUiCanvas.height());
  } else {
    Serial.println("[pet] ui canvas unavailable, drawing direct");
  }
  SPIFFS.begin(true);
  Serial.printf("[pet] psram found=%d total=%u free=%u heap=%u\n",
                psramFound() ? 1 : 0,
                static_cast<unsigned>(ESP.getPsramSize()),
                static_cast<unsigned>(ESP.getFreePsram()),
                static_cast<unsigned>(ESP.getFreeHeap()));
  playDebugBeep(1200, 120);

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(PET_WIFI_SSID, PET_WIFI_PASSWORD);
  Serial.printf("[pet] boot ssid=%s api=%s\n", PET_WIFI_SSID, PET_API_BASE_URL);
  enableMicMode();
  gEmotion = "neutral";
  setState(DeviceState::Idle, "Hold BtnA to talk", "idle");
}

void loop() {
  M5.update();
  ensureWifi();
  updateShakeGesture();
  const bool btnADown = M5.BtnA.isPressed();

  if (gState == DeviceState::Speaking && btnADown && !gBtnAWasDown) {
    stopPlayback();
    startRecording();
  } else if (gState != DeviceState::Recording && btnADown && !gBtnAWasDown) {
    startRecording();
  }

  if (gState == DeviceState::Recording) {
    captureRecording();
    if (!btnADown && gBtnAWasDown) {
      finishRecording();
    }
  }

  updateStateMachine();
  drawUi();
  gBtnAWasDown = btnADown;
  delay(10);
}
