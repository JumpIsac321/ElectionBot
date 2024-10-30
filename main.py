import discord
from discord.ext import commands, tasks
import mysql.connector
from dotenv import load_dotenv
import os
import time
import datetime
import random

from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from mysql.connector.pooling import PooledMySQLConnection

load_dotenv()

PASSWORD = os.getenv("DATABASE_PASSWORD")
TOKEN = os.getenv("TOKEN")
if TOKEN == None:
    TOKEN = ""

intents = discord.Intents.all()

client = commands.Bot(command_prefix="$",intents=intents)

guild = client.get_guild(1269805832145600533)
if guild == None:
    raise Exception("No guild")


law_channel_id = 1300131141185175663
bill_channel_id = 1300147371971313856
presidents_office_id = 0
law_channel = client.get_channel(law_channel_id)
bill_channel = client.get_channel(bill_channel_id)
presidents_office = client.get_channel(presidents_office_id)

mydb: MySQLConnectionAbstract | PooledMySQLConnection | None = None
mycursor: MySQLCursorAbstract | None = None

@client.event
async def on_ready():
    global mydb
    global mycursor
    mydb = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = PASSWORD,
        database = "Electionbot"
    )
    mycursor = mydb.cursor()
    check_bills.start()
    check_election.start()
    #try:
        #synced = await client.tree.sync()
        #print(f"synced: {len(synced)}")
    #except Exception as e:
        #print(e)
    print("working")

@client.command()
async def hello(ctx):
    await ctx.send("hi")

@client.command()
async def get_members(ctx:commands.Context):
    #testing: 1277053200528052316
    #main: 1297301010934403124
    guild = ctx.guild
    if guild == None:
        return
    members = guild.members
    for member in members:
        if not member.bot:
            await ctx.send(member.name)

@client.command()
async def run(ctx:commands.Context):
    global mycursor
    global mydb
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT * FROM Candidates WHERE name = %s",(ctx.author.name,))
    if len(mycursor.fetchall()) != 0:
        await ctx.send("You are already running")
        return
    mycursor.execute("INSERT INTO Candidates (name,user_id) VALUES (%s,%s)",(ctx.author.name,ctx.author.id))
    mydb.commit()

@client.command()
async def unrun(ctx:commands.Context):
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT * FROM Candidates WHERE name = %s",(ctx.author.name,))
    if len(mycursor.fetchall()) == 0:
        await ctx.send("You are not running")
        return
    mycursor.execute("DELETE FROM Candidates WHERE name = %s",(ctx.author.name,))
    mydb.commit()

def s(input:int):
    if input == 1:
        return ""
    return "s"

@client.command()
async def candidates(ctx:commands.Context):
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT name, votes FROM Candidates")
    candidates = mycursor.fetchall()
    candidates_str = ""
    for (candidate,votes) in candidates:
        candidates_str += f"{candidate}: {votes} vote{s(int(str(votes)))}\n"
    if candidates_str == "":
        await ctx.send("There are currently no candidates")
        return
    await ctx.send(candidates_str)

@client.command()
async def vote(ctx:commands.Context,vote:discord.User):
    if mycursor == None or mydb == None:
        return
    username = vote.name
    mycursor.execute("SELECT id FROM Voters WHERE name = %s",(ctx.author.name,))
    if len(mycursor.fetchall()) != 0:
        await ctx.send("You already voted")
        return
    mycursor.execute("SELECT id FROM Candidates WHERE name = %s",(ctx.author.name,))
    if len(mycursor.fetchall()) != 0:
        await ctx.send("You are a candidate")
        return
    mycursor.execute("SELECT id FROM Candidates WHERE name = %s",(username,))
    if len(mycursor.fetchall()) == 0:
        await ctx.send("That user is not running")
        return
    mycursor.execute("UPDATE Candidates SET votes = votes + 1 WHERE name = %s",(username,))
    mycursor.execute("INSERT INTO Voters (name) VALUES (%s)",(ctx.author.name,))
    mydb.commit()
    await ctx.send("Voted!")

@client.command()
async def top_candidate(ctx:commands.Context):
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT votes FROM Candidates ORDER BY votes DESC LIMIT 1")
    top_votes_raw = mycursor.fetchone()
    if top_votes_raw == None:
        await ctx.send("No candidates")
        return
    (top_votes,) = top_votes_raw
    mycursor.execute("SELECT name FROM Candidates WHERE votes = %s",(str(top_votes),))
    candidates_str = ""
    for (candidate,) in mycursor.fetchall():
        candidates_str += f"{candidate}\n"
    await ctx.send(candidates_str)

#@client.tree.command()
#async def testing(interactions:discord.Interaction):
    #await interactions.response.send_message("tested")


