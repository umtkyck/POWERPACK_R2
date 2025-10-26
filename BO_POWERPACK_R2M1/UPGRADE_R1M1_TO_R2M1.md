# PowerPack Upgrade: R1M1 → R2M1

## Overview
This document describes the changes made to upgrade the PowerPack firmware and Python application from **R1M1** to **R2M1**.

## Hardware Changes

### R1M1 (Previous Version)
- **1 Latching Relay** controlled by SET/RESET signals
  - GPIO_M1 (PB13) = SET signal
  - GPIO_M2 (PB12) = RESET signal
  - ON: M1=HIGH, M2=LOW
  - OFF: M1=LOW, M2=HIGH

### R2M1 (Current Version)
- **2 Independent Relays** controlled separately
  - GPIO_M1 (PB13) = Relay 1 control
  - GPIO_M2 (PB12) = Relay 2 control
  - Each relay: HIGH=ON, LOW=OFF

## Firmware Changes (STM32)

### File: `Core/Src/main.c`

#### 1. Updated Header Documentation
```c
// OLD: HW_BO_POWERPACK_R1M1
// NEW: HW_BO_POWERPACK_R2M1

// OLD: m1 set m2 reset on / m1 reset m2 set off
// NEW: Relay 1 controlled by GPIO_M1 (PB13)
//      Relay 2 controlled by GPIO_M2 (PB12)
```

#### 2. Data Structure Changes
```c
// OLD:
typedef struct {
    uint8_t relay_state;      // Single relay
    ...
} PowerPackState_t;

// NEW:
typedef struct {
    uint8_t relay1_state;     // Relay 1 state
    uint8_t relay2_state;     // Relay 2 state
    ...
} PowerPackState_t;
```

#### 3. Command Definitions
```c
// OLD:
#define CMD_SET_RELAY  0x01  // Single relay command

// NEW:
#define CMD_SET_RELAY1 0x01  // Control Relay 1
#define CMD_SET_RELAY2 0x02  // Control Relay 2
```

#### 4. Firmware Version
```c
// OLD: v1.0.0
// NEW: v2.0.0
```

#### 5. Function Updates

**Set_Relay() Function:**
```c
// OLD: void Set_Relay(uint8_t state)
// NEW: void Set_Relay(uint8_t relay_num, uint8_t state)

// OLD Implementation: SET/RESET latching relay
// NEW Implementation: Direct control of two independent relays
void Set_Relay(uint8_t relay_num, uint8_t state)
{
  if (relay_num == 1) {
    HAL_GPIO_WritePin(GPIO_M1_PORT, GPIO_M1_PIN, state ? GPIO_PIN_SET : GPIO_PIN_RESET);
    powerpack_state.relay1_state = state;
  } else if (relay_num == 2) {
    HAL_GPIO_WritePin(GPIO_M2_PORT, GPIO_M2_PIN, state ? GPIO_PIN_SET : GPIO_PIN_RESET);
    powerpack_state.relay2_state = state;
  }
}
```

**Send_Status_Response() Function:**
```c
// OLD: response[2] = 0; // Reserved
// NEW: response[2] = powerpack_state.relay2_state;
```

## Python Application Changes

### File: `PC_APP/powerpack_controller.py`

#### 1. Version Updates
```python
# OLD:
PYTHON_APP_VERSION = "v1.0.1"
STM32_FIRMWARE_VERSION = "v1.0.0"

# NEW:
PYTHON_APP_VERSION = "v2.0.0"
STM32_FIRMWARE_VERSION = "v2.0.0"
```

#### 2. Command Definitions
```python
# OLD:
CMD_SET_RELAY = 0x01  # Single relay command

# NEW:
CMD_SET_RELAY1 = 0x01  # Control Relay 1
CMD_SET_RELAY2 = 0x02  # Control Relay 2
```

#### 3. Controller Class Updates
```python
# OLD:
self.relay_state = False  # Single relay

# NEW:
self.relay1_state = False  # Relay 1
self.relay2_state = False  # Relay 2
```

