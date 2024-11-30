import discord
from discord.abc import Messageable
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
constitution_id = 1306801660206649400
law_channel: discord.abc.Messageable | None = None
bill_channel: discord.abc.Messageable | None = None
presidents_office: discord.abc.Messageable | None = None
constitution: discord.abc.Messageable | None = None
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
    global constitution
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
    constitution_tmp = client.get_channel(constitution_id)
    if not constitution_tmp or not isinstance(constitution_tmp,discord.abc.Messageable):
        constitution = None
    else:
        constitution = constitution_tmp
    print(law_channel)
    print(bill_channel)
    print(presidents_office)
    #try:
        #synced = await client.tree.sync()
        #print(f"synced: {len(synced)}")
    #except Exception as e:
        #print(e)
    print("working")

#previous president
def previous_president_id():
    if not mycursor or not mydb or not guild:
        return None
    mycursor.execute("SELECT previous_winner FROM Previous_winner")
    previous_president = mycursor.fetchone()
    if not previous_president:
        return None
    (previous_president,) = previous_president
    if not previous_president:
        return None
    return int(str(previous_president))

def previous_president():
    if not mycursor or not mydb or not guild:
        return None
    mycursor.execute("SELECT previous_winner FROM Previous_winner")
    previous_president = mycursor.fetchone()
    if not previous_president:
        return None
    (previous_president,) = previous_president
    if previous_president == None:
        return None
    previous_president = guild.get_member(int(str(previous_president)))
    return previous_president

def set_previous_president(id: int):
    if not mycursor or not mydb:
        return None
    mycursor.execute("UPDATE Previous_winner SET previous_winner = %s",(id,))
    mydb.commit()

#current president

def get_current_president():
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

def current_president_id():
    if not mycursor or not mydb or not guild:
        return None
    mycursor.execute("SELECT current_president FROM Current_president")
    current_president = mycursor.fetchone()
    if not current_president:
        return None
    (current_president,) = current_president
    return int(str(current_president))

def set_current_president(id: int):
    if not mycursor or not mydb:
        return None
    mycursor.execute("UPDATE Current_president SET current_president = %s",(id,))
    mydb.commit()

#bill_voters
def add_to_bill_voters(name:str,bill_id:int):
    if not mycursor or not mydb:
        return
    mycursor.execute("INSERT INTO Bill_voters (name,bill_id) VALUES (%s,%s)",(name,bill_id))
    mydb.commit()

def voted_for_bill(name:str,bill_id:int):
    if not mycursor or not mydb:
        return None
    mycursor.execute("SElECT id FROM Bill_voters WHERE name = %s AND bill_id = %s",(name,bill_id))
    if len(mycursor.fetchall()) != 0:
        return True
    return False

#bills
async def add_bill(bill:str,channel:Messageable,result_time:int,is_amendment:bool):
    if mycursor == None or mydb == None:
        return
    if is_amendment:
        mycursor.execute("INSERT INTO Bills (bill,upvotes,downvotes,result_time,is_amendment) VALUES (%s,0,0,%s,1)",(bill,result_time))
    else:
        mycursor.execute("INSERT INTO Bills (bill,upvotes,downvotes,result_time,is_amendment) VALUES (%s,0,0,%s,0)",(bill,result_time))
    mydb.commit()
    id = inserted_id()
    if is_amendment:
        bill_message = await channel.send(f"Amendment #{id}: {bill} :arrow_up::0 :arrow_down::0 @everyone")
    else:
        bill_message = await channel.send(f"Bill #{id}: {bill} :arrow_up::0 :arrow_down::0 @everyone")
    mycursor.execute("UPDATE Bills SET message_id = %s WHERE id = %s",(bill_message.id,int(str(id))))
    mydb.commit()

def remove_bill(bill_id:int):
    if not mycursor or not mydb:
        return
    mycursor.execute("DELETE FROM Bills WHERE id = %s",(bill_id,))
    mydb.commit()

def upvote_bill(bill_id:int):
    if not mycursor or not mydb:
        return
    mycursor.execute("UPDATE Bills SET upvotes = upvotes + 1 WHERE id = %s",(bill_id,))
    mydb.commit()

def downvote_bill(bill_id:int):
    if not mycursor or not mydb:
        return
    mycursor.execute("UPDATE Bills SET downvotes = downvotes + 1 WHERE id = %s",(bill_id,))
    mydb.commit()

def bill_display_information(bill_id:int):
    if not mycursor or not mydb:
        return None
    mycursor.execute("SELECT bill,upvotes,downvotes,message_id FROM Bills WHERE id = %s",(bill_id,))
    raw_bill_info = mycursor.fetchone()
    return raw_bill_info

