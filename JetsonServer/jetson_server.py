import socket
import threading
import time

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

# ---------------- GPIO Pins ----------------
MOTOR_X_PIN = 32
MOTOR_Y_PIN = 33
DIRECTION_X = 37
DIRECTION_Y = 35
LIMIT_PIN = 40
SYNC_IN = 31

GPIO.setmode(GPIO.BOARD)
GPIO.setup(MOTOR_X_PIN, GPIO.OUT)
GPIO.setup(MOTOR_Y_PIN, GPIO.OUT)
GPIO.setup(DIRECTION_X, GPIO.OUT)
GPIO.setup(DIRECTION_Y, GPIO.OUT)
GPIO.setup(LIMIT_PIN, GPIO.IN)
GPIO.setup(SYNC_IN, GPIO.OUT)

# ---------------- PWM setup ----------------
FIXED_DUTY = 50  # Fixed speed

frequency = 7500
x_pwm = GPIO.PWM(MOTOR_X_PIN, frequency)
y_pwm = GPIO.PWM(MOTOR_Y_PIN, frequency)
x_pwm.start(0)
y_pwm.start(0)

# ---------------- Motor control state ----------------
running = True

# ---------------- Helper functions ----------------
def setDirection(direction):
    if direction == "UP":
        GPIO.output(DIRECTION_Y, GPIO.LOW)
    elif direction == "DOWN":
        GPIO.output(DIRECTION_Y, GPIO.HIGH)
    elif direction == "R":
        GPIO.output(DIRECTION_X, GPIO.LOW)
    elif direction == "L":
        GPIO.output(DIRECTION_X, GPIO.HIGH)

def set_motor(axis, on_off):
    """Turn motor PWM on or off."""
    if axis == "x":
        if on_off:
            x_pwm.ChangeDutyCycle(FIXED_DUTY)
        else:
            x_pwm.ChangeDutyCycle(0)
    if axis == "y":
        if on_off:
            y_pwm.ChangeDutyCycle(FIXED_DUTY)
        else:
            y_pwm.ChangeDutyCycle(0)

# ---------------- Homing ----------------
def home_system(send_fn=None):
    setDirection("L")
    set_motor("x", True)
    while GPIO.input(LIMIT_PIN) == 0:
        time.sleep(0.01)
    set_motor("x", False)

    setDirection("R")
    set_motor("x", True)
    while GPIO.input(LIMIT_PIN) == 1:
        time.sleep(0.01)
    set_motor("x", False)

    setDirection("DOWN")
    set_motor("y", True)
    while GPIO.input(LIMIT_PIN) == 0:
        time.sleep(0.01)
    set_motor("y", False)

    setDirection("UP")
    set_motor("y", True)
    while GPIO.input(LIMIT_PIN) == 1:
        time.sleep(0.01)
    set_motor("y", False)

    msg = "Homing complete"
    print(msg)
    if send_fn:
        send_fn(msg)

def home_x(send_fn=None):
    setDirection("L")
    set_motor("x", True)
    while GPIO.input(LIMIT_PIN) == 0:
        time.sleep(0.01)
    set_motor("x", False)

    setDirection("R")
    set_motor("x", True)
    while GPIO.input(LIMIT_PIN) == 1:
        time.sleep(0.01)
    set_motor("x", False)
    
    msg = "Homing X complete"
    print(msg)
    if send_fn:
        send_fn(msg)

# ---------------- Strip map SAR movement ----------------
def move_distance(distance_mm, direction, freq_hz=frequency, send_fn=None):
    setDirection(direction)
    steps_needed = ((distance_mm * 200 * 16) / 8.0)  # STEPS_PER_MM
    
    timeSleep = steps_needed/freq_hz
    
    delay = 1.0 / (2 * freq_hz)
    pwm = y_pwm if direction in ["UP","DOWN"] else x_pwm

    pwm.ChangeDutyCycle(FIXED_DUTY)
    time.sleep(timeSleep) 
    pwm.ChangeDutyCycle(0)

    msg = f"Moved {distance_mm}mm {direction}"
    print(msg)
    if send_fn:
        send_fn(msg)
        
# ---------------- TCP Server ----------------
TCP_IP = "192.168.180.2"  # Jetson IP
TCP_PORT = 5005

def client_thread(conn, addr):
    print(f"Connected by {addr}")

    def send_msg(msg):
        try:
            conn.sendall((msg + "\n").encode())
        except:
            pass  # client may have disconnected

    try:
        while True:
            data = conn.recv(1024).decode('utf-8').strip()
            if not data:
                break
            print(f"Received: {data}")
            send_msg(f"Received: {data}")

            # Motor movement commands
            if data.endswith("_START"):
                cmd = data.replace("_START", "")
                axis = "y" if cmd in ["UP", "DOWN"] else "x"
                setDirection(cmd)
                set_motor(axis, True)
                send_msg(f"{cmd}_ON")
            elif data.endswith("_STOP"):
                cmd = data.replace("_STOP", "")
                axis = "y" if cmd in ["UP", "DOWN"] else "x"
                setDirection(cmd)
                set_motor(axis, False)
                send_msg(f"{cmd}_OFF")
            # Homing
            elif data == "HOME":
                home_system(send_fn=send_msg)
                send_msg("HOME_DONE")
            # Strip map SAR single move
            elif data == "HOME_X":
                home_x(send_fn=send_msg)
                send_msg("HOME_DONE")
            elif data.startswith("MOVE"):
                parts = data.split("_")  # MOVE_2_R
                if len(parts) == 3:
                    distance = float(parts[1])
                    direction = parts[2]
                    move_distance(distance, direction, send_fn=send_msg)
                    send_msg(f"MOVED_{distance}_{direction}")

    except Exception as e:
        print(f"Client error: {e}")
    finally:
        conn.close()

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((TCP_IP, TCP_PORT))
    s.listen(1)
    print(f"Server listening on {TCP_IP}:{TCP_PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=client_thread, args=(conn, addr), daemon=True).start()

# ---------------- Main ----------------
try:
    start_server()
except KeyboardInterrupt:
    running = False
    GPIO.cleanup()
