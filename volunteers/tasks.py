from celery import shared_task
from .models import RunningSession
from .utils import analyze_fit_file
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

@shared_task
def process_session_file(session_id):
    """
    Celery task to process an uploaded session file in the background.
    """
    logger.info(f"Starting to process session file for Session ID: {session_id}")
    
    try:
        session = RunningSession.objects.get(id=session_id)
    except RunningSession.DoesNotExist:
        logger.error(f"Session with ID {session_id} does not exist.")
        return

    try:
        # Get the file path from the model's FileField
        file_path = session.session_file.path
        
        # Analyze the file using our helper function
        summary_data, timeseries_data = analyze_fit_file(file_path)

        if summary_data is None and timeseries_data is None:
            raise ValueError("Failed to parse .fit file, it might be corrupt.")

        # Update the session model instance with the results
        session.total_distance_km = summary_data.get('total_distance_km')
        session.total_duration_secs = summary_data.get('total_duration_secs')
        session.avg_heart_rate = summary_data.get('avg_heart_rate')
        session.max_heart_rate = summary_data.get('max_heart_rate')
        session.timeseries_data = timeseries_data
        session.status = RunningSession.STATUS_COMPLETED
        session.processing_error = None # Clear any previous errors
        session.save()
        
        logger.info(f"Successfully processed session file for Session ID: {session_id}")

    except Exception as e:
        logger.error(f"Error processing session ID {session_id}: {e}")
        # If any error occurs during processing, mark the session as 'failed'
        session.status = RunningSession.STATUS_FAILED
        # --- THIS IS THE ADDED LINE ---
        session.processing_error = str(e) # Save the error message to the database
        session.save()