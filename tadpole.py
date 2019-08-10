from datetime import datetime
import browsercookie
import requests

import pytz

from baby_tracker import BabyTracker

url = "https://www.tadpoles.com/remote/v1/events?direction=range&earliest_event_time=1564632000&latest_event_time=1567310400&num_events=300&client=dashboard.com/parents"
cookies = browsercookie.firefox()

r = requests.get(url, cookies=cookies)

json = r.json()

events = {}

if "events" in json:
    events = json["events"]

print(len(events))
# get the last "notify" event


my_date = "2019-08-01"
biggest_event = {}
for event in events:
    if event["type"] == "DailyReport":
        if event["event_date"] == my_date:
            print(
                f"found a daily report. event_date: {event['event_date']}. entries count: {len(event['entries'])}"
            )
            if "entries" in biggest_event:
                if len(event["entries"]) > len(biggest_event["entries"]):
                    biggest_event = event
            else:
                biggest_event = event


print("biggest entries: ", len(biggest_event["entries"]))

transactions = []

if "entries" in biggest_event:
    # loop through each entry
    for entry in biggest_event["entries"]:
        actor = None
        start_time = None

        if "start_time" in entry:
            start_time_edt = datetime.fromtimestamp(entry["start_time"])
            start_time = start_time_edt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S +0000")

        if "parent" in entry and entry["parent"] == True:
            parent = True
            # print("PARENT IS TRUE!!!")

        if not parent:
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
        #     print("----------------------------\nBOTTLE")
        #     if not parent:
        #         if "contents" in entry:
        #             print(f"contents: {entry['contents']}")
        #         else:
        #             print("no contents??")

        #         if "amount_offered" in entry:
        #             print(f"amount_offered: {entry['amount_offered']}")
        #         else:
        #             print("no amount offered??")

        #     print(f"quantity: {entry['quantity']}")
        elif entry["type"] == "nap":
            print(entry)
            if "start_time" in entry and "end_time" in entry:
                stop_time_edt = datetime.fromtimestamp(entry["end_time"])
                stop_time = stop_time_edt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S +0000")

                delta = stop_time_edt - start_time_edt

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

        # reset parent flag
        parent = False


tracker = BabyTracker()
tracker.create_transactions(transactions)

# TODO
# create baby tracker events
# check if baby tracker events exist
#
