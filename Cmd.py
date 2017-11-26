import Sys, Conversation
import Cooldown as CD
import asyncio, random, datetime, time, discord, json, praw
import forecastio, os, sys, git, os

# Reddit
reddit = praw.Reddit('bot1')

# Forecast
forecast_api_key = Sys.Read_Personal(data_type='Forecast_Key')
lat = 42.538690
lng = -71.046564


class Ranks:
    AdminNames = [
        'ElGrubb#2774',  # Dom
        'AlbertoBenitez#1615',  # Alberto
        'Stevieboy#2126'  # Scangas

    ]
    Admins = [
        239791371110580225,  # Dom
        281866259824508928,  # Berto
        215639561181724672,  # Scangas
        211271446226403328  # Tracy
    ]
    NoUse = [
        ''
    ]


class Vars:
    AdminCode = random.randint(0, 4000)
    Bot = None
    Disabled = False
    start_time = time.clock()

    QuickChat_Data = []
    QuickChat_TriggerList = []


def CheckPrivilage(message, nec):
    # Checks the guild to see which privileges the bot has
    # nec is a list of the privileges it requires
    """
    "Send Messages"
    "Edit Messages"
    "React Messages"
    "Delete Messages"
    """


async def CheckMessage(message, start=None, notInclude=None, close=None, prefix=None, guild=None, sender=None, admin=None):
    """
    Checks through the contents of a message and params to see if its good to run the function
    :param message:     The message object
    :param start:       What the message should start with (IE in "/poll" it'd be "poll"
    :param close:       True or False, whether or not to test how close it was
    :param notInclude   Something to not have in the message
    :param prefix:      What the command ignite should be (None=Words, 1=Any Operator, str=specific operator)
    :param guild:       Specific guild? Should be guild ID
    :param sender:      Specific user? Should be user ID
    :param admin:       Should they be an 'admin'
    :return:            Returns True if message passes, False if not. 
    """
    totalPossibleCorrect = 0  # Has how many features this can have correct
    numberCorrect = 0

    # PREFIX
    hasPrefix, content = 0, message.content
    totalPossibleCorrect += 1
    for possiblePrefix in Conversation.Command_Prefixes:  # For each possible prefix:
        if message.content.startswith(possiblePrefix):  # If message has it
            hasPrefix += 1  # Add one to this

    if not prefix:  # if message shouldn't have a prefix
        if hasPrefix == 0:
            numberCorrect += 1
            content = message.content
    elif prefix is True or prefix == 1:  # If it should have a prefix
        if hasPrefix > 0:
            numberCorrect += 1
            content = message.content[1:]
        else:
            return False
    elif type(prefix) == str:  # Or if prefix is a string
        if message.content.lower().startswith(prefix.lower()):
            numberCorrect += 1
            content = message.content[1:]
        else:
            return False

    # START
    if start:  # If there's a certain phrase the message should start with
        totalPossibleCorrect += 1
        if content.lower().startswith(start.lower()):
            numberCorrect += 1
        elif close:
            if Sys.PercentSimilar(message.content, start.lower()) >= 85:
                numberCorrect += 1

    # Not Include
    if notInclude:
        totalPossibleCorrect += 1
        if notInclude.lower() not in content.lower():
            numberCorrect += 1

    # Server
    if guild:
        totalPossibleCorrect += 1
        if message.guild.id == guild:
            numberCorrect += 1

    # Sender
    if sender:
        totalPossibleCorrect += 1
        if message.author.id == sender:
            numberCorrect += 1

    # Admin
    if admin:
        totalPossibleCorrect += 1
        if message.author.id in Ranks.Admins:
            numberCorrect += 1

    if numberCorrect == totalPossibleCorrect:
        Vars.Bot.loop.create_task(loadingSign(message))
        return True
    else:
        return False

# Loading Sign
async def loadingSign(message):
    try:
        await message.add_reaction(Conversation.Emoji['circle'])
        await asyncio.sleep(.25)
        await message.remove_reaction(Conversation.Emoji['circle'], Vars.Bot.user)
    except:
        pass


class Helpers:
    @staticmethod
    async def Confirmation(message, text, yes_text=None, deny_text="Action Cancelled.", timeout=60,
                           return_timeout=False, deleted_original_message=False):
        """
        Sends a confirmation for a command
        :param message: The message object
        :param text: What the message of the embed should say
        :param yes_text: If you want a confirmed message to play for 4 seconds
        :param deny_text: If you want a message to play when x is hit. 
        :param timeout: How long to wait for a conclusion
        :return: Returns True if Yes, False if No, and None if timed out. 
        """
        # Establish two emojis
        CancelEmoji = Conversation.Emoji['x']
        ContinueEmoji = Conversation.Emoji['check']

        def check(reaction, user):  # Will be used to validate answers
            # Returns if user is initial user and reaction is either of those
            if user == message.author and str(reaction.emoji) in [CancelEmoji, ContinueEmoji]:
                return reaction, user

        em = discord.Embed(title=text, timestamp=datetime.datetime.now(), colour=Sys.Colors["Goldbot"])
        em.set_author(name="Confirmation:", icon_url=Vars.Bot.user.avatar_url)

        # Send message and add emojis
        msg = await message.channel.send(embed=em)
        await msg.add_reaction(ContinueEmoji)
        await msg.add_reaction(CancelEmoji)

        try:
            # Wait for the reaction(s)
            reaction, user = await Vars.Bot.wait_for('reaction_add', timeout=timeout, check=check)

        except asyncio.TimeoutError:
            # If it times out
            await msg.delete()
            await message.channel.send(deny_text, delete_after=5)
            if return_timeout:
                return "Timed Out"
            else:
                return None

        # If they hit the X
        if reaction.emoji == CancelEmoji:
            await msg.delete()
            await message.channel.send(deny_text, delete_after=5)
            return False

        # If they hit the check
        elif reaction.emoji == ContinueEmoji:
            await msg.delete()
            if not deleted_original_message:
                await message.add_reaction(ContinueEmoji)
            if yes_text:
                await message.channel.send(yes_text, delete_after=5)
            return True

    @staticmethod
    def RetrieveData(type=None):
        """
        Reads the Data.txt file, changes from JSON to dict, and returns the specific type
        :param type:  The item of data requested
        :return: The dict or list containing the data
        
        Possible Types:
        type="Memes"
        type="Quotes"
        """
        # Retrieve the data from the read-only file
        file = open("Data.txt",'r')
        data = file.read()
        file.close()

        # Turn into JSON Dict
        data = json.loads(data)
        if type:
            try:
                return data[type]
            except KeyError:
                return None
        else:
            return data

    @staticmethod
    def SaveData(data_dict, type=None):
        """
        Saves data of a special type in Data.txt
        :param data_dict: the Dictionary or List to be saved as
        :param type: The type of data. Quotes, Memes, etc
        :return: True or False
        """
        old_data = Helpers.RetrieveData()

        to_save = None
        if type in old_data:  # If a type exists
            old_data[type] = data_dict
            to_save = old_data
        elif type:  # Even if it doesn't exist
            old_data[type] = data_dict
            to_save = old_data
        elif not type:  # If there is no type
            to_save = data_dict
        else:  # If something else happened
            raise EnvironmentError("Something arose...")

        to_save = json.dumps(to_save, indent=2)
        with open("Data.txt", "w") as file:
            file.write(to_save)
        return True


