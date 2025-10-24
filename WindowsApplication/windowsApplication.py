import sys
import socket
import threading
import queue
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer
import serial, time, subprocess
import shutil
import os

# ---------------- FILES ----------------
src_file = "C:/Users/Matthew/OneDrive - University of Cape Town/EEE4022S/App/Windows/fpga/adc_data_Raw_0.bin" #Default file that the DCA saves the .bin to. Log files also saved to this location. 
dst_dir = "C:/Users/Matthew/OneDrive - University of Cape Town/EEE4022S/App/Windows/Data" #File location where you intend to save data. Different to SRC file to make file management easier. 

# ---------------- JETSON SERVER CONFIGURATION ----------------
JETSON_IP = "192.168.180.2"  # Jetson IP configured on the Ethernet communication link.
JETSON_PORT = 5005 #Config port of Windows PC used for communication.

#Note: Wirewall must EITHER be disabled OR add an Inbound and Outbound rule for these ports. 

# ---------------- AWR+DCA GLOBAL VARIABLES ----------------
message_queue = queue.Queue()
sock = None

SERIAL_PORT = 'COM11'
BAUD = 115200
CFG_FILE = 'profile.cfg'           # full radar config
SENSOR_STOP_FILE = 'sensor_stop.cfg'  # contains just "sensorStop"
SENSOR_RESTART_FILE = 'sensor_restart.cfg'  # contains just "sensorStart"
SENSOR_START_FILE = 'sensor_start.cfg' 

DATACARD_JSON = './configFile.json'
DCA1000_CLI = './DCA1000EVM_CLI_Control'  # Linux CLI binary

# ---------------- COMMUNICATION THREAD ----------------
def listen_to_jetson(sock):
    while True:
        try:
            data = sock.recv(1024).decode().strip()
            if not data:
                break
            message_queue.put(data)
        except:
            break

# ---------------- Radar ----------------

# ---------------- DCA1000 CONTROL ----------------
def run_cli(cmd): #Function which sends CLI commands in the format specified in mmWave SDK and DCA1000 CLI Guide. 
    full_cmd = [DCA1000_CLI] + cmd.split() + [DATACARD_JSON]
    print(f"[INFO] Running: {' '.join(full_cmd)}")
    subprocess.run(full_cmd, check=True)

# ---------------- AWR1642 UART CONFIG ----------------
def send_line(ser, line, wait=0.01):
    """Send a single line to the radar and collect replies quickly."""
    ser.write((line + '\n').encode())
    time.sleep(wait)
    out = b''
    while ser.in_waiting:
        out += ser.read(ser.in_waiting)
        time.sleep(0.005)
    return out.decode(errors='ignore').strip()

# ---------------- JETSON SERVER TRANSMISSION ----------------
def send_cmd(self, cmd): #For sending commands to the Jetson Server to control platform. 
        if sock:
            try:
                sock.sendall((cmd + "\n").encode())
            except Exception as e:
                self.output_box.append(f"Error sending: {e}")

def send_cfg(port, cfg_file, baud=115200): #For sending commands to the Jetson Server to control platform. 
    """Send a .cfg file to the radar and show CLI responses."""
    ser = serial.Serial(port, baud, timeout=0.5)
    time.sleep(0.2)
    ser.write(b'\n') 
    time.sleep(0.05)
    if ser.in_waiting:
        print(ser.read(ser.in_waiting).decode(errors='ignore'))

    with open(cfg_file, 'r') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith(('%','#','//')):
                continue
            print('>>>', line)
            resp = send_line(ser, line)
            if resp:
                print(resp)
            time.sleep(0.01)
    ser.close()

def configure_radar(self):
    run_cli("reset_fpga")
    time.sleep(4)
    run_cli("reset_ar_device")
    time.sleep(4)

    run_cli("fpga")
    run_cli("record")
    
    send_cfg(SERIAL_PORT, CFG_FILE)    
    time.sleep(2)
    send_cfg(SERIAL_PORT, SENSOR_STOP_FILE)
    time.sleep(1.5)

