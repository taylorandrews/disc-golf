import os
import json

path_to_data = "data/tournament_90947_MPO_round12.json"

def main():
    print("Hello, World!")

if __name__ == "__main__":
    with open(path_to_data, 'r') as file:
        data_str = file.read()
        data = json.loads(data_str)
        
    for pool in data["data"]:
       for layout in pool["layouts"]:
           print(layout["LayoutID"])