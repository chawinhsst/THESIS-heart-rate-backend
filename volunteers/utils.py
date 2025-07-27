# in backend/volunteers/utils.py

import fitparse
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import timezone
import os

# ==============================================================================
# MAIN DISPATCHER FUNCTION
# ==============================================================================

def analyze_session_file(file_path):
    """
    Analyzes a session file by detecting its extension (.fit, .tcx, .csv)
    and calling the appropriate parser.
    """
    _, extension = os.path.splitext(file_path)
    extension = extension.lower()

    if extension == '.fit':
        return analyze_fit_file(file_path)
    elif extension == '.tcx':
        return analyze_tcx_file(file_path)
    elif extension == '.csv':
        return analyze_csv_file(file_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")

# ==============================================================================
# .TCX FILE PARSER
# ==============================================================================

def analyze_tcx_file(file_path):
    """
    Parses a .tcx file to extract summary and time-series data.
    """
    namespaces = {
        'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
        'ns3': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
    }
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError:
        return None, None

    time_series_data = []
    summary_data = {}
    heart_rates = []

    # Extract detailed trackpoint data
    for trackpoint in root.findall('.//tcx:Trackpoint', namespaces):
        point = {}
        time_el = trackpoint.find('tcx:Time', namespaces)
        hr_el = trackpoint.find('.//tcx:HeartRateBpm/tcx:Value', namespaces)
        
        # Extract common fields
        point['timestamp'] = time_el.text if time_el is not None else None
        point['heart_rate'] = int(hr_el.text) if hr_el is not None else None
        
        lat_el = trackpoint.find('.//tcx:LatitudeDegrees', namespaces)
        lon_el = trackpoint.find('.//tcx:LongitudeDegrees', namespaces)
        alt_el = trackpoint.find('tcx:AltitudeMeters', namespaces)
        dist_el = trackpoint.find('tcx:DistanceMeters', namespaces)

        point['position_lat'] = float(lat_el.text) if lat_el is not None else None
        point['position_long'] = float(lon_el.text) if lon_el is not None else None
        point['altitude'] = float(alt_el.text) if alt_el is not None else None
        point['distance'] = float(dist_el.text) if dist_el is not None else None

        # Extract extension data (Speed, Cadence)
        tpx = trackpoint.find('.//ns3:TPX', namespaces)
        if tpx is not None:
            speed_el = tpx.find('ns3:Speed', namespaces)
            cad_el = tpx.find('ns3:RunCadence', namespaces)
            point['speed'] = float(speed_el.text) if speed_el is not None else None
            point['cadence'] = int(cad_el.text) * 2 if cad_el is not None else None # Cadence is often steps/min, so multiply by 2 for rpm

        if point.get('heart_rate') is not None:
            heart_rates.append(point['heart_rate'])
        
        if point.get('timestamp'):
            time_series_data.append(point)

    # Extract summary data from the 'Lap' element
    lap_element = root.find('.//tcx:Lap', namespaces)
    if lap_element is not None:
        total_dist = lap_element.find('tcx:DistanceMeters', namespaces)
        total_time = lap_element.find('tcx:TotalTimeSeconds', namespaces)
        
        if total_dist is not None:
            summary_data['total_distance_km'] = round(float(total_dist.text) / 1000, 2)
        if total_time is not None:
            summary_data['total_duration_secs'] = round(float(total_time.text), 2)

    # Calculate summary stats from timeseries if not in lap data
    if heart_rates:
        if 'avg_heart_rate' not in summary_data:
            summary_data['avg_heart_rate'] = round(sum(heart_rates) / len(heart_rates))
        if 'max_heart_rate' not in summary_data:
            summary_data['max_heart_rate'] = max(heart_rates)

    return summary_data, time_series_data

# ==============================================================================
# .CSV FILE PARSER
# ==============================================================================

def analyze_csv_file(file_path):
    """
    Parses a .csv file to extract summary and time-series data.
    Assumes common column names from devices like Garmin/Strava exports.
    """
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}")

    # --- Standardize Column Names ---
    column_map = {
        'Timestamp': 'timestamp',
        'Time': 'timestamp',
        'Heart Rate': 'heart_rate',
        'HeartRate': 'heart_rate',
        'hr': 'heart_rate',
        'Speed': 'speed',
        'speed (m/s)': 'speed',
        'Cadence': 'cadence',
        'Run Cadence': 'cadence',
        'Altitude': 'altitude',
        'altitude (m)': 'altitude',
        'Distance': 'distance',
        'distance (m)': 'distance',
        'Latitude': 'position_lat',
        'Longitude': 'position_long',
        'Power': 'power',
    }
    df.rename(columns=lambda c: column_map.get(c, c.strip()), inplace=True)
    
    summary_data = {}
    
    if 'heart_rate' not in df.columns:
        raise ValueError("CSV file must contain a 'Heart Rate' column.")

    # --- CORRECTED TIMESTAMP HANDLING ---
    if 'timestamp' in df.columns:
        # Convert column to datetime objects. pandas automatically handles the 'Z' for UTC.
        timestamps = pd.to_datetime(df['timestamp'])

        # Check if the parsed datetimes are "naive" (have no timezone info).
        if timestamps.dt.tz is None:
            # If naive, assume UTC and apply the timezone.
            timestamps = timestamps.dt.tz_localize('UTC')
        else:
            # If already timezone-aware, ensure they are converted to UTC.
            timestamps = timestamps.dt.tz_convert('UTC')

        # Now, format to the ISO string standard for the database.
        df['timestamp'] = timestamps.dt.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

        # Calculate duration from the clean timestamps.
        start_time = timestamps.iloc[0]
        end_time = timestamps.iloc[-1]
        summary_data['total_duration_secs'] = round((end_time - start_time).total_seconds(), 2)

    # Calculate Summary Statistics
    summary_data['avg_heart_rate'] = round(df['heart_rate'].mean())
    summary_data['max_heart_rate'] = int(df['heart_rate'].max())
    
    if 'distance' in df.columns:
        # Use the last valid distance value in case of trailing empty rows.
        last_valid_distance = df['distance'].dropna().iloc[-1]
        summary_data['total_distance_km'] = round(last_valid_distance / 1000, 2)
    
    # Convert DataFrame to a list of dictionaries for timeseries data
    df.replace({pd.NA: None, pd.NaT: None}, inplace=True)
    time_series_data = df.to_dict('records')

    return summary_data, time_series_data


# ==============================================================================
# .FIT FILE PARSER (Your original code, slightly adjusted for consistency)
# ==============================================================================

def analyze_fit_file(file_path):
    """
    Parses a .fit file and extracts summary and ALL time-series data,
    applying the correct conversions for scale and offset.
    """
    try:
        fitfile = fitparse.FitFile(file_path)
    except fitparse.FitParseError:
        # Handle cases where the file is corrupt or not a valid .fit file
        return None, None

    time_series_data = []
    summary_data = {}
    heart_rates = []

    for record in fitfile.get_messages('record'):
        point = record.get_values()
        
        if 'timestamp' in point and point['timestamp']:
            point['timestamp'] = point['timestamp'].replace(tzinfo=timezone.utc).isoformat()
        
        if 'position_lat' in point and point.get('position_lat') is not None:
            point['position_lat'] = point['position_lat'] * (180.0 / 2**31)
        if 'position_long' in point and point.get('position_long') is not None:
            point['position_long'] = point['position_long'] * (180.0 / 2**31)
        
        if 'enhanced_speed' in point and point.get('enhanced_speed') is not None:
            point['speed'] = point['enhanced_speed']
        elif 'speed' in point and point.get('speed') is not None:
            point['speed'] = point['speed']

        if 'enhanced_altitude' in point and point.get('enhanced_altitude') is not None:
            point['altitude'] = (point['enhanced_altitude'] / 5.0) - 500.0
        elif 'altitude' in point and point.get('altitude') is not None:
            point['altitude'] = (point['altitude'] / 5.0) - 500.0

        if 'cadence' in point and point.get('cadence') is not None:
            if 'fractional_cadence' in point and point.get('fractional_cadence') is not None:
                point['cadence'] = point['cadence'] + (point['fractional_cadence'] / 128.0)

        if 'respiration_rate' in point and point.get('respiration_rate') is not None:
            point['respiration_rate'] = point['respiration_rate'] / 100.0

        if 'heart_rate' in point and point.get('heart_rate') is not None:
            heart_rates.append(point['heart_rate'])

        if point.get('timestamp'):
            time_series_data.append(point)

    # Process summary data from the 'session' message
    for session_msg in fitfile.get_messages('session'):
        summary_data.update(session_msg.get_values())
    
    if 'total_distance' in summary_data:
        summary_data['total_distance_km'] = round(summary_data.get('total_distance', 0) / 1000, 2)
    if 'total_elapsed_time' in summary_data:
        summary_data['total_duration_secs'] = round(summary_data.get('total_elapsed_time', 0), 2)

    if heart_rates:
        if 'avg_heart_rate' not in summary_data:
            summary_data['avg_heart_rate'] = round(sum(heart_rates) / len(heart_rates))
        if 'max_heart_rate' not in summary_data:
            summary_data['max_heart_rate'] = max(heart_rates)

    return summary_data, time_series_data