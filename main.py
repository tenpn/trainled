from network_manager import NetworkManager
import train_secrets
import trains_azure
import cached_mileage
import trains_ascii
import math
import collections
import uasyncio
import time
import plasma
from plasma import plasma_stick
from machine import Pin

NUM_LEDS = 96
NET_REFRESH_INTERVAL = 120
LED_REFRESH_INTERVAL = 0.1
LED_REFRESHES_PER_NET_REFRESH = math.floor(NET_REFRESH_INTERVAL / float(LED_REFRESH_INTERVAL))
CHANGE_BLEND_DURATION = 1
SPEED_MULT = 2.0

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

TrainlineIndicies = collections.namedtuple("TrainlineIndicies", ["stations", "lr", "rl"])            

def calc_timetable_indicies_at(now, lr_timetable, rl_timetable) -> TrainlineIndicies:
    total_separation = sum(cached_mileage.distances)
    station_indicies = []
    next_led_index = 0
    
    # one more station than the separation between stations
    for stn_index in range(cached_mileage.station_count):
        if stn_index > 0:
            # pad the tracks
            track_length_between_stations = math.floor(NUM_LEDS * (cached_mileage.distances[stn_index-1]/total_separation))
            next_led_index += track_length_between_stations
        
        station_indicies.append(next_led_index)
        
    # draw trains
    lr_train_indices = []
    
    (lr_train_positions, rl_train_positions) = trains_azure.get_train_positions_at(now, lr_timetable, rl_timetable)

    for (prev_stn_index, prop) in lr_train_positions:
        station_interval = station_indicies[prev_stn_index + 1] - station_indicies[prev_stn_index]
        train_char_index = station_indicies[prev_stn_index] + math.floor(prop * station_interval)
        lr_train_indices.append(train_char_index)
        
    rl_train_indices = []

    for (prev_stn_index, prop) in rl_train_positions:
        # we're going left
        station_interval = station_indicies[prev_stn_index] - station_indicies[prev_stn_index - 1]
        train_char_index = station_indicies[prev_stn_index - 1] + math.floor(prop * station_interval)
        rl_train_indices.append(train_char_index)
        
    #station_names = trains_azure.get_station_names_from_timetable(lr_timetable)
    #print(trains_ascii.render_ascii_tracks(lr_train_positions, rl_train_positions, station_names))
    
    return TrainlineIndicies(station_indicies, lr_train_indices, rl_train_indices)

def lerp_col(c0, c1, t: float):
    """lerps between two arrays of identical lenght

    Args:
        c0 (List[float]]): 
        c1 (List[float]): 
        t (float): 0..1

    Returns:
        List[float]: memberwise lerp, does not clamp. floors to int.
    """
    return [math.floor(c0[i]*(1-t) + c1[i]*t) for i in range(len(c1))]

def draw_timetable_indicies(prev : TrainlineIndicies, current : TrainlineIndicies, blend: float) -> None:
    for i in range(NUM_LEDS):
        prev_col = (100,200,100) if i in prev.rl \
            else (200,100,100) if i in prev.lr \
            else (150,150,150) if i in prev.stations \
            else (0,0,0)
        current_col = (100, 200, 100) if i in current.rl \
            else (200, 100, 100) if i in current.lr \
            else (150, 150, 150) if i in current.stations \
            else (0, 0, 0)
        lerped_col = lerp_col(prev_col, current_col, blend) 
        led_strip.set_rgb(i, lerped_col[0], lerped_col[1], lerped_col[2])

if __name__=="__main__":

    # start updating the LED strip
    led_strip.start()
    
    # set up wifi
    try:
        network_manager = NetworkManager(train_secrets.WIFI_COUNTRY, status_handler=status_handler)
        uasyncio.get_event_loop().run_until_complete(network_manager.client(train_secrets.WIFI_SSID, train_secrets.WIFI_PSK))
        
        current_timetable_tickms : int = 0
        prev_trainline : TrainlineIndicies = None
        current_trainline : TrainlineIndicies = None  
        last_change_tickms : int = 0;

        while True:
            print("update start")
            
            # ask this before we start drawing, so it doesn't stall things
            timetables = trains_azure.get_timetables()
            if timetables is None:
                show_error()
                time.sleep(NET_REFRESH_INTERVAL)
            else:
                current_timetable_tickms = time.ticks_ms()
                print(f"got new timetable at {current_timetable_tickms}")
                
                for i in range(LED_REFRESHES_PER_NET_REFRESH):
                    now_ticksms = time.ticks_ms()
                    
                    generated_age_s = SPEED_MULT * time.ticks_diff(now_ticksms, current_timetable_tickms)/1000
                    now = timetables.generatedAt + (generated_age_s/60/60)
                    
                    new_trainline = \
                        calc_timetable_indicies_at(now, timetables.lr_timetable, timetables.rl_timetable)
                        
                    if prev_trainline is None:
                        current_trainline = new_trainline
                        prev_trainline = new_trainline
                        last_change_tickms = now_ticksms
                        
                    if current_trainline.lr != new_trainline.lr or current_trainline.rl != new_trainline.rl:
                        last_change_tickms = now_ticksms
                        prev_trainline = current_trainline
                        current_trainline = new_trainline

                    s_since_change = time.ticks_diff(now_ticksms, last_change_tickms)/1000
                    blend = min(1, s_since_change/CHANGE_BLEND_DURATION)

                    draw_timetable_indicies(prev_trainline, current_trainline, blend)

                    time.sleep(LED_REFRESH_INTERVAL)
        
    except Exception as e:
        print(f'Wifi connection failed! {e}')
        # if no wifi, then you get...
        show_error()
