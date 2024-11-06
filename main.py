import discord
from discord.ext import commands, tasks
import mysql.connector
from dotenv import load_dotenv
import os
import time
import datetime

from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract 
from mysql.connector.pooling import PooledMySQLConnection

load_dotenv()

PASSWORD = os.getenv("DATABASE_PASSWORD")
TOKEN = os.getenv("TOKEN")
if TOKEN == None:
    TOKEN = ""

intents = discord.Intents.all()

client = commands.Bot(command_prefix="$",intents=intents)

law_channel_id = 1300131141185175663
bill_channel_id = 1300147371971313856
presidents_office_id = 1302836640217305141
law_channel: discord.abc.Messageable | None = None
bill_channel: discord.abc.Messageable | None = None
presidents_office: discord.abc.Messageable | None = None
mydb: MySQLConnectionAbstract | PooledMySQLConnection | None = None
mycursor: MySQLCursorAbstract | None = None
guild: discord.Guild | None = None

@client.event
async def on_ready():
    global mydb
    global mycursor
    global guild
    global law_channel
    global bill_channel
    global presidents_office
    mydb = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = PASSWORD,
        database = "Electionbot"
    )
    mycursor = mydb.cursor()
    check_bills.start()
    check_election.start()
    guild = client.get_guild(1269805832145600533)
    if guild == None:
        raise Exception("No guild")
    law_channel_tmp = client.get_channel(law_channel_id)
    if not law_channel_tmp or not isinstance(law_channel_tmp,discord.abc.Messageable):
        law_channel = None
    else:
        law_channel = law_channel_tmp
    bill_channel_tmp = client.get_channel(bill_channel_id)
    if not bill_channel_tmp or not isinstance(bill_channel_tmp,discord.abc.Messageable):
        bill_channel = None
    else:
        bill_channel = bill_channel_tmp
    presidents_office_tmp = client.get_channel(presidents_office_id)
    if not presidents_office_tmp or not isinstance(presidents_office_tmp,discord.abc.Messageable):
        presidents_office = None
    else:
        presidents_office = presidents_office_tmp
    print(law_channel)
    print(bill_channel)
    print(presidents_office)
    #try:
        #synced = await client.tree.sync()
        #print(f"synced: {len(synced)}")
    #except Exception as e:
        #print(e)
    print("working")

def previous_president_id():
    if not mycursor or not mydb or not guild:
        return None
    mycursor.execute("SELECT previous_winner FROM Previous_winner")
    previous_president = mycursor.fetchone()
    if not previous_president:
        return None
    (previous_president,) = previous_president
    print(previous_president)
    if not previous_president:
        return None
    return int(str(previous_president))

def current_president_id():
    if not mycursor or not mydb or not guild:
        return None
    mycursor.execute("SELECT current_president FROM Current_president")
    current_president = mycursor.fetchone()
    if not current_president:
        return None
    (current_president,) = current_president
    return int(str(current_president))

def previous_president():
    if not mycursor or not mydb or not guild:
        return None
    mycursor.execute("SELECT previous_president FROM Previous_president")
    previous_president = mycursor.fetchone()
    if not previous_president:
        return None
    (previous_president,) = previous_president
    if previous_president == None:
        return None
    previous_president = guild.get_member(int(str(previous_president)))
    return previous_president

def current_president():
    if not mycursor or not mydb or not guild:
        return None
    mycursor.execute("SELECT current_president FROM Current_president")
    current_president = mycursor.fetchone()
    if not current_president:
        return None
    (current_president,) = current_president
    if current_president == None:
        return None
    current_president = guild.get_member(int(str(current_president)))
    return current_president

def is_running(name:str):
    if not mycursor or not mydb or not guild:
        return None
    mycursor.execute("SELECT * FROM Candidates WHERE name = %s",(name,))
    if len(mycursor.fetchall()) != 0:
        return True
    return False

