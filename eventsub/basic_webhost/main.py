from flask import Flask, jsonify, request, Response, render_template, redirect
import hmac
import hashlib
import requests
import json
app = Flask(__name__)


# The URL that Twitch will post back to 
base_url = ""

# Client ID from Twitch (dev.twitch.tv)
client_id = ""

# Client Secret from Twitch (dev.twitch.tvb)
client_secret = ""

# Random string to be used to sign messages from Twitch
twitch_eventsub_secret = "0123456789abcdefghiABCDEFGHI"

# Twitch User ID to test with
twitch_user_id = "12826" # Twitch

# Subscription Type to test with
subscription_type = "channel.follow"


#####                                   #####
# Most of this does not need to be modified #
#####                                   #####


# The Base URL for all things Event Sub
eventsub_subscription_url = "https://api.twitch.tv/helix/eventsub/subscriptions"


# Generate an access token for authenticating requests
auth_body = {
    "client_id": client_id,
    "client_secret": client_secret,
    "grant_type": "client_credentials"
}
auth_response = requests.post("https://id.twitch.tv/oauth2/token", auth_body)


# Setup Headers for future requests
keys = auth_response.json()
headers = {
    "Client-ID": client_id,
    "Authorization": f"Bearer {keys['access_token']}"
}


# Used to verify a message to ensure it's from Twitch
def verify_signature(request):
    hmac_message = request.headers['Twitch-Eventsub-Message-Id'] + request.headers['Twitch-Eventsub-Message-Timestamp'] + request.data.decode()
    message_signature = "sha256=" + hmac.new(str.encode(twitch_eventsub_secret), str.encode(hmac_message), hashlib.sha256).hexdigest()
    if message_signature == request.headers['Twitch-Eventsub-Message-Signature']:
        return True
    return False


# Generic landing page.... just because
@app.route("/")
def hello_world():
    return render_template("index.html", client_id=client_id, base_url=base_url)


# Handle auth to verify tokens
@app.route("/auth")
def auth_client():
    code = request.args.get('code')
    request_uri = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&code={code}&grant_type=authorization_code&redirect_uri={base_url}/auth"
    response = requests.post(request_uri, headers=headers)
    return Response(response=json.dumps(response.json(), sort_keys=True, indent=4), status=200, mimetype='application/json')


# Setup a test subscription 
@app.route("/setup", methods=["GET"])
def setup_subscription():
    body = {
            "type": subscription_type,
            "version": "1",
            "condition": {
                "broadcaster_user_id": twitch_user_id
            },
            "transport": {
                "method": "webhook",
                "callback": f"{base_url}/webhooks/callback",
                "secret": twitch_eventsub_secret
            }
        }
    new_subscription_response = requests.post(eventsub_subscription_url, json=body, headers=headers)
    return Response(response=json.dumps(new_subscription_response.json(), sort_keys=True, indent=4), status=200, mimetype="application/json")


# Used to Reset (aka delete) all subscriptions (does NOT paginate, so may need to run multiple times)
@app.route("/reset", methods=["GET"])
def reset_subscriptions():
    subscription_list = requests.get(eventsub_subscription_url, headers=headers).json()
    for subscription in subscription_list['data']:
        requests.delete(eventsub_subscription_url, headers=headers, params={"id": subscription['id']})
    return Response(response=json.dumps(subscription_list, sort_keys=True, indent=4), status=200, mimetype="application/json")


# Used to list subscriptions that would be deleted with /reset
@app.route("/list", methods=["GET"])
def list_subscriptions():
    subscription_list = requests.get(eventsub_subscription_url, headers=headers).json()
    return Response(response=json.dumps(subscription_list, sort_keys=True, indent=4), status=200, mimetype="application/json")


