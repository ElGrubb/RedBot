import Sys, Cmd, Conversation
import discord, random, traceback, asyncio
from datetime import datetime, timedelta


class MyClient(discord.Client):
    async def on_ready(self):
        print("Admin Code: " + str(Cmd.Vars.AdminCode))
        join = 'Logged on as {0}'.format(self.user)
        print(join + "\n" + "="*len(join))
        game = discord.Game(name="v" + Cmd.Vars.Version + "  |  @Dom")
        await bot.change_presence(status=discord.Status.online, game=game)

        Cmd.Vars.Creator = Cmd.Vars.Bot.get_user(int(Sys.Read_Personal(data_type="Dom_ID")))
        # Check if it just restarted:
        await Cmd.Admin.CheckRestart()

        await Cmd.Memes.CleanMemes()  # Clean Meme Files
        await Cmd.Other.InterpretQuickChat()  # Prepare QuickChat Data
        await Cmd.Cooldown.SetUpCooldown()  # Set up Cooldown Data
        Cmd.Vars.start_time = datetime.utcnow()

        if Sys.Read_Personal(data_type="Bot_Type") == "RedBot":
            em = discord.Embed(title="I have just started", timestamp=Cmd.Vars.start_time, color=Cmd.Vars.Bot_Color)
            await Cmd.Vars.Creator.send(embed=em)
        Cmd.Vars.Ready = True

    async def on_message(self, message):
        if message.author == bot.user:
            return

        if not Cmd.Vars.Ready:  # Ensures the bot is ready to go if a message is sent
            await asyncio.sleep(1)
            if not Cmd.Vars.Ready:  # If, after a second, it's not ready, the bot returns this thread
                return

        if Cmd.Vars.Disabled:
            await Cmd.Admin.Enable(message)
            return

        await Cmd.test(message)
        await Cmd.Help(message)

        # 'SEND' Commands
        await Cmd.Memes.SendMeme(message)
        await Cmd.Quotes.SendQuote(message)
        await Cmd.Quotes.QuoteCommand(message)

        # 'OTHER' COMMANDS
        await Cmd.Other.QuickChat(message)
        await Cmd.Other.YesNo(message)
        await Cmd.Other.Change_Color(message)
        await Cmd.Other.Poll(message)
        await Cmd.Other.OldWeather(message)
        await Cmd.Other.Calculate(message)
        await Cmd.Other.NoContext(message)
        await Cmd.Other.ChatLinkShorten(message)
        await Cmd.Other.CountMessages(message)

        # ADMIN Commands
        await Cmd.Admin.CopyFrom(message)
        await Cmd.Admin.Juliana(message)
        await Cmd.Admin.Delete(message)
        await Cmd.Admin.Stop(message)
        await Cmd.Admin.LeaveServer(message)
        await Cmd.Admin.Disable(message)
        await Cmd.Admin.Talk(message)
        await Cmd.Admin.Status(message)
        await Cmd.Admin.Restart(message)
        await Cmd.Admin.Update(message)
        await Cmd.Admin.SaveDataFromMessage(message)
        await Cmd.Admin.SendData(message)
        await Cmd.Admin.ChangePersonal(message)
        await Cmd.Admin.Broadcast(message)

        await Cmd.Admin.SinglePrivateMessage(message)

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

        error_text = "**ERROR**: *" + Sys.Response(Conversation.Error_Response).strip() + "*"

        to_send = str(traceback.format_exc())
        to_send = "```py" + to_send + "```"
        to_send = to_send.replace("C:\\Users\\spong\\", "")
        to_send = to_send.replace("C:/Users/spong/", "").replace("Desktop", "")
        still_up = "`Function stopped mid process. Bot still active`"
        message = error_text + "\n" + to_send + still_up + "\n" + Cmd.Vars.Creator.mention

        crash_channel = bot.get_channel(Sys.Channel["Errors"])

        # Log in #Crashes
        to_log = datetime.now().strftime("%b %d %Y %r") + "\n**Location:**  "
        if has_channel:
            to_log += channel.guild.name + "   /   #" + channel.name + "   (*" + str(channel.id) + "*)"
        to_log += "\n" + context + "\n" + to_send

        if has_channel:
            if await Cmd.CheckPermissions(channel, "send_messages"):
                await channel.send(message)
            else:
                has_channel = False
        if not has_channel:
            await crash_channel.send(Cmd.Vars.Creator.mention + ", this below was `Unlogged` in original channel.\n")

        to_log = "== -- " * 4 + "==\n" + to_log
        await crash_channel.send(to_log)


    async def on_reaction_add(self, reaction, user):
        if user == bot.user:
            return
        if reaction.emoji == Conversation.Emoji["quote"]:
            await Cmd.Quotes.OnQuoteReaction(reaction, user)
        if reaction.emoji == Conversation.Emoji["x"]:
            await Cmd.On_React.On_X(reaction, user)

    async def on_raw_reaction_add(self, emoji, message_id, channel_id, user_id):
        channel = bot.get_channel(channel_id)
        message = await channel.get_message(message_id)

        if user_id == bot.user.id:
            return

        # If it was sent after bot was turned on / restarted
        if message.created_at >= Cmd.Vars.start_time:
            return

        # If the reaction was added to a message not in the cache
        # Now to find the reaction and user
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

bot.loop.create_task(Cmd.Timer.TimeThread())
bot.run(token)