def bill_id_exists(bill_id:int):
    if not mycursor or not mydb:
        return None
    mycursor.execute("SELECT id FROM Bills WHERE id = %s",(bill_id,))
    if len(mycursor.fetchall()) == 0:
        return False
    return True

#candidates
def add_candidate(name:str,id:int):
    if mycursor == None or mydb == None:
        return
    mycursor.execute("INSERT INTO Candidates (name,user_id) VALUES (%s,%s)",(name,id))
    mydb.commit()

def remove_candidate(name:str):
    if mycursor == None or mydb == None:
        return
    mycursor.execute("DELETE FROM Candidates WHERE name = %s",(name,))
    mydb.commit()

def is_running(name:str):
    if not mycursor or not mydb or not guild:
        return None
    mycursor.execute("SELECT * FROM Candidates WHERE name = %s",(name,))
    if len(mycursor.fetchall()) != 0:
        return True
    return False

def vote_president(name:str):
    if not mycursor or not mydb:
        return
    mycursor.execute("UPDATE Candidates SET votes = votes + 1 WHERE name = %s",(name,))
    mydb.commit()

def unvote_president(candidate_id:int):
    if not mycursor or not mydb:
        return
    mycursor.execute("UPDATE Candidates SET votes = votes - 1 WHERE user_id = %s",(candidate_id,))
    mydb.commit()

#president_bills
async def add_president_bill(bill:str,original_message_id:int,original_id:int,channel):
    if not mycursor or not mydb or not guild:
        return None
    mycursor.execute("INSERT INTO Bills (bill,bill_channel_message_id,original_id) VALUES (%s,0,0,%s)",(bill,original_message_id,original_id))
    mydb.commit()
    id = inserted_id()
    bill_message = await channel.send(f"Bill #{id}: {bill} :arrow_up::0 :arrow_down::0 @everyone")
    mycursor.execute("UPDATE Bills SET message_id = %s WHERE id = %s",(bill_message.id,int(str(id))))
    mydb.commit()

async def remove_president_bill(bill_id:int):
    if not mycursor or not mydb:
        return
    mycursor.execute("DELETE FROM President_bills WHERE id = %s",(bill_id,))
    mydb.commit()

def president_display_information(bill_id:int):
    if not mycursor or not mydb:
        return None
    mycursor.execute("SELECT bill,message_id FROM President_bills WHERE id = %s",(bill_id,))
    raw_bill_info = mycursor.fetchone()
    return raw_bill_info

#voters
def has_voted(name:str):
    if not mycursor or not mydb:
        return None
    mycursor.execute("SELECT id FROM Voters WHERE name = %s",(name,))
    if len(mycursor.fetchall()) != 0:
        return True
    return False


def add_to_voters(name:str,vote_id:int):
    if not mycursor or not mydb:
        return
    mycursor.execute("INSERT INTO Voters (name,candidate_id) VALUES (%s,%s)",(name,vote_id))
    mydb.commit()

def remove_from_voters(name:str):
    if not mycursor or not mydb:
        return
    mycursor.execute("DELETE FROM Voters WHERE name = %s",(name,))
    mydb.commit()

#impeachment
def get_impeachment():
    if not mycursor or not mydb:
        return
    mycursor.execute("SELECT current_impeachment,upvotes,downvotes,result_time,message_id,president_id FROM Impeachment")
    impeachment_info = mycursor.fetchone()
    if not impeachment_info:
        return None
    (current_impeachment,upvotes,downvotes,result_time,message_id,president_id) = impeachment_info
    if int(str(current_impeachment)) == 0:
        return None
    return (upvotes,downvotes,result_time,message_id,president_id)

def stop_impeachment():
    if not mycursor or not mydb:
        return
    mycursor.execute("UPDATE Impeachment SET upvotes = 0, downvotes = 0, result_time = NULL, message_id = NULL, current_impeachment = 0, president_id = NULL")
    mydb.commit()

def upvote_impeachment():
    if not mycursor or not mydb:
        return
    mycursor.execute("UPDATE Impeachment SET upvotes = upvotes + 1")

def downvote_impeachment():
    if not mycursor or not mydb:
        return
    mycursor.execute("UPDATE Impeachment SET downvotes = downvotes + 1")

#next_election_time
def get_election_time():
    if not mycursor or not mydb:
        return
    mycursor.execute("SELECT time FROM Next_election_time")
    time = mycursor.fetchone()
    if not time:
        return
    (time,) = time
    if time:
        return int(str(time))
    return None

