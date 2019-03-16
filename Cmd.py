import Sys, Conversation
import asyncio, random, time, discord, json, praw
from datetime import datetime, timedelta
import forecastio, os, sys, git, wolframalpha, traceback, urllib.request, pyimgur
from geopy.geocoders import Nominatim

from functools import wraps

# Reddit
reddit = praw.Reddit('bot1')

# Forecast
forecast_api_key = Sys.Read_Personal(data_type='Forecast_Key')

# Wolfram Alpha
wolfram_client = wolframalpha.Client(Sys.Read_Personal(data_type='Wolfram_Alpha_Key'))


class ContextMessage:
    "Okay so this class is made whenever a message is sent"

    __slots__ = ['HasPrefix', 'IsAdmin', 'InDM', 'IsCreator', 'OriginalContent', "Message", 'StrippedContent', "Deleted", 'Channel']

    def __init__(self, message):
        self.Message = message
        self.OriginalContent = message.content
        self.StrippedContent = message.content.strip().lower()

        self.HasPrefix = False
        self.IsAdmin = False
        self.InDM = False
        self.IsCreator = False

        self.Deleted = False

        if message.content:
            if message.content.strip()[0] in Vars.Command_Prefixes:
                self.HasPrefix = True
                self.StrippedContent = self.StrippedContent[1:]

        if message.author.id in Ranks.Admins:
            self.IsAdmin = True

        if type(message.channel) == discord.channel.DMChannel:
            self.InDM = True

        if message.author.id == Ranks.CreatorID:
            self.IsCreator = True

        self.Channel = message.channel

        return

    def To_Dict(self):
        # returns Dictionary containing the important stuff
        temp = {
            "Message_ID": self.Message.id,
            "Channel_ID": self.Message.channel.id,
            "Author_ID": self.Message.author.id,

            "OriginalContent": self.OriginalContent,
            "Content": self.Message.content,

            "HasPrefix": self.HasPrefix,
            "InDM": self.InDM,
            "IsAdmin": self.IsAdmin,
            "IsCreator": self.IsCreator
        }

        if self.InDM:
            temp["Guild_ID"] = None
        else:
            temp["Guild_ID"] = self.Message.guild.id

        return temp

    async def Refresh(self):
        # Refreshes the self.Message to ensure it's up to date
        id = self.Message.id
        channel = self.Message.channel
        try:
            newmsg = await channel.get_message(id)
            self.Message = newmsg
            return self.Message

        except discord.NotFound:
            self.Deleted = True

    async def IsDeleted(self):
        if self.Deleted:
            return True

        id = self.Message.id
        try:
            channel = self.Message.channel
            newmsg = await channel.get_message(id)
        except discord.NotFound:
            self.Deleted = True
            return True

        return False

    async def add_reaction(self, reactions, just_names=False):
        if type(reactions) == str:
            reactions = [reactions]

        if await self.IsDeleted():
            return None

        if just_names:
            reactions = [Conversation.Emoji[reaction] for reaction in reactions]

        for reaction in reactions:
            await self.Message.add_reaction(reaction)

        return True


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

    CreatorID = 239791371110580225


class Vars:  # Just a default class to hold a lot of the information that'll be accessed system-wide
    Version = "5.20"
    Command_Prefixes = ["/", "!", "?", "."]

    AdminCode = random.randint(0, 4000)
    Bot = None
    Disabled = False
    Disabler = None
    start_time = None
    Safety_Mode = False

    Safety_Mode_Info = {"Error_Message": ""}

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
            raise KeyError("Permission not accepted")

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


def Command(Admin=False, Start=None, Prefix=True, Include=None, NotInclude=None, ChannelID=None, GuildID=None, AuthorID=None,
            MarkMessage=True, CalledInternally=False, Attachment=None, NoSpace=False):
    def Command_Decorator(func):
        async def Function_Wrapper(Context):
            """
            Called before a function as so:
            @Command(info)
            async def Function(Context)

            :param Admin: Bool          Should this be an admin-only command?
            :param Start: str/list      Should the message start with something?
            :param Prefix: bool/str/list    Should the message have a command prefix? If so, what kind?
            :param Include: str         Is there something the message should have in it? .lower()
            :param NotInclude: str      Is there something the message should NOT have in it? .lower()
            :param ChannelID: int / list    Is it channel specific?
            :param GuildID: int / list      Is it guild specific?
            :param AuthorID: int / list     Is it author specific?
            :param MarkMessage: bool     Should the system mark the message as used for the command if successful?
            :param CalledInternally: bool   Should the system notice if it's marked or not
            :param Attachment: bool / none  Bool if it matters if there's an attachment, if not, None
            :return: 
            """
            if not CalledInternally:  # Return if already called
                if await SeenMessages.CheckSeen(Context.Message.id):
                    return False

            if Admin:  # Desired: Admin
                if not Context.IsAdmin:
                    return

            if Start:  # If there's a certain way the message should start
                if type(Start) == list:  # Multiple Possibilities
                    # First let's add the spaces
                    if not NoSpace:
                        NewStart = []
                        for item in Start:
                            NewStart.append(item.lower() + " ")
                    else:
                        NewStart = []
                        for item in Start:
                            NewStart.append(item.lower())

                    Found = False
                    for PotentialStart in NewStart:  # Iterate through them, seeing if any apply
                        if Context.StrippedContent.startswith(PotentialStart):
                            Found = True  # If so, break and set Found to True so it doesn't return
                            break

                    if not Found:  # Return if no Potential Start is Found
                        return

                elif type(Start) == str:  # If there's only one possiblity for how it should start
                    if not NoSpace:
                        NewStart = Start.lower() + " "
                    else:
                        NewStart = Start.lower()
                    if not Context.StrippedContent.startswith(NewStart):  # If it doesn't start that way, return.
                        return

            if Prefix:  # Desired: Command Prefix "  /  ?  .  "
                if type(Prefix) == bool:  # If they just want the standard prefix
                    if not Context.HasPrefix:
                        return

                elif type(Prefix) == str:  # If there's a specific prefix they're looking for:
                    if not Context.Message.content.strip().startswith(Prefix):
                        return

                elif type(Prefix) == list:  # If there's a whole group of possible prefixes to use
                    Found = False
                    # Iterate through each item in the list until we find the prefix desired
                    for PotentialPrefix in Prefix:
                        if Context.Message.content.strip().lower().startswith(Prefix.lower()):
                            Found = True
                            break
                    if not Found:
                        return

            elif not Prefix:  # Or if the command doesn't want a prefix
                if Context.HasPrefix:  # And it has one:
                    return

            if Include:  # Desired: This str in the message
                if Include.lower() not in Context.StrippedContent:
                    return

            if NotInclude:  # Desired: This str not in the message
               if NotInclude.lower() in Context.StrippedContent:
                   return

            if ChannelID:
                if type(ChannelID) == str:  # If it's a string, make it an integer
                    ChannelID_List = [int(ChannelID)]
                elif type(ChannelID) == int:  # If it's not in a list, make it into a list
                    ChannelID_List = [ChannelID]
                elif type(ChannelID) == list:
                    ChannelID_List = ChannelID

                if Context.Message.channel.id not in ChannelID_List:  # If the ID is not in the list:
                    return

            if GuildID:
                if type(GuildID) == str:  # If it's a string, make it an integer, then a list
                    GuildID_List = [int(GuildID)]
                elif type(GuildID) == int:  # If it's not in a list, make it into a list
                    GuildID_List = [GuildID]
                elif type(GuildID) == list:
                    GuildID_List = GuildID

                if Context.Message.guild.id not in GuildID_List:  # If the ID is not in the list:
                    return

            if AuthorID:
                if type(AuthorID) == str:  # If it's a string, make it an integer
                    AuthorID_List = [int(AuthorID)]
                elif type(AuthorID) == int:  # If it's not in a list, make it into a list
                    AuthorID_List = [AuthorID]
                elif type(AuthorID) == list:
                    AuthorID_List = AuthorID

                if Context.Message.author.id not in AuthorID_List:  # If the ID is not in the list:
                    return

            if type(Attachment) == bool:
                if Attachment:
                    if not Context.Message.attachments:
                        return False
                elif not Attachment:
                    if Context.Message.attachments:
                        return False

            # If we've reached this point, all criteria MUST be met, so we can finally run the function.
            if MarkMessage:
                await SeenMessages.LogFound(Context.Message.id)

            # ========================
            await func(Context)
            # ========================

        return Function_Wrapper
    return Command_Decorator


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
    for possiblePrefix in Vars.Command_Prefixes:  # For each possible prefix:
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
    async def Confirmation(SendChannel, Responders, text:str, yes_text=None, deny_text="Action Cancelled.", timeout=60,
                           return_timeout=False, deleted_original_message=False, mention=None, extra_text=None,
                           add_reaction=True, image=None, color=Vars.Bot_Color, footer_text=None, originalctx=None, Embed=None,
                           Outside_Text=None, Delete_After=True):
        """
        Sends a confirmation for a command
        :param SendChannel: The channel object to send the message lmao
        :param Responders: a List or user to send the message to
        :param text: What the message of the embed should say
        :param yes_text: If you want a confirmed message to play for 4 seconds
        :param deny_text: If you want a message to play when x is hit. 
        :param timeout: How long to wait for a conclusion
        :param mention: If the bot should mention the player in the beginning
        :return: Returns True if Yes, False if No, and None if timed out. 
        """

        Responders_ID = []
        if not type(Responders) == list:
            Responders = [Responders]

        for Responder in Responders:
            Responders_ID.append(Responder.id)


        # Establish two emojis
        CancelEmoji = Conversation.Emoji['x']
        ContinueEmoji = Conversation.Emoji['check']

        if mention:
            before_message = mention.mention
            if Outside_Text:
                before_message += ", " + Outside_Text
        else:
            before_message = Outside_Text

        if not Embed:
            em = discord.Embed(title=text, description=extra_text, timestamp=Helpers.EmbedTime(), colour=color)

            em.set_author(name="Confirmation:", icon_url=Vars.Bot.user.avatar_url)
            if footer_text:
                em.set_footer(text=footer_text)
            if image:
                em.set_image(url=image)
        else:
            em = Embed

        # Send message and add emojis

        QuestionMsg = await SendChannel.send(before_message, embed=em)

        await QuestionMsg.add_reaction(ContinueEmoji)
        await QuestionMsg.add_reaction(CancelEmoji)

        ReactionInfo = await Helpers.WaitForReaction(reaction_emoji=[ContinueEmoji, CancelEmoji], message=QuestionMsg,
                                                     users_id=Responders_ID, timeout=timeout, remove_wrong=True)

        if not ReactionInfo:
            if Delete_After:
                await QuestionMsg.delete()
            await SendChannel.send(deny_text, delete_after=5)

            if return_timeout:
                return "Timed Out"
            else:
                return False

        reaction = ReactionInfo["Reaction"]
        user = ReactionInfo["User"]

        # If they hit the X
        if reaction.emoji == CancelEmoji:
            if Delete_After:
                await QuestionMsg.delete()
            await SendChannel.send(deny_text, delete_after=5)
            return False

        # If they hit the check
        elif reaction.emoji == ContinueEmoji:
            if Delete_After:
                await QuestionMsg.delete()
            if not deleted_original_message:
                if add_reaction and originalctx:
                    if not await originalctx.IsDeleted():
                        await originalctx.Message.add_reaction(ContinueEmoji)
            if yes_text:
                await SendChannel.send(yes_text, delete_after=5)
            return True

    @staticmethod
    async def UserChoice(SendChannel, Responders, Question: str, Choices, timeout:int = 60, description=None, title=None,
                         Color=Vars.Bot_Color, Show_Avatar=False, Show_Cancel=False):
        """
        Ran just like Interraction.Confirmation(), in which the bot prompts the user to answer with an option. Multiple choices not supported yet. 
        :param Context: The Context object of the message
        :param Question:  String, what to ask
        :param Choices: Either a list of choices, or a list of dicts of 'Option', 'Emoji'
        :param timeout: int, how long to wait before returning None
        :return The string of the option chosen 
        """

        Responders_ID = []
        if not type(Responders) == list:
            Responders = [Responders]

        for Responder in Responders:
            Responders_ID.append(Responder.id)

        if type(Choices) != list or not Choices:
            raise TypeError("Choices can be a list of dictionaries, or just a list of strings. Nothing else")
        if len(Choices) > 10:
            MultiplePages = True
        else:
            MultiplePages = False


        # This is a list of the letters A-J
        LetterEmoji = ['\U0001F1E6', '\U0001F1E7', '\U0001F1E8', '\U0001F1E9', '\U0001F1EA', '\U0001F1EB',
                       '\U0001F1EC', '\U0001F1ED', '\U0001F1EE', '\U0001F1EF']

        # Iterates through all choices, creating a dict for each if not already there
        NewChoices = []
        i = 0
        for item in Choices:
            if type(item) == str:
                NewChoices.append({'Option': item, 'Emoji': LetterEmoji[i]})
            elif type(item) == dict:
                NewChoices.append(item)
            else:
                raise TypeError("Choices should be a list of strings or a list of dicts containing 'Option' and 'Emoji'")
            i += 1
            if i >= 10:  # Ensures each page of emoji get their own A B C etc
                i = 0

        if Show_Avatar:
            Avatar = Vars.Bot.user.avatar_url
        else:
            Avatar = ""

        if not MultiplePages:
            if Show_Cancel:  # If the user wants to show the cancel option:
                NewChoices.append({"Option": "Cancel", "Emoji": Conversation.Emoji["x"]})


            ChoiceStringList = []
            for choice in NewChoices:
                tempStr = choice["Emoji"] + "  " + Sys.FirstCap(choice["Option"])
                ChoiceStringList.append(tempStr)

            EmbedContent = "\n".join(ChoiceStringList)

            if description:
                EmbedContent = description + "\n" + EmbedContent

            em = discord.Embed(description=EmbedContent, title=title, color=Color, timestamp=Helpers.EmbedTime())
            em.set_author(icon_url=Avatar, name=Question)
            em.set_footer(text="Times out after " + str(timeout) + " seconds")

            # Send the first section.
            sent = await SendChannel.send(embed=em)

            EmojiList = []
            for item in NewChoices:
                await sent.add_reaction(item["Emoji"])
                EmojiList.append(item["Emoji"])
            
            Answer = await Helpers.WaitForReaction(reaction_emoji=EmojiList, message=sent, users_id=Responders_ID, timeout=timeout, remove_wrong=True)

            # So this'll either be None, or a Reaction Dict thing:
            # {"Reaction": reaction, "User": user}

            await Helpers.QuietDelete(sent)

            if not Answer:
                return None

            AnswerReaction = Answer["Reaction"]
            for item in NewChoices:
               if AnswerReaction.emoji == item["Emoji"]:
                    return item['Option']

        elif MultiplePages:
            # Create lists that have certain purposes for each page
            PageDict = {}  # will house all information about the page:
            """
            PageDict = {
                0: {
                "Content": str,
                "EmojiList": [str],
                "Embed": discord.Embed(),
                "Options": 
                }}
            """
            CurrentPage = 0
            MaxPage = None

            SeparatedNewChoices = []  # Houses a list of lists, for each possible choice
            i = 0
            tempChoices = []
            # Separate each group of 10 choices into a list, for SeparatedNewChoices
            for Choice in NewChoices:
                tempChoices.append(Choice)
                i += 1
                if i >= 10:
                    SeparatedNewChoices.append(tempChoices)
                    i = 0
                    tempChoices = []

            if tempChoices not in SeparatedNewChoices:
                SeparatedNewChoices.append(tempChoices)

            if Show_Cancel:
                for ChoiceList in SeparatedNewChoices:
                    ChoiceList.append({"Option": "Cancel", "Emoji": Conversation.Emoji["x"]})

            MaxPage = len(SeparatedNewChoices) - 1

            # Now we have a list of each list. This'll make it easy to separate things out.
            i = 0
            for Grouping in SeparatedNewChoices:
                # For each group of 10
                EmojiList = []
                EmbedContentList = []
                for Choice in Grouping:  # For each option inside of each page
                    EmojiList.append(Choice["Emoji"])  # Add the emoji to the grouping's listing
                    tempStr = Choice["Emoji"] + "  " + Sys.FirstCap(Choice["Option"])
                    EmbedContentList.append(tempStr)

                # Now, move EmbedContentList into EmbedContent
                EmbedContent = "\n".join(EmbedContentList)
                if description:
                    EmbedContent = description + "\n" + EmbedContent

                em = discord.Embed(description=EmbedContent, title=title, color=Color, timestamp=Helpers.EmbedTime())
                em.set_author(icon_url=Avatar, name=Question)
                em.set_footer(text="Page " + str(i + 1) + "/" + str(MaxPage + 1) + " | Times out after " + str(timeout) + " seconds")

                tempDict = {"EmojiList": EmojiList,
                            "Content": EmbedContent,
                            "Embed": em,
                            "Options": Grouping}
                PageDict[i] = tempDict
                i += 1

            # Now we have PageDict, which has all the information we'd ever need.
            MaxPage = len(SeparatedNewChoices) - 1

            # Okay, let's send the message:
            Prompt = await SendChannel.send(embed=PageDict[CurrentPage]["Embed"])

            GoLeft =  Conversation.Emoji["TriangleLeft"]
            GoRight = Conversation.Emoji["TriangleRight"]

            await Prompt.add_reaction(GoLeft)
            await Prompt.add_reaction(GoRight)

            ChosenEmoji = None
            Stop = False
            while not Stop:
                # Add Reactions
                for reaction in PageDict[CurrentPage]["EmojiList"]:
                    await Prompt.add_reaction(reaction)

                AllPossibleEmoji = PageDict

                # Wait for reactions
                response = await Helpers.WaitForReaction(reaction_emoji = PageDict[CurrentPage]["EmojiList"]+ [GoLeft, GoRight],
                                                         message=Prompt, users_id=Responders_ID, timeout=timeout, remove_wrong=True)
                if not response:
                    await Helpers.QuietDelete(Prompt)
                    return None

                if response["Reaction"].emoji in [GoLeft, GoRight]:
                    if IsDMChannel(SendChannel):
                        for reaction in PageDict[CurrentPage]["EmojiList"]:
                            # print(reaction)
                            await Prompt.remove_reaction(reaction, Vars.Bot.user)
                    else:
                        await Helpers.RemoveAllReactions(Prompt)
                        await Prompt.add_reaction(GoLeft)
                        await Prompt.add_reaction(GoRight)

                    if response["Reaction"].emoji == GoLeft:
                        CurrentPage -= 1
                        if CurrentPage < 0:
                            CurrentPage = MaxPage
                    elif response["Reaction"].emoji == GoRight:
                        CurrentPage += 1
                        if CurrentPage > MaxPage:
                            CurrentPage = 0

                    await Prompt.edit(embed=PageDict[CurrentPage]["Embed"])
                else:
                    ChosenEmoji = response["Reaction"].emoji
                    Stop = True

            # Exiting, we have "response" now
            for Option in PageDict[CurrentPage]["Options"]:
                if Option["Emoji"] == ChosenEmoji:
                    await Helpers.QuietDelete(Prompt)
                    return Option["Option"]

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
    async def NewAskQuestion(SendChannel, Question, Timeout=20, SpecSender=None, Description=None, AfterDelete=False):
        if SpecSender:
            if type(SpecSender) != list:
                SpecSender = [SpecSender]

        Em = discord.Embed(description=Description, color=Vars.Bot_Color)
        Em.set_author(name=Question, icon_url=Vars.Bot.user.avatar_url)
        Em.set_footer(text=str(Timeout) + " second Timeout | I am listening for a response.")

        QuestionMsg = await SendChannel.send(embed=Em)
        await QuestionMsg.add_reaction(Conversation.Emoji['circle'])
        QuestionMsgCtx = ContextMessage(QuestionMsg)

        def check(m):
            if m.channel.id != SendChannel.id:
                return False

            if SpecSender:
                if m.author.id not in SpecSender:  # List of ID's
                    return False

            return True

        try:
            Response = await Vars.Bot.wait_for('message', check=check, timeout=Timeout)

            if not await QuestionMsgCtx.IsDeleted():
                await QuestionMsg.clear_reactions()
                if AfterDelete:
                    await QuestionMsg.delete()
                else:
                    Em.color = discord.Embed.Empty
                    Em.set_footer(text="Satisfied: Received Response, No Longer Listening.")

                    await QuestionMsg.edit(embed=Em)
            return Response

        except asyncio.TimeoutError:
            if not await QuestionMsgCtx.IsDeleted():
                await QuestionMsg.clear_reactions()
                if AfterDelete:
                    await QuestionMsg.delete()
                else:
                    Em.color = discord.Embed.Empty
                    Em.set_footer(text="Timed Out, No Longer Listening to messages.")

                    await QuestionMsg.edit(embed=Em)
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
    async def Deleted(message: discord.Message):
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
        except:
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
            return datetime.now() + timedelta(hours=5)
        else:
            return datetime.now()

    @staticmethod
    async def WaitForReaction(reaction_emoji = None, message: discord.Message = None, users_id=[], timeout: int = 60,
                              emoji_num: int = 1, remove_wrong: bool = False):
        """
        Will wait for a reaction that fits the criteria
        :param reaction_emoji: 
        :param message: 
        :param users_id: 
        :param timeout: 
        :return: None, if timeout, dict if success
        """
        if type(reaction_emoji) != list:
            reaction_emoji = [reaction_emoji]

        if type(users_id) != list:
            users_id = [users_id]

        FinalInfo = None

        async def RemoveReaction(reaction, user):
            if not IsDMChannel(reaction.message.channel):
                if not await Helpers.Deleted(reaction.message):
                    await reaction.message.remove_reaction(reaction.emoji, user)


        def check(init_reaction, init_user):  #  A mini function ran per reaction add
            # First, let's ensure it's not a bot
            if init_user.bot:
                return False

            if message:  # If the message is the same
                if init_reaction.message.id != message.id:
                    return False

            if reaction_emoji:  # If the reaction emoji is not in the emoji list
                if init_reaction.emoji not in reaction_emoji:
                    if remove_wrong:
                        Vars.Bot.loop.create_task(RemoveReaction(init_reaction, init_user))
                    return False

            if users_id:  # If the user is correct
                if int(init_user.id) not in users_id:
                    if remove_wrong:
                        Vars.Bot.loop.create_task(RemoveReaction(init_reaction, init_user))
                    return False

            if emoji_num > 1:  # If there's a certain number of emoji to hit
                if init_reaction.count < emoji_num:
                    return False

            return True


        Found = False
        while not Found:
            try:
                # Wait for the reaction(s)
                reaction, user = await Vars.Bot.wait_for('reaction_add', timeout=timeout, check=check)
                return {"Reaction": reaction, "User": user}

            except asyncio.TimeoutError:
                return None

    @staticmethod
    async def RemoveBotReactions(message):
        if await Helpers.Deleted(message):
            return True

        message = await Helpers.ReGet(message)

        if not IsDMChannel(message.channel):
            await message.clear_reactions()

        for reaction in message.reactions:
            async for user in reaction.users():

                if user.id == Vars.Bot.user.id:
                    await message.remove_reaction(reaction.emoji, user)

    @staticmethod
    async def RemoveAllReactions(message):
        if IsDMChannel(message.channel):
            await Helpers.RemoveBotReactions(message)
            return

        if await Helpers.Deleted(message):
            return True

        # TODO Add functionality if it doesn't have all perms, becubceause that could be very bad for it
        await message.clear_reactions()

    @staticmethod
    async def TextToLatAndLong(text):
        geolocator = Nominatim(user_agent="bing")

        content = text

        switchlist = [["brandeis", "brandeis university"]]
        for item in switchlist:
            if content.strip().lower() == item[0]:
                content = item[1]

        location = geolocator.geocode(content)
        if not location:
            return None

        # print(location.raw)
        return [float(location.raw["lat"]), float(location.raw["lon"]), location.raw["display_name"], location.raw["icon"]]

    @staticmethod
    async def ShortenTextInLink(text):
        """
        Takes in text and shortens all of the links within
        :param text: String with some links
        :return:     String with the links shortened using TinyUrl
        """
        LinkList = []
        EditedText = text

        # Iterate through each word in the text and replace the links in EditedText
        for Word in text.split(" "):
            if not Word.lower().startswith("http"):
                # If the Word doesn't start with http, keep moving
                continue

            # If we're here, it means that the word is a link
            Shortened_Link = Sys.Shorten_Link(Word)

            # Let's now add the little part of the word in parethesis
            MainDomain = Word.replace("//", "/").split("/")[1]
            MainDomain = MainDomain.replace("www.", "")
            MainDomain = "*(" + Sys.FirstCap(MainDomain) + ")*"

            Shortened_Word = Shortened_Link + " " + MainDomain

            # Compare to see if its shorter than the original
            if len(Word) > len(Shortened_Word) + 8:  # If the shortened_link is 8 less or more than the original, replace it
                EditedText = EditedText.replace(Word, Shortened_Word)

        return EditedText
    
    
    
