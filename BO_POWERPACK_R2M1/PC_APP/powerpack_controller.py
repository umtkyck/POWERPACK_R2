#!/usr/bin/env python3
"""
PowerPack Controller - Python Application
Controls HW_BO_POWERPACK_R2M1 board via USB CDC

Features:
- Relay control (2 independent relays)
- Dimmer control (2 channels, 0-10V output)
- Status monitoring
- GUI interface
- Heartbeat LED indicator

Requirements:
pip install pyserial tkinter
"""

import serial
import serial.tools.list_ports
import struct
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import queue
import logging

# Version information
PYTHON_APP_VERSION = "v2.0.0"
STM32_FIRMWARE_VERSION = "v2.0.0"  # Will be updated from device

# Command definitions (must match firmware)
CMD_SET_RELAY1 = 0x01       # Control Relay 1
CMD_SET_RELAY2 = 0x02       # Control Relay 2
CMD_SET_DIMMER1 = 0x03
CMD_SET_DIMMER2 = 0x04
CMD_GET_STATUS = 0x05
CMD_ENABLE_DIMMER1 = 0x06
CMD_ENABLE_DIMMER2 = 0x07
CMD_DISABLE_DIMMER1 = 0x08
CMD_DISABLE_DIMMER2 = 0x09
CMD_GET_VERSION = 0x0A

