# jira-cli

This script creates a Jira issue, moves it onto the board, assigns it to me, and moves it to "In Progress".

## Setup
```
$ git clone https://github.com/Sebelino/jira-cli
$ cd jira-cli/
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ cp example.config.yaml config.yaml
```
Then [generate a personal Jira API token](https://id.atlassian.com/manage-profile/security/api-tokens) and edit `config.yaml` to suit your needs.

## Usage
Create an issue based on `config.yaml`:
```
$ ./create_issue.py
```
To use a different configuration file:
```
$ ./create_issue.py -c config_my_other_board.yaml
```
