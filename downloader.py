import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json
import zipfile
import sys


class GetHTMLFile:
    def __init__(self, url):
        self.event_url = url
        # self.driver = driver
        chrome_options = Options()
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        self.driver = webdriver.Chrome(options=chrome_options)
    def get_eventPHP_file(self):
        file = None
        i1 = 0
        self.driver.get(self.event_url)
        while file is None and i1 < 5:
            i2 = 0
            while self.driver.current_url != self.event_url and i2 < 2:
                self.driver.get(self.event_url)
                time.sleep(0.2*i2)
                i2 += 1
            requests_found = self.get_all_network_requests()
            for req in requests_found:
                if "php" in req['url']:
                    print(req)
                    print('')
                    event_php_file = requests.get(req['url'])
                    file = event_php_file.text
            i1 += 1
        return file
    def get_all_network_requests(self):
        """Extract all network requests from performance logs"""
        logs = self.driver.get_log('performance')
        requests = []
        
        for log in logs:
            try:
                message = json.loads(log['message'])['message']
                method = message.get('method')
                
                if method == 'Network.responseReceived':
                    params = message['params']
                    response = params['response']
                    
                    requests.append({
                        'url': response['url'],
                        'status': response['status'],
                        'mime_type': response.get('mimeType', ''),
                        'request_id': params.get('requestId', ''),
                    })
                    
            except (KeyError, json.JSONDecodeError):
                continue
        
        return requests

class HTMLParser:
    def __init__(self, HTML_FILE_CONTENT):
        self.HTML_FILE_CONTENT = HTML_FILE_CONTENT
        self.soup = BeautifulSoup(HTML_FILE_CONTENT, 'html.parser')
        self.event_data = {}

    def parse_event_details(self):
        """Extract main event details like name, location, dates, and categories."""
        event_header = self.soup.find('div', class_='single-event-header')
        if event_header:
            title = event_header.find('h5').text.strip() if event_header.find('h5') else ''
            dates = event_header.find('p').text.strip() if event_header.find('p') else ''
            
            # Extract event name and location from title
            # Example: "2025 FORMULA KITE WORLD CHAMPIONSHIPS – Cagliari"
            event_name_match = re.match(r'(.+?)\s*–\s*(.+)', title)
            if event_name_match:
                event_name = event_name_match.group(1).strip()
                location = event_name_match.group(2).strip()
            else:
                event_name = title
                location = ''

            self.event_data['event_name'] = event_name
            self.event_data['location'] = location
            self.event_data['dates'] = dates
            self.event_data['full_title'] = title

        # Extract categories
        categories = self.soup.find('div', class_='single-event-classi')
        if categories:
            category_text = categories.find('dl').text.strip() if categories.find('dl') else ''
            self.event_data['categories'] = category_text

        # Extract official website
        website = self.soup.find('div', class_='single-event-site')
        if website:
            website_link = website.find('a')['href'] if website.find('a') else ''
            self.event_data['website'] = website_link

        # Extract event logo URL
        logo = self.soup.find('div', class_='single-event-logo')
        if logo and logo.find('img'):
            self.event_data['logo_url'] = logo.find('img')['src']

    def parse_races(self):
        """Extract race information organized by date."""
        race_blocks = self.soup.find_all('div', class_='single-block-list')
        races_by_date = {}

        for block in race_blocks:
            date_headers = block.find_all('h4')
            for date_header in date_headers:
                date = date_header.text.strip()
                races = []
                race_list = date_header.find_next('ul')
                if race_list:
                    for race_item in race_list.find_all('li'):
                        race_info = {}
                        event_name = race_item.find('div', class_='event-name')
                        if event_name:
                            race_title = event_name.find('a').text.strip() if event_name.find('a') else ''
                            race_info['title'] = race_title
                            race_info['race_link'] = event_name.find('a')['href'] if event_name.find('a') else ''
                            
                            # Extract ranking link
                            ranking_btn = event_name.find('a', class_='view-ranking--btn')
                            race_info['ranking_link'] = ranking_btn['href'] if ranking_btn else ''
                            
                            # Extract export data
                            export_btn = event_name.find('a', class_='export--btn')
                            if export_btn:
                                race_info['export_id'] = export_btn.get('data-id', '')
                                race_info['start_time'] = export_btn.get('data-start-at', '')
                            
                            # Extract category and order from data-order
                            data_order = event_name.get('data-order', '')
                            category_match = re.match(r'1_(formula-kite-[a-z]+)_(\d+)', data_order)
                            if category_match:
                                race_info['category'] = category_match.group(1)
                                race_info['order'] = category_match.group(2)
                            
                            races.append(race_info)
                races_by_date[date] = races

        self.event_data['races'] = races_by_date

    def parse_social_form(self):
        """Extract social form details and introductory text."""
        social_form = self.soup.find('form', id='social-links-form')
        if social_form:
            self.event_data['social_form'] = {
                'action': social_form.get('action', ''),
                'method': social_form.get('method', ''),
                'fields': ['social_link', 'social-links-policy-acceptance']
            }

        # Extract social links introductory text
        social_intro = self.soup.find('div', class_='social-links--intro')
        if social_intro:
            intro_text = ' '.join([p.text.strip() for p in social_intro.find_all('p')])
            self.event_data['social_intro'] = intro_text

    def get_event_data(self):
        """Run all parsing methods and return the collected data."""
        self.parse_event_details()
        self.parse_races()
        self.parse_social_form()
        return self.event_data

    def get_race_summary(self):
        """Generate a summary of races by date and category."""
        summary = {}
        for date, races in self.event_data.get('races', {}).items():
            categories = []
            for race in races:
                try:
                    categories.append(race['category'])
                except KeyError:
                    pass
            summary[date] = {
                'total_races': len(races),
                'categories': list(set(categories)),
                'race_titles': [race.get('title', '') for race in races]
            }
        return summary