# Used to handle webhooks sent
@app.route("/webhooks/callback", methods=["POST"])
def twitch_callback():
    # Check the request signature to ensure it's from Twitch
    if not verify_signature(request):
        return Response(response="wrong signature", status=405, mimetype="text/plain")

    # Grab the body of the request
    request_body = request.get_json()
    # Get the subscription data
    subscription_data = request_body['subscription']

    # If it's not a transport method of webhook, reject it
    if subscription_data['transport']['method'] != "webhook":
        return Response(response="", status=405, mimetype="text/plain")

    # If it's a pending webhook and passed signature verifications, return the challenge
    if subscription_data['status'] == "webhook_callback_verification_pending":
        return Response(response=request_body['challenge'], status=200, mimetype="text/plain")

    # If it's gotten this far, it's an event so grab the even data
    event_data = request_body['event']
    subscription_type = subscription_data['type']

    if subscription_type == "channel.update":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelupdate
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} updated their channel with title {event_data['title']}, category {event_data['category_name']}")

    elif subscription_type == "channel.follow":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelfollow
        print(f"{subscription_type}: {event_data['user_name']} followed {event_data['broadcaster_user_name']} at {event_data['followed_at']}")

    elif subscription_type == "channel.subscribe":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscribe
        print(f"{subscription_type}: {event_data['user_name']} subscribed to {event_data['broadcaster_user_name']} at tier {event_data['tier']}")

    elif subscription_type == "channel.subscribe.end":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptionend
        print(f"{subscription_type}: {event_data['user_name']} ended their subscription to {event_data['broadcaster_user_name']} at tier {event_data['tier']}")

    elif subscription_type == "channel.subscribe.gift":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptiongift
        print(f"{subscription_type}: {event_data['user_name']} gifted {event_data['total']} subscriptions to {event_data['broadcaster_user_name']} at tier {event_data['tier']}")

    elif subscription_type == "channel.subscribe.message":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelsubscriptionmessage
        print(f"{subscription_type}: {event_data['user_name']} resubscribed to {event_data['broadcaster_user_name']} at tier {event_data['tier']} for {event_data['cumulative_months']} months")

    elif subscription_type == "channel.cheer":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelcheer
        print(f"{subscription_type}: {event_data['user_name'] or 'anonymous'} cheered {event_data['bits']} bits to {event_data['broadcaster_user_name']} with the message {event_data['message']}")

    elif subscription_type == "channel.raid":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelraid
        print(f"{subscription_type}: {event_data['from_broadcaster_user_name']} raided {event_data['to_broadcaster_user_name']} with {event_data['viewers']} viewers")

    elif subscription_type == "channel.ban":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelban
        print(f"{subscription_type}: {event_data['user_name']} was banned by {event_data['moderator_user_name']} from {event_data['to_broadcaster_user_name']}'s chat and is {'permanent' if event_data['is_permanent'] else 'not permanent'}")

    elif subscription_type == "channel.unban":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelunban
        print(f"{subscription_type}: {event_data['user_name']} was unbanned by {event_data['moderator_user_name']} from {event_data['to_broadcaster_user_name']}'s chat")

    elif subscription_type == "channel.moderator.add":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelmoderatoradd
        print(f"{subscription_type}: {event_data['user_name']} was added as a moderator by {event_data['broadcaster_user_name']}")

    elif subscription_type == "channel.moderator.remove":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelmoderatorremove
        print(f"{subscription_type}: {event_data['user_name']} was removed as a moderator by {event_data['broadcaster_user_name']}")

    elif subscription_type == "channel.channel_points_custom_reward.add":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardadd
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} added a point redemption called {event_data['title']} that costs {event_data['cost']} points")

    elif subscription_type == "channel.channel_points_custom_reward.update":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardupdate
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} updated a point redemption called {event_data['title']} that costs {event_data['cost']} points")

    elif subscription_type == "channel.channel_points_custom_reward.remove":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_rewardremove
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} removed a point redemption called {event_data['title']} that costs {event_data['cost']} points")

    elif subscription_type == "channel.channel_points_custom_reward_redemption.add":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_reward_redemptionadd
        print(f"{subscription_type}: {event_data['user_name']} claimed a point redemption called {event_data['reward']['title']} that costs {event_data['reward']['cost']} points")

    elif subscription_type == "channel.channel_points_custom_reward_redemption.update":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelchannel_points_custom_reward_redemptionupdate
        print(f"{subscription_type}: {event_data['user_name']} had their point redemption updated called {event_data['reward']['title']} that costs {event_data['reward']['cost']} points to {event_data['status']}")

    elif subscription_type == "channel.poll.begin":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollbegin
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} started a poll titled {event_data['title']}")

    elif subscription_type == "channel.poll.progress":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollprogress
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} poll has received progress, titled {event_data['title']}")

    elif subscription_type == "channel.poll.end":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpollend
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} poll has ended, titled {event_data['title']}")

    elif subscription_type == "channel.prediction.begin":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionbegin
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} has started a prediction titled {event_data['title']}")

    elif subscription_type == "channel.prediction.progress":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionprogress
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} prediction has received progress, titled {event_data['title']}")

    elif subscription_type == "channel.prediction.lock":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionlock
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} prediction has been locked, titled {event_data['title']}")

    elif subscription_type == "channel.prediction.end":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelpredictionend
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} prediction has ended, titled {event_data['title']}")

    elif subscription_type == "channel.hype_train.begin":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainbegin
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} has a hype train beginning")

    elif subscription_type == "channel.hype_train.progress":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainprogress
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} progress has been applied to a level {event_data['level']} hype train with {event_data['progress']}/{event_data['goal']} progress")

    elif subscription_type == "channel.hype_train.end":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#channelhype_trainend
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} hype train has ended at level {event_data['level']}")

    elif subscription_type == "drop.entitlement.grant":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#dropentitlementgrant
        # Only for those associated to an organization that gives out drops
        print(f"{subscription_type}: Drops issued to {len(event_data)} users")

    elif subscription_type == "extension.bits_transaction.create":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#extensionbits_transactioncreate
        print(f"{subscription_type}: {event_data['user_name']} gave {event_data['product']['bits']} bits to {event_data['broadcaster_user_login']} via {event_data['product']['name']}")

    elif subscription_type == "stream.online":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#streamonline
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} went online at {event_data['started_at']}")

    elif subscription_type == "stream.offline":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#streamoffline
        print(f"{subscription_type}: {event_data['broadcaster_user_name']} went offline")

    elif subscription_type == "user.authorization.grant":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userauthorizationgrant
        print(f"{subscription_type}: {event_data['user_name']} granted authorization to me")

    elif subscription_type == "user.authorization.revoke":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userauthorizationrevoke
        print(f"{subscription_type}: {event_data['user_name']} revoke authorization to me")

    elif subscription_type == "user.update":
        # https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types#userupdate
        print(f"{subscription_type}: {event_data['user_name']} was updated")

    else:
        print(request_body)

    return Response(response="OK", status=202, mimetype="text/plain")