class Admin:
    @staticmethod
    async def Delete(message):
        """
        Deletes a certain number of messages
        :param message: The original message
        :return: returns nothing
        """
        if not await CheckMessage(message, start="Delete", prefix=True, admin=True):
            return

        # Clean up the message
        content = message.content.lower().replace("delete", "")
        content = content[1:].strip()

        # Makes sure that it is a proper integer in the message
        try:
            content = int(content)
        except ValueError:
            await message.channel.send("Not a valid number of messages. Try again", delete_after=5)
            await asyncio.sleep(5)
            await message.delete()
            return

        # Cooldown Shit
        cd_notice = CD.CheckCooldown("delete", message.author, message.guild)  # Do the cooldown CMD
        if type(cd_notice) == int:
            # If there is an active cooldown
            msg = await message.channel.send('Cooldown Active, please wait: `' + await Sys.SecMin(cd_notice) + '`')
            await asyncio.sleep(5)
            await message.channel.delete([msg, message])
            return

        if content > 9:
            confirmation = await Helpers.Confirmation(message, "Delete " + str(content) + " messages?",
                                                      deny_text="Deletion Cancelled", timeout=20)
        else:
            confirmation = True
        if confirmation:
            await message.channel.purge(limit=content + 1)  # Delete the messages
            await message.channel.send("Deleted " + str(content) + " messages", delete_after=5)  # Send message

    @staticmethod
    async def Stop(message):
        """
        Stops the Bot
        :param message: Message.content
        :return: Returns nothing
        """
        if not await CheckMessage(message, start="stop", prefix=True, admin=True):
            return

        # Check to make sure the user confirms it
        confirmation = await Helpers.Confirmation(message, "Shut Down?", deny_text="Shut Down Cancelled")
        if confirmation:
            await Vars.Bot.change_presence(status=discord.Status.offline)  # Status to offline
            await Vars.Bot.logout()  # Log off

    @staticmethod
    async def LeaveServer(message):
        if not await CheckMessage(message, start="leave", prefix=True, admin=True):
            return

        text = "Leave " + message.guild.name + "?"  # Says "Leave Red Playground?"
        confirmation = await Helpers.Confirmation(message, text, deny_text="I will stay.")  # Waits for confirmation
        if confirmation:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Set up Time String
            await message.channel.send(Vars.Bot.user.name + " Left at " + current_time)  # Sends goodbye
            await message.guild.leave  # Leaves

    @staticmethod
    async def Disable(message):
        if not await CheckMessage(message, prefix=True, admin=True, start="Disable"):
            return False
        Vars.Disabled = True
        await Vars.Bot.change_presence(game=(discord.Game(name='Offline')), status=discord.Status.do_not_disturb)
        msg = await message.channel.send('Bot Disabled.')
        await asyncio.sleep(5)
        await message.channel.delete_messages([msg, message])

        # Wait to re-enable
        await asyncio.sleep(6)
        if not Vars.Disabled:
            return

        # If still disabled:
        to_send = message.author.mention + ", would you like to Re-Enable?"
        confirmation = await Helpers.Confirmation(message, to_send, timeout=30, return_timeout=True, deleted_original_message=True)
        if not confirmation:  # If they say X, stay disabled:
            await message.channel.send("Will stay disabled indefinitely. ", delete_after=5)
            return
        if confirmation:
            await message.channel.send("Enabling.")
            Vars.Disabled = False
            return

    @staticmethod
    async def Enable(message):
        if not await CheckMessage(message, prefix=True, admin=True, start="Enable"):
            return True
        Vars.Disabled = False
        await Vars.Bot.change_presence(status=discord.Status.online)
        msg = await message.channel.send('Bot Enabled.')
        await asyncio.sleep(5)
        await msg.delete()
        await message.channel.delete_messages([msg, message])

    @staticmethod
    async def Talk(message):  # TODO REDO
        if not await CheckMessage(message, start="Talk", prefix=True, admin=True):
            return
        msg = message.content[5:].strip()
        guild, channel = message.guild, message.channel
        real_msg = []
        # If there are server / channel modifiers
        if '*' in message.content:
            split_content = message.content.split(' ')
            for part in split_content:
                # For each modifier
                if "%%" in part:  # Used to represent a space
                    part = part.replace("%%", ' ')

                # For the server modifier:
                if part.startswith('*'):
                    if not part[1:len(part)].startswith('*'):  # Server
                        # As long as its not two *, that means channel
                        for bot_guild in Vars.Bot.guilds:
                            # For each server the bot can see
                            if part[1:len(part)] in bot_guild.name:
                                # If the snippit given is in that servers name, set guild equal to it
                                guild = bot_guild
                                break

                    # For the channel
                    if part.startswith('**'):
                        if not guild:
                            guild = message.guild
                        for bot_channel in guild.channels:
                            if part[2:len(part)] in bot_channel.name:
                                channel = bot_channel
                                break
                    else:
                        channel = message.channel
                else:
                    real_msg.append(part)
        if real_msg:
            sentence = ''
            for part in real_msg:
                sentence += part + ' '
            msg = sentence[5:].strip()

        msg = Sys.FirstCap(msg)

        await channel.send(msg)

    @staticmethod
    async def Status(message):
        if not await CheckMessage(message, prefix=True, start="status", admin=True):
            return
        sentTime = message.created_at
        recievedTime = datetime.datetime.utcnow()
        difference = recievedTime - sentTime

        sendmsg = "Bot is ONLINE"
        sendmsg += "\n**Speed:** " + str(difference)[5:] + " seconds. "
        sendmsg += "\n**Uptime:** " + Sys.SecMin(round(time.clock() - Vars.start_time))
        em = discord.Embed(title="Current Status", timestamp=datetime.datetime.now(), colour=Sys.Colors["Goldbot"],
                           description=sendmsg)
        em.set_author(name=Vars.Bot.user, icon_url=Vars.Bot.user.avatar_url)

        await message.channel.send(embed=em)

    @staticmethod
    async def Restart(message):
        if not await CheckMessage(message, prefix=True, start="restart", admin=True):
            return
        confirmation = await Helpers.Confirmation(message, "Restart?", deny_text="Restart Cancelled")
        if not confirmation:
            return
        # Add check to message
        await message.add_reaction(Conversation.Emoji["check"])

        # Set up so it knows that it has restarted
        info = {
            "Restarted": True,
            "Type": "Command",
            "Channel_ID": message.channel.id
        }
        Helpers.SaveData(info, type="System")

        # Restart
        await Vars.Bot.logout()
        os.execv(sys.executable, ['python'] + sys.argv)
        return

    @staticmethod
    async def CheckRestart():
        # Runs on start, checks if it just restarted
        restart_data = Helpers.RetrieveData("System")

        if restart_data["Restarted"]:
            channel = Vars.Bot.get_channel(restart_data["Channel_ID"])
            await channel.send("Successfully Committed a `Full` Restart.")
            restart_data["Restarted"] = False
            Helpers.SaveData(restart_data, type="System")

    @staticmethod
    async def Update(message):
        if not await CheckMessage(message, prefix=True, admin=True, start="update"):
            return
        if not await Helpers.Confirmation(message, "Update?", deny_text="Update Cancelled", timeout=20):
            return

        channel = message.channel
        g = git.cmd.Git(os.getcwd())
        output = g.pull()

        to_send = "`" + output + "`"
        await channel.send(output)

        if output == "Already up to date.":
            return

        await message.add_reaction(Conversation.Emoji["check"])
        info = {
            "Restarted": True,
            "Type": "Update",
            "Channel_ID": message.channel.id
        }
        Helpers.SaveData(info, type="System")
        await Vars.Bot.logout()
        os.execv(sys.executable, ['python'] + sys.argv)
        return