# ---------------- GUI ----------------
class MotorControlApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Motor Control")
        self.resize(400, 400)
        self.layout = QVBoxLayout()

        # ---------------- ARROW BUTTONS----------------
        self.up_btn = QPushButton("↑")
        self.down_btn = QPushButton("↓")
        self.left_btn = QPushButton("←")
        self.right_btn = QPushButton("→")

        for btn in [self.up_btn, self.down_btn, self.left_btn, self.right_btn]:
            btn.setStyleSheet("""
                QPushButton { font-size: 20px; }
                QPushButton:pressed { background-color: green; color: white; }
            """)
        
        # Connect signals
        self.up_btn.pressed.connect(lambda: self.send_cmd("UP_START"))
        self.up_btn.released.connect(lambda: self.send_cmd("UP_STOP"))
        self.down_btn.pressed.connect(lambda: self.send_cmd("DOWN_START"))
        self.down_btn.released.connect(lambda: self.send_cmd("DOWN_STOP"))
        self.left_btn.pressed.connect(lambda: self.send_cmd("L_START"))
        self.left_btn.released.connect(lambda: self.send_cmd("L_STOP"))
        self.right_btn.pressed.connect(lambda: self.send_cmd("R_START"))
        self.right_btn.released.connect(lambda: self.send_cmd("R_STOP"))

        # Arrange in cross pattern
        arrow_layout = QVBoxLayout()
        arrow_layout.addWidget(self.up_btn, alignment=Qt.AlignCenter)

        middle_row = QHBoxLayout()
        middle_row.addWidget(self.left_btn)
        middle_row.addStretch()
        middle_row.addWidget(self.right_btn)
        arrow_layout.addLayout(middle_row)

        arrow_layout.addWidget(self.down_btn, alignment=Qt.AlignCenter)
        self.layout.addLayout(arrow_layout)

        # ---------------- Home & Capture Buttons ----------------
        self.home_btn = QPushButton("Home")
        self.sar_singleAxis_scan_btn = QPushButton("Capture 1D Scan")
        self.range_btn = QPushButton("Capture Frames")
        self.sar_twoAxis_scan_btn = QPushButton("Capture 2D Scan")

        # Connect signals
        self.home_btn.clicked.connect(lambda: self.send_cmd("HOME"))
        self.sar_singleAxis_scan_btn.clicked.connect(self.sar_singleAxis_scan)
        self.range_btn.clicked.connect(self.single_frame_capture)
        self.sar_twoAxis_scan_btn.clicked.connect(self.sar_twoAxis_scan)

        for btn in [self.home_btn, self.sar_singleAxis_scan_btn, self.range_btn, self.sar_twoAxis_scan_btn]:
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { font-size: 18px; }
                QPushButton:pressed { background-color: green; color: white; }
            """)

        bottom_layout = QVBoxLayout()
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        row1.addWidget(self.home_btn)
        row1.addWidget(self.sar_singleAxis_scan_btn)
        row2.addWidget(self.range_btn)
        row2.addWidget(self.sar_twoAxis_scan_btn)
        bottom_layout.addLayout(row1)
        bottom_layout.addLayout(row2)
        self.layout.addLayout(bottom_layout)

        # ---------------- Read-only Textbox ----------------
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)
        self.layout.addWidget(self.output_box)

        self.setLayout(self.layout)

        # ---------------- Timer to update messages ----------------
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_messages)
        self.timer.start(100)

    def send_cmd(self, cmd):
        if sock:
            try:
                sock.sendall((cmd + "\n").encode())
            except Exception as e:
                self.output_box.append(f"Error sending: {e}")

    def update_messages(self):
        while not message_queue.empty():
            msg = message_queue.get()
            self.output_box.append(msg)

    def sar_singleAxis_scan(self):
        configure_radar(self)

        count = 0
        print("[SAR] Starting DCA record...")
        run_cli("start_record")
        time.sleep(2)  

        dx = 1
        steps = 370*(1/dx)

        while count<steps:#steps: #370mm is experimentally determined - the wingspan in the x direction                     

            print("[SAR] Starting sensor...")
            send_cfg(SERIAL_PORT, SENSOR_RESTART_FILE)

            # Wait for radar to finish one frame (adjust delay per frameCfg)
            time.sleep(0.1)
            
            print("[SAR] Stopping sensor...")
            send_cfg(SERIAL_PORT, SENSOR_STOP_FILE)
        
            send_cmd(self, f"MOVE_{dx}_R")

            print(count)
            count+=1
            
        print("[SAR] Stopping DCA record...")
        # run_cli("stop_record")

        # create unique filename

        time.sleep(10)
        dst_file = os.path.join(dst_dir, f"{count}_0.bin")
        
        try:
            shutil.copy2(src_file, dst_file)  # copies file + metadata
            print(f"Copied to {dst_file}")
        except PermissionError:
            print("File is locked, retrying later...")
        except Exception as e:
            print(f"Error copying file: {e}")

    def single_frame_capture(self):
        configure_radar(self)

        print("[SAR] Starting DCA record...")
        run_cli("start_record")
        time.sleep(2)

        print("[SAR] Starting sensor...")
        send_cfg(SERIAL_PORT, SENSOR_RESTART_FILE)

        
        time.sleep(1)# Wait for radar to finish one frame (adjust delay per frameCfg)

        time.sleep(10)# Standard wait time for saving files.
        dst_file = os.path.join(dst_dir, f"RangeProfile.bin")
        countX = 0
        try:
            shutil.copy2(src_file, dst_file)  # copies file + metadata
            print(f"Copied to {dst_file}")
        except PermissionError:
            print("File is locked, retrying later...")
        except Exception as e:
            print(f"Error copying file: {e}")

    def sar_twoAxis_scan(self):
        dx = 5
        dy = 5
        stepsX = 200*(1/dx)#370mm across
        stepsY = 200*(1/dy)

        configure_radar(self)
        
        send_cfg(SERIAL_PORT, CFG_FILE)    
        time.sleep(2)
        send_cfg(SERIAL_PORT, SENSOR_STOP_FILE)
        time.sleep(1.5)

        countY = 0
        while countY<stepsY:
            countX = 0

            print("[SAR] Starting DCA record...")
            run_cli("start_record")
            time.sleep(2)

            while countX<stepsX:#steps: #370mm is experimentally determined - the wingspan in the x direction                     

                # print("[SAR] Starting sensor...")
                send_cfg(SERIAL_PORT, SENSOR_RESTART_FILE)

                # Wait for radar to finish one frame (adjust delay per frameCfg)
                time.sleep(0.2)
                
                # print("[SAR] Stopping sensor...")
                send_cfg(SERIAL_PORT, SENSOR_STOP_FILE)
                    
                send_cmd(self, f"MOVE_{dx}_R")
                time.sleep(0.1)
                print(countX)
                countX+=1
            
            send_cmd(self, "HOME_X") 
            time.sleep(12)

            dst_file = os.path.join(dst_dir, f"{countX}_{countY}.bin")
            countX = 0
            try:
                shutil.copy2(src_file, dst_file)  # copies file + metadata
                print(f"Copied to {dst_file}")
            except PermissionError:
                print("File is locked, retrying later...")
            except Exception as e:
                print(f"Error copying file: {e}")
            countY+=1
            time.sleep(0.1)
            send_cmd(self, f"MOVE_{dy}_UP")
            time.sleep(0.1)

# ---------------- Main ----------------
def main():
    global sock
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((JETSON_IP, JETSON_PORT))
    except Exception as e:
        print(f"Cannot connect to Jetson: {e}")
        return

    # Start listener thread
    threading.Thread(target=listen_to_jetson, args=(sock,), daemon=True).start()

    # Start GUI
    app = QApplication(sys.argv)
    window = MotorControlApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