#### 4. set_relay() Method
```python
# OLD:
def set_relay(self, state):
    self.send_command(CMD_SET_RELAY, 1 if state else 0)
    self.relay_state = state

# NEW:
def set_relay(self, relay_num, state):
    cmd = CMD_SET_RELAY1 if relay_num == 1 else CMD_SET_RELAY2
    self.send_command(cmd, 1 if state else 0)
    if relay_num == 1:
        self.relay1_state = state
    else:
        self.relay2_state = state
```

#### 5. GUI Updates
```python
# OLD: Single relay control
# - relay_var
# - One checkbox for "Main Relay"

# NEW: Two relay controls
# - relay1_var, relay2_var
# - Two checkboxes for "Relay 1" and "Relay 2"
```

#### 6. Status Response Parsing
```python
# OLD:
status = {
    'relay': bool(data[1]),  # Single relay
    ...
}

# NEW:
status = {
    'relay1': bool(data[1]),  # Relay 1
    'relay2': bool(data[2]),  # Relay 2
    ...
}
```

## Communication Protocol

### Status Response Format (8 bytes)
```
Byte 0: CMD_GET_STATUS (0x05)
Byte 1: Relay 1 State (0=OFF, 1=ON)
Byte 2: Relay 2 State (0=OFF, 1=ON)    <- CHANGED from reserved
Byte 3: Dimmer 1 Value MSB
Byte 4: Dimmer 1 Value LSB
Byte 5: Dimmer 2 Value MSB
Byte 6: Dimmer 2 Value LSB
Byte 7: Dimmer Enable Flags (bit 1=Dimmer1, bit 0=Dimmer2)
```

### Command Format
```
OLD:
- CMD_SET_RELAY (0x01) - Control single relay

NEW:
- CMD_SET_RELAY1 (0x01) - Control Relay 1
- CMD_SET_RELAY2 (0x02) - Control Relay 2
```

## Testing Checklist

### Hardware Tests
- [ ] Relay 1 turns ON/OFF independently
- [ ] Relay 2 turns ON/OFF independently
- [ ] Both relays can be ON simultaneously
- [ ] Dimmer 1 functionality unchanged
- [ ] Dimmer 2 functionality unchanged

### Software Tests
- [ ] Python GUI connects to STM32
- [ ] Firmware version displays as v2.0.0
- [ ] Relay 1 checkbox controls Relay 1
- [ ] Relay 2 checkbox controls Relay 2
- [ ] Status updates correctly show both relay states
- [ ] "All OFF" button turns off both relays
- [ ] Test Sequence runs correctly with both relays

## Backward Compatibility

⚠️ **Breaking Changes:**
- R2M1 firmware is **NOT compatible** with R1M1 Python application
- R2M1 Python application is **NOT compatible** with R1M1 firmware
- The command protocol has changed (CMD_SET_RELAY split into CMD_SET_RELAY1 and CMD_SET_RELAY2)

**Version Matching Required:**
- Firmware v2.0.0 ↔ Python App v2.0.0

## Files Modified

1. `BO_POWERPACK_R2M1/Core/Src/main.c` - Firmware implementation
2. `BO_POWERPACK_R2M1/Core/Inc/main.h` - Already had correct pin definitions
3. `BO_POWERPACK_R2M1/PC_APP/powerpack_controller.py` - Python application

## Summary

The upgrade from R1M1 to R2M1 successfully transitions from:
- ✅ One latching relay (with SET/RESET control) → Two independent relays
- ✅ Single relay command → Separate commands for each relay  
- ✅ Firmware v1.0.0 → v2.0.0
- ✅ Python App v1.0.1 → v2.0.0
- ✅ All other functionality (dimmers, USB CDC, status monitoring) preserved

The hardware now provides more flexible control with two independent relay outputs while maintaining all dimmer control capabilities.


