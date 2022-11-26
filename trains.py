import requests
from typing import Dict

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
URL = "https://huxley2.azurewebsites.net"

def query(path: str) -> str:
    return f"{URL}/{path}?accessToken={SECRETS['access_key']}"

right_from_left_query = query(f"arrivals/{SECRETS['right_stn']}/from/{SECRETS['left_stn']}/2")
print(right_from_left_query)
right_from_left = requests.get(right_from_left_query)
trains = right_from_left.json().get("trainServices")
for train in trains:
    print(f"train {train['serviceIdUrlSafe']} from {train['origin'][0]['locationName']} to {train['destination'][0]['locationName']}")
    train_info = requests.get(query(f"service/{train['serviceIdUrlSafe']}")).json()
    print(f'due to arrive at {train_info["sta"]}')
    

