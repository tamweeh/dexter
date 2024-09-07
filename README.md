# Deckster

Deckster is a Python package for collecting data from tweedeck. It also comes with a built-in flask app to controll adding and removing columns wihtout having to enteract with the browser running tweetdeck.

## Prerequisite
Active Twitter account that logs in without having to verify everytime.

## Requirements

```bash
pip install -r requirements.txt
```

## Usage
An example python file is included -> test_stream.py

```python
from stream import run

run.get_stream("TWITTER_USERNAME", "TWITTER_PASSOWRD")
```

# Flask App
Running this with your personal ip address and port will help controlling tweetdeck columns easier.
You will be able to show existing columns, add and remove columnms.
NOTE: Currently the maximum allowed column count is set to 5, to avoid too many request errors, which can occur.