class PowerPackController:
    def __init__(self):
        self.serial_conn = None
        self.status_queue = queue.Queue()
        self.running = False
        self.status_thread = None
        self.last_communication = 0
        self.communication_timeout = 5.0  # 5 seconds timeout (increased)
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        
        # Device status
        self.relay1_state = False       # Relay 1
        self.relay2_state = False       # Relay 2
        self.dimmer1_value = 0
        self.dimmer2_value = 0
        self.dimmer1_enabled = False
        self.dimmer2_enabled = False
        self.firmware_version = "Unknown"
        
        # Setup logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def find_powerpack_port(self):
        """Find the PowerPack device on USB ports"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "STM32" in port.description or "Virtual COM Port" in port.description:
                return port.device
        return None
    
    def get_port_list_with_descriptions(self):
        """Get list of ports with descriptions"""
        ports = serial.tools.list_ports.comports()
        port_list = []
        for port in ports:
            # Format: "COM3 - STM32 Virtual ComPort"
            port_info = f"{port.device} - {port.description}"
            port_list.append(port_info)
        return port_list
    
    def extract_port_from_selection(self, selection):
        """Extract port name from selection string"""
        if " - " in selection:
            return selection.split(" - ")[0]
        return selection
    
    def connect_usb(self, port=None):
        """Connect to PowerPack via USB CDC"""
        try:
            if port is None:
                port = self.find_powerpack_port()
                if port is None:
                    raise Exception("PowerPack device not found")
            
            # Extract port name if it contains description
            if " - " in port:
                port = port.split(" - ")[0]
            
            self.logger.info(f"=== USB Connection Attempt to {port} ===")
            
            # Close existing connection if any
            if self.serial_conn and self.serial_conn.is_open:
                self.logger.info("Closing existing connection")
                self.serial_conn.close()
                time.sleep(0.5)
            
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=115200,
                timeout=2.0,        # Increased timeout
                write_timeout=2.0,  # Increased timeout
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            self.logger.info(f"Serial port opened: {port}")
            
            # Clear buffers
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            self.logger.info("Buffers cleared")
            
            # Wait for connection to stabilize and check for boot message
            self.logger.info("Waiting 3 seconds for device to stabilize...")
            time.sleep(3)
            
            # Check for any initial data (boot message)
            bytes_waiting = self.serial_conn.in_waiting
            self.logger.info(f"Bytes waiting after stabilization: {bytes_waiting}")
            
            if bytes_waiting > 0:
                boot_data = self.serial_conn.read(bytes_waiting)
                self.logger.info(f"*** Received boot data ({len(boot_data)} bytes): {boot_data}")
                self.logger.info(f"*** Boot data hex: {boot_data.hex()}")
            else:
                self.logger.warning("!!! No boot message received from device !!!")
            
            # Update communication timestamp
            self.last_communication = time.time()
            self.connection_attempts = 0
            
            self.logger.info(f"=== Connection established to {port} ===")
            return True
            
        except Exception as e:
            self.connection_attempts += 1
            self.logger.error(f"!!! USB connection FAILED (attempt {self.connection_attempts}): {e} !!!")
            if self.serial_conn:
                try:
                    self.serial_conn.close()
                except:
                    pass
                self.serial_conn = None
            return False
    
    def disconnect(self):
        """Disconnect from PowerPack"""
        self.running = False
        
        # Stop monitoring thread
        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join(timeout=2.0)  # Wait max 2 seconds
        
        # Close serial connection
        if self.serial_conn:
            try:
                if self.serial_conn.is_open:
                    self.serial_conn.close()
            except Exception as e:
                self.logger.error(f"Error closing serial port: {e}")
            finally:
                self.serial_conn = None
    
    def is_connected(self):
        """Check if device is connected and communicating"""
        if not self.serial_conn:
            self.logger.debug("is_connected: No serial connection")
            return False
        
        # Check if connection is still alive
        try:
            if not self.serial_conn.is_open:
                self.logger.debug("is_connected: Serial port not open")
                return False
        except Exception as e:
            self.logger.debug(f"is_connected: Exception checking port: {e}")
            return False
        
        # Check if we received data within timeout period
        time_since_last_comm = time.time() - self.last_communication
        is_active = time_since_last_comm < self.communication_timeout
        
        self.logger.debug(f"is_connected: Port open, last_comm={time_since_last_comm:.1f}s ago, active={is_active}")
        return is_active
    
    def send_usb_command(self, cmd, param=0, value=0):
        """Send command via USB"""
        if not self.serial_conn or not self.serial_conn.is_open:
            raise Exception("USB not connected")
        
        try:
            # Pack command: cmd(1) + param(1) + value(2) + padding(4)
            data = struct.pack('<BBHBBBB', cmd, param, value, 0, 0, 0, 0)
            
            # Clear input buffer before sending
            self.serial_conn.reset_input_buffer()
            
            # Send command
            bytes_written = self.serial_conn.write(data)
            self.serial_conn.flush()
            
            self.logger.debug(f"Sent command 0x{cmd:02X}, {bytes_written} bytes written")
            
            # Update communication timestamp
            self.last_communication = time.time()
            
        except Exception as e:
            self.logger.error(f"Failed to send USB command: {e}")
            raise
    
    def send_command(self, cmd, param=0, value=0):
        """Send command via USB"""
        try:
            if self.serial_conn:
                self.send_usb_command(cmd, param, value)
                self.logger.info(f"Sent command: 0x{cmd:02X} (param={param}, value={value})")
            else:
                raise Exception("No USB connection available")
        except Exception as e:
            self.logger.error(f"Command send failed: {e}")
            raise
    
    def set_relay(self, relay_num, state):
        """Control relay (1 or 2)"""
        cmd = CMD_SET_RELAY1 if relay_num == 1 else CMD_SET_RELAY2
        self.send_command(cmd, 1 if state else 0)
        
        if relay_num == 1:
            self.relay1_state = state
        else:
            self.relay2_state = state
    
    def set_dimmer(self, dimmer_num, percentage):
        """Set dimmer output (0-100%)"""
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be 0-100")
        
        # Convert percentage to 12-bit DAC value (0-4095)
        dac_value = int((percentage / 100.0) * 4095)
        
        cmd = CMD_SET_DIMMER1 if dimmer_num == 1 else CMD_SET_DIMMER2
        self.send_command(cmd, 0, dac_value)
        
        if dimmer_num == 1:
            self.dimmer1_value = dac_value
        else:
            self.dimmer2_value = dac_value
    
    def enable_dimmer(self, dimmer_num, enable=True):
        """Enable/disable dimmer output"""
        if dimmer_num == 1:
            cmd = CMD_ENABLE_DIMMER1 if enable else CMD_DISABLE_DIMMER1
            self.dimmer1_enabled = enable
        else:
            cmd = CMD_ENABLE_DIMMER2 if enable else CMD_DISABLE_DIMMER2
            self.dimmer2_enabled = enable
        
        self.send_command(cmd)
    
    def debug_test(self):
        """Debug test - send raw commands"""
        try:
            if not self.controller.serial_conn:
                self.update_status("âŒ Not connected")
                return
            
            self.update_status("ðŸ”§ Debug Test: Testing USB communication...")
            
            # Test 1: Simple status command
            self.update_status("ðŸ”§ Test 1: Sending status command (0x05)")
            raw_data = bytes([0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            self.controller.serial_conn.reset_input_buffer()
            self.controller.serial_conn.write(raw_data)
            self.controller.serial_conn.flush()
            time.sleep(1)
            
            if self.controller.serial_conn.in_waiting > 0:
                response = self.controller.serial_conn.read(self.controller.serial_conn.in_waiting)
                self.update_status(f"ðŸ”§ Status Response: {[hex(b) for b in response]}")
            else:
                self.update_status("ðŸ”§ No status response")
            
            # Test 2: Version command
            self.update_status("ðŸ”§ Test 2: Sending version command (0x0A)")
            raw_data = bytes([0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            self.controller.serial_conn.reset_input_buffer()
            self.controller.serial_conn.write(raw_data)
            self.controller.serial_conn.flush()
            time.sleep(1)
            
            if self.controller.serial_conn.in_waiting > 0:
                response = self.controller.serial_conn.read(self.controller.serial_conn.in_waiting)
                self.update_status(f"ðŸ”§ Version Response: {[hex(b) for b in response]}")
            else:
                self.update_status("ðŸ”§ No version response")
            
            # Test 3: Invalid command
            self.update_status("ðŸ”§ Test 3: Sending invalid command (0xFF)")
            raw_data = bytes([0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            self.controller.serial_conn.reset_input_buffer()
            self.controller.serial_conn.write(raw_data)
            self.controller.serial_conn.flush()
            time.sleep(1)
            
            if self.controller.serial_conn.in_waiting > 0:
                response = self.controller.serial_conn.read(self.controller.serial_conn.in_waiting)
                self.update_status(f"ðŸ”§ Invalid Response: {[hex(b) for b in response]}")
            else:
                self.update_status("ðŸ”§ No invalid command response")
            
            self.update_status("ðŸ”§ Debug test completed. Check STM32 LEDs for activity.")
                
        except Exception as e:
            self.update_status(f"ðŸ”§ Debug test failed: {e}")
    
    def get_status(self):
        """Request status from device"""
        self.send_command(CMD_GET_STATUS)
    
    def get_version(self):
        """Request version from device"""
        self.send_command(CMD_GET_VERSION)
    
    def read_usb_response(self):
        """Read response from USB"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
        
        try:
            # Check if data is available
            if self.serial_conn.in_waiting == 0:
                return None
            
            data = self.serial_conn.read(8)
            if len(data) == 8:
                # Update communication timestamp when we receive data
                self.last_communication = time.time()
                self.logger.info(f"RAW DATA: {[hex(b) for b in data]} (CMD: {hex(data[0])})")
                return self.parse_response(data)
            elif len(data) > 0:
                self.logger.warning(f"Received incomplete data: {len(data)} bytes: {[hex(b) for b in data]}")
                
        except serial.SerialException as e:
            self.logger.error(f"Serial communication error: {e}")
            # Connection lost
            if self.serial_conn:
                try:
                    self.serial_conn.close()
                except:
                    pass
                self.serial_conn = None
        except Exception as e:
            self.logger.error(f"USB read error: {e}")
        
        return None
    
    def parse_response(self, data):
        """Parse response from device"""
        if len(data) < 8:
            self.logger.warning(f"Received short response: {len(data)} bytes")
            return None
        
        cmd = data[0]
        self.logger.info(f"Received response: CMD=0x{cmd:02X}, Data={[hex(b) for b in data]}")
        
        if cmd == CMD_GET_STATUS:
            return self.parse_status_response(data)
        elif cmd == CMD_GET_VERSION:
            return self.parse_version_response(data)
        else:
            self.logger.warning(f"Unknown response command: 0x{cmd:02X}")
        
        return None
    
    def parse_status_response(self, data):
        """Parse status response"""
        if len(data) < 8:
            return None
        
        cmd = data[0]
        if cmd != CMD_GET_STATUS:
            return None
        
        status = {
            'type': 'status',
            'relay1': bool(data[1]),          # Relay 1
            'relay2': bool(data[2]),          # Relay 2
            'dimmer1_value': (data[3] << 8) | data[4],
            'dimmer2_value': (data[5] << 8) | data[6],
            'dimmer1_enabled': bool(data[7] & 0x02),
            'dimmer2_enabled': bool(data[7] & 0x01)
        }
        
        # Update internal state
        self.relay1_state = status['relay1']
        self.relay2_state = status['relay2']
        self.dimmer1_value = status['dimmer1_value']
        self.dimmer2_value = status['dimmer2_value']
        self.dimmer1_enabled = status['dimmer1_enabled']
        self.dimmer2_enabled = status['dimmer2_enabled']
        
        return status
    
    def parse_version_response(self, data):
        """Parse version response"""
        if len(data) < 8:
            return None
        
        cmd = data[0]
        if cmd != CMD_GET_VERSION:
            return None
        
        # Version format: major.minor.patch (data[1].data[2].data[3])
        major = data[1]
        minor = data[2]
        patch = data[3]
        
        self.firmware_version = f"v{major}.{minor}.{patch}"
        
        return {
            'type': 'version',
            'version': self.firmware_version
        }
    
    def status_monitor_thread(self):
        """Background thread to monitor status"""
        last_status_request = 0
        status_request_interval = 2.0  # Request status every 2 seconds
        
        self.logger.info("=== Status monitor thread started ===")
        
        while self.running:
            try:
                # Try to read status response
                response = None
                if self.serial_conn and self.serial_conn.is_open:
                    response = self.read_usb_response()
                    
                    # Periodically request status to maintain communication
                    current_time = time.time()
                    if current_time - last_status_request > status_request_interval:
                        try:
                            self.logger.debug("Sending periodic status request...")
                            self.get_status()
                            last_status_request = current_time
                        except Exception as e:
                            self.logger.debug(f"Failed to request status: {e}")
                
                if response:
                    self.logger.info(f"✓ Got response: {response['type']}")
                    self.status_queue.put(response)
                
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Status monitor error: {e}")
                time.sleep(1)
        
        self.logger.info("=== Status monitor thread stopped ===")
    
    def start_monitoring(self):
        """Start status monitoring"""
        self.running = True
        self.status_thread = threading.Thread(target=self.status_monitor_thread)
        self.status_thread.daemon = True
        self.status_thread.start()


