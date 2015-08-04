##Deploying in Heroku

###The first time

...

Configure S3 to hold static assets:

    $ heroku config:set AWS_ACCESS_KEY_ID=
    $ heroku config:set AWS_SECRET_ACCESS_KEY=
    $ heroku config:set AWS_STORAGE_BUCKET_NAME=

Pick the theme:

    $ heroku config:set THEME=presupuesto-dvmi

###Updating the Heroku app

    $ git checkout heroku
    $ git rebase master
    $ git push --force heroku heroku:master
