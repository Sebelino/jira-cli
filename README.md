# jira-cli

This script creates a Jira issue, moves it onto the board, assigns it to me, and moves it to "In Progress".

## Setup
```
$ cp example.config.yaml config.yaml
```
Then [generate a personal Jira API token](https://id.atlassian.com/manage-profile/security/api-tokens) and edit `config.yaml` to suit your needs.

## Usage
```
$ ./create_issue.py
```
