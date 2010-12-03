import re
import string
from random import choice

def word_wrap(string, width=80, ind1=0, ind2=0, prefix=''):
    """ word wrapping function.
        string: the string to wrap
        width: the column number to wrap at
        prefix: prefix each line with this string (goes before any indentation)
        ind1: number of characters to indent the first line
        ind2: number of characters to indent the rest of the lines
    """
    string = prefix + ind1*" " + string
    newstring = ""
    if len(string) > width:
        while True:
            # find position of nearest whitespace char to the left of "width"
            marker = width-1
            while not string[marker].isspace():
                marker = marker - 1

            # remove line from original string and add it to the new string
            newline = string[0:marker] + "\n"
            newstring = newstring + newline
            string = prefix + ind2*" " + string[marker+1:]

            # break out of loop when finished
            if len(string) <= width:
                break

    return newstring + string
    
def linkify(text):
    #s = text or ''
    #s = str(s)
    #urls
    #r="((?:ftp|https?)://[^ \t\n\r()\"']+)"
    #s=re.sub(r,r'<a rel="nofollow" href="\1">\1</a>',s)
    #twitter usernames
    #r = '(^|[\n ])@([A-Za-z0-9]*)(\s|\n|\r|\t|$)'
    #s = re.sub(r,r'\1<a rel="nofollow" href="http://www.twitter.com/\2">@\2</a>\1', s)
    return text

def randomkey():
    size = 8
    randomstr = ''.join([choice(string.letters + string.digits) for i in range(size)])
    return randomstr.lower()
    
def strip_tags(value):
    return re.sub(r'<[^>]*?>', '', value)