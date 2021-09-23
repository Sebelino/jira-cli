#!/usr/bin/env python3

import json
from atlassian import Jira
from pprint import pprint

class IssueCreator:

    def __init__(self):
        self.project_key = "EP"

    def create(self):
        board, = jira.get_all_agile_boards(project_key=self.project_key)["values"]

        all_sprints = jira.get_all_sprint(board["id"])

        current_sprint, = [s for s in all_sprints["values"] if s["state"] == "active"]

        fields = {
            "summary": "(delet this) Test issue",
            "project": {
                "key": self.project_key,
            },
            "issuetype": {
                "name": "Task",
            },
            "customfield_10019": current_sprint["id"],
        }

        created_issue = jira.create_issue(fields)

        labels = jira.get_issue_labels(created_issue['id'])

        if "to-be-groomed" in labels:
            labels.remove("to-be-groomed")

        fields = {
            "labels": labels,
        }

        jira.update_issue_field(created_issue['key'], fields)

        all_users = [u for u in jira.get_all_assignable_users_for_project(self.project_key, limit=1000)]

        if len(all_users) >= 1000:
            raise Exception("This script currently assumes < 1000 Jira users")

        me, = [u for u in all_users if 'Sebastian Olsson' in u['displayName']]

        my_accountid = me['accountId']

        jira.assign_issue(created_issue['key'], account_id=my_accountid)

if __name__ == "__main__":

    with open("credentials.json", 'r') as f:
        credentials = json.load(f)

    jira = Jira(
        url=credentials["url"],
        username=credentials["username"],
        password=credentials["api_token"],
    )

    creator = IssueCreator()

    creator.create()