class Timer:
    @staticmethod
    def DigitTime():
        hour = time.strftime('%H')
        minute = time.strftime('%M')
        return hour + ':' + minute

    @staticmethod
    async def TimeThread(bot):
        await asyncio.sleep(10)
        old_time, current_time = None, None
        # while not Vars.Crash:
        while True:
            await asyncio.sleep(5)
            old_time = current_time
            current_time = Timer.DigitTime()

            # Morning Weather
            if current_time != old_time:  # Ensures this only runs on minute change
                if current_time == '06:30':
                    today = datetime.datetime.now().strftime("%B %d")
                    print("Good Morning! It is " + today)
                    await Cmd.T_Weather(bot)


class Quotes:
    @staticmethod
    async def SendQuote(message):
        """
        Sends random quote from the file
        Quote JSON Format:
        Quotes: {position: 6, data: [{date:x, quote:x, id:x, name:x}, {date:x, quote:x, id:x, name:x}]}

        :param message: MSG Object
        :return: Nothing
        """
        if not await CheckMessage(message, prefix=True, start="send quote"):
            return

        # Cooldown
        cd_notice = CD.CheckCooldown("quote", message.author, message.guild)
        if type(cd_notice) == int:
            msg = await message.channel.send('Cooldown Active, please wait: `' + Sys.SecMin(cd_notice) + '`')
            await asyncio.sleep(5)
            await message.channel.delete_messages([msg, message])
            return

        # Get Quote Dict
        data = Helpers.RetrieveData(type="Quotes")
        # if str(message.guild.id) in data:
        #     data = data[str(message.guild.id)]
        # else:
        #     await message.channel.send("No saved quotes for this server! Save some quotes!", delete_after=10)
        #     return
        chosen_quote = data["info"][data["position"]]

        # Update Quote List etc
        data["position"] += 1
        if data["position"] >= len(data["info"]):
            random.shuffle(data["info"])
            data["position"] = 0
        Helpers.SaveData(data, type="Quotes")

        # Modify the Data a bit
        date = datetime.datetime.fromtimestamp(chosen_quote["date"])
        quote = "**\"**" + chosen_quote["quote"] + "**\"**"
        sender_obj = await Vars.Bot.get_user_info(chosen_quote["user_id"])

        # Prepare the Embed
        em = discord.Embed(title=quote, timestamp=date, colour=Sys.Colors["Goldbot"])
        em.set_footer(text="Saved Quote", icon_url=message.guild.icon_url)
        em.set_author(name=sender_obj.name, icon_url=sender_obj.avatar_url)

        await message.channel.send(embed=em)

    @staticmethod
    async def QuoteCommand(message):
        if not await CheckMessage(message, start="quote", prefix=True):
            return
        if len(message.mentions) == 0:
            await message.channel.send("Please follow the correct format: `/quote @Redbot How are you?`",
                                       delete_after=5)
            return
        elif len(message.mentions) > 1:
            await message.channel.send("You can only quote one individual.", delete_after=5)
            return

        # Seperate reactioned user from the message
        mention_user = message.mentions[0]
        content = message.clean_content[7:].replace("@" + mention_user.name, '').strip()

        # Create Embed
        em = discord.Embed(title="Quote this?", timestamp=datetime.datetime.now(), colour=Sys.Colors["Goldbot"],
                           description="**\"**" + content + "**\"**")
        em.set_author(name=mention_user, icon_url=mention_user.avatar_url)
        em.set_footer(text="10 minute timeout")

        # Send Message
        msg = await message.channel.send("Create Quote?", embed=em)

        def check(reaction, user):  # Will be used to validate answers
            # Returns if there are 3 more reactions who aren't this bot
            if reaction.count >= 2 and reaction.emoji == Conversation.Emoji["quote"]:
                return reaction, user
            else:
                return False

        await msg.add_reaction(Conversation.Emoji["quote"])

        try:
            # Wait for the reaction(s)
            reaction, user = await Vars.Bot.wait_for('reaction_add', timeout=600, check=check)

        except asyncio.TimeoutError:
            # If it times out
            await msg.delete()
            await message.channel.send("Failed to receive 3 reactions", delete_after=5)
            return None

        await msg.delete()
        await message.add_reaction(Conversation.Emoji["check"])

        await Quotes.NoteQuote(quote=content, user=mention_user)

    @staticmethod
    async def OnQuoteReaction(reaction, user):
        if reaction.emoji != Conversation.Emoji['quote']:
            return
        if user == reaction.message.author:
            await reaction.message.remove_reaction(reaction.emoji, user)
            return
        if reaction.message.author == Vars.Bot.user:
            return
        if reaction.count >= 3:
            await reaction.message.clear_reactions()
            await reaction.message.add_reaction(Conversation.Emoji["check"])
            await Quotes.NoteQuote(quote=reaction.message.content, user=reaction.message.author)
            await reaction.message.channel.send("Saved quote " + reaction.message.content)

    @staticmethod
    async def NoteQuote(quote=None, user=None):
        date = datetime.datetime.now()
        timestamp = time.mktime(date.timetuple())
        quote = quote.strip()
        user_name = str(user)
        user_id = user.id

        data = Helpers.RetrieveData(type="Quotes")
        data['info'].append({'date': timestamp, 'quote': quote, 'user_id': user_id, 'user_name': user_name})

        Helpers.SaveData(data_dict=data, type="Quotes")


