import os
import requests
import json
from .console import (
    pretty_print,
    MessageType
)

class Slack():
    # the __init__ method initializes the Slack token and channel
    def __init__(self, token, channel): 
        self.token = os.getenv('RF_SLACK_TOKEN')
        self.channel = os.getenv('RF_SLACK_CHANNEL')
        self.base_url = "https://slack.com/api/"
    
    # create function for each corresponding slack block kit element from oad_dict written in the main script
    def build_title_block(self, pr_title):
      return {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Threat Model Mate Review Required on: :bufo-offers-a-llama: {pr_title}",
                "emoji": True
            }
        }
    def build_repo_info_block(self, repository, commit_url=None):
        text = f"*Info:* :hugging_face: See <https://github.com/{repository}|repo>"
        if commit_url:
            text += f" and <{commit_url}|commit>"

        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text + " for more information"
            }
        }
    def build_ticket_block(self, ticket_id):
      return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Ticket `{ticket_id}` extracted, see <https://linear.app/{ticket_id}|here> for more information",
                "emoji": True
            }
        }
    def build_reasoning_block_in_scope(self, reason_in_scope):
       return {
           "type": "section",
           "text":
               {
                "type": "mrkdwn",
                "text": f"*Model Review Reason:*\n\n{reason_in_scope}"
               }
       }
    def build_divider_block(self):
       return {
            "type": "divider"
       }
    def build_reasoning_block_out_of_scope(self, reason_out_of_scope):
       return {
           "type": "section",
           "text":
               {
                "type": "mrkdwn",
                "text": f"*Out of Scope Reason:*\n\n{reason_out_of_scope}"
               }
       }
    def build_slack_blocks(self, message):
            blocks = []
            in_scope = message["in_scope"]
    
            for obj in in_scope:
                if obj is None:
                    continue

                # extract the pr title nested object and append to the function blocks
                pr_title  = obj["pr"]["title"]
                title_block = self.build_title_block(pr_title)
                blocks.append(title_block)

                # extract the pr repo and url nested object and append to the function blocks
                repository = obj["pr"]["repository"]
                commit_url = obj["pr"]["url"]
                info_block = self.build_repo_info_block(repository, commit_url)  
                blocks.append(info_block)

                # extract the ticket object and append to the function blocks
                ticket = obj.get("ticket")
                if ticket:
                    ticket_id = ticket.get("id")
                    if ticket_id:
                        ticket_block = self.build_ticket_block(ticket_id)
                        blocks.append(ticket_block)
                if ticket is not None:
                    ticket_id = ticket.get("id", "No Ticket ID Provided")
                    ticket_block = self.build_ticket_block(ticket_id)
                    blocks.append(ticket_block)

                # extract the in_scope reason nested object and append to the function blocks
                reason_in_scope = obj["review"]["reasoning"]
                reason_in_scope_block = self.build_reasoning_block_in_scope(reason_in_scope)
                blocks.append(reason_in_scope_block)

                # add a divider block between in and out of scope
                divider_block = self.build_divider_block()
                blocks.append(divider_block)
            
            out_of_scope = message["out_of_scope"]
            
            for obj in out_of_scope:
                if obj is None:
                    continue
                
                # extract the out_of_scope reason nested object and append to the function blocks
                reason_out_of_scope = obj["review"]["reasoning"]
                reason_out_of_scope_block = self.build_reasoning_block_out_of_scope(reason_out_of_scope)
                blocks.append(reason_out_of_scope_block)
#
            return blocks


    # the post_message method sends a message to the specified Slack channel using the Slack API
    def post_message(self, message):
        # Implementation of post_message
        url = self.base_url + "chat.postMessage"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self.token}"
        }
    
        #block_payload = self.build_slack_blocks(json.loads(message)) # TODO changes the message to a dictionary
        blocks = self.build_slack_blocks(json.loads(message)) # TODO changes the message to a dictionary
        payload = {
            "channel": self.channel,
            "blocks": blocks
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
    
        # Check if the response status code is not 200 (OK)
        if not response.status_code // 100 == 2:
            # Log the error or raise an exception
            raise Exception(f"Failed to post message: {response.status_code} - {response.text}")
        
        # If successful, pretty_print the success message
        pretty_print(f"Slack post status, channel: {self.channel}, response: {response.json()}", MessageType.INFO)
