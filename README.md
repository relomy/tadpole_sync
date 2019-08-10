* Create data files for your config and your baby. These should be json files names `config.json` and `baby_data.json` respectively. They should be formatted like
```
{
    "application_id": "String" # id of your Alexa App, or null
}
```
and
```
{
    "dueDay": "YYYY-mm-dd HH:MM:SS +0000",
    "BCObjectType": "Baby",
    "gender": "false", # true = boy?
    "pictureName": "String",
    "dob": "YYYY-mm-dd HH:MM:SS +0000",
    "newFlage": "false", # ??
    "timestamp": "YYYY-mm-dd HH:MM:SS +0000", # Timestamp of the Baby Tracker object creation.
    "name": "String",
    "objectID": "String"
}
```
Please these files in the `config` directory.