class Memes:
    """
    Meme data file:
    {"Memes": [
        {"12345":[
            [201711202037, "www.google.com"]
        ]]}
    """
    subs = {
        'meme': "dankmemes+BikiniBottomTwitter+2meirl4meirl+youdontsurf+imgoingtohellforthis",
        'dank': "dankmemes+BikiniBottomTwitter+2meirl4meirl+youdontsurf+imgoingtohellforthis",
        'normie': "memes+funny",
        'wholesome': "wholesomememes+eyebleach+rarepuppers",
        'aww': 'cats+cute+dogs+aww',
        'hmmm': 'hmmm+hmmmgifs',
        'cringe': 'cringeanarchy+tumblrinaction+sadcringe+cringepics+niceguys+4panelcringe',
        'doggo': 'rarepuppers+doggos',
        'surreal': 'surrealmemes'
    }

    @staticmethod
    async def SendMeme(message, is_repeat=False):
        if not await CheckMessage(message, start="send", notInclude="quote", prefix=True):
            return
        # If the channel is private
        if str(message.channel).startswith("Direct Message"):
            await message.channel.send("Meme Sending only supported in group servers.", delete_after=5)
            await message.add_reaction(Conversation.Emoji["e"])
            return

        channel = message.channel

        # To make sure it knows the type to send
        content = message.content.lower()
        content_check = 0
        for key in Memes.subs:
            if key in content:
                content_check += 1
            content_check += 1
        if content_check == 0:
            await channel.send('I don\'t understand that type', delete_after=5)
            await message.add_reaction(Conversation.Emoji["x"])
            return

        # CoolDown Shit
        if not is_repeat:
            cd_notice = CD.CheckCooldown("meme", message.author, message.guild)
            if type(cd_notice) == int:
                await channel.send('Cooldown Active, please wait: `' + Sys.SecMin(cd_notice) + '`', delete_after=5)
                await message.add_reaction(Conversation.Emoji["x"])
                return

        await channel.trigger_typing()

        # Remove everything but the type of meme to send
        content = content[1:]
        content = content[0:len(content) - 1] if content[-1].strip().lower() == 's' else content # Remove trailing "s"
        content = content.replace('send', '').strip() # Remove send
        subreddit = reddit.subreddit(Memes.subs[content])

        # Creates list 'urls' that has all sent urls
        url_list = []
        data = Helpers.RetrieveData(type="Memes")
        guild_id = str(message.guild.id)
        if guild_id in data:  # If data exists for server:
            for pair in data[guild_id]:
                url_list.append(pair[1])
        else:  # If there is no server data:
            url_list = []

        # Search through Reddit for a not used meme
        found_meme = None
        times = 0
        for submission in subreddit.hot(limit=100):  # Iterates through each submission
            times += 1
            if not submission.stickied:  # To ensure its not stickied
                if submission.url not in url_list:
                    found_meme = submission
                    break

        # Make sure the link is an image
        is_image = None
        extension = found_meme.url.replace(found_meme.url[0:-4], "")
        if extension in [".png", ".jpg", "jpeg"]:
            is_image = True
        # If we're not sure if its an image, it'll not send an embed.


        # Prepare to send the message
        if not found_meme:
            await channel.send("No fresh memes. Try later.", delete_after=10)
            await message.add_reaction(Conversation.Emoji["x"])
            return
        if len(found_meme.url) <= 20:
            link = found_meme.url
        else:
            link = Sys.Shorten_Link(found_meme.url)

        # Embed
        if is_image:
            em = discord.Embed(title=found_meme.title, timestamp=datetime.datetime.now())
            em.set_image(url=link)
            em.set_footer(text="Sent " + Sys.FirstCap(content))
            msg = await channel.send(embed=em)
        else:
            to_send = link + '\n'
            to_send += '**\"** ' + found_meme.title + ' **\"**\n'
            msg = await channel.send(to_send)

        await Memes.AddMeme(message.guild.id, found_meme.url)
        await Memes.CleanMemes()

        # Now comes the fun part: The reactions
        # Set up emojis 'info' and 'repeat'
        info = Conversation.Emoji['info']
        repeat = Conversation.Emoji['repeat']
        if 'hmmm' in message.content.lower():
            repeat = Conversation.Emoji['hmmm']

        # These two allow us to have multiple reactions
        used_info = False
        used_repeat = True if is_repeat else False

        # Function to use to validate a response
        def check(init_reaction, init_user):
            if init_reaction.emoji in [info, repeat] and init_user != Vars.Bot.user:
                return init_reaction, init_user

        # Okay so this loop continues until both reactions are used or timeout
        continue_on = True
        while continue_on:
            if not used_repeat:  # if the repeat emoji hasn't been pressed
                await msg.add_reaction(repeat)
            if not used_info:  # If the info emoji hasn't been pressed
                await msg.add_reaction(info)

            try:
                # Wait for the reaction(s)
                reaction, user = await Vars.Bot.wait_for('reaction_add', timeout=40, check=check)

            # Timeout
            except asyncio.TimeoutError:
                continue_on = False  # Don't continue
                await msg.clear_reactions()
                return

            # If a reaction is added:
            await msg.clear_reactions()
            if reaction.emoji == info:  # INFO
                used_info = True
                new_msg = link + '\n'
                new_msg += '**Title:**  ' + str(found_meme.title) + '\n'
                new_msg += '**Score:**  ' + str(found_meme.score) + '\n'
                new_msg += '**Subreddit:**  /r/' + str(found_meme.subreddit) + '\n'
                new_msg += '**Author:**  /u/' + str(found_meme.author) + '\n'
                new_msg += '**Post Link:**  ' + str(found_meme.shortlink) + '\n'
                await msg.edit(embed=None, content=new_msg)
            elif reaction.emoji == repeat:  # REPEAT
                used_repeat = True
                Vars.Bot.loop.create_task(Memes.SendMeme(message, is_repeat=True))

            if used_info and used_repeat:  # If both have been used
                continue_on = False  # Do not continue
        return


    @staticmethod
    async def AddMeme(guild_id, meme_url):
        data = Helpers.RetrieveData(type="Memes")
        guild_id = str(guild_id)
        if guild_id not in data:  # If there is no Data for the guild id
            data[guild_id] = []

        to_add = [str(Sys.TimeStamp()), meme_url]

        data[guild_id].append(to_add)

        Helpers.SaveData(data, type="Memes")

    @staticmethod
    async def CleanMemes():
        timestamp = Sys.TimeStamp()
        data_dict = Helpers.RetrieveData(type="Memes")

        # Removes any link pair that is less than 2 days away
        for server in data_dict:
            temp_list = []
            for link_group in data_dict[server]:  # For each [time, link] per server
                # Only adds link_group to temp_list if less than 2 days btwn now and then
                if timestamp - int(link_group[0]) <= 20000:  # If less than 2 days
                    temp_list.append(link_group)
                else:
                    pass
                    # print(timestamp - int(link_group[0]), timestamp, int(link_group[0]))
            data_dict[server] = temp_list

        # Removes server if there's no data
        new_dict = {}
        for server in data_dict:
            if data_dict[server]:
                new_dict[server] = data_dict[server]

        Helpers.SaveData(new_dict, type="Memes")


