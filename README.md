IFB299 Community Organization

## Dependencies
* [Django](https://www.djangoproject.com/)
* [Bootstrap3 for Django](https://github.com/dyve/django-bootstrap3)
* [Django Notifications](https://github.com/django-notifications/django-notifications)

## How to setup and run the django server
Django requires python (preferably python3 but python2 should work) and pip to install. Django can be installed with the following command
```shell
pip install Django==1.10.1
```
Next the servers dependencies need to be install. This can be done using the following commands
```shell
pip install django-bootstrap3
pip install django-notifications-hq
```
Now with the dependences installed the django server can be started from the CommunityOrganization folder by running the following command
```shell
python manage.py runserver
```
Django should start a server at localhost on port 8000
```shell
http://127.0.0.1:8000/
```
or
```shell
http://localhost:8000/
```
