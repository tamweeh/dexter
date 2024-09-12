# Dexter

This is a Python package for collecting data from tweedeck. The app will act as a watcher that opens the tweetdeck page and listens to the backend requests that are automatically are made by X. Whenever the endpoint that gets posts is present it will be collected and sent to the desired destination (***Kafka*** in this case)

A supporting FastAPI app will be needed to control the columns and queries. 

## Prerequisite
Active X pro account (preferably one that logs in without having to verify everytime).

## Requirements

```bash
pip install -r requirements.txt
```

## Usage
Add user credentials (username, password, and email) to the .env file
```
# User Credentials
USER=falangebeaver
PASSWORD=FriendsRules#1994
EMAIL=falangebeaverhausen@gmail.com
```
Add redis configuration to store user header sessions
```
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```
Then run the python script
```bash
python main.py
```

## Using Docker
example build
```bash
docker build -t dexter:1.0 .
```
example run
```bash
docker run -d --name=dexter dexter:1.0
```