import Sys, Cmd, Conversation
import discord, random, traceback
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

    async def on_message(self, message):
        if message.author == bot.user:
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
        await Cmd.Other.No_Context(message)
        await Cmd.Other.ChatLinkShorten(message)
        await Cmd.Other.CountMessages(message)

        # ADMIN Commands
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

    async def on_error(self, event_method, *args, **kwargs):
        argument = args[0]
        # argument could be reaction, or message
        if type(argument) == discord.reaction.Reaction:
            channel = argument.message.channel
        elif type(argument) == discord.message.Message:
            channel = argument.channel

        error_text = "**ERROR**: *" + Sys.Response(Conversation.Error_Response).strip() + "*"
        await channel.send(error_text)
        to_send = str(traceback.format_exc())
        to_send = "```py" + to_send + "```"
        to_send = to_send.replace("C:\\Users\\spong\\", "")
        to_send = to_send.replace("C:/Users/spong/", "").replace("Desktop", "")
        await channel.send(to_send)
        await channel.send(bot.get_user(239791371110580225).mention)

    async def on_reaction_add(self, reaction, user):
        if user == bot.user:
            return
        if reaction.emoji == Conversation.Emoji["quote"]:
            await Cmd.Quotes.OnQuoteReaction(reaction, user)
        if reaction.emoji == Conversation.Emoji["x"]:
            await Cmd.On_React.On_X(reaction, user)

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
        print(red_role.name)

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