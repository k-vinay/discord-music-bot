# Gagan Gupta | Vinay Krishna | Srividya Gandikota | Rishi Raja | Satvik Mojnidar

import glob
import discord
import numpy as np
#from apiclient.discovery import build
import json
import subprocess
from discord.ext import commands
import youtube_dl
import asyncio
import asgiref
# from path import Path
from youtube_search import YoutubeSearch

f = open("secrets.txt")
clientTag=f.readline()
TOKEN = f.readline()
spTOKEN = f.readline()
cmd = ["curl", "-X", "POST", "-H", "Authorization: Basic " + spTOKEN, "-d", "grant_type=client_credentials", "https://accounts.spotify.com/api/token"]
auth=(json.loads(subprocess.check_output(cmd).decode("utf-8")))["access_token"]
f.close()

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(source, *, data, volume=0.3):
        super().__init__(source, volume)

        data = data

        title = data.get('title')
        url = data.get('url')

    @classmethod
    async def from_url(cls, url, serverId, *, loop=None, stream=False):
        # print("getting loop")
        loop = loop or asyncio.get_event_loop()
        print("getting data 1")
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        print("getting data 2")
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        print("getting file name")
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        # try:
            # return cls(discord.FFmpegAudio(filename, args=ffmpeg_options), data=data), filename
        # except:
            # return await discord.FFmpegOpusAudio.from_probe(filename), filename
        print("about to probe from",filename)
        retval = await discord.FFmpegOpusAudio.from_probe(filename)
        print("finished probe")
        return retval, filename

bot = commands.Bot(command_prefix = "$")
queues = {}
vcs = {}
files = {}
print_lists = {}

@bot.event
async def on_ready():
    channel = bot.get_channel(495806090873798656)
    print("ready")
    await channel.send("Ready!")

def playqueue(vc, serverId):
    queue = queues.get(serverId,[])
    if(len(queue) == 0):
        print("queue is empty")
        return
    else:
        if(vc.is_playing()):
            vc.stop()
        else:
            player = queue.pop(0)
            vc.play(player, after=lambda e:playqueue(vc,serverId))
            if(len(print_lists.get(serverId, []))>0):
                print_lists[serverId].pop(0)
            print("playing")
        #skipCount+=1


@bot.command(pass_context = True)
async def q(ctx, uri):
    message = ctx.message
    serverId = message.guild.id
    if(ctx.message.author==bot.user):
        return
    if(ctx.message.channel.id!=495806090873798656):
        return
    
    playlistcode = uri
    if(playlistcode.startswith("https://open.spotify.com/playlist/")):
        playlistcode = playlistcode[len("https://open.spotify.com/playlist/"):]
    
    if (playlistcode.startswith("spotify:playlist:")):
        print("good input")
        playlistcode = playlistcode[len("spotify:playlist:"):]
        # gagans code
        limit = 100
        offset = 0
        count = 1
        cmd = ["curl", "-X", "GET", "https://api.spotify.com/v1/playlists/"+playlistcode+"/tracks?market=ES&fields=total%2Citems(track(name%2Cartists))&limit="+str(limit)+"&offset="+str(offset), "-H", "Accept: application/json", "-H", "Content-Type: application/json", "-H" ,"Authorization: Bearer " + auth]
        data=json.loads(subprocess.check_output(cmd).decode("utf-8"))
        cmd = ["curl", "-X", "GET", "https://api.spotify.com/v1/playlists/"+playlistcode+"?fields=fields%3Dname", "-H", "Accept: application/json", "-H", "Content-Type: application/json", "-H" ,"Authorization: Bearer " + auth]
        data2=json.loads(subprocess.check_output(cmd).decode("utf-8"))
        title = data2["name"]
        songs = []
        if("error" in data):
            await message.channel.send("playlist no bueno")
            return
        total = int(data["total"])
        left = total
        if(total>100):
            limit=100
        if(total>0 and total<100):
            limit=total

        i=0
        while(left>0):
            print("Left:"+str(left)+" Limit:"+str(limit)+" Offset:"+str(offset)+"\n\n")
            cmd = ["curl", "-X", "GET", "https://api.spotify.com/v1/playlists/"+playlistcode+"/tracks?market=ES&fields=total%2Citems(track(name%2Cartists))&limit="+str(limit)+"&offset="+str(offset), "-H", "Accept: application/json", "-H", "Content-Type: application/json", "-H" ,"Authorization: Bearer " + auth]
            data=json.loads(subprocess.check_output(cmd).decode("utf-8"))
            for song in data["items"]:
                songs.append([])
                songs[i].append((song["track"])["name"])
                for artist in (song["track"])["artists"]:
                    songs[i].append(artist["name"])
                i+=1
            left=left-limit
            offset=total-left
            if(total>100):
                limit=100
            if(total>0 and total<100):
                limit=left
        playlist = []
        if vcs.get(serverId,None)== None:
            a_v = message.author.voice
            if(not a_v):
                v_c = None
            else:
                v_c = a_v.channel
            if(not v_c):
                await ctx.send("you are not in voice!")
                return
            vc = await v_c.connect()
            vcs[serverId]=vc
        else: 
            vc=vcs[serverId]
        queues[serverId] = queues.get(serverId, [])
        for row in np.random.permutation(songs):
            query = row[0]+" by "+row[1] + " "
            done = False
            print(str(count) + ". " + query)
            attempts = 0
            while(not done and attempts<5):
                try:
                    results = json.loads(YoutubeSearch(query, max_results=2).to_json())
                    # print(results)
                    url="https://youtube.com"+str(((results["videos"])[0])["url_suffix"])
                    # if("karaoke" in results["videos"][0]["title"].lower()):
                        # url="https://youtube.com"+str(((results["videos"])[1])["url_suffix"])
                        # print("2nd link")
                    done = True
                except:
                    print("*******error results empty***********")
                    attempts += 1
            if(attempts==5):
                await message.channel.send("Couldn't find " + query)
            else:
                fname = subprocess.check_output(["youtube-dl", "-x", url])
                fname = subprocess.check_output(["youtube-dl", "--get-filename", url])
                fname = fname.decode()
                fname = fname[:fname.rfind(".")]
                if("]" in fname):
                    fname = fname[:fname.find("]")]
                fname = glob.glob(fname + "*")[0]
                print(fname)
                player = await discord.FFmpegOpusAudio.from_probe(fname)
                print("probe finished")
                queues[serverId].append(player)
                if(not vc.is_playing()):
                    playqueue(vc, serverId)
            count+=1
        count-=1
        await message.channel.send("queued " + str(count) + " songs from " + title)
    else:
        await message.channel.send("bad input")

