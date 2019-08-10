from datetime import datetime

import browsercookie
import pytz
import requests

from baby_tracker import BabyTracker


def get_largest_event(event_date):
    largest_event = {}
    for event in events:
        if event["type"] == "DailyReport":
            if event["event_date"] == event_date:
                print(
                    f"found a daily report. event_date: {event['event_date']}. entries count: {len(event['entries'])}"
                )
                if "entries" in largest_event:
                    if len(event["entries"]) > len(largest_event["entries"]):
                        largest_event = event
                else:
                    largest_event = event

    return largest_event


def get_utc_date_string(timestamp):
    return (
        datetime.fromtimestamp(timestamp).astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S +0000")
    )


url = "https://www.tadpoles.com/remote/v1/events?direction=range&earliest_event_time=1564632000&latest_event_time=1567310400&num_events=300&client=dashboard.com/parents"


cookies = browsercookie.firefox()

r = requests.get(url, cookies=cookies)

json = r.json()

events = {}

if "events" in json:
    events = json["events"]
else:
    raise ("There are no events in the response.")


my_date = "2019-08-09"
largest_event = get_largest_event(my_date)


print("biggest entries: ", len(largest_event["entries"]))

transactions = []

if "entries" in largest_event:
    # loop through each entry
    for entry in largest_event["entries"]:
        actor = None
        start_time = None

        if "start_time" in entry:
            start_time = get_utc_date_string(entry["start_time"])

        if "parent" in entry and entry["parent"] == True:
            actor = "Parent"
        else:
            if "actor" in entry and entry["actor"]:
                actor = entry["actor"]

            if "prepared_actor" in entry and entry["prepared_actor"]:
                actor = entry["prepared_actor"]

        if entry["type"] == "bathroom":
            print(
                "bathroom found: actor: {} start_time: {} classification: {}".format(
                    actor, entry["start_time"], entry["classification"]
                )
            )
            transactions.append(
                {
                    "type": "diaper",
                    "actor": actor,
                    "start_time": start_time,
                    "classification": entry["classification"],
                }
            )

        elif entry["type"] == "food":

            quantity = entry["quantity"]
            amount_offered = None
            contents = None

            if "amount_offered" in entry:
                amount_offered = entry["amount_offered"]

            if "contents" in entry:
                contents = entry["contents"]

            print(
                "bottle found: actor: {} start_time: {} contents: {}".format(
                    actor, entry["start_time"], contents
                )
            )
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
            if "start_time" in entry and "end_time" in entry:
                stop_time = get_utc_date_string(entry["end_time"])

                delta = datetime.fromtimestamp(entry["end_time"]) - datetime.fromtimestamp(
                    entry["start_time"]
                )

                duration = int(delta.seconds / 60)

                print(
                    "completed nap found: actor: {} start_time: {} stop_time: {} duration: {}".format(
                        actor, entry["start_time"], entry["end_time"], duration
                    )
                )

                transactions.append(
                    {
                        "type": "nap",
                        "actor": actor,
                        "start_time": start_time,
                        "end_time": datetime.fromtimestamp(entry["end_time"]).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "duration": duration,
                    }
                )

tracker = BabyTracker()
tracker.create_transactions(transactions)

# TODO
# create baby tracker events
# check if baby tracker events exist
#
