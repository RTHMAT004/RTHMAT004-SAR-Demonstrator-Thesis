import sys, time, socket
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QLabel,
    QHBoxLayout, QSlider, QGroupBox, QRadioButton, QGraphicsView, QGraphicsScene
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

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
        def PWM(*a, **kw):
            class _PWM:
                def start(self, duty): pass
                def ChangeDutyCycle(self, duty): pass
                def stop(self): pass
            return _PWM()
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

pwm_x = GPIO.PWM(MOTOR_X_PIN, 1000)
pwm_y = GPIO.PWM(MOTOR_Y_PIN, 1000)
pwm_x.start(0)
pwm_y.start(0)

def set_motor(axis, duty, direction):
    """Set PWM duty cycle with direction."""
    # You could invert pins here if using H-bridge or direction pins
    if axis == "x":
        pwm_x.ChangeDutyCycle(duty)
    elif axis == "y":
        pwm_y.ChangeDutyCycle(duty)

def stop_motors():
    pwm_x.ChangeDutyCycle(0)
    pwm_y.ChangeDutyCycle(0)

# --------------------------------------------------
# SAR Data Capture (DCA1000 via UDP)
# --------------------------------------------------
UDP_IP = "192.168.33.30"
UDP_PORT = 4098
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SAR Controller")
        self.layout = QVBoxLayout()

        # ---------------- Motor Controls ----------------
        motor_group = QGroupBox("Motor Control")
        motor_layout = QHBoxLayout()

        # X Axis
        x_group = QGroupBox("X Axis")
        x_layout = QVBoxLayout()
        self.slider_x = QSlider(Qt.Horizontal)
        self.slider_x.setRange(0, 100)
        self.slider_x.setValue(0)
        self.label_x = QLabel("Speed: 0%")
        self.dir_x_fwd = QRadioButton("Forward")
        self.dir_x_rev = QRadioButton("Reverse")
        self.dir_x_fwd.setChecked(True)
        self.slider_x.valueChanged.connect(self.update_x)
        x_layout.addWidget(self.label_x)
        x_layout.addWidget(self.slider_x)
        x_layout.addWidget(self.dir_x_fwd)
        x_layout.addWidget(self.dir_x_rev)
        x_group.setLayout(x_layout)

        # Y Axis
        y_group = QGroupBox("Y Axis")
        y_layout = QVBoxLayout()
        self.slider_y = QSlider(Qt.Horizontal)
        self.slider_y.setRange(0, 100)
        self.slider_y.setValue(0)
        self.label_y = QLabel("Speed: 0%")
        self.dir_y_fwd = QRadioButton("Forward")
        self.dir_y_rev = QRadioButton("Reverse")
        self.dir_y_fwd.setChecked(True)
        self.slider_y.valueChanged.connect(self.update_y)
        y_layout.addWidget(self.label_y)
        y_layout.addWidget(self.slider_y)
        y_layout.addWidget(self.dir_y_fwd)
        y_layout.addWidget(self.dir_y_rev)
        y_group.setLayout(y_layout)

        motor_layout.addWidget(x_group)
        motor_layout.addWidget(y_group)
        motor_group.setLayout(motor_layout)
        self.layout.addWidget(motor_group)

        # ---------------- SAR Controls ----------------
        sar_group = QGroupBox("SAR Control")
        sar_layout = QHBoxLayout()
        self.btn_capture = QPushButton("Capture SAR")
        self.btn_process = QPushButton("Process SAR")
        sar_layout.addWidget(self.btn_capture)
        sar_layout.addWidget(self.btn_process)
        sar_group.setLayout(sar_layout)
        self.layout.addWidget(sar_group)

        # ---------------- Status + Image ----------------
        self.label_status = QLabel("Ready")
        self.layout.addWidget(self.label_status)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.layout.addWidget(self.view)

        self.setLayout(self.layout)

        # Connect buttons
        self.btn_capture.clicked.connect(self.capture)
        self.btn_process.clicked.connect(self.process)

        self.raw_data = None
        self.processed = None

    # Motor handlers
    def update_x(self, value):
        self.label_x.setText(f"Speed: {value}%")
        direction = "fwd" if self.dir_x_fwd.isChecked() else "rev"
        set_motor("x", value, direction)

    def update_y(self, value):
        self.label_y.setText(f"Speed: {value}%")
        direction = "fwd" if self.dir_y_fwd.isChecked() else "rev"
        set_motor("y", value, direction)

    # SAR handlers
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
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        self.label_status.setText("Image displayed")

# --------------------------------------------------
# Main Entry
# --------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SARApp()
    window.show()
    ret = app.exec_()
    stop_motors()
    GPIO.cleanup()
    sys.exit(ret)
