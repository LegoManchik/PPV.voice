
def first_number(x):
    try:
        if (split := x.split('_', 1))[0].isdigit():
            return int(x.split('_')[0])
        else:
            return float('inf')
    except TypeError:
        return None