@client.tree.command()
async def create_bill(interaction:discord.Interaction, law:str):
    #law_channel = 1300131141185175663 
    bill_channel_id = 1300147371971313856
    bill_channel = client.get_channel(bill_channel_id)
    if not isinstance(bill_channel,discord.abc.Messageable):
        return
    voting_time = 72
    if mycursor == None or mydb == None:
        return
    result_time = int(time.time()) + voting_time*3600
    mycursor.execute("INSERT INTO Bills (bill,upvotes,downvotes,result_time) VALUES (%s,0,0,%s)",(law,result_time))
    mydb.commit()
    mycursor.execute("SELECT LAST_INSERT_ID()")
    raw_id = mycursor.fetchone()
    if raw_id == None:
        return
    (id,) = raw_id
    bill_message = await bill_channel.send(f"Bill #{id}: {law} :arrow_up::0 :arrow_down::0 @everyone")
    mycursor.execute("UPDATE Bills SET message_id = %s WHERE id = %s",(bill_message.id,int(str(id))))
    mydb.commit()
    await interaction.response.send_message("Bill created!")

@client.command()
async def upvote(ctx:commands.Context,bill_id:int):
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT id FROM Bills WHERE id = %s",(bill_id,))
    if len(mycursor.fetchall()) == 0:
        await ctx.send("That bill doesn't exist")
        return
    mycursor.execute("SElECT id FROM Bill_voters WHERE name = %s AND bill_id = %s",(ctx.author.name,bill_id))
    if len(mycursor.fetchall()) != 0:
        await ctx.send("You already voted for this bill")
        return
    mycursor.execute("UPDATE Bills SET upvotes = upvotes + 1 WHERE id = %s",(bill_id,))
    mydb.commit()
    mycursor.execute("INSERT INTO Bill_voters (name,bill_id) VALUES (%s,%s)",(ctx.author.name,bill_id))
    mydb.commit()
    await update_bill(bill_id)

@client.command()
async def downvote(ctx:commands.Context,bill_id:int):
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT id FROM Bills WHERE id = %s",(bill_id,))
    if len(mycursor.fetchall()) == 0:
        await ctx.send("That bill doesn't exist")
        return
    mycursor.execute("SElECT id FROM Bill_voters WHERE name = %s AND bill_id = %s",(ctx.author.name,bill_id))
    if len(mycursor.fetchall()) != 0:
        await ctx.send("You already voted for this bill")
        return
    mycursor.execute("UPDATE Bills SET downvotes = downvotes + 1 WHERE id = %s",(bill_id,))
    mydb.commit()
    mycursor.execute("INSERT INTO Bill_voters (name,bill_id) VALUES (%s,%s)",(ctx.author.name,bill_id))
    mydb.commit()
    await update_bill(bill_id)

@client.command()
async def update_bills(ctx:commands.Context):
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT id FROM Bills")
    for (bill_id,) in mycursor.fetchall():
        await update_bill(int(str(bill_id)))
    await ctx.send("Updated!")

async def update_bill(bill_id):
    bill_channel_id = 1300147371971313856
    bill_channel = client.get_channel(bill_channel_id)
    if bill_channel == None:
        return
    if not isinstance(bill_channel,discord.abc.Messageable):
        return
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT bill,upvotes,downvotes,message_id FROM Bills WHERE id = %s",(bill_id,))
    raw_bill_info = mycursor.fetchone()
    if raw_bill_info == None:
        return
    (bill,upvotes,downvotes,message_id) = raw_bill_info
    new_message = f"Bill #{bill_id}: {bill} :arrow_up::{upvotes} :arrow_down::{downvotes} @everyone"
    bill_message = await bill_channel.fetch_message(int(str(message_id)))
    await bill_message.edit(content=new_message)

@client.command()
async def bills(ctx:commands.Context):
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT id,bill FROM Bills")
    bills_str = ""
    for (id,bill) in mycursor.fetchall():
        bills_str += f"{id}: {bill}\n"
    await ctx.send(bills_str)

@client.command()
async def sync(ctx):
    print("sync command")
    if ctx.author.id == 718151375967748098:
        synced = await client.tree.sync()
        await ctx.send(f'Command tree synced. {len(synced)}')
    else:
        await ctx.send('You must be the owner to use this command!')

@tasks.loop(minutes=5)
async def check_bills():
    global law_channel
    global bill_channel
    global presidents_office
    if law_channel == None or bill_channel == None or presidents_office == None or \
    (not isinstance(law_channel,discord.abc.Messageable)) or (not isinstance(bill_channel,discord.abc.Messageable)) or (not isinstance(presidents_office,discord.abc.Messageable)):
        return
    print("checking bills")
    #get bills
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT id,bill,upvotes,downvotes,result_time,message_id FROM Bills")
    for (id,bill,upvotes,downvotes,result_time,message_id) in mycursor.fetchall():
        if time.time() >= int(str(result_time)):
            await bill_result(id,bill,upvotes,downvotes,message_id,presidents_office,bill_channel)

