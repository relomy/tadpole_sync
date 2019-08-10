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

        # self.config = json.load(open(os.path.join(dir_config, "config.json")))
        self.config = json.load(open("config/config.json"))
        assert set(self.config.keys()) == {"application_id"}

        # get baby_data from json and assert keys
        # TODO: load this from the baby tracker server
        # not sure what he's talking about
        # self.baby_data = json.load(open(os.path.join(dir_config, "baby_data.json")))
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

        # get devices
        # devices = self.get_devices()

        # create transaction
        # diaper = self.create_diaper_transaction("2019-08-07 23:56:15 +0000", "dirty")
        # meal = self.create_bottle_transaction("2019-08-07 12:30:15 +0000", 4.5)

        # if self.record_transaction(meal):
        #     self.logger.info("transaction recorded successfully!")
        # else:
        #     self.logger.info("there was an error.")

        # get_new_devices = self.get_devices()

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
        #     value="357513371890ED1DC31DB07EE8E45D074428B62AC1ECF7522B204D5DAA3027CCF32C1A2501532543FF95A57A8DFB9929525C138EAE2AB9BE930826AA4125C18FAA38D51017",
        # )

        p = session.post(self.URL + "/session", headers=headers, data=json.dumps(new_device))
        self.logger.info(p.text)
        self.logger.info(session.cookies)

        # c1 = requests.cookies.create_cookie(
        #     "AWSELB",
        #     "357513371890ED1DC31DB07EE8E45D074428B62AC140814EEF36AA02F3C3BD0A5F43F3D504D878B55936D185CD18F661CE4D650C4198ACF86893DAB17C6AB6C401F88B2A80",
        # )
        # c2 = requests.cookies.create_cookie("PHPSESSID", "mebpart8pdaoc2bict8dmi7ut1")
        # session.cookies.set_cookie(c1)
        # session.cookies.set_cookie(c2)

        return session

    def create_transactions(self, tadpole_dict):
        for tadpole_trans in sorted(tadpole_dict, key=lambda i: i["type"]):
            transaction = ""
            self.logger.info("Creating transaction [{}]".format(tadpole_dict["type"]))

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
                self.logger.info(f"create_nap: {tadpole_trans}")
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
        return 0

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
        # self.logger.info(f"new_transaction: {new_transaction}")
        self.logger.debug(f"syncing transaction: {transaction}")
        data = self.generate_sync_data(transaction, self.last_sync_id() + 1)
        # data = self.generate_sync_data(transaction, 1528)

        self.logger.info(f"Posting transaction")
        self.logger.debug(f"post data: {data}")
        # post = self.session.post(self.URL + "/account/transaction", headers=headers, json=data)

        # if post.status_code == 201:
        #     self.logger.info(f"POST successful! status code: {post.status_code}")
        #     return True
        # else:
        #     self.logger.info(f"POST error? status code: {post.status_code}")
        #     self.logger.info(f"POST headers: {post.headers}")
        #     return False

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

    def get_last_transaction_for_device(self, device, last_sync=None):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "br, gzip, deflate",
            "Accept-Language": "en-us",
            "charset": "utf-8",
            "Connection": "keep-alive",
            "User-Agent": "BabyTrackerPro/36 CFNetwork/1098.1 Darwin/19.0.0",
        }
        if not last_sync:
            last_sync = int(device["LastSyncID"]) - 1

        # URL2 = "https://prodapp.babytrackers.com/account/transaction/B2D6EA52-D800-4C04-963B-7FF4A7B0A37A/1412"
        r = self.session.get(
            self.URL + f"/account/transaction/{device['DeviceUUID']}/{last_sync}", headers=headers
        )

        last_transaction = r.json()

        if len(last_transaction) == 1:
            return last_transaction[0]

        return None

    def get_decoded_transaction_json(transaction):
        return json.loads(base64.b64decode(transaction).decode())