def has_voted(name:str):
    if not mycursor or not mydb:
        return None
    mycursor.execute("SELECT id FROM Voters WHERE name = %s",(name,))
    if len(mycursor.fetchall()) != 0:
        return True
    return False

def inserted_id():
    if not mycursor or not mydb:
        return None
    mycursor.execute("SELECT LAST_INSERT_ID()")
    raw_id = mycursor.fetchone()
    if raw_id == None:
        return
    (id,) = raw_id
    return id

def bill_id_exists(bill_id:int):
    if not mycursor or not mydb:
        return None
    mycursor.execute("SELECT id FROM Bills WHERE id = %s",(bill_id,))
    if len(mycursor.fetchall()) == 0:
        return False
    return True

def voted_for_bill(name:str,bill_id:int):
    if not mycursor or not mydb:
        return None
    mycursor.execute("SElECT id FROM Bill_voters WHERE name = %s AND bill_id = %s",(name,bill_id))
    if len(mycursor.fetchall()) != 0:
        return True
    return False

def display_information(bill_id:int):
    if not mycursor or not mydb:
        return None
    mycursor.execute("SELECT bill,upvotes,downvotes,message_id FROM Bills WHERE id = %s",(bill_id,))
    raw_bill_info = mycursor.fetchone()
    return raw_bill_info

def president_display_information(bill_id:int):
    if not mycursor or not mydb:
        return None
    mycursor.execute("SELECT bill,message_id FROM President_bills WHERE id = %s",(bill_id,))
    raw_bill_info = mycursor.fetchone()
    return raw_bill_info
    
    
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
    if is_running(ctx.author.name):
        await ctx.send("You are already running")
        return
    previous_president_id_var = previous_president_id()
    current_president_id_var = current_president_id()
    if previous_president_id_var and current_president_id_var:
        if previous_president_id_var == current_president_id_var and previous_president_id_var == ctx.author.id:
            await ctx.send("You have already had 2 terms")
            return
    mycursor.execute("INSERT INTO Candidates (name,user_id) VALUES (%s,%s)",(ctx.author.name,ctx.author.id))
    mydb.commit()

@client.command()
async def unrun(ctx:commands.Context):
    if mycursor == None or mydb == None:
        return
    if not is_running(ctx.author.name):
        await ctx.send("You are not running")
        return
    mycursor.execute("DELETE FROM Candidates WHERE name = %s",(ctx.author.name,))
    mydb.commit()
    mycursor.execute("DELETE FROM Voters WHERE candidate = %s",(ctx.author.name,))
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
    if has_voted(ctx.author.name):
        await ctx.send("You have already voted")
        return
    if is_running(ctx.author.name):
        await ctx.send("You are a candidate")
        return
    if not is_running(username):
        await ctx.send("That user is not running")
        return
    mycursor.execute("UPDATE Candidates SET votes = votes + 1 WHERE name = %s",(username,))
    mydb.commit()
    mycursor.execute("INSERT INTO Voters (name,candidate) VALUES (%s)",(ctx.author.name,username))
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
    #bill_channel_id = 1300147371971313856
    #bill_channel = client.get_channel(bill_channel_id)
    if not isinstance(bill_channel,discord.abc.Messageable):
        return
    voting_time = 72
    if mycursor == None or mydb == None:
        return
    result_time = int(time.time()) + voting_time*3600
    mycursor.execute("INSERT INTO Bills (bill,upvotes,downvotes,result_time) VALUES (%s,0,0,%s)",(law,result_time))
    mydb.commit()
    id = inserted_id()
    bill_message = await bill_channel.send(f"Bill #{id}: {law} :arrow_up::0 :arrow_down::0 @everyone")
    mycursor.execute("UPDATE Bills SET message_id = %s WHERE id = %s",(bill_message.id,int(str(id))))
    mydb.commit()
    await interaction.response.send_message("Bill created!")

