import network
import time
import machine
import ujson
from umqtt.simple import MQTTClient

class NetworkHandler:
    """handler class for network"""
    def __init__(self, display, ssid, password):
        self.SSID = ssid
        self.PASSWORD = password
        self.attempt = 0
        self.display = display
        
    def connect(self):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(self.SSID, self.PASSWORD)
        
        max_wait = 5 # wait 10 seconds to connect
        while max_wait > 0:
            if wlan.isconnected():
                print("Connected to WLAN")
                return wlan.isconnected()
            
            self.display.centered_texts([
                " ", "Connecting WLAN", " ",
                f"Try {11 - max_wait} of 10",
            ])
            
            time.sleep(1)
            max_wait -= 1
            
        print("WLAN connection failed")
        
        self.display.centered_texts([
            " ", "Connection fail", " ",
            "Continuing", "offline",
        ])
        
        time.sleep(3)

        return wlan.isconnected()

class MQTTHandler:
    def __init__(self, display, broker_ip, broker_port):
        self.BROKER_IP = broker_ip
        self.BROKER_PORT = broker_port
        self.client_id = "pico_w_client"
        self.mqtt_topics_pub = ("kubios-request", "hr-data")
        self.mqtt_topics_sub = "kubios-response"
        self.display = display
        self.is_connected = False
        self.client = None
        self.last_message = None
        
    def connect(self):
        self.display.centered_texts([" ", "Connecting MQTT"])
        
        try:
            self.client = MQTTClient(self.client_id, self.BROKER_IP, self.BROKER_PORT)
            self.client.set_callback(self.on_sub_message)
            self.client.connect(clean_session = True)
            self.client.subscribe(self.mqtt_topics_sub)
            
            print("Connected to MQTT broker")
            
            self.is_connected = True
            
        except Exception as e:
            print(f"Error occurred when connecting to MQTT broker: {e}")
            self.is_connected = False
        finally:
            return self.is_connected
       
    def on_sub_message(self, topic, message):
        print(f"Recieved MQTT message on topic: {topic}")
        print(f"Message: {message}")
        
        try:
            self.last_message = ujson.loads(message)
        except ValueError:
            print("Failed to decode JSON.")
            self.last_message = message
        
    def publish(self, topic, data):
        if self.client is None:
            raise Exception("No client to publish mqtt messages to.")
        
        if topic not in self.mqtt_topics_pub:
            raise Exception(f"Invalid MQTT topic. Please use one of the following:\n {self.mqtt_topics}")
        
        if isinstance(data, dict):
            data = ujson.dumps(data)
        
        self.client.publish(topic, data)
        
    def listen(self):
        if self.client:
            self.client.check_msg()
    
    def get_last_message(self):
        return self.last_message

    def reset_last_message(self):
        self.last_message = None
        