class Interraction:
    @staticmethod
    async def Confirmation(SendChannel, Responders, text: str, yes_text=None, deny_text="Action Cancelled.", timeout=60,
                           return_timeout=False, deleted_original_message=False, mention=None, extra_text=None,
                           add_reaction=True, image=None, color=Vars.Bot_Color, footer_text=None, originalctx=None,
                           Embed=None,
                           Outside_Text=None, Delete_After=True):
        """
        Sends a confirmation for a command
        :param SendChannel: The channel object to send the message lmao
        :param Responders: a List or user to send the message to
        :param text: What the message of the embed should say
        :param yes_text: If you want a confirmed message to play for 4 seconds
        :param deny_text: If you want a message to play when x is hit. 
        :param timeout: How long to wait for a conclusion
        :param mention: If the bot should mention the player in the beginning
        :return: Returns True if Yes, False if No, and None if timed out. 
        """

        Responders_ID = []
        if not type(Responders) == list:
            Responders = [Responders]

        for Responder in Responders:
            Responders_ID.append(Responder.id)

        # Establish two emojis
        CancelEmoji = Conversation.Emoji['x']
        ContinueEmoji = Conversation.Emoji['check']

        if mention:
            before_message = mention.mention
            if Outside_Text:
                before_message += ", " + Outside_Text
        else:
            before_message = Outside_Text

        if not Embed:
            em = discord.Embed(title=text, description=extra_text, timestamp=Helpers.EmbedTime(), colour=color)

            em.set_author(name="Confirmation:", icon_url=Vars.Bot.user.avatar_url)
            if footer_text:
                em.set_footer(text=footer_text)
            if image:
                em.set_image(url=image)
        else:
            em = Embed

        # Send message and add emojis

        QuestionMsg = await SendChannel.send(before_message, embed=em)

        await QuestionMsg.add_reaction(ContinueEmoji)
        await QuestionMsg.add_reaction(CancelEmoji)

        ReactionInfo = await Helpers.WaitForReaction(reaction_emoji=[ContinueEmoji, CancelEmoji], message=QuestionMsg,
                                                     users_id=Responders_ID, timeout=timeout, remove_wrong=True)

        if not ReactionInfo:
            if Delete_After:
                await QuestionMsg.delete()
            await SendChannel.send(deny_text, delete_after=5)

            if return_timeout:
                return "Timed Out"
            else:
                return False

        reaction = ReactionInfo["Reaction"]
        user = ReactionInfo["User"]

        # If they hit the X
        if reaction.emoji == CancelEmoji:
            if Delete_After:
                await QuestionMsg.delete()
            await SendChannel.send(deny_text, delete_after=5)
            return False

        # If they hit the check
        elif reaction.emoji == ContinueEmoji:
            if Delete_After:
                await QuestionMsg.delete()
            if not deleted_original_message:
                if add_reaction and originalctx:
                    if not await originalctx.IsDeleted():
                        await originalctx.Message.add_reaction(ContinueEmoji)
            if yes_text:
                await SendChannel.send(yes_text, delete_after=5)
            return True

    @staticmethod
    async def UserChoice(SendChannel, Responders, Question: str, Choices, timeout: int = 60, description=None,
                         title=None,
                         Color=Vars.Bot_Color, Show_Avatar=False, Show_Cancel=False):
        """
        Ran just like Interraction.Confirmation(), in which the bot prompts the user to answer with an option. Multiple choices not supported yet. 
        :param Context: The Context object of the message
        :param Question:  String, what to ask
        :param Choices: Either a list of choices, or a list of dicts of 'Option', 'Emoji'
        :param timeout: int, how long to wait before returning None
        :return The string of the option chosen 
        """

        Responders_ID = []
        if not type(Responders) == list:
            Responders = [Responders]

        for Responder in Responders:
            Responders_ID.append(Responder.id)

        if type(Choices) != list or not Choices:
            raise TypeError("Choices can be a list of dictionaries, or just a list of strings. Nothing else")
        if len(Choices) > 10:
            MultiplePages = True
        else:
            MultiplePages = False

        # This is a list of the letters A-J
        LetterEmoji = ['\U0001F1E6', '\U0001F1E7', '\U0001F1E8', '\U0001F1E9', '\U0001F1EA', '\U0001F1EB',
                       '\U0001F1EC', '\U0001F1ED', '\U0001F1EE', '\U0001F1EF']

        # Iterates through all choices, creating a dict for each if not already there
        NewChoices = []
        i = 0
        for item in Choices:
            if type(item) == str:
                NewChoices.append({'Option': item, 'Emoji': LetterEmoji[i]})
            elif type(item) == dict:
                NewChoices.append(item)
            else:
                raise TypeError(
                    "Choices should be a list of strings or a list of dicts containing 'Option' and 'Emoji'")
            i += 1
            if i >= 10:  # Ensures each page of emoji get their own A B C etc
                i = 0

        if Show_Avatar:
            Avatar = Vars.Bot.user.avatar_url
        else:
            Avatar = ""

        if not MultiplePages:
            if Show_Cancel:  # If the user wants to show the cancel option:
                NewChoices.append({"Option": "Cancel", "Emoji": Conversation.Emoji["x"]})

            ChoiceStringList = []
            for choice in NewChoices:
                tempStr = choice["Emoji"] + "  " + Sys.FirstCap(choice["Option"])
                ChoiceStringList.append(tempStr)

            EmbedContent = "\n".join(ChoiceStringList)

            if description:
                EmbedContent = description + "\n" + EmbedContent

            em = discord.Embed(description=EmbedContent, title=title, color=Color, timestamp=Helpers.EmbedTime())
            em.set_author(icon_url=Avatar, name=Question)
            em.set_footer(text="Times out after " + str(timeout) + " seconds")

            # Send the first section.
            sent = await SendChannel.send(embed=em)

            EmojiList = []
            for item in NewChoices:
                await sent.add_reaction(item["Emoji"])
                EmojiList.append(item["Emoji"])

            Answer = await Helpers.WaitForReaction(reaction_emoji=EmojiList, message=sent, users_id=Responders_ID,
                                                   timeout=timeout, remove_wrong=True)

            # So this'll either be None, or a Reaction Dict thing:
            # {"Reaction": reaction, "User": user}

            await Helpers.QuietDelete(sent)

            if not Answer:
                return None

            AnswerReaction = Answer["Reaction"]
            for item in NewChoices:
                if AnswerReaction.emoji == item["Emoji"]:
                    return item['Option']

        elif MultiplePages:
            # Create lists that have certain purposes for each page
            PageDict = {}  # will house all information about the page:
            """
            PageDict = {
                0: {
                "Content": str,
                "EmojiList": [str],
                "Embed": discord.Embed(),
                "Options": 
                }}
            """
            CurrentPage = 0
            MaxPage = None

            SeparatedNewChoices = []  # Houses a list of lists, for each possible choice
            i = 0
            tempChoices = []
            # Separate each group of 10 choices into a list, for SeparatedNewChoices
            for Choice in NewChoices:
                tempChoices.append(Choice)
                i += 1
                if i >= 10:
                    SeparatedNewChoices.append(tempChoices)
                    i = 0
                    tempChoices = []

            if tempChoices not in SeparatedNewChoices:
                SeparatedNewChoices.append(tempChoices)

            if Show_Cancel:
                for ChoiceList in SeparatedNewChoices:
                    ChoiceList.append({"Option": "Cancel", "Emoji": Conversation.Emoji["x"]})

            MaxPage = len(SeparatedNewChoices) - 1

            # Now we have a list of each list. This'll make it easy to separate things out.
            i = 0
            for Grouping in SeparatedNewChoices:
                # For each group of 10
                EmojiList = []
                EmbedContentList = []
                for Choice in Grouping:  # For each option inside of each page
                    EmojiList.append(Choice["Emoji"])  # Add the emoji to the grouping's listing
                    tempStr = Choice["Emoji"] + "  " + Sys.FirstCap(Choice["Option"])
                    EmbedContentList.append(tempStr)

                # Now, move EmbedContentList into EmbedContent
                EmbedContent = "\n".join(EmbedContentList)
                if description:
                    EmbedContent = description + "\n" + EmbedContent

                em = discord.Embed(description=EmbedContent, title=title, color=Color, timestamp=Helpers.EmbedTime())
                em.set_author(icon_url=Avatar, name=Question)
                em.set_footer(text="Page " + str(i + 1) + "/" + str(MaxPage + 1) + " | Times out after " + str(
                    timeout) + " seconds")

                tempDict = {"EmojiList": EmojiList,
                            "Content": EmbedContent,
                            "Embed": em,
                            "Options": Grouping}
                PageDict[i] = tempDict
                i += 1

            # Now we have PageDict, which has all the information we'd ever need.
            MaxPage = len(SeparatedNewChoices) - 1

            # Okay, let's send the message:
            Prompt = await SendChannel.send(embed=PageDict[CurrentPage]["Embed"])

            GoLeft = Conversation.Emoji["TriangleLeft"]
            GoRight = Conversation.Emoji["TriangleRight"]

            await Prompt.add_reaction(GoLeft)
            await Prompt.add_reaction(GoRight)

            ChosenEmoji = None
            Stop = False
            while not Stop:
                # Add Reactions
                for reaction in PageDict[CurrentPage]["EmojiList"]:
                    await Prompt.add_reaction(reaction)

                AllPossibleEmoji = PageDict

                # Wait for reactions
                response = await Helpers.WaitForReaction(
                    reaction_emoji=PageDict[CurrentPage]["EmojiList"] + [GoLeft, GoRight],
                    message=Prompt, users_id=Responders_ID, timeout=timeout, remove_wrong=True)
                if not response:
                    await Helpers.QuietDelete(Prompt)
                    return None

                if response["Reaction"].emoji in [GoLeft, GoRight]:
                    if IsDMChannel(SendChannel):
                        for reaction in PageDict[CurrentPage]["EmojiList"]:
                            # print(reaction)
                            await Prompt.remove_reaction(reaction, Vars.Bot.user)
                    else:
                        await Helpers.RemoveAllReactions(Prompt)
                        await Prompt.add_reaction(GoLeft)
                        await Prompt.add_reaction(GoRight)

                    if response["Reaction"].emoji == GoLeft:
                        CurrentPage -= 1
                        if CurrentPage < 0:
                            CurrentPage = MaxPage
                    elif response["Reaction"].emoji == GoRight:
                        CurrentPage += 1
                        if CurrentPage > MaxPage:
                            CurrentPage = 0

                    await Prompt.edit(embed=PageDict[CurrentPage]["Embed"])
                else:
                    ChosenEmoji = response["Reaction"].emoji
                    Stop = True

            # Exiting, we have "response" now
            for Option in PageDict[CurrentPage]["Options"]:
                if Option["Emoji"] == ChosenEmoji:
                    await Helpers.QuietDelete(Prompt)
                    return Option["Option"]


    @staticmethod
    async def ListStrings(SendChannel, StringList, Title, TimeOut=60, Limited_Responders=None, Color=Vars.Bot_Color,
                          Footer_Text=None, Footer_Image=None, Extra_Text="", Max_Items=10, Author_Image=None):
        """
        Creates an interractive movable list of the StringList, each one after another, with functioning arrows
        :param SendChannel: The channel to send the ListString in
        :param StringList:  List of all the strings that you want to be in the list, organized
        :param Title:       The title of the embed
        :param TimeOut:     How long to wait before the Bot kills the list
        :param Limited_Responders:   Who can respond? If None, everyone
        :param Color:       Color of the embed before it is killed
        :param Footer_Text: Text in the footer
        :param Extra_Text:  Stuff to add before the list
        :return: None
        """

        if not Author_Image:
            Author_Image = Vars.Bot.user.avatar_url

        IsDM = IsDMChannel(SendChannel)

        # We want a dictionary Page_Dict that contains information for each page.
        Page_Dict = {}
        if Max_Items:
            temp = []
            for i in range(0, len(StringList)):
                if i % Max_Items == 0 and i != 0:
                    Page_Dict[len(Page_Dict)] = {"OriginalContents": temp}
                    temp = [StringList[i]]
                elif i == len(StringList) - 1:
                    temp.append(StringList[i])
                    Page_Dict[len(Page_Dict)] = {"OriginalContents": temp}
                else:
                    temp.append(StringList[i])
        elif not Max_Items:
            raise AttributeError("Interraction.ListStrings needs an attribute Max_Items to be set to an integer, not " + repr(Max_Items))

        for PageNum in Page_Dict:
            Page_Dict[PageNum]["FlattenedContent"] = Extra_Text + "\n".join(Page_Dict[PageNum]["OriginalContents"])

            Footer = "Page " + str(PageNum + 1) + "/" + str(len(Page_Dict))
            if Footer_Text:
                Footer += " | " + Footer_Text

            em = discord.Embed(description=Page_Dict[PageNum]["FlattenedContent"], color=Color, timestamp=Helpers.EmbedTime())
            em.set_author(name=Title, icon_url=Author_Image)

            if Footer_Image:
                em.set_footer(text=Footer, icon_url = Footer_Image)

            else:
                em.set_footer(text=Footer)

            Page_Dict[PageNum]["Embed"] = em


        CurrentPage = 0
        List_Object = await SendChannel.send(embed=Page_Dict[0]["Embed"])

        # Reactions:
        ButtonNext = Conversation.Emoji["TriangleRight"]
        ButtonBack = Conversation.Emoji["TriangleLeft"]
        ButtonSkip = Conversation.Emoji["SkipRight"]

        ButtonList = [ButtonBack, ButtonNext, ButtonSkip]

        # Add to message
        for button in ButtonList:
            await List_Object.add_reaction(button)

        Stop = False
        while not Stop:
            Reactions = await Helpers.WaitForReaction(reaction_emoji=ButtonList, message=List_Object, timeout=TimeOut,
                                                      remove_wrong=True)
            if Reactions == None:
                Stop = True
                continue

            elif Reactions:
                # Okay so at this point we have some reactions
                ReactionEmoji = Reactions["Reaction"].emoji
                if ReactionEmoji == ButtonNext:
                    CurrentPage = CurrentPage + 1 if CurrentPage + 1 < len(Page_Dict) else 0

                elif ReactionEmoji == ButtonBack:
                    CurrentPage = CurrentPage - 1 if CurrentPage - 1 >= 0 else len(Page_Dict) - 1

                elif ReactionEmoji == ButtonSkip:
                    CurrentPage = len(Page_Dict) - 1

                if not IsDM:
                    await List_Object.remove_reaction(ReactionEmoji, Reactions["User"])
                await List_Object.edit(embed=Page_Dict[CurrentPage]["Embed"])


        newembed = Page_Dict[CurrentPage]["Embed"]
        newembed.color = discord.Embed.Empty
        await List_Object.edit(embed=newembed)
        await Helpers.RemoveAllReactions(List_Object)
        return





class Log:
    Guild_Directory = {}  # {GuildID: LogChannelObj}
    Logging_Folder_ID = 487134325389918218

    SentColor = 0x42a1f4
    EditColor = 0xe5c1ff
    DeleteColor = 0xAA0000

    @staticmethod
    async def LogSend(Context):  # Ran on every message; logs
        # First we need the ID of the channel for that guild
        GuildLogChannel = await Log.FindLogChannel(Context.Message.channel)

        # Now let's prepare the Embed to send
        title = "**Message Sent in: "
        if Context.InDM:
            title += "Direct Messages"
        else:
            title += Context.Message.channel.name + "/" + Context.Message.guild.name

        title += "**\n"

        description = Context.Message.content[0:1500]
        name = Context.Message.author.name + "#" + str(Context.Message.author.discriminator)

        timestamp = Helpers.EmbedTime().strftime("%A %B %d at %X")
        timestamp = "\n_Originally sent on " + timestamp + "_"

        footer = "ID: " + str(Context.Message.id)

        em = discord.Embed(description=title + description + timestamp, color=Log.SentColor)
        em.set_author(name=name, icon_url=Context.Message.author.avatar_url)
        em.set_footer(text=footer)
        # todo add images to log

        SentLogMessage = await GuildLogChannel.send(embed=em)

        return SentLogMessage

    @staticmethod
    async def FindGuildLogCategory():
        """
        Locates the GuildLog Category in the Red Playground Server
        :return: discord.CategoryChannel
        """
        LogCategory = None
        PlayGroundGuild = Vars.Bot.get_guild(Conversation.Server_IDs["PlayGround"])
        # Let's iterate through each category until we find the one
        for TempCategory in PlayGroundGuild.categories:
            if TempCategory.id == Log.Logging_Folder_ID:
                LogCategory = TempCategory
                break

        return LogCategory

    @staticmethod
    async def FindLogChannel(SentChannel):
        """
        Checks Log.Guild_Directory to see if the channel is already there
        If not, searches for it in the Discord Guild, and adds it to the directory
        If not, creates it in the discord, adds it to the directory.
        :param SentChannel: the discord.Channel obj of the channel that the message was sent in
        :return: the discord.Channel obj of the channel to log the message in
        """

        # First off, is it a DM Channel? If so, the "SentGuildID" is RedBot's UserId
        if IsDMChannel(SentChannel):
            SentGuildID = Vars.Bot.user.id
            DM = True
        else:
            SentGuildID = SentChannel.guild.id
            DM = False

        # Do we already have the SentGuildID in the Log.Guild_Directory?
        if SentGuildID in Log.Guild_Directory.keys():
            # If so:
            LogChannelObj = Log.Guild_Directory[SentGuildID]
            return LogChannelObj

        # Okay, is the channel in the cateogry?
        LogCategory = await Log.FindGuildLogCategory()

        # Now we have LogCategory. Let's check the channels in it for the following:
        LogIdentifier = str(SentGuildID)
        LogChannelObj = None
        # Let's iterate
        for TempChannel in LogCategory.channels:
            if TempChannel.name.endswith(LogIdentifier):
                LogChannelObj = TempChannel

        # If we haven't found a LogChannelObj, let's create one
        if not LogChannelObj:
            # Create Name
            if DM:
                SentGuildName = "Direct Messages"
            else:
                SentGuildName = SentChannel.guild.name
                if len(SentGuildName) > 20:
                    SentGuildName = SentGuildName[0:20]

            LogChannelName = SentGuildName + " " + str(SentGuildID)
            PlayGroundGuild = Vars.Bot.get_guild(Conversation.Server_IDs["PlayGround"])
            LogChannelObj = await PlayGroundGuild.create_text_channel(LogChannelName, category=LogCategory)

        # Okay so now we have a LogChannelObj, so let's update Log.Guild_Directory
        Log.Guild_Directory[SentGuildID] = LogChannelObj

        return LogChannelObj

    @staticmethod
    async def CleanUpLogData():
        """
        Should be ran nightly, ensures all log channels have the correct names and cleans the log cache
        :return: None
        """
        # First, let's iterate through each item in the GuildLog Category to see if the channels all have the right name
        GuildLogCategory = await Log.FindGuildLogCategory()
        for Channel in GuildLogCategory.channels:
            # We need to confirm that the item we're working with is a logchannel
            PossibleChannelID = Channel.name.split("-")[-1]  # This formula gives us the last word in it

            if not PossibleChannelID.isdigit():
                # If it's not a number, this channel isn't for a guildlog, so move on.
                continue

            elif int(PossibleChannelID) == Vars.Bot.user.id:
                # If it is a number but it's the bot's ID, this is the direct messages channel
                continue

            # If we're here, the channel name must be right, so let's just check if the names are all correct
            LoggedGuild = Vars.Bot.get_guild(int(PossibleChannelID))
            if not LoggedGuild:
                # If it's not a real guild, move on
                continue

            # This'll ensure the name is equal to that of the channel
            GuildName = LoggedGuild.name.lower()[0:20].strip().replace(" ","-")
            GuildName = GuildName + "-" + PossibleChannelID

            if GuildName != Channel.name:
                # Send Embed discussing name change
                em = discord.Embed(title="Logging Guild Name Change / Log Channel Name Change", description=
                                   "Old: " + Channel.name + "\nNew: " + GuildName)
                await Channel.send(embed=em)

                await Channel.edit(name=GuildName)

        # Now that all of that madness is over, let's just clear the Log.Guild_Directory
        Log.Guild_Directory = {}

    @staticmethod
    async def AppendSentLog(Add_Str: str, Msg_ID: int, LogChannel, New_Color=None):
        """
        Ran by a few functions to add something to a message log. Can be an edit, deletion, etc.
        :param Add_Str:     The string of text to append to the bottom
        :param Msg_ID:      The ID of the message to change
        :param LogChannel:  The channel to look in
        :param New_Color:   The color if you want to change it
        :return:            None
        """

        ID_Search_String = "ID: " + str(Msg_ID)  # This'll be what we look for in the footer of messages

        Matching_Log_Msg = None
        async for loggedmessage in LogChannel.history(limit=500):
            if not loggedmessage.embeds:  # If it doesn't have embeds, move on.
                continue
            if loggedmessage.author.id != Vars.Bot.user.id:
                continue

            # Set Log_Embed equal to the dict of the embed content
            Log_Embed = loggedmessage.embeds[0].to_dict()
            if 'footer' in Log_Embed.keys():  # If it has a footer element
                if 'text' in Log_Embed['footer'].keys():  # And a text element
                    if ID_Search_String == Log_Embed['footer']['text']:  # Check if the footer text matches the id string
                        Matching_Log_Msg = loggedmessage  # if so, end. we've found our match
                        break


        if Matching_Log_Msg:  # If it does have the message:
            Em_Old = Matching_Log_Msg.embeds[0].to_dict()
            Matching_Log_Msg_Content = Em_Old['description']
            New_Description = Matching_Log_Msg_Content + "\n\n" + Add_Str.strip()
            if New_Color:
               Color_Change = New_Color
            else:
                Color_Change = Em_Old['color']


            # Create embed
            em = discord.Embed(description=New_Description, color=Color_Change)
            em.set_author(name=Em_Old['author']['name'], icon_url=Em_Old['author']['icon_url'])
            em.set_footer(text=Em_Old['footer']['text'])


            await Matching_Log_Msg.edit(embed=em)

    @staticmethod
    async def LogEdit(BeforeContext, AfterContext):  # Ran on every edit; logs edits
        GuildLogChannel = await Log.FindLogChannel(AfterContext.Message.channel)

        if BeforeContext.Message.content == AfterContext.Message.content:
            return

        content = AfterContext.Message.content
        if len(content) > 1000:
            content = content[0:1000] + "[...]"

        timestamp = Helpers.EmbedTime().strftime("%A %B %d at %X")
        timestamp = "\n_Edited on " + timestamp + "_"

        Edit_Log_Str = "\n**Edited To:**\n" + content + timestamp

        await Log.AppendSentLog(Edit_Log_Str, AfterContext.Message.id, GuildLogChannel, New_Color=Log.EditColor)

    @staticmethod
    async def LogDelete(Context, Reason):
        if not type(Context) == ContextMessage:
            Context = ContextMessage(Context)

        if Context.Message.author.bot:
            if Context.Message.author.id == Vars.Bot.user.id:
                DeletedFromBot = True
                return
            return

        # Assuming not from bot
        GuildLogChannel = await Log.FindLogChannel(Context.Message.channel)


        Delete_Log_Str = ''
        if not Reason:
            timestamp = Helpers.EmbedTime().strftime("%A %B %d at %X")

            Delete_Log_Str = "\n**Deleted on " + timestamp + ".**"
        else:
            Delete_Log_Str = Reason



        await Log.AppendSentLog(Delete_Log_Str, Context.Message.id, GuildLogChannel, New_Color=Log.DeleteColor)

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


