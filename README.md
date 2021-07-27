# DealsPoster bot

This bot has been built as requested by u/DealsPoster on reddit

`docker-compose.yml`
```
version: '2.3'
services:
  DealsPoster:
    image: dgc1980/dealsposterbot:latest
    environment:
      REDDIT_USER: YOUR_REDDIT_BOT_USERNAMR
      REDDIT_PASS: YOUR_REDDIT_BOT_PASS
      REDDIT_CID: YOURCLIENTID
      REDDIT_SECRET: YOURSECRET
      REDDIT_SUBREDDIT: SubReddit
      EXPIRED_TRIGGER: "expired"
      EXPIRED_SCHEDULE: "set expiry"
      ## "mods" for mods only, "submitter" for submitter and mods, or "anyone" to allow anyone to set expiry(can be abused)
      EXPIRED_SCHEDULE_TYPE: "submitter"

      POST_REPLY="If this deal has expired, you can notify the moderators by replying to this comment with **EXPIRED** after 3 reports this deal will automatically be marked as expired."
    volumes:
      - ./dealsposter:/app/config
    restart: always
```
