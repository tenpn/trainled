from network_manager import NetworkManager
import train_secrets
import trains_azure
import cached_mileage
import math
import uasyncio
import time
import plasma
from plasma import plasma_stick
from machine import Pin

NUM_LEDS = 96

# set up the Pico W's onboard LED
pico_led = Pin('LED', Pin.OUT)

# set up the WS2812 / NeoPixel™ LEDs
led_strip = plasma.WS2812(NUM_LEDS, 0, 0, plasma_stick.DAT, color_order=plasma.COLOR_ORDER_GRB)

def show_error():
    for i in range(NUM_LEDS):
        led_strip.set_rgb(i, 255, 0, 0)

def status_handler(mode, status, ip):
    # reports wifi connection status
    print(mode, status, ip)
    print('Connecting to wifi...')
    # flash while connecting
    for i in range(min(20, NUM_LEDS)):
        led_strip.set_rgb(i, 255, 255, 255)
        time.sleep(0.02)
    for i in range(min(20, NUM_LEDS)):
        led_strip.set_rgb(i, 0, 0, 0)
    if status is not None:
        if status:
            print('Wifi connection successful!')
        else:
            print('Wifi connection failed!')
            show_error()
            
def update_trains():
    # draw stations
    
    total_separation = sum(cached_mileage.distances)
    station_indicies = []
    next_led_index = 0
    # one more station than the separation between stations
    for stn_index in range(cached_mileage.station_count):
        prev_led_index = next_led_index
        if stn_index > 0:
            # pad the tracks
            track_length_between_stations = math.floor(NUM_LEDS * (cached_mileage.distances[stn_index-1]/total_separation))
            next_led_index += track_length_between_stations

        for bg_index in range(prev_led_index+1, next_led_index):
            led_strip.set_rgb(bg_index, 0, 0, 0)
            
        led_strip.set_rgb(next_led_index, 200, 200, 200)
        station_indicies.append(next_led_index)
        
    # draw trains
    (lr_train_positions, rl_train_positions, now, lr_station_names) = trains_azure.get_latest_train_positions()

    for (prev_stn_index, prop) in lr_train_positions:
        station_interval = station_indicies[prev_stn_index + 1] - station_indicies[prev_stn_index]
        train_char_index = station_indicies[prev_stn_index] + math.floor(prop * station_interval)
        led_strip.set_rgb(train_char_index, 255, 50, 50)

    for (prev_stn_index, prop) in rl_train_positions:
        # we're going left
        station_interval = station_indicies[prev_stn_index] - station_indicies[prev_stn_index - 1]
        train_char_index = station_indicies[prev_stn_index - 1] + math.floor(prop * station_interval)
        led_strip.set_rgb(train_char_index, 50, 255, 50)

if __name__=="__main__":

    # start updating the LED strip
    led_strip.start()
    
    # set up wifi
    try:
        network_manager = NetworkManager(train_secrets.WIFI_COUNTRY, status_handler=status_handler)
        uasyncio.get_event_loop().run_until_complete(network_manager.client(train_secrets.WIFI_SSID, train_secrets.WIFI_PSK))
        while True:
            update_trains()
            time.sleep(30)
        
    except Exception as e:
        print(f'Wifi connection failed! {e}')
        # if no wifi, then you get...
        show_error()
