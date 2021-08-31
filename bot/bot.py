import sqlite3

import time
import praw
import prawcore
import requests

import logging
import re
import os
import datetime

import schedule
import dateparser

from numpy import loadtxt

reddit_cid = os.environ['REDDIT_CID']
reddit_secret = os.environ['REDDIT_SECRET']

reddit_user = os.environ['REDDIT_USER']
reddit_pass = os.environ['REDDIT_PASS']

reddit_subreddit = os.environ['REDDIT_SUBREDDIT']

EXPIRED_TRIGGER = os.environ['EXPIRED_TRIGGER']
AVAILABLE_TRIGGER = os.environ['AVAILABLE_TRIGGER']
EXPIRED_SCHEDULE = os.environ['EXPIRED_SCHEDULE']
EXPIRED_SCHEDULE_TYPE = os.environ['EXPIRED_SCHEDULE_TYPE']


DB_FILE = os.environ['DB_FILE']


POST_REPLY = os.environ['POST_REPLY']




post_footer = "\n\n^(**Note:** I am a bot. this action was performed automatically. Intentional abuse will likely result in a ban.)"

web_useragent = 'python:DealPosterBot (by dgc1980)'


reddit = praw.Reddit(client_id=reddit_cid,
                     client_secret=reddit_secret,
                     password=reddit_pass,
                     user_agent=web_useragent,
                     username=reddit_user)
subreddit = reddit.subreddit(reddit_subreddit)



apppath='/app/config/'

### for my local testing.
#apppath='./'


if not os.path.isfile(apppath+DB_FILE):
    con = sqlite3.connect(apppath+DB_FILE)
    cursorObj = con.cursor()
    cursorObj.execute("CREATE TABLE IF NOT EXISTS schedules(id integer PRIMARY KEY, postid text, schedtime integer)")
    con.commit()
    cursorObj.execute("CREATE TABLE IF NOT EXISTS expirecounter(id integer PRIMARY KEY, postid text, counter integer)")
    con.commit()
    cursorObj.execute("CREATE TABLE IF NOT EXISTS originalflair(id integer PRIMARY KEY, postid text, css text)")
    con.commit()


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=apppath+'affiliatebot.log',
                    filemode='a')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
os.environ['TZ'] = 'UTC'


def download(url, file_name):
    with open(file_name, "wb") as file:
        response = requests.get(url)
        file.write(response.content)



f = open(apppath+"submissionids.txt","a+")
f.close()
f = open(apppath+"messageids.txt","a+")
f.close()

def submissionID(postid):
    f = open(apppath+"submissionids.txt","a+")
    f.write(postid + "\n")
    f.close()

def messageID(postid):
    f = open(apppath+"messageids.txt","a+")
    f.write(postid + "\n")
    f.close()


def check_post(post):
   if post.created < int(time.time()) - 86400:
       return
   if post.title[0:1].lower() == "[" or post.title[0:1].lower() == "[":
       if post.id in open(apppath+'submissionids.txt').read():
           return
       donotprocess=False
       for top_level_comment in post.comments:
           try:
               if top_level_comment.author and top_level_comment.author.name == reddit_user:
                   submissionID(post.id)
                   break
           except AttributeError:
               pass
       else:
           if not donotprocess:
               comment = post.reply(POST_REPLY + post_footer)
               comment.mod.distinguish(sticky=True)

               tm = dateparser.parse( "in 30 days", settings={'PREFER_DATES_FROM': 'future', 'TIMEZONE': 'UTC', 'TO_TIMEZONE': 'UTC'} )
               tm2 = time.mktime( tm.timetuple() )

               con = sqlite3.connect(apppath+DB_FILE, timeout=20)
               cursorObj = con.cursor()
               cursorObj.execute('INSERT into schedules(postid, schedtime) values(?,?)',(msg.submission.id,tm2) )
               con.commit()
               con.close()

               submissionID(post.id)
               return