class Admin:
    @staticmethod
    @Command(Start="Delete", Prefix=True, Admin=True, NoSpace=True, NotInclude="DeleteSince")
    async def Delete(Context):
        """
        Deletes a certain number of messages
        :param message: The original message
        :return: returns nothing
        """
        message = Context.Message


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
            confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, "Delete " + str(content) + " messages?",
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

                #Log.SetLogChannel()
                #await Helpers.SendLongMessage(Log.LogChannel, AllIDs)

    @staticmethod
    @Command(Start="DeleteSince", Prefix=True, Admin=True, NoSpace=True)
    async def DeleteSince(Context):
        Content = Context.Message.content[len(" DeleteSince"):].strip()

        LastHour = "In the Last Hour"
        Last5Minutes = "In the Last 5 Minutes"
        CustomChoice = "OR enter a custom time"

        FirstChoice = await Interraction.UserChoice(Context.Channel, Context.Message.author, "DeleteSince: How far back should I go?", description="I should delete messages sent: ",
                                               Choices=[Last5Minutes, LastHour, CustomChoice], Show_Cancel=True)
        if FirstChoice == "Cancel":
            return

        # Okay so the item we're looking for is SinceTimeStamp
        SinceTimeStamp = None

        if FirstChoice == CustomChoice:
            MinuteChoice = "Minutes"
            HourChoice = "Hours"
            DayChoice = "Days"

            SecondChoice = await Interraction.UserChoice(Context.Channel, Context.Message.author, "DeleteSince: What unit would you like to use?", description="Next you'll give me a number, what will be the unit of time associated with it?",
                                                    Choices=[MinuteChoice, HourChoice, DayChoice], Show_Cancel=True)
            if SecondChoice == "Cancel":
                return

            AnswerMsg = await Helpers.NewAskQuestion(Context.Message.channel, "Answer this: I should delete messages sent in the last ___ " + SecondChoice, SpecSender=Context.Message.author.id, AfterDelete=True)
            if not AnswerMsg:
                return

            try:
                TimeAmount = int(AnswerMsg.content.strip())
            except:
                return

            if SecondChoice == MinuteChoice:
                SinceTimeStamp = (Helpers.EmbedTime() - timedelta(minutes=TimeAmount)).timestamp()
            elif SecondChoice == HourChoice:
                SinceTimeStamp = (Helpers.EmbedTime() - timedelta(hours=TimeAmount)).timestamp()
            elif SecondChoice == DayChoice:
                SinceTimeStamp = (Helpers.EmbedTime() - timedelta(days=TimeAmount)).timestamp()


        elif FirstChoice == LastHour:
            SinceTimeStamp = (Helpers.EmbedTime() - timedelta(hours=1)).timestamp()
        elif Firstchoice == Last5Minutes:
            SinceTimeStamp = (Helpers.EmbedTime() - timedelta(minutes=5)).timestamp()

        await Context.Message.channel.send("That's all. Goodbye.")  # TODO FINISHcmd

    @staticmethod
    @Command(Start="Guilds", Prefix=True, Admin=True, NoSpace=True)
    async def GuildInfo(Context):
        message = Context.Message

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
    @Command(Start="Copy", Prefix=True, Admin=True)
    async def CopyFrom(Context):
        message = Context.Message

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
    @Command(Start="PermissionsIn", Prefix=True, Admin=True)
    async def PermissionsIn(Context):
        message = Context.Message

        guild = message.guild
        content = message.content[15:]
        ChannelID = int(content)
        Permchannel = Vars.Bot.get_channel(ChannelID)

        sendmsg = ""
        for permission in Permchannel.permissions_for(guild.get_member(Vars.Bot.user.id)):
            sendmsg += "\n" + permission[0] + "   " + str(permission[1])

        await Helpers.SendLongMessage(message.channel, sendmsg)

    @staticmethod
    @Command(Start="stop", Prefix=True, Admin=True, NoSpace=True)
    async def Stop(Context):
        """
        Stops the Bot
        :param message: Message.content
        :return: Returns nothing
        """
        message = Context.Message

        # Check to make sure the user confirms it
        confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, "Shut Down?", deny_text="Shut Down Cancelled")
        if confirmation:
            await Vars.Bot.change_presence(status=discord.Status.offline)  # Status to offline
            await Vars.Bot.logout()  # Log off

    @staticmethod
    @Command(Start="leave", Prefix=True, Admin=True, NoSpace=True)
    async def LeaveServer(Context):
        message = Context.Message

        text = "Leave " + message.guild.name + "?"  # Says "Leave Red Playground?"
        confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, text, deny_text="I will stay.")  # Waits for confirmation
        if confirmation:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Set up Time String
            await message.channel.send(Vars.Bot.user.name + " Left at " + current_time)  # Sends goodbye
            await message.guild.leave()  # Leaves

    @staticmethod
    @Command(Start="ForceLeave", Prefix=True, Admin=True, NoSpace=True)
    async def ForceLeave(Context):
        message = Context.Message

        ChannelToLeave = int(message.content[11:])  # Channel within Guild
        ChannelToLeave = Vars.Bot.get_channel(ChannelToLeave)
        GuildToLeave = ChannelToLeave.guild
 # hi
        text = "Leave " + GuildToLeave.name + "?"  # Says "Leave Red Playground?"
        confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, text, deny_text="I will stay.")  # Waits for confirmation
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
    @Command(Start="Disable", Prefix=True, Admin=True, NoSpace=True)
    async def Disable(Context):
        message = Context.Message

        if not await Interraction.Confirmation(Context.Channel, Context.Message.author, "Disable?", deny_text="Will Stay Enabled."):
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
        confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, to_send, timeout=30, return_timeout=True, deleted_original_message=True)
        if not confirmation:  # If they say X, stay disabled:
            await message.channel.send("Will stay disabled indefinitely. ", delete_after=5)
            return
        if confirmation:
            await message.channel.send("Enabling.")
            Vars.Disabled = False
            Vars.Disabler = None
            return

    @staticmethod
    @Command(Start="Enable", Admin=True, Prefix=True, NoSpace=True)
    async def Enable(Context):
        message = Context.Message

        if Vars.Disabler:
            if message.author.id != Vars.Disabler and message.author.id != Vars.Creator.id:
                return False

        Vars.Disabled = False
        Vars.Disabler = None

        await Other.StatusChange()

        msg = await message.channel.send('Bot Enabled.')
        await asyncio.sleep(5)
        await msg.delete()
        await message.channel.delete_messages([msg, message])

    @staticmethod
    @Command(Start="Talk", Prefix=True, Admin=True)
    async def Talk(Context):
        message = Context.Message

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
                response = await Interraction.Confirmation(Context.Channel, Context.Message.author, "Click when ready", timeout=120)
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
    @Command(Start="Status", Prefix=True, Admin=True, NoSpace=True)
    async def Status(Context):
        message = Context.Message

        sentTime = message.created_at
        receivedTime = datetime.utcnow()
        difference = receivedTime - sentTime

        now = datetime.utcnow()
        delta = now - Vars.start_time
        delta = delta.total_seconds()

        sendmsg = "Bot is ONLINE"
        sendmsg += "\n**Speed:** " + str(difference)[5:] + " seconds. "
        sendmsg += "\n**Uptime:** " + Sys.SecMin(int(delta))

        if Timer.Ping:
            sendmsg += "\n**TimeThread Ping:** " + str(int(datetime.now().timestamp()) - Timer.Ping) + " seconds since."
        else:
            sendmsg += "\n**No TimeThread Ping**"

        em = discord.Embed(title="Current Status", timestamp=Helpers.EmbedTime(), colour=Vars.Bot_Color,
                           description=sendmsg)
        em.set_author(name=Vars.Bot.user, icon_url=Vars.Bot.user.avatar_url)

        await message.channel.send(embed=em)

        TimerIsRunning = await Timer.IsRunning()
        if not TimerIsRunning:
            confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, "TimeThread is NOT running. Start it?")

            if confirmation:
                try:
                    await Timer.StartTimeThread()
                    Started_Successfully = False

                except:
                    second_confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, "That returned an error. Continue?.")
                    if second_confirmation:
                        Started_Successfully = True
                    else:
                        return

                await asyncio.sleep(2)
                if not await Timer.IsRunning():
                    Started_Successfully = False


                if Started_Successfully:
                    return

                RestartRedBot = "Restart Thread of RedBot"
                RestartRaspPi = "Restart whole RedBot Computer"

                Choices = [RestartRedBot, RestartRaspPi]

                final_choice = await Interraction.UserChoice(Context.Channel, Context.Message.author, "Didn't work. What action should I take?", Choices, Show_Cancel=True)

                if not final_choice:
                    return

                if final_choice == "Cancel":
                    return

                if final_choice == RestartRaspPi:
                    await Vars.Creator.send("Performing Full System Restart")
                    info = {
                        "Restarted": True,
                        "Type": "Full OS Restart.",
                        "Channel_ID": Context.Message.channel.id
                    }
                    Helpers.SaveData(info, type="System")

                    CMDOutput = os.popen("sudo reboot").read()

                elif final_choice == RestartRedBot:
                    await Admin.BotRestart("TimeThread Check Full Restart", Context.Message.channel.id)
                    return

        #elif TimerIsRunning == "NoPing":
        #    await message.channel.send("I have not recieved a ping from the timethread yet. If I have just restarted, "
        #                               "this is okay. Otherwise, you should check for an error because I haven't started"
        #                               " the timethread since I've booted. ")

    @staticmethod
    async def BotRestart(type, Channel_ID, Log=True):
        if Log:
            info = {
                "Restarted": True,
                "Type": type,
                "Channel_ID": Channel_ID
            }
            Helpers.SaveData(info, type="System")

        # Restart

        Timer.StopThreadTwo = True
        while Timer.Running:
            Timer.StopThreadTwo = True
            await asyncio.sleep(.5)  # Documentation

        await asyncio.sleep(5)

        os.execv(sys.executable, ['python3'] + sys.argv)
        return

    @staticmethod
    @Command(Start="Restart", Prefix=True, Admin=True, NoSpace=True)
    async def Restart(Context):
        message = Context.Message

        confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, "Restart?", deny_text="Restart Cancelled")
        if not confirmation:
            return
        # Add check to message
        await message.add_reaction(Conversation.Emoji["check"])

        await Admin.BotRestart("Requested Restart", message.channel.id)

    @staticmethod
    async def CheckRestart():
        # Runs on start, checks if it just restarted
        restart_data = Helpers.RetrieveData("System")

        if restart_data["Restarted"]:
            channel = Vars.Bot.get_channel(restart_data["Channel_ID"])
            to_send = "Successfully Completed a `Full` " + restart_data["Type"]
            if channel:
                await channel.send(to_send)
            else:
                Creator = Vars.Creator
                if not Creator:
                    Creator = Vars.Bot.get_user(int(Sys.Read_Personal(data_type="Dom_ID")))

                await Creator.send(to_send)

            restart_data["Restarted"] = False
            Helpers.SaveData(restart_data, type="System")

            if restart_data["Type"] == "Update":
                await Admin.OnUpdate(restart_data["Channel_ID"])
                return True
        return False

    @staticmethod
    @Command(Start="Update", Prefix=True, Admin=True, NoSpace=True)
    async def Update(Context, fromBot=False):
        message = Context.Message

        if Context.InDM:
            await message.channel.send("Oops! Can only update rn from a group server! :)\nTerminated Update.")
            return

        if not await Interraction.Confirmation(Context.Channel, Context.Message.author, "Update?", deny_text="Update Cancelled", timeout=20):
            return

        channel = message.channel
        g = git.cmd.Git(os.getcwd())
        output = g.pull()

        to_send = "`" + output + "`"
        await channel.send(output)

        if "Already" in output:
            return

        await message.add_reaction(Conversation.Emoji["check"])
        print("Restarting RedBot for Requested Update")
        await Admin.BotRestart("Update", message.channel.id)

    @staticmethod
    async def InternalUpdate():
        g = git.cmd.Git(os.getcwd())
        output = g.pull()
        if "Already" in output:
            return
        print("Restarting RedBot for Automagic Update")

        await Admin.BotRestart("Automatic Update", 267071439109226496)

    @staticmethod
    @Command(Start="SaveData", Prefix=True, Admin=True)
    async def SaveDataFromMessage(Context):
        # BROKEN!
        """
        Guides through the process of saving data to the remote bot from a discord message.
        :param message: The message object
        :return: Nothing, but should save the data.
        """
        message = Context.Message

        channel = message.channel

        currentData = Helpers.RetrieveData()

        if not await Interraction.Confirmation(Context.Channel, Context.Message.author, "THIS IS BROKEN. CONTINUE?"):
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
            confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, "Cannot find data type. Continue?", timeout=30)
            if not confirmation:
                # If they do not want to continue
                return

        to_load = ""
        is_long = await Interraction.Confirmation(Context.Channel, Context.Message.author, "Is it longer than 2000?")
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

    @staticmethod
    @Command(Start="Download Data", Prefix=True, Admin=True, NoSpace=True)
    async def SendData(Context):
        message = Context.Message

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


        pretty_print = await Interraction.Confirmation(Context.Channel, Context.Message.author, "Do you want it to be pretty print?")

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
    @Command(Start="Change Personal", Prefix=True, Admin=True)
    async def ChangePersonal(Context):
        message = Context.Message

        if message.author != Vars.Creator:
            return

        content = message.content[16:].strip()

        if not await Interraction.Confirmation(Context.Channel, Context.Message.author, "Add " + content + " To Personal? Cannot be reversed."):
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
    @Command(Start="Broadcast", Prefix=True, Admin=True, NoSpace=True)
    async def Broadcast(Context):
        message = Context.Message

        if not await Interraction.Confirmation(Context.Channel, Context.Message.author, "Are you sure you want to broadcast?"):
            return

        message.content = message.content[1:].replace("broadcast", "").strip()

        await Helpers.MessageAdmins(message.content)

    @staticmethod
    @Command(Start="p", Admin=True, Prefix=True)
    async def SinglePrivateMessage(Context):
        message = Context.Message
        # This will delete any message that starts with /p after 20 seconds

        await message.add_reaction(Conversation.Emoji["x"])

        SecretChannel = Vars.Bot.get_channel(Sys.Channel["DeleteLog"])

        SecretContent = await Helpers.FormatMessage(message, IncludeArea=True, FullName=True)

        await SecretChannel.send(SecretContent)
        await asyncio.sleep(5)
        if not await Helpers.Deleted(message):
            await message.delete()

    @staticmethod
    @Command(Start = "os", Admin=True, Prefix=True)
    async def OsCommand(Context):
        message = Context.Message

        CMDInput = message.content[3:].strip()

        try:
            CMDOutput = os.popen(CMDInput).read()
        except:
            await Admin.BotRestart("Restart. \nSomething went wrong during OS Command!",
                                   Context.Message.channel.id)

        await Helpers.SendLongMessage(message.channel, CMDOutput)

        await message.channel.send("== End of Output ==")
        return


class OnEvents:
    """
    Class containing functions that are run on each event.
    """
    @staticmethod
    async def On_Ready(selfbot):
        """
        Run every time the bot starts up to start important functions
        :param selfbot: the self object of the bot that is fed through
        :return: True if sucessful.
        """
        print("Admin Code: " + str(Vars.AdminCode))
        join = 'Logged on as {0}'.format(selfbot.user)
        print(join + "\n" + "=" * len(join))
        Vars.Creator = Vars.Bot.get_user(int(Sys.Read_Personal(data_type="Dom_ID")))
        await Admin.InternalUpdate()

        await Other.StatusChange()

        # Check if it just restarted:
        isupdate = await Admin.CheckRestart()  # True or False if update

        await Memes.CleanMemes()  # Clean Meme Files
        await Other.InterpretQuickChat()  # Prepare QuickChat Data
        await Cooldown.SetUpCooldown()  # Set up Cooldown Data
        Vars.start_time = datetime.utcnow()

        if Sys.Read_Personal(data_type="Bot_Type") == "RedBot":  # vs GOLDBOT
            string = "I have just started up"
            if isupdate:
                string += ". Updated."
            em = discord.Embed(title=string, timestamp=Vars.start_time, color=Vars.Bot_Color)
            await Vars.Creator.send(embed=em)

        await Remind.CheckForOldReminders()
        await Poll.RefreshData()
        await Poll.CleanData()

        Vars.Ready = True
        print("Ready!")

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
        # Double check if it's the bot
        if member.id == Vars.Bot.user.id:
            return

        guild = member.guild
        channel_list = []
        for channel in guild.text_channels:
            channel_list.append(channel)
        default_channel = channel_list[0]

        permissions = await CheckPermissions(default_channel, ["view_audit_log", "send_messages", "change_nickname"],
                                             return_all=True)
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

    @staticmethod
    async def On_Error(event_method, *args, **kwargs):
        """
        Ran on every error within the bot.
        :param event_method:    Tells you what function had the error
        :param args:            The stuff affected (message obj, reaction obj, etc)
        :param kwargs:          Other stuff? Not really sure what goes here tbh
        :return:                Nothing really. Sends in channel
        """
        # Okay so we want these two things from the args/kwargs:
        Context   = None  # The context in which it happened
        Traceback = None  # What lines of code stopped this
        Channel = None

        Context, Location = None, None
        if args:  # Okay so if there's a message, or a reaction, sent along
            First_Argument = args[0]

            # So now we have this First_Argument, here's what we want
            ArgumentType = None
            if type(First_Argument) == discord.reaction.Reaction:
                ArgumentType = "Reaction"
            elif type(First_Argument) == discord.message.Message:
                ArgumentType = "Message"
            elif type(First_Argument) == discord.guild.Guild:
                ArgumentType = "Guild"

            # Now we know what type the argument was, let's dictate what we want from this

            # Let's start with Context
            if ArgumentType == "Reaction":
                Channel = First_Argument.message.channel

                Context = "**Reaction** on message by `" + First_Argument.message.author + "` saying `" + First_Argument.message.content[                                                                                   0:60]
                try:
                    Context += "`\nReaction was `" + First_Argument.emoji + "` by `" + str(await First_Argument.users().flatten())
                except:
                    Context += "\nError Retrieving Reaction Info"

            elif ArgumentType == "Message":
                Channel = First_Argument.channel

                Context = "**Message** by " + First_Argument.author.name + " *`(" + str(First_Argument.author.id) + \
                          ")`* saying **\"**`" + First_Argument.content[0:80] + "`**\"**"

            # Now let's do Location
            if ArgumentType == "Message" or ArgumentType == "Reaction":
                # Quick if DM Channel
                if IsDMChannel(Channel):
                    Location = "**Location:** #Direct Messages Channel"
                else:
                    Location = "**Location:** #" + Channel.name + " *`(" + str(Channel.id) + ")`* in " \
                                                 + Channel.guild.name + " *`(" + str(Channel.guild.id) + ")`*"

            # Okay so now we have an official Location and Context

        if not Context or not Location:
            # So if there is no Context and no Location
            Context = "**RedBot Internal Error** in *`" + str(event_method) + "`* function."
            Location = "No futher knowledge"

        # Okay so now we have Context and Location. Let's figure out the Long_TraceBack and Short_Traceback
        Short_TraceBack = ""
        Long_TraceBack  = ""

        # This will create a list of the system traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tblist = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tblist = tblist[2:]

        # Now let's work with the traceback a bit
        new_tblist = []
        for part in tblist:
            # Okay so these are some things to shorten the criteria
            part = part.replace("\\", "/").strip()
            part = part.replace("C:/Users/spong/Desktop/", "").replace("/home/pi/Desktop/", "")
            part = part.replace("C:/Users/spong/AppData/Local/Programs/Python/Python36-32/lib/site-packages/", "")
            part = part.replace("During ", "# During ")
            part = part.replace("RedBot/", "").replace("GoldBot/", "")
            part = part.replace("File ", "")
            part = part.replace("    ", "\t")

            if part.startswith("\"discord/") or part.startswith("Traceback"):
                continue

            # After all that nonsense, we need to add it to new_tblist
            new_tblist.append(part)

        # Now let's set up the Short_TraceBack and Long_Traceback
        Short_TraceBack = new_tblist[-1]
        Long_TraceBack  = '\n'.join(new_tblist)

        # Now we have both of them. Let's make two messages, Short_Em and Long_Em
        # SHORT_EM
        CatchPhrase = Sys.Response(Conversation.Error_Response).strip()
        Short_Em_Description = CatchPhrase + "\n\t*`" + Short_TraceBack + "`*"
        Short_Em = discord.Embed(color=Vars.Bot_Color, description=Short_Em_Description)
        Short_Em.set_author(name="RedBot Error", icon_url=Vars.Bot.user.avatar_url, url="http://www.github.com/ElGrubb/RedBot")
        Short_Em.set_footer(text="I'm still running, but I have terminated the command. ")

        # LONG_EM
        DateStamp = datetime.now().strftime("%b %d %Y at %r")
        Long_Em_Description = Context + "\n" + Location + "\n```py\n" + Long_TraceBack + "```"
        Long_Em = discord.Embed(color=Vars.Bot_Color, description=Long_Em_Description)
        Long_Em.set_author(name="RedBot Error", icon_url=Vars.Bot.user.avatar_url, url="http://www.github.com/ElGrubb/RedBot")
        Long_Em.set_footer(text="Error Occurred on " + DateStamp+ ", but I could recover successfully with no damage done. Crisis Averted")

        # Let's just test to see if it's with on_ready
        if str(event_method).lower() == "on_ready":
            Vars.Safety_Mode = True
            await Vars.Creator.send("Error during On_Ready! Starting in safety mode.")

        # Quick test if it's GoldBot or not
        if Vars.Bot.user.name == "GoldBot":
            if Channel:  await Channel.send(embed=Long_Em)
            else:   await Vars.Creator.send(embed=Long_Em)
            return

        Crash_Channel = Vars.Bot.get_channel(Sys.Channel["Errors"])
        await Crash_Channel.send(embed=Long_Em)

        if Channel:  await Channel.send(embed=Short_Em)
        else:   await Vars.Creator.send(embed=Long_Em)

        return

    @staticmethod
    async def On_Guild_Join(Guild):
        # Ran when the bot joins a guild
        # First thing to do is check that the bot is given all permissions
        Bot_Member = Guild.get_member(Vars.Bot.user.id)

        # Tell Creator that it joined the server
        to_send = "I have just been added to " + Guild.name
        Creator_Message = await Vars.Creator.send(to_send)

        Integration_Role = None
        # Find the role created by Integration (Should be named RedBot/GoldBot)
        for Bot_Role in Bot_Member.roles:
            if Bot_Role.name == Vars.Bot.user.name:
                Integration_Role = Bot_Role

        # Create a Permission Dictionary (PermDict) of the Integration Roles given
        PermDict = {}
        for permission in Integration_Role.permissions:
            PermDict[permission[0]] = permission[1]

        # Now we want to see if it can read and write messages. Otherwise we have to leave.
        if not PermDict["read_messages"] or not PermDict["send_messages"]:
            await Guild.leave()
            return

        # Assuming you can send messages, let's send a hello message in the Top Channel
        Top_Channel = Guild.text_channels[0]

        def CreateEmbed(Description, Done_Working=False):
            """
            Creates the embed necessary for the Guild Join
            :param Description: What to put in the message
            :return: The discord.Embed object
            """

            title = "I'm Setting Everything Up."
            bottom = "  ---  Hang tight while I work through all the calculations."
            if Done_Working:
                title = ""
                bottom = ""

            em = discord.Embed(color=Vars.Bot_Color, description=Description, title=title)
            em.set_author(name="Hi, I'm " + Vars.Bot.user.name + ".", icon_url=Vars.Bot.user.avatar_url)
            em.set_footer(text="Joining " + Guild.name + bottom, icon_url=Guild.icon_url)
            return em

        ProgressMsg = await Top_Channel.send(embed=CreateEmbed("Checking Guild Permissions..."))

        # Okay so now we need to check what permissions we don't have.
        Necessary_Permissions = ['add_reactions', 'attach_files', 'change_nickname', 'embed_links', 'external_emojis',
                                 'manage_channels', 'manage_messages', 'manage_roles', 'read_message_history', 'read_messages',
                                 'send_messages', 'view_audit_log']
        Recommended_Permissions = ['administrator', 'manage_guild', 'mention_everyone', 'manage_emojis', 'kick_members']
        Not_Needed_Permissions = ['ban_members', 'connect', 'manage_nicknames', 'manage_webhooks', 'move_members', 'mute_members',
                                  'send_tts_messages', 'speak', 'use_voice_activation']

        # So let's go through each permission!
        # NECESSARY PERMISSIONS
        Missing_Necessary_Permission = False
        Necessary_String = ""
        for permission in Necessary_Permissions:
            if not PermDict[permission]:
                Necessary_String += "\n" + Conversation.Emoji['x'] + " " + Sys.FirstCap(permission)
                Missing_Necessary_Permission = True
        if Necessary_String:
            Necessary_String = "Absolutely Necessary Permissions: ```" + Necessary_String + "```"

        # RECOMMENDED PERMISSIONS
        Recommended_String = ""
        for permission in Recommended_Permissions:
            if not PermDict[permission]:
                Recommended_String += "\n" + Conversation.Emoji['x'] + " " + Sys.FirstCap(permission)
        if Recommended_String:
            Recommended_String = "Recommended Permissions: ```" + Recommended_String + "```"

        # See if there's anything we need :)
        await ProgressMsg.delete()
        All_Strings = ""
        if Recommended_String or Necessary_String:
            All_Strings = Necessary_String + Recommended_String
            All_Strings.strip()
            All_Strings += "\nPlease add these to the `" + Vars.Bot.user.name + "` role, not my color one!"

            PermissionMsg = await Top_Channel.send(embed=CreateEmbed(All_Strings, Done_Working=True))

        if Missing_Necessary_Permission:
            # If the bot is missing a necessary permission, it should leave the server
            await Top_Channel.send(embed=CreateEmbed("I am going to leave now. Please give me the permissions when you add "
                                   "me in the server and it'll be put in my integration role.", Done_Working=True))
            await Guild.leave()
            return

        # Moving on, now we know we have the right permissions. Let's put some filler text
        ProgressMsg = await Top_Channel.send(embed=CreateEmbed("Creating Color Role"))
        color = discord.Color(Vars.Bot_Color)
        color_role = await Guild.create_role(name=Vars.Bot.user.name + " Color", color=color,
                                           reason="Created to have my color be true")
        await Bot_Member.add_roles(color_role)

        # Now we have the color role. We now are pretty great to go. Let's add some weird filler because it does nothing important
        async def ProgressMessageEdits():
            try:
                await asyncio.sleep(2)
                await ProgressMsg.edit(embed=CreateEmbed("Creating Database entry for Guild..."))

                await asyncio.sleep(2)
                await ProgressMsg.edit(embed=CreateEmbed("Creating Database entry for Guild...\n"
                                                         "Adding members to database..."))

                await asyncio.sleep(6)
                await ProgressMsg.edit(embed=CreateEmbed("Checking Guild Statistic..."))

                await asyncio.sleep(1)
                await ProgressMsg.edit(embed=CreateEmbed("Doing other random ass stuff"))

                await asyncio.sleep(2)
                await ProgressMsg.edit(embed=CreateEmbed("Cleaning stuff up..."))

                await asyncio.sleep(5)
                await ProgressMsg.edit(embed=CreateEmbed("Waiting for Confirmation..."))

            except discord.NotFound:
                return 0

        # Okay so we're going to run the ProgressMessageEdits thread simotaneously while waiting for confirmation
        NewThread = Vars.Bot.loop.create_task(ProgressMessageEdits())
        Confirmation = await Interraction.Confirmation(Vars.Creator, Vars.Creator, "Should I stay?", extra_text=All_Strings,
                                                  deny_text="Okay, leaving", yes_text="Okay, staying!")

        await Helpers.QuietDelete(ProgressMsg)

        if Confirmation == False:
            await Top_Channel.send(embed=CreateEmbed("I'm leaving due to a negative confirmation. <3", Done_Working=True))
            await Guild.leave()
            return

        # If the confirmation is true, send the Hello Message

        WelcomeEmbed = discord.Embed(description="\nI am a bot created by *`Dom#2774`*  to help with all sorts of stuff."
                                                 "\nHere are some commands and functions you can do with me:", color=Vars.Bot_Color)
        WelcomeEmbed.set_thumbnail(url=Vars.Bot.user.avatar_url)
        WelcomeEmbed.set_author(name="Hi, I'm RedBot")
        OtherText = "**Reminders** - I can remind you of text, links, or images at any given time"\
                    "```>>> /remind {When you want to be reminded} {Stuff to be reminded with}"\
                    "\n>>> /remind 6 hours 2 minutes http://www.WPI.edu"\
                    "\n>>> /r 12:24 that I need to water my plant"\
                    "\n>>> /editreminders```"\
                    "\n**Polls** - I can create polls for user votes in the guild"\
                    "```>>> /poll Should we add RedBot?\n\tAbsolutely\n\tMaybe not\n\tNever!```"\
                    "\n**Tags** - I can save images, links, and data under a 'key' to be recalled at any time"\
                    "```>>> /settag {Key-Separated-By-Hyphens} Content to save"\
                    "\n>>> /settag WPI-Website http://www.WPI.edu  # To set the tag"\
                    "\n>>> /tag WPI-Website  # To call the tag (shorten /tag to /t)"\
                    "\n>>> /setptag {Personal-Tag-Key} Content # To set a tag only you can access"\
                    "\n>>> /ptag Personal Tag Key # To call that personal tag```"\
                    "\n**Calculations** - I can access Wolfram Alpha to provide in-Discord-queries"\
                    "```>>> =5 + 3"\
                    "\n>>> Capital of Oregon"\
                    "\n>>> Derivative of f(x) = 3 sin(x) + 7x"\
                    "\n>>> CO2 structure```"\
                    "\n**Other Functions** - This is barely all I can do."\
                    "```>>> /weather {location}"\
                    "\n>>> /color {Hex Code}  # To change your rank color"\
                    "\n>>> /upload {image attachment}"\
                    "\n>>> /shorten {link}"\
                    "\n>>> /send {meme/doggo/cringe/surreal}"\
                    "\nAnd quote functionality {/help quote}```"\
                    "\nPlease perform /help {command name} to learn more about specific commands"

        await Top_Channel.send(embed=WelcomeEmbed)
        await Top_Channel.send(OtherText)


