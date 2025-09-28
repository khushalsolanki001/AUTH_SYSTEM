#it was for AUTH using github and discord
import discord
from discord.ext import commands
import requests
import base64
import json
import random
import string
from datetime import datetime, timedelta, timezone

# ========== CONFIG ==========
TOKEN = ''
GITHUB_TOKEN = '' //use here github token
GITHUB_USERNAME = '' //use your github username
GITHUB_REPO = 'AUTH_SYSTEM'
FILE_PATH = 'user.json'
ALLOWED_CHANNEL_ID = 
LOG_CHANNEL_ID = 
OWNER_ID = 

API_URL = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{FILE_PATH}"
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# ========== DISCORD INTENTS ==========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, owner_id=OWNER_ID)

# ========== UTILS ==========
def is_owner():
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID:
            return True
        raise commands.NotOwner("You are not the owner!")
    return commands.check(predicate)

def load_json():
    r = requests.get(API_URL, headers=HEADERS)
    if r.status_code == 404:
        data = {"users": [], "resellers": {}, "keys": []}
        encoded = base64.b64encode(json.dumps(data, indent=4).encode()).decode()
        payload = {"message": "Initialize user.json", "content": encoded}
        create = requests.put(API_URL, headers=HEADERS, json=payload)
        create.raise_for_status()
        return data, create.json()['content']['sha']
    r.raise_for_status()
    content = r.json()
    decoded = base64.b64decode(content['content']).decode()
    return json.loads(decoded), content['sha']

def save_json(data, sha, msg):
    encoded = base64.b64encode(json.dumps(data, indent=4).encode()).decode()
    payload = {"message": msg, "content": encoded, "sha": sha}
    r = requests.put(API_URL, headers=HEADERS, json=payload)
    r.raise_for_status()

def gen_random_key(length=16):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ========== BOT COMMANDS ==========

@bot.command()
@is_owner()
async def addreseller(ctx, user: discord.Member, credits: int):
    data, sha = load_json()
    data['resellers'][str(user.id)] = credits
    save_json(data, sha, f"Add/Update reseller {user.id}")
    await ctx.send(f"Reseller {user.mention} now has {credits} credits.")

@bot.command()
async def credits(ctx):
    data, _ = load_json()
    credits = data['resellers'].get(str(ctx.author.id), 0)
    await ctx.send(f"You have {credits} credits.")

@bot.command(name='adduser')
async def adduser(ctx, username: str, password: str, days: int):
    data, sha = load_json()
    if any(u['username'] == username for u in data['users']):
        return await ctx.send("User already exists.")

    if ctx.author.id != OWNER_ID:
        reseller_credits = data['resellers'].get(str(ctx.author.id), 0)
        if reseller_credits <= 0:
            return await ctx.send("You do not have enough credits.")
        data['resellers'][str(ctx.author.id)] -= 1

    expiry = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")
    data['users'].append({"username": username, "password": password, "hwid": [], "expiry": expiry})
    save_json(data, sha, f"Add user {username}")
    await ctx.send(f"User {username} added.")

@bot.command()
@is_owner()
async def genkeys(ctx, amount: int, days: int):
    data, sha = load_json()
    keys = []
    for _ in range(amount):
        key = gen_random_key()
        expiry = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")
        data['keys'].append({"key": key, "expiry": expiry})
        keys.append(key)
    save_json(data, sha, f"Generated {amount} keys")
    await ctx.send(f"Generated keys:\n```\n{chr(10).join(keys)}\n```")

@bot.command()
async def deleteuser(ctx, username: str):
    data, sha = load_json()
    users = data['users']
    updated = [u for u in users if u['username'] != username]
    if len(updated) == len(users):
        return await ctx.send("User not found.")
    data['users'] = updated
    save_json(data, sha, f"Delete user {username}")
    await ctx.send(f"User {username} deleted.")

@bot.command()
async def resetuser(ctx, username: str):
    data, sha = load_json()
    for user in data['users']:
        if user['username'] == username:
            user['hwid'] = []
            save_json(data, sha, f"Reset HWID for {username}")
            return await ctx.send(f"User {username}'s HWID reset.")
    await ctx.send("User not found.")

@bot.command()
async def userinfo(ctx, username: str):
    data, _ = load_json()
    for user in data['users']:
        if user['username'] == username:
            return await ctx.send(f"```json\n{json.dumps(user, indent=4)}\n```")
    await ctx.send("User not found.")

@bot.command()
async def extenduser(ctx, username: str, days: int):
    data, sha = load_json()
    for user in data['users']:
        if user['username'] == username:
            new_expiry = datetime.strptime(user['expiry'], "%Y-%m-%d") + timedelta(days=days)
            user['expiry'] = new_expiry.strftime("%Y-%m-%d")
            save_json(data, sha, f"Extended user {username}")
            return await ctx.send(f"Extended {username} by {days} days.")
    await ctx.send("User not found.")

@bot.command()
@is_owner()
async def listusers(ctx):
    data, _ = load_json()
    await ctx.send(f"Total users: {len(data['users'])}")

@bot.command()
@is_owner()
async def deleteall(ctx):
    data, sha = load_json()
    data['users'] = []
    save_json(data, sha, "Deleted all users")
    await ctx.send("All users deleted.")

@bot.command()
@is_owner()
async def deleteexpireusers(ctx):
    data, sha = load_json()
    now = datetime.now(timezone.utc)
    data['users'] = [u for u in data['users'] if datetime.strptime(u['expiry'], "%Y-%m-%d") > now]
    save_json(data, sha, "Deleted expired users")
    await ctx.send("Expired users deleted.")

@bot.command()
@is_owner()
async def backup(ctx):
    data, _ = load_json()
    await ctx.send(file=discord.File(fp=bytes(json.dumps(data, indent=4), 'utf-8'), filename='backup.json'))

@bot.command()
@is_owner()
async def ownerpanel(ctx):
    await ctx.send("Available owner commands: !listusers, !deleteall, !deleteexpireusers, !backup, !addreseller")

@bot.command()
async def helpme(ctx):
    embed = discord.Embed(
        title="🤖 Bot Commands",
        description="Here's a list of available commands:",
        color=discord.Color.orange()
    )
    embed.add_field(name="!adduser username password days", value="➕ Add user (reseller deducts credits)", inline=False)
    embed.add_field(name="!credits", value="💰 Check your credits", inline=False)
    embed.add_field(name="!genkeys amount days", value="🔑 Generate license keys (owner only)", inline=False)
    embed.add_field(name="!userinfo username", value="🔍 Show user info", inline=False)
    embed.add_field(name="!deleteuser username", value="🗑 Delete a user", inline=False)
    embed.add_field(name="!resetuser username", value="♻ Reset HWID", inline=False)
    embed.add_field(name="!extenduser username days", value="⏳ Extend subscription", inline=False)
    embed.add_field(name="!addreseller @user credits", value="🏦 Add/update reseller credits (owner only)", inline=False)
    embed.add_field(name="!ownerpanel", value="⚙ Owner commands list", inline=False)
    await ctx.send(embed=embed)

# ========== ERROR HANDLER ==========
@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"Error: {str(error)}")

# ========== RUN BOT ==========
if __name__ == '__main__':
    bot.run(TOKEN)
