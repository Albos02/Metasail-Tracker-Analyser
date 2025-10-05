import os
import requests
from selenium import webdriver
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json
import zipfile


class GetHTMLFile:
    def __init__(self, directory):
        self.directory = directory
        self.html_files = self.list_html_files(directory)

    def list_html_files(self, directory):
        html_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".html"):
                    html_files.append(os.path.join(root, file))
        return html_files

    def choose_html_file(self):
        if not self.html_files:
            print("No html files found in directory.")
            return None
        print("Choose an html file:")
        for i, file in enumerate(self.html_files):
            print(f"{i+1}. {file}")
        choice = int(input("Enter the number of the file: ")) - 1
        if choice < 0 or choice >= len(self.html_files):
            print("Invalid choice.")
            return None
        return self.html_files[choice]
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
            summary[date] = {
                'total_races': len(races),
                'categories': list(set(race['category'] for race in races)),
                'race_titles': [race['title'] for race in races]
            }
        return summary

class SessionIDExtractor:
    def __init__(self):
        self.driver = webdriver.Chrome()
        # self.driver.get("https://app.metasail.it/live/776/")
    def get_id(self, url):
        self.driver.get(url)
        self.current_url = self.driver.current_url
        self.session_id = self.current_url.split("S(")[1].split(")")[0]
        return self.session_id

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
        for zip_file in self.zip_file_list:
            zip_file_path = os.path.join(self.event_path, zip_file.replace('.zip', ''))
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(zip_file_path)
            
            race_id = zip_file.split('race_')[1].split('.zip')[0]
            race_data_file = 'race_data_' + race_id + '.json'
            race_data_file_path = os.path.join(zip_file_path, race_data_file)
            os.rename(os.path.join(self.event_path, race_data_file), race_data_file_path)

    def remove_zip_files(self):
        for zip_file in self.zip_file_list:
            print(f"Removing {zip_file}")
            os.remove(os.path.join(self.event_path, zip_file))

if __name__ == "__main__":
    directory = os.getcwd()
    html_finder = GetHTMLFile(directory)
    HTML_FILE = html_finder.choose_html_file()

    if HTML_FILE:
        print(f"Selected file: {HTML_FILE}")

        with open(HTML_FILE, "r") as f:
            HTML_FILE_CONTENT = f.read()
    
    html_parser = HTMLParser(HTML_FILE_CONTENT)
    data = html_parser.get_event_data()
    summary = html_parser.get_race_summary()
    event_title = data['event_name'].replace(' ', '_')

    selenium_session_id_extractor = SessionIDExtractor()
    for date, races in data['races'].items():
        for race in races:
            print(f"Race Title: {race['title']}")
            print(f"Race Link: {race['race_link']}")
            print(f"Ranking Link: {race['ranking_link']}")
            print(f"Export ID: {race['export_id']}")
            print(f"Start Time: {race['start_time']}")
            print(f"Category: {race['category']}")
            print(f"Order: {race['order']}")
            print()

            session_id = selenium_session_id_extractor.get_id(race['race_link'])
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
                'category': race['category'],
                'order': race['order']
            }
            with open(f"{event_directory}/race_data_{race['export_id']}.json", 'w') as f:
                json.dump(race_data, f, indent=2)
            
    zip_extractor = ZipExtractor(event_directory)
    zip_extractor.extract_all_zips()
    zip_extractor.remove_zip_files()