# import pykobo

from kobo import manager


URL_KOBO = "https://kf.kobotoolbox.org/"
API_VERSION = 2
MYTOKEN = "f820e2c138e487e28c87fbb9af4685f7f68051a4"


# Initialize the Manager object

km = manager.Manager(url=URL_KOBO, api_version=API_VERSION, token=MYTOKEN)
my_forms = km.get_forms()
print(my_forms)
# km = pykobo.Manager(url=URL_KOBO, api_version=API_VERSION, token=MYTOKEN)

uid = "aAfruCuf8SbUd4jaztbmto"

my_form = km.get_form(uid)

my_form.fetch_data()

print(my_form.data)