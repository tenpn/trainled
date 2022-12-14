import cached_mileage
import train_secrets
import math
import collections

try:
    import urequests as requests
except ImportError:
    import requests

#URL = "http://localhost:7071/api/trainline"
URL = "https://ldbws-line.azurewebsites.net/api/trainline"
    
def query(left, right):
    """_summary_

    Args:
        left (str): _description_
        right (str): _description_

    Returns:
        _type_: a (u)request object
    """
    fullURL = f"{URL}/?left_crs={left}&right_crs={right}&code={train_secrets.AZURE_AUTH_CODE}"
    return requests.get(fullURL)

def get_train_position_from_timetable_entry(train_times_at_stations, now):
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

def str_from_decimal_time(dec_time) -> str:
    hrs = math.floor(dec_time)
    mins = math.floor((dec_time-hrs)*60)
    return f"{hrs:02}:{mins:02}"

Timetables = collections.namedtuple("Timetables", ["lr_timetable", "rl_timetable", "generatedAt"])

def get_station_names_from_timetable(lr_timetable):
    """assumes valid timetables

    Args:
        lr_timetable: 

    Returns:
        List[str]: station CRSs from left to right
    """
    return [stn['crs'] for stn in lr_timetable[0]]

IS_SIMULATED: bool = True

def get_simulated_timetable(station_names, distances, start_time: float, finish_time:float):
    total_distance = cached_mileage.total_mileage
    speed = (finish_time - start_time)/total_distance
    timetable = []
    now = start_time
    for i in range(len(station_names)):
        if i > 0:
            now = now + distances[i-1] * speed
        timetable.append({"crs": station_names[i], "time": now})
    return timetable    

def get_simulated_timetables():
    filler_station_count = cached_mileage.station_count-2
    filler_station_names = [str(i+1) for i in range(filler_station_count)]
    station_names = [train_secrets.LEFT_STATION_CRS] + filler_station_names + [train_secrets.RIGHT_STATION_CRS]
    rl_station_names = list(reversed(station_names))
    rl_distances = list(reversed(cached_mileage.distances))
    
    now = 10
    return Timetables(
        [
            get_simulated_timetable(station_names, cached_mileage.distances, 9.6, 10.1),
            get_simulated_timetable(station_names, cached_mileage.distances, 9.8, 10.3),
            get_simulated_timetable(station_names, cached_mileage.distances, 10, 10.5), 
            get_simulated_timetable(station_names, cached_mileage.distances, 10.1, 10.6),
        ],
        [
            get_simulated_timetable(rl_station_names, rl_distances, 9.6, 10.1),
            get_simulated_timetable(rl_station_names, rl_distances, 9.8, 10.3),
            get_simulated_timetable(rl_station_names, rl_distances, 10, 10.5),
            get_simulated_timetable(rl_station_names, rl_distances, 10.1, 10.6),
        ],
        now
    )

def get_timetables() -> Timetables:
    """ask azure for latest timetables

    Returns:
        Timetables: None if something went wrong
    """
    if IS_SIMULATED:
        return get_simulated_timetables()
        
    trains_response = query(train_secrets.LEFT_STATION_CRS, train_secrets.RIGHT_STATION_CRS)

    if trains_response.status_code != 200:
        print(f"something went wrong: code {trains_response.status_code} {trains_response}")
        trains_response.close()
        return None

    trains = trains_response.json()
    trains_response.close()
    
    return Timetables(trains["lr"], trains["rl"], trains["now"])

def print_timetable(lr_timetable, rl_timetable, now: float) -> None:
    print(str_from_decimal_time(now))

    print(">")
    print("\n".join([", ".join([f"{stop['crs'].lower()}@{str_from_decimal_time(stop['time'])}" for stop in timetable_entry])
          for timetable_entry in lr_timetable]))

    print("<")
    print("\n".join([", ".join([f"{stop['crs'].lower()}@{str_from_decimal_time(stop['time'])}" for stop in timetable_entry])
          for timetable_entry in rl_timetable]))

def get_train_positions_at(now, lr_timetable, rl_timetable):
    """computes new train positions from the timetalbes. a position is relative to a station.

    Returns:
        Tuple[List, List]: ([(left station index, distance), ...], [(right station index, distance), ...] )
    """
    
    lr_train_positions = [get_train_position_from_timetable_entry([stn['time'] for stn in timetable_entry], now)
                          for timetable_entry in lr_timetable]
    lr_train_positions = [train_pos for train_pos in lr_train_positions if train_pos is not None]

    rl_train_positions = [get_train_position_from_timetable_entry([stn['time'] for stn in timetable_entry], now)
                          for timetable_entry in rl_timetable]
    rl_train_positions = [train_pos for train_pos in rl_train_positions if train_pos is not None]
    
    # need to flip indicies for the other direction
    rl_train_positions = [(cached_mileage.station_count - prev_stn_index-1, 1-prop)
                          for (prev_stn_index, prop) in rl_train_positions]
    
    return (lr_train_positions, rl_train_positions)
