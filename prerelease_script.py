import subprocess


def compilemessages(data):
    subprocess.call(['django-admin', 'compilemessages'])
