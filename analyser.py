import os
import json
import pandas as pd
import folium
from folium import plugins
from collections import defaultdict
import datetime
import sys

def parse_gps_data(file_path):
    with open(file_path, 'r') as f:
        data = f.read()

    data = [x for x in data.split('A') if x]

    headers = ['TrackerID', 'time?', 'lon', 'lat', 'idk', 'idk', 'heading?', 'speed', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk', 'idk']
    df = pd.DataFrame([i.split('|') for i in data], columns=headers)

    df['TrackerID'] = df['TrackerID'].astype(int)
    df['speed'] = df['speed'].str.rstrip(' kn').astype(float)
    df['lat'] = df['lat'].astype(float)
    df['lon'] = df['lon'].astype(float)
    df['time?'] = df['time?'].astype(int)
    df['heading?'] = pd.to_numeric(df['heading?'], errors='coerce').fillna(0).astype(float)

    print(df.head(3))

    tracker_ids = df['TrackerID'].unique().tolist()
    print(tracker_ids, len(tracker_ids))

    traces = defaultdict(list)

    for index, row in df.iterrows():
        tracker_id = row['TrackerID']
        timestamp = row['time?']
        longitude = row['lon']
        latitude = row['lat']
        speed = row['speed']
        heading = row['heading?']

        traces[tracker_id].append({
            'timestamp': timestamp,
            'latitude': latitude,
            'longitude': longitude,
            'speed': speed,
            'heading': heading
        })

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

def create_boat_icon_svg(color, heading):
    """Create a rotated boat SVG icon"""
    svg = f'''
    <svg width="40" height="40" xmlns="http://www.w3.org/2000/svg">
        <g transform="translate(20,20) rotate({heading})">
            <path d="M0,-15 L-5,10 L0,8 L5,10 Z" fill="{color}" stroke="white" stroke-width="1"/>
            <circle cx="0" cy="0" r="2" fill="white"/>
        </g>
    </svg>
    '''
    return svg

def create_map_with_timeline(traces, race_id=None):
    avg_lat = sum(point['latitude'] for tracker in traces.values() for point in tracker) / sum(len(tracker) for tracker in traces.values())
    avg_lon = sum(point['longitude'] for tracker in traces.values() for point in tracker) / sum(len(tracker) for tracker in traces.values())
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)
    
    colors = ['blue', 'red', 'green', 'purple', 'orange', 'darkblue', 'darkred', 'darkgreen', 'cadetblue', 'pink']
    
    boat_names = load_boat_names(race_id)
    race_path = load_race_path(race_id)
    
    # Prepare features for TimestampedGeoJson
    features = []
    
    for idx, (tracker_id, points) in enumerate(traces.items()):
        print(idx, tracker_id)
        boat_name = None
        mark_name = None

        full_tracker = 'A' + str(tracker_id).zfill(4)
        boat_name = boat_names.get(full_tracker)
        mark_name = race_path.get(full_tracker)
        if mark_name is not None:
            mark_name = mark_name[0]
        print(mark_name)

        if boat_name is not None and mark_name is not None:
            print(boat_name, mark_name)
            raise Exception('Both boat_name and mark_name have values')
        elif boat_name is None and mark_name is None:
            tracker_name = full_tracker
        elif boat_name is None:
            tracker_name = mark_name
        elif mark_name is None:
            tracker_name = boat_name
        
        color = colors[idx % len(colors)]
        
        # Draw the full trace as a polyline
        locations = [(point['latitude'], point['longitude']) for point in points]
        folium.PolyLine(
            locations,
            color=color,
            weight=2.5,
            opacity=0.5,
            popup=tracker_name
        ).add_to(m)
        
        # Create timestamped features for each point
        for point in points:
            # Convert timestamp to ISO format (assuming Unix timestamp)
            try:
                dt = datetime.datetime.fromtimestamp(point['timestamp'])
                time_str = dt.isoformat()
            except:
                time_str = datetime.datetime.fromtimestamp(point['timestamp']/1000).isoformat()
            
            icon_svg = create_boat_icon_svg(color, point['heading'])
            
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [point['longitude'], point['latitude']]
                },
                'properties': {
                    'time': time_str,
                    'popup': f"{tracker_name}<br>Speed: {point['speed']:.1f} kts<br>Heading: {point['heading']:.0f}°",
                    'icon': icon_svg,
                    'iconstyle': {
                        'markerColor': color,
                        'color': 'white'
                    },
                    'style': {
                        'color': color,
                        'weight': 3
                    },
                    'heading': point['heading'],
                    'tracker_name': tracker_name,
                    'speed': point['speed']
                }
            }
            features.append(feature)
    
    # Add TimestampedGeoJson
    plugins.TimestampedGeoJson(
        {
            'type': 'FeatureCollection',
            'features': features
        },
        period='PT1S',
        add_last_point=True,
        auto_play=True,
        loop=True,
        max_speed=10,
        loop_button=True,
        date_options='YYYY-MM-DD HH:mm:ss',
        time_slider_drag_update=True,
        duration='PT1M'
    ).add_to(m)
    
    return m

def main(file_path):
    traces = parse_gps_data(file_path)
    
    race_id = None
    path_parts = file_path.split(os.sep)
    for part in path_parts:
        if part.startswith('race_'):
            try:
                race_id = part.split('_')[1]
                break
            except (IndexError, ValueError):
                continue
    
    map_object = create_map_with_timeline(traces, race_id)
    
    output_path = 'gps_traces_timeline_map.html'
    map_object.save(output_path)
    print(f"Map with timeline saved to {output_path}")

def select_event_folder(choice_1):
    event_folders = os.listdir('events/')
    choice = choice_1
    if choice < 0 or choice >= len(event_folders):
        print('Invalid choice.')
        return None
    return os.path.join('events/', event_folders[choice])

def select_race_folder(event_folder, choice_2):
    race_folders = os.listdir(event_folder)
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