import re


def first_number(x):
    try:
        if x is None:
            return None

        x_str = str(x)
        number_str = ''

        for char in x_str:
            if char.isdigit():
                number_str += char
            else:
                break
        if number_str:
            return int(number_str)
        else:
            return float('inf')

    except (TypeError, ValueError):
        return None
