import Sys, Cmd, Conversation
import discord, random, traceback, asyncio, sys, time
from datetime import datetime, timedelta


class ContextMessage:
    "Okay so this class is made whenever a message is sent"

    __slots__ = ['HasPrefix', 'IsAdmin', 'InDM', 'IsCreator', 'OriginalContent', "Message", 'StrippedContent', "Deleted"]

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
            if message.content.strip()[0] in Cmd.Vars.Command_Prefixes:
                self.HasPrefix = True
                self.StrippedContent = self.StrippedContent[1:]

        if message.author.id in Cmd.Ranks.Admins:
            self.IsAdmin = True

        if type(message.channel) == discord.channel.DMChannel:
            self.InDM = True

        if message.author.id == Cmd.Ranks.CreatorID:
            self.IsCreator = True

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


class MyClient(discord.Client):
    async def on_ready(self):
        print("Admin Code: " + str(Cmd.Vars.AdminCode))
        join = 'Logged on as {0}'.format(self.user)
        print(join + "\n" + "="*len(join))
        await Cmd.Other.StatusChange()

        Cmd.Vars.Creator = Cmd.Vars.Bot.get_user(int(Sys.Read_Personal(data_type="Dom_ID")))
        # Check if it just restarted:
        isupdate = await Cmd.Admin.CheckRestart()  # True or False if update

        await Cmd.Memes.CleanMemes()  # Clean Meme Files
        await Cmd.Other.InterpretQuickChat()  # Prepare QuickChat Data
        await Cmd.Cooldown.SetUpCooldown()  # Set up Cooldown Data
        Cmd.Vars.start_time = datetime.utcnow()

        if Sys.Read_Personal(data_type="Bot_Type") == "RedBot":  # vs GOLDBOT
            string = "I have just started up"
            if isupdate:
                string += ". Updated."
            em = discord.Embed(title=string, timestamp=Cmd.Vars.start_time, color=Cmd.Vars.Bot_Color)
            await Cmd.Vars.Creator.send(embed=em)

        await Cmd.Remind.CheckForOldReminders()
        await Cmd.Poll.RefreshData()
        await Cmd.Poll.CleanData()


        Cmd.Vars.Ready = True

    async def on_message(self, message):
        if message.author.bot:
            return

        if not Cmd.Vars.Ready:  # Ensures the bot is ready to go if a message is sent
            await asyncio.sleep(2)
            if not Cmd.Vars.Ready:  # If, after a second, it's not ready, the bot returns this thread
                return


        # Set Up ContextMessage
        Context = ContextMessage(message)

        if Cmd.Vars.Disabled:
            await Cmd.Log.LogSent(message)
            Continue = await Cmd.Admin.Enable(message)
            if not Continue:
                return

        await Cmd.test(Context)

        await Cmd.Log.LogSent(message)

        await Cmd.Poll.OnMessage(Context)
        await Cmd.Help.OnMessage(Context)
        await Cmd.Calculate.OnMessage(Context)
        await Cmd.Remind.RemindCommand(Context)
        await Cmd.Todo.OnMessage(Context)
        await Cmd.Tag.OnMessage(Context)
        await Cmd.Call.OnMessage(Context)

        # 'SEND' Commands
        await Cmd.Memes.SendMeme(Context)
        await Cmd.Quotes.SendQuote(Context)
        await Cmd.Quotes.QuoteCommand(Context)

        # 'OTHER' COMMANDS
        await Cmd.Other.OnMessage(Context)

        # ADMIN Commands
        await Cmd.Admin.CopyFrom(Context)
        await Cmd.Admin.Delete(Context)
        await Cmd.Admin.Stop(Context)
        await Cmd.Admin.LeaveServer(Context)
        await Cmd.Admin.ForceLeave(Context)
        await Cmd.Admin.Disable(Context)
        await Cmd.Admin.Talk(Context)
        await Cmd.Admin.Status(Context)
        await Cmd.Admin.Restart(Context)
        await Cmd.Admin.Update(Context)
        await Cmd.Admin.SaveDataFromMessage(Context)
        await Cmd.Admin.SendData(Context)
        await Cmd.Admin.ChangePersonal(Context)
        await Cmd.Admin.Broadcast(Context)
        await Cmd.Admin.PermissionsIn(Context)

        await Cmd.Admin.GuildInfo(Context)

        await Cmd.Admin.SinglePrivateMessage(Context)


    async def on_message_edit(self, before, after):
        await Cmd.Log.LogEdit(before, after)


    async def on_error(self, event_method, *args, **kwargs):
        argument = args[0]

        has_channel = True
        context = None
        # argument could be reaction, or message
        if type(argument) == discord.reaction.Reaction:
            channel = argument.message.channel
            context = "**Reaction** on message by `" + argument.message.author + "` saying `" + argument.message.content[0:40]
            try:
                context += "`\nReaction was `" + argument.emoji + "` by `" + str(await argument.users().flatten())
            except:
                context += "\nError Retrieving Reaction Info"
        elif type(argument) == discord.message.Message:
            channel = argument.channel
            context = "**Message** by  `" + argument.author.name + "`   `" + str(argument.author.id) + \
                      "`   saying   `" + argument.content[0:80] + "`  "

        elif type(argument) == discord.emoji.PartialReactionEmoji:
            channel = bot.get_channel(args[2])
            message = await channel.get_message(args[1])
            adder = channel.guild.get_member(args[3])
            context = "**Partial Reaction** on message by  `" + message.author.name + "`  saying  `" + message.content[0:40]
            try:
                context += " `\nReaction was  `" + argument.name + "`  by  `" + adder.name + "`"
            except:
                context += "` \nError Retrieving Reaction Info"
        else:
            has_channel = False

        exc_type, exc_value, exc_traceback = sys.exc_info()
        tblist = traceback.format_exception(exc_type, exc_value, exc_traceback)

        NewTBList = []
        for item in tblist:
            if "site-packages\discord" not in item:
                temp = item.replace("\\", "/")
                temp = temp.replace("C:/Users/spong/Desktop", "").replace("/home/pi/Desktop", "")
                temp = temp.replace("File \"/", "")
                temp = temp.replace("RedBot/", "").replace("GoldBot/", "")

                temp = "\"" + temp.strip()

                temp = temp.replace("\n", ":\n")
                NewTBList.append(temp)

        NewTBList = NewTBList[1:]

        ErrorMessage = NewTBList[-1][1:]

        NewTBList = NewTBList[0 : len(NewTBList) - 1]

        FullTraceBack = "\n".join(NewTBList)
        FullTraceBack += "\n" + ErrorMessage

        # First we send the small error message, and then the big boys come out
        description = Sys.Response(Conversation.Error_Response).strip()
        description += "\n    *`" + ErrorMessage + "`*"
        em = discord.Embed(color=Cmd.Vars.Bot_Color, description=description)
        em.set_author(name="RedBot Error", icon_url=bot.user.avatar_url, url="http://www.github.com/ElGrubb/RedBot")

        em.set_footer(text="Don't worry, I'm still running, but I have terminated the command. ")

        send = "```py\n" + FullTraceBack + "```"


        try:
            await channel.send(embed=em)
        except discord.NotFound:
            pass


        # Full Error Report time:
        UserName = ""
        UserID = ""
        OriginalMsg = ""

        if Cmd.IsDMChannel(channel):
            ChannelName = "Private DM"
            GuildName = "Direct Message"

        else:
            ChannelName = "#" + channel.name + " *(" + str(channel.id) + ")*"
            GuildName = channel.guild.name + " *(" + str(channel.guild.id) + ")*"


        FullError = ""
        FullError += datetime.now().strftime("%b %d %Y %r") + \
                     "\n**Location:** " + ChannelName + " in " + GuildName + \
                     "\n**Context:** " + context


        FullError += "```py\n" + FullTraceBack + "```"


        crash_channel = bot.get_channel(Sys.Channel["Errors"])

        await crash_channel.send(FullError)



        return



        # Log in #Crashes
        to_log = datetime.now().strftime("%b %d %Y %r") + "\n**Location:**  "
        if has_channel:
            to_log += channel.guild.name + "   /   #" + channel.name + "   (*" + str(channel.id) + "*)"
        to_log += "\n" + context + "\n" + to_send

        if has_channel:
            if await Cmd.CheckPermissions(channel, "send_messages"):
                await channel.send(embed=em)
            else:
                has_channel = False
        if not has_channel:
            await crash_channel.send(Cmd.Vars.Creator.mention + ", this below was `Unlogged` in original channel.\n")


        em = discord.Embed(description=to_log, color=Cmd.Vars.Bot_Color)

        await crash_channel.send(embed=em)


    async def on_reaction_add(self, reaction, user):
        if user == bot.user:
            return

        ReactionIsForPoll = await Cmd.Poll.OnReaction(reaction, user)
        if ReactionIsForPoll:
            return


        if reaction.emoji == Conversation.Emoji["quote"]:
            await Cmd.Quotes.OnQuoteReaction(reaction, user)
        if reaction.emoji == Conversation.Emoji["x"]:
            await Cmd.On_React.On_X(reaction, user)

    async def on_raw_reaction_add(self, payload):
        message_id = payload.message_id
        channel_id = payload.channel_id
        user_id = payload.user_id
        guild_id = payload.guild_id
        emoji = payload.emoji

        channel = bot.get_channel(channel_id)

        try:
            message = await channel.get_message(message_id)
        except:
            return

        if user_id == bot.user.id:
            return

        # If it was sent after bot was turned on / restarted
        if message.created_at >= Cmd.Vars.start_time:
            return

        # If the reaction was added to a message not in the cache
        # Now to find the reaction and user
        if Cmd.IsDMChannel(channel):
            return

        user = channel.guild.get_member(user_id)
        reaction = None
        given_emoji = emoji.name
        # For each reaction in the message
        for partial_reaction in message.reactions:
            if partial_reaction.custom_emoji:  # If the emoji is custom (str)
                # shorten <:etc:124125> to etc
                to_test = str(partial_reaction.emoji).split(":")[1]
            else:
                # If not, just keep it as the string it is
                to_test = partial_reaction.emoji
            if to_test == given_emoji:
                reaction = partial_reaction
                break

        if reaction:
            await self.on_reaction_add(reaction, user)


    async def on_message_delete(self, message):
        await Cmd.Other.On_Message_Delete(message)

    async def on_member_join(self, member):
        await Cmd.Other.On_Member_Join(member)

    async def on_member_remove(self, member):
        await Cmd.Other.On_Member_Remove(member)

    async def on_guild_join(self, guild):
        to_send = "I have just been added to " + guild.name
        initial_message = await Cmd.Vars.Creator.send(to_send)
        confirmation = await Cmd.Helpers.Confirmation(Cmd.Vars.Creator, "Should I?", deny_text="Okay, leaving")

        if confirmation == False:
            await guild.leave()
            await initial_message.delete()
            await Cmd.Vars.Creator.send("I have officially left " + guild.name)

        bot_member = None
        for member in guild.members:
            if member.id == Cmd.Vars.Bot.id:
                bot_member = member

        red_role = bot_member.roles[0]

        color = discord.Colour(Cmd.Vars.Bot_Color)
        await red_role.edit(color=color)


    async def on_guild_remove(self, guild):
        creator = Cmd.Vars.Creator
        await creator.send("I have officially left " + guild.name)


async def getBot():
    return bot


bot = MyClient()
Cmd.Vars.Bot = bot
if Sys.Read_Personal(data_type="Bot_Type") == "GoldBot":
    token = Sys.Read_Personal(data_type='Golden_Run_Code')
elif Sys.Read_Personal(data_type="Bot_Type") == "RedBot":
    token = Sys.Read_Personal(data_type='Run_Code')
else:
    token = Sys.Read_Personal(data_type='Run_Code')

def Main():
    bot.loop.create_task(Cmd.Timer.TimeThread())
    bot.run(token)

while True:
    Main()
