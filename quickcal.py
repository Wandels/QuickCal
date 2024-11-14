import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
import pytz
from google.auth.transport.requests import Request

# Load environment variables from .env
load_dotenv()

# Define scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Load file paths
CLIENT_SECRET_FILE = os.getenv('CLIENT_SECRET_FILE')
TOKEN_FILE = os.getenv('TOKEN_FILE')
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')

# Define CST timezone
CST = pytz.timezone('America/Chicago')

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

def format_datetime(dt):
    """Convert datetime object to a more readable format in CST."""
    dt_cst = dt.astimezone(CST)  # Convert to CST
    return dt_cst.strftime("%Y-%m-%d %I:%M %p")

def parse_datetime(dt_str, timezone):
    """Convert ISO datetime to a timezone-aware datetime object."""
    dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = timezone.localize(dt)  # Localize naive datetime to the calendar's timezone
    return dt.astimezone(CST)  # Convert to CST

def merge_intervals(intervals):
    """Merge overlapping intervals."""
    if not intervals:
        return []
    intervals.sort()
    merged = [intervals[0]]
    for current in intervals[1:]:
        last = merged[-1]
        if current[0] <= last[1]:  # Overlapping intervals
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            merged.append(current)
    return merged

def get_availability(days=5):
    """List the user's availability across all calendars and aggregate for overall free time."""
    creds = authenticate()
    service = build('calendar', 'v3', credentials=creds)
    
    now = datetime.datetime.now(datetime.timezone.utc)
    end_time = now + datetime.timedelta(days=days)
    availability = "Available times across all calendars:\n"

    busy_intervals = []

    # List all calendars and collect busy intervals
    calendar_list = service.calendarList().list().execute()
    for calendar in calendar_list.get('items', []):
        calendar_id = calendar['id']
        
        # Get the calendar's timezone
        calendar_timezone = pytz.timezone(calendar.get('timeZone', 'UTC'))

        events_result = service.events().list(
            calendarId=calendar_id, timeMin=now.isoformat(), timeMax=end_time.isoformat(),
            singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        if not events:
            availability += f"\nCalendar: {calendar.get('summary')}\nAll day available.\n"
        else:
            availability += f"\nCalendar: {calendar.get('summary')}\n"
            for event in events:
                start = parse_datetime(event['start'].get('dateTime', event['start'].get('date')), calendar_timezone)
                end = parse_datetime(event['end'].get('dateTime', event['end'].get('date')), calendar_timezone)
                busy_intervals.append((start, end))
                availability += f"Busy: {format_datetime(start)} - {format_datetime(end)}\n"

    # Merge all busy intervals
    merged_busy_intervals = merge_intervals(busy_intervals)

    # Calculate free times based on merged busy intervals
    free_times = []
    current = now.astimezone(CST)
    for start, end in merged_busy_intervals:
        if current < start:
            free_times.append((current, start))
        current = max(current, end)
    if current < end_time.astimezone(CST):
        free_times.append((current, end_time.astimezone(CST)))

    # Display overall availability
    availability += "\nOverall Available Times:\n"
    if not free_times:
        availability += "No available times.\n"
    else:
        for start, end in free_times:
            availability += f"Available: {format_datetime(start)} - {format_datetime(end)}\n"

    print(availability)

if __name__ == '__main__':
    get_availability()
