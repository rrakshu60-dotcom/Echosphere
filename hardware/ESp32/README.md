# 🔊 EchoSphere ESP32 Smart Speaker & Live Notice Display Node

Native C++/Arduino firmware for the **Classic 38-Pin ESP32 NodeMCU DevKit** with:
1. **MAX98357A I2S 3W Class-D Amplifier** connected to an **8Ω Speaker**.
2. **1.8" Color TFT LCD Screen (128x160 SPI ST7735)** in rich 160x128 landscape mode.
3. **Discrete Status LEDs** (Notice Broadcasting LED on GPIO 21, Heartbeat LED on GPIO 22).

This firmware replaces the Python edge speaker clients (`speaker_node_client.py` and `speaker_node_client_2.py`) with hardware firmware directly communicating with the EchoSphere backend.

---

## ⚡ System Highlights

1. **Native Smart Speaker Edge Client**:
   - Replaces the Python edge clients with pure C++/Arduino firmware running on the ESP32.
   - Auto-registers with the EchoSphere backend (`POST /api/v1/hardware/speakers/register`).
   - Sends telemetry heartbeats every 3 seconds to keep node status **ONLINE** in the app.
   - Responds to all app commands: `TEST_SPEAKER`, `PLAY_ANNOUNCEMENT`, `PLAY_EMERGENCY`, `PAUSE`, `RESUME`, `STOP`, `SET_VOLUME`, `RESTART`.
   - Delivers 16-bit PCM digital audio over hardware **I2S** to the **MAX98357A 3W amplifier** and **8Ω speaker**:
     - Campus attention chime (587Hz -> 880Hz)
     - Emergency alarm siren sweeps (650Hz <-> 1400Hz frequency modulation)
     - Announcement melody jingles and diagnostic self-tests
   - Automatically notifies the backend when playback finishes (`POST /api/v1/hardware/queue/{id}/action?action=complete`) so the queue **auto-advances** in the app!

2. **1.8" Color TFT Display & Status LED Ticker**:
   - **While Broadcasting (`NOW BROADCASTING`)**:
     - Displays `> NOW BROADCASTING` (or flashing red `! EMERGENCY BROADCAST !`).
     - Notice Title with smooth horizontal scrolling ticker for long titles.
     - Priority Badge (`[HIGH]`, `[NORMAL]`, `[EMERGENCY]`) and Department (`AIML`, `College-Wide`).
     - Dynamic 16-bar color audio visualizer (` ▄█▀█▄ `) dancing while the audio plays through the 8Ω speaker.
     - **Broadcasting LED (GPIO 21)** turns **ON** (solid for normal, strobe flash for emergency).
   - **When Idle (`TODAY'S NOTICES`)**:
     - Automatically displays `* TODAY'S NOTICE [1/N]`.
     - Cycles smoothly through today's published announcements from the app every 5 seconds.
     - Displays category, department, priority badge, and a smooth scrolling summary ticker.
     - **Broadcasting LED (GPIO 21)** turns **OFF**.
     - **Heartbeat LED (GPIO 22)** pulses briefly every 3 seconds to confirm live server connectivity.
   - **Virtual Serial ASCII Mirror**:
     - Prints structured ASCII display boxes to the Arduino Serial Monitor at 115200 baud for instant debugging.

---

## 📌 Strict Pinout Guard: Zero Outputs on Pins 32 to 39

> [!IMPORTANT]
> **Constraint Enforced**: On the classic 38-pin ESP32 NodeMCU, GPIOs 34, 35, 36 (VP), and 39 (VN) are **Input-Only (GPI)** pins with no output drivers. Pins 32 and 33 are analog/touch pins.  
> **This firmware strictly enforces that ZERO outputs are assigned to GPIOs 32 through 39.**  
> Every output peripheral is wired to safe, robust general-purpose GPIOs `< 32`. Compile-time `static_assert` statements prevent any outputs from ever being assigned to pins 32-39.

### Complete Pin Assignment Table

