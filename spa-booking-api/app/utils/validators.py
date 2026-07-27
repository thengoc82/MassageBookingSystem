import re


def validate_phone_number(phone):
    pattern = r'^0[0-9]{9,10}$'
    return bool(re.match(pattern, phone))

def validate_time_format(time_str):
    pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
    return bool(re.match(pattern, time_str))

def validate_date_format(date_str):
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(pattern, date_str))
