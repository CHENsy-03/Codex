"""Network Health Check Zone - CLI
Usage:
    python -m monitor              # all devices
    python -m monitor HW2024001    # specific device
"""
import sys
from monitor.reporter import print_check_zone, get_recommendations
from monitor.metrics_collector import MetricsCollector

if len(sys.argv) > 1:
    did = sys.argv[1]
    print_check_zone(did)
    m = MetricsCollector.get_instance().get_device_metrics(did)
    if m:
        print()
        for r in get_recommendations(m):
            print("  " + r)
else:
    print_check_zone()
    all_m = MetricsCollector.get_instance().get_all_metrics()
    for did in all_m:
        recs = get_recommendations(all_m[did])
        for r in recs:
            print("  [" + did + "] " + r)