def check_message(msg):
    expired = False
    available = False
    setsched = False
    responded = 0
    try:
        if msg is None:
            return
        if isinstance(msg, praw.models.Comment):
            for comment in msg.refresh().replies:
                try:
                    if comment.author.name == reddit_username:
                        responded = 0
                except AttributeError:
                    responded = 0
        if msg.author is not None:
            logging.info("Message recieved from " + msg.author.name + ": " + msg.body)
            logging.info("* " + msg.submission.id + ": " + msg.submission.title)
    except AttributeError:
        if msg.author is not None:
            logging.info("error checking comment by: " + msg.author.name)


    if responded == 0:
            if isinstance(msg, praw.models.Comment):
                text = msg.body.lower()
                u = msg.author
            try:
                if text.index(EXPIRED_TRIGGER.lower()) > -1:
                    expired = True
            except ValueError:
                pass

            try:
                if text.index(AVAILABLE_TRIGGER.lower()) > -1:
                    available = True
            except ValueError:
                pass
    try:
        if text.index(EXPIRED_SCHEDULE.lower()) > -1:
            ismod= False
            for moderator in subreddit.moderator():
                if moderator.name == msg.submission.author.name:
                  ismod = True
            if msg.author.name == msg.submission.author.name or ismod and EXPIRED_SCHEDULE_TYPE.lower() == 'submitter':
                 setsched = True
            elif ismod and EXPIRED_SCHEDULE_TYPE.lower() == 'mods':
                 setsched = True
            elif EXPIRED_SCHEDULE_TYPE.lower() == 'anyone':
                setsched = True
    except:
        pass
#### Error checking to make sure people are not calling the bot via "u/BOTNAME EXPIRED" to trigger the bot and make it crash
    if msg.submission.subreddit != subreddit:
        setsched = False
        expired = False
        logging.info("abuse https://redd.id/" + msg.submission.id + " by: "+msg.author.name)
        msg.mark_read()
####
    if setsched:
        if re.search("(\d{1,2}:\d{2} \d{2}\/\d{2}\/\d{4})", text) is not None:
            con = sqlite3.connect(apppath+DB_FILE, timeout=20)
            match1 = re.search("(\d{1,2}:\d{2} \d{2}\/\d{2}\/\d{4})", text)
            tm = datetime.datetime.strptime(match1.group(1), "%H:%M %d/%m/%Y")
            tm2 = time.mktime(tm.timetuple())
            cursorObj = con.cursor()
            cursorObj.execute('DELETE from schedules WHERE postid = ' + msg.submission.id)
            cursorObj.execute('INSERT into schedules(postid, schedtime) values(?,?)',(msg.submission.id,tm2) )
            con.commit()
            con.close()
            logging.info("setting up schedule: " + msg.author.name + "for https://redd.it/" + msg.submission.id + " at " + str(tm.strftime('%Y-%m-%d %H:%M:%S'))  )
            myreply = msg.reply("This deal has been scheduled to expire as requested by /u/"+msg.author.name+". at " + str(tm.strftime('%Y-%m-%d %H:%M:%S')) + " UTC" + post_footer).mod.distinguish(how='yes')
            msg.mark_read()
        else:
            match1 = re.search("set expiry\ ([\w\:\ \-\+]+)", text)
            tm = dateparser.parse( match1.group(1), settings={'PREFER_DATES_FROM': 'future', 'TIMEZONE': 'UTC', 'TO_TIMEZONE': 'UTC'} )
            tm2 = time.mktime( tm.timetuple() )
            con = sqlite3.connect(apppath+DB_FILE, timeout=20)
            cursorObj = con.cursor()
            cursorObj.execute('DELETE from schedules WHERE postid = ' + msg.submission.id)
            cursorObj.execute('INSERT into schedules(postid, schedtime) values(?,?)',(msg.submission.id,tm2) )
            con.commit()
            con.close()
            logging.info("setting up schedule: " + msg.author.name + "for https://redd.it/" + msg.submission.id + " at " + str(tm.strftime('%Y-%m-%d %H:%M:%S'))  )
            myreply = msg.reply("This deal has been scheduled to expire as requested by /u/"+msg.author.name+". at " + str(tm.strftime('%Y-%m-%d %H:%M:%S')) + " UTC" + post_footer).mod.distinguish(how='yes')
            msg.mark_read()
    elif available:
        if msg.submission.link_flair_text is not None and "expired:" in msg.submission.link_flair_text.lower():
            new_flair = ""
            try:
              new_flair = msg.submission.link_flair_text.replace("Expired: ","")
            except:
              pass
            con = sqlite3.connect(apppath+DB_FILE, timeout=20)
            cursorObj = con.cursor()
            cursorObj.execute('SELECT * FROM originalflair WHERE postid = "'+msg.submission.id+'"')
            rows = cursorObj.fetchall()
            css_class = ""
            if len(rows) != 0:
              css_class = rows[0][2]
            if new_flair == "" or new_flair == "Expired:":
              msg.submission.mod.flair(text='',css_class=css_class)
            else:
              msg.submission.mod.flair(text=new_flair,css_class=css_class)
            msg.submission.mod.unspoiler()
            myreply = msg.reply("Deal is available again.\n\nIf this deal has expired or sold out, you can reply to this comment with `expired`.").mod.distinguish(how='yes')

            msg.mark_read()

        else:
            myreply = msg.reply("This deal is already been marked as avilable.  We use flairs and spoilers to distinguish deals that are expired.").mod.distinguish(how='yes')
            msg.mark_read()
            logging.info("already expired... responded to: " + msg.author.name)
    elif expired:
        if msg.submission.link_flair_text is not None and "expired:" in msg.submission.link_flair_text.lower():
            myreply = msg.reply("This deal has already been marked expired.  We use flairs and spoilers to distinguish deals that are expired.").mod.distinguish(how='yes')
            msg.mark_read()
            logging.info("already expired... responded to: " + msg.author.name)
        else:
            new_flair = "Expired:"
            try:
              new_flair = "Expired: " + msg.submission.link_flair_text
            except:
              pass

            con = sqlite3.connect(apppath+DB_FILE, timeout=20)
            cursorObj = con.cursor()
            cursorObj.execute('DELETE FROM originalflair WHERE postid = "'+msg.submission.id+'"')
            cursorObj.execute('INSERT into originalflair (postid, css) VALUES(?,?)', (msg.submission.id,msg.submission.link_flair_css_class))
            con.commit()
            con.close()
            msg.submission.mod.flair(text=new_flair,css_class="expired")
            msg.submission.mod.spoiler()

            myreply = msg.reply("Deal has been marked expired.\n\nIf this was a mistake, please reply with `available`.").mod.distinguish(how='yes')
            msg.mark_read()