def set_election_time(time:int):
    if not mycursor or not mydb:
        return
    mycursor.execute("UPDATE Next_election_time SET time = %s",(time,))
    mydb.commit()

def inserted_id():
    if not mycursor or not mydb:
        return None
    mycursor.execute("SELECT LAST_INSERT_ID()")
    raw_id = mycursor.fetchone()
    if raw_id == None:
        return
    (id,) = raw_id
    return id

def had_two_terms(id:int):
    previous_president_id_var = previous_president_id()
    current_president_id_var = current_president_id()
    if previous_president_id_var and current_president_id_var and \
        previous_president_id_var == current_president_id_var and previous_president_id_var == id:
            return True
    return False

def clear_candidates():
    if not mycursor or not mydb:
        return None
    mycursor.execute("DELETE FROM Candidates")
    mydb.commit()

def clear_voters():
    if not mycursor or not mydb:
        return None
    mycursor.execute("DELETE FROM Voters")
    mydb.commit()

@client.command()
async def run(ctx:commands.Context):
    if is_running(ctx.author.name):
        await ctx.send("You are already running")
        return
    if had_two_terms(ctx.author.id):
        await ctx.send("You have already had 2 terms")
    add_candidate(ctx.author.name,ctx.author.id)

@client.command()
async def unrun(ctx:commands.Context):
    if not is_running(ctx.author.name):
        await ctx.send("You are not running")
        return
    remove_candidate(ctx.author.name)

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
    if has_voted(ctx.author.name):
        await ctx.send("You have already voted")
        return
    if is_running(ctx.author.name):
        await ctx.send("You are a candidate")
        return
    if not is_running(vote.name):
        await ctx.send("That user is not running")
        return
    vote_president(vote.name)
    add_to_voters(ctx.author.name,vote.id)
    await ctx.send("Voted!")

@client.command()
async def unvote(ctx:commands.Context):
    if not mycursor or not mydb:
        return
    mycursor.execute("SELECT candidate_id FROM Voters WHERE name = %s",(ctx.author.name,))
    candidate_id = mycursor.fetchone()
    if not candidate_id:
        return
    (candidate_id,) = candidate_id
    unvote_president(int(str(candidate_id)))
    remove_from_voters(ctx.author.name)

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

@client.tree.command()
async def create_bill(interaction:discord.Interaction, law:str):
    if not bill_channel:
        return
    voting_time = 72
    if mycursor == None or mydb == None:
        return
    result_time = int(time.time()) + voting_time*3600
    await add_bill(law,bill_channel,result_time,False)
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
    upvote_bill(bill_id)
    add_to_bill_voters(ctx.author.name,bill_id)
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
    downvote_bill(bill_id)
    add_to_bill_voters(ctx.author.name,bill_id)
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
    if not bill_channel:
        return
    if mycursor == None or mydb == None:
        return
    display_information_var = bill_display_information(bill_id)
    if display_information_var == None:
        return
    (bill,upvotes,downvotes,message_id) = display_information_var
    new_message = f"Bill #{bill_id}: {bill} :arrow_up::{upvotes} :arrow_down::{downvotes} @everyone"
    bill_message = await bill_channel.fetch_message(int(str(message_id)))
    await bill_message.edit(content=new_message)

async def update_president_bill(bill_id):
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
    if bills_str == "":
        await ctx.send("No bills")
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
    if not law_channel or not bill_channel or not presidents_office or not guild or not constitution:
        return
    if mycursor == None or mydb == None:
        return
    mycursor.execute("SELECT id,bill,upvotes,downvotes,result_time,message_id,is_amendment FROM Bills")
    for (id,bill,upvotes,downvotes,result_time,message_id,is_amendment) in mycursor.fetchall():
        if time.time() >= int(str(result_time)):
            await bill_result(id,bill,upvotes,downvotes,message_id,presidents_office,bill_channel,is_amendment,constitution)

    impeachment_info = get_impeachment()
    if not impeachment_info:
        return
    (upvotes,downvotes,result_time,message_id,president_id) = impeachment_info
    if time.time() < int(str(result_time)):
        return
    president_member = guild.get_member(int(str(president_id)))
    if not president_member:
        return
    if int(str(upvotes)) < 2 * int(str(downvotes)):
        await bill_channel.send(f"{president_member.mention} was not impeached")
        stop_impeachment()
    else:
        admin = guild.get_role(1299892838363824260)
        if admin == None:
            print("No admin")
            return
        await president_member.remove_roles(admin)
        next_election_in = 24
        election_time = int(time.time()) + next_election_in * 3600
        set_election_time(election_time)
        current_president = get_current_president()
        if not current_president:
            return
        await bill_channel.send(f"{current_president.name} has been impeached")
    impeachment_message = await bill_channel.fetch_message(int(str(message_id)))
    await impeachment_message.delete()
        
