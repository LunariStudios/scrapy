"""
Scrapy signals

These signals are documented in docs/topics/signals.rst. Please don't add new
signals here without documenting them there.
"""

engine_started = object()
engine_stopped = object()
engine_backout = object()
scheduler_empty = object()
spider_opened = object()
spider_idle = object()
spider_closed = object()
spider_error = object()
request_scheduled = object()
request_dropped = object()
request_reached_downloader = object()
request_left_downloader = object()
response_received = object()
response_downloaded = object()
headers_received = object()
bytes_received = object()
item_scraped = object()
item_dropped = object()
item_error = object()
feed_slot_closed = object()
feed_exporter_closed = object()

# Request lifecycle signals (for observability)
request_scraping_complete = object()  # After ALL processing for request (in enqueue_scrape finally)
item_processing_complete = object()   # After all items processed with statistics

# Middleware chain processing signals (for observability)
middleware_chain_complete = object()  # After all middlewares in a chain have been processed
middleware_method_complete = object()  # After each individual middleware method completes

# Rate limiting signals (429 Too Many Requests)
spider_rate_limited = object()          # 429 received, engine pausing
spider_rate_limited_resumed = object()  # Engine resumed after rate-limit pause
spider_rate_limited_shutdown = object() # Retry-After exceeds max wait, shutting down

# Engine performance telemetry signals (per-subsystem snapshots)
downloader_state = object()   # Downloader active/queued/transferring/concurrency snapshot
scraper_state = object()      # Scraper queue/active/itemproc/limits snapshot
scheduler_state = object()    # Scheduler pending + slot inprogress snapshot
