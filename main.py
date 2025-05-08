import micropython

from machine import Pin, I2C
from ssd1306 import SSD1306_I2C

from components.Encoder import Encoder
from components.Switch import Switch
from components.Display import Display
from components.Sensor import SensorFifo

from menu import Menu
from measurement import LiveHRMeasurement, AnalysisMeasurement
from capture_history import History
from network_handlers import NetworkHandler, MQTTHandler

micropython.alloc_emergency_exception_buf(200)

rot = Encoder(10, 11)
switch = Switch(12, Pin.IN, Pin.PULL_UP)

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
i2c = I2C(1, scl = Pin(15), sda = Pin(14), freq = 400000)
display = Display(DISPLAY_WIDTH, DISPLAY_HEIGHT, i2c, line_spacing = 1)
display.clear()

# WLAN & MQTT config
WLAN_SSID = "KMD652_Group_7"
WLAN_PASSWORD = "RyhMa7paSS"
MQTT_BROKER_IP = "192.168.7.252"
MQTT_BROKER_PORT = 21883

# initialize wlan & mqtt connection
WLAN = NetworkHandler(display, WLAN_SSID, WLAN_PASSWORD)
MQTT = MQTTHandler(display, MQTT_BROKER_IP, MQTT_BROKER_PORT)
wlan_connected = WLAN.connect()

# initialize the menu
menu_items = [
    ("Instant HR", LiveHRMeasurement(display, switch, 1024).run),
    ("HRV Analysis", AnalysisMeasurement(display, switch, 1024, with_kubios = False, mqtt_handler = MQTT).run),
    ("History", History(display, switch, rot, "history").run),
]

if wlan_connected: # initialize mqtt connection & add kubios to menu if wlan is connected
    MQTT.connect()
    menu_items.insert(2, ("Kubios", AnalysisMeasurement(display, switch, 1024, with_kubios = True, mqtt_handler = MQTT).run))

menu = Menu(
    display = display,
    options = [item[0] for item in menu_items],
    actions = [item[1] for item in menu_items],
    text_size = 16
)
menu.show()

# main loop
while True:
    if rot.fifo.has_data():
        delta = rot.fifo.get()
        menu.move_pointer(delta)
        menu.show()
    
    if switch.single_press():
        menu.select()() # main functionalities happen here
        display.clear()
        menu.show()
        continue