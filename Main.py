import Sys, Cmd, Conversation
import discord, random

# AdminCmds = Cmd.Admin()

class MyClient(discord.Client):
    async def on_ready(self):
        print("Admin Code: " + str(Cmd.Vars.AdminCode))
        join = 'Logged on as {0}'.format(self.user)
        print(join + "\n" + "="*len(join))

        # Check if it just restarted:
        await Cmd.Admin.CheckRestart()

        await Cmd.Memes.CleanMemes()  # Clean Meme Files
        await Cmd.Other.InterpretQuickChat()  # Prepare QuickChat Data

    async def on_message(self, message):
        if message.author == bot.user:
            return

        if Cmd.Vars.Disabled:
            await Cmd.Admin.Enable(message)
            return

        await Cmd.Other.QuickChat(message)
        await Cmd.test(message)
        await Cmd.Quotes.SendQuote(message)
        await Cmd.Quotes.QuoteCommand(message)


        await Cmd.Memes.SendMeme(message)

        await Cmd.Other.YesNo(message)
        await Cmd.Other.Change_Color(message)
        await Cmd.Other.Poll(message)

        # ADMIN Commands
        await Cmd.Admin.Delete(message)
        await Cmd.Admin.Stop(message)
        await Cmd.Admin.LeaveServer(message)
        await Cmd.Admin.Disable(message)
        await Cmd.Admin.Talk(message)
        await Cmd.Admin.Status(message)
        await Cmd.Admin.Restart(message)

    async def on_reaction_add(self, reaction, user):
        if user == bot.user:
            return
        if reaction.emoji == Conversation.Emoji["quote"]:
            await Cmd.Quotes.OnQuoteReaction(reaction, user)
        if reaction.emoji == Conversation.Emoji["x"]:
            await Cmd.On_React.On_X(reaction, user)

    async def on_member_join(self, member):
        await Cmd.Other.On_Member_Join(member)



async def getBot():
    return bot


bot = MyClient()
Cmd.Vars.Bot = bot
token = Sys.Read_Personal(data_type='Golden_Run_Code')
bot.loop.create_task(Cmd.Timer.TimeThread(bot))
bot.run(token)