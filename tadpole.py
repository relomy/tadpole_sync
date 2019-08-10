import logging
import logging.config
from datetime import datetime

import browsercookie
import pytz
import requests

from baby_tracker import BabyTracker

# load the logging configuration
logging.config.fileConfig("logging.ini")

logger = logging.getLogger(__name__)


def get_largest_event(events, target_date):
    largest_event = {}
    for event in events:
        if event["type"] == "DailyReport":
            if event["event_date"] == target_date:
                if "entries" in largest_event:
                    event_size = len(event["entries"])
                    logger.debug(
                        f"Found event (size: {event_size}) in DailyReport for {event['event_date']}"
                    )
                    if event_size > len(largest_event["entries"]):
                        largest_event = event
                else:
                    largest_event = event

    return largest_event


def get_utc_date_string(timestamp):
    return (
        datetime.fromtimestamp(timestamp).astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S +0000")
    )


def calculate_duration(start_time, end_time):
    delta = datetime.fromtimestamp(end_time) - datetime.fromtimestamp(start_time)
    return int(delta.seconds / 60)


def get_transactions(event):
    transactions = []
    if "entries" in event:
        # loop through each entry
        for entry in event["entries"]:
            # skip notes
            if entry["type"] == "note":
                continue

            # set actor (used for BabyTracker note) based on entry fields, if there is one
            actor = "..no one?"
            if "parent" in entry and entry["parent"] == True:
                actor = "Parent"
            else:
                if "actor" in entry and entry["actor"]:
                    actor = entry["actor"]
                elif "prepared_actor" in entry and entry["prepared_actor"]:
                    actor = entry["prepared_actor"]

            if "start_time" in entry:
                start_time = get_utc_date_string(entry["start_time"])
            else:
                raise Exception("No start_time found in entry")

            if entry["type"] == "bathroom":
                logger.info(f"Found a diaper @ {start_time}")
                # determine type of diaper to send to BabyTracker
                if "Wet" in entry["classification"]:
                    diaper_type = "wet"
                elif "BM" in entry["classification"]:
                    diaper_type = "dirty"
                elif "Dry" in entry["classification"]:
                    diaper_type = "dry"
                else:
                    raise Exception(f"Unsupported diaper type: {entry['classification']}")

                transactions.append(
                    {
                        "type": "diaper",
                        "actor": actor,
                        "start_time": start_time,
                        "diaper_type": diaper_type,
                    }
                )

            elif entry["type"] == "food":
                logger.info(f"Found a meal @ {start_time}")
                quantity = entry["quantity"]
                amount_offered = None
                contents = None

                if "amount_offered" in entry:
                    amount_offered = entry["amount_offered"]

                if "contents" in entry:
                    contents = entry["contents"]

                transactions.append(
                    {
                        "type": "meal",
                        "actor": actor,
                        "start_time": start_time,
                        "quantity": quantity,
                        "amount_offered": amount_offered,
                        "contents": contents,
                    }
                )
            elif entry["type"] == "nap":
                logger.info(f"Found a nap @ {start_time}")
                # completed naps only - must have an end_time
                if "end_time" in entry:
                    end_time = get_utc_date_string(entry["end_time"])

                    # calculate duration
                    duration = calculate_duration(entry["start_time"], entry["end_time"])

                    transactions.append(
                        {
                            "type": "nap",
                            "actor": actor,
                            "start_time": start_time,
                            "end_time": end_time,
                            "duration": duration,
                        }
                    )
    else:
        raise Exception("No entries found in largest_event")

    return transactions


def main():
    logger.info("Getting events from https://www.tadpoles.com")
    logger.debug("Getting cookies from Firefox")
    # TODO - authenticate properly with requests?
    cookies = browsercookie.firefox()
    url = "https://www.tadpoles.com/remote/v1/events?direction=range&earliest_event_time=1564632000&latest_event_time=1567310400&num_events=300&client=dashboard.com/parents"

    logger.debug(f"Perform GET request. URL: {url}")
    r = requests.get(url, cookies=cookies)
    json = r.json()

    events = {}
    if "events" in json:
        events = json["events"]
    else:
        raise Exception("There are no events in the response.")

    my_date = "2019-08-09"
    logger.info(f"Getting largest event for {my_date}")
    event = get_largest_event(events, my_date)

    if event == None:
        raise Exception("Event is empty.")

    logger.info(f"Getting transactions for event (date: {event['event_date']})")
    transactions = get_transactions(event)

    # TODO
    # create baby tracker events
    # check if baby tracker events exist
    logger.info("Creating transactions in BabyTracker")
    tracker = BabyTracker()
    tracker.create_transactions(transactions)


if __name__ == "__main__":
    main()

