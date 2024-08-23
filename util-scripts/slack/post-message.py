import os
import requests
import json

class Slack:
    # the __init__ method initializes the Slack token and channel
    def __init__(self, token, channel): 
        self.token = os.getenv('RF_SLACK_TOKEN', token)
        self.channel = os.getenv('RF_SLACK_CHANNEL', channel)
        self.base_url = "https://slack.com/api/"
    
        print(f"Slack token: {self.token[:8]}")
        print(f"Slack channel: {self.channel}")

    # The post_message method sends a message to the specified Slack channel using the Slack API
    def post_message(self, message):
        url = self.base_url + "chat.postMessage"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self.token}"
        }
        payload = {
            "channel": self.channel,
            "text": message
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # Check if the response status code is not in the 20X range
        if not response.status_code // 100 == 2:
            # Log the error or raise an exception
            raise Exception(f"Failed to post message: {response.status_code} - {response.text}")
        
        return response.json()

if __name__ == "__main__":
    slack_channel = os.getenv('RF_SLACK_CHANNEL')
    slack_integration = Slack(token=os.getenv('RF_SLACK_TOKEN'), channel=slack_channel)

    # Example payload
    payload = {
        "title": "New Integration",
        "description": "This is a new integration for Slack."
    }

    # Format the message
    message = f"*Title:* {payload['title']}\n*Description:* {payload['description']}"

    # Post the message
    response = slack_integration.post_message(message)
    print(response)