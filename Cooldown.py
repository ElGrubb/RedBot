import datetime, time

def TimeStamp():
    import datetime
    return int(datetime.datetime.now().timestamp())


class Cooldown:
    meme_types = ["meme", "quote", "nocontext", "delete"]
    data = {}
    defaults = {
        "meme": [30, 30],
        "quote": [60, 45],
        "nocontext": [5, 10],
        "delete": [5, 3]
    }


def SetUpCooldown():
    for meme_type in Cooldown.meme_types:
        Cooldown.data[meme_type] = {}


def AddUser(meme_type, user, guild):
    # Make sure to turn user into user id
    if user not in Cooldown.data[meme_type]:  # If it doesn't exist so far
        addition = {
            "guild": guild,   # Server ID
            "user": user,       # User ID
            "times": 1,         # How many times they have done it since its hit 0
            "wait": Cooldown.defaults[meme_type][0],         # How long to wait until they can do it again
            "refrac": Cooldown.defaults[meme_type][1],       # How long to wait after they can do it before it goes to 0
            "call": TimeStamp()

        }
        Cooldown.data[meme_type][user] = addition  # Set Cooldown.data[meme_type] with a new user as that user
        return 60


def UpdateUser(meme_type, user, guild):
    if user in Cooldown.data[meme_type]:  # IF the ID is existing
        Cooldown.data[meme_type][user]["times"] += 1
        Cooldown.data[meme_type][user]["wait"] += round((Cooldown.defaults[meme_type][0] * Cooldown.data[meme_type][user]["times"]/2))
        Cooldown.data[meme_type][user]["refrac"] = int(Cooldown.data[meme_type][user]["wait"]/2)
        Cooldown.data[meme_type][user]["call"] = TimeStamp()

        if Cooldown.data[meme_type][user]["wait"] > 600:
            Cooldown.data[meme_type][user]["wait"] = 540
            Cooldown.data[meme_type][user]["refrac"] = 480

        return Cooldown.data[meme_type][user]["wait"]


def CheckCooldown(meme_type, user, guild):
    now = TimeStamp()
    user = int(user.id)
    guild = int(guild.id)

    # Runs when a command is fired.
    if user not in Cooldown.data[meme_type]:  # Adds person to database
        AddUser(meme_type, user, guild)
        return False
    elif user in Cooldown.data[meme_type]:  # If they're already in
        wait = Cooldown.data[meme_type][user]["wait"]
        refrac = Cooldown.data[meme_type][user]["refrac"]
        change = now - Cooldown.data[meme_type][user]["call"]

        if change >= wait:  # If wait ime is over
            if change >= wait + refrac:  # If refrac time is over
                del Cooldown.data[meme_type][user]
                AddUser(meme_type, user, guild)
                return False
            else:
                UpdateUser(meme_type, user, guild)
        else:  # If cool down is still going
            return wait - change
    return True


SetUpCooldown()