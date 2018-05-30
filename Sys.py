import time
from pyshorteners import Shortener
import random


def Read_Personal(data_type=None):
    """
    Reads the personal data from "Personal.txt"
    :param data_type: What specific application it wants data from, IE "Wolfram Alpha"
    :return: either a str or dict, depending on if you have a requested data_type or not
    """
    file = open("Personal.txt", 'r')
    lines = file.readlines()
    file.close()

    data_dict = {}
    key, part = '', []
    for line in lines:  # For each line
        line = line.replace('\n', '').strip()  # Clean it up
        if line:  # If there is text
            if line.startswith('@'):  # If a new section is found

                if key and part:  # If there's previous sections
                    if len(part) == 1:  # If there's only one item in this section
                        part = part[0]  # Set data_type from list to string
                    data_dict[key] = part  # No matter, add key and part
                key = line.replace('@', '')  # Set up new key
                part = []  # Replace part
            else:
                part.append(line)  # If its not a key, append to part
    if len(part) == 1:  # Cleanup stuff
        part = part[0]
    data_dict[key] = part

    if data_type:  # If a certain data_type is requested
        if data_type in data_dict:  # If data_type found
            return data_dict[data_type]
        else:  # If data_type not found
            return None
    else:  # If all data requested
        return data_dict


def PercentSimilar(compare, new):
    """
    Compares two strings based on how similar they are
    :param compare:  The string to compare against
    :param new:      The new string to use
    :return:         Returns number 1-100 on how similar. 100=Exact Same.
    Disregards case. 
    """
    compare = compare.lower().strip()
    new = new.lower().strip()

    top_row = ["q", "w", "e", "r", 'r', 't', 'y', 'u', 'i', 'o', 'p']
    mid_row = ["a", "s", "d", "f", 'g', 'h', 'j', 'k', 'l']  # +1 of top
    low_row = ["z", "x", "c", "v", 'b', 'n', 'm']  # +2 of top

    total_correct = 0
    correction_list = []
    for i in range(0,len(new)):
        if new[i] == compare[i]:
            total_correct += 4
            correction_list.append(4)
        else:
            if correction_list[-1] != 4:
                second_part = correction_list[-1] -2 if correction_list[-1] > 0 else 0
                total_correct += second_part
                correction_list.append(second_part)
            else:
                correction_list.append(2)
                total_correct += 2
    end_str = total_correct / len(new) * 100
    return round(end_str)


def SecMin(sec):
    minutes, hours, days = 0, 0, 0
    while True:
        if sec - 60 >= 0:
            sec = sec - 60
            minutes += 1
            if sec == 0:
                sec = -1  # Use of -1 so that string doesnt look like 1:::04
        else:
            break
    while True:
        if minutes - 60 >= 0:
            minutes = minutes - 60
            hours += 1
            if minutes == 0:
                minutes = -1
        else:
            break
    while True:
        if hours - 24 >= 0:
            hours = hours - 24
            days += 1
            if hours == 0:
                hours = -1
        else:
            break
    day_string, hour_string, minute_string, second_string = '', '', '', ''
    day_string = str(days) + ':' if days > 0 else day_string
    hour_string = str(hours) + ':' if hours > 0 else hour_string
    minute_string = str(minutes) + ':' if minutes > 0 else minute_string
    second_string = str(sec)

    hour_string = '00:' if hours == -1 else hour_string
    minute_string = '00:' if minutes == -1 else minute_string
    second_string = '00' if sec == -1 else second_string

    hour_string = '0' + hour_string if len(hour_string) == 2 else hour_string
    minute_string = '0' + minute_string if len(minute_string) == 2 else minute_string
    second_string = '0' + second_string if len(second_string) == 1 else second_string
    return day_string + hour_string + minute_string + second_string


def FirstCap(input_string):
    input_string = input_string.strip()
    if len(input_string) > 1:
        input_string = input_string[0].upper() + input_string[1:len(input_string)]
    else:
        input_string = input_string.upper()
    return input_string


