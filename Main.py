import Sys, Cmd, Conversation
import discord, random

# AdminCmds = Cmd.Admin()

class MyClient(discord.Client):
    async def on_ready(self):
        print("Admin Code: " + str(Cmd.Vars.AdminCode))
        join = 'Logged on as {0}'.format(self.user)
        print(join + "\n" + "="*len(join))

        game = discord.Game(name="Version " + Cmd.Vars.Version)
        await bot.change_presence(status=discord.Status.online, game=game)

        # Check if it just restarted:
        await Cmd.Admin.CheckRestart()

        await Cmd.Memes.CleanMemes()  # Clean Meme Files
        await Cmd.Other.InterpretQuickChat()  # Prepare QuickChat Data
        Cmd.Cooldown.SetUpCooldown()  # Set up Cooldown Data

    async def on_message(self, message):
        if message.author == bot.user:
            return

        if Cmd.Vars.Disabled:
            await Cmd.Admin.Enable(message)
            return

        await Cmd.test(message)

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

        # ADMIN Commands
        await Cmd.Admin.Delete(message)
        await Cmd.Admin.Stop(message)
        await Cmd.Admin.LeaveServer(message)
        await Cmd.Admin.Disable(message)
        await Cmd.Admin.Talk(message)
        await Cmd.Admin.Status(message)
        await Cmd.Admin.Restart(message)
        await Cmd.Admin.Update(message)

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
bot.loop.create_task(Cmd.Timer.TimeThread(bot))
bot.run(token)