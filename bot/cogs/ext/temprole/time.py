import re


def parse_time_string(time_string: str) -> int:
    time_units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    pattern = re.compile(r"(\d+d|\d+h|\d+m|\d+s)")
    matches = pattern.findall(time_string)

    if len("".join(matches)) != len(time_string):
        err = "Invalid time format"
        raise ValueError(err)

    total_seconds = 0
    for match in matches:
        number = int(match[:-1])
        unit = match[-1]
        total_seconds += number * time_units[unit]

    return total_seconds