@client.command()
async def upvote(ctx:commands.Context,bill_id:int):
    if mycursor == None or mydb == None:
        return
    if not bill_id_exists(bill_id):
        await ctx.send("That bill doesn't exist")
        return
    if voted_for_bill(ctx.author.name,bill_id):
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
    if not bill_id_exists(bill_id):
        await ctx.send("That bill doesn't exist")
        return
    if voted_for_bill(ctx.author.name,bill_id):
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
    mycursor.execute("SELECT id FROM President_bills")
    for (bill_id,) in mycursor.fetchall():
        await update_president_bill(int(str(bill_id)))
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
    display_information_var = display_information(bill_id)
    if display_information_var == None:
        return
    (bill,upvotes,downvotes,message_id) = display_information_var
    new_message = f"Bill #{bill_id}: {bill} :arrow_up::{upvotes} :arrow_down::{downvotes} @everyone"
    bill_message = await bill_channel.fetch_message(int(str(message_id)))
    await bill_message.edit(content=new_message)

async def update_president_bill(bill_id):
    global presidents_office
    if not presidents_office:
        return
    if not mycursor or not mydb:
        return
    display_information_var = president_display_information(bill_id)
    if not display_information_var:
        return
    (bill,message_id) = display_information_var
    new_message = f"New Bill! #{bill_id}: {bill} <@&1299892838363824260>"
    bill_message = await presidents_office.fetch_message(int(str(message_id)))
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
    if not law_channel or not bill_channel or not presidents_office or \
    (not isinstance(law_channel,discord.abc.Messageable)) or (not isinstance(bill_channel,discord.abc.Messageable)) or (not isinstance(presidents_office,discord.abc.Messageable)) or not guild:
        print("channels doesn't exist")
        print(f"law channel: {law_channel}")
        print(f"bill channel: {bill_channel}")
        print(f"presidents_office: {presidents_office}")
        return
    print("checking bills")
    #get bills
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT id,bill,upvotes,downvotes,result_time,message_id FROM Bills")
    for (id,bill,upvotes,downvotes,result_time,message_id) in mycursor.fetchall():
        if time.time() >= int(str(result_time)):
            await bill_result(id,bill,upvotes,downvotes,message_id,presidents_office,bill_channel)
    #mycursor.execute("SELECT current_impeachment,upvotes,downvotes,result_time,message_id,president_id FROM Impeachment")
    #impeachment_info = mycursor.fetchone()
    #if not impeachment_info:
        #return
    #(current_impeachment,upvotes,downvotes,result_time,message_id,president_id) = impeachment_info
    #if int(str(current_impeachment)) == 0:
        #return
    #if int(str(upvotes)) < 2 * int(str(downvotes)):
        #president_member = guild.get_member(int(str(president_id)))
        #if not president_member:
            #return
        #impeachment_message = await bill_channel.fetch_message(int(str(message_id)))
        #await impeachment_message.delete()
        #await bill_channel.send(f"{president_member.mention} was not impeached")
    #else:
        
    
    

async def bill_result(bill_channel_id,bill,upvotes,downvotes,bill_channel_message_id,presidents_office,bill_channel:discord.abc.Messageable):
    if mycursor == None or mydb == None:
        return
    if int(str(upvotes)) >= int(str(downvotes)):
        #give president bill
        mycursor.execute("INSERT INTO President_bills (bill,bill_channel_message_id) VALUES (%s,%s)",(bill,bill_channel_message_id))
        mydb.commit()
        #get id
        id = inserted_id()
        #send to president
        presidents_office_bill_message = await presidents_office.send(f"New Bill! #{id}: {bill} <@&1299892838363824260>")
        #add message id
        mycursor.execute("UPDATE President_bills SET message_id = %s WHERE id = %s",(presidents_office_bill_message.id,int(str(id))))
        mydb.commit()
        bill_channel_message = await bill_channel.fetch_message(int(str(bill_channel_message_id)))
        await bill_channel_message.edit(content=f"{bill_channel_message.content} (waiting for presidential approval)")
    else:
        await bill_channel.send(f"Bill #{bill_channel_id} died")
        bill_channel_message = await bill_channel.fetch_message(int(str(bill_channel_message_id)))
        await bill_channel_message.delete()
    mycursor.execute("DELETE FROM Bill_voters WHERE bill_id = %s",(int(str(bill_channel_id)),))
    mydb.commit()
    mycursor.execute("DELETE FROM Bills WHERE id = %s",(int(str(bill_channel_id)),))
    mydb.commit()

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
    print("Checking election")
    if datetime.datetime.today().weekday() != 0:
        print("Not monday")
        return
    print("It's monday, starting...")
    await election()