async def bill_result(bill_channel_id,bill,upvotes,downvotes,bill_channel_message_id,presidents_office,bill_channel:discord.abc.Messageable):
    if mycursor == None or mydb == None:
        return
    if int(str(upvotes)) >= int(str(downvotes)):
        #give president bill
        mycursor.execute("INSERT INTO President_bills (bill,bill_channel_message_id) VALUES (%s)",(bill,bill_channel_message_id))
        mydb.commit()
        #get id
        mycursor.execute("SELECT LAST_INSERT_ID()")
        raw_id = mycursor.fetchone()
        if raw_id == None:
            return
        (presidents_office_id,) = raw_id
        #send to president
        presidents_office_bill_message = await presidents_office.send(f"New Bill! #{presidents_office_id}: {bill} <@&1299892838363824260>")
        #add message id
        mycursor.execute("UPDATE President_bills SET message_id = %s WHERE id = %s",(presidents_office_bill_message.id,int(str(id))))
        mydb.commit()
        bill_channel_message = await bill_channel.fetch_message(int(str(bill_channel_message_id)))
        await bill_channel_message.edit(content=f"{bill_channel_message.content} (waiting for presidential approval)")
    else:
        await bill_channel.send(f"Bill #{bill_channel_id} died")
        bill_channel_message = await bill_channel.fetch_message(int(str(bill_channel_message_id)))
        await bill_channel_message.delete()
    mycursor.execute("DELETE FROM Bills WHERE id = %s",(int(str(bill_channel_id)),))

@client.command()
async def approve(ctx:commands.Context,bill_id:int):
    law_channel_id = 1300131141185175663
    law_channel = client.get_channel(law_channel_id)
    bill_channel_id = 1300147371971313856
    bill_channel = client.get_channel(bill_channel_id)
    if law_channel == None or bill_channel == None or (not isinstance(law_channel,discord.abc.Messageable)) or (not isinstance(bill_channel,discord.abc.Messageable)):
        return
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT id,bill FROM President_bills WHERE id = %s",(bill_id,))
    raw_bill = mycursor.fetchone()
    if raw_bill == None:
        await ctx.send("That bill doesn't exist")
        return
    (_,bill) = raw_bill
    await law_channel.send(f"{bill}")
    mycursor.execute("SELECT bill_channel_message_id FROM President_bills WHERE id = %s",(bill_id,))
    raw_bill_id = mycursor.fetchone()
    if raw_bill_id == None:
        return
    (bill_channel_message_id,) = raw_bill_id
    bill_channel_message = await bill_channel.fetch_message(int(str(bill_channel_message_id)))
    await bill_channel_message.delete()
    mycursor.execute("DELETE FROM President_bills WHERE id = %s",(bill_id,))
    mydb.commit()

@client.command()
async def veto(ctx:commands.Context,bill_id:int):
    law_channel_id = 1300131141185175663
    law_channel = client.get_channel(law_channel_id)
    bill_channel_id = 1300147371971313856
    bill_channel = client.get_channel(bill_channel_id)
    if law_channel == None or bill_channel == None or (not isinstance(law_channel,discord.abc.Messageable)) or (not isinstance(bill_channel,discord.abc.Messageable)):
        return
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT id FROM President_bills WHERE id = %s",(bill_id,))
    raw_id = mycursor.fetchone()
    if raw_id == None:
        await ctx.send("That bill doesn't exist")
        return
    mycursor.execute("SELECT bill_channel_message_id FROM President_bills WHERE id = %s",(bill_id,))
    raw_bill_id = mycursor.fetchone()
    if raw_bill_id == None:
        return
    (bill_channel_message_id,) = raw_bill_id
    bill_channel_message = await bill_channel.fetch_message(int(str(bill_channel_message_id)))
    await bill_channel_message.delete()
    mycursor.execute("DELETE FROM President_bills WHERE id = %s",(bill_id,))
    mydb.commit()
    await bill_channel.send(f"Bill #{bill_channel_id} was vetoed")

@tasks.loop(time=datetime.time(hour=23,tzinfo=datetime.timezone.utc))
async def check_election():
    global guild
    if guild == None:
        return
    if mycursor == None or mydb == None:
        print("database issue")
        return
    print("Checking election")
    if datetime.datetime.today().weekday() != 0:
        print("Not monday")
        return
    print("It's monday, starting...")



    admin = guild.get_role(1299892838363824260)
    if admin == None:
        print("No admin")
        return
    mycursor.execute("SELECT previous_winner FROM Previous_winner")
    previous_winner = mycursor.fetchone()
    if previous_winner == None:
        return
    (previous_winner,) = previous_winner
    previous_winner = guild.get_member(int(str(previous_winner)))
    if previous_winner != None:
        await previous_winner.remove_roles(admin)
    await winner.add_roles(admin)

def get_winner():
    global guild
    if guild == None:
        return
    if mycursor == None or mydb == None:
        print("database issue")
        return



    mycursor.execute("SELECT votes FROM Candidates ORDER BY votes DESC LIMIT 1")
    top_votes = mycursor.fetchone()
    if top_votes == None:
        print("No candidates")
        return
    (top_votes,) = top_votes
    print(f"top_votes:{top_votes}")
    mycursor.execute("SELECT user_id FROM Candidates WHERE votes = %s",(str(top_votes),))
    candidate_ids = mycursor.fetchall()
    if len(candidate_ids) > 1:
        return
    return guild.get_member(int(str(candidate_ids[0])))

    

@client.command()
async def manual_election(ctx:commands.Context):
    if ctx.author.id != 718151375967748098:
        await ctx.send("Nope")
    await check_election()

client.run(TOKEN)
