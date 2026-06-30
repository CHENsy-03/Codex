
"""Network Health Check Zone — formatted terminal report

Usage:
    from monitor.reporter import print_check_zone
    print_check_zone()           # all devices
    print_check_zone("HW2024001")  # one device
    
    or via CLI:
    python -m monitor.reporter
"""

import time
from monitor.metrics_collector import MetricsCollector


def _bar(value, max_val=10, width=20):
    """Render a horizontal bar"""
    filled = int((value / max_val) * width) if max_val > 0 else 0
    filled = min(filled, width)
    bar = "#" * filled + "." * (width - filled)
    return bar


def _fmt_time(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _fmt_duration(sec):
    if sec < 60:
        return f"{sec}s"
    elif sec < 3600:
        return f"{sec//60}m {sec%60}s"
    else:
        return f"{sec//3600}h {(sec%3600)//60}m"


def generate_check_zone(device_id: str = None) -> str:
    """Generate the formatted Check Zone report string"""
    collector = MetricsCollector.get_instance()

    if device_id:
        metrics_list = [collector.get_device_metrics(device_id)]
    else:
        all_metrics = collector.get_all_metrics()
        metrics_list = list(all_metrics.values())

    if not metrics_list:
        return "+====================================+\n" \
               "|     Network Health Check Zone       |\n" \
               "+====================================+\n" \
               "|  No data collected yet.             |\n" \
               "|  Start the bridge and send survey   |\n" \
               "|  data to populate metrics.          |\n" \
               "+====================================+"

    lines = []
    lines.append("+======================================================+")
    lines.append("|         Network Health Check Zone                    |")
    lines.append("+======================================================+")

    for m in metrics_list:
        if not m:
            continue

        lines.append(f"| Device: {m['device_id']:<44}|")
        lines.append(f"| Since:  {_fmt_time(m['start_time']):<20}"
                     f"  Duration: {_fmt_duration(m['duration_sec']):>15} |")
        lines.append("|                                              |")
        lines.append("|  +---------------------+----------+---------+ |")

        def row(label, value, rate_str="", warn_at=0):
            status = " "
            if rate_str and rate_str != "N/A":
                rate = float(rate_str.rstrip("% "))
                if rate > 5.0:
                    status = "!"
                elif rate > 2.0:
                    status = "!"
                else:
                    status = "*"
            return f"|  | {label:<19} | {str(value):>8} | {rate_str:>7} {status}| |"

        lines.append(row("Total Messages", m['total_msgs']))
        lines.append(row("Lost Packets", m['lost_packets'],
                         f"{m['loss_rate']}%" if m['loss_rate'] > 0 else "0%"))
        lines.append(row("CRC Failures", m['crc_failures'],
                         f"{m['crc_rate']}%" if m['crc_rate'] > 0 else "0%"))
        lines.append(row("Retransmits", m['retransmits'],
                         f"{m['retrans_rate']}%" if m['retrans_rate'] > 0 else "0%"))
        lines.append(row("Success Rate",
                         f"{m['success_rate']}%" if m['success_rate'] > 0 else "N/A"))
        lines.append("|  +---------------------+----------+---------+ |")
        lines.append("|                                              |")

        # Visual bars
        max_rate = max(m['loss_rate'], m['crc_rate'], m['retrans_rate'], 1)
        max_bar = max(max_rate, 10)
        lines.append(f"|  Packet Loss:  {_bar(m['loss_rate'], max_bar)} {m['loss_rate']}%  |")
        lines.append(f"|  CRC Errors:   {_bar(m['crc_rate'], max_bar)} {m['crc_rate']}%  |")
        lines.append(f"|  Retransmits:  {_bar(m['retrans_rate'], max_bar)} {m['retrans_rate']}%  |")

        if m['avg_latency_ms'] > 0:
            lines.append(f"|  Avg Latency:  {m['avg_latency_ms']} ms                         |")

        lines.append("|                                              |")

        # Status
        status_icon = {"NORMAL": "*", "WARNING": "!", "CRITICAL": "!"}
        icon = status_icon.get(m['status'], "?")
        lines.append(f"|  Overall: {icon} {m['status']:<41}|")
        lines.append(f"|  Thresholds: loss<2% crc<1% latency<500ms     |")

    lines.append("+======================================================+")
    return "\n".join(lines)


def print_check_zone(device_id: str = None):
    """Print the Check Zone to terminal"""
    print(generate_check_zone(device_id))


def get_recommendations(metrics: dict) -> list:
    """Generate actionable recommendations based on metrics"""
    recs = []
    if metrics.get('crc_rate', 0) > 1.0:
        recs.append(f"! CRC errors at {metrics['crc_rate']}%: "
                    f"Check GPS module cable shielding, "
                    f"reduce electromagnetic interference")
    if metrics.get('loss_rate', 0) > 2.0:
        recs.append(f"! Packet loss at {metrics['loss_rate']}%: "
                    f"Weak network signal, consider directional antenna "
                    f"or cellular booster")
    if metrics.get('loss_rate', 0) > 5.0:
        recs.append(f"! Critical packet loss: "
                    f"Survey will have frequent failures. "
                    f"Move to area with better reception")
    if metrics.get('avg_latency_ms', 0) > 500:
        recs.append(f"! High latency ({metrics['avg_latency_ms']}ms): "
                    f"Consider closer MQTT broker or 5G network")
    if metrics.get('success_rate', 100) < 90:
        recs.append(f"! Low survey success rate ({metrics['success_rate']}%): "
                    f"Likely due to data corruption or network issues above")
    if not recs:
        recs.append(f"* All metrics within normal range. No action needed.")
    return recs
