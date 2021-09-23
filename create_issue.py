#!/usr/bin/env python3

import json
from atlassian import Jira
from pprint import pprint

class IssueCreator:

    USER_LIMIT = 1000

    def __init__(self):
        self.project_key = "EP"

        with open("credentials.json", 'r') as f:
            credentials = json.load(f)

        self.jira = Jira(
            url=credentials["url"],
            username=credentials["username"],
            password=credentials["api_token"],
        )

    def create(self):
        issue = self.create_issue()
        self.postprocess_issue(issue)

    def create_issue(self):
        board, = self.jira.get_all_agile_boards(project_key=self.project_key)["values"]

        all_sprints = self.jira.get_all_sprint(board["id"])

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

        return self.jira.create_issue(fields)

    def postprocess_issue(self, issue):
        self.remove_labels(issue)
        self.assign(issue)

    def remove_labels(self, issue):
        labels = self.jira.get_issue_labels(issue['id'])
        if "to-be-groomed" in labels:
            labels.remove("to-be-groomed")
        fields = {
            "labels": labels,
        }
        self.jira.update_issue_field(issue['key'], fields)

    def assign(self, issue):
        all_users = [u for u in self.jira.get_all_assignable_users_for_project(self.project_key, limit=self.USER_LIMIT)]

        if len(all_users) >= self.USER_LIMIT:
            raise Exception("This script currently assumes < 1000 Jira users")

        me, = [u for u in all_users if 'Sebastian Olsson' in u['displayName']]

        my_accountid = me['accountId']

        self.jira.assign_issue(issue['key'], account_id=my_accountid)

if __name__ == "__main__":
    creator = IssueCreator()
    creator.create()