@bot.command(pass_context = True)
async def song(ctx,query):
    message = ctx.message
    serverId = message.guild.id
    if vcs.get(message.guild.id,None)== None:
        vc=await bot.get_channel(461410591836340225).connect()
        vcs[message.guild.id]=vc
    else: 
        vc=vcs[message.guild.id]
    
    if(not query.startswith("https://www.youtube.com/watch?v=")):
        results = json.loads(YoutubeSearch(query, max_results=1).to_json())
        query="https://youtube.com"+str(((results["videos"])[0])["url_suffix"])
    fname = subprocess.check_output(["youtube-dl", "-x", query])
    fname = subprocess.check_output(["youtube-dl", "--get-filename", query])
    fname = fname.decode()
    fname = fname[:fname.rfind(".")]
    if("]" in fname):
        fname = fname[:fname.find("]")]
    fname = glob.glob(fname + "*")[0]
    print(fname)
    player = await discord.FFmpegOpusAudio.from_probe(fname)
    print("probe finished")
    queues[serverId] = queues.get(serverId, [])
    queues[serverId].append(player)
    if(not vc.is_playing()):
        playqueue(vc, serverId)

        

@bot.command(pass_context = True)
async def list(ctx):
    message = ctx.message
    serverId = message.guild.id
    printstr = ""
    for i in range(min(len(print_lists.get(serverId, [])), 10)):
        printstr = printstr + print_lists[serverId][i] + "\n"
    if(printstr==""):
        await message.channel.send("```queue is empty```")
    else:
        await message.channel.send("```Currently playing: "+printstr+"```")

@bot.command(pass_context = True)
async def h(ctx):
    message = ctx.message
    await message.channel.send("""$q (spotify uri) -- queues and plays all the songs from a spotify playlist into discord
$song (url or name) -- searches web for song and plays individual song
$stop -- will stop all current music and siconnect bot
$skip -- will skip current song playing
$list -- lists the first ten songs in queue""")

@bot.command(pass_context = True)
async def stop(ctx):
    print("**stopping**")
    # files=d.walkfiles('*.webm')
    # for vc in vcs:
        # await vcs[vc].disconnect()
    # for file in files:
        # file.remove()
    # filesOther = d.walkfiles('*.m4a')
    await ctx.message.channel.send("stopping")
    serverId = ctx.message.guild.id
    vc = vcs.pop(serverId, None)
    if(not vc is None and vc.is_playing()):
        await vc.disconnect()
    for file in files.get(serverId, []):
        subprocess.run(["rm", file])
    queues[serverId] = []
    files[serverId] = []
    print_lists[serverId] = []
    vcs.pop(serverId, None)

@bot.command(pass_context = True)    
async def skip(ctx):
    # await ctx.message.channel.send("sorry, this is a WIP. ending")
    # if(vcs[ctx.message.guild.id].is_playing()):
        # await vcs[ctx.message.guild.id].disconnect()
    # for serverId in files:
        # for file in files[serverId]:
            # subprocess.run(["rm", file])
    # raise SystemExit
    # skipCount+=1
    await ctx.message.channel.send("skipping some songs")
    vc=vcs[ctx.message.guild.id]
    playqueue(vc, ctx.message.guild.id)

@bot.command(pass_context = True)
async def pause(ctx):
    #skipCount+=1
    vc=vcs[ctx.message.guild.id]
    vc.pause()

@bot.command(pass_context = True)    
async def play(ctx):
    #skipCount+=1
    vc=vcs[ctx.message.guild.id]
    vc.resume()
  
bot.run(TOKEN)
