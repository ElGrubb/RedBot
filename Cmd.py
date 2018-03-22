import Sys, Conversation
import asyncio, random, time, discord, json, praw
from datetime import datetime, timedelta
import forecastio, os, sys, git, wolframalpha, traceback

# Reddit
reddit = praw.Reddit('bot1')

# Forecast
forecast_api_key = Sys.Read_Personal(data_type='Forecast_Key')
lat = 42.538690
lng = -71.046564

# Wolfram Alpha
wolfram_client = wolframalpha.Client(Sys.Read_Personal(data_type='Wolfram_Alpha_Key'))


class Ranks:
    Admins = [
        239791371110580225,  # Dom
        # 215639561181724672,  #Scangas
        211271446226403328,  # Tracy
        266454101766832131   # Louis
    ]
    NoUse = [
        ''
    ]
    Bots = [
        380212294837075969,  # GoldBot
        267070013096198144   # RedBot
    ]


class Vars:
    AdminCode = random.randint(0, 4000)
    Bot = None
    Disabled = False
    Disabler = None
    start_time = None
    Version = "4.15"

    if Sys.Read_Personal(data_type="Bot_Type") == "RedBot":
        Bot_Color = Sys.Colors["RedBot"]
    elif Sys.Read_Personal(data_type="Bot_Type") == "GoldBot":
        Bot_Color = Sys.Colors["GoldBot"]

    QuickChat_Data = []
    QuickChat_TriggerList = []


    Creator = None
    Ready = False


async def CheckPermissions(channel, nec, return_all=False):
    # Checks the guild to see which privileges the bot has
    # nec is a list of the privileges it requires
    if type(nec) == str:
        nec = [nec.strip()]

    bot_user = channel.guild.get_member(Vars.Bot.user.id)

    # Create list of permissions
    Perm_Dict = {}
    for permission in bot_user.permissions_in(channel):
        Perm_Dict[permission[0]] = permission[1]

    for item in nec:  # For each required in the command
        if item not in Perm_Dict:  # If its a nonexistant permission
            raise KeyError("Permission not normal one")

    if return_all and len(nec) > 1:
        to_return = {}
        for item in nec:
            to_return[item] = Perm_Dict[item]
        return to_return
    elif return_all and len(nec) == 1:
        return Perm_Dict[nec[0]]

    for item in nec:  # For each required in the command
        if not Perm_Dict[item]:  # If the bot doesn't have it:
            return False
    return True
    """ Here are the possible ones you can have:
    add_reactions
    administrator
    attach_files
    ban_members
    change_nickname
    connect
    create_instant_invite
    deafen_members
    embed_links
    external_emojis
    kick_members
    manage_channels
    manage_emojis
    manage_guild
    manage_messages
    manage_nicknames
    manage_roles
    manage_webhooks
    mention_everyone
    move_members
    mute_members
    read_message_history
    read_messages
    send_messages
    send_tts_messages
    speak
    use_voice_activation
    view_audit_log
    """


