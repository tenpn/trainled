import trains_azure
import cached_mileage
import math

def make_ascii_tracks(station_chars, station_separations):
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
            track_length_between_stations = math.floor(
                rail_length * (station_separations[stn_index-1]/total_separation))
            track_str += "-" * track_length_between_stations

        track_str += station_chars[stn_index]
        station_indicies.append(len(track_str))

    return (track_str, station_indicies)

if __name__=="__main__":
    (lr_train_locs, rl_train_locs, now, lr_station_names) = trains_azure.get_latest_train_positions()
    if lr_train_locs is None:
        exit(1)

    # doesn't matter which train we use, stations are the same
    station_chars = [stn[0] for stn in lr_station_names]
    (tracks_str, station_indicies) = make_ascii_tracks(station_chars, cached_mileage.distances)

    for (prev_stn_index, prop) in lr_train_locs:
        station_interval = station_indicies[prev_stn_index + 1] - station_indicies[prev_stn_index]
        train_char_index = station_indicies[prev_stn_index] + math.floor(prop * station_interval)
        tracks_str = tracks_str[:train_char_index] + '>' + tracks_str[train_char_index+1:]

    for (prev_stn_index, prop) in rl_train_locs:
        # we're going left
        station_interval = station_indicies[prev_stn_index] - station_indicies[prev_stn_index - 1]
        train_char_index = station_indicies[prev_stn_index - 1] + math.floor(prop * station_interval)
        tracks_str = tracks_str[:train_char_index] + '<' + tracks_str[train_char_index+1:]

    print(tracks_str)