class PowerPackGUI:
    def __init__(self):
        self.controller = PowerPackController()
        self.root = tk.Tk()
        self.root.title("PowerPack Controller R2M1 - DEBUG")
        self.root.geometry("800x700")  # Bigger for debug window
        
        # Heartbeat LED state
        self.led_state = False
        self.led_color = "red"
        self.last_connection_state = False
        
        # Timer IDs for proper cleanup
        self.update_timer_id = None
        self.heartbeat_timer_id = None
        self.connection_monitor_id = None
        
        # Setup console handler to capture logs
        self.setup_console_logging()
        
        self.create_widgets()
        self.update_timer()
        self.heartbeat_timer()
        self.connection_monitor()
    
    def setup_console_logging(self):
        """Setup logging to GUI console"""
        import logging
        
        class GUILogHandler(logging.Handler):
            def __init__(self, gui):
                super().__init__()
                self.gui = gui
                
            def emit(self, record):
                msg = self.format(record)
                # Will be displayed in console_text widget
                if hasattr(self.gui, 'console_text'):
                    try:
                        self.gui.console_text.insert(tk.END, msg + '\n')
                        self.gui.console_text.see(tk.END)
                        
                        # Limit to last 500 lines
                        lines = int(self.gui.console_text.index('end-1c').split('.')[0])
                        if lines > 500:
                            self.gui.console_text.delete('1.0', f'{lines-500}.0')
                    except:
                        pass
        
        # Add GUI handler to controller's logger
        self.gui_handler = GUILogHandler(self)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', 
                                     datefmt='%H:%M:%S')
        self.gui_handler.setFormatter(formatter)
        self.controller.logger.addHandler(self.gui_handler)
    
    def create_widgets(self):
        """Create GUI widgets"""
        # Top frame for title and LED
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Title
        title_label = tk.Label(top_frame, text="PowerPack Controller", 
                              font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        # Heartbeat LED
        led_frame = tk.Frame(top_frame)
        led_frame.pack(side=tk.RIGHT)
        
        tk.Label(led_frame, text="Status:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.led_canvas = tk.Canvas(led_frame, width=20, height=20)
        self.led_canvas.pack(side=tk.LEFT, padx=5)
        self.led_circle = self.led_canvas.create_oval(2, 2, 18, 18, fill="red", outline="darkred")
        
        # Version info frame
        version_frame = ttk.LabelFrame(self.root, text="Version Information", padding=10)
        version_frame.pack(fill=tk.X, padx=10, pady=5)
        
        version_info_frame = tk.Frame(version_frame)
        version_info_frame.pack(fill=tk.X)
        
        tk.Label(version_info_frame, text=f"Python App: {PYTHON_APP_VERSION}", 
                font=("Arial", 9)).pack(side=tk.LEFT)
        
        self.firmware_version_label = tk.Label(version_info_frame, 
                                              text=f"STM32 Firmware: {self.controller.firmware_version}",
                                              font=("Arial", 9))
        self.firmware_version_label.pack(side=tk.RIGHT)
        
        # Connection frame
        conn_frame = ttk.LabelFrame(self.root, text="Connection", padding=10)
        conn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(conn_frame, text="USB Port:").grid(row=0, column=0, sticky=tk.W)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=40, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=5)
        
        self.refresh_btn = ttk.Button(conn_frame, text="Refresh", command=self.refresh_ports)
        self.refresh_btn.grid(row=0, column=2, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_usb)
        self.connect_btn.grid(row=0, column=3, padx=5)
        
        self.disconnect_btn = ttk.Button(conn_frame, text="Disconnect", command=self.disconnect, state="disabled")
        self.disconnect_btn.grid(row=0, column=4, padx=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(self.root, text="Status", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_text = tk.Text(status_frame, height=4, width=70)
        self.status_text.pack()
        
        # Relay control frame
        relay_frame = ttk.LabelFrame(self.root, text="Relay Control", padding=10)
        relay_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Relay 1
        ttk.Label(relay_frame, text="Relay 1:").grid(row=0, column=0, sticky=tk.W)
        self.relay1_var = tk.BooleanVar()
        ttk.Checkbutton(relay_frame, text="ON", variable=self.relay1_var, 
                       command=lambda: self.set_relay(1, self.relay1_var.get())).grid(row=0, column=1)
        
        # Relay 2
        ttk.Label(relay_frame, text="Relay 2:").grid(row=1, column=0, sticky=tk.W)
        self.relay2_var = tk.BooleanVar()
        ttk.Checkbutton(relay_frame, text="ON", variable=self.relay2_var,
                       command=lambda: self.set_relay(2, self.relay2_var.get())).grid(row=1, column=1)
        
        # Info label
        ttk.Label(relay_frame, text="(Independent relay control via GPIO_M1 and GPIO_M2)", 
                 font=("Arial", 8), foreground="gray").grid(row=2, column=0, columnspan=3, padx=10, sticky=tk.W)
        
        # Dimmer control frame
        dimmer_frame = ttk.LabelFrame(self.root, text="Dimmer Control", padding=10)
        dimmer_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Dimmer 1
        ttk.Label(dimmer_frame, text="Dimmer 1:").grid(row=0, column=0, sticky=tk.W)
        self.dimmer1_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(dimmer_frame, text="Enable", variable=self.dimmer1_enabled_var,
                       command=lambda: self.enable_dimmer(1, self.dimmer1_enabled_var.get())).grid(row=0, column=1)
        
        self.dimmer1_var = tk.DoubleVar(value=0)
        dimmer1_scale = ttk.Scale(dimmer_frame, from_=0, to=100, variable=self.dimmer1_var,
                                 command=lambda v: self.set_dimmer(1, float(v)))
        dimmer1_scale.grid(row=0, column=2, sticky=tk.EW, padx=10)
        
        self.dimmer1_label = ttk.Label(dimmer_frame, text="0%")
        self.dimmer1_label.grid(row=0, column=3)
        
        # Dimmer 2
        ttk.Label(dimmer_frame, text="Dimmer 2:").grid(row=1, column=0, sticky=tk.W)
        self.dimmer2_enabled_var = tk.BooleanVar()
        ttk.Checkbutton(dimmer_frame, text="Enable", variable=self.dimmer2_enabled_var,
                       command=lambda: self.enable_dimmer(2, self.dimmer2_enabled_var.get())).grid(row=1, column=1)
        
        self.dimmer2_var = tk.DoubleVar(value=0)
        dimmer2_scale = ttk.Scale(dimmer_frame, from_=0, to=100, variable=self.dimmer2_var,
                                 command=lambda v: self.set_dimmer(2, float(v)))
        dimmer2_scale.grid(row=1, column=2, sticky=tk.EW, padx=10)
        
        self.dimmer2_label = ttk.Label(dimmer_frame, text="0%")
        self.dimmer2_label.grid(row=1, column=3)
        
        dimmer_frame.columnconfigure(2, weight=1)
        
        # Control buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Get Status", command=self.get_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Get Version", command=self.get_version).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Debug Test", command=self.debug_test).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="All OFF", command=self.all_off).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Test Sequence", command=self.test_sequence).pack(side=tk.LEFT, padx=5)
        
        # Debug Console frame
        console_frame = ttk.LabelFrame(self.root, text="Debug Console", padding=10)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create console text with scrollbar
        console_scroll = ttk.Scrollbar(console_frame)
        console_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.console_text = tk.Text(console_frame, height=10, width=90, 
                                   yscrollcommand=console_scroll.set,
                                   bg='black', fg='#00FF00', 
                                   font=('Courier', 9))
        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        console_scroll.config(command=self.console_text.yview)
        
        # Add clear console button
        ttk.Button(button_frame, text="Clear Console", 
                  command=lambda: self.console_text.delete('1.0', tk.END)).pack(side=tk.RIGHT, padx=5)
        
        self.refresh_ports()
    
    def connection_monitor(self):
        """Monitor connection status and update UI accordingly"""
        try:
            current_state = self.controller.is_connected()
            
            # Check if connection state changed
            if current_state != self.last_connection_state:
                self.last_connection_state = current_state
                
                if current_state:
                    # Just connected
                    self.update_status("âœ… Device connected and communicating")
                    self.connect_btn.config(state="disabled")
                    self.disconnect_btn.config(state="normal")
                    self.port_combo.config(state="disabled")
                    self.refresh_btn.config(state="disabled")
                else:
                    # Just disconnected
                    if self.controller.serial_conn:
                        self.update_status("âŒ Communication lost - device disconnected")
                    else:
                        self.update_status("âšª Ready to connect")
                    
                    self.connect_btn.config(state="normal")
                    self.disconnect_btn.config(state="disabled")
                    self.port_combo.config(state="readonly")
                    self.refresh_btn.config(state="normal")
            
            # Schedule next check only if window still exists
            if self.root.winfo_exists():
                self.connection_monitor_id = self.root.after(1000, self.connection_monitor)
                
        except tk.TclError:
            # Window was destroyed
            pass
    
    def update_led(self):
        """Update heartbeat LED"""
        if self.controller.is_connected():
            # Green heartbeat when connected
            self.led_color = "lightgreen" if self.led_state else "green"
            outline_color = "darkgreen"
        else:
            # Red when disconnected
            self.led_color = "red"
            outline_color = "darkred"
        
        self.led_canvas.itemconfig(self.led_circle, fill=self.led_color, outline=outline_color)
    
    def heartbeat_timer(self):
        """Heartbeat timer for LED animation"""
        try:
            if self.controller.is_connected():
                self.led_state = not self.led_state  # Toggle for heartbeat effect
            else:
                self.led_state = False  # Solid red when disconnected
            
            self.update_led()
            
            # Schedule next heartbeat only if window still exists
            if self.root.winfo_exists():
                self.heartbeat_timer_id = self.root.after(500, self.heartbeat_timer)
                
        except tk.TclError:
            # Window was destroyed
            pass
    
    def refresh_ports(self):
        """Refresh available COM ports"""
        ports = self.controller.get_port_list_with_descriptions()
        self.port_combo['values'] = ports
        if ports:
            # Try to find PowerPack device and select it
            powerpack_port = self.controller.find_powerpack_port()
            if powerpack_port:
                for i, port_desc in enumerate(ports):
                    if powerpack_port in port_desc:
                        self.port_combo.current(i)
                        break
            else:
                self.port_combo.current(0)
        
        self.update_status(f"ðŸ“¡ Found {len(ports)} USB ports")
    
    def connect_usb(self):
        """Connect via USB"""
        try:
            port_selection = self.port_var.get()
            if not port_selection:
                messagebox.showerror("Error", "Please select a USB port")
                return
            
            port = self.controller.extract_port_from_selection(port_selection)
            self.update_status(f"ðŸ”Œ Connecting to {port}...")
            
            # Disable UI during connection
            self.connect_btn.config(state="disabled")
            self.port_combo.config(state="disabled")
            self.refresh_btn.config(state="disabled")
            self.root.update()
            
            if self.controller.connect_usb(port):
                self.controller.start_monitoring()
                self.update_status(f"âœ… Connected to {port}")
                
                # Wait a moment for connection to stabilize
                time.sleep(2)
                
                # Request initial data with delays
                try:
                    self.update_status("ðŸ“‹ Requesting firmware version...")
                    self.controller.get_version()
                    time.sleep(1)
                    
                    self.update_status("ðŸ“Š Requesting device status...")
                    self.controller.get_status()
                    
                except Exception as e:
                    self.update_status(f"âš ï¸ Initial communication failed: {e}")
                
            else:
                self.update_status("âŒ Connection failed")
                # Re-enable UI on failure
                self.connect_btn.config(state="normal")
                self.port_combo.config(state="readonly")
                self.refresh_btn.config(state="normal")
                messagebox.showerror("Error", "Failed to connect via USB")
                
        except Exception as e:
            self.update_status(f"âŒ Connection error: {str(e)}")
            # Re-enable UI on error
            self.connect_btn.config(state="normal")
            self.port_combo.config(state="readonly")
            self.refresh_btn.config(state="normal")
            messagebox.showerror("Error", f"USB connection failed: {e}")
    
    def disconnect(self):
        """Disconnect from device"""
        self.update_status("ðŸ”Œ Disconnecting...")
        self.controller.disconnect()
        self.update_status("âšª Disconnected")
    
    def set_relay(self, relay_num, state):
        """Set relay state"""
        try:
            self.controller.set_relay(relay_num, state)
            self.update_status(f"ðŸ”Œ Relay {relay_num} {'ON' if state else 'OFF'}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set relay: {e}")
    
    def set_dimmer(self, dimmer_num, percentage):
        """Set dimmer percentage"""
        try:
            self.controller.set_dimmer(dimmer_num, percentage)
            if dimmer_num == 1:
                self.dimmer1_label.config(text=f"{percentage:.1f}%")
            else:
                self.dimmer2_label.config(text=f"{percentage:.1f}%")
            self.update_status(f"Dimmer {dimmer_num} set to {percentage:.1f}%")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set dimmer: {e}")
    
    def enable_dimmer(self, dimmer_num, enable):
        """Enable/disable dimmer"""
        try:
            self.controller.enable_dimmer(dimmer_num, enable)
            self.update_status(f"Dimmer {dimmer_num} {'enabled' if enable else 'disabled'}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to enable dimmer: {e}")
    
    def get_status(self):
        """Get device status"""
        try:
            self.controller.get_status()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get status: {e}")
    
    def get_version(self):
        """Get device version"""
        try:
            self.controller.logger.info("Requesting firmware version...")
            self.controller.get_version()
            
            # Wait for response with timeout
            start_time = time.time()
            timeout = 3.0  # 3 seconds timeout
            
            while time.time() - start_time < timeout:
                try:
                    response = self.controller.status_queue.get_nowait()
                    if response['type'] == 'version':
                        self.firmware_version_label.config(text=f"STM32 Firmware: {response['version']}")
                        self.update_status(f"ðŸ“‹ Firmware version: {response['version']}")
                        return
                except queue.Empty:
                    time.sleep(0.1)
            
            # Timeout reached
            self.update_status("âš ï¸ Version request timeout - no response from device")
            
        except Exception as e:
            self.controller.logger.error(f"Failed to request version: {e}")
            self.update_status(f"âŒ Version request failed: {e}")
    
    def debug_test(self):
        """Debug test - send raw commands"""
        try:
            if not self.controller.serial_conn:
                self.update_status("âŒ Not connected")
                return
            
            self.update_status("ðŸ”§ Debug Test: Sending raw version command...")
            
            # Send raw version command
            raw_data = bytes([0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            self.controller.serial_conn.write(raw_data)
            self.controller.serial_conn.flush()
            
            self.update_status(f"ðŸ”§ Sent raw bytes: {[hex(b) for b in raw_data]}")
            
            # Wait and read response
            time.sleep(0.5)
            if self.controller.serial_conn.in_waiting > 0:
                response = self.controller.serial_conn.read(self.controller.serial_conn.in_waiting)
                self.update_status(f"ðŸ”§ Received bytes: {[hex(b) for b in response]}")
            else:
                self.update_status("ðŸ”§ No response received")
                
        except Exception as e:
            self.update_status(f"ðŸ”§ Debug test failed: {e}")
    
    def all_off(self):
        """Turn everything off"""
        try:
            self.controller.set_relay(1, False)
            self.controller.set_relay(2, False)
            self.controller.enable_dimmer(1, False)
            self.controller.enable_dimmer(2, False)
            self.controller.set_dimmer(1, 0)
            self.controller.set_dimmer(2, 0)
            
            # Update GUI
            self.relay1_var.set(False)
            self.relay2_var.set(False)
            self.dimmer1_enabled_var.set(False)
            self.dimmer2_enabled_var.set(False)
            self.dimmer1_var.set(0)
            self.dimmer2_var.set(0)
            
            self.update_status("All outputs turned OFF")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to turn off: {e}")
    
    def test_sequence(self):
        """Run test sequence"""
        def test():
            try:
                self.update_status("Starting test sequence...")
                
                # Test relays
                self.controller.set_relay(1, True)
                time.sleep(1)
                self.controller.set_relay(2, True)
                time.sleep(1)
                self.controller.set_relay(1, False)
                self.controller.set_relay(2, False)
                
                # Test dimmers
                self.controller.enable_dimmer(1, True)
                self.controller.enable_dimmer(2, True)
                
                for i in range(0, 101, 10):
                    self.controller.set_dimmer(1, i)
                    self.controller.set_dimmer(2, 100 - i)
                    time.sleep(0.5)
                
                self.controller.set_dimmer(1, 0)
                self.controller.set_dimmer(2, 0)
                self.controller.enable_dimmer(1, False)
                self.controller.enable_dimmer(2, False)
                
                self.update_status("Test sequence completed")
                
            except Exception as e:
                self.update_status(f"Test failed: {e}")
        
        threading.Thread(target=test, daemon=True).start()
    
    def update_status(self, message):
        """Update status display"""
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        
        # Limit status text to last 100 lines
        lines = int(self.status_text.index('end-1c').split('.')[0])
        if lines > 100:
            self.status_text.delete('1.0', f'{lines-100}.0')
    
    def update_timer(self):
        """Update GUI from status queue"""
        try:
            while True:
                response = self.controller.status_queue.get_nowait()
                
                if response['type'] == 'status':
                    # Update GUI with received status
                    self.relay1_var.set(response['relay1'])
                    self.relay2_var.set(response['relay2'])
                    self.dimmer1_enabled_var.set(response['dimmer1_enabled'])
                    self.dimmer2_enabled_var.set(response['dimmer2_enabled'])
                    
                    # Convert DAC values to percentages
                    dimmer1_pct = (response['dimmer1_value'] / 4095.0) * 100
                    dimmer2_pct = (response['dimmer2_value'] / 4095.0) * 100
                    
                    self.dimmer1_var.set(dimmer1_pct)
                    self.dimmer2_var.set(dimmer2_pct)
                    self.dimmer1_label.config(text=f"{dimmer1_pct:.1f}%")
                    self.dimmer2_label.config(text=f"{dimmer2_pct:.1f}%")
                
                elif response['type'] == 'version':
                    # Update firmware version display
                    self.firmware_version_label.config(text=f"STM32 Firmware: {response['version']}")
                    self.update_status(f"ðŸ“‹ Firmware version: {response['version']}")
                
        except queue.Empty:
            pass
        except Exception as e:
            self.controller.logger.error(f"Update timer error: {e}")
        
        # Schedule next update only if window still exists
        try:
            if self.root.winfo_exists():
                self.update_timer_id = self.root.after(100, self.update_timer)
        except tk.TclError:
            # Window was destroyed
            pass
    
    def run(self):
        """Start GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"Error in mainloop: {e}")
        finally:
            # Ensure cleanup happens
            try:
                self.controller.disconnect()
            except:
                pass
    
    def on_closing(self):
        """Handle window closing"""
        try:
            # Stop all background operations
            self.controller.disconnect()
            
            # Cancel any pending after() calls
            try:
                self.root.after_cancel(self.update_timer)
            except:
                pass
            
            try:
                self.root.after_cancel(self.heartbeat_timer)
            except:
                pass
            
            try:
                self.root.after_cancel(self.connection_monitor)
            except:
                pass
            
            # Destroy the window
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
            # Force exit if cleanup fails
            import sys
            sys.exit(0)


def main():
    """Main function"""
    print("PowerPack Controller v2.0.0 - R2M1")
    print("=" * 40)
    
    # Check if GUI mode or command line mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        # Command line mode
        controller = PowerPackController()
        
        print("Available commands:")
        print("  connect_usb [port] - Connect via USB")
        print("  relay <1|2> <on|off> - Control relay")
        print("  dimmer <1|2> <0-100> - Set dimmer percentage")
        print("  enable_dimmer <1|2> - Enable dimmer")
        print("  disable_dimmer <1|2> - Disable dimmer")
        print("  status - Get status")
        print("  version - Get version")
        print("  quit - Exit")
        
        while True:
            try:
                cmd = input("\n> ").strip().split()
                if not cmd:
                    continue
                
                if cmd[0] == "quit":
                    break
                elif cmd[0] == "connect_usb":
                    port = cmd[1] if len(cmd) > 1 else None
                    if controller.connect_usb(port):
                        print("Connected via USB")
                        controller.start_monitoring()
                    else:
                        print("Connection failed")
                        
                elif cmd[0] == "relay" and len(cmd) == 3:
                    relay_num = int(cmd[1])
                    state = cmd[2].lower() == "on"
                    controller.set_relay(relay_num, state)
                    print(f"Relay {relay_num} {'ON' if state else 'OFF'}")
                    
                elif cmd[0] == "dimmer" and len(cmd) == 3:
                    dimmer_num = int(cmd[1])
                    percentage = float(cmd[2])
                    controller.set_dimmer(dimmer_num, percentage)
                    print(f"Dimmer {dimmer_num} set to {percentage}%")
                    
                elif cmd[0] == "enable_dimmer" and len(cmd) == 2:
                    dimmer_num = int(cmd[1])
                    controller.enable_dimmer(dimmer_num, True)
                    print(f"Dimmer {dimmer_num} enabled")
                    
                elif cmd[0] == "disable_dimmer" and len(cmd) == 2:
                    dimmer_num = int(cmd[1])
                    controller.enable_dimmer(dimmer_num, False)
                    print(f"Dimmer {dimmer_num} disabled")
                    
                elif cmd[0] == "status":
                    controller.get_status()
                    print("Status requested")
                    
                elif cmd[0] == "version":
                    controller.get_version()
                    print("Version requested")
                    
                else:
                    print("Invalid command")
                    
            except Exception as e:
                print(f"Error: {e}")
        
        controller.disconnect()
        
    else:
        # GUI mode - create and run only once
        try:
            app = PowerPackGUI()
            app.run()
        except Exception as e:
            print(f"GUI Error: {e}")
        finally:
            # Ensure clean exit
            import sys
            sys.exit(0)


if __name__ == "__main__":
    main()