class Other:
    @staticmethod
    async def PrepareWeatherData():
        """
        Called to give dict of weather data
        :return: 
        """
        # Receives Data
        forecast = forecastio.load_forecast(forecast_api_key, lat, lng)
        byHour = forecast.hourly()
        byCurrent = forecast.currently()
        byDaily = forecast.daily()

        # Creates hourly dict
        current_hour = working_on_hour = int(time.strftime('%I'))
        hourly_dict = {str(current_hour): byCurrent.temperature}  # Current time
        rain_dict = {str(current_hour): byCurrent.precipProbability}  # Current rain forecast
        # For each hourly data
        for item in byHour.data:
            working_on_hour += 1
            if working_on_hour > 12:  # Ensure time doesn't go over 12
                working_on_hour = 12 - working_on_hour
            hourly_dict[str(working_on_hour)] = item.temperature
            rain_dict[str(working_on_hour)] = item.precipProbability

        # 7 day Forecast
        working_on_hour = int(time.strftime('%I'))

    @staticmethod
    async def Change_Color(message):
        if not await CheckMessage(message, prefix=True, start="color"):
            return
        send_message = ""
        # TODO CHECK PERMISSIONS
        # Prepare encoded name (len=10)
        encoded_name = await Sys.Encode(int(message.author.id), 63)
        # Prepare guild
        guild = message.guild
        color_role = False

        # Get message down to hex code
        message.content = message.content[1:].lower().replace('color', '').strip().replace("#", "")

        # Go through the roles in the guild to see if it exists
        role_exists = False
        for role in guild.roles:
            if role.name.startswith(encoded_name):
                role_exists = role
                role_to_edit = role

        # Create Color item
        try:
            color = discord.Colour(int(message.content, 16))
        except:
            failure = "Please use a Hex Code. Try this link: "
            failure += Sys.Shorten_Link('https://www.webpagefx.com/web-design/color-picker/')
            second_message = await message.channel.send(failure)
            await asyncio.sleep(5)
            await second_message.delete()
            await message.delete()
            return

        role_name = encoded_name + ' color ' + message.author.name

        # If the role exists,
        if role_exists:
            await role_to_edit.edit(color=color, reason="Requested Change.")
            send_message = "Edited your role, `" + role_name + "` to change the color to " + message.content
            color_role = role_exists
            if role_exists not in message.author.roles:
                await message.author.add_roles(role_exists)

        # If it doesn't exist
        elif not role_exists:
            # Search each role the player has to see if the player is the only one in it
            individual_player_role = False
            for player_role in message.author.roles:
                # Iterates for each role the player has
                found = 0  # +1 for each player in the role
                for member in message.guild.members:
                    # Iterates for each member in the guild
                    if member != message.author and member != Vars.Bot.user:
                        if player_role in member.roles:
                            found += 1

                # If it is individual to the player
                if found == 0:
                    individual_player_role = player_role
                    try:
                        await message.guild.edit_role(individual_player_role, color=color)
                        send_message = 'Edited your role, `' + Sys.FirstCap(
                            individual_player_role.name) + \
                                       '` with the color `' + message.content + '`'
                        color_role = individual_player_role
                    except:
                        # Some issue
                        individual_player_role = False

            # No individual Role
            if not individual_player_role:
                new_role = await message.guild.create_role(name=role_name, color=color)
                await message.author.add_roles(new_role)
                if guild.id == Conversation.Server_IDs['Dmakir']:
                    for server_role in guild.roles:
                        if server_role.name == 'Chat':
                            await new_role.edit(position=server_role.position)
                send_message = "Created a new role, `" + role_name + "` with the color of " + message.content
                color_role = new_role
        if color_role:
            # Moves the color role above everything else
            highest_role = 1
            for hier_role in message.guild.role_hierarchy:
                if hier_role in message.author.roles:
                    if hier_role.color != '#000000':
                        highest_role = hier_role.position
                        print(highest_role, hier_role)
                        break
            if highest_role != 0:
                await color_role.edit(position=highest_role)
        await message.add_reaction(Conversation.Emoji['check'])
        sent = await message.channel.send(send_message, delete_after=10)

    @staticmethod
    async def YesNo(message):
        if not await CheckMessage(message, prefix=True, start="yesno"):
            return
        # Establish Emojis
        ThumbsUp = Conversation.Emoji['thumbsup']
        ThumbsDown = Conversation.Emoji['thumbsdown']
        StopEmoji = Conversation.Emoji['stop']

        await message.delete()
        # Format Embed
        message.content = message.content[1:].lower().replace('yesno', '').strip()
        to_send = '**YesNo:**  ' + Sys.FirstCap(message.content)
        to_send += '\n *- Please click thumbs up or thumbs down to respond "Yes" or "No"*'
        to_send += '\n *- By ' + message.author.mention + '*'
        # Send and add reactions
        new_msg = await message.channel.send(to_send)
        await new_msg.add_reaction(Conversation.Emoji['thumbsup'])
        await new_msg.add_reaction(Conversation.Emoji['thumbsdown'])

        pm_message = "I just created that Poll for you. If you want to stop it, add a stop_sign "
        pm_message += "reaction to that message! It looks like this:" + Conversation.Emoji['stop']
        pm_message += " and has the name: `:octagonal_sign:`"
        # Checks if user just got the pm
        async for past_message in message.author.history(limit=1):
            if past_message.content != pm_message:
                await message.author.send(pm_message)

        # LISTEN FOR REACTIONS
        async def remove_reaction(reaction, user):
            # Can remove a reaction without needing async
            await reaction.message.remove_reaction(reaction.emoji, user)
            return

        def check(reaction, user):
            # Makes sure its a Thumb Up, Thumbs down, or Stop Emoji.
            # Otherwise: Removes
            if user == Vars.Bot.user:
                return False
            if reaction.emoji in [ThumbsUp, ThumbsDown, StopEmoji] and reaction.message.id == new_msg.id:
                return reaction, user
            else:
                Vars.Bot.loop.create_task(remove_reaction(reaction, user))

        Stop = False  # Used when the cycle is finally stopped
        while not Stop:
            try:
                # Wait for the reaction(s)
                reaction, user = await Vars.Bot.wait_for('reaction_add', timeout=1200, check=check)

            except asyncio.TimeoutError:
                # If it times out
                Stop = "Timed Out"

                break

            if reaction.emoji == StopEmoji:
                # If user wants to stop it:
                Stop = "Stop Emoji"
                break

            message_reactions = reaction.message.reactions
            for p_reaction in message_reactions:  # For each reaction
                if p_reaction.emoji != reaction.emoji:  # If its not equal current emoji
                    people = await p_reaction.users().flatten()  # If they're in it
                    if user in people:
                        await new_msg.remove_reaction(p_reaction.emoji, user)

        # If it stops the loop:
        # Re-get the message
        new_msg = await message.channel.get_message(new_msg.id)
        await new_msg.remove_reaction(ThumbsDown, Vars.Bot.user)
        await new_msg.remove_reaction(ThumbsUp, Vars.Bot.user)

        said_yes, said_no = [], []
        for p_reaction in new_msg.reactions:
            if p_reaction.emoji == ThumbsUp:
                said_yes = await p_reaction.users().flatten()
            elif p_reaction.emoji == ThumbsDown:
                said_no = await p_reaction.users().flatten()

        mentions = new_msg.mentions
        new_content = new_msg.content.replace('**YesNo:**', '**Closed:**')  # Replace yesno with closed
        new_content = new_content.split('\n')  # Split into list by each line
        tally = "\n- *There were %s votes YES and %s votes NO.*" % (len(said_yes), len(said_no))

        yes_string, no_string = '', ''
        for person in said_yes:
            person = person.name
            if not yes_string:
                yes_string = '\n- **Yes**: ' + person
            else:
                yes_string += ', ' + person

        for person in said_no:
            person = person.name
            if not no_string:
                no_string = '\n- **No**: ' + person
            else:
                no_string += ', ' + person

        new_content = new_content[0] + tally + yes_string + no_string + '\n' + new_content[2]
        await new_msg.edit(content=new_content)

        await new_msg.clear_reactions()

    @staticmethod
    async def Poll(message):
        if not await CheckMessage(message, prefix=True, start="poll"):
            return

        not_symbols = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+/\\\'\".,~`<>: "
        message.content = message.content[1:].lower().replace("poll", "").strip()
        content = message.content.split("\n")
        to_send = ""
        title = content[0]
        sections_list = []
        for i in range(0, len(content)):  # For each line of the string
            if i != 0:  # Except the first part
                part = content[i].strip()
                emoji = False

                if part[0].lower() not in not_symbols:  # If its a known emoji
                    emoji = part[0]
                    part = part.strip()[1:]

                elif part[0] == "<":  # If its a custom emoji
                    counter = -1
                    emoji = ""
                    for letter in part:
                        counter += 1
                        emoji += letter
                        if letter == ">":  break
                    part = part[counter + 1:].strip()

                sections_list.append([part, emoji])

        if len(sections_list) > 10:
            msg = await message.channel.send("Too many options, the limit is 10.", delete_after=10)
            return
        await message.delete()
        for i in range(0, len(sections_list)):
            reg = ":regional_indicator_"
            alphabet = ['\U0001F1E6', '\U0001F1E7', '\U0001F1E8', '\U0001F1E9', '\U0001F1EA', '\U0001F1EB',
                        '\U0001F1EC', '\U0001F1ED', '\U0001F1EE', '\U0001F1EF']
            if not sections_list[i][1]:
                sections_list[i][1] = alphabet[i]

        for section in sections_list:
            new_append = "\n" + section[1] + "   " + Sys.FirstCap(section[0])
            to_send += new_append

        user_number = "http://" + str(message.author.id) + ".com"
        em = discord.Embed(description=to_send, colour=message.author.color, title="**Poll**: " + Sys.FirstCap(title))
        em.set_author(name=message.author.name + "#" + str(message.author.discriminator),
                      icon_url=message.author.avatar_url,
                      url=user_number)
        msg = await message.channel.send(embed=em)

        for section in sections_list:
            if section[1].startswith("<"):
                section[1] = section[1].replace('<', '').replace('>', '')
            await msg.add_reaction(section[1])

        # ===== WAIT ======
        list_of_emojis = []
        for section in sections_list:
            list_of_emojis.append(section[1])
        stop_emoji = Conversation.Emoji['stop']

        # Functions
        async def remove_reaction(reaction, user):
            # Can remove a reaction without needing async
            await reaction.message.remove_reaction(reaction.emoji, user)
            return

        def check(reaction, user):
            # Makes sure its a Thumb Up, Thumbs down, or Stop Emoji.
            # Otherwise: Removes
            if user == Vars.Bot.user:
                return False
            if msg.id == reaction.message.id and reaction.emoji in list_of_emojis:
                return reaction, user
            elif reaction.emoji == stop_emoji:
                originAuthor = message.author  # Original Author
                if user == originAuthor:
                    return reaction, user
                else:
                    return False
            elif msg.id == reaction.message.id:
                Vars.Bot.loop.create_task(remove_reaction(reaction, user))

        Stop = False
        while not Stop:
            try:
                reaction, user = await Vars.Bot.wait_for('reaction_add', timeout=1200, check=check)
            except asyncio.TimeoutError:
                stop = "Timed Out"
                break
            # If it got an emoji in the list, or stop

            if reaction.emoji == stop_emoji:
                stop = "Stopped"
                break

            message_reactions = reaction.message.reactions
            for p_reaction in message_reactions:
                if p_reaction.emoji != reaction.emoji:
                    people = await p_reaction.users().flatten()  # If they're in it
                    if user in people:
                        await reaction.message.remove_reaction(p_reaction.emoji, user)
        # When stopped:
        msg = await message.channel.get_message(msg.id)  # Get new msg
        originAuthor = message.author

        emoji_list = []
        response_list = []
        for part2 in msg.reactions:
            emoji_list.append(part2.emoji)
            people_exist = False
            people = await part2.users().flatten()
            for person in people:
                if person != Vars.Bot.user:
                    response_list.append(person.name)
                    people_exist = True
            if not people_exist:
                response_list.append("  ")

        embed = msg.embeds[0].to_dict()
        print(embed)
        old_description = embed['description'].split('\n')
        new_description = ""
        for i in range(0, len(old_description)):
            new_description += old_description[i] + "  -  *" + response_list[i] + "*" + "\n"

        em = discord.Embed(title="**Closed: **" + embed['title'].replace("**Poll**:", "").strip(),
                           description=new_description)
        em.set_author(name=originAuthor.name + "#" + str(originAuthor.discriminator),
                      icon_url=originAuthor.avatar_url,
                      url="http://" + str(originAuthor.id) + ".com")

        await msg.edit(embed=em)
        await msg.clear_reactions()
        return

    @staticmethod
    async def InterpretQuickChat():
        """
        Runs on start
        :return: a dict of each part of quickchat data
        """
        data = Helpers.RetrieveData("QuickChat")
        new_data = []
        # This part here deals with the lists as triggers
        for item in data:
            if type(item['trigger']) == str:
                new_data.append(item)
            elif type(item['trigger']) == list:
                for trigger in item['trigger']:  # for each trigger in the list:
                    temp_dict = {}
                    for key in item:  # For each part of the quickchat in question
                        temp_dict[key] = item[key]
                    temp_dict['trigger'] = trigger  # Replace trigger list with one trigger
                    new_data.append(temp_dict)

        TriggerList = []
        for key in new_data:
            TriggerList.append(key)

        Vars.QuickChat_Data = new_data
        Vars.QuickChat_TriggerList = TriggerList
        return

    @staticmethod
    async def QuickChat(message):
        chat_function = False
        for total_data in Vars.QuickChat_Data:
            if total_data["trigger"].lower() in message.content.lower():
                chat_function = total_data
                break
        if not chat_function:
            return

        channel = message.channel
        # Reply with Response
        if chat_function['type'] == 'reply':
            await channel.send(Sys.FirstCap(chat_function['use']))
            return
        # Reply with Random Response
        elif chat_function['type'] == 'conversation':
            if Sys.FirstCap(chat_function['use']) in Conversation.ReplyList:
                msg = Conversation.ReplyList[Sys.FirstCap(chat_function['use'])]
                await channel.send(Sys.Response(msg, message=message))
            return
        # Add Reaction
        elif chat_function['type'] == 'react':
            reaction = await message.add_reaction(Conversation.Emoji[chat_function['use']])
            return
        # Delete Message
        elif chat_function['type'] == 'delete':
            await message.delete()
            if chat_function['use']:
                msg = await channel.send(Sys.FirstCap(chat_function['use']))
            return
        # Autocorrect
        elif chat_function['type'] == 'autocorrect':
            trigger = Sys.FirstCap(chat_function['trigger'])
            correction = Sys.FirstCap(chat_function['use'])
            msg = '**AutoCorrect**:  You said `\'%s\'`, did you mean `\'%s\'`?' % (trigger, correction)
            await channel.send(msg)
            return
        return

    @staticmethod
    async def On_Member_Join(member):
        guild = member.guild
        channel_list = []
        for channel in guild.text_channels:
            channel_list.append(channel)
        default_channel = channel_list[0]

        description = "Account Created at: " + member.created_at.strftime("%H:%M:%S  on  %m-%d-%Y")
        description += "\nJoined Server at: " + datetime.datetime.now().strftime("%H:%M:%S  on  %m-%d-%Y")
        description += '\nID: `' + str(member.id) + '`'
        if member.bot:
            description += '\nYou are a bot. I do not like being replaced.'
        em = discord.Embed(description=description, colour=0xffffff)
        em.set_author(name=member.name + "#" + str(member.discriminator), icon_url=member.avatar_url)

        await default_channel.send("Welcome!", embed=em)

        # if guild == Vars.Bot.get_server(Conversation.Server_IDs['Dmakir']):
        #     await Cmd.Dmakir_New_Member(member, bot)

    @staticmethod
    async def On_Member_Remove(member):
        guild = member.guild
        channel_list = []
        for channel in guild.text_channels:
            channel_list.append(channel)
        default_channel = channel_list[0]

        reason = False
        async for entry in guild.audit_logs(limit=1):
            if str(entry.action) == 'AuditLogAction.kick' and entry.target.id == member.id:
                reason = "Kicked by " + Sys.FirstCap(entry.user.name)
            elif str(entry.action) == 'AuditLogAction.ban' and entry.target.id == member.id:
                reason = "Banned by " + Sys.FirstCap(entry.user.name)
            else:
                reason = "Left on their own terms."

        description = "**Reason: **" + reason
        description += '\n**ID:** `' + str(member.id) + '`'

        # Embed
        em = discord.Embed(description=description, colour=0xffffff, timestamp=datetime.datetime.now())
        em.set_author(name=member.name + " left.", icon_url=member.avatar_url)
        em.set_footer(text=Sys.FirstCap(guild.name), icon_url=guild.icon_url)

        await default_channel.send("Goodbye!", embed=em)

    @staticmethod
    async def On_Message_Delete(message):
        delete_from_redbot = False
        guild = message.guild
        # If the delete was on a Redbot message and not by an admin
        async for entry in guild.audit_logs(limit=1):
            if str(entry.action) == 'AuditLogAction.message_delete':
                if message.author == Vars.Bot.user and entry.user not in Ranks.Admins:
                    delete_from_redbot = entry.user.name
                else:
                    delete_from_redbot = False

        if delete_from_redbot:
            if message.content.startswith("Welcome!") or message.content.startswith("Goodbye!"):
                new_content = "**Reconstructed** after deletion attempt by %s at %s + \n" % \
                              (delete_from_redbot, datetime.datetime.now())
                message.content = new_content + message.content
                await message.channel.send(message.content, embed=message.embeds[0])

            elif message.content.startswith("**Reconstructed**"):
                content = message.content.split('\n')[1]
                new_content = "**Reconstructed** after deletion attempt by %s at %s + \n" % \
                              (delete_from_redbot, datetime.datetime.now())
                message.content = new_content + content
                await message.channel.send(message.content, embed=message.embeds[0])





class On_React:
    @staticmethod
    async def On_X(reaction, user):
        message = reaction.message
        total_users = await reaction.users().flatten()
        if Vars.Bot.user in total_users:  # If bot originally reacted X
            try:
                await message.delete()
            except discord.errors.NotFound:
                pass
            return

        # If bot didn't originally react:
        if user.id in Ranks.Admins:
            await message.add_reaction(Conversation.Emoji['check'])
            await asyncio.sleep(.4)
            await message.delete()
            return





async def test(message):
    if not await CheckMessage(message, prefix=True, start="test", admin=True):
        return
    # await message.author.send("1994920.28408880002")
    new_msg = await message.channel.send("Emoji me")
    await new_msg.add_reaction('\U0001f44e')
    await message.channel.send(new_msg.reactions[0].emoji)