class Cooldown:
    meme_types = ["meme", "quote", "nocontext", "delete", "remind"]
    data = {}
    defaults = {
        "meme": [30, 30],
        "quote": [30, 15],
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
    Ping = None

    @staticmethod
    def DigitTime():
        hour = time.strftime('%H')
        minute = time.strftime('%M')
        return hour + ':' + minute

    @staticmethod
    async def TimeThread():
        print("Started TimeThread")
        Timer.Running = True
        await asyncio.sleep(10)
        old_time, current_time = None, None

        Timer.Ping = int(datetime.now().timestamp())

        # while not Vars.Crash:
        while not Timer.StopThreadTwo:
            await asyncio.sleep(3)
            old_time = current_time
            current_time = Timer.DigitTime()

            # Morning Weather
            if current_time != old_time:  # Ensures this only runs on minute change
                Timer.Ping = int(datetime.now().timestamp())
                print(current_time)

                try:
                    await Timer.TimeThreadRounds(current_time)

                except Exception as e:
                    # Okay so now we have Context and Location. Let's figure out the Long_TraceBack and Short_Traceback
                    Short_TraceBack = ""
                    Long_TraceBack = ""

                    # This will create a list of the system traceback
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    tblist = traceback.format_exception(exc_type, exc_value, exc_traceback)
                    tblist = tblist[2:]

                    # Now let's work with the traceback a bit
                    new_tblist = []
                    for part in tblist:
                        # Okay so these are some things to shorten the criteria
                        part = part.replace("\\", "/").strip()
                        part = part.replace("C:/Users/spong/Desktop/", "").replace("/home/pi/Desktop/", "")
                        part = part.replace(
                            "C:/Users/spong/AppData/Local/Programs/Python/Python36-32/lib/site-packages/", "")
                        part = part.replace("During ", "# During ")
                        part = part.replace("RedBot/", "").replace("GoldBot/", "")
                        part = part.replace("File ", "")
                        part = part.replace("    ", "\t")

                        if part.startswith("\"discord/") or part.startswith("Traceback"):
                            continue

                        # After all that nonsense, we need to add it to new_tblist
                        new_tblist.append(part)

                    # Now let's set up the Short_TraceBack and Long_Traceback
                    Short_TraceBack = new_tblist[-1]
                    Long_TraceBack = '\n'.join(new_tblist)

                    print(Long_TraceBack)

                    try:
                        await Vars.Creator.send("Just crashed now. Shutting RedBot Down. Beep boop.")
                    except:
                        pass
                    quit()

                    break  # todo FINISH

        Timer.Running = False
        print("TimeThread Terminated.")

    @staticmethod
    async def TimeThreadRounds(current_time):
        if current_time == '06:30':
            try:
                today = datetime.now().strftime("%B %d")
                print("Good Morning! It is " + today)
                await Other.T_Weather()
            except Exception as e:
                await Vars.Creator.send("Error during weather, error = " + str(e))

        if current_time == '23:00':
            await Timer.NightlyCheck()

        await Remind.CheckForReminders()

        if current_time.endswith(":01") or current_time.endswith(":30"):
            if not Vars.Disabled:
                try:
                    await Other.StatusChange()  # NEvermind
                except:
                    print("OOF")


    @staticmethod
    async def StartTimeThread():
        Timer.StopThreadTwo = True
        Vars.Bot.loop.create_task(Timer.TimeThread())
        Timer.StopThreadTwo = False

    @staticmethod
    async def IsRunning():
        # Returns True if the timethread is running, false if not.
        Now = int(datetime.now().timestamp())
        if not Timer.Ping:
            return "NoPing"
        if Now - Timer.Ping >= 90:  # Two minutes since last ping:
            return False
        return True

    @staticmethod
    async def NightlyCheck():
        """
        So these are the things that happen nightly at 11:00 PM
        :return: None
        """

        # So first let's send the DataFile
        DataLogChannel = Conversation
        DateStamp = datetime.now().strftime("%b %d %Y at %r")

        OrigPath = os.getcwd()
        if OrigPath.startswith("C:"):       Slash = "\\"
        elif OrigPath.startswith("/home"):  Slash = "/"
        addpath = Slash + "Data.txt"

        newfile = discord.File(os.getcwd() + addpath)
        FileChannel = Vars.Bot.get_channel(Conversation.Channel_IDs["FileLog"])
        await FileChannel.send("**Nightly File Send: **" + DateStamp, file=newfile)

        # Other checks to do nightly!
        await Remind.CheckForOldReminders()
        await Poll.CleanData()


class Quotes:
    @staticmethod
    async def OnMessage(Context):
        # Ran on message
        await Quotes.SendQuote(Context)
        await Quotes.QuoteCommand(Context)
        await Quotes.QuoteVote(Context)

    @staticmethod
    @Command(Prefix=True, Start="send quote", NoSpace= True)
    async def SendQuote(Context):
        """
        Sends random quote from the file
        Quote JSON Format:
        Quotes: {position: 6, data: [{date:x, quote:x, id:x, name:x}, {date:x, quote:x, id:x, name:x}]}

        :param message: MSG Object
        :return: Nothing
        """
        message = Context.Message
        GuildID = str(message.guild.id)
        #if GuildID == "267071439109226496":
        #    GuildID = "438483635818201089"

        # Cooldown
        cd_notice = Cooldown.CheckCooldown("quote", message.author, message.guild)
        if type(cd_notice) == int:
            msg = await message.channel.send('Cooldown Active, please wait: `' + Sys.SecMin(cd_notice) + '`')
            await asyncio.sleep(5)
            await message.channel.delete_messages([msg, message])
            return

        # Get Quote Dict
        data = Helpers.RetrieveData(type="Quotes")
        # This returns a dictionary of server id (keys) that have a dict about position and the data

        if GuildID not in data.keys():
            em = discord.Embed(description="There are no saved quotes for this server!\n"
                                                                "To save a quote, add a " + Conversation.Emoji["quote"] + " reaction "
                                                                "to a message.", timestamp=Helpers.EmbedTime())
            em.set_author(name="Quote Error", icon_url=Vars.Bot.user.avatar_url)
            em.set_footer(text=message.guild.name, icon_url=message.guild.icon_url)
            await message.channel.send(embed=em)
            await message.add_reaction(Conversation.Emoji["x"])
            return

        QuoteCount = len(data[GuildID]["Data"])  # A measure of how many quotes the server has saved
        if QuoteCount <= 3:
            em = discord.Embed(description="There are only " + str(QuoteCount) + " saved quotes for this server!\n"
                                           "To save a quote, add a " + Conversation.Emoji["quote"] + " reaction"
                                           "to a message. Once you have more than 3 saved quotes, you can use `/send quote`.",
                               timestamp=Helpers.EmbedTime())
            em.set_author(name="Quote Error", icon_url=Vars.Bot.user.avatar_url)
            em.set_footer(text=message.guild.name, icon_url=message.guild.icon_url)
            await message.channel.send(embed=em)
            await message.add_reaction(Conversation.Emoji["x"])
            return


        QuoteList = data[GuildID]["Data"]
        Position = data[GuildID]["Position"]

        ChosenQuote = QuoteList[Position]

        # Update Quote List etc
        data[GuildID]["Position"] += 1
        if data[GuildID]["Position"] >= len(data[GuildID]["Data"]):
            random.shuffle(data[GuildID]["Data"])
            data[GuildID]["Position"] = 0
        Helpers.SaveData(data, type="Quotes")

        # Modify the Data a bit
        date = datetime.fromtimestamp(ChosenQuote["date"])
        quote = "**\"**" + ChosenQuote["quote"] + "**\"**"
        sender_obj = await Vars.Bot.get_user_info(ChosenQuote["user_id"])
        guild_obj = Vars.Bot.get_guild(int(GuildID))
        if not guild_obj:
            guild_obj = message.guild

        # Prepare the Embed
        em = discord.Embed(description=quote, timestamp=date, colour=Vars.Bot_Color)
        em.set_footer(text="Saved Quote", icon_url=guild_obj.icon_url)
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
    @Command(Start="quote", Prefix=True)
    async def QuoteCommand(Context):
        message = Context.Message

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

        if Context.InDM:
            await message.channel.send("Are you really trying to create a quote... with just a robot?\nThat's sad.")
            return

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
        em.set_footer(text="10 minute timeout; Looking for 6 reactions total")

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
            await message.channel.send("Failed to receive reactions", delete_after=5)
            return None
        await Helpers.QuietDelete(msg)
        if not await Helpers.Deleted(message):
            await message.add_reaction(Conversation.Emoji["check"])

        data = await Quotes.NoteQuote(quote=content, user=mention_user, GuildID=message.guild.id)

        em = discord.Embed(title=data['quote'], timestamp=Helpers.EmbedTime(), colour=0xFFFFFF)
        em.set_footer(text="Saved Quote", icon_url=message.guild.icon_url)
        em.set_author(name=mention_user.name, icon_url=mention_user.avatar_url)

        await message.channel.send("Saved Quote:", embed=em)

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
            await Helpers.RemoveAllReactions(reaction.message)
            return
        if await CheckMessage(reaction.message, prefix=True, CalledInternally=True):
            await reaction.message.channel.send("Sorry, no quoting commands. Boss's orders.", delete_after=5)
            await Helpers.RemoveAllReactions(reaction.message)
            return

        if len(reaction.message.content) > 500:
            await reaction.message.channel.send("Simply too long to quote.", delete_after=5)
            await Helpers.RemoveAllReactions(reaction.message)
            return

        if reaction.count == 1:
            await reaction.message.channel.send("You are starting a Quote Vote! If 5 people react with that emoji, I'll save it as a quote.", delete_after=20)

        if reaction.count >= 5:
            await reaction.message.clear_reactions()
            await reaction.message.add_reaction(Conversation.Emoji["check"])
            data = await Quotes.NoteQuote(quote=reaction.message.content, user=reaction.message.author, GuildID=reaction.message.guild.id)

            em = discord.Embed(title=data['quote'], timestamp=Helpers.EmbedTime(), colour=0xFFFFFF)
            em.set_footer(text="Saved Quote", icon_url=reaction.message.guild.icon_url)
            em.set_author(name=reaction.message.author.name, icon_url=reaction.message.author.avatar_url)

            await reaction.message.channel.send("Saved quote:", embed=em)

    @staticmethod
    async def NoteQuote(quote=None, user=None, GuildID=None):
        date = datetime.now()
        timestamp = time.mktime(date.timetuple())
        quote = quote.strip()
        user_name = str(user)
        user_id = user.id

        data = Helpers.RetrieveData(type="Quotes")

        if str(GuildID) not in data.keys():
            data[str(GuildID)] = {
                "Position": 0,
                "Data": []
            }

        QuoteDict = {'date': timestamp, 'quote': quote, 'user_id': user_id, 'user_name': user_name}

        data[str(GuildID)]['Data'].append(QuoteDict)

        Helpers.SaveData(data_dict=data, type="Quotes")

        return QuoteDict

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

    @staticmethod
    @Command(Start="OutputQuotes", Prefix=True, Admin=True, NoSpace=True)
    async def QuoteVote(Context):
        QuoteData = Helpers.RetrieveData(type="Quotes")
        SendString = ""
        for Quote in QuoteData["info"]:
            SendString += Quote["user_name"] + "\t" + str(Quote["user_id"]) + "\t" + str(Quote["date"]) + "\t" + Quote["quote"]

            SendString += "\n"
        print(SendString)


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
    @Command(Start="send", Prefix=True, NotInclude="quote")
    async def SendMeme(Context, is_repeat=False):  # Todo Rewrite
        message = Context.Message
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

        return    # TODO: REDO MEME SENDING

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
                    await Helpers.RemoveAllReactions(msg)
                except discord.errors.NotFound:
                    pass
                return

            # If a reaction is added:
                await Helpers.RemoveAllReactions(msg)
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
    async def OnMessage(Context):
        await Other.QuickChat(Context)
        await Other.Change_Color(Context)
        await Other.Weather(Context)
        await Other.OldWeather(Context)
        await Other.NoContext(Context)
        await Other.ChatLinkShorten(Context)
        await Other.LinkShortenCommand(Context)
        await Other.CountMessages(Context)
        await Other.Upload(Context)
        await Other.AutoUpload(Context)
        await Other.UpdateNotes(Context)
        await Other.SendFile(Context)
        await Other.NewFile(Context)

    @staticmethod
    async def StatusChange():
        CurrentHour = (datetime.now()).hour

        # Okay let's go between possible times
        if 6 <= CurrentHour <= 10:  # Between 6 o clock and 10:
            New_Status = random.choice(["Good Morning", "Morning", "Hello", "Bright and Early", "Wakey Wakey", "Wake Up!", "How'd You Sleep?", "Great Morning!",
                                        "Lovely Morning", "Need Coffee?", "Have Breakfast", "5 more minutes, mom"])

        elif 10 < CurrentHour < 12:
            New_Status = random.choice(["Need Coffee", "Making Lunch", "Hello", "Working Hard", "Hardly Working", "Running Smoothly", "Working Well!"])

        elif 12 <= CurrentHour <= 16:
            New_Status = random.choice(["Happy Afternoon", "Good Afternoon", "Eating Lunch", "Working Hard", "Great Day", "Good Afternoon!", "Get Some Work Done", "Get to Work!",
                                        "Good Afternoon.", "Get to Work", "Say Hi!", "Shouldn't you be Working?", "\"Hello, RedBot!\""])

        elif  16 < CurrentHour <= 19:
            New_Status = random.choice(["Making Dinner", "Preparing Sunset", "Good Evening", "Great Evening", "Hello", "Howdy Neighbor"])

        elif 19 < CurrentHour <= 21:
            New_Status = random.choice(["Great Evening", "Good Evening", "Sun Setting", "Running Repair", "Having Dessert", "Running Well", "Evening!", "Howdy!"])

        elif 21 <= CurrentHour <= 24:
            New_Status = random.choice(["Go to Sleep", "It's bedtime", "Go to Bed", "Sweet Dreams", "Good Night", "Sweet Dreams", "Good Night", "Great Night",
                                        "The Stars are Beautiful Tonight!", "You Best Be Sleeping", "Have you seen the moon?"])

        elif 0 <= CurrentHour <= 4:
            New_Status = random.choice(["You Up?", "Go to Sleep", "Hello.", "It's Late.", "Get Some Sleep", "So Quiet", "Silent Night", "Sweet Dreams",
                                        "Sleep well!", "Sweet Dreams", "I Hope You're Asleep!", ":)"])

        elif 5 == CurrentHour:
            New_Status = random.choice(["A few more hours", "Up So Soon?", "Preparing Weather Data", "Dawn", "Watching Sunrise", "Go Back to Sleep", "You Up?", "Hello."])

        # Now we have all of those cute ass statements
        # Let's add a bit of variance
        Variance = random.randrange(0, 200)

        ActivityType = discord.ActivityType.playing
        StatusPrefix = "v" + Vars.Version + " | "

        if Variance == 36:
            # 1 in 200 chance, 0.5%
            ActivityType = discord.ActivityType.listening
            New_Status = random.choice(["You Closely", "You.", "Them.", "The Voices"])
            StatusPrefix = ""
        if Variance == 37 or Variance == 38:
            ActivityType = discord.ActivityType.watching
            New_Status = random.choice(["You...", "You.", "Them", "It Closely", "The Thing"])
            StatusPrefix = ""

        if 100 < Variance < 200 and 8 < CurrentHour < 20:
            New_Status = random.choice(["Online", "Bot Active", "RedBot Active", "Up and running!", "Hello", "Hello, Human.", "Hello, Human", "Active", "Awaiting your Command...", "@Dom#2774"])

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
    @Command(Prefix=True, Start="color")
    async def Change_Color(Context):
        message = Context.Message

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
    async def QuickChat(Context):
        message = Context.Message

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
            await channel.send(chat_function['use'])
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
    @Command(Prefix=True, Start="fullweather", NoSpace=True)
    async def OldWeather(Context):
        message = Context.Message
        forecast = forecastio.load_forecast(forecast_api_key, lat, lng)
        byHour = forecast.hourly()
        byCurrent = forecast.currently()
        byDaily = forecast.daily()
        response = Sys.Response(Conversation.WeatherResponse)
        msg = '```md\n# Weather Forcast for ' + place_name + ":"
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
            await Other.SendWeather(default_channel)

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
    @Command(Start="No Context", Prefix=True, NoSpace=True)
    async def NoContext(Context):
        message = Context.Message

        if Context.InDM:
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

        # Uses creation timestamp
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
    async def ChatLinkShorten(Context, command=False):
        """Scans chat for any mention of a link
        Sees how long it is, and offers to shorten it if need be.
        """
        message = Context.Message
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

        if message.content[0] in [";", '/', '-', '.']:
            return


        UsableContent = message.content.strip()
        Links = []

        # Now we need to find the link:
        ContentWords = UsableContent.replace("\n", " ").split(" ")
        for Word in ContentWords:
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
                if not await Helpers.Deleted(message) and not Context.InDM:
                    await message.remove_reaction(Conversation.Emoji["link"], Vars.Bot.user)
                return

            # Now that we know they wanted it shortened, our first order of business
            # is to delete the original
            if not Context.InDM:
                await message.delete()

        # Now it's time to format what the bot will send
        NewContent = message.content
        for link in Shortened_Links:
            To_Replace = Shortened_Links[link]["Short"] + " *(" + Shortened_Links[link]["Partial"] + ")* "
            NewContent = NewContent.replace(link, To_Replace)

        if Context.InDM:
            Color = 0xFFFFFF
        else:
            Color = message.author.color

        LinkSendEmbed = discord.Embed(description=NewContent, color=Color)
        LinkSendEmbed.set_author(name=message.author.name + "#" + message.author.discriminator, icon_url=message.author.avatar_url)
        LinkSendEmbed.set_footer(text="RedBot Link Shortener")

        await message.channel.send(embed=LinkSendEmbed)

    @staticmethod
    @Command(Start="shorten", Prefix=True)
    async def LinkShortenCommand(Context):
        """
        Shortens a given link using TinyUrl
        """
        Context.Message.content = Context.Message.content[8:].strip()
        await Other.ChatLinkShorten(Context, command=True)

    @staticmethod
    @Command(Start="Count", Prefix=True)
    async def CountMessages(Context):
        message = Context.Message

        stop_emoji = Conversation.Emoji["blue_book"]
        text = "I will count messages until I see a " + stop_emoji + " reaction. My limit is: `2500` messages."
        description = "Click the Check when you're ready!"

        if not await Interraction.Confirmation(Context.Channel, Context.Message.author, text=text, deny_text="Count cancelled", timeout=120,
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
    @Command(Start="weather", Prefix=True, NoSpace=True)
    async def Weather(Context):
        Other_Content = Context.StrippedContent[7:].strip()
        if Other_Content:
            HasLocation = True
            LatAndLong = await Helpers.TextToLatAndLong(Other_Content)

            if not LatAndLong:
                HasLocation = False
        else:
            HasLocation = False


        if HasLocation:
            await Other.SendWeather(Context.Message.channel, LatAndLong)
        else:
            await Other.SendWeather(Context.Message.channel)

    @staticmethod
    async def SendWeather(channel, location=[]):
        # Obtain Forecast Dataset
        if location:
            latitude = location[0]
            longitude = location[1]
            place_name = location[2]
            if len(place_name.split(",")) > 2:
                place_name = place_name.split(",")[0]
            icon = location[3]
        else:
            latitude = 42.538690
            longitude = -71.046564
            place_name = "Lynnfield, MA"
            icon = None
        forecast = forecastio.load_forecast(forecast_api_key, latitude, longitude)

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

        em = discord.Embed(description=msg, colour=0x498fff, timestamp=Helpers.EmbedTime())
        if icon:
            em.set_footer(text="Weather for " + place_name, icon_url=icon)
        else:
            em.set_footer(text="Weather for " + place_name)

        await channel.send(embed=em)

        return

    @staticmethod
    @Command(Prefix=True, Start="Upload", NoSpace=True)
    async def Upload(Context):
        message = Context.Message
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
    @Command(Prefix=False, Attachment=True)
    async def AutoUpload(Context):
        message = Context.Message

        suffixes = [".png", ".jpg", ".jpeg", ".gif", ".ico"]
        IsImage = False
        for suffix in suffixes:
            if message.attachments[0].url.lower().strip().endswith(suffix):
                IsImage = True
                break
        if not IsImage:
            return

        # So there's an attachment
        UploadEmoji = Conversation.Emoji["upload"]
        await message.add_reaction(UploadEmoji)

        def Check(reaction, user):
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
                    await Helpers.RemoveAllReactions(message)
                    return

        await Helpers.RemoveAllReactions(message)
        if await Helpers.Deleted(message):
            raise FileNotFoundError("I cannot find the message with the image. Was it deleted?")

        AttachmentUploaded = await Helpers.DownloadAndUpload(message, message.attachments[0], SendProgress=False)
        await message.channel.send("<" + AttachmentUploaded.link + ">")

    @staticmethod
    @Command(Start="UpdateNotes", Prefix=True, NoSpace=True)
    async def UpdateNotes(Context):
        message = Context.Message

        ColorListing = [ Sys.Colors["RedBot"],
                         Sys.Colors["GoldBot"],
                         0x27AE60,
                         0x5499C7,
                         0x9B59B6
        ]

        UpdateFull = Conversation.UpdateNotes
        while len(ColorListing) < len(UpdateFull) + 1:
            ColorListing = ColorListing + ColorListing


        em = discord.Embed(color=ColorListing[0], description="Here are all of my update notes for this version.")
        em.set_thumbnail(url=Vars.Bot.user.avatar_url)
        em.set_author(name="RedBot v" + Vars.Version, icon_url=Vars.Bot.user.avatar_url)
        await message.channel.send(embed=em)

        i = 0
        for Note in UpdateFull:
            i += 1
            em = discord.Embed(color=ColorListing[i], description=Note["Content"])
            em.set_author(name=Note["Name"], icon_url=Vars.Bot.user.avatar_url)

            await message.channel.send(embed=em)

    @staticmethod
    @Command(Start="SendFile", Prefix=True, Admin=True, NoSpace=True)
    async def SendFile(Context):
        await Context.Message.channel.trigger_typing()

        OriginalContent = Context.StrippedContent
        OriginalContent = OriginalContent[8:].strip()

        addpath = None
        OrigPath = os.getcwd()
        if OrigPath.startswith("C:"):  # Being ran on a windows machine
            Slash = "\\"
        elif OrigPath.startswith("/home"):
            Slash = "/"
        else:
            raise WindowsError("Cannot figure out what machine this is running on.")

        if OriginalContent.lower() == "data":
            addpath = Slash + "Data.txt"

        elif OriginalContent.lower() == "personal":
            addpath = Slash + "Personal.txt"

        if not addpath:
            await Context.Message.add_reaction(Conversation.Emoji["x"])
            await Context.Message.channel.send("Please specify what file you want! Files include: `data`")
            return

        newfile = discord.File(os.getcwd() + addpath)
        await Context.Message.channel.send(file=newfile)

    @staticmethod
    @Command(Start="NewFile", Prefix=True, Admin=True, NoSpace=True)
    async def NewFile(Context):
        # Ran to update a file
        await Context.Message.channel.trigger_typing()

        # Find out what file we're replacing
        OriginalContent = Context.StrippedContent
        OriginalContent = OriginalContent[8:].strip()

        # Now the goal is to find out what machine we're using
        addpath = None
        OrigPath = os.getcwd()
        if OrigPath.startswith("C:"):  # Being ran on a windows machine
            Slash = "\\"
        elif OrigPath.startswith("/home"):  # Being ran on RPI / Linux
            Slash = "/"
        else:
            raise WindowsError("Cannot figure out what machine this is running on.")

        # Now that we have that, we need to figure out what they're replacing (/NewFile data)
        if OriginalContent.lower() == "data":
            addpath = Slash + "Data.txt"

        elif OriginalContent.lower() == "personal":
            addpath = Slash + "Personal.txt"

        if not addpath:
            await Context.Message.add_reaction(Conversation.Emoji["x"])
            await Context.Message.channel.send("Please specify what file you want! Files include: `data`")
            return

        newfile = discord.File(os.getcwd() + addpath)
        newfilepath = os.getcwd() + addpath

        if not Context.Message.attachments:
            await Context.Message.add_reaction(Conversation.Emoji["x"])
            await Context.Message.channel.send("Please also attach a file to replace the given one with")
            return

        File = Context.Message.attachments[0]

        confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, "Are you absolutely you want to replace?", extra_text=os.getcwd() + addpath, deny_text="That's what I thought. Cancelled")

        if not confirmation:
            return

        await Context.Message.channel.trigger_typing()
        await Context.Message.channel.send("@RedBot" + addpath + " Replacement by " + Context.Message.author.name, file=newfile)
        await Vars.Creator.send("@RedBot" + addpath + " Replacement by " + Context.Message.author.name, file=newfile)

        await Context.Message.channel.trigger_typing()

        os.remove(newfilepath)
        await File.save(newfilepath)

        await Context.Message.channel.send("Successful Transfer of files. Restarting now.")
        await Admin.BotRestart("File Transfer Successful. Bot Restarted and running. New File accepted.", Context.Message.channel.id)


class Poll:
    RunningPolls = {}

    @staticmethod
    async def OnMessage(Context):
        await Poll.PollCommand(Context)
        await Poll.ListPolls(Context)

    @staticmethod
    @Command(Prefix=True, Start=["poll", "yesno"])
    async def PollCommand(Context):
        """
        /poll Which Emoji is cooler?
        :car: The car Emoji
        :No Car: No Car Emoji
        :param message: the input message
        :return: Nothing
        """
        message = Context.Message
        # if not await CheckMessage(message, prefix=True, start="poll"):
        #     if not await CheckMessage(message, prefix=True, start="yesno"):
        #         return

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

        if Context.InDM:
            await PollError(message, "Do you really want to do a Poll with yourself in a DM with a robot? \nThat's just sad.", sendFormat=False)
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
        await Helpers.RemoveAllReactions(PollMessage)

    @staticmethod
    async def OnReaction(reaction, user):
        # Ran from OnReaction in Main.py, whenever someone adds a reaction to something

        # First let's run some checks to ensure it's the message we're talking about
        if str(reaction.message.id) not in Poll.RunningPolls.keys():
            return

        PollData = Poll.RunningPolls[str(reaction.message.id)]


        PollMessage = await Helpers.GetMsg(PollData["SentID"], PollData["ChannelID"])

        if reaction.message.id != int(PollData["SentID"]):
            return

        # If it got an emoji in the list, or stop, continue on
        stop_emoji = Conversation.Emoji["stop"]
        if reaction.emoji == stop_emoji:
            if user.id == Vars.Creator.id or int(user.id) == int(PollData["MessageAuthorID"]):

                await Poll.FormatDescription(PollData, PollMessage.reactions, TitleAdd="Closed - ", Color=0x36393e)
                PollMessage = await Helpers.ReGet(PollMessage)

                await PollMessage.clear_reactions()

                await Poll.StopPollRunning(str(PollMessage.id))
                return

        if reaction.emoji not in PollData["EmojiList"]:
            await reaction.message.remove_reaction(reaction.emoji, user)


        # Now let's deal with the ugly reaction bit
        AllMessageReactions = reaction.message.reactions  # Gets all the reactions on the message sorted by emoji

        for IndividualReaction in AllMessageReactions:
            # If the emoji we're looking at is different from the one the user clicked:
            if IndividualReaction.emoji != reaction.emoji:
                # Var people is a list of everyone who voted for it
                people = await IndividualReaction.users().flatten()

                if user in people:
                    await reaction.message.remove_reaction(IndividualReaction.emoji, user)

    @staticmethod
    @Command(Prefix=True, Start="Polls")
    async def ListPolls(Context):
        pass


class Calculate:
    @staticmethod
    async def OnMessage(Context):
        await Calculate.CalcCommand(Context)

        return

    @staticmethod
    @Command(Prefix="=")
    async def CalcCommand(Context):
        message = Context.Message

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
    embed_color = 0x41f4bb
    ReservedTags = ["list", "help", "delete", "edit", "info", "random"]

    @staticmethod
    async def OnMessage(Context):
        await Tag.SetTag(Context)
        await Tag.TagFunction(Context)
        #await Tag.ClearTagData(Context)

        return

    @staticmethod
    async def FormatEmbed(TagDict, Context):
        if TagDict["Personal"]:
            IsPersonalTag = True
        else:
            IsPersonalTag = False

        TagKey = TagDict["Key"]

        # Now, we have the correct tag dict. Time to format the embed and send it.
        TagType = Context.Message.author.name + "'s Personal Tag" if IsPersonalTag else Context.Message.guild.name + "'s Server Tag"
        TagColor = await Tag.GetTagColor(Context, IsPersonalTag)
        TagImage = Context.Message.author.avatar_url if IsPersonalTag else Context.Message.guild.icon_url

        if TagDict["Color"]:
            TagColor = TagDict["Color"]

        TagTypeAdd = ": " + Sys.FirstCap(TagKey) if IsPersonalTag else "  >> /Tag " + Sys.FirstCap(TagKey)

        TagSendEmbed = discord.Embed(description=TagDict["Content"], color=TagColor)
        TagSendEmbed.set_footer(text=TagType + TagTypeAdd, icon_url=TagImage)

        if TagDict["Image"]:
            TagSendEmbed.set_image(url=TagDict["Image"])

        return TagSendEmbed

    @staticmethod
    @Command(Prefix=True, Start=["t", "tag", "pt", "ptag"])
    async def TagFunction(Context):
        """
        The function when someone wants to call a Tag
        :param Context:  The ContextMessage object of the message sent
        :return: None
        """
        async def ReturnError(ErrorStr, SendFormat=False):
            # If there is some issue, this will make things easier.
            Color = await Tag.GetTagColor(Context, IsPersonalTag)

            em = discord.Embed(color=Color, description=ErrorStr)
            em.set_author(name="Something Went Wrong.", icon_url=Vars.Bot.user.avatar_url)
            em.set_footer(text="For help creating and using Tags, perform \"/help Tag\"")

            await Context.Message.add_reaction(Conversation.Emoji["x"])
            await Context.Channel.send(embed=em)
            return

        IsPersonalTag = False
        if Context.StrippedContent.startswith(("pt ", "ptag")):
            IsPersonalTag = True
        elif Context.InDM:
            IsPersonalTag = True

        # Find TagKey
        SplitContentParts = Context.Message.content.split(" ")
        if len(SplitContentParts) == 1:
            # If there is no key in the tag, it's wrong.
            await ReturnError("Seems you forgot a key... ```css\n/tag {key}   # To call a Server Tag"
                              "\n/ptag {key}  # To call a Personal Tag```")
            return
        TagKey = SplitContentParts[1:]
        TagKey = " ".join(TagKey)

        # Return error if there's no TagKey
        if not TagKey:
            await Help.InternalHelp(Context.Channel, type="tag")
            return

        # If it's a system function, run the function and return
        TagKey = TagKey.lower().strip()
        if TagKey.split(" ")[0] in Tag.ReservedTags:
            await Tag.Reserve(TagKey, Context, IsPersonalTag)
            return

        # Set up LocationID and then retrieve the tag
        AuthorID = Context.Message.author.id
        if Context.InDM:
            GuildID = AuthorID
        else:
            GuildID = Context.Message.guild.id

        TagDict = await Tag.GetTag(TagKey, IsPersonalTag, AuthorID, GuildID)

        if not TagDict:  # If there's no tag found
            await Tag.NoTagFound(TagKey, Context, IsPersonalTag)
            return

        TagSendEmbed = await Tag.FormatEmbed(TagDict, Context)

        await Context.Channel.send(embed=TagSendEmbed)
        return

    @staticmethod
    async def GetTagColor(Context, IsPersonalTag):
        if Context.InDM:
            return 0xFFFFFF

        if IsPersonalTag:
            # If it's a personal tag, choose one:
            return Context.Message.author.color
        else:
            return Tag.embed_color

    @staticmethod
    async def NoTagFound(TagKey, Context, IsPersonalTag):
        if IsPersonalTag:
            AllTagData = await Tag.GetPersonalTagList(ID=Context.Message.author.id)
        else:
            AllTagData = await Tag.GetGuildTagList(ID=Context.Message.guild.id)

        DidYouMean = await Tag.DidYouMean(TagKey, AllTagData)

        ListCommand = "/PTag List" if IsPersonalTag else "/Tag List"
        TagType = "Personal" if IsPersonalTag else "Server"

        DidYouMean += "\n\nType `" + ListCommand + "` to view all " + TagType + " Tags."

        OtherTag = ""

        # If there's a tag by that name in the other data list, check
        if IsPersonalTag and not Context.InDM:
            GuildTagData = await Tag.GetGuildTagList(ID=Context.Message.guild.id)
            if TagKey in list(GuildTagData.keys()):
                OtherTag = "\n" + Sys.FirstCap(Context.Message.guild.name) + " has a Server Tag named " + TagKey
        elif Context.InDM:
            OtherTag = ""
        else:
            PersonalTagData = await Tag.GetPersonalTagList(ID=Context.Message.author.id)
            if TagKey in list(PersonalTagData.keys()):
                OtherTag = "\nYou have a Personal Tag named " + TagKey

        Color = await Tag.GetTagColor(Context, IsPersonalTag)

        NoTag_Embed = discord.Embed(description=DidYouMean.strip() + OtherTag, color=Color)
        NoTag_Embed.set_author(name="No " + TagType + " Tag found with the key: `" + Sys.FirstCap(TagKey) + "`")

        if IsPersonalTag:
            NoTag_Embed.set_footer(text=Context.Message.author.name + "'s Personal Tag: Cannot find.",
                                   icon_url=Context.Message.author.avatar_url)

        else:
            NoTag_Embed.set_footer(text=Context.Message.guild.name + "'s Server Tag: Cannot find.",
                                   icon_url=Context.Message.guild.icon_url)

        await Context.Channel.send(embed=NoTag_Embed)
        if not await Context.IsDeleted():
            # If the message is not deleted, add an X
            await Context.Message.add_reaction(Conversation.Emoji['x'])
        return

    @staticmethod
    async def GetTag(TagKey, IsPersonalTag, AuthorID, GuildID):
        """
        Runs internally and returns the Tag Object
        :param TagKey:          The Key of the Tag
        :param IsPersonalTag:   True/False
        :param LocationID:      The GuildID or PersonalID
        :return:               (True/False, TagObject)
        """

        AllGuildTagsList = await Tag.GetGuildTagList(ID=GuildID)
        AllPersonalTagsList = await Tag.GetPersonalTagList(ID=AuthorID)

        # Look to see if there's a Guild Tag
        InGuildTagsList = None
        if TagKey in AllGuildTagsList:
            # If the Key is in the GuildTags:
            InGuildTagsList = AllGuildTagsList[TagKey]

        # Look to see if there's a PersonalTag
        InPersonalTagsList = None
        if TagKey in AllPersonalTagsList:
            # If the Key is in the GuildTags:
            InPersonalTagsList = AllPersonalTagsList[TagKey]

        if IsPersonalTag:
            # If it's a Personal Tag, check to see if it's in the GuildTag list
            if InPersonalTagsList:
                return InPersonalTagsList
            else:  # If it's not a
                return {}

        else:
            # If it's a Guild tag
            if InGuildTagsList:
                return InGuildTagsList
            elif InPersonalTagsList:
                return InPersonalTagsList
            else:
                return {}

    @staticmethod
    async def DidYouMean(TagKey, TagDict):
        # Returns a string of "Did you mean: " after a tag doens't work.
        # Takes in a dictionary
        TagNameList = list(TagDict.keys())

        # Okay so we want to score each tag in the list by similarity to the Key
        SimilarDict = {}

        for item in TagNameList:
            item = item.lower().strip()

            # If the key is in the item, the score is the length minus the nonlength
            if TagKey in item:
                Difference = len(item) - len(TagKey)
                Average = (len(item) + len(TagKey)) / 2
                Score = abs(Difference) / Average
                Score = 1 / Score
                SimilarDict[item] = Score + 4
                continue

            # Go through each letter to see how similar it is
            Score = 0
            Limit = len(TagKey) if len(TagKey) < len(item) else len(item)
            for i in range(0, Limit - 1):
                if TagKey[i] == item[i]:
                    Score += 1

            SimilarDict[item] = Score

        SortedTupleList = sorted(SimilarDict.items(), key=lambda x: x[1])
        SortedTupleList.reverse()  # Now it is the biggest one first

        AddToDidYouMean = []  # Will house all of the words that we want to ask the user if they wanted

        # Now we iterate through each one in the SortedTupleList
        PreviousScore = None
        for WordScore in SortedTupleList:
            if WordScore[1] == 0:
                # If the score is zero, break, since we know that everything after is less than or equal to 0
                break
            elif WordScore[1] <= 1 and len(AddToDidYouMean) > 1:
                # If the score is already 1 and there's at least one word in there, break
                break
            elif WordScore[1] <= 2 and len(AddToDidYouMean) <= 1:
                break

            if PreviousScore:
                # If there was a previous score, break if this score is less than 33% of that
                Cutoff = 0.33 * PreviousScore

                if WordScore[1] <= Cutoff:  # If the score is less than the cutoff, break
                    break
            # If we're this far, it's good to add
            AddToDidYouMean.append(WordScore[0])
            PreviousScore = WordScore[1]

        # So now we should have a DidYouMean list.
        # If not, return nothing
        if not AddToDidYouMean:
            return ""

        # Capitalize each value of AddToDidYouMean
        FinalAddToDidYouMean = []
        for word in AddToDidYouMean:
            FinalAddToDidYouMean.append("`" + Sys.FirstCap(word)+ "`")

        DidYouMeanString = "**Did You Mean: **" + ",  ".join(FinalAddToDidYouMean) + "  ?"

        return DidYouMeanString

    @staticmethod
    async def GetGuildTagList(ID=None):
        """
        Returns the list of all Guild Tags with a given ID
        :param ID: The int (or str)
        :return:   Dict of the tags, either all tags within a guild or all tags total
        """
        AllPublicTagsDict = Helpers.RetrieveData(type="Tag")

        if not AllPublicTagsDict:
            # If there are no saved Public tags, return {}
            return {}

        elif not ID:
            # If they don't want any specific guild
            return AllPublicTagsDict

        elif str(ID) in AllPublicTagsDict.keys():
            # If the guild is registered
            return AllPublicTagsDict[ str(ID) ]

        else:
            # If the guild isn't in the AllPublicTagsDict, return nothing
            return {}

    @staticmethod
    async def GetPersonalTagList(ID=None):
        """
        Return the list of all Personal Tags for the given person
        :param ID: the int (or str)
        :return:   The Dict of all of the Personal Tags
        """
        AllPersonalTagsDict = Helpers.RetrieveData(type="PTag")

        if not AllPersonalTagsDict:
            # If there are no PTags, return {}
            return {}

        elif not ID:
            # If they don't want any specific person
            return AllPersonalTagsDict

        elif str(ID) in AllPersonalTagsDict.keys():
            # If the person does have personal tags registered
            return AllPersonalTagsDict[ str(ID) ]

        else:
            # If the person has no tags registered
            return {}

    @staticmethod
    @Command(Prefix=True, Start=["settag", "st", "setptag", "spt", "psettag", "ptagset"])
    async def SetTag(Context):
        """
        Creates a Tag
        :param Context: The Cmd.ContextMessage object that's passed into it
        :return:        None, hopefully :)
        """
        async def ReturnError(ErrorStr, SendFormat=False):
            # If there is some issue, this will make things easier.
            if SendFormat:
                format = "\n\nTry following the format:\n" \
                         "**Setting a Server-Wide Tag:**" \
                         "```py\n>> /settag Bot-Color 0xFFFFFFF  # Create a tag of the bots color within a guild"\
                         "\n>> /settag Class-Schedule <attach image to message>  # Add an Image to an Embed" \
                         "\n>> /settag Band-Twitter https://www.twitter.com/[...]  # Add a link to be shortened```" \
                         "**Setting a Personal Tag:**" \
                         "```py\n>> /psettag access-code-discord OU812 I814U  # Create a personal tag with personal details" \
                         "\n# Only you can access Personal Tags```"
            else:
                format = ""

            Color = await Tag.GetTagColor(Context, IsPersonalTag)

            em = discord.Embed(color=Color, description=ErrorStr + format)
            em.set_author(name="SetTag Error", icon_url=Vars.Bot.user.avatar_url)
            em.set_footer(text="For help creating and using Tags, perform \"/help Tag\"")

            await Context.Message.add_reaction(Conversation.Emoji["x"])
            await Context.Channel.send(embed=em)

            return

        IsPersonalTag = False

        if Context.StrippedContent.startswith(("setptag", "spt", "psettag", "ptagset")):
            # If the Message starts with any of those, it's a personal tag
            IsPersonalTag = True

        elif Context.InDM:
            # If it's in a Direct Messages channel, it's a Personal Tag
            IsPersonalTag = True

        Split_Content_Segments = Context.Message.content.split(" ")  # The concent of the message split by sentence

        # The 3 horsemen of the apocolapse:
        TagKey      = ""
        TagContent  = ""
        TagImageUrl = ""

        # So the second item in Split_Content_Segments is the key
        if len(Split_Content_Segments) < 2:
            # If there's less than 2 items in the Split_Content_Segments, ["/settag", "key", "content"]
            await ReturnError("Remember to follow the format!", SendFormat=True); return

        # KEY
        TagKey = Split_Content_Segments[1]
        TagKey = TagKey.replace("-", " ").replace("_", " ").lower()

        # CONTENT
        if len(Split_Content_Segments) >= 2:
            # No content following in the tag
            Total_Content_Segments = Split_Content_Segments[2:]
            TagContent = " ".join(Total_Content_Segments)

            TagContent = await Helpers.ShortenTextInLink(TagContent)

        # IMAGE
        if Context.Message.attachments:
            # Add image to the Tag Content
            AttachmentUploaded = await Helpers.DownloadAndUpload(Context.Message, Context.Message.attachments[0])
            if AttachmentUploaded:
                TagImageUrl = AttachmentUploaded.link

        # Check the Tag
        if IsPersonalTag or Context.InDM:
            AlreadyGivenTagDict = await Tag.GetPersonalTagList(ID=Context.Message.author.id)
        else:
            AlreadyGivenTagDict = await Tag.GetGuildTagList(ID=Context.Message.guild.id)
        Response = await Tag.CheckPotentialTag(TagKey, TagContent, TagImageUrl, AlreadyGivenTagDict)

        if Response:  # If there's an error, let's format the error and then send it out
            Type_Replacement = "Personal Tag" if IsPersonalTag else "Server Tag"
            Cmd_Replacement  = "ptag" if IsPersonalTag else "tag"
            Response = Response.replace("{Type}", Type_Replacement).replace("{TagCommand}", Cmd_Replacement)
            await ReturnError(Response, SendFormat=True)
            return

        # Tag is good to go! Let's confirm it
        TagCommand = "/ptag" if IsPersonalTag else "/tag"
        TagType = "Personal Tag" if IsPersonalTag else "Server Tag"

        YouSayISay = "```You Send:  >> " + TagCommand + " " + TagKey
        YouSayISay += "\nI Respond: >> " + TagContent
        YouSayISay += " {+Attachment:}```" if TagImageUrl else "```"

        Color = await Tag.GetTagColor(Context, IsPersonalTag)

        ConfirmationEmbed = discord.Embed(title="Create " + TagType + "?", description=YouSayISay, color=Color,
                                          timestamp=Helpers.EmbedTime())
        if IsPersonalTag:
            ConfirmationEmbed.set_author(name=Context.Message.author.name + "#" + Context.Message.author.discriminator,
                                         icon_url=Context.Message.author.avatar_url)
            ConfirmationEmbed.set_footer(text="This will only be callable by you. 60 second Timeout.")
        else:
            ConfirmationEmbed.set_author(name=Context.Message.guild.name + " Tag",
                                         icon_url=Context.Message.guild.icon_url)
            ConfirmationEmbed.set_footer(text="Everyone in this server can call this tag here. 60 second Timeout.")

        if TagImageUrl:
            ConfirmationEmbed.set_image(url=TagImageUrl)

        # Let's see if there's a response
        response = await Interraction.Confirmation(Context.Channel, Context.Message.author, "", Embed=ConfirmationEmbed,
                                              deny_text="Okay, I cancelled the tag.", originalctx=Context, mention=Context.Message.author,
                                              Outside_Text="Does this all look correct?", add_reaction=False)

        if not response:
            # If it timed out or wasn't liked, return
            return

        # Next let's see if the creator is a guild administrator
        IsGuildAdmin = False
        if Context.InDM:  # If it's a DM channel
            IsGuildAdmin = True
        elif Context.IsAdmin:  # If the user is known to RedBot as an admin
            IsGuildAdmin = True
        else:  # Check guild to see if the user has a few permissions
            Guild_Permissions = Context.Message.author.guild_permissions
            IsGuildAdmin = Guild_Permissions.manage_guild or Guild_Permissions.administrator

        IsGuildAdmin = True  # TODO REMOVE

        if not IsGuildAdmin and not IsPersonalTag:
            # If it's not a personal tag and if the creator isn't an admin, create a vote
            # Let's make a slight change to our embed
            VoteEmbed = ConfirmationEmbed
            VoteEmbed.title = "Tag Vote: Should this be a Server Tag?"
            VoteEmbed.color = await Tag.GetTagColor(Context, IsPersonalTag)
            VoteEmbed.set_footer(text="Add a reaction to vote. Anyone here can call the tag. 10 minute Timeout.")

            # Send VoteMsg
            VoteMsg = await Context.Channel.send("**Public Vote**: You need _3_ votes to save the tag", embed=VoteEmbed)

            # Establish TagEmoji
            TagEmoji = Conversation.Emoji["tag"]
            await VoteMsg.add_reaction(TagEmoji)

            # Wait for 4 reactions
            NecessaryVotes = await Helpers.WaitForReaction(reaction_emoji=TagEmoji, message=VoteMsg, timeout=610,
                             emoji_num=3, remove_wrong=True)

            await Helpers.QuietDelete(VoteMsg)

            if not NecessaryVotes:
                await Context.Channel.send("Timed out without enough votes. Cancelled.", delete_after=20)
                await Context.Message.add_reaction(Conversation.Emoji["x"])
                return

        # If we've gotten this far, it's good to save! Let's use a function built for this
        SaveID = Context.Message.author.id if IsPersonalTag else Context.Message.guild.id
        await Tag.SaveTag(TagKey, TagContent, TagImageUrl, SaveID, IsPersonalTag, Context)

        await Context.Message.add_reaction(Conversation.Emoji["check"])

        # SuccessEmbed
        SuccessEmbed = ConfirmationEmbed
        SuccessEmbed.title = "Successfully saved Tag"
        SuccessEmbed.color = await Tag.GetTagColor(Context, IsPersonalTag)


        footer_text = "This Tag will be only callable by " + Context.Message.author.name if IsPersonalTag else "Everyone in the server can call this."
        SuccessEmbed.set_footer(text=footer_text)

        await Context.Channel.send(embed=SuccessEmbed)

        return

    @staticmethod
    async def CheckPotentialTag(TagKey, TagContent, TagImageUrl, AlreadyGivenTagDict, DoNotCheck=[]):
        """
        Takes in 3 objects to check all of the things in the Tag to double check everything
        :param TagKey:      The Key of the tag
        :param TagContent:  The Text Content of the Tag  (Maybe None)
        :param TagImage:    An image  (Maybe None)
        :return             None if it checks out, or gives a String if it's wrong
        """

        ErrorMessage = ""

        # Let's start performing some checks!
        if TagKey in AlreadyGivenTagDict.keys():
            ErrorMessage = "{Type} Key already in use!\nPerform the following to see the key: " \
                           "```/{TagCommand} " + TagKey + "```" \
                                                          "To edit or delete that tag, do this command:" \
                                                          "```/{TagCommand} edit " + TagKey + "```"
            if "key" in DoNotCheck:
                ErrorMessage = ""

        elif len(TagKey.split(" ")) >= 8:
            ErrorMessage = "Key is too long! Max of 150 characters and 8 words or less." \
                           "\nViolation: " + str(len(TagKey.split(" "))) + " words, 8 max."

        elif len(TagKey) > 150:
            ErrorMessage = "Key is too long! Max of 150 characters and 8 words or less." \
                           "\nViolation: " + str(len(TagKey)) + " characters, 150 max."

        elif len(TagKey) < 3:
            ErrorMessage = "Key is far too short! Minimum of 3 characters." \
                           "\nViolation: " + str(len(TagKey)) + " characters, 3 min."

        elif len(TagContent) > 1000:
            ErrorMessage = "Tag Content is too long." \
                           "\nViolation: " + str(len(TagContent)) + " characters, 1000 max. Remember that Discord can only send 1000 characters at once  :)"

        elif not TagContent and not TagImageUrl:
            ErrorMessage = "You need to add either an image or text content!"

        elif TagKey in Tag.ReservedTags:
            ErrorMessage = "TagKey \"`" + TagKey + "`\" reserved for system function."

        return ErrorMessage

    @staticmethod
    async def SaveTag(TagKey, TagContent, TagImageUrl, ID, IsPersonalTag, Context):
        if not TagImageUrl:
            TagImageUrl = None

        if IsPersonalTag:
            GuildID = None
        else:
            GuildID = Context.Message.guild.id

        NewTagDict = {
            "Key": TagKey,
            "Content": TagContent,
            "Creator": Context.Message.author.id,
            "Guild": GuildID,
            "Channel": Context.Channel.id,
            "Time": (datetime.now() + timedelta(hours=3)).timestamp(),
            "Admin": False,
            "Image": TagImageUrl,
            "Personal": IsPersonalTag,
            "Color": None
        }
        # Now it adds it to the correct section, or creates it
        if IsPersonalTag:
            AllPersonalTagData = await Tag.GetPersonalTagList()
            if str(ID) in AllPersonalTagData.keys():
                # If the person already has some personal tags registered, add it in
                AllPersonalTagData[str(ID)][TagKey] = NewTagDict
            else:
                # Otherwise create a section for the person with this tag
                AllPersonalTagData[str(ID)] = {TagKey: NewTagDict}

            Helpers.SaveData(AllPersonalTagData, type="PTag")

        else:
            AllGuildTagData = await Tag.GetGuildTagList()
            if str(ID) in AllGuildTagData.keys():
                # If the person already has some personal tags registered, add it in
                AllGuildTagData[str(ID)][TagKey] = NewTagDict
            else:
                # Otherwise create a section for the person with this tag
                AllGuildTagData[str(ID)] = {TagKey: NewTagDict}

            Helpers.SaveData(AllGuildTagData, type="Tag")

        return True

    @staticmethod
    async def Reserve(TagKey, Context, IsPersonalTag):
        # ["list", "help", "delete", "edit", "info", "random"]
        if Context.InDM:
            IsPersonalTag = True

        # Go through the functions and choose one
        if TagKey == "list":
            await Tag.Reserve_List(TagKey, Context, IsPersonalTag)
            return

        elif TagKey.split(" ")[0] == ("delete"):
            await Tag.Reserve_Delete(TagKey, Context, IsPersonalTag)
            return

        elif TagKey == "random":
            await Tag.Reserve_Random(TagKey, Context, IsPersonalTag)
            return

        elif TagKey.split(" ")[0] == ("info"):
            await Tag.Reserve_Info(TagKey, Context, IsPersonalTag)
            return

        elif TagKey.split(" ")[0] == ("edit"):
            await Tag.EditTag(TagKey, Context, IsPersonalTag)

    @staticmethod
    async def Reserve_List(TagKey, Context, IsPersonalTag):
        # Called from Tag.Reserve, which is called from Tag.TagFunction
        if IsPersonalTag:
            AllTagData = await Tag.GetPersonalTagList(ID=Context.Message.author.id)
        elif Context.InDM:
            AllTagData = await Tag.GetPersonalTagList(ID=Context.Message.author.id)
            IsPersonalTag = True
        else:
            AllTagData = await Tag.GetGuildTagList(ID=Context.Message.guild.id)

        TagKeyList = list(AllTagData.keys())
        TagKeyList.sort()

        NewTagKeyList = []

        for i in range(0, len(TagKeyList)):
            Add = "`" + str(i+1) + ".  `  " + Sys.FirstCap(TagKeyList[i])
            if AllTagData[TagKeyList[i]]["Image"]:
                Add += "  *+[Image]*"
            NewTagKeyList.append(Add)

        Title = Context.Message.author.name + "\'s Personal Tag List" if IsPersonalTag else Context.Message.guild.name + " Server Tag List"
        Color = await Tag.GetTagColor(Context, IsPersonalTag)
        Icon = Context.Message.author.avatar_url if IsPersonalTag else Context.Message.guild.icon_url

        if not NewTagKeyList:
            NoTagsMsg = "You have no saved tags :(\nDo `/setPtag {key} {content} {+image}` to create one" if IsPersonalTag else \
                Context.Message.guild.name + " has no saved tags :(\nDo `/settag {key} {content} {+image}` to create one"
            em = discord.Embed(description=NoTagsMsg, color=Color)
            em.set_footer(icon_url=Icon, text=Title)
            await Context.Channel.send(embed=em)
            return


        await Interraction.ListStrings(Context.Channel, NewTagKeyList, Title, Color=Color, Author_Image=Icon)
        return

    @staticmethod
    async def Reserve_Delete(TagKey, Context, IsPersonalTag):
        # Deletes a Tag
        async def RaiseError(Error):
            Color = await Tag.GetTagColor(Context, IsPersonalTag)

            em = discord.Embed(color=Color,
                               description=Error)
            em.set_author(name="Tag Deletion Error", icon_url=Vars.Bot.user.avatar_url)
            em.set_footer(text="For help deleting and using tags, perform \"/help Tag\"")

            await Context.Message.add_reaction(Conversation.Emoji["x"])
            await Context.Channel.send(embed=em)
            return

        if IsPersonalTag:
            TagType = "your Personal Tag"
        else:
            TagType = "the Server Tag"

        if not " " in TagKey:
            await RaiseError("Format: /tag delete (key)\nFor Personal Tags: /ptag delete (key)")
            return

        TagKey = " ".join(TagKey.split(" ")[1:])

        # Let's verify we can get the key:
        TagData = await Tag.GetTag(TagKey, IsPersonalTag, Context.Message.author.id, Context.Message.guild.id)
        if not TagData:
            TagDict = await Tag.RetrievePTagList(id=Context.Message.author.id) if IsPersonalTag else \
                await Tag.RetrieveTagList(GuildID=Context.Message.guild.id)
            DidYouMean = await Tag.DidYouMean(TagKey, TagDict)
            await RaiseError("Tag key not found!\n" + DidYouMean)
            return

        if TagData["Personal"]:
            IsPersonalTag = True

        Color = await Tag.GetTagColor(Context, IsPersonalTag)


        if not await Interraction.Confirmation(Context.Channel, Context.Message.author, "Delete " + TagType + ": " + TagKey + " ",
                                               deny_text="Tag Re-Saved.",color=Color):
            return

        if IsPersonalTag:
            AllPersonalTagData = await Tag.GetPersonalTagList()
            AllPersonalTagData[str(Context.Message.author.id)].pop(TagKey)
            Helpers.SaveData(AllPersonalTagData, type="PTag")

        Success_Em = discord.Embed(color=Color, description="Sucessfully deleted " + TagType + " *" + TagKey + "* from my database.")
        Success_Em.set_author(name=TagType + " Deletion")
        await Context.Channel.send(embed=Success_Em)
        await Context.Message.add_reaction(Conversation.Emoji["check"])
        return

    @staticmethod
    async def Reserve_Random(TagKey, Context, IsPersonalTag):
        if IsPersonalTag:
            AllTagData = await Tag.GetPersonalTagList(ID=Context.Message.author.id)
        else:
            AllTagData = await Tag.GetGuildTagList(ID=Context.Message.guild.id)

        # Now let's randomly choose one

        ChosenTagKey = random.choice(list( AllTagData.keys() ))
        ChosenTagDict = AllTagData[ChosenTagKey]

        TagEmbed = await Tag.FormatEmbed(ChosenTagDict, Context)

        await Context.Channel.send(embed=TagEmbed)

    @staticmethod
    async def Reserve_Info(TagKey, Context, IsPersonalTag):

        async def RaiseError(Error):
            Color = await Tag.GetTagColor(Context, IsPersonalTag)

            em = discord.Embed(color=Color,
                               description=Error)
            em.set_author(name="Tag Info Error", icon_url=Vars.Bot.user.avatar_url)
            em.set_footer(text="For help deleting and using tags, perform \"/help Tag\"")

            await Context.Message.add_reaction(Conversation.Emoji["x"])
            await Context.Channel.send(embed=em)
            return

        Color = await Tag.GetTagColor(Context, IsPersonalTag)

        TagKey = " ".join(TagKey.split(" ")[1:]).strip().lower()

        if not TagKey:
            await RaiseError("Please specify which tag you'd like the info for. ```>> "
                       "/tag info {key}\n>> /ptag info {key}```")
            return

        AuthorID = Context.Message.author.id
        GuildID = AuthorID if Context.InDM else Context.Message.guild.id

        TagData = await Tag.GetTag(TagKey, IsPersonalTag, AuthorID, GuildID)

        if not TagData:
            await Tag.NoTagFound(TagKey, Context, IsPersonalTag)
            return

        if TagData["Personal"]:  IsPersonalTag = True

        SendMsg = "Key: " + TagData["Key"]
        SendMsg += "\nContent: " + TagData["Content"]
        SendMsg += "\nCreator: " + Vars.Bot.get_user(TagData["Creator"]).name + " (" + str(TagData["Creator"]) + ")"
        SendMsg += "\nGuild: " + Vars.Bot.get_guild(TagData["Guild"]).name + " (" + str(TagData["Guild"]) + ")"
        SendMsg += "\nTime: " + str(datetime.fromtimestamp(TagData["Time"]))
        SendMsg += "\nImage: " + str(TagData["Image"])
        SendMsg += "\nColor: " + str(TagData["Color"])


        Footer = Context.Message.author.name + "\'s Personal Tag: " + TagKey if IsPersonalTag \
            else Context.Message.guild.name + "'s Server Tag >> /tag " + TagKey
        Image = Context.Message.author.avatar_url if IsPersonalTag else Context.Message.guild.icon_url
        Title = "Personal Tag Information: " + TagKey if IsPersonalTag else "Server Tag Information: " + TagKey

        em = discord.Embed(color=await Tag.GetTagColor(Context, IsPersonalTag), description=SendMsg)
        em.set_footer(text=Footer, icon_url=Image)
        em.set_author(name=Title)

        await Context.Channel.send(embed=em)

    @staticmethod
    async def EditTag(TagKey, Context, IsPersonalTag):
        message = Context.Message
        StrGuildID = str(Context.Message.guild.id)

        TagKey = TagKey.replace("edit", "").strip()

        async def SaveData(AllTagData, NewTagData, IsPersonalTag):
            AllTagData[NewTagData["Key"]] = NewTagData
            if IsPersonalTag:
                AllTagData[NewTagData["Key"]] = NewTagData
                IsPersonalTagData = await Tag.RetrievePTagList()
                IsPersonalTagData[str(message.author.id)] = AllTagData
                Helpers.SaveData(PersonalTagData, type="PTag")
                return
            elif not IsPersonalTag:
                # Okay so first we need to check if the Data is ready to go
                AllGuildTagData = await Tag.RetrieveTagList()
                AllGuildTagData[StrGuildID] = AllTagData

                Helpers.SaveData(AllGuildTagData, type="Tag")
            return

        async def SendMessage(text, title=None):
            Color = await Tag.GetTagColor(Context, IsPersonalTag)

            Footer = "Editing "
            Footer += Context.Message.author.name + "\'s Personal Tag: " + TagKey if IsPersonalTag \
                else Context.Message.guild.name + "'s Server Tag >> /tag " + TagKey
            Image = Context.Message.author.avatar_url if IsPersonalTag else Context.Message.guild.icon_url

            em = discord.Embed(color=Color, description=text)
            em.set_footer(text="Tag Edit: " + Footer, icon_url=Image)
            if title:
                em.set_author(name=Title)

            sentmsg = await Context.Channel.send(embed=em)
            return sentmsg

        if not IsPersonalTag:
            if Context.Message.author.id not in Ranks.Admins:
                return

        if not TagKey:
            await SendMessage("Please Specify which Tag you'd like to edit: ```"
                              ">> /tag edit {key}\n>>/ptag edit {key}")
            return

        AuthorID = Context.Message.author.id
        GuildID = AuthorID if IsPersonalTag else Context.Message.guild.id

        TagData = await Tag.GetTag(TagKey, IsPersonalTag, AuthorID, GuildID)
        if not TagData:
            await Tag.NoTagFound(TagKey, Context, IsPersonalTag)
            return

        if TagData["Personal"]:
            IsPersonalTag = True

        if IsPersonalTag:
            AllTagData = await Tag.GetPersonalTagList(ID=Context.Message.author.id)
            TagType = "Personal Tag"
        else:
            AllTagData = await Tag.GetGuildTagList(ID=Context.Message.guild.id)
            TagType = "Server Tag"

        # Prepare Dialogue asking what action they wish to do

        OptOne = {"Option": "Change Tag Key", "Emoji": Conversation.Emoji["key"]}
        OptTwo = {"Option": "Change Tag Content", "Emoji": Conversation.Emoji['notepad']}
        OptThree = {"Option": "Change Tag Image", "Emoji": Conversation.Emoji['camera']}
        OptFour = {"Option": "Change Tag Color", "Emoji": Conversation.Emoji['paintbrush']}
        OptFive = {"Option": "Delete Tag", "Emoji": Conversation.Emoji['trash']}

        Color = await Tag.GetTagColor(Context, IsPersonalTag)

        Response = await Interraction.UserChoice(Context.Channel, Context.Message.author,
                                                 "Edit " + TagType + ": " + TagKey,
                                                 Choices=[OptOne, OptTwo, OptThree, OptFour, OptFive],
                                                 Color=Color, timeout=60,
                                                 title="Choose the option of the action you'd like to do",
                                                 Show_Cancel=True)

        if Response == None:
            await SendMessage("Tag Edit Timed Out.")
            return
        elif Response == "Cancel":
            return


        # Now we find which they chose
        if Response == OptOne["Option"]:
            EditMode = "Key"
        if Response == OptTwo["Option"]:
            EditMode = "Content"
        if Response == OptThree["Option"]:
            EditMode = "Image"
        if Response == OptFour["Option"]:
            EditMode = "Color"
        if Response == OptFive["Option"]:
            EditMode = "Delete"

        # Delete tag if requested
        if EditMode == "Delete":
            if not await Interraction.Confirmation(Context.Channel, Context.Message.author,
                                                   "Delete " + TagType + ": " + TagKey, color=Color):
                return
            AllTagData.pop(TagKey)

            if IsPersonalTag:
                AllPersonalTagData = await Tag.GetPersonalTagList()
                AllPersonalTagData[str(Context.Message.author.id)].pop(TagKey)
                Helpers.SaveData(AllPersonalTagData, type="PTag")

            else:
                AllGuildTagData = await Tag.GetGuildTagList()
                AllGuildTagData[str(Context.Message.guild.id)].pop(TagKey)
                Helpers.SaveData(AllGuildTagData, type="Tag")


            await SendMessage("Deleted " + TagType + " " + TagKey + " from RedBot Database")
            await Context.Message.add_reaction(Conversation.Emoji["check"])
            return

        ResponsePrompt = await SendMessage("Okay, send the new **" + EditMode + "** that you desire for your "
                                                    + TagType + ".")

        def check2(init_msg):
            if init_msg.author.id == Context.Message.author.id:
                return True

        try:
            ResponseMsg = await Vars.Bot.wait_for('message', timeout=60, check=check2)

        except asyncio.TimeoutError:
            await SendMessage("Edit Timed Out.")
            await Helpers.QuietDelete(ResponsePrompt)
            return

        await Helpers.QuietDelete(ResponsePrompt)
        await message.channel.trigger_typing()

        # Okay so now we have the new part of the tag, so it's time to split off and run the command per grouping

        if IsPersonalTag:
            AllTagData = await Tag.GetPersonalTagList(ID=Context.Message.author.id)
        else:
            AllTagData = await Tag.GetGuildTagList(ID=Context.Message.guild.id)

        # KEY
        if EditMode == "Key":
            NewKey = ResponseMsg.content.strip().replace("-", " ").lower()
            IsSafeMsg = await Tag.CheckPotentialTag(NewKey, TagData["Content"], TagData["Image"], AllTagData)

            if IsSafeMsg:
                await SendMessage(IsSafeMsg)
                return

            # if Key is good:
            TagData["Key"] = NewKey

        elif EditMode == "Content":
            NewContent = ResponseMsg.content.strip()

            # Shorten any links
            NewContent = await Helpers.ShortenTextInLink(NewContent)

            # Okay so now all links are shortened, check length:
            IsSafeMsg = await Tag.CheckPotentialTag(TagData["Key"], NewContent, TagData["Image"], AllTagData, DoNotCheck=["key"])
            if IsSafeMsg:
                await SendMessage(IsSafeMsg)
                return

            # if it's cleared to go
            TagData["Content"] = NewContent

        elif EditMode == "Image":
            try:
                NewImage = ResponseMsg.attachments[0]
            except:
                await SendMessage("You forgot to attach an image, bud.")
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
                second_message = await SendMessage(failure)
                return

            TagData["Color"] = str(color).replace("#", "")
            TagData['Color'] = color.value

        await Helpers.QuietDelete(ResponseMsg)

        # So at this point we have an updated TagData Dict to use
        if not "Color" in TagData.keys():
            TagData["Color"] = Vars.Bot_Color

        ConfirmMessage = "This is the " + TagType + " you want?"
        if IsPersonalTag:
            Command = "/ptag "
        else:
            Command = "/tag "

        if not TagData["Color"]:
            TagData["Color"] = Vars.Bot_Color
        Extra_Text = "```You Send:  > " + Command + TagData["Key"] + "\nI Respond: > " + TagData["Content"].replace(
            "```", "\'\'\'") + "```"
        Confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, ConfirmMessage,
                                                       extra_text=Extra_Text, add_reaction=False,
                                                       deny_text=TagType + " Edit Cancelled",
                                                       image=TagData["Image"], color=TagData["Color"])
        if not Confirmation:
            return

        # If they confirmed it:
        AllTagData.pop(TagKey)

        # AllTagData[TagData["Key"]] = TagData

        # Set it in the new dict
        await SaveData(AllTagData, TagData, IsPersonalTag)

        ExitMessage = "Successfully Edited the " + TagType + ". To use it, type: ```css\n" + Command + TagData[
            "Key"] + "```"
        await SendMessage(ExitMessage)

        return




