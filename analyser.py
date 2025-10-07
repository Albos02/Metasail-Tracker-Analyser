import os
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

    # Dictionary to store traces by vessel ID
    traces = defaultdict(list)

    for index, row in df.iterrows():
        # Extract relevant fields
        vessel_id = row['TrackerID']
        timestamp = row['time?']
        longitude = row['lon']
        latitude = row['lat']
        speed = row['speed']  # Speed in knots (e.g., "22.7 kn")

        # Store the point in the vessel's trace
        traces[vessel_id].append({
            'timestamp': timestamp,
            'latitude': latitude,
            'longitude': longitude,
            'speed': speed
        })

    # Sort each vessel's points by timestamp
    for vessel_id in traces:
        traces[vessel_id].sort(key=lambda x: x['timestamp'])

    return traces

def create_map(traces):
    # Initialize map centered on the average coordinates
    avg_lat = sum(point['latitude'] for vessel in traces.values() for point in vessel) / sum(len(vessel) for vessel in traces.values())
    avg_lon = sum(point['longitude'] for vessel in traces.values() for point in vessel) / sum(len(vessel) for vessel in traces.values())
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)
    
    # Define colors for different vessels
    colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkblue', 'darkred', 'darkgreen', 'cadetblue', 'pink']
    
    # Plot each vessel's trace
    for idx, (vessel_id, points) in enumerate(traces.items()):
        # Create a polyline for the vessel's path
        locations = [(point['latitude'], point['longitude']) for point in points]
        folium.PolyLine(
            locations,
            color=colors[idx % len(colors)],
            weight=2.5,
            opacity=1,
            popup=f"Vessel {vessel_id}"
        ).add_to(m)
        
        # Add markers for start and end points
        start_point = points[0]
        end_point = points[-1]
        
        # Start point marker
        folium.Marker(
            location=(start_point['latitude'], start_point['longitude']),
            popup=f"Vessel {vessel_id} Start\nSpeed: {start_point['speed']}\nTime: {start_point['timestamp']}",
            icon=folium.Icon(color=colors[idx % len(colors)], icon='play')
        ).add_to(m)
        
        # End point marker
        folium.Marker(
            location=(end_point['latitude'], end_point['longitude']),
            popup=f"Vessel {vessel_id} End\nSpeed: {end_point['speed']}\nTime: {end_point['timestamp']}",
            icon=folium.Icon(color=colors[idx % len(colors)], icon='stop')
        ).add_to(m)
    
    return m

def main(file_path):
    # Parse the GPS data
    traces = parse_gps_data(file_path)

    # Create the map
    map_object = create_map(traces)
    
    # Save the map to an HTML file in the same directory as the input file
    # output_path = os.path.join(os.path.dirname(file_path), 'gps_traces_map.html')
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
