#!/usr/bin/env python3

import yaml
from atlassian import Jira
import argparse
from pprint import pprint

DEFAULT_CONFIG_FILE = "config.yaml"

class IssueCreator:

    USER_LIMIT = 1000

    def __init__(self, config_file: str):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        self.jira = Jira(
            url=config["url"],
            username=config["username"],
            password=config["api_token"],
        )

        self.project_key = config["project_key"]
        self.summary = config["summary"]
        self.issuetype = config["issuetype"]
        self.assignee = config["assignee"]
        self.status = config["status"]
        self.description = config["description"]

        self._sprint_field = None

    def create(self):
        issue = self.create_issue()
        self.postprocess_issue(issue)

    @property
    def sprint_custom_field(self):
        return self._sprint_field or self.get_sprint_custom_field()

    def get_sprint_custom_field(self):
        field, = [f["id"] for f in jira.get_all_custom_fields() if f["name"] == "Sprint"]
        self._sprint_field = field
        return field

    def get_current_sprint(self):
        board, = self.jira.get_all_agile_boards(project_key=self.project_key)["values"]
        all_sprints = self.jira.get_all_sprint(board["id"])
        current_sprint, = [s for s in all_sprints["values"] if s["state"] == "active"]
        return current_sprint

    def create_issue(self):
        current_sprint = self.get_current_sprint()

        fields = {
            "summary": self.summary,
            "project": {
                "key": self.project_key,
            },
            "issuetype": {
                "name": self.issuetype,
            },
            "description": self.description,
            self.sprint_custom_field: current_sprint["id"],
        }

        return self.jira.create_issue(fields)

    def postprocess_issue(self, issue):
        self.remove_labels(issue, ["to-be-groomed"])
        self.assign_to_me(issue)
        self.move_issue_to_status(issue, self.status)

    def move_issue_to_status(self, issue, status):
        jira.issue_transition(issue["key"], status)

    def remove_labels(self, issue, disposable_labels):
        current_labels = self.jira.get_issue_labels(issue['id'])
        for disposable_label in disposable_labels:
            if disposable_label in current_labels:
                current_labels.remove(disposable_label)
        fields = {
            "labels": current_labels,
        }
        self.jira.update_issue_field(issue['key'], fields)

    def get_assignee_accountid(self, assignee_name):
        all_users = [u for u in self.jira.get_all_assignable_users_for_project(self.project_key, limit=self.USER_LIMIT)]

        if len(all_users) >= self.USER_LIMIT:
            raise Exception("This script currently assumes < {} Jira users".format(self.USER_LIMIT))

        assignee, = [u for u in all_users if assignee_name in u['displayName']]

        return assignee['accountId']

    def assign_to_me(self, issue):
        assignee_accountid = self.get_assignee_accountid(self.assignee)
        self.assign(issue, assignee_accountid)

    def assign(self, issue, account_id):
        self.jira.assign_issue(issue['key'], account_id=account_id)

def parse_args():
    parser = argparse.ArgumentParser(description="Create an issue with minimum hassle.")
    parser.add_argument("--config_file", "-c", type=str, default=DEFAULT_CONFIG_FILE, help="Path to configuration YAML file")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()

    creator = IssueCreator(args.config_file)

    jira = creator.jira

    creator.create()
