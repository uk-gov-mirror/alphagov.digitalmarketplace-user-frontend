from flask import current_app
from dmutils.email.helpers import hash_string


def log_email_error(exception, email_type, error_code, email_address):
    """
    Log errors in a separate module so we can patch `current_app.logger` in tests
    and assert the calls, without affecting the test client.
    """
    current_app.logger.error(
        "{code}: {email_type} email for email_hash {email_hash} failed to send. "
        "Error: {error}",
        extra={
            'email_hash': hash_string(email_address),
            'error': str(exception),
            'code': '{}'.format(error_code),
            'email_type': email_type
        }
    )
