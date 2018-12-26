import Sys, Cmd, Conversation
import discord, random, traceback, asyncio, sys, time
from datetime import datetime, timedelta
from Cmd import ContextMessage

class RedBot(discord.Client):
    async def on_ready(self):
        await Cmd.OnEvents.On_Ready(self)

    async def on_message(self, message):
        if message.author.bot:
            return

        # Ok so let's see if it's starting in Safety_Mode
        if Cmd.Vars.Safety_Mode:
            if not message.author.id == Cmd.Vars.Creator.id:
                await message.channel.send("I am currently in safety mode due to an error during the startup process")
                return
            await message.channel.send("`Safety Mode Response:`")


        if not Cmd.Vars.Ready and not Cmd.Vars.Safety_Mode:  # Ensures the bot is ready to go if a message is sent
            await asyncio.sleep(1)
            if not Cmd.Vars.Ready:  # If, after a second, it's not ready, the bot returns this thread
                return

        # Set Up ContextMessage
        Context = ContextMessage(message)

        if Cmd.Vars.Disabled:
            await Cmd.Log.LogSent(Context)
            Continue = await Cmd.Admin.Enable(Context)
            if not Continue:
                return

        await Cmd.test(Context)

        await Cmd.Log.LogSend(Context)

        await Cmd.Poll.OnMessage(Context)
        await Cmd.Help.OnMessage(Context)
        await Cmd.Calculate.OnMessage(Context)
        await Cmd.Remind.OnMessage(Context)
        await Cmd.Todo.OnMessage(Context)
        await Cmd.Tag.OnMessage(Context)
        await Cmd.Call.OnMessage(Context)
        await Cmd.Quotes.OnMessage(Context)

        # 'SEND' Commands
        await Cmd.Memes.SendMeme(Context)

        # 'OTHER' COMMANDS
        await Cmd.Other.OnMessage(Context)

        # ADMIN Commands
        await Cmd.Admin.CopyFrom(Context)
        await Cmd.Admin.Delete(Context)
        await Cmd.Admin.DeleteSince(Context)
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
        await Cmd.Admin.OsCommand(Context)

        await Cmd.Admin.GuildInfo(Context)

        await Cmd.Admin.SinglePrivateMessage(Context)

    async def on_message_edit(self, before, after):
        #await Cmd.Log.LogEdit(before, after)

        BeforeContext = ContextMessage(before)
        AfterContext = ContextMessage(after)
        await Cmd.Log.LogEdit(BeforeContext, AfterContext)

    async def on_error(self, event_method, *args, **kwargs):
        await Cmd.OnEvents.On_Error(event_method, *args, **kwargs)
        return

    async def on_reaction_add(self, reaction, user):
        if user == bot.user:
            return

        ReactionIsForPoll = await Cmd.Poll.OnReaction(reaction, user)
        if ReactionIsForPoll:
            return

        if reaction.emoji == Conversation.Emoji["quote"]:
            await Cmd.Quotes.OnQuoteReaction(reaction, user)
        if reaction.emoji == Conversation.Emoji["x"]:
            await Cmd.OnEvents.On_X(reaction, user)

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
        await Cmd.OnEvents.On_Message_Delete(message)
        Context = ContextMessage(message)
        await Cmd.Log.LogDelete(Context, None)

    async def on_member_join(self, member):
        await Cmd.OnEvents.On_Member_Join(member)

    async def on_member_remove(self, member):
        await Cmd.OnEvents.On_Member_Remove(member)

    async def on_guild_join(self, guild):
        await Cmd.OnEvents.On_Guild_Join(guild)

    async def on_guild_remove(self, guild):
        creator = Cmd.Vars.Creator
        await creator.send("I have officially left " + guild.name)

    async def on_voice_state_update(self, member, before, after):
        await Cmd.Call.on_voice_state_update(member, before, after)


async def getBot():
    return bot


bot = RedBot()
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
