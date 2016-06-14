import tldextract
import urlparse
target_host = "www.google.com"
local_host = "localhost"

tld = tldextract.extract(target_host).registered_domain

google_dict = {"/mail":"mail.google.com","/ServiceLogin":"accounts.google.com","/accountLoginInfoXhr": "accounts.google.com", "/signin":"accounts.google.com", "/CheckCookie":"accounts.google.com", "/ManageAccount":"accounts.google.com","/Logout":"accounts.google.com","/?authuser": "myaccount.google.com"}

path_host_dict = google_dict
def getHost(path):
    for x in path_host_dict:
        if path.startswith(x):
            return path_host_dict[x]
    return target_host

def replaceCookie(value):
    replace = [".www.google.com","www.google.com",".google.com","google.com"]
    for x in replace:
        value = value.replace(x, local_host)
    return value
