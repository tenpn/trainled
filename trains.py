import requests

def load_auth() -> str:
    with open("secrets.txt", "r") as secrets:
        return f"accessToken={secrets.readline()}"

auth_str = load_auth()
knn_from_bhm = requests.get(
    "https://huxley2.azurewebsites.net/arrivals/knn/from/bhm/2?" + auth_str)
trains = knn_from_bhm.json().get("trainServices")
for train in trains:
    print(f"train {train['serviceIdUrlSafe']} from {train['origin'][0]['locationName']} to {train['destination'][0]['locationName']}")
    train_info = requests.get(f"https://huxley2.azurewebsites.net/service/{train['serviceIdUrlSafe']}?{auth_str}").json()
    print(f'due to arrive at {train_info["sta"]}')
    

