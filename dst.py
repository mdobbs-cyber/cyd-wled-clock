# dst.py — US Daylight Saving Time auto-detection
# Uses the US federal DST rule (post-2007 Energy Policy Act):
#   Start:  2nd Sunday in March     at 02:00 local standard time
#   End:    1st Sunday in November  at 02:00 local standard time
#
# Returns 1 (hour offset) if DST is currently in effect, else 0.
# Call:  dst.get_dst_offset(year, month, day, hour)

def _day_of_week(year, month, day):
    """Zeller-based weekday. Returns 0=Sunday, 1=Monday ... 6=Saturday."""
    if month < 3:
        month += 12
        year -= 1
    k = year % 100
    j = year // 100
    h = (day + (13 * (month + 1)) // 5 + k + k // 4 + j // 4 - 2 * j) % 7
    # h: 0=Sat,1=Sun,2=Mon,...,6=Fri  -> convert to 0=Sun
    return (h + 6) % 7  # 0=Sun, 1=Mon, ..., 6=Sat

def _nth_weekday(year, month, weekday, n):
    """Return the day-of-month for the Nth occurrence of weekday in month.
       weekday: 0=Sun ... 6=Sat
       n: 1-based (1=first, 2=second, ...)
    """
    # Find what weekday the 1st of the month falls on
    first_dow = _day_of_week(year, month, 1)
    # Days until we hit the target weekday
    diff = (weekday - first_dow) % 7
    day = 1 + diff + (n - 1) * 7
    return day

def get_dst_offset(year, month, day, hour):
    """Return 1 if US DST is active at (year, month, day, hour), else 0."""
    # Quick range check — DST only possible March through November
    if month < 3 or month > 11:
        return 0
    if month > 3 and month < 11:
        return 1

    if month == 3:
        # 2nd Sunday in March, starts at 02:00
        spring_day = _nth_weekday(year, 3, 0, 2)  # 0=Sunday, 2nd occurrence
        if day < spring_day:
            return 0
        if day == spring_day:
            return 1 if hour >= 2 else 0
        return 1  # after spring_day

    if month == 11:
        # 1st Sunday in November, ends at 02:00
        fall_day = _nth_weekday(year, 11, 0, 1)  # 0=Sunday, 1st occurrence
        if day < fall_day:
            return 1
        if day == fall_day:
            return 1 if hour < 2 else 0
        return 0  # after fall_day

    return 0  # should never reach