async def CheckMessage(message, start=None, notInclude=None, close=None, prefix=None, guild=None, sender=None, admin=None,
                       include=None):
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
    :param include:     Something that should be inside the message
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

    # Include
    if include:  # If there's a certain phrase the message should start with
        totalPossibleCorrect += 1
        if include.lower() in content.lower():
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
    async def Confirmation(message, text:str, yes_text=None, deny_text="Action Cancelled.", timeout=60,
                           return_timeout=False, deleted_original_message=False, mention=None, extra_text=None):
        """
        Sends a confirmation for a command
        :param message: The message object
        :param text: What the message of the embed should say
        :param yes_text: If you want a confirmed message to play for 4 seconds
        :param deny_text: If you want a message to play when x is hit. 
        :param timeout: How long to wait for a conclusion
        :param mention: If the bot should mention the player in the beginning
        :return: Returns True if Yes, False if No, and None if timed out. 
        """
        if type(message) == discord.message.Message:
            author = message.author
            channel = message.channel
            guild = message.guild
            is_message = True
        elif type(message) == discord.user.User:
            author = message
            channel = message
            guild = message
            is_message = False
        else:
            raise TypeError("Should never be called.")

        # Establish two emojis
        CancelEmoji = Conversation.Emoji['x']
        ContinueEmoji = Conversation.Emoji['check']

        if mention:
            before_message = mention.mention
        else:
            before_message = None

        em = discord.Embed(title=text, description=extra_text, timestamp=datetime.now(), colour=Vars.Bot_Color)

        em.set_author(name="Confirmation:", icon_url=Vars.Bot.user.avatar_url)
        # Send message and add emojis

        msg = await channel.send(before_message, embed=em)

        await msg.add_reaction(ContinueEmoji)
        await msg.add_reaction(CancelEmoji)

        def check(reaction, user):  # Will be used to validate answers
            # Returns if user is initial user and reaction is either of those
            if reaction.message.id != msg.id:
                return
            if user == author and str(reaction.emoji) in [CancelEmoji, ContinueEmoji]:
                return reaction, user

        try:
            # Wait for the reaction(s)
            reaction, user = await Vars.Bot.wait_for('reaction_add', timeout=timeout, check=check)

        except asyncio.TimeoutError:
            # If it times out
            try:
                await msg.delete()
            except discord.errors.NotFound:
                pass
            await channel.send(deny_text, delete_after=5)
            if return_timeout:
                return "Timed Out"
            else:
                return None

        # If they hit the X
        if reaction.emoji == CancelEmoji:
            await msg.delete()
            await channel.send(deny_text, delete_after=5)
            return False

        # If they hit the check
        elif reaction.emoji == ContinueEmoji:
            await msg.delete()
            if not deleted_original_message:
                if is_message:
                    await message.add_reaction(ContinueEmoji)
            if yes_text:
                await channel.send(yes_text, delete_after=5)
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

    @staticmethod
    async def AskQuestion(prompt, channel=None, timeout=30, sender=False, integer_answer=False, answers=None):
        """Ran when needed, prompts for question"""
        if not channel:
            raise ConnectionError("Need to specify some sort of channel")

        def check(m):
            if sender:
                if sender != m.author:
                    return False
            if integer_answer:
                try:
                    int(m.content.strip())
                except:
                    return False
            if answers:
                if m.content.strip().lower() not in answers:
                    Vars.Bot.loop.create_task(ifAnswers(m))
                    return False
            return True

        async def ifAnswers(m):
            """
            If the function is given a list of possible answers
            :param m: the message object
            :return: nothing. Sends message. 
            """
            possible_answers = ""
            for answer in answers:
                if possible_answers:
                    possible_answers += ", `" + Sys.FirstCap(answer) + "`"
                if not possible_answers:
                    possible_answers = "`" + Sys.FirstCap(answer) + "`"
            await m.channel.send("Not a valid response. Responses are: \n" + possible_answers, delete_after=60)

        msg = await channel.send(prompt)
        await msg.add_reaction(Conversation.Emoji['circle'])

        try:
            response = await Vars.Bot.wait_for('message', check=check, timeout=timeout)
            await msg.clear_reactions()
            return response
        except asyncio.TimeoutError:
            await msg.clear_reactions()
            await channel.send("Timed out.", delete_after=10)
            return None

    @staticmethod
    async def MessageAdmins(prompt, embed=None):
        Admin_List = []
        for admin in Ranks.Admins:
            Admin_List.append(Vars.Bot.get_user(admin))

        for admin in Admin_List:
            print("Messaged " + admin.name)
            if embed:
                await admin.send(prompt, embed=embed)
            else:
                await admin.send(prompt)

    @staticmethod
    async def FormatMessage(message, IncludeDate=False, IncludeArea=False, Markdown=True, FullName=False, Discriminator=False):
        """
            Prepares a message into a text object with certain specifications
            :param message: The message object
            :param IncludeDate: Include the date and time sent?
            :param IncludeArea: Include the server and channel?
            :param Markdown: Whether or not to include boldness, etc
            :param Discriminator: To include the #1241 after a person's name or not. 
            :return: A string containing everything. 
            """
        MessageContent = Sys.FirstCap(message.content)
        if message.attachments:
            MessageAttachments = "\nAttachments:"
            for item in message.attachments:
                MessageAttachments += " - **" + item.filename + "** - " + Sys.Shorten_Link(item.url)
        else:
            MessageAttachments = ""

        if FullName:  # If we want the full name
            MessageSender = Sys.FirstCap(message.author.name)
        else:  # If just nickname
            MessageSender = Sys.FirstCap(message.author.display_name)
        if IncludeArea + IncludeDate:
            MessageSender = " - " + MessageSender

        # Add the 4 digit code found after a user's name
        if Discriminator:
            MessageDiscriminator = "#" + message.author.discriminator
        else:
            MessageDiscriminator = ""

        # Add the Server and Channel it's from in the format 'Server/#Channel'
        if IncludeArea:
            MessageArea = message.guild.name + "/#" + message.channel.name
        else:
            MessageArea = ""

        # Add the date sent
        if IncludeDate:
            MessageDate = message.created_at.strftime("%x %X")
        else:
            MessageDate = ""

        if IncludeDate + IncludeArea == 2 and Markdown:
            # If there's a lot of things on the message:
            StartMessage = ":\n **\"** "
            EndMessage = " **\"**"
            BeforeAll = "="*25 + "\n"
        else:
            StartMessage = ": "
            EndMessage = ""
            BeforeAll = ""

        # Create the actual full string
        if Markdown:  # if it should be created in markdown format
            MessageSender = "**" + MessageSender + "**"
            MessageDiscriminator = " *" + MessageDiscriminator + "*" if Discriminator else ""
            MessageArea = " " + MessageArea + "" if IncludeArea else ""
            MessageDate = " " + MessageDate + "" if IncludeDate else ""

        EndString = BeforeAll + MessageDate + MessageArea + MessageSender + MessageDiscriminator
        EndString += StartMessage + MessageContent + EndMessage + MessageAttachments

        return EndString.strip()


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

        # If they just typed /delete:
        if not content:
            content = 1

        # Makes sure that it is a proper integer in the message
        try:
            content = int(content)
        except ValueError:
            await message.channel.send("Not a valid number of messages. Try again", delete_after=5)
            await asyncio.sleep(5)
            await message.delete()
            return

        # Cooldown Shit
        cd_notice = Cooldown.CheckCooldown("delete", message.author, message.guild)  # Do the cooldown CMD
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
    async def CopyFrom(message):
        if not await CheckMessage(message, start="Copy", prefix=True, admin=True):
            return

        content = message.content[5:].strip()
        if "embed" in content:
            content = content.lower().replace("embed","").strip()
            embed = True
        else:
            embed = False

        try:
            int(content)
        except:
            raise TypeError("/Copy {timestamp}")

        starttime = time.clock()

        timestamp = int(content)
        startreading = datetime.fromtimestamp(timestamp)

        await message.delete()

        channel = message.channel

        SendChannel = Vars.Bot.get_channel(425763690344611840)

        BotChannel = await channel.send("Working...")

        Counted = 0
        to_send = ""
        PreviousAuthor = None
        MessageString = ""
        async for foundmessage in channel.history(after=startreading, limit=1000):
            formatted = await Helpers.FormatMessage(foundmessage, IncludeDate=True, FullName=True)
            Counted += 1
            if embed:
                if foundmessage.author == PreviousAuthor:
                    MessageString += "\n" if MessageString else ""
                    MessageString += formatted
                else:

                    em = discord.Embed(description=foundmessage.content, timestamp=foundmessage.created_at)
                    em.set_author(name=foundmessage.author.name, url="http://" + str(foundmessage.author.id) + ".com", icon_url=foundmessage.author.avatar_url)
                    if foundmessage.attachments:
                        em.set_image(url=foundmessage.attachments[0].url)
                    await SendChannel.send(embed=em)
                    await BotChannel.edit(content="Working... #" + str(Counted))
            else:
                if len(to_send + formatted) < 1950:
                    # If there's room to add formatted:
                    to_send += "\n" + formatted

                else:
                    # If there's no room
                    await SendChannel.send(to_send)
                    to_send = formatted
                    await BotChannel.edit(content="Working... #" + str(Counted))

            PreviousAuthor = foundmessage.author

        await BotChannel.edit(content="Done   " + message.author.mention)
        await asyncio.sleep(5)
        await BotChannel.delete()
        await SendChannel.send(Vars.Creator.mention())


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
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Set up Time String
            await message.channel.send(Vars.Bot.user.name + " Left at " + current_time)  # Sends goodbye
            await message.guild.leave()  # Leaves

    @staticmethod
    async def Disable(message):
        if not await CheckMessage(message, prefix=True, admin=True, start="Disable"):
            return False
        if not await Helpers.Confirmation(message, "Disable?", deny_text="Will Stay Enabled."):
            return

        Vars.Disabled = True
        await Vars.Bot.change_presence(game=(discord.Game(name='Offline')), status=discord.Status.do_not_disturb)
        msg = await message.channel.send('Bot Disabled.')
        await asyncio.sleep(5)
        await message.channel.delete_messages([msg, message])
        Vars.Disabler = message.author.id

        # Wait to re-enable
        await asyncio.sleep(1200)
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
            Vars.Disabler = None
            return

    @staticmethod
    async def Enable(message):
        if not await CheckMessage(message, prefix=True, admin=True, start="Enable"):
            return True
        if Vars.Disabler:
            if message.author.id != Vars.Disabler and message.author.id != Vars.Creator.id:
                return

        Vars.Disabled = False
        Vars.Disabler = None
        await Vars.Bot.change_presence(status=discord.Status.online)
        msg = await message.channel.send('Bot Enabled.')
        await asyncio.sleep(5)
        await msg.delete()
        await message.channel.delete_messages([msg, message])

    @staticmethod
    async def Talk(message):
        if not await CheckMessage(message, start="Talk", prefix=True, admin=True):
            return
        """
        /talk server=server serverino, channel=hotel_lobby, Hello
        """
        server, channel = None, None
        content = message.content[5:].strip()
        if "-delay" in content:
            delay = True
            content = content.replace('-delay', "").strip()
        else:
            delay = False

        async def Ask(given_type, message, given_guild=None, ):
            """
            :param given_type: Either Server or Channel (no caps0
            :param message: original message
            :return: object of server
            """
            items_to_use = {}
            bot = Vars.Bot
            if given_type == "server":
                guild_list = bot.guilds  # list of all guilds
                for item in guild_list:  # Condense list into dict of name: object
                    items_to_use[item.name] = item
            elif given_type == "channel":
                channel_list = given_guild.channels  # list of all guilds
                for item in channel_list:  # Condense list into dict of name: object
                    if type(item) == discord.channel.TextChannel:
                        items_to_use[item.name] = item
            else:
                raise ValueError("Need to specify 'channel' or 'server'")

            ask_string = ""
            counter = -1
            ask_list = []
            for key in items_to_use:
                counter += 1
                if ask_string:
                    ask_string += "\n"
                ask_string += str(counter) + ": " + key
                ask_list.append(key)

            ask_message = await message.channel.send("Which " + given_type + " would you like to send to?\n" + ask_string)

            def Check(m):
                # Checks for response from user
                if m.channel == message.channel and m.author == message.author:
                    return True

            try:
                response_message = await bot.wait_for('message', check=Check, timeout=15)
            except asyncio.TimeoutError:
                await message.channel.send("Timed out", delete_after=10)
                await ask_message.delete()
                await message.add_reaction(Conversation.Emoji["x"])
                return

            # Now that we have a response:
            for name in items_to_use:
                if response_message.content.lower() in name.lower():
                    found = items_to_use[name]
                    await ask_message.delete()
                    return found

            # If it cannot find it:
            response = response_message.content
            try:
                num = int(response.strip())
                return items_to_use[ask_list[num]]  # num in ask list gives the name assigned to each num
            except:
                await message.channel.send("Cannot find " + response_message.content + " in the list. Try again?")
                return None

        guild = await Ask("server", message)
        if guild:
            channel = await Ask('channel', message, given_guild=guild)
        if guild and channel:
            if delay:
                response = await Helpers.Confirmation(message, "Click when ready", timeout=120)
                if not response:
                    return
            await channel.send(content)
            await message.channel.send("Successfully sent message")
            return
        # if "server=" in content:
        #     # If user defined server in the message's content:
        #     server_name, channel_name = "", ""
        #     split_content = content.split(",")
        #     for part in split_content:
        #         # For each part in the message (remember the syntax!)
        #         if part.strip().startswith("server="):
        #             server_name = part

    @staticmethod
    async def Status(message):
        if not await CheckMessage(message, prefix=True, start="status", admin=True):
            return
        sentTime = message.created_at
        recievedTime = datetime.utcnow()
        difference = recievedTime - sentTime

        now = datetime.utcnow()
        delta = now - Vars.start_time
        delta = delta.total_seconds()

        sendmsg = "Bot is ONLINE"
        sendmsg += "\n**Speed:** " + str(difference)[5:] + " seconds. "
        sendmsg += "\n**Uptime:** " + Sys.SecMin(int(delta))
        em = discord.Embed(title="Current Status", timestamp=datetime.now(), colour=Vars.Bot_Color,
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
            "Type": "Restart",
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
            to_send = "Successfully Completed a `Full` " + restart_data["Type"]
            await channel.send(to_send)
            restart_data["Restarted"] = False
            Helpers.SaveData(restart_data, type="System")

            if restart_data["Type"] == "Update":
                await Admin.OnUpdate(restart_data["Channel_ID"])

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

        if "Already" in output:
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

    @staticmethod
    async def SaveDataFromMessage(message):
        # BROKEN!
        """
        Guides through the process of saving data to the remote bot from a discord message.
        :param message: The message object
        :return: Nothing, but should save the data.
        """
        if not await CheckMessage(message, start="SaveData", prefix=True, admin=True):
            return
        channel = message.channel

        currentData = Helpers.RetrieveData()

        if not await Helpers.Confirmation(message, "THIS IS BROKEN. CONTINUE?"):
            return

        def check(m):
            # Checks if correct author and channel
            if m.channel.id == channel.id and m.author.id == message.author.id:
                return True

        # Asks for data type
        msg = await channel.send("What type of data would you like to create?")
        response = await Vars.Bot.wait_for("message", check=check)
        await channel.delete_messages([msg, response])

        looking_for = Sys.FirstCap(response.content).strip().replace(" ", "_")
        if looking_for not in currentData:
            confirmation = await Helpers.Confirmation(message, "Cannot find data type. Continue?", timeout=30)
            if not confirmation:
                # If they do not want to continue
                return

        to_load = ""
        is_long = await Helpers.Confirmation(message, "Is it longer than 2000?")
        if not is_long:
            msg = await channel.send("Please send the json.dumps string.")
            response = await Vars.Bot.wait_for("message", check=check)
            await channel.delete_messages([msg, response])
            to_load = response.content

        else:
            stop = False
            total_string = ""
            while not stop:
                msg = await channel.send("Send it in pieces. send `done` when done")
                response = await Vars.Bot.wait_for("message", check=check)
                await channel.delete_messages([msg, response])

                if response.content.lower() == "done":
                    to_load = total_string
                    stop = True

                else:
                    total_string += response.content.strip()

        new_json = json.loads(to_load)

        Helpers.SaveData(new_json, type=looking_for)
        msg = await channel.send("Success.")

    @staticmethod
    async def OnUpdate(channel):
        # to_add = "\n\n@Dom_ID\n239791371110580225"
        # with open("Personal.txt", "r") as file:
        #     lines = file.read()
        #     file.close()
        # with open("Personal.txt", "w") as file:
        #     file.write(lines + to_add)
        #     file.close()
        # await channel.send("Successfully Migrated Help Text")
        pass

    @staticmethod
    async def SendData(message):
        if not await CheckMessage(message, start="download data", prefix=True, admin=True):
            return

        content = message.content[1:].replace("download data", "").strip()
        data = Helpers.RetrieveData()
        if content:
            if content not in data:
                await message.channel.send("could not find data type. Types are:")
                error_string = ""
                for key in data:
                    error_string = error_string + key + "    "
                await message.channel.send(error_string)
                return
            else:
                data = data[content]

        if not await Helpers.Confirmation(message, "Send data?"):
            return

        pretty_print = await Helpers.Confirmation(message, "Do you want it to be pretty print?")

        # Prepare data
        if pretty_print:
            send_string = json.dumps(data, indent=2)
        else:
            send_string = json.dumps(data)

        def Split_Text(start, looking_for):
            """
            Splits a good text at the closets item to the starting index
            :param start:  A number, the length of the string
            :param looking_for:  What are we looking for to split it at?
            :return:  first_string, second_string without the looking_for inbetween
            """

        while len(send_string) >= 2000:
            await message.channel.send(send_string[0:2000])
            send_string = send_string[2000:]
        if len(send_string) >= 0:
            await message.channel.send(send_string)

    @staticmethod
    async def ChangePersonal(message):
        if not await CheckMessage(message, start="change personal", prefix=True, admin=True):
            return
        if message.author != Vars.Creator:
            return

        content = message.content[16:].strip()

        if not await Helpers.Confirmation(message, "Add " + content + " To Personal? Cannot be reversed."):
            return

        content = content.split(":")
        if type(content) != list:
            await message.channel.send("Use this format:  `Key: Value`")
            return
        while len(content) > 2:
            content[1] = content[1] + ":" + content[2]
            del content[2]

        to_add = "\n\n" + content[0] + "\n" + content[1]

        with open("Personal.txt", "r") as file:
            lines = file.read()
            file.close()
        with open("Personal.txt", "w") as file:
            file.write(lines + to_add)
            file.close()

        await message.delete()
        await message.channel.send("Success. ", delete_after=20)

    @staticmethod
    async def Broadcast(message):
        if not await CheckMessage(message, admin=True, prefix=True, start="broadcast"):
            return

        if not await Helpers.Confirmation(message, "Are you sure you want to broadcast?"):
            return

        message.content = message.content[1:].replace("broadcast", "").strip()

        await Helpers.MessageAdmins(message.content)

    @staticmethod
    async def SinglePrivateMessage(message):
        if not await CheckMessage(message, admin=True, prefix=True, start="p "):
            return
        # This will delete any message that starts with /p after 20 seconds

        await message.add_reaction(Conversation.Emoji["x"])

        SecretChannel = Vars.Bot.get_channel(Sys.Channel["DeleteLog"])

        SecretContent = await Helpers.FormatMessage(message, IncludeArea=True, FullName=True)

        await SecretChannel.send(SecretContent)
        await asyncio.sleep(20)
        await message.delete()

    @staticmethod
    async def Juliana(message):
        if message.author.id != 277152050305957889:
            return
        if message.guild.id != 215639569071210496:
           return


        emoji = discord.utils.get(message.guild.emojis, name='spookolz')
        if emoji:
            await message.add_reaction(emoji)
            await asyncio.sleep(10*60)
            if message:
                await message.clear_reactions()

class Cooldown:
    meme_types = ["meme", "quote", "nocontext", "delete"]
    data = {}
    defaults = {
        "meme": [30, 30],
        "quote": [60, 45],
        "nocontext": [5, 10],
        "delete": [5, 3]
    }

    @staticmethod
    def TimeStamp():
        return int(datetime.now().timestamp())

    @staticmethod
    async def SetUpCooldown():
        for meme_type in Cooldown.meme_types:
            Cooldown.data[meme_type] = {}

    @staticmethod
    def AddUser(meme_type, user, guild):
        # Make sure to turn user into user id
        if user not in Cooldown.data[meme_type]:  # If it doesn't exist so far
            addition = {
                "guild": guild,  # Server ID
                "user": user,  # User ID
                "times": 1,  # How many times they have done it since its hit 0
                "wait": Cooldown.defaults[meme_type][0],  # How long to wait until they can do it again
                "refrac": Cooldown.defaults[meme_type][1],  # How long to wait after they can do it before it goes to 0
                "call": Cooldown.TimeStamp()

            }
            Cooldown.data[meme_type][user] = addition  # Set Cooldown.data[meme_type] with a new user as that user
            return 60

    @staticmethod
    def UpdateUser(meme_type, user, guild):
        if user in Cooldown.data[meme_type]:  # IF the ID is existing
            Cooldown.data[meme_type][user]["times"] += 1
            Cooldown.data[meme_type][user]["wait"] += round(
                (Cooldown.defaults[meme_type][0] * Cooldown.data[meme_type][user]["times"] / 2))
            Cooldown.data[meme_type][user]["refrac"] = int(Cooldown.data[meme_type][user]["wait"] / 2)
            Cooldown.data[meme_type][user]["call"] = Cooldown.TimeStamp()

            if Cooldown.data[meme_type][user]["wait"] > 600:
                Cooldown.data[meme_type][user]["wait"] = 540
                Cooldown.data[meme_type][user]["refrac"] = 480

            return Cooldown.data[meme_type][user]["wait"]


    @staticmethod
    def CheckCooldown(meme_type, user, guild):
        now = Cooldown.TimeStamp()
        user = int(user.id)
        guild = int(guild.id)

        Cooldown.data = Cooldown.data  # Doesn't work without this line...

        # Runs when a command is fired.
        if user not in Cooldown.data[meme_type]:  # Adds person to database
            Cooldown.AddUser(meme_type, user, guild)
            return False
        elif user in Cooldown.data[meme_type]:  # If they're already in
            wait = Cooldown.data[meme_type][user]["wait"]
            refrac = Cooldown.data[meme_type][user]["refrac"]
            change = now - Cooldown.data[meme_type][user]["call"]

            if change >= wait:  # If wait ime is over
                if change >= wait + refrac:  # If refrac time is over
                    del Cooldown.data[meme_type][user]
                    Cooldown.AddUser(meme_type, user, guild)
                    return False
                else:
                    Cooldown.UpdateUser(meme_type, user, guild)
            else:  # If cool down is still going
                return wait - change
        return True


class Timer:
    @staticmethod
    def DigitTime():
        hour = time.strftime('%H')
        minute = time.strftime('%M')
        return hour + ':' + minute

    @staticmethod
    async def TimeThread():
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
                    today = datetime.now().strftime("%B %d")
                    print("Good Morning! It is " + today)
                    await Other.T_Weather()


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
        cd_notice = Cooldown.CheckCooldown("quote", message.author, message.guild)
        if type(cd_notice) == int:
            msg = await message.channel.send('Cooldown Active, please wait: `' + Sys.SecMin(cd_notice) + '`')
            await asyncio.sleep(5)
            await message.channel.delete_messages([msg, message])
            return

        # Get Quote Dict
        data = Helpers.RetrieveData(type="Quotes")
        chosen_quote = data["info"][data["position"]]

        # Update Quote List etc
        data["position"] += 1
        if data["position"] >= len(data["info"]):
            random.shuffle(data["info"])
            data["position"] = 0
        Helpers.SaveData(data, type="Quotes")

        # Modify the Data a bit
        date = datetime.fromtimestamp(chosen_quote["date"])
        quote = "**\"**" + chosen_quote["quote"] + "**\"**"
        sender_obj = await Vars.Bot.get_user_info(chosen_quote["user_id"])

        # Prepare the Embed
        em = discord.Embed(title=quote, timestamp=date, colour=Vars.Bot_Color)
        em.set_footer(text="Saved Quote", icon_url=message.guild.icon_url)
        em.set_author(name=sender_obj.name, icon_url=sender_obj.avatar_url)

        await message.channel.send(embed=em)

    @staticmethod
    async def CheckTime():
        # Right now itll always return true
        return True

        hour = datetime.now().hour
        if 1 < hour < 6:
            return False
        else:
            return True

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

        if not await Quotes.CheckTime():
            await message.channel.send("Quote Functionality no longer works this late at night.", delete_after=5)
            await message.delete()
        # Seperate reactioned user from the message
        mention_user = message.mentions[0]
        content = message.clean_content[7:].replace("@" + mention_user.name, '').strip()

        # Create Embed
        em = discord.Embed(title="Quote this?", timestamp=datetime.now(), colour=Vars.Bot_Color,
                           description="**\"**" + content + "**\"**")
        em.set_author(name=mention_user, icon_url=mention_user.avatar_url)
        em.set_footer(text="10 minute timeout")

        # Send Message
        msg = await message.channel.send("Create Quote?", embed=em)

        def check(init_reaction, init_user):  # Will be used to validate answers
            # Returns if there are 3 more reactions who aren't this bot
            if init_reaction.message.id != msg.id or init_user.id == Vars.Bot.user.id:
                return False
            if init_reaction.count >= 6 and init_reaction.emoji == Conversation.Emoji["quote"]:
                return init_reaction, init_user
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

        if not await Quotes.CheckTime():
            await reaction.message.channel.send("Quote Functionality no longer works this late at night.", delete_after=5)
            await reaction.message.clear_reactions()
            return

        if reaction.count >= 5:
            await reaction.message.clear_reactions()
            await reaction.message.add_reaction(Conversation.Emoji["check"])
            await Quotes.NoteQuote(quote=reaction.message.content, user=reaction.message.author)
            await reaction.message.channel.send("Saved quote \"" + reaction.message.content + "\"")

    @staticmethod
    async def NoteQuote(quote=None, user=None):
        date = datetime.now()
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

        await channel.trigger_typing()

        # Remove everything but the type of meme to send
        content = content[1:]
        content = content[0:len(content) - 1] if content[-1].strip().lower() == 's' else content # Remove trailing "s"
        content = content.replace('send', '').strip()  # Remove send

        # Make sure content is in subs
        if content not in Memes.subs:
            possible_subs = "`"  # list of all possible send types
            for key in Memes.subs:
                if possible_subs is not "`":
                    possible_subs += ", " + Sys.FirstCap(key)
                else:
                    possible_subs += Sys.FirstCap(key)
            possible_subs += "`"
            await channel.send("\"" + content + "\" is not a valid type. Possible types are:\n" + possible_subs)
            return
        # CoolDown Shit
        if not is_repeat:
            cd_notice = Cooldown.CheckCooldown("meme", message.author, message.guild)
            if type(cd_notice) == int:
                await channel.send('Cooldown Active, please wait: `' + Sys.SecMin(cd_notice) + '`', delete_after=5)
                await message.add_reaction(Conversation.Emoji["x"])
                return

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
            em = discord.Embed(title=found_meme.title, timestamp=datetime.now())
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
            if init_reaction.message.id != msg.id:
                return
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
                try:
                    await msg.clear_reactions()
                except discord.errors.NotFound:
                    pass
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

        # If they just want their own color
        if message.content == "info":
            member = message.guild.get_member(message.author.id)
            await message.channel.send("Your current color is " + str(member.color))
            return

        # Go through the roles in the guild to see if it exists
        role_exists = False
        for role in guild.roles:
            if role.name.startswith(encoded_name):
                role_exists = role
                role_to_edit = role

        if message.content == "clear":
            await message.author.remove_roles(role_to_edit)
            await message.channel.send("Removed your role")
            return

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
            if user == Vars.Bot.user or reaction.message.id != new_msg.id:
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
        # PRepare the message for interpretation
        not_symbols = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+/\\\'\".,~`<>: "
        message.content = message.content[1:].lower().replace("poll", "").strip()
        content = message.content.split("\n")
        to_send = ""
        title = content[0]
        sections_list = []
        # Go through it and interpret each line
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
                        if letter == ">": break
                    part = part[counter + 1:].strip()

                sections_list.append([part, emoji])

        if len(sections_list) > 10:
            msg = await message.channel.send("Too many options, the limit is 10.", delete_after=10)
            return
        await message.delete()

        if not sections_list:
            await message.channel.send("Woah woah woah, you need some options")
            return

        # Add emojis to those that don't have them
        for i in range(0, len(sections_list)):
            reg = ":regional_indicator_"
            alphabet = ['\U0001F1E6', '\U0001F1E7', '\U0001F1E8', '\U0001F1E9', '\U0001F1EA', '\U0001F1EB',
                        '\U0001F1EC', '\U0001F1ED', '\U0001F1EE', '\U0001F1EF']
            if not sections_list[i][1]:
                sections_list[i][1] = alphabet[i]

        # Set up each line to print
        for section in sections_list:
            new_append = "\n" + section[1] + "   " + Sys.FirstCap(section[0])
            to_send += new_append

        # User ID can be found as a url link
        user_number = "http://" + str(message.author.id) + ".com"
        em = discord.Embed(description=to_send, colour=message.author.color, title="**Poll**: " + Sys.FirstCap(title))
        em.set_author(name=message.author.name + "#" + str(message.author.discriminator),
                      icon_url=message.author.avatar_url,
                      url=user_number)
        msg = await message.channel.send(embed=em)  # Send embedded message

        # Add reactions
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
                if user == originAuthor or user == Vars.Creator:
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
        for part2 in msg.reactions:  # For each Reaction
            emoji_data = {}
            emoji_list.append(part2.emoji)  # Add the emoji symbol to emoji_list
            emoji_data["emoji"] = part2.emoji
            people_exist = False
            people = await part2.users().flatten()  # All people for said emoji
            emoji_user_string = ""
            for person in people:  # for each person
                if person != Vars.Bot.user:  # If the person isn't a bot
                    if emoji_user_string:
                        emoji_user_string += ", " + person.name
                    else:
                        emoji_user_string = person.name
                        people_exist = True
            if not people_exist:
                emoji_user_string = "   "
            emoji_data["users"] = emoji_user_string
            response_list.append(emoji_data)
        embed = msg.embeds[0].to_dict()
        old_description = embed['description'].split('\n')
        new_description = ""
        for i in range(0, len(old_description)):
            new_description += old_description[i] + "  -  *" + response_list[i]["users"] + "*" + "\n"

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
        if message.author.id in Ranks.Bots:
            return

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
        description += "\nJoined Server at: " + datetime.now().strftime("%H:%M:%S  on  %m-%d-%Y")
        description += '\nID: `' + str(member.id) + '`'
        if member.bot:
            description += '\nYou are a bot. I do not like being replaced.'
        em = discord.Embed(description=description, colour=0xffffff)
        em.set_author(name=member.name + "#" + str(member.discriminator), icon_url=member.avatar_url)
        em.set_footer(text=Sys.FirstCap(guild.name), icon_url=guild.icon_url)

        permissions = await CheckPermissions(default_channel, ["send_messages", "change_nickname"], return_all=True)

        # Add to audit log
        if permissions["change_nickname"]:
            bot_member = guild.get_member(Vars.Bot.user.id)
            old_name = bot_member.name
            await bot_member.edit(nick="Thinking...", reason=member.name + " joined.")
            await bot_member.edit(nick=old_name)

        # Send the message
        if permissions['send_messages']:
            await default_channel.send("Welcome!", embed=em)
        else:
            for channel in guild.text_channels:
                if await CheckPermissions(channel, "send_messages"):
                    await channel.send("Welcome!", embed=em)
                    return
            await Helpers.MessageAdmins("Cannot send this in " + guild.name + "\nWelcome!", embed=em)

    @staticmethod
    async def On_Member_Remove(member):
        guild = member.guild
        channel_list = []
        for channel in guild.text_channels:
            channel_list.append(channel)
        default_channel = channel_list[0]

        permissions = await CheckPermissions(default_channel, ["view_audit_log", "send_messages", "change_nickname"], return_all=True)
        if permissions["view_audit_log"]:
            reason = False
            async for entry in guild.audit_logs(limit=1):
                if str(entry.action) == 'AuditLogAction.kick' and entry.target.id == member.id:
                    reason = "Kicked by " + Sys.FirstCap(entry.user.name)
                elif str(entry.action) == 'AuditLogAction.ban' and entry.target.id == member.id:
                    reason = "Banned by " + Sys.FirstCap(entry.user.name)
                else:
                    reason = "Left on their own terms."
        else:
            reason = "[*Unable to read Audit Log*]"

        description = "**Reason: **" + reason
        description += '\n**ID:** `' + str(member.id) + '`'

        # Embed
        em = discord.Embed(description=description, colour=0xffffff, timestamp=datetime.now())
        em.set_author(name=member.name + " left.", icon_url=member.avatar_url)
        em.set_footer(text=Sys.FirstCap(guild.name), icon_url=guild.icon_url)

        # Add to audit log
        if permissions["change_nickname"]:
            bot_member = guild.get_member(Vars.Bot.user.id)
            old_name = bot_member.name
            await bot_member.edit(nick="Thinking...", reason=member.name + " left.")
            await bot_member.edit(nick=old_name)

        # Send the message
        if permissions['send_messages']:
            await default_channel.send("Goodbye!", embed=em)
        else:
            for channel in guild.text_channels:
                if await CheckPermissions(channel, "send_messages"):
                    await channel.send("Goodbye!", embed=em)
                    return
            await Helpers.MessageAdmins("Cannot send this in " + guild.name + "\nGoodbye!", embed=em)

    @staticmethod
    async def On_Message_Delete(message):
        delete_from_redbot = False
        if Vars.Disabled:
            return
        guild = message.guild
        if str(message.channel).startswith("Direct Message"):
            return

        created_at = time.mktime(message.created_at.timetuple())
        now_time = time.mktime(datetime.utcnow().timetuple())
        secondsDiff = (now_time - created_at)
        maxSeconds = 60 * 60 * 4  # 4 hours

        if not message.author.bot:  # If neither of these things are true, so it's just any other msssage, log it
            DeleteLoggerChannel = Vars.Bot.get_channel(Sys.Channel["DeleteLog"])
            LoggedMessage = await Helpers.FormatMessage(message, IncludeArea=True, FullName=True, Discriminator=True, IncludeDate=True)
            await DeleteLoggerChannel.send(LoggedMessage)
            return

        recent_from_bot = False
        if maxSeconds > secondsDiff:  # If the message was sent less than 4 hours ago
            if message.author == Vars.Bot.user:
                recent_from_bot = True

        permissions = await CheckPermissions(message.channel, ["send_messages", "view_audit_log"], return_all=True)
        if permissions['view_audit_log']:
            # If the delete was on a RedBot message and not by an admin
            async for entry in guild.audit_logs(limit=1):
                if str(entry.action) == 'AuditLogAction.message_delete':
                    if message.author == Vars.Bot.user and entry.user not in Ranks.Admins:
                        delete_from_redbot = entry.user.name
                    else:
                        delete_from_redbot = False
        else:  # if it can't see the audit log
            if recent_from_bot:
                delete_from_redbot = "`Unknown`"
            else:
                delete_from_redbot = False

        async def Attempt_To_Send(message, content, embed):
            """Ran if it cannot send the message"""
            guild = message.guild
            channel = message.channel
            sent = False
            for channel in guild.text_channels:
                if await CheckPermissions(channel, "send_messages"):
                    await channel.send(content, embed=embed)
                    sent = True
                    break
            if not sent:
                await Helpers.MessageAdmins("Cannot send this in " + guild.name + "\n" + content, embed=embed)

        if delete_from_redbot:
            if message.content.startswith("Welcome!") or message.content.startswith("Goodbye!"):
                new_content = "**Reconstructed** after deletion attempt by %s at %s + \n" % \
                              (delete_from_redbot, datetime.now())
                message.content = new_content + message.content
                if permissions['send_messages']:
                    await message.channel.send(message.content, embed=message.embeds[0])
                else:
                    await Attempt_To_Send(message, message.content, embed=message.embeds[0])

            elif message.content.startswith("**Reconstructed**"):
                content = message.content.split('\n')[1]
                new_content = "**Reconstructed** after deletion attempt by %s at %s + \n" % \
                              (delete_from_redbot, datetime.now())
                message.content = new_content + content
                if permissions['send_messages']:
                    await message.channel.send(message.content, embed=message.embeds[0])
                else:
                    await Attempt_To_Send(message, message.content, embed=message.embeds[0])



    @staticmethod
    async def FakeJoin(message):
        if not await CheckMessage(message, start="FakeJoin", prefix=True, admin=True):
            return


        guild = bot.get
        channel_list = []
        for channel in guild.text_channels:
            channel_list.append(channel)
        default_channel = channel_list[0]

        description = "Account Created at: " + member.created_at.strftime("%H:%M:%S  on  %m-%d-%Y")
        description += "\nJoined Server at: " + datetime.now().strftime("%H:%M:%S  on  %m-%d-%Y")
        description += '\nID: `' + str(member.id) + '`'
        if member.bot:
            description += '\nYou are a bot. I do not like being replaced.'
        em = discord.Embed(description=description, colour=0xffffff)
        em.set_author(name=member.name + "#" + str(member.discriminator), icon_url=member.avatar_url)
        em.set_footer(text=Sys.FirstCap(guild.name), icon_url=guild.icon_url)

        permissions = await CheckPermissions(default_channel, ["send_messages", "change_nickname"], return_all=True)

        # Add to audit log
        if permissions["change_nickname"]:
            bot_member = guild.get_member(Vars.Bot.user.id)
            old_name = bot_member.name
            await bot_member.edit(nick="Thinking...", reason=member.name + " joined.")
            await bot_member.edit(nick=old_name)

        # Send the message
        if permissions['send_messages']:
            await default_channel.send("Welcome!", embed=em)

    @staticmethod
    async def OldWeather(message, morning=False):
        if not morning:
            if not await CheckMessage(message, prefix=True, start="Weather"):
                return
        forecast = forecastio.load_forecast(forecast_api_key, lat, lng)
        byHour = forecast.hourly()
        byCurrent = forecast.currently()
        byDaily = forecast.daily()
        response = Sys.Response(Conversation.WeatherResponse)
        msg = '```md\n# Weather Forcast for Lynnfield:'
        msg += '\n- Currently ' + str(round(byHour.data[0].temperature)) + ' degrees'
        if str(round(byHour.data[0].apparentTemperature)) != str(round(byHour.data[0].temperature)):
            msg += ' but it feels like ' + str(round(byHour.data[0].apparentTemperature))
        msg += '.\n- It is ' + byCurrent.summary
        msg += '\n- I predict that there will be ' + byHour.summary
        msg += '\n# Hourly Forcast:'
        data = 7 if not morning else 15
        for i in range(0, data):
            new_time = the_time = int(time.strftime('%I')) + i
            if new_time > 12:
                new_time += -12
                the_time = new_time
                new_time = str(new_time) + 'AM' if time.strftime('%p') == 'PM' else str(new_time) + 'PM'
            else:
                new_time = str(new_time) + 'PM' if time.strftime('%p') == 'PM' else str(new_time) + 'AM'
            dot = ' ' if the_time < 10 else ''
            msg += '\n- ' + dot + new_time + "  -  " + str(round(byHour.data[i].temperature))
            msg += " degrees  -  " + str(round(byHour.data[i].precipProbability * 100)) + "%"

        msg += '\n# Seven Day Forecast:'
        byDay = forecast.daily()
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        weekday = int(time.strftime('%w'))
        msg += '\n *Weekday   Date     Low    High   Precip.*'
        date = int(time.strftime('%d'))
        months31 = [1, 3, 5, 7, 8, 10, 12]
        for i in range(0, 7):
            day = days[weekday + i] if weekday + i < 7 else days[(weekday + i) - 7]
            divider = ' ' * (9 - len(day))
            monthdate = date + i
            if int(time.strftime('%m')) in months31 and monthdate > 31:
                monthdate += -31
            elif int(time.strftime('%m')) == 2 and monthdate > 28:
                monthdate += -28
            elif int(time.strftime('%m')) not in months31 and monthdate > 30:
                monthdate += -30

            monthdate = '0' + str(monthdate) if monthdate < 10 else str(monthdate)
            msg += '\n- ' + day + divider + ' (' + monthdate + ')' + '  ~  ' + str(round(byDay.data[i].temperatureMin))
            msg += '  ~  ' + str(round(byDay.data[i].temperatureMax))
            msg += '  ~  ' + str(round(byDay.data[i].precipProbability * 100)) + '%'

        msg += '\n# Today\'s Facts:'
        msg += '\n- Cloud Cover: ' + str(round(100 * byCurrent.cloudCover)) + '%'
        msg += '```'
        channel = message.channel if not morning else message
        # Timer tells if the weather comes on a channel or not
        # em = discord.Embed(title=response, description=msg, colour=0x4286f4)
        # em.set_author(name='The Weather', icon_url=bot.user.avatar_url)

        await channel.send(response + msg)

    @staticmethod
    async def T_Weather():
        guild = Vars.Bot.get_guild(Conversation.Server_IDs['Dmakir'])
        channel_list = []
        for channel in guild.text_channels:
            channel_list.append(channel)
        default_channel = channel_list[0]

        if default_channel:
            await Other.OldWeather(default_channel, morning=True)

    @staticmethod
    async def Calculate(message):
        if not await CheckMessage(message, prefix="="):
            return

        if message.content.startswith('='):  # Remove any beginning =
            message.content = message.content[1:len(message.content)]
        if message.content.startswith('='):  # If there's a second, return
            return
        if not message.content:
            return

        await message.channel.trigger_typing()
        res = wolfram_client.query(message.content)

        if res['@success'] == 'false':  # If it can't find anything
            msg = await message.channel.send('Hmmm, I can\'t seem to figure that one out. Try Rephrasing?')
            return

        # We're looking for input_pod and detail_pod_1
        input_pod, result_pod, detail_pod_1 = False, False, False
        for pod in res.pods:
            if pod['@id'] == 'Input':
                input_pod = pod
            elif pod['@title'] == 'Result':
                result_pod = pod
            if pod['@position'] == '300':
                detail_pod_1 = pod
        if not result_pod:
            try:
                result_pod = next(res.results)
            except:
                result_pod = None
                for new_pod in res.pods:
                    if new_pod['@position'] == '200':
                        result_pod = new_pod
                if not result_pod:
                    msg = await message.channel.send('Hmmm, I can\'t seem to figure that one out. Try Rephrasing?')
                    return
        if detail_pod_1 == result_pod:
            detail_pod_1 = False

        # So now we figure out what to write for each
        input_text, detail_text, result_text = [], [], []
        for subpod in input_pod.subpods:  # INPUT POD
            input_text.append(subpod.plaintext)

        for subpod in result_pod.subpods:
            result_text.append(subpod.plaintext)

        if detail_pod_1:
            for subpod in detail_pod_1.subpods:
                detail_text.append(subpod.plaintext)

        if len(input_text) == 1:
            input_text = input_text[0]
        else:
            temp_text = []
            for part in input_text:
                if temp_text:
                    temp_text += '\n' + part
                else:
                    temp_text = part
            input_text = temp_text

        # Okay so I hate this part but I do it anyway
        if not result_text[0]:
            result_text = ''
        elif len(result_text) == 1:  # Brings down to 1 text if only 1 elin list
            result_text = result_text[0].split('\n')
            if len(result_text) == 1:
                result_text = result_text[0]

        if not detail_text[0]:
            detail_text = ''
        elif len(detail_text) == 1:  # Brings down to 1 text if only 1 elin list
            detail_text = detail_text[0].split('\n')
            if len(detail_text) == 1:
                detail_text = detail_text[0]

        # Okay so now we construct the answer
        to_send = '**Input Interpretation:**  `'  # Begin the message
        to_send += input_text + '`'
        to_send += '\n**Result:**  ' if result_text else ''
        if type(result_text) == list:
            to_send += '```'
            for part in result_text:
                to_send += '\n' + part
            to_send += '```'
        elif not result_text:
            to_send = to_send
        else:
            to_send += '`' + result_text + '`'

        # ADD IMAGE
        image_link = False
        image_types = ['image', 'plot', 'musicnotation', 'visualrepresentation', 'structurediagram']
        for pod in res.pods:  # Go through each pod
            # Go through each pod
            found = False
            for prefix in image_types:
                if prefix.lower() in pod['@id'].lower():
                    found = True
            if found:
                # So if the ID is Image or Plot
                for subpod in pod.subpods:
                    # For each subpod, see if its image or picture (different somehow)
                    if 'img' in subpod:  # Graph / Plot
                        image_link = subpod['img']['@src']
                    elif 'imagesource' in subpod:  # Picture
                        image_link = subpod['imagesource']
                    else:
                        image_link = False
        if image_link:
            to_send += '\n**Image:** ' + Sys.Shorten_Link(image_link)

        # ADD DETAIL
        if detail_text:
            to_send += '\n**Details: **'
            if type(detail_text) == list:
                to_send += '```'
                for part in detail_text:
                    to_send += '\n' + part
                to_send += '```'
            else:
                to_send += '`' + detail_text + '`'

        await message.channel.send(to_send)

    @staticmethod
    async def NoContext(message):
        if not await CheckMessage(message, start="no context", prefix=True):
            return

        # Cooldown Shit
        cd_notice = Cooldown.CheckCooldown("nocontext", message.author, message.guild)
        if type(cd_notice) == int:
            msg = await message.channel.send('Cooldown Active, please wait: `' + Sys.SecMin(cd_notice) + '`')
            await asyncio.sleep(5)
            await message.channel.delete_messages([msg, message])
            return
        symbols = "abcdefghijklmnopqrstuvwxyz0123456789"

        # Set up variables for guild and creation time
        guild = message.guild
        guild_created_at = guild.created_at
        # Get default channel
        channel_list = []
        for channel in guild.text_channels:
            channel_list.append(channel)
        default_channel = channel_list[0]

        # Uses creation timestmap
        created_timestamp = time.mktime(guild_created_at.timetuple())
        now_timestamp = time.mktime(datetime.now().timetuple())
        difference = now_timestamp - created_timestamp

        # Find random time from creation to now
        rand_difference = random.uniform(0, 1) * difference
        new_time = datetime.fromtimestamp(rand_difference + created_timestamp)

        # Find message
        new_message, msg = False, False
        async for part in default_channel.history(before=new_time, limit=400):
            if not part.author.bot and part.content != "":
                if part.content.lower()[0] in symbols and "http" not in part.content.lower():
                    if " " in part.content.lower() and 10 < len(part.content.lower()) < 250:
                        new_message = part
                        break
        if not new_message:
            await message.delete()
            msg = await message.channel.send("Something went horribly wrong.", delete_after=5)
            return
        Date = new_message.created_at
        addition = " pm" if int(Date.strftime("%H")) <= 11 else " am"
        DateStr = "*" + Date.strftime("%A, %B %e")
        if Date.strftime("%Y") != datetime.now().strftime("%Y"):
            DateStr += ", " + Date.strftime("%Y") + " "
        DateStr += Date.strftime(" at %I:%M") + addition + "*"

        em = discord.Embed(title=Sys.FirstCap(new_message.content), description=DateStr, color=0xFFFFFF)
        em.set_footer(icon_url=new_message.author.avatar_url, text=new_message.author.display_name + " - No Context")
        msg = await message.channel.send(embed=em)

    @staticmethod
    async def ChatLinkShorten(message):
        if not await CheckMessage(message, include="http", prefix=False):
            return
        string = message.content.strip()

        if message.author.bot:
            return

        if " " in string:  # If there's a space in the message, IE more text
            original_string = string
            new_string = ""
            string = string.split(" ")  # make string into a list
            for part in string:  # For each section
                if part.startswith("http"):  # if its the link
                    new_string = part
                    break
            if not new_string:
                return
            string = new_string

            more_content = original_string.replace(new_string, "").strip()
        else:
            more_content = False

        shortened_string = Sys.Shorten_Link(string)
        saved_length = len(string) - len(shortened_string)
        if saved_length < 20:
            return
        extra_text = "It would be `" + str(saved_length) + "` characters shorter."

        confirmation = await Helpers.Confirmation(message, "Would you like to shorten that link?", deny_text="Okay.",
                                                  timeout=40, mention=message.author, extra_text=extra_text)
        if not confirmation:
            return

        # Find domain of link
        partial = string.split("//")[1]
        if "www." in partial:
            partial = partial.replace("www.", "").strip()
        partial = partial.split(".")
        domain = partial[0] + "." + partial[1].split("/")[0]

        text = "**Shortened Link from " + message.author.name + ":  **" + shortened_string + "   (*" + domain + "*)"
        if type(more_content) == str and more_content:
            text += "\n**\" **" + more_content + " **\"**"
            await message.add_reaction(Conversation.Emoji["x"])
        await message.delete()

        await message.channel.send(text)

    @staticmethod
    async def CountMessages(message):
        if not await CheckMessage(message, start="Count", prefix=True):
            return

        stop_emoji = Conversation.Emoji["blue_book"]
        text = "I will count messages until I see a " + stop_emoji + " reaction. My limit is: `2500` messages."
        description = "Click the Check when you're ready!"

        if not await Helpers.Confirmation(message, text=text, deny_text="Count cancelled", timeout=120,
                                          extra_text=description):
            return
        await message.channel.trigger_typing()
        counter = 0
        final_count = 0
        async for part in message.channel.history(limit=10^5):
            counter += 1
            for emoji in part.reactions:
                if stop_emoji == emoji.emoji:
                    final_count = counter
            if final_count:
                break

        await message.channel.send(str(final_count) + " messages.")


class On_React:
    @staticmethod
    async def On_X(reaction, user):
        if user.id in Ranks.Bots:
            return

        message = reaction.message
        total_users = await reaction.users().flatten()
        if Vars.Bot.user in total_users:  # If bot originally reacted X
            if message.author.id != Vars.Bot.user.id:
                # If the message isn't by the bot:
                try:
                    await message.delete()
                    return
                except Exception:
                    pass
            return

        # If bot didn't originally react:
        elif user.id in Ranks.Admins:
            try:
                await message.add_reaction(Conversation.Emoji['check'])
                await asyncio.sleep(.4)
                await message.delete()
            except Exception:
                pass
            return


async def test(message):
    if not await CheckMessage(message, prefix=True, start="test", admin=True):
        return
    raise TypeError("Help")


async def Help(message):
    if not await CheckMessage(message, start="help", prefix=True):
        return
    # Has a cycle for the help
    channel = message.channel

    # Set up Emojis
    Big_Back = '\U000023ee'
    Back = '\U000025c0'
    Stop = '\U000023f9'
    Next = '\U000025b6'
    Big_Next = '\U000023ed'
    emoji_list = [Big_Back, Back, Stop, Next, Big_Next]

    current_page = 0

    help_data = Helpers.RetrieveData(type="Help_Text")
    if not help_data:
        await channel.send("Error Retrieving Data", delete_after=5)
        return

    msg = None
    stop_cycle = False
    while not stop_cycle:  # While user still wants the help embed
        title = help_data[current_page]["title"]
        description = ""
        description = help_data[current_page]["body"]
        if help_data[current_page]["color"] == 'bot':
            color = Vars.Bot_Color
        else:
            color = 0xFFFFFF
        em = discord.Embed(title=title, timestamp=datetime.now(), colour=color, description=description)
        em.set_author(name=Vars.Bot.user.name, icon_url=Vars.Bot.user.avatar_url)
        if help_data[current_page]["footer"]:
            em.set_footer(text=help_data[current_page]["footer"])

        # Send the embed
        if msg:
            await msg.edit(embed=None)
            await msg.edit(embed=em)
            msg = await channel.get_message(msg.id)
        elif not msg:
            msg = await channel.send(embed=em)
            # Add Reaction
            for emoji in emoji_list:
                await msg.add_reaction(emoji)

        # Add emoji of what page you're on
        await msg.add_reaction(help_data[current_page]["emoji"])

        # Check Function
        async def remove_reaction(init_reaction, init_user):
            # Can remove a reaction without needing async
            await init_reaction.message.remove_reaction(init_reaction.emoji, init_user)
            return

        def check(init_reaction, init_user):
            if init_reaction.message.id != msg.id:
                return
            if init_user.id == Vars.Bot.user.id:
                return
            if init_reaction.emoji in emoji_list and init_user.id == message.author.id:
                return True
            else:
                Vars.Bot.loop.create_task(remove_reaction(init_reaction, init_user))

        # Wait for Reaction
        try:
            reaction, user = await Vars.Bot.wait_for('reaction_add', timeout=60, check=check)

        except asyncio.TimeoutError:
            # If timed out
            await msg.clear_reactions()
            break
        await msg.remove_reaction(reaction.emoji, user)
        await msg.remove_reaction(help_data[current_page]["emoji"], Vars.Bot.user)

        if reaction.emoji == Big_Back:
            current_page = 0
        elif reaction.emoji == Back:
            current_page -= 1
            if current_page < 0:
                current_page = len(help_data) - 1
        elif reaction.emoji == Stop:
            await msg.clear_reactions()
            stop_cycle = True
            break
        elif reaction.emoji == Next:
            current_page += 1
            if current_page >= len(help_data):
                current_page = 0
        elif reaction.emoji == Big_Next:
            current_page = len(help_data) - 1

