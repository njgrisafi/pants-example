from find_needle import find_needle
from find_needle import rules as find_needle_rules


def rules():
    return (*find_needle.rules(), *find_needle_rules.rules())
