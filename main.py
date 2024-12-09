from machine import Pin, ADC, SoftI2C, RTC, Timer
from time import sleep, ticks_ms, ticks_diff
import network
import socket
from tsl2591 import Tsl2591
import BME280

# Initialize Sensors
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))  # For BME280
bme = BME280.BME280(i2c=i2c)

i2c_light = SoftI2C(scl=Pin(18), sda=Pin(19))  # For TSL2591
tsl = Tsl2591()  # Initialize TSL2591 sensor

# ADC and Flow Sensor Initialization
pH_pin = 36
flowmeter_pin = 39
adcPH = ADC(Pin(pH_pin))
adcPH.atten(ADC.ATTN_11DB)  # Configure ADC for 3.3V range
flow_frequency = 0
cloopTime = ticks_ms()

# Network setup
ssid = "HANZE-ZP11"
password = "sqr274YzW6"

def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        print("Connecting to WiFi...")
        sleep(1)
    print(f"Connected to WiFi: {wlan.ifconfig()}")
    return wlan

# Flow interrupt handler
def flow(pin):
    global flow_frequency
    flow_frequency += 1

flowmeter = Pin(flowmeter_pin, Pin.IN, Pin.PULL_DOWN)
flowmeter.irq(trigger=Pin.IRQ_RISING, handler=flow)

# Sensor Reading Functions
def read_pH():
    adc_value = adcPH.read()
    pH_SLOPE = -0.0051
    pH_INTERCEPT = 15.449
    return adc_value * pH_SLOPE + pH_INTERCEPT

def read_luminosity():
    full, ir = tsl.get_full_luminosity()
    lux = tsl.calculate_lux(full, ir)
    return lux

def read_flow():
    global flow_frequency
    current_time = ticks_ms()
    if ticks_diff(current_time, cloopTime) >= 10000:
        liters_per_hour = int((flow_frequency * 60) / 7.5)
        flow_frequency = 0  # Reset for next calculation
        return liters_per_hour
    return 0

def read_bme280():
    temperature = bme.temperature
    return temperature

# Web Server Functionality
def web_page(temp, pH, flow, lux):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ESP32 Sensor Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; }}
            .data-box {{ margin: 20px; padding: 10px; border: 1px solid #ccc; display: inline-block; }}
        </style>
    </head>
    <body>
        <h1>ESP32 Sensor Dashboard</h1>
        <div class="data-box">
            <h2>Temperature</h2>
            <p>{temp} °C</p>
        </div>
        <div class="data-box">
            <h2>pH</h2>
            <p>{pH:.2f}</p>
        </div>
        <div class="data-box">
            <h2>Flow Rate</h2>
            <p>{flow} L/h</p>
        </div>
        <div class="data-box">
            <h2>Luminosity</h2>
            <p>{lux:.2f} Lux</p>
        </div>
    </body>
    </html>
    """
    return html

def start_web_server():
    wlan = connect_to_wifi()
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("Web server running on:", addr)

    while True:
        conn, addr = s.accept()
        print("Client connected from:", addr)
        request = conn.recv(1024).decode('utf-8')
        print("Request:", request)

        # Gather sensor data
        temp = read_bme280()
        pH = read_pH()
        flow = read_flow()
        lux = read_luminosity()

        # Respond with HTML
        response = web_page(temp, pH, flow, lux)
        conn.send("HTTP/1.1 200 OK\nContent-Type: text/html\nConnection: close\n\n")
        conn.sendall(response)
        conn.close()

# Start the web server
start_web_server()
