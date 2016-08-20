# Using Redis for Caching Data in Django

Data drives web applications. On the server, data moves between the application and the database, and in Django, the ORM is primarily used to construct those queries. Unfortunately, querying a database takes a toll on application performance. The more times the application calls the database during an HTTP request, the longer it takes to return a response. In an environment where <a href="https://www.nngroup.com/articles/response-times-3-important-limits/">users expect website response times of less than a second</a>, every database query affects the user experience.

Since many <a href="https://www.digitalocean.com/community/tutorials/5-common-server-setups-for-your-web-application">common server setups</a> separate the application from the database, Django must make a network call to retrieve data. Network latency plays a substantial role in the amount of time it takes for the ORM to execute database queries. 

> Latency is the amount of time needed to send information from one point to another. 

Given the direct relationship between the number of network calls and the time it takes for them to resolve, reducing that number should improve application performance.

One way to reduce the number of network calls is by caching data that does not change very often yet is frequently queried. Using a cache gives Django the ability to make a single network call (to the cache) instead of multiple calls to the database. 

In the following tutorial, I will demonstrate how to use Redis as a cache for Django. First, I will show you how to inspect the number of database queries your application is making without the cache in place. Next, I will walk you through the process of setting up and using the Redis server and the Redis CLI in conjunction with your Django application. Lastly, I will explain how to use the Django Debug Toolbar to conveniently monitor what network calls are being made when your application APIs are accessed.

# Setup

I have created an example application to introduce you to the concept of caching. Before you clone the repository, install <a href="https://virtualenvwrapper.readthedocs.org/en/latest/install.html">virtualenvwrapper</a>. This is a tool that lets you install the specific Python dependencies that your project needs, allowing you to target the versions and libraries required by your app in isolation. Once installation is complete, make a new virtual environment for our example app using the `mkvirtualenv` command. Creating a virtual environment also activates it.

Next, change directories to where you keep projects and clone the example app repository with `git`. Change directories to the cloned repository. Install all of the required Python dependencies with `pip`. You should see Django installed, along with <a href="http://niwinz.github.io/django-redis/latest/">django-redis</a> and <a href="https://django-debug-toolbar.readthedocs.io/en/stable/">Django Debug Toolbar</a>. We will dive into these libraries in the following sections.

After the installations have completed, finish setting up the example app by building the database and populating it with sample data. Make sure to create a superuser too, so that you can log into the admin site. Follow the code examples below and then try running the site to make sure it is working correctly. Visit the admin page to confirm that the data has been properly loaded.

```bash
local:~ user$ mkvirtualenv example
(example)local:~ user$ cd ~/Projects
(example)local:Projects user$ git clone https://github.com/ParentJA/example-django-redis.git
(example)local:Projects user$ cd example-django-redis
(example)local:example-django-redis user$ pip install -r requirements.txt
(example)local:example-django-redis user$ python manage.py migrate
(example)local:example-django-redis user$ python manage.py createsuperuser
(example)local:example-django-redis user$ python manage.py loaddata cookbook/fixtures/cookbook.json
(example)local:example-django-redis user$ python manage.py runserver
```

Once you have the Django app running, move onto the Redis installation. Download and install <a href="http://redis.io/download">Redis</a>. Alternatively, you can install Redis using a package manager such as *apt-get* or *homebrew* depending on your OS. 

> Redis is an open source (BSD licensed), in-memory data structure store, used as database, cache and message broker.

Run the Redis server from your terminal. In the example below, I have installed and am running `redis-server` according to the instructions on the Redis site.

```bash
local:Projects user$ cd redis-3.2.0
local:redis-3.2.0 user$ src/redis-server
```

Next, start up the Redis command-line interface (CLI) and test that it connects to the Redis server. We will be using the Redis CLI to inspect the keys that we add to the cache.

```bash
local:Projects user$ cd redis-3.2.0
local:redis-3.2.0 user$ src/redis-cli -n 1
127.0.0.1:6379[1]> ping
PONG
```

It is important to understand that Django and Redis are two separate applications, which are connected together via the installed *django-redis* library. Redis provides an API with various commands that a developer can use to act on the data store, and *django-redis* translates this API into Python code. Django uses *django-redis* to execute commands in Redis.

Looking at our example app, we can see the Redis configuration in the *settings.py* file. We define a default cache with the `CACHES` setting, using a built-in *django-redis* cache as our backend. Redis runs on port 6379 by default, and we define point to that location in our setting. One last thing to mention is that *django-redis* appends key names with a prefix and a version to help distinguish similar keys. In this case, I have defined the prefix to be "example".

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
        "KEY_PREFIX": "example"
    }
}
```

## Retrieving Data from a Database

Now that we have our example app up and running, we can dive into the code and make some interesting observations. As previously mentioned, most applications retrieve data via network calls to a database on an external server. Each network call takes time to resolve. Django provides a handy library that allows you to track your application's database queries. We can use utilities from `django.db` to see just how many network calls our application is sending.

In the example below, I have a function that retrieves all of the recipes in a cookbook. My data model includes three related entities, and every time I query the database, Django makes three separate network calls.

**cookbook/services.py**

```python
from django.db import reset_queries, connection
from cookbook.models import Recipe


