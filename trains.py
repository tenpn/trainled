import requests
from typing import Dict, List
import math

URL = "https://huxley2.azurewebsites.net"

def load_secrets() -> Dict[str,str]:
    """just uses newlines to grab info and assumes ordering

    Returns:
        Dict[str,str]: the secrets data, with useful keys
    """
    with open("secrets.txt", "r") as secrets:
        lines = secrets.readlines()
        return { 
            "access_key": lines[0].strip(),
            "left_stn": lines[1].strip(),
            "right_stn": lines[2].strip(),
        }

SECRETS = load_secrets()

def load_distances() -> List[float]:
    """
    Returns:
        List[float]: the separation between the stations in floating point miles
    """
    with open("cached_mileage.txt", "r") as cached_mileage:
        return [float(line) for line in cached_mileage.readlines()]
    
DISTANCES = load_distances()
TOTAL_DISTANCE = sum(DISTANCES)
    
def query(path: str) -> str:
    return f"{URL}/{path}?accessToken={SECRETS['access_key']}"

def hours_decimal_from_time_str(time_str: str) -> float:
    """turns a HH:MM time string into a decimal, where the units are the hours since midnight and the decimal is the fraction through the hour

    Args:
        time_str (str): "hh:mm"

    Returns:
        float: hours.fraction_through_hour
    """
    # not sure if this is 24h clock or not yet?
    return int(time_str[0:2]) + (int(time_str[3:])/60.0)

right_from_left_query = query(f"arrivals/{SECRETS['right_stn']}/from/{SECRETS['left_stn']}")
print(right_from_left_query)
right_from_left = requests.get(right_from_left_query)
trains = right_from_left.json().get("trainServices")
for train in trains:
    print(f"train {train['serviceIdUrlSafe']} from {train['origin'][0]['locationName']} to {train['destination'][0]['locationName']}")
    train_info = requests.get(query(f"service/{train['serviceIdUrlSafe']}")).json()
    # train_info[previousCallingPoints] = [ { callingPoint: [ { locationName: "long name", crs: "code", st/at/at: ... }, ]}]
    # find stations between left and right inc:
    prev_locations = train_info["previousCallingPoints"][0]["callingPoint"]
    interesting_locations = []
    for prev_location in prev_locations:
        if len(interesting_locations) > 0 or prev_location["crs"].lower() == SECRETS["left_stn"].lower():
            interesting_locations.append({
                'locationName': prev_location['locationName'],
                'crs': prev_location['crs'],
                'time': hours_decimal_from_time_str(prev_location['st']),
            })
    interesting_locations.append({
        'locationName': train_info['locationName'],
        'crs': train_info['crs'],
        'time': hours_decimal_from_time_str(train_info['sta']),
    })
    
    print(str(interesting_locations))
    
    # build an ascii string for the LED string
    rail_length = 50
    station_spacing = math.floor((rail_length-1)/(len(interesting_locations)-1)) # we want the last station at the end of the str
    track_str = ""
    for stn_index in range(len(interesting_locations)):
        current_loc = interesting_locations[stn_index]
        if stn_index > 0:
            # pad the tracks
            pos_delta = DISTANCES[stn_index-1]/TOTAL_DISTANCE
            track_str += "-" * math.floor(rail_length*pos_delta)
        track_str += interesting_locations[stn_index]["crs"][0]
    
    print(track_str)
    