async def election():
    global guild
    if guild == None:
        return
    if mycursor == None or mydb == None:
        print("database issue")
        return
    admin = guild.get_role(1299892838363824260)
    if admin == None:
        print("No admin")
        return

    winner = get_winner()
    if winner == None:
        return
    shift_back(winner)
    mycursor.execute("SELECT previous_winner FROM Previous_winner")
    previous_winner = mycursor.fetchone()
    if previous_winner == None:
        return
    (previous_winner,) = previous_winner
    if previous_winner:
        print(f"previous_winner:{previous_winner}")
        previous_winner = guild.get_member(int(str(previous_winner)))
        if previous_winner != None:
            await previous_winner.remove_roles(admin)
    await winner.add_roles(admin)
    mycursor.execute("DELETE FROM Candidates")
    mydb.commit()
    mycursor.execute("DELETE FROM Voters")
    mydb.commit()
    print("Election happened")

def shift_back(winner:discord.Member):
    if mycursor == None or mydb == None:
        print("database issue")
        return
    mycursor.execute("SELECT current_president FROM Current_president")
    current_president = mycursor.fetchone()
    print(current_president)
    print(str(current_president))
    if str(current_president) == "(None,)" or not current_president:
        mycursor.execute("UPDATE Previous_winner SET previous_winner = NULL")
        mydb.commit()
    else:
        (current_president,) = current_president
        mycursor.execute("UPDATE Previous_winner SET previous_winner = %s",(int(str(current_president)),))
        mydb.commit()
    mycursor.execute("UPDATE Current_president SET current_president = %s",(winner.id,))
    mydb.commit()
    print("shifted!")

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
        return None
    (top_votes,) = top_votes
    print(f"top_votes:{top_votes}")
    mycursor.execute("SELECT user_id FROM Candidates WHERE votes = %s",(str(top_votes),))
    candidate_ids = mycursor.fetchall()
    if len(candidate_ids) > 1:
        return None
    print(candidate_ids[0])
    (id,) = candidate_ids[0]
    return guild.get_member(int(str(id)))

@client.command()
async def manual_election(ctx:commands.Context):
    if ctx.author.id != 718151375967748098:
        await ctx.send("Nope")
    await election()

@client.command()
async def impeach(_:commands.Context):
    global bill_channel
    global guild
    if not mycursor or not mydb or not bill_channel or not isinstance(bill_channel,discord.abc.Messageable) or not guild:
        return
    mycursor.execute("SELECT current_president FROM Current_president")
    president = mycursor.fetchone()
    if president == None:
        return
    (president,) = president
    president = guild.get_member(int(str(president)))
    if not president:
        return
    impeach_message = await bill_channel.send(f"Impeach {president.mention}? :arrow_up::0 :arrow_down::0 @everyone")
    current_time = int(time.time())
    result_hours = 72
    result_time = current_time + result_hours * 3600
    mycursor.execute("UPDATE Impeachment SET current_impeachment = 1, upvotes = 0, downvotes = 0, result_time = %s, message_id = %s",(result_time,impeach_message.id))

client.run(TOKEN)
