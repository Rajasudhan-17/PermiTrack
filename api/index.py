import sys
import os
import traceback

# Add root directory to python path to ensure import resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from leave_app import create_app
    app = create_app()
except Exception as e:
    tb = traceback.format_exc()
    print(f"Flask boot failed:\n{tb}", file=sys.stderr)
    
    # Fallback WSGI app to display the actual traceback in the browser for easy debugging
    def app(environ, start_response):
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain; charset=utf-8')])
        return [f"Flask Boot Failure Traceback:\n\n{tb}".encode('utf-8')]
