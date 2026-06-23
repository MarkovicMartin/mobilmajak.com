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
    print('OK')
