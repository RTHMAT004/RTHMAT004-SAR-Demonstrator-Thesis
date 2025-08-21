import sys, time, socket
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel,
    QHBoxLayout, QGraphicsView, QGraphicsScene
)
from PyQt5.QtGui import QPixmap, QImage

# --------------------------------------------------
# GPIO setup (with PC mock fallback)
# --------------------------------------------------
try:
    import Jetson.GPIO as GPIO
except ImportError:
    class MockGPIO:
        BOARD = OUT = IN = HIGH = LOW = PUD_UP = None
        def setmode(*a, **kw): pass
        def setup(*a, **kw): pass
        def output(*a, **kw): pass
        def input(*a, **kw): return 1
        def cleanup(*a, **kw): pass
    GPIO = MockGPIO()

MOTOR_X_PIN = 12
MOTOR_Y_PIN = 13
LIMIT_X_PIN = 16
LIMIT_Y_PIN = 18

GPIO.setmode(GPIO.BOARD)
GPIO.setup(MOTOR_X_PIN, GPIO.OUT)
GPIO.setup(MOTOR_Y_PIN, GPIO.OUT)
GPIO.setup(LIMIT_X_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LIMIT_Y_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

position = {"x": 0, "y": 0}

def step_motor(pin, steps=100, delay=0.002):
    for i in range(steps):
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(delay)

def move_x(steps=200):
    if GPIO.input(LIMIT_X_PIN) == GPIO.LOW:
        return "X limit reached"
    step_motor(MOTOR_X_PIN, steps)
    position["x"] += steps
    return f"X pos: {position['x']}"

def move_y(steps=200):
    if GPIO.input(LIMIT_Y_PIN) == GPIO.LOW:
        return "Y limit reached"
    step_motor(MOTOR_Y_PIN, steps)
    position["y"] += steps
    return f"Y pos: {position['y']}"

def home_motors():
    while GPIO.input(LIMIT_X_PIN) == GPIO.HIGH:
        step_motor(MOTOR_X_PIN, 1)
    while GPIO.input(LIMIT_Y_PIN) == GPIO.HIGH:
        step_motor(MOTOR_Y_PIN, 1)
    position["x"] = position["y"] = 0
    return "Motors homed"

# --------------------------------------------------
# SAR Data Capture (DCA1000 via UDP)
# --------------------------------------------------
UDP_IP = "192.168.33.30"   # DCA1000 default IP
UDP_PORT = 4098            # data port
PACKET_SIZE = 4096

def capture_sar_data(duration=2.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(5.0)

    packets = []
    start_time = time.time()
    while time.time() - start_time < duration:
        try:
            data, _ = sock.recvfrom(PACKET_SIZE)
            packets.append(data)
        except socket.timeout:
            break
    sock.close()

    raw_bytes = b"".join(packets)
    samples = np.frombuffer(raw_bytes, dtype=np.int16)

    num_rx = 4
    if len(samples) >= num_rx:
        samples = samples[: (len(samples)//num_rx)*num_rx].reshape((-1, num_rx))
    else:
        samples = np.zeros((128, num_rx), dtype=np.int16)

    return samples

# --------------------------------------------------
# SAR Processing
# --------------------------------------------------
def process_sar_data(raw_data):
    if raw_data is None or raw_data.size == 0:
        return None
    range_profiles = np.fft.fft(raw_data, axis=0)
    image = np.abs(np.fft.fftshift(np.fft.fft2(range_profiles)))
    return (image / image.max() * 255).astype(np.uint8)

# --------------------------------------------------
# GUI
# --------------------------------------------------
class SARApp(QWidget):
    def _init_(self):
        super()._init_()
        self.setWindowTitle("SAR Controller")
        self.layout = QVBoxLayout()

        # Motor controls
        motor_layout = QHBoxLayout()
        self.btn_x = QPushButton("Move X Axis")
        self.btn_y = QPushButton("Move Y Axis")
        self.btn_home = QPushButton("Home Motors")
        motor_layout.addWidget(self.btn_x)
        motor_layout.addWidget(self.btn_y)
        motor_layout.addWidget(self.btn_home)
        self.layout.addLayout(motor_layout)

        # SAR controls
        sar_layout = QHBoxLayout()
        self.btn_capture = QPushButton("Capture SAR")
        self.btn_process = QPushButton("Process SAR")
        sar_layout.addWidget(self.btn_capture)
        sar_layout.addWidget(self.btn_process)
        self.layout.addLayout(sar_layout)

        # Display
        self.label_status = QLabel("Ready")
        self.layout.addWidget(self.label_status)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.layout.addWidget(self.view)

        self.setLayout(self.layout)

        # Connect
        self.btn_x.clicked.connect(self.move_x)
        self.btn_y.clicked.connect(self.move_y)
        self.btn_home.clicked.connect(self.home)
        self.btn_capture.clicked.connect(self.capture)
        self.btn_process.clicked.connect(self.process)

        self.raw_data = None
        self.processed = None

    def move_x(self):
        msg = move_x()
        self.label_status.setText(msg)

    def move_y(self):
        msg = move_y()
        self.label_status.setText(msg)

    def home(self):
        msg = home_motors()
        self.label_status.setText(msg)

    def capture(self):
        self.raw_data = capture_sar_data()
        self.label_status.setText("Captured SAR data")

    def process(self):
        self.processed = process_sar_data(self.raw_data)
        if self.processed is None:
            self.label_status.setText("No data")
            return
        h, w = self.processed.shape
        qimg = QImage(self.processed.data, w, h, QImage.Format_Grayscale8)
        pix = QPixmap.fromImage(qimg)
        self.scene.clear()
        self.scene.addPixmap(pix)
        self.view.fitInView(self.scene.itemsBoundingRect(), 1)
        self.label_status.setText("Image displayed")

# --------------------------------------------------
# Main Entry
# --------------------------------------------------
if _name_ == "_main_":
    app = QApplication(sys.argv)
    window = SARApp()
    window.show()
    ret = app.exec_()
    GPIO.cleanup()
    sys.exit(ret)