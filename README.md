Create .json files for your config and place them in the `config` directory.

Example `config.json`
```
{
    "application_id": "String" # randomly generated UUID
}
```
Example `baby_data.json`
```
{
    "dueDay": "YYYY-mm-dd HH:MM:SS +0000",
    "BCObjectType": "Baby",
    "gender": "false", # true = boy
    "pictureName": "String",
    "dob": "YYYY-mm-dd HH:MM:SS +0000",
    "newFlage": "false", # ??
    "timestamp": "YYYY-mm-dd HH:MM:SS +0000", # Timestamp of the Baby Tracker object creation.
    "name": "String",
    "objectID": "String"
}
```

Please remember to have a `.env` file with your email and password as well.
```
EMAIL="example@example.com"
PASSWORD="password123"
```