async def bill_result(bill_channel_id,bill,upvotes,downvotes,bill_channel_message_id,presidents_office,bill_channel:discord.abc.Messageable,is_amendment,constitution_channel):
    print(f"bill_channel_id:{bill_channel_id}")
    print(f"bill:{bill}")
    print(f"upvotes:{upvotes}")
    print(f"downvotes:{downvotes}")
    print(f"bill_channel_message_id:{bill_channel_message_id}")
    print(f"presidents_office:{presidents_office}")
    print(f"bill_channel:{bill_channel}")
    if mycursor == None or mydb == None:
        return
    if is_amendment == 1 and int(str(upvotes)) >= 2*int(str(downvotes)):
        constitution_channel.send(str(bill))
        mycursor.execute("DELETE FROM Bill_voters WHERE bill_id = %s",(int(str(bill_channel_id)),))
        mydb.commit()
        remove_bill(bill_channel_id)
        message = await bill_channel.fetch_message(bill_channel_message_id)
        await message.delete()
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
    remove_bill(bill_channel_id)

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
    president = current_president_id()
    if president != ctx.author.id:
        await ctx.send("You are not the president")
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
    if law_channel == None or bill_channel == None:
        return
    if mycursor == None or mydb == None:
        return
    president = current_president_id()
    if president != ctx.author.id:
        await ctx.send("You are not the president")
        return
    mycursor.execute("SELECT id FROM President_bills WHERE id = %s",(bill_id,))
    raw_id = mycursor.fetchone()
    if raw_id == None:
        await ctx.send("That bill doesn't exist")
        return
    mycursor.execute("SELECT bill_channel_message_id,original_id FROM President_bills WHERE id = %s",(bill_id,))
    raw_info = mycursor.fetchone()
    if raw_info == None:
        return
    (bill_channel_message_id,original_id) = raw_info
    bill_channel_message = await bill_channel.fetch_message(int(str(bill_channel_message_id)))
    await bill_channel_message.delete()
    await remove_president_bill(bill_id)
    await bill_channel.send(f"Bill #{int(str(original_id))} was vetoed")

@client.tree.command()
async def change(interaction:discord.Interaction,bill_id:int,new_bill:str):
    if not bill_channel:
        return
    president = current_president_id()
    if interaction.user.id != president:
        await interaction.response.send_message("You are not the president")
        return
    await remove_president_bill(bill_id)
    waiting_time = 24
    result_time = int(time.time())+waiting_time*3600
    await add_bill(new_bill,bill_channel,result_time,False)

@tasks.loop(time=datetime.time(hour=23,tzinfo=datetime.timezone.utc))
async def check_election():
    print("Checking election")
    next_election = get_election_time()
    if datetime.datetime.today().weekday() != 0 or (next_election and time.time() > next_election):
        return
    await election()

async def election():
    if not guild:
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
    previous_winner = previous_president()
    if previous_winner:
        await previous_winner.remove_roles(admin)
    await winner.add_roles(admin)
    clear_candidates()
    clear_voters()
    stop_impeachment()
    print("Election happened")

def shift_back(winner:discord.Member):
    if mycursor == None or mydb == None:
        print("database issue")
        return
    current_president = current_president_id()
    if not current_president:
        mycursor.execute("UPDATE Previous_winner SET previous_winner = NULL")
        mydb.commit()
    else:
        set_previous_president(current_president)
    set_current_president(winner.id)

def get_winner():
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
    if not mycursor or not mydb or not bill_channel or not guild:
        return
    president = get_current_president()
    if not president:
        return
    impeach_message = await bill_channel.send(f"Impeach {president.mention}? :arrow_up::0 :arrow_down::0 @everyone")
    current_time = int(time.time())
    result_hours = 48
    result_time = current_time + result_hours * 3600
    mycursor.execute("UPDATE Impeachment SET current_impeachment = 1, upvotes = 0, downvotes = 0, result_time = %s, message_id = %s",(result_time,impeach_message.id))

@client.tree.command()
async def create_amendment(interaction:discord.Interaction,amendment:str):
    if not bill_channel:
        return
    voting_time = 72
    if mycursor == None or mydb == None:
        return
    result_time = int(time.time()) + voting_time*3600
    await add_bill(amendment,bill_channel,result_time,True)
    await interaction.response.send_message("Bill created!")

client.run(TOKEN)