def run_schedule():
  tm = str(int(time.time()))
  con = sqlite3.connect(apppath+DB_FILE)
  cursorObj = con.cursor()
  cursorObj.execute('SELECT * FROM schedules WHERE schedtime <= ' + tm + ';')
  rows = cursorObj.fetchall()
  if len(rows) > 0:
    for row in rows:
      if reddit.submission(row[1]).removed_by_category != "None":
        logging.info("running schedule on https://reddit.com/" + row[1])
        new_flair = "Expired:"
        submission = reddit.submission(row[1])
        try:
            new_flair = "Expired: " + submission.link_flair_text
        except:
            pass
        old_flair = ""
        try:
            old_flair = submission.link_flair_text.lower()
        except:
            pass

        try:
            if "expired:" in old_flair:
                logging.info("this submission has already been marked expired")
            else:
                con = sqlite3.connect(apppath+DB_FILE, timeout=20)
                cursorObj = con.cursor()
                cursorObj.execute('DELETE FROM originalflair WHERE postid = "'+msg.submission.id+'"')
                cursorObj.execute('INSERT into originalflair (postid, css) VALUES(?,?)', (submission.id,submission.link_flair_css_class))
                con.commit()
                con.close()
                submission.mod.flair(text=new_flair)
                submission.mod.spoiler()
        except:
          submission.mod.flair(text=new_flair,css_class="expired")
          submission.mod.spoiler()

        cursorObj.execute('DELETE FROM schedules WHERE postid = "'+ row[1]+'"')
        con.commit()
  con.close();


run_schedule()
schedule.every(1).minutes.do(run_schedule)
logging.info("bot initialized...." )
while True:
  schedule.run_pending()
  try:
    logging.debug("checking messages")
    for msg in reddit.inbox.stream(pause_after=-1):
        if msg is None:
            break
        if msg.id in open(apppath+'messageids.txt').read():
          continue
        check_message(msg)
    logging.debug("checking submissions")
    for post in subreddit.stream.submissions(pause_after=-1):
        if post is None:
            break
        if post.id in open(apppath+'submissionids.txt').read():
          continue
        check_post(post)
  except (prawcore.exceptions.RequestException, prawcore.exceptions.ResponseException):
    logging.info("Error connecting to reddit servers. Retrying in 30 seconds...")
    time.sleep(30)



