import requests
from typing import Dict, List, Tuple, Union
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

def get_locations_from_train_info(train_info: Dict) -> Dict[str, Union[str, float]]:
    """generates info about when this train will be visiting each station 

    Args:
        train_info (Dict): from huxley/service endpoint

    Returns:
        Dict[str, Union[str, float]]: { crs: "crs code", time: decimal-hours-when-train-is-due }
    """
    # train_info[previousCallingPoints] = [ { callingPoint: [ { locationName: "long name", crs: "code", st/at/at: ... }, ]}]
    # find stations between left and right inc:
    prev_locations = train_info["previousCallingPoints"][0]["callingPoint"]
    interesting_locations = []
    for prev_location in prev_locations:
        if len(interesting_locations) > 0 or prev_location["crs"].lower() == SECRETS["left_stn"].lower():
            interesting_locations.append({
                'crs': prev_location['crs'],
                'time': hours_decimal_from_time_str(prev_location['st']),
            })
    interesting_locations.append({
        'crs': train_info['crs'],
        'time': hours_decimal_from_time_str(train_info['sta']),
    })
    return interesting_locations

train_infos = [requests.get(query(f"service/{train['serviceIdUrlSafe']}")).json() for train in trains]
train_locs = [get_locations_from_train_info(train_info) for train_info in train_infos]
print("\n".join([str(train_loc) for train_loc in train_locs]))

def get_train_position_from_station_times(train_times_at_stations: List[float], now: float) -> Tuple[int, float]:
    """finds where the train is based on the current time and when the train will be at each station

    Args:
        train_times_at_stations (List[float]): list of times we'll be at each station in order
        now (float): current time in decimal-hours

    Returns:
        Tuple[int, float]: (the index of our next station, the proportional distance between last station and next)
    """
    for stn_index in range(1, len(train_locs)):
        prev_stn_time = train_times_at_stations[stn_index-1]
        current_stn_time = train_times_at_stations[stn_index]
        
        if now > prev_stn_time and now <= current_stn_time:
            proportion = (now - prev_stn_time)/(current_stn_time - prev_stn_time)
            return (stn_index-1, proportion)
        
    return None

# there's something wrong with this format?
# now = datetime.strptime("2022-12-03T20:53:08.2488111+00:00".strip(), "%Y-%m-%dT%H:%M:%S.%f%z")
# hey let's be dumb:
now = hours_decimal_from_time_str(train_infos[0]['generatedAt'][11:16])
print(now)

train_positions = [get_train_position_from_station_times([stn['time'] for stn in train_loc], now) for train_loc in train_locs]
train_positions = [train_pos for train_pos in train_positions if train_pos is not None]

def make_ascii_tracks(station_chars: List[str], station_separations: List[float]) -> Tuple[str, List[int]]:
    """makes the ascii string of the train tracks, and a list of indeices of each station. uses distance info

    Args:        
        station_chars (List[str]): the char to use for each station in the route
        station_separations (List[float]): the distance between each pair of stations. assumed to be 1 less than station_chars.

    Returns:
        Tuple[str, List[int]]: the tracks, with a char for each station, with a list of string indicies of each station
    """
    rail_length = 50
    track_str = ""
    station_indicies = []
    for stn_index in range(len(station_chars)):
        if stn_index > 0:
            # pad the tracks
            track_length_between_stations = math.floor(rail_length * (station_separations[stn_index-1]/TOTAL_DISTANCE))
            track_str += "-" * track_length_between_stations

        track_str += station_chars[stn_index]
        station_indicies.append(len(track_str))

    return (track_str, station_indicies)

station_chars = [stn['crs'][0] for stn in train_locs[0]]
(tracks_str, station_indicies) = make_ascii_tracks(station_chars, DISTANCES)

for (prev_stn_index, prop) in train_positions:
    station_interval = station_indicies[prev_stn_index+1] - station_indicies[prev_stn_index]
    train_char_index = station_indicies[prev_stn_index] + math.floor(prop * station_interval)
    tracks_str = tracks_str[:train_char_index] + '>' + tracks_str[train_char_index+1:]

print(tracks_str)
    

