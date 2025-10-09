import os
import json
import pandas as pd
import folium
import io
import os
from collections import defaultdict
import datetime
import sys

def parse_gps_data(file_path):
    # Read the CSV file into a DataFrame
    with open(file_path, 'r') as f:
        data = f.read()

    data = [x for x in data.split('A') if x]


    headers = ['TrackerID', 'time?', 'lon', 'lat', 'idk', 'idk', 'heading?', 'speed', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk']
    df = pd.DataFrame([i.split('|') for i in data], columns=headers)

    # Convert TrackerId to int
    df['TrackerID'] = df['TrackerID'].astype(int)
    # Convert speed to float
    df['speed'] = df['speed'].str.rstrip(' kn').astype(float)
    # Convert lat to float
    df['lat'] = df['lat'].astype(float)
    # Convert lon to float
    df['lon'] = df['lon'].astype(float)
    # Convert time to int
    df['time?'] = df['time?'].astype(int)

    print(df.head(3))

    tracker_ids = df['TrackerID'].unique().tolist()
    print(tracker_ids, len(tracker_ids))
    for tracker_id in tracker_ids:
        print(tracker_id)
        df[df['TrackerID'] == tracker_id]

    # Dictionary to store traces by tracker ID
    traces = defaultdict(list)

    for index, row in df.iterrows():
        # Extract relevant fields
        tracker_id = row['TrackerID']
        timestamp = row['time?']
        longitude = row['lon']
        latitude = row['lat']
        speed = row['speed']  # Speed in knots (e.g., "22.7 kn")

        # Store the point in the tracker's trace
        traces[tracker_id].append({
            'timestamp': timestamp,
            'latitude': latitude,
            'longitude': longitude,
            'speed': speed
        })

    # Sort each tracker's points by timestamp
    for tracker_id in traces:
        traces[tracker_id].sort(key=lambda x: x['timestamp'])

    return traces

def load_boat_names(race_id):
    filename = f'boats_dict_{race_id}.json'
    race_folder_name = f'race_{race_id}'
    full_path = os.path.join(directory, event_folder, race_folder_name, filename)
    with open(full_path, 'r') as f:
        return json.load(f)

def load_race_path(race_id):
    filename = f'race_path_{race_id}.json'
    race_folder_name = f'race_{race_id}'
    full_path = os.path.join(directory, event_folder, race_folder_name, filename)
    with open(full_path, 'r') as f:
        data = json.load(f)

    race_data = {}
    for mark in data:
        print(mark)
        race_data[mark['seriale1']] = [mark['boa1'], mark['boa2']]
        race_data[mark['seriale2']] = [mark['boa1'], mark['boa2']]
    
    print(race_data)
    return race_data

def create_map(traces, race_id=None):
    avg_lat = sum(point['latitude'] for tracker in traces.values() for point in tracker) / sum(len(tracker) for tracker in traces.values())
    avg_lon = sum(point['longitude'] for tracker in traces.values() for point in tracker) / sum(len(tracker) for tracker in traces.values())
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)
    
    colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkblue', 'darkred', 'darkgreen', 'cadetblue', 'pink']
    
    boat_names = load_boat_names(race_id)
    race_path = load_race_path(race_id)
    
    for idx, (tracker_id, points) in enumerate(traces.items()):
        print(idx, tracker_id)
        boat_name = None
        mark_name = None

        full_tracker = 'A' + str(tracker_id).zfill(4)
        boat_name = boat_names.get(full_tracker)
        # print(boat_name)
        mark_name = race_path.get(full_tracker)
        if mark_name is not None:
            mark_name = mark_name[0]
        print(mark_name)

        if boat_name is not None and mark_name is not None:
            print(boat_name, mark_name)
            raise Exception('Both boat_name and mark_name have values')
        elif boat_name is None and mark_name is None:
            tracker_name = full_tracker
            # raise Exception('Both boat_name and mark_name are None')
        elif boat_name is None:
            tracker_name = mark_name
        elif mark_name is None:
            tracker_name = boat_name
        
        locations = [(point['latitude'], point['longitude']) for point in points]
        folium.PolyLine(
            locations,
            color=colors[idx % len(colors)],
            weight=2.5,
            opacity=1,
            popup=tracker_name
        ).add_to(m)
        
        # Add markers for start and end points
        start_point = points[0]
        end_point = points[-1]
        
        # Start point marker
        folium.Marker(
            location=[0, 0],  # Hide the marker
            popup='',  # No popup text
            icon=folium.DivIcon(icon_size=(0, 0))  # Hide the icon
        ).add_to(m)
        
        # End point marker
        folium.Marker(
            # location=(end_point['latitude'], end_point['longitude']),
            location=[0, 0],
            # popup=f"{boat_name} - End\nSpeed: {end_point['speed']:.1f} kts\nTime: {end_point['timestamp']}",
            popup='',
            icon=folium.Icon(icon_size=(0, 0))
        ).add_to(m)
    
    return m

def main(file_path):
    # Parse the GPS data
    traces = parse_gps_data(file_path)
    
    # Extract race_id from file_path if possible
    race_id = None
    path_parts = file_path.split(os.sep)
    for part in path_parts:
        if part.startswith('race_'):
            try:
                race_id = part.split('_')[1]
                break
            except (IndexError, ValueError):
                continue
    

    map_object = create_map(traces, race_id)
    
    # Save the map to an HTML file in the same directory as the input file
    output_path = 'gps_traces_map.html'
    map_object.save(output_path)
    print(f"Map saved to {output_path}")


### FILE INPUT ###
def select_event_folder(choice_1):
    event_folders = os.listdir('events/')
    # print('Select an event folder:')
    # for i, folder in enumerate(event_folders):
    #     print(f'{i+1}. {folder}')
    # choice = int(input('Enter the number of the folder: ')) - 1
    # choice = 1
    choice = choice_1
    if choice < 0 or choice >= len(event_folders):
        print('Invalid choice.')
        return None
    return os.path.join('events/', event_folders[choice])

def select_race_folder(event_folder, choice_2):
    race_folders = os.listdir(event_folder)
    # print('Select a race folder:')
    # for i, folder in enumerate(race_folders):
    #     print(f'{i+1}. {folder}')
    # choice = int(input('Enter the number of the folder: ')) - 1
    # choice = 0
    choice = choice_2
    if choice < 0 or choice >= len(race_folders):
        print('Invalid choice.')
        return None
    return os.path.join(event_folder, race_folders[choice])

def combine_files(race_folder):
    files = os.listdir(race_folder)
    files = [file for file in files if file.isdigit()]
    files.sort(key=lambda x: int(x))
    combined_data = ''
    for file in files:
        with open(os.path.join(race_folder, file), 'r') as f:
            combined_data += f.read()
    return combined_data

if __name__ == "__main__":
    choice_1 = int(sys.argv[1])
    choice_2 = int(sys.argv[2])
    directory = os.getcwd()
    event_folder = select_event_folder(choice_1)
    if event_folder:
        race_folder = select_race_folder(event_folder, choice_2)
        if race_folder:
            print('found a folder', race_folder)
            print(os.listdir(race_folder))
            main(os.path.join(race_folder, '1'))
            combined_data = combine_files(race_folder)
            with open(os.path.join(race_folder, 'combined_data.csv'), 'w') as f:
                f.write(combined_data)
            if combined_data:
                main(os.path.join(race_folder, 'combined_data.csv'))
