import argparse
import logging
import logging.config
from datetime import datetime, timedelta

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
        datetime.fromtimestamp(timestamp)
        .astimezone(pytz.utc)
        .strftime("%Y-%m-%d %H:%M:%S +0000")
    )


def calculate_duration(start_time, end_time):
    delta = datetime.fromtimestamp(end_time) - datetime.fromtimestamp(start_time)
    return int(delta.seconds / 60)


def parse_event_entry(entry, actor, start_time):
    entry_types = {"bathroom": "diaper", "food": "meal", "nap": "nap"}

    t = {"type": entry_types[entry["type"]], "actor": actor, "start_time": start_time}

    if entry["type"] == "bathroom":
        # determine type of diaper to send to BabyTracker
        classification = entry["classification"]
        if "Wet" in classification:
            diaper_type = "wet"
        elif "BM" in classification:
            diaper_type = "dirty"
        elif "Dry" in classification:
            diaper_type = "dry"
        else:
            logger.error(f"Unsupported diaper type: {classification}")
            return False

        t["diaper_type"] = diaper_type

    elif entry["type"] == "food":
        quantity = entry["quantity"]
        amount_offered = None
        contents = None

        if "amount_offered" in entry:
            amount_offered = entry["amount_offered"]

        if "contents" in entry:
            contents = entry["contents"]

        t["quantity"] = quantity
        t["amount_offered"] = amount_offered
        t["contents"] = contents

    elif entry["type"] == "nap":
        # completed naps only - must have an end_time
        if "end_time" not in entry:
            return None

        end_time = get_utc_date_string(entry["end_time"])

        # calculate duration
        duration = calculate_duration(entry["start_time"], entry["end_time"])

        t["end_time"] = end_time
        t["duration"] = duration

    return t


def get_transactions(event):
    transactions = []
    if "entries" in event:
        # loop through each entry
        for entry in event["entries"]:
            # skip notes and "activity" - picture?
            if entry["type"] == "note" or entry["type"] == "activity":
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

            logger.info(f"Found a {entry['type']} event @ {start_time}")

            event_entry = parse_event_entry(entry, actor, start_time)

            if event_entry:
                transactions.append(event_entry)

    else:
        raise Exception("No entries found in largest_event")

    return transactions


def transaction_already_exists(transaction, tracker_events):
    for event in tracker_events:
        # if type and start_time match, transaction already exists
        if (
            transaction["type"] == event["type"]
            and transaction["start_time"] == event["start_time"]
        ):
            logger.info(
                f"{transaction['type']} : {event['start_time']} matches, return true"
            )
            return True


def valid_date(date_string):
    """Check date argument to determine if it is a valid.

    Arguments
    ---------
        date_string {string} -- date from argument

    Returns
    -------
        {datetime.datetime} -- YYYY-MM-DD format

    """
    try:
        return datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}' - valid is YYYY-MM-DD.".format(date_string)
        raise argparse.ArgumentTypeError(msg)


def main():
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--date",
        required=True,
        help="Date (YYYY-MM-DD) to pull Tadpole events",
        default=datetime.today(),
        type=valid_date,
    )
    parser.add_argument(
        "-f",
        "--force",
        help="Do not check BabyTrack events prior to syncing Tadpole events",
    )
    args = parser.parse_args()

    logger.info("Getting events from https://www.tadpoles.com")
    logger.debug("Getting cookies from Firefox")
    # TODO - authenticate properly with requests?
    cookies = browsercookie.firefox()
    today = datetime.today()
    week_ahead = today + timedelta(days=7)
    week_ago = today - timedelta(days=7)
    earliest_time = int(week_ago.timestamp())
    latest_time = int(week_ahead.timestamp())
    url = f"https://www.tadpoles.com/remote/v1/events?direction=range&earliest_event_time={earliest_time}&latest_event_time={latest_time}&num_events=300&client=dashboard.com/parents"

    logger.debug(f"Perform GET request. URL: {url}")
    r = requests.get(url, cookies=cookies)
    json = r.json()

    events = {}
    if "events" in json:
        events = json["events"]
    else:
        raise Exception("There are no events in the response.")

    # use date from argument
    my_date = f"{args.date:%Y-%m-%d}"
    logger.info(f"Getting largest event for {my_date}")
    event = get_largest_event(events, my_date)

    if not event:
        logger.error("Event is empty.")
        exit()

    logger.info(f"Getting transactions for event (date: {event['event_date']})")
    transactions = get_transactions(event)

    # get last transactions from babytracker
    tracker = BabyTracker()
    tracker_events = tracker.get_last_transactions_decoded()

    logger.info("tracker_events count: {}".format(len(tracker_events)))

    # compare babytracker/tadpole and remove transactions that already exist
    logger.info("Comparing transactions from Tadpole and events from BabyTracker")
    transactions = [
        t for t in transactions if not transaction_already_exists(t, tracker_events)
    ]

    if transactions:
        logger.info("Creating transactions in BabyTracker")
        tracker.create_transactions(transactions)


if __name__ == "__main__":
    main()

