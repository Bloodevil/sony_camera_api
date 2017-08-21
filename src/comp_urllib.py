try:
  python_version = 3
  import urllib.request, urllib.error, urllib.parse
except ImportError:
  python_version = 2
  import urllib2


def urlopen(url, data = None):
  global python_version
  if python_version == 3:
    return urllib.request.urlopen(url, data)
  elif python_version == 2:
    return urllib2.urlopen(url, data)