class SessionIDExtractor:
    def __init__(self, driver):
        self.driver = driver
        # self.driver.get("https://app.metasail.it/live/776/")
    def get_id(self, race_id, url):
        self.driver.get(url)
        self.current_url = self.driver.current_url
        self.session_id = self.current_url.split("S(")[1].split(")")[0]
        return self.session_id
class BoatsDictExtractor:
    def __init__(self, driver):
        self.driver = driver
    def get_boats_dict(self, race_id, url):
        if race_id not in self.driver.current_url:
            self.driver.get(url)
        html_content = self.driver.page_source
        return self.page_source_parser(html_content)
    def page_source_parser(self, html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        boat_container = soup.find("div", id="barcheDivScrollabile")
        boat_entries = boat_container.find_all("div", class_="row")
        boats_dict = {}
        for boat in boat_entries:
            tracker_id = boat["id"].split("-")[1]
            boat_name = boat.find("div", class_="descrizione").text.strip()
            boats_dict[tracker_id] = boat_name
        return boats_dict
class RacePathListExtractor:
    def __init__(self, driver):
        self.driver = driver
    def get_race_path_list(self, race_id, url):
        if race_id not in self.driver.current_url:
            self.driver.get(url)
        html_content = self.driver.page_source
        return self.page_source_parser(html_content)
    def page_source_parser(self, html_content):
        match = re.search(r"var racePathList = (\[.*?\]);", html_content, re.DOTALL)
        if match:
            race_path_list_str = match.group(1)
            cleaned_str = race_path_list_str.replace("'", '"')
            try:
                race_path_list_data = json.loads(cleaned_str)
                return race_path_list_data
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
        else:
            print("Could not find the 'racePathList' variable in the file.")

class ZipDownloader:
    def __init__(self, directory, session_id, export_id):
        print(directory, session_id, export_id)
        self.directory = directory
        self.url = 'https://app.metasail.it/' + '(S(' + session_id + '))' + '/race_' + export_id + '.zip'
        self.export_id = export_id

    def get_zip(self):
        try:
            # Create directories if they don't exist
            os.makedirs(self.directory, exist_ok=True)
            # Download the ZIP file
            response = requests.get(self.url)
            response.raise_for_status()  # Raise an error for bad status codes
            zip_path = os.path.join(self.directory, f"race_{self.export_id}.zip")
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            return f"Downloaded {zip_path}"
        except requests.RequestException as e:
            return f"Failed to download {self.url}: {e}"
        except OSError as e:
            return f"Failed to save {zip_path}: {e}"

class ZipExtractor:
    def __init__(self, event_path):
        self.event_path = event_path
        self.zip_file_list = self.list_zip_files()
    def list_zip_files(self):
        """List all ZIP files in the event directory."""
        zip_files = []
        for file in os.listdir(self.event_path):
            if file.endswith('.zip'):
                zip_files.append(os.path.join(self.event_path, file))
        print('ZIP files found:', zip_files)
        return zip_files
    def extract_all_zips(self):
        race_data_files = [file for file in os.listdir(self.event_path) if 'race_data_' in file]
        boats_dict_files = [file for file in os.listdir(self.event_path) if 'boats_dict_' in file]
        race_path_files = [file for file in os.listdir(self.event_path) if 'race_path_' in file]

        for zip_file in self.zip_file_list:
            zip_file_path = os.path.join(self.event_path, zip_file.replace('.zip', ''))
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(zip_file_path)
            
            race_id = zip_file.split('race_')[1].split('.zip')[0]

            # Moving race_data files
            race_data_file = 'race_data_' + race_id + '.json'
            race_data_file_path = os.path.join(zip_file_path, race_data_file)
            os.rename(os.path.join(self.event_path, race_data_file), race_data_file_path)

            # Moving boats_dict files
            boats_dict_file = 'boats_dict_' + race_id + '.json'
            boats_dict_file_path = os.path.join(zip_file_path, boats_dict_file)
            os.rename(os.path.join(self.event_path, boats_dict_file), boats_dict_file_path)

            # Moving boats_dict files
            race_path_file = 'race_path_' + race_id + '.json'
            race_path_file_path = os.path.join(zip_file_path, race_path_file)
            os.rename(os.path.join(self.event_path, race_path_file), race_path_file_path)

    def remove_zip_files(self):
        for zip_file in self.zip_file_list:
            print(f"Removing {zip_file}")
            os.remove(os.path.join(self.event_path, zip_file))

if __name__ == "__main__":
    event_id = sys.argv[1]
    url = 'https://www.metasail.com/live/' + event_id
    directory = os.getcwd()

    html_finder = GetHTMLFile(url)
    HTML_FILE_CONTENT = None
    i = 0
    while HTML_FILE_CONTENT is None and i < 5:
        HTML_FILE_CONTENT = html_finder.get_eventPHP_file()
        i += 1
    
    html_parser = HTMLParser(HTML_FILE_CONTENT)
    data = html_parser.get_event_data()
    summary = html_parser.get_race_summary()
    event_title = data['event_name'].replace(' ', '_')

    webdriver = webdriver.Chrome()
    session_id_extractor = SessionIDExtractor(webdriver)
    boats_dict_extractor = BoatsDictExtractor(webdriver)
    race_path_list_extractor = RacePathListExtractor(webdriver)


    for date, races in data['races'].items():
        for race in races:
            print(f"Race Title: {race['title']}")
            print(f"Race Link: {race['race_link']}")
            print(f"Ranking Link: {race['ranking_link']}")
            print(f"Export ID: {race['export_id']}")
            print(f"Start Time: {race['start_time']}")
            try:
                print(f"Category: {race['category']}")
            except KeyError:
                print("Category: N/A")
            try:
                print(f"Order: {race['order']}")
            except KeyError:
                print("Order: N/A")
            print()

            session_id = session_id_extractor.get_id(race['export_id'], race['race_link'])
            print(f"Session ID: {session_id}")

            print()

            event_directory = os.path.join(directory, 'events', event_title)
            zip_downloader = ZipDownloader(event_directory, session_id, race['export_id'])
            zip_downloader.get_zip()

            race_data = {
                'title': race['title'],
                'race_link': race['race_link'],
                'ranking_link': race['ranking_link'],
                'export_id': race['export_id'],
                'start_time': race['start_time'],
                'category': race.get('category', ''),
                'order': race.get('order', ''),
                'session_id': session_id,
                'event_name': data['event_name'],
                'event_location': data['location'],
                'event_dates': data['dates'],
                'event_full_title': data['full_title']
            }
            with open(f"{event_directory}/race_data_{race['export_id']}.json", 'w') as f:
                json.dump(race_data, f, indent=2)

            boats_dict = boats_dict_extractor.get_boats_dict(race['export_id'], race['race_link'])
            with open(f"{event_directory}/boats_dict_{race['export_id']}.json", 'w') as f:
                json.dump(boats_dict, f, indent=2)

            race_path = race_path_list_extractor.get_race_path_list(race['export_id'], race['race_link'])
            with open(f"{event_directory}/race_path_{race['export_id']}.json", 'w') as f:
                json.dump(race_path, f, indent=2)


            
    zip_extractor = ZipExtractor(event_directory)
    zip_extractor.extract_all_zips()
    zip_extractor.remove_zip_files()

def generate_index():
    """Generate index.json file listing all events and races"""
    events_dir = 'events'
    index = []

    if not os.path.exists(events_dir):
        print(f"Error: {events_dir} directory not found")
        return

    # Iterate through event folders
    for event_folder in os.listdir(events_dir):
        event_path = os.path.join(events_dir, event_folder)

        if not os.path.isdir(event_path):
            continue

        event_data = {
            'name': event_folder.replace('_', ' ').title(),
            'folder': event_folder,
            'races': []
        }

        # Iterate through race folders
        for race_folder in os.listdir(event_path):
            race_path = os.path.join(event_path, race_folder)

            if not os.path.isdir(race_path) or not race_folder.startswith('race_'):
                continue

            # Check if combined_data.csv exists
            combined_file = os.path.join(race_path, 'combined_data.csv')

            # Extract race ID
            race_id = race_folder  # e.g., "race_12345"
            race_number = race_folder.split('_')[1] if '_' in race_folder else race_folder

            # Count data files
            data_files = [f for f in os.listdir(race_path) if f.isdigit()]
            num_files = len(data_files)

            # Check for boat names and race path files
            boats_file = os.path.join(race_path, f'boats_dict_{race_number}.json')
            race_path_file = os.path.join(race_path, f'race_path_{race_number}.json')
            race_data_file = os.path.join(race_path, f'race_data_{race_number}.json')

            has_boats = os.path.exists(boats_file)
            has_race_path = os.path.exists(race_path_file)

            # Load title and start_time from race_data file
            title = ''
            start_time = ''
            if os.path.exists(race_data_file):
                try:
                    with open(race_data_file, 'r') as f:
                        race_data = json.load(f)
                        title = race_data.get('title', '')
                        start_time = race_data.get('start_time', '')
                except (json.JSONDecodeError, KeyError):
                    pass

            race_info = {
                'name': f'Race {race_number} ({race_id})',
                'id': race_id,
                'title': title,
                'start_time': start_time,
                'num_files': num_files,
                'has_combined': os.path.exists(combined_file),
                'has_boats': has_boats,
                'has_race_path': has_race_path
            }

            event_data['races'].append(race_info)

        # Sort races by race number
        event_data['races'].sort(key=lambda x: x['name'])

        if event_data['races']:  # Only add events that have races
            index.append(event_data)

    # Sort events by name
    index.sort(key=lambda x: x['name'])

    # Save index.json
    output_file = os.path.join(events_dir, 'index.json')
    with open(output_file, 'w') as f:
        json.dump(index, f, indent=2)

    print(f"Generated {output_file}")
    print(f"Found {len(index)} events with {sum(len(e['races']) for e in index)} races total")

    # Print summary
    for event in index:
        print(f"\n{event['name']} ({event['folder']})")
        for race in event['races']:
            status = "✓" if race['has_combined'] else "✗"
            print(f"  {status} {race['name']} - {race['num_files']} files")

generate_index()