===============
Liquidb
===============

Liquidb is a Django app that simplifies migration management.
It introduces commits (savepoints) that allows developer to take snapshot of current migration state of whole Django project.
Snapshot introduces abstraction layer, which let you easily switch back and forth in complicated migration graph of dependent apps.
In order to roll(back/forward) all migrations should be revertable.



Requirements
============

Django Liquidb requires:
    * Django 2.2 or later;
    * Python 3.6 or later.


Getting It
==========

You can get Django Liquidb by using pip::

    $ pip install django-liquidb

If you want to install it from source, grab the git repository from GitHub and run setup.py::

    $ git clone git@github.com:Gusakovskiy/django-liquidb.git
    $ cd django-liquidb
    $ python setup.py install



Quick start
-----------

1. Add "Liquidb" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'liquidb',
    ]


2. Run ``python manage.py migrate liquidb`` to create the liquidb models.
3. Create initial commit ``python manage.py create_migration_snapshot --name init``

Using It
-----------

Create snapshot of your current state::

    $ branch=$(git branch | sed -n -e 's/^\* \(.*\)/\1/p')
    $ hash=$(git rev-parse $branch)
    $ python manage.py create_migration_snapshot --name $branch-${hash:0:8}

In case you want to overwrite some snapshot::

    $ python manage.py create_migration_snapshot --name $branch-${hash:0:8} --overwrite 1


Return to desired state of db::

    $ python manage.py checkout_snapshot --name state_name

Return to latest snapshot::

    $ python manage.py checkout_latest_snapshot

If snapshot history is messed up you always can delete it without impact on your migration state and start from scratch::

    $ python manage.py delete_snapshot_history


If want to delete only one snapshot(it can not delete currently applied snapshot remember to checkout before that)::

    $ python manage.py delete_snapshot_by_name --name name



Or if you prefer admin vies you can always visit `/admin/liquidb/snapshot/` and create/apply/delete snapshot there.
> If you would like to change to readonly view in admin please change ADMIN_SNAPSHOT_ACTIONS env variable to False or overwrite it you settings


Getting Involved
================

Open Source projects can always use more help. Fixing a problem, documenting a feature, adding
translation in your language. If you have some time to spare and like to help us, here are the places to do so:

- GitHub: https://github.com/Gusakovskiy/django-liquidb

Support
=======

Django Liquidb is development and maintained by developers in an Open Source manner.
Any support is welcome. You could help by writing documentation, pull-requests, report issues and/or translations.

Please remember that nobody is paid directly to develop or maintain Django Liquidb so we do have to divide our time
between work/family/hobby/this project and the rest of life.