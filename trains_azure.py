import cached_mileage
import train_secrets
import math

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

def get_train_position_from_station_times(train_times_at_stations, now):
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
    return f"{hrs}:{mins}"

def get_latest_train_positions():
    """computes new train positions from the internet

    Returns:
        Tuple[List, List, float, List[str]]: ([(left station index, distance), ...], [(right station index, distance), ...], decimal time now, l>r station CRSs)
    """
    trains_response = query(train_secrets.LEFT_STATION_CRS, train_secrets.RIGHT_STATION_CRS)
    print(trains_response)
    if trains_response.status_code != 200:
        print("something went wrong: " + str(trains_response))
        trains_response.close()
        return (None,None,0,None)

    trains = trains_response.json()
    trains_response.close()
        
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
    
    lr_station_names = [stn['crs'] for stn in lr_train_locs[0]]
    
    lr_train_positions = [get_train_position_from_station_times([stn['time'] for stn in train_loc], now)
                          for train_loc in lr_train_locs]
    lr_train_positions = [train_pos for train_pos in lr_train_positions if train_pos is not None]

    rl_train_positions = [get_train_position_from_station_times([stn['time'] for stn in train_loc], now)
                          for train_loc in rl_train_locs]
    rl_train_positions = [train_pos for train_pos in rl_train_positions if train_pos is not None]
    
    # need to flip indicies for the other direction
    rl_train_positions = [(cached_mileage.station_count - prev_stn_index-1, 1-prop)
                          for (prev_stn_index, prop) in rl_train_positions]
    
    return (lr_train_positions, rl_train_positions, now, lr_station_names)
