# Gunicorn configuration file pro WebMajak Django app

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = 2  # Pro 1GB RAM doporučuji 2 workery
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/home/webmajak/webapp/logs/gunicorn_access.log"
errorlog = "/home/webmajak/webapp/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'gunicorn_webmajak'

# Daemon mode
daemon = False
# Bez pidfile pod systemd (sdílený conf na stagingu dřív ukazoval na webapp/gunicorn.pid → konflikt s produkcí).

# User and group
user = "webmajak"
group = "webmajak"

# Preload app for better memory usage
preload_app = True

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# SSL (pro budoucí HTTPS)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile" 