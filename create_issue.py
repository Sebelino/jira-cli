#!/usr/bin/env python3

import yaml
from atlassian import Jira
import argparse
from pprint import pprint
import requests
import os

DEFAULT_CONFIG_FILE = "config.yaml"
API_TOKEN_ENVVAR = "JIRA_CLI_API_TOKEN"

class IssueCreator:

    USER_LIMIT = 1000

    def __init__(self, config_file: str):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        self.jira = Jira(
            url=config["url"],
            username=config["username"],
            password=self.read_api_token(config),
        )

        self.project_key = config["project_key"]
        self.summary = config["summary"]
        self.issuetype = config["issuetype"]
        self.assignee = config["assignee"]
        self.status = config["status"]
        self.description = config["description"]
        self.fields = config.get("fields", dict())

        self._project = None
        self._sprint_field = None
        self._board_supports_sprints = None
        self._current_sprint_id = None
        self._all_custom_fields = None

    def create(self):
        issue = self.create_issue()
        self.postprocess_issue(issue)

    @staticmethod
    def read_api_token(config):
        config_value = config.get("api_token")
        envvar_value = os.getenv(API_TOKEN_ENVVAR)
        if config_value and envvar_value:
            raise Exception("API token cannot be set in both the configuration file and in the {} environment variable.".format(API_TOKEN_ENVVAR))
        if not config_value and not envvar_value:
            raise Exception("API token missing. Either set api_token in the configuration file or set it in the {} environment variable.".format(API_TOKEN_ENVVAR))
        return config_value or envvar_value

    @property
    def sprint_custom_field(self):
        return self._sprint_field or self.get_sprint_custom_field()

    @property
    def current_sprint_id(self):
        return self._current_sprint_id or self.get_current_sprint_id()

    @property
    def board_supports_sprints(self):
        if self._board_supports_sprints is not None:
            return self._board_supports_sprints
        current_sprint_id = self.get_current_sprint_id()
        if current_sprint_id is None:
            self._board_supports_sprints = False
            return False
        self._current_sprint_id = current_sprint_id
        self._board_supports_sprints = True
        return True

    def get_sprint_custom_field(self):
        field, = [f["id"] for f in self.all_custom_fields if f["name"] == "Sprint"]
        self._sprint_field = field
        return field

    @property
    def all_custom_fields(self):
        if not self._all_custom_fields:
            self._all_custom_fields = self.jira.get_all_custom_fields()
        return self._all_custom_fields

    @property
    def project(self):
        if not self._project:
            self._project = self.jira.get_project(self.project_key)
        return self._project

    def custom_field_name_to_id(self, field_name: str) -> str:
        scoped_fields = [f for f in self.all_custom_fields if "scope" in f]
        project_id = self.project["id"]
        project_fields = [f for f in scoped_fields if f["scope"]["project"]["id"] == project_id]
        matching_fields = [f for f in project_fields if f["name"].lower() == field_name.lower()]
        if len(matching_fields) == 0:
            raise Exception("There are no custom fields with the name {}".format(field_name))
        if len(matching_fields) >= 2:
            raise Exception("There is more than one custom field with the name {}".format(field_name))
        matching_field, = matching_fields
        return matching_field["id"]

    def get_current_sprint_id(self):
        board, = self.jira.get_all_agile_boards(project_key=self.project_key)["values"]
        try:
            all_sprints = self.jira.get_all_sprint(board["id"])
        except requests.exceptions.HTTPError as e:
            if str(e) == "The board does not support sprints":
                return None
            raise e
        current_sprint, = [s for s in all_sprints["values"] if s["state"] == "active"]
        return current_sprint["id"]

    def create_issue(self):
        fields = {
            "summary": self.summary,
            "project": {
                "key": self.project_key,
            },
            "issuetype": {
                "name": self.issuetype,
            },
            "description": self.description,
        }

        if self.board_supports_sprints:
            fields[self.sprint_custom_field] = self.current_sprint_id

        return self.jira.create_issue(fields)

    def postprocess_issue(self, issue):
        self.remove_labels(issue, ["to-be-groomed"])
        self.assign(issue, self.assignee)
        self.move_issue_to_status(issue, self.status)
        self.set_fields(issue, self.fields)

    def move_issue_to_status(self, issue, status):
        jira.issue_transition(issue["key"], status)

    def set_fields(self, issue, fields):
        fields = {self.custom_field_name_to_id(k): v for k, v in fields.items()}
        fields = {k: self.correct_field_value(v, k, issue) for k, v in fields.items()}
        self.jira.update_issue_field(issue['key'], fields)

    def correct_field_value(self, field_value, field, issue):
        metadata = jira.issue_createmeta(self.project_key)
        metadata, = metadata["projects"]
        metadata, = [t for t in metadata["issuetypes"] if field in t["fields"]]
        metadata = metadata["fields"]
        metadata = metadata[field]
        if "allowedValues" not in metadata:
            return field_value
        metadata = metadata["allowedValues"]
        matching_options = [option for option in metadata if option["value"] == field_value]
        if len(matching_options) == 0:
            raise Exception("There is no option for the field {} by the name {}".format(field, field_value))
        if len(matching_options) >= 2:
            raise Exception("Found multiple options for the field {} matching the name {}".format(field, field_value))
        matching_option, = matching_options
        return {"id": matching_option["id"]}

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

    def assign(self, issue, assignee):
        assignee_accountid = self.get_assignee_accountid(assignee)
        self.jira.assign_issue(issue['key'], account_id=assignee_accountid)

def parse_args():
    parser = argparse.ArgumentParser(description="Create an issue with minimum hassle.")
    parser.add_argument("--config_file", "-c", type=str, default=DEFAULT_CONFIG_FILE, help="Path to configuration YAML file")
    parser.add_argument("--noop", "-n", action="store_true", help="If set, don't create an issue")
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_args()

    creator = IssueCreator(args.config_file)

    jira = creator.jira

    if not args.noop:
        creator.create()
