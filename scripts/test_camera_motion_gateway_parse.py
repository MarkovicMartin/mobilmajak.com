#!/usr/bin/env python3
"""Unit testy parsování ISAPI alertů v bráně."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('gw', ROOT / 'camera_motion_gateway.py')
gw = importlib.util.module_from_spec(spec)
sys.modules['gw'] = gw
spec.loader.exec_module(gw)


def test_vmd_active_is_motion():
    xml = """<?xml version="1.0"?>
<EventNotificationAlert>
  <eventType>VMD</eventType>
  <eventState>active</eventState>
</EventNotificationAlert>"""
    assert gw.parse_alert_xml(xml) is True


def test_vmd_inactive_is_quiet():
    xml = """<?xml version="1.0"?>
<EventNotificationAlert>
  <eventType>VMD</eventType>
  <eventState>inactive</eventState>
</EventNotificationAlert>"""
    assert gw.parse_alert_xml(xml) is False


def test_heartbeat_ignored():
    xml = """<?xml version="1.0"?>
<EventNotificationAlert>
  <eventType>heartBeat</eventType>
  <eventState>active</eventState>
</EventNotificationAlert>"""
    assert gw.parse_alert_xml(xml) is None


if __name__ == '__main__':
    test_vmd_active_is_motion()
    test_vmd_inactive_is_quiet()
    test_heartbeat_ignored()
    spec2 = importlib.util.spec_from_file_location(
        'gw_live', ROOT / 'camera-gateway' / 'camera_motion_gateway.py',
    )
    live = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(live)
    from datetime import datetime
    assert live.minute_sample_has_motion(1000.0, 1059.0) is True
    assert live.minute_sample_has_motion(1000.0, 1060.0) is False
    assert live.minute_sample_has_motion(0.0, 1060.0) is False
    assert live.in_log_clock_window(datetime(2026, 10, 12, 7, 30), '07:30', '20:30') is True
    assert live.in_log_clock_window(datetime(2026, 10, 12, 7, 29), '07:30', '20:30') is False
    assert live.in_log_clock_window(datetime(2026, 10, 12, 20, 30), '07:30', '20:30') is False
    assert live.in_log_clock_window(datetime(2026, 10, 12, 3, 0), '07:30', '20:30') is False
    print('OK')
