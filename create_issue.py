#!/usr/bin/env python3

import json
from atlassian import Jira
from pprint import pprint

def create_issue(project_key: str):
    board, = jira.get_all_agile_boards(project_key=project_key)["values"]

    all_sprints = jira.get_all_sprint(board["id"])

    current_sprint, = [s for s in all_sprints["values"] if s["state"] == "active"]

    fields = {
        "summary": "(delet this) Test issue",
        "project": {
            "key": project_key,
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

    all_users = [u for u in jira.get_all_assignable_users_for_project(project['key'], limit=1000)]

    if len(all_users) >= 1000:
        raise Exception("This script currently assumes < 1000 Jira users")

    me, = [u for u in all_users if 'Sebastian Olsson' in u['displayName']]

    my_accountid = me['accountId']

    jira.assign_issue(created_issue['key'], account_id=my_accountid)

if __name__ == "__main__":

    project_key = "EP"

    with open("credentials.json", 'r') as f:
        credentials = json.load(f)

    jira = Jira(
        url=credentials["url"],
        username=credentials["username"],
        password=credentials["api_token"],
    )

    project = jira.project(project_key)

    issue_types = project['issueTypes']

    task_issue_type, = [tpe for tpe in project['issueTypes'] if tpe["name"] == "Task"]

    #create_issue(project)
