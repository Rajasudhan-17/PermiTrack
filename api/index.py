import sys
import os
import traceback

# Add root directory to python path to ensure import resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class WSGIWrapper:
    def __init__(self):
        self._app = None
        self._error = None

    def __call__(self, environ, start_response):
        # Lazy load the Flask application on the first request
        if not self._app and not self._error:
            try:
                from leave_app import create_app
                self._app = create_app()
            except Exception as e:
                self._error = traceback.format_exc()
                print(f"Flask boot failed:\n{self._error}", file=sys.stderr)
        
        # If the Flask application failed to boot, return the traceback directly
        if self._error:
            start_response('500 Internal Server Error', [('Content-Type', 'text/plain; charset=utf-8')])
            return [f"Flask Boot Failure Traceback:\n\n{self._error}".encode('utf-8')]
            
        # Otherwise, delegate the request to Flask
        return self._app(environ, start_response)

# Define the app at the top level of the module so Vercel's static AST parser finds it
app = WSGIWrapper()