| Peripheral | Peripheral Pin | ESP32 GPIO | Direction | Safe? | Description |
|---|---|---|---|---|---|
| **MAX98357A** | **BCLK** | **GPIO 26** | OUTPUT | ✅ `< 32` | I2S Bit Clock |
| **MAX98357A** | **LRC** | **GPIO 25** | OUTPUT | ✅ `< 32` | I2S Left/Right Clock (Word Select) |
| **MAX98357A** | **DIN** | **GPIO 27** | OUTPUT | ✅ `< 32` | I2S Serial Audio Data |
| **MAX98357A** | **GND** | **GND** | Power | — | Ground |
| **MAX98357A** | **VIN** | **VIN (5V)** | Power | — | 5V power from USB / power supply |
| **MAX98357A** | **GAIN** | **GND (or float)**| Config | — | Tied to GND for 9dB gain (or float for 12dB) |
| **8Ω Speaker** | **+ / -** | **SPK+ / SPK-** | Audio | — | Wired directly to MAX98357A speaker screw terminals |
| **1.8" TFT SPI**| **SCL / SCK** | **GPIO 18** | OUTPUT | ✅ `< 32` | SPI Serial Clock |
| **1.8" TFT SPI**| **SDA / MOSI**| **GPIO 23** | OUTPUT | ✅ `< 32` | SPI Master Out Slave In |
| **1.8" TFT SPI**| **CS** | **GPIO 5** | OUTPUT | ✅ `< 32` | TFT Chip Select |
| **1.8" TFT SPI**| **DC / A0** | **GPIO 4** | OUTPUT | ✅ `< 32` | TFT Data / Command |
| **1.8" TFT SPI**| **RES / RST** | **GPIO 15** | OUTPUT | ✅ `< 32` | TFT Reset |
| **1.8" TFT SPI**| **BLK / LED** | **3.3V (or VIN)**| Power | — | Backlight power |
| **1.8" TFT SPI**| **VCC** | **3.3V (or 5V)** | Power | — | TFT logic power |
| **1.8" TFT SPI**| **GND** | **GND** | Power | — | Ground |
| **Notice LED** | **Anode (+)** | **GPIO 21** | OUTPUT | ✅ `< 32` | Active Notice LED (via 220Ω resistor) |
| **Heartbeat LED**| **Anode (+)** | **GPIO 22** | OUTPUT | ✅ `< 32` | Telemetry Status LED (via 220Ω resistor) |
| **Onboard LED** | **Blue LED** | **GPIO 2** | OUTPUT | ✅ `< 32` | ESP32 DevKit built-in LED |
| **Test Button** | **Push Button**| **GPIO 34** | INPUT | ✅ Input | Optional hardware self-test button |

---

## 🔌 Circuit Wiring Diagram

```
                 Classic 38-Pin ESP32 NodeMCU
                    +--------------------+
              3V3 --|  [ ]          [ ]  |-- GND
               EN --|  [ ]          [ ]  |-- GPIO 23 ----> TFT SDA / MOSI
    (GPI) GPIO 36 --|  [ ]          [ ]  |-- GPIO 22 ----> [ 220Ω ] -> (+) Heartbeat LED (-) -> GND
    (GPI) GPIO 39 --|  [ ]          [ ]  |-- GPIO 1  (TX)
    (GPI) GPIO 34 --|  [ ]          [ ]  |-- GPIO 3  (RX)
    (GPI) GPIO 35 --|  [ ]          [ ]  |-- GPIO 21 ----> [ 220Ω ] -> (+) Notice LED (-) -> GND
          GPIO 32 --|  [ ]          [ ]  |-- GND
          GPIO 33 --|  [ ]          [ ]  |-- GPIO 19
     I2S  GPIO 25 --|  [ ]          [ ]  |-- GPIO 18 ----> TFT SCL / SCK
     I2S  GPIO 26 --|  [ ]          [ ]  |-- GPIO 5  ----> TFT CS
     I2S  GPIO 27 --|  [ ]          [ ]  |-- GPIO 17
          GPIO 14 --|  [ ]          [ ]  |-- GPIO 16
          GPIO 12 --|  [ ]          [ ]  |-- GPIO 4  ----> TFT DC / A0
              GND --|  [ ]          [ ]  |-- GPIO 0
          GPIO 13 --|  [ ]          [ ]  |-- GPIO 2  ----> Built-in Blue LED
              ... --|  [ ]          [ ]  |-- GPIO 15 ----> TFT RES / RST
              VIN --|  [ ]          [ ]  |-- ...
                    +--------------------+

1. MAX98357A I2S Amplifier:
   - VIN   ---> ESP32 VIN (5V)
   - GND   ---> ESP32 GND
   - BCLK  ---> ESP32 GPIO 26
   - LRC   ---> ESP32 GPIO 25
   - DIN   ---> ESP32 GPIO 27
   - GAIN  ---> Tied to GND (for clean 9dB gain) or leave unconnected (for 12dB)
   - SPK+  ---> 8Ω Speaker (+)
   - SPK-  ---> 8Ω Speaker (-)

2. 1.8" Color TFT LCD (128x160 SPI ST7735):
   - VCC   ---> ESP32 3V3 (or 5V if module has onboard 3.3V regulator)
   - GND   ---> ESP32 GND
   - CS    ---> ESP32 GPIO 5
   - RESET ---> ESP32 GPIO 15
   - A0/DC ---> ESP32 GPIO 4
   - SDA   ---> ESP32 GPIO 23 (MOSI)
   - SCK   ---> ESP32 GPIO 18 (SCLK)
   - LED   ---> ESP32 3V3 (Backlight)

3. Notice Broadcasting LED:
   - Anode (+)  ---> 220Ω resistor ---> ESP32 GPIO 21
   - Cathode(-) ---> ESP32 GND

4. Heartbeat Status LED:
   - Anode (+)  ---> 220Ω resistor ---> ESP32 GPIO 22
   - Cathode(-) ---> ESP32 GND
```

