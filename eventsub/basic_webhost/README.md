# How to run

### Install Dependencies:
```
pip install -r requirements.txt
```

### Configure
Edit the following lines in `main.py`
```python
base_url = "" # Set this to the base URL you have pointed to your dev machine MUST BE HTTPS WITH VALID CERTIFICATE

client_id = "" # Get this from https://dev.twitch.tv/console/apps

client_secret = "" # Get this from https://dev.twitch.tv/console/apps

subscription_type = "channel.follow" # Put whatever you want to test from https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types
```

### Run the application
Do this by running whichever file suits your system
  
* `run.ps1` for Windows with PowerShell
* `run.bat` for Windows with Command Prompt
* `run.sh` for Linux hosts

### Built in URLS
* `/` - This is the root path, with a few helpful links for the rest of the URLs
* `/auth` - This is for when authorizing the application using the link on the `/` page
* `/setup` - This will setup a subscription for whatever you defined in `main.py` as the `subscription_type`
* `/reset` - This will delete all subscriptions you have setup with the `client_id` defined in `main.py`
* `/list` - This will return a list of all subscriptions for the `client_id` defined in `main.py`
* `/webhooks/callback` - Used for Twitch to POST back to and handles all events currently available to Eventsub (as of 2021-07-28)
  * If an subscription type is not implemented/handled then the raw JSON from Twitch will be printed to console
