import logging
import azure.functions as func

from run_weekly_pipeline import run_weekly_pipeline

app = func.FunctionApp()

@app.schedule(
    schedule="0 0 9 * * FRI",  # Every Friday at 9:00 AM UTC (10:00 AM CET, 11:00 AM CEST)
    arg_name="timer",
    run_on_startup=False,
    use_monitor=False
)
def weekly_ai_digest(timer: func.TimerRequest) -> None:
    """
    Azure Function triggered weekly to:
    1. Fetch and analyze new AI articles
    2. Generate weekly digest report
    3. Send email newsletter
    
    Schedule: Every Friday at 9:00 AM UTC
    """
    if timer.past_due:
        logging.info('The timer is past due!')

    logging.info('Weekly AI Digest pipeline starting...')
    
    try:
        run_weekly_pipeline()
        logging.info('Weekly AI Digest pipeline completed successfully.')
    except Exception as e:
        logging.error(f'Pipeline failed with error: {str(e)}')
        raise
