import Sys, Conversation
import asyncio, random, time, discord, json, praw
from datetime import datetime, timedelta
import forecastio, os, sys, git, wolframalpha, traceback, urllib.request, pyimgur

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
        239791371110580225,     # Dom
        211271446226403328,     # Tracy
        266454101766832131,     # Louis
        351471785914400789      # Raden
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
    Version = "5.00"

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

class SeenMessages:
    RecentlySeen = []

    @staticmethod
    async def LogFound(id):
        SeenMessages.RecentlySeen.append(id)
        if len(SeenMessages.RecentlySeen) > 25:
            SeenMessages.RecentlySeen = SeenMessages.RecentlySeen[1:]
        return

    @staticmethod
    async def CheckSeen(id):
        if id in SeenMessages.RecentlySeen:
            return True
        return False


async def CheckMessage(message, start=None, notInclude=None, close=None, prefix=None, guild=None, sender=None, admin=None,
                       include=None, markMessage=True, CalledInternally=False, returnCutContent=False):
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

    # Check Seen
    if not CalledInternally:
        if await SeenMessages.CheckSeen(message.id):
            return False

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
        if type(start) == list:
            for item in start:
                if content.lower().startswith(item.lower()):
                    numberCorrect += 1
        elif content.lower().startswith(start.lower()):
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
        if int(message.author.id) in Ranks.Admins:
            numberCorrect += 1

    # Include
    if include:  # If there's a certain phrase the message should start with
        totalPossibleCorrect += 1
        if include.lower() in content.lower():
            numberCorrect += 1

    if not start:
        #print(numberCorrect, totalPossibleCorrect)
        pass

    if numberCorrect == totalPossibleCorrect:
        # Vars.Bot.loop.create_task(loadingSign(message))
        if markMessage:
            await SeenMessages.LogFound(message.id)
        return True
    else:
        return False

def IsDMChannel(channel):
    if type(channel) == discord.channel.DMChannel:
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
                           return_timeout=False, deleted_original_message=False, mention=None, extra_text=None,
                           add_reaction=True, image=None, color=Vars.Bot_Color, footer_text=None):
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

        em = discord.Embed(title=text, description=extra_text, timestamp=Helpers.EmbedTime(), colour=color)

        em.set_author(name="Confirmation:", icon_url=Vars.Bot.user.avatar_url)
        if footer_text:
            em.set_footer(text=footer_text)
        if image:
            em.set_image(url=image)
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
                return False

        # If they hit the X
        if reaction.emoji == CancelEmoji:
            await msg.delete()
            await channel.send(deny_text, delete_after=5)
            return False

        # If they hit the check
        elif reaction.emoji == ContinueEmoji:
            await msg.delete()
            if not deleted_original_message:
                if is_message and add_reaction:
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

    @staticmethod
    async def SendLongMessage(channel, content):

        while len(content) > 2000:
            await channel.send(content[0:1999])
            content = content[1999:]
        if content:
            await channel.send(content)
        return

    @staticmethod
    async def ReGet(message):
        id = message.id
        channel = message.channel
        try:
            newmsg = await channel.get_message(id)
            return newmsg
        except discord.NotFound:
            return None

    @staticmethod
    async def Deleted(message):
        id = message.id
        channel = message.channel
        try:
            newmsg = await channel.get_message(id)
        except discord.NotFound:
            return True
        return False

    @staticmethod
    async def GetMsg(messageID, channelID):
        try:
            channel = Vars.Bot.get_channel(int(channelID))
        except discord.NotFound:
            return None

        try:
            newmsg = await channel.get_message(int(messageID))
            return newmsg
        except discord.NotFound:
            return None

    @staticmethod
    async def QuietDelete(message, wait=None):
        id = message.id
        channel = message.channel
        if wait:
            await asyncio.sleep(wait)
        try:
            await message.delete()
        except discord.NotFound:
            return None
        return True

        sectionlist = []
        while len(content) > 1980:
            SplitContent = content.split('\n')
            # Test to see if there's a line break near the 2000 cutoff
            BuiltString = ""
            for i in range(0, len(Splitcontent)):  # Counter for each number
                if len(BuildString) < 2000:
                    # If the BuildString is still less than 2000
                    if len(BuildString + SplitContent[i]) > 2000:  # If adding this next section will put it over:
                        if BuildString > 1500:
                            break
                        else:
                            BuildString += "\n" + SplitContent[0:1980-len(buildstring)]
                    else:
                        BuildString += "\n" + SplitContent[i]

                BuiltString += SplitContent

            sectionlist.append(content[5])

    @staticmethod
    async def DownloadAndUpload(message, attachment, title="Uploaded from RedBot", SendProgress=True):
        # Called from within Bot

        # Create Images Folder if not already created
        if not os.path.isdir("Images"):
            os.makedirs("Images")

        def MsgEmbed(content):
            # Creates a simple embed based on the given text.
            em = discord.Embed(description="**Image Progress: **" + Sys.FirstCap(content))
            em.set_author(name="RedBot Image Uploading", icon_url=Vars.Bot.user.avatar_url)
            em.set_footer(icon_url="https://i.imgur.com/2Pq0iFl.png", text="Uploading to Imgur Services")

            return em

        DiscordURL = attachment.url.lower()
        if DiscordURL.endswith("/"):
            DiscordURL = DiscordURL[0:len(DiscordURL)-1]

        ImageSuffixes = [".png", ".jpg", ".jpeg", ".gif"]
        HasSuffix = False
        for Suffix in ImageSuffixes:
            if DiscordURL.endswith(Suffix):
                HasSuffix = True

        if not HasSuffix:
            await message.channel.send("Cannot read image!")
            return False


        if SendProgress: Progress = await message.channel.send(embed=MsgEmbed("Downloading onto RedBot Servers..."))
        await message.channel.trigger_typing()

        Image_Title = str(random.randrange(100000, 99999999))  +  ".jpg"
        Image_PATH = "Images\\" + Image_Title

        # Download Image
        await attachment.save(Image_PATH)# + Image_Title)

        if SendProgress: await Progress.edit(embed=MsgEmbed("**Contacting Imgur..."))

        # Prepare Imgur Client
        CLIENT_ID = Sys.Read_Personal(data_type='Imgur_Client')

        # Actually upload it
        if SendProgress: await Progress.edit(embed=MsgEmbed("Uploading to Imgur Servers..."))
        im = pyimgur.Imgur(CLIENT_ID)
        uploaded_image = im.upload_image(Image_PATH, title=title)

        # Delete Local File
        if SendProgress: await Progress.edit(embed=MsgEmbed("Deleting Local File..."))
        os.remove(Image_PATH)

        if SendProgress: await Helpers.QuietDelete(Progress)

        return uploaded_image


    @staticmethod
    def EmbedTime(utc=True):
        if utc:
            return datetime.now() + timedelta(hours=4)
        else:
            return datetime.now()