def TimeStamp():
    # YEAR - MO - DA - HR - MN
    t = time.strftime('%Y')
    t += time.strftime('%m')
    t += time.strftime('%d')
    t += time.strftime('%H')
    t += time.strftime('%M')
    timestamp = int(t)
    return timestamp


Colors = {
    "RedBot": 0xff2600,
    "GoldBot": 0xFCC101
}


def Shorten_Link(link, undo=False):
    shortener = Shortener('Tinyurl')
    if undo:
        return shortener.expand(link)

    error = False
    new_link = False
    for i in range(0, 20):
        try:
            new_link = shortener.short(link)
            break
        except Exception:
            error = True
    if not new_link:
        return link
    return new_link

# Data for encoding / decoding
SY2VA = {'0': 0,
         '1': 1,
         '2': 2,
         '3': 3,
         '4': 4,
         '5': 5,
         '6': 6,
         '7': 7,
         '8': 8,
         '9': 9,
         'A': 10,
         'B': 11,
         'C': 12,
         'D': 13,
         'E': 14,
         'F': 15,
         'G': 16,
         'H': 17,
         'I': 18,
         'J': 19,
         'K': 20,
         'L': 21,
         'M': 22,
         'N': 23,
         'O': 24,
         'P': 25,
         'Q': 26,
         'R': 27,
         'S': 28,
         'T': 29,
         'U': 30,
         'V': 31,
         'W': 32,
         'X': 33,
         'Y': 34,
         'Z': 35,
         'a': 36,
         'b': 37,
         'c': 38,
         'd': 39,
         'e': 40,
         'f': 41,
         'g': 42,
         'h': 43,
         'i': 44,
         'j': 45,
         'k': 46,
         'l': 47,
         'm': 48,
         'n': 49,
         'o': 50,
         'p': 51,
         'q': 52,
         'r': 53,
         's': 54,
         't': 55,
         'u': 56,
         'v': 57,
         'w': 58,
         'x': 59,
         'y': 60,
         'z': 61,
         '!': 62}

async def Encode(num, base):
    VA2SY = dict(map(reversed, SY2VA.items()))
    # Take a integer and base to convert to.
    # Create an array to store the digits in.
    # While the integer is not zero:
    #     Divide the integer by the base to:
    #         (1) Find the "last" digit in your number (value).
    #         (2) Store remaining number not "chopped" (integer).
    #     Save the digit in your storage array.
    # Return your joined digits after putting them in the right order.
    array = []
    while num:
        num, value = divmod(num, base)
        array.append(VA2SY[value])
    return ''.join(reversed(array))


async def Decode(string, base):
    integer = 0
    for character in string:
        assert character in SY2VA, 'Found unknown character!'
        value = SY2VA[character]
        assert value < base, 'Found digit outside base!'
        integer *= base
        integer += value
    return integer


def Response(type, message=None):
    try:
        randnumber = random.randint(0, len(type)-1)
    except:
        return ''
    if message:
        return type[randnumber].format(message)
    else:
        return type[randnumber]

Channel = {
    "Errors": 343422937380028420,
    "DeleteLog": 422850384088793092
}


def DateFixer(month, day, year):
    def FindTotalMonthDays(month):
        TotalMonthDays = 0
        if month in [1, 3, 5, 7, 8, 10, 12]:
            TotalMonthDays = 31
        elif month in [4, 6, 9, 11]:
            TotalMonthDays = 30
        else:
            TotalMonthDays = 28

        return TotalMonthDays

    if day <= 0:
        month -= 1
        TotalMonthDays = FindTotalMonthDays(month)

        day = TotalMonthDays + day

    CurrentDays = FindTotalMonthDays(month)
    if day > CurrentDays:  # If the day is over the month
        month += 1
        day = day - CurrentDays

    if month <= 0:
        month = 12 - month
        year -= 1

    if month > 12:
        year += 1
        month = month - 12

    return month, day, year







    return month, day, year