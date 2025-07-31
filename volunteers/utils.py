# in backend/volunteers/utils.py

import fitparse
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import timezone
import os
import numpy as np

# --- NEW HELPER FUNCTION ---
# This is a safe addition. It prevents server crashes if calculations result in
# 'Not a Number' (NaN), which is not a valid JSON value.
def clean_summary_data(summary_data):
    """Converts any numpy NaN or Inf values in a dictionary to None."""
    if not summary_data:
        return {}
    cleaned_data = {}
    for key, value in summary_data.items():
        # Check if the value is a float and is NaN or Infinity
        if isinstance(value, (float, np.floating)) and (np.isnan(value) or np.isinf(value)):
            cleaned_data[key] = None
        else:
            cleaned_data[key] = value
    return cleaned_data

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

    parser = {
        '.fit': analyze_fit_file,
        '.tcx': analyze_tcx_file,
        '.csv': analyze_csv_file,
    }.get(extension)

    if parser:
        summary_data, time_series_data = parser(file_path)
        # --- MODIFIED --- This safely cleans the data before it's saved.
        return clean_summary_data(summary_data), time_series_data
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

    for trackpoint in root.findall('.//tcx:Trackpoint', namespaces):
        point = {}
        time_el = trackpoint.find('tcx:Time', namespaces)
        hr_el = trackpoint.find('.//tcx:HeartRateBpm/tcx:Value', namespaces)
        
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

        tpx = trackpoint.find('.//ns3:TPX', namespaces)
        if tpx is not None:
            speed_el = tpx.find('ns3:Speed', namespaces)
            cad_el = tpx.find('ns3:RunCadence', namespaces)
            point['speed'] = float(speed_el.text) if speed_el is not None else None
            point['cadence'] = int(cad_el.text) * 2 if cad_el is not None else None

        # --- MODIFIED --- This is the only change needed for the labeling feature.
        point['Anomaly'] = 0

        if point.get('heart_rate') is not None:
            heart_rates.append(point['heart_rate'])
        
        if point.get('timestamp'):
            time_series_data.append(point)

    lap_element = root.find('.//tcx:Lap', namespaces)
    if lap_element is not None:
        total_dist = lap_element.find('tcx:DistanceMeters', namespaces)
        total_time = lap_element.find('tcx:TotalTimeSeconds', namespaces)
        
        if total_dist is not None:
            summary_data['total_distance_km'] = round(float(total_dist.text) / 1000, 2)
        if total_time is not None:
            summary_data['total_duration_secs'] = round(float(total_time.text), 2)

    if heart_rates:
        if 'avg_heart_rate' not in summary_data:
            summary_data['avg_heart_rate'] = round(sum(heart_rates) / len(heart_rates)) if heart_rates else 0
        if 'max_heart_rate' not in summary_data:
            summary_data['max_heart_rate'] = max(heart_rates) if heart_rates else 0

    return summary_data, time_series_data

# ==============================================================================
# .CSV FILE PARSER (FINAL ENHANCED VERSION)
# ==============================================================================

def analyze_csv_file(file_path):
    """
    Parses complex CSV files by cleaning, transforming, and filling data.
    """
    try:
        df = pd.read_csv(file_path, skip_blank_lines=True, skipinitialspace=True)
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}")

    df.columns = df.columns.str.strip()
    
    column_map = {
        'Timestamp': 'timestamp', 'Time': 'timestamp', 'Heart Rate': 'heart_rate',
        'HeartRate': 'heart_rate', 'hr': 'heart_rate', 'Speed': 'speed',
        'speed (m/s)': 'speed', 'Cadence': 'cadence', 'Run Cadence': 'cadence',
        'RunCadence': 'cadence', 'Altitude': 'altitude', 'altitude (m)': 'altitude',
        'Distance': 'distance', 'distance (m)': 'distance', 'Latitude': 'position_lat',
        'Longitude': 'position_long', 'Power': 'power', 'Watts': 'power',
    }
    df.rename(columns=lambda c: column_map.get(c, c), inplace=True)
    
    numeric_cols = [
        'distance', 'enhanced_altitude', 'enhanced_speed', 'gps_accuracy',
        'position_lat', 'position_long', 'speed', 'heart_rate', 'power'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    cols_to_ffill = ['distance', 'heart_rate', 'position_lat', 'position_long', 'gps_accuracy']
    for col in cols_to_ffill:
        if col in df.columns:
            df[col] = df[col].ffill()

    if 'position_lat' in df.columns:
        df['position_lat'] = df['position_lat'] * (180.0 / 2**31)
    if 'position_long' in df.columns:
        df['position_long'] = df['position_long'] * (180.0 / 2**31)
    if 'enhanced_altitude' in df.columns:
        df['altitude'] = (df['enhanced_altitude'] / 5.0) - 500.0
    if 'enhanced_speed' in df.columns:
        df['speed'] = df['enhanced_speed']

    if 'timestamp' in df.columns:
        timestamps = pd.to_datetime(df['timestamp'], errors='coerce')
        df.dropna(subset=['timestamp'], inplace=True)
        if not timestamps.dropna().empty:
            if timestamps.dt.tz is None: timestamps = timestamps.dt.tz_localize('UTC')
            else: timestamps = timestamps.dt.tz_convert('UTC')
            df['timestamp'] = timestamps.dt.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
            start_time, end_time = timestamps.dropna().iloc[0], timestamps.dropna().iloc[-1]
            summary_data = {'total_duration_secs': round((end_time - start_time).total_seconds(), 2)}
        else: summary_data = {}
    else: raise ValueError("CSV file must contain a 'timestamp' or 'Time' column.")

    if 'heart_rate' in df.columns and not df['heart_rate'].dropna().empty:
        summary_data['avg_heart_rate'] = df['heart_rate'].mean()
        summary_data['max_heart_rate'] = df['heart_rate'].max()
    
    if 'distance' in df.columns and not df['distance'].dropna().empty:
        summary_data['total_distance_km'] = df['distance'].dropna().iloc[-1] / 1000

    # --- MODIFIED --- This is the only change needed for the labeling feature.
    df['Anomaly'] = 0

    df = df.replace({np.nan: None})
    time_series_data = df.to_dict('records')

    return summary_data, time_series_data


# ==============================================================================
# .FIT FILE PARSER
# ==============================================================================

def analyze_fit_file(file_path):
    """
    Parses a .fit file and extracts summary and ALL time-series data.
    """
    try:
        fitfile = fitparse.FitFile(file_path)
    except fitparse.FitParseError:
        return None, None

    time_series_data = []
    summary_data = {}
    heart_rates = []

    for record in fitfile.get_messages('record'):
        point = record.get_values()
        
        # --- MODIFIED --- This is the only change needed for the labeling feature.
        point['Anomaly'] = 0
        
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

    for session_msg in fitfile.get_messages('session'):
        summary_data.update(session_msg.get_values())
    
    if 'total_distance' in summary_data:
        summary_data['total_distance_km'] = summary_data.get('total_distance', 0) / 1000
    if 'total_elapsed_time' in summary_data:
        summary_data['total_duration_secs'] = summary_data.get('total_elapsed_time', 0)

    if heart_rates:
        if 'avg_heart_rate' not in summary_data:
            summary_data['avg_heart_rate'] = sum(heart_rates) / len(heart_rates) if heart_rates else 0
        if 'max_heart_rate' not in summary_data:
            summary_data['max_heart_rate'] = max(heart_rates) if heart_rates else 0

    return summary_data, time_series_data