# Query Optimization Notes

## Instrumentation

- Added `read/utils/db_debug.py` with `query_debugger` and `log_query_stats`
  utilities. Views now log SQL counts and timings automatically in `DEBUG`
  mode (see decorators applied across `users/views.py`) so hotspots can be
  profiled without third-party tooling.

## Dashboards & APIs

- `reading_logs/helpers/data_helpers.get_dashboard_data` now caches results per
  group/date range and reuses the log dataset to derive both per-student and
  daily aggregates. This removes an extra aggregation query and avoids
  recomputing identical payloads for repeat requests.

- `users.views.api_admin_students` now uses `Prefetch` and annotations to
  gather classrooms, reading groups, parents, and latest log dates in bulk,
  reducing N+1 queries to a fixed set regardless of student count.

## Database Configuration

- Enabled `CONN_MAX_AGE = 60` in settings to reuse database connections,
  eliminating repeated connection handshakes during bursts of API activity.

These changes collectively shrink query counts on high-traffic pages, while the
new instrumentation makes it straightforward to monitor regressions during
future work.