class Log:
    LogChannel = None
    SentColor = 0x42a1f4
    EditColor = 0xe5c1ff
    DeleteColor = 0xAA0000

    @staticmethod
    def IsRedBot():
        if Vars.Bot.user.name == "RedBot":
            return True
        else:
            return False


    @staticmethod
    def SetLogChannel():
        if Log.LogChannel:
            return
        else:
            Log.LogChannel = Vars.Bot.get_channel(Sys.Channel["DeleteLog"])


    @staticmethod
    async def AppendLogged(givenid, append, NewColor=None):
        Log.SetLogChannel()

        if not Log.IsRedBot:
            return

        # Called from bot when something needs to be added to a logged message
        async for loggedmessage in Log.LogChannel.history(limit=1000):
            if loggedmessage.embeds:  # If it has embeds
                FoundLog = loggedmessage.embeds[0].to_dict()

                # Look for footer ID
                if 'footer' in FoundLog.keys():
                    if 'text' in FoundLog['footer'].keys():
                        IDStr = FoundLog['footer']['text'][4:].strip()
                        ID = int(IDStr)

                        if ID == givenid:
                            # Then we have found the message
                            # Create new dict object
                            NewContent = FoundLog['description'] + append

                            if NewColor:
                                color = NewColor
                            else:
                                color = FoundLog['color']

                            em = discord.Embed(description=NewContent, color=color)
                            em.set_author(name=FoundLog['author']['name'], icon_url=FoundLog['author']['icon_url'])
                            em.set_footer(text=FoundLog['footer']['text'])

                            if "image" in FoundLog.keys():
                                em.set_image(url=FoundLog['image']['url'])

                            await loggedmessage.edit(embed=em)
                            return True
        return False

    @staticmethod
    async def LogSent(message):
        # Ran by bot to log a sent message
        Log.SetLogChannel()

        if not Log.IsRedBot():
            return

        if message.author.bot:
            return

        if len(message.content) > 500:
            content = message.content[0:500] + " [...]"
        else:
            content = message.content

        if type(message.channel) == discord.channel.DMChannel:
            GuildName = "Direct Messages"
        else:
            GuildName = message.channel.mention + "/" + message.guild.name

        description = "**Message Sent in " + GuildName + "**\n" + content
        timestamp = datetime.now() + timedelta(hours = 3)
        timestamp = timestamp.strftime("%A %B %d at %X")
        timestamp = "\n_Originally sent on " + timestamp + "_"

        em = discord.Embed(description=description + timestamp, color=Log.SentColor)
        em.set_author(name=message.author.name + "#" + str(message.author.discriminator),
                      icon_url=message.author.avatar_url)
        em.set_footer(text="ID: " + str(message.id))
        if message.attachments:
            em.set_image(url=message.attachments[0].url)

        await Log.LogChannel.send(embed=em)

    @staticmethod
    async def LogEdit(before, after):
        Log.SetLogChannel()

        if not Log.IsRedBot():
            return

        if after.author.bot:
            return

        if len(after.content) > 500:
            content = after.content[0:500] + " [...]"
        else:
            content = after.content

        phrase = "\n**Edited to:**\n" + content
        await Log.AppendLogged(before.id, phrase, NewColor=Log.EditColor)

    @staticmethod
    async def LogDelete(message, type):
        Log.SetLogChannel()

        if not Log.IsRedBot():
            return

        if message.author.bot:
            return

        phrase = "\n**" + type + "**"
        await Log.AppendLogged(message.id, phrase, NewColor=Log.DeleteColor)

    @staticmethod
    async def LogCommand(message, type, success, DM=False):
        # Logs a command being done afterwards
        CommandLog = Vars.Bot.get_channel(Sys.Channel["CommandLog"])

        Title = "**Command of Type: " + type + "** executed by " + message.author.name + " in "

        if DM:
            Title += "**private DM.**"

        else:
            Title += message.channel.name + "/" + message.guild.name

        description = "Content: `" + message.content + "`\nBot Response: " + success

        em = discord.Embed(color=Log.SentColor, title=Title, description=description)

        await CommandLog.send(embed=em)

    @staticmethod
    async def ErrorLog(args): # TODO Redo Logging
        Argument = args[0]
        return
        print(type(Argument))


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
            purged_messages = await message.channel.purge(limit=content + 1)  # Delete the messages
            await message.channel.send("Deleted " + str(content) + " messages", delete_after=5)  # Send message

            # Log deletes
            if content < 20:  # If there are less than 20 purged
                for deleted_message in purged_messages:
                    # For each message deleted
                    await Log.LogDelete(deleted_message, "Requested Purge by " + message.author.name + \
                                  " of " + str(content) +" messages.")
            else:
                AllIDs = "**Logging a Systematic Purge by " + message.author.name + " **(" + str(message.author.id) + ")** of " + str(content) + " messages**\n"

                for deleted_message in purged_messages:
                    content = deleted_message.content if len(deleted_message.content) < 100 else deleted_message.content[0:100] + " [...]"

                    AllIDs += "- " + str(deleted_message.id) + "  " + deleted_message.author.name + " - " + content + "\n"

                Log.SetLogChannel()
                await Helpers.SendLongMessage(Log.LogChannel, AllIDs)


    @staticmethod
    async def GuildInfo(message):
        if not await CheckMessage(message, start="guilds", prefix=True, admin=True):
            return

        sendmessage = "" # test this

        for guild in Vars.Bot.guilds:
            sendmessage += "**" + guild.name + "** - " + str(guild.id) + "\n"
            for channel in guild.text_channels:
                sendmessage += "- " + channel.name + " - " + str(channel.id)

                if not await CheckPermissions(channel, "read_messages"):
                    # if it can't read the chat:
                    sendmessage += " - CANNOT READ"


                sendmessage += "\n"


            sendmessage += "\n"

        await Helpers.SendLongMessage(message.channel, sendmessage)

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

        if "-h" in content.lower():
            content = content.replace("-h", "").strip()
            SendHere = True
        else:
            SendHere = False

        try:
            int(content)
        except:
            raise TypeError("/Copy {Channel ID}")

        starttime = time.clock()

        # timestamp = int(content)

        # timestamp = 1461383520  # Beginnig of discord
        timestamp = 1524525435  # when we left
        startreading = datetime.fromtimestamp(timestamp)

        Read_From = int(content)

        await message.delete() # A few issues

        channel = Vars.Bot.get_channel(Read_From)
        if not SendHere:
            SendChannel = Vars.Bot.get_channel(428394717798072342)
        elif SendHere:
            SendChannel = message.channel


        WorkingMessage = await message.channel.send("Working...")

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
                    await WorkingMessage.edit(content="Working... #" + str(Counted))
            else:
                if len(to_send + formatted) < 1950:
                    # If there's room to add formatted:
                    to_send += "\n" + formatted

                else:
                    # If there's no room
                    await SendChannel.send(to_send)
                    to_send = formatted
                    await WorkingMessage.edit(content="Working... #" + str(Counted))

            PreviousAuthor = foundmessage.author

        if to_send:
            await SendChannel.send(to_send)
        #await SendChannel.send(embed=em)
        await WorkingMessage.edit(content="Done   " + message.author.mention)
        await asyncio.sleep(5)
        await WorkingMessage.delete()
        await SendChannel.send(Vars.Creator.mention)

    @staticmethod
    async def PermissionsIn(message):
        if not await CheckMessage(message, start="PermissionsIn", prefix=True, admin=True):
            return

        guild = message.guild
        content = message.content[15:]
        ChannelID = int(content)
        Permchannel = Vars.Bot.get_channel(ChannelID)

        sendmsg = ""
        for permission in Permchannel.permissions_for(guild.get_member(Vars.Bot.user.id)):
            sendmsg += "\n" + permission[0] + "   " + str(permission[1])

        await Helpers.SendLongMessage(message.channel, sendmsg)


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
    async def ForceLeave(message):
        if not await CheckMessage(message, start="ForceLeave", prefix=True, admin=True):
            return
        ChannelToLeave = int(message.content[11:])  # Channel within Guild
        ChannelToLeave = Vars.Bot.get_channel(ChannelToLeave)
        GuildToLeave = ChannelToLeave.guild

        text = "Leave " + GuildToLeave.name + "?"  # Says "Leave Red Playground?"
        confirmation = await Helpers.Confirmation(Vars.Creator, text, deny_text="I will stay.")  # Waits for confirmation
        if confirmation:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Set up Time String
            invitelist = []

            #for i in range(0, 20):
            #    invite = await ChannelToLeave.create_invite(max_age=0, reason="Error: line 228, in _run_event "
            #                                                                "yield from self.on_error(event_name, *args, **kwargs)")
            #    invitelist.append(invite)
            #    await message.channel.send(invite.url + " - " + str(invite.id))
            await ChannelToLeave.send(Vars.Bot.user.name + " Left at " + current_time)  # Sends goodbye
            await GuildToLeave.leave()  # Leaves

            await Vars.Creator.send(Vars.Bot.user.name + " Left at " + current_time + " from " + GuildToLeave.name)  # Sends goodbye)

            await message.channel.send(Vars.Bot.user.name + " Left at " + current_time + " from " + GuildToLeave.name)  # Sends goodbye)

    @staticmethod
    async def Disable(message):
        if not await CheckMessage(message, prefix=True, admin=True, start="Disable"):
            return False
        if not await Helpers.Confirmation(message, "Disable?", deny_text="Will Stay Enabled."):
            return

        Vars.Disabled = True
        await Vars.Bot.change_presence(activity=(discord.Game(name='Offline')), status=discord.Status.offline)
        msg = await message.channel.send('Bot Disabled.')
        await asyncio.sleep(5)
        await message.channel.delete_messages([msg, message])
        Vars.Disabler = message.author.id

        if "-n" in message.content:
            await message.author.send("Will not self re-enable")
            return

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
            if message.author == Vars.Creator:
                return True
            else:
                return False
        if Vars.Disabler:
            if message.author.id != Vars.Disabler and message.author.id != Vars.Creator.id:
                return False

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
        receivedTime = datetime.utcnow()
        difference = receivedTime - sentTime

        now = datetime.utcnow()
        delta = now - Vars.start_time
        delta = delta.total_seconds()

        sendmsg = "Bot is ONLINE"
        sendmsg += "\n**Speed:** " + str(difference)[5:] + " seconds. "
        sendmsg += "\n**Uptime:** " + Sys.SecMin(int(delta))
        em = discord.Embed(title="Current Status", timestamp=Helpers.EmbedTime(), colour=Vars.Bot_Color,
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
                return True
        return False

    @staticmethod
    async def Update(message, fromBot=False):
        if not await CheckMessage(message, prefix=True, admin=True, start="update"):
            return
        if not await Helpers.Confirmation(message, "Update?", deny_text="Update Cancelled", timeout=20):
            return

        print("Working")

        channel = message.channel
        g = git.cmd.Git(os.getcwd())
        output = g.pull()

        print("Pulled")

        to_send = "`" + output + "`"
        await channel.send(output)
        print("Sent")

        if "Already" in output:
            return

        await message.add_reaction(Conversation.Emoji["check"])
        info = {
            "Restarted": True,
            "Type": "Update",
            "Channel_ID": message.channel.id
        }
        print("Saved Info") # Documentation
        Helpers.SaveData(info, type="System")
        print("Killing TimeThread")
        Timer.StopThreadTwo = True
        while Timer.Running:
            Timer.StopThreadTwo = True
            await asyncio.sleep(.5)


        print("Logging Out")
        await Vars.Bot.logout()
        print("Adding it back in")
        os.execv(sys.executable, ['python'] + sys.argv)
        print("Returning")
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

        return
        tempTagList = await Tag.RetrieveTagList()
        for TagKey in tempTagList.keys():
            tempTagList[TagKey]["Personal"] = False
            if "Color" not in tempTagList[TagKey].keys():
                tempTagList[TagKey]["Color"] = Vars.Bot_Color
            if not tempTagList[TagKey]["Color"]:
                tempTagList[TagKey]["Color"] = Vars.Bot_Color





        Helpers.SaveData(tempTagList, type="Tag")

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
        await asyncio.sleep(5)
        if not await Helpers.Deleted(message):
            await message.delete()


class Cooldown:
    meme_types = ["meme", "quote", "nocontext", "delete", "remind"]
    data = {}
    defaults = {
        "meme": [30, 30],
        "quote": [60, 45],
        "nocontext": [5, 10],
        "delete": [5, 3],
        "remind": [5, 10]
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
    StopThreadTwo = False
    Running = False
    @staticmethod
    def DigitTime():
        hour = time.strftime('%H')
        minute = time.strftime('%M')
        return hour + ':' + minute

    @staticmethod
    async def TimeThread():
        Timer.Running = True
        await asyncio.sleep(10)
        old_time, current_time = None, None
        # while not Vars.Crash:
        while not StopThreadTwo:
            await asyncio.sleep(3)
            old_time = current_time
            current_time = Timer.DigitTime()

            # Morning Weather
            if current_time != old_time:  # Ensures this only runs on minute change
                if current_time == '06:30':
                    try:
                        today = datetime.now().strftime("%B %d")
                        print("Good Morning! It is " + today)
                        await Other.T_Weather()
                    except Exception as e:
                        await Vars.Creator.send("Error during weather, error = " + str(e))

                if current_time == '12:00':
                    await Remind.CheckForOldReminders()
                    await Poll.CleanData()

                await Remind.CheckForReminders()

                if current_time.endswith(":01") or current_time.endswith(":45"):
                    await Other.StatusChange()

        Timer.Running = False
        print("Stopped TimeThread.")


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

        hour = await Helpers.EmbedTime().hour
        if 1 < hour < 6:
            return False
        else:
            return True

    @staticmethod
    async def QuoteCommand(message):
        if not await CheckMessage(message, start="quote", prefix=True):
            return
        if len(message.mentions) == 0:
            await message.channel.send("Please follow the correct format: `/quote @RedBot How are you?`",
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
        content = message.clean_content[7:].replace("@" + mention_user.display_name, '').strip()
        if content.startswith("\""):
            content = content[1:]
        if content[-1] == "\"":
            content = content[0:len(content)-1]


        # Create Embed
        em = discord.Embed(title="Quote this?", timestamp=Helpers.EmbedTime(), colour=Vars.Bot_Color,
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
            await Helpers.QuietDelete(msg)
            await message.channel.send("Failed to receive 3 reactions", delete_after=5)
            return None
        await Helpers.QuietDelete(msg)
        if not await Helpers.Deleted(message):
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
        if await CheckMessage(reaction.message, prefix=True, CalledInternally=True):
            await reaction.message.channel.send("Quoting Commands confuses me!", delete_after=5)
            await reaction.message.clear_reactions()
            return

        if len(reaction.message.content) > 500:
            await reaction.message.channel.send("Simply too long to quote.", delete_after=5)
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

    @staticmethod
    async def EditQuote(message):
        if not CheckMessage(message, start="EditQuote", admin=True, prefix=True):
            return
        # Allows the user to select a quote and then change it / Delete it remotely

        # First we're going to want to make lists of quotes, 10 quotes per list
        TotalQuoteList = []

        RawQuoteData = Helpers.RetrieveData(type="Quotes") # Given as Quote Dict

        QuoteCounter = -1
        for QuoteObject in RawQuoteData['info']:
            # Create a string for the quote and put that string in TotalQuoteList
            QuoteCounter += 1
            QuoteString = str(QuoteCounter) + ". " + QuoteObject['user_name']
            QuoteString += " - \"" + QuoteObject['quote'] + "\""

            TotalQuoteList.append(QuoteString)

        # So now we have a list of each quote string. Need to


class Memes:
    """
    Meme data file:
    {"Memes": [
        {"12345":[
            [201711202037, "www.google.com"]
        ]]}
    """
    subs = {
        'meme': "dankmemes+BikiniBottomTwitter+youdontsurf+imgoingtohellforthis",
        'dank': "dankmemes+BikiniBottomTwitter+youdontsurf+imgoingtohellforthis",
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
            em = discord.Embed(title=found_meme.title, timestamp=Helpers.EmbedTime())
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
    async def OnMessage(message):
        await Other.QuickChat(message)
        await Other.Change_Color(message)
        await Other.Weather(message)
        await Other.OldWeather(message)
        await Other.NoContext(message)
        await Other.ChatLinkShorten(message)
        await Other.LinkShortenCommand(message)
        await Other.CountMessages(message)
        await Other.Upload(message)
        await Other.AutoUpload(message)
        await Other.UpdateNotes(message)

    @staticmethod
    async def StatusChange():
        CurrentHour = (datetime.now()).hour

        # Okay let's go between possible times
        if 6 <= CurrentHour <= 10:  # Between 6 o clock and 10:
            New_Status = random.choice(["Good Morning", "Morning", "Hello", "Bright and Early"])

        elif 10 < CurrentHour < 12:
            New_Status = random.choice(["Need Coffee", "Making Lunch", "Hello", "Working Hard", "Hardly Working", "Running Smoothly"])

        elif 12 <= CurrentHour <= 16:
            New_Status = random.choice(["Happy Afternoon", "Good Afternoon", "Eating Lunch", "Working Hard", "Great Day", "Okay Day"])

        elif  16 < CurrentHour <= 19:
            New_Status = random.choice(["Making Dinner", "Preparing Sunset", "Good Evening", "Great Evening", "Hello"])

        elif 19 < CurrentHour <= 21:
            New_Status = random.choice("Great Evening", "Good Evening", "Sun Setting", "Running Repair", "Having Dessert", "Running Well", "No Errors")

        elif 21 <= CurrentHour <= 24:
            New_Status = random.choice(["Go to Sleep", "Go to Bed", "You Sleep", "Sweet Dreams", "Good Night", "Great Night", "The Stars", "You Best Be Sleeping"])

        elif 0 <= CurrentHour <= 4:
            New_Status = random.choice(["You Up?", "Go to Sleep", "Hello.", "It's Late.", "Get some sleep", "It's Quiet Right Now", "Silent Night", "Sweet Dreams",
                                        "I Don't Sleep so You Can", ":)"])


        elif 5 == CurrentHour:
            New_Status = random.choice(["A few more hours", "Up So Soon?", "Preparing Weather Data", "Dawn", "Watching Sunrise"])

        # Now we have all of those cute ass statements
        # Let's add a bit of variance
        Variance = random.randrange(0, 200)

        ActivityType = discord.ActivityType.playing
        StatusPrefix = "v" + Vars.Version + " | "

        if Variance == 36:
            # 1 in 200 chance, 0.5%
            ActivityType = discord.ActivityType.listening
            New_Status = random.choice(["You Closely", "You.", "Them"])
        if Variance == 37 or Variance == 38:
            ActivityType = discord.ActivityType.watching
            New_Status = random.choice(["You...", "You.", "Them", "It Closely", "The Thing"])

        if 100 < Variance < 200 and 8 < CurrentHour < 20:
            New_Status = random.choice(["Online", "Bot Active", "No Issues", "Hello", "Hello, Human.", "Active", "Ready"])

        game = discord.Activity(type=ActivityType, name=StatusPrefix + New_Status)
        await Vars.Bot.change_presence(status=discord.Status.online, activity=game)



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

        perm = await CheckPermissions(message.channel, ['manage_roles', 'send_messages'])
        if not perm:
            await message.channel.send("Woah woah woah, I don't have the permission to `manage roles`")
            return

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
    async def InterpretQuickChat():
        """
        Runs on start
        :return: a dict of each part of quickchat data
        """
        data = Conversation.QuickChat
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

        # Random Chance
        if 'chance' in chat_function:
            if random.randrange(0, 100) > chat_function['chance']:
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
        em = discord.Embed(description=description, colour=0xffffff, timestamp=Helpers.EmbedTime())
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

        async def LogDeletion(message):
            await Log.LogDelete(message, "Deleted.")
            return


            DeleteLoggerChannel = Vars.Bot.get_channel(Sys.Channel["DeleteLog"])
            # First check to see if it's already a logged deletion:
            OneHour = datetime.now() - timedelta(hours = 1)
            async for LogMessage in DeleteLoggerChannel.history(after=OneHour):
                # For each message in the logger's history:
                if LogMessage.embeds:  # If there's an embed
                    embed = LogMessage.embeds[0].to_dict()  # Grab it as embed
                    if "description" in embed.keys():
                        if embed["description"].startswith("**Deleted"):
                            if embed["footer"]["text"].startswith("ID"):
                                LogMessageID = int(embed["footer"]["text"][3:].strip())
                                if LogMessageID == message.id:
                                    await LogMessage.add_reaction(Conversation.Emoji["check"])
                                    return

            # Create Embed for Logging Purposes
            title = "**Deleted message by " + message.author.mention + " in " + message.channel.mention + \
                    "/" + message.guild.name + "**\n"

            em = discord.Embed(description=title + message.content, colour=0xff0000, timestamp=Helpers.EmbedTime())
            em.set_author(name=message.author.name + "#" + str(message.author.discriminator),
                          icon_url=message.author.avatar_url)
            em.set_footer(text="ID: " + str(message.id))

            if message.attachments:
                em.set_image(url=message.attachments[0].url)

            await DeleteLoggerChannel.send(embed=em)
            return

        if not message.author.bot:  # If neither of these things are true, so it's just any other message, log it
            await LogDeletion(message)

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
    async def OldWeather(message, morning=False):
        if not morning:
            if not await CheckMessage(message, prefix=True, start="FullWeather"):
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
        guild = Vars.Bot.get_guild(Conversation.Server_IDs['Lounge'])
        channel_list = []
        for channel in guild.text_channels:
            channel_list.append(channel)
        default_channel = channel_list[0]

        if default_channel:
            #await Other.OldWeather(default_channel, morning=True)
            await Other.Weather(None, channel=default_channel)

    @staticmethod
    async def T_Graduation():
        guild = Vars.Bot.get_guild(Conversation.Server_IDs['Lounge'])
        channel_list = []
        for channel in guild.text_channels:
            channel_list.append(channel)
        default_channel = channel_list[0]

        if not default_channel:
            return

        a = datetime.now()
        b = datetime.strptime('06/01/2018', "%m/%d/%Y")
        difference = b - a

        daysdifference = difference.days + 1

        if daysdifference >= 0:
            if daysdifference == 1:
                is_are = "is"
            else:
                is_are = "are"
            await default_channel.send("There " + is_are + " **" + str(daysdifference) + " days** until Graduation.")

        else:
            # If the day has passed:
            if daysdifference == -1:
                await default_channel.send("Graduation was: **yesterday**. Congradulations!")
            else:
                await default_channel.send("There have been **" + str(daysdifference) + " Days** since Grdauation.")

        return

    @staticmethod
    async def NoContext(message):
        if not await CheckMessage(message, start="no context", prefix=True):
            return

        if IsDMChannel(message.channel):
            await message.channel.send("No Context only works in Guilds/Servers!")
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
    async def ChatLinkShorten(message, command=False):
        """Scans chat for any mention of a link
        Sees how long it is, and offers to shorten it if need be.
        """
        # Ensure the message has http in it
        if not command:
            if not await CheckMessage(message, include="http", prefix=False):
                return
        if command:
            if "http" not in message.content.lower():
                await message.channel.send("Please follow the format: /shorten <link>")
                await message.add_reaction(Conversation.Emoji["x"])
                return

        if message.author.bot:
            return

        #if IsDMChannel(message.channel):
        #    return

        UsableContent = message.content.strip()
        Links = []

        # Now we need to find the link:
        ContentWords = UsableContent.replace("\n", " ").split(" ")
        for Word in ContentWords:
            #print(Word)
            if Word.lower().strip().startswith("http"):
                Links.append(Word)

        # Let's ensure that everything is shortenable
        Shortened_Links = {}
        for Link in Links:
            ShortenedVersion = Sys.Shorten_Link(Link)

            # Now let's create a dict that'll help us in the longrun
            tempdict = {"Short": ShortenedVersion}

            # Let's find the main url part
            partial = Link.replace("www.", "").split("//")

            if len(partial) == 1:
                return

            # Partial should now have "[Https:, therest.com/whatever]
            MainDomain = partial[1].split("/")[0]
            # MainDomain should now just be "en.wikipedia.org" which is exactly what we want
            tempdict["Partial"] = MainDomain
            tempdict["Difference"] = len(Link) - len(ShortenedVersion)

            Shortened_Links[Link] = tempdict

        # Now that we have a list, Links, of all the different links, let's see if the user wants
        # to shorten it

        # Reaction Stuff
        if not command:
            await message.add_reaction(Conversation.Emoji["link"])

            # This function will be ran on every new reaction_add to see if it's the link we want
            def check(reaction, user):
                if user.id == Vars.Bot.user.id:
                    return None
                if user.id == message.author.id:
                    if reaction.message.id == message.id:
                        if reaction.emoji == Conversation.Emoji["link"]:
                            return reaction, user

                return None

            try:
                reaction, user = await Vars.Bot.wait_for('reaction_add', check=check, timeout=60)
            except asyncio.TimeoutError:
                if not await Helpers.Deleted(message):
                    await message.remove_reaction(Conversation.Emoji["link"], Vars.Bot.user)
                return

            # Now that we know they wanted it shortened, our first order of business
            # is to delete the original
            await message.delete()

        # Now it's time to format what the bot will send
        NewContent = message.content
        for link in Shortened_Links:
            To_Replace = Shortened_Links[link]["Short"] + " *(" + Shortened_Links[link]["Partial"] + ")* "
            NewContent = NewContent.replace(link, To_Replace)

        LinkSendEmbed = discord.Embed(description=NewContent, color=message.author.color)
        LinkSendEmbed.set_author(name=message.author.name + "#" + message.author.discriminator, icon_url=message.author.avatar_url)
        LinkSendEmbed.set_footer(text="RedBot Link Shortener")

        await message.channel.send(embed=LinkSendEmbed)

    @staticmethod
    async def LinkShortenCommand(message):
        if not await CheckMessage(message, start="shorten", prefix=True):
            return
        """
        Shortens a given link using TinyUrl
        """
        message.content = message.content[8:].strip()
        await Other.ChatLinkShorten(message, command=True)



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

    @staticmethod
    async def Weather(message, channel=None):
        if not channel:
            if not await CheckMessage(message, start="weather", prefix=True):
                return

        # Obtain Forecast Dataset
        forecast = forecastio.load_forecast(forecast_api_key, lat, lng)

        DataDaily = forecast.daily()  # Daily
        DataHourly = forecast.hourly()  # Hourly
        DataMinutely = forecast.minutely()  # Minutely
        DataCurrently = forecast.currently()  # Currently
        DataAlerts = forecast.alerts()  # Alerts

        # Now we need to organize the data into dictionaries
        WeatherDict = {}

        DayDataList = []
        for day in DataDaily.data:  # For each Day
            OneDayDict = {}  # Create temporary Dict
            OneDayDict['Data'] = day.d
            OneDayDict['Summary'] = day.summary

            # Set up the Time Information
            Time = {}
            # print(dir(day))
            DayNum = datetime.fromtimestamp(int(day.d['time'])).strftime('%m')
            DayWeek = datetime.fromtimestamp(int(day.d['time'])).strftime('%a')
            DayWeekFull = datetime.fromtimestamp(int(day.d['time'])).strftime('%A')
            Time['DayNum'] = DayNum
            Time['DayWeek'] = DayWeek
            Time['DayWeekFull'] = DayWeekFull

            OneDayDict['Time'] = Time

            # Add to Main Dict
            DayDataList.append(OneDayDict)
        WeatherDict['Daily'] = DayDataList

        HourDataList = []
        for hour in DataHourly.data:  # For each Day
            OneHourDict = {}  # Create temporary Dict
            OneHourDict['Data'] = hour.d
            OneHourDict['Summary'] = hour.summary

            # Set up Time Information
            Time = {}
            Hour24 = datetime.fromtimestamp(int(hour.d['time'])).strftime('%H')
            Hour = datetime.fromtimestamp(int(hour.d['time'])).strftime('%I')
            Time['hour24'] = Hour24
            Time['hour'] = Hour

            OneHourDict['Time'] = Time

            # Add to Main Dict
            HourDataList.append(OneHourDict)
        WeatherDict['Hourly'] = HourDataList

        MinuteDataList = []
        for minute in DataMinutely.data:  # For each Day
            OneMinuteDict = {}  # Create temporary Dict
            OneMinuteDict['Data'] = minute.d
            MinuteDataList.append(OneMinuteDict)

        WeatherDict['Minutely'] = MinuteDataList
        WeatherDict['Currently'] = DataCurrently
        if 'Alerts' in WeatherDict.keys():
            WeatherDict['Alerts'] = DataAlerts[0].json
        else:
            WeatherDict['Alerts'] = {}

        # Now that we have everything all in WeatherDict, we can start to construct our whole Message
        def SelectList(selectlist):
            # Selects one option out of a list at random
            return random.choice(selectlist)

        Phrases = Conversation.WeatherText  # Dictionary of weather responses
        msg = SelectList(Phrases['Intro'])

        # Replace "Morning" with "Afternoon" or "Night"
        CurrentHour = WeatherDict["Currently"].d["time"]
        CurrentHour = datetime.fromtimestamp(int(CurrentHour))
        CurrentHour = int(CurrentHour.strftime("%H"))

        CurrentTimeArea = ""
        if CurrentHour > 19:        # More than 7 pm
            CurrentTimeArea = "Night"
        elif CurrentHour > 12:      # More than 12 pm
            CurrentTimeArea = "Afternoon"
        elif CurrentHour >= 6:      # More than 6 am
            CurrentTimeArea = "Morning"
        elif CurrentHour < 6:       # Early Morning (Earlier than 6)
            CurrentTimeArea = "Night"
        else:                       # Anything else
            CurrentTimeArea = "Day"

        msg = msg.replace("%DayTime%", CurrentTimeArea)


        # Set up the Currently Section
        CurrentlyTemp = round(WeatherDict['Currently'].d['temperature'])  # Assign Current Temp Float to CurrentTemp
        msg += " " + SelectList(Phrases["Currently"]).replace("%Now%", str(
            CurrentlyTemp) + " degrees")  # Add random phrase for it

        ApparentTemp = round(
            WeatherDict['Currently'].d['apparentTemperature'])  # Assign ApparentTemperature "feelsLike"

        if abs(ApparentTemp - CurrentlyTemp) > 3:  # If there's more than 3 degree difference
            # Include Feels Like in the message
            msg += " " + SelectList(Phrases["FeelsLike"]).replace("%FeelsLike%", str(ApparentTemp) + " degrees.")
        else:  # Otherwise do not include it in the currently section
            msg += "."

        # At a Glance
        Summary = WeatherDict["Daily"][0]["Data"]["summary"]
        msg += "\n - **Today:** " + Summary

        # Add High and Low
        # Assign HighTemp and LowTemp
        HighTemp = round(WeatherDict['Daily'][0]["Data"]["temperatureMax"])
        LowTemp = round(WeatherDict['Daily'][0]["Data"]["temperatureMin"])

        # Create the HighTime based on the local timestmap
        HighTime = WeatherDict['Daily'][0]["Data"]["temperatureMaxTime"]
        HighTime = datetime.fromtimestamp(int(HighTime)).strftime('%I:00 %p')

        # Create the LowTime based on the local timestamp
        LowTime = WeatherDict['Daily'][0]["Data"]["temperatureMinTime"]
        LowTime = datetime.fromtimestamp(int(LowTime)).strftime('%I:00 %p')

        # Create the HighText phrase
        HighText = SelectList(Phrases["HighLow"])
        HighText = HighText.replace("%Type%", "high").replace("%Temp%", str(HighTemp)).replace("%Time%", HighTime)

        # Create the LowText Phrase and make the first letter Lowercase
        LowText = SelectList(Phrases["HighLow"])
        LowText = LowText.replace("%Type%", "low").replace("%Temp%", str(LowTemp)).replace("%Time%", LowTime)
        LowText = LowText[0].lower() + LowText[1:]

        # Create the whole section
        HighLowText = HighText + " " + SelectList(Phrases["Transitions"]) + " " + LowText

        # Append to Message
        msg += "\n - " + HighLowText + "."

        # Today's Humidity  - Only displays if over a certain percentage
        Humidity = WeatherDict["Daily"][0]["Data"]["humidity"]
        if Humidity > 0.9:
            HumidText = SelectList(Phrases["Humidity"])
            msg += "\n - " + HumidText

        # Cloud Cover (or lack of)
        CloudCover = WeatherDict["Daily"][0]["Data"]["cloudCover"]
        if CloudCover > 0.95:
            msg += "\n - " + SelectList(Phrases["Cloudy"])

        if CloudCover < 0.1:
            msg += "\n - " + SelectList(Phrases["Sunny"])

        # Precipitation
        PrecipProbability = WeatherDict["Daily"][0]["Data"]["precipProbability"]
        if PrecipProbability >= 0.75:
            # If there's a 3/4 chance of Precipitation
            # Now we need to find out when it starts
            HourCounter = 0
            Start = {}
            End = {}
            for hour in WeatherDict["Hourly"]:
                hourtime = datetime.fromtimestamp(hour["Data"]["time"])

                if hour["Data"]["precipProbability"] >= 0.5 and not Start:
                    Start["Probability"] = hour["Data"]["precipProbability"]
                    Start["Hour"] = datetime.fromtimestamp(hour["Data"]["time"]).strftime("%I %p")
                    Start["Type"] = hour["Data"]["precipType"]

                    if hourtime.strftime("A") == WeatherDict["Daily"][0]["Time"]["DayWeekFull"]:
                        # Then the start is today
                        Start["Date"] = "today"
                    else:
                        Start["Date"] = "tomorrow"

                # Now we need an end
                if hour["Data"]["precipProbability"] < 0.4 and not End:
                    End["Probability"] = hour["Data"]["precipProbability"]
                    End["Hour"] = datetime.fromtimestamp(hour["Data"]["time"]).strftime("%I %p")

                    if hourtime.strftime("A") == WeatherDict["Daily"][0]["Time"]["DayWeekFull"]:
                        # Then the start is today
                        End["Date"] = "today"
                    else:
                        End["Date"] = "tomorrow"
                if HourCounter > 24:
                    break


                HourCounter += 1

            if Start:

                # Now we have Start and maybe End
                PrecipMessage = ""
                StartText = SelectList(Phrases["PrecipitationStart"])
                if "Type" not in Start.keys():
                    Start["Type"] = "Rain"
                if "Hour" not in Start.keys():
                    Start["Hour"] = "Today"
                if "Date" not in Start.keys():
                    Start["Date"] = "soon"
                StartText = StartText.replace("%Type%", Start["Type"]).replace("%Time%", Start["Hour"])
                StartText = StartText.replace("%Date%", Start["Date"]).replace("%Chance%",
                                                                           str(int(Start["Probability"] * 100)) + "%")

                if End:
                    EndText = SelectList(Phrases["PrecipitationEnd"]).replace("%Time%", End["Hour"]).replace("%Date%",
                                                                                                         End["Date"])
                    # EndText = EndText[0].lower() + EndText[1:]
                else:
                    EndText = ""

                PrecipMessage = StartText + " " + SelectList(Phrases["Transitions"]) + " " + EndText + "."

                msg += "\n - " + PrecipMessage

        # Tomorrow's Forecast
        Summary = WeatherDict["Daily"][1]["Data"]["summary"]
        msg += "\n - **Tomorrow:** " + Summary

        em = discord.Embed(description=msg, colour=0x498fff, timestamp=Helpers.EmbedTime() + timedelta(hours=4))
        #em.set_author(name=WeatherDict["Daily"][0]["Data"]["summary"])
        if channel:
            await channel.send(embed=em)
        else:
            await message.channel.send(embed=em)
        return

    @staticmethod
    async def Upload(message):
        if not await CheckMessage(message, prefix=True, start="Upload"):
            return
        # This function will upload an image to imgur and give the user a link
        UsableContent = message.content[7:].strip()
        if not UsableContent:
            UsableContent = "Uploaded Image from RedBot"

        if message.attachments:
            HasAttachment = message.attachments[0]

        else:
            SentMsg = await message.channel.send("Please send the image you would like me to upload:")


            # If there's no attachment, we're going to wait here and prompt for one.
            Stop = False

            def Check(NewMsg):
                # This function checks to make sure the authors are the same and its in the same channel
                if message.author.id == NewMsg.author.id and message.channel.id == NewMsg.channel.id:

                    if NewMsg.attachments:

                        return True

            while not Stop:

                try:
                    NewMessage = await Vars.Bot.wait_for("message", timeout=60, check=Check)
                except asyncio.TimeoutError:
                    await Helpers.QuietDelete(NewMessage)
                    await message.channel.send("Upload Timed Out", delete_after=10)

                    if not Helpers.Deleted(message):
                        await message.add_reaction(Conversation.Emoji["x"])
                    return

                # If there is a NewMessage with an attachment:
                if NewMessage:
                    HasAttachment = NewMessage.attachments[0]
                    break

        if not HasAttachment:
            await message.channel.send("Whoops, something went wrong. Hmmm")
            return

        # But now we have an attachment
        ImageURL = await Helpers.DownloadAndUpload(message, HasAttachment, title=UsableContent)

        if ImageURL:
            em = discord.Embed(color=Vars.Bot_Color, description = ImageURL.link, title="Here is your uploaded image:")
            em.set_image(url=ImageURL.link)
            em.set_footer(text="Powered by Imgur | Requested by " + message.author.name)
            await message.channel.send(embed=em)
        else:
            await message.channel.send("Something went horribly wrong.")

    @staticmethod
    async def AutoUpload(message):
        if not message.attachments:
            return
        if await CheckMessage(message, prefix=True, CalledInternally=True):
            return

        suffixes = [".png", ".jpg", ".jpeg", ".gif", ".ico"]
        IsImage = False
        for suffix in suffixes:
            if message.attachments[0].url.lower().strip().endswith(suffix):
                IsImage = True
                break
        if not IsImage:
            return


        # So there's an attachment
        UploadEmoji = '\U00002b06'
        await message.add_reaction(UploadEmoji)

        def Check(reaction, user):
            if user.id == message.author.id:
                if reaction.message.id == message.id:
                    if not user.bot:
                        return True
            return False

        Stop = False
        while not Stop:
            try:
                reaction, user = await Vars.Bot.wait_for("reaction_add", check=Check, timeout=10)
                Stop = True

            except asyncio.TimeoutError:
                if not await Helpers.Deleted(message):
                    await message.clear_reactions()
                    return

        await message.clear_reactions()
        if await Helpers.Deleted(message):
            raise FileNotFoundError("I cannot find the message with the image. Was it deleted?")

        AttachmentUploaded = await Helpers.DownloadAndUpload(message, message.attachments[0], SendProgress=False)
        await message.channel.send("<" + AttachmentUploaded.link + ">")


    @staticmethod
    async def UpdateNotes(message):
        if not await CheckMessage(message, start="updatenotes", prefix=True):
            return
        em = discord.Embed(color=Vars.Bot_Color)
        em.set_thumbnail(url=Vars.Bot.user.avatar_url)
        em.set_author(name="RedBot v" + Vars.Version, icon_url=Vars.Bot.user.avatar_url)

        UpdateFull = Conversation.UpdateNotes
        for Note in UpdateFull:
            em.add_field(name=Note["Name"], value=Note["Content"], inline=True)


        await message.channel.send(embed=em)


class Poll:
    RunningPolls = {}

    @staticmethod
    async def OnMessage(message):
        await Poll.PollCommand(message)

    @staticmethod
    async def PollCommand(message):
        """
        /poll Which Emoji is cooler?
        :car: The car Emoji
        :No Car: No Car Emoji
        :param message: the input message
        :return: Nothing
        """
        if not await CheckMessage(message, prefix=True, start="poll"):
            if not await CheckMessage(message, prefix=True, start="yesno"):
                return

        async def PollError(cmdMessage, error: str, sendFormat: bool = True):
            """
            A function to send an error message, similar to reminders
            :param cmdMessage: The originalmessage
            :param error: str, the error message
            :param sendFormat: bool, True or False to append the format
            :return: None
            """

            if sendFormat:
                formatStr = "```/poll Here, you write your question?\n" \
                            ":b: Response 1\n" \
                            ":blue_car: Response 2\n" \
                            "...```" \
                            "If you do not have emoji, each response will be assigned a letter"
                sendContent = "Here is a sample Format:" + formatStr
            else:
                sendContent = ""

            em = discord.Embed(title=error, description= sendContent)
            em.set_author(name= "Poll Error", icon_url= Vars.Bot.user.avatar_url)

            await cmdMessage.channel.send(embed=em)
            if not await Helpers.Deleted(cmdMessage):
                await cmdMessage.add_reaction(Conversation.Emoji["x"])
            return

        await message.channel.trigger_typing()

        await Log.LogCommand(message, "Poll", "Successfully Set Up Poll.")

        # Prepare some strings for later use
        Characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+/\\\'\".,~`<>: "
        LetterEmoji = ['\U0001F1E6', '\U0001F1E7', '\U0001F1E8', '\U0001F1E9', '\U0001F1EA', '\U0001F1EB',
                    '\U0001F1EC', '\U0001F1ED', '\U0001F1EE', '\U0001F1EF']


        # Create ContentLines, that'll go through each section of this message
        UsableContent = message.content[6:].strip().lower()
        ContentLines = UsableContent.split("\n")

        # Begin making PollData (dict)
        PollData = {"Question": ContentLines[0]}
        Responses = []  # Will be eventually put into PollData

        # Okay so now we need to figure out if it is a YesNo (no options)
        if len(ContentLines) > 1:  # If there are 1 or more lines in the poll:
            PollType = "Poll"
            # Iterate through each line, figuring out what's emoji and what's option
            for Line in ContentLines[1:]:
                Line = Line.strip()
                Emoji = None
                # Test for Python-Approved Unicode first
                if Line[0] not in Characters:
                    Emoji = Line[0]
                    Line = Line.strip()[1:]

                # Test if, otherwise, it's a custom emoji
                elif Line[0].startswith("<"):
                    Emoji = Line.split(">")[0]  + ">"  # Isolate the emoji
                    Line = Line.replace(Emoji, "").strip()

                Responses.append({
                    "Emoji": Emoji,
                    "Response": Line.strip()
                })

        else:  # If there were no given responses:
            PollType = "YesNo"
            Responses = [ {
                    "Emoji": Conversation.Emoji["thumbsup"],
                    "Response": "Yes"
                },{
                    "Emoji": Conversation.Emoji["thumbsdown"],
                    "Response": "No"
                } ]
        PollData["Type"] = PollType

        # Let's run a quick test here:
        if len(Responses) > 10:
            await PollError(message, "Too many responses! Max is 10!", sendFormat=True)
            return
        if not PollData["Question"].strip():
            await PollError(message, "You should involve at least a question...", sendFormat=True)
            return

        # Now we have given Responses / Emoji (or None), we should add some data to Responses
        EmojiList = []
        for i in range(0, len(Responses)):
            Responses[i]["Place"] = i  # Gives them a numerical Place in line

            if not Responses[i]["Emoji"]:
                Responses[i]["Emoji"] = LetterEmoji[i]

            # Let's also shorten it to 250 characters per response
            if len(Responses[i]["Response"]) > 250:
                Responses[i]["Response"] = Responses[i]["Response"][0:250] + " [...]"

            EmojiList.append(Responses[i]["Emoji"])


        # We can now encorperate Responses into PollData
        PollData["Responses"] = Responses
        PollData["EmojiList"] = EmojiList

        # -== Prepare PollEmbed ==- #
        Description = ""
        # Format Body
        for Response in PollData["Responses"]:
            if Description:
                Description += "\n"

            Description += Response["Emoji"] + "  " + Sys.FirstCap(Response["Response"])

        PollEmbed = discord.Embed(title= PollType + ": " + Sys.FirstCap(PollData["Question"]), description=Description, color=Vars.Bot_Color)
        PollEmbed.set_author(name=message.author.name + "#" + message.author.discriminator,
                             icon_url=message.author.avatar_url, url="http://" + str(message.id) + ".com")

        SentEmbed = await message.channel.send(embed=PollEmbed)

        for Response in PollData["Responses"]:
            EmojiAdd = Response["Emoji"]
            if EmojiAdd.startswith("<"):
                EmojiAdd = EmojiAdd.replace(">", "").replace("<", "")
            await SentEmbed.add_reaction(EmojiAdd)

        DM_Message = "I just created that Poll for you. If you want to stop it, add a stop_sign reaction to that " \
                     "message! It looks like this: :octagonal_sign: and has the name: `:octagonal_sign:`"
        async for past_message in message.author.history(limit=1):
            if past_message.content != DM_Message:
                await message.author.send(DM_Message)

        PollData["SentID"] = SentEmbed.id
        PollData["OriginalID"] = message.id
        PollData["ChannelID"] = message.channel.id
        PollData["MessageAuthorID"] = message.author.id
        PollData["MessageAuthor"] = message.author.name + "#" + message.author.discriminator
        PollData["MessageAuthorAvatarURL"] = message.author.avatar_url
        PollData["TimeStamp"] = int(datetime.now().timestamp())


        await Poll.AddData(PollData)

    @staticmethod
    async def AddData(PollData):
        # Called internally, adds data for this running poll
        SentID = str(PollData["SentID"])


        Poll.RunningPolls[SentID] = PollData
        Helpers.SaveData(Poll.RunningPolls, "Poll")

    @staticmethod
    async def RefreshData():
        Data = Helpers.RetrieveData("Poll")
        if not Data:
            Data = {}
        Poll.RunningPolls = Data

    @staticmethod
    async def StopPollRunning(ID):
        await Poll.RefreshData()

        ID = str(ID)

        if ID not in Poll.RunningPolls.keys():
            return

        del Poll.RunningPolls[ID]
        Helpers.SaveData(Poll.RunningPolls, "Poll")

    @staticmethod
    async def CleanData():
        # Cleans up to make sure all data is correct, cleans polls too
        AllPollData = Poll.RunningPolls

        for key in AllPollData.keys():
            PollData = AllPollData[key]
            if not await Helpers.GetMsg(PollData["SentID"], PollData["ChannelID"]):
                await Poll.StopPollRunning(key)

            else:
                DifferenceStamp = int(datetime.now().timestamp()) - int(PollData['TimeStamp'])
                if DifferenceStamp > 60*60*24*4:  # More than two days old:
                    msg = await Helpers.GetMsg(PollData["SentID"], PollData["ChannelID"])
                    await Poll.FormatDescription(PollData, msg.reactions, TitleAdd="AutoClosed - ", Color=0x000000)

                    await Poll.StopPollRunning(key)

    @staticmethod
    async def FormatDescription(PollData, AllMessageReactions, TitleAdd="", Color=Vars.Bot_Color):
        # We're going to add a bit to each Responses that has a list of all members who currently have reacted to it,
        # and add it all to FormatData
        FormatData = []
        PollMessage = await Helpers.GetMsg(PollData["SentID"], PollData["ChannelID"])

        for Response in PollData["Responses"]:
            temp = Response
            for Reaction in AllMessageReactions:
                if Response["Emoji"] == Reaction.emoji:
                    temp["Users"] = await Reaction.users().flatten()
                elif str(Response["Emoji"]) == str(Reaction.emoji):
                    temp["Users"] = await Reaction.users().flatten()

            if "Users" not in temp.keys():
                temp["Users"] = ""

            FormatData.append(temp)

        # So now we have FormatData
        Description = ""
        for item in FormatData:
            if Description:
                Description += "\n"

            # Let's reconstruct each emoji, but now also include the users who reacted it
            Description += item["Emoji"] + "  " + item["Response"]

            UserString = ""
            for User in item["Users"]:
                if User.id != Vars.Bot.user.id:
                    if UserString:
                        UserString += ", "

                    UserString += User.name
            if UserString:
                Description += "\n     *" + UserString + "*"

        # Now that we have the description, let's re make the embed
        PollEmbed = discord.Embed(title=TitleAdd + PollData["Type"] + ": " + Sys.FirstCap(PollData["Question"]),
                                  description=Description,
                                  color=Color)
        PollEmbed.set_author(name=PollData["MessageAuthor"],
                             icon_url=PollData["MessageAuthorAvatarURL"])

        await PollMessage.edit(embed=PollEmbed)
        await PollMessage.clear_reactions()


    @staticmethod
    async def OnReaction(reaction, user):
        # Ran from OnReaction in Main.py, whenever someone adds a reaction to something

        # First let's run some checks to ensure it's the message we're talking about
        if str(reaction.message.id) not in Poll.RunningPolls.keys():
            return

        PollData = Poll.RunningPolls[str(reaction.message.id)]


        PollMessage = await Helpers.GetMsg(PollData["SentID"], PollData["ChannelID"])

        # If it got an emoji in the list, or stop, continue on
        stop_emoji = Conversation.Emoji["stop"]
        if reaction.emoji == stop_emoji:
            if user.id == Vars.Bot.user.id or int(user.id) == int(PollData["MessageAuthorID"]):

                await Poll.FormatDescription(PollData, PollMessage.reactions, TitleAdd="Closed - ", Color=0x36393e)
                PollMessage = await Helpers.ReGet(PollMessage)

                await PollMessage.clear_reactions()

                await Poll.StopPollRunning(str(PollMessage.id))
                return


        # Now let's deal with the ugly reaction bit
        AllMessageReactions = reaction.message.reactions  # Gets all the reactions on the message sorted by emoji

        for IndividualReaction in AllMessageReactions:
            # If the emoji we're looking at is different from the one the user clicked:
            if IndividualReaction.emoji != reaction.emoji:
                # Var people is a list of everyone who voted for it
                people = await IndividualReaction.users().flatten()

                if user in people:
                    await reaction.message.remove_reaction(IndividualReaction.emoji, user)


class Calculate:
    @staticmethod
    async def OnMessage(message):
        await Calculate.Command(message)

        return

    @staticmethod
    async def Command(message):
        if not await CheckMessage(message, prefix="="):
            return

        if message.content.startswith("=="):  # If people are doing a divider or something
            return

        usableContent = message.content[1:]
        if not usableContent:
            return

        await message.channel.trigger_typing()
        res = wolfram_client.query(usableContent)

        # First, let's see if there was some sort of error in the res process:
        if res["@error"] == 'true':
            em = discord.Embed(description="Wolfram Alpha server Error, try again later.", color=Vars.Bot_Color)
            em.set_author(name="Calculate Error")
            await message.channel.send(embed=em)
            return

        if res["@success"] == 'false':
            em = discord.Embed(description="Wolfram Alpha can't seem to figure out your query. Try rephrasing.", color=Vars.Bot_Color)
            em.set_author(name="Calculate Error")
            await message.channel.send(embed=em)
            return

        em = discord.Embed(title="Calculate", color=Vars.Bot_Color)

        PodList = []
        for pod in res.pods:
            bad_titles = ["AlternateForm"]
            if pod["@id"] not in bad_titles:
                PodList.append(pod)


        for pod in PodList:
            HasImage = False
            if int(pod["@position"]) > 400:
                break

            if int(pod["@numsubpods"]) > 1:
                subpod = pod["subpod"][0]
            else:
                subpod = pod["subpod"]


            image_types = ['image', 'plot', 'musicnotation', 'visualrepresentation', 'structurediagram']

            DoNotShowImageTitles = ['Result', "Number length", "Scientific notation", "Notes"]

            ShowImage = True
            if int(subpod["img"]["@width"]) < 100 or int(subpod["img"]["@height"]) < 50:
                ShowImage = False
            if int(subpod["img"]["@width"]) + int(subpod["img"]["@height"]) < 150:
                ShowImage = False
            if int(subpod["img"]["@width"]) * int(subpod["img"]["@height"]) < 15000:
                ShowImage = False
            if pod["@title"] in DoNotShowImageTitles:
                ShowImage = False

            em = None
            if not HasImage and int(pod["@position"]) > 100 and ShowImage:
                if 'img' in subpod:  # Graph / Plot
                    image_link = subpod["img"]["@src"]
                elif 'imagesource' in subpod:  # Picture
                    image_link = subpod['imagesource']
                else:
                    image_link = False

                if image_link:
                    possible_ends = [".png", ".jpg", ".jpeg", ".gif"]
                    has_ending = False
                    for item in possible_ends:
                        if image_link.lower().strip().endswith(item):
                            has_ending=True
                            break

                    if not has_ending:
                        image_link = image_link + ".jpg"

                    em = discord.Embed(title=pod["@title"], color=Vars.Bot_Color)
                    em.set_image(url=image_link)

            if not em:
                em = discord.Embed(title=pod["@title"], color=Vars.Bot_Color, description=pod.text)

            await message.channel.send(embed=em)
        return


class Tag:
    @staticmethod
    async def OnMessage(message):

        await Tag.SetTag(message)
        await Tag.TagFunction(message)
        await Tag.ClearTagData(message)

        return

    embed_color = Vars.Bot_Color
    @staticmethod
    async def RetrieveTagList():
        # Called internally, retrieves the dictionary of tags
        taglist = Helpers.RetrieveData(type="Tag")
        if not taglist:
            return {}
        return taglist

    @staticmethod
    async def RetrievePTagList(id=None):
        # Called internally, retrieves the dictionary of Personal Tags for an invidual
        AllPTags = Helpers.RetrieveData(type="PTag")
        if not AllPTags:
            return {}
        if not id:
            return AllPTags

        if str(id) not in AllPTags.keys():
            return {}
        else:
            return AllPTags[str(id)]

    @staticmethod
    async def SetTag(message):
        PersonalTag = False
        if not await CheckMessage(message, start=["settag", "st"], prefix=True):  # admin=True):
            if not await CheckMessage(message, start=["setptag", "spt", "psettag"], prefix=True):
                return
            PersonalTag = True
        # Creates the Tag given, starts a TagVote if not an admin.

        async def ReturnError(message, error_message, sendformat=False):
            # If there is some issue, this will make things easier.
            await message.add_reaction(Conversation.Emoji["x"])

            if sendformat:
                format = "```\n/settag Class-Schedule <attach image to message>"
                format += "\n/st Band-Twitter https://www.twitter.com/[...]"
                format += "\n/psettag access-code-for-discord OU812 I814U```"
                error_message += format

            em = discord.Embed(color=Tag.embed_color, description=error_message)
            em.set_author(name="SetTag Error", icon_url=Vars.Bot.user.avatar_url)

            await message.channel.send(embed=em, delete_after=40)
            return

        # Format: /settag cheese-and-stuff https://www.cheese.com
        content = message.content[1:].strip()
        for item in ["settag", "st", "setptag", "psettag"]:
            if content.lower().startswith(item):
                content = content[len(item):].strip()

        if "-a" in content.lower().split(" "):
            AdminTag = True
            SpaceList = content.split(" ")
            NewSpaceList = []
            for part in SpaceList:
                if part.lower() != "-a":
                    NewSpaceList.append(part)
            contentstr = ""
            for part in NewSpaceList:
                if contentstr:
                    contentstr += " " + part
                else:
                    contentstr = part
            content = contentstr
        else:
            AdminTag = False

        if "-f" in content.lower().split(" "):
            ForceTag = True
            SpaceList = content.split(" ")
            NewSpaceList = []
            for part in SpaceList:
                if part.lower() != "-f":
                    NewSpaceList.append(part)
            contentstr = ""
            for part in NewSpaceList:
                if contentstr:
                    contentstr += " " + part
                else:
                    contentstr = part
            content = contentstr
        else:
            ForceTag = False

        # User: > .t TagKey
        # Bot : > TagContent
        TagKey = content.split(" ")[0].strip().lower()
        TagContent = content[len(TagKey):].strip()

        TagKey = TagKey.replace("-", " ")  # Replaces "Cheese-And-Stuff" with "Cheese And Stuff"
        TagKey = TagKey.replace("_", " ")

        # Shorten Links within Tag
        if "http" in TagContent:
            ContentWords = TagContent.split(" ")  # Split by spaces
            for word in ContentWords:
                if "http" in word.lower():  # If this particular word contains the link

                    while not word.lower().startswith("http"):  # Keep going one by one until you find it
                        word = word[1:]
                    # We now have word starting in the right place, but not ending yet
                    if word.endswith("\""):
                        word = word.replace("\"", "")
                    word = word.strip()
                    while "\n" in word:
                        word = word[:len(word)-1]

                    shortened_word = Sys.Shorten_Link(word)
                    # Replace original usage with shortened link
                    TagContent = TagContent.replace(word, shortened_word)

        # ATTACHMENTS
        if message.attachments:
            HasAttachment = True
            AttachmentUploaded = await Helpers.DownloadAndUpload(message, message.attachments[0])

            if not AttachmentUploaded:
                HasAttachment = False
        else:
            HasAttachment = False

        ReservedTags = ["list", "help", "delete", "edit", "info", "random"]


        # Some Fail-Safes about size and stuff
        if TagKey.count(" ") >= 6:
            await ReturnError(message, error_message="Key can only be 6 or less words/numerals", sendformat=True)
            return
        if len(TagKey) > 100:
            await ReturnError(message, error_message="Your key is too long!", sendformat=True)
            return
        if len(TagContent) > 1000:
            await ReturnError(message, error_message="Tag Content is too long!", sendformat=True)
            return
        if not HasAttachment and not TagContent.strip():
            await ReturnError(message, error_message="Missing Tag Content", sendformat=True)
            return
        if TagKey in ReservedTags:
            await ReturnError(message, error_message="Sorry, that tag is reserved for a system function.", sendformat=True)
            return
        if TagKey.lower().startswith("list"):
            try:
                int(TagKey.split(" ")[-1])
                await ReturnError(message, error_message="Sorry, that tag is reserved for a system function.")
                return
            except:
                pass

        # Verify that they're an admin
        IsAdmin = await CheckMessage(message, prefix=True, admin=True, CalledInternally=True)

        if IsAdmin or PersonalTag:
            yes_text = None
        elif not IsAdmin:
            yes_text = "Let's take it to a vote!"

        if not IsAdmin and AdminTag:
            AdminTag = False
        if not IsAdmin and ForceTag:
            ForceTag = False

        # See if TagKey is already used:
        if PersonalTag:
            TagData = await Tag.RetrievePTagList(message.author.id)
        else:
            TagData = await Tag.RetrieveTagList()
        if TagKey in TagData.keys():
            if TagData[TagKey]["Admin"] and not IsAdmin:
                # If the tag they want to overwrite is admin and they are not:
                await ReturnError(message, error_message="This Tag is Occupied by a more important function. Insufficient "
                                           "Permissions to Overwrite.")
                return
            else:
                # If its not an admin tag, give them opportunity to override
                if not PersonalTag:
                    PersonalTagData = await Tag.RetrievePTagList(id=message.author.id)
                    if TagKey not in PersonalTagData.keys():
                        confirmation = await Helpers.Confirmation(message, "Tag already exists. Create Personal Tag?")
                        if confirmation:
                            PersonalTag = True
                            TagData = await Tag.RetrievePTagList(id=message.author.id)
                        else:
                            await ReturnError(message, "To edit, type ```css\n/tag edit " + TagKey + "```")
                elif PersonalTag:
                    SendMsg = "This personal tag is already occupied by you! To edit it, type ```css\n/ptag edit " + TagKey + "```"
                    await message.channel.send(SendMsg)
                    return
        if HasAttachment:
            image = AttachmentUploaded.link
        else:
            image = None


        if not ForceTag:
            if PersonalTag:
                ConfirmMessage = "Create Personal Tag?"
                command = "/ptag"
                footer_text = "You will be the only person able to access this tag."
            else:
                ConfirmMessage = "Create Tag?"
                command = "/tag"
                footer_text = "Everyone will be able to call this tag."
            Extra_Text = "```You Send:  > " + command + " " + TagKey  + "\nI Respond: > " + TagContent.replace("```","\'\'\'") + "```"
            Confirmation = await Helpers.Confirmation(message, ConfirmMessage, extra_text=Extra_Text, add_reaction=False,
                                                  deny_text="Tag Creation Cancelled", yes_text=yes_text,
                                                  image=image, footer_text=footer_text)
            if not Confirmation:
                return

        await message.channel.trigger_typing()

        if not IsAdmin and not PersonalTag:
            # Initiate a Vote
            em = discord.Embed(title="Tag this?", timestamp=Helpers.EmbedTime(), colour=Vars.Bot_Color,
                               description=Extra_Text)
            em.set_author(name=message.author, icon_url=message.author.avatar_url)
            em.set_footer(text="10 minute timeout")
            if HasAttachment:
                em.set_image(url=AttachmentUploaded.link)

            # Send Message
            msg = await message.channel.send("Create Tag?", embed=em)

            def check(init_reaction, init_user):  # Will be used to validate answers
                # Returns if there are 3 more reactions who aren't this bot

                if init_reaction.message.id != msg.id or init_user.id == Vars.Bot.user.id:
                    return False
                if init_reaction.count >= 4  and init_reaction.emoji == Conversation.Emoji["tag"]:
                    return init_reaction, init_user
                else:
                    return False

            await msg.add_reaction(Conversation.Emoji["tag"])

            try:
                # Wait for the reaction(s)
                reaction, user = await Vars.Bot.wait_for('reaction_add', timeout=600, check=check)

            except asyncio.TimeoutError:
                # If it times out
                await Helpers.QuietDelete(msg)
                await message.channel.send("Failed to receive 3 reactions", delete_after=5)
                return None

            # Elif it has all 3 needed
            await Helpers.QuietDelete(msg)

        # If accepted or if IsAdmin:
        NewTagDict = {
            "Key": TagKey,
            "Content": TagContent,
            "Creator": message.author.id,
            "Guild": message.guild.id,
            "Channel": message.channel.id,
            "Time": (datetime.now() + timedelta(hours=3)).timestamp(),
            "Admin": AdminTag,
            "Image": Vars.Bot_Color,
            "Personal": PersonalTag,
            "Color": None
        }
        if HasAttachment:
            NewTagDict["Image"] = AttachmentUploaded.link
        else:
            NewTagDict["Image"] = None

        # Download current data and save the new tag there
        if PersonalTag:
            FullPTagData = await Tag.RetrievePTagList()
            if not FullPTagData:
                FullPTagData = {}

            # Add the key of the ID to the dict
            if str(message.author.id) not in FullPTagData.keys():
                FullPTagData[str(message.author.id)] = {}

            FullPTagData[str(message.author.id)][TagKey] = NewTagDict

            Helpers.SaveData(FullPTagData, type="PTag")

        else:
            FullTagData = await Tag.RetrieveTagList()
            if not FullTagData:  # If it's not yet set up / used
                FullTagData = {}
            # Add the key to the dict
            FullTagData[TagKey] = NewTagDict
            # Save the data and close out
            Helpers.SaveData(FullTagData, type="Tag")

        if not await Helpers.Deleted(message):
            await message.add_reaction(Conversation.Emoji["check"])

        ExitMessage = "Successfully Created "



        if PersonalTag: ExitMessage += "**Personal**"
        elif AdminTag: ExitMessage += " **Admin**"

        ExitMessage += " Tag. To use it, type: ```css\n"

        if PersonalTag: ExitMessage += Sys.FirstCap(message.author.name) + " >> /ptag " + TagKey + "```"
        else: ExitMessage += "/tag " + TagKey + "```"

        await message.channel.send(ExitMessage)
        return

    @staticmethod
    async def GetTag(message, TagKey, PersonalTag=False):
        # Called Internally, retrieves the tag and if it can't, sends a message.
        # Returns None: No tag. Message Sent.
        # Returns TagData

        PTagData = await Tag.RetrievePTagList(id=message.author.id)
        AllTagData = await Tag.RetrieveTagList()

        add = ""

        if PersonalTag:
            if TagKey in PTagData.keys():
                return PTagData[TagKey]
            FullTagData = PTagData
        elif not PersonalTag:
            if TagKey in AllTagData.keys():
                return AllTagData[TagKey]
            FullTagData = AllTagData
            if TagKey in PTagData:
                add = "\nYou have a personal tag named __" + TagKey + "__."

        # If it can't find it:
        DidYouMean = ""
        if TagKey not in FullTagData.keys():
            KeyList = []  # Create list of Tag Keys
            for TagData in FullTagData:
                KeyList.append(FullTagData[TagData]["Key"])

            # Filter out Keys with similar starts
            FirstLetterList = []
            for Key in KeyList:
                if Key.startswith(TagKey[0]):
                    FirstLetterList.append(Key)

            if len(FirstLetterList) > 0:  # If there are any similar starting Tags
                if len(FirstLetterList) > 10:  # Shorten down the list to less than 10
                    NextList = []
                    for value in FirstLetterList:
                        if value.startswith(TagKey[0:2]):
                            NextList.append(value)

                    # Double check that NextList has any values
                    if len(NextList) == 0:
                        NextList = FirstLetterList
                    elif len(NextList) > 10:
                        NextList = FirstLetterList[0:10]

                    FinalList = NextList
                else:
                    FinalList = FirstLetterList

                # Now we have a list of tags to concatenate
                DidYouMean = ""
                for tag in FinalList:
                    if DidYouMean:
                        DidYouMean += ", "
                    DidYouMean += tag

                DidYouMean = "**Did you mean:** *" + DidYouMean + "*?"
            else:
                Tagstring = ""

            if PersonalTag:
                SendString = "Cannot find Key __" + Sys.FirstCap(TagKey) + "__ in your Personal Tag Data!  " + DidYouMean
            else:
                SendString = "Cannot find Key __" + Sys.FirstCap(TagKey) + "__ in Data!  " + DidYouMean

            SendString += add
            await message.channel.send(SendString)

            await message.add_reaction(Conversation.Emoji["x"])
            return None

    @staticmethod
    async def TagFunction(message):
        PersonalTag = False
        if not await CheckMessage(message, start=["t ", "tag"], prefix=True):
            if not await CheckMessage(message, start=["pt ", "ptag"], prefix=True):
                return
            PersonalTag = True

        content = message.content[1:]

        Message_Starts = ["ptag", "tag", "pt", "t"]
        for Start in Message_Starts:
            if content.startswith(Start):
                content = content[len(Start):]
                break

        TagKey = content.lower().strip()
        if not TagKey.strip():
            await Help.InternalHelp(message.channel, type="tag")
            return

        AllTagData = await Tag.RetrieveTagList()

        if TagKey.startswith("list"):
            # If they did /tag list
            if TagKey == "list":
                await Tag.ListTag(message, PersonalTag=PersonalTag)
                return
            # Else, if there's a number afterwards:
            try:
                integer = int(TagKey.split(" ")[-1].strip())
                await Tag.ListTag(message, PersonalTag=PersonalTag)
                return
            except ValueError:
                pass
        if TagKey == "help":
            # If they did /tag help
            await Tag.HelpTag(message) # todo HERE TOO
            return
        if "info" == TagKey.split(" ")[0]:
            # If the key starts with "info"
            await Tag.InfoTag(message, TagKey, PersonalTag=PersonalTag)
            return
        if "edit" == TagKey.split(" ")[0]:
            # /tag edit ___
            await Tag.EditTag(message, TagKey, PersonalTag=PersonalTag)
            return
        if TagKey == "random":
            await Tag.RandomTag(message, PersonalTag=PersonalTag)
            return

        TagData = await Tag.GetTag(message, TagKey, PersonalTag=PersonalTag)
        if not TagData:
            return

        # If it does exist in the data
        # TagData = AllTagData[TagKey]
        if TagData["Admin"]:
            # If it's an admin only tag:
            IsAdmin = await CheckMessage(message, prefix=True, admin=True, CalledInternally=True)
            if not IsAdmin:
                await message.channel.send(Conversation.Emoji["x"] + " This is an admin-only tag! Sorry.")
                await message.add_reaction(Conversation.Emoji["x"])
                return
            # If it is an admin then there's no issue

        if "Color" not in TagData.keys():
            TagData["Color"] = Vars.Bot_Color
        elif not TagData["Color"]:
            TagData["Color"] = Vars.Bot_Color

        em = discord.Embed(description=TagData["Content"], color=TagData["Color"])
        if "Image" in TagData.keys():
            if TagData["Image"]:
                em.set_image(url=TagData["Image"])

        if PersonalTag:
            em.set_footer(text="/ptag " + TagData["Key"])
        else:
            em.set_footer(text="/tag " + TagData["Key"])

        await message.channel.send(embed=em) #TagData["Content"])
        return

    @staticmethod
    async def ClearTagData(message):
        if not await CheckMessage(message, start="ClearTagData", admin=True, prefix=True):
            return

        if not await Helpers.Confirmation(message, "Are you sure you want to clear?"):
            return

        Helpers.SaveData({}, type="Tag")

    @staticmethod
    async def ListTag(message, PersonalTag=False):
        # Called internally with /tag list
        ListDict = {
            "Showing": 0
        }

        if PersonalTag:
            AllTagData = await Tag.RetrievePTagList(id=message.author.id)
            ListType = Sys.FirstCap(message.author.name) + "'s"
        else:
            ListType = "Public"
            AllTagData = await Tag.RetrieveTagList()

        if message.content.strip().split(" ")[-1].lower() != "list":
            # If it's something else added to the end:
            if await CheckMessage(message, admin=True, CalledInternally=True, prefix=True):
                # If they're an admin
                try:
                    User_ID = int(message.content.strip().split(" ")[-1].strip())
                    user = Vars.Bot.get_user(User_ID)

                    AllTagData = await Tag.RetrievePTagList(id=message.content.strip().split(" ")[-1].lower().strip())

                    ListType = Sys.FirstCap(user.name) + "'s"

                except ValueError:
                    pass


        SectionedKeyList = []  # Contains the keys each in groups of 10
        TempList = []
        for FoundTag in sorted(AllTagData):
            # 10 tags per list
            if len(TempList) == 10:  # If there are 10 in the queue
                SectionedKeyList.append(TempList)  # Box them up and put them in the SectionedKeyList
                TempList = []  # Reset Queue
            FoundTag = AllTagData[FoundTag]
            KeyStr = FoundTag["Key"]  # Make string KeyStr that keeps track of the key's name
            if "Image" in FoundTag.keys():
                if FoundTag["Image"]:
                    KeyStr += " [Image]"  # Add quantifier if its an image

            TempList.append(KeyStr)  # Add to TempList

        if TempList:  # If there are any remaining values
            SectionedKeyList.append(TempList)  # Box up and put in SectionedKeyList
            TempList = []

        FinalKeyList = []  # List of strings per page
        for box in SectionedKeyList:
            string = ""
            for key in box:
                if string:
                    string += "\n"
                string += "- " + key
            FinalKeyList.append(string)

        ListDict["Keys"] = FinalKeyList

        # Now send the first message
        if PersonalTag:
            ListType += " Personal"
        title = "List of " + ListType + " Saved Tags"

        if not ListDict["Keys"]:
            em = discord.Embed(description="You have No Personal Tags. Do ```css\n/setptag <key> <tag> <image attachment>``` to create one!")
            em.set_author(name="Personal Tag List Error", icon_url=Vars.Bot.user.avatar_url)
            await message.channel.send(embed=em)
            return

        em = discord.Embed(title=title, description=ListDict["Keys"][0], color=Vars.Bot_Color)
        em.set_footer(text="Page 1/" + str(len(ListDict["Keys"])))
        ListMsg = await message.channel.send(embed=em)

        # If there's only one page, do not show the buttons.
        if len(ListDict["Keys"]) <= 1:
            return

        # Prepare the Buttons
        ButtonNext = Conversation.Emoji["TriangleRight"]
        ButtonBack = Conversation.Emoji["TriangleLeft"]
        ButtonSkip = Conversation.Emoji["SkipRight"]

        ButtonList = [ButtonBack, ButtonNext, ButtonSkip]

        # Add to message
        for button in ButtonList:
            await ListMsg.add_reaction(button)

        StopWhileLoop = False
        while not StopWhileLoop:
            # Standard loop that runs per each reaction added

            # Will be able to remove an indifferent reaction
            async def remove_reaction(init_reaction, init_user):
                # Can remove a reaction without needing async
                await asyncio.sleep(.25)
                await init_reaction.message.remove_reaction(init_reaction.emoji, init_user)
                return

            # Checks to make sure the reaction is valid
            def check(init_reaction, init_user):
                if init_reaction.message.id != ListMsg.id:  # On this message
                    return
                if init_user.id == Vars.Bot.user.id:  # Not a bot
                    return
                if init_reaction.emoji in ButtonList and init_user.id == message.author.id:  # Acceptable Emoji & Origional User
                    return True
                else:  # If not:  Start Async loop to remove reaction
                    Vars.Bot.loop.create_task(remove_reaction(init_reaction, init_user))
                    return

            # Wait for Reaction
            try:
                reaction, user = await Vars.Bot.wait_for('reaction_add', timeout=60, check=check)

            except asyncio.TimeoutError:
                # If timed out
                await ListMsg.clear_reactions()
                StopWhileLoop = True  # Ensure it won't loop again
                break  # Break Loop

            # If we are successful, remove the reaction and check which emoji it is
            Vars.Bot.loop.create_task(remove_reaction(reaction, user))

            # Back Button
            if reaction.emoji == ButtonBack:
                MoveTo = ListDict['Showing'] - 1
                if MoveTo < 0:
                    MoveTo = len(ListDict['Keys']) - 1

            # Next Button
            if reaction.emoji == ButtonNext:
                MoveTo = ListDict['Showing'] + 1
                if MoveTo >= len(ListDict['Keys']):
                    MoveTo = 0

            # Skip Ahead Button
            if reaction.emoji == ButtonSkip:
                if ListDict['Showing'] == len(ListDict["Keys"]) - 1:
                    MoveTo = 0
                else:
                    MoveTo = len(ListDict["Keys"]) - 1

            # Update ListDict
            ListDict['Showing'] = MoveTo

            # Update Message / Send it
            em = discord.Embed(title="List of Saved Tags", description=ListDict["Keys"][MoveTo], color=Vars.Bot_Color)
            em.set_footer(text="Page " + str(MoveTo +1) + "/" + str(len(ListDict['Keys'])))
            await ListMsg.edit(embed=em)

            # Update the message item we have
            ListMsg = await Helpers.ReGet(ListMsg)

        # When we're out of the loop now:
        em = discord.Embed(title="List of Saved Tags", description=ListDict["Keys"][ListDict["Showing"]])
        em.set_footer(text="Page " + str(ListDict["Showing"] + 1) + "/" + str(len(ListDict['Keys'])) + " - /tag List")
        await ListMsg.edit(embed=em)
        return

    @staticmethod
    async def HelpTag(message):
        HelpDesc = "The Tag Command allows me to remember certain images, links, or phrases and send them after a key " \
                   "phrase is given, IE `/tag tailgate`" \
                   "\n\n**To Call A Tag**\n" \
                   "- To call a tag in my memory, type `/tag ___` or `/t ___` with the appropriate key." \
                   "\n\n **To Create a Tag**\n" \
                   "- To create a tag, type `/settag <key> <content>`. For example, You could say `/settag Dog I like Dogs`" \
                   ". When you type `/t dog`, I'll respond with 'I like Dogs'." \
                   "\n- Sometimes I decide to call a vote on a tag if I feel it may be niche or bad." \
                   "\n- If you want to tag with an image, type `/settag <key>` in the message attached to the image. You can" \
                   "have an image and content such as a link in the same tag. " \
                   "\n- *Keep in mind that I upload all images to Imgur and shorten all links using TinyURL" \
                   "\n\n**Helpful Commands**" \
                   "\n  -  /tag Help" \
                   "\n  -  /tag List" \
                   "\n  -  /tag Info ____" \
                   "\n  -  /tag Edit ____"
        em = discord.Embed(title="Tag Help", description=HelpDesc, color=Vars.Bot_Color)
        await message.channel.send(embed=em)
        return

    @staticmethod
    async def InfoTag(message, TagKey, PersonalTag=False):
        # Display some info about the tag's creation

        if PersonalTag:
            AllTagData = await Tag.RetrievePTagList(id=message.author.id)
        else:
            AllTagData = await Tag.RetrieveTagList()

        TagKey = TagKey.replace("info", "").strip()

        TagData = await Tag.GetTag(message, TagKey, PersonalTag=PersonalTag)
        if not TagData:
            return


        SendMsg = "```\nKey: " + TagData["Key"]
        SendMsg += "\nContent: " + TagData["Content"]
        SendMsg += "\nCreator: " + Vars.Bot.get_user(TagData["Creator"]).name + " (" + str(TagData["Creator"]) + ")"
        SendMsg += "\nGuild: " + Vars.Bot.get_guild(TagData["Guild"]).name + " (" + str(TagData["Guild"]) + ")"
        SendMsg += "\nTime: " + str(datetime.fromtimestamp(TagData["Time"]))
        SendMsg += "\nAdmin Only? " + str(TagData["Admin"])
        SendMsg += "\nImage: " + str(TagData["Image"])
        SendMsg += "\nColor: " + str(TagData["Color"])

        SendMsg += "\n```"
        if PersonalTag:
            title = "Personal Tag Info"
        else:
            title = "Tag Info"
        em = discord.Embed(title=title, description=SendMsg, color=Vars.Bot_Color)

        if TagData["Image"]:
            em.set_image(url=TagData["Image"])

        await message.channel.send(embed=em)
        return

    @staticmethod
    async def EditTag(message, TagKey, PersonalTag=False):
        if PersonalTag:
            AllTagData = await Tag.RetrievePTagList(id=message.author.id)
        else:
            AllTagData = await Tag.RetrieveTagList()

        TagKey = TagKey.replace("edit", "").strip()

        if PersonalTag:
            TagType = "Personal Tag"
        else:
            TagType = "Tag"

        async def SaveData(TagData, PersonalTag):
            if PersonalTag:
                PersonalTagData = await Tag.RetrievePTagList()
                PersonalTagData[str(message.author.id)] = TagData
                Helpers.SaveData(PersonalTagData, type="PTag")
                return
            elif not PersonalTag:
                Helpers.SaveData(TagData, type="Tag")

        if not PersonalTag:
            if message.author.id not in Ranks.Admins:
                return

        TagData = await Tag.GetTag(message, TagKey, PersonalTag=PersonalTag)
        if not TagData:
            return

        # Prepare Dialogue asking what action they wish to do
        ChoiceBoxString = ":one:  Change Tag Key\n:two:  Change Tag Content\n:three:  Change Tag Image" \
                          "\n:four:  Change Tag Color\n:five:  Delete Tag"
        em = discord.Embed(title="Edit " + TagType + ": " + TagKey, description=ChoiceBoxString)
        ChoiceBoxMsg = await message.channel.send(embed=em)

        ['\U0001F1E6', '\U0001F1E7', '\U0001F1E8', '\U0001F1E9', '\U0001F1EA', '\U0001F1EB',
         '\U0001F1EC', '\U0001F1ED', '\U0001F1EE', '\U0001F1EF']

        ReactOne   = '\U0001F1E6'
        ReactTwo   = '\U0001F1E7'
        ReactThree = '\U0001F1E8'
        ReactFour  = '\U0001F1E9'
        ReactFive  = '\U0001F1EA'

        ReactList = [ReactOne, ReactTwo, ReactThree, ReactFour, ReactFive]

        for reaction in ReactList:
            await ChoiceBoxMsg.add_reaction(reaction)

        # Remove Reaction Function
        async def remove_reaction(init_reaction, init_user):
            # Can remove a reaction without needing async
            await init_reaction.message.remove_reaction(init_reaction.emoji, init_user)
            return

        def check(init_reaction, init_user):
            if init_user.id == Vars.Bot.user.id:
                return False
            if init_reaction.emoji in ReactList and init_user.id == message.author.id:
                return True
            else:
                Vars.Bot.loop.create_task(remove_reaction(init_reaction, init_user))

        try:
            reaction, user = await Vars.Bot.wait_for('reaction_add', timeout=60, check=check)

        except asyncio.TimeoutError:
            # If timed out
            await message.send("Edit Timed Out.")
            await Helpers.QuietDelete(ChoiceBoxMsg)
            return

        await Helpers.QuietDelete(ChoiceBoxMsg)

        # Now we find which they chose
        if reaction.emoji == ReactOne:
            EditMode = "Key"
        if reaction.emoji == ReactTwo:
            EditMode = "Content"
        if reaction.emoji == ReactThree:
            EditMode = "Image"
        if reaction.emoji == ReactFour:
            EditMode = "Color"
        if reaction.emoji == ReactFive:
            EditMode = "Delete"

        # Delete tag if requested
        if EditMode == "Delete":
            if not await Helpers.Confirmation(message, "Delete " + TagType + "? " + TagKey):
                return
            AllTagData.pop(TagKey)
            await SaveData(AllTagData, PersonalTag)
            await message.channel.send("Deleted " + TagType + " " + TagKey + " from RedBot Database")
            await message.add_reaction(Conversation.Emoji["check"])
            return

        ResponsePrompt = await message.channel.send("Okay, send the new **" + EditMode + "** that you desire for your "
                                                    + TagType + ".")

        def check2(init_msg):
            if init_msg.author.id == message.author.id:
                return True

        try:
            ResponseMsg = await Vars.Bot.wait_for('message', timeout=60, check=check2)

        except asyncio.TimeoutError:
            await message.send("Edit Timed Out.")
            await Helpers.QuietDelete(ChoiceBoxMsg)
            return


        await Helpers.QuietDelete(ResponsePrompt)
        await message.channel.trigger_typing()

        # Okay so now we have the new part of the tag, so it's time to split off and run the command per grouping

        # KEY
        if EditMode == "Key":
            NewKey = ResponseMsg.content.strip().replace("-", " ").lower()
            if len(NewKey) > 100:
                await message.channel.send("Key is too long!")
                return
            elif NewKey.count(" ") >= 6:
                await message.channel.send("Key has too many spaces!")
                return
            elif NewKey in AllTagData:
                await message.channel.send(TagType + " already exists!")
                return

            # if Key is good:
            TagData["Key"] = NewKey

        elif EditMode == "Content":
            NewContent = ResponseMsg.content.strip()

            # Shorten any links
            if "http" in NewContent:
                ContentWords = NewContent.split(" ")  # Split by spaces
                for word in ContentWords:
                    if "http" in word.lower():  # If this particular word contains the link

                        while not word.lower().startswith("http"):  # Keep going one by one until you find it
                            word = word[1:]
                        # We now have word starting in the right place, but not ending yet
                        if word.endswith("\""):
                            word = word.replace("\"", "")
                        word = word.strip()
                        while "\n" in word:
                            word = word[:len(word) - 1]

                        shortened_word = Sys.Shorten_Link(word)
                        # Replace original usage with shortened link
                        NewContent = NewContent.replace(word, shortened_word)

            # Okay so now all links are shortened, check length:
            if len(NewContent) > 1000:
                await message.channel.send("Too long!")
                return

            # if it's cleared to go
            TagData["Content"] = NewContent

        elif EditMode == "Image":
            try:
                NewImage = ResponseMsg.attachments[0]
            except:
                await message.channel.send("You forgot to attach an image, bud.")
                return

            ImageLink = await Helpers.DownloadAndUpload(message, NewImage)
            NewImage = ImageLink.link
            TagData["Image"] = NewImage

        elif EditMode == "Color":
            # Ensure the content is a color
            try:
                color = discord.Colour(int(ResponseMsg.content.strip(), 16))
            except:
                failure = "Please use a Hex Code. Try this link: "
                failure += Sys.Shorten_Link('https://www.webpagefx.com/web-design/color-picker/')
                second_message = await message.channel.send(failure)
                return

            TagData["Color"] = str(color).replace("#","")
            TagData['Color'] = color.value

        await Helpers.QuietDelete(ResponseMsg)

        # So at this point we have an updated TagData Dict to use
        if not "Color" in TagData.keys():
            TagData["Color"] = Vars.Bot_Color

        ConfirmMessage = "This is the " + TagType + " you want?"
        if PersonalTag:
            Command = "/ptag "
        else:
            Command = "/tag "

        if not TagData["Color"]:
            TagData["Color"] = Vars.Bot_Color
        Extra_Text = "```You Send:  > " + Command + TagData["Key"] + "\nI Respond: > " + TagData["Content"].replace("```", "\'\'\'") + "```"
        Confirmation = await Helpers.Confirmation(message, ConfirmMessage, extra_text=Extra_Text, add_reaction=False,
                                                  deny_text= TagType + " Edit Cancelled",
                                                  image=TagData["Image"], color=TagData["Color"])
        if not Confirmation:
            return

        # If they confirmed it:
        AllTagData.pop(TagKey)
        AllTagData[TagData["Key"]] = TagData

        # Set it in the new dict
        await SaveData(AllTagData, PersonalTag)

        ExitMessage = "Successfully Edited the " + TagType + ". To use it, type: ```css\n" + Command + TagData["Key"] + "```"
        await message.channel.send(ExitMessage)

        return

    @staticmethod
    async def RandomTag(message, PersonalTag=False):
        # Called if /tag random
        if PersonalTag:
            AllTagData = await Tag.RetrievePTagList(id=message.author.id)
        else:
            AllTagData = await Tag.RetrieveTagList()

        SelectedTagKey = random.choice(list(AllTagData.keys()))

        TagData = AllTagData[SelectedTagKey]

        if TagData["Admin"]:
            # If it's an admin only tag:
            IsAdmin = await CheckMessage(message, prefix=True, admin=True, CalledInternally=True)
            if not IsAdmin:
                await message.channel.send("This is an admin-only tag! Sorry.")
                await message.add_reaction(Conversation.Emoji["x"])
                return
            # If it is an admin then there's no issue

        if "Color" not in TagData.keys():
            TagData["Color"] = Vars.Bot_Color
        elif not TagData["Color"]:
            TagData["Color"] = Vars.Bot_Color

        em = discord.Embed(description=TagData["Content"], color=TagData["Color"])
        if "Image" in TagData.keys():
            if TagData["Image"]:
                em.set_image(url=TagData["Image"])
        em.set_footer(text="/tag " + TagData["Key"])

        await message.channel.send(embed=em) #TagData["Content"])
        return


class Remind:
    # Working on the new /remind command
    embed_color = 0x4286f4

    @staticmethod
    async def RemindCommand(message):
        if not await CheckMessage(message, start="remind ", prefix=True):
            return

        await message.channel.trigger_typing()

        usablecontent = message.content[7:].strip()

        if type(message.channel) == discord.channel.DMChannel:
            DMChannel = True
        else:
            DMChannel = False

        if not DMChannel: # TODO Update Cooldown to work on DM Channels
            cd_notice = Cooldown.CheckCooldown("remind", message.author, message.guild)
            if type(cd_notice) == int:
                await message.channel.send('Cooldown Active, please wait: `' + Sys.SecMin(cd_notice) + '`', delete_after=5)
                await message.add_reaction(Conversation.Emoji["x"])
                return


        # Let's take a look for any images in the Reminds
        if message.attachments:
            IsImage = message.attachments[0]
            # Save IsImage
            IsImage = await Helpers.DownloadAndUpload(message, IsImage)
            IsImage = IsImage.link
        else:
            IsImage = None


        # Let's shorten any links in the reminder
        if "http" in usablecontent.lower():
            temporary = usablecontent + ''
            TempParts = temporary.strip().split(" ")

            for section in TempParts:
                if section.lower().startswith("http"):  # If that word is a link:
                    shortened = Sys.Shorten_Link(section)
                    temporary = temporary.replace(section, shortened)

            usablecontent = temporary

        # So we need to first figure out if the bot is given a specific time today, or an amount of time to wait.
        # Unlack usablecontent into each individual word

        async def ReturnError(message, error_message, sendformat=False):
            # If there is some issue, this will make things easier.
            await message.add_reaction(Conversation.Emoji["x"])

            if sendformat:
                format = "```\n/remind 2 days Clean Your Room"
                format += "\n/remind 12:45 Hello there"
                format += "\n/remind 2 hours 35 minutes These are Examples```"
                error_message += format

            em = discord.Embed(color=Remind.embed_color, description=error_message)
            em.set_author(name="Reminder Error", icon_url=Vars.Bot.user.avatar_url)

            await message.channel.send(embed=em, delete_after=40)
            return

        def CheckUnit(string):
            # Checks to see if the string is a real unit of time
            string = string.lower().strip()
            unitlist = ["second", "minute", "hour", "day", "week", "month", "year", "decade", "am", "pm"]

            fulllist = []

            for item in unitlist:
                fulllist.append(item)
                fulllist.append(item + "s")

            if string.lower().strip() in fulllist:
                return True

            return False

        contentwords = usablecontent.split()

        if len(contentwords) < 2:
            await ReturnError(message, "You need to follow the format:", sendformat=True)

            return

        # Now let's analyze the first thing, and see if it's a time or a number
        firstitem = contentwords[0]
        firstitemtype = None

        if firstitem.startswith("<@!"):
            SendToUser = firstitem
            contentwords = contentwords[1:]
            firstitem = contentwords[0]

            message.content = message.content.replace(SendToUser, "").strip()

        else:
            SendToUser = None

        if SendToUser:
            SendToUser = int(SendToUser[3:].replace(">",""))
            SendToUser = Vars.Bot.get_user(SendToUser)

            if not SendToUser:
                await ReturnError(message, "Cannot find the person you speak of!")
                return

            if DMChannel:
                # TODO This thread should eventually talk to the person in their own DM Channel
                await ReturnError(message, "You can only remind yourself in a DM Channel!")
                return

        if not SendToUser:
            SendToUser = message.author
            #await ReturnError(message, "Cannot find the person you speak of!")
            #return

        try:
            firstitem = int(firstitem)
            firstitemtype = "Number"  # A number is associated with a unit of time to wait
        except:
            if ":" in firstitem:
                firstitemtype = "Time"  # A time is a specific time to go off
            if "/" in firstitem or "-" in firstitem:
                firstitemtype = "Date"

        if firstitemtype == "Number" and contentwords[1].lower() in ["am", "pm"]:
            firstitemtype = "Time"  # A simple time is "3 am" instead of "3:00 am"
            usablecontent = usablecontent.replace(contentwords[0], contentwords[0] + ":00")
            firstitem = contentwords[0] = str(firstitem) + ":00"

        # Now our goal is to develop a time object based on the given information
        RemindTime = None  # Goal is to populate this with a time on when to populate it
        RemindMessage = None    # Goal is to have a string here to send with the reminder


        if firstitemtype == "Number":  # "3 hours 2 days 1 minute"
            timedata = []  # Will be populated with all of the wait time information
            tempMsg = []

            i = 0
            stop = False
            while not stop:
                if contentwords[i].isdigit():
                    int(contentwords[i])  # Try to make it an integer, see if it's a number
                    # If it's successful, see if the next item is a unit

                    if i < len(contentwords) - 1:

                        # Now that we know that we're not at the end of the message:
                        if CheckUnit(contentwords[i+1]):
                            # Double Check that the next item is a unit
                            TempTimeDict = {
                                "Amount": contentwords[i],
                                "Unit": contentwords[i+1]
                            }
                            timedata.append(TempTimeDict)
                elif CheckUnit(contentwords[i]):
                    pass
                else:
                    for j in range(i, len(contentwords)):
                        tempMsg.append(contentwords[j])
                    stop = True

                if i == len(contentwords) - 1:
                    stop = True
                i += 1

            # Now we have a list timedata that lists all the criteria from now. We need to isolate the new message
            # ISOLATE THE MESSAGE

            NowTime = datetime.now()  # Current Time Dict
            LaterTime = NowTime + timedelta()

            for timeitem in timedata:  # Clean up timedata
                if timeitem["Unit"].endswith("s"):  # Remove any plural units
                    timeitem["Unit"] = timeitem["Unit"][0:len(timeitem["Unit"])-1]

                timeitem["Amount"] = int(timeitem["Amount"])  # Make integer Amounts

                if timeitem["Unit"] in ["month", "year", "decade", "second"]:  # Ensure only accepted units are used
                    await ReturnError(message, "Unit `" + timeitem["Unit"] + "` "
                                               "not supported! Try: `minute`, `hour`, `day`, `week`")
                    return

            for timeitem in timedata:
                if timeitem["Unit"] == "minute":
                    LaterTime = LaterTime + timedelta(minutes=timeitem["Amount"])

                if timeitem["Unit"] == "hour":
                    LaterTime = LaterTime + timedelta(hours=timeitem["Amount"])

                if timeitem["Unit"] == "day":
                    LaterTime = LaterTime + timedelta(days=timeitem["Amount"])

                if timeitem["Unit"] == "week":
                    LaterTime = LaterTime + timedelta(weeks=timeitem["Amount"])

            tempString = ""
            for item in tempMsg:
                tempString += item + " "

            RemindMessage = Sys.FirstCap(tempString.strip())
            RemindTime = LaterTime


        elif firstitemtype == "Time" or firstitemtype == "Date":
            # Okay so now we're looking for any part of a Time or Date

            info = []

            i = 0
            stop = False
            while not stop:
                CurrentPhrase = contentwords[i]

                if ":" in CurrentPhrase and not CurrentPhrase.lower().strip().startswith("http"):
                    # So this is a time
                    if CurrentPhrase.count(":") > 1:
                        await ReturnError(message, CurrentPhrase + " is not a valid time! Hr:Mn is.")
                        return

                    TempDict = {
                        "Type": "Time",
                        "Hour": CurrentPhrase.split(":")[0],
                        "Minute": CurrentPhrase.split(":")[1]
                    }

                    OriginalNote = CurrentPhrase
                    AMPM = None
                    if i < len(contentwords) - 1:
                        # As long as there's enough for another word:
                        if contentwords[i + 1].lower().strip() in ["am", "pm"]:
                            AMPM = contentwords[i + 1]
                            OriginalNote += " " + contentwords[i + 1]

                    if not AMPM:  # If there is no given AM or PM, the bot guesses
                        if 8 < int(CurrentPhrase.split(":")[0]) < 11:
                            AMPM = "am"

                        elif int(CurrentPhrase.split(":")[0]) == 12:
                            AMPM = "pm"
                        else:
                            AMPM = "pm"

                    TempDict["AMPM"] = AMPM
                    TempDict["Original"] = OriginalNote


                    info.append(TempDict)

                if "-" in CurrentPhrase:
                    CurrentPhrase = CurrentPhrase.replace("-", "/")

                if "/" in CurrentPhrase and not CurrentPhrase.lower().strip().startswith("http"):
                    # First we need to see if a year is included
                    if CurrentPhrase.count("/") >= 3:
                        await ReturnError(message, "Date is improper: Mo/Da/Year")
                        return

                    # These are the 3 items we need to populate
                    Month = None
                    Day = None
                    Year = None

                    GivenFirst = CurrentPhrase.split("/")[0]
                    GivenSecond = CurrentPhrase.split("/")[1]

                    if CurrentPhrase.count("/") == 1:  # First, let's deal with the year
                        # No year, so Mo/Da:
                        Year = datetime.now().strftime("%Y")

                    else:  # So Mo/Da/Yr
                        GivenYear = CurrentPhrase.split("/")[2]

                        if not GivenYear.isdigit():
                            await ReturnError(message, "Year is not integer: Try Format Mo/Da/Year, or just Mo/Da")
                            return

                        if len(str(GivenYear)) == 4:
                            Year = int(GivenYear)
                        elif len(str(GivenYear)) == 2:
                            Year = 2000 + int(GivenYear)

                        else:
                            # Improper Year?
                            await ReturnError(message, "Year is improper: Either do Mo/Da/Year or Mo/Da/Yr")
                            return

                    # So now we have a year, so we need to convert GivenFirst and GivenSecond into integers and compare
                    if not GivenFirst.isdigit():
                        await ReturnError(message, "Improper Date! Please only use numbers: Mo/Da/Yr")
                        return
                    else:
                        GivenFirst = int(GivenFirst)

                    if not GivenSecond.isdigit():
                        await ReturnError(message, "Improper Date! Please only use numbers: Mo/Da/Yr")
                        return
                    else:
                        GivenSecond = int(GivenSecond)

                    # Now we should assume that FirstGiven is month, unless proven otherwise:
                    GivenMonth, GivenDay = None, None

                    if 12 < GivenFirst:
                        if 12 < GivenSecond:
                            # If both the month and the day are bigger than 12:
                            await ReturnError(message, "Improper Date! Please only use numbers: Mo/Da/Yr")
                            return

                        else: # If the second item is the month:
                            GivenMonth = GivenSecond
                            GivenDay = GivenFirst
                    else:
                        GivenMonth = GivenFirst
                        GivenDay = GivenSecond

                    info.append(
                        {
                            "Type": "Date",
                            "Day": GivenDay,
                            "Month": GivenMonth,
                            "Year": GivenYear,
                            "Original": CurrentPhrase
                        }
                    )

                if i >= len(contentwords) -1:
                    stop = True

                i += 1

            # Okay so now we have a list (info) that describes all of the dates and times mentioned in the message
            # What we next need to do is ensure that there is one date and one time present
            ReminderDate = None
            ReminderTime = None

            for item in info:
                if not ReminderDate and item["Type"] == "Date":
                    ReminderDate = item

                if not ReminderTime and item["Type"] == "Time":
                    ReminderTime = item

            # Now we have the first date and first item of the message. We now need to work on fixing any missing holes
            if not ReminderTime:
                # Todo Prompt for another time
                ReminderTime = {
                    "Type": "Time",
                    "Hour": '8',
                    "Minute": '01',
                    "AMPM": 'am'
                }

            if not ReminderDate:

                def HourStampMaker(input):
                    # Makes HourStamp "2356" for comparing times
                    Hour = int(input.strftime("%H")) * 100
                    HourStamp = Hour + int(input.strftime("%M"))
                    return HourStamp

                NowHourStamp = HourStampMaker(datetime.now())

                # Now let's make an HourStamp for the proposed time
                PartialHourStamp = int(ReminderTime["Hour"])
                PartialHourStamp += 12 if ReminderTime["AMPM"] == "pm" else 0
                PartialHourStamp = PartialHourStamp * 100

                RemindHourStamp = PartialHourStamp + int(ReminderTime["Minute"])


                if RemindHourStamp < NowHourStamp:  # If the time to remind already happened, the day should be one more
                    tempday = int(datetime.now().strftime('%d')) + 1
                    tempmonth = int(datetime.now().strftime('%m'))
                    tempyear = int(datetime.now().strftime('%y'))

                    endmonth, endday, endyear = Sys.DateFixer(tempmonth, tempday, tempyear)

                    ReminderDate = {
                        "Type": "Date",
                        "Day": endday,
                        "Month": endmonth,
                        "Year": endyear
                    }
                elif RemindHourStamp > NowHourStamp:  # If the reminder is later that day
                    tempday = int(datetime.now().strftime('%d'))
                    tempmonth = int(datetime.now().strftime('%m'))
                    tempyear = int(datetime.now().strftime('%y'))

                    endmonth, endday, endyear = Sys.DateFixer(tempmonth, tempday, tempyear)

                    ReminderDate = {
                        "Type": "Date",
                        "Day": endday,
                        "Month": endmonth,
                        "Year": endyear
                    }
                else:  # If the time is now
                    await ReturnError(message, "The Time Given is NOW!")
                    return


            # So, now we have ReminderDate and ReminderTime. Time to make a time object out of it
            # First, a bit of cleaning up
            Day = str(ReminderDate["Day"])
            Month = str(ReminderDate["Month"])
            Year = str(ReminderDate["Year"])

            Hour = str(ReminderTime["Hour"])
            Minute = str(ReminderTime["Minute"])

            if Hour == "12" and AMPM == "AM":
                Hour = "0"
                Day = str(int(Day) + 1)

            if len(Year) > 2:
                Year = Year[-2 : len(Year)]  # Ensure we just have the last two digits of the date

            if len(Day) == 1:
                Day = "0" + Day

            if len(Month) == 1:
                Month = "0" + Month

            DateString = Month + " " + Day + " " + Year

            if ReminderTime["AMPM"].lower() == "pm" and int(Hour) <= 12:
                Hour = str( int(Hour) + 12 )

            if int(Hour) == 24:
                Hour = "12"

            if len(Hour) == 1:
                Hour = "0" + Hour

            if len(Minute) == 1:
                Minute = "0" + Minute

            TotalString = DateString + " " + Hour + " " + Minute

            EndTimeStamp = time.strptime(TotalString, "%m %d %y %H %M")

            # Let's deal with the message
            usablecontent = usablecontent.strip()

            if "Original" not in ReminderDate.keys():
                ReminderDate["Original"] = ""

            if "Original" not in ReminderTime.keys():
                ReminderTime["Original"] = ""

            usablecontent = usablecontent.replace(ReminderDate["Original"], "").replace(ReminderTime["Original"], "")

            RemindMessage = Sys.FirstCap(usablecontent.strip())
            RemindTime = EndTimeStamp


        # Okay so at this point we should have a time object and a remind string... A few more failsafes before we get into the fun!

        # First let's make sure the time hasn't happened already
        CurrentTime = datetime.now()

        if not RemindTime:
            RemindTime = datetime.now() + timedelta(minutes=15)
            RemindMessage = Sys.FirstCap(usablecontent.strip())

        if type(RemindTime) == time.struct_time:
            RemindTime = datetime.fromtimestamp(time.mktime(RemindTime))

        if RemindTime < CurrentTime:
            await ReturnError(message, "Time " + str(RemindTime) + " has already happened!", sendformat=True)
            return

        if len(RemindMessage) > 250:
            await ReturnError(message, "Your Reminder Message is too long! Keep it less than 250 characters!")
            return

        if RemindTime > CurrentTime + timedelta(days=14):
            await ReturnError(message, "The maximum time you can set a reminder is 14 Days!")
            return

        # Okay so now we're ready to deal with the confirmation
        toSendDateString = RemindTime.strftime("%A, %B %d, %Y at %I:%M %p")

        string = "```md\n# " + toSendDateString + "\nI say: > @" + SendToUser.name + ", " + RemindMessage + "```"

        ReminderData = await Remind.SaveReminder(RemindTime, RemindMessage, message, SendToUser, IsImage)

        em = discord.Embed(color=Remind.embed_color, description=string)
        if SendToUser.id == message.author.id:
            em.set_author(name="Okay, I'll Remind You", icon_url=Vars.Bot.user.avatar_url)
        else:
            em.set_author(name="Okay, I'll Remind " + SendToUser.name, icon_url=Vars.Bot.user.avatar_url)

        if IsImage:
            em.set_image(url=IsImage)

        em.set_footer(text="Want to cancel? Hit the X reaction below. ")

        sent = await message.channel.send(embed=em)

        await Log.LogCommand(message, "Reminder", "Successfully Set Reminder", DM=DMChannel)

        if DMChannel:
            reaction_to_add = Conversation.Emoji["check"]
        else:
            reaction_to_add = Conversation.Emoji["clock"]

        await message.add_reaction(reaction_to_add)

        # Now we'll add the x to cancel the reminder
        await sent.add_reaction(Conversation.Emoji["x"])
        def Check(reaction, user):
            if reaction.emoji == Conversation.Emoji["x"]:
                if user.id == message.author.id:
                    if reaction.message.id == sent.id:
                        return True
            return False

        Stop = False
        while not Stop:
            try:
                reaction, user = await Vars.Bot.wait_for("reaction_add", check=Check, timeout=50)
                break

            except asyncio.TimeoutError:
                if not await Helpers.Deleted(sent):
                    await sent.clear_reactions()

                reaction, user = None, None
                break

        if reaction and user:
            await Remind.DeleteSpecificReminder(ReminderData)
            await Helpers.QuietDelete(sent)
            await message.channel.send("I have deleted the reminder. Try again?", delete_after=10)
            if not await Helpers.Deleted(message):
                await message.clear_reactions()
                await message.add_reaction(Conversation.Emoji["x"])

        await Helpers.QuietDelete(sent, wait=60)

        return

    @staticmethod
    async def DateStamp(dt):
        # Returns timestamp with seconds = 0
        dt = dt.replace(second=0, microsecond=0)

        stamp = datetime.timestamp(dt)

        return round(stamp)

    @staticmethod
    async def SaveReminder(RemindTime, RemindMessage, message, SendToUser, Image):
        # Saves the Reminder in the data
        RemindStamp = await Remind.DateStamp(RemindTime)
        To_Add = {
            "RemindStamp": RemindStamp,
            "Message": RemindMessage,
            "Author": message.author.id,
            "Created_At": await Remind.DateStamp(datetime.now()),
            "OriginalMessage": message.content,
            "OriginalMessageID": message.id,
            "Channel": message.channel.id,
            "RemindPerson": SendToUser.id,
            "Image": Image,
            "Repeat": 0
        }

        if type(message.channel) == discord.channel.DMChannel:  # If it's a Direct Message Channel
            To_Add["Guild"] = None
        else:
            To_Add["Guild"] = message.guild.id

        PreviousReminders = Helpers.RetrieveData(type="Remind")
        if not PreviousReminders:
            PreviousReminders = {}

        if str(RemindStamp) in PreviousReminders.keys():
            PreviousReminders[str(RemindStamp)].append(To_Add)
        else:
            PreviousReminders[str(RemindStamp)] = [To_Add]

        Helpers.SaveData(PreviousReminders, type="Remind")
        return To_Add

    @staticmethod
    async def ReSaveReminder(Reminder, NewTime):
        # Saves the Reminder in the data
        RemindStamp = await Remind.DateStamp(NewTime)

        Reminder["RemindStamp"] = RemindStamp

        if "Repeat" not in Reminder.keys():
            Reminder["Repeat"] = 1

        else:
            Reminder["Repeat"] += 1

        To_Add = Reminder

        PreviousReminders = Helpers.RetrieveData(type="Remind")
        if not PreviousReminders:
            PreviousReminders = {}

        if str(RemindStamp) in PreviousReminders.keys():
            PreviousReminders[str(RemindStamp)].append(To_Add)
        else:
            PreviousReminders[str(RemindStamp)] = [To_Add]

        Helpers.SaveData(PreviousReminders, type="Remind")
        return To_Add

    @staticmethod
    async def DeleteReminder(RemindStamp):
        PreviousRemindData = Helpers.RetrieveData(type="Remind")

        if str(RemindStamp) in PreviousRemindData.keys():
            del PreviousRemindData[str(RemindStamp)]

        Helpers.SaveData(PreviousRemindData, type="Remind")
        return

    @staticmethod
    async def DeleteSpecificReminder(Reminder):
        PreviousReminderData = Helpers.RetrieveData(type="Remind")

        RemindStamp = str(Reminder["RemindStamp"])

        if RemindStamp not in PreviousReminderData.keys():
            return None

        # Try to find the place in which the reminder is located
        try:
            RemindPlaceIndex = PreviousReminderData[RemindStamp].index(Reminder)
        except ValueError:  # If it's not there, return
            return None

        # Delete the place in which the reminder is located within the list dict
        del PreviousReminderData[RemindStamp][RemindPlaceIndex]

        if not PreviousReminderData[RemindStamp]:
            del PreviousReminderData[RemindStamp]

        Helpers.SaveData(PreviousReminderData, type="Remind")

        return True


    @staticmethod
    async def CheckForReminders():
        RemindData = Helpers.RetrieveData(type="Remind")

        if not RemindData:
            return

        Now = await Remind.DateStamp(datetime.now())

        if str(Now) in RemindData.keys():
            # If there are reminders to be done now
            await Remind.SendReminder(RemindData[str(Now)], Now)

        else:
            return False

    @staticmethod
    async def SendReminder(RemindList, Now, Add=""):
        SentMsg = None

        for Reminder in RemindList:
            # For each reminder given
            ContentMessage = Reminder["Message"]
            if "Image" in Reminder.keys():
                if Reminder["Image"]:
                    ContentMessage += " [Image]"
            em = discord.Embed(color=Remind.embed_color, description=Reminder["Message"])
            em.set_author(name="Reminder:", icon_url=Vars.Bot.user.avatar_url)

            if Reminder["Author"] == Reminder["RemindPerson"]:
                AddFooter = Reminder["OriginalMessage"]
            else:
                OriginalPerson = Vars.Bot.get_user(int(Reminder["Author"]))
                AddFooter = OriginalPerson.name + ": " + Reminder["OriginalMessage"]

            if len(AddFooter) > 40:
                AddFooter = AddFooter[0:40] + "[...]"

            if Reminder["Repeat"] >= 1:
                AddFooter += " | You have been reminded " + str(Reminder["Repeat"]) + " time"
                if Reminder["Repeat"] >= 2:
                    AddFooter += "s"

                AddFooter += "."


            em.set_footer(text=AddFooter)

            if "Image" in Reminder.keys():
                if Reminder["Image"]:
                    em.set_image(url=Reminder["Image"])

            SendChannel = Vars.Bot.get_channel(int(Reminder["Channel"]))
            RemindPerson = Vars.Bot.get_user(int(Reminder["RemindPerson"]))
            RemindPersonMention = RemindPerson.mention

            if SendChannel:
                Good_To_Send = False
                if type(SendChannel) == discord.channel.DMChannel:
                    Good_To_Send = True

                if not Good_To_Send:
                    if await CheckPermissions(SendChannel, "send_messages"):
                        Good_To_Send = True

                if Good_To_Send:
                    # If the channel exists and the bot can send messages in it:
                    SentMsg = await SendChannel.send(RemindPersonMention + Add + ", " + ContentMessage, embed=em)

                    await asyncio.sleep(.2)
                    await SentMsg.edit(content=RemindPersonMention + Add, embed=em)

            # And let's try to remove that clock from the original message
            if "OriginalMessageID" not in Reminder.keys():
                return

            if not Reminder["OriginalMessageID"]:
                return

            originalmsg = await SendChannel.get_message(int(Reminder["OriginalMessageID"]))

            if not originalmsg:
                return
            if not SentMsg:
                return

            try:  # TODO This is a Temporary Solution to the DM Problem
                await originalmsg.clear_reactions()
                await originalmsg.add_reaction(Conversation.Emoji["check"])

            except:
                pass

            thread = Vars.Bot.loop.create_task(Remind.SentReminderActions(Reminder, originalmsg, SendChannel, SentMsg, RemindPerson))

        # Now that it's been sent, it must be deleted
        await Remind.DeleteReminder(str(RemindList[0]["RemindStamp"]))

        return

    @staticmethod
    async def SentReminderActions(Reminder, originalmsg, SendChannel, SentMsg, RemindPerson):

        if Reminder["Repeat"] > 2:
            return


        # Now we do the emojis
        emoji_five   = '5\u20e3'
        emoji_ten    = '\U0001f51f'
        emoji_mystery = '\U00002601'
        emoji_list = [emoji_five, emoji_ten, emoji_mystery]

        for emoji in emoji_list:
            await SentMsg.add_reaction(emoji)


        async def RemoveReaction(reaction, user):
            if not await Helpers.Deleted(reaction.message):
                await reaction.message.remove_reaction(reaction.emoji, user)

        def Check(reaction, user):
            if user.bot:
                return
            if user.id == int(Reminder["RemindPerson"]):
                if reaction.message.id == SentMsg.id:
                    if reaction.emoji in emoji_list:
                        return reaction, user

            Vars.Bot.loop.create_task(RemoveReaction(reaction, user))

        Stop = False
        while not Stop:
            try:
                reaction, user = await Vars.Bot.wait_for("reaction_add", check=Check, timeout=60)
                break

            except asyncio.TimeoutError:
                if not await Helpers.Deleted(SentMsg):
                    await SentMsg.clear_reactions()
                return

        if reaction.emoji == emoji_five:
            NewTime = datetime.now() + timedelta(minutes=5)
        elif reaction.emoji == emoji_ten:
            NewTime = datetime.now() + timedelta(minutes=10)
        elif reaction.emoji == emoji_mystery:
            # This one will randomly pick a time close to, or far away, but always on the 5 or 10.
            # First let's see the time difference between the remindstamp and the initial message
            await SendChannel.trigger_typing()

            AskedTime = originalmsg.created_at - timedelta(hours=4)
            AskedTime = await Remind.DateStamp(AskedTime)
            RemindedTime = Reminder["RemindStamp"]
            Difference = RemindedTime - AskedTime

            # Okay so now we have a datapoint for how long was in between being reminded. The first thing
            # we want to do its jump to the next round number (5 or 10) of minutes

            Minutes_Now = datetime.now().minute # Now lets get that sweet sweet last digit
            if Minutes_Now < 10:
                Minutes_Now_LD = Minutes_Now
            else:
                Minutes_Now_LD = int(str(Minutes_Now)[1])

            Minutes_Add = 10 - Minutes_Now_LD

            # So this Minutes_Add will tell us how much to add to get to the next minute ending in 10. Now let's
            # analyze the difference.

            AddRemindMinutes = 0


            if Difference <= 300: # Less than 5 minutes
                if Minutes_Add > 5:
                    if random.choice([0, 1]): # 50% chance it'll do:
                        AddRemindMinutes = Minutes_Add - 5  # 5 less
                    else:
                        AddRemindMinutes = Minutes_Add # All (still < 10)
                else:  # If the add is less than 5, but the Difference is still 5
                    if random.choice([0, 1]): # 50% chance it'll do:
                        AddRemindMinutes = Minutes_Add + 5  # 5 more
                    else:
                        AddRemindMinutes = Minutes_Add # All (still < 5)

            elif Difference <= 1200: # Twenty Minutes
                if Minutes_Add > 5:
                    Minutes_Add -= 5

                RandAdd = random.choice([5, 10, 15, 20])
                AddRemindMinutes = Minutes_Add + RandAdd

            else:  # Longer than 20 minutes
                if Minutes_Add > 5:
                    Minutes_Add -= 5
                RandAdd = random.choice([30, 45, 60])
                AddRemindMinutes = Minutes_Add + RandAdd

            # Okay so now we have AddRemindMinutes
            # We want to bring it down a certain amount for every time they've been reminded before. Based on the scale of the number
            if AddRemindMinutes <= 5:
                CutDown = 0  # Remember that each CutDown could be done up to 3 times
            elif AddRemindMinutes <= 15 and Reminder["Repeat"] >= 1:
                CutDown = 5
            elif AddRemindMinutes <= 25:
                CutDown = Reminder["Repeat"] * 5
            else:
                CutDown = Reminder["Repeat"] * random.choice([5, 10])

            if AddRemindMinutes - CutDown > 0:
                AddRemindMinutes -= CutDown

            NewTime = datetime.now() + timedelta(minutes=AddRemindMinutes)


        await Remind.ReSaveReminder(Reminder, NewTime)

        toSendDateString = NewTime.strftime("%A, %B %d, %Y at %I:%M %p")

        if reaction.emoji == emoji_mystery:
            toSendDateString = "Mystery Remind Time"
            footer = "I decided on a new time to remind you based on how long you originally specified."
        else:
            footer = ""

        string = "```md\n# " + toSendDateString + "\nI say: > @" + RemindPerson.name + ", " + Reminder["Message"] + "```"

        em = discord.Embed(color=Remind.embed_color, description=string)
        em.set_author(name="Okay, I'll Remind You Again", icon_url=Vars.Bot.user.avatar_url)

        if Reminder["Image"]:
            em.set_image(url=Reminder["Image"])

        if footer:
            em.set_footer(text=footer)



        sent = await SendChannel.send(embed=em)
        await SentMsg.clear_reactions()




    @staticmethod
    async def CheckForOldReminders():
        # Runs on update, reboot, looking for any older reminders it may have missed

        Now = await Remind.DateStamp(datetime.now())

        RemindData = Helpers.RetrieveData(type="Remind")

        if not RemindData:
            return

        for Reminder in RemindData:
            if int(Reminder) < Now:
                # If the reminder has already passed:
                    delta = Now - int(Reminder)
                    delta = round(delta/60)
                    await Remind.SendReminder(RemindData[str(Reminder)], Now, Add=", Sorry, I am " + str(delta) + " minutes late due to an outage")


class Todo:
    @staticmethod
    async def OnMessage(message):
        await Todo.Command(message)

    @staticmethod
    async def RetrieveData():
        "Called Internally to get all of the Todo Data"
        Data = Helpers.RetrieveData(type="Todo")
        if not Data:
            return {}

        else:
            return Data

    @staticmethod
    async def Command(message):
        if not await CheckMessage(message, prefix=True, start="todo"):
            return

        usableContent = message.content[5:].strip()

        TodoData = Todo.RetrieveData()


class Help:
    # Displays Help for a given command type
    @staticmethod
    async def OnMessage(message):
        await Help.HelpCommandGeneral(message)
        return

    @staticmethod
    async def HelpCommandGeneral(message):
        # Runs per command, just to see if its either like: /yesno help or /help yesno
        usableContent = message.content
        if not await CheckMessage(message, prefix=True, include="help", markMessage=False):
            return
        if not message.content[1:5].lower() == "help" and not " help" in message.content.lower():
            return

        usableContent = usableContent[1:]

        seperatedWords = usableContent.split(" ")

        HasHelp = 0

        for word in seperatedWords:
            if word.lower().strip() == "help":
                HasHelp = word

        if not HasHelp:
            return

        usableContent = usableContent.replace(HasHelp, "").strip().lower()

        if not usableContent.strip():
            await Help.HelpGUI(message)
            return

        HelpText = Conversation.Help

        if usableContent.lower().endswith("s"):
            usableContent = usableContent[0:len(usableContent)-1]
        if usableContent.lower().endswith("ed"):
            usableContent = usableContent[0:len(usableContent)-2]


        if usableContent not in HelpText.keys():
            em = discord.Embed(description="I can't find `"+ usableContent + "` in my data. You can just do /help to "
                                                                             "see all help messages", color=Vars.Bot_Color)
            await message.add_reaction(Conversation.Emoji["x"])

        else:
            em = discord.Embed(description=HelpText[usableContent], color=Vars.Bot_Color, title=Sys.FirstCap(usableContent) + " Help")
            em.set_thumbnail(url=Vars.Bot.user.avatar_url)
            em.set_footer(text=message.content)

        await message.channel.send(embed=em)
        await SeenMessages.LogFound(message.id)

        #await message.channel.send(usableContent)

    @staticmethod
    async def InternalHelp(channel, type=None):
        if not type:
            type = "Help"

        AllHelpTexts = Conversation.Help
        if type not in AllHelpTexts.keys():
            raise KeyError("Help type isn't in prepared listings!")
            return

        HelpText = AllHelpTexts[type]
        em = discord.Embed(description=HelpText, color=Vars.Bot_Color, title=Sys.FirstCap(type) + " Help")
        em.set_thumbnail(url=Vars.Bot.user.avatar_url)

        await channel.send(embed=em)
        return


    @staticmethod
    async def HelpGUI(message):
        # Summoned by help command, shows each help section with clickable arrows
        HelpText = Conversation.Help

        HelpString = ""
        for key in HelpText:
            HelpString += "\n*- " + Sys.FirstCap(key) + "*"

        em = discord.Embed(description="There are many different extentions to this command: " + HelpString,
                           title="Help Command", color=Vars.Bot_Color)
        em.set_thumbnail(url=Vars.Bot.user.avatar_url)
        em.set_footer(text=message.content)

        await message.channel.send(embed=em)


class On_React:
    @staticmethod
    async def On_X(reaction, user):
        if user.id in Ranks.Bots:
            return

        if await Helpers.Deleted(reaction.message):
            return

        message = reaction.message
        try:
            total_users = await reaction.users().flatten()

        except discord.NotFound:
            return
        if Vars.Bot.user in total_users:  # If bot originally reacted X
            if message.author.id != Vars.Bot.user.id:
                # If the message isn't by the bot:
                try:
                    await message.delete()
                    return
                except Exception:
                    pass
            return

        # If bot didn't originally react:f
        elif user.id in Ranks.Admins:
            try:
                await Log.LogDelete(message, "Requested Delete by " + user.name)
                await message.delete()
            except Exception:
                pass
            return


async def test(message):
    if not await CheckMessage(message, prefix=True, start="test", admin=True):
        return

    await asyncio.sleep(10)
    0/0

    await message.add_reaction(Conversation.Emoji["check"])
    return
