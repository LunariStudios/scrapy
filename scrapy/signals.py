"""
Scrapy signals

These signals are documented in docs/topics/signals.rst. Please don't add new
signals here without documenting them there.
"""

engine_started = object()
engine_stopped = object()
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
