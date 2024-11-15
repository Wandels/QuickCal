import os
import datetime
import pytz
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Define scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Load file paths
CLIENT_SECRET_FILE = os.getenv('CLIENT_SECRET_FILE')
TOKEN_FILE = os.getenv('TOKEN_FILE')
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')

def authenticate():
    """Authenticate the user with OAuth token or service account credentials."""
    creds = None
    if CLIENT_SECRET_FILE and TOKEN_FILE:
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
    if not creds and SERVICE_ACCOUNT_FILE:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return creds

def format_datetime(dt_str):
    """Convert ISO datetime to CST for readability."""
    dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    utc_dt = dt.replace(tzinfo=datetime.timezone.utc)
    cst_dt = utc_dt.astimezone(pytz.timezone("America/Chicago"))  # Convert to CST
    return cst_dt.strftime("%Y-%m-%d %I:%M %p %Z")

def print_all_day_events():
    """Print details of all-day events across all calendars."""
    creds = authenticate()
    service = build('calendar', 'v3', credentials=creds)
    
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    end_of_day = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=5)).isoformat()
    print("All-Day Events Across All Calendars:\n")
    
    # List all calendars
    calendar_list = service.calendarList().list().execute()
    for calendar in calendar_list.get('items', []):
        calendar_id = calendar['id']
        print(f"Calendar: {calendar.get('summary')}")
        
        # Fetch events for each calendar
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=now, timeMax=end_of_day,
            singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        # Print all-day events
        for event in events:
            if 'date' in event['start']:  # Identifies all-day events
                start = event['start'].get('date')
                end = event['end'].get('date')
                summary = event.get('summary', 'No title')
                print(f"Event: {summary}")
                print(f"Start: {start}")
                print(f"End: {end}\n")

def get_availability(days=5):
    """List the user's availability across all calendars for the specified number of days, excluding all-day events."""
    creds = authenticate()
    service = build('calendar', 'v3', credentials=creds)
    
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    end_of_day = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).isoformat()
    availability = "Available times across all calendars:\n"
    
    # List all calendars
    calendar_list = service.calendarList().list().execute()
    for calendar in calendar_list.get('items', []):
        calendar_id = calendar['id']
        availability += f"\nCalendar: {calendar.get('summary')}\n"
        
        # Fetch events for each calendar
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=now, timeMax=end_of_day,
            singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        # Extract available time slots for each calendar, excluding all-day events
        if not events:
            availability += "All day available.\n"
        else:
            last_end = now
            for event in events:
                # Skip all-day events
                if 'date' in event['start']:
                    continue
                
                # Process regular events
                start = event['start'].get('dateTime')
                end = event['end'].get('dateTime')
                if start > last_end:
                    availability += f"Available: {format_datetime(last_end)} - {format_datetime(start)}\n"
                last_end = end
            availability += f"Available: {format_datetime(last_end)} - End of day\n"

    # Output formatted availability
    print(availability)

if __name__ == '__main__':
    print_all_day_events()
    get_availability()
