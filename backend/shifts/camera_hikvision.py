"""
Parsování HTTP alarmů z Hikvision / HiLook NVR (bez lokální brány).
"""
import re
from xml.etree import ElementTree

from django.utils import timezone
from django.utils.dateparse import parse_datetime

MOTION_EVENT_TYPES = re.compile(
    r'^(VMD|motion|fielddetection|linedetection|intrusion|human|humanBody|alarm)$',
    re.IGNORECASE,
)

MOTION_KEYWORDS = re.compile(
    r'(motion|vmd|linedetection|fielddetection|intrusion|human|alarm)',
    re.IGNORECASE,
)


def _local_tag(tag: str) -> str:
    return tag.split('}')[-1] if '}' in tag else tag


def _extract_xml_payload(raw: bytes) -> str:
    text = raw.decode('utf-8', errors='replace').strip()
    if not text:
        return ''
    if '<EventNotificationAlert' in text:
        start = text.find('<EventNotificationAlert')
        end = text.find('</EventNotificationAlert>')
        if end != -1:
            return text[start : end + len('</EventNotificationAlert>')]
    if text.startswith('<?xml') or text.startswith('<'):
        return text
    return text


def parse_hikvision_alarm(raw: bytes):
    """
    Vrací dict: motion (bool|None), event_type, event_state, cas (aware|None), ignored (bool).
    motion=None znamená „neukládat“ (heartbeat / neznámá událost).
    """
    xml_text = _extract_xml_payload(raw)
    if not xml_text or '<' not in xml_text:
        return {'motion': None, 'ignored': True, 'reason': 'empty'}

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        if MOTION_KEYWORDS.search(xml_text):
            return {
                'motion': True,
                'event_type': 'unknown',
                'event_state': None,
                'cas': None,
                'ignored': False,
            }
        return {'motion': None, 'ignored': True, 'reason': 'parse_error'}

    fields = {}
    for el in root.iter():
        tag = _local_tag(el.tag)
        if tag in ('eventType', 'eventState', 'eventDescription', 'dateTime', 'channelID'):
            if el.text:
                fields[tag] = el.text.strip()

    event_type = fields.get('eventType', '')
    event_state = (fields.get('eventState') or '').lower()

    if event_type and not MOTION_EVENT_TYPES.match(event_type) and not MOTION_KEYWORDS.search(event_type):
        return {
            'motion': None,
            'ignored': True,
            'reason': 'not_motion',
            'event_type': event_type,
        }

    if event_state in ('inactive', 'stop', 'stopped', 'off'):
        motion = False
    elif event_state in ('active', 'start', 'started', 'on'):
        motion = True
    else:
        motion = True

    cas = None
    dt_raw = fields.get('dateTime')
    if dt_raw:
        parsed = parse_datetime(dt_raw.replace('Z', '+00:00'))
        if parsed:
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
            cas = parsed

    return {
        'motion': motion,
        'event_type': event_type or None,
        'event_state': event_state or None,
        'cas': cas,
        'ignored': False,
        'channel_id': fields.get('channelID'),
    }
