import time
import ujson
from components.Switch import Switch

def average(values):
    return round(sum(values) / len(values)) if values else 0

def stddev(values):
    if len(values) < 2:
        return 0
    avg = average(values)
    variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5

def wait_for_press(switch, debounce_ms = 50):
    if not switch or type(switch) != Switch:
        raise Exception("Incorrect switch passed to utility function.")

    while not switch.single_press():
        time.sleep_ms(debounce_ms)
        
def save_json(directory, data):
    """save data to a JSON file with timestamped filename"""
    identifier = data.get('timestamp', int(time.time()))
    
    try:
        filename = f"{directory}/{identifier}.json"
        with open(filename, "w") as f:
            ujson.dump(data, f)
            f.flush()
            f.close()
        print(f"Data saved to {filename}")
    except Exception as e:
        print(f"Error saving data to JSON: {e}")

def convert_iso_epoch(iso_string):
    iso_string = "2025-05-08T06:46:34.673110+00:00"

    date_part = iso_string.split(".")[0]  # '2025-05-08T06:46:34'

    # Extract components
    date_str, time_str = date_part.split("T")
    year, month, day = map(int, date_str.split("-"))
    hour, minute, second = map(int, time_str.split(":"))

    # Create time tuple (year, month, mday, hour, minute, second, weekday, yearday)
    tm = (year, month, day, hour, minute, second, 0, 0)

    # Convert to epoch time
    epoch_time = time.mktime(tm)

    return epoch_time