def get_recipes_without_cache():
    # Reset database queries.
    reset_queries()

    # Retrieve recipes.
    recipes = list(Recipe.objects.prefetch_related('ingredient_set__food'))

    # Count database queries.
    print 'Database called {count} times.'.format(count=len(connection.queries))

    return recipes
```

You can test this behavior using the Python shell. Every time you call the `get_recipes_without_cache()` function, the database is queried three times. Try to run the function as many times as you want; the result never changes.

```bash
(example)local:example user$ python manage.py shell
>>> from cookbook.services import get_recipes_without_cache
>>> get_recipes_without_cache()
Database called 3 times.
>>> get_recipes_without_cache()
Database called 3 times.
>>> 
```

## Retrieving Data from a Cache

Imagine the total number of network calls that your application will make as users start to visit your site. If 1,000 users hit the API that retrieves cookbook recipes, then your application will query the database 3,000 times. That number only grows as your application scales. Luckily, these database queries are great candidates for caching. The recipes in a cookbook rarely change, if ever. Also, since viewing cookbooks is the central theme of the app, the API retrieving the recipes is guaranteed to be called frequently. 

> When considering which database queries to cache, remember to target ones that are called frequently yet seldom change.

In the example below, I modify the recipe retrieval function to use caching. When the function runs, it checks if the *recipes* key is in the cache. If the key exists, then the app retrieves the data from the cache and returns it. If not, Django queries the database and then stashes the result in the cache with the *recipes* key. The first time this function is run, Django will query the database and then will also make a network call to Redis to store the data in the cache. Each subsequent call to the function will completely bypass the database and will make a single network call to the Redis cache.

**cookbook/services.py**

```python
from django.core.cache import cache
from django.db import reset_queries, connection
from cookbook.models import Recipe


def get_recipes_with_cache():
    # Reset database queries.
    reset_queries()

    # Retrieve recipes.
    if 'recipes' in cache:
        recipes = cache.get('recipes')
    else:
        recipes = list(Recipe.objects.prefetch_related('ingredient_set__food'))
        cache.set('recipes', recipes)

    # Count database queries.
    print 'Database called {count} times.'.format(count=len(connection.queries))

    return recipes
```

You can test this behavior in the shell as in the previous example. Notice that the first time you run `get_recipes_with_cache()`, three database queries are made. Each time after that though, the database is not called at all!

```bash
(example)local:example user$ python manage.py shell
>>> from cookbook.services import get_recipes_with_cache
>>> get_recipes_with_cache()
Database called 3 times.
>>> get_recipes_with_cache()
Database called 0 times.
>>> 
```

At this point we can use the Redis CLI to look at what gets stored on the Redis server. In the Redis command-line, enter the `keys *` command, which returns all keys matching any pattern. You should see 1 key called "example:1:recipes". Remember, "example" is our key prefix, "1" is the version, and "recipes" is the name we gave the key. 

Next, run the `get example:1:recipes` command to retrieve the data from the Redis data store. You should see a lot of random characters. The Python objects pulled from the database are serialized using a special algorithm to compress the data for efficient storage. You are seeing the character representation of that data. When that data is retrieved from the cache by *django-redis*, it is deserialized back into Python objects.

```bash
local:redis user$ src/redis-cli -n 1
127.0.0.1:6379[1]> keys *
1) "example:1:recipes"
127.0.0.1:6379[1]> get example:1:recipes
```

You can see the result of the deserialization with some simple Python code.

```bash
(example)local:example user$ python manage.py shell
>>> from cookbook.services import get_recipes_with_cache
>>> recipes = get_recipes_with_cache()
>>> for recipe in recipes:
>>>     foods = [ingredient.food.name for ingredient in recipe.ingredient_set.all()]
>>>     print '{recipe}: {foods}'.format(recipe=recipe, foods=', '.join(foods))
>>>
```

**NOTE: Run the `flushall` command on the Redis CLI to clear all of the keys from the data store.**

## Using Django Debug Toolbar

We do not have to use the shell and the Redis CLI to track the network calls made during an HTTP request. In fact, *Django Debug Toolbar* is a useful tool we can use to show us the network activity that happens with each API call in our application. Run the example app and visit `http://localhost:8000/cookbook/` in your browser. You should see a simple page open with two recipes and a list of ingredients under each recipe name. 

You should also see a sidebar on the righthand side of your screen. Expand the sidebar and look at the options. Find the links labelled "SQL" and "Cache". If you clear your cache and reload the browser, you should see that 3 SQL calls were made to retrieve the cookbook recipes. Click on the link to view the details. You will notice that the example app also made a single network call to Redis to store the retrieved data in the cache. Reload your browser again and notice that the SQL queries have vanished. The "Cache" link detail shows that the app retrieved the Python data via the "recipes" key. Reload the page several more times and witness the behavior. The cache is called every time, while the database is not queried again.

## Wrap-up

Network calls are costly, and that cost adds up as your application grows in popularity. In some instances, you can greatly reduce the amount of network calls your application makes by caching commonly retrieved data. This tutorial gave you a glimpse of how to implement caching, yet as you explore caching more in depth, you will find that it is a complex topic. Implementing caching in a robust application has many pitfalls and gotchas. As you develop applications in Django, keep performance in mind. Learn more about optimizing performance through smarter database queries and caching, and remember to always test locally using the *Django Debug Toolbar*.
