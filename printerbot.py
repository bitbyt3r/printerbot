import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import queue
import tempfile
import requests
import threading

app = App(token=os.environ["SLACK_BOT_TOKEN"])
print_queue = queue.Queue()

@app.event('message')
def message_posted(event, say):
    if event['channel'] != os.environ['SLACK_CHANNEL']:
        return
    if event['files']:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Let me know how you want this printed."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "input",
                "block_id": "copies",
                "element": {
                    "type": "number_input",
                    "is_decimal_allowed": False,
                    "min_value": "1",
                    "initial_value": "1",
                    "max_value": "100"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Copies",
                    "emoji": True
                }
            },
            {
                "block_id": "printer",
                "type": "input",
                "element": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a printer",
                        "emoji": True
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "STOPS",
                                "emoji": True
                            },
                            "value": "STOPS"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "TechOps",
                                "emoji": True
                            },
                            "value": "TechOps"
                        }
                    ],
                },
                "label": {
                    "type": "plain_text",
                    "text": "Destination Printer",
                    "emoji": True
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Print",
                            "emoji": True
                        },
                        "value": event['files'][0]['url_private_download'],
                        "action_id": "print"
                    }
                ]
            }
        ]
        say(
            blocks=blocks,
            thread_ts=event['ts']
        )

@app.action("print")
def print_action(ack, say, body):
    ack()
    print(body['state'])
    copies = int(body['state']['values']['copies']['copies']['value'])
    printer = body['state']['values']['printer']['printer']['selected_option']['value']
    file_url = body['message']['blocks'][4]['elements'][0]['value']
    say(f"Printing {copies} {'copies' if copies > 1 else 'copy'} on {printer} printer", thread_ts=body['message']['thread_ts'])
    print_queue.put({
        "copies": copies,
        "printer": printer,
        "file_url": file_url
    })

def print_thread():
    while True:
        job = print_queue.get()
        print("Printing", job)
        r = requests.get(job['file_url'], allow_redirects=True)
        with tempfile.NamedTemporaryFile(delete=False) as FILE:
            FILE.write(r.content)
            if os.system(f"lpr -H cups:631 -P {job['printer']} -# {job['copies']} {FILE.name}") == 0:
                print(f"Job {job['file_url']}@{job['copies']} started successfully.")
            else:
                print(f"Failed to print {job['file_url']}@{job['copies']} on {job['printer']}")
        print_queue.task_done()
            
        

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    printer = threading.Thread(target=print_thread)
    printer.daemon = True
    printer.start()
    handler.start()