class Remind:
    # Working on the new /remind command
    embed_color = 0x4286f4
    @staticmethod
    async def OnMessage(Context):
        await Remind.RemindCommand(Context)
        await Remind.ListReminders(Context)
        await Remind.EditReminders(Context)

    @staticmethod
    async def ReturnError(message, error_message, sendformat=True, title="Reminder Error"):
        # If there is some issue, this will make things easier.
        await message.add_reaction(Conversation.Emoji["x"])

        if sendformat:
            format = "```\n/remind 2 days Clean Your Room"
            format += "\n/remind 12:45 Hello there"
            format += "\n/remind 2 hours 35 minutes These are Examples```"
            error_message += format

        em = discord.Embed(color=Remind.embed_color, description=error_message)
        em.set_author(name=title, icon_url=Vars.Bot.user.avatar_url)

        await message.channel.send(embed=em)
        return

    @staticmethod
    @Command(Start=["remind", "r"], Prefix=True)
    async def RemindCommand(Context):
        message = Context.Message

        if not Context.InDM: # TODO Update Cooldown to work on DM Channels
            cd_notice = Cooldown.CheckCooldown("remind", message.author, message.guild)
            if type(cd_notice) == int:
                await Remind.ReturnError(message, 'Cooldown Active, please wait: `' + Sys.SecMin(cd_notice) + '`', sendformat=False)
                await message.add_reaction(Conversation.Emoji["x"])
                return

        # First let's send the typing indicator
        await message.channel.trigger_typing()

        # Set content
        Content = message.content[1:]  # message.content without the command prefix

        # So, Reminders can be started with either "remind", or "r". Let's figure out which one and remove it
        for start in ["remind ", "r "]:
            if Content.lower().startswith(start):  # If it starts with that start
                Content = Content[len(start):]  # Snip that beginning part off
                break

        firstitem = Content.strip().split(" ")[0]
        if firstitem.startswith("<@!"):
            SendToUser = firstitem
            Content = Content.replace(firstitem, "").strip()

        else:
            SendToUser = None

        if SendToUser:
            SendToUser = int(SendToUser[3:].replace(">",""))
            SendToUser = Vars.Bot.get_user(SendToUser)

            if not SendToUser:
                await Remind.ReturnError(message, "Cannot find the person you speak of!")
                return

            if Context.InDM:
                # TODO This thread should eventually talk to the person in their own DM Channel
                await Remind.ReturnError(message, "You can only remind yourself in a DM Channel!")
                return

        if not SendToUser:
            SendToUser = message.author


        # Let's take a look for any images in the Reminds
        if message.attachments:
            IsImage = message.attachments[0]
            # Save IsImage
            IsImage = await Helpers.DownloadAndUpload(message, IsImage)
            IsImage = IsImage.link
        else:
            IsImage = None


        # Let's shorten any links in the reminder
        if "http" in Content.lower():
            TempParts = Content.strip().split(" ")

            for section in TempParts:
                if section.lower().strip().startswith("http"):  # If that word is a link:
                    shortened = Sys.Shorten_Link(section)
                    Content = Content.replace(section, shortened)


        # So now let's build a vocabulary of time / date words
        RemindWords = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
                       "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
                                                                                           "today", "tomorrow", "day", "days", "week", "weeks", "month", "months", "minute", "minutes", "hour", "hours", "second", "seconds",
                       "morning", "noon", "afternoon", "night", "evening", "in", "at", "on", "pm", "am", "late", "early", "this", "the",
                       "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "fifteen", "twenty", "tonight"]

        RemindTimeList = []  # A listing of each word in order that the program *thinks* may be a part of the reminder time section

        i = 0
        for word in Content.split(" "):
            word = word.strip()
            AddToList = False
            if "http" in word.lower():
                continue

            if word.lower() in RemindWords:  # If that word is in that above listing, add to list and continue
                AddToList = True

            if ":" in word.lower():  # indicative of a time
                AddToList = True

            if "/" in word.lower() or "-" in word.lower():
                if "http" not in word.lower():
                    AddToList = True

            if len(word) < 6:
                Endings = ["st", "nd", "rd", "th"]
                for end in Endings:
                    if word.endswith(end):
                        tempword = word.replace(end, "")
                        try:
                            int(tempword)
                            AddToList = True
                        except:
                            pass

            if not AddToList:  # If there's none of those characteristics, maybe it's a number
                try:
                    num = int(word)
                    AddToList = True

                except:
                    pass

            if AddToList:
                RemindTimeList.append(word)

            else:
                break

            i += 1

        if not RemindTimeList:
            await Remind.ReturnError(message, "Error parsing reminder. Please follow format:")
            return

        # Now let's send along our data to the interpreter
        RemindTime, Ignored_Words = await Remind.RemindInterpretation(RemindTimeList)

        # HAS INTERPRETATION
        CurrentTime = datetime.now()

        # If they say "Tomorrow" But it's early in the morning, see what they really mean
        if "tomorrow" in Sys.LowerStripList(RemindTimeList) and 0 <= int(CurrentTime.strftime("%H")) <= 4:
            RemindTime = await Remind.VerifyTomorrow(RemindTime, CurrentTime, Context)

        New_Ignored_Words = {}
        for Ignore in Ignored_Words:
            New_Ignored_Words[Ignore["Orig_Word"]] = Ignore

        # Now let's figure out that message.
        OrigMsgList = Content.split(" ")
        i = 0
        To_Save_List = []
        for saved_word in OrigMsgList:
            # For each word in that message list
            if saved_word.lower().strip() in New_Ignored_Words.keys():
                if i == New_Ignored_Words[saved_word.lower().strip()]["Place"]:
                    To_Save_List.append(saved_word)
            elif saved_word not in RemindTimeList:
                To_Save_List.append(saved_word)

            i += 1

        RemindMsg = " ".join(To_Save_List)

        if RemindMsg.lower().startswith("that"):
            RemindMsg = RemindMsg[4:].strip()

        To_s = ["You should", "You have to", "You need to", "You better", "It's time to ", "You can", "Please"]

        if RemindMsg.lower().startswith("to"):
            RemindMsg = RemindMsg[2:].strip()
            RemindMsg = random.choice(To_s) + " " + RemindMsg
            if random.choice([0,0,0,0,1]):
                RemindMsg += random.choice([" soon", " now"])

        RemindMsg = Sys.FirstCap(RemindMsg).strip()

        # Find out if it ends with punctuation
        if not RemindMsg[len(RemindMsg)-1 : len(RemindMsg)] in [".", ",", "!", "?", " "]:
            RemindMsg += "."

        CurrentTime = datetime.now()

        if len(RemindMsg) > 500:
            await Remind.ReturnError(message, "Your Reminder Message is too long! Keep it less than 500 characters! \nYours is: " + len(RemindMsg))
            return

        if RemindTime > CurrentTime + timedelta(days=65):
            await Remind.ReturnError(message, "The maximum time you can set a reminder is 2 Months!")
            return


        if RemindTime < CurrentTime:
            await Remind.ReturnError(message, "Given RemindTime already happened!")
            return

        toSendDateString = await Remind.GiveDateString(RemindTime, CurrentTime)

        FirstTitleString = toSendDateString

        if SendToUser.id == message.author.id:
            FinalTitleString = "Okay, I'll remind you."
        else:
            FinalTitleString = "Okay, I'll remind " + SendToUser.name + "#" + SendToUser.discriminator

        string = "```md\n# " + toSendDateString + "\nI say: > @" + SendToUser.name + ", " + RemindMsg + "```"

        ReminderData = await Remind.SaveReminder(RemindTime, RemindMsg, message, SendToUser, IsImage)

        em = discord.Embed(color=Remind.embed_color, description=string)
        em.set_author(name="Scheduled Reminder:", icon_url=Vars.Bot.user.avatar_url)

        if IsImage:
            em.set_image(url=IsImage)

        em.set_footer(text="Want to cancel? Hit the X reaction below. ")

        sent = await message.channel.send(FirstTitleString, embed=em)
        await sent.edit(content=FinalTitleString, embed=em)

        await Log.LogCommand(message, "Reminder", "Successfully Set Reminder", DM=Context.InDM)

        if Context.InDM:
            reaction_to_add = Conversation.Emoji["clock"]
        else:
            reaction_to_add = Conversation.Emoji["clock"]

        await message.add_reaction(reaction_to_add)

        # Now we'll add the x to cancel the reminder
        await sent.add_reaction(Conversation.Emoji["x"])

        React_Info = await Helpers.WaitForReaction(reaction_emoji=Conversation.Emoji["x"], message=sent, timeout=30, users_id=message.author.id)

        if React_Info == None:
            await Helpers.RemoveBotReactions(sent)
            em.set_footer(text="")
            await sent.edit(content=FinalTitleString, embed=em)

        if React_Info:
            await Helpers.RemoveBotReactions(message)
            await Remind.DeleteSpecificReminder(ReminderData)
            await Helpers.QuietDelete(sent)
            await message.channel.send("I have deleted the reminder. Try again?", delete_after=10)
            if not await Helpers.Deleted(message):
                await message.add_reaction(Conversation.Emoji["x"])

        return

    @staticmethod
    async def RemindInterpretation(WordList):
        # Called internally. Iterates through wordlist to find two things: Date and Time
        FinalDate = None
        FinalTime = None

        # Now we want to find out what the type of each word is

        """
        Types can be:
        Number          1
        WrittenNumber   "one"
        WeekDay         "saturday"
        MonthDay        "26th"
        Month           "january"
        RelativeDay     "tomorrow"
        RelativeTime    "afternoon"
        TimeUnit        "hours"
        Time            "3:00"
        AMPM            "am"
        Date            "3/17"
        Helper          "in",
        AddTime         "early"
        """

        def FindType(word):
            word = word.lower().strip()
            # Input: word
            # Does: Finds out what the type is. Returns the second it has it.
            # return: The string containing the type

            HasType = False

            # NUMBER
            try:
                int(word)
                return "Number"
            except ValueError:
                pass

            # WRITTENNUMBER
            if word in ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "fifteen", "twenty"]:
                return "WrittenNumber"

            # WEEKDAY
            if word in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                return "WeekDay"

            # MONTHDAY
            for ending in ["st", "nd", "rd", "th"]:
                if word.endswith(ending):
                    return "MonthDay"

            # MONTH
            if word in ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]:
                return "Month"

            # RELATIVEDAY
            if word in ["today", "tomorrow"]:
                return "RelativeDay"

            # RELATIVETIME
            if word in ["tonight", "morning", "noon", "afternoon", "night", "evening"]:
                return "RelativeTime"

            # TIMEUNIT
            TimeUnits = ["second", "minute", "hour", "day", "week", "month"]
            if word.endswith("s"):
                if word[0:len(word)-1] in TimeUnits:
                    return "TimeUnit"
            else:
                if word in TimeUnits:
                    return "TimeUnit"

            # TIME
            if ":" in word and len(word) < 8:
                return "Time"

            # AMPM
            if word in ["am", "pm"]:
                return "AMPM"

            # DATE
            if "/" in word:
                return "Date"
            elif "-" in word:
                return "Date"

            # HELPER
            if word in ["in", "at", "on", "this", "the"]:
                return "Helper"

            # AddTime
            if word in ["early", "late"]:
                return "AddTime"

            return None


        ItemDict = []
        i = 0
        for word in WordList:
            info = {
                "Word": word,
                "Type": FindType(word),
                "Place": i
            }
            ItemDict.append(info)
            i += 1

        # Okay so now we have all of the items categorized

        # Okay so now lets do some cleaning. We want to remove items that don't really matter to us, and clean up the ones who do
        def CleanUp(WordDict):
            orig_word = WordDict["Word"].lower()
            word_type = WordDict["Type"]
            new_word = None

            if word_type == "Number":
                new_word = int(orig_word)
                return new_word, "Number"

            if word_type == "WrittenNumber":
                WritDict = {
                    "one": 1,
                    "two": 2,
                    "three": 3,
                    "four": 4,
                    "five": 5,
                    "six": 6,
                    "seven": 7,
                    "eight": 8,
                    "nine": 9,
                    "ten": 10,
                    "fifteen": 15,
                    "twenty": 20
                }
                return WritDict[orig_word], "Number"


            if word_type == "MonthDay":
                new_num = None
                for ending in ["st", "nd", "rd", "th"]:
                    if orig_word.endswith(ending):
                        new_num = orig_word.replace(ending, "")
                        break

                try:
                    new_num = int(new_num)
                    return new_num, "MonthDay"

                except ValueError:
                    return None, None

            if word_type == "Month":
                month_info = {
                    "january": 1,
                    "february": 2,
                    "march": 3,
                    "april": 4,
                    "may": 5,
                    "june": 6,
                    "july": 7,
                    "august": 8,
                    "september": 9,
                    "october": 10,
                    "november": 11,
                    "december": 12
                }
                return month_info[orig_word], word_type

            if word_type == "TimeUnit":
                if orig_word.endswith("s"):
                    orig_word = orig_word[0:len(orig_word)-1]
                return orig_word, "TimeUnit"

            if word_type == "Helper":
                return None, None

            return orig_word, word_type

        CleanItemDict = []
        for item in ItemDict:
            info = {
                "Orig_Word": item["Word"],
                "Orig_Type": item["Type"],
                "Already_Found": False,
                "Place": item["Place"]
            }
            NewWord, NewType = CleanUp(item)
            if NewWord and NewType:
                info["Word"] = NewWord
                info["Type"] = NewType

                CleanItemDict.append(info)
            i += 1


        # Okay so now comes the Fun Part, in which we go through each individual item in the list to try and find these things:
        TempAdd = []     # Represents amounts we should add to a given date
        TempSecure = []  # Represents Factors we know for certain (Direct date / time)
        Modifier = []    # Early / Late, held off until final step
        Ignore_List = [] # A list of the words and phrases that we ignored

        def Next(i, c=1):  # c can represent any constant, it's the skip factor
            # Returns the next item in TempDict if it's not serviced
            if i + c >= len(CleanItemDict):  # If it's over the bound
                return {"Word": None, "Type": None}

            if CleanItemDict[i + c]["Already_Found"]:
                return {"Word": None, "Type": None}

            return CleanItemDict[i + c]

        i = 0
        for item in CleanItemDict:
            if not item["Already_Found"]:
                NextItem = Next(i)
                # So if the item is fair game to use
                if item["Type"] == "Number":
                    if 2000 < item["Word"] < 2020:
                        TempSecure.append({
                            "Time": None,
                            "Date": {
                                "DayNum": None,
                                "MonthNum": None,
                                "YearNum": item["Word"]
                            },
                            "Strength": 5
                        })
                        item["Already_Found"] = True
                        continue

                    elif NextItem["Type"] == "TimeUnit":
                        TempAdd.append({
                            "Amount": item["Word"],
                            "Unit": NextItem["Word"]
                        })
                        item["Already_Found"] = True
                        NextItem["Already_Found"] = True

                    elif NextItem["Type"] == "AMPM":
                        TempSecure.append({
                            "Time": {
                                "Minute": 00,
                                "Hour": item["Word"],
                                "AMPM": NextItem["Word"]
                            },
                            "Date": None,
                            "Strength": 5
                        })
                        item["Already_Found"] = True
                        NextItem["Already_Found"] = True

                    elif NextItem["Type"] == "Month":
                        TempSecure.append({
                            "Time": None,
                            "Date": {
                                "DayNum": item["Word"],
                                "MonthNum": NextItem["Word"],
                                "YearNum": None
                            },
                            "Strength": 3
                        })
                        item["Already_Found"] = True
                        NextItem["Already_Found"] = True

                    # If it's not a time or an addative unite, Assume it's an hour without an ampm
                    if not item["Already_Found"] and 0 < item["Word"] <= 24 and not TempAdd:
                        TempSecure.append({
                            "Time": {
                                "Minute": 00,
                                "Hour": item["Word"],
                                "AMPM": None
                            },
                            "Date": None,
                            "Strength": 2
                        })
                        item["Already_Found"] = True

                # If the item is a weekday, do very little.
                elif item["Type"] == "WeekDay":
                    # Okay so if the item is a weekday, either it matters very little or a lot
                    # Little: /r Saturday November 3rd [msg] (November 3rd does heavy lifting)
                    # Lot: /r saturday morning [msg]

                    # So what we're going to do is add a weak (low strength) entry for the day of this saturday.
                    # If nothing else is found, the system'll choose it
                    WeekDay_Date = 1
                    DatePointer = datetime.now()
                    for i in range(0, 8):
                        DatePointer = DatePointer + timedelta(days=1)
                        if DatePointer.strftime("%A") == Sys.FirstCap(item["Word"]):
                            WeekDay_Date = int(DatePointer.strftime("%d"))
                            break

                    TempSecure.append({
                        "Time": None,
                        "Date": {
                            "DayNum": WeekDay_Date,
                            "MonthNum": None,
                            "YearNum": None
                        },
                        "Strength": 2
                    })
                    item["Already_Found"] = True

                # If it's a month Day, check if the next item is a month
                elif item["Type"] == "MonthDay":
                    if NextItem["Type"] == "Month":
                        TempSecure.append({
                            "Time": None,
                            "Date": {
                                "DayNum": item["Word"],
                                "MonthNum": NextItem["Word"],
                                "YearNum": None
                            },
                            "Strength": 5
                        })
                        NextItem[Already_Found] = True
                        item["Already_Found"] = True
                        continue

                    # If we reach this point, there's no month next, so let's just assume they mean either this or next month
                    if not item["Already_Found"]:
                        Current_Day = int(datetime.now().strftime("%d"))
                        if Current_Day > item["Word"]:  # IE if the date has already happened this month:
                            ItemMonth = int(datetime.now().strftime("%m")) + 1
                            if ItemMonth > 12:
                                ItemMonth = 1
                                ItemYear = int(datetime.now().strftime("%Y")) + 1
                            else:
                                ItemYear = int(datetime.now().strftime("%Y"))
                        else:
                            ItemMonth = int(datetime.now().strftime("%m"))
                            ItemYear = int(datetime.now().strftime("%Y"))

                        TempSecure.append({
                            "Time": None,
                            "Date": {
                                "DayNum": item["Word"],
                                "MonthNum": ItemMonth,
                                "YearNum": ItemYear
                            },
                            "Strength": 3
                        })
                        item["Already_Found"] = True
                        continue

                elif item["Type"] == "Month":
                    if NextItem["Type"] == "Number" or NextItem["Type"] == "MonthDay":
                        TempSecure.append({
                            "Time": None,
                            "Date": {
                                "DayNum": NextItem["Word"],
                                "MonthNum": item["Word"],
                                "YearNum": None
                            },
                            "Strength": 4
                        })
                        NextItem["Already_Found"] = True
                        item["Already_Found"] = True

                    elif not item["Already_Found"]:
                        TempSecure.append({
                            "Time": None,
                            "Date": {
                                "DayNum": None,
                                "MonthNum": item["Word"],
                                "YearNum": None
                            },
                            "Strength": 3
                        })
                        item["Already_Found"] = True

                elif item["Type"] == "RelativeDay":
                    if item["Word"] == "today":
                        TempSecure.append({
                            "Time": None,
                            "Date": {
                                "DayNum": int(datetime.now().strftime("%d")),
                                "MonthNum": int(datetime.now().strftime("%m")),
                                "YearNum": int(datetime.now().strftime("%Y"))
                            },
                            "Strength": 4
                        })
                        item["Already_Found"] = True

                    if item["Word"] == "tomorrow":
                        TempSecure.append({
                            "Time": None,
                            "Date": {
                                "DayNum": int(datetime.now().strftime("%d")) + 1,
                                "MonthNum": int(datetime.now().strftime("%m")),
                                "YearNum": int(datetime.now().strftime("%Y"))
                            },
                            "Strength": 4
                        })
                        item["Already_Found"] = True

                elif item["Type"] == "RelativeTime":
                    # All about the hour
                    word = item["Word"]
                    if word == "morning":
                        hour = 8
                        AMPM = "am"
                    elif word == "noon":
                        hour = 12
                        AMPM = "pm"
                    elif word == "afternoon":
                        hour = 3
                        AMPM = "pm"
                    elif word == "evening":
                        hour = 7
                        AMPM = "pm"
                    elif word == "night":
                        hour = 9
                        AMPM = "pm"
                    elif word == "tonight":
                        TempSecure.append({
                            "Time": {
                                "Minute": 00,
                                "Hour": 9,
                                "AMPM": 'pm'

                            },
                            "Date": {
                                "DayNum": int(datetime.now().strftime("%d")),
                                "MonthNum": int(datetime.now().strftime("%m")),
                                "YearNum": int(datetime.now().strftime("%Y"))
                            },
                            "Strength": 4
                        })
                        item["Already_Found"] = True
                        continue


                    TempSecure.append({
                        "Time": {
                            "Minute": 00,
                            "Hour": hour,
                            "AMPM": AMPM

                        },
                        "Date": None,
                        "Strength": 3
                    })
                    item["Already_Found"] = True

                elif item["Type"] == "TimeUnit":
                    pass  # Do Nothing! These should only follow a number!

                elif item["Type"] == "Time":
                    # Finally, an actual feature the previous Remind Command had
                    if NextItem["Type"] == "AMPM":
                        AMPM = NextItem["Word"]
                        NextItem["Already_Found"] = True
                    else:
                        AMPM = None

                    TempSecure.append({
                        "Time": {
                            "Minute": int(item['Word'].split(":")[1]),
                            "Hour": item['Word'].split(":")[0],
                            "AMPM": AMPM
                        },
                        "Date": None,
                        "Strength": 4

                    })
                    item["Already_Found"] = True

                elif item["Type"] == "AMPM":
                    TempSecure.append({
                        "Time": {
                            "Minute": None,
                            "Hour": None,
                            "AMPM": item["Word"]
                        },
                        "Date": None,
                        "Strength": 3

                    })
                    item["Already_Found"] = True

                elif item["Type"] == "Date":
                    Parts = item["Word"].replace("-", "/").replace("\\","/").split("/")
                    if len(Parts) >= 3:
                        Year = int(Parts[2])
                    else:
                        Year = None

                    Day = int(Parts[1])
                    Month = int(Parts[0])

                    if Day <= 12 and Month > 12:
                        Day, Month = Month, Day

                    TempSecure.append({
                        "Time": None,
                        "Date": {
                            "DayNum": Day,
                            "MonthNum": Month,
                            "YearNum": Year
                        },
                        "Strength": 5
                    })
                    item["Already_Found"] = True

                elif item["Type"] == "Helper":
                    pass

                elif item["Type"] == "AddTime":
                    Modifier.append(item)

                if not item["Already_Found"]:
                    Ignore_List.append(item)

            i += 1


        # Alright, that was chaos. Now, we want to combine all of the TempSecure into one item
        FinalSecure = {
            "Time": {
                "Minute": None,
                "Hour": None,
                "AMPM": None,
                "Strength": 0
            },
            "Date": {
                "DayNum": None,
                "MonthNum": None,
                "YearNum": None,
                "Strength": 0
            }
        }

        for PotentialSecure in TempSecure:
            if PotentialSecure["Time"]:
                if not FinalSecure["Time"]:
                    FinalSecure["Time"]["Minute"] = PotentialSecure["Time"]["Minute"]
                    FinalSecure["Time"]["Hour"] = PotentialSecure["Time"]["Hour"]
                    FinalSecure["Time"]["AMPM"] = PotentialSecure["Time"]["AMPM"]
                    FinalSecure["Time"]["Strength"] = PotentialSecure["Strength"]

                elif PotentialSecure["Strength"] > FinalSecure["Time"]["Strength"]:
                    FinalSecure["Time"]["Minute"] = PotentialSecure["Time"]["Minute"]
                    FinalSecure["Time"]["Hour"] = PotentialSecure["Time"]["Hour"]
                    FinalSecure["Time"]["AMPM"] = PotentialSecure["Time"]["AMPM"]
                    FinalSecure["Time"]["Strength"] = PotentialSecure["Strength"]

            if PotentialSecure["Date"]:
                for item in ["DayNum", "MonthNum", "YearNum"]:
                    if PotentialSecure["Date"][item]:

                        if not FinalSecure["Date"][item] and FinalSecure["Date"]["Strength"]:
                            # If there's none of one item, but the others have a strength
                            if PotentialSecure["Strength"] >= FinalSecure["Date"]["Strength"]:
                                FinalSecure["Date"][item] = PotentialSecure["Date"][item]
                                FinalSecure["Date"]["Strength"] = PotentialSecure["Strength"]

                        elif not FinalSecure["Date"][item] and not FinalSecure["Date"]["Strength"]:
                            # If there's none of one item, and no strength
                            FinalSecure["Date"][item] = PotentialSecure["Date"][item]
                            FinalSecure["Date"]["Strength"] = PotentialSecure["Strength"]

                        elif FinalSecure["Date"]["Strength"] < PotentialSecure["Strength"]:
                            FinalSecure["Date"][item] = PotentialSecure["Date"][item]
                            FinalSecure["Date"]["Strength"] = PotentialSecure["Strength"]


        # So now, let's start to try to clean up what we have and figure out what we don't have
        TimeData = FinalSecure["Time"]
        DateData = FinalSecure["Date"]


        NowData = {
            "DayNum": int(datetime.now().strftime("%d")),
            "MonthNum": int(datetime.now().strftime("%m")),
            "YearNum": int(datetime.now().strftime("%Y")),
        }

        HasDateInformation = False
        for item in [DateData["DayNum"], DateData["MonthNum"], DateData["YearNum"]]:
            if item:
                HasDateInformation = True

        HasTimeInformation = False
        for item in (TimeData["Hour"], TimeData["Minute"]):
            if item:
                HasTimeInformation = True

        for partial in ["Minute", "Hour"]:
            if TimeData[partial]:
                TimeData[partial] = int(TimeData[partial])
                if TimeData[partial] < 0:
                    TimeData[partial] *= -1

        for partial in ["DayNum", "MonthNum", "YearNum"]:
            if DateData[partial]:
                DateData[partial] = int(DateData[partial])
                if DateData[partial] < 0:
                    DateData[partial] *= -1


        if not HasDateInformation and not HasTimeInformation and TempAdd:
            # If there's no date, no time, but there are things to add:
            DateData = {
                "DayNum": int(datetime.now().strftime("%d")),
                "MonthNum": int(datetime.now().strftime("%m")),
                "YearNum": int(datetime.now().strftime("%Y")),
            }

            TimeData = {
                "Hour": int(datetime.now().strftime("%H")),
                "Minute": int(datetime.now().strftime("%M")),
                "AMPM": "am"
            }


        # Month and No Day  -  If month is current, Tomorrow, otherwise, 1st of month
        if DateData["MonthNum"] and not DateData["DayNum"]:
            if NowData["MonthNum"] == DateData["MonthNum"]:
                DateData["DayNum"] = NowData["DayNum"] + 1
            else:
                DateData["DayNum"] = 1

        # Day and No Month  -  If day already happened, next month, otherwise, this month
        if DateData["DayNum"] and not DateData["MonthNum"]:
            if DateData["DayNum"] <= NowData["DayNum"]:
                DateData["MonthNum"] = NowData["MonthNum"] + 1
            else:
                DateData["MonthNum"] = NowData["MonthNum"]

        # Month and No Year  - If month already happened, next year, otherwise, this year
        if DateData["MonthNum"] and not DateData["YearNum"]:
            if DateData["MonthNum"] < NowData["MonthNum"]:
                DateData["YearNum"] = NowData["YearNum"] + 1
            else:
                DateData["YearNum"] = NowData["YearNum"]


        # Dates are all set, now let's do time
        # No minute
        if TimeData["Minute"] == None:
            TimeData["Minute"] = 1

        if TimeData["Hour"] == None:
            TimeData["Hour"] = 9

            if not TimeData["AMPM"]:
                TimeData["AMPM"] = 'am'

        if not TimeData["AMPM"]:
            CurrentHour = int(datetime.now().strftime("%I"))
            CurrentAMPM = datetime.now().strftime("%p").lower()

            if TimeData["Hour"] < CurrentHour:
                TimeData['AMPM'] = 'pm' if CurrentAMPM == 'am' else 'am'

            elif TimeData["Hour"] > CurrentHour:
                TimeData['AMPM'] = CurrentAMPM

            else:  # If the hour is the same:
                CurrentMinute = int(datetime.now().strftime("%M"))
                if TimeData["Minute"] <= CurrentMinute:
                    TimeData['AMPM'] = 'pm' if CurrentAMPM == 'am' else 'am'

                else:
                    TimeData['AMPM'] = CurrentAMPM


            if 2 < TimeData["Hour"] < 5 and TimeData['AMPM'] == 'am':
                TimeData["AMPM"] = 'pm'

        if HasTimeInformation and not HasDateInformation:
            TimeValue = TimeData["Hour"] * 100 + TimeData["Minute"]  # 4 digit number MiHr
            if TimeData["AMPM"] == "pm" and TimeData["Hour"] != 12:
                TimeValue += 1200
            NowTimeValue = int(datetime.now().strftime("%H")) * 100 + int(datetime.now().strftime("%M"))

            if NowTimeValue >= TimeValue:
                DayPlus = 1
            else:
                DayPlus = 0


            DateData = {
                "DayNum": int(datetime.now().strftime("%d")) + DayPlus,
                "MonthNum": int(datetime.now().strftime("%m")),
                "YearNum": int(datetime.now().strftime("%Y")),
            }


        # Okay, time to balance things and then we're good to go!
        def Balance(Given_Time, Given_Date):
            # Balances things out to ensure that there are no issues, returns date dict
            Hour, Minute = Given_Time["Hour"], Given_Time["Minute"]
            Day, Month, Year = Given_Date["DayNum"], Given_Date["MonthNum"], Given_Date["YearNum"]

            if Given_Time["AMPM"] == 'pm':
                if Given_Time["Hour"] == 12:
                    Hour = 12
                else:
                    Hour = Given_Time["Hour"] + 12
            else:
                Hour = Given_Time["Hour"]

            if Month > 12:
                Year += 1
                Month = Month - 12

            # Now let's try to create a time object
            Minute = str(Minute)
            Hour = str(Hour)
            Day = str(Day)
            Month = str(Month)
            Year = str(Year)


            # Change "2" to "02" or "" to "00"
            for item in [Minute, Hour, Day, Month]:
                while len(item) < 2:
                    item = "0" + item


            string = ", ".join([Minute, Hour, Day, Month, Year])

            return string

        string = Balance(TimeData, DateData)

        dt = time.strptime(string, "%M, %H, %d, %m, %Y")

        dt = datetime.fromtimestamp(time.mktime(dt))

        for timeitem in TempAdd:
            # Don't think we forgot about tempadd!
            if timeitem["Unit"].lower().strip() == "minute":
                dt = dt + timedelta(minutes=timeitem["Amount"])

            elif timeitem["Unit"].lower().strip() == "hour":
                dt = dt + timedelta(hours=timeitem["Amount"])

            elif timeitem["Unit"].lower().strip() == "day":
                dt = dt + timedelta(days=timeitem["Amount"])

            elif timeitem["Unit"].lower().strip() == "week":
                dt = dt + timedelta(weeks=timeitem["Amount"])

        return dt, Ignore_List

    @staticmethod
    async def VerifyTomorrow(RemindTime, CurrentTime, Context):
        # Ran if the user says "Tomorrow" and the time is between 12 and 4 am
        # First let's just ensure that the reminder time - one day hasn't already happened
        MinusDayTime = RemindTime - timedelta(days=1)
        if MinusDayTime < CurrentTime:
            # If the RemindTime - 1day has already happened:
            return RemindTime  # Return because we're done.

        # If we're still here, it's possible they meant today or tomorrow.
        TodayStr = "Later Today *" + CurrentTime.strftime("(%b %d)*")
        TomorrowStr = "Tomorrow *" + (CurrentTime + timedelta(days=1)).strftime("(%b %d)*")

        Choices = [
            {"Option": TodayStr, "Emoji": Conversation.Emoji['red']},
            {"Option": TomorrowStr, "Emoji": Conversation.Emoji['blue']}
        ]

        Description = "My time is " + CurrentTime.strftime("%I:%M %p") + ", so 'tomorrow' could mean later today, or tomorrow. Which did you mean?"

        Response = await Interraction.UserChoice(Context.Channel, Context.Message.author, "What did you mean by 'Tomorrow'?", Choices=Choices, description=Description, timeout=60,
                                            Color=Remind.embed_color)


        if not Response:  # No response, default to today
            await Context.Message.channel.send("Timed Out, assuming 'tomorrow' means later today.", delete_after=20)
            RemindTime = RemindTime - timedelta(days=1)
            return RemindTime

        if Response == TodayStr:
            return RemindTime - timedelta(days=1)

        else:
            return RemindTime

        return RemindTime

    @staticmethod
    async def GiveDateString(RemindTime, CurrentTime, sendFull=False):
        if sendFull:
            return RemindTime.strftime("%a, %b %d, %Y at %I:%M %p")

        if RemindTime.strftime("%b %d") == CurrentTime.strftime("%b %d"):
            add = "Today"

            if int(RemindTime.strftime("%H")) >= 18:
                add = "Tonight"
            elif int(RemindTime.strftime("%H")) >= 12:
                add = "This Afternoon"
            elif int(RemindTime.strftime("%H")) >= 4:
                add = "This Morning"

            toSendDateString = RemindTime.strftime(add + " at %I:%M %p")

        elif RemindTime.strftime("%b %d") == (CurrentTime + timedelta(days=1)).strftime("%b %d"):
            add = "Tomorrow"
            if int(RemindTime.strftime("%H")) >= 18:
                add = "Tomorrow Night"
            elif int(RemindTime.strftime("%H")) >= 12:
                add = "Tomorrow Afternoon"
            elif 5 <= int(RemindTime.strftime("%H")) < 11:
                add = "Tomorrow Morning"

            toSendDateString = RemindTime.strftime(add + " at %I:%M %p")



        else:
            toSendDateString = RemindTime.strftime("%a, %b %d, %Y at %I:%M %p")

        return toSendDateString

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
            "Repeat": 0,
            "RemindStr": RemindTime.strftime("%a, %b %d, %Y at %I:%M %p")
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

            if not SendChannel:
                if not Reminder["Guild"]:
                    # If there's no guild, it's a DM Reminder
                    await RemindPerson.create_dm()
                    SendChannel = RemindPerson.dm_channel

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
                continue

            if not Reminder["OriginalMessageID"] or not SentMsg or not SendChannel:
                continue

            try:
                originalmsg = await SendChannel.get_message(int(Reminder["OriginalMessageID"]))

                if not originalmsg:
                    return
            except:
                continue

            await Helpers.RemoveAllReactions(originalmsg)
            await originalmsg.add_reaction(Conversation.Emoji["check"])

            thread = Vars.Bot.loop.create_task(Remind.SentReminderActions(Reminder, originalmsg, SendChannel, SentMsg, RemindPerson))

        # Now that it's been sent, it must be deleted
        await Remind.DeleteReminder(str(RemindList[0]["RemindStamp"]))

        return

    @staticmethod
    async def SentReminderActions(Reminder, originalmsg, SendChannel, SentMsg, RemindPerson):
        if Reminder["Repeat"] > 4:
            return

        # Now we do the emojis
        emoji_five   = '5\u20e3'
        emoji_ten    = '\U0001f51f'
        emoji_mystery = '\U00002601'
        emoji_calendar = '\U0001f5d3'
        emoji_list = [emoji_five, emoji_ten, emoji_mystery, emoji_calendar]

        for emoji in emoji_list:
            await SentMsg.add_reaction(emoji)

        async def RemoveReaction(reaction, user):
            if not await Helpers.Deleted(reaction.message) and not IsDMChannel(SendChannel):
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
                await Helpers.RemoveAllReactions(SentMsg)
                Stop = True
                return
        await Helpers.RemoveBotReactions(SentMsg)


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
        elif reaction.emoji == emoji_calendar:
            # Prompt for a new Time To be Reminded
            em = discord.Embed(color=Remind.embed_color, description="Please send the new date or time you'd like to be reminded. Do not include the message :)")
            em.set_author(name="Reschedule Reminder", icon_url=Vars.Bot.user.avatar_url)

            Prompt = await SendChannel.send(embed=em)

            def check(ResponseMsg):
                if ResponseMsg.channel.id != Prompt.channel.id:
                    return False
                if ResponseMsg.author.id != RemindPerson.id:
                    return False
                else:
                    return True

            try:
                Response = await Vars.Bot.wait_for('message', check=check, timeout=30)
                await Response.add_reaction(emoji_calendar)
                if not IsDMChannel(SendChannel):
                    await Helpers.QuietDelete(Prompt)

            except asyncio.TimeoutError:
                await Helpers.QuietDelete(Prompt)
                await SendChannel.send("Timed out.", delete_after=10)
                return None

            # Okay so now we have this Response Msg
            Content = Response.content.lower().split(" ")

            try:
                NewTime, ignore_list = await Remind.RemindInterpretation(Content)
            except:
                em = discord.Embed(color=Remind.embed_color, description="Something went wrong! Verify that your response is a date / time.")
                em.set_author(icon_url=Vars.Bot.user.avatar_url, name="Reminder Rescheduling Error")
                await SendChannel.send(embed=em)
                return

            if "tomorrow" in Sys.LowerStripList(Content) and 0 <= int(CurrentTime.strftime("%H")) <= 4:
                Context = ContextMessage(originalmsg)
                NewTime = await Remind.VerifyTomorrow(NewTime, CurrentTime, Context)

        CurrentTime = datetime.now()

        if CurrentTime > NewTime:
            await Remind.ReturnError(reaction.message, "That time has already happened! Oh well.")
            return

        if NewTime > CurrentTime + timedelta(days=65):
            await Remind.ReturnError(reaction.message, "The maximum time you can set a reminder is 2 Months!")
            return



        await Remind.ReSaveReminder(Reminder, NewTime)


        toSendDateString = await Remind.GiveDateString(NewTime, CurrentTime)


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

    @staticmethod
    @Command(Start="Reminders", Prefix=True, NoSpace=True)
    async def ListReminders(Context):

        message = Context.Message
        # Returns a dict of every reminder you have
        RemindData = Helpers.RetrieveData(type="Remind")

        UserReminders = []
        for remindertime in sorted(RemindData.keys()):
            for reminder in RemindData[remindertime]:
                if int(reminder["RemindPerson"]) == message.author.id:
                    UserReminders.append(reminder)

        if len(UserReminders) > 8:
            More = len(UserReminders) - 8
            UserReminders = UserReminders[0:8]
        else:
            More = False

        description = "```md"
        for Reminder in UserReminders:
            temp = '\n'
            RemindTime = datetime.fromtimestamp(int(Reminder["RemindStamp"]))

            temp += await Remind.GiveDateString(RemindTime, datetime.now())
            # temp += "\n"

            AddMessage = Reminder["Message"]
            if len(AddMessage) > 100:
                AddMessage = AddMessage[0:100] + "[...]"

            temp += "  >>  " + AddMessage

            if Reminder["Image"]:
                temp += "  [Image]"

            description += temp

        description += "```"

        if UserReminders:
            name = "Here Are Your Upcoming Reminders:"
        else:
            description = "Do /remind <when> <message> <image attachment> to set one :)"
            name = "You have NO Upcoming Reminders"

        em = discord.Embed(description=description, color=Remind.embed_color, timestamp=Helpers.EmbedTime())
        em.set_author(name=name, icon_url=Vars.Bot.user.avatar_url)
        if More:
            em.set_footer(text="Hiding " + str(More) + " reminders to save space.")


        await message.channel.send(embed=em)

    @staticmethod
    @Command(Start="EditReminders", Prefix=True, NoSpace=True)
    async def EditReminders(Context):
        message = Context.Message

        # Get Reminder Data
        RemindData = Helpers.RetrieveData(type="Remind")

        # Create a list of all the reminders, sorted by time, that a person has
        UserReminders = []
        for remindertime in sorted(RemindData.keys()):  # For each remind time
            for reminder in RemindData[remindertime]:  # For each reminder at that time
                if int(reminder["RemindPerson"]) == message.author.id:  # If the person is the same
                    UserReminders.append(reminder)  # Append it to list

        if not UserReminders:  # If there are no reminders scheduled for that uesr: return
            await Remind.ReturnError(message, "You have no reminders scheduled! Use `/remind` to schedule some!")
            return

        # We're going to be using the Interraction.UserChoice Framework. What we need is a list of option strings
        OptionList = []
        # We also want a dictionary of the options to their respective Reminders
        OptionDict = {}
        for Reminder in UserReminders:  # For each reminder:
            # Create tempTime string that has the time that we'll be reminded at
            tempTime = datetime.fromtimestamp(int(Reminder["RemindStamp"]))
            tempTime = await Remind.GiveDateString(tempTime, datetime.now())

            # Message string that has the message
            tempMsg = Reminder["Message"][0:100] + "[...]" if len(Reminder["Message"]) > 100 else Reminder["Message"]
            tempMsg = tempMsg + " [Image]" if Reminder["Image"] else tempMsg

            # This tempStr string has the actual option to click on
            tempStr = "**" + tempTime + "** >> *" + tempMsg + "*"

            OptionList.append(tempStr)
            OptionDict[tempStr] = Reminder

        response = await Interraction.UserChoice(Context.Channel, Context.Message.author, "Which Reminder would you like to edit?", OptionList, Show_Cancel=True)

        if not response:
            return

        if response == "Cancel":
            return

        ChosenReminder = OptionDict[response]

        # Okay so here are the options possible
        Options = [
            {"Option": "Change Time/Date", "Emoji": Conversation.Emoji["clock"]},
            {"Option": "Change Message", "Emoji": Conversation.Emoji["message"]},
            {"Option": "Upload New Image", "Emoji": Conversation.Emoji["upload"]},
            {"Option": "Delete Reminder", "Emoji": Conversation.Emoji["trash"]}
        ]

        RemindTime = datetime.fromtimestamp(int(ChosenReminder["RemindStamp"]))
        RemindTimeString = await Remind.GiveDateString(RemindTime, datetime.now())

        RemindMsg = ChosenReminder["Message"][0:500] if len(ChosenReminder["Message"]) > 500 else ChosenReminder["Message"]
        if ChosenReminder["Image"]:
            RemindMsg += " | Image = " + ChosenReminder["Image"]

        Description = "What would you like to change about this reminder?```md\n# " + RemindTimeString + "\nI say >> " + RemindMsg + "```"

        response = await Interraction.UserChoice(Context.Channel, Context.Message.author, "Edit Reminder?", Options, description=Description, Show_Cancel=True)

        if not response or response == "Cancel":
            return

        def check(m):
            if m.channel.id != Context.Message.channel.id:
                return
            if m.author.id != Context.Message.author.id:
                return
            return True

        NewReminder = ChosenReminder.copy()

        if response == "Change Time/Date":
            AskPrompt = "The current listed time and date for this reminder is: *`" + RemindTimeString + "`*. Please send what you would like to change it to."

            SatisfiedTimeAndDate = False
            while not SatisfiedTimeAndDate:
                em = discord.Embed(description=AskPrompt, color=Remind.embed_color, timestamp=Helpers.EmbedTime())
                em.set_author(name="Change Reminder Time / Date?")
                em.set_footer(text="Times Out after 60 seconds. Please send the message in this channel.")

                TimeAndDatePrompt = await Context.Message.channel.send(embed=em)

                try:
                    NewTimeDateMessage = await Vars.Bot.wait_for('message', check=check, timeout=60)
                except asyncio.TimeoutError:
                    await Context.Message.channel.send("Timed out.", delete_after=10)
                    if not Context.IsDeleted():
                        await Context.Message.add_reaction(Conversation.Emoji["x"])
                    await QuietDelete(AskPrompt)
                    return

                await Helpers.QuietDelete(TimeAndDatePrompt)

                if NewTimeDateMessage:
                    NewRemindTime, ignored_list = await Remind.RemindInterpretation(NewTimeDateMessage.content.split(" "))

                    CorrectString = "This is the time / date I specified."
                    WrongString = "This time / date is wrong, let me try again"
                    VerifyTimeOptions = [
                        {"Option": CorrectString, "Emoji": Conversation.Emoji["check"]},
                        {"Option": WrongString, "Emoji": Conversation.Emoji["repeat"]}
                    ]


                    VerifyTime = await Interraction.UserChoice(Context.Channel, Context.Message.author, "I'll remind you: " + await Remind.GiveDateString(NewRemindTime, datetime.now()), VerifyTimeOptions, Show_Cancel=True )

                    if not VerifyTime or VerifyTime == "Cancel":
                        return

                    if VerifyTime == CorrectString:
                        SatisfiedTimeAndDate = True
                    else:
                        SatisfiedTimeAndDate = False

            # Now we have NewRemindTime
            NewReminder["RemindStamp"] = await Remind.DateStamp(NewRemindTime)
            NewReminder["RemindStr"] = await Remind.GiveDateString(NewRemindTime, datetime.now(), sendFull=True)

        elif response == "Change Message":
            AskPrompt = "The current listed message for this reminder is: " + ChosenReminder["Message"] + "  What would you like to change it to?"

            em = discord.Embed(description=AskPrompt, color=Remind.embed_color, timestamp=Helpers.EmbedTime())
            em.set_author(name="Change Reminder Message?")
            em.set_footer(text="Times Out after 60 seconds. Please send the message in this channel.")

            NewMessagePrompt = await Context.Message.channel.send(embed=em)

            try:
                NewMessage = await Vars.Bot.wait_for('message', check=check, timeout=60)
            except asyncio.TimeoutError:
                await Context.Message.channel.send("Timed out.", delete_after=10)
                if not Context.IsDeleted():
                    await Context.Message.add_reaction(Conversation.Emoji["x"])
                await QuietDelete(AskPrompt)
                return

            await Helpers.QuietDelete(NewMessagePrompt)

            # Now we have NewMessage
            NewContent = NewMessage.content
            NewReminder["Message"] = Sys.FirstCap(NewContent)

        elif response == "Upload New Image":
            if not ChosenReminder["Image"]:
                AskPrompt = "There is no image for this reminder. Please send one and we can add it."
            else:
                AskPrompt = "The following is the current Reminder Image. Please send its replacement"

            em = discord.Embed(description=AskPrompt, color=Remind.embed_color, timestamp=Helpers.EmbedTime())
            em.set_author(name="Reminder Image")
            em.set_footer(text="Times Out after 60 seconds. Please send the message in this channel.")
            if ChosenReminder["Image"]:
                em.set_image(url=ChosenReminder["Image"])

            NewMessagePrompt = await Context.Message.channel.send(embed=em)

            try:
                NewMessage = await Vars.Bot.wait_for('message', check=check, timeout=60)
            except asyncio.TimeoutError:
                await Context.Message.channel.send("Timed out.", delete_after=10)
                if not Context.IsDeleted():
                    await Context.Message.add_reaction(Conversation.Emoji["x"])
                await QuietDelete(AskPrompt)
                return

            await Helpers.QuietDelete(NewMessagePrompt)

            if not NewMessage.attachments:
                await Remind.ReturnError(Context.Message, "That message has no image. Cancelling edit.", sendformat=False)
                return

            ImageUrl = await Helpers.DownloadAndUpload(NewMessage, NewMessage.attachments[0])

            await Helpers.RemoveBotReactions(NewMessage)

            NewReminder["Image"] = ImageUrl.link

        # CHECKS
        if len(NewReminder["Message"]) > 500:
            await Remind.ReturnError(Context.Message, "Reminder message is too long! It can only be at max 500 characters.", sendformat=False)
            return
        WillBeRemindedTime = datetime.fromtimestamp(int(NewReminder["RemindStamp"]))
        if datetime.now() > WillBeRemindedTime:
            await Remind.ReturnError(Context.Message, "Time / Date has already occurred!", sendformat=False)
            return

        await Remind.DeleteSpecificReminder(ChosenReminder)
        if response == "Delete Reminder":
            em = discord.Embed(description="Successfully deleted the reminder.", color=Remind.embed_color)
            em.set_author(name="Deleted Reminder")
            await Context.Message.channel.send(embed=em)
            return
        await Remind.ReSaveReminder(NewReminder, WillBeRemindedTime)

        RemindStr = "```md\n# " + await Remind.GiveDateString(WillBeRemindedTime, datetime.now()) + "\nI Say >> " + NewReminder["Message"] + "```"

        em = discord.Embed(description="Successfully updated your reminder." + RemindStr, color=Remind.embed_color)
        em.set_author(name="Updated Reminder")
        if NewReminder["Image"]:
            em.set_image(url=NewReminder["Image"])

        await Context.Message.channel.send(embed=em)


