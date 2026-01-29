import datetime
import requests
from tenacity.wait import wait_base

class wait_on_retry_after(wait_base):
    """
    Custom wait class to wait based on the Retry-After header in the response
    """
    def __init__(self, default_wait=10, max_wait=60):
        self.default_wait = default_wait
        self.max_wait = max_wait

    def __call__(self, retry_state):
        # check exception from the previous attempt
        if not retry_state.outcome:
            return self.default_wait

        exception = retry_state.outcome.exception()

        # check if the exception is an HTTPError and has a response
        if isinstance(exception, requests.HTTPError) and hasattr(exception, "response"):
            response = exception.response
            # get the Retry-After header
            retry_after = response.headers.get("Retry-After")

            if retry_after:
                try:
                    # if specified as seconds
                    return min(max(int(retry_after), 0), self.max_wait)
                except ValueError:
                    try:
                        # if specified as a date
                        dt = datetime.datetime.strptime(retry_after, "%a, %d %b %Y %H:%M:%S GMT")
                        dt = dt.replace(tzinfo=datetime.timezone.utc)
                        wait_time = (dt - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
                        return min(max(wait_time, 0), self.max_wait)
                    except Exception:
                        return self.default_wait

        return self.default_wait
