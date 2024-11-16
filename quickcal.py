import os
import datetime
import pytz
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dateutil.parser import isoparse

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

# def format_datetime(dt_str):
#     """Convert ISO datetime to CST for readability."""
#     dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
#     utc_dt = dt.replace(tzinfo=datetime.timezone.utc)
#     cst_dt = utc_dt.astimezone(pytz.timezone("America/Chicago"))  # Convert to CST
#     return cst_dt.strftime("%Y-%m-%d %I:%M %p %Z")

def format_datetime(dt_str):
    """Convert ISO datetime to CST for readability."""
    dt = isoparse(dt_str)
    cst_dt = dt.astimezone(pytz.timezone("America/Chicago"))
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

# def get_availability(days=5):
#     """List the user's availability across all calendars for the specified number of days, excluding all-day events."""
#     creds = authenticate()
#     service = build('calendar', 'v3', credentials=creds)
    
#     now = datetime.datetime.now(datetime.timezone.utc).isoformat()
#     end_of_day = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).isoformat()
#     #print:
#     availability = "Available times across all calendars:\n"
#     #return:
#     calendar_availabilities = {}
    
#     # List all calendars
#     calendar_list = service.calendarList().list().execute()
#     for calendar in calendar_list.get('items', []):
#         calendar_id = calendar['id']
#         #return:
#         calendar_name = calendar.get('summary')
#         calendar_availabilities[calendar_name] = []
#         #print:
#         availability += f"\nCalendar: {calendar.get('summary')}\n"
        
#         # Fetch events for each calendar
#         events_result = service.events().list(
#             calendarId=calendar_id, timeMin=now, timeMax=end_of_day,
#             singleEvents=True, orderBy='startTime'
#         ).execute()
#         events = events_result.get('items', [])
        
#         # Extract available time slots for each calendar, excluding all-day events
#         if not events:
#             availability += "All day available.\n"
#         else:
#             last_end = now
#             for event in events:
#                 # Skip all-day events
#                 if 'date' in event['start']:
#                     continue
                
#                 # Process regular events
#                 start = event['start'].get('dateTime')
#                 end = event['end'].get('dateTime')
#                 if start > last_end:
#                     availability += f"Available: {format_datetime(last_end)} - {format_datetime(start)}\n"
#                 last_end = end
#             availability += f"Available: {format_datetime(last_end)} - End of day\n"

#     # Output formatted availability
#     print(availability)
def get_calendar_availability(days=5):
    creds = authenticate()
    service = build('calendar', 'v3', credentials=creds)
    
    now = datetime.datetime.now(datetime.timezone.utc)
    end_of_day = now + datetime.timedelta(days=days)
    calendar_availabilities = {}
    
    # List all calendars
    calendar_list = service.calendarList().list().execute()
    for calendar in calendar_list.get('items', []):
        calendar_id = calendar['id']
        calendar_name = calendar.get('summary')
        calendar_availabilities[calendar_name] = []
        
        # Fetch events for each calendar
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=now.isoformat(), timeMax=end_of_day.isoformat(),
            singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        if not events:
            # No events -> full availability
            calendar_availabilities[calendar_name].append({
                'start': now.isoformat(),
                'end': end_of_day.isoformat()
            })
        else:
            # Process events to extract availability
            last_end = now
            for event in events:
                if 'date' in event['start']:  # Skip all-day events
                    continue
                
                start_str = event['start'].get('dateTime')
                end_str = event['end'].get('dateTime')
                start = isoparse(start_str)
                end = isoparse(end_str)
                
                # Ensure valid intervals
                if start > last_end:
                    calendar_availabilities[calendar_name].append({
                        'start': last_end.isoformat(),
                        'end': start.isoformat()
                    })
                last_end = end
            
            # Add availability from the last event to the end of the day
            if last_end < end_of_day:
                calendar_availabilities[calendar_name].append({
                    'start': last_end.isoformat(),
                    'end': end_of_day.isoformat()
                })
        
        # Ensure all intervals are valid (start < end)
        calendar_availabilities[calendar_name] = [
            interval for interval in calendar_availabilities[calendar_name]
            if isoparse(interval['start']) < isoparse(interval['end'])
        ]

    return calendar_availabilities

def aggregate_availability_intersection(calendar_data):
    def intersect_ranges(range1, range2):
        """Helper to find the intersection of two ranges."""
        start1 = isoparse(range1['start'])
        end1 = isoparse(range1['end'])
        start2 = isoparse(range2['start'])
        end2 = isoparse(range2['end'])
        start = max(start1, start2)
        end = min(end1, end2)
        if start < end:
            return {'start': start.isoformat(), 'end': end.isoformat()}
        return None

    # Extract availability for each calendar
    calendars = list(calendar_data.values())
    if not calendars:
        return []

    # Start with the first calendar's availability
    intersection = calendars[0]
    
    # Intersect with all subsequent calendars
    for other_calendar in calendars[1:]:
        new_intersection = []
        for range1 in intersection:
            for range2 in other_calendar:
                intersected_range = intersect_ranges(range1, range2)
                if intersected_range:
                    new_intersection.append(intersected_range)
        intersection = new_intersection
    
    return intersection


# if __name__ == '__main__':
#     print_all_day_events()
#     get_availability()
if __name__ == '__main__':
    # Fetch availability for all calendars
    calendar_data = get_calendar_availability()

    # Aggregate intersection of all calendars
    combined_availability = aggregate_availability_intersection(calendar_data)

    # Print the combined availability
    print("Combined Availability:")
    for slot in combined_availability:
        print(f"Start: {format_datetime(slot['start'])}, End: {format_datetime(slot['end'])}")
