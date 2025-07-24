# in backend/volunteers/utils.py

import fitparse
from datetime import timezone

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
        
        # --- Apply Specific Conversions Based on .fit Specification ---

        if 'timestamp' in point and point['timestamp']:
            point['timestamp'] = point['timestamp'].replace(tzinfo=timezone.utc).isoformat()
        
        if 'position_lat' in point and point.get('position_lat') is not None:
            point['position_lat'] = point['position_lat'] * (180.0 / 2**31)
        if 'position_long' in point and point.get('position_long') is not None:
            point['position_long'] = point['position_long'] * (180.0 / 2**31)
        
        # --- THIS SECTION IS CORRECTED ---
        # The .get_values() method already returns speed in m/s. No division needed.
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
        summary_data['avg_heart_rate'] = round(sum(heart_rates) / len(heart_rates))
        summary_data['max_heart_rate'] = max(heart_rates)

    return summary_data, time_series_data