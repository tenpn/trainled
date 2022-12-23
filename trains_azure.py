import requests
from typing import Dict, List, Tuple, Union
import math
import train_secrets
import cached_mileage

#URL = "http://localhost:7071/api/trainline"
URL = "https://ldbws-line.azurewebsites.net/api/trainline"
    
def query(left: str, right: str) -> requests.Response:
    fullURL = f"{URL}/?left_crs={left}&right_crs={right}&code={train_secrets.AZURE_AUTH_CODE}"
    return requests.get(fullURL)

def get_train_position_from_station_times(train_times_at_stations: List[float], now: float) -> Tuple[int, float]:
    """finds where the train is based on the current time and when the train will be at each station

    Args:
        train_times_at_stations (List[float]): list of times we'll be at each station in order
        now (float): current time in decimal-hours

    Returns:
        Tuple[int, float]: (the index of our prev station, the proportional distance between prev station and next)
    """
    for stn_index in range(1, len(train_times_at_stations)):
        prev_stn_time = train_times_at_stations[stn_index-1]
        current_stn_time = train_times_at_stations[stn_index]
        
        if now > prev_stn_time and now <= current_stn_time:
            proportion = (now - prev_stn_time)/(current_stn_time - prev_stn_time)
            return (stn_index-1, proportion)
        
    return None

def make_ascii_tracks(station_chars: List[str], station_separations: List[float]) -> Tuple[str, List[int]]:
    """makes the ascii string of the train tracks, and a list of indeices of each station. uses distance info

    Args:        
        station_chars (List[str]): the char to use for each station in the route
        station_separations (List[float]): the distance between each pair of stations. assumed to be 1 less than station_chars.

    Returns:
        Tuple[str, List[int]]: the tracks, with a char for each station, with a list of string indicies of each station
    """
    rail_length = 50
    total_separation = sum(station_separations)
    track_str = ""
    station_indicies = []
    for stn_index in range(len(station_chars)):
        if stn_index > 0:
            # pad the tracks
            track_length_between_stations = math.floor(rail_length * (station_separations[stn_index-1]/total_separation))
            track_str += "-" * track_length_between_stations

        track_str += station_chars[stn_index]
        station_indicies.append(len(track_str))

    return (track_str, station_indicies)

def str_from_decimal_time(dec_time: float) -> str:
    hrs = math.floor(dec_time)
    mins = math.floor((dec_time-hrs)*60)
    return f"{hrs}:{mins}"

if __name__=="__main__":
    distances = cached_mileage.distances
    
    trains_response = query(train_secrets.LEFT_STATION_CRS, train_secrets.RIGHT_STATION_CRS)
    if trains_response.ok == False:
        print("something went wrong: " + str(trains_response))
        exit(1)
        
    trains = trains_response.json()
        
    # [{crs: CRS, time: float}, ...]
    lr_train_locs = trains["lr"]    
    rl_train_locs = trains["rl"]
    
    now = trains["now"]
    print(str_from_decimal_time(now))
    
    print(">")
    print("\n".join([", ".join([f"{stop['crs'].lower()}@{str_from_decimal_time(stop['time'])}" for stop in train_loc]) 
          for train_loc in lr_train_locs]))

    print("<")
    print("\n".join([", ".join([f"{stop['crs'].lower()}@{str_from_decimal_time(stop['time'])}" for stop in train_loc])
          for train_loc in rl_train_locs]))
    
    # doesn't matter which train we use, stations are the same
    station_chars = [stn['crs'][0] for stn in lr_train_locs[0]]
    (tracks_str, station_indicies) = make_ascii_tracks(station_chars, distances)

    lr_train_positions = [get_train_position_from_station_times([stn['time'] for stn in train_loc], now) 
                          for train_loc in lr_train_locs]
    lr_train_positions = [train_pos for train_pos in lr_train_positions if train_pos is not None]
    
    rl_train_positions = [get_train_position_from_station_times([stn['time'] for stn in train_loc], now)
                          for train_loc in rl_train_locs]
    rl_train_positions = [train_pos for train_pos in rl_train_positions if train_pos is not None]
    # need to flip indicies for the other direction
    rl_train_positions = [(len(station_indicies) - prev_stn_index-1, 1-prop) for (prev_stn_index,prop) in rl_train_positions]

    for (prev_stn_index, prop) in lr_train_positions:
        station_interval = station_indicies[prev_stn_index + 1] - station_indicies[prev_stn_index]
        train_char_index = station_indicies[prev_stn_index] + math.floor(prop * station_interval)
        tracks_str = tracks_str[:train_char_index] + '>' + tracks_str[train_char_index+1:]
    
    for (prev_stn_index, prop) in rl_train_positions:
        # we're going left
        station_interval = station_indicies[prev_stn_index] - station_indicies[prev_stn_index - 1]
        train_char_index = station_indicies[prev_stn_index - 1] + math.floor(prop * station_interval)
        tracks_str = tracks_str[:train_char_index] + '<' + tracks_str[train_char_index+1:]

    print(tracks_str)