---

## 🛠️ Software Setup & Installation

### Option 1: Arduino IDE

1. **Install ESP32 Board Support**:
   - Go to **File -> Preferences**.
   - In *Additional Boards Manager URLs*, add:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to **Tools -> Board -> Boards Manager**, search for `esp32`, and install.

2. **Install Required Libraries**:
   - Go to **Tools -> Manage Libraries...** and install:
     - `ArduinoJson` (by Benoît Blanchon) — Version 6.x or 7.x
     - `Adafruit ST7735 and ST7789 Library` (by Adafruit)
     - `Adafruit GFX Library` (by Adafruit)

3. **Configure Settings**:
   - Open `hardware/ESp32/config.h`.
   - Update your Wi-Fi credentials:
     ```cpp
     #define WIFI_SSID     "Your_WiFi_Name"
     #define WIFI_PASSWORD "Your_WiFi_Password"
     ```
   - Select node profile:
     - `1` for **Node 1: Hardware Speaker Client 1** (`D4:F3:2D:22:2A:CB`, Auditorium / Campus)
     - `2` for **Node 2: Hardware Speaker Client 2** (`D4:F3:2D:22:2A:CC`, Block B - AI Lab)
     - `0` for **Auto-Detect** (Uses the ESP32's hardware Wi-Fi MAC)

4. **Upload to ESP32**:
   - Select board: **ESP32 Dev Module** (or **NodeMCU-32S**).
   - Select COM port.
   - Click **Upload**.
   - Open **Serial Monitor** at **115200 baud**.

---

### Option 2: PlatformIO (VS Code or CLI)

```bash
cd "hardware/ESp32"
pio run --target upload
pio device monitor --baud 115200
```

---

## 🧪 Testing the Setup

1. **Boot Test**:
   - The ESP32 boots, initializes the 1.8" TFT screen (shows blue header and status), connects to Wi-Fi, and registers with the backend.
   - The node immediately appears **ONLINE** in the EchoSphere app with a green pulse badge.
   - The ESP32 outputs an attention chime over I2S through the MAX98357A to the 8Ω speaker.
   - Heartbeat LED (GPIO 22) flashes every 3 seconds.

2. **Idle Mode (Today's Notices Ticker)**:
   - When no broadcast is running, the 1.8" TFT screen displays `* TODAY'S NOTICE [1/N]`.
   - It rotates through the day's announcements every 5 seconds with priority pills and scrolling text.

3. **Active Broadcast**:
   - Broadcast any notice from the app or trigger an Emergency Override.
   - Notice LED on **GPIO 21** lights up immediately.
   - 8Ω speaker plays the attention chime or emergency siren sweeps.
   - 1.8" TFT screen displays `> NOW BROADCASTING` (or red `! EMERGENCY BROADCAST !`) with the notice title and dynamic dancing multi-color audio equalizer bars.
   - Once playback completes, the ESP32 automatically informs the backend queue (`action=complete`).
   - The queue advances to the next notice, and the TFT returns to the daily notice ticker!