class Todo:
    @staticmethod
    async def OnMessage(Context):
        await Todo.TodoCommand(Context)

    @staticmethod
    async def RetrieveData():
        "Called Internally to get all of the Todo Data"
        Data = Helpers.RetrieveData(type="Todo")
        if not Data:
            return {}

        else:
            return Data

    @staticmethod
    @Command(Prefix=True, Start="todo")
    async def TodoCommand(Context):
        messasge = Context.Message

        usableContent = message.content[5:].strip()

        TodoData = Todo.RetrieveData()


class Help:
    # Displays Help for a given command type
    @staticmethod
    async def OnMessage(Context):
        await Help.HelpCommandGeneral(Context)
        return

    @staticmethod
    @Command(Prefix=True, Include="help", MarkMessage=False)
    async def HelpCommandGeneral(Context):
        message = Context.Message
        # Runs per command, just to see if its either like: /yesno help or /help yesno
        usableContent = message.content

        if not message.content[1:5].lower() == "help" and not " help" in message.content.lower():
            return

        usableContent = usableContent[1:]

        seperatedWords = usableContent.strip().split(" ")

        if len(seperatedWords) > 2:
            return

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

        type = type.lower()

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


class Call:
    CurrentCallChannels = []

    @staticmethod
    async def OnMessage(Context):
        await Call.CreateCallChannel(Context)
        await Call.DeleteChannel(Context)

    @staticmethod
    @Command(Start="DeleteChannel", Admin=True, Prefix=True, NoSpace=True)
    async def DeleteChannel(Context):
        Permissions = await CheckPermissions(Context.Message.channel, ["manage_channels", "manage_guild", "manage_roles",
                                                                       "send_messages", "read_messages"], return_all=True)
        PermissionsNeeded = [key for key in Permissions if not Permissions[key]]

        if PermissionsNeeded:
            PermissionString = ", ".join(PermissionsNeeded)
            em = discord.Embed(description="I need the server permission(s): `" + PermissionString + "` in order to perform this action.", color=Vars.Bot_Color)
            em.set_author(name="Permissions Error", icon_url=Vars.Bot.user.avatar_url)
            await Context.Message.channel.send(embed=em)
            return

        confirmation = await Interraction.Confirmation(Context.Channel, Context.Message.author, "Delete this channel?")
        if confirmation:
            await Context.Message.channel.delete()

    @staticmethod
    async def on_voice_state_update(member, before, after):
        # called from Main.py, whenever a user joins a call or changes something
        if Call.CurrentCallChannels:
            if before.channel != after.channel:
                await Call.CallChannelAdd(member, before, after)

    @staticmethod
    @Command(Start="CreateCallChannel", Prefix=True, NoSpace=True)
    async def CreateCallChannel(Context):
        message = Context.Message

        guild = message.guild

        if not message.author.voice:
            em = discord.Embed(color=Vars.Bot_Color, description="In order to create a voice call channel, I need you to be in that voice channel! ")
            em.set_author(icon_url=Vars.Bot.user.avatar_url, name="Call Channel Error")

            await message.channel.send(embed=em)
            await message.add_reaction(Conversation.Emoji["x"])
            return

        Permissions = await CheckPermissions(Context.Message.channel, ["manage_channels", "manage_guild", "manage_roles",
                                                                       "send_messages", "read_messages"], return_all=True)

        PermissionsNeeded = [key for key in Permissions if not Permissions[key]]

        if PermissionsNeeded:
            PermissionString = ", ".join(PermissionsNeeded)
            em = discord.Embed(
                description="I need the server permission(s): `" + PermissionString + "` in order to perform this action.",
                color=Vars.Bot_Color)
            em.set_author(name="Permissions Error", icon_url=Vars.Bot.user.avatar_url)
            await Context.Message.channel.send(embed=em)
            return

        CurrentCall = message.author.voice.channel


        overwrites = {  # First Off, let's ensure that the default role cannot see it and that we can
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        CallChannel = await guild.create_text_channel(CurrentCall.name + " Text", overwrites=overwrites, category=CurrentCall.category)  # Create this call channel

        To_Be_Added = []
        for member in guild.members:
            if member.voice:
                To_Be_Added.append(member)

        if To_Be_Added:
            overwrites = {}
            for member in To_Be_Added:
                if not member.guild_permissions.administrator:
                    await CallChannel.set_permissions(member, read_messages=True, send_messages=True)

        InfoDict = {
            "TextChannelID": CallChannel.id,
            "VoiceChannelID": CurrentCall.id,
            "JoinedMembers": [member.id for member in To_Be_Added],
            "OriginalChannelID": message.channel.id
        }


        Call.CurrentCallChannels.append(InfoDict)

        Member_Mention = [member.mention for member in To_Be_Added]

        Welcome_Message = ", ".join(Member_Mention)
        Welcome_Message = "Welcome " + Welcome_Message + " to the Call Channel for the voice channel " + \
                          CallChannel.mention + ". Only the people who are in that voice channel, or who join, will be " \
                                                "able to read the contents of this channel.\n\nIt'll automatically delete " \
                                                "after everybody leaves the voice call. "

        await CallChannel.send(Welcome_Message)

    @staticmethod
    async def CallChannelAdd(member, before, after):
        if (before.channel and not after.channel):
            VoiceChannel = before.channel
            Action = "Left"
        elif (after.channel and not before.channel):
            VoiceChannel = after.channel
            Action = "Joined"

        FoundChannelInfo = None
        for ChannelInfo in Call.CurrentCallChannels:
            if ChannelInfo["VoiceChannelID"] == VoiceChannel.id:
                FoundChannelInfo = ChannelInfo

        if not FoundChannelInfo:  # Ensure that it's a call channel used
            return

        TextChannel = Vars.Bot.get_channel(ChannelInfo["TextChannelID"])

        if not await CheckPermissions(TextChannel, ["manage_channels", "manage_guild", "manage_roles",
                                              "send_messages", "read_messages"]):
            await TextChannel.send("It seems there's been a permissions change for me. Deleting all local data for this"
                                   "channel... I will no longer supervise or manage this channel to avoid bugs.")
            Call.CurrentCallChannels.remove(FoundChannelInfo)


        if Action == "Joined":
            if member.id not in FoundChannelInfo["JoinedMembers"]:
                if not member.guild_permissions.administrator:
                    await TextChannel.set_permissions(member, read_messages=True)
                await TextChannel.send("Welcome " + member.mention + " to the Call and the Call Channel.")

                Call.CurrentCallChannels.remove(FoundChannelInfo)

                FoundChannelInfo["JoinedMembers"].append(member.id)
                Call.CurrentCallChannels.append(FoundChannelInfo)


        elif Action == "Left":
            # Make a dict of each person in the call channel and if they're still in call
            UserInTextList = [member.guild.get_member(id) for id in FoundChannelInfo["JoinedMembers"]]
            InCallList = [1 if user.voice else 0 for user in UserInTextList]

            if sum(InCallList) == 0:
                # If nobody's in the call:
                Call.CurrentCallChannels.remove(FoundChannelInfo)

                OriginalChannel = member.guild.get_channel(FoundChannelInfo["OriginalChannelID"])
                await OriginalChannel.send("Everyone left call, so I deleted the call channel.")

                await TextChannel.delete()


@Command(Admin=True, Start="test", Prefix=True, NoSpace=True)
async def test(Context):
    Confirmation = await Helpers.Confirmation(Context.Message.channel, Context.Message.author, "This will turn off the "
                                                                                               "TimeThread. Continue?")

    if not Confirmation:
        return


    Timer.StopThreadTwo = True



    #ActivityType = discord.ActivityType.watching
    #game = discord.Activity(type=ActivityType, name=Context.Message.content)
    #await Vars.Bot.change_presence(status=discord.Status.online, activity=game)