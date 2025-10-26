# PowerPack Controller R2M1 - v2.0.0

## 📋 Overview

This application controls the HW_BO_POWERPACK_R2M1 board via USB CDC.

## ✨ Features

- **2 Independent Relay Control** (GPIO_M1 and GPIO_M2)
- **2 Channel Dimmer Control** (0-10V output, GP8413 DAC)
- **USB CDC Communication**
- **Status Monitoring**
- **Graphical User Interface (GUI)**
- **Heartbeat LED Indicator**

## 🚀 Quick Start

### Step 1: Hardware Connection
1. Connect your STM32 board to the computer via USB cable
2. Windows should automatically recognize the device (STM32 Virtual COM Port)

### Step 2: Run Application
1. Double-click `PowerPack_Controller_R2M1_v2.0.0.exe` to run
2. No installation required - it's a standalone executable

### Step 3: Connect
1. Select the correct COM port from the **USB Port** dropdown
2. Click the **"Connect"** button
3. If successful, the green LED will start pulsing

### Step 4: Control
- **Relay 1 & Relay 2:** Use ON/OFF checkboxes to control
- **Dimmer 1 & Dimmer 2:** 
  - Enable with "Enable" checkbox
  - Adjust 0-100% with slider

### Additional Buttons
- **Get Status:** Request status information from device
- **Get Version:** Check firmware version
- **Debug Test:** Run USB communication test
- **All OFF:** Turn off all outputs
- **Test Sequence:** Run automated test sequence

## 📊 Technical Specifications

### Hardware
- **MCU:** STM32F103C8T6
- **Relay Control:** 
  - Relay 1: GPIO_M1 (PB13)
  - Relay 2: GPIO_M2 (PB12)
- **Dimmer Control:**
  - DAC: GP8413 (I2C)
  - Output: 0-10V analog
  - Enable 1: DIM_OUT_EN_1 (PB0)
  - Enable 2: DIM_OUT_EN_2 (PB1)
- **Communication:** USB CDC (Virtual COM Port)

### Software
- **Python Version:** v2.0.0
- **Firmware Version:** v2.0.0
- **Communication Protocol:**
  - Baud Rate: 115200
  - Data Bits: 8
  - Parity: None
  - Stop Bits: 1

## 🔧 Troubleshooting

### "Connection Failed" Error
1. Ensure USB cable is properly connected
2. Verify correct COM port is selected
3. Another program may be using the COM port - close it
4. Unplug and reconnect the device

### "Device Not Found" Error
1. Ensure STM32 USB driver is installed
2. Check COM port in Windows Device Manager
3. Verify firmware is loaded on the device

### Relays Not Working
1. Ensure power supply is connected
2. Check relay status with "Get Status"
3. Both relays work independently - test both

### No Dimmer Output
1. Ensure "Enable" checkbox is checked
2. Verify slider value is not 0%
3. Measure 0-10V output with multimeter

## 📝 Command Line Usage

For advanced users, CLI mode:

```bash
PowerPack_Controller_R2M1_v2.0.0.exe --cli
```

Available commands:
- `connect_usb [port]` - Connect via USB
- `relay <1|2> <on|off>` - Control relay
- `dimmer <1|2> <0-100>` - Set dimmer percentage
- `enable_dimmer <1|2>` - Enable dimmer
- `disable_dimmer <1|2>` - Disable dimmer
- `status` - Get status
- `version` - Get version
- `quit` - Exit

## ⚠️ Compatibility

**Important:** This version is only compatible with R2M1 hardware!

- ✅ **Compatible:** HW_BO_POWERPACK_R2M1 + Firmware v2.0.0
- ❌ **Incompatible:** HW_BO_POWERPACK_R1M1 + Firmware v1.0.0

Differences between R1M1 and R2M1:
- **R1M1:** 1 latching relay (SET/RESET control)
- **R2M1:** 2 independent relays (direct control)

## 📞 Support

If you experience issues:
1. Check messages in status window
2. Test communication with "Debug Test"
3. Restart device (unplug-replug)
4. Close and reopen application

## 📄 License

© 2025 BlackOcean Technologies
All rights reserved.

---

**Last Update:** October 25, 2025  
**Version:** 2.0.0  
**Hardware:** R2M1


