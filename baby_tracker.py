import base64
import json
import logging
import os
import uuid
from datetime import datetime

import requests


class BabyTracker(object):
    """Authenticate and create transactions to BabyTracker app."""

    URL = "https://prodapp.babytrackers.com"

    def __init__(self, logger=None):
        # setup logging
        self.logger = logger or logging.getLogger(__name__)

        # set up config directory
        dir_config = os.path.join(os.path.dirname(__file__), "config")
        self.config = json.load(open("config/config.json"))
        assert set(self.config.keys()) == {"application_id"}

        # get baby_data from json and assert keys
        # TODO: load this from the baby tracker server
        # not sure what he's talking about
        self.baby_data = json.load(open("config/baby_data.json"))
        assert set(self.baby_data.keys()) == {
            "dueDay",
            "BCObjectType",
            "gender",
            "pictureName",
            "dob",
            "newFlage",
            "timestamp",
            "name",
            "objectID",
        }

        # create session
        self.session = self.create_auth_session()

        # get devices - this is just mimicing what the iOS does. we don't use it.
        devices = self.get_devices()

    def create_auth_session(self):
        session = requests.session()

        try:
            email = os.getenv("EMAIL")
            password = os.getenv("PASSWORD")
        except:
            raise Exception("Make sure the .env file has EMAIL and PASSWORD set")

        new_device = {
            "Device": {
                "DeviceOSInfo": "Tadpole",
                "DeviceName": "BabyTracker Python",
                "DeviceUUID": self.config["application_id"],
            },
            # TODO: I don't know what this means
            "AppInfo": {"AppType": 0, "AccountType": 0},
            "Password": password,
            "EmailAddress": email,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Encoding": "br, gzip, deflate",
            "Accept-Language": "en-us",
            "charset": "utf-8",
            "Connection": "keep-alive",
            "User-Agent": "BabyTrackerPro/36 CFNetwork/1098.1 Darwin/19.0.0",
        }

        # session.cookies.set_cookie(
        #     name="AWSELB",
        #     value="",
        # )

        p = session.post(self.URL + "/session", headers=headers, data=json.dumps(new_device))
        self.logger.info(p.text)
        self.logger.info(session.cookies)

        # c1 = requests.cookies.create_cookie(
        #     "AWSELB",
        #     "",
        # )
        # c2 = requests.cookies.create_cookie("PHPSESSID", "")
        # session.cookies.set_cookie(c1)
        # session.cookies.set_cookie(c2)

        return session

    def create_transactions(self, tadpole_dict):
        for tadpole_trans in sorted(tadpole_dict, key=lambda i: i["type"]):
            transaction = ""
            self.logger.info("Creating transaction [{}]".format(tadpole_trans["type"]))

            if tadpole_trans["actor"]:
                actor = tadpole_trans["actor"]
            else:
                actor = "Parent"

            if tadpole_trans["type"] == "diaper":
                note = f"Diaper changed by {actor}"
                transaction = self.create_diaper_transaction(
                    tadpole_trans["start_time"], tadpole_trans["diaper_type"], note
                )

            elif tadpole_trans["type"] == "meal":
                if tadpole_trans["amount_offered"]:
                    note = f"Fed by {actor} (offered {tadpole_trans['amount_offered']}oz)"
                else:
                    note = f"Fed by {actor}"
                transaction = self.create_bottle_transaction(
                    tadpole_trans["start_time"], tadpole_trans["quantity"], note
                )

            elif tadpole_trans["type"] == "nap":
                note = f"Woke up at {tadpole_trans['end_time']}"
                transaction = self.create_sleep_transaction(
                    tadpole_trans["start_time"], tadpole_trans["duration"], note
                )

            self.record_transaction(transaction)
            devices = self.get_devices()

    def create_diaper_transaction(self, timestamp, diaper_type, note="auto-created"):
        # diaper
        # "status": 0 - wet
        # "status": 1 - dirty
        # "status": 2 - mixed
        # "status": 0 + "amount": 0 - #dry
        diaper_status = {"wet": 0, "dry": 0, "dirty": 1, "mixed": 2}

        # default amount is 2, except for dry
        if diaper_type == "dry":
            amount = 0
        else:
            amount = 2

        return {
            "BCObjectType": "Diaper",
            "pooColor": 5,
            "peeColor": 5,
            "objectID": str(uuid.uuid4()).upper(),
            "time": timestamp,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S +0000"),
            "newFlage": "true",
            "pictureLoaded": "true",
            "texture": 5,
            "amount": amount,
            "baby": self.baby_data,
            "flag": 0,
            "pictureNote": [],
            "status": diaper_status[diaper_type],
            "note": note,
        }

    def create_bottle_transaction(self, timestamp, amount, note="auto-created"):
        return {
            "amount": {"value": amount, "englishMeasure": "true", "BCObjectType": "VolumeMeasure"},
            "BCObjectType": "Pumped",
            "note": note,
            "time": timestamp,
            "newFlage": "true",
            "pictureLoaded": "true",
            "pictureNote": [],
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S +0000"),
            "baby": self.baby_data,
            "objectID": str(uuid.uuid4()).upper(),
        }

    def create_sleep_transaction(self, start_time, duration, note="auto-created"):
        # duration =
        return {
            "BCObjectType": "Sleep",
            "note": note,
            "time": start_time,
            "newFlage": "true",
            "pictureLoaded": "true",
            "duration": duration,
            "pictureNote": [],
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S +0000"),
            "baby": self.baby_data,
            "objectID": str(uuid.uuid4()).upper(),
        }

    def generate_sync_data(self, transaction, sync_id, code="new"):
        opcode = {"new": 0, "update": 1, "delete": 2}
        return {
            "OPCode": opcode[code],
            "Transaction": base64.b64encode(json.dumps(transaction).encode()).decode(),
            "SyncID": sync_id,
        }

    def last_sync_id(self):
        response = self.session.get(self.URL + "/account/device")
        devices = json.loads(response.text)
        for device in devices:
            if device["DeviceUUID"] == self.config["application_id"]:
                return device["LastSyncID"]
        raise Exception("last_sync_id not found. I've had issues with returning 0 here.")

    def record_transaction(self, transaction):
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Encoding": "br, gzip, deflate",
            "Accept-Language": "en-us",
            "charset": "utf-8",
            "Connection": "keep-alive",
            "User-Agent": "BabyTrackerPro/36 CFNetwork/1098.1 Darwin/19.0.0",
        }
        self.logger.debug(f"syncing transaction: {transaction}")
        data = self.generate_sync_data(transaction, self.last_sync_id() + 1)

        self.logger.info(f"Posting transaction")
        self.logger.debug(f"post data: {data}")
        post = self.session.post(self.URL + "/account/transaction", headers=headers, json=data)

        if post.status_code == 201:
            self.logger.debug(f"POST successful! status code: {post.status_code}")
            return True

        self.logger.debug(f"POST error? status code: {post.status_code}")
        self.logger.debug(f"POST headers: {post.headers}")
        return False

    def get_devices(self):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "br, gzip, deflate",
            "Accept-Language": "en-us",
            "charset": "utf-8",
            "Connection": "keep-alive",
            "User-Agent": "BabyTrackerPro/36 CFNetwork/1098.1 Darwin/19.0.0",
        }
        r = self.session.get(self.URL + "/account/device", headers=headers)
        return r.json()

    def get_transactions_for_device(self, device, count=None):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "br, gzip, deflate",
            "Accept-Language": "en-us",
            "charset": "utf-8",
            "Connection": "keep-alive",
            "User-Agent": "BabyTrackerPro/36 CFNetwork/1098.1 Darwin/19.0.0",
        }
        if not count:
            last_sync = int(device["LastSyncID"]) - 1
        else:
            last_sync = int(device["LastSyncID"]) - count

        # URL2 = "https://prodapp.babytrackers.com/account/transaction/B2D6EA52-D800-4C04-963B-7FF4A7B0A37A/1412"
        r = self.session.get(
            self.URL + f"/account/transaction/{device['DeviceUUID']}/{last_sync}", headers=headers
        )

        transactions = r.json()

        if len(transactions) >= 1:
            return transactions

        return None

    def get_last_transactions(self):
        devices = self.get_devices()

        # loop through devices and get transactions for each
        count = 10
        all_transactions = []
        for device in devices:
            transactions = self.get_transactions_for_device(device, count)

            for transaction in transactions:
                if transaction["OPCode"] != 2:
                    decoded_transaction = self.get_decoded_transaction_json(
                        transaction["Transaction"]
                    )
                    all_transactions.append(decoded_transaction)

        return all_transactions

    def get_decoded_transaction_json(self, transaction):
        return json.loads(base64.b64decode(transaction